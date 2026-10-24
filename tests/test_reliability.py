import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from core.device_manager import DeviceManager
from cctv_server import CCTVHeadlessServer


class ConfigurationTests(unittest.TestCase):
    def test_generated_ids_remain_unique_after_removal(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = DeviceManager(str(Path(folder)/'config.json'))
            for name in ('a','b','c'):
                manager.add_camera({'name':name})
            removed_id = manager.get_cameras()[1]['id']
            manager.delete_camera(removed_id)
            manager.add_camera({'name':'d'})
            ids = [cam['id'] for cam in manager.get_cameras()]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertNotIn(removed_id, ids)

    def test_failed_replace_preserves_previous_config_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'config.json'
            manager = DeviceManager(str(path))
            original = path.read_bytes()
            manager.config['cameras'].append({'id':'new'})
            with patch('core.device_manager.os.replace', side_effect=OSError('simulated disk failure')):
                manager.save_config()
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(folder).glob('*.tmp')), [])
            manager.save_config()
            self.assertEqual(json.loads(path.read_text())['cameras'], [{'id':'new'}])

    def test_serialization_failure_preserves_previous_config(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'config.json'
            manager = DeviceManager(str(path))
            original = path.read_bytes()
            manager.config['bad'] = object()
            manager.save_config()
            self.assertEqual(path.read_bytes(), original)


class HeadlessTests(unittest.TestCase):
    def test_startup_uses_current_server_interface(self):
        # A real WebStreamingServer on an ephemeral port, without camera hardware.
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder)/'config.json'
            config.write_text(json.dumps({'cameras':[], 'app_settings':{'web_port':0}}))
            alert_manager = MagicMock()
            with patch('cctv_server.AlertManager', return_value=alert_manager), \
                 patch('cctv_server.get_resource_manager', return_value=MagicMock()), \
                 patch('cctv_server.enable_windows_sleep_prevention'), \
                 patch('cctv_server.restore_windows_sleep'):
                server = CCTVHeadlessServer(str(config))
                try:
                    server.start()
                    self.assertTrue(server.web_server.is_running)
                    self.assertGreater(server.web_server.port, 0)
                    alert_manager.set_app_settings.assert_called_once()
                finally:
                    server.stop()
                alert_manager.flush_and_save_sync.assert_called_once()


if __name__ == '__main__':
    unittest.main()
