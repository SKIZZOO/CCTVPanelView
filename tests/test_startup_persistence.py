"""Exercise the real first-show lifecycle, including the splash delay."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from core.camera_stream import CameraStreamWorker
from core.device_manager import DeviceManager
from ui.main_window import MainWindow


class StartupPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_cwd = os.getcwd()
        os.chdir(self.temp.name)
        self.config_path = str(Path(self.temp.name) / "config.json")
        self.manager = DeviceManager(self.config_path)
        self.manager.config["app_settings"].update(
            auto_clean_on_startup=False, show_performance_prompt_on_startup=False,
            default_layout="2x2", session_slot_assignments={"0": "one", "1": "", "7": "two"})
        self.manager.config["cameras"] = [{"id": "camera", "name": "Fixture", "ip": "127.0.0.1",
            "configured": True, "streams": [
                {"id": "one", "name": "One", "url": "rtsp://127.0.0.1/one"},
                {"id": "two", "name": "Two", "url": "rtsp://127.0.0.1/two"}]}]
        self.manager.save_config()
        self.stack = ExitStack()
        self.windows = []
        self.stack.enter_context(patch("ui.main_window.DeviceManager", side_effect=lambda: DeviceManager(self.config_path)))
        for target in ("WebStreamingServer.start", "SignalMonitor.start", "enable_windows_sleep_prevention"):
            self.stack.enter_context(patch("ui.main_window." + target))
        for target in ("apply_performance_profile", "_setup_system_tray", "_update_cpu_monitor"):
            self.stack.enter_context(patch.object(MainWindow, target))
        self.stack.enter_context(patch("ui.components.ptz_pad.PTZController"))
        # Keep real tile assignment, signals and persistence; only disable network/thread startup.
        self.stack.enter_context(patch.object(CameraStreamWorker, "start"))

    def new_window(self):
        window = MainWindow()
        self.windows.append(window)
        return window

    def dispose(self, window):
        window.cpu_monitor_timer.stop()
        window.hide()
        for tile in window.video_tiles:
            tile.detach_stream()
        for worker in window.active_workers.values():
            worker._ai_executor.shutdown(wait=True)
        window.active_workers.clear()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.windows.remove(window)

    def tearDown(self):
        for window in list(self.windows):
            self.dispose(window)
        self.stack.close()
        os.chdir(self.previous_cwd)
        self.temp.cleanup()

    def test_delayed_first_show_restores_then_remembers_new_assignments_after_restart(self):
        window = self.new_window()
        # The normal splash keeps MainWindow hidden past the old 150 ms startup timer.
        QTest.qWait(350)
        self.assertEqual(DeviceManager(self.config_path).config["app_settings"]["session_slot_assignments"]["0"], "one")
        window.show()
        QTest.qWait(50)
        self.assertFalse(window._restoring_session)
        self.assertEqual(window.video_tiles[0].stream_id, "one")
        self.assertEqual(window.video_tiles[7].stream_id, "two")
        self.assertFalse(window.video_tiles[1].stream_id)
        # Real camera assignment, clear, layout change and close-to-tray paths write immediately.
        window.start_stream_on_tile(0, window.device_manager.get_stream_by_id("two"))
        window._on_tile_closed(7)
        window.set_grid_layout("1x2")
        window._minimize_to_tray(QCloseEvent())
        saved = DeviceManager(self.config_path).config["app_settings"]
        self.assertEqual(saved["session_slot_assignments"]["0"], "two")
        self.assertEqual(saved["session_slot_assignments"]["7"], "")
        self.assertEqual(saved["default_layout"], "1x2")
        self.dispose(window)
        restarted = self.new_window()
        QTest.qWait(350)
        restarted.show()
        QTest.qWait(50)
        self.assertEqual(restarted.current_layout, "1x2")
        self.assertEqual(restarted.video_tiles[0].stream_id, "two")
        self.assertFalse(restarted.video_tiles[1].stream_id)
        self.assertFalse(restarted.video_tiles[7].stream_id)

    def test_restoring_from_tray_does_not_reapply_startup_assignments(self):
        window = self.new_window()
        with patch.object(window, "activate_startup_view", wraps=window.activate_startup_view) as restore:
            window.show()
            QTest.qWait(50)
            self.assertEqual(restore.call_count, 1)
            window.hide()
            window.show()
            QTest.qWait(50)
            self.assertEqual(restore.call_count, 1)


if __name__ == "__main__":
    unittest.main()
