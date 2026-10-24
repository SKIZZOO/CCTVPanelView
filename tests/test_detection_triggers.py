import os
import tempfile
import unittest
from unittest.mock import Mock, patch
import cv2
import numpy as np
from core.motion_detector import MotionDetector
from core.ai_detector import AIDetection, TemporalDetectionTracker
from core.settings import normalize_settings


class MotionTriggerTests(unittest.TestCase):
    def setUp(self):
        self.frame = np.zeros((360, 640, 3), np.uint8)
        self.mask = np.zeros((360, 640), np.uint8)
        self.mask[100:160, 100:150] = 255
        self.detector = MotionDetector(min_area=200, downscale_width=640)
        self.detector._frame_shape = (360, 640)
        self.detector._warmup_started = 0
        self.detector.warmup_sec = 0
        self.detector.bg_subtractor = Mock()
        self.detector.bg_subtractor.apply.side_effect = lambda _: self.mask.copy()

    def process(self, now):
        with patch("core.motion_detector.time.monotonic", return_value=now):
            return self.detector.process_frame(self.frame, draw_boxes=False)[1]

    def test_requires_continuous_motion_and_rejects_light_shift(self):
        self.assertFalse(self.process(100))
        self.assertFalse(self.process(100.5))
        self.mask[:] = 255
        self.assertFalse(self.process(101))
        self.mask[:] = 0
        self.mask[100:160, 100:150] = 255
        self.assertFalse(self.process(101.3))
        self.assertTrue(self.process(102.6))

    def test_high_frame_rate_does_not_suppress_before_confirmation(self):
        values = [self.process(100 + i / 60) for i in range(100)]
        self.assertTrue(any(values))

    def test_background_warmup_never_alerts(self):
        self.detector.warmup_sec = 1.5
        self.detector._warmup_started = None
        self.assertFalse(self.process(100))
        self.assertFalse(self.process(101))
        self.assertIsNone(self.detector._motion_candidate_start)

    def test_unrelated_setting_change_preserves_background(self):
        background = self.detector.bg_subtractor
        self.detector.update_settings(5, 700, motion_cooldown=5)
        self.assertIs(background, self.detector.bg_subtractor)

    def test_exclusion_zone_prevents_alarm(self):
        self.detector.set_exclusion_zones([[0, 0, 1, 1]])
        self.assertFalse(self.process(100))
        self.assertFalse(self.process(103))


class AITriggerTests(unittest.TestCase):
    @staticmethod
    def detection(x=100):
        return AIDetection("person", "person", .9, (x, 100, 60, 100))

    def test_movement_does_not_bypass_confirmation(self):
        tracker = TemporalDetectionTracker(confirm_delay=1.2)
        self.assertEqual([], tracker.update([self.detection()], now=100))
        self.assertEqual([], tracker.update([self.detection(180)], now=100.1))
        self.assertTrue(tracker.update([self.detection(180)], now=101.3))

    def test_detection_gap_restarts_unconfirmed_candidate(self):
        tracker = TemporalDetectionTracker(confirm_delay=1.2, persistence_timeout=1)
        tracker.update([self.detection()], now=100)
        self.assertEqual([], tracker.update([self.detection()], now=102))
        self.assertEqual([], tracker.update([self.detection()], now=102.5))
        self.assertTrue(tracker.update([self.detection()], now=103.3))

    def test_moving_confirmed_target_does_not_reset_alert_flag(self):
        tracker = TemporalDetectionTracker(confirm_delay=.2)
        tracker.update([self.detection()], now=100)
        tracker.update([self.detection()], now=100.3)
        tracker._tracks[1].has_alerted = True
        result = tracker.update([self.detection(190)], now=100.4)
        self.assertTrue(result[0].has_alerted)

    def test_invalid_numeric_settings_are_finite_and_bounded(self):
        result = normalize_settings({"ai_conf_threshold": "nan", "motion_confirm_delay": -9,
                                     "motion_min_area": "bad", "default_layout": "invalid"})
        self.assertEqual(.45, result["ai_conf_threshold"])
        self.assertEqual(0, result["motion_confirm_delay"])
        self.assertEqual(2800, result["motion_min_area"])
        self.assertEqual("2x2", result["default_layout"])

    def test_live_worker_applies_independent_confirmation_and_cooldown(self):
        from core.camera_stream import CameraStreamWorker
        with tempfile.TemporaryDirectory() as temp:
            old = os.getcwd()
            os.chdir(temp)
            try:
                with patch("core.camera_stream.AIDetector"):
                    worker = CameraStreamWorker("test", "Test", "")
                worker.apply_camera_settings({"motion_confirm_delay": .6, "detection_confirm_sec": 1.7,
                                              "motion_hold_sec": 4, "motion_cooldown_sec": 9})
                self.assertEqual(.6, worker.detector.confirm_delay)
                self.assertEqual(1.7, worker.ai_tracker.confirm_delay)
                self.assertEqual(9, worker.motion_alarm_cooldown)
                self.assertEqual(4, worker.detector.motion_cooldown)
                worker.apply_camera_settings({"master_alerts_enabled": False})
                self.assertFalse(worker.motion_detection_enabled)
                self.assertFalse(worker.ai_detection_enabled)
                worker._ai_executor.shutdown(wait=True)
            finally:
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()
