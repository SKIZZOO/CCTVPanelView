import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import installer


class InstallerTests(unittest.TestCase):
    def test_upgrade_preserves_configuration_and_deploys_only_native_launchers(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "payload"
            source.mkdir()
            runtime = source / "payload" / "CCTVPanelView"
            (runtime / "_internal").mkdir(parents=True)
            (runtime / "CCTVPanelView.exe").write_bytes(b"fixture")
            (runtime / "_internal" / "library.dll").write_bytes(b"runtime fixture")
            (source / "CCTVPanelView-Uninstall.exe").write_bytes(b"fixture")
            target = Path(temp) / "installed"
            target.mkdir()
            config = {"cameras": [{"id": "preserved", "streams": [{"id": "custom-feed"}]}], "app_settings": {"default_layout": "custom", "session_slot_assignments": {"0": "custom-feed", "1": ""}, "custom_layout": {"assignments": ["custom-feed", ""]}}}
            path = target / "cameras_config.json"
            path.write_text(json.dumps(config))
            result = []
            worker = installer.InstallerDeploymentWorker(str(target), False, False, False, False)
            worker.installation_finished.connect(lambda ok, message: result.append((ok, message)))
            with patch.object(installer, "BASE_DIR", str(source)), \
                 patch.object(worker, "msleep"), patch("psutil.process_iter", return_value=[]), \
                 patch.dict("sys.modules", {"winreg": MagicMock()}):
                worker.run()
            self.assertEqual([(True, "Success")], result)
            self.assertEqual(config, json.loads(path.read_text()))
            self.assertTrue((target / "CCTVPanelView.exe").is_file())
            self.assertEqual((target / "_internal" / "library.dll").read_bytes(), b"runtime fixture")
            backups = list((target / "config-backups").glob("*.json"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), path.read_bytes())
            self.assertFalse(list(target.glob("*.bat")))
            self.assertFalse(list(target.glob("*.vbs")))

    def test_missing_payload_fails_before_creating_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "installed"
            result = []
            worker = installer.InstallerDeploymentWorker(str(target), False, False, False, False)
            worker.installation_finished.connect(lambda ok, message: result.append((ok, message)))
            with patch.object(installer, "BASE_DIR", temp):
                worker.run()
            self.assertFalse(result[0][0])
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
