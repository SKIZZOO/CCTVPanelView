"""Animate in a tiny companion process while the workstation GUI initializes."""
import atexit
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def application_icon(bundle_dir):
    from PyQt6.QtGui import QIcon
    for name in ("cctv_logo.ico", "app_icon.ico", "cctvpanelview_logo.png", "app_icon.png"):
        icon = QIcon(str(Path(bundle_dir) / "assets" / name))
        if not icon.isNull():
            return icon
    return QIcon()


class StartupAnimation:
    def __init__(self, source_root):
        self.temp = tempfile.TemporaryDirectory(prefix="cctv-startup-")
        self.control = Path(self.temp.name) / "state"
        command = [sys.executable]
        if not getattr(sys, "frozen", False):
            command.append(str(Path(source_root) / "main.py"))
        command += ["--startup-splash", f"--startup-control={self.control}", f"--startup-parent={os.getpid()}"]
        environment = os.environ.copy()
        environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        try:
            self.process = subprocess.Popen(command, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            self.temp.cleanup()
            raise
        atexit.register(self.close)

    def _signal(self, state):
        if self.process.poll() is None:
            temporary = self.control.with_suffix(".tmp")
            temporary.write_text(state, encoding="ascii")
            os.replace(temporary, self.control)

    def hide(self): self._signal("hide")
    def show(self): self._signal("show")

    def finish(self, window=None):
        # Never wait for animation completion on the main UI thread.
        self._signal("ready")
        from PyQt6.QtCore import QTimer
        self.cleanup_timer = QTimer()
        self.cleanup_timer.setInterval(500)
        def cleanup():
            if self.process.poll() is not None:
                self.cleanup_timer.stop()
                self.temp.cleanup()
        self.cleanup_timer.timeout.connect(cleanup)
        self.cleanup_timer.start()

    def close(self):
        try:
            if self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            pass
        try: self.temp.cleanup()
        except OSError: pass


def parent_alive(pid):
    if os.name == "nt":
        import ctypes as c
        from ctypes import wintypes as w
        kernel = c.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        kernel.OpenProcess.restype = w.HANDLE
        kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        kernel.CloseHandle.argtypes = [w.HANDLE]
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle:
            return c.get_last_error() == 5
        try: return kernel.WaitForSingleObject(handle, 0) == 258
        finally: kernel.CloseHandle(handle)
    try: os.kill(pid, 0); return True
    except OSError: return False


def run_startup_animation(argv, bundle_dir):
    from PyQt6.QtCore import QTimer, Qt
    from PyQt6.QtWidgets import QApplication
    from core.windows_identity import set_process_app_id
    from ui.components.splash_screen import CyberneticSplashScreen
    def option(name):
        return next((arg.split("=", 1)[1] for arg in argv if arg.startswith(name + "=")), None)
    control = Path(option("--startup-control"))
    parent = int(option("--startup-parent"))
    report = option("--startup-report")
    set_process_app_id()
    app = QApplication(argv)
    app.setApplicationName("CCTVPanelView")
    app.setQuitOnLastWindowClosed(False)
    icon = application_icon(bundle_dir)
    app.setWindowIcon(icon)
    splash = CyberneticSplashScreen(wait_for_ready=True)
    splash.setWindowTitle("CCTVPanelView — Starting")
    splash.setWindowIcon(icon)
    splash.finished.connect(app.quit)
    frames = [0]
    splash.timer.timeout.connect(lambda: frames.__setitem__(0, frames[0] + 1))
    splash.show()
    control.with_suffix(".started").write_text("ready", encoding="ascii")
    state = [None]
    monitor = QTimer()
    monitor.setInterval(100)
    def check():
        if not parent_alive(parent):
            app.quit(); return
        try: value = control.read_text(encoding="ascii")[:32]
        except OSError: return
        if value == state[0]: return
        state[0] = value
        if value == "hide": splash.hide()
        elif value == "show": splash.show()
        elif value == "ready": splash.complete()
    monitor.timeout.connect(check)
    monitor.start()
    result = app.exec()
    if report:
        native_icon = None
        if os.name == "nt":
            import ctypes as c
            from ctypes import wintypes as w
            user = c.WinDLL("user32")
            user.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
            user.SendMessageW.restype = c.c_void_p
            native_icon = bool(user.SendMessageW(int(splash.winId()), 0x7f, 1, 0))
        Path(report).write_text(json.dumps({"frames": frames[0], "icon": not icon.isNull(),
            "native_icon": native_icon, "taskbar_window": splash.windowType() == Qt.WindowType.Window}), encoding="utf-8")
    return result
