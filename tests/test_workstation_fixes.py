import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import io
import threading
import time
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import numpy as np
from PyQt6.QtCore import QCoreApplication, QThread
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication
import test_desktop_state as desktop
from core.device_manager import DeviceManager
from core.settings import normalize_settings
from core.sound_manager import SoundManager, SoundProfile
from core.alert_filters import alert_category, visible_alert
from core.resource_manager import get_resource_manager
from core.ai_detector import AIDetector
from ui.components.settings_dialog import SettingsDialog


class SoundTests(unittest.TestCase):
    def test_volume_changes_pcm_energy_without_changing_duration(self):
        with tempfile.TemporaryDirectory() as temp:
            path = str(Path(temp) / "tone.wav")
            samples = (np.sin(np.arange(1000) * .2) * 20000).astype("<i2")
            with wave.open(path, "wb") as output:
                output.setnchannels(1); output.setsampwidth(2); output.setframerate(44100)
                output.writeframes(samples.tobytes())
            energies = []
            for volume in (0, 25, 50, 100):
                data = SoundManager.scaled_wav(path, volume)
                with wave.open(io.BytesIO(data), "rb") as source:
                    self.assertEqual(source.getnframes(), 1000)
                    values = np.frombuffer(source.readframes(1000), "<i2").astype(float)
                energies.append(float(np.sqrt(np.mean(values ** 2))))
            self.assertEqual(energies[0], 0)
            self.assertAlmostEqual(energies[1] / energies[3], .25, places=3)
            self.assertAlmostEqual(energies[2] / energies[3], .5, places=3)

    def test_saved_volume_units_and_legacy_profiles_migrate(self):
        for old in (.8, 80):
            self.assertEqual(normalize_settings({"alert_volume": old})["sound_volume"], 80)
        self.assertEqual(SoundManager.volume_from_settings({"sound_volume": 1}), 1)
        self.assertEqual(SoundManager.normalize_profile("tactical_siren"), SoundProfile.SIREN)

    def test_native_playback_receives_scaled_memory_on_background_thread(self):
        manager = SoundManager()
        complete = threading.Event()
        calls = []
        def playback(data, flags):
            calls.append((data, flags, threading.get_ident()))
            complete.set()
        with patch("core.sound_manager.winsound.PlaySound", side_effect=playback):
            manager.play_sound(SoundProfile.SIREN, 25)
            self.assertTrue(complete.wait(3))
            self.assertTrue(calls[0][0].startswith(b"RIFF"))
            self.assertNotEqual(calls[0][2], threading.get_ident())
            self.assertFalse(calls[0][1] & 1, "SND_ASYNC is invalid with memory playback")
        if manager._playback_thread:
            manager._playback_thread.join(1)


class ResourceTests(unittest.TestCase):
    def test_decoder_cpu_is_counted_even_when_psutil_returns_new_objects(self):
        class Process:
            def __init__(self, pid, used): self.pid, self.used = pid, used
            def create_time(self): return self.pid
            def cpu_times(self): return SimpleNamespace(user=self.used, system=0)
            def children(self, recursive=True): return [Process(2, cpu[1])]
        cpu = [0, 0]
        root = Process(1, 0)
        manager = get_resource_manager()
        with patch.multiple(manager, _psutil_proc=root, total_cores=4, _cpu_samples={}, _cpu_sample_lock=threading.Lock()), patch("core.resource_manager.time.monotonic", side_effect=[1, 2]), patch("core.resource_manager.psutil.cpu_percent", return_value=80):
            self.assertEqual(manager.get_process_cpu_percent(), 0)
            root.used, cpu[1] = 2, 1
            self.assertEqual(manager.get_process_cpu_percent(), 75)
            self.assertEqual(manager.get_child_cpu_percent(), 25)

    def test_ai_model_loading_is_deferred_until_inference(self):
        with patch.object(AIDetector, "_load_model") as load:
            detector = AIDetector()
            load.assert_not_called()
            detector.detect(np.zeros((64, 64, 3), np.uint8))
            load.assert_called_once()


class WorkstationFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): desktop.DesktopStateTests.setUpClass()

    def setUp(self):
        self.fixture = desktop.DesktopStateTests()
        self.fixture.setUp()
        self.window = self.fixture.window
        self.manager = self.fixture.manager
        self.window._restoring_session = False

    def tearDown(self): self.fixture.tearDown()

    def test_latest_layout_and_hidden_slots_are_saved_on_close_to_tray(self):
        self.window.set_grid_layout("4x4")
        self.window.video_tiles[8].stream_id = "s2"
        event = QCloseEvent()
        self.window._minimize_to_tray(event)
        saved = DeviceManager(self.manager.config_file).config["app_settings"]
        self.assertEqual(saved["default_layout"], "4x4")
        self.assertEqual(saved["session_slot_assignments"]["8"], "s2")

    def test_custom_layout_template_keeps_latest_tile_assignment(self):
        self.window.app_settings["custom_layout"] = {"rows": 1, "cols": 2,
            "slots": [{"r": 0, "c": 0}, {"r": 0, "c": 1}], "assignments": ["old", ""]}
        self.window.current_layout = "custom"
        self.window.video_tiles[0].stream_id = "s2"
        self.window.video_tiles[1].stream_id = ""
        self.assertTrue(self.window.save_session_state())
        saved = DeviceManager(self.manager.config_file).config["app_settings"]
        self.assertEqual(saved["custom_layout"]["assignments"], ["s2", ""])

    def test_settings_preserve_every_supported_layout_and_group_related_controls(self):
        for layout in ("1x1", "2x1", "1x2", "2x2", "1+5", "3x3", "4x4", "custom"):
            dialog = SettingsDialog({"default_layout": layout, "sound_volume": 27})
            self.assertEqual(dialog.cmb_layout.currentData(), layout)
            self.assertEqual(dialog.stack.count(), 6)
            self.assertEqual(dialog.slider_sound_vol.value(), 27)
            self.assertTrue(dialog.stack.widget(1).isAncestorOf(dialog.slider_sound_vol))
            self.assertTrue(dialog.stack.widget(2).isAncestorOf(dialog.sw_wind_enabled))
            self.assertTrue(dialog.stack.widget(4).isAncestorOf(dialog.sw_night_auto))
            dialog.settings_search.setText("speaker volume")
            self.assertEqual(dialog.sidebar.currentRow(), 1)
            dialog.deleteLater()
        QApplication.processEvents()

    def test_filters_apply_to_existing_and_new_cards_and_persist_without_deleting(self):
        for category in ("motion", "person", "animal", "car"):
            self.window._add_alert_card({"id": category, "label": category})
        for key, check in self.window.alert_filter_checks.items():
            check.setChecked(key == "person")
        self.assertFalse(self.window.alert_cards["person"].isHidden())
        self.assertTrue(self.window.alert_cards["motion"].isHidden())
        self.window._add_alert_card({"id": "new-car", "label": "car"})
        self.assertTrue(self.window.alert_cards["new-car"].isHidden())
        self.assertEqual(len(self.window.alert_cards), 5)
        saved = DeviceManager(self.manager.config_file).config["app_settings"]
        self.assertEqual(saved["visible_alert_categories"], ["person"])
        self.assertEqual(alert_category({"label": "TRUCK"}), "vehicle")
        self.assertFalse(visible_alert({"label": "person"}, []))

    def test_topbar_sampling_runs_in_background_and_ui_receives_fresh_snapshot(self):
        manager = get_resource_manager()
        thread_ids = []
        snapshot = manager.get_hardware_telemetry_snapshot()
        snapshot["cpu"]["app_pct"] = 12.3
        def sample(path):
            thread_ids.append(threading.get_ident())
            time.sleep(.1)
            return snapshot
        with patch.object(manager, "get_hardware_telemetry_snapshot", side_effect=sample):
            started = time.monotonic()
            self.window._update_cpu_monitor()
            self.assertLess(time.monotonic() - started, .05)
            deadline = time.monotonic() + 2
            while self.window._telemetry_pending and time.monotonic() < deadline:
                QApplication.processEvents()
                time.sleep(.005)
            self.assertNotEqual(thread_ids[0], threading.get_ident())
            self.assertIn("12.3", self.window.btn_cpu_monitor.text())

    def test_siren_settings_preview_uses_same_percent_as_live_alerts(self):
        dialog = SettingsDialog({"sound_volume": 32, "sound_profile": SoundProfile.SIREN})
        with patch.object(dialog.sound_manager, "play_test_tone") as preview:
            dialog._test_sound()
            self.assertEqual(preview.call_args.args[1], 32)
        dialog._preview_timer.stop()
        dialog.deleteLater()


if __name__ == "__main__": unittest.main()
