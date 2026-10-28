"""Persistent, responsive update notice beneath the workstation header."""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton


class UpdateBanner(QFrame):
    review_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("application_update_banner")
        self.setStyleSheet("""
            QFrame#application_update_banner { background: #102a43; border-bottom: 1px solid #38bdf8; }
            QLabel { color: #e0f2fe; background: transparent; border: none; }
            QPushButton { color: #ffffff; background: #0369a1; border: 1px solid #38bdf8;
                          border-radius: 6px; padding: 7px 14px; font-weight: 600; }
            QPushButton:hover { background: #075985; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.button = QPushButton("Review update")
        self.button.clicked.connect(self.review_requested.emit)
        layout.addWidget(self.message, 1)
        layout.addWidget(self.button)
        self.hide()

    def show_release(self, version):
        self.message.setText(f"CCTVPanelView {version} is available. Update when you are ready.")
        self.show()
