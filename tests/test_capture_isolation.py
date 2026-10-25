import threading
import time
import unittest
import tempfile
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from multiprocessing import shared_memory
from unittest.mock import patch

import numpy as np
from PyQt6.QtCore import QCoreApplication
from core.capture_process import IsolatedCapture
from core.signal_monitor import SignalMonitor


def stalled_decoder(url, sender, stop, sequence, open_ms, read_ms, attached):
    # Model native code that ignores timeouts and shutdown requests.
    time.sleep(60)


def healthy_decoder(url, sender, stop, sequence, open_ms, read_ms, attached):
    memory = shared_memory.SharedMemory(create=True, size=48 * 64 * 3)
    pixels = np.ndarray((48, 64, 3), np.uint8, buffer=memory.buf)
    try:
        sender.send((memory.name, pixels.shape, 30.0))
        attached.wait(5)
        while not stop.is_set():
            sequence.value += 1
            pixels.fill((sequence.value // 2) % 255)
            sequence.value += 1
            stop.wait(1 / 30)
    finally:
        memory.close()
        memory.unlink()
        sender.close()


def delayed_decoder(url, sender, stop, sequence, open_ms, read_ms, attached):
    sender.send({"stage": "opening"})
    time.sleep(1.5)
    sender.send({"stage": "waiting_for_frame"})
    time.sleep(1.5)
    healthy_decoder(url, sender, stop, sequence, open_ms, read_ms, attached)


class CaptureIsolationTests(unittest.TestCase):
    def test_open_and_first_keyframe_have_separate_deadlines(self):
        capture = IsolatedCapture(open_timeout=2.5, read_timeout=2.5, _target=delayed_decoder)
        try:
            self.assertTrue(capture.open("delayed-keyframe"), capture.error_code)
            self.assertTrue(capture.read()[0])
        finally:
            capture.release()

    def test_cancellation_callback_interrupts_connection_test(self):
        cancelled = threading.Event()
        capture = IsolatedCapture(open_timeout=30, cancelled=cancelled.is_set, _target=stalled_decoder)
        attempt = threading.Thread(target=capture.open, args=("stuck",))
        try:
            attempt.start()
            time.sleep(.1)
            cancelled.set()
            attempt.join(.4)
            self.assertFalse(attempt.is_alive())
        finally:
            capture.release()
    def test_failed_process_start_can_be_cleaned_up(self):
        capture = IsolatedCapture()
        with patch("multiprocessing.process.BaseProcess.start", side_effect=OSError("fixture process limit")):
            with self.assertRaises(OSError):
                capture.open("unused")
        capture.release()
        capture.release()

    def test_live_mjpeg_keeps_playing_while_another_endpoint_hangs(self):
        import cv2
        stopping = threading.Event()
        jpeg = cv2.imencode(".jpg", np.full((96, 128, 3), 70, np.uint8))[1].tobytes()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                if self.path == "/hang":
                    stopping.wait(10)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()
                try:
                    while not stopping.is_set():
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " +
                                         str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
                        self.wfile.flush()
                        stopping.wait(1 / 25)
                except OSError:
                    pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        base = f"http://127.0.0.1:{server.server_port}"
        healthy = IsolatedCapture()
        broken = IsolatedCapture(open_timeout=2)
        attempt = None
        try:
            self.assertTrue(healthy.open(base + "/live"))
            result = []
            attempt = threading.Thread(target=lambda: result.append(broken.open(base + "/hang")))
            attempt.start()
            arrivals = []
            end = time.monotonic() + 3.5
            while time.monotonic() < end:
                self.assertTrue(healthy.read()[0])
                arrivals.append(time.monotonic())
            attempt.join(1)
            self.assertEqual(result, [False])
            self.assertGreater(len(arrivals), 30)
            self.assertLess(max(b - a for a, b in zip(arrivals, arrivals[1:])), .35)
        finally:
            broken.interrupt()
            if attempt:
                attempt.join(1)
            broken.release()
            healthy.release()
            stopping.set()
            server.shutdown()
            server.server_close()

    def test_real_decoder_reads_local_video_in_spawned_process(self):
        import cv2
        with tempfile.TemporaryDirectory() as temp:
            video = str(Path(temp) / "stream.avi")
            writer = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*"MJPG"), 15, (64, 48))
            self.assertTrue(writer.isOpened())
            for value in range(100):
                writer.write(np.full((48, 64, 3), value, np.uint8))
            writer.release()
            capture = IsolatedCapture()
            try:
                self.assertTrue(capture.open(video))
                ok, frame = capture.read()
                self.assertTrue(ok)
                self.assertEqual(frame.shape, (48, 64, 3))
            finally:
                capture.release()

    def test_stuck_open_and_termination_do_not_pause_healthy_frames(self):
        healthy = IsolatedCapture(open_timeout=5, _target=healthy_decoder)
        broken = IsolatedCapture(open_timeout=1.2, _target=stalled_decoder)
        try:
            self.assertTrue(healthy.open("synthetic"))
            result = []
            attempt = threading.Thread(target=lambda: result.append(broken.open("stuck")))
            attempt.start()
            arrivals = []
            end = time.monotonic() + 1.6
            while time.monotonic() < end:
                ok, frame = healthy.read()
                self.assertTrue(ok)
                self.assertTrue(np.all(frame == frame[0, 0, 0]), "Torn frame")
                arrivals.append(time.monotonic())
            attempt.join(1)
            self.assertEqual(result, [False])
            started = time.monotonic()
            broken.release()
            self.assertLess(time.monotonic() - started, 1.3)
            self.assertGreater(len(arrivals), 25)
            self.assertLess(max(b - a for a, b in zip(arrivals, arrivals[1:])), .3)
            self.assertTrue(healthy.read()[0])
        finally:
            healthy.release()
            broken.release()

    def test_interrupt_cancels_open_without_waiting_for_native_code(self):
        capture = IsolatedCapture(open_timeout=30, _target=stalled_decoder)
        attempt = threading.Thread(target=capture.open, args=("stuck",))
        try:
            attempt.start()
            time.sleep(.15)
            started = time.monotonic()
            capture.interrupt()
            attempt.join(.3)
            self.assertFalse(attempt.is_alive())
            self.assertLess(time.monotonic() - started, .3)
        finally:
            capture.release()

    def test_network_probe_results_are_independent_and_not_duplicated(self):
        app = QCoreApplication.instance() or QCoreApplication([])
        monitor = SignalMonitor()
        blocked = threading.Event()
        calls = []
        def probe(ip, timeout, port=554):
            calls.append(ip)
            if ip == "bad":
                blocked.wait(2)
            return {"is_online": ip != "bad", "latency_ms": 1}
        try:
            with patch.object(monitor, "_probe_single_ip", side_effect=probe):
                monitor.set_camera_ips(["bad", "good"])
                for _ in range(20):
                    monitor.probe_all_cameras()
                deadline = time.monotonic() + 1
                while "good" not in monitor.signal_cache and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.005)
                self.assertIn("good", monitor.signal_cache)
                self.assertNotIn("bad", monitor.signal_cache)
                self.assertEqual(calls.count("bad"), 1)
                self.assertEqual(calls.count("good"), 1)
        finally:
            monitor.stop()
            blocked.set()


if __name__ == "__main__":
    unittest.main()
