import sys
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
import os
import threading
import traceback
from datetime import datetime

# Frozen PyInstaller directory handling
if getattr(sys, 'frozen', False):
    EXE_DIR = os.path.dirname(os.path.abspath(sys.executable))
    BUNDLE_DIR = getattr(sys, '_MEIPASS', EXE_DIR)
else:
    EXE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = EXE_DIR

BASE_DIR = BUNDLE_DIR
os.environ["PATH"] = BUNDLE_DIR + os.pathsep + os.environ.get("PATH", "")
os.chdir(EXE_DIR)
if BUNDLE_DIR not in sys.path:
    sys.path.insert(0, BUNDLE_DIR)
if EXE_DIR not in sys.path:
    sys.path.insert(0, EXE_DIR)

# Low-overhead thread and math environment to prevent background CPU spin-waiting & latency spikes
os.environ["OMP_WAIT_POLICY"] = "PASSIVE"
os.environ["KMP_BLOCKTIME"] = "0"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|"
    "stimeout;5000000|"
    "timeout;5000000|"
    "fflags;nobuffer|"
    "flags;low_delay|"
    "max_delay;0|"
    "buffer_size;102400|"
    "threads;1"
)

# Set up logging directories and files in EXE_DIR so they persist across runs
LOGS_DIR = os.path.join(EXE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
CRASH_LOG_PATH = os.path.join(EXE_DIR, "crash.log")
RUNTIME_LOG_PATH = os.path.join(LOGS_DIR, "app_runtime.log")


class DualLogger:
    """Thread-safe stream logger that simultaneously writes to a log file and terminal (if available)."""
    def __init__(self, filename: str, stream=None, max_bytes: int = 10 * 1024 * 1024):
        self.filename = filename
        self.stream = stream
        self.max_bytes = max_bytes
        self._lock = threading.Lock()
        try:
            if os.path.exists(filename) and os.path.getsize(filename) > self.max_bytes:
                bak = filename + ".old"
                if os.path.exists(bak):
                    try:
                        os.remove(bak)
                    except Exception:
                        pass
                os.replace(filename, bak)
        except Exception:
            pass

    def write(self, data):
        if not data:
            return
        if self.stream:
            try:
                self.stream.write(data)
                self.stream.flush()
            except Exception:
                pass
        with self._lock:
            try:
                with open(self.filename, "a", encoding="utf-8", errors="replace") as f:
                    f.write(data)
            except Exception:
                pass

    def flush(self):
        if self.stream:
            try:
                self.stream.flush()
            except Exception:
                pass


def log_crash(trace_str: str, context: str = "Unhandled Exception"):
    """Persist crash trace to crash.log and runtime log without letting the process die."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n{'='*75}\n[{timestamp}] [CRASH INTERCEPTED] [{context}]\n{trace_str}\n{'='*75}\n"
    try:
        with open(CRASH_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass
    try:
        with open(os.path.join(LOGS_DIR, "crash.log"), "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def global_excepthook(exc_type, exc_val, exc_tb):
    """
    Global sys.excepthook.
    In PyQt6, if no custom sys.excepthook is defined, any uncaught exception inside a slot
    causes PyQt6 to call std::abort() or qFatal(), instantly killing the process!
    Installing this hook prevents PyQt6 from aborting, logs the stack trace, and keeps the UI running.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_val, exc_tb)
        return
    trace_str = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
    log_crash(trace_str, context="PyQt6/MainThread")
    print(f"[FATAL TRAP PREVENTED - MAIN THREAD]:\n{trace_str}", file=sys.stderr)


def global_thread_excepthook(args):
    """Global threading.excepthook to intercept unhandled exceptions in background threads."""
    trace_str = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    th_name = getattr(args.thread, "name", "WorkerThread")
    log_crash(trace_str, context=f"Thread: {th_name}")
    print(f"[FATAL TRAP PREVENTED - THREAD {th_name}]:\n{trace_str}", file=sys.stderr)


from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont, QPixmap, QColor, QPainter



_INSTANCE_MUTEX = None


def activate_existing_window():
    """Brings an already running CCTVPanelView window to the foreground."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def enum_windows_callback(hwnd, extra):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                if "CCTVPanelView" in buff.value and user32.IsWindowVisible(hwnd):
                    SW_RESTORE = 9
                    user32.ShowWindow(hwnd, SW_RESTORE)
                    user32.SetForegroundWindow(hwnd)
                    return False
            return True

        user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
    except Exception:
        pass


def check_single_instance() -> bool:
    """Returns True if this is the only instance running, or False if another is already active."""
    global _INSTANCE_MUTEX
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        mutex_name = "Local\\CCTVPanelView_SingleInstance_Mutex"
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        last_error = ctypes.windll.kernel32.GetLastError()
        ERROR_ALREADY_EXISTS = 183
        if last_error == ERROR_ALREADY_EXISTS:
            return False
        _INSTANCE_MUTEX = mutex
        return True
    except Exception:
        return True


def main():
    if "--camera-diagnostics" in sys.argv:
        from core.diagnostics import run_camera_diagnostics
        raise SystemExit(run_camera_diagnostics(sys.argv))
    if "--self-test" in sys.argv:
        from core.diagnostics import run_self_test
        raise SystemExit(run_self_test(sys.argv))
    if "--update-check" in sys.argv:
        from core.diagnostics import run_update_check
        raise SystemExit(run_update_check(sys.argv))
    # Install global exception hooks
    sys.excepthook = global_excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = global_thread_excepthook

    # Redirect stdout and stderr to persistent runtime log
    sys.stdout = DualLogger(RUNTIME_LOG_PATH, sys.stdout)
    sys.stderr = DualLogger(RUNTIME_LOG_PATH, sys.stderr)

    # Single instance guard: bring existing window to front and exit if already running
    if not check_single_instance():
        print("[Startup] CCTVPanelView is already running. Bringing existing window to foreground.")
        activate_existing_window()
        sys.exit(0)

    if "--headless" in sys.argv:
        from cctv_server import main as headless_main
        return headless_main()

    # Enable High DPI scaling
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    # Set Windows AppUserModelID so Windows Taskbar pins and displays the custom app icon
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = "cctvpanelview.studio.ai.cctv.v1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication(sys.argv)
    # Ensure closing the main window quits the application cleanly
    app.setQuitOnLastWindowClosed(True)
    app.setApplicationName("CCTVPanelView")
    app.setOrganizationName("CCTVPanelView")

    # Load high-resolution application icon
    icon_ico = os.path.join(BASE_DIR, "assets", "cctv_logo.ico")
    if not os.path.exists(icon_ico):
        icon_ico = os.path.join(BASE_DIR, "assets", "app_icon.ico")
    icon_png = os.path.join(BASE_DIR, "assets", "app_icon.png")
    icon_path = icon_ico if os.path.exists(icon_ico) else icon_png
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    else:
        app_icon = None

    # Set default clean system font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Paint a lightweight, static loading view before importing/building the
    # workstation. No animation or artificial two-second delay on the GUI thread.
    pixmap = QPixmap(340, 130)
    pixmap.fill(QColor("#0f172a"))
    painter = QPainter(pixmap)
    painter.setPen(QColor("#e2e8f0")); painter.setFont(QFont("Segoe UI", 13))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Starting CCTVPanelView…")
    painter.end()
    splash = QSplashScreen(pixmap)
    splash.show()
    app.processEvents()

    # Check if first-run setup or requested via flags
    from core.device_manager import DeviceManager
    dm = DeviceManager()
    has_completed_onboarding = dm.config.get("app_settings", {}).get("has_completed_onboarding", False)
    cameras = dm.get_cameras()
    force_setup = "--setup" in sys.argv or "--wizard" in sys.argv
    is_demo_setup = "--demo-setup" in sys.argv or "--demo" in sys.argv
    is_fresh_install = (not has_completed_onboarding) and (len(cameras) == 0)

    if force_setup or is_demo_setup or is_fresh_install:
        from PyQt6.QtWidgets import QDialog
        from ui.components.onboarding_wizard import OnboardingWizard
        splash.hide()
        wiz = OnboardingWizard(is_demo=is_demo_setup)
        if app_icon:
            wiz.setWindowIcon(app_icon)
        res = wiz.exec()
        if res != int(QDialog.DialogCode.Accepted) and (force_setup or is_demo_setup):
            sys.exit(0)

    splash.show()
    app.processEvents()
    from ui.main_window import MainWindow
    window = MainWindow()
    if app_icon:
        window.setWindowIcon(app_icon)
    window.show()
    splash.finish(window)
    window.raise_()
    window.activateWindow()

    exit_code = app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
