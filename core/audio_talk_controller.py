"""Cancellable ONVIF intercom: Qt capture on its owning thread, network I/O off it."""
import queue
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtMultimedia import QMediaDevices, QAudioSource, QAudioFormat, QAudioDevice
from core.camera_urls import build_rtsp_url
from core.rtsp_audio import RTSPBackchannel, AudioProtocolError


def _calc_alaw_sample(sample):
    mask = 0xD5 if sample >= 0 else 0x55
    value = min(32767, sample if sample >= 0 else -sample - 1)
    if value < 256:
        encoded = value >> 4
    else:
        segment = value.bit_length() - 8
        encoded = (segment << 4) | ((value >> (segment + 3)) & 15)
    return encoded ^ mask


def _calc_mulaw_sample(sample):
    mask = 0xFF if sample >= 0 else 0x7F
    value = min(32635, abs(sample)) + 132
    segment = max(0, value.bit_length() - 8)
    return ((segment << 4) | ((value >> (segment + 3)) & 15)) ^ mask


def encode_g711(pcm, codec="PCMA", gain=1.0):
    samples = np.frombuffer(pcm[:len(pcm) // 2 * 2], dtype="<i2").astype(np.float64)
    samples = np.clip(np.rint(samples * gain), -32768, 32767).astype(np.int16)
    encode = _calc_alaw_sample if codec == "PCMA" else _calc_mulaw_sample
    return bytes(encode(int(value)) for value in samples)


def pcm16_to_alaw(pcm_bytes, gain=1.0):
    return encode_g711(pcm_bytes, "PCMA", gain)


def compute_audio_level(pcm_bytes):
    if len(pcm_bytes) < 2:
        return 0.0
    samples = np.frombuffer(pcm_bytes[:len(pcm_bytes) // 2 * 2], dtype="<i2").astype(float)
    return min(1.0, float(np.sqrt(np.mean(samples * samples))) / 8000)


class AudioConverter:
    """Streaming native microphone PCM -> mono 8 kHz signed 16-bit PCM."""
    def __init__(self, sample_rate, channels, sample_format):
        self.rate = sample_rate
        self.channels = channels
        self.format = sample_format
        self.buffer = np.empty(0, dtype=float)
        self.position = 0.0
        self.remainder = b""
        self.filter_kernel = None
        self.filter_tail = np.empty(0)
        if sample_rate > 8000:
            cutoff = 3600 / sample_rate
            positions = np.arange(31) - 15
            kernel = 2 * cutoff * np.sinc(2 * cutoff * positions) * np.hamming(31)
            self.filter_kernel = kernel / kernel.sum()
            self.filter_tail = np.zeros(30)

    def convert(self, raw):
        formats = {"Int16": ("<i2", 32768), "Int32": ("<i4", 2147483648),
                   "UInt8": ("u1", 128), "Float": ("<f4", 1)}
        if self.format not in formats or self.rate <= 0 or self.channels <= 0:
            raise ValueError("Unsupported microphone format")
        dtype, scale = formats[self.format]
        width = np.dtype(dtype).itemsize * self.channels
        raw = self.remainder + raw
        size = len(raw) // width * width
        self.remainder = raw[size:]
        if not size:
            return b""
        values = np.frombuffer(raw[:size], dtype=dtype).astype(float)
        if self.format == "UInt8":
            values -= 128
        values = np.nan_to_num(values / scale).reshape(-1, self.channels).mean(axis=1)
        if self.filter_kernel is not None:
            extended = np.concatenate((self.filter_tail, values))
            self.filter_tail = extended[-30:]
            values = np.convolve(extended, self.filter_kernel, mode="valid")
        self.buffer = np.concatenate((self.buffer, values))
        if len(self.buffer) < 2:
            return b""
        positions = np.arange(self.position, len(self.buffer) - 1, self.rate / 8000)
        if not positions.size:
            return b""
        output = np.interp(positions, np.arange(len(self.buffer)), self.buffer)
        next_position = positions[-1] + self.rate / 8000
        consumed = min(int(next_position), len(self.buffer) - 1)
        self.buffer = self.buffer[consumed:]
        self.position = next_position - consumed
        return np.clip(np.rint(output * 32767), -32768, 32767).astype("<i2").tobytes()


class AudioTalkController(QObject):
    state_changed = pyqtSignal(bool, str)
    audio_level_updated = pyqtSignal(float)
    error_occurred = pyqtSignal(str)
    _connected = pyqtSignal(object, int)
    _failed = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.gain = 1.2
        self.input_device_id = ""
        self.is_broadcasting = False
        self.is_connecting = False
        self._generation = 0
        self._stop_event = threading.Event()
        self._audio_source = self._io_device = None
        self._pcm_buffer = bytearray()
        self._queue = queue.Queue(maxsize=10)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="Intercom")
        self._future = None
        self._connected.connect(self._begin_capture)
        self._failed.connect(self._handle_failure)

    def start_broadcast(self, camera_ip, username="admin", password="", rtsp_port=554,
                        stream_path="/live/ch00_0", stream_url=""):
        if self.is_broadcasting or self.is_connecting:
            return
        self._generation += 1
        generation = self._generation
        self._stop_event = threading.Event()
        self._queue = queue.Queue(maxsize=10)
        self._pcm_buffer.clear()
        self.is_connecting = True
        self.state_changed.emit(False, "Connecting to camera speaker…")
        url = stream_url or build_rtsp_url("", "", camera_ip, rtsp_port, stream_path)
        self._future = self._executor.submit(self._network_loop, url, username, password,
                                             self._stop_event, self._queue, generation)

    def stop_broadcast(self):
        self._generation += 1
        self._stop_event.set()
        if self._future:
            self._future.cancel()
        self.is_connecting = self.is_broadcasting = False
        source, self._audio_source = self._audio_source, None
        self._io_device = None
        if source:
            source.stop()
            source.deleteLater()
        self._pcm_buffer.clear()
        self.audio_level_updated.emit(0.0)
        self.state_changed.emit(False, "Intercom idle")

    def shutdown(self):
        self.stop_broadcast()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def set_gain(self, gain):
        self.gain = max(.5, min(3.5, float(gain)))

    def set_input_device(self, device_id):
        self.stop_broadcast()
        self.input_device_id = device_id or ""

    def _input_device(self):
        for device in QMediaDevices.audioInputs():
            if bytes(device.id()).hex() == self.input_device_id:
                return device
        return QAudioDevice() if self.input_device_id else QMediaDevices.defaultAudioInput()

    def get_default_device_name(self):
        device = self._input_device()
        return device.description() if not device.isNull() else "No microphone available"

    def _network_loop(self, url, username, password, stop, outgoing, generation):
        connection = RTSPBackchannel(url, username, password, stop)
        try:
            connection.connect()
            if stop.is_set():
                return
            self._connected.emit(connection, generation)
            sequence, timestamp, ssrc = 100, 1000, int.from_bytes(__import__("os").urandom(4), "big")
            last_keepalive = time.monotonic()
            while not stop.is_set():
                try:
                    pcm, gain = outgoing.get(timeout=.05)
                except queue.Empty:
                    pcm = None
                if pcm is not None:
                    payload = encode_g711(pcm, connection.codec, gain)
                    packet = struct.pack("!BBHII", 0x80, connection.payload, sequence & 65535, timestamp & 0xFFFFFFFF, ssrc) + payload
                    connection.sock.sendall(struct.pack("!BBH", 0x24, connection.channel, len(packet)) + packet)
                    sequence += 1
                    timestamp += 160
                if time.monotonic() - last_keepalive >= 20:
                    connection.request("OPTIONS")
                    last_keepalive = time.monotonic()
        except Exception as error:
            if not stop.is_set():
                message = str(error) if isinstance(error, AudioProtocolError) else "Camera audio connection failed or was interrupted."
                try:
                    self._failed.emit(message, generation)
                except RuntimeError:
                    pass
        finally:
            connection.close()

    @pyqtSlot(object, int)
    def _begin_capture(self, connection, generation):
        if generation != self._generation or self._stop_event.is_set():
            return
        try:
            device = self._input_device()
            if device.isNull():
                raise ValueError("No microphone is available. Select an input device in Windows or the intercom panel.")
            fmt = QAudioFormat()
            fmt.setSampleRate(8000)
            fmt.setChannelCount(1)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            if not device.isFormatSupported(fmt):
                fmt = device.preferredFormat()
            self._converter = AudioConverter(fmt.sampleRate(), fmt.channelCount(), fmt.sampleFormat().name)
            self._audio_source = QAudioSource(device, fmt, self)
            self._audio_source.setBufferSize(max(fmt.bytesPerFrame() * fmt.sampleRate() // 10, 320))
            self._audio_source.stateChanged.connect(self._capture_state_changed)
            self._io_device = self._audio_source.start()
            if self._io_device is None or self._audio_source.error().value != 0:
                raise ValueError("Microphone could not start. Check Windows microphone permission and device availability.")
            self._io_device.readyRead.connect(self._on_mic_ready_read)
            self.is_connecting = False
            self.is_broadcasting = True
            self.state_changed.emit(True, f"Broadcasting via {connection.codec}: {device.description()}")
        except Exception as error:
            self._handle_failure(str(error), generation)

    def _capture_state_changed(self, state):
        if self.is_broadcasting and self._audio_source and self._audio_source.error().value != 0:
            self._handle_failure("Microphone stopped. Check the selected device and Windows audio permissions.", self._generation)

    def _on_mic_ready_read(self):
        if not self.is_broadcasting or self._io_device is None:
            return
        try:
            pcm = self._converter.convert(bytes(self._io_device.readAll()))
            self.audio_level_updated.emit(compute_audio_level(pcm))
            self._pcm_buffer.extend(pcm)
            while len(self._pcm_buffer) >= 320:
                chunk = bytes(self._pcm_buffer[:320])
                del self._pcm_buffer[:320]
                try:
                    self._queue.put_nowait((chunk, self.gain))
                except queue.Full:
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._queue.put_nowait((chunk, self.gain))
        except Exception:
            self._handle_failure("Microphone audio could not be converted.", self._generation)

    @pyqtSlot(str, int)
    def _handle_failure(self, message, generation):
        if generation != self._generation:
            return
        self.stop_broadcast()
        self.error_occurred.emit(message)
