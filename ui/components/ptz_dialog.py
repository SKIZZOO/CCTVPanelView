import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QIcon
from ui.components.ptz_pad import PTZPad


class PTZControlDialog(QDialog):
    """
    Modeless floating tool window for PTZ & 2-Way Audio Intercom control.
    Triggered via the 'Control PTZ' button in the top bar.
    Can be positioned freely or pinned while viewing live feeds.
    """
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.WindowCloseButtonHint)
        self.setWindowTitle("Control PTZ & Interfon")
        self.setModal(False)
        self.resize(380, 700)
        self.setMinimumWidth(360)
        self.setMaximumWidth(460)

        # High-tech Obsidian Dark styling
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0e17;
                color: #f1f5f9;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)

        self.ptz_pad = PTZPad(self)
        layout.addWidget(self.ptz_pad)

    def closeEvent(self, event):
        if hasattr(self.parent(), "_on_ptz_dialog_closed"):
            self.parent()._on_ptz_dialog_closed()
        super().closeEvent(event)

    def reject(self):
        self.hide()
        if hasattr(self.parent(), "_on_ptz_dialog_closed"):
            self.parent()._on_ptz_dialog_closed()
