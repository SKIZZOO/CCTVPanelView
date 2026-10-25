import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import time
import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import urlsplit, unquote
from PyQt6.QtWidgets import QApplication
from core.camera_urls import build_rtsp_url, stream_path, camera_endpoint
from core.connection_test import ConnectionTestWorker
from core.device_manager import DeviceManager
from core.camera_stream import CameraStreamWorker, StreamStatus
from core.signal_monitor import SignalMonitor
from ui.components.device_dialog import DeviceDialog
from ui.components.settings_dialog import SettingsDialog


class CameraConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_reserved_credentials_and_ipv6_are_encoded(self):
        url = build_rtsp_url("u@ser", "p:/#?% word", "::1", 8554, "/channel?quality=1")
        parsed = urlsplit(url)
        self.assertEqual(unquote(parsed.username), "u@ser")
        self.assertEqual(unquote(parsed.password), "p:/#?% word")
        self.assertEqual(camera_endpoint(url), ("::1", 8554))
        self.assertEqual(stream_path(url), "/channel?quality=1")

    def test_test_worker_uses_exact_url_without_form_socket_gate(self):
        url = "rtsps://url-user:secret@stream.example:8554/custom?channel=3"
        worker = ConnectionTestWorker(url, "different-form-host", 1)
        results = []
        worker.test_finished.connect(lambda *value: results.append(value))
        with patch.object(DeviceManager, "test_connection", return_value={"success": True, "message": "verified"}) as test:
            worker.run()
        self.assertEqual(test.call_args.args, (url,))
        self.assertEqual(results, [(True, "verified")])
        worker._finished()

    def test_device_dialog_tests_and_saves_exact_custom_url(self):
        url = "rtsp://url-user:secret@127.0.0.1:8554/custom?channel=3"
        dialog = DeviceDialog()
        dialog.txt_name.setText("Custom camera")
        dialog.txt_ip.setText("127.0.0.2")
        dialog.txt_stream1_url.setText(url)
        with patch("ui.components.device_dialog.AsyncConnectionTester") as factory:
            dialog._test_connection()
            self.assertEqual(factory.call_args.args[0], url)
        dialog.test_worker = None
        dialog._save_camera()
        self.assertEqual(dialog.result_data["streams"][0]["url"], url)

    def test_settings_load_test_and_apply_preserve_custom_url(self):
        url = "rtsp://stream-user:secret@127.0.0.1:8554/custom?profile=2"
        camera = {"id": "c1", "name": "Camera", "ip": "127.0.0.2", "port": 554,
                  "username": "form-user", "password": "other", "streams": [{"id": "s1", "url": url}]}
        dialog = SettingsDialog(current_settings={}, cameras=[camera])
        self.assertEqual(dialog.txt_cam_url1.text(), url)
        with patch("ui.components.settings_dialog.AsyncSettingsConnectionTester") as factory:
            dialog._test_camera_connection()
            self.assertEqual(factory.call_args.kwargs["url"], url)
        dialog.test_worker = None
        dialog._apply_active_camera_connection()
        self.assertEqual(dialog.cameras[0]["streams"][0]["url"], url)
        dialog.hide()
        dialog.deleteLater()

    def test_changed_url_cannot_receive_a_stale_success_badge(self):
        dialog = DeviceDialog()
        dialog._tested_url = "rtsp://127.0.0.1/old"
        dialog.txt_stream1_url.setText("rtsp://127.0.0.1/new")
        dialog._on_test_finished(True, "Verified old camera")
        self.assertIn("changed", dialog.lbl_test_result.text())
        dialog.deleteLater()

    def test_connection_field_edits_keep_custom_path_and_password_spaces(self):
        dialog = DeviceDialog()
        dialog.txt_stream1_url.setText("rtsp://127.0.0.1/custom?profile=2")
        dialog.txt_user.setText("u@ser")
        dialog.txt_pass.setText(" p:/?#% ")
        parsed = urlsplit(dialog.txt_stream1_url.text())
        self.assertEqual(unquote(parsed.password), " p:/?#% ")
        self.assertEqual(stream_path(dialog.txt_stream1_url.text()), "/custom?profile=2")
        dialog.deleteLater()

    def test_staying_in_settings_does_not_cancel_the_pending_test(self):
        from PyQt6.QtGui import QCloseEvent
        dialog = SettingsDialog(current_settings={}, cameras=[])
        worker = MagicMock()
        worker.isRunning.return_value = True
        dialog.test_worker = worker
        event = QCloseEvent()
        with patch.object(dialog, "has_unsaved_changes", return_value=True), patch.object(dialog, "_prompt_unsaved_changes", return_value="cancel"):
            dialog.closeEvent(event)
        self.assertFalse(event.isAccepted())
        worker.cancel.assert_not_called()
        dialog.test_worker = None
        dialog.deleteLater()

    def test_reachable_endpoint_with_failed_video_is_not_called_offline(self):
        capture = MagicMock()
        capture.open.return_value = False
        capture.error_code = "open_failed"
        with patch("core.capture_process.IsolatedCapture", return_value=capture), patch("socket.create_connection"):
            result = DeviceManager.test_connection("rtsp://127.0.0.1:8554/camera")
        self.assertFalse(result["success"])
        self.assertTrue(result["reachable"])
        self.assertIn("reachable", result["error"])
        self.assertNotIn("offline", result["error"].lower())
        capture.release.assert_called_once()

    def test_network_monitor_probes_configured_stream_port(self):
        monitor = SignalMonitor()
        monitor._endpoints = {"camera": (("localhost", 8554),)}
        monitor.camera_ips = ["camera"]
        result = {"is_online": True, "latency_ms": 1}
        try:
            with patch.object(monitor, "_probe_single_ip", return_value=result) as probe:
                monitor._probe_and_report("camera", (("localhost", 8554),))
                self.assertEqual(probe.call_args.kwargs["port"], 8554)
                self.app.processEvents()
                self.assertTrue(monitor.signal_cache["camera"]["is_online"])
        finally:
            monitor.stop()

    def test_stale_video_is_not_evidence_of_current_connectivity(self):
        worker = CameraStreamWorker("test", "Camera", "rtsp://127.0.0.1/camera")
        try:
            worker._running = True
            worker.status = StreamStatus.LIVE
            worker._last_frame_received_time = time.time() - 30
            self.assertFalse(worker.has_recent_frame())
            worker._last_frame_received_time = time.time()
            self.assertTrue(worker.has_recent_frame())
            worker.status = StreamStatus.RECONNECTING
            self.assertFalse(worker.has_recent_frame())
        finally:
            worker.stop(wait=False)


if __name__ == "__main__":
    unittest.main()
