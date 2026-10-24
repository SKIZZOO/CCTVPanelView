import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import QTimer
import test_desktop_state as desktop
from core.camera_stream import CameraStreamWorker
from core.device_manager import DeviceManager
from ui.components.device_dialog import DeviceDialog


class CameraSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        desktop.DesktopStateTests.setUpClass()

    def setUp(self):
        self.fixture = desktop.DesktopStateTests()
        self.fixture.setUp()
        self.window = self.fixture.window
        self.manager = self.fixture.manager
        cam = self.manager.config["cameras"][0]
        cam["name"] = "Fixture"
        for stream in cam["streams"]:
            stream["url"] = "rtsp://127.0.0.1/test"
        self.window._restoring_session = False
        self.starts = patch.object(CameraStreamWorker, "start")
        self.starts.start()

    def tearDown(self):
        for worker in self.window.active_workers.values():
            worker._ai_executor.shutdown(wait=True)
        self.starts.stop()
        self.fixture.tearDown()

    def add_through_dialog(self, password):
        def fill_and_save():
            dialog = QApplication.activeModalWidget()
            self.assertIsInstance(dialog, DeviceDialog)
            dialog.txt_name.setText("Added through UI")
            dialog.txt_ip.setText("127.0.0.2")
            dialog.txt_pass.setText(password)
            dialog.btn_save.click()
        QTimer.singleShot(0, fill_and_save)
        self.window.open_add_camera_dialog()

    def test_save_button_persists_camera_and_assigns_a_real_worker(self):
        self.add_through_dialog("fixture")
        camera = self.manager.get_cameras()[-1]
        self.assertEqual("Added through UI", camera["name"])
        self.assertEqual(camera["streams"][0]["id"], self.window.video_tiles[0].stream_id)
        stored = DeviceManager(self.manager.config_file).get_cameras()[-1]
        self.assertEqual(camera["id"], stored["id"])
        self.assertIn(camera["streams"][0]["id"], self.window.active_workers)

    def test_anonymous_camera_can_be_added_and_assigned(self):
        self.add_through_dialog("")
        camera = self.manager.get_cameras()[-1]
        self.assertTrue(self.manager.is_camera_configured(camera))
        self.assertEqual(camera["streams"][0]["id"], self.window.video_tiles[0].stream_id)

    def test_startup_restore_assigns_real_workers(self):
        self.window.activate_startup_view()
        self.assertEqual("s1", self.window.video_tiles[0].stream_id)
        self.assertEqual("s2", self.window.video_tiles[7].stream_id)
        self.assertIn("s1", self.window.active_workers)
        self.assertFalse(self.window._restoring_session)

    def test_completing_setup_assigns_requested_tile_after_modal_closes(self):
        camera = self.manager.get_cameras()[0]
        camera["configured"] = False
        camera["password"] = ""
        def complete(**kwargs):
            camera["configured"] = True
            self.manager.save_config()
        with patch("ui.main_window.CameraSetupPromptDialog.exec", return_value=QDialog.DialogCode.Accepted), \
             patch.object(self.window, "open_settings_dialog", side_effect=complete):
            self.window._prompt_unconfigured_camera(camera, target_tile_idx=2)
        self.assertEqual("s1", self.window.video_tiles[2].stream_id)
        self.assertFalse(self.window._in_prompt_unconfigured)

    def test_failed_save_reports_error_instead_of_silent_success(self):
        count = len(self.manager.get_cameras())
        with patch("core.device_manager.os.replace", side_effect=PermissionError("fixture disk failure")), \
             patch("ui.main_window.QMessageBox.critical") as message:
            self.add_through_dialog("fixture")
        self.assertEqual(count, len(self.manager.get_cameras()))
        message.assert_called_once()

    def test_new_camera_ids_do_not_collide_at_same_address(self):
        ids = []
        for _ in range(2):
            dialog = DeviceDialog()
            dialog.txt_name.setText("Fixture")
            dialog.txt_ip.setText("127.0.0.2")
            dialog._save_camera()
            ids.append(dialog.result_data["id"])
            dialog.deleteLater()
        self.assertNotEqual(*ids)


if __name__ == "__main__":
    unittest.main()
