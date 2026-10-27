"""Background update checks with explicit download and install actions."""
import os
from pathlib import Path
import threading
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar
from core.updates import check_latest, download_release, version_tuple
from core.version import APP_VERSION


class UpdateManager(QObject):
    checked = pyqtSignal(object)
    downloaded = pyqtSignal(str)
    failed = pyqtSignal(str)
    progress = pyqtSignal(int)
    busy_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.release = None
        self.installer_path = None
        self.busy = False
        self.cancelled = threading.Event()

    def _run(self, work, signal):
        if self.busy: return
        self.busy = True
        self.busy_changed.emit(True)
        def run():
            try:
                result = work()
                if not self.cancelled.is_set(): signal.emit(result)
            except Exception as error:
                if not self.cancelled.is_set():
                    try: self.failed.emit(str(error))
                    except RuntimeError: pass
            finally:
                self.busy = False
                try: self.busy_changed.emit(False)
                except RuntimeError: pass
        threading.Thread(target=run, daemon=True, name="AppUpdate").start()

    def check(self):
        def work():
            release = check_latest()
            self.release = release
            self.installer_path = None
            return release
        self._run(work, self.checked)

    def download(self):
        release = self.release
        if not release or version_tuple(release.version) <= version_tuple(APP_VERSION): return
        def work():
            cache = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CCTVPanelView" / "updates"
            path = download_release(release, cache, progress=self.progress.emit, cancelled=self.cancelled)
            self.installer_path = path
            return path
        self._run(work, self.downloaded)

    def shutdown(self): self.cancelled.set()


class UpdateDialog(QDialog):
    install_requested = pyqtSignal()

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("CCTVPanelView updates")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Installed version: {APP_VERSION}"))
        self.status = QLabel("Check the official GitHub repository for a newer stable version.")
        self.status.setWordWrap(True); layout.addWidget(self.status)
        self.bar = QProgressBar(); self.bar.setRange(0, 100); self.bar.hide(); layout.addWidget(self.bar)
        self.check_button = QPushButton("Check for updates")
        self.download_button = QPushButton("Download verified update")
        self.install_button = QPushButton("Install and restart")
        self.download_button.setEnabled(False); self.install_button.setEnabled(False)
        self.check_button.clicked.connect(manager.check)
        self.download_button.clicked.connect(self._download)
        self.install_button.clicked.connect(self.install_requested.emit)
        for button in (self.check_button, self.download_button, self.install_button): layout.addWidget(button)
        note = QLabel("Checks use GitHub HTTPS. Downloads must match the release's size and SHA-256 digest. Installation saves your layout, closes the app safely, and opens Setup in the current installation folder. These installers are not code-signed.")
        note.setWordWrap(True); layout.addWidget(note)
        manager.checked.connect(self._checked)
        manager.downloaded.connect(self._downloaded)
        manager.failed.connect(self._failed)
        manager.progress.connect(self.bar.setValue)
        manager.busy_changed.connect(self._busy)
        if manager.release: self._checked(manager.release)
        if manager.installer_path: self._downloaded(manager.installer_path)
        self._busy(manager.busy)

    def _checked(self, release):
        newer = version_tuple(release.version) > version_tuple(APP_VERSION)
        self.status.setText(f"Version {release.version} is available." if newer else f"You are up to date. Latest stable release: {release.version}.")
        self.download_button.setEnabled(newer and not self.manager.busy)
        self.install_button.setEnabled(False)

    def _download(self):
        self.status.setText("Downloading from GitHub and verifying the installer…")
        self.bar.setValue(0); self.bar.show(); self.manager.download()

    def _downloaded(self, path):
        self.status.setText("Download verified. Install when you are ready to close the workstation.")
        self.bar.setValue(100); self.install_button.setEnabled(True)

    def _failed(self, message):
        self.status.setText("Update could not complete: " + message)
        self.install_button.setEnabled(False)

    def _busy(self, busy):
        self.check_button.setEnabled(not busy)
        newer = self.manager.release and version_tuple(self.manager.release.version) > version_tuple(APP_VERSION)
        self.download_button.setEnabled(bool(newer) and not busy and not self.manager.installer_path)
        self.install_button.setEnabled(not busy and bool(self.manager.installer_path))
