"""Real local encoding checks; no cameras or network services are involved."""
import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import MagicMock
import cv2
import numpy as np
from core.async_recorder import AsyncVideoRecorder
from core.alert_manager import AlertClipSession


class MediaIntegrationTests(unittest.TestCase):
    def test_recording_finalizes_a_playable_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = str(Path(temp) / "manual.mp4")
            recorder = AsyncVideoRecorder(path, fps=15, width=320, height=240)
            recorder.start()
            for index in range(30):
                frame = np.full((240, 320, 3), index * 8, np.uint8)
                recorder.write_frame(frame)
            recorder.stop(wait=True, timeout=15)
            capture = cv2.VideoCapture(path)
            self.assertTrue(capture.isOpened())
            self.assertGreater(capture.get(cv2.CAP_PROP_FRAME_COUNT), 10)
            self.assertTrue(capture.read()[0])
            capture.release()

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required for alert encoding")
    def test_alert_clip_with_compressed_prebuffer_is_playable(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "alert.mp4"
            raw = Path(temp) / "raw.mp4"
            frame = np.full((240, 320, 3), 96, np.uint8)
            jpeg = cv2.imencode(".jpg", frame)[1]
            session = AlertClipSession(MagicMock(), "test", "", {"label": "PERSON", "unique_id": "TEST"},
                                       str(raw), str(path), fps=15, max_duration_sec=3,
                                       record_dual_clips=True, trigger_frame=frame)
            session.set_prebuffer([(jpeg, time.time()) for _ in range(10)])
            for _ in range(10):
                session.push_frame(frame, frame)
            session.finish(wait=True, timeout=20)
            self.assertFalse(session.thread.is_alive())
            self.assertTrue(path.exists())
            capture = cv2.VideoCapture(str(path))
            self.assertTrue(capture.read()[0])
            capture.release()
            self.assertTrue(raw.exists())


if __name__ == "__main__":
    unittest.main()
