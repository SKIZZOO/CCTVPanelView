"""
CCTVPanelView - Windows 11 & Settings-Style Recordings & Incident Studio.
Features:
- Left Vertical Sidebar Navigation matching SettingsDialog layout (Libraries, Per-Camera Filters, Cloud Storage).
- Center High-Performance Media Feed with 16:9 cards, instant search, and smart date filters.
- Right Card-Based Inspector with 100% full-frame uncropped high-definition preview (zero shrunk boxes or burned borders).
- Translucent glass OSD badges for AI detections.
- Cloud storage and local storage synchronization with instant indexing.
"""

import os
import glob
import re
import time
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

import cv2
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox,
    QLineEdit, QComboBox, QSplitter, QWidget, QFrame, QScrollArea,
    QRadioButton, QButtonGroup, QDialogButtonBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal, QRect, QRectF, QPointF
from PyQt6.QtGui import (
    QIcon, QPixmap, QImage, QPainter, QColor, QFont, QImageReader,
    QPen, QBrush, QPainterPath, QPolygonF, QLinearGradient
)


def format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def create_gallery_vector_icon(icon_type: str, color: str = "#38bdf8", size: int = 16) -> QIcon:
    """Renders crisp vector icons for the CCTV recordings studio."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    fg = QColor(color)
    pen = QPen(fg, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    if icon_type in ("all", "all_media"):
        s = size * 0.32
        p.drawRoundedRect(QRectF(size * 0.12, size * 0.12, s, s), 1.5, 1.5)
        p.drawRoundedRect(QRectF(size * 0.56, size * 0.12, s, s), 1.5, 1.5)
        p.drawRoundedRect(QRectF(size * 0.12, size * 0.56, s, s), 1.5, 1.5)
        p.drawRoundedRect(QRectF(size * 0.56, size * 0.56, s, s), 1.5, 1.5)
    elif icon_type in ("alerts", "incident"):
        path = QPainterPath()
        path.moveTo(size * 0.50, size * 0.12)
        path.lineTo(size * 0.85, size * 0.25)
        path.quadTo(size * 0.85, size * 0.65, size * 0.50, size * 0.90)
        path.quadTo(size * 0.15, size * 0.65, size * 0.15, size * 0.25)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(int(size * 0.50), int(size * 0.35), int(size * 0.50), int(size * 0.55))
        p.drawEllipse(QPointF(size * 0.50, size * 0.70), 0.7, 0.7)
    elif icon_type == "motion":
        p.drawArc(QRectF(size * 0.10, size * 0.10, size * 0.80, size * 0.80), int(30 * 16), int(120 * 16))
        p.drawArc(QRectF(size * 0.25, size * 0.25, size * 0.50, size * 0.50), int(30 * 16), int(120 * 16))
        p.setBrush(QBrush(fg))
        p.drawEllipse(QPointF(size * 0.50, size * 0.65), size * 0.12, size * 0.12)
    elif icon_type in ("snapshots", "snapshot", "photo"):
        p.drawRoundedRect(QRectF(size * 0.12, size * 0.28, size * 0.76, size * 0.58), 2.5, 2.5)
        p.drawRoundedRect(QRectF(size * 0.32, size * 0.14, size * 0.36, size * 0.14), 1.5, 1.5)
        p.drawEllipse(QPointF(size * 0.50, size * 0.57), size * 0.18, size * 0.18)
    elif icon_type == "camera":
        p.drawRoundedRect(QRectF(size * 0.12, size * 0.26, size * 0.52, size * 0.36), 2, 2)
        path = QPainterPath()
        path.moveTo(size * 0.64, size * 0.34)
        path.lineTo(size * 0.86, size * 0.24)
        path.lineTo(size * 0.86, size * 0.64)
        path.lineTo(size * 0.64, size * 0.54)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(int(size * 0.32), int(size * 0.62), int(size * 0.32), int(size * 0.80))
        p.drawLine(int(size * 0.18), int(size * 0.80), int(size * 0.46), int(size * 0.80))
    elif icon_type == "drive":
        path = QPainterPath()
        path.moveTo(size * 0.22, size * 0.72)
        path.lineTo(size * 0.78, size * 0.72)
        path.quadTo(size * 0.90, size * 0.72, size * 0.88, size * 0.58)
        path.quadTo(size * 0.86, size * 0.44, size * 0.72, size * 0.42)
        path.quadTo(size * 0.68, size * 0.20, size * 0.48, size * 0.20)
        path.quadTo(size * 0.30, size * 0.20, size * 0.26, size * 0.40)
        path.quadTo(size * 0.12, size * 0.44, size * 0.12, size * 0.58)
        path.quadTo(size * 0.12, size * 0.72, size * 0.22, size * 0.72)
        p.drawPath(path)
    elif icon_type == "prune":
        p.drawLine(int(size * 0.18), int(size * 0.28), int(size * 0.82), int(size * 0.28))
        p.drawRoundedRect(QRectF(size * 0.36, size * 0.14, size * 0.28, size * 0.14), 1, 1)
        path = QPainterPath()
        path.moveTo(size * 0.25, size * 0.28)
        path.lineTo(size * 0.30, size * 0.84)
        path.quadTo(size * 0.31, size * 0.88, size * 0.36, size * 0.88)
        path.lineTo(size * 0.64, size * 0.88)
        path.quadTo(size * 0.69, size * 0.88, size * 0.70, size * 0.84)
        path.lineTo(size * 0.75, size * 0.28)
        p.drawPath(path)
        p.drawLine(int(size * 0.42), int(size * 0.40), int(size * 0.42), int(size * 0.74))
        p.drawLine(int(size * 0.58), int(size * 0.40), int(size * 0.58), int(size * 0.74))
    elif icon_type == "refresh":
        p.drawArc(QRectF(size * 0.16, size * 0.16, size * 0.68, size * 0.68), int(45 * 16), int(260 * 16))
        path = QPainterPath()
        path.moveTo(size * 0.78, size * 0.30)
        path.lineTo(size * 0.86, size * 0.45)
        path.lineTo(size * 0.70, size * 0.45)
        path.closeSubpath()
        p.setBrush(QBrush(fg))
        p.drawPath(path)
    elif icon_type == "clock":
        p.drawEllipse(QRectF(size * 0.14, size * 0.14, size * 0.72, size * 0.72))
        p.drawLine(int(size * 0.50), int(size * 0.26), int(size * 0.50), int(size * 0.50))
        p.drawLine(int(size * 0.50), int(size * 0.50), int(size * 0.70), int(size * 0.50))
    elif icon_type == "specs":
        p.drawRoundedRect(QRectF(size * 0.12, size * 0.16, size * 0.76, size * 0.52), 2, 2)
        p.drawLine(int(size * 0.50), int(size * 0.68), int(size * 0.50), int(size * 0.82))
        p.drawLine(int(size * 0.30), int(size * 0.82), int(size * 0.70), int(size * 0.82))
    elif icon_type == "storage":
        p.drawEllipse(QRectF(size * 0.18, size * 0.16, size * 0.64, size * 0.24))
        p.drawLine(int(size * 0.18), int(size * 0.28), int(size * 0.18), int(size * 0.72))
        p.drawLine(int(size * 0.82), int(size * 0.28), int(size * 0.82), int(size * 0.72))
        p.drawArc(QRectF(size * 0.18, size * 0.60, size * 0.64, size * 0.24), int(180 * 16), int(180 * 16))
    elif icon_type == "play":
        cx, cy = size * 0.50, size * 0.50
        p.drawEllipse(QRectF(size * 0.10, size * 0.10, size * 0.80, size * 0.80))
        p.setBrush(QBrush(fg))
        tri = QPolygonF([QPointF(cx - size * 0.10, cy - size * 0.18), QPointF(cx + size * 0.18, cy), QPointF(cx - size * 0.10, cy + size * 0.18)])
        p.drawPolygon(tri)
    p.end()
    return QIcon(pix)


class GallerySettingCard(QFrame):
    """Clean rounded card container matching SettingsDialog aesthetic."""
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            GallerySettingCard {
                background-color: #121826;
                border: 1px solid #222d42;
                border-radius: 10px;
            }
        """)
        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(14, 12, 14, 12)
        self.card_layout.setSpacing(8)

        if title:
            lbl_title = QLabel(title, self)
            lbl_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #f1f5f9; background: transparent;")
            self.card_layout.addWidget(lbl_title)

    def add_widget(self, w: QWidget):
        self.card_layout.addWidget(w)


class GalleryDialog(QDialog):
    """
    CCTVPanelView Recordings & Incident Studio:
    Windows 11 Fluent / Settings-Style Split Dual-Pane Media Browser & Inspector.
    """
    def __init__(
        self,
        snapshot_dir: str = "snapshots",
        recording_dir: str = "recordings",
        google_drive_dir: Optional[str] = None,
        alert_manager: Optional[Any] = None,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("CCTVPanelView - Recordings & Incident Studio")
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(1180, 740)
        self.setMinimumSize(940, 580)

        self.alert_manager = alert_manager
        self.gdrive_dir = os.path.abspath(google_drive_dir or recording_dir or "recordings")
        self.configured_rec_dir = os.path.abspath(recording_dir or "recordings")
        self.configured_snap_dir = os.path.abspath(snapshot_dir or "snapshots")

        # In-memory thumbnail and preview cache
        self._thumb_cache: Dict[str, QPixmap] = {}
        self._preview_cache: Dict[str, QPixmap] = {}
        self.all_items: List[Dict[str, Any]] = []
        self.filtered_items: List[Dict[str, Any]] = []
        self.current_selected_item: Optional[Dict[str, Any]] = None

        # Active filter states
        self.active_category = "all"        # all, alerts, motion, snapshots
        self.active_camera_filter = "all"   # all, or camera name

        self._setup_ui()
        self.refresh_media()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                color: #f1f5f9;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QLabel {
                color: #e2e8f0;
            }
            QLineEdit {
                background-color: #141b2d;
                border: 1px solid #25334c;
                border-radius: 8px;
                color: #f8fafc;
                padding: 7px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
                background-color: #182239;
            }
            QComboBox {
                background-color: #141b2d;
                border: 1px solid #25334c;
                border-radius: 8px;
                color: #f8fafc;
                padding: 6px 12px;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #3b82f6;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QListWidget#gallery_sidebar {
                background-color: #080d1a;
                border: none;
                border-right: 1px solid rgba(255, 255, 255, 0.06);
                padding: 10px 6px;
            }
            QListWidget#gallery_sidebar::item {
                color: #94a3b8;
                font-weight: 600;
                font-size: 12px;
                padding: 9px 12px;
                border-radius: 8px;
                margin: 2px 4px;
                border: 1px solid transparent;
            }
            QListWidget#gallery_sidebar::item:hover:!selected {
                background-color: rgba(255, 255, 255, 0.05);
                color: #f1f5f9;
            }
            QListWidget#gallery_sidebar::item:selected {
                background-color: rgba(56, 189, 248, 0.14);
                color: #ffffff;
                font-weight: 700;
                border: 1px solid rgba(56, 189, 248, 0.40);
            }
            QListWidget#media_list {
                background-color: #0b0f19;
                border: none;
                padding: 8px;
            }
            QListWidget#media_list::item {
                background-color: #111726;
                border: 1px solid #1e293b;
                border-radius: 10px;
                margin: 4px 2px;
                padding: 10px;
            }
            QListWidget#media_list::item:hover:!selected {
                background-color: #162035;
                border-color: #38bdf8;
            }
            QListWidget#media_list::item:selected {
                background-color: #172544;
                border: 1px solid #38bdf8;
            }
            QPushButton {
                background-color: #182238;
                border: 1px solid #2b3954;
                border-radius: 8px;
                color: #f8fafc;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #23314d;
                border-color: #38bdf8;
            }
            QScrollBar:vertical {
                background: #0a0e18;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #24324c;
                min-height: 24px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #38bdf8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 14, 16, 14)
        root_layout.setSpacing(10)

        # 1. Top Header Bar
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_png = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.png")
        if os.path.exists(icon_png):
            lbl_logo = QLabel(self)
            lbl_logo.setPixmap(QPixmap(icon_png).scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            lbl_logo.setFixedSize(30, 30)
            lbl_logo.setStyleSheet("background: transparent;")
            header.addWidget(lbl_logo)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_title = QLabel("CCTV Video Recordings & Incidents Studio")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #38bdf8; letter-spacing: 0.3px;")
        title_col.addWidget(lbl_title)

        gdrive_status = "Storage Archive Active" if os.path.exists(self.configured_rec_dir) else "Ready"
        self.lbl_subtitle = QLabel(f"Storage: {gdrive_status} • Uncropped HD Full-Frame Previews")
        self.lbl_subtitle.setStyleSheet("font-size: 11px; color: #94a3b8;")
        title_col.addWidget(self.lbl_subtitle)
        header.addLayout(title_col)

        header.addStretch()

        btn_gdrive = QPushButton(" Open Storage Folder")
        btn_gdrive.setIcon(create_gallery_vector_icon("drive", color="#38bdf8", size=16))
        btn_gdrive.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.12);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 8px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.22);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        btn_gdrive.setToolTip("Open CCTV recordings directory in Windows File Explorer")
        btn_gdrive.clicked.connect(self._open_gdrive_folder)
        header.addWidget(btn_gdrive)

        btn_prune = QPushButton(" Clean && Prune Disk")
        btn_prune.setIcon(create_gallery_vector_icon("prune", color="#f87171", size=16))
        btn_prune.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.10);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.30);
                border-radius: 8px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.22);
                border-color: #ef4444;
                color: #fca5a5;
            }
        """)
        btn_prune.setToolTip("Free disk space by pruning older recordings or unindexed snapshots")
        btn_prune.clicked.connect(self._open_prune_dialog)
        header.addWidget(btn_prune)

        btn_refresh = QPushButton(" Refresh Library")
        btn_refresh.setIcon(create_gallery_vector_icon("refresh", color="#38bdf8", size=16))
        btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #0e1526;
                color: #cbd5e1;
                border: 1px solid #1a253a;
                border-radius: 8px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #162035;
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        btn_refresh.clicked.connect(self.refresh_media)
        header.addWidget(btn_refresh)

        root_layout.addLayout(header)

        # 2. Main Body Split: Left Sidebar + Center Media Feed + Right Card Inspector
        body_split = QHBoxLayout()
        body_split.setSpacing(12)

        # === LEFT SIDEBAR (SettingsDialog Style) ===
        self.sidebar = QListWidget(self)
        self.sidebar.setObjectName("gallery_sidebar")
        self.sidebar.setFixedWidth(220)
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar.currentRowChanged.connect(self._on_sidebar_item_changed)
        body_split.addWidget(self.sidebar)

        # === CENTER MEDIA BROWSER ===
        center_widget = QWidget(self)
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by camera, date, detection (Person, Vehicle, Bear)...")
        self.txt_search.setClearButtonEnabled(True)
        self.txt_search.textChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.txt_search, stretch=3)

        self.cmb_date = QComboBox()
        self.cmb_date.addItems(["All Dates", "Today", "Yesterday", "Last 7 Days", "Last 30 Days"])
        self.cmb_date.currentIndexChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.cmb_date, stretch=1)

        self.cmb_sort = QComboBox()
        self.cmb_sort.addItems(["Newest First", "Oldest First", "Largest File Size"])
        self.cmb_sort.currentIndexChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.cmb_sort, stretch=1)

        center_layout.addLayout(filter_bar)

        # Media List
        self.media_list = QListWidget(center_widget)
        self.media_list.setObjectName("media_list")
        self.media_list.setIconSize(QSize(136, 76))
        self.media_list.setSpacing(6)
        self.media_list.itemSelectionChanged.connect(self._on_item_selected)
        self.media_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        center_layout.addWidget(self.media_list, stretch=1)

        body_split.addWidget(center_widget, stretch=1)

        # === RIGHT CARD INSPECTOR (SettingCard Aesthetic) ===
        self.inspector_scroll = QScrollArea(self)
        self.inspector_scroll.setFixedWidth(370)
        self.inspector_scroll.setWidgetResizable(True)
        self.inspector_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.inspector_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.inspector_scroll.setStyleSheet("background: transparent;")

        insp_content = QWidget()
        insp_content.setStyleSheet("background: transparent;")
        insp_layout = QVBoxLayout(insp_content)
        insp_layout.setContentsMargins(0, 0, 0, 0)
        insp_layout.setSpacing(10)

        # --- Card 1: High-Definition Full-Frame Preview ---
        card_preview = GallerySettingCard("", insp_content)
        card_preview.card_layout.setContentsMargins(10, 10, 10, 10)

        # Preview Container
        self.preview_container = QWidget(card_preview)
        self.preview_container.setFixedSize(340, 191)
        self.preview_container.setStyleSheet("""
            QWidget {
                background-color: #060911;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
        """)
        p_box = QVBoxLayout(self.preview_container)
        p_box.setContentsMargins(0, 0, 0, 0)

        self.lbl_preview_thumb = QLabel(self.preview_container)
        self.lbl_preview_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_thumb.setStyleSheet("background: transparent; border: none;")
        self.lbl_preview_thumb.setText("Select a recording to preview")
        p_box.addWidget(self.lbl_preview_thumb)

        card_preview.add_widget(self.preview_container)
        insp_layout.addWidget(card_preview)

        # --- Card 2: Incident Telemetry & Details ---
        self.card_details = GallerySettingCard("Incident Telemetry & Details", insp_content)

        self.lbl_meta_cam = self._create_telemetry_row("Camera", "-", "camera")
        self.lbl_meta_event = self._create_telemetry_row("Trigger Event", "-", "alerts")
        self.lbl_meta_time = self._create_telemetry_row("Timestamp", "-", "clock")
        self.lbl_meta_specs = self._create_telemetry_row("Specs & FPS", "-", "specs")
        self.lbl_meta_size = self._create_telemetry_row("File Size", "-", "storage")
        self.lbl_meta_storage = self._create_telemetry_row("Storage Path", "-", "drive")

        insp_layout.addWidget(self.card_details)

        # --- Card 3: Action Buttons ---
        card_actions = GallerySettingCard("Actions", insp_content)

        self.btn_play_app = QPushButton(" Play Video in Studio")
        self.btn_play_app.setIcon(create_gallery_vector_icon("play", color="#ffffff", size=16))
        self.btn_play_app.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #2563eb);
                color: #ffffff;
                border: 1px solid #3b82f6;
                font-size: 13px;
                font-weight: 700;
                padding: 10px 16px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #3b82f6;
                border-color: #60a5fa;
            }
        """)
        self.btn_play_app.clicked.connect(self._play_selected_in_app)
        card_actions.add_widget(self.btn_play_app)

        self.btn_toggle_variant = QPushButton(" Toggle AI Boxed / Raw Video")
        self.btn_toggle_variant.clicked.connect(self._toggle_selected_variant)
        self.btn_toggle_variant.hide()
        card_actions.add_widget(self.btn_toggle_variant)

        self.btn_open_file_folder = QPushButton(" Reveal in Windows Explorer")
        self.btn_open_file_folder.setIcon(create_gallery_vector_icon("drive", color="#94a3b8", size=14))
        self.btn_open_file_folder.clicked.connect(self._show_selected_in_folder)
        card_actions.add_widget(self.btn_open_file_folder)

        self.btn_delete = QPushButton(" Delete Media File")
        self.btn_delete.setIcon(create_gallery_vector_icon("prune", color="#f87171", size=14))
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.12);
                border: 1px solid rgba(239, 68, 68, 0.35);
                color: #f87171;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.28);
                border-color: #ef4444;
                color: #ffffff;
            }
        """)
        self.btn_delete.clicked.connect(self._delete_selected)
        card_actions.add_widget(self.btn_delete)

        insp_layout.addWidget(card_actions)
        insp_layout.addStretch()

        self.inspector_scroll.setWidget(insp_content)
        body_split.addWidget(self.inspector_scroll)

        root_layout.addLayout(body_split, stretch=1)

        # 3. Footer Status Bar
        footer = QHBoxLayout()
        self.lbl_footer_status = QLabel("Loading media library...")
        self.lbl_footer_status.setStyleSheet("color: #94a3b8; font-size: 11px;")
        footer.addWidget(self.lbl_footer_status)
        footer.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)

        root_layout.addLayout(footer)

    def _create_telemetry_row(self, label: str, default_val: str, icon_type: str = "") -> QLabel:
        row_w = QWidget(self.card_details)
        row_w.setStyleSheet("""
            QWidget {
                background: transparent;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                padding-bottom: 4px;
            }
        """)
        row_l = QHBoxLayout(row_w)
        row_l.setContentsMargins(0, 3, 0, 3)
        row_l.setSpacing(6)

        if icon_type:
            lbl_ico = QLabel(row_w)
            lbl_ico.setPixmap(create_gallery_vector_icon(icon_type, color="#38bdf8", size=14).pixmap(14, 14))
            lbl_ico.setFixedSize(14, 14)
            lbl_ico.setStyleSheet("background: transparent; border: none;")
            row_l.addWidget(lbl_ico)

        lbl_k = QLabel(label, row_w)
        lbl_k.setFixedWidth(90)
        lbl_k.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8; background: transparent; border: none;")
        row_l.addWidget(lbl_k)

        lbl_v = QLabel(default_val, row_w)
        lbl_v.setWordWrap(True)
        lbl_v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl_v.setStyleSheet("font-size: 11px; font-weight: 700; color: #f1f5f9; background: transparent; border: none;")
        lbl_v.setMaximumWidth(220)
        row_l.addWidget(lbl_v, stretch=1)

        self.card_details.add_widget(row_w)
        return lbl_v

    def _build_sidebar(self, total_all: int, total_alerts: int, total_motion: int, total_snaps: int, cam_counts: Dict[str, int]):
        """Populates left vertical sidebar navigation matching SettingsDialog layout."""
        self.sidebar.blockSignals(True)
        self.sidebar.clear()

        # Section: Libraries
        hdr_lib = QListWidgetItem("LIBRARIES")
        hdr_lib.setFlags(Qt.ItemFlag.NoItemFlags)
        hdr_lib.setForeground(QColor(100, 116, 139))
        font_hdr = QFont("Segoe UI", 9, QFont.Weight.ExtraBold)
        hdr_lib.setFont(font_hdr)
        self.sidebar.addItem(hdr_lib)

        items_spec = [
            (f" All Media ({total_all:,})", "cat:all", "all"),
            (f" AI Incident Clips ({total_alerts:,})", "cat:alerts", "alerts"),
            (f" Motion Recordings ({total_motion:,})", "cat:motion", "motion"),
            (f" Photo Snapshots ({total_snaps:,})", "cat:snapshots", "snapshots"),
        ]
        for text, tag, icon_name in items_spec:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, tag)
            item.setIcon(create_gallery_vector_icon(icon_name, color="#94a3b8", size=16))
            self.sidebar.addItem(item)

        # Section: Filter by Camera
        hdr_cam = QListWidgetItem("FILTER BY CAMERA")
        hdr_cam.setFlags(Qt.ItemFlag.NoItemFlags)
        hdr_cam.setForeground(QColor(100, 116, 139))
        hdr_cam.setFont(font_hdr)
        self.sidebar.addItem(hdr_cam)

        it_all_cam = QListWidgetItem(f" All Cameras ({total_all:,})")
        it_all_cam.setData(Qt.ItemDataRole.UserRole, "cam:all")
        it_all_cam.setIcon(create_gallery_vector_icon("camera", color="#94a3b8", size=16))
        self.sidebar.addItem(it_all_cam)

        for cam_name, count in sorted(cam_counts.items(), key=lambda x: x[1], reverse=True):
            it_cam = QListWidgetItem(f" {cam_name} ({count:,})")
            it_cam.setData(Qt.ItemDataRole.UserRole, f"cam:{cam_name}")
            it_cam.setIcon(create_gallery_vector_icon("camera", color="#94a3b8", size=16))
            self.sidebar.addItem(it_cam)

        self.sidebar.blockSignals(False)

        # Restore active selection
        self._select_sidebar_tag(f"cat:{self.active_category}")

    def _select_sidebar_tag(self, target_tag: str):
        for i in range(self.sidebar.count()):
            it = self.sidebar.item(i)
            tag = it.data(Qt.ItemDataRole.UserRole)
            if tag == target_tag:
                self.sidebar.setCurrentItem(it)
                return
        # Fallback to row 1 (All Media)
        if self.sidebar.count() > 1:
            self.sidebar.setCurrentRow(1)

    def _on_sidebar_item_changed(self, row: int):
        it = self.sidebar.item(row)
        if not it:
            return
        tag = it.data(Qt.ItemDataRole.UserRole)
        if not tag or not isinstance(tag, str):
            return

        if tag.startswith("cat:"):
            self.active_category = tag[4:]
            self.active_camera_filter = "all"
        elif tag.startswith("cam:"):
            self.active_camera_filter = tag[4:]

        self._apply_filters()

    def refresh_media(self):
        """Discovers and indexes recordings across Google Drive and local storage with high performance."""
        self.all_items = []
        seen_paths = set()
        raw_entries = []

        candidate_dirs = [
            os.path.join(self.gdrive_dir, "recordings", "alarms"),
            os.path.join(self.gdrive_dir, "recordings"),
            os.path.join(self.gdrive_dir, "snapshots", "alarms"),
            os.path.join(self.gdrive_dir, "snapshots"),
            os.path.join(self.configured_rec_dir, "alarms"),
            self.configured_rec_dir,
            os.path.join(self.configured_snap_dir, "alarms"),
            self.configured_snap_dir,
        ]

        search_dirs = []
        for d in candidate_dirs:
            abs_d = os.path.abspath(d)
            if os.path.isdir(abs_d) and abs_d not in search_dirs:
                search_dirs.append(abs_d)

        # Fast scandir across folders
        for s_dir in search_dirs:
            try:
                for entry in os.scandir(s_dir):
                    if not entry.is_file():
                        continue
                    p = os.path.abspath(entry.path)
                    if p in seen_paths:
                        continue
                    fn_lower = entry.name.lower()
                    if fn_lower.startswith("tmp_") or fn_lower.startswith("."):
                        continue
                    is_vid = fn_lower.endswith((".mp4", ".mkv", ".avi", ".mov"))
                    is_snap = fn_lower.endswith((".jpg", ".jpeg", ".png"))
                    if not (is_vid or is_snap):
                        continue

                    seen_paths.add(p)
                    try:
                        st = entry.stat()
                        raw_entries.append((p, entry.name, st.st_size, st.st_mtime, is_vid, is_snap))
                    except Exception:
                        pass
            except Exception as e:
                print(f"[Gallery] Error scanning {s_dir}: {e}")

        self._raw_scanned_files = raw_entries

        # Sort descending by mtime (newest first)
        raw_entries.sort(key=lambda x: x[3], reverse=True)

        total_vids = sum(1 for x in raw_entries if x[4])
        total_snaps = sum(1 for x in raw_entries if x[5])
        total_alerts = sum(1 for x in raw_entries if ("alarms" in x[0].lower() or "ALARM" in x[1].upper() or "ALERT" in x[1].upper()))
        total_manual = max(0, total_vids - sum(1 for x in raw_entries if x[4] and ("alarms" in x[0].lower() or "ALARM" in x[1].upper() or "ALERT" in x[1].upper())))

        # Parse metadata for items
        cam_counts: Dict[str, int] = {}
        for p, fname, sz, mtime, is_vid, is_snap in raw_entries:
            item_data = self._parse_file_metadata(p, fname, sz, mtime, is_vid, is_snap)
            self.all_items.append(item_data)
            cname = item_data["camera_name"]
            cam_counts[cname] = cam_counts.get(cname, 0) + 1

        # Populate left sidebar
        self._build_sidebar(len(raw_entries), total_alerts, total_manual, total_snaps, cam_counts)
        self._apply_filters()

    def _parse_file_metadata(self, filepath: str, filename: str, size: int, mtime: float, is_vid: bool, is_snap: bool) -> Dict[str, Any]:
        dt = datetime.fromtimestamp(mtime)
        base, _ = os.path.splitext(filename)

        is_alert = (
            "alarms" in filepath.lower() or
            "ALARM" in filename.upper() or
            "ALERT" in filename.upper() or
            "_AI_BOXED" in filename.upper() or
            "_RAW" in filename.upper() or
            "_HIGHLIGHTED" in filename.upper()
        )

        is_gdrive = ("google drive" in filepath.lower() or "my drive" in filepath.lower() or filepath.upper().startswith("X:"))

        cam_name = "Camera"
        lens_name = "Lens 1"
        event_desc = "Motion Event"
        variant = "Video"

        clean = re.sub(r'^(CCTV_Snapshot_|CCTV_Manual_|CCTV_Motion_|CCTV_|ALARM_|REC_)', '', base, flags=re.IGNORECASE)

        if "_AI_BOXED" in filename.upper() or "_HIGHLIGHTED" in filename.upper():
            variant = "AI Boxed"
        elif "_RAW" in filename.upper():
            variant = "Raw Video"
        elif is_snap:
            variant = "Snapshot"
        elif "MANUAL" in filename.upper():
            variant = "Manual Rec"

        if "fata" in filename.lower():
            cam_name = "Fata (Dual-Lens 2K)"
        elif "afara" in filename.lower():
            cam_name = "Afara"
        elif "spate" in filename.lower():
            cam_name = "Spate"
        elif "camera9d85" in filename.lower():
            cam_name = "camera9D85"

        if "lens2" in filename.lower() or "fixedwide" in filename.lower():
            lens_name = "Lens 2 (Fixed Wide)"
        elif "lens1" in filename.lower() or "ptz" in filename.lower():
            lens_name = "Lens 1 (PTZ Zoom)"
        elif "main" in filename.lower():
            lens_name = "Main Stream"

        # Detection classification
        if "person" in filename.lower():
            m_pct = re.search(r'(\d+)pct', filename, re.IGNORECASE)
            pct_str = f" ({m_pct.group(1)}%)" if m_pct else ""
            event_desc = f"AI Person Detected{pct_str}"
        elif "vehicle" in filename.lower() or "car" in filename.lower():
            event_desc = "AI Vehicle Detected"
        elif "animal" in filename.lower() or "bear" in filename.lower() or "dog" in filename.lower():
            event_desc = "AI Animal Detected"
        elif "manual" in filename.lower():
            event_desc = "Manual Recording"
        elif "motion" in filename.lower():
            event_desc = "Motion Event"

        return {
            "path": filepath,
            "filename": filename,
            "size": size,
            "mtime": mtime,
            "date_obj": dt.date(),
            "date_str": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "is_video": is_vid,
            "is_snapshot": is_snap,
            "is_alert": is_alert,
            "is_gdrive": is_gdrive,
            "camera_name": cam_name,
            "lens": lens_name,
            "event_desc": event_desc,
            "variant": variant
        }

    def _apply_filters(self):
        query = self.txt_search.text().strip().lower()
        items = list(self.all_items)

        # 1. Category Filter from Left Sidebar
        if self.active_category == "alerts":
            items = [x for x in items if x["is_alert"] and x["is_video"]]
        elif self.active_category == "motion":
            items = [x for x in items if x["is_video"] and not x["is_alert"]]
        elif self.active_category == "snapshots":
            items = [x for x in items if x["is_snapshot"]]

        # 2. Camera Filter from Left Sidebar
        if self.active_camera_filter != "all":
            items = [x for x in items if x["camera_name"] == self.active_camera_filter]

        # 3. Date Filter ComboBox
        date_idx = self.cmb_date.currentIndex()
        today = date.today()
        if date_idx == 1:    # Today
            items = [x for x in items if x["date_obj"] == today]
        elif date_idx == 2:  # Yesterday
            yesterday = today - timedelta(days=1)
            items = [x for x in items if x["date_obj"] == yesterday]
        elif date_idx == 3:  # Last 7 Days
            cutoff = today - timedelta(days=7)
            items = [x for x in items if x["date_obj"] >= cutoff]
        elif date_idx == 4:  # Last 30 Days
            cutoff = today - timedelta(days=30)
            items = [x for x in items if x["date_obj"] >= cutoff]

        # 4. Search Query Filter
        if query:
            items = [
                x for x in items if (
                    query in x["filename"].lower() or
                    query in x["camera_name"].lower() or
                    query in x["event_desc"].lower() or
                    query in x["date_str"].lower() or
                    query in x["lens"].lower()
                )
            ]

        # 5. Sort Order
        sort_mode = self.cmb_sort.currentIndex()
        if sort_mode == 0:
            items.sort(key=lambda x: x["mtime"], reverse=True)
        elif sort_mode == 1:
            items.sort(key=lambda x: x["mtime"], reverse=False)
        elif sort_mode == 2:
            items.sort(key=lambda x: x["size"], reverse=True)

        self.filtered_items = items
        self._render_list()

    def _get_thumbnail(self, item: Dict[str, Any]) -> Optional[QPixmap]:
        """Returns 136x76 16:9 thumbnail with keyframe extraction, duration badge, and cinema styling."""
        path = item["path"]
        if path in self._thumb_cache:
            return self._thumb_cache[path]

        pix: Optional[QPixmap] = None

        # 1. Snapshots: load directly with hardware-scaled QImageReader
        if item["is_snapshot"] and os.path.exists(path):
            try:
                reader = QImageReader(path)
                reader.setScaledSize(QSize(136, 76))
                qimg = reader.read()
                if not qimg.isNull():
                    pix = QPixmap.fromImage(qimg)
            except Exception:
                pass

        # 2. Videos: check adjacent or paired snapshot
        if not pix and item["is_video"]:
            base_no_ext, _ = os.path.splitext(path)
            candidate_jpg = base_no_ext + ".jpg"
            if os.path.exists(candidate_jpg):
                try:
                    reader = QImageReader(candidate_jpg)
                    reader.setScaledSize(QSize(136, 76))
                    qimg = reader.read()
                    if not qimg.isNull():
                        pix = QPixmap.fromImage(qimg)
                except Exception:
                    pass

            if not pix:
                snap_cand = path.replace("\\recordings\\", "\\snapshots\\").replace("/recordings/", "/snapshots/")
                snap_cand_base, _ = os.path.splitext(snap_cand)
                snap_clean = re.sub(r'_(HIGHLIGHTED|AI_Boxed|RAW|Raw)$', '', snap_cand_base, flags=re.IGNORECASE) + ".jpg"
                if os.path.exists(snap_clean):
                    try:
                        reader = QImageReader(snap_clean)
                        reader.setScaledSize(QSize(136, 76))
                        qimg = reader.read()
                        if not qimg.isNull():
                            pix = QPixmap.fromImage(qimg)
                    except Exception:
                        pass

        # 3. Video keyframe extraction with OpenCV (VideoCapture)
        if not pix and item["is_video"] and os.path.exists(path) and item.get("size", 0) > 2048:
            try:
                cap = cv2.VideoCapture(path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                    total_f = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    target_frame = min(int(fps * 1.0), max(0, int(total_f - 1)))
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = rgb.shape
                        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
                        pix = QPixmap.fromImage(qimg).scaled(136, 76, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                        if pix.width() != 136 or pix.height() != 76:
                            x_off = max(0, (pix.width() - 136) // 2)
                            y_off = max(0, (pix.height() - 76) // 2)
                            pix = pix.copy(x_off, y_off, 136, 76)
            except Exception:
                pass

        # 4. Fallback: Sleek cinematic glass card with glowing blue play glyph (never raw [VIDEO] text!)
        if not pix:
            img = QImage(136, 76, QImage.Format.Format_ARGB32)
            img.fill(QColor(11, 15, 25))
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            grad = QLinearGradient(0, 0, 136, 76)
            grad.setColorAt(0, QColor(18, 24, 38))
            grad.setColorAt(1, QColor(10, 14, 23))
            p.setBrush(QBrush(grad))
            p.setPen(QPen(QColor(36, 48, 71), 1))
            p.drawRoundedRect(QRectF(1, 1, 134, 74), 6, 6)

            cx, cy = 68, 38
            p.setBrush(QBrush(QColor(29, 78, 216, 180)))
            p.setPen(QPen(QColor(56, 189, 248), 1.5))
            p.drawEllipse(QRectF(cx - 16, cy - 16, 32, 32))

            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.setPen(Qt.PenStyle.NoPen)
            tri = QPolygonF([QPointF(cx - 4, cy - 7), QPointF(cx + 8, cy), QPointF(cx - 4, cy + 7)])
            p.drawPolygon(tri)

            cam_short = item.get("camera_name", "CAM").split("(")[0].strip()[:14]
            p.setPen(QColor(148, 163, 184))
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.drawText(QRect(4, 56, 128, 16), Qt.AlignmentFlag.AlignCenter, cam_short)
            p.end()
            pix = QPixmap.fromImage(img)
        else:
            comp = QPixmap(pix)
            p = QPainter(comp)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            badge_text = "PHOTO" if item["is_snapshot"] else "11s"
            if item["is_video"]:
                approx_secs = max(5, min(120, int(item.get("size", 0) / (250 * 1024))))
                badge_text = f"{approx_secs}s"

            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            fm = p.fontMetrics()
            bw = fm.horizontalAdvance(badge_text) + 8
            bh = 16
            bx = 136 - bw - 6
            by = 76 - bh - 6

            p.setBrush(QBrush(QColor(0, 0, 0, 180)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(bx, by, bw, bh), 3, 3)

            p.setPen(QColor(241, 245, 249))
            p.drawText(QRect(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, badge_text)

            if item["is_video"]:
                cx, cy = 68, 38
                p.setBrush(QBrush(QColor(0, 0, 0, 120)))
                p.setPen(QPen(QColor(255, 255, 255, 180), 1))
                p.drawEllipse(QRectF(cx - 12, cy - 12, 24, 24))
                p.setBrush(QBrush(QColor(255, 255, 255, 230)))
                p.setPen(Qt.PenStyle.NoPen)
                tri = QPolygonF([QPointF(cx - 3, cy - 5), QPointF(cx + 5, cy), QPointF(cx - 3, cy + 5)])
                p.drawPolygon(tri)

            p.end()
            pix = comp

        self._thumb_cache[path] = pix
        return pix

    def _get_inspector_preview(self, item: Dict[str, Any]) -> Optional[QPixmap]:
        """
        Loads uncropped, full-resolution HD preview frame (340x191) with crystal clarity.
        Completely eliminates the shrunk inner box and blurry upscaling.
        """
        path = item["path"]
        if path in self._preview_cache:
            return self._preview_cache[path]

        # 1. For snapshots: load at 340x191 using QImageReader with smooth antialiasing
        if item["is_snapshot"] and os.path.exists(path):
            try:
                reader = QImageReader(path)
                reader.setScaledSize(QSize(340, 191))
                qimg = reader.read()
                if not qimg.isNull():
                    pix = QPixmap.fromImage(qimg)
                    self._preview_cache[path] = pix
                    return pix
            except Exception:
                pass

        # 2. For videos: check adjacent full-resolution snapshot
        base_no_ext, _ = os.path.splitext(path)
        candidate_jpg = base_no_ext + ".jpg"
        if os.path.exists(candidate_jpg):
            try:
                reader = QImageReader(candidate_jpg)
                reader.setScaledSize(QSize(340, 191))
                qimg = reader.read()
                if not qimg.isNull():
                    pix = QPixmap.fromImage(qimg)
                    self._preview_cache[path] = pix
                    return pix
            except Exception:
                pass

        # 3. For video without adjacent snapshot: extract crystal clear keyframe at t=1.0s (past intro frames)
        if item["is_video"] and os.path.exists(path) and item.get("size", 0) > 2048:
            try:
                cap = cv2.VideoCapture(path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                    total_f = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    target_frame = min(int(fps * 1.0), max(0, int(total_f - 1)))
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = rgb.shape
                        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
                        pix = QPixmap.fromImage(qimg).scaled(340, 191, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self._preview_cache[path] = pix
                        return pix
            except Exception:
                pass

        # Fallback to thumbnail scaled smoothly
        thumb = self._get_thumbnail(item)
        if thumb:
            pix = thumb.scaled(340, 191, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self._preview_cache[path] = pix
            return pix

        return None

    def _render_list(self):
        self.media_list.clear()

        # Display newest 150 matching items for instant responsiveness
        display_items = self.filtered_items[:150]

        for item in display_items:
            cam = item["camera_name"]
            lens = item["lens"]
            event = item["event_desc"]
            dt_str = item["date_str"]
            sz_str = format_bytes(item["size"])
            loc_str = "Google Drive" if item["is_gdrive"] else "Local"
            var_str = f" [{item['variant']}]" if item["variant"] != "Video" else ""

            # Sleek 3-line readable format
            line1 = f"{cam} • {lens}{var_str}"
            line2 = f"{event}  |  {dt_str}"
            line3 = f"{sz_str}  |  {loc_str}"

            text = f"{line1}\n{line2}\n{line3}"

            list_item = QListWidgetItem()
            list_item.setText(text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)

            thumb = self._get_thumbnail(item)
            if thumb:
                list_item.setIcon(QIcon(thumb))

            self.media_list.addItem(list_item)

        total_sz = sum(x["size"] for x in self.filtered_items)
        self.lbl_footer_status.setText(
            f"Showing {len(display_items)} of {len(self.filtered_items):,} matching items "
            f"(Total Size: {format_bytes(total_sz)}) • Storage: {self.configured_rec_dir}"
        )

        if self.media_list.count() > 0:
            self.media_list.setCurrentRow(0)
        else:
            self._clear_inspector()

    def _on_item_selected(self):
        curr = self.media_list.currentItem()
        if not curr:
            self._clear_inspector()
            return
        item = curr.data(Qt.ItemDataRole.UserRole)
        self.current_selected_item = item
        self._update_inspector(item)

    def _update_inspector(self, item: Dict[str, Any]):
        path = item["path"]
        preview_pix = self._get_inspector_preview(item)

        if preview_pix:
            # Render subtle translucent glass OSD chip directly onto the preview pixmap for a pristine Apple/UniFi look
            comp_pix = QPixmap(preview_pix)
            p = QPainter(comp_pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            # Determine theme color
            ev_upper = item["event_desc"].upper()
            if "PERSON" in ev_upper:
                badge_bg = QColor(239, 68, 68, 220)
                badge_border = QColor(248, 113, 113)
                dot_color = QColor(239, 68, 68)
                badge_title = "AI PERSON"
            elif "ANIMAL" in ev_upper or "BEAR" in ev_upper or "DOG" in ev_upper:
                badge_bg = QColor(245, 158, 11, 220)
                badge_border = QColor(251, 191, 36)
                dot_color = QColor(245, 158, 11)
                badge_title = "AI ANIMAL"
            elif "VEHICLE" in ev_upper or "CAR" in ev_upper:
                badge_bg = QColor(14, 165, 233, 220)
                badge_border = QColor(56, 189, 248)
                dot_color = QColor(14, 165, 233)
                badge_title = "AI VEHICLE"
            elif item["is_snapshot"]:
                badge_bg = QColor(16, 185, 129, 220)
                badge_border = QColor(52, 211, 153)
                dot_color = QColor(16, 185, 129)
                badge_title = "PHOTO"
            else:
                badge_bg = QColor(100, 116, 139, 220)
                badge_border = QColor(148, 163, 184)
                dot_color = QColor(148, 163, 184)
                badge_title = "MOTION"

            # Top-left glass capsule
            cam_short = item["camera_name"].split("(")[0].strip()
            chip_text = f"{badge_title} • {cam_short}"
            chip_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            p.setFont(chip_font)
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(chip_text)

            pill_w = tw + 26
            pill_h = 24
            p.setBrush(QBrush(QColor(11, 15, 25, 210)))
            p.setPen(QPen(QColor(51, 65, 85, 230), 1))
            p.drawRoundedRect(QRectF(8, 8, pill_w, pill_h), 6, 6)

            # Glowing beacon dot
            p.setBrush(QBrush(dot_color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(15, 16, 8, 8))

            p.setPen(QColor(248, 250, 252))
            p.drawText(QRect(28, 8, tw + 4, pill_h), Qt.AlignmentFlag.AlignVCenter, chip_text)

            # Bottom-right format pill
            fmt_str = "1080P HD" if item["is_video"] else "HIGH-RES SNAPSHOT"
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            f_fm = p.fontMetrics()
            f_tw = f_fm.horizontalAdvance(fmt_str)
            p.setBrush(QBrush(QColor(0, 0, 0, 190)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(comp_pix.width() - f_tw - 18, comp_pix.height() - 26, f_tw + 12, 20), 4, 4)
            p.setPen(QColor(148, 163, 184))
            p.drawText(QRect(comp_pix.width() - f_tw - 12, comp_pix.height() - 26, f_tw, 20), Qt.AlignmentFlag.AlignCenter, fmt_str)

            # If video, draw play icon in center
            if item["is_video"]:
                cx = comp_pix.width() // 2
                cy = comp_pix.height() // 2
                p.setBrush(QBrush(QColor(29, 78, 216, 210)))
                p.setPen(QPen(QColor(96, 165, 250), 1.5))
                p.drawEllipse(QRectF(cx - 20, cy - 20, 40, 40))
                # Triangle
                p.setBrush(QBrush(QColor(255, 255, 255)))
                p.setPen(Qt.PenStyle.NoPen)
                from PyQt6.QtGui import QPolygonF
                from PyQt6.QtCore import QPointF
                tri = QPolygonF([QPointF(cx - 5, cy - 8), QPointF(cx + 9, cy), QPointF(cx - 5, cy + 8)])
                p.drawPolygon(tri)

            p.end()
            self.lbl_preview_thumb.setPixmap(comp_pix)
        else:
            self.lbl_preview_thumb.setText("No Preview Available")

        # Telemetry Card rows
        self.lbl_meta_cam.setText(f"{item['camera_name']} • {item['lens']}")
        self.lbl_meta_event.setText(f"{item['event_desc']} [{item['variant']}]")
        self.lbl_meta_time.setText(item["date_str"])
        self.lbl_meta_specs.setText("1920x1080 @ 25fps (H.264)" if item["is_video"] else "High-Res JPEG")
        loc_text = "Google Drive (X:)" if item["is_gdrive"] else "Local Storage"
        self.lbl_meta_size.setText(f"{format_bytes(item['size'])} ({loc_text})")

        fm = self.lbl_meta_storage.fontMetrics()
        elided_p = fm.elidedText(path, Qt.TextElideMode.ElideMiddle, 218)
        self.lbl_meta_storage.setText(elided_p)
        self.lbl_meta_storage.setToolTip(path)

        if item["is_video"]:
            self.btn_play_app.setText(" Play Video in Studio")
            self.btn_play_app.setIcon(create_gallery_vector_icon("play", color="#ffffff", size=16))
            self.btn_play_app.show()
        else:
            self.btn_play_app.setText(" View Fullscreen Photo")
            self.btn_play_app.setIcon(create_gallery_vector_icon("snapshots", color="#ffffff", size=16))
            self.btn_play_app.show()

        if "_AI_Boxed" in path or "_HIGHLIGHTED" in path or "_Raw" in path or "_RAW" in path:
            self.btn_toggle_variant.show()
        else:
            self.btn_toggle_variant.hide()

    def _clear_inspector(self):
        self.current_selected_item = None
        self.lbl_preview_thumb.clear()
        self.lbl_preview_thumb.setText("Select a recording to preview")
        self.lbl_meta_cam.setText("-")
        self.lbl_meta_event.setText("-")
        self.lbl_meta_time.setText("-")
        self.lbl_meta_specs.setText("-")
        self.lbl_meta_size.setText("-")
        self.lbl_meta_storage.setText("-")
        self.btn_play_app.hide()
        self.btn_toggle_variant.hide()

    def _on_item_double_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self._play_item(data)

    def _play_selected_in_app(self):
        if self.current_selected_item:
            self._play_item(self.current_selected_item)

    def _play_item(self, item: Dict[str, Any]):
        filepath = item["path"]
        if not os.path.exists(filepath):
            QMessageBox.warning(self, "Missing File", f"File not found on disk:\n{filepath}")
            return

        if item["is_video"]:
            try:
                from ui.components.video_player_dialog import VideoPlayerDialog
                dlg = VideoPlayerDialog(filepath, parent=self)
                dlg.exec()
            except Exception as e:
                QMessageBox.warning(self, "Player Error", f"Failed to play video in app:\n{e}")
        else:
            try:
                os.startfile(filepath)
            except Exception as e:
                QMessageBox.warning(self, "Viewer Error", f"Failed to open image:\n{e}")

    def _toggle_selected_variant(self):
        if not self.current_selected_item:
            return
        path = self.current_selected_item["path"]
        partner = ""
        if "_AI_Boxed" in path:
            partner = path.replace("_AI_Boxed", "_Raw")
        elif "_Raw" in path and not "_RAW" in path:
            partner = path.replace("_Raw", "_AI_Boxed")
        elif "_HIGHLIGHTED" in path:
            partner = path.replace("_HIGHLIGHTED", "_RAW")
        elif "_RAW" in path:
            partner = path.replace("_RAW", "_HIGHLIGHTED")

        if partner and os.path.exists(partner):
            for i in range(self.media_list.count()):
                it = self.media_list.item(i)
                data = it.data(Qt.ItemDataRole.UserRole)
                if data and os.path.abspath(data["path"]).lower() == os.path.abspath(partner).lower():
                    self.media_list.setCurrentItem(it)
                    return
            stat = os.stat(partner)
            p_data = self._parse_file_metadata(partner, os.path.basename(partner), stat.st_size, stat.st_mtime, True, False)
            self._update_inspector(p_data)
        else:
            QMessageBox.information(self, "Partner Clip", "Partner AI/Raw video clip was not found on disk.")

    def _show_selected_in_folder(self):
        if not self.current_selected_item:
            return
        path = self.current_selected_item["path"]
        if not os.path.exists(path):
            return
        try:
            import subprocess
            subprocess.run(["explorer", f"/select,{os.path.abspath(path)}"], check=False)
        except Exception:
            os.startfile(os.path.dirname(path))

    def _delete_selected(self):
        if not self.current_selected_item:
            return
        item = self.current_selected_item
        path = item["path"]
        if not os.path.exists(path):
            self.refresh_media()
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete:\n{item['filename']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                os.remove(path)
                self.all_items = [x for x in self.all_items if x["path"] != path]
                self._apply_filters()
            except Exception as e:
                QMessageBox.warning(self, "Delete Error", f"Failed to delete file:\n{e}")

    def _open_gdrive_folder(self):
        target = self.gdrive_dir if os.path.exists(self.gdrive_dir) else self.configured_rec_dir
        os.makedirs(target, exist_ok=True)
        try:
            os.startfile(target)
        except Exception as e:
            QMessageBox.warning(self, "Explorer Error", f"Failed to open folder:\n{e}")

    def _open_prune_dialog(self):
        """Allows user to clean up disk storage and prune old recordings/snapshots."""
        if not self.alert_manager:
            QMessageBox.information(self, "Storage Prune", "Alert manager is not attached.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Storage Optimization & Cleanup")
        dlg.resize(500, 320)
        dlg.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
                color: #f1f5f9;
            }
            QLabel { color: #e2e8f0; }
            QRadioButton {
                color: #f8fafc;
                font-size: 12px;
                padding: 4px;
            }
            QRadioButton:hover {
                color: #38bdf8;
            }
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                padding: 6px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        lbl_head = QLabel("Disk Storage Optimization")
        lbl_head.setStyleSheet("font-size: 15px; font-weight: 800; color: #38bdf8;")
        layout.addWidget(lbl_head)

        total_files = len(getattr(self, "_raw_scanned_files", []))
        total_sz = sum(x[2] for x in getattr(self, "_raw_scanned_files", []))
        lbl_info = QLabel(
            f"Current Library: <b>{total_files:,} media files</b> occupying <b>{format_bytes(total_sz)}</b>.<br>"
            "Pruning removes older media to free gigabytes of disk space and keep loading instant."
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("font-size: 12px; color: #cbd5e1;")
        layout.addWidget(lbl_info)

        rb_orphans = QRadioButton("Prune untracked snapshots older than 2 days (Keep all active alerts safe)")
        rb_orphans.setChecked(True)
        rb_3d = QRadioButton("Prune media older than 3 days (Free several GB)")
        rb_7d = QRadioButton("Prune media older than 7 days")
        rb_14d = QRadioButton("Prune media older than 14 days")

        btn_grp = QButtonGroup(dlg)
        btn_grp.addButton(rb_orphans, 1)
        btn_grp.addButton(rb_3d, 2)
        btn_grp.addButton(rb_7d, 3)
        btn_grp.addButton(rb_14d, 4)

        layout.addWidget(rb_orphans)
        layout.addWidget(rb_3d)
        layout.addWidget(rb_7d)
        layout.addWidget(rb_14d)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_ok = bbox.button(QDialogButtonBox.StandardButton.Ok)
        btn_ok.setText("Prune Storage Now")
        btn_ok.setStyleSheet("background-color: #991b1b; color: #ffffff; border-color: #ef4444; font-weight: 700; padding: 6px 16px;")
        bbox.accepted.connect(dlg.accept)
        bbox.rejected.connect(dlg.reject)
        layout.addWidget(bbox)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            choice = btn_grp.checkedId()
            total_freed = 0
            total_removed = 0
            if choice == 1:
                n, b = self.alert_manager.prune_orphaned_snapshots(max_age_days=2, max_count=500)
                total_removed += n
                total_freed += b
            elif choice == 2:
                n1, b1 = self.alert_manager.prune_orphaned_snapshots(max_age_days=3, max_count=300)
                n2, b2 = self.alert_manager.prune_old_recordings(max_age_days=3)
                total_removed += n1 + n2
                total_freed += b1 + b2
            elif choice == 3:
                n1, b1 = self.alert_manager.prune_orphaned_snapshots(max_age_days=7, max_count=500)
                n2, b2 = self.alert_manager.prune_old_recordings(max_age_days=7)
                total_removed += n1 + n2
                total_freed += b1 + b2
            elif choice == 4:
                n1, b1 = self.alert_manager.prune_orphaned_snapshots(max_age_days=14, max_count=1000)
                n2, b2 = self.alert_manager.prune_old_recordings(max_age_days=14)
                total_removed += n1 + n2
                total_freed += b1 + b2

            self.refresh_media()
            QMessageBox.information(
                self, "Storage Pruned",
                f"Successfully removed {total_removed:,} files.\nFreed {format_bytes(total_freed)} of disk space!"
            )
