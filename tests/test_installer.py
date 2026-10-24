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
            for name in ("CCTVPanelView.exe", "CCTVPanelView-Uninstall.exe"):
                (source / name).write_bytes(b"fixture")
            target = Path(temp) / "installed"
            target.mkdir()
            config = {"cameras": [{"id": "preserved"}], "app_settings": {"default_layout": "3x3"}}
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
