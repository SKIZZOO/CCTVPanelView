import re
import unittest
from unittest.mock import patch
from core.notification_media import attachment_name
from core.notification_dispatcher import NotificationDispatcher


class AttachmentPresentationTests(unittest.TestCase):
    def test_event_time_and_camera_are_readable_and_stable(self):
        self.assertEqual(attachment_name("Front Gate (Main stream)", "PERSON", "2026-10-29 09:04:48"),
                         "Person_Front-Gate_2026-10-29_09-04-48_Preview.mp4")
        self.assertTrue(attachment_name("Front Gate", "CAR", "2026-10-28 23:59:59", snapshot=True)
                        .endswith("2026-10-28_23-59-59_Snapshot.jpg"))

    def test_untrusted_names_cannot_inject_headers_or_paths(self):
        name = attachment_name("../../Poartă\r\nInjected:" + "x" * 300, "../PERSON", "invalid")
        self.assertRegex(name, r"^[A-Za-z0-9_-]+\.mp4$")
        self.assertLess(len(name), 110)
        self.assertIn("Poarta", name)
        self.assertNotIn("..", name)
        self.assertTrue(attachment_name("", "", None).startswith("Detection_Camera_"))

    def test_video_and_snapshot_use_clean_titles_and_selected_names(self):
        with patch("core.notification_dispatcher.get_local_lan_ip", return_value="127.0.0.1"):
            dispatcher = NotificationDispatcher({})
        with patch.object(dispatcher, "_publish_ntfy") as publish:
            dispatcher._send_ntfy_video("Front Gate", "PERSON", .85, "Person walking", "09:04:48", b"video", "Person_Front-Gate.mp4")
            args = publish.call_args.args
            self.assertEqual(args[0], "Person video | Front Gate")
            self.assertEqual(args[-1], "Person_Front-Gate.mp4")
            self.assertEqual(args[2], "movie_camera")
            self.assertLess(len(args[1]), 190)
            dispatcher._send_ntfy("Front Gate", "PERSON", .85, "Person walking", "09:04:48", "", b"jpeg", "Person_Front-Gate.jpg")
            self.assertEqual(publish.call_args.args[0], "Person detected | Front Gate")
            self.assertEqual(publish.call_args.args[-1], "Person_Front-Gate.jpg")
