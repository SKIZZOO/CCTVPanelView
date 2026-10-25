"""Per-camera native decoder isolation with a bounded, latest-frame mailbox.

No frame queue or shared OpenCV VideoCapture state exists between cameras.
The sequence counter avoids a process lock that a hung decoder could strand.
"""
import multiprocessing as mp
from multiprocessing import shared_memory
import time


def _decode(url, sender, stop, sequence, open_ms, read_ms, attached):
    import os
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|threads;1"
    if os.name == "nt":
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    import cv2
    import numpy as np
    cv2.setNumThreads(1)
    cap = None
    memory = None
    try:
        params = [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, open_ms,
                  cv2.CAP_PROP_READ_TIMEOUT_MSEC, read_ms]
        if hasattr(cv2, "CAP_PROP_N_THREADS"):
            params += [cv2.CAP_PROP_N_THREADS, 1]
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG, params)
        if not cap.isOpened():
            return
        ok, frame = cap.read()
        if not ok or frame is None:
            return
        # Reject unreasonable allocations from malformed stream metadata.
        if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3 or frame.nbytes > 128 * 1024 * 1024:
            return
        memory = shared_memory.SharedMemory(create=True, size=frame.nbytes)
        pixels = np.ndarray(frame.shape, dtype=np.uint8, buffer=memory.buf)
        sender.send((memory.name, frame.shape, cap.get(cv2.CAP_PROP_FPS)))
        if not attached.wait(open_ms / 1000):
            return
        while not stop.is_set():
            if frame.shape != pixels.shape:
                break  # Reopen this camera if its resolution changes.
            sequence.value += 1
            np.copyto(pixels, frame)
            sequence.value += 1
            ok, frame = cap.read()
            if not ok or frame is None:
                break
    except Exception:
        # URLs can contain passwords; never send native exception text to the UI.
        pass
    finally:
        if cap is not None:
            cap.release()
        sender.close()
        if memory is not None:
            memory.close()
            memory.unlink()


class IsolatedCapture:
    def __init__(self, open_timeout=6.0, read_timeout=4.0, *, _target=_decode):
        self.open_timeout = open_timeout
        self.read_timeout = read_timeout
        self._target = _target
        context = mp.get_context("spawn")
        self._stop = context.Event()
        self._attached = context.Event()
        self._sequence = context.Value("Q", 0, lock=False)
        self._receiver, self._sender = context.Pipe(duplex=False)
        self._process = None
        self._memory = None
        self._shape = None
        self._fps = 0.0
        self._last_sequence = 0
        self._grabbed = False

    def open(self, url):
        if self._stop.is_set():
            return False
        context = mp.get_context("spawn")
        self._process = context.Process(target=self._target, args=(
            url, self._sender, self._stop, self._sequence,
            int(self.open_timeout * 1000), int(self.read_timeout * 1000), self._attached), daemon=True)
        self._process.start()
        self._sender.close()
        deadline = time.monotonic() + self.open_timeout
        while not self._stop.is_set() and time.monotonic() < deadline:
            if self._receiver.poll(0.02):
                try:
                    name, shape, fps = self._receiver.recv()
                    self._memory = shared_memory.SharedMemory(name=name)
                    self._shape, self._fps = shape, fps
                    self._attached.set()
                    return True
                except (EOFError, OSError, ValueError):
                    break
            if not self._process.is_alive():
                break
        return False

    def isOpened(self):
        return self._memory is not None and not self._stop.is_set()

    def get(self, prop):
        import cv2
        return {cv2.CAP_PROP_FRAME_WIDTH: self._shape[1] if self._shape else 0,
                cv2.CAP_PROP_FRAME_HEIGHT: self._shape[0] if self._shape else 0,
                cv2.CAP_PROP_FPS: self._fps}.get(prop, 0)

    def grab(self):
        self._grabbed = False
        deadline = time.monotonic() + self.read_timeout
        while self.isOpened() and time.monotonic() < deadline:
            sequence = self._sequence.value
            if sequence and not sequence % 2 and sequence != self._last_sequence:
                self._last_sequence = sequence
                self._grabbed = True
                return True
            if not self._process.is_alive():
                break
            self._stop.wait(0.005)
        return False

    def retrieve(self):
        import numpy as np
        if not self._grabbed or not self.isOpened():
            return False, None
        pixels = np.ndarray(self._shape, dtype=np.uint8, buffer=self._memory.buf)
        deadline = time.monotonic() + .05
        while not self._stop.is_set() and time.monotonic() < deadline:
            before = self._sequence.value
            if before % 2:
                self._stop.wait(.001)
                continue
            frame = pixels.copy()
            if before == self._sequence.value:
                self._last_sequence = before
                self._grabbed = False
                return True, frame
            self._stop.wait(.001)
        return False, None

    def read(self):
        return self.retrieve() if self.grab() else (False, None)

    def interrupt(self):
        """Safe for GUI callers: wake polling without waiting for a decoder."""
        self._stop.set()

    def release(self):
        self.interrupt()
        if self._process is not None:
            if self._process.pid is not None:
                self._process.join(0.15)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(0.5)
            if self._process.is_alive():
                self._process.kill()
                self._process.join(0.5)
            if not self._process.is_alive():
                self._process.close()
            self._process = None
        if self._memory is not None:
            self._memory.close()
            self._memory = None
        self._receiver.close()
        self._sender.close()
