import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication, QLineEdit
from core.device_manager import DeviceManager
from core.notification_dispatcher import NotificationDispatcher
from core.notification_policy import notification_category, notification_categories
from ui.components.settings_dialog import SettingsDialog


class ImmediateThread:
    def __init__(self, target, args=(), **kwargs): self.target, self.args = target, args
    def start(self): self.target(*self.args)


class NotificationPolicyTests(unittest.TestCase):
    def make_dispatcher(self, **changes):
        settings = dict(phone_notifications_enabled=True, master_alerts_enabled=True,
            outgoing_notification_categories=["person"], phone_alert_cooldown_sec=0,
            ntfy_enabled=True, ntfy_topic="test-only-not-a-real-topic",
            telegram_enabled=True, telegram_token="fixture", telegram_chat_id="fixture",
            discord_enabled=True, discord_webhook_url="https://example.invalid/webhook",
            phone_notify_video=True)
        settings.update(changes)
        with patch("core.notification_dispatcher.get_local_lan_ip", return_value="127.0.0.1"):
            return NotificationDispatcher(settings)

    def test_person_only_uses_detection_labels_never_descriptions_or_substrings(self):
        dispatcher = self.make_dispatcher()
        for label in ("PERSON", "people", "HUMAN", "om", "persoană"):
            self.assertTrue(dispatcher.should_notify_label(label), label)
        for label in ("MOTION", "CAR", "DOG", "CAT", "UNKNOWN", "MANUAL", "COMMON", "AUTOMATION"):
            entry = dict(label=label, description="Person walking from the car park",
                         what_found="PERSON", trigger_reason="Motion confirmed from camera")
            self.assertFalse(dispatcher.should_notify_label(label, entry), label)
        self.assertEqual(notification_category({"category": "vehicle", "label": "PERSON"}), "vehicle")
        self.assertIsNone(notification_category({"label": "person and car"}))

    def test_each_category_and_explicit_empty_selection(self):
        from core.ai_detector import PERSON_CLASSES, VEHICLE_CLASSES, ANIMAL_CLASSES
        for category, classes in (("person", PERSON_CLASSES), ("vehicle", VEHICLE_CLASSES), ("animal", ANIMAL_CLASSES)):
            dispatcher = self.make_dispatcher(outgoing_notification_categories=[category])
            for label in classes:
                self.assertTrue(dispatcher.should_notify_label(label), label)
        labels = {"person": "PERSON", "vehicle": "TRUCK", "animal": "CHICKEN", "motion": "MIȘCARE"}
        for category in labels:
            dispatcher = self.make_dispatcher(outgoing_notification_categories=[category])
            for other, label in labels.items():
                self.assertEqual(dispatcher.should_notify_label(label), other == category)
        for selected in ([], None, "person", ["invalid"]):
            dispatcher = self.make_dispatcher(outgoing_notification_categories=selected)
            self.assertFalse(dispatcher.should_notify_label("PERSON"))
        self.assertEqual(notification_categories({"notify_person": False, "notify_animal": True}), ["animal"])

    def test_photo_and_video_filter_is_identical_for_all_three_services(self):
        dispatcher = self.make_dispatcher()
        with tempfile.TemporaryDirectory() as temp, patch("core.notification_dispatcher.threading.Thread", ImmediateThread):
            video = Path(temp) / "fixture.mp4"
            video.write_bytes(b"x" * 3000)
            with patch.object(dispatcher, "_send_ntfy") as ntfy, patch.object(dispatcher, "_send_telegram") as telegram, \
                 patch.object(dispatcher, "_send_discord") as discord, patch.object(dispatcher, "_send_ntfy_video") as ntfy_video, \
                 patch.object(dispatcher, "_send_telegram_video") as telegram_video, patch.object(dispatcher, "_send_discord_video") as discord_video:
                for label in ("CAR", "DOG", "MOTION", "UNKNOWN", "PERSON"):
                    entry = dict(label=label, video_path=str(video), description="Motion from person camera")
                    dispatcher.send_alert(entry)
                    dispatcher.send_video_alert(entry)
                for delivery in (ntfy, telegram, discord, ntfy_video, telegram_video, discord_video):
                    self.assertEqual(delivery.call_count, 1)
                    self.assertEqual(delivery.call_args.args[1], "PERSON")

    def test_disarm_and_pending_policy_changes_stop_delivery(self):
        dispatcher = self.make_dispatcher()
        dispatcher.update_settings({"master_alerts_enabled": False})
        with patch("core.notification_dispatcher.threading.Thread") as thread:
            dispatcher.send_alert({"label": "PERSON"})
            dispatcher.send_video_alert({"label": "PERSON"})
            thread.assert_not_called()
        dispatcher.update_settings({"master_alerts_enabled": True, "outgoing_notification_categories": []})
        with patch("builtins.open", side_effect=AssertionError("Must filter before reading media")):
            dispatcher._dispatch_worker({"label": "PERSON", "snapshot_path": "fixture.jpg"})
            dispatcher._dispatch_video_worker({"label": "PERSON", "video_path": "fixture.mp4"})
        dispatcher.update_settings({"outgoing_notification_categories": ["person"], "phone_notify_video": False})
        dispatcher._dispatch_video_worker({"label": "PERSON"})

    def test_notification_defaults_do_not_publish_to_a_shared_topic(self):
        with patch("core.notification_dispatcher.get_local_lan_ip", return_value="127.0.0.1"):
            dispatcher = NotificationDispatcher()
        self.assertFalse(dispatcher.is_phone_enabled)
        self.assertFalse(dispatcher.ntfy_enabled)
        self.assertEqual(dispatcher.ntfy_topic, "")
        dispatcher = self.make_dispatcher(telegram_bot_token="legacy")
        self.assertEqual(dispatcher.telegram_token, "fixture")
        dispatcher.settings.pop("telegram_token")
        self.assertEqual(dispatcher.telegram_token, "legacy")


class NotificationSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def test_people_preset_saves_independently_and_survives_rearming_and_restart(self):
        dialog = SettingsDialog(dict(notify_person=True, notify_vehicle=True, notify_animal=True,
            notify_motion=True, outgoing_notification_categories=["animal"], phone_notifications_enabled=False))
        dialog.btn_people_only.click()
        dialog.sw_master_alerts.setChecked(False)
        dialog.sw_master_alerts.setChecked(True)
        self.assertTrue(dialog.sw_notify_motion.isChecked())
        self.assertFalse(dialog.sw_phone_enabled.isChecked())
        self.assertTrue(dialog.stack.widget(2).isAncestorOf(dialog.sw_notify_person))
        self.assertTrue(dialog.stack.widget(1).isAncestorOf(dialog.btn_people_only))
        self.assertTrue(dialog.has_unsaved_changes())
        saved = []
        dialog.settings_saved.connect(saved.append)
        dialog._commit_and_save_data()
        self.assertEqual(saved[0]["outgoing_notification_categories"], ["person"])
        self.assertTrue(saved[0]["notify_vehicle"])
        with tempfile.TemporaryDirectory() as temp:
            manager = DeviceManager(str(Path(temp) / "config.json"))
            manager.config["app_settings"].update(saved[0]); self.assertTrue(manager.save_config())
            restored = SettingsDialog(DeviceManager(manager.config_file).config["app_settings"])
            self.assertEqual([key for key, switch in restored.outgoing_category_switches.items() if switch.isChecked()], ["person"])
            self.assertFalse(restored.has_unsaved_changes())
            self.assertEqual(restored.txt_tg_token.echoMode(), QLineEdit.EchoMode.Password)
            restored.deleteLater()
        dialog.deleteLater()
        self.app.processEvents()


if __name__ == "__main__": unittest.main()
