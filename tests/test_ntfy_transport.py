import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import io
import json
import threading
import time
import unittest
import urllib.error
import ssl
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from core.notification_dispatcher import NotificationDispatcher
from ui.components.settings_dialog import SettingsDialog
from core.network_tls import verified_tls_context


class Response(io.BytesIO):
    def __init__(self, data=b'{"id":"fixture-id","event":"message"}'):
        super().__init__(data)


class NtfyTransportTests(unittest.TestCase):
    def setUp(self):
        with patch("core.notification_dispatcher.get_local_lan_ip", return_value="127.0.0.1"):
            self.dispatcher = NotificationDispatcher({"ntfy_enabled": True, "ntfy_topic": "fixture-topic"})

    def test_photo_and_clip_requests_do_not_depend_on_google_drive_or_cloud_files(self):
        with patch("core.notification_dispatcher.urllib.request.urlopen", side_effect=lambda request, **kwargs: Response()) as request, \
             patch("core.notification_dispatcher.verified_tls_context", return_value=object()), \
             patch("builtins.open", side_effect=FileNotFoundError("optional sync database unavailable")):
            self.dispatcher._send_ntfy("Camera", "PERSON", .9, "Person detected", "12:00", "confirmed", b"jpeg")
            self.dispatcher._send_ntfy_video("Camera", "PERSON", .9, "Person detected", "12:00", b"mp4", "clip.mp4")
        self.assertEqual(request.call_count, 2)
        photo, clip = [call.args[0] for call in request.call_args_list]
        self.assertEqual([photo.get_method(), clip.get_method()], ["PUT", "PUT"])
        self.assertEqual([photo.data, clip.data], [b"jpeg", b"mp4"])
        self.assertEqual(photo.get_header("Priority"), "urgent")
        self.assertEqual(clip.get_header("Filename"), "clip.mp4")
        self.assertIsNone(clip.get_header("Actions"))
        self.assertIsNone(clip.get_header("Click"))

    def test_missing_snapshot_is_sent_as_utf8_text_with_safe_headers(self):
        with patch("core.notification_dispatcher.urllib.request.urlopen", return_value=Response()) as request:
            self.dispatcher._send_ntfy("Camera\r\nInjected", "PERSON", .9, "Persoană lângă poartă", "12:00", "", None)
        actual = request.call_args.args[0]
        self.assertEqual(actual.get_method(), "POST")
        self.assertEqual(actual.data.decode("utf-8"), "Persoană lângă poartă")
        self.assertNotIn("\n", actual.get_header("Title"))
        self.assertIsNone(actual.get_header("Filename"))

    def test_attachment_limit_falls_back_to_text_without_claiming_cloud_upload(self):
        for video in (False, True):
            calls = []
            def publish(request, **kwargs):
                calls.append(request)
                if len(calls) == 1:
                    raise urllib.error.HTTPError(request.full_url, 413, "too large", {}, None)
                return Response()
            with patch("core.notification_dispatcher.urllib.request.urlopen", side_effect=publish):
                if video: self.dispatcher._send_ntfy_video("Camera", "PERSON", .9, "Person", "12:00", b"mp4", "clip.mp4")
                else: self.dispatcher._send_ntfy("Camera", "PERSON", .9, "Person", "12:00", "", b"jpeg")
            self.assertEqual([r.get_method() for r in calls], ["PUT", "POST"])
            self.assertIsNone(calls[-1].get_header("Filename"))
            self.assertNotIn(b"Google Drive", calls[-1].data)

    def test_server_rejection_and_invalid_success_bodies_are_not_reported_as_success(self):
        for status in (401, 403, 429, 500):
            error = urllib.error.HTTPError("https://ntfy.sh/secret-topic", status, "no", {}, None)
            with patch("core.notification_dispatcher.urllib.request.urlopen", side_effect=error):
                ok, message = self.dispatcher.send_test_notification("ntfy")
            self.assertFalse(ok)
            self.assertIn(str(status), message)
            self.assertNotIn("secret-topic", message)
        for response in (b"<html>proxy login</html>", b'{}', b'{"event":"keepalive","id":"fixture"}'):
            with patch("core.notification_dispatcher.urllib.request.urlopen", return_value=Response(response)):
                ok, _ = self.dispatcher.send_test_notification("ntfy")
            self.assertFalse(ok)

    def test_manual_test_contains_no_camera_data_and_requires_message_acknowledgement(self):
        with patch("core.notification_dispatcher.urllib.request.urlopen", return_value=Response()) as request:
            ok, message = self.dispatcher.send_test_notification("ntfy")
        self.assertTrue(ok)
        actual = request.call_args.args[0]
        self.assertEqual(actual.get_method(), "POST")
        self.assertIsNone(actual.get_header("Filename"))
        self.assertIn(b"No camera data is included", actual.data)
        self.assertIn("Server accepted", message)

    def test_empty_topic_never_sends_to_a_shared_fallback(self):
        self.dispatcher.settings["ntfy_topic"] = ""
        with patch("core.notification_dispatcher.urllib.request.urlopen") as request:
            ok, _ = self.dispatcher.send_test_notification("ntfy")
        self.assertFalse(ok)
        request.assert_not_called()


class VerifiedTlsTests(unittest.TestCase):
    def test_missing_windows_default_store_keeps_bundled_roots_and_verification(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(ssl.SSLContext, "load_default_certs", side_effect=FileNotFoundError("missing default trust store")):
            context = verified_tls_context()
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertGreater(context.cert_store_stats()["x509_ca"], 0)

    def test_explicit_missing_custom_ca_is_not_silently_ignored(self):
        with patch.dict(os.environ, {"SSL_CERT_FILE": "Z:/nonexistent/explicit-custom-ca.pem"}):
            with self.assertRaises(OSError): verified_tls_context()

    def test_publish_request_receives_a_verifying_tls_context(self):
        with patch("core.notification_dispatcher.get_local_lan_ip", return_value="127.0.0.1"):
            dispatcher = NotificationDispatcher({"ntfy_enabled": True, "ntfy_topic": "fixture-topic"})
        with patch("core.notification_dispatcher.urllib.request.urlopen", return_value=Response()) as request:
            dispatcher._send_ntfy("Fixture", "TEST", 0, "Fixture", "12:00", "", None)
        context = request.call_args.kwargs["context"]
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)


class NtfySettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def test_settings_test_uses_unsaved_topic_on_background_thread(self):
        dialog = SettingsDialog({"ntfy_enabled": True, "ntfy_topic": "old-topic"})
        dialog.txt_ntfy_topic.setText("edited-topic")
        observed = []
        def send(dispatcher, service):
            observed.append((dispatcher.ntfy_topic, service, threading.get_ident()))
            time.sleep(.1)
            return True, "Server accepted test"
        with patch.object(NotificationDispatcher, "send_test_notification", send):
            started = time.monotonic(); dialog.btn_ntfy_test.click()
            self.assertLess(time.monotonic() - started, .08)
            deadline = time.monotonic() + 2
            while not dialog.btn_ntfy_test.isEnabled() and time.monotonic() < deadline:
                self.app.processEvents(); time.sleep(.005)
        self.assertEqual(observed[0][:2], ("edited-topic", "ntfy"))
        self.assertNotEqual(observed[0][2], threading.get_ident())
        self.assertIn("accepted", dialog.lbl_ntfy_test.text())
        dialog.deleteLater(); self.app.processEvents()


if __name__ == "__main__": unittest.main()
