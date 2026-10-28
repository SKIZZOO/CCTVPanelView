import io
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from core.notification_dispatcher import NotificationDispatcher, private_drive_folder_url
from ui.components.settings_dialog import SettingsDialog

LINK = "https://drive.google.com/drive/folders/private_fixture?usp=sharing"


class DriveFolderDeliveryTests(unittest.TestCase):
    def make_dispatcher(self):
        with patch("core.notification_dispatcher.get_local_lan_ip", return_value="127.0.0.1"):
            return NotificationDispatcher({"phone_notifications_enabled": True, "ntfy_enabled": True,
                "ntfy_topic": "fixture", "phone_notify_video": True,
                "ntfy_video_delivery": "google_drive_folder", "ntfy_google_drive_folder_url": LINK,
                "outgoing_notification_categories": ["person"]})

    def test_100_mb_recording_sends_one_small_folder_notification_without_reading_media(self):
        dispatcher = self.make_dispatcher()
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "person_recording.mp4"
            with video.open("wb") as file: file.truncate(100_000_000)
            with patch("builtins.open", side_effect=AssertionError("Must not read/upload full media")), \
                 patch("core.notification_dispatcher.prepare_phone_video", side_effect=AssertionError("Must not compress full video")), \
                 patch("core.notification_dispatcher.verified_tls_context", return_value=object()), \
                 patch("core.notification_dispatcher.urllib.request.urlopen", return_value=io.BytesIO(b'{"id":"fixture","event":"message"}')) as send:
                dispatcher._dispatch_video_worker({"label": "PERSON", "video_path": str(video)})
            send.assert_called_once()
            request = send.call_args.args[0]
            self.assertEqual(request.get_method(), "POST")
            self.assertLess(len(request.data), 2000)
            self.assertIn(b"person_recording.mp4", request.data)
            self.assertIn(b"100.0 MB", request.data)
            self.assertIn(b"does not confirm cloud upload", request.data)
            self.assertEqual(request.get_header("Click"), LINK)
            self.assertEqual(json.loads(request.get_header("Actions"))[0]["url"], LINK)
            self.assertIsNone(request.get_header("Filename"))
            self.assertIsNone(request.get_header("Attach"))
            self.assertEqual(video.stat().st_size, 100_000_000)

    def test_google_folder_mode_respects_people_filter_and_disarm(self):
        dispatcher = self.make_dispatcher()
        with patch.object(dispatcher, "_send_ntfy_drive_folder") as send:
            dispatcher._dispatch_video_worker({"label": "CAR", "video_path": "unused"})
            dispatcher.settings["master_alerts_enabled"] = False
            dispatcher._dispatch_video_worker({"label": "PERSON", "video_path": "unused"})
        send.assert_not_called()

    def test_only_real_google_drive_folder_urls_are_accepted(self):
        for link in (LINK, "https://drive.google.com/drive/u/0/folders/fixture_123"):
            self.assertEqual(private_drive_folder_url(link), link)
        for link in ("", "http://drive.google.com/drive/folders/id", "https://drive.google.com.evil/drive/folders/id",
                     "https://drive.google.com@evil/drive/folders/id", "https://drive.google.com/open?id=x",
                     "https://drive.google.com/drive/folders/id?redirect=https://evil", "javascript:alert(1)"):
            with self.assertRaises(ValueError): private_drive_folder_url(link)


class DriveFolderSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def test_folder_picker_resolves_link_in_background_without_pasting(self):
        import threading
        import time
        dialog = SettingsDialog({"ntfy_video_delivery": "google_drive_folder"})
        observed = []
        def resolve(folder):
            observed.append((folder, threading.get_ident()))
            time.sleep(.1)
            return LINK
        with patch("ui.components.settings_dialog.QFileDialog.getExistingDirectory", return_value="X:/My Drive/CCTV"), \
             patch("core.drive_folder.resolve_drive_folder_url", side_effect=resolve):
            started = time.monotonic()
            dialog._browse_ntfy_drive_folder()
            self.assertLess(time.monotonic() - started, .08)
            deadline = time.monotonic() + 2
            while not dialog.txt_ntfy_drive_folder.text() and time.monotonic() < deadline:
                self.app.processEvents(); time.sleep(.005)
        self.assertEqual(dialog.txt_ntfy_drive_folder.text(), LINK)
        self.assertEqual(observed[0][0], "X:/My Drive/CCTV")
        self.assertNotEqual(observed[0][1], threading.get_ident())
        self.assertTrue(dialog.txt_ntfy_drive_folder.isReadOnly())
        dialog.deleteLater(); self.app.processEvents()

    def test_folder_mode_and_url_save_and_restore_without_enabling_sharing(self):
        dialog = SettingsDialog({})
        self.assertEqual(dialog.cmb_ntfy_video_delivery.currentData(), "preview")
        dialog.cmb_ntfy_video_delivery.setCurrentIndex(1)
        self.assertTrue(dialog.txt_ntfy_drive_folder.isEnabled())
        dialog.txt_ntfy_drive_folder.setText(LINK)
        self.assertTrue(dialog.has_unsaved_changes())
        saved = []; dialog.settings_saved.connect(saved.append)
        dialog._commit_and_save_data()
        self.assertEqual(saved[0]["ntfy_video_delivery"], "google_drive_folder")
        self.assertEqual(saved[0]["ntfy_google_drive_folder_url"], LINK)
        restored = SettingsDialog(saved[0])
        self.assertEqual(restored.cmb_ntfy_video_delivery.currentData(), "google_drive_folder")
        self.assertEqual(restored.txt_ntfy_drive_folder.text(), LINK)
        self.assertFalse(restored.has_unsaved_changes())
        dialog.deleteLater(); restored.deleteLater(); self.app.processEvents()
