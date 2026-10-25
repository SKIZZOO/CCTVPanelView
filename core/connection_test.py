"""One cancellable camera test implementation for both configuration dialogs."""
from PyQt6.QtCore import QThread, pyqtSignal
from core.device_manager import DeviceManager

_active_tests = set()  # Keep a closing dialog's QThread alive until cleanup ends.


class ConnectionTestWorker(QThread):
    test_finished = pyqtSignal(bool, str)

    def __init__(self, url, ip="", port=554):
        super().__init__()
        self.url = url
        _active_tests.add(self)
        self.finished.connect(self._finished)

    def _finished(self):
        _active_tests.discard(self)

    def cancel(self):
        self.requestInterruption()

    def run(self):
        try:
            # The URL itself is authoritative. A separate form IP/port probe must
            # not reject a working custom URL before its video is tested.
            result = DeviceManager.test_connection(self.url, cancelled=self.isInterruptionRequested)
            if not self.isInterruptionRequested():
                self.test_finished.emit(bool(result.get("success")),
                                        result.get("message") or result.get("error", "Video was not verified."))
        except Exception:
            if not self.isInterruptionRequested():
                self.test_finished.emit(False, "The video test could not complete. Check the stream URL and try again.")
