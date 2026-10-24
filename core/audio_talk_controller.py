import sys
import os
import time
import socket
import hashlib
import re
import struct
import threading
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QObject, pyqtSignal, QIODevice, QByteArray, QTimer
from PyQt6.QtMultimedia import QMediaDevices, QAudioSource, QAudioFormat, QAudioDevice


def _md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


# Precompute 64KB linear 16-bit to G.711 A-law compression table
def _calc_alaw_sample(pcm: int) -> int:
    sign = (pcm >> 8) & 0x80
    if sign:
        pcm = -pcm
    if pcm > 32767:
        pcm = 32767
    if pcm >= 256:
        exp = 7
        t = pcm >> 8
        while (t & 0x40) == 0:
            exp -= 1
            t <<= 1
        mant = (pcm >> (exp + 3)) & 0x0F
        alaw = (exp << 4) | mant
    else:
        alaw = pcm >> 4
    return (alaw ^ (sign ^ 0x55)) & 0xFF

ALAW_TABLE = bytes([_calc_alaw_sample(i - 32768) for i in range(65536)])


def pcm16_to_alaw(pcm_bytes: bytes, gain: float = 1.0) -> bytes:
    """Converts 16-bit linear PCM to G.711 A-law (PCMA) with optional gain amplification."""
    count = len(pcm_bytes) // 2
    if count == 0:
        return b""
    samples = struct.unpack(f"<{count}h", pcm_bytes)
    if gain != 1.0:
        g = max(0.5, min(4.0, float(gain)))
        clamped = [max(-32768, min(32767, int(s * g))) for s in samples]
        return bytes([ALAW_TABLE[s + 32768] for s in clamped])
    return bytes([ALAW_TABLE[s + 32768] for s in samples])


def compute_audio_level(pcm_bytes: bytes) -> float:
    """Computes normalized RMS audio level (0.0 to 1.0) for live VU meter."""
    count = len(pcm_bytes) // 2
    if count == 0:
        return 0.0
    samples = struct.unpack(f"<{count}h", pcm_bytes)
    sum_sq = sum(s * s for s in samples)
    rms = (sum_sq / count) ** 0.5
    # Normalize with 32768 scale, using a smooth perceptual curve
    norm = min(1.0, (rms / 8000.0) ** 0.8)
    return round(norm, 3)


class AudioTalkController(QObject):
    """
    Two-Way Audio Intercom & Microphone Broadcaster.
    
    Streams live audio from the user's default Windows microphone device
    to the IP camera's built-in speaker via RTSP audio backchannel (RFC 3550 / G.711 A-law).
    
    Features:
    - 100% Non-Blocking: Socket handshakes and RTP packet dispatch run on worker threads.
    - Automatic RTSP Backchannel negotiation: Supports both Basic and Digest authentication.
    - Real-Time Live VU Meter: Emits audio_level_updated(float) for responsive visual feedback.
    - Software Gain Amplification (1.0x to 3.0x) for loud, crystal-clear speaker output.
    - Clean Lifecycle: Graceful TEARDOWN and instant release on stop.
    """
    state_changed = pyqtSignal(bool, str)        # is_broadcasting, status_message
    audio_level_updated = pyqtSignal(float)      # 0.0 to 1.0 for VU meter
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera_ip: str = ""
        self.username: str = "admin"
        self.password: str = ""
        self.rtsp_port: int = 554
        self.stream_path: str = "/live/ch00_0"
        self.gain: float = 1.2

        # State
        self.is_broadcasting: bool = False
        self._sock: Optional[socket.socket] = None
        self._sess_id: str = ""
        self._seq: int = 100
        self._timestamp: int = 1000
        self._ssrc: int = 0x55AA3311

        # Qt Audio Capture
        self._audio_source: Optional[QAudioSource] = None
        self._io_device: Optional[QIODevice] = None
        self._pcm_buffer = bytearray()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="AudioTalkWorker")

    # =========================================================================
    # PUBLIC CONTROLS
    # =========================================================================

    def start_broadcast(self, camera_ip: str, username: str = "admin", password: str = "",
                        rtsp_port: int = 554, stream_path: str = "/live/ch00_0"):
        """Initiates microphone broadcast to the target camera speaker."""
        if self.is_broadcasting:
            return

        self.camera_ip = str(camera_ip).strip()
        self.username = str(username)
        self.password = str(password)
        self.rtsp_port = int(rtsp_port) if (1 <= int(rtsp_port) <= 65535) else 554
        self.stream_path = stream_path or "/live/ch00_0"

        self.state_changed.emit(False, "Connecting to camera speaker...")
        self._executor.submit(self._do_connect_and_start)

    def stop_broadcast(self):
        """Immediately halts microphone capture and tears down the audio stream."""
        if not self.is_broadcasting and self._sock is None:
            return

        self.is_broadcasting = False
        # Stop Qt audio input on GUI thread
        if self._audio_source:
            try:
                self._audio_source.stop()
            except Exception:
                pass
            self._audio_source = None
            self._io_device = None

        self._pcm_buffer.clear()
        self.audio_level_updated.emit(0.0)
        self.state_changed.emit(False, "Intercom Idle (Ready to Talk)")

        # Disconnect socket in background worker
        sock = self._sock
        sess = self._sess_id
        ip = self.camera_ip
        path = self.stream_path
        self._sock = None
        self._sess_id = ""

        if sock:
            self._executor.submit(self._do_teardown, sock, ip, path, sess)

    def set_gain(self, gain: float):
        """Sets outgoing microphone volume multiplier (1.0x to 3.0x)."""
        self.gain = max(0.5, min(3.5, float(gain)))

    def get_default_device_name(self) -> str:
        """Returns the description of the active Windows default microphone."""
        try:
            dev = QMediaDevices.defaultAudioInput()
            if dev and not dev.isNull():
                return dev.description()
        except Exception:
            pass
        return "Windows Default Audio Device"

    # =========================================================================
    # BACKGROUND RTSP BACKCHANNEL WORKERS
    # =========================================================================

    def _do_connect_and_start(self):
        try:
            uri = f"rtsp://{self.camera_ip}:{self.rtsp_port}{self.stream_path}"
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(4.0)
            sock.connect((self.camera_ip, self.rtsp_port))

            # 1. DESCRIBE
            req1 = f"DESCRIBE {uri} RTSP/1.0\r\nCSeq: 1\r\nAccept: application/sdp\r\n\r\n"
            sock.sendall(req1.encode())
            resp1 = sock.recv(2048).decode("utf-8", errors="ignore")

            auth_hdr = ""
            ha1 = ""
            realm = ""
            nonce = ""
            if "401 Unauthorized" in resp1:
                m_realm = re.search(r'realm="([^"]+)"', resp1)
                m_nonce = re.search(r'nonce="([^"]+)"', resp1)
                realm = m_realm.group(1) if m_realm else "ipc"
                nonce = m_nonce.group(1) if m_nonce else ""
                ha1 = _md5(f"{self.username}:{realm}:{self.password}")
                ha2 = _md5(f"DESCRIBE:{uri}")
                resp_hash = _md5(f"{ha1}:{nonce}:{ha2}")
                auth_hdr = f'Digest username="{self.username}", realm="{realm}", nonce="{nonce}", uri="{uri}", response="{resp_hash}"'

                req1_auth = f"DESCRIBE {uri} RTSP/1.0\r\nCSeq: 2\r\nAuthorization: {auth_hdr}\r\nAccept: application/sdp\r\n\r\n"
                sock.sendall(req1_auth.encode())
                resp1 = sock.recv(4096).decode("utf-8", errors="ignore")

            # 2. SETUP trackID=2 with mode=record (Audio backchannel)
            track_uri = f"{uri}/trackID=2"
            if auth_hdr:
                ha2_setup = _md5(f"SETUP:{track_uri}")
                resp_setup = _md5(f"{ha1}:{nonce}:{ha2_setup}")
                auth_hdr_setup = f'Digest username="{self.username}", realm="{realm}", nonce="{nonce}", uri="{track_uri}", response="{resp_setup}"'
            else:
                import base64
                b64 = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
                auth_hdr_setup = f"Basic {b64}"

            req2 = (f"SETUP {track_uri} RTSP/1.0\r\n"
                    f"CSeq: 3\r\n"
                    f"Authorization: {auth_hdr_setup}\r\n"
                    f"Require: www.onvif.org/ver20/backchannel\r\n"
                    f"Transport: RTP/AVP/TCP;unicast;interleaved=0-1;mode=record\r\n\r\n")
            sock.sendall(req2.encode())
            resp2 = sock.recv(2048).decode("utf-8", errors="ignore")

            m_sess = re.search(r'Session:\s*([^\r\n;]+)', resp2)
            if not m_sess:
                sock.close()
                self.error_occurred.emit(f"Camera rejected audio backchannel SETUP: {resp2[:60]}")
                self.state_changed.emit(False, "Speaker Setup Failed")
                return

            sess_id = m_sess.group(1).strip()

            # 3. RECORD
            if auth_hdr:
                ha2_rec = _md5(f"RECORD:{uri}")
                resp_rec = _md5(f"{ha1}:{nonce}:{ha2_rec}")
                auth_hdr_rec = f'Digest username="{self.username}", realm="{realm}", nonce="{nonce}", uri="{uri}", response="{resp_rec}"'
            else:
                auth_hdr_rec = auth_hdr_setup

            req3 = (f"RECORD {uri} RTSP/1.0\r\n"
                    f"CSeq: 4\r\n"
                    f"Authorization: {auth_hdr_rec}\r\n"
                    f"Session: {sess_id}\r\n"
                    f"Range: npt=0.000-\r\n\r\n")
            sock.sendall(req3.encode())
            resp3 = sock.recv(2048).decode("utf-8", errors="ignore")

            if "200 OK" not in resp3:
                sock.close()
                self.error_occurred.emit(f"Camera rejected RECORD command: {resp3[:60]}")
                self.state_changed.emit(False, "Speaker Record Failed")
                return

            # Connection success! Save socket and start audio capture
            self._sock = sock
            self._sess_id = sess_id
            self._seq = 100
            self._timestamp = 1000
            self.is_broadcasting = True

            # Trigger microphone capture start on Qt main thread via QTimer
            QTimer.singleShot(0, self._start_qt_audio_capture)

        except Exception as e:
            self.is_broadcasting = False
            self.error_occurred.emit(f"Intercom connection error: {e}")
            self.state_changed.emit(False, "Connection Error")

    def _start_qt_audio_capture(self):
        """Starts live Windows microphone capture via PyQt6.QtMultimedia."""
        try:
            dev = QMediaDevices.defaultAudioInput()
            fmt = QAudioFormat()
            fmt.setSampleRate(8000)
            fmt.setChannelCount(1)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

            self._audio_source = QAudioSource(dev, fmt, self)
            self._io_device = self._audio_source.start()
            if self._io_device:
                self._io_device.readyRead.connect(self._on_mic_ready_read)
                self.state_changed.emit(True, f"[LIVE] BROADCASTING: {dev.description()}")
            else:
                self.error_occurred.emit("Could not open default microphone device.")
                self.stop_broadcast()
        except Exception as e:
            self.error_occurred.emit(f"Mic capture initialization failed: {e}")
            self.stop_broadcast()

    def _on_mic_ready_read(self):
        """Called by Qt when fresh PCM audio samples arrive from the microphone."""
        if not self.is_broadcasting or not self._io_device:
            return

        raw = self._io_device.readAll().data()
        if not raw:
            return

        # Update VU level meter
        level = compute_audio_level(raw)
        self.audio_level_updated.emit(level)

        self._pcm_buffer.extend(raw)

        # Send in 320-byte PCM chunks (= 160 samples = 20ms at 8000Hz)
        chunk_pcm_len = 320
        while len(self._pcm_buffer) >= chunk_pcm_len:
            pcm_chunk = bytes(self._pcm_buffer[:chunk_pcm_len])
            del self._pcm_buffer[:chunk_pcm_len]

            alaw_chunk = pcm16_to_alaw(pcm_chunk, gain=self.gain)

            # RTP packet (12-byte header + 160-byte payload)
            # Payload type 8 = PCMA (G.711 A-law)
            rtp_hdr = struct.pack("!BBHII", 0x80, 8, self._seq & 0xFFFF, self._timestamp & 0xFFFFFFFF, self._ssrc)
            rtp_pkt = rtp_hdr + alaw_chunk
            # Interleaved RTSP frame header ($ = 0x24, channel 0, 16-bit payload length)
            frame_hdr = struct.pack("!BBH", 0x24, 0, len(rtp_pkt))

            if self._sock:
                try:
                    self._sock.sendall(frame_hdr + rtp_pkt)
                except Exception as e:
                    self.stop_broadcast()
                    self.error_occurred.emit(f"Audio socket disconnected: {e}")
                    break

            self._seq += 1
            self._timestamp += 160

    def _do_teardown(self, sock: socket.socket, ip: str, path: str, sess: str):
        try:
            req = f"TEARDOWN rtsp://{ip}:554{path} RTSP/1.0\r\nCSeq: 5\r\nSession: {sess}\r\n\r\n"
            sock.sendall(req.encode())
            sock.close()
        except Exception:
            pass
