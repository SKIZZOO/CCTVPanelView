"""
CCTVPanelView - Windows 11 / UniFi Protect Style Modern Settings Center.
Features:
- Left Vertical Sidebar Navigation with clean icons and indicators.
- Right Card-Based Settings Area (SettingCard & SettingRow) with zero stretched void.
- Modern Animated iOS/Windows 11 Toggle Switches instead of square checkboxes.
- Fixed-width right-aligned controls (Comboboxes, Sliders with numeric badges).
- 100% full compatibility with all DeviceManager configuration keys.
"""

import os
import json
import socket
from typing import Dict, Any, List, Optional
from core.connection_test import ConnectionTestWorker
from core.camera_urls import build_rtsp_url, stream_path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton,
    QComboBox, QSlider, QLineEdit, QFileDialog, QScrollArea, QFrame,
    QProgressBar, QStackedWidget, QListWidget, QListWidgetItem,
    QApplication, QMessageBox, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF, QPointF, QThread, QTimer
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QFont, QPen, QBrush, QPainterPath
)


def create_settings_vector_icon(icon_type: str, color: str = "#94a3b8", size: int = 18) -> QIcon:
    """Renders crisp Apple Vision / SF-style vector icons for settings sections."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    fg = QColor(color)
    pen = QPen(fg, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    if icon_type == "appearance":
        path = QPainterPath()
        path.moveTo(size * 0.50, size * 0.12)
        path.cubicTo(size * 0.88, size * 0.12, size * 0.92, size * 0.55, size * 0.78, size * 0.78)
        path.cubicTo(size * 0.72, size * 0.88, size * 0.60, size * 0.75, size * 0.52, size * 0.80)
        path.cubicTo(size * 0.44, size * 0.85, size * 0.45, size * 0.92, size * 0.35, size * 0.90)
        path.cubicTo(size * 0.12, size * 0.86, size * 0.08, size * 0.35, size * 0.50, size * 0.12)
        p.drawPath(path)
        p.drawEllipse(QPointF(size * 0.34, size * 0.38), 1.2, 1.2)
        p.drawEllipse(QPointF(size * 0.52, size * 0.30), 1.2, 1.2)
        p.drawEllipse(QPointF(size * 0.68, size * 0.42), 1.2, 1.2)
        p.drawEllipse(QPointF(size * 0.60, size * 0.65), 1.6, 1.6)
    elif icon_type == "mobile":
        p.drawRoundedRect(QRectF(size * 0.26, size * 0.12, size * 0.48, size * 0.76), 2.5, 2.5)
        p.drawLine(int(size * 0.42), int(size * 0.78), int(size * 0.58), int(size * 0.78))
        p.drawLine(int(size * 0.44), int(size * 0.20), int(size * 0.56), int(size * 0.20))
        p.setBrush(QBrush(fg))
        p.drawEllipse(QPointF(size * 0.80, size * 0.22), 1.8, 1.8)
    elif icon_type == "ai_motion":
        path = QPainterPath()
        path.moveTo(size * 0.50, size * 0.12)
        path.lineTo(size * 0.85, size * 0.25)
        path.quadTo(size * 0.85, size * 0.65, size * 0.50, size * 0.90)
        path.quadTo(size * 0.15, size * 0.65, size * 0.15, size * 0.25)
        path.closeSubpath()
        p.drawPath(path)
        p.drawEllipse(QPointF(size * 0.50, size * 0.48), size * 0.15, size * 0.15)
    elif icon_type == "storage":
        path = QPainterPath()
        path.moveTo(size * 0.22, size * 0.74)
        path.lineTo(size * 0.78, size * 0.74)
        path.quadTo(size * 0.90, size * 0.74, size * 0.88, size * 0.58)
        path.quadTo(size * 0.86, size * 0.44, size * 0.72, size * 0.42)
        path.quadTo(size * 0.68, size * 0.20, size * 0.48, size * 0.20)
        path.quadTo(size * 0.30, size * 0.20, size * 0.26, size * 0.40)
        path.quadTo(size * 0.12, size * 0.44, size * 0.12, size * 0.58)
        path.quadTo(size * 0.12, size * 0.74, size * 0.22, size * 0.74)
        p.drawPath(path)
        p.drawLine(int(size * 0.50), int(size * 0.64), int(size * 0.50), int(size * 0.44))
        p.drawLine(int(size * 0.50), int(size * 0.44), int(size * 0.42), int(size * 0.52))
        p.drawLine(int(size * 0.50), int(size * 0.44), int(size * 0.58), int(size * 0.52))
    elif icon_type == "cameras":
        p.drawRoundedRect(QRectF(size * 0.14, size * 0.26, size * 0.50, size * 0.36), 2, 2)
        path = QPainterPath()
        path.moveTo(size * 0.64, size * 0.34)
        path.lineTo(size * 0.86, size * 0.24)
        path.lineTo(size * 0.86, size * 0.64)
        path.lineTo(size * 0.64, size * 0.54)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(int(size * 0.32), int(size * 0.62), int(size * 0.32), int(size * 0.82))
        p.drawLine(int(size * 0.18), int(size * 0.82), int(size * 0.46), int(size * 0.82))
    elif icon_type == "performance":
        p.drawRoundedRect(QRectF(size * 0.24, size * 0.24, size * 0.52, size * 0.52), 2, 2)
        p.drawRect(QRectF(size * 0.40, size * 0.40, size * 0.20, size * 0.20))
        for off in (size * 0.36, size * 0.64):
            p.drawLine(int(off), int(size * 0.12), int(off), int(size * 0.24))
            p.drawLine(int(off), int(size * 0.76), int(off), int(size * 0.88))
            p.drawLine(int(size * 0.12), int(off), int(size * 0.24), int(off))
            p.drawLine(int(size * 0.76), int(off), int(size * 0.88), int(off))
    elif icon_type == "sound":
        path = QPainterPath()
        path.moveTo(size * 0.16, size * 0.36)
        path.lineTo(size * 0.32, size * 0.36)
        path.lineTo(size * 0.52, size * 0.20)
        path.lineTo(size * 0.52, size * 0.80)
        path.lineTo(size * 0.32, size * 0.64)
        path.lineTo(size * 0.16, size * 0.64)
        path.closeSubpath()
        p.drawPath(path)
        p.drawArc(QRectF(size * 0.48, size * 0.32, size * 0.30, size * 0.36), -45 * 16, 90 * 16)
        p.drawArc(QRectF(size * 0.58, size * 0.22, size * 0.34, size * 0.56), -45 * 16, 90 * 16)
    elif icon_type == "night":
        path = QPainterPath()
        path.moveTo(size * 0.65, size * 0.15)
        path.arcTo(QRectF(size * 0.18, size * 0.15, size * 0.66, size * 0.66), 90, 180)
        path.arcTo(QRectF(size * 0.32, size * 0.20, size * 0.54, size * 0.54), 270, -180)
        path.closeSubpath()
        p.drawPath(path)
        sx, sy = size * 0.74, size * 0.26
        p.drawLine(int(sx - 2), int(sy), int(sx + 2), int(sy))
        p.drawLine(int(sx), int(sy - 2), int(sx), int(sy + 2))
    elif icon_type == "wind":
        path1 = QPainterPath()
        path1.moveTo(size * 0.15, size * 0.32)
        path1.lineTo(size * 0.58, size * 0.32)
        path1.arcTo(QRectF(size * 0.48, size * 0.18, size * 0.24, size * 0.28), -90, 180)
        p.drawPath(path1)

        path2 = QPainterPath()
        path2.moveTo(size * 0.25, size * 0.50)
        path2.lineTo(size * 0.68, size * 0.50)
        path2.arcTo(QRectF(size * 0.58, size * 0.36, size * 0.24, size * 0.28), -90, 180)
        p.drawPath(path2)

        p.drawLine(int(size * 0.15), int(size * 0.68), int(size * 0.65), int(size * 0.68))
    elif icon_type in ("warning", "alert"):
        path = QPainterPath()
        path.moveTo(size * 0.50, size * 0.12)
        path.lineTo(size * 0.90, size * 0.85)
        path.lineTo(size * 0.10, size * 0.85)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(int(size * 0.50), int(size * 0.38), int(size * 0.50), int(size * 0.58))
        p.drawEllipse(QPointF(size * 0.50, size * 0.72), 1.2, 1.2)

    p.end()
    return QIcon(pix)

from core.sound_manager import get_sound_manager, SoundProfile
from core.camera_stream import NightVisionMode, QualityMode
from core.resource_manager import get_resource_manager, PerformanceProfile, PROFILE_DEFAULTS
from ui.styles import AVAILABLE_THEMES, get_theme_qss
from ui.components.zone_editor_dialog import ZoneEditorDialog
from ui.components.toggle_switch import ToggleSwitch
from ui.components.device_dialog import create_dialog_icon


AsyncSettingsConnectionTester = ConnectionTestWorker


class CameraSetupPromptDialog(QDialog):
    """
    Modern Obsidian Glass prompt dialog displayed when the user attempts
    to stream or assign an unconfigured / unauthenticated camera.
    Provides clear guidance and 1-click navigation to Camera Settings.
    """
    def __init__(self, camera_name: str = "Camera", parent=None):
        super().__init__(parent)
        self.camera_name = camera_name
        self.setWindowTitle("Camera Setup Required")
        self.setFixedSize(470, 230)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 12px;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)

        # Header with icon and descriptive text
        h_box = QHBoxLayout()
        h_box.setSpacing(14)

        icon_lbl = QLabel(self)
        icon_lbl.setPixmap(create_settings_vector_icon("cameras", color="#38bdf8", size=32).pixmap(32, 32))
        h_box.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignTop)

        text_box = QVBoxLayout()
        text_box.setSpacing(6)
        lbl_title = QLabel("Camera Setup Required", self)
        lbl_title.setStyleSheet("color: #f8fafc; font-weight: 700; font-size: 15px; font-family: 'Segoe UI', sans-serif;")
        text_box.addWidget(lbl_title)

        lbl_desc = QLabel(
            f"<b>{self.camera_name}</b> has not been configured yet.<br>"
            "Security credentials (password) and connection parameters must be set before this camera can stream in the grid.",
            self
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4; font-family: 'Segoe UI', sans-serif;")
        text_box.addWidget(lbl_desc)

        h_box.addLayout(text_box, 1)
        layout.addLayout(h_box)

        layout.addStretch(1)

        # Action Buttons
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedHeight(34)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                color: #94a3b8;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 7px;
                padding: 6px 18px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                color: #f1f5f9;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(btn_cancel)

        btn_bar.addStretch(1)

        btn_setup = QPushButton("Open Camera Settings", self)
        btn_setup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_setup.setFixedHeight(34)
        btn_setup.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #2563eb);
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 7px;
                padding: 6px 20px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #1d4ed8);
            }
        """)
        btn_setup.clicked.connect(self.accept)
        btn_bar.addWidget(btn_setup)

        layout.addLayout(btn_bar)


CYBER_SETTINGS_WIDGET_STYLE = """
    /* Cyber Dark ComboBox */
    QComboBox {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #090e1a, stop:1 #111a2e);
        border: 1px solid rgba(56, 189, 248, 0.35);
        border-radius: 8px;
        padding: 4px 12px;
        font-size: 12.5px;
        font-weight: 600;
        color: #f8fafc;
        min-height: 24px;
    }
    QComboBox:hover {
        border: 1px solid #38bdf8;
        background: #14223d;
    }
    QComboBox:focus {
        border: 1px solid #38bdf8;
        background: #14223d;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 26px;
        border-left: 1px solid rgba(56, 189, 248, 0.2);
        border-top-right-radius: 8px;
        border-bottom-right-radius: 8px;
        background: rgba(56, 189, 248, 0.05);
    }
    QComboBox::drop-down:hover {
        background: rgba(56, 189, 248, 0.15);
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid #38bdf8;
        width: 0;
        height: 0;
    }
    QComboBox QAbstractItemView {
        background-color: #0b1120;
        border: 1px solid #38bdf8;
        border-radius: 8px;
        selection-background-color: rgba(56, 189, 248, 0.25);
        selection-color: #ffffff;
        color: #e2e8f0;
        padding: 6px;
        outline: none;
    }
    QComboBox QAbstractItemView::item {
        min-height: 30px;
        padding: 6px 12px;
        margin: 2px 0px;
        border-radius: 6px;
    }
    QComboBox QAbstractItemView::item:hover {
        background-color: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
    }
    QComboBox QAbstractItemView::item:selected {
        background-color: rgba(56, 189, 248, 0.25);
        color: #ffffff;
        font-weight: bold;
    }

    /* Cyber Dark LineEdit */
    QLineEdit {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #090e1a, stop:1 #111a2e);
        border: 1px solid rgba(56, 189, 248, 0.35);
        border-radius: 8px;
        padding: 4px 12px;
        font-size: 12.5px;
        color: #f8fafc;
        selection-background-color: #0284c7;
        selection-color: #ffffff;
        min-height: 24px;
    }
    QLineEdit:hover {
        border: 1px solid #38bdf8;
        background: #14223d;
    }
    QLineEdit:focus {
        border: 1px solid #38bdf8;
        background: #14223d;
    }

    /* Cyber Dark SpinBox */
    QSpinBox {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #090e1a, stop:1 #111a2e);
        border: 1px solid rgba(56, 189, 248, 0.35);
        border-radius: 8px;
        padding: 4px 8px;
        font-size: 12.5px;
        font-weight: 600;
        color: #f8fafc;
        min-height: 24px;
    }
    QSpinBox:hover, QSpinBox:focus {
        border: 1px solid #38bdf8;
        background: #14223d;
    }
    QSpinBox::up-button, QSpinBox::down-button {
        width: 20px;
        background: rgba(56, 189, 248, 0.08);
        border: none;
        border-left: 1px solid rgba(56, 189, 248, 0.2);
    }
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
        background: rgba(56, 189, 248, 0.2);
    }
    QSpinBox::up-arrow {
        image: none;
        border-left: 3px solid transparent;
        border-right: 3px solid transparent;
        border-bottom: 4px solid #38bdf8;
        width: 0;
        height: 0;
    }
    QSpinBox::down-arrow {
        image: none;
        border-left: 3px solid transparent;
        border-right: 3px solid transparent;
        border-top: 4px solid #38bdf8;
        width: 0;
        height: 0;
    }

    /* Cyber Dark Secondary Buttons */
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0b1528, stop:1 #132342);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.40);
        border-radius: 8px;
        padding: 5px 14px;
        font-size: 12px;
        font-weight: 700;
        min-height: 24px;
    }
    QPushButton:hover {
        background: #0284c7;
        color: #ffffff;
        border-color: #38bdf8;
    }
    QPushButton:pressed {
        background: #0369a1;
    }
    QPushButton:disabled {
        background: rgba(30, 41, 59, 0.4);
        color: #64748b;
        border-color: rgba(255, 255, 255, 0.08);
    }

    /* Cyber Dark Sliders */
    QSlider::groove:horizontal {
        height: 6px;
        background: #1e293b;
        border-radius: 3px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    QSlider::sub-page:horizontal {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8);
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #f8fafc;
        border: 2px solid #38bdf8;
        width: 14px;
        margin-top: -5px;
        margin-bottom: -5px;
        border-radius: 7px;
    }
    QSlider::handle:horizontal:hover {
        background: #38bdf8;
        border-color: #ffffff;
    }
"""


class SettingCard(QFrame):
    """Clean rounded card container (Windows 11 / UniFi Protect aesthetic)."""
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            SettingCard {{
                background-color: #17181f;
                border: 1px solid #282a35;
                border-radius: 10px;
            }}
            {CYBER_SETTINGS_WIDGET_STYLE}
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(12)

        if title:
            lbl_title = QLabel(title, self)
            lbl_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #f3f4f6; background: transparent;")
            self.layout.addWidget(lbl_title)
        if subtitle:
            lbl_sub = QLabel(subtitle, self)
            lbl_sub.setWordWrap(True)
            lbl_sub.setStyleSheet("font-size: 11px; color: #9ca3af; background: transparent; margin-bottom: 2px;")
            self.layout.addWidget(lbl_sub)

    def add_row(self, row: QWidget):
        self.layout.addWidget(row)


class SettingRow(QFrame):
    """
    Two-column row:
    - Left: Title (bold) + Subtitle description (muted)
    - Right: Control widget (fixed-width ToggleSwitch, QComboBox, Slider, etc.)
    """
    def __init__(self, title: str, description: str = "", control: Optional[QWidget] = None, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            SettingRow {
                background: transparent;
                border: none;
                border-bottom: 1px solid #22242e;
                padding-bottom: 8px;
                margin-top: 2px;
            }
        """)
        h_layout = QHBoxLayout(self)
        h_layout.setContentsMargins(0, 4, 0, 6)
        h_layout.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        lbl_title = QLabel(title, self)
        lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #e2e8f0; background: transparent;")
        text_col.addWidget(lbl_title)

        if description:
            lbl_desc = QLabel(description, self)
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("font-size: 11px; color: #94a3b8; background: transparent;")
            text_col.addWidget(lbl_desc)

        h_layout.addLayout(text_col, stretch=1)

        if control:
            h_layout.addWidget(control, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


class UnsavedChangesPromptDialog(QDialog):
    """
    Modern Obsidian Glass prompt dialog displayed when the user attempts
    to close Settings with unsaved modifications.
    Allows user to Save Changes, Discard, or Cancel (stay in settings).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_action = "cancel"  # "save", "discard", "cancel"
        self.setWindowTitle("Unsaved Changes")
        self.setFixedSize(490, 215)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 12px;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)

        # Header with warning icon and descriptive text
        h_box = QHBoxLayout()
        h_box.setSpacing(14)

        icon_lbl = QLabel(self)
        icon_lbl.setPixmap(create_settings_vector_icon("warning", color="#f59e0b", size=32).pixmap(32, 32))
        h_box.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignTop)

        text_box = QVBoxLayout()
        text_box.setSpacing(6)
        lbl_title = QLabel("Unsaved Changes", self)
        lbl_title.setStyleSheet("color: #f8fafc; font-weight: 700; font-size: 15px; font-family: 'Segoe UI', sans-serif;")
        text_box.addWidget(lbl_title)

        lbl_desc = QLabel(
            "You have modified settings that have not been saved yet.<br>"
            "Would you like to save your changes before exiting?",
            self
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4; font-family: 'Segoe UI', sans-serif;")
        text_box.addWidget(lbl_desc)

        h_box.addLayout(text_box, 1)
        layout.addLayout(h_box)

        layout.addStretch(1)

        # Action Buttons: Discard Changes, Cancel, Save Changes
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        btn_discard = QPushButton("Discard Changes", self)
        btn_discard.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_discard.setFixedHeight(34)
        btn_discard.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.15);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.40);
                border-radius: 7px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.30);
                color: #ffffff;
                border-color: #ef4444;
            }
        """)
        btn_discard.clicked.connect(self._on_discard)
        btn_bar.addWidget(btn_discard)

        btn_bar.addStretch(1)

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedHeight(34)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                color: #94a3b8;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 7px;
                padding: 6px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                color: #f1f5f9;
            }
        """)
        btn_cancel.clicked.connect(self._on_cancel)
        btn_bar.addWidget(btn_cancel)

        btn_save = QPushButton("Save Changes", self)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setFixedHeight(34)
        btn_save.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #2563eb);
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 7px;
                padding: 6px 18px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #1d4ed8);
                border-color: #7dd3fc;
            }
        """)
        btn_save.clicked.connect(self._on_save)
        btn_bar.addWidget(btn_save)

        layout.addLayout(btn_bar)

    def _on_save(self):
        self.user_action = "save"
        self.accept()

    def _on_discard(self):
        self.user_action = "discard"
        self.accept()

    def _on_cancel(self):
        self.user_action = "cancel"
        self.reject()


class SettingsDialog(QDialog):
    """
    Modern Settings Window for CCTVPanelView.
    - Left Sidebar (Windows 11 Navigation)
    - Right Stacked Cards with aerated rows and toggle switches.
    """
    settings_saved = pyqtSignal(dict)
    check_updates_requested = pyqtSignal()
    ntfy_test_finished = pyqtSignal(bool, str)
    camera_connection_updated = pyqtSignal(dict)

    def __init__(self, current_settings=None, cameras=None, selected_camera_id=None, parent=None):
        super().__init__(parent)
        self.settings = dict(current_settings or {})
        self.cameras = list(cameras or [])
        self.selected_camera_id = selected_camera_id
        self.camera_overrides = {}
        self.sound_manager = get_sound_manager()
        self.test_worker: Optional[AsyncSettingsConnectionTester] = None

        # Cache existing per-camera settings and guarantee default username "admin"
        for c in self.cameras:
            cid = c.get("id")
            if cid:
                self.camera_overrides[cid] = dict(c.get("settings", {}))
            if not c.get("username"):
                c["username"] = "admin"

        self.setWindowTitle("Settings - CCTVPanelView")
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(960, 680)
        self.setMinimumSize(820, 560)
        self._setup_ui()

        self.ntfy_test_finished.connect(self._show_ntfy_test_result)
        self._initial_state = self._capture_current_dialog_state()

    def _create_masked_input(self, placeholder: str = "", text: str = "", width: Optional[int] = None, on_text_changed=None):
        """Creates a masked password/credential input field equipped with an interactive eye reveal toggle."""
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        txt = QLineEdit(container)
        txt.setEchoMode(QLineEdit.EchoMode.Password)
        txt.setPlaceholderText(placeholder)
        txt.setFixedHeight(32)
        if text:
            txt.setText(text)
        if width:
            txt.setFixedWidth(width)
        if on_text_changed:
            txt.textChanged.connect(on_text_changed)

        btn_eye = QPushButton(container)
        btn_eye.setFixedSize(32, 32)
        btn_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye.setToolTip("Show / Hide sensitive content")
        btn_eye.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #090e1a, stop:1 #111a2e);
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 8px;
                padding: 0px;
            }
            QPushButton:hover {
                background: #14223d;
                border-color: #38bdf8;
            }
        """)
        eye_box = QVBoxLayout(btn_eye)
        eye_box.setContentsMargins(0, 0, 0, 0)
        eye_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_eye = QLabel(btn_eye)
        lbl_eye.setPixmap(create_dialog_icon("eye", color="#94a3b8", size=14))
        lbl_eye.setStyleSheet("background: transparent; border: none;")
        eye_box.addWidget(lbl_eye)

        def _toggle():
            if txt.echoMode() == QLineEdit.EchoMode.Password:
                txt.setEchoMode(QLineEdit.EchoMode.Normal)
                lbl_eye.setPixmap(create_dialog_icon("eye_slash", color="#38bdf8", size=14))
                btn_eye.setToolTip("Hide sensitive content")
            else:
                txt.setEchoMode(QLineEdit.EchoMode.Password)
                lbl_eye.setPixmap(create_dialog_icon("eye", color="#94a3b8", size=14))
                btn_eye.setToolTip("Show sensitive content")

        btn_eye.clicked.connect(_toggle)
        lay.addWidget(txt, stretch=1)
        lay.addWidget(btn_eye)
        return container, txt, btn_eye

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Header Bar
        header = QFrame(self)
        header.setStyleSheet("background-color: #14151a; border-bottom: 1px solid #282a35;")
        header.setFixedHeight(64)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(22, 12, 22, 12)

        icon_png = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.png")
        if os.path.exists(icon_png):
            lbl_logo = QLabel(header)
            lbl_logo.setPixmap(QPixmap(icon_png).scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            lbl_logo.setFixedSize(30, 30)
            lbl_logo.setStyleSheet("background: transparent; margin-right: 6px;")
            h_layout.addWidget(lbl_logo)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("Application Settings", header)
        title.setStyleSheet("font-size: 15px; font-weight: 800; color: #f3f4f6; background: transparent;")
        subtitle = QLabel("Customize appearance, alerts, AI detection, and CCTV storage", header)
        subtitle.setStyleSheet("font-size: 11px; color: #9ca3af; background: transparent;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        h_layout.addLayout(title_box)

        h_layout.addStretch(1)

        btn_cancel = QPushButton("Cancel", header)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #0f172a;
                color: #94a3b8;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 7px 18px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #f8fafc;
                border-color: #334155;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        h_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save && Apply", header)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #2563eb);
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 7px 20px;
                font-weight: 800;
                font-size: 12px;
                letter-spacing: 0.4px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #1d4ed8);
                border-color: #7dd3fc;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)
        btn_save.clicked.connect(self._save_settings)
        h_layout.addWidget(btn_save)

        root_layout.addWidget(header)

        # 2. Main Body Split: Left Sidebar + Right Pages Stack
        body = QWidget(self)
        body.setStyleSheet("background-color: #101114;")
        b_layout = QHBoxLayout(body)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(0)

        # Left Sidebar (QListWidget)
        self.sidebar = QListWidget(body)
        self.sidebar.setObjectName("settings_sidebar")
        self.sidebar.setFixedWidth(230)
        self.sidebar.setIconSize(QSize(18, 18))
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar.setStyleSheet("""
            QListWidget#settings_sidebar {
                background-color: #101114;
                border: none;
                border-right: 1px solid #232530;
                outline: none;
                padding: 14px 8px 10px 8px;
            }
            QListWidget#settings_sidebar::item {
                color: #94a3b8;
                font-weight: 600;
                font-size: 12px;
                padding: 10px 14px;
                border-radius: 8px;
                margin-bottom: 4px;
                border: 1px solid transparent;
            }
            QListWidget#settings_sidebar::item:hover:!selected {
                background-color: rgba(255, 255, 255, 0.05);
                color: #f1f5f9;
            }
            QListWidget#settings_sidebar::item:selected {
                background-color: rgba(56, 189, 248, 0.14);
                border: 1px solid rgba(56, 189, 248, 0.40);
                color: #ffffff;
                font-weight: 700;
            }
        """)

        nav_items = [
            (" General & layout", "appearance"),
            (" Alerts & sounds", "mobile"),
            (" Detection", "ai_motion"),
            (" Recording & storage", "storage"),
            (" Cameras & image", "cameras"),
            (" PC Performance", "performance"),
            (" Sounds & Alarms", "sound"),
            (" Night Mode & Contrast", "night"),
            (" Wind Stabilization Filter", "wind")
        ]

        for text, icon_type in nav_items:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, icon_type)
            item.setIcon(create_settings_vector_icon(icon_type, color="#94a3b8", size=18))
            self.sidebar.addItem(item)

        b_layout.addWidget(self.sidebar)

        # Right Stacked Widget
        self.stack = QStackedWidget(body)
        self.stack.setStyleSheet(CYBER_SETTINGS_WIDGET_STYLE)
        b_layout.addWidget(self.stack, stretch=1)

        root_layout.addWidget(body)

        # Populate pages
        self._build_tab_appearance()     # Index 0
        self._build_tab_notifications()  # Index 1
        self._build_tab_ai_motion()      # Index 2
        self._build_tab_storage()        # Index 3
        self._build_tab_cameras()        # Index 4
        self._build_tab_performance()    # Index 5
        self._build_tab_sound()          # Index 6
        self._build_tab_night()          # Index 7
        self._build_tab_wind()           # Index 8

        # Incident creation and outgoing delivery are different choices.
        detection_layout = self.stack.widget(2).widget().layout()
        detection_layout.insertWidget(0, self.incident_category_card)

        # Keep related controls on the same page, preserving the first six page
        # indexes used by existing shortcuts and deep links.
        for source_index, destination in ((6, 1), (7, 4), (8, 2)):
            source_layout = self.stack.widget(source_index).widget().layout()
            destination_layout = self.stack.widget(destination).widget().layout()
            while source_layout.count():
                item = source_layout.takeAt(0)
                if item.widget():
                    destination_layout.insertWidget(max(0, destination_layout.count() - 1), item.widget())
        while self.stack.count() > 6:
            page = self.stack.widget(6)
            self.stack.removeWidget(page)
            page.deleteLater()
        while self.sidebar.count() > 6:
            self.sidebar.takeItem(6)
        self.settings_search = QLineEdit()
        self.settings_search.setStyleSheet("QLineEdit { background: #111827; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; min-height: 20px; }")
        self.settings_search.setPlaceholderText("Find a setting: volume, camera, retention, detection…")
        self.settings_search.textChanged.connect(self._search_settings)
        root_layout.insertWidget(1, self.settings_search)
        self.settings_search_feedback = QLabel("No matching settings. Try a shorter search.")
        self.settings_search_feedback.setVisible(False)
        root_layout.insertWidget(2, self.settings_search_feedback)

        # Sync sidebar selection with stacked widget and dynamic active icon color
        self.sidebar.currentRowChanged.connect(self._on_sidebar_row_changed)
        self.sidebar.setCurrentRow(0)

    def _search_settings(self, text):
        query = text.strip().casefold()
        first = None
        for index in range(self.stack.count()):
            page = self.stack.widget(index)
            labels = " ".join(label.text() for label in page.findChildren(QLabel)).casefold()
            match = not query or query in labels or query in self.sidebar.item(index).text().casefold()
            self.sidebar.item(index).setHidden(not match)
            if match and first is None:
                first = index
        self.settings_search_feedback.setVisible(first is None)
        self.stack.setVisible(first is not None)
        if first is not None and self.sidebar.item(self.sidebar.currentRow()).isHidden():
            self.sidebar.setCurrentRow(first)

    def _on_sidebar_row_changed(self, row: int):
        self.stack.setCurrentIndex(row)
        for i in range(self.sidebar.count()):
            it = self.sidebar.item(i)
            tag = it.data(Qt.ItemDataRole.UserRole)
            if tag:
                col = "#38bdf8" if i == row else "#94a3b8"
                it.setIcon(create_settings_vector_icon(tag, color=col, size=18))

    def _create_scrollable_page(self) -> tuple[QScrollArea, QVBoxLayout]:
        """Creates a smooth scroll area and returns the layout container."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        scroll.setWidget(container)
        return scroll, layout

    # -------------------------------------------------------------
    #  TAB 0: APPEARANCE & THEMES
    # -------------------------------------------------------------
    def _build_tab_appearance(self):
        scroll, layout = self._create_scrollable_page()

        card_layout = SettingCard("Startup Camera Grid Layout", "Select the default window grid arrangement when launching the application")

        self.cmb_layout = QComboBox()
        self.cmb_layout.setFixedWidth(210)
        self.cmb_layout.setFixedHeight(32)
        for label, key in [("Single camera", "1x1"), ("Two side by side", "2x1"),
                           ("Two stacked", "1x2"), ("Four cameras", "2x2"),
                           ("One large + five", "1+5"), ("Nine cameras", "3x3"),
                           ("Sixteen cameras", "4x4"), ("Custom layout", "custom")]:
            self.cmb_layout.addItem(label, key)
        idx = self.cmb_layout.findData(self.settings.get("default_layout", "2x2"))
        if idx >= 0:
            self.cmb_layout.setCurrentIndex(idx)
        card_layout.add_row(SettingRow("Startup Grid Layout", "Window arrangement when launching the application", self.cmb_layout))

        layout.addWidget(card_layout)

        card_hud = SettingCard("Video HUD Overlays", "Choose telemetry elements displayed over camera streams")

        self.sw_hud_clock = ToggleSwitch(checked=self.settings.get("show_hud_clock", False))
        card_hud.add_row(SettingRow("Clock & Date", "Display digital timestamp in the upper corner of the video", self.sw_hud_clock))

        self.sw_hud_cam_name = ToggleSwitch(checked=self.settings.get("show_hud_camera_name", False))
        card_hud.add_row(SettingRow("Camera & Lens Name", "Display camera label on screen", self.sw_hud_cam_name))

        self.sw_hud_wifi = ToggleSwitch(checked=self.settings.get("show_hud_wifi", True))
        card_hud.add_row(SettingRow("Wi-Fi / Network Signal", "Monitor wireless connection signal strength on each camera", self.sw_hud_wifi))

        layout.addWidget(card_hud)

        card_close = SettingCard("Workstation Window & Exit Behavior", "Control what happens when pressing the window Close (X) button")

        self.cmb_close_action = QComboBox()
        self.cmb_close_action.setFixedWidth(250)
        self.cmb_close_action.setFixedHeight(32)
        self.cmb_close_action.addItem("Always ask me what to do", "ask")
        self.cmb_close_action.addItem("Hide in System Tray (Keep recording 24/7)", "tray")
        self.cmb_close_action.addItem("Quit application completely", "quit")

        remember = bool(self.settings.get("remember_close_action", False))
        curr_action = self.settings.get("close_action", "ask")
        if not remember:
            self.cmb_close_action.setCurrentIndex(0)
        else:
            idx = self.cmb_close_action.findData(curr_action)
            if idx >= 0:
                self.cmb_close_action.setCurrentIndex(idx)
            else:
                self.cmb_close_action.setCurrentIndex(0)

        card_close.add_row(SettingRow("Close (X) Button Action", "Specify whether closing the window prompts, minimizes to tray, or exits", self.cmb_close_action))
        layout.addWidget(card_close)

        card_wizard = SettingCard("First-Run & Setup Wizard", "Re-run the interactive workstation setup wizard to configure storage, CPU profiling, and cameras")
        btn_wizard = QPushButton("Launch Setup Wizard")
        btn_wizard.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_wizard.setFixedWidth(180)
        btn_wizard.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        btn_wizard.clicked.connect(self._launch_setup_wizard)
        card_wizard.add_row(SettingRow("Initial Setup Wizard", "Guided 5-stage setup: storage drive selection, hardware profile, network camera scan, and preferences", btn_wizard))
        layout.addWidget(card_wizard)

        from core.version import APP_VERSION
        updates_card = SettingCard("Application updates", f"Installed version {APP_VERSION}. Check the official GitHub stable release and verify installer downloads.")
        self.sw_auto_updates = ToggleSwitch(checked=self.settings.get("auto_check_updates", True))
        updates_card.add_row(SettingRow("Automatically check for updates", "Checks in the background after startup and every six hours. Downloads and installation wait for your action.", self.sw_auto_updates))
        self.btn_check_updates = QPushButton("Check for updates…")
        self.btn_check_updates.clicked.connect(self.check_updates_requested.emit)
        updates_card.add_row(SettingRow("Download and install", "Save your layout and update the existing installation folder.", self.btn_check_updates))
        layout.addWidget(updates_card)

        layout.addStretch(1)
        self.stack.addWidget(scroll)

    def _launch_setup_wizard(self):
        from ui.components.onboarding_wizard import OnboardingWizard
        wiz = OnboardingWizard(is_demo=False, parent=self)
        wiz.exec()

    def _on_theme_changed(self, theme_name: str):
        if hasattr(self, "sw_live_preview") and self.sw_live_preview.isChecked():
            app = QApplication.instance()
            if app:
                app.setStyleSheet(get_theme_qss(theme_name))

    # -------------------------------------------------------------
    #  TAB 1: MOBILE NOTIFICATIONS
    # -------------------------------------------------------------
    def _build_tab_notifications(self):
        scroll, layout = self._create_scrollable_page()

        card_security = SettingCard("Master Security & Incident Alerts", "Arm or disarm all security alerts and notifications across desktop, alarms, and mobile in one switch")
        self.sw_master_alerts = ToggleSwitch(checked=self.settings.get("master_alerts_enabled", True), active_color="#10b981")
        self.sw_master_alerts.toggled.connect(self._on_master_alerts_toggled)
        card_security.add_row(SettingRow("Arm Security System", "Activate AI object recognition, motion alarms, desktop banners, and incident recordings", self.sw_master_alerts))

        btn_optimal = QPushButton("Apply Recommended Alert Settings")
        btn_optimal.setFixedHeight(32)
        btn_optimal.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_optimal.setToolTip("One-click optimal security setup (AI Persons, Vehicles, Animals, Motion, Desktop Toasts & Sirens)")
        btn_optimal.clicked.connect(self._apply_recommended_alert_settings)
        card_security.add_row(SettingRow("One-Click Recommended Security", "Automatically configure proven detection and alert parameters", btn_optimal))

        layout.addWidget(card_security)

        card_master = SettingCard("Master Mobile Notification Switch", "Globally enable or pause all notifications to mobile devices")
        self.sw_phone_enabled = ToggleSwitch(checked=self.settings.get("phone_notifications_enabled", False), active_color="#0284c7")
        card_master.add_row(SettingRow("Enable Mobile Push Alerts", "Broadcast instant photos, detections, and 10s video clips to your smartphone", self.sw_phone_enabled))
        layout.addWidget(card_master)

        card_filter = SettingCard("Create incident alerts", "Choose categories that create local incidents, alarm clips and desktop alerts")
        self.incident_category_card = card_filter

        self.sw_notify_person = ToggleSwitch(checked=self.settings.get("notify_person", False), active_color="#0284c7")
        card_filter.add_row(SettingRow("People", "Create an incident when a person is detected", self.sw_notify_person))

        self.sw_notify_vehicle = ToggleSwitch(checked=self.settings.get("notify_vehicle", False))
        card_filter.add_row(SettingRow("Vehicles", "Cars, vans, motorcycles, or bicycles", self.sw_notify_vehicle))

        self.sw_notify_animal = ToggleSwitch(checked=self.settings.get("notify_animal", False))
        card_filter.add_row(SettingRow("Animals & Pets", "Dogs, cats, birds, or farm animals", self.sw_notify_animal))

        self.sw_notify_motion = ToggleSwitch(checked=self.settings.get("notify_motion", False))
        card_filter.add_row(SettingRow("General Motion", "Create incidents for confirmed motion without an identified object", self.sw_notify_motion))

        layout.addWidget(card_filter)

        from core.notification_policy import CATEGORY_LABELS, notification_categories
        outgoing = SettingCard("Send notifications for", "Applies to ntfy, Telegram and Discord photos and clips. Recording and the incident feed keep their own settings.")
        selected = notification_categories(self.settings)
        self.outgoing_category_switches = {}
        for category, label in CATEGORY_LABELS.items():
            switch = ToggleSwitch(checked=category in selected)
            self.outgoing_category_switches[category] = switch
            outgoing.add_row(SettingRow(label, "Send outgoing notifications for this detection category", switch))
        self.btn_people_only = QPushButton("People only")
        self.btn_people_only.setFixedHeight(32)
        self.btn_people_only.clicked.connect(self._select_people_only_notifications)
        outgoing.add_row(SettingRow("People-only preset", "Requires AI person detection and People incidents enabled under Detection. Does not enable a delivery service.", self.btn_people_only))
        layout.addWidget(outgoing)

        card_mobile = SettingCard("Mobile Push Services (ntfy.sh & Telegram)", "Free instant push notifications with captured snapshots and AI visual descriptions")

        self.sw_ntfy_enabled = ToggleSwitch(checked=self.settings.get("ntfy_enabled", False))
        card_mobile.add_row(SettingRow("Enable Mobile Push (ntfy.sh)", "Free iOS & Android app without mandatory account", self.sw_ntfy_enabled))

        topic_frame = QWidget()
        tf_layout = QHBoxLayout(topic_frame)
        tf_layout.setContentsMargins(0, 0, 0, 0)
        tf_layout.setSpacing(8)
        self.txt_ntfy_topic = QLineEdit()
        self.txt_ntfy_topic.setFixedWidth(180)
        self.txt_ntfy_topic.setFixedHeight(32)
        self.txt_ntfy_topic.setPlaceholderText("Leave blank or set topic")
        self.txt_ntfy_topic.setText(self.settings.get("ntfy_topic", ""))
        tf_layout.addWidget(self.txt_ntfy_topic)
        btn_gen_topic = QPushButton("New Topic")
        btn_gen_topic.setFixedHeight(32)
        btn_gen_topic.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gen_topic.setToolTip("Generate an unguessable secret topic channel")
        btn_gen_topic.clicked.connect(self._generate_secret_ntfy_topic)
        tf_layout.addWidget(btn_gen_topic)
        card_mobile.add_row(SettingRow("ntfy Topic (Secret Channel)", "Topic name subscribed in your ntfy mobile app", topic_frame))

        self.btn_ntfy_test = QPushButton("Send text-only test")
        self.btn_ntfy_test.setFixedHeight(32)
        self.btn_ntfy_test.clicked.connect(self._test_ntfy_delivery)
        self.lbl_ntfy_test = QLabel("Uses the topic above. No camera images or video are sent by this test.")
        self.lbl_ntfy_test.setWordWrap(True)
        self.lbl_ntfy_test.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 8px 0;")
        card_mobile.add_row(SettingRow("Test ntfy delivery", "Checks these current settings without waiting for a detection.", self.btn_ntfy_test))
        card_mobile.add_row(self.lbl_ntfy_test)

        self.sw_send_video = ToggleSwitch(checked=self.settings.get("phone_notify_video", self.settings.get("send_video_to_phone", False)))
        card_mobile.add_row(SettingRow("Send Video Clip to Phone", "Include recorded MP4 clip (pre + post alarm)", self.sw_send_video))

        self.sw_telegram_enabled = ToggleSwitch(checked=self.settings.get("telegram_enabled", False))
        card_mobile.add_row(SettingRow("Enable Telegram Bot Alerts", "Send photos and clips directly to your Telegram chat or channel", self.sw_telegram_enabled))

        self.txt_tg_token = QLineEdit()
        self.txt_tg_token.setFixedWidth(220)
        self.txt_tg_token.setFixedHeight(32)
        self.txt_tg_token.setPlaceholderText("123456:ABC-DEF...")
        self.txt_tg_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_tg_token.setText(self.settings.get("telegram_token", self.settings.get("telegram_bot_token", "")))
        card_mobile.add_row(SettingRow("Telegram Bot Token", "Bot token obtained from @BotFather", self.txt_tg_token))

        self.txt_tg_chat = QLineEdit()
        self.txt_tg_chat.setFixedWidth(220)
        self.txt_tg_chat.setFixedHeight(32)
        self.txt_tg_chat.setPlaceholderText("-100xxxxxxx or Chat ID")
        self.txt_tg_chat.setText(self.settings.get("telegram_chat_id", ""))
        card_mobile.add_row(SettingRow("Telegram Chat ID", "Target chat or channel ID", self.txt_tg_chat))

        layout.addWidget(card_mobile)

        card_desktop = SettingCard("PC Desktop Alerts (Windows)", "Desktop notification banners on your computer monitor")

        self.sw_desktop_toasts = ToggleSwitch(checked=self.settings.get("show_desktop_notifications", True))
        card_desktop.add_row(SettingRow("On-Screen Toast Banners", "Display alert banner in the corner of Windows desktop", self.sw_desktop_toasts))

        self.slider_toast_dur = QSlider(Qt.Orientation.Horizontal)
        self.slider_toast_dur.setRange(2, 20)
        self.slider_toast_dur.setValue(int(self.settings.get("notification_duration_sec", 6)))
        self.slider_toast_dur.setFixedWidth(140)
        lbl_toast_val = QLabel(f"{self.slider_toast_dur.value()} sec")
        lbl_toast_val.setStyleSheet("font-weight: 700; color: #38bdf8; min-width: 45px;")
        self.slider_toast_dur.valueChanged.connect(lambda v: lbl_toast_val.setText(f"{v} sec"))
        sl_box = QWidget()
        sl_lay = QHBoxLayout(sl_box)
        sl_lay.setContentsMargins(0, 0, 0, 0)
        sl_lay.addWidget(self.slider_toast_dur)
        sl_lay.addWidget(lbl_toast_val)
        card_desktop.add_row(SettingRow("Banner Duration", "How many seconds the alert banner remains visible", sl_box))

        layout.addWidget(card_desktop)
        layout.addStretch(1)
        self.stack.addWidget(scroll)

    def _generate_secret_ntfy_topic(self):
        import uuid
        secret = f"cctv_{uuid.uuid4().hex[:12]}"
        self.txt_ntfy_topic.setText(secret)

    def _test_ntfy_delivery(self):
        import threading
        from core.notification_dispatcher import NotificationDispatcher
        settings = {"ntfy_enabled": self.sw_ntfy_enabled.isChecked(),
                    "ntfy_topic": self.txt_ntfy_topic.text().strip(),
                    "ntfy_server": self.settings.get("ntfy_server", "")}
        self.btn_ntfy_test.setEnabled(False)
        self.lbl_ntfy_test.setText("Sending one text-only test in the background…")
        def run():
            try:
                ok, message = NotificationDispatcher(settings).send_test_notification("ntfy")
            except Exception as error:
                ok, message = False, NotificationDispatcher.ntfy_error_message(error)
            try: self.ntfy_test_finished.emit(ok, message)
            except RuntimeError: pass
        threading.Thread(target=run, daemon=True, name="NtfyTest").start()

    def _show_ntfy_test_result(self, ok, message):
        self.btn_ntfy_test.setEnabled(True)
        self.lbl_ntfy_test.setText(message)
        self.lbl_ntfy_test.setStyleSheet(f"color: {'#34d399' if ok else '#f87171'}; font-size: 11px; padding: 8px 0;")

    def _on_master_alerts_toggled(self, armed: bool):
        """Arming pauses/resumes delivery without rewriting category preferences."""

    def _select_people_only_notifications(self):
        for category, switch in self.outgoing_category_switches.items():
            switch.setChecked(category == "person")

    def _apply_recommended_alert_settings(self):
        """One-click proven security configuration for maximum protection with zero false alarm spam."""
        if hasattr(self, "sw_master_alerts"):
            self.sw_master_alerts.setChecked(True)
        if hasattr(self, "sw_notify_person"):
            self.sw_notify_person.setChecked(True)
        if hasattr(self, "sw_notify_vehicle"):
            self.sw_notify_vehicle.setChecked(True)
        if hasattr(self, "sw_notify_animal"):
            self.sw_notify_animal.setChecked(True)
        if hasattr(self, "sw_notify_motion"):
            self.sw_notify_motion.setChecked(True)
        if hasattr(self, "sw_desktop_toasts"):
            self.sw_desktop_toasts.setChecked(True)
        if hasattr(self, "sw_ai_enabled"):
            self.sw_ai_enabled.setChecked(True)
        if hasattr(self, "slider_ai_conf"):
            self.slider_ai_conf.setValue(40)
        if hasattr(self, "slider_min_area"):
            self.slider_min_area.setValue(2800)
        if hasattr(self, "sw_foliage_filter"):
            self.sw_foliage_filter.setChecked(True)
        if hasattr(self, "slider_cooldown"):
            self.slider_cooldown.setValue(5)
        if hasattr(self, "sw_dual_clips"):
            self.sw_dual_clips.setChecked(True)
        if hasattr(self, "sw_clip_audio"):
            self.sw_clip_audio.setChecked(True)
        if hasattr(self, "slider_clip_dur"):
            self.slider_clip_dur.setValue(10)
        if hasattr(self, "slider_pre_buf"):
            self.slider_pre_buf.setValue(5)

    # -------------------------------------------------------------
    #  TAB 2: MOTION & AI DETECTION
    # -------------------------------------------------------------
    def _build_tab_ai_motion(self):
        scroll, layout = self._create_scrollable_page()

        card_ai = SettingCard("YOLO AI Engine & Visual Recognition", "Detect persons, vehicles, and animals using artificial intelligence")

        self.sw_ai_enabled = ToggleSwitch(checked=self.settings.get("ai_detection_enabled", True), active_color="#0284c7")
        card_ai.add_row(SettingRow("Smart AI Scanning Active", "Analyze frames to accurately identify objects in front of the camera", self.sw_ai_enabled))

        self.sw_smart_desc = ToggleSwitch(checked=self.settings.get("enable_smart_descriptions", True))
        card_ai.add_row(SettingRow("Detailed Visual Descriptions", "Describe detected subjects (e.g. 'person in red jacket and dark pants')", self.sw_smart_desc))

        self.slider_ai_conf = QSlider(Qt.Orientation.Horizontal)
        self.slider_ai_conf.setRange(25, 95)
        self.slider_ai_conf.setValue(int(float(self.settings.get("ai_conf_threshold", 0.40)) * 100))
        self.slider_ai_conf.setFixedWidth(140)
        lbl_conf_val = QLabel(f"{self.slider_ai_conf.value()}%")
        lbl_conf_val.setStyleSheet("font-weight: 700; color: #38bdf8; min-width: 40px;")
        self.slider_ai_conf.valueChanged.connect(lambda v: lbl_conf_val.setText(f"{v}%"))
        conf_box = QWidget()
        c_lay = QHBoxLayout(conf_box)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.addWidget(self.slider_ai_conf)
        c_lay.addWidget(lbl_conf_val)
        card_ai.add_row(SettingRow("Minimum AI Confidence", "Filter out uncertain detections (recommended 40% - 50%)", conf_box))

        layout.addWidget(card_ai)

        card_size = SettingCard("Motion Size Calibration & Presets", "Eliminate false alarms from leaves, shadows, or insects")

        preset_box = QWidget()
        p_lay = QHBoxLayout(preset_box)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.setSpacing(6)

        btn_p_pet = QPushButton("Pet (1200px)")
        btn_p_pet.setFixedHeight(30)
        btn_p_pet.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_p_pet.clicked.connect(lambda: self.slider_min_area.setValue(1200))
        p_lay.addWidget(btn_p_pet)

        btn_p_pers = QPushButton("Person (2800px)")
        btn_p_pers.setFixedHeight(30)
        btn_p_pers.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_p_pers.clicked.connect(lambda: self.slider_min_area.setValue(2800))
        p_lay.addWidget(btn_p_pers)

        btn_p_car = QPushButton("Vehicle (5000px)")
        btn_p_car.setFixedHeight(30)
        btn_p_car.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_p_car.clicked.connect(lambda: self.slider_min_area.setValue(5000))
        p_lay.addWidget(btn_p_car)

        card_size.add_row(SettingRow("Quick Size Presets", "One-click configuration of minimum tracked object size", preset_box))

        self.slider_min_area = QSlider(Qt.Orientation.Horizontal)
        self.slider_min_area.setRange(200, 8000)
        self.slider_min_area.setValue(int(self.settings.get("motion_min_area", 2800)))
        self.slider_min_area.setFixedWidth(140)
        lbl_area_val = QLabel(f"{self.slider_min_area.value()} px")
        lbl_area_val.setStyleSheet("font-weight: 700; color: #38bdf8; min-width: 55px;")
        self.slider_min_area.valueChanged.connect(lambda v: lbl_area_val.setText(f"{v} px"))
        area_box = QWidget()
        a_lay = QHBoxLayout(area_box)
        a_lay.setContentsMargins(0, 0, 0, 0)
        a_lay.addWidget(self.slider_min_area)
        a_lay.addWidget(lbl_area_val)
        card_size.add_row(SettingRow("Minimum Object Size (Pixels)", "Objects smaller than this threshold will be ignored (2,800px recommended)", area_box))

        self.sw_foliage_filter = ToggleSwitch(checked=self.settings.get("motion_foliage_filter", True), active_color="#0284c7")
        card_size.add_row(SettingRow("Anti-Wind Foliage & Leaf Filter", "Suppresses false motion alarms caused by leaves rustling and tree branches swaying in wind", self.sw_foliage_filter))

        self.slider_cooldown = QSlider(Qt.Orientation.Horizontal)
        self.slider_cooldown.setRange(1, 30)
        self.slider_cooldown.setValue(int(self.settings.get("motion_cooldown_sec", 5.0)))
        self.slider_cooldown.setFixedWidth(140)
        lbl_cd_val = QLabel(f"{self.slider_cooldown.value()} sec")
        lbl_cd_val.setStyleSheet("font-weight: 700; color: #38bdf8; min-width: 45px;")
        self.slider_cooldown.valueChanged.connect(lambda v: lbl_cd_val.setText(f"{v} sec"))
        cd_box = QWidget()
        cd_lay = QHBoxLayout(cd_box)
        cd_lay.setContentsMargins(0, 0, 0, 0)
        cd_lay.addWidget(self.slider_cooldown)
        cd_lay.addWidget(lbl_cd_val)
        card_size.add_row(SettingRow("Cooldown Between Consecutive Alerts", "Quiet period between alerts from the same camera", cd_box))

        self.spin_motion_confirm = QDoubleSpinBox()
        self.spin_motion_confirm.setRange(0.0, 10.0)
        self.spin_motion_confirm.setSingleStep(0.1)
        self.spin_motion_confirm.setSuffix(" s")
        self.spin_motion_confirm.setValue(float(self.settings.get("motion_confirm_delay", 1.2)))
        card_size.add_row(SettingRow("Motion confirmation", "Continuous motion required before an alert. Longer delays reject brief disturbances.", self.spin_motion_confirm))
        self.spin_ai_confirm = QDoubleSpinBox()
        self.spin_ai_confirm.setRange(0.0, 10.0)
        self.spin_ai_confirm.setSingleStep(0.1)
        self.spin_ai_confirm.setSuffix(" s")
        self.spin_ai_confirm.setValue(float(self.settings.get("detection_confirm_sec", 0.8)))
        card_size.add_row(SettingRow("AI confirmation", "An object must persist across at least two detections and this delay.", self.spin_ai_confirm))
        self.spin_motion_hold = QDoubleSpinBox()
        self.spin_motion_hold.setRange(0.5, 30.0)
        self.spin_motion_hold.setSuffix(" s")
        self.spin_motion_hold.setValue(float(self.settings.get("motion_hold_sec", 3.0)))
        for spin in (self.spin_motion_confirm, self.spin_ai_confirm, self.spin_motion_hold):
            spin.setFixedWidth(110)
            spin.setMinimumHeight(30)
            spin.setStyleSheet("QDoubleSpinBox { color: #f1f5f9; background: #111a2e; border: 1px solid #334155; border-radius: 6px; padding: 4px; }")
        card_size.add_row(SettingRow("Motion hold", "Keep motion active briefly after movement stops; this is separate from alert cooldown.", self.spin_motion_hold))
        self.cmb_detection_preset = QComboBox()
        self.cmb_detection_preset.addItem("Outdoor / foliage", (2800, 55, 1.2, 0.8, 10, True))
        self.cmb_detection_preset.addItem("Indoor / quiet scene", (1200, 50, 0.6, 0.6, 5, False))
        self.cmb_detection_preset.addItem("Fast crossing", (1200, 60, 0.2, 0.3, 5, True))
        self.btn_detection_preset = QPushButton("Apply preset")
        def apply_detection_preset():
            area, confidence, motion_delay, ai_delay, cooldown, foliage = self.cmb_detection_preset.currentData()
            self.slider_min_area.setValue(area)
            self.slider_ai_conf.setValue(confidence)
            self.spin_motion_confirm.setValue(motion_delay)
            self.spin_ai_confirm.setValue(ai_delay)
            self.slider_cooldown.setValue(cooldown)
            self.sw_foliage_filter.setChecked(foliage)
        self.btn_detection_preset.clicked.connect(apply_detection_preset)
        preset_row = QWidget()
        preset_layout = QHBoxLayout(preset_row)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.addWidget(self.cmb_detection_preset)
        preset_layout.addWidget(self.btn_detection_preset)
        card_size.add_row(SettingRow("Scene preset", "Apply a starting point, then tune against real activity in your camera view.", preset_row))
        layout.addWidget(card_size)
        layout.addStretch(1)
        self.stack.addWidget(scroll)

    # -------------------------------------------------------------
    #  TAB 3: STORAGE & GOOGLE DRIVE
    # -------------------------------------------------------------
    def _build_tab_storage(self):
        scroll, layout = self._create_scrollable_page()

        card_gdrive = SettingCard("Google Drive & Local Storage", "Automatic saving of video clips and snapshots to local or cloud directories")

        dir_box = QWidget()
        d_lay = QHBoxLayout(dir_box)
        d_lay.setContentsMargins(0, 0, 0, 0)
        d_lay.setSpacing(8)
        self.txt_rec_dir = QLineEdit()
        self.txt_rec_dir.setFixedWidth(220)
        self.txt_rec_dir.setFixedHeight(32)
        self.txt_rec_dir.setText(self.settings.get("recording_dir", "recordings"))
        d_lay.addWidget(self.txt_rec_dir)
        btn_browse_rec = QPushButton("Browse...")
        btn_browse_rec.setFixedHeight(32)
        btn_browse_rec.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_rec.clicked.connect(self._browse_rec_dir)
        d_lay.addWidget(btn_browse_rec)
        card_gdrive.add_row(SettingRow("Video Recordings Folder (CCTV)", "Workstation storage directory for 24/7 video archives", dir_box))

        snap_box = QWidget()
        s_lay = QHBoxLayout(snap_box)
        s_lay.setContentsMargins(0, 0, 0, 0)
        s_lay.setSpacing(8)
        self.txt_snap_dir = QLineEdit()
        self.txt_snap_dir.setFixedWidth(220)
        self.txt_snap_dir.setFixedHeight(32)
        self.txt_snap_dir.setText(self.settings.get("snapshot_dir", "snapshots"))
        s_lay.addWidget(self.txt_snap_dir)
        btn_browse_snap = QPushButton("Browse...")
        btn_browse_snap.setFixedHeight(32)
        btn_browse_snap.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_snap.clicked.connect(self._browse_snap_dir)
        s_lay.addWidget(btn_browse_snap)
        card_gdrive.add_row(SettingRow("Snapshot Photo Folder", "Directory for photos captured upon detection", snap_box))

        layout.addWidget(card_gdrive)

        card_clips = SettingCard("Incident Video Recording (Pre & Post Alarm)", "Configure clip duration and quality saved on detection")

        self.slider_pre_buf = QSlider(Qt.Orientation.Horizontal)
        self.slider_pre_buf.setRange(0, 10)
        self.slider_pre_buf.setValue(int(self.settings.get("pre_alarm_buffer_sec", 3)))
        self.slider_pre_buf.setFixedWidth(140)
        lbl_pre_val = QLabel(f"{self.slider_pre_buf.value()} sec")
        lbl_pre_val.setStyleSheet("font-weight: 700; color: #38bdf8; min-width: 45px;")
        self.slider_pre_buf.valueChanged.connect(lambda v: lbl_pre_val.setText(f"{v} sec"))
        pre_box = QWidget()
        pb_lay = QHBoxLayout(pre_box)
        pb_lay.setContentsMargins(0, 0, 0, 0)
        pb_lay.addWidget(self.slider_pre_buf)
        pb_lay.addWidget(lbl_pre_val)
        card_clips.add_row(SettingRow("Pre-Alarm Buffer Recording", "Save video before detection occurred to observe approach", pre_box))

        self.slider_clip_dur = QSlider(Qt.Orientation.Horizontal)
        self.slider_clip_dur.setRange(5, 60)
        self.slider_clip_dur.setValue(int(self.settings.get("alert_clip_duration_sec", 15)))
        self.slider_clip_dur.setFixedWidth(140)
        lbl_dur_val = QLabel(f"{self.slider_clip_dur.value()} sec")
        lbl_dur_val.setStyleSheet("font-weight: 700; color: #38bdf8; min-width: 45px;")
        self.slider_clip_dur.valueChanged.connect(lambda v: lbl_dur_val.setText(f"{v} sec"))
        dur_box = QWidget()
        db_lay = QHBoxLayout(dur_box)
        db_lay.setContentsMargins(0, 0, 0, 0)
        db_lay.addWidget(self.slider_clip_dur)
        db_lay.addWidget(lbl_dur_val)
        card_clips.add_row(SettingRow("Maximum Alert Clip Duration", "Seconds to record while motion persists", dur_box))

        self.sw_dual_clips = ToggleSwitch(checked=self.settings.get("record_dual_clips", True))
        card_clips.add_row(SettingRow("Save Dual Versions (AI Overlays + Clean Feed)", "Preserve annotated detection clip alongside raw pristine footage", self.sw_dual_clips))

        self.sw_clip_audio = ToggleSwitch(checked=self.settings.get("record_audio_in_clips", False))
        card_clips.add_row(SettingRow("Include Camera Microphone Audio", "Record RTSP audio channel into saved MP4 files", self.sw_clip_audio))

        layout.addWidget(card_clips)

        card_retention = SettingCard("Automatic Cleanup & Disk Retention", "Automatically delete old footage to protect disk space")

        self.cmb_retention = QComboBox()
        self.cmb_retention.setFixedWidth(220)
        self.cmb_retention.setFixedHeight(32)
        self.cmb_retention.addItem("After 7 Days", 7)
        self.cmb_retention.addItem("After 14 Days", 14)
        self.cmb_retention.addItem("After 30 Days (Recommended)", 30)
        self.cmb_retention.addItem("After 60 Days", 60)
        self.cmb_retention.addItem("Keep Indefinitely", 0)
        curr_ret = self.settings.get("retention_days", 30)
        idx = self.cmb_retention.findData(curr_ret)
        if idx >= 0:
            self.cmb_retention.setCurrentIndex(idx)
        card_retention.add_row(SettingRow("Recording Retention Period", "Recordings older than this threshold are purged automatically", self.cmb_retention))

        self.sw_auto_clean = ToggleSwitch(checked=self.settings.get("auto_clean_on_startup", True))
        card_retention.add_row(SettingRow("Auto Cleanup on Startup", "Scan and free storage space every time application starts", self.sw_auto_clean))

        layout.addWidget(card_retention)
        layout.addStretch(1)
        self.stack.addWidget(scroll)

    def _browse_rec_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select CCTV Recordings Directory")
        if d:
            self.txt_rec_dir.setText(d)

    def _browse_snap_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Snapshot Directory")
        if d:
            self.txt_snap_dir.setText(d)

    # -------------------------------------------------------------
    #  TAB 4: INDIVIDUAL CAMERAS
    # -------------------------------------------------------------
    def _format_camera_selector_label(self, cam: dict) -> str:
        name = cam.get("name") or "Camera"
        is_dual = cam.get("is_dual_lens", False)
        lens_tag = "Dual-Lens" if is_dual else "Single Lens"
        has_pwd = bool(str(cam.get("password", "")).strip())
        is_cfg = cam.get("configured") is not False and bool(cam.get("streams"))
        cfg_tag = "" if is_cfg else " [Needs Setup]"
        return f"{name}  •  {lens_tag}{cfg_tag}"

    def _update_camera_badges(self, cam: dict):
        if not cam or not hasattr(self, "badge_cam_lens"):
            return
        is_dual = cam.get("is_dual_lens", False)
        has_pwd = bool(str(cam.get("password", "")).strip())
        is_cfg = cam.get("configured") is not False and bool(cam.get("streams"))

        if is_dual:
            self.badge_cam_lens.setText("Dual-Lens (2 Streams)")
            self.badge_cam_lens.setStyleSheet("""
                QLabel {
                    background: rgba(56, 189, 248, 0.15);
                    border: 1px solid rgba(56, 189, 248, 0.4);
                    color: #38bdf8;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 700;
                }
            """)
        else:
            self.badge_cam_lens.setText("Single Lens (1 Stream)")
            self.badge_cam_lens.setStyleSheet("""
                QLabel {
                    background: rgba(148, 163, 184, 0.1);
                    border: 1px solid rgba(148, 163, 184, 0.25);
                    color: #94a3b8;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)

        if is_cfg:
            self.badge_cam_status.setText("Configured")
            self.badge_cam_status.setStyleSheet("""
                QLabel {
                    background: rgba(16, 185, 129, 0.15);
                    border: 1px solid rgba(16, 185, 129, 0.4);
                    color: #34d399;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 700;
                }
            """)
        else:
            self.badge_cam_status.setText("Needs Setup")
            self.badge_cam_status.setStyleSheet("""
                QLabel {
                    background: rgba(245, 158, 11, 0.15);
                    border: 1px solid rgba(245, 158, 11, 0.4);
                    color: #fbbf24;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 700;
                }
            """)

    def _build_tab_cameras(self):
        scroll, layout = self._create_scrollable_page()

        card_sel = SettingCard("Active Camera Profile", "Select a camera workstation profile to configure credentials, lens routing, and night vision")

        # Premium Selector Container with Cyber Dark styling
        sel_container = QWidget(card_sel)
        sel_layout = QHBoxLayout(sel_container)
        sel_layout.setContentsMargins(0, 4, 0, 8)
        sel_layout.setSpacing(14)

        # Left: Clean title and live status badges
        info_box = QVBoxLayout()
        info_box.setSpacing(6)
        lbl_sel_title = QLabel("Active Camera Device", sel_container)
        lbl_sel_title.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: 600;")
        info_box.addWidget(lbl_sel_title)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(8)

        # Lens Mode Badge
        self.badge_cam_lens = QLabel(sel_container)
        self.badge_cam_lens.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Status Badge
        self.badge_cam_status = QLabel(sel_container)
        self.badge_cam_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badges_row.addWidget(self.badge_cam_lens)
        badges_row.addWidget(self.badge_cam_status)
        badges_row.addStretch(1)
        info_box.addLayout(badges_row)

        sel_layout.addLayout(info_box)
        sel_layout.addStretch(1)

        # Right: Styled QComboBox (width 280 perfectly matching inputs below)
        self.cmb_active_cam = QComboBox(sel_container)
        self.cmb_active_cam.setFixedWidth(280)
        self.cmb_active_cam.setFixedHeight(36)
        self.cmb_active_cam.setIconSize(QSize(16, 16))
        self.cmb_active_cam.setStyleSheet("""
            QComboBox {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #090e1a, stop:1 #111a2e);
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 13px;
                font-weight: 600;
                color: #f8fafc;
            }
            QComboBox:hover {
                border: 1px solid #38bdf8;
                background: #14223d;
            }
            QComboBox:focus {
                border: 1px solid #38bdf8;
                background: #14223d;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border-left: 1px solid rgba(56, 189, 248, 0.2);
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background: rgba(56, 189, 248, 0.05);
            }
            QComboBox::drop-down:hover {
                background: rgba(56, 189, 248, 0.15);
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #38bdf8;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #0b1120;
                border: 1px solid #38bdf8;
                border-radius: 8px;
                selection-background-color: rgba(56, 189, 248, 0.25);
                selection-color: #ffffff;
                color: #e2e8f0;
                padding: 6px;
                outline: none;
                min-width: 310px;
            }
            QComboBox QAbstractItemView::item {
                min-height: 34px;
                padding: 6px 12px;
                margin: 2px 0px;
                border-radius: 6px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: rgba(56, 189, 248, 0.15);
                color: #38bdf8;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: rgba(56, 189, 248, 0.25);
                color: #ffffff;
                font-weight: bold;
            }
        """)

        cam_icon = create_settings_vector_icon("cameras", color="#38bdf8", size=16)
        for idx, c in enumerate(self.cameras):
            cid = c.get("id", "")
            lbl = self._format_camera_selector_label(c)
            self.cmb_active_cam.addItem(cam_icon, lbl, cid)

        self.cmb_active_cam.currentIndexChanged.connect(self._on_camera_selector_changed)
        sel_layout.addWidget(self.cmb_active_cam)

        card_sel.layout.addWidget(sel_container)
        layout.addWidget(card_sel)

        # Card 2: Connection Parameters & Security Credentials
        card_conn = SettingCard("Camera Connection & Security Credentials", "Update IP address, RTSP port, credentials, and test live connection")

        self.txt_cam_name = QLineEdit()
        self.txt_cam_name.setFixedWidth(280)
        self.txt_cam_name.setFixedHeight(32)
        card_conn.add_row(SettingRow("Camera Name", "Display name in viewing grid and event logs", self.txt_cam_name))

        # IP & Port Row (Masked IP with reveal button)
        ip_port_box = QWidget()
        ip_port_lay = QHBoxLayout(ip_port_box)
        ip_port_lay.setContentsMargins(0, 0, 0, 0)
        ip_port_lay.setSpacing(8)

        lbl_ip_tag = QLabel("IP:", ip_port_box)
        lbl_ip_tag.setStyleSheet("color: #94a3b8; font-size: 11px;")
        box_ip, self.txt_cam_ip, _ = self._create_masked_input(placeholder="192.168.1.100", width=140, on_text_changed=self._auto_update_cam_urls)

        lbl_port_tag = QLabel("Port:", ip_port_box)
        lbl_port_tag.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.spin_cam_port = QSpinBox(ip_port_box)
        self.spin_cam_port.setRange(1, 65535)
        self.spin_cam_port.setValue(554)
        self.spin_cam_port.setFixedWidth(80)
        self.spin_cam_port.setFixedHeight(32)
        self.spin_cam_port.valueChanged.connect(self._auto_update_cam_urls)

        ip_port_lay.addWidget(lbl_ip_tag)
        ip_port_lay.addWidget(box_ip)
        ip_port_lay.addWidget(lbl_port_tag)
        ip_port_lay.addWidget(self.spin_cam_port)
        card_conn.add_row(SettingRow("IP Address & RTSP Port", "Workstation network endpoint for live RTSP streaming (Masked)", ip_port_box))

        # Username (Masked with reveal button, default "admin")
        box_user, self.txt_cam_user, _ = self._create_masked_input(placeholder="admin", text="admin", width=244, on_text_changed=self._auto_update_cam_urls)
        card_conn.add_row(SettingRow("RTSP Username", "ONVIF or local camera authentication user (Masked)", box_user))

        # Password (Masked with reveal button, Enter triggers test feed)
        box_pass, self.txt_cam_pass, _ = self._create_masked_input(placeholder="Leave blank if none", width=244, on_text_changed=self._auto_update_cam_urls)
        self.txt_cam_pass.returnPressed.connect(lambda: self._test_camera_connection())
        card_conn.add_row(SettingRow("Camera Password", "Masked security credential set in mobile camera app", box_pass))

        # Dual Lens Toggle
        self.sw_cam_dual = ToggleSwitch(checked=False)
        self.sw_cam_dual.toggled.connect(self._on_cam_dual_toggled)
        card_conn.add_row(SettingRow("Dual-Lens Hardware", "Enable secondary wide panoramic lens alongside PTZ zoom", self.sw_cam_dual))

        # Stream 1 URL (Masked with reveal button)
        box_url1, self.txt_cam_url1, _ = self._create_masked_input(placeholder="rtsp://...", width=244)
        card_conn.add_row(SettingRow("Stream 1 URL (Primary / PTZ)", "Full authenticated RTSP feed path (Masked)", box_url1))

        # Stream 2 URL (Container for Dual Lens, Masked with reveal button)
        box_url2, self.txt_cam_url2, _ = self._create_masked_input(placeholder="rtsp://...", width=244)
        self.row_cam_url2 = SettingRow("Stream 2 URL (Secondary / Wide)", "Full authenticated secondary lens RTSP feed path (Masked)", box_url2)
        card_conn.add_row(self.row_cam_url2)

        # Connection Diagnostics Row
        test_box = QWidget()
        test_lay = QHBoxLayout(test_box)
        test_lay.setContentsMargins(0, 0, 0, 0)
        test_lay.setSpacing(10)

        self.lbl_test_badge = QLabel("Not Tested", test_box)
        self.lbl_test_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 41, 59, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
                color: #94a3b8;
                font-weight: 600;
                font-size: 11px;
            }
        """)
        test_lay.addWidget(self.lbl_test_badge)

        self.btn_test_conn = QPushButton("Test Connection", test_box)
        self.btn_test_conn.setFixedWidth(130)
        self.btn_test_conn.setFixedHeight(28)
        self.btn_test_conn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test_conn.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 41, 59, 0.85);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #0284c7;
                color: #ffffff;
                border-color: #38bdf8;
            }
            QPushButton:disabled {
                background-color: rgba(30, 41, 59, 0.4);
                color: #64748b;
                border-color: rgba(255, 255, 255, 0.08);
            }
        """)
        self.btn_test_conn.clicked.connect(self._test_camera_connection)
        test_lay.addWidget(self.btn_test_conn)

        card_conn.add_row(SettingRow("Connection Diagnostics", "Probe TCP socket reachability and RTSP video decoding", test_box))

        # Connection Action Row
        act_box = QWidget()
        act_lay = QHBoxLayout(act_box)
        act_lay.setContentsMargins(0, 0, 0, 0)
        act_lay.setSpacing(10)

        self.lbl_conn_feedback = QLabel(act_box)
        self.lbl_conn_feedback.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 600;")
        act_lay.addWidget(self.lbl_conn_feedback, stretch=1)

        btn_apply_conn = QPushButton("Save && Reconnect in Panel", act_box)
        btn_apply_conn.setFixedWidth(200)
        btn_apply_conn.setFixedHeight(30)
        btn_apply_conn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply_conn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        btn_apply_conn.clicked.connect(self._apply_active_camera_connection)
        act_lay.addWidget(btn_apply_conn)

        card_conn.add_row(SettingRow("Apply & Reconnect", "Commit parameters to profile and immediately reconnect in Panel View", act_box))
        layout.addWidget(card_conn)

        # Card 3: Selected Camera Parameters
        card_over = SettingCard("Selected Camera Parameters", "Orientation, framerate, and per-camera filters")

        self.sw_cam_flip = ToggleSwitch(checked=False)
        self.sw_cam_flip.toggled.connect(self._on_cam_flip_toggled)
        card_over.add_row(SettingRow("Rotate Image 180 (Flip)", "Useful if camera is mounted upside-down", self.sw_cam_flip))

        self.cmb_cam_fps = QComboBox()
        self.cmb_cam_fps.setFixedWidth(200)
        self.cmb_cam_fps.setFixedHeight(32)
        self.cmb_cam_fps.addItem("Auto (Native Stream)", 0)
        self.cmb_cam_fps.addItem("10 FPS (Low CPU)", 10)
        self.cmb_cam_fps.addItem("15 FPS (Optimal CCTV)", 15)
        self.cmb_cam_fps.addItem("20 FPS", 20)
        self.cmb_cam_fps.addItem("25 FPS", 25)
        self.cmb_cam_fps.currentIndexChanged.connect(self._on_cam_fps_changed)
        card_over.add_row(SettingRow("Target Frame Rate (FPS)", "Lowering frame rate saves CPU processing power", self.cmb_cam_fps))

        self.sw_cam_ai = ToggleSwitch(checked=True)
        self.sw_cam_ai.toggled.connect(self._on_cam_ai_toggled)
        card_over.add_row(SettingRow("AI Detection on This Camera", "Disable scanning if this camera does not require AI analysis", self.sw_cam_ai))

        btn_zone = QPushButton("Edit Exclusion Zones")
        btn_zone.setFixedWidth(180)
        btn_zone.setFixedHeight(32)
        btn_zone.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_zone.clicked.connect(self._open_zone_editor)
        card_over.add_row(SettingRow("Masked Zones (Ignore Motion)", "Draw exclusion zones for trees, public roads, or flags", btn_zone))

        layout.addWidget(card_over)
        layout.addStretch(1)
        self.stack.addWidget(scroll)

        if self.cameras:
            initial_id = self.selected_camera_id or self.cameras[0].get("id")
            self._current_loaded_cam_id = initial_id
            idx = self.cmb_active_cam.findData(initial_id)
            if idx >= 0:
                self.cmb_active_cam.setCurrentIndex(idx)
            self._load_camera_overrides_to_ui(initial_id)

    def _extract_rtsp_path(self, url: str, default_path: str = "/live/ch00_0") -> str:
        return stream_path(url, default_path)

    def _build_rtsp_url(self, user: str, pwd: str, ip: str, port: int, path: str) -> str:
        return build_rtsp_url(user, pwd, ip, port, path)

    def _test_camera_connection(self):
        ip = self.txt_cam_ip.text().strip()
        port = self.spin_cam_port.value()
        user = self.txt_cam_user.text().strip() or "admin"
        pwd = self.txt_cam_pass.text()

        if not ip:
            self.lbl_test_badge.setText("Missing IP")
            self.lbl_test_badge.setStyleSheet("background-color: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; border-radius: 6px; padding: 4px 10px; color: #fca5a5; font-weight: 600; font-size: 11px;")
            return

        url = self.txt_cam_url1.text().strip()
        if not url:
            self._auto_update_cam_urls()
            url = self.txt_cam_url1.text().strip()
        self._tested_url = url
        self._tested_camera_id = self.cmb_active_cam.currentData()

        self.btn_test_conn.setEnabled(False)
        self.btn_test_conn.setText("Testing...")
        self.lbl_test_badge.setText("Probing RTSP...")
        self.lbl_test_badge.setStyleSheet("background-color: rgba(56, 189, 248, 0.2); border: 1px solid #38bdf8; border-radius: 6px; padding: 4px 10px; color: #38bdf8; font-weight: 600; font-size: 11px;")

        self.test_worker = AsyncSettingsConnectionTester(url=url, ip=ip, port=port)
        self.test_worker.test_finished.connect(self._on_test_connection_finished)
        self.test_worker.start()

    def _on_test_connection_finished(self, success: bool, message: str):
        self.btn_test_conn.setEnabled(True)
        self.btn_test_conn.setText("Test Connection")
        if (self.txt_cam_url1.text().strip() != getattr(self, "_tested_url", "") or
                self.cmb_active_cam.currentData() != getattr(self, "_tested_camera_id", None)):
            self.lbl_test_badge.setText("Settings changed — test again")
            return
        if success:
            self.lbl_test_badge.setText("Online / Verified")
            self.lbl_test_badge.setToolTip(message)
            self.lbl_test_badge.setStyleSheet("background-color: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; border-radius: 6px; padding: 4px 10px; color: #34d399; font-weight: 700; font-size: 11px;")
        else:
            self.lbl_test_badge.setText("Video not verified")
            self.lbl_test_badge.setToolTip(message)
            self.lbl_test_badge.setStyleSheet("background-color: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; border-radius: 6px; padding: 4px 10px; color: #fca5a5; font-weight: 700; font-size: 11px;")

    def _on_cam_dual_toggled(self, val: bool):
        self.row_cam_url2.setVisible(val)
        cid = self.cmb_active_cam.currentData()
        cam = next((c for c in self.cameras if c.get("id") == cid), None)
        if cam:
            cam["is_dual_lens"] = val
            self._update_camera_badges(cam)
            curr_idx = self.cmb_active_cam.findData(cid)
            if curr_idx >= 0:
                self.cmb_active_cam.setItemText(curr_idx, self._format_camera_selector_label(cam))
        if val and not self.txt_cam_url2.text().strip():
            self._auto_update_cam_urls()

    def _auto_update_cam_urls(self, *args):
        if getattr(self, "_loading_connection", False):
            return
        ip = self.txt_cam_ip.text().strip()
        port = self.spin_cam_port.value()
        user = self.txt_cam_user.text().strip()
        pwd = self.txt_cam_pass.text()
        if ip:
            curr_url1 = self.txt_cam_url1.text().strip()
            path1 = self._extract_rtsp_path(curr_url1, "/live/ch00_0")
            self.txt_cam_url1.setText(self._build_rtsp_url(user, pwd, ip, port, path1))

            curr_url2 = self.txt_cam_url2.text().strip()
            path2 = self._extract_rtsp_path(curr_url2, "/live/ch01_0")
            self.txt_cam_url2.setText(self._build_rtsp_url(user, pwd, ip, port, path2))

        cid = self.cmb_active_cam.currentData()
        cam = next((c for c in self.cameras if c.get("id") == cid), None)
        if cam:
            preview_cam = dict(cam)
            preview_cam["password"] = pwd
            preview_cam["ip"] = ip
            self._update_camera_badges(preview_cam)

    def _apply_active_camera_connection(self, target_cam_id: Optional[str] = None):
        cid = target_cam_id or self.cmb_active_cam.currentData()
        if not cid:
            return
        cam = next((c for c in self.cameras if c.get("id") == cid), None)
        if not cam:
            return

        name = self.txt_cam_name.text().strip() or cam.get("name", "Camera")
        ip = self.txt_cam_ip.text().strip() or cam.get("ip", "192.168.1.100")
        port = self.spin_cam_port.value()
        user = self.txt_cam_user.text().strip() or "admin"
        pwd = self.txt_cam_pass.text()
        is_dual = self.sw_cam_dual.isChecked()

        curr_url1 = self.txt_cam_url1.text().strip()
        path1 = self._extract_rtsp_path(curr_url1, cam.get("lens1_path") or "/live/ch00_0")
        url1 = curr_url1 or self._build_rtsp_url(user, pwd, ip, port, path1)

        curr_url2 = self.txt_cam_url2.text().strip()
        path2 = self._extract_rtsp_path(curr_url2, cam.get("lens2_path") or "/live/ch01_0")
        url2 = (curr_url2 or self._build_rtsp_url(user, pwd, ip, port, path2)) if is_dual else ""

        self.txt_cam_url1.setText(url1)
        if is_dual:
            self.txt_cam_url2.setText(url2)

        cam["name"] = name
        cam["ip"] = ip
        cam["port"] = port
        cam["username"] = user
        cam["password"] = pwd
        cam["is_dual_lens"] = is_dual
        cam["lens1_path"] = path1
        cam["lens2_path"] = path2 if is_dual else ""
        cam["configured"] = bool(ip and url1)

        streams = [
            {
                "id": f"{cid}_lens1",
                "name": "Lens 1 (PTZ Zoom)" if is_dual else "Main Stream",
                "channel": 0,
                "url": url1,
                "is_ptz": True
            }
        ]
        if is_dual:
            streams.append({
                "id": f"{cid}_lens2",
                "name": "Lens 2 (Fixed Wide)",
                "channel": 1,
                "url": url2,
                "is_ptz": False
            })
        cam["streams"] = streams

        self._update_camera_badges(cam)

        curr_idx = self.cmb_active_cam.findData(cid)
        if curr_idx >= 0:
            cam_icon = create_settings_vector_icon("cameras", color="#38bdf8", size=16)
            self.cmb_active_cam.setItemText(curr_idx, self._format_camera_selector_label(cam))
            self.cmb_active_cam.setItemIcon(curr_idx, cam_icon)

        # Emit camera_connection_updated to signal MainWindow immediately!
        self.camera_connection_updated.emit(dict(cam))
        self.lbl_conn_feedback.setText("Saved & live reconnect signaled to Panel View!")
        self.lbl_conn_feedback.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 700;")

    def _on_camera_selector_changed(self, idx: int):
        prev_cid = getattr(self, "_current_loaded_cam_id", None)
        if prev_cid:
            self._apply_active_camera_connection(target_cam_id=prev_cid)
        cid = self.cmb_active_cam.currentData()
        self._current_loaded_cam_id = cid
        if cid:
            self._load_camera_overrides_to_ui(cid)

    def _load_camera_overrides_to_ui(self, cid: str):
        self._loading_connection = True
        try:
            self._load_camera_fields(cid)
        finally:
            self._loading_connection = False

    def _load_camera_fields(self, cid: str):
        cam = next((c for c in self.cameras if c.get("id") == cid), None)
        if cam:
            self.txt_cam_name.setText(cam.get("name", ""))
            self.txt_cam_ip.setText(cam.get("ip", ""))
            self.spin_cam_port.setValue(int(cam.get("port", 554)))
            self.txt_cam_user.setText(cam.get("username") or "admin")
            self.txt_cam_pass.setText(cam.get("password", ""))
            is_dual = bool(cam.get("is_dual_lens", False))
            self.sw_cam_dual.setChecked(is_dual)
            self.row_cam_url2.setVisible(is_dual)

            streams = cam.get("streams", [])
            if len(streams) >= 1:
                self.txt_cam_url1.setText(streams[0].get("url", ""))
            elif cam.get("lens1_path"):
                self.txt_cam_url1.setText(build_rtsp_url(cam.get("username", ""), cam.get("password", ""), cam.get("ip", ""), cam.get("port", 554), cam["lens1_path"]))
            else:
                self.txt_cam_url1.setText("")

            if len(streams) >= 2:
                self.txt_cam_url2.setText(streams[1].get("url", ""))
            elif cam.get("lens2_path"):
                self.txt_cam_url2.setText(build_rtsp_url(cam.get("username", ""), cam.get("password", ""), cam.get("ip", ""), cam.get("port", 554), cam["lens2_path"]))
            else:
                self.txt_cam_url2.setText("")

            if hasattr(self, "lbl_test_badge"):
                self.lbl_test_badge.setText("Not Tested")
                self.lbl_test_badge.setToolTip("")
                self.lbl_test_badge.setStyleSheet("background-color: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 4px 10px; color: #94a3b8; font-weight: 600; font-size: 11px;")
            self.lbl_conn_feedback.setText("")
            self._update_camera_badges(cam)

        ov = self.camera_overrides.get(cid, {})
        self.sw_cam_flip.setChecked(ov.get("flip_horizontal", False))
        fps = ov.get("target_fps", 0)
        idx = self.cmb_cam_fps.findData(fps)
        if idx >= 0:
            self.cmb_cam_fps.setCurrentIndex(idx)
        self.sw_cam_ai.setChecked(ov.get("ai_enabled", True))

    def _on_cam_flip_toggled(self, val: bool):
        cid = self.cmb_active_cam.currentData()
        if cid:
            self.camera_overrides.setdefault(cid, {})["flip_horizontal"] = val

    def _on_cam_fps_changed(self, idx: int):
        cid = self.cmb_active_cam.currentData()
        if cid:
            self.camera_overrides.setdefault(cid, {})["target_fps"] = self.cmb_cam_fps.currentData()

    def _on_cam_ai_toggled(self, val: bool):
        cid = self.cmb_active_cam.currentData()
        if cid:
            self.camera_overrides.setdefault(cid, {})["ai_enabled"] = val

    def _open_zone_editor(self):
        cid = self.cmb_active_cam.currentData()
        cam = next((c for c in self.cameras if c.get("id") == cid), None)
        cname = cam.get("name", "Camera") if cam else "Camera"
        dlg = ZoneEditorDialog(cid, cname, parent=self)
        dlg.exec()

    # -------------------------------------------------------------
    #  TAB 5: PC PERFORMANCE
    # -------------------------------------------------------------
    def _build_tab_performance(self):
        scroll, layout = self._create_scrollable_page()

        card_stream = SettingCard("Default Video Stream Quality", "Choose default rendering clarity and processing mode for connected cameras")
        self.cmb_default_quality = QComboBox()
        self.cmb_default_quality.setFixedWidth(280)
        self.cmb_default_quality.setFixedHeight(32)
        self.cmb_default_quality.addItem("MAX (Pristine App Quality - Studio Clarity)", QualityMode.ULTRA_MAX)
        self.cmb_default_quality.addItem("2K Ultra HD (Native Raw - 2304x1296)", QualityMode.ULTRA_2K)
        self.cmb_default_quality.addItem("720p HD (Balanced - 1280x720)", QualityMode.MID_HD)
        self.cmb_default_quality.addItem("360p SD (Low Overhead - 640x360)", QualityMode.LOW_SD)
        curr_q = self.settings.get("default_quality", QualityMode.ULTRA_MAX)
        idx_q = self.cmb_default_quality.findData(curr_q)
        if idx_q >= 0:
            self.cmb_default_quality.setCurrentIndex(idx_q)
        card_stream.add_row(SettingRow("Global Camera Quality", "Resolution & ISP post-processing clarity preset", self.cmb_default_quality))
        layout.addWidget(card_stream)

        card_cpu = SettingCard("CPU & Hardware Optimization Profile", "Tailored settings for AMD Ryzen CCD1/CCD2 and Intel Core architectures")

        self.cmb_perf_profile = QComboBox()
        self.cmb_perf_profile.setFixedWidth(210)
        self.cmb_perf_profile.setFixedHeight(32)
        self.cmb_perf_profile.addItem("Balanced (Recommended)", "medium")
        self.cmb_perf_profile.addItem("Background / gaming", "gamer")
        self.cmb_perf_profile.addItem("Eco / Energy Saver", "low")
        self.cmb_perf_profile.addItem("Full performance", "high")
        curr_prof = self.settings.get("performance_profile", "medium")
        curr_prof = {"balanced": "medium", "performance": "gamer", "eco": "low", "extreme": "high"}.get(curr_prof, curr_prof)
        idx = self.cmb_perf_profile.findData(curr_prof)
        if idx >= 0:
            self.cmb_perf_profile.setCurrentIndex(idx)
        card_cpu.add_row(SettingRow("CPU Performance Profile", "Automatic thread pinning and system priority allocation", self.cmb_perf_profile))

        self.sw_show_perf_prompt = ToggleSwitch(checked=self.settings.get("show_performance_prompt_on_startup", False))
        card_cpu.add_row(SettingRow("Show Performance Prompt at Startup", "Allow quick profile selection when launching application", self.sw_show_perf_prompt))

        layout.addWidget(card_cpu)

        card_cv = SettingCard("Resource Saving & Frame Skipping", "Optimizations for smooth rendering with multiple 2K streams")

        self.sw_ai_motion_gated = ToggleSwitch(checked=self.settings.get("ai_motion_gated_only", True), active_color="#0284c7")
        card_cv.add_row(SettingRow("AI Scan Only When Motion Detected", "Massive CPU savings: AI idles when scene is static", self.sw_ai_motion_gated))

        self.slider_ai_skip = QSlider(Qt.Orientation.Horizontal)
        self.slider_ai_skip.setRange(0, 5)
        self.slider_ai_skip.setValue(int(self.settings.get("ai_skip_frames", 1)))
        self.slider_ai_skip.setFixedWidth(140)
        lbl_skip_val = QLabel(f"{self.slider_ai_skip.value()} frames")
        lbl_skip_val.setStyleSheet("font-weight: 700; color: #38bdf8; min-width: 50px;")
        self.slider_ai_skip.valueChanged.connect(lambda v: lbl_skip_val.setText(f"{v} frames"))
        skip_box = QWidget()
        sb_lay = QHBoxLayout(skip_box)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.addWidget(self.slider_ai_skip)
        sb_lay.addWidget(lbl_skip_val)
        card_cv.add_row(SettingRow("AI Frame Skip", "Analyze every 2nd or 3rd frame for lower hardware load", skip_box))

        self.cmb_display_fps = QComboBox()
        self.cmb_display_fps.setFixedWidth(210)
        self.cmb_display_fps.setFixedHeight(32)
        self.cmb_display_fps.addItem("15 FPS (Balanced)", 15)
        self.cmb_display_fps.addItem("20 FPS", 20)
        self.cmb_display_fps.addItem("25 FPS", 25)
        self.cmb_display_fps.addItem("30 FPS (Smooth)", 30)
        self.cmb_display_fps.addItem("Unlimited (Native)", 0)
        curr_fps = self.settings.get("display_fps_cap", 25)
        idx = self.cmb_display_fps.findData(curr_fps)
        if idx >= 0:
            self.cmb_display_fps.setCurrentIndex(idx)
        card_cv.add_row(SettingRow("Display Screen FPS Cap", "Caps GUI render FPS for low GPU overhead", self.cmb_display_fps))

        layout.addWidget(card_cv)
        layout.addStretch(1)
        self.stack.addWidget(scroll)

    # -------------------------------------------------------------
    #  TAB 6: SOUNDS & ALARMS
    # -------------------------------------------------------------
    def _build_tab_sound(self):
        scroll, layout = self._create_scrollable_page()

        card_snd = SettingCard("Local PC Audio Alarms", "Acoustic alerts played through computer speakers upon detection")

        snd_row = QWidget()
        sr_lay = QHBoxLayout(snd_row)
        sr_lay.setContentsMargins(0, 0, 0, 0)
        sr_lay.setSpacing(8)
        self.cmb_sound_profile = QComboBox()
        self.cmb_sound_profile.setFixedWidth(160)
        self.cmb_sound_profile.setFixedHeight(32)
        from core.sound_manager import SoundProfile, SoundManager
        for profile in SoundProfile.ALL:
            self.cmb_sound_profile.addItem(profile, profile)
        curr_snd = SoundManager.normalize_profile(self.settings.get("sound_profile", SoundProfile.CYBER_CHIME))
        idx = self.cmb_sound_profile.findData(curr_snd)
        if idx >= 0:
            self.cmb_sound_profile.setCurrentIndex(idx)
        sr_lay.addWidget(self.cmb_sound_profile)
        btn_test_snd = QPushButton("Test Audio")
        btn_test_snd.setFixedHeight(32)
        btn_test_snd.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test_snd.clicked.connect(self._test_sound)
        sr_lay.addWidget(btn_test_snd)
        card_snd.add_row(SettingRow("Siren Sound Profile", "Audio tone played when a subject is detected", snd_row))

        self.slider_sound_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_sound_vol.setRange(0, 100)
        self.slider_sound_vol.setValue(SoundManager.volume_from_settings(self.settings))
        self.slider_sound_vol.setFixedWidth(140)
        lbl_vol_val = QLabel(f"{self.slider_sound_vol.value()}%")
        lbl_vol_val.setStyleSheet("font-weight: 700; color: #38bdf8; min-width: 40px;")
        self.slider_sound_vol.valueChanged.connect(lambda v: lbl_vol_val.setText(f"{v}%"))
        self.slider_sound_vol.valueChanged.connect(lambda v: self.sound_manager.stop() if v == 0 else None)
        self.slider_sound_vol.sliderReleased.connect(self._test_sound)
        vol_box = QWidget()
        vb_lay = QHBoxLayout(vol_box)
        vb_lay.setContentsMargins(0, 0, 0, 0)
        vb_lay.addWidget(self.slider_sound_vol)
        vb_lay.addWidget(lbl_vol_val)
        card_snd.add_row(SettingRow("PC Speaker Volume", "Audio loudness of local alarms", vol_box))

        custom_row = QWidget()
        custom_layout = QHBoxLayout(custom_row)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        self.txt_custom_sound = QLineEdit(self.settings.get("custom_sound_path", ""))
        self.txt_custom_sound.setPlaceholderText("Uncompressed PCM WAV file")
        custom_layout.addWidget(self.txt_custom_sound)
        browse_sound = QPushButton("Browse…")
        browse_sound.clicked.connect(self._browse_sound)
        custom_layout.addWidget(browse_sound)
        card_snd.add_row(SettingRow("Custom sound file", "Choose Custom WAV File above to use this file", custom_row))
        self.sw_siren_enabled = ToggleSwitch(checked=self.settings.get("sound_alarms_enabled", True))
        card_snd.add_row(SettingRow("Enable audible alerts", "Play the selected tone for alert events", self.sw_siren_enabled))
        self.sound_feedback = QLabel("")
        card_snd.layout.addWidget(self.sound_feedback)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._sound_preview_result)

        self.sw_motion_sound = ToggleSwitch(checked=self.settings.get("motion_sound", False))
        card_snd.add_row(SettingRow("Short Beep on Any Motion", "Subtle alert on motion even before subject confirmation", self.sw_motion_sound))

        self.sw_mute_startup = ToggleSwitch(checked=self.settings.get("mute_on_startup", False))
        card_snd.add_row(SettingRow("Launch App Muted", "Start application with sound muted for discretion", self.sw_mute_startup))

        layout.addWidget(card_snd)
        layout.addStretch(1)
        self.stack.addWidget(scroll)

    def _browse_sound(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose alert sound", "", "PCM WAV audio (*.wav)")
        if path:
            self.txt_custom_sound.setText(path)
            self.cmb_sound_profile.setCurrentIndex(self.cmb_sound_profile.findData(SoundProfile.CUSTOM))

    def _sound_preview_result(self):
        self.sound_feedback.setText(self.sound_manager.last_error or "Preview complete — output uses the Windows default playback device.")

    def _test_sound(self):
        if self.sound_manager:
            volume = self.slider_sound_vol.value()
            profile = self.cmb_sound_profile.currentData()
            custom = self.txt_custom_sound.text().strip()
            if profile == SoundProfile.CUSTOM and not os.path.isfile(custom):
                self.sound_feedback.setText("Choose an existing PCM WAV file first.")
                return
            self.sound_manager.play_test_tone(profile, volume, custom_path=custom)
            self.sound_feedback.setText("Muted" if volume == 0 else f"Playing preview at {volume}%…")
            self._preview_timer.start(1200)

    # -------------------------------------------------------------
    #  TAB 7: NIGHT MODE & CONTRAST
    # -------------------------------------------------------------
    def _build_tab_night(self):
        scroll, layout = self._create_scrollable_page()

        card_night = SettingCard("Night Visibility Enhancement", "Dynamic algorithms for maximum clarity in darkness")

        self.sw_clahe = ToggleSwitch(checked=self.settings.get("night_clahe_boost", True), active_color="#0284c7")
        card_night.add_row(SettingRow("Night Contrast Boost (CLAHE)", "Equalizes histogram to reveal faces and details in the dark", self.sw_clahe))

        self.sw_gamma = ToggleSwitch(checked=self.settings.get("night_gamma_lift", True))
        card_night.add_row(SettingRow("Shadow Gamma Lift", "Illuminates dark shadows without washing out lit areas", self.sw_gamma))

        self.sw_night_auto = ToggleSwitch(checked=self.settings.get("night_auto_switch", True))
        card_night.add_row(SettingRow("Automatic Day / Night Switching", "Detects low ambient light and activates filters automatically", self.sw_night_auto))

        layout.addWidget(card_night)
        layout.addStretch(1)
        self.stack.addWidget(scroll)

    # -------------------------------------------------------------
    #  TAB 8: WIND STABILIZATION FILTER
    # -------------------------------------------------------------
    def _build_tab_wind(self):
        scroll, layout = self._create_scrollable_page()

        card_wind = SettingCard("Wind & Camera Oscillation Filter", "Filters out false alarms caused by shaking camera poles or wind-blown branches")

        self.sw_wind_enabled = ToggleSwitch(checked=self.settings.get("wind_filter_enabled", True), active_color="#0284c7")
        card_wind.add_row(SettingRow("Enable Wind Filter", "Ignores periodic oscillations caused by wind gusts", self.sw_wind_enabled))

        self.sw_shield_fata = ToggleSwitch(checked=self.settings.get("shield_fata_wind", True))
        card_wind.add_row(SettingRow("Priority Protection for Wide / Exposed Lens", "Special stabilization profile for wide lens exposed to branches", self.sw_shield_fata))

        self.slider_wind_tol = QSlider(Qt.Orientation.Horizontal)
        self.slider_wind_tol.setRange(1, 10)
        self.slider_wind_tol.setValue(int(float(self.settings.get("wind_tolerance", 0.5)) * 10))
        self.slider_wind_tol.setFixedWidth(140)
        lbl_tol_val = QLabel(f"{self.slider_wind_tol.value() / 10.0:.1f}")
        lbl_tol_val.setStyleSheet("font-weight: 700; color: #38bdf8; min-width: 35px;")
        self.slider_wind_tol.valueChanged.connect(lambda v: lbl_tol_val.setText(f"{v / 10.0:.1f}"))
        tol_box = QWidget()
        tb_lay = QHBoxLayout(tol_box)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.addWidget(self.slider_wind_tol)
        tb_lay.addWidget(lbl_tol_val)
        card_wind.add_row(SettingRow("Oscillation Tolerance", "Higher values tolerate stronger wind gusts", tol_box))

        layout.addWidget(card_wind)
        layout.addStretch(1)
        self.stack.addWidget(scroll)

    # -------------------------------------------------------------
    #  SAVE, DIRTY TRACKING & EXPORT
    # -------------------------------------------------------------
    def _commit_and_save_data(self):
        # Automatically commit connection parameters for active camera if loaded
        if hasattr(self, "_apply_active_camera_connection"):
            self._apply_active_camera_connection()

        res = {
            "auto_check_updates": self.sw_auto_updates.isChecked(),
            # Appearance
            "theme": self.settings.get("theme", "Cyber Dark"),
            "default_layout": self.cmb_layout.currentData() if hasattr(self, "cmb_layout") else self.settings.get("default_layout", "2x2"),
            "show_hud_clock": self.sw_hud_clock.isChecked() if hasattr(self, "sw_hud_clock") else False,
            "show_hud_camera_name": self.sw_hud_cam_name.isChecked() if hasattr(self, "sw_hud_cam_name") else False,
            "show_hud_wifi": self.sw_hud_wifi.isChecked() if hasattr(self, "sw_hud_wifi") else True,
            "close_action": self.cmb_close_action.currentData() if hasattr(self, "cmb_close_action") else "ask",
            "remember_close_action": (self.cmb_close_action.currentData() != "ask") if hasattr(self, "cmb_close_action") else False,

            # Notifications & Security
            "master_alerts_enabled": self.sw_master_alerts.isChecked() if hasattr(self, "sw_master_alerts") else True,
            "phone_notifications_enabled": self.sw_phone_enabled.isChecked() if hasattr(self, "sw_phone_enabled") else False,
            "outgoing_notification_categories": [category for category, switch in self.outgoing_category_switches.items() if switch.isChecked()],
            "notify_person": self.sw_notify_person.isChecked() if hasattr(self, "sw_notify_person") else False,
            "notify_vehicle": self.sw_notify_vehicle.isChecked() if hasattr(self, "sw_notify_vehicle") else False,
            "notify_animal": self.sw_notify_animal.isChecked() if hasattr(self, "sw_notify_animal") else False,
            "notify_motion": self.sw_notify_motion.isChecked() if hasattr(self, "sw_notify_motion") else False,
            "ntfy_enabled": self.sw_ntfy_enabled.isChecked() if hasattr(self, "sw_ntfy_enabled") else False,
            "ntfy_topic": self.txt_ntfy_topic.text().strip() if hasattr(self, "txt_ntfy_topic") else "",
            "send_video_to_phone": self.sw_send_video.isChecked() if hasattr(self, "sw_send_video") else False,
            "phone_notify_video": self.sw_send_video.isChecked() if hasattr(self, "sw_send_video") else False,
            "telegram_enabled": self.sw_telegram_enabled.isChecked() if hasattr(self, "sw_telegram_enabled") else False,
            "telegram_token": self.txt_tg_token.text().strip() if hasattr(self, "txt_tg_token") else "",
            "telegram_chat_id": self.txt_tg_chat.text().strip() if hasattr(self, "txt_tg_chat") else "",
            "show_desktop_notifications": self.sw_desktop_toasts.isChecked() if hasattr(self, "sw_desktop_toasts") else False,
            "notification_duration_sec": self.slider_toast_dur.value() if hasattr(self, "slider_toast_dur") else 5,

            # AI & Motion
            "ai_detection_enabled": self.sw_ai_enabled.isChecked() if hasattr(self, "sw_ai_enabled") else False,
            "enable_smart_descriptions": self.sw_smart_desc.isChecked() if hasattr(self, "sw_smart_desc") else False,
            "ai_conf_threshold": float(self.slider_ai_conf.value()) / 100.0 if hasattr(self, "slider_ai_conf") else 0.40,
            "motion_min_area": self.slider_min_area.value() if hasattr(self, "slider_min_area") else 2800,
            "motion_foliage_filter": self.sw_foliage_filter.isChecked() if hasattr(self, "sw_foliage_filter") else True,
            "motion_confirm_delay": self.spin_motion_confirm.value(),
            "detection_confirm_sec": self.spin_ai_confirm.value(),
            "motion_hold_sec": self.spin_motion_hold.value(),
            "motion_cooldown_sec": float(self.slider_cooldown.value()) if hasattr(self, "slider_cooldown") else 3.0,

            # Storage & GDrive
            "recording_dir": self.txt_rec_dir.text().strip() if hasattr(self, "txt_rec_dir") and self.txt_rec_dir.text().strip() else "recordings",
            "snapshot_dir": self.txt_snap_dir.text().strip() if hasattr(self, "txt_snap_dir") and self.txt_snap_dir.text().strip() else "snapshots",
            "pre_alarm_buffer_sec": self.slider_pre_buf.value() if hasattr(self, "slider_pre_buf") else 5,
            "alert_clip_duration_sec": self.slider_clip_dur.value() if hasattr(self, "slider_clip_dur") else 15,
            "record_dual_clips": self.sw_dual_clips.isChecked() if hasattr(self, "sw_dual_clips") else False,
            "record_audio_in_clips": self.sw_clip_audio.isChecked() if hasattr(self, "sw_clip_audio") else False,
            "retention_days": self.cmb_retention.currentData() if hasattr(self, "cmb_retention") else 7,
            "auto_clean_on_startup": self.sw_auto_clean.isChecked() if hasattr(self, "sw_auto_clean") else True,

            # Performance & Quality
            "default_quality": self.cmb_default_quality.currentData() if hasattr(self, "cmb_default_quality") else "MAX",
            "performance_profile": self.cmb_perf_profile.currentData() if hasattr(self, "cmb_perf_profile") else "balanced",
            "show_performance_prompt_on_startup": self.sw_show_perf_prompt.isChecked() if hasattr(self, "sw_show_perf_prompt") else False,
            "ai_motion_gated_only": self.sw_ai_motion_gated.isChecked() if hasattr(self, "sw_ai_motion_gated") else True,
            "ai_skip_frames": self.slider_ai_skip.value() if hasattr(self, "slider_ai_skip") else 1,
            "display_fps_cap": self.cmb_display_fps.currentData() if hasattr(self, "cmb_display_fps") else 25,

            # Sound
            "sound_profile": self.cmb_sound_profile.currentData() if hasattr(self, "cmb_sound_profile") else "cyber_chime",
            "custom_sound_path": self.txt_custom_sound.text().strip(),
            "sound_alarms_enabled": self.sw_siren_enabled.isChecked(),
            "sound_volume": self.slider_sound_vol.value() if hasattr(self, "slider_sound_vol") else 80,
            "motion_sound": self.sw_motion_sound.isChecked() if hasattr(self, "sw_motion_sound") else False,
            "mute_on_startup": self.sw_mute_startup.isChecked() if hasattr(self, "sw_mute_startup") else False,

            # Night & Contrast
            "night_clahe_boost": self.sw_clahe.isChecked() if hasattr(self, "sw_clahe") else False,
            "night_gamma_lift": self.sw_gamma.isChecked() if hasattr(self, "sw_gamma") else False,
            "night_auto_switch": self.sw_night_auto.isChecked() if hasattr(self, "sw_night_auto") else False,

            # Wind
            "wind_filter_enabled": self.sw_wind_enabled.isChecked() if hasattr(self, "sw_wind_enabled") else False,
            "shield_fata_wind": self.sw_shield_fata.isChecked() if hasattr(self, "sw_shield_fata") else False,
            "wind_tolerance": float(self.slider_wind_tol.value()) / 10.0 if hasattr(self, "slider_wind_tol") else 1.5,

            # Camera Overrides & Updated Cameras
            "camera_overrides": self.camera_overrides,
            "updated_cameras": self.cameras
        }

        # Keep existing untouched values
        for k, v in self.settings.items():
            if k not in res:
                res[k] = v

        self.settings_saved.emit(res)
        self._initial_state = self._capture_current_dialog_state()

    def _save_settings(self):
        self._commit_and_save_data()
        super().accept()

    def _capture_current_dialog_state(self) -> dict:
        # Build active camera state from controls if available
        active_cam_state = {}
        if hasattr(self, "cmb_active_cam") and hasattr(self, "txt_cam_name"):
            cid = self.cmb_active_cam.currentData()
            active_cam_state = {
                "cid": cid,
                "name": self.txt_cam_name.text().strip(),
                "ip": self.txt_cam_ip.text().strip(),
                "port": self.spin_cam_port.value() if hasattr(self, "spin_cam_port") else 554,
                "user": self.txt_cam_user.text().strip() if hasattr(self, "txt_cam_user") else "admin",
                "pass": self.txt_cam_pass.text() if hasattr(self, "txt_cam_pass") else "",
                "dual": self.sw_cam_dual.isChecked() if hasattr(self, "sw_cam_dual") else False,
                "url1": self.txt_cam_url1.text().strip() if hasattr(self, "txt_cam_url1") else "",
                "url2": self.txt_cam_url2.text().strip() if hasattr(self, "txt_cam_url2") else "",
                "flip": self.sw_cam_flip.isChecked() if hasattr(self, "sw_cam_flip") else False,
                "fps": self.cmb_cam_fps.currentData() if hasattr(self, "cmb_cam_fps") else 0,
                "ai": self.sw_cam_ai.isChecked() if hasattr(self, "sw_cam_ai") else True,
            }

        return {
            "default_layout": self.cmb_layout.currentData() if hasattr(self, "cmb_layout") else "",
            "auto_check_updates": self.sw_auto_updates.isChecked(),
            "show_hud_clock": self.sw_hud_clock.isChecked() if hasattr(self, "sw_hud_clock") else False,
            "show_hud_camera_name": self.sw_hud_cam_name.isChecked() if hasattr(self, "sw_hud_cam_name") else False,
            "show_hud_wifi": self.sw_hud_wifi.isChecked() if hasattr(self, "sw_hud_wifi") else False,
            "close_action": self.cmb_close_action.currentData() if hasattr(self, "cmb_close_action") else "",

            "master_alerts_enabled": self.sw_master_alerts.isChecked() if hasattr(self, "sw_master_alerts") else True,
            "phone_notifications_enabled": self.sw_phone_enabled.isChecked() if hasattr(self, "sw_phone_enabled") else False,
            "outgoing_notification_categories": [category for category, switch in self.outgoing_category_switches.items() if switch.isChecked()],
            "notify_person": self.sw_notify_person.isChecked() if hasattr(self, "sw_notify_person") else False,
            "notify_vehicle": self.sw_notify_vehicle.isChecked() if hasattr(self, "sw_notify_vehicle") else False,
            "notify_animal": self.sw_notify_animal.isChecked() if hasattr(self, "sw_notify_animal") else False,
            "notify_motion": self.sw_notify_motion.isChecked() if hasattr(self, "sw_notify_motion") else False,
            "ntfy_enabled": self.sw_ntfy_enabled.isChecked() if hasattr(self, "sw_ntfy_enabled") else False,
            "ntfy_topic": self.txt_ntfy_topic.text().strip() if hasattr(self, "txt_ntfy_topic") else "",
            "send_video_to_phone": self.sw_send_video.isChecked() if hasattr(self, "sw_send_video") else False,
            "telegram_enabled": self.sw_telegram_enabled.isChecked() if hasattr(self, "sw_telegram_enabled") else False,
            "telegram_token": self.txt_tg_token.text().strip() if hasattr(self, "txt_tg_token") else "",
            "telegram_chat_id": self.txt_tg_chat.text().strip() if hasattr(self, "txt_tg_chat") else "",
            "show_desktop_notifications": self.sw_desktop_toasts.isChecked() if hasattr(self, "sw_desktop_toasts") else False,
            "notification_duration_sec": self.slider_toast_dur.value() if hasattr(self, "slider_toast_dur") else 5,

            "ai_detection_enabled": self.sw_ai_enabled.isChecked() if hasattr(self, "sw_ai_enabled") else False,
            "enable_smart_descriptions": self.sw_smart_desc.isChecked() if hasattr(self, "sw_smart_desc") else False,
            "ai_conf_threshold": self.slider_ai_conf.value() if hasattr(self, "slider_ai_conf") else 40,
            "motion_min_area": self.slider_min_area.value() if hasattr(self, "slider_min_area") else 2800,
            "motion_foliage_filter": self.sw_foliage_filter.isChecked() if hasattr(self, "sw_foliage_filter") else True,
            "motion_confirm_delay": self.spin_motion_confirm.value(),
            "detection_confirm_sec": self.spin_ai_confirm.value(),
            "motion_hold_sec": self.spin_motion_hold.value(),
            "motion_cooldown_sec": self.slider_cooldown.value() if hasattr(self, "slider_cooldown") else 3,

            "recording_dir": self.txt_rec_dir.text().strip() if hasattr(self, "txt_rec_dir") else "",
            "snapshot_dir": self.txt_snap_dir.text().strip() if hasattr(self, "txt_snap_dir") else "",
            "pre_alarm_buffer_sec": self.slider_pre_buf.value() if hasattr(self, "slider_pre_buf") else 5,
            "alert_clip_duration_sec": self.slider_clip_dur.value() if hasattr(self, "slider_clip_dur") else 15,
            "record_dual_clips": self.sw_dual_clips.isChecked() if hasattr(self, "sw_dual_clips") else False,
            "record_audio_in_clips": self.sw_clip_audio.isChecked() if hasattr(self, "sw_clip_audio") else False,
            "retention_days": self.cmb_retention.currentData() if hasattr(self, "cmb_retention") else 7,
            "auto_clean_on_startup": self.sw_auto_clean.isChecked() if hasattr(self, "sw_auto_clean") else True,

            "default_quality": self.cmb_default_quality.currentData() if hasattr(self, "cmb_default_quality") else "MAX",
            "performance_profile": self.cmb_perf_profile.currentData() if hasattr(self, "cmb_perf_profile") else "balanced",
            "show_performance_prompt_on_startup": self.sw_show_perf_prompt.isChecked() if hasattr(self, "sw_show_perf_prompt") else False,
            "ai_motion_gated_only": self.sw_ai_motion_gated.isChecked() if hasattr(self, "sw_ai_motion_gated") else True,
            "ai_skip_frames": self.slider_ai_skip.value() if hasattr(self, "slider_ai_skip") else 1,
            "display_fps_cap": self.cmb_display_fps.currentData() if hasattr(self, "cmb_display_fps") else 25,

            "sound_profile": self.cmb_sound_profile.currentData() if hasattr(self, "cmb_sound_profile") else "cyber_chime",
            "custom_sound_path": self.txt_custom_sound.text().strip(),
            "sound_alarms_enabled": self.sw_siren_enabled.isChecked(),
            "sound_volume": self.slider_sound_vol.value() if hasattr(self, "slider_sound_vol") else 80,
            "motion_sound": self.sw_motion_sound.isChecked() if hasattr(self, "sw_motion_sound") else False,
            "mute_on_startup": self.sw_mute_startup.isChecked() if hasattr(self, "sw_mute_startup") else False,

            "night_clahe_boost": self.sw_clahe.isChecked() if hasattr(self, "sw_clahe") else False,
            "night_gamma_lift": self.sw_gamma.isChecked() if hasattr(self, "sw_gamma") else False,
            "night_auto_switch": self.sw_night_auto.isChecked() if hasattr(self, "sw_night_auto") else False,

            "wind_filter_enabled": self.sw_wind_enabled.isChecked() if hasattr(self, "sw_wind_enabled") else False,
            "shield_fata_wind": self.sw_shield_fata.isChecked() if hasattr(self, "sw_shield_fata") else False,
            "wind_tolerance": self.slider_wind_tol.value() if hasattr(self, "slider_wind_tol") else 15,

            "active_cam_state": active_cam_state,
            "cameras_dump": json.dumps(self.cameras, sort_keys=True, default=str),
            "overrides_dump": json.dumps(self.camera_overrides, sort_keys=True, default=str)
        }

    def has_unsaved_changes(self) -> bool:
        if not hasattr(self, "_initial_state") or self._initial_state is None:
            return False
        return self._capture_current_dialog_state() != self._initial_state

    def _prompt_unsaved_changes(self) -> str:
        dlg = UnsavedChangesPromptDialog(self)
        dlg.exec()
        return dlg.user_action

    def reject(self):
        if self.has_unsaved_changes():
            action = self._prompt_unsaved_changes()
            if action == "save":
                self._commit_and_save_data()
                super().accept()
            elif action == "discard":
                super().reject()
            else:
                return  # Stay in dialog
        else:
            super().reject()

    def done(self, result):
        if self.test_worker is not None and self.test_worker.isRunning():
            self.test_worker.cancel()
        super().done(result)

    def closeEvent(self, event):
        if self.has_unsaved_changes():
            action = self._prompt_unsaved_changes()
            if action == "save":
                self._commit_and_save_data()
                event.accept()
            elif action == "discard":
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
        if event.isAccepted() and self.test_worker is not None and self.test_worker.isRunning():
            self.test_worker.cancel()

