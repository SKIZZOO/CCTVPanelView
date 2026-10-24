import os
from typing import List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont


class RetentionCleanupDialog(QDialog):
    """
    Storage Retention Dialog for alerts older than retention period (default 7 days).
    Allows user to review expired alerts and either approve deletion or decline to keep them.
    """
    def __init__(self, expired_alerts: List[Dict[str, Any]], retention_days: int = 7, parent=None):
        super().__init__(parent)
        self.expired_alerts = expired_alerts
        self.retention_days = retention_days
        self.setWindowTitle(f"Storage Retention: Media Older than {retention_days} Days")
        self.resize(620, 480)
        self.setMinimumSize(520, 380)

        self.user_declined = False
        self.snooze_days = 0

        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
                color: #f1f5f9;
            }
            QLabel {
                color: #e2e8f0;
            }
            QFrame#card {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 12px;
            }
            QListWidget {
                background-color: #070b14;
                border: 1px solid #1e293b;
                border-radius: 4px;
                color: #f1f5f9;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #111827;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #1e293b;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QCheckBox {
                color: #94a3b8;
                font-size: 11px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Info Card
        card = QFrame(self)
        card.setObjectName("card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(10, 10, 10, 10)
        c_layout.setSpacing(6)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_title = QLabel("Storage Retention & Cleanup", card)
        lbl_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #38bdf8;")
        
        count = len(self.expired_alerts)
        total_bytes = sum(a.get("total_bytes", 0) for a in self.expired_alerts)
        size_mb = total_bytes / (1024 * 1024)

        lbl_sub = QLabel(f"<b>{count} alert recordings</b> are older than {self.retention_days} days (occupying <b>{size_mb:.1f} MB</b>).", card)
        lbl_sub.setStyleSheet("font-size: 12px; color: #cbd5e1;")
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_sub)
        c_layout.addLayout(title_col)

        lbl_desc = QLabel(
            "To preserve disk space, CCTVPanelView can remove these expired alerts. "
            "You can choose to delete them now or keep them permanently.",
            card
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 11px; margin-top: 4px;")
        c_layout.addWidget(lbl_desc)

        layout.addWidget(card)

        # List of expired alerts
        lbl_list_hdr = QLabel("Alerts eligible for cleanup:", self)
        lbl_list_hdr.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase;")
        layout.addWidget(lbl_list_hdr)

        self.alert_list_widget = QListWidget(self)
        for a in self.expired_alerts:
            cam = a.get("camera_name", "Camera")
            lens = a.get("lens", "Lens1")
            lbl = a.get("label", "Detection").upper()
            ts = a.get("timestamp", "")
            days = a.get("age_days", 30)
            bytes_val = a.get("total_bytes", 0)
            mb_val = bytes_val / (1024 * 1024)

            item_text = f"[ALERT] {lbl}  •  {cam} [{lens}]  •  {ts} ({days} days ago)  •  {mb_val:.1f} MB"
            item = QListWidgetItem(item_text)
            self.alert_list_widget.addItem(item)

        layout.addWidget(self.alert_list_widget, stretch=1)

        # Checkbox: Don't ask again for 7 days
        self.chk_snooze = QCheckBox("Do not remind me again for 7 days if I keep them", self)
        layout.addWidget(self.chk_snooze)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_decline = QPushButton("Keep Alerts (Do Not Delete)", self)
        self.btn_decline.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 8px 18px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2563eb;
                border-color: #3b82f6;
                color: #ffffff;
            }
        """)
        self.btn_decline.clicked.connect(self._on_decline)
        btn_row.addWidget(self.btn_decline)

        btn_row.addStretch()

        self.btn_remove = QPushButton("Delete Expired Records", self)
        self.btn_remove.setStyleSheet("""
            QPushButton {
                background-color: #991b1b;
                color: #ffffff;
                border: 1px solid #ef4444;
                border-radius: 4px;
                padding: 8px 18px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.btn_remove.clicked.connect(self._on_remove)
        btn_row.addWidget(self.btn_remove)

        layout.addLayout(btn_row)

    def _on_decline(self):
        self.user_declined = True
        self.snooze_days = 7 if self.chk_snooze.isChecked() else 0
        self.reject()

    def _on_remove(self):
        self.user_declined = False
        self.accept()
