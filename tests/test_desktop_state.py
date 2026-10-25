import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
from pathlib import Path
from contextlib import ExitStack
import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from core.device_manager import DeviceManager
from ui.main_window import MainWindow
from ui.components.settings_dialog import SettingsDialog


class DesktopStateTests(unittest.TestCase):
    def test_retiring_camera_does_not_wait_on_gui_thread(self):
        import threading
        import time
        from PyQt6.QtCore import QThread
        done = threading.Event()
        calls = []
        class Worker(QThread):
            def run(self):
                done.wait(3)
            def stop(self, wait=True):
                calls.append(wait)
        worker = Worker()
        worker.start()
        try:
            started = time.monotonic()
            self.window._retire_worker(worker)
            self.assertLess(time.monotonic() - started, .1)
            self.assertEqual(calls, [False])
            self.assertIn(worker, self.window._retiring_workers)
            done.set()
            self.assertTrue(worker.wait(1000))
            self.app.processEvents()
            self.assertNotIn(worker, self.window._retiring_workers)
        finally:
            done.set()
            worker.wait(1000)

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.old_cwd = os.getcwd()
        self.temp = tempfile.TemporaryDirectory()
        os.chdir(self.temp.name)
        self.manager = DeviceManager(str(Path(self.temp.name) / "config.json"))
        self.manager.config["app_settings"].update(
            has_completed_onboarding=True, auto_clean_on_startup=False,
            default_layout="2x2", session_slot_assignments={"0": "s1", "1": "", "7": "s2"})
        self.manager.config["cameras"] = [{"id": "c1", "ip": "127.0.0.1", "password": "fixture", "streams": [
            {"id": "s1", "name": "One"}, {"id": "s2", "name": "Two"}]}]
        self.manager.save_config()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch("ui.main_window.DeviceManager", return_value=self.manager))
        for target in ("WebStreamingServer.start", "SignalMonitor.start", "enable_windows_sleep_prevention"):
            self.stack.enter_context(patch("ui.main_window." + target))
        self.stack.enter_context(patch("ui.components.ptz_pad.PTZController"))
        for target in ("apply_performance_profile", "_check_startup_performance_mode", "_setup_system_tray"):
            self.stack.enter_context(patch.object(MainWindow, target))
        self.window = MainWindow()

    def tearDown(self):
        self.window.cpu_monitor_timer.stop()
        self.window.hide()
        self.window.deleteLater()
        self.app.processEvents()
        self.stack.close()
        os.chdir(self.old_cwd)
        self.temp.cleanup()

    def test_initial_ui_does_not_erase_saved_assignments(self):
        settings = DeviceManager(self.manager.config_file).config["app_settings"]
        self.assertEqual({"0": "s1", "1": "", "7": "s2"}, settings["session_slot_assignments"])

    def test_restore_keeps_empty_and_hidden_tiles(self):
        def attach(index, stream):
            self.window.video_tiles[index].stream_id = stream["id"]
        with patch.object(self.window, "start_stream_on_tile", side_effect=attach):
            self.window.activate_startup_view()
        self.assertEqual("s1", self.window.video_tiles[0].stream_id)
        self.assertFalse(self.window.video_tiles[1].stream_id)
        self.assertEqual("s2", self.window.video_tiles[7].stream_id)
        self.assertEqual("s2", self.manager.config["app_settings"]["session_slot_assignments"]["7"])

    def test_arming_preserves_user_preferences(self):
        self.window.app_settings.update(notify_animal=False, auto_record_on_motion=False, ai_detection_enabled=False)
        self.window.toggle_master_alerts(force_state=False)
        self.window.toggle_master_alerts(force_state=True)
        self.assertFalse(self.window.app_settings["notify_animal"])
        self.assertFalse(self.window.app_settings["auto_record_on_motion"])
        self.assertFalse(self.window.app_settings["ai_detection_enabled"])

    def test_settings_changes_are_dirty_and_saved(self):
        dialog = SettingsDialog(current_settings=self.window.app_settings, cameras=[])
        self.assertFalse(dialog.has_unsaved_changes())
        saved = []
        dialog.settings_saved.connect(saved.append)
        dialog.spin_ai_confirm.setValue(2.1)
        dialog.spin_motion_confirm.setValue(.7)
        self.assertTrue(dialog.has_unsaved_changes())
        dialog._commit_and_save_data()
        self.assertEqual(2.1, saved[0]["detection_confirm_sec"])
        self.assertEqual(.7, saved[0]["motion_confirm_delay"])
        dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()
