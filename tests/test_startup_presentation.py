import json
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from PyQt6.QtWidgets import QApplication
from core.startup_animation import application_icon, parent_alive
from core.windows_identity import APP_USER_MODEL_ID, create_shortcut, restore_legacy_icons
from ui.components.splash_screen import CyberneticSplashScreen

ROOT = Path(__file__).resolve().parents[1]


class StartupPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def test_icon_contains_visible_small_and_high_dpi_frames(self):
        icon = application_icon(ROOT)
        self.assertFalse(icon.isNull())
        for size in (16, 32, 256):
            pixmap = icon.pixmap(size, size)
            self.assertFalse(pixmap.isNull())
            image = pixmap.toImage()
            self.assertTrue(any(image.pixelColor(x, y).alpha() > 0
                                for x in range(image.width()) for y in range(image.height())))

    def test_animation_waits_for_ready_and_skip_still_finishes(self):
        splash = CyberneticSplashScreen(duration_sec=.01, wait_for_ready=True)
        splash.timer.stop()
        for _ in range(20): splash._on_tick()
        self.assertFalse(splash.is_fading_out)
        self.assertGreater(splash.elapsed, .01)
        finished = []; splash.finished.connect(lambda: finished.append(True))
        splash._skip_to_finish()
        for _ in range(20): splash._on_tick()
        self.assertTrue(finished)
        splash.close(); splash.deleteLater()

    def test_animation_keeps_ticking_in_child_while_parent_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            control, report = Path(temp) / "control", Path(temp) / "report.json"
            env = os.environ.copy(); env["QT_QPA_PLATFORM"] = "offscreen"
            process = subprocess.Popen([sys.executable, str(ROOT / "main.py"), "--startup-splash",
                f"--startup-control={control}", f"--startup-parent={os.getpid()}", f"--startup-report={report}"],
                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                # Intentionally no Qt processEvents: parent initialization cannot
                # drive or stall the companion's independent event loop.
                deadline = time.monotonic() + 10
                while not control.with_suffix(".started").exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(control.with_suffix(".started").exists())
                time.sleep(.8)
                control.write_text("ready", encoding="ascii")
                stdout, stderr = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, stderr.decode(errors="replace"))
                result = json.loads(report.read_text())
                self.assertGreater(result["frames"], 20)
                self.assertTrue(result["icon"])
                self.assertTrue(result["taskbar_window"])
            finally:
                if process.poll() is None: process.kill(); process.wait()

    def test_legacy_pinned_icon_paths_are_restored_from_onedir_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "_internal/assets"; source.mkdir(parents=True)
            (source / "cctv_logo.ico").write_bytes(b"fixture icon")
            restore_legacy_icons(root)
            self.assertEqual((root / "assets/cctv_logo.ico").read_bytes(), b"fixture icon")

    @unittest.skipUnless(sys.platform == "win32", "Windows shell required")
    def test_native_shortcut_uses_executable_icon_and_app_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Caméra's app.exe"; target.write_bytes(b"fixture")
            shortcut = root / "CCTVPanelView.lnk"
            create_shortcut(target, shortcut, root, "CCTVPanelView")
            path = str(shortcut).replace("'", "''")
            folder = str(root).replace("'", "''")
            command = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{path}'); "
                       f"$f=(New-Object -ComObject Shell.Application).Namespace('{folder}'); "
                       "@{target=$s.TargetPath;icon=$s.IconLocation;id=$f.ParseName('CCTVPanelView.lnk').ExtendedProperty('System.AppUserModel.ID')} | ConvertTo-Json -Compress")
            result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                capture_output=True, check=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
            value = json.loads(result.stdout.decode("utf-8", errors="replace"))
            self.assertTrue(value["icon"].endswith("app.exe,0"))
            self.assertEqual(value["id"], APP_USER_MODEL_ID)
