import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from core.updates import (parse_release, version_tuple, validate_download_url, download_release,
                          verify_installer, GitHubRedirects)
from core.installation import preserve_upgrade_profile, backup_profile
from core.onboarding_profiles import prepare_camera
from ui.components.update_dialog import UpdateManager, UpdateDialog
from ui.components.settings_dialog import SettingsDialog


def release_data(payload=b"fixture installer", version="9.0.0"):
    tag = "v" + version
    name = f"CCTVPanelView-{version}-Setup.exe"
    return {"tag_name": tag, "html_url": f"https://github.com/SKIZZOO/CCTVPanelView/releases/tag/{tag}",
        "draft": False, "prerelease": False, "assets": [{"name": name, "state": "uploaded", "size": len(payload),
        "browser_download_url": f"https://github.com/SKIZZOO/CCTVPanelView/releases/download/{tag}/{name}",
        "digest": "sha256:" + hashlib.sha256(payload).hexdigest()}]}


class UpdateVerificationTests(unittest.TestCase):
    def test_versions_compare_numerically_and_ignore_prereleases(self):
        self.assertGreater(version_tuple("v2.10.0"), version_tuple("2.9.9"))
        for value in ("latest", "2.3", "v2.3.0-beta", "../../2.3.0"):
            with self.assertRaises(ValueError): version_tuple(value)
        self.assertEqual(parse_release(release_data()).version, "9.0.0")

    def test_release_must_have_expected_repository_asset_size_and_digest(self):
        changes = [("draft", True), ("prerelease", True), ("html_url", "https://github.com/other/repo/releases/tag/v9.0.0")]
        for key, value in changes:
            data = release_data(); data[key] = value
            with self.assertRaises(ValueError): parse_release(data)
        for key, value in (("digest", ""), ("size", 0), ("size", 2**40), ("size", True),
                           ("browser_download_url", "https://example.invalid/Setup.exe"), ("state", "new")):
            data = release_data(); data["assets"][0][key] = value
            with self.assertRaises(ValueError): parse_release(data)
        data = release_data(); data["assets"] *= 2
        with self.assertRaises(ValueError): parse_release(data)

    def test_redirects_reject_http_unknown_hosts_and_embedded_credentials(self):
        for url in ("http://github.com/a", "https://github.com.evil.invalid/a", "https://user@github.com/a", "https://github.com:8443/a"):
            with self.assertRaises(ValueError): validate_download_url(url)
        self.assertEqual(validate_download_url("https://release-assets.githubusercontent.com/a?signature=x"), "https://release-assets.githubusercontent.com/a?signature=x")
        with self.assertRaises(ValueError): GitHubRedirects().redirect_request(None, None, 302, "redirect", {}, "http://github.com/a")

    def test_download_verifies_bytes_and_rechecks_tampering_before_launch(self):
        payload = b"fixture installer"
        release = parse_release(release_data(payload))
        with tempfile.TemporaryDirectory() as temp, patch("core.updates.open_url", return_value=io.BytesIO(payload)):
            progress = []
            path = download_release(release, temp, progress.append)
            verify_installer(path, release)
            self.assertEqual(progress[-1], 100)
            Path(path).write_bytes(b"x" * len(payload))
            with self.assertRaises(ValueError): verify_installer(path, release)

    def test_incomplete_oversized_mismatched_and_cancelled_downloads_never_leave_an_exe(self):
        release = parse_release(release_data())
        for payload in (b"short", b"x" * release.size, b"x" * (release.size + 1)):
            with tempfile.TemporaryDirectory() as temp, patch("core.updates.open_url", return_value=io.BytesIO(payload)):
                with self.assertRaises(ValueError): download_release(release, temp)
                self.assertFalse(list(Path(temp).rglob("*.exe")))
                self.assertFalse(list(Path(temp).rglob("*.part")))
        cancelled = threading.Event(); cancelled.set()
        with tempfile.TemporaryDirectory() as temp, patch("core.updates.open_url", return_value=io.BytesIO(b"x")):
            with self.assertRaises(ValueError): download_release(release, temp, cancelled=cancelled)


class UpgradePreservationTests(unittest.TestCase):
    def profile(self):
        return {"cameras": [{"id": "camera", "streams": [{"id": "custom-stream-id", "url": "rtsps://user:p%40ss@127.0.0.1:322/custom?x=1", "sub_url": "rtsp://127.0.0.1/sub", "flip": True}]}],
                "app_settings": {"default_layout": "custom", "session_slot_assignments": {"0": "custom-stream-id", "3": ""}, "custom_layout": {"assignments": ["custom-stream-id"]}, "recording_dir": "recordings"}}

    def test_upgrade_and_relocation_keep_camera_ids_layout_and_media_locations(self):
        with tempfile.TemporaryDirectory() as temp:
            previous = Path(temp) / "old"; previous.mkdir()
            path = previous / "cameras_config.json"; path.write_text(json.dumps(self.profile()))
            original = path.read_bytes()
            self.assertTrue(preserve_upgrade_profile(previous))
            self.assertEqual(path.read_bytes(), original)
            target = Path(temp) / "new"
            self.assertTrue(preserve_upgrade_profile(target, previous))
            migrated = json.loads((target / "cameras_config.json").read_text())
            self.assertEqual(migrated["cameras"], self.profile()["cameras"])
            self.assertEqual(migrated["app_settings"]["session_slot_assignments"], self.profile()["app_settings"]["session_slot_assignments"])
            self.assertEqual(migrated["app_settings"]["recording_dir"], str(previous / "recordings"))
            self.assertEqual(path.read_bytes(), original)

    def test_existing_destination_wins_and_corrupt_profile_stops_upgrade(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cameras_config.json"; path.write_text(json.dumps(self.profile()))
            self.assertTrue(preserve_upgrade_profile(temp, Path(temp) / "unrelated"))
            path.write_text("corrupt")
            with self.assertRaises(ValueError): backup_profile(path)
            with self.assertRaises(ValueError): preserve_upgrade_profile(temp)
            self.assertEqual(path.read_text(), "corrupt")

    def test_setup_preserves_custom_stream_ids_urls_and_extra_streams(self):
        from core.onboarding_profiles import merge_setup_cameras
        camera = self.profile()["cameras"][0]
        camera["streams"].append({"id": "another-custom-id", "url": "rtsp://127.0.0.1/custom2", "name": "Extra"})
        original = deepcopy(camera)
        self.assertEqual(prepare_camera(camera), original)
        self.assertEqual(camera, original)
        fresh = prepare_camera({"id": "new", "ip": "127.0.0.1", "username": "admin", "password": "p@ss", "is_dual_lens": True})
        self.assertEqual(len(fresh["streams"]), 2)
        self.assertIn("p%40ss", fresh["streams"][0]["url"])
        previous = deepcopy(camera); previous["ip"] = "127.0.0.1"
        scan = {"id": "rescan-id", "ip": "127.0.0.1", "configured": False}
        self.assertEqual(merge_setup_cameras([scan], [previous]), [previous])
        configured = deepcopy(previous); configured["id"] = "new-camera-id"; configured["configured"] = True
        for i, stream in enumerate(configured["streams"]): stream["id"] = f"new-stream-{i}"
        merged = merge_setup_cameras([configured], [previous])[0]
        self.assertEqual(merged["id"], previous["id"])
        self.assertEqual([s["id"] for s in merged["streams"]], [s["id"] for s in previous["streams"]])


class UpdateUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def test_check_runs_off_ui_thread_and_dialog_offers_only_newer_releases(self):
        manager = UpdateManager()
        dialog = UpdateDialog(manager)
        ids = []
        release = parse_release(release_data())
        def check():
            ids.append(threading.get_ident()); time.sleep(.1); return release
        with patch("ui.components.update_dialog.check_latest", side_effect=check):
            start = time.monotonic(); dialog.check_button.click()
            self.assertLess(time.monotonic() - start, .08)
            deadline = time.monotonic() + 2
            while manager.busy and time.monotonic() < deadline:
                self.app.processEvents(); time.sleep(.005)
            self.app.processEvents()
        self.assertNotEqual(ids[0], threading.get_ident())
        self.assertTrue(dialog.download_button.isEnabled())
        self.assertFalse(dialog.install_button.isEnabled())
        old = parse_release(release_data(version="1.0.0")); manager.release = old
        dialog._checked(old); dialog._busy(False)
        self.assertFalse(dialog.download_button.isEnabled())
        dialog.deleteLater(); manager.shutdown(); manager.deleteLater(); self.app.processEvents()

    def test_auto_check_setting_is_saved_and_dirty_tracked(self):
        dialog = SettingsDialog({"auto_check_updates": True})
        self.assertFalse(dialog.has_unsaved_changes())
        dialog.sw_auto_updates.setChecked(False)
        self.assertTrue(dialog.has_unsaved_changes())
        saved = []; dialog.settings_saved.connect(saved.append); dialog._commit_and_save_data()
        self.assertFalse(saved[0]["auto_check_updates"])
        dialog.deleteLater(); self.app.processEvents()

    def test_settings_update_text_is_clean_unicode(self):
        from PyQt6.QtWidgets import QLabel, QPushButton
        dialog = SettingsDialog({})
        self.assertEqual(dialog.btn_check_updates.text(), "Check for updates")
        for widget in dialog.findChildren(QLabel) + dialog.findChildren(QPushButton):
            for broken in ("\u00e2\u20ac", "\ufffd"):
                self.assertNotIn(broken, widget.text())
        dialog.deleteLater(); self.app.processEvents()

    def test_installer_reuses_registered_folder_and_does_not_reopen_setup(self):
        import installer
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "cameras_config.json").write_text(json.dumps({"cameras": [], "app_settings": {"default_layout": "3x3"}}))
            with patch("installer.registered_install_dir", return_value=temp):
                dialog = installer.CCTVPanelViewInstaller(dry_run=True)
            self.assertEqual(dialog.txt_dest_path.text(), temp)
            self.assertFalse(dialog.chk_open_wizard.isChecked())
            self.assertFalse(dialog.chk_launch_wizard.isChecked())
            self.assertFalse(dialog.chk_open_wizard.isEnabled())
            dialog.deleteLater(); self.app.processEvents()


class WorkstationUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_desktop_state as desktop
        desktop.DesktopStateTests.setUpClass()

    def setUp(self):
        import test_desktop_state as desktop
        self.fixture = desktop.DesktopStateTests(); self.fixture.setUp()
        self.window = self.fixture.window

    def tearDown(self): self.fixture.tearDown()

    def test_update_banner_is_at_top_and_not_now_never_downloads_or_installs(self):
        release = parse_release(release_data())
        manager = self.window._get_update_manager(); manager.release = release
        with patch.object(self.window, "isVisible", return_value=True), \
             patch.object(self.window, "isActiveWindow", return_value=True), \
             patch.object(self.window, "isMinimized", return_value=False), \
             patch("ui.main_window.QApplication.activeModalWidget", return_value=None), \
             patch.object(manager, "download") as download, \
             patch.object(self.window, "_install_downloaded_update") as install:
            self.window._on_update_checked(release)
            prompt = self.window._update_prompt
            self.assertIsNotNone(prompt)
            self.assertEqual(self.window.central_widget.layout().indexOf(self.window.update_banner), 1)
            self.assertIn("9.0.0", self.window.update_banner.message.text())
            next(button for button in prompt.buttons() if button.text() == "Not now").click()
            QApplication.processEvents()
            self.assertIsNone(self.window._update_prompt)
            self.assertFalse(self.window.update_banner.isHidden())
            self.window._on_update_checked(release)
            self.assertIsNone(self.window._update_prompt)
            download.assert_not_called(); install.assert_not_called()

    def test_accepting_update_opens_verified_download_flow_only_after_consent(self):
        release = parse_release(release_data())
        self.window._get_update_manager().release = release
        with patch.object(self.window, "isVisible", return_value=True), \
             patch.object(self.window, "isActiveWindow", return_value=True), \
             patch.object(self.window, "isMinimized", return_value=False), \
             patch("ui.main_window.QApplication.activeModalWidget", return_value=None), \
             patch.object(self.window, "open_update_dialog") as open_dialog:
            self.window._on_update_checked(release)
            open_dialog.assert_not_called()
            prompt = self.window._update_prompt
            next(button for button in prompt.buttons() if button.text() == "Update now").click()
            open_dialog.assert_called_once_with(auto_download=True)
            QApplication.processEvents()

    def test_background_update_waits_for_foreground_before_prompting(self):
        release = parse_release(release_data())
        self.window._get_update_manager().release = release
        with patch.object(self.window, "isVisible", return_value=False):
            self.window._on_update_checked(release)
        self.assertIsNone(getattr(self.window, "_update_prompt", None))
        with patch.object(self.window, "isVisible", return_value=True), \
             patch.object(self.window, "isActiveWindow", return_value=True), \
             patch.object(self.window, "isMinimized", return_value=False), \
             patch("ui.main_window.QApplication.activeModalWidget", return_value=None):
            self.window._maybe_prompt_update()
            self.assertIsNotNone(self.window._update_prompt)
            self.window._update_prompt.reject()
            QApplication.processEvents()

    def test_current_or_older_release_does_not_show_an_update_notice(self):
        self.window._on_update_checked(parse_release(release_data(version="1.0.0")))
        self.assertTrue(self.window.update_banner.isHidden())
        self.assertIsNone(getattr(self.window, "_update_prompt", None))

    def test_install_handoff_saves_layout_and_passes_current_directory_without_scripts(self):
        payload = b"fixture installer"; release = parse_release(release_data(payload))
        path = Path(self.fixture.temp.name) / "Setup.exe"; path.write_bytes(payload)
        manager = self.window._get_update_manager(); manager.release = release; manager.installer_path = str(path)
        self.window._restoring_session = False; self.window.video_tiles[0].stream_id = "s2"
        executable = str(Path(self.fixture.temp.name) / "CCTVPanelView.exe")
        with patch("sys.frozen", True, create=True), patch("sys.executable", executable), \
             patch("subprocess.Popen") as launch, patch.object(self.window, "close") as close:
            self.window._install_downloaded_update()
        args = launch.call_args.args[0]
        self.assertEqual(args[:3], [str(path), "--install-dir", self.fixture.temp.name])
        self.assertEqual(args[3:], ["--wait-for-pid", str(os.getpid())])
        saved = json.loads(Path(self.fixture.manager.config_file).read_text())
        self.assertEqual(saved["app_settings"]["session_slot_assignments"]["0"], "s2")
        self.assertTrue(list((Path(self.fixture.temp.name) / "config-backups").glob("*.json")))
        close.assert_called_once()
        path.write_bytes(b"tampered")
        with patch("subprocess.Popen") as launch, patch("ui.main_window.QMessageBox.warning") as warning:
            self.window._install_downloaded_update()
        launch.assert_not_called(); warning.assert_called_once()

    def test_large_archive_maintenance_runs_off_ui_thread_and_preserves_prompt_policy(self):
        from core.maintenance import startup_maintenance
        manager = MagicMock()
        self.assertTrue(startup_maintenance(manager, {"retention_prompt_before_delete": True}))
        manager.remove_alerts.assert_not_called()
        manager.get_alerts_older_than.return_value = [{"id": "expired"}]
        self.assertFalse(startup_maintenance(manager, {"retention_prompt_before_delete": False}))
        manager.remove_alerts.assert_called_once_with(["expired"])
        ids = []
        def slow_scan(*args):
            ids.append(threading.get_ident()); time.sleep(.15); return False
        with patch("core.maintenance.startup_maintenance", side_effect=slow_scan):
            started = time.monotonic(); self.window._start_background_maintenance()
            self.assertLess(time.monotonic() - started, .08)
            deadline = time.monotonic() + 2
            while self.window._maintenance_pending and time.monotonic() < deadline:
                QApplication.processEvents(); time.sleep(.005)
            QApplication.processEvents()
        self.assertNotEqual(ids[0], threading.get_ident())


if __name__ == "__main__": unittest.main()
