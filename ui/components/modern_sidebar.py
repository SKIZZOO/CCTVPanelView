import os
import json
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTreeWidget, QTreeWidgetItem, QStackedWidget, QProgressBar,
    QScrollArea, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt6.QtGui import QColor, QFont, QBrush, QIcon, QPainter, QCursor, QPainterPath, QPen
from PyQt6.QtCore import QRectF, QPointF


def create_sidebar_vector_icon(icon_type: str, active: bool = False, size: int = 14, custom_color: Optional[str] = None) -> QIcon:
    """Renders crisp, anti-aliased vector icons for the modern Apple / Windows 11 sidebar."""
    from PyQt6.QtGui import QPixmap
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    fg = QColor(custom_color) if custom_color else (QColor("#38bdf8") if active else QColor("#94a3b8"))
    pen = QPen(fg, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    if icon_type == "cameras":
        p.drawRoundedRect(QRectF(size * 0.14, size * 0.28, size * 0.72, size * 0.52), 2, 2)
        p.drawEllipse(QPointF(size * 0.50, size * 0.54), size * 0.16, size * 0.16)
        p.drawRoundedRect(QRectF(size * 0.32, size * 0.16, size * 0.36, size * 0.14), 1.5, 1.5)
    elif icon_type == "alerts":
        path = QPainterPath()
        path.moveTo(size * 0.50, size * 0.16)
        path.cubicTo(size * 0.32, size * 0.22, size * 0.26, size * 0.55, size * 0.20, size * 0.72)
        path.lineTo(size * 0.80, size * 0.72)
        path.cubicTo(size * 0.74, size * 0.55, size * 0.68, size * 0.22, size * 0.50, size * 0.16)
        p.drawPath(path)
        p.drawLine(int(size * 0.42), int(size * 0.82), int(size * 0.58), int(size * 0.82))
    elif icon_type == "hud":
        path = QPainterPath()
        path.moveTo(size * 0.14, size * 0.52)
        path.lineTo(size * 0.32, size * 0.52)
        path.lineTo(size * 0.42, size * 0.22)
        path.lineTo(size * 0.56, size * 0.78)
        path.lineTo(size * 0.68, size * 0.42)
        path.lineTo(size * 0.76, size * 0.52)
        path.lineTo(size * 0.86, size * 0.52)
        p.drawPath(path)
    elif icon_type == "dock":
        p.drawRoundedRect(QRectF(size * 0.14, size * 0.18, size * 0.72, size * 0.64), 2, 2)
        p.drawLine(int(size * 0.48), int(size * 0.18), int(size * 0.48), int(size * 0.82))
        p.drawLine(int(size * 0.62), int(size * 0.44), int(size * 0.72), int(size * 0.50))
        p.drawLine(int(size * 0.72), int(size * 0.50), int(size * 0.62), int(size * 0.56))
    elif icon_type == "stream":
        path = QPainterPath()
        path.moveTo(size * 0.34, size * 0.24)
        path.lineTo(size * 0.74, size * 0.50)
        path.lineTo(size * 0.34, size * 0.76)
        path.closeSubpath()
        p.fillPath(path, QBrush(fg))
    elif icon_type == "manage":
        p.drawLine(int(size * 0.18), int(size * 0.34), int(size * 0.82), int(size * 0.34))
        p.drawEllipse(QPointF(size * 0.38, size * 0.34), size * 0.11, size * 0.11)
        p.drawLine(int(size * 0.18), int(size * 0.66), int(size * 0.82), int(size * 0.66))
        p.drawEllipse(QPointF(size * 0.62, size * 0.66), size * 0.11, size * 0.11)
    p.end()
    return QIcon(pix)


class ModernSegmentedNavBar(QFrame):
    """
    Ultra-modern frosted capsule segmented navigation bar (Apple Vision / Windows 11 style).
    Features vector icons, rounded pills, and smooth active indicator states.
    """
    page_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("modern_segmented_nav")
        self.setFixedHeight(36)
        self.setStyleSheet("""
            QFrame#modern_segmented_nav {
                background-color: #070b14;
                border: 1px solid #1a2336;
                border-radius: 8px;
                padding: 2px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)

        self.btn_cameras = QPushButton(" Cameras (0)", self)
        self.btn_cameras.setIcon(create_sidebar_vector_icon("cameras", active=True, size=14))
        self.btn_alerts = QPushButton(" Alerts (0)", self)
        self.btn_alerts.setIcon(create_sidebar_vector_icon("alerts", active=False, size=14))
        self.btn_telemetry = QPushButton(" System HUD", self)
        self.btn_telemetry.setIcon(create_sidebar_vector_icon("hud", active=False, size=14))

        self.buttons = [self.btn_cameras, self.btn_alerts, self.btn_telemetry]

        for idx, btn in enumerate(self.buttons):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=idx: self.set_current_index(i))
            layout.addWidget(btn)

        self._current_index = 0
        self._compact_mode = False
        self._tab_labels = ["Cameras (0)", "Alerts (0)", "System HUD"]
        self._update_tab_labels()
        self._update_button_styles()

    def set_current_index(self, index: int):
        if index < 0 or index >= len(self.buttons):
            return
        self._current_index = index
        self._update_button_styles()
        self.page_changed.emit(index)

    def current_index(self) -> int:
        return self._current_index

    def set_tab_text(self, index: int, text: str):
        if 0 <= index < len(self.buttons):
            self._tab_labels[index] = text
            self._update_tab_labels()

    def _update_tab_labels(self):
        for i, btn in enumerate(self.buttons):
            label = self._tab_labels[i] if i < len(self._tab_labels) else ""
            btn.setText("" if self._compact_mode else f" {label}")
            btn.setToolTip(label)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        compact = self.width() < 270
        if compact != self._compact_mode:
            self._compact_mode = compact
            self._update_tab_labels()

    def _update_button_styles(self):
        active_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a263c, stop:1 #141f32);
                color: #38bdf8;
                font-size: 11px;
                font-weight: 700;
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 6px;
                padding: 4px 6px;
            }
        """
        inactive_style = """
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px 6px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: #f1f5f9;
            }
        """
        icons_spec = ["cameras", "alerts", "hud"]
        for i, btn in enumerate(self.buttons):
            is_active = (i == self._current_index)
            btn.setChecked(is_active)
            btn.setIcon(create_sidebar_vector_icon(icons_spec[i], active=is_active, size=14))
            btn.setStyleSheet(active_style if is_active else inactive_style)


class ModernSideTabWidget(QWidget):
    """
    Seamless drop-in replacement for QTabWidget.
    Combines ModernSegmentedNavBar, QStackedWidget, and top-right dock toggle button with vector icon.
    """
    currentChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("modern_side_tabs_wrapper")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(6)

        # Header row: Segmented pill bar on left, dock position toggle button on right
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        self.nav_bar = ModernSegmentedNavBar(self)
        self.nav_bar.page_changed.connect(self._on_page_changed)
        header_row.addWidget(self.nav_bar, stretch=1)

        self.btn_dock_side = QPushButton(self)
        self.btn_dock_side.setObjectName("btn_dock_side")
        self.btn_dock_side.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dock_side.setToolTip("Dock sidebar on Left / Right side of workstation")
        self.btn_dock_side.setIcon(create_sidebar_vector_icon("dock", size=14))
        self.btn_dock_side.setFixedSize(34, 34)
        self.btn_dock_side.setStyleSheet("""
            QPushButton#btn_dock_side {
                background-color: #0c1220;
                color: #94a3b8;
                border: 1px solid #1e293b;
                border-radius: 7px;
                padding: 0px;
            }
            QPushButton#btn_dock_side:hover {
                background-color: #1e293b;
                color: #38bdf8;
                border-color: #0284c7;
            }
        """)
        header_row.addWidget(self.btn_dock_side)

        root_layout.addLayout(header_row)

        self.stack = QStackedWidget(self)
        root_layout.addWidget(self.stack, stretch=1)

    def _on_page_changed(self, index: int):
        self.stack.setCurrentIndex(index)
        self.currentChanged.emit(index)

    def addTab(self, widget: QWidget, label: str):
        idx = self.stack.addWidget(widget)
        self.nav_bar.set_tab_text(idx, label)
        return idx

    def setCurrentIndex(self, index: int):
        self.nav_bar.set_current_index(index)

    def currentIndex(self) -> int:
        return self.stack.currentIndex()

    def setTabText(self, index: int, text: str):
        self.nav_bar.set_tab_text(index, text)

    def setCornerWidget(self, widget: QWidget, corner=None):
        pass


class CameraHeaderCardWidget(QFrame):
    """
    Sleek, modern round card header for a physical camera device.
    Zero pill shapes, glowing beacon dot, circular 26px action buttons.
    """
    play_all_requested = pyqtSignal(dict)
    menu_requested = pyqtSignal(dict, QPoint)

    def __init__(self, cam_data: dict, is_online: bool = True, parent=None):
        super().__init__(parent)
        self.cam_data = cam_data
        self.setObjectName("camera_header_card")
        self.setStyleSheet("""
            QFrame#camera_header_card {
                background-color: #0b101c;
                border: 1px solid #1a2336;
                border-radius: 9px;
                padding: 6px 8px;
            }
            QFrame#camera_header_card:hover {
                background-color: #101726;
                border-color: #2b3954;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        # Status Dot (round glowing beacon)
        self.status_dot = QLabel(self)
        self.status_dot.setFixedSize(8, 8)
        dot_color = "#38bdf8" if is_online else "#64748b"
        self.status_dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 4px;")
        layout.addWidget(self.status_dot)

        # Info Box (Title + IP / Model)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        cam_name = cam_data.get("name", "Camera")
        self.lbl_name = QLabel(cam_name, self)
        self.lbl_name.setStyleSheet("color: #f8fafc; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        info_layout.addWidget(self.lbl_name)

        is_dual = cam_data.get("is_dual_lens", False)
        type_str = "Dual-Lens PTZ" if is_dual else "Single Lens"
        self.lbl_sub = QLabel(f"{type_str} • Active" if is_online else f"{type_str} • Standby", self)
        self.lbl_sub.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 500; border: none; background: transparent;")
        info_layout.addWidget(self.lbl_sub)
        layout.addLayout(info_layout, stretch=1)

        # Subtle round circular badge for dual-lens (NOT a pill!)
        if is_dual:
            badge = QLabel("2K", self)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(22, 22)
            badge.setToolTip("2K Ultra HD Dual-Lens System")
            badge.setStyleSheet("""
                background-color: rgba(56, 189, 248, 0.12);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 11px;
                font-size: 8px;
                font-weight: 800;
            """)
            layout.addWidget(badge)

        # Circular Play All Button (26x26, border-radius 13px)
        self.btn_play_all = QPushButton(self)
        self.btn_play_all.setObjectName("cam_card_play_btn")
        self.btn_play_all.setToolTip("Stream all lenses into empty grid slots")
        self.btn_play_all.setIcon(create_sidebar_vector_icon("stream", size=11, custom_color="#38bdf8"))
        self.btn_play_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play_all.setFixedSize(26, 26)
        self.btn_play_all.setStyleSheet("""
            QPushButton#cam_card_play_btn {
                background-color: rgba(56, 189, 248, 0.12);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 13px;
                padding: 0px;
            }
            QPushButton#cam_card_play_btn:hover {
                background-color: #0284c7;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.btn_play_all.clicked.connect(lambda: self.play_all_requested.emit(self.cam_data))
        layout.addWidget(self.btn_play_all)

        # Circular Manage Button (26x26, border-radius 13px)
        self.btn_menu = QPushButton(self)
        self.btn_menu.setObjectName("cam_card_menu_btn")
        self.btn_menu.setToolTip("Camera settings, rename, night vision & actions")
        self.btn_menu.setIcon(create_sidebar_vector_icon("manage", size=11, custom_color="#94a3b8"))
        self.btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_menu.setFixedSize(26, 26)
        self.btn_menu.setStyleSheet("""
            QPushButton#cam_card_menu_btn {
                background-color: #141c2c;
                color: #94a3b8;
                border: 1px solid #202d44;
                border-radius: 13px;
                padding: 0px;
            }
            QPushButton#cam_card_menu_btn:hover {
                background-color: #202d44;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.btn_menu.clicked.connect(self._on_menu_clicked)
        layout.addWidget(self.btn_menu)

    def _on_menu_clicked(self):
        global_pos = self.btn_menu.mapToGlobal(QPoint(0, self.btn_menu.height()))
        self.menu_requested.emit(self.cam_data, global_pos)


class StreamRowCardWidget(QFrame):
    """
    Sleek indented card for an individual camera stream/lens.
    Round 22px circular lens badge (PTZ vs Wide), no blue border on left,
    and 24px circular quick-action buttons.
    """
    stream_requested = pyqtSignal(dict)
    rename_requested = pyqtSignal(dict)
    menu_requested = pyqtSignal(dict, QPoint)

    def __init__(self, stream_data: dict, parent=None):
        super().__init__(parent)
        self.stream_data = stream_data
        self.setObjectName("stream_row_card")
        self.setStyleSheet("""
            QFrame#stream_row_card {
                background-color: #080d17;
                border: 1px solid #162032;
                border-radius: 8px;
                padding: 3px 6px;
            }
            QFrame#stream_row_card:hover {
                background-color: #0e1526;
                border-color: #25334e;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 6, 4)
        layout.setSpacing(8)

        is_ptz = stream_data.get("is_ptz", False)
        lens_name = stream_data.get("name", "Stream")

        # Circular Lens Badge (22x22 round circle, NOT a pill!)
        pill_txt = "P" if is_ptz else "W"
        pill_color = "#38bdf8" if is_ptz else "#60a5fa"
        pill_bg = "rgba(56, 189, 248, 0.12)" if is_ptz else "rgba(96, 165, 250, 0.12)"
        pill_bd = "rgba(56, 189, 248, 0.35)" if is_ptz else "rgba(96, 165, 250, 0.35)"

        self.lbl_pill = QLabel(pill_txt, self)
        self.lbl_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_pill.setFixedSize(22, 22)
        self.lbl_pill.setToolTip("PTZ Optical Zoom Lens" if is_ptz else "Panoramic Wide Angle Lens")
        self.lbl_pill.setStyleSheet(f"""
            background-color: {pill_bg};
            color: {pill_color};
            border: 1px solid {pill_bd};
            border-radius: 11px;
            font-size: 9px;
            font-weight: 800;
        """)
        layout.addWidget(self.lbl_pill)

        # Stream Name
        lbl_name = QLabel(lens_name, self)
        lbl_name.setStyleSheet("color: #cbd5e1; font-size: 10px; font-weight: 600; border: none; background: transparent;")
        lbl_name.setToolTip("Drag onto any grid tile slot or click play")
        layout.addWidget(lbl_name, stretch=1)

        # Circular Stream Play Button (24x24 round, border-radius 12px)
        self.btn_play = QPushButton(self)
        self.btn_play.setObjectName("stream_row_play_btn")
        self.btn_play.setToolTip("Assign this lens to currently selected grid slot")
        self.btn_play.setIcon(create_sidebar_vector_icon("stream", size=9, custom_color="#38bdf8"))
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.setFixedSize(24, 24)
        self.btn_play.setStyleSheet("""
            QPushButton#stream_row_play_btn {
                background-color: rgba(56, 189, 248, 0.12);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 12px;
                padding: 0px;
            }
            QPushButton#stream_row_play_btn:hover {
                background-color: #0284c7;
                color: #ffffff;
                border-color: #0284c7;
            }
        """)
        self.btn_play.clicked.connect(lambda: self.stream_requested.emit(self.stream_data))
        layout.addWidget(self.btn_play)

        # Circular Rename/Edit Lens Button (24x24 round, border-radius 12px)
        self.btn_rename = QPushButton(self)
        self.btn_rename.setObjectName("stream_row_rename_btn")
        self.btn_rename.setToolTip("Rename this lens")
        self.btn_rename.setIcon(create_sidebar_vector_icon("manage", size=9, custom_color="#94a3b8"))
        self.btn_rename.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rename.setFixedSize(24, 24)
        self.btn_rename.setStyleSheet("""
            QPushButton#stream_row_rename_btn {
                background-color: #141c2c;
                color: #94a3b8;
                border: 1px solid #202d44;
                border-radius: 12px;
                padding: 0px;
            }
            QPushButton#stream_row_rename_btn:hover {
                background-color: #202d44;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.btn_rename.clicked.connect(lambda: self.rename_requested.emit(self.stream_data))
        layout.addWidget(self.btn_rename)

    def contextMenuEvent(self, event):
        self.menu_requested.emit(self.stream_data, event.globalPos())
        event.accept()


class ModernDraggableCameraTree(QTreeWidget):
    """
    State-of-the-art camera list supporting drag & drop, instant search filtering,
    clean card rendering, and context menu actions.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cam_tree")
        self.setDragEnabled(True)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)
        self.setIndentation(6)
        self.setAnimated(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("""
            QTreeWidget#cam_tree {
                background-color: transparent;
                border: none;
                outline: none;
                padding: 0px;
            }
            QTreeWidget#cam_tree::item {
                background-color: transparent;
                border: none;
                margin: 2px 0px;
                padding: 0px;
            }
            QTreeWidget#cam_tree::item:hover {
                background-color: transparent;
            }
            QTreeWidget#cam_tree::item:selected {
                background-color: transparent;
            }
        """)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "stream":
            return

        stream_data = data.get("data")
        mime = QMimeData()
        mime.setData("application/x-camera-stream", json.dumps(stream_data).encode("utf-8"))
        from PyQt6.QtGui import QDrag
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)

    def filter_cameras(self, query: str):
        """Filters cameras and streams in real-time as user types in search box."""
        q = (query or "").strip().lower()
        for i in range(self.topLevelItemCount()):
            cam_item = self.topLevelItem(i)
            cam_data = cam_item.data(0, Qt.ItemDataRole.UserRole)
            if not cam_data:
                continue

            cam_dict = cam_data.get("data", {})
            name = str(cam_dict.get("name", "")).lower()
            ip = str(cam_dict.get("ip", "")).lower()

            match_cam = (q in name) or (q in ip)
            match_child = False

            for j in range(cam_item.childCount()):
                s_item = cam_item.child(j)
                s_data = s_item.data(0, Qt.ItemDataRole.UserRole)
                s_dict = s_data.get("data", {}) if s_data else {}
                s_name = str(s_dict.get("name", "")).lower()

                if q in s_name or match_cam:
                    s_item.setHidden(False)
                    match_child = True
                else:
                    s_item.setHidden(True)

            cam_item.setHidden(not (match_cam or match_child))
            if q:
                cam_item.setExpanded(True)


class ModernSidebarTelemetryWidget(QWidget):
    """
    Dedicated spacious Telemetry & Cloud Storage page.
    Replaces the cramped bottom widget with expansive, beautifully formatted cards.
    """
    open_folder_requested = pyqtSignal()
    open_web_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("modern_telemetry_page")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # 1. Cloud Storage Card
        card_storage = QFrame(self)
        card_storage.setStyleSheet("""
            QFrame {
                background-color: #0b101c;
                border: 1px solid #1a2234;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        st_layout = QVBoxLayout(card_storage)
        st_layout.setContentsMargins(8, 8, 8, 8)
        st_layout.setSpacing(6)

        st_hdr = QHBoxLayout()
        lbl_st_title = QLabel("GOOGLE DRIVE CLOUD NVR", card_storage)
        lbl_st_title.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 0.8px;")
        st_hdr.addWidget(lbl_st_title)
        st_hdr.addStretch()

        self.lbl_cloud_status = QLabel("SYNC ACTIVE", card_storage)
        self.lbl_cloud_status.setStyleSheet("""
            color: #38bdf8;
            font-size: 9px;
            font-weight: 700;
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 3px;
            padding: 1px 5px;
        """)
        st_hdr.addWidget(self.lbl_cloud_status)
        st_layout.addLayout(st_hdr)

        self.lbl_storage_path = QLabel("Local CCTV Storage", card_storage)
        self.lbl_storage_path.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 600;")
        st_layout.addWidget(self.lbl_storage_path)

        self.storage_bar = QProgressBar(card_storage)
        self.storage_bar.setRange(0, 100)
        self.storage_bar.setValue(45)
        self.storage_bar.setTextVisible(False)
        self.storage_bar.setFixedHeight(5)
        self.storage_bar.setStyleSheet("""
            QProgressBar {
                background-color: #131a29;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8);
                border-radius: 2px;
            }
        """)
        st_layout.addWidget(self.storage_bar)

        self.lbl_storage_sub = QLabel("Active storage • Auto retention 30 days", card_storage)
        self.lbl_storage_sub.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 500;")
        st_layout.addWidget(self.lbl_storage_sub)

        btn_open_folder = QPushButton("Open CCTV Folder in Explorer", card_storage)
        btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_folder.setStyleSheet("""
            QPushButton {
                background-color: #131b2c;
                color: #cbd5e1;
                border: 1px solid #1e293b;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        btn_open_folder.clicked.connect(lambda: self.open_folder_requested.emit())
        st_layout.addWidget(btn_open_folder)
        layout.addWidget(card_storage)

        # 2. AI Engine Card
        card_ai = QFrame(self)
        card_ai.setStyleSheet("""
            QFrame {
                background-color: #0b101c;
                border: 1px solid #1a2234;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        ai_layout = QVBoxLayout(card_ai)
        ai_layout.setContentsMargins(8, 8, 8, 8)
        ai_layout.setSpacing(6)

        ai_hdr = QHBoxLayout()
        lbl_ai_title = QLabel("AI VISION & DETECTION", card_ai)
        lbl_ai_title.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 0.8px;")
        ai_hdr.addWidget(lbl_ai_title)
        ai_hdr.addStretch()

        lbl_ai_badge = QLabel("NEURAL READY", card_ai)
        lbl_ai_badge.setStyleSheet("""
            color: #a855f7;
            font-size: 9px;
            font-weight: 700;
            background: rgba(168, 85, 247, 0.12);
            border: 1px solid rgba(168, 85, 247, 0.3);
            border-radius: 3px;
            padding: 1px 5px;
        """)
        ai_hdr.addWidget(lbl_ai_badge)
        ai_layout.addLayout(ai_hdr)

        self.lbl_ai_model = QLabel("Model: YOLOv8 High-Speed Neural Net", card_ai)
        self.lbl_ai_model.setStyleSheet("color: #f8fafc; font-size: 11px; font-weight: 600;")
        ai_layout.addWidget(self.lbl_ai_model)

        self.lbl_ai_filters = QLabel("Active Detectors: Person • Vehicle • Animal", card_ai)
        self.lbl_ai_filters.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 500;")
        ai_layout.addWidget(self.lbl_ai_filters)
        layout.addWidget(card_ai)

        # 3. Mobile Web Hub Card
        card_web = QFrame(self)
        card_web.setStyleSheet("""
            QFrame {
                background-color: #0b101c;
                border: 1px solid #1a2234;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        web_layout = QVBoxLayout(card_web)
        web_layout.setContentsMargins(8, 8, 8, 8)
        web_layout.setSpacing(6)

        web_hdr = QHBoxLayout()
        lbl_web_title = QLabel("MOBILE WEB APP STREAMING", card_web)
        lbl_web_title.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 0.8px;")
        web_hdr.addWidget(lbl_web_title)
        web_hdr.addStretch()

        self.lbl_web_status = QLabel("PORT 8080 LIVE", card_web)
        self.lbl_web_status.setStyleSheet("""
            color: #38bdf8;
            font-size: 9px;
            font-weight: 700;
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 3px;
            padding: 1px 5px;
        """)
        web_hdr.addWidget(self.lbl_web_status)
        web_layout.addLayout(web_hdr)

        self.lbl_web_url = QLabel("http://127.0.0.1:8080", card_web)
        self.lbl_web_url.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 600;")
        web_layout.addWidget(self.lbl_web_url)

        btn_open_web = QPushButton("Open Mobile Hub in Browser", card_web)
        btn_open_web.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_web.setStyleSheet("""
            QPushButton {
                background-color: #131b2c;
                color: #cbd5e1;
                border: 1px solid #1e293b;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        btn_open_web.clicked.connect(lambda: self.open_web_requested.emit())
        web_layout.addWidget(btn_open_web)
        layout.addWidget(card_web)

        layout.addStretch()


class PersistentSlimFooter(QFrame):
    """
    Sleek, high-tech bottom HUD telemetry strip displayed across all sidebar tabs.
    Features interactive capsules for Google Drive sync, AI Neural Net status, and Live Web Streaming.
    """
    open_drive_requested = pyqtSignal()
    open_web_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("persistent_slim_footer")
        self.setFixedHeight(0)
        self.hide()
        self.setStyleSheet("background: transparent; border: none;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Google Drive Cloud Sync Capsule (Clickable)
        self.drive_capsule = QFrame(self)
        self.drive_capsule.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drive_capsule.setToolTip("Google Drive CCTV Storage (Click to open folder in File Explorer)")
        self.drive_capsule.setStyleSheet("""
            QFrame {
                background-color: rgba(56, 189, 248, 0.08);
                border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 4px;
                padding: 1px 6px;
            }
            QFrame:hover {
                background-color: rgba(56, 189, 248, 0.16);
                border-color: #38bdf8;
            }
        """)
        d_layout = QHBoxLayout(self.drive_capsule)
        d_layout.setContentsMargins(4, 2, 4, 2)
        d_layout.setSpacing(5)

        self.dot_drive = QLabel(self.drive_capsule)
        self.dot_drive.setFixedSize(6, 6)
        self.dot_drive.setStyleSheet("background-color: #38bdf8; border-radius: 3px;")
        d_layout.addWidget(self.dot_drive)

        self.lbl_drive = QLabel("Drive: Synced", self.drive_capsule)
        self.lbl_drive.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 700; border: none; background: transparent;")
        d_layout.addWidget(self.lbl_drive)
        self.drive_capsule.mousePressEvent = lambda e: self.open_drive_requested.emit()
        layout.addWidget(self.drive_capsule)

        layout.addStretch()

        # 2. AI Inference Engine Capsule
        self.ai_capsule = QFrame(self)
        self.ai_capsule.setToolTip("Active AI Neural Detection Engine (YOLOv8)")
        self.ai_capsule.setStyleSheet("""
            QFrame {
                background-color: rgba(168, 85, 247, 0.10);
                border: 1px solid rgba(168, 85, 247, 0.30);
                border-radius: 4px;
                padding: 1px 6px;
            }
            QFrame:hover {
                background-color: rgba(168, 85, 247, 0.18);
                border-color: #c084fc;
            }
        """)
        ai_layout = QHBoxLayout(self.ai_capsule)
        ai_layout.setContentsMargins(4, 2, 4, 2)
        ai_layout.setSpacing(4)

        self.dot_ai = QLabel(self.ai_capsule)
        self.dot_ai.setFixedSize(5, 5)
        self.dot_ai.setStyleSheet("background-color: #a855f7; border-radius: 2px;")
        ai_layout.addWidget(self.dot_ai)

        self.lbl_ai = QLabel("YOLOv8", self.ai_capsule)
        self.lbl_ai.setStyleSheet("color: #c084fc; font-size: 9px; font-weight: 800; border: none; background: transparent; letter-spacing: 0.4px;")
        ai_layout.addWidget(self.lbl_ai)
        layout.addWidget(self.ai_capsule)

        # 3. Web Streaming Server Capsule (Clickable)
        self.web_capsule = QFrame(self)
        self.web_capsule.setCursor(Qt.CursorShape.PointingHandCursor)
        self.web_capsule.setToolTip("Mobile Streaming Hub & RTSP Feeds (Click to open Mobile Access)")
        self.web_capsule.setStyleSheet("""
            QFrame {
                background-color: rgba(56, 189, 248, 0.10);
                border: 1px solid rgba(56, 189, 248, 0.30);
                border-radius: 4px;
                padding: 1px 6px;
            }
            QFrame:hover {
                background-color: rgba(56, 189, 248, 0.20);
                border-color: #38bdf8;
            }
        """)
        w_layout = QHBoxLayout(self.web_capsule)
        w_layout.setContentsMargins(4, 2, 4, 2)
        w_layout.setSpacing(4)

        self.dot_web = QLabel(self.web_capsule)
        self.dot_web.setFixedSize(5, 5)
        self.dot_web.setStyleSheet("background-color: #38bdf8; border-radius: 2px;")
        w_layout.addWidget(self.dot_web)

        self.lbl_web = QLabel(":8080 Live", self.web_capsule)
        self.lbl_web.setStyleSheet("color: #38bdf8; font-size: 9px; font-weight: 800; border: none; background: transparent; letter-spacing: 0.4px;")
        w_layout.addWidget(self.lbl_web)
        self.web_capsule.mousePressEvent = lambda e: self.open_web_requested.emit()
        layout.addWidget(self.web_capsule)
