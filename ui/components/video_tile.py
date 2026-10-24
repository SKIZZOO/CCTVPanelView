import os
import re
import math
import time
from typing import Optional, List, Dict, Any, Tuple
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QMenu, QSizePolicy, QGraphicsOpacityEffect,
    QDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, pyqtSlot, QPoint, QPointF, QRect, QRectF, QTimer, QSize,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, pyqtProperty
)
from PyQt6.QtGui import QPainter, QImage, QColor, QFont, QPen, QBrush, QIcon, QPixmap, QPainterPath, QCursor

from core.camera_stream import CameraStreamWorker, StreamStatus, QualityMode, NightVisionMode
from core.audio_stream import AudioPlayer
from ui.components.zone_editor_dialog import ZoneEditorDialog
from ui.components.settings_dialog import CameraSetupPromptDialog


TILE_ACTION_BTN_STYLE = """
    QPushButton {
        background-color: transparent;
        border: none;
        border-radius: 14px;
        padding: 2px;
    }
    QPushButton:hover {
        background-color: rgba(255, 255, 255, 0.16);
    }
    QPushButton:pressed {
        background-color: rgba(255, 255, 255, 0.28);
    }
"""


def format_clean_camera_title(raw_name: str) -> str:
    """Formats lengthy hardware camera strings and strips raw IP addresses into clean, crisp surveillance titles."""
    if not raw_name or raw_name == "Empty Slot":
        return raw_name
    # Strip long technical model tags like (Dual-Lens 2K), (2K), (JA-A12 Dual Lens PTZ)
    clean = re.sub(r"\s*\((Dual-Lens|JA-[A-Z0-9]+|2K|Outdoor|Indoor)[^)]*\)", "", raw_name, flags=re.I)
    # Remove raw IPv4 addresses (e.g. 192.168.1.100)
    clean = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "", clean)
    clean = clean.replace(" - Lens 1 (PTZ Zoom)", " • PTZ")
    clean = clean.replace(" - Lens 2 (Fixed Wide)", " • Wide")
    clean = clean.replace(" - Lens 1 (PTZ)", " • PTZ")
    clean = clean.replace(" - Lens 2 (Wide)", " • Wide")
    clean = clean.replace(" - Lens 1 (Fixed Wide)", " • Wide")
    clean = clean.replace(" - Lens 2 (PTZ Zoom)", " • PTZ")
    clean = clean.replace(" - Main Stream", " • Main")
    clean = clean.replace(" - Sub Stream", " • Sub")
    clean = clean.replace(" - ", " • ")
    clean = re.sub(r"\s+", " ", clean).strip()
    clean = clean.strip(" •-:")
    if not clean or clean.lower() == "camera":
        return "Camera"
    return clean


def create_tile_icon(icon_type: str, active: bool = False, size: int = 24, custom_color: Optional[str] = None) -> QIcon:
    """Renders high-definition vector icons for video tile action buttons and context menus."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    if custom_color:
        fg_color = QColor(custom_color)
    else:
        fg_color = QColor("#38bdf8") if active else QColor("#cbd5e1")
        if icon_type == "record":
            fg_color = QColor("#38bdf8") if active else QColor("#38bdf8")

    pen = QPen(fg_color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    if icon_type == "night":
        path = QPainterPath()
        path.moveTo(size * 0.65, size * 0.18)
        path.cubicTo(size * 0.30, size * 0.22, size * 0.22, size * 0.70, size * 0.60, size * 0.85)
        path.cubicTo(size * 0.35, size * 0.72, size * 0.35, size * 0.35, size * 0.65, size * 0.18)
        if active:
            painter.fillPath(path, QBrush(fg_color if custom_color else QColor("#38bdf8")))
        else:
            painter.strokePath(path, pen)
            painter.fillPath(path, QBrush(QColor(fg_color.red(), fg_color.green(), fg_color.blue(), 40)))
        # Micro star accent
        star_x = size * 0.74
        star_y = size * 0.28
        painter.setBrush(QBrush(fg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(star_x, star_y), 1.6, 1.6)

    elif icon_type == "color":
        c = QPointF(size * 0.5, size * 0.5)
        painter.drawEllipse(c, size * 0.18, size * 0.18)
        if active or custom_color:
            col = fg_color if custom_color else QColor("#f59e0b")
            painter.fillPath(QPainterPath(), QBrush(col))
            painter.setBrush(QBrush(col))
            painter.drawEllipse(c, size * 0.18, size * 0.18)
        for angle in (0, 45, 90, 135, 180, 225, 270, 315):
            rad = math.radians(angle)
            p1 = QPointF(c.x() + math.cos(rad) * size * 0.27, c.y() + math.sin(rad) * size * 0.27)
            p2 = QPointF(c.x() + math.cos(rad) * size * 0.38, c.y() + math.sin(rad) * size * 0.38)
            painter.drawLine(p1, p2)

    elif icon_type == "audio":
        spk = QPainterPath()
        spk.moveTo(size * 0.22, size * 0.40)
        spk.lineTo(size * 0.36, size * 0.40)
        spk.lineTo(size * 0.52, size * 0.26)
        spk.lineTo(size * 0.52, size * 0.74)
        spk.lineTo(size * 0.36, size * 0.60)
        spk.lineTo(size * 0.22, size * 0.60)
        spk.closeSubpath()
        painter.fillPath(spk, QBrush(fg_color))
        if active:
            painter.drawArc(QRectF(size * 0.44, size * 0.34, size * 0.30, size * 0.32), -50 * 16, 100 * 16)
        else:
            slash_pen = QPen(QColor("#ef4444"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(slash_pen)
            painter.drawLine(int(size * 0.28), int(size * 0.28), int(size * 0.72), int(size * 0.72))

    elif icon_type == "snapshot":
        body_rect = QRectF(size * 0.16, size * 0.32, size * 0.68, size * 0.50)
        painter.drawRoundedRect(body_rect, 3, 3)
        top_bump = QRectF(size * 0.35, size * 0.20, size * 0.30, size * 0.14)
        painter.drawRoundedRect(top_bump, 2, 2)
        painter.drawEllipse(QPointF(size * 0.50, size * 0.57), size * 0.16, size * 0.16)

    elif icon_type == "record":
        if active:
            stop_rect = QRectF(size * 0.32, size * 0.32, size * 0.36, size * 0.36)
            painter.fillRect(stop_rect, QColor("#ffffff"))
            painter.setPen(QPen(QColor("#38bdf8"), 1))
            painter.drawRoundedRect(stop_rect, 2, 2)
        else:
            painter.setBrush(QBrush(QColor(fg_color if custom_color else "#38bdf8")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(size * 0.5, size * 0.5), size * 0.28, size * 0.28)

    elif icon_type == "solo":
        m = size * 0.22
        e = size * 0.78
        l = size * 0.20
        painter.drawLine(int(m), int(m + l), int(m), int(m))
        painter.drawLine(int(m), int(m), int(m + l), int(m))
        painter.drawLine(int(e - l), int(m), int(e), int(m))
        painter.drawLine(int(e), int(m), int(e), int(m + l))
        painter.drawLine(int(m), int(e - l), int(m), int(e))
        painter.drawLine(int(m), int(e), int(m + l), int(e))
        painter.drawLine(int(e - l), int(e), int(e), int(e))
        painter.drawLine(int(e), int(e - l), int(e), int(e))

    elif icon_type == "restore":
        m = size * 0.36
        e = size * 0.64
        l = size * 0.16
        painter.drawLine(int(m - l), int(m), int(m), int(m))
        painter.drawLine(int(m), int(m - l), int(m), int(m))
        painter.drawLine(int(e + l), int(m), int(e), int(m))
        painter.drawLine(int(e), int(m - l), int(e), int(m))
        painter.drawLine(int(m - l), int(e), int(m), int(e))
        painter.drawLine(int(m), int(e + l), int(m), int(e))
        painter.drawLine(int(e + l), int(e), int(e), int(e))
        painter.drawLine(int(e), int(e + l), int(e), int(e))

    elif icon_type == "radar":
        c = QPointF(size * 0.5, size * 0.5)
        painter.drawEllipse(c, size * 0.14, size * 0.14)
        painter.drawArc(QRectF(size * 0.22, size * 0.22, size * 0.56, size * 0.56), 45 * 16, 90 * 16)
        painter.drawArc(QRectF(size * 0.10, size * 0.10, size * 0.80, size * 0.80), 45 * 16, 90 * 16)

    elif icon_type in ("zone", "zone_draw"):
        pen_dash = QPen(fg_color, 1.8, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen_dash)
        painter.drawRoundedRect(QRectF(size * 0.18, size * 0.18, size * 0.64, size * 0.64), 3, 3)
        # Subtle crosshair drafting center
        cross_pen = QPen(fg_color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(cross_pen)
        painter.drawLine(int(size * 0.5), int(size * 0.36), int(size * 0.5), int(size * 0.64))
        painter.drawLine(int(size * 0.36), int(size * 0.5), int(size * 0.64), int(size * 0.5))

    elif icon_type == "eye":
        eye_pen = QPen(fg_color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(eye_pen)
        path = QPainterPath()
        path.moveTo(size * 0.16, size * 0.50)
        path.quadTo(size * 0.50, size * 0.20, size * 0.84, size * 0.50)
        path.quadTo(size * 0.50, size * 0.80, size * 0.16, size * 0.50)
        painter.drawPath(path)
        painter.setBrush(QBrush(fg_color))
        painter.drawEllipse(QPointF(size * 0.50, size * 0.50), size * 0.13, size * 0.13)

    elif icon_type == "zoom_reset":
        z_pen = QPen(fg_color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(z_pen)
        c = QPointF(size * 0.44, size * 0.44)
        r = size * 0.26
        painter.drawEllipse(c, r, r)
        painter.drawLine(int(size * 0.62), int(size * 0.62), int(size * 0.84), int(size * 0.84))
        # Center "1"
        font = QFont("Segoe UI", int(size * 0.30), QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(fg_color)
        painter.drawText(QRectF(size * 0.24, size * 0.24, size * 0.40, size * 0.40), Qt.AlignmentFlag.AlignCenter, "1")

    elif icon_type == "more":
        painter.setBrush(QBrush(fg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        r = size * 0.075
        painter.drawEllipse(QPointF(size * 0.28, size * 0.5), r, r)
        painter.drawEllipse(QPointF(size * 0.50, size * 0.5), r, r)
        painter.drawEllipse(QPointF(size * 0.72, size * 0.5), r, r)

    elif icon_type in ("close", "close_feed"):
        c_pen = QPen(fg_color if custom_color else QColor("#ffffff"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(c_pen)
        m = size * 0.28
        e = size * 0.72
        painter.drawLine(int(m), int(m), int(e), int(e))
        painter.drawLine(int(e), int(m), int(m), int(e))

    elif icon_type == "plus":
        p_pen = QPen(fg_color if custom_color else QColor("#38bdf8"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(p_pen)
        m = size * 0.26
        e = size * 0.74
        mid = size * 0.50
        painter.drawLine(int(round(m)), int(round(mid)), int(round(e)), int(round(mid)))
        painter.drawLine(int(round(mid)), int(round(m)), int(round(mid)), int(round(e)))

    elif icon_type == "camera":
        cam_pen = QPen(fg_color if custom_color else QColor("#38bdf8"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(cam_pen)
        body = QRectF(size * 0.16, size * 0.32, size * 0.68, size * 0.48)
        painter.drawRoundedRect(body, 3, 3)
        top_rect = QRectF(size * 0.36, size * 0.20, size * 0.28, size * 0.14)
        painter.drawRoundedRect(top_rect, 2, 2)
        painter.drawEllipse(QPointF(size * 0.50, size * 0.56), size * 0.15, size * 0.15)

    elif icon_type in ("settings", "gear"):
        pen = QPen(fg_color if custom_color else QColor("#38bdf8"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        c = QPointF(size * 0.5, size * 0.5)
        r_outer = size * 0.30
        r_inner = size * 0.12
        painter.drawEllipse(c, r_inner, r_inner)
        for i in range(8):
            angle = i * (360 / 8)
            rad = math.radians(angle)
            p1 = QPointF(c.x() + math.cos(rad) * (r_outer - 1), c.y() + math.sin(rad) * (r_outer - 1))
            p2 = QPointF(c.x() + math.cos(rad) * (r_outer + 3), c.y() + math.sin(rad) * (r_outer + 3))
            painter.drawLine(p1, p2)
        painter.drawEllipse(c, r_outer, r_outer)

    elif icon_type in ("rename", "edit"):
        pen = QPen(fg_color if custom_color else QColor("#38bdf8"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        path = QPainterPath()
        path.moveTo(size * 0.68, size * 0.22)
        path.lineTo(size * 0.78, size * 0.32)
        path.lineTo(size * 0.36, size * 0.74)
        path.lineTo(size * 0.22, size * 0.78)
        path.lineTo(size * 0.26, size * 0.64)
        path.closeSubpath()
        painter.strokePath(path, pen)
        painter.drawLine(QPointF(size * 0.58, size * 0.32), QPointF(size * 0.68, size * 0.42))

    elif icon_type in ("lens", "tag"):
        pen = QPen(fg_color if custom_color else QColor("#38bdf8"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        c = QPointF(size * 0.5, size * 0.5)
        painter.drawEllipse(c, size * 0.28, size * 0.28)
        painter.drawEllipse(c, size * 0.14, size * 0.14)
        painter.drawArc(QRectF(size * 0.28, size * 0.28, size * 0.44, size * 0.44), 30 * 16, 60 * 16)

    elif icon_type == "quality":
        pen = QPen(fg_color if custom_color else QColor("#38bdf8"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        rect = QRectF(size * 0.16, size * 0.24, size * 0.68, size * 0.52)
        painter.drawRoundedRect(rect, 3, 3)
        font = QFont("Segoe UI", int(size * 0.24), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "HD")

    elif icon_type in ("video", "stream"):
        pen = QPen(fg_color if custom_color else QColor("#38bdf8"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        body = QRectF(size * 0.16, size * 0.28, size * 0.44, size * 0.44)
        painter.drawRoundedRect(body, 2, 2)
        tri = QPainterPath()
        tri.moveTo(size * 0.62, size * 0.40)
        tri.lineTo(size * 0.82, size * 0.28)
        tri.lineTo(size * 0.82, size * 0.72)
        tri.lineTo(size * 0.62, size * 0.60)
        tri.closeSubpath()
        painter.drawPath(tri)

    painter.end()
    return QIcon(pixmap)


def create_phone_signal_pixmap(pct: int, color: str = "#38bdf8", is_online: bool = True, size: QSize = QSize(20, 14)) -> QPixmap:
    """
    Renders an authentic, sleek phone cellular signal indicator with 4 stepped vertical bars:
    - 4 bars active: >= 75%
    - 3 bars active: 50% - 74%
    - 2 bars active: 25% - 49%
    - 1 bar active: 1% - 24%
    - 0 bars active (dimmed): Offline or 0%
    """
    pixmap = QPixmap(size.width(), size.height())
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    if not is_online:
        active_bars = 0
    elif pct >= 75:
        active_bars = 4
    elif pct >= 50:
        active_bars = 3
    elif pct >= 25:
        active_bars = 2
    elif pct > 0:
        active_bars = 1
    else:
        active_bars = 0

    active_color = QColor(color)
    dim_color = QColor(255, 255, 255, 45)

    bar_w = 2.5
    bar_gap = 1.5
    total_w = 4 * bar_w + 3 * bar_gap
    start_x = (size.width() - total_w) / 2.0
    base_y = size.height() - 2.0

    height_ratios = [0.35, 0.55, 0.78, 1.00]
    max_h = size.height() - 4.0

    painter.setPen(Qt.PenStyle.NoPen)
    for i in range(4):
        bx = start_x + i * (bar_w + bar_gap)
        bh = max(2.5, max_h * height_ratios[i])
        by = base_y - bh
        fill_col = active_color if (i < active_bars) else dim_color
        painter.setBrush(QBrush(fill_col))
        painter.drawRoundedRect(QRectF(bx, by, bar_w, bh), 1.0, 1.0)

    painter.end()
    return pixmap


class CameraAssignDialog(QDialog):
    """
    Modern Apple Glass modal dialog to assign an available camera stream
    to an empty video slot or add a new camera to the surveillance system.
    """
    def __init__(self, tile_index: int, available_streams: list, active_assignments: dict = None, parent=None):
        super().__init__(parent)
        self.tile_index = tile_index
        self.available_streams = available_streams or []
        self.active_assignments = active_assignments or {}
        self.selected_stream = None
        self.request_add_new = False

        self.setWindowTitle(f"Assign Camera - Slot #{tile_index + 1}")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setMinimumWidth(460)
        self.setMaximumWidth(520)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 14px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(16)

        # Header Section
        header_widget = QWidget(self)
        h_layout = QHBoxLayout(header_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(14)

        icon_lbl = QLabel(header_widget)
        icon_lbl.setPixmap(create_tile_icon("camera", size=32, custom_color="#38bdf8").pixmap(32, 32))
        h_layout.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        lbl_head = QLabel(f"Assign Camera to Slot #{self.tile_index + 1}", header_widget)
        lbl_head.setStyleSheet("color: #f1f5f9; font-weight: 700; font-size: 15px; font-family: 'Segoe UI', -apple-system, sans-serif;")
        title_box.addWidget(lbl_head)

        lbl_desc = QLabel("Select an active stream to display in this slot, or add a new camera.", header_widget)
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 12px; font-family: 'Segoe UI', -apple-system, sans-serif;")
        title_box.addWidget(lbl_desc)
        h_layout.addLayout(title_box)
        h_layout.addStretch(1)

        layout.addWidget(header_widget)

        # Stream list / Empty state
        self.stream_list = QListWidget(self)
        self.stream_list.setStyleSheet("""
            QListWidget {
                background-color: #080d1a;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 6px;
                color: #f1f5f9;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 6px;
                margin: 2px 0px;
                background-color: rgba(255, 255, 255, 0.03);
            }
            QListWidget::item:hover {
                background-color: rgba(56, 189, 248, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.30);
            }
            QListWidget::item:selected {
                background-color: rgba(2, 132, 199, 0.35);
                border: 1px solid #38bdf8;
                color: #ffffff;
            }
        """)

        cam_icon = create_tile_icon("camera", size=22, custom_color="#38bdf8")

        for s in self.available_streams:
            s_id = s.get("id")
            raw_cam_name = s.get("camera_name", "Camera")
            raw_lens_name = s.get("name", "Stream")
            display_title = format_clean_camera_title(f"{raw_cam_name} • {raw_lens_name}")
            ip_str = s.get("camera_ip") or s.get("rtsp_url", "")
            if len(ip_str) > 42:
                ip_str = ip_str[:39] + "..."

            has_pwd = bool(str(s.get("has_password", "") or s.get("password", "")).strip())
            is_cfg = s.get("is_configured", False) if "is_configured" in s else (bool(s.get("configured", False)) and has_pwd)
            active_slot = self.active_assignments.get(s_id)

            if not is_cfg:
                item_text = f"{display_title}   [Needs Setup]\n{ip_str}"
            elif active_slot:
                item_text = f"{display_title}   [Active in Slot #{active_slot}]\n{ip_str}"
            else:
                item_text = f"{display_title}\n{ip_str}"

            item = QListWidgetItem(cam_icon, item_text)
            item.setData(Qt.ItemDataRole.UserRole, s)
            self.stream_list.addItem(item)

        if self.stream_list.count() > 0:
            self.stream_list.setCurrentRow(0)
            layout.addWidget(self.stream_list)
        else:
            lbl_no_cams = QLabel("No active cameras detected in the system.\nClick '+ Add New Camera' below to set up your device.", self)
            lbl_no_cams.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_no_cams.setStyleSheet("color: #64748b; font-size: 12px; padding: 30px; font-style: italic;")
            layout.addWidget(lbl_no_cams)

        self.stream_list.itemDoubleClicked.connect(self._on_item_double_clicked)

        # Buttons Bar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        # Add New Camera button
        self.btn_add_new = QPushButton("+ Add New Camera...", self)
        self.btn_add_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_new.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.12);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.22);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        self.btn_add_new.clicked.connect(self._on_add_new_clicked)
        btn_bar.addWidget(self.btn_add_new)

        btn_bar.addStretch(1)

        # Keep Slot Empty (Cancel) button
        self.btn_cancel = QPushButton("Keep Slot Empty", self)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                color: #94a3b8;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                color: #f1f5f9;
                border-color: rgba(255, 255, 255, 0.24);
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(self.btn_cancel)

        # Assign Camera (Primary) button
        self.btn_assign = QPushButton("Assign Camera", self)
        self.btn_assign.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_assign.setEnabled(self.stream_list.count() > 0)
        self.btn_assign.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.05);
                color: #475569;
            }
        """)
        self.btn_assign.clicked.connect(self._on_assign_clicked)
        btn_bar.addWidget(self.btn_assign)

        layout.addLayout(btn_bar)

    def _prompt_if_unconfigured(self, stream_data: dict) -> bool:
        if not stream_data:
            return True

        # Check through parent window's device_manager if available
        is_cfg = False
        dev_mgr = None
        p = self.parent()
        while p:
            if hasattr(p, "device_manager"):
                dev_mgr = p.device_manager
                break
            p = p.parent() if hasattr(p, "parent") else None

        cid = stream_data.get("camera_id")
        if dev_mgr and cid:
            cam = dev_mgr.get_camera_by_id(cid)
            if cam:
                is_cfg = dev_mgr.is_camera_configured(cam)

        if not is_cfg and not dev_mgr:
            has_pwd = bool(str(stream_data.get("has_password", "") or stream_data.get("password", "")).strip())
            is_cfg = bool(stream_data.get("configured", False)) and has_pwd

        if not is_cfg:
            cname = stream_data.get("camera_name", "Camera")
            dlg = CameraSetupPromptDialog(camera_name=cname, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.request_configure_cam_id = stream_data.get("camera_id")
                self.accept()
                return False
            return False
        return True

    def _on_item_double_clicked(self, item: QListWidgetItem):
        stream_data = item.data(Qt.ItemDataRole.UserRole)
        if not self._prompt_if_unconfigured(stream_data):
            return
        self.selected_stream = stream_data
        self.accept()

    def _on_assign_clicked(self):
        cur = self.stream_list.currentItem()
        if cur:
            stream_data = cur.data(Qt.ItemDataRole.UserRole)
            if not self._prompt_if_unconfigured(stream_data):
                return
            self.selected_stream = stream_data
            self.accept()

    def _on_add_new_clicked(self):
        self.request_add_new = True
        self.accept()


class VideoTile(QFrame):
    """
    Ultra-flexible video display tile with:
    - Real-time Motion Detection alert indicator
    - AI Person & Animal Detection with Alarms
    - Real-time Audio Playback with 1-click Mute/Unmute
    - Dynamic Quality switching (2K Ultra / Mid HD / Low Sub-stream)
    - Night Vision / Low-Light Contrast Boost toggle
    - Digital Zoom (1x - 5x) with directional PTZ pan & preset recall
    - Full Drag-and-Drop assignment
    - Right-click contextual camera selector
    - Live stats and recording overlay
    """
    tile_selected = pyqtSignal(int)          # tile_index
    solo_toggled = pyqtSignal(int, bool)     # tile_index, is_solo
    tile_double_clicked = pyqtSignal(int)    # tile_index (double click triggers full screen)
    stream_requested = pyqtSignal(int, dict) # tile_index, stream_data
    dual_lens_requested = pyqtSignal(dict)   # camera_data
    stream_closed = pyqtSignal(int)          # tile_index
    ai_alarm_triggered = pyqtSignal(int, str, str, str, float, object) # tile_idx, stream_id, name, target_desc, conf, frame
    audio_toggled = pyqtSignal(int, bool)    # tile_idx, is_unmuted

    def __init__(self, tile_index: int, parent=None):
        super().__init__(parent)
        self.tile_index = tile_index

        # Primary stream
        self.stream_id = None
        self.stream_name = "Empty Slot"
        self.camera_ip = None
        self.stream_info = None
        self.worker: CameraStreamWorker = None
        self.current_frame: QImage = None

        # State
        self.is_selected = False
        self.is_hovered = False
        self.is_solo = False
        self.is_recording = False
        self.status = StreamStatus.IDLE
        self.status_msg = "No Camera Assigned"
        self.width_res = 0
        self.height_res = 0
        self.fps = 0.0
        self.current_quality = QualityMode.ULTRA_2K
        self.night_boost_active = False
        self.color_night_active = False

        # Motion detection state & breathing animation
        self.is_motion_active = False
        self.motion_pulse_alpha = 0
        self._motion_pulse_phase = 0.0
        self.motion_timer = QTimer(self)
        self.motion_timer.setInterval(100)
        self.motion_timer.timeout.connect(self._step_motion_pulse)

        # Recording pulse animation state
        self._rec_pulse_phase = 0.0
        self._rec_elapsed_str = "00:00"
        self.rec_pulse_timer = QTimer(self)
        self.rec_pulse_timer.setInterval(100)
        self.rec_pulse_timer.timeout.connect(self._step_rec_pulse)

        # Close button animation progress
        self._close_progress = 0.0

        # Digital Zoom & Pan state
        self.zoom_level = 1.0
        self.pan_offset = QPoint(0, 0)
        self.is_panning = False
        self.pan_start_pos = QPoint(0, 0)

        # Audio Player
        self.audio_player = AudioPlayer()
        self.is_audio_enabled = False

        # Presets for Digital PTZ
        self.ptz_presets = {
            1: (1.0, QPoint(0, 0)),
            2: (1.8, QPoint(-80, 0)),
            3: (1.8, QPoint(80, 0)),
            4: (2.2, QPoint(0, -60))
        }

        # AI Alert Timer
        self.ai_alert_timer = QTimer(self)
        self.ai_alert_timer.setSingleShot(True)
        self.ai_alert_timer.setInterval(4000)
        self.ai_alert_timer.timeout.connect(self._hide_ai_alert)

        # Snapshot flash animation
        self.flash_alpha = 0
        self.flash_timer = QTimer(self)
        self.flash_timer.setInterval(30)
        self.flash_timer.timeout.connect(self._step_flash)

        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Exclusion / Ignore Zones State
        self.exclusion_zones = []
        self.show_exclusion_zones = False
        self.is_drawing_zone_mode = False
        self.zone_drag_start = None
        self.zone_current_rect = None
        self._last_dest_rect = (0, 0, 0, 0)
        self._dock_slide_offset = 0

        self.setObjectName(f"video_tile_{tile_index}")
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._setup_ui()
        self._update_border()

    def minimumSizeHint(self) -> QSize:
        return QSize(80, 50)

    def sizeHint(self) -> QSize:
        return QSize(320, 180)

    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setStyleSheet("""
            VideoTile {
                background-color: #080c16;
                border: 1px solid #1e293b;
                border-radius: 6px;
            }
        """)

        # Main overlay layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(6, 6, 6, 6)

        # --- Interactive Ignore Zone Banner (Top) ---
        self.zone_banner = QFrame(self)
        self.zone_banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(24, 24, 27, 0.95), stop:1 rgba(9, 9, 11, 0.95));
                border: 1px solid #ef4444;
                border-radius: 6px;
                padding: 2px 4px;
            }
        """)
        zb_layout = QHBoxLayout(self.zone_banner)
        zb_layout.setContentsMargins(6, 2, 6, 2)
        zb_layout.setSpacing(6)

        lbl_zb = QLabel("<b>Exclusion Zone Drawing</b> (Drag mouse over video to define):", self.zone_banner)
        lbl_zb.setStyleSheet("color: #fca5a5; font-size: 11px;")
        zb_layout.addWidget(lbl_zb)

        self.lbl_zone_count = QLabel("0 zones", self.zone_banner)
        self.lbl_zone_count.setStyleSheet("color: #fbbf24; font-weight: bold; font-size: 11px;")
        zb_layout.addWidget(self.lbl_zone_count)

        zb_layout.addStretch()

        btn_zb_clear = QPushButton("Clear All", self.zone_banner)
        btn_zb_clear.setToolTip("Clear all exclusion zones for this camera")
        btn_zb_clear.setStyleSheet("background: #7f1d1d; color: #fecaca; border: 1px solid #ef4444; border-radius: 4px; padding: 2px 8px; font-size: 10px; font-weight: 700;")
        btn_zb_clear.clicked.connect(self.clear_exclusion_zones)
        zb_layout.addWidget(btn_zb_clear)

        btn_zb_done = QPushButton("Save", self.zone_banner)
        btn_zb_done.setToolTip("Save zones and return to normal view")
        btn_zb_done.setStyleSheet("background: #0369a1; color: #e0f2fe; border: 1px solid #38bdf8; border-radius: 4px; padding: 2px 8px; font-size: 10px; font-weight: 700;")
        btn_zb_done.clicked.connect(self.toggle_draw_ignore_zone)
        zb_layout.addWidget(btn_zb_done)

        self.zone_banner.hide()
        self.main_layout.addWidget(self.zone_banner)

        # --- Top Header Overlay (Apple Glass Tag & Close) ---
        self.top_bar = QWidget(self)
        self.top_bar.setStyleSheet("background: transparent;")
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(6, 6, 6, 0)
        top_layout.setSpacing(6)

        # 1. Stretch on left so all capsules anchor cleanly on the top-right
        top_layout.addStretch(1)

        # 2. Capsule A: Frosted Glass Camera Status & Badges
        self.top_tag = QFrame(self.top_bar)
        self.top_tag.setObjectName("top_tag")
        self.top_tag.setStyleSheet("""
            QFrame#top_tag {
                background-color: rgba(15, 23, 42, 0.82);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 14px;
            }
        """)
        tag_layout = QHBoxLayout(self.top_tag)
        tag_layout.setContentsMargins(8, 3, 8, 3)
        tag_layout.setSpacing(6)

        self.slot_badge = QLabel(f"#{self.tile_index + 1}", self.top_tag)
        self.slot_badge.setStyleSheet("color: #64748b; font-weight: 700; font-size: 10px;")
        self.slot_badge.hide()
        tag_layout.addWidget(self.slot_badge)

        self.status_dot = QLabel(self.top_tag)
        self.status_dot.setFixedSize(7, 7)
        self.status_dot.setStyleSheet("background-color: #38bdf8; border-radius: 3.5px;")
        tag_layout.addWidget(self.status_dot)

        self.status_pill = QLabel("IDLE", self.top_tag)
        self.status_pill.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 10px; background: transparent; border: none;")
        tag_layout.addWidget(self.status_pill)

        self.title_label = QLabel(self.stream_name, self.top_tag)
        self.title_label.setMaximumWidth(160)
        self.title_label.setStyleSheet("color: #f8fafc; font-family: 'Segoe UI', Arial, sans-serif; font-weight: 700; font-size: 11px; background: transparent; border: none;")
        tag_layout.addWidget(self.title_label)

        self.badge_signal = QLabel(self.top_tag)
        self.badge_signal.setObjectName("badge_signal")
        self.badge_signal.setFixedSize(26, 20)
        self.badge_signal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge_signal.setStyleSheet("""
            QLabel#badge_signal {
                background-color: rgba(56, 189, 248, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 10px;
                padding: 1px 2px;
            }
        """)
        self.badge_signal.hide()
        tag_layout.addWidget(self.badge_signal)

        self.badge_motion = QLabel("● MOTION", self.top_tag)
        self.badge_motion.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.22);
            border: 1px solid #38bdf8;
            color: #ffffff;
            font-weight: 700;
            font-size: 10px;
            border-radius: 8px;
            padding: 1px 6px;
        """)
        self.motion_opacity_effect = QGraphicsOpacityEffect(self.badge_motion)
        self.motion_opacity_effect.setOpacity(0.0)
        self.badge_motion.setGraphicsEffect(self.motion_opacity_effect)
        self.motion_fade_anim = QPropertyAnimation(self.motion_opacity_effect, b"opacity", self)
        self.motion_fade_anim.finished.connect(self._on_motion_fade_finished)
        self.badge_motion.hide()
        tag_layout.addWidget(self.badge_motion)

        self.badge_ai = QLabel("ALERT", self.top_tag)
        self.badge_ai.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.22);
            border: 1px solid #38bdf8;
            color: #7dd3fc;
            font-weight: 700;
            font-size: 10px;
            border-radius: 8px;
            padding: 1px 6px;
        """)
        self.badge_ai.hide()
        tag_layout.addWidget(self.badge_ai)

        self.rec_badge = QPushButton("● REC 00:00", self.top_tag)
        self.rec_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rec_badge.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.22);
                border: 1px solid #38bdf8;
                color: #ffffff;
                font-weight: 700;
                font-size: 10px;
                border-radius: 8px;
                padding: 1px 6px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.45);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        self.rec_opacity_effect = QGraphicsOpacityEffect(self.rec_badge)
        self.rec_opacity_effect.setOpacity(0.0)
        self.rec_badge.setGraphicsEffect(self.rec_opacity_effect)
        self.rec_fade_anim = QPropertyAnimation(self.rec_opacity_effect, b"opacity", self)
        self.rec_fade_anim.finished.connect(self._on_rec_fade_finished)
        self.rec_badge.clicked.connect(self.toggle_recording)
        self.rec_badge.hide()
        tag_layout.addWidget(self.rec_badge)

        self.badge_wind = QLabel("Wind Filter", self.top_tag)
        self.badge_wind.setStyleSheet("""
            background-color: rgba(2, 132, 199, 0.25);
            border: 1px solid rgba(56, 189, 248, 0.40);
            color: #7dd3fc;
            font-weight: 700;
            font-size: 10px;
            border-radius: 8px;
            padding: 1px 6px;
        """)
        self.badge_wind.hide()
        tag_layout.addWidget(self.badge_wind)

        self.badge_trigger = QLabel("TRIGGER", self.top_tag)
        self.badge_trigger.setStyleSheet("""
            background-color: rgba(37, 99, 235, 0.25);
            border: 1px solid #3b82f6;
            color: #93c5fd;
            font-weight: 700;
            font-size: 10px;
            border-radius: 8px;
            padding: 1px 6px;
        """)
        self.badge_trigger.hide()
        tag_layout.addWidget(self.badge_trigger)

        top_layout.addWidget(self.top_tag)

        # 3. Capsule B: Standalone Circular Frosted Glass White X Close Button with entrance pop & hover glow
        self.btn_close = QPushButton(self.top_bar)
        self.btn_close.setToolTip("Close Feed")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setIcon(create_tile_icon("close", size=24, custom_color="#ffffff"))
        self.btn_close.setIconSize(QSize(7, 7))
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.28);
                border-color: #38bdf8;
            }
            QPushButton:pressed {
                background-color: rgba(2, 132, 199, 0.45);
                border-color: #0284c7;
            }
        """)
        self.btn_close.clicked.connect(self.close_stream)
        self.close_opacity_effect = QGraphicsOpacityEffect(self.btn_close)
        self.close_opacity_effect.setOpacity(0.0)
        self.btn_close.setGraphicsEffect(self.close_opacity_effect)
        self.close_anim = QPropertyAnimation(self, b"close_btn_progress", self)
        self.close_anim.finished.connect(self._on_close_anim_finished)
        self.btn_close.hide()
        top_layout.addWidget(self.btn_close)

        self.main_layout.addWidget(self.top_bar)
        self.main_layout.addStretch(1)

        # --- Empty Slot Center Prompt (Apple Glass Frosted Circle) ---
        self.empty_slot_widget = QWidget(self)
        self.empty_slot_widget.setObjectName("empty_slot_widget")
        self.empty_slot_widget.setStyleSheet("background: transparent;")
        empty_layout = QVBoxLayout(self.empty_slot_widget)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.setSpacing(8)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Center Frosted Circle '+' Button
        self.btn_empty_add = QPushButton(self.empty_slot_widget)
        self.btn_empty_add.setToolTip("Add Camera Stream to Slot")
        self.btn_empty_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_empty_add.setFixedSize(54, 54)
        self.btn_empty_add.setIcon(create_tile_icon("plus", size=26, custom_color="#38bdf8"))
        self.btn_empty_add.setIconSize(QSize(26, 26))
        self.btn_empty_add.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 23, 42, 0.85);
                border: 1.5px solid rgba(56, 189, 248, 0.40);
                border-radius: 27px;
            }
            QPushButton:hover {
                background-color: rgba(14, 116, 144, 0.38);
                border: 2px solid #38bdf8;
            }
            QPushButton:pressed {
                background-color: rgba(14, 116, 144, 0.65);
                border: 2px solid #0284c7;
            }
        """)
        self.btn_empty_add.clicked.connect(self.prompt_assign_camera)
        empty_layout.addWidget(self.btn_empty_add, 0, Qt.AlignmentFlag.AlignCenter)

        # Labels
        self.lbl_empty_title = QLabel("Add Camera", self.empty_slot_widget)
        self.lbl_empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_title.setStyleSheet("""
            color: #f1f5f9;
            font-weight: 700;
            font-size: 13px;
            font-family: 'Segoe UI', -apple-system, sans-serif;
            background: transparent;
            border: none;
        """)
        empty_layout.addWidget(self.lbl_empty_title, 0, Qt.AlignmentFlag.AlignCenter)

        self.lbl_empty_sub = QLabel("Click to assign or drag from sidebar", self.empty_slot_widget)
        self.lbl_empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_sub.setStyleSheet("""
            color: #64748b;
            font-weight: 500;
            font-size: 11px;
            font-family: 'Segoe UI', -apple-system, sans-serif;
            background: transparent;
            border: none;
        """)
        empty_layout.addWidget(self.lbl_empty_sub, 0, Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addWidget(self.empty_slot_widget, 0, Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addStretch(1)

        # --- Bottom Center Controls Overlay (Apple Glass Island) ---
        self.bottom_bar = QWidget(self)
        self.bottom_bar.setStyleSheet("background: transparent;")
        self.bottom_wrap_layout = QHBoxLayout(self.bottom_bar)
        self.bottom_wrap_layout.setContentsMargins(0, 0, 0, 8)
        self.bottom_wrap_layout.setSpacing(0)

        # Horizontal Center Alignment
        self.bottom_wrap_layout.addStretch(1)

        self.control_dock = QFrame(self.bottom_bar)
        self.control_dock.setObjectName("control_dock")
        self.control_dock.setStyleSheet("""
            QFrame#control_dock {
                background-color: rgba(15, 23, 42, 0.82);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 18px;
            }
            QFrame#control_dock:hover {
                background-color: rgba(15, 23, 42, 0.94);
                border-color: rgba(56, 189, 248, 0.40);
            }
        """)
        dock_layout = QHBoxLayout(self.control_dock)
        dock_layout.setContentsMargins(6, 4, 6, 4)
        dock_layout.setSpacing(3)

        # Audio Toggle Button (Pure Icon)
        self.btn_audio = QPushButton(self.control_dock)
        self.btn_audio.setToolTip("Live Audio (Click to Mute / Unmute)")
        self.btn_audio.setIcon(create_tile_icon("audio", active=self.is_audio_enabled, size=24))
        self.btn_audio.setIconSize(QSize(16, 16))
        self.btn_audio.setFixedSize(28, 28)
        self.btn_audio.setStyleSheet(TILE_ACTION_BTN_STYLE)
        self.btn_audio.clicked.connect(self.toggle_audio)
        dock_layout.addWidget(self.btn_audio)

        # Snapshot Button (Pure Icon)
        self.btn_snapshot = QPushButton(self.control_dock)
        self.btn_snapshot.setToolTip("Capture Snapshot (HD)")
        self.btn_snapshot.setIcon(create_tile_icon("snapshot", size=24))
        self.btn_snapshot.setIconSize(QSize(16, 16))
        self.btn_snapshot.setFixedSize(28, 28)
        self.btn_snapshot.setStyleSheet(TILE_ACTION_BTN_STYLE)
        self.btn_snapshot.clicked.connect(self.take_snapshot)
        dock_layout.addWidget(self.btn_snapshot)

        # Manual Record Button (Pure Icon)
        self.btn_record = QPushButton(self.control_dock)
        self.btn_record.setToolTip("Start/Stop Manual Recording")
        self.btn_record.setIcon(create_tile_icon("record", active=False, size=24))
        self.btn_record.setIconSize(QSize(16, 16))
        self.btn_record.setFixedSize(28, 28)
        self.btn_record.setStyleSheet(TILE_ACTION_BTN_STYLE)
        self.btn_record.clicked.connect(self.toggle_recording)
        dock_layout.addWidget(self.btn_record)

        # Divider 1
        sep1 = QFrame(self.control_dock)
        sep1.setFixedSize(1, 14)
        sep1.setStyleSheet("background-color: rgba(255, 255, 255, 0.15);")
        dock_layout.addWidget(sep1)

        # Quality Selector Pill (2K / HD / SD)
        self.btn_quality = QPushButton("2K", self.control_dock)
        self.btn_quality.setToolTip("Switch Quality: 2K Ultra -> 720p HD -> 360p SD")
        self.btn_quality.setFixedSize(36, 22)
        self.btn_quality.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #38bdf8;
                font-weight: 700;
                font-size: 10px;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 11px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.28);
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.btn_quality.clicked.connect(self._cycle_quality)
        dock_layout.addWidget(self.btn_quality)

        # Full Color Night Button (Pure Icon)
        self.btn_color_night = QPushButton(self.control_dock)
        self.btn_color_night.setToolTip("Full-Color Night Mode: Force warm white floodlight & color")
        self.btn_color_night.setIcon(create_tile_icon("color", active=self.color_night_active, size=24))
        self.btn_color_night.setIconSize(QSize(16, 16))
        self.btn_color_night.setFixedSize(28, 28)
        self.btn_color_night.setStyleSheet(TILE_ACTION_BTN_STYLE)
        self.btn_color_night.clicked.connect(self.toggle_color_night_mode)
        dock_layout.addWidget(self.btn_color_night)

        # Night Contrast Boost Button (Pure Icon)
        self.btn_night = QPushButton(self.control_dock)
        self.btn_night.setToolTip("Night Vision Boost: Enhance contrast and low-light shadow detail")
        self.btn_night.setIcon(create_tile_icon("night", active=self.night_boost_active, size=24))
        self.btn_night.setIconSize(QSize(16, 16))
        self.btn_night.setFixedSize(28, 28)
        self.btn_night.setStyleSheet(TILE_ACTION_BTN_STYLE)
        self.btn_night.clicked.connect(self.toggle_night_boost)
        dock_layout.addWidget(self.btn_night)

        # Solo / Maximize Tile (Pure Icon)
        self.btn_solo = QPushButton(self.control_dock)
        self.btn_solo.setToolTip("Maximize / Restore Tile")
        self.btn_solo.setIcon(create_tile_icon("solo", size=24))
        self.btn_solo.setIconSize(QSize(16, 16))
        self.btn_solo.setFixedSize(28, 28)
        self.btn_solo.setStyleSheet(TILE_ACTION_BTN_STYLE)
        self.btn_solo.clicked.connect(self.toggle_solo)
        dock_layout.addWidget(self.btn_solo)

        # Divider 2
        sep2 = QFrame(self.control_dock)
        sep2.setFixedSize(1, 14)
        sep2.setStyleSheet("background-color: rgba(255, 255, 255, 0.15);")
        dock_layout.addWidget(sep2)

        # More Actions Popover Button (•••)
        self.btn_more = QPushButton(self.control_dock)
        self.btn_more.setToolTip("More Camera Tools (Exclusion Zone, Vectors, Zoom Reset)...")
        self.btn_more.setIcon(create_tile_icon("more", size=24))
        self.btn_more.setIconSize(QSize(16, 16))
        self.btn_more.setFixedSize(28, 28)
        self.btn_more.setStyleSheet(TILE_ACTION_BTN_STYLE)
        self.btn_more.clicked.connect(self._show_more_tools_menu)
        dock_layout.addWidget(self.btn_more)

        # Compatibility hidden instances for existing programmatic callbacks
        self.btn_movement_view = QPushButton(self)
        self.btn_movement_view.hide()
        self.btn_ignore_zone = QPushButton(self)
        self.btn_ignore_zone.hide()
        self.btn_reset_zoom = QPushButton(self)
        self.btn_reset_zoom.hide()
        self.show_fps_hud = False
        self.metrics_label = QLabel(self)
        self.metrics_label.setStyleSheet("""
            QLabel {
                background-color: rgba(15, 23, 42, 0.82);
                color: #94a3b8;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 10px;
                font-weight: 600;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                padding: 2px 8px;
            }
        """)
        self.metrics_label.hide()
        self.zoom_badge = QLabel("1.0x", self)
        self.zoom_badge.hide()

        # Add centered dock and push from right
        self.bottom_wrap_layout.addWidget(self.control_dock)
        self.bottom_wrap_layout.addStretch(1)

        # Hardware-composited smooth entrance & exit animations
        self.dock_opacity_effect = QGraphicsOpacityEffect(self.control_dock)
        self.dock_opacity_effect.setOpacity(0.0)
        self.control_dock.setGraphicsEffect(self.dock_opacity_effect)

        self.dock_anim_group = QParallelAnimationGroup(self)
        self.dock_anim_opacity = QPropertyAnimation(self.dock_opacity_effect, b"opacity", self)
        self.dock_anim_slide = QPropertyAnimation(self, b"dock_slide_offset", self)
        self.dock_anim_group.addAnimation(self.dock_anim_opacity)
        self.dock_anim_group.addAnimation(self.dock_anim_slide)
        self.dock_anim_group.finished.connect(self._on_dock_anim_finished)

        self.bottom_bar.hide()
        self.main_layout.addWidget(self.bottom_bar)

        # Initial empty slot state: hide top & bottom controls, reveal centered add prompt
        if not self.stream_id:
            self.empty_slot_widget.show()
            self.top_bar.hide()
            self.bottom_bar.hide()

    def _show_more_tools_menu(self):
        """Opens modern Apple glass popover menu with color-coded vector micro-icons."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(15, 23, 42, 0.96);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 10px;
                padding: 5px;
                color: #f1f5f9;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 600;
            }
            QMenu::item {
                padding: 6px 14px 6px 8px;
                border-radius: 6px;
                margin: 1px 0px;
            }
            QMenu::item:selected {
                background-color: rgba(2, 132, 199, 0.38);
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.10);
                margin: 4px 6px;
            }
        """)

        act_zone = menu.addAction(create_tile_icon("zone_draw", False, 18, custom_color="#38bdf8"), "Draw Exclusion Zone...")
        act_zone.triggered.connect(self.toggle_draw_ignore_zone)

        if self.exclusion_zones:
            is_showing = getattr(self, "show_exclusion_zones", False)
            act_show_zones = menu.addAction(create_tile_icon("eye", is_showing, 18, custom_color="#60a5fa"), "Show Exclusion Zones Overlay")
            act_show_zones.setCheckable(True)
            act_show_zones.setChecked(is_showing)
            act_show_zones.triggered.connect(lambda chk: self.toggle_show_exclusion_zones(chk))

        radar_active = getattr(self, "movement_view_active", False)
        act_radar = menu.addAction(create_tile_icon("radar", radar_active, 18, custom_color="#38bdf8"), "Movement Vector Debug")
        act_radar.setCheckable(True)
        act_radar.setChecked(radar_active)
        act_radar.triggered.connect(self.toggle_movement_view)

        if self.zoom_level > 1.0:
            act_reset_zoom = menu.addAction(create_tile_icon("zoom_reset", False, 18, custom_color="#818cf8"), f"Reset Digital Zoom ({self.zoom_level:.1f}x -> 1:1)")
            act_reset_zoom.triggered.connect(self.reset_zoom)

        if self.width() < 460:
            menu.addSeparator()
            night_active = getattr(self, "night_boost_active", False)
            act_night = menu.addAction(create_tile_icon("night", night_active, 18, custom_color="#f59e0b"), "Night Vision Contrast Boost")
            act_night.setCheckable(True)
            act_night.setChecked(night_active)
            act_night.triggered.connect(self.toggle_night_boost)

            color_active = getattr(self, "color_night_active", False)
            act_color = menu.addAction(create_tile_icon("color", color_active, 18, custom_color="#fb923c"), "Full Color Night Mode")
            act_color.setCheckable(True)
            act_color.setChecked(color_active)
            act_color.triggered.connect(self.toggle_color_night_mode)

        menu.addSeparator()
        show_hud = getattr(self, "show_fps_hud", False)
        act_hud = menu.addAction(create_tile_icon("camera", show_hud, 18, custom_color="#38bdf8"), "Show Resolution & FPS HUD")
        act_hud.setCheckable(True)
        act_hud.setChecked(show_hud)
        act_hud.triggered.connect(lambda chk: self.toggle_fps_hud(chk))

        menu.addSeparator()
        act_close = menu.addAction(create_tile_icon("close_feed", False, 18, custom_color="#ffffff"), "Close Camera Feed")
        act_close.triggered.connect(self.close_stream)

        menu.exec(self.btn_more.mapToGlobal(QPoint(0, -menu.sizeHint().height() - 4)))

    @pyqtProperty(int)
    def dock_slide_offset(self) -> int:
        return self._dock_slide_offset

    @dock_slide_offset.setter
    def dock_slide_offset(self, val: int):
        self._dock_slide_offset = val
        if hasattr(self, "bottom_wrap_layout"):
            self.bottom_wrap_layout.setContentsMargins(0, 0, 0, max(0, val))

    def _should_dock_be_visible(self) -> bool:
        if not self.stream_id:
            return False
        is_hovered = bool(self.is_hovered)
        is_rec = bool(self.is_recording)
        is_drawing = bool(getattr(self, "is_drawing_zone_mode", False))
        is_alerting = bool(self.badge_motion.isVisible() or self.badge_ai.isVisible())
        is_connecting = self.status in (StreamStatus.CONNECTING, StreamStatus.RECONNECTING)
        return is_hovered or is_alerting or is_rec or is_connecting or is_drawing

    def _on_dock_anim_finished(self):
        if not self._should_dock_be_visible() and hasattr(self, "dock_opacity_effect"):
            if self.dock_opacity_effect.opacity() <= 0.05:
                self.bottom_bar.hide()

    @pyqtProperty(float)
    def close_btn_progress(self) -> float:
        return self._close_progress

    @close_btn_progress.setter
    def close_btn_progress(self, val: float):
        self._close_progress = max(0.0, min(1.0, float(val)))
        if hasattr(self, "close_opacity_effect"):
            self.close_opacity_effect.setOpacity(self._close_progress)
        if hasattr(self, "btn_close"):
            icon_sz = int(round(7 + 5 * self._close_progress))
            self.btn_close.setIconSize(QSize(icon_sz, icon_sz))

    def _set_close_button_visible(self, show: bool, animate: bool = True):
        if not hasattr(self, "btn_close") or not hasattr(self, "close_anim"):
            return
        if show:
            if not self.btn_close.isVisible():
                self.btn_close.show()
            if animate:
                if self.close_anim.state() == QPropertyAnimation.State.Running:
                    self.close_anim.stop()
                if self._close_progress < 0.98:
                    self.close_anim.setDuration(200)
                    self.close_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                    self.close_anim.setStartValue(self._close_progress)
                    self.close_anim.setEndValue(1.0)
                    self.close_anim.start()
            else:
                self.close_btn_progress = 1.0
        else:
            if not self.btn_close.isVisible() or self._close_progress <= 0.02:
                self.close_btn_progress = 0.0
                self.btn_close.hide()
                return
            if animate:
                if self.close_anim.state() == QPropertyAnimation.State.Running:
                    self.close_anim.stop()
                self.close_anim.setDuration(200)
                self.close_anim.setEasingCurve(QEasingCurve.Type.InQuad)
                self.close_anim.setStartValue(self._close_progress)
                self.close_anim.setEndValue(0.0)
                self.close_anim.start()
            else:
                self.close_btn_progress = 0.0
                self.btn_close.hide()

    def _on_close_anim_finished(self):
        if self._close_progress <= 0.05 and not (self.is_hovered and bool(self.stream_id)):
            self.btn_close.hide()

    def _set_motion_badge_visible(self, show: bool, animate: bool = True):
        if not hasattr(self, "badge_motion") or not hasattr(self, "motion_fade_anim"):
            return
        if show:
            if not self.badge_motion.isVisible():
                self.badge_motion.show()
            self._step_motion_pulse()
            if animate:
                if self.motion_fade_anim.state() == QPropertyAnimation.State.Running:
                    self.motion_fade_anim.stop()
                cur_op = self.motion_opacity_effect.opacity() if hasattr(self, "motion_opacity_effect") else 0.0
                if cur_op < 0.98:
                    self.motion_fade_anim.setDuration(220)
                    self.motion_fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                    self.motion_fade_anim.setStartValue(cur_op)
                    self.motion_fade_anim.setEndValue(1.0)
                    self.motion_fade_anim.start()
            else:
                if hasattr(self, "motion_opacity_effect"):
                    self.motion_opacity_effect.setOpacity(1.0)
        else:
            if not self.badge_motion.isVisible():
                return
            if animate:
                if self.motion_fade_anim.state() == QPropertyAnimation.State.Running:
                    self.motion_fade_anim.stop()
                cur_op = self.motion_opacity_effect.opacity() if hasattr(self, "motion_opacity_effect") else 1.0
                self.motion_fade_anim.setDuration(250)
                self.motion_fade_anim.setEasingCurve(QEasingCurve.Type.InQuad)
                self.motion_fade_anim.setStartValue(cur_op)
                self.motion_fade_anim.setEndValue(0.0)
                self.motion_fade_anim.start()
            else:
                if hasattr(self, "motion_opacity_effect"):
                    self.motion_opacity_effect.setOpacity(0.0)
                self.badge_motion.hide()
                if self.motion_timer.isActive():
                    self.motion_timer.stop()
                self.motion_pulse_alpha = 0
                self.update()

    def _on_motion_fade_finished(self):
        if hasattr(self, "motion_opacity_effect") and self.motion_opacity_effect.opacity() <= 0.05 and not self.is_motion_active:
            self.badge_motion.hide()
            if self.motion_timer.isActive():
                self.motion_timer.stop()
            self.motion_pulse_alpha = 0
            self.update()

    def _set_rec_badge_visible(self, show: bool, animate: bool = True):
        if not hasattr(self, "rec_badge") or not hasattr(self, "rec_fade_anim"):
            return
        if show:
            if not self.rec_badge.isVisible():
                self.rec_badge.show()
            self._step_rec_pulse()
            if animate:
                if self.rec_fade_anim.state() == QPropertyAnimation.State.Running:
                    self.rec_fade_anim.stop()
                cur_op = self.rec_opacity_effect.opacity() if hasattr(self, "rec_opacity_effect") else 0.0
                if cur_op < 0.98:
                    self.rec_fade_anim.setDuration(220)
                    self.rec_fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                    self.rec_fade_anim.setStartValue(cur_op)
                    self.rec_fade_anim.setEndValue(1.0)
                    self.rec_fade_anim.start()
            else:
                if hasattr(self, "rec_opacity_effect"):
                    self.rec_opacity_effect.setOpacity(1.0)
        else:
            if not self.rec_badge.isVisible():
                return
            if animate:
                if self.rec_fade_anim.state() == QPropertyAnimation.State.Running:
                    self.rec_fade_anim.stop()
                cur_op = self.rec_opacity_effect.opacity() if hasattr(self, "rec_opacity_effect") else 1.0
                self.rec_fade_anim.setDuration(250)
                self.rec_fade_anim.setEasingCurve(QEasingCurve.Type.InQuad)
                self.rec_fade_anim.setStartValue(cur_op)
                self.rec_fade_anim.setEndValue(0.0)
                self.rec_fade_anim.start()
            else:
                if hasattr(self, "rec_opacity_effect"):
                    self.rec_opacity_effect.setOpacity(0.0)
                self.rec_badge.hide()
                if self.rec_pulse_timer.isActive():
                    self.rec_pulse_timer.stop()

    def _on_rec_fade_finished(self):
        if hasattr(self, "rec_opacity_effect") and self.rec_opacity_effect.opacity() <= 0.05 and not self.is_recording:
            self.rec_badge.hide()
            if hasattr(self, "rec_pulse_timer") and self.rec_pulse_timer.isActive():
                self.rec_pulse_timer.stop()

    def _step_rec_pulse(self):
        if not self.is_recording:
            return
        self._rec_pulse_phase += 0.18
        sin_val = (math.sin(self._rec_pulse_phase) + 1.0) / 2.0
        bg_alpha = 0.20 + 0.20 * sin_val
        border_alpha = 0.50 + 0.50 * sin_val
        self.rec_badge.setText(f"● REC {self._rec_elapsed_str}")
        self.rec_badge.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(56, 189, 248, {bg_alpha:.2f});
                border: 1px solid rgba(56, 189, 248, {border_alpha:.2f});
                color: #ffffff;
                font-weight: 700;
                font-size: 10px;
                border-radius: 8px;
                padding: 1px 6px;
            }}
            QPushButton:hover {{
                background-color: rgba(56, 189, 248, 0.45);
                border-color: #38bdf8;
                color: #ffffff;
            }}
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        is_compact = w < 460
        if hasattr(self, "btn_color_night") and hasattr(self, "btn_night"):
            self.btn_color_night.setVisible(bool(self.stream_id) and not is_compact)
            self.btn_night.setVisible(bool(self.stream_id) and not is_compact)
        if hasattr(self, "title_label"):
            if w < 420:
                self.title_label.setMaximumWidth(90)
            else:
                self.title_label.setMaximumWidth(160)

        # Responsive scaling for empty slot center prompt
        if hasattr(self, "empty_slot_widget") and hasattr(self, "lbl_empty_sub"):
            self.lbl_empty_sub.setVisible(w >= 220 and h >= 140)
            if hasattr(self, "lbl_empty_title"):
                self.lbl_empty_title.setVisible(h >= 110)
            if hasattr(self, "btn_empty_add"):
                if w < 160 or h < 120:
                    self.btn_empty_add.setFixedSize(40, 40)
                    self.btn_empty_add.setIconSize(QSize(20, 20))
                    self.btn_empty_add.setStyleSheet("""
                        QPushButton {
                            background-color: rgba(15, 23, 42, 0.85);
                            border: 1.5px solid rgba(56, 189, 248, 0.40);
                            border-radius: 20px;
                        }
                        QPushButton:hover {
                            background-color: rgba(14, 116, 144, 0.38);
                            border: 2px solid #38bdf8;
                        }
                    """)
                else:
                    self.btn_empty_add.setFixedSize(54, 54)
                    self.btn_empty_add.setIconSize(QSize(26, 26))
                    self.btn_empty_add.setStyleSheet("""
                        QPushButton {
                            background-color: rgba(15, 23, 42, 0.85);
                            border: 1.5px solid rgba(56, 189, 248, 0.40);
                            border-radius: 27px;
                        }
                        QPushButton:hover {
                            background-color: rgba(14, 116, 144, 0.38);
                            border: 2px solid #38bdf8;
                        }
                        QPushButton:pressed {
                            background-color: rgba(14, 116, 144, 0.65);
                            border: 2px solid #0284c7;
                        }
                    """)
        if hasattr(self, "metrics_label") and getattr(self, "show_fps_hud", False):
            self._reposition_hud()

    def _reposition_hud(self):
        """Positions the optional resolution and FPS HUD in the bottom-left corner with clean padding."""
        if hasattr(self, "metrics_label"):
            pad = 10
            lbl_w = self.metrics_label.width()
            lbl_h = self.metrics_label.height()
            self.metrics_label.move(pad, max(pad, self.height() - lbl_h - pad))
            self.metrics_label.raise_()

    def toggle_fps_hud(self, show: bool = None):
        """Toggles the optional resolution & FPS HUD pill."""
        if show is None:
            self.show_fps_hud = not getattr(self, "show_fps_hud", False)
        else:
            self.show_fps_hud = bool(show)

        if self.show_fps_hud and getattr(self, "width_res", 0) > 0:
            self.metrics_label.setText(f"{self.width_res}x{self.height_res} • {self.fps:.0f} FPS")
            self.metrics_label.adjustSize()
            self._reposition_hud()
            self.metrics_label.show()
        else:
            self.metrics_label.hide()

    def _update_controls_visibility(self, animate: bool = True):
        """Displays action buttons and bottom-center control dock with sleek, fluid transitions."""
        has_stream = bool(self.stream_id)

        # If tile has no camera stream assigned, keep dock and top bar completely hidden
        if not has_stream:
            if hasattr(self, "empty_slot_widget"):
                self.empty_slot_widget.show()
            if hasattr(self, "top_bar"):
                self.top_bar.hide()
            if hasattr(self, "bottom_bar"):
                self.bottom_bar.hide()
            return

        if hasattr(self, "empty_slot_widget"):
            self.empty_slot_widget.hide()

        is_hovered = bool(self.is_hovered)
        is_rec = bool(self.is_recording)
        is_drawing = bool(getattr(self, "is_drawing_zone_mode", False))
        is_alerting = bool(self.badge_motion.isVisible() or self.badge_ai.isVisible())
        is_connecting = self.status in (StreamStatus.CONNECTING, StreamStatus.RECONNECTING)

        should_show = is_hovered or is_alerting or is_rec or is_connecting or is_drawing

        # Top Bar (Status, Name, Alert Pills, Close Button)
        if hasattr(self, "top_bar"):
            self.top_bar.setVisible(should_show or has_stream or is_connecting)
            if hasattr(self, "btn_close"):
                self._set_close_button_visible(is_hovered and has_stream, animate=animate)

        # Responsive collapse check for bottom dock
        w = self.width()
        is_compact = w < 460
        if hasattr(self, "btn_color_night") and hasattr(self, "btn_night"):
            self.btn_color_night.setVisible(has_stream and not is_compact)
            self.btn_night.setVisible(has_stream and not is_compact)

        if should_show and (is_hovered or is_drawing):
            if not self.bottom_bar.isVisible():
                self.bottom_bar.show()

            self.btn_audio.setVisible(has_stream)
            self.btn_snapshot.setVisible(has_stream)
            self.btn_record.setVisible(has_stream)
            self.btn_quality.setVisible(has_stream)
            self.btn_solo.setVisible(True)
            self.btn_more.setVisible(True)

            if animate and hasattr(self, "dock_anim_group") and hasattr(self, "dock_opacity_effect"):
                if self.dock_anim_group.state() == QParallelAnimationGroup.State.Running:
                    self.dock_anim_group.stop()
                cur_op = self.dock_opacity_effect.opacity()
                cur_slide = getattr(self, "_dock_slide_offset", 0)
                if cur_op < 0.98 or cur_slide < 6:
                    self.dock_anim_opacity.setDuration(220)
                    self.dock_anim_opacity.setEasingCurve(QEasingCurve.Type.OutCubic)
                    self.dock_anim_opacity.setStartValue(cur_op)
                    self.dock_anim_opacity.setEndValue(1.0)

                    self.dock_anim_slide.setDuration(220)
                    self.dock_anim_slide.setEasingCurve(QEasingCurve.Type.OutCubic)
                    self.dock_anim_slide.setStartValue(cur_slide)
                    self.dock_anim_slide.setEndValue(6)

                    self.dock_anim_group.start()
            else:
                if hasattr(self, "dock_opacity_effect"):
                    self.dock_opacity_effect.setOpacity(1.0)
                self.dock_slide_offset = 6
        else:
            if animate and hasattr(self, "dock_anim_group") and hasattr(self, "dock_opacity_effect") and self.bottom_bar.isVisible() and self.dock_opacity_effect.opacity() > 0.02:
                if self.dock_anim_group.state() == QParallelAnimationGroup.State.Running:
                    self.dock_anim_group.stop()
                cur_op = self.dock_opacity_effect.opacity()
                cur_slide = getattr(self, "_dock_slide_offset", 0)

                self.dock_anim_opacity.setDuration(250)
                self.dock_anim_opacity.setEasingCurve(QEasingCurve.Type.InQuad)
                self.dock_anim_opacity.setStartValue(cur_op)
                self.dock_anim_opacity.setEndValue(0.0)

                self.dock_anim_slide.setDuration(250)
                self.dock_anim_slide.setEasingCurve(QEasingCurve.Type.InQuad)
                self.dock_anim_slide.setStartValue(cur_slide)
                self.dock_anim_slide.setEndValue(0)

                self.dock_anim_group.start()
            else:
                self.bottom_bar.hide()
                if hasattr(self, "dock_opacity_effect"):
                    self.dock_opacity_effect.setOpacity(0.0)
                self.dock_slide_offset = 0

    def enterEvent(self, event):
        self.is_hovered = True
        self._update_controls_visibility(animate=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        try:
            pos = self.mapFromGlobal(QCursor.pos())
            if self.rect().contains(pos):
                super().leaveEvent(event)
                return
        except Exception:
            pass
        self.is_hovered = False
        self._update_controls_visibility(animate=True)
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        if not self.is_hovered:
            self.is_hovered = True
            self._update_controls_visibility(animate=True)
        super().mouseMoveEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)

    def assign_stream(self, stream_info: dict, worker: CameraStreamWorker):
        """Attaches a live camera stream worker to this tile."""
        self.stream_info = stream_info
        self.stream_id = stream_info.get("id")
        raw_name = stream_info.get("display_title", stream_info.get("name", "Camera"))
        self.stream_name = format_clean_camera_title(raw_name)
        self.camera_ip = stream_info.get("camera_ip")
        self.title_label.setText(self.stream_name)
        self.title_label.setToolTip(f"Camera Stream: {raw_name}")

        self.worker = worker
        self.worker.frame_ready.connect(self.on_frame_ready)
        self.worker.status_changed.connect(self.on_status_changed)
        self.worker.stats_updated.connect(self.on_stats_updated)
        self.worker.recording_status.connect(self.on_recording_status)
        self.worker.motion_event.connect(self.on_motion_event)
        self.worker.quality_changed.connect(self.on_quality_changed)
        self.worker.ai_alarm_detected.connect(self.on_ai_alarm_detected)
        self.worker.wind_shake_detected.connect(self.on_wind_shake_detected)
        if hasattr(self.worker, "trigger_event"):
            self.worker.trigger_event.connect(self.on_trigger_event)

        self.current_quality = self.worker.quality_mode
        self.btn_quality.setText(self.current_quality)
        self._update_movement_view_btn_style(getattr(self.worker, "movement_view_enabled", False))

        # Load exclusion zones from device manager or stream_info
        parent_win = self.window()
        dev_mgr = getattr(parent_win, "device_manager", None)
        if dev_mgr and self.stream_id:
            cam_id = stream_info.get("camera_id")
            self.exclusion_zones = dev_mgr.get_stream_exclusion_zones(self.stream_id, cam_id)
        elif "exclusion_zones" in stream_info:
            self.exclusion_zones = list(stream_info.get("exclusion_zones", []))
        else:
            self.exclusion_zones = list(getattr(self.worker, "exclusion_zones", []))

        if self.worker:
            self.worker.set_exclusion_zones(self.exclusion_zones)
        self._update_ignore_zone_btn_style()

        if hasattr(self, "empty_slot_widget"):
            self.empty_slot_widget.hide()

        self._update_controls_visibility()
        self.update()

    def detach_stream(self):
        """Detaches worker from this tile."""
        if self.worker:
            try:
                self.worker.frame_ready.disconnect(self.on_frame_ready)
                self.worker.status_changed.disconnect(self.on_status_changed)
                self.worker.stats_updated.disconnect(self.on_stats_updated)
                self.worker.recording_status.disconnect(self.on_recording_status)
                self.worker.motion_event.disconnect(self.on_motion_event)
                self.worker.quality_changed.disconnect(self.on_quality_changed)
                self.worker.ai_alarm_detected.disconnect(self.on_ai_alarm_detected)
                self.worker.wind_shake_detected.disconnect(self.on_wind_shake_detected)
                if hasattr(self.worker, "trigger_event"):
                    self.worker.trigger_event.disconnect(self.on_trigger_event)
            except Exception:
                pass
            self.badge_trigger.hide()
            self.worker = None

        if self.audio_player.is_playing():
            self.audio_player.stop()
        self.is_audio_enabled = False
        self.btn_audio.setText("Audio")
        self.stream_id = None
        self.stream_info = None
        self.stream_name = "Empty Slot"
        self.title_label.setText(self.stream_name)
        self.title_label.setToolTip("")
        self.status = StreamStatus.IDLE
        self.status_msg = "No Camera Assigned"
        self.current_frame = None
        self.is_motion_active = False
        self._set_motion_badge_visible(False, animate=False)
        self.badge_ai.hide()
        self.badge_wind.hide()
        self.badge_signal.hide()
        self.metrics_label.hide()
        self.zoom_badge.hide()
        self._set_rec_badge_visible(False, animate=False)
        self._set_close_button_visible(False, animate=False)
        self.exclusion_zones = []
        self.is_drawing_zone_mode = False
        self.zone_banner.hide()
        self.btn_ignore_zone.hide()
        if hasattr(self, "empty_slot_widget"):
            self.empty_slot_widget.show()
        if hasattr(self, "top_bar"):
            self.top_bar.hide()
        if hasattr(self, "bottom_bar"):
            self.bottom_bar.hide()
        self._update_controls_visibility()
        self._update_status_ui()
        self.update()

    def update_signal_info(self, sig: dict):
        """Updates the live phone-style cellular signal indicator on this video tile."""
        is_streaming_live = (self.worker is not None and getattr(self.worker, "status", None) == StreamStatus.LIVE) or (self.fps > 0) or (self.current_frame is not None)

        if not sig or not sig.get("is_online"):
            if is_streaming_live:
                pct = 95
                pix = create_phone_signal_pixmap(pct=pct, color="#38bdf8", is_online=True)
                self.badge_signal.setPixmap(pix)
                self.badge_signal.setStyleSheet("""
                    QLabel#badge_signal {
                        background-color: rgba(56, 189, 248, 0.12);
                        border: 1px solid rgba(56, 189, 248, 0.35);
                        border-radius: 10px;
                        padding: 1px 2px;
                    }
                """)
                fps_txt = f"{self.fps:.0f} FPS" if self.fps > 0 else "Live"
                self.badge_signal.setToolTip(f"Signal: 95% (4/4 Bars Cellular Health)\nCamera Active / Streaming Live ({fps_txt})")
                self.badge_signal.show()
                return

            pix = create_phone_signal_pixmap(pct=0, color="#94a3b8", is_online=False)
            self.badge_signal.setPixmap(pix)
            self.badge_signal.setStyleSheet("""
                QLabel#badge_signal {
                    background-color: rgba(15, 23, 42, 0.65);
                    border: 1px solid rgba(148, 163, 184, 0.25);
                    border-radius: 10px;
                    padding: 1px 2px;
                }
            """)
            self.badge_signal.setToolTip("Signal Offline (0/4 Bars - Connection timed out)")
            self.badge_signal.show()
            return

        pct = sig.get("percent", 80)
        lat = sig.get("latency_ms", 0)
        pix = create_phone_signal_pixmap(pct=pct, color="#38bdf8", is_online=True)
        self.badge_signal.setPixmap(pix)
        self.badge_signal.setStyleSheet("""
            QLabel#badge_signal {
                background-color: rgba(56, 189, 248, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 10px;
                padding: 1px 2px;
            }
        """)
        bars = 4 if pct >= 75 else 3 if pct >= 50 else 2 if pct >= 25 else 1 if pct > 0 else 0
        self.badge_signal.setToolTip(f"Signal: {pct}% ({bars}/4 Bars Cellular Health)\nLatency: {lat:.1f}ms")
        self.badge_signal.show()

    def on_wind_shake_detected(self, s_id: str, is_shaking: bool):
        if s_id != self.stream_id:
            return
        if is_shaking:
            self.badge_wind.show()
        else:
            self.badge_wind.hide()
        self.update()

    def close_stream(self):
        self.stream_closed.emit(self.tile_index)
        self.detach_stream()

    def on_ai_alarm_detected(self, s_id: str, s_name: str, target_desc: str, conf: float, frame: object):
        if s_id != self.stream_id:
            return
        if target_desc:
            td_lower = target_desc.lower()
            conf_str = f" {int(conf * 100)}%" if conf > 0 else ""
            if "person" in td_lower:
                short_tag = f"PERSON{conf_str}"
                theme_color = "#f43f5e"
            elif "car" in td_lower:
                short_tag = f"CAR{conf_str}"
                theme_color = "#38bdf8"
            elif "truck" in td_lower:
                short_tag = f"TRUCK{conf_str}"
                theme_color = "#38bdf8"
            elif "motorcycle" in td_lower:
                short_tag = f"MOTORCYCLE{conf_str}"
                theme_color = "#38bdf8"
            elif "vehicle" in td_lower:
                short_tag = f"VEHICLE{conf_str}"
                theme_color = "#38bdf8"
            elif "dog" in td_lower:
                short_tag = f"DOG{conf_str}"
                theme_color = "#f59e0b"
            elif "cat" in td_lower:
                short_tag = f"CAT{conf_str}"
                theme_color = "#f59e0b"
            elif "animal" in td_lower:
                short_tag = f"ANIMAL{conf_str}"
                theme_color = "#f59e0b"
            else:
                first_word = target_desc.split(":")[0].strip().upper()
                short_tag = f"{first_word}{conf_str}"
                theme_color = "#38bdf8"

            self.current_motion_label = short_tag
            self.current_motion_color = theme_color
            self.current_motion_time = time.time()
            self._set_motion_badge_visible(True, animate=True)
            self.badge_ai.hide()
            self.ai_alert_timer.start()
        self.ai_alarm_triggered.emit(self.tile_index, s_id, s_name, target_desc, conf, frame)

    def _hide_ai_alert(self):
        self.badge_ai.hide()
        if not self.is_motion_active:
            self._set_motion_badge_visible(False, animate=True)
        else:
            self.current_motion_label = "MOTION"
            self.current_motion_color = "#38bdf8"
            self._step_motion_pulse()

    def toggle_audio(self):
        if not self.stream_info:
            return
        rtsp_url = self.stream_info.get("url")
        if not rtsp_url:
            return

        if self.is_audio_enabled:
            self.audio_player.stop()
            self.is_audio_enabled = False
            self.btn_audio.setText("")
            self.btn_audio.setIcon(create_tile_icon("audio", active=False, size=24))
            self.btn_audio.setStyleSheet(TILE_ACTION_BTN_STYLE)
            self.btn_audio.setToolTip("Live Audio (Click to Unmute)")
        else:
            self.audio_player.play(rtsp_url, volume=100)
            self.is_audio_enabled = True
            self.btn_audio.setText("")
            self.btn_audio.setIcon(create_tile_icon("audio", active=True, size=24))
            self.btn_audio.setStyleSheet("background-color: rgba(2, 132, 199, 0.35); border-radius: 14px; border: none;")
            self.btn_audio.setToolTip("Audio Playing (Click to Mute)")
        self.audio_toggled.emit(self.tile_index, self.is_audio_enabled)

    # --- Digital PTZ Methods ---
    def pan_by(self, dx: int, dy: int):
        """Smoothly shifts the viewport in the active direction (Digital PTZ)."""
        if self.zoom_level > 1.0:
            self.pan_offset += QPoint(dx, dy)
            self.update()

    def zoom_by(self, delta: float):
        """Smoothly zooms in/out (Digital PTZ Zoom)."""
        self.zoom_level = max(1.0, min(5.0, self.zoom_level + delta))
        if self.zoom_level > 1.0:
            self.zoom_badge.setText(f"{self.zoom_level:.1f}x")
            self.zoom_badge.show()
            self.btn_reset_zoom.show()
        else:
            self.reset_zoom()
        self.update()

    def goto_preset(self, preset_num: int):
        p = max(1, min(4, int(preset_num)))
        if p in self.ptz_presets:
            zoom, offset = self.ptz_presets[p]
            self.zoom_level = zoom
            self.pan_offset = QPoint(offset.x(), offset.y())
            if self.zoom_level > 1.0:
                self.zoom_badge.setText(f"{self.zoom_level:.1f}x")
                self.zoom_badge.show()
                self.btn_reset_zoom.show()
            else:
                self.zoom_badge.hide()
                self.btn_reset_zoom.hide()
            self.update()

    def save_preset(self, preset_num: int):
        p = max(1, min(4, int(preset_num)))
        self.ptz_presets[p] = (self.zoom_level, QPoint(self.pan_offset.x(), self.pan_offset.y()))

    def on_frame_ready(self, s_id: str, q_img: QImage, w: int, h: int, fps: float):
        if s_id != self.stream_id or self.isHidden():
            return
        self.current_frame = q_img
        self.width_res = w
        self.height_res = h
        self.fps = fps
        if self.badge_signal.text() == "Offline":
            self.badge_signal.setText("95%")
            self.badge_signal.setStyleSheet("""
                background-color: rgba(15, 23, 42, 0.9);
                color: #38bdf8;
                font-weight: 700;
                font-size: 11px;
                border-radius: 4px;
                padding: 2px 6px;
                border: 1px solid #38bdf8;
            """)
            self.badge_signal.setToolTip(f"Camera Active / Streaming Live ({fps:.0f} FPS)")
            self.badge_signal.show()
        self.update()

    def update_status(self, message: str, color: str = "#38bdf8"):
        """Updates tile status message overlay and refreshes display."""
        self.status_msg = message
        if hasattr(self, "badge_signal") and self.badge_signal is not None:
            self.badge_signal.setText(message[:14] if len(message) > 14 else message)
            self.badge_signal.setStyleSheet(f"""
                background-color: rgba(15, 23, 42, 0.9);
                color: {color};
                font-weight: 700;
                font-size: 11px;
                border-radius: 4px;
                padding: 2px 6px;
                border: 1px solid {color};
            """)
            self.badge_signal.show()
        self.update()

    def on_status_changed(self, s_id: str, status: str, message: str):
        if s_id != self.stream_id:
            return
        self.status = status
        self.status_msg = message
        if status == StreamStatus.LIVE and self.badge_signal.text() == "Offline":
            self.badge_signal.setText("95%")
            self.badge_signal.setStyleSheet("""
                background-color: rgba(15, 23, 42, 0.9);
                color: #38bdf8;
                font-weight: 700;
                font-size: 11px;
                border-radius: 4px;
                padding: 2px 6px;
                border: 1px solid #38bdf8;
            """)
            self.badge_signal.setToolTip("Camera Active / Streaming Live")
            self.badge_signal.show()
        self._update_status_ui()

    def on_stats_updated(self, s_id: str, fps: float, w: int, h: int):
        if s_id != self.stream_id:
            return
        self.fps = fps
        self.width_res = w
        self.height_res = h
        if getattr(self, "show_fps_hud", False):
            self.metrics_label.setText(f"{w}x{h} • {fps:.0f} FPS")
            self.metrics_label.adjustSize()
            self._reposition_hud()
            self.metrics_label.show()
        else:
            self.metrics_label.hide()

    def on_recording_status(self, s_id: str, is_recording: bool, elapsed_str: str):
        if s_id != self.stream_id:
            return
        self.is_recording = is_recording
        self._rec_elapsed_str = elapsed_str
        if is_recording:
            self._set_rec_badge_visible(True, animate=True)
            if not self.rec_pulse_timer.isActive():
                self.rec_pulse_timer.start()
            self._step_rec_pulse()
        else:
            self._set_rec_badge_visible(False, animate=True)
            self.btn_record.setIcon(create_tile_icon("record", active=False))
            self.btn_record.setStyleSheet(TILE_ACTION_BTN_STYLE)
        self._update_controls_visibility()

    def on_motion_event(self, s_id: str, is_motion: bool, num_targets: int):
        if s_id != self.stream_id:
            return
        self.is_motion_active = is_motion
        if is_motion:
            now = time.time()
            if (now - getattr(self, "current_motion_time", 0.0)) > 8.0:
                self.current_motion_label = "MOTION"
                self.current_motion_color = "#38bdf8"
            self._set_motion_badge_visible(True, animate=True)
            if not self.motion_timer.isActive():
                self.motion_timer.start()
        else:
            self._set_motion_badge_visible(False, animate=True)

    @pyqtSlot(str, bool, str, dict)
    def on_trigger_event(self, s_id: str, is_triggered: bool, reason: str, details: dict):
        if s_id != self.stream_id:
            return
        # Internal event tracking - keep display clean without duplicate badges
        pass

    def _check_hide_trigger_badge(self):
        self.badge_trigger.hide()

    def toggle_movement_view(self):
        if not self.worker:
            return
        current = getattr(self.worker, "movement_view_enabled", False)
        new_state = not current
        self.worker.set_movement_view(new_state)
        self.movement_view_active = new_state
        self._update_movement_view_btn_style(new_state)
        self._update_controls_visibility()

    def _update_movement_view_btn_style(self, active: bool):
        if active:
            self.btn_movement_view.setStyleSheet("""
                QPushButton {
                    background-color: #06b6d4;
                    color: #030712;
                    border: 1px solid #22d3ee;
                    font-size: 13px;
                    font-weight: 800;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #22d3ee; }
            """)
        else:
            self.btn_movement_view.setStyleSheet(TILE_ACTION_BTN_STYLE)

    def toggle_draw_ignore_zone(self):
        """Toggles interactive click-and-drag drawing mode for ignore / exclusion zones."""
        if not self.stream_id:
            return
        self.is_drawing_zone_mode = not self.is_drawing_zone_mode
        self._update_ignore_zone_btn_style()
        self._update_controls_visibility()

        if self.is_drawing_zone_mode:
            self.zone_banner.show()
            self._update_zone_count_label()
            self.setCursor(Qt.CursorShape.CrossCursor)
            parent_win = self.window()
            if hasattr(parent_win, "statusBar"):
                parent_win.statusBar().showMessage("Exclusion zones active: Drag with mouse to define a zone or click zone button to finish.", 5000)
        else:
            self.zone_banner.hide()
            self.unsetCursor()
            self._save_exclusion_zones()
            parent_win = self.window()
            if hasattr(parent_win, "statusBar"):
                parent_win.statusBar().showMessage(f"Exclusion zones saved ({len(self.exclusion_zones)} active).", 4000)
        self.update()

    def open_zone_editor_dialog(self):
        """Opens dedicated visual ZoneEditorDialog with freeze preview."""
        if not self.stream_id:
            return
        dlg = ZoneEditorDialog(self.stream_name, self.current_frame, self.exclusion_zones, parent=self.window())
        if dlg.exec():
            self.exclusion_zones = dlg.get_configured_zones()
            if self.worker:
                self.worker.set_exclusion_zones(self.exclusion_zones)
            self._save_exclusion_zones()
            self._update_zone_count_label()
            self._update_ignore_zone_btn_style()
            self.update()
            parent_win = self.window()
            if hasattr(parent_win, "statusBar"):
                parent_win.statusBar().showMessage(f"Exclusion zones updated ({len(self.exclusion_zones)} active).", 3500)

    def toggle_show_exclusion_zones(self, show: bool):
        self.show_exclusion_zones = bool(show)
        self.update()

    def clear_exclusion_zones(self):
        self.exclusion_zones = []
        if self.worker:
            self.worker.set_exclusion_zones([])
        self._save_exclusion_zones()
        self._update_zone_count_label()
        self._update_ignore_zone_btn_style()
        self.update()
        parent_win = self.window()
        if hasattr(parent_win, "statusBar"):
            parent_win.statusBar().showMessage("All exclusion zones cleared.", 3500)

    def _save_exclusion_zones(self):
        parent_win = self.window()
        dev_mgr = getattr(parent_win, "device_manager", None)
        if dev_mgr and self.stream_info:
            cam_id = self.stream_info.get("camera_id")
            dev_mgr.set_stream_exclusion_zones(self.stream_id, self.exclusion_zones, cam_id)
        if self.worker:
            self.worker.set_exclusion_zones(self.exclusion_zones)

    def _update_zone_count_label(self):
        cnt = len(self.exclusion_zones)
        self.lbl_zone_count.setText(f"{cnt} {'zone' if cnt == 1 else 'zones'}")

    def _update_ignore_zone_btn_style(self):
        if self.is_drawing_zone_mode:
            self.btn_ignore_zone.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: #ffffff;
                    border: 1px solid #f87171;
                    font-size: 13px;
                    font-weight: 800;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #dc2626; }
            """)
        else:
            self.btn_ignore_zone.setStyleSheet(TILE_ACTION_BTN_STYLE)

    def on_quality_changed(self, s_id_or_mode: str, mode: Optional[str] = None):
        if mode is None:
            target_mode = s_id_or_mode
        else:
            if s_id_or_mode and s_id_or_mode != self.stream_id:
                return
            target_mode = mode
        self.current_quality = target_mode
        self.btn_quality.setText(target_mode)

    def _cycle_quality(self):
        """Cycles quality: MAX -> 2K -> MID -> LOW -> MAX"""
        if not self.worker:
            return
        if self.current_quality == QualityMode.ULTRA_MAX:
            new_q = QualityMode.ULTRA_2K
        elif self.current_quality == QualityMode.ULTRA_2K:
            new_q = QualityMode.MID_HD
        elif self.current_quality == QualityMode.MID_HD:
            new_q = QualityMode.LOW_SD
        else:
            new_q = QualityMode.ULTRA_MAX
        self.set_quality(new_q)

    def set_quality(self, mode: str):
        if self.worker:
            self.worker.set_quality(mode)

    def toggle_night_boost(self):
        self.night_boost_active = not self.night_boost_active
        if self.worker:
            self.worker.set_night_boost(self.night_boost_active)
        self.btn_night.setIcon(create_tile_icon("night", active=self.night_boost_active, size=24))
        if self.night_boost_active:
            self.btn_night.setStyleSheet("background-color: rgba(56, 189, 248, 0.28); border-radius: 14px; border: 1px solid #38bdf8;")
        else:
            self.btn_night.setStyleSheet(TILE_ACTION_BTN_STYLE)

        parent_win = self.window()
        dev_mgr = getattr(parent_win, "device_manager", None)
        if dev_mgr and self.stream_info:
            cam_id = self.stream_info.get("camera_id")
            if cam_id:
                cur = dev_mgr.get_camera_settings(cam_id)
                cur["night_mode"] = NightVisionMode.COLOR_BOOST if self.night_boost_active else NightVisionMode.OFF
                dev_mgr.update_camera_settings(cam_id, cur)

    def toggle_color_night_mode(self):
        """Toggles Full-Color Night Mode for this camera stream."""
        self.color_night_active = not self.color_night_active
        if self.worker:
            self.worker.set_color_night_mode(self.color_night_active)

        self.btn_color_night.setText("")
        self.btn_color_night.setIcon(create_tile_icon("color", active=self.color_night_active, size=24))
        if self.color_night_active:
            self.btn_color_night.setStyleSheet("background-color: rgba(245, 158, 11, 0.28); border-radius: 14px; border: 1px solid #f59e0b;")
            self.btn_color_night.setToolTip("Color Night Mode ACTIVE: Full night colors forced (Click to turn off)")
        else:
            self.btn_color_night.setStyleSheet(TILE_ACTION_BTN_STYLE)
            self.btn_color_night.setToolTip("Color Night Mode: Click to Force Full Color at Night")

        parent_win = self.window()
        dev_mgr = getattr(parent_win, "device_manager", None)
        if dev_mgr and self.stream_info:
            cam_id = self.stream_info.get("camera_id")
            if cam_id:
                cur = dev_mgr.get_camera_settings(cam_id)
                cur["night_mode"] = NightVisionMode.COLOR_NIGHT if self.color_night_active else NightVisionMode.OFF
                dev_mgr.update_camera_settings(cam_id, cur)

        # Dispatches camera hardware white light floodlight command if controller available
        if dev_mgr and self.camera_ip:
            from core.ptz_controller import PTZController
            for cam in dev_mgr.get_cameras():
                if cam.get("ip") == self.camera_ip:
                    user = cam.get("username", "admin")
                    pwd = cam.get("password", "")
                    port = int(cam.get("onvif_port", 8899))
                    try:
                        ctrl = PTZController(self.camera_ip, user, pwd, port=port)
                        ctrl.set_white_light(self.color_night_active)
                    except Exception:
                        pass
                    break

        self._update_controls_visibility()
        self.update()

    def _step_motion_pulse(self):
        self._motion_pulse_phase += 0.22
        sin_val = (math.sin(self._motion_pulse_phase) + 1.0) / 2.0
        bg_alpha = 0.18 + 0.22 * sin_val
        border_alpha = 0.50 + 0.50 * sin_val
        lbl_text = getattr(self, "current_motion_label", "MOTION")
        col_hex = getattr(self, "current_motion_color", "#38bdf8")
        if hasattr(self, "badge_motion") and self.badge_motion.isVisible():
            self.badge_motion.setText(f"● {lbl_text}")
            self.badge_motion.setStyleSheet(f"""
                QLabel {{
                    background-color: rgba(56, 189, 248, {bg_alpha:.2f});
                    border: 1px solid {col_hex};
                    color: #ffffff;
                    font-weight: 700;
                    font-size: 10px;
                    border-radius: 8px;
                    padding: 1px 6px;
                }}
            """)
        self.motion_pulse_alpha = int(100 + 130 * sin_val)
        self.update()

    def _update_status_ui(self):
        if self.status == StreamStatus.LIVE:
            self.status_pill.setText("LIVE")
            self.status_pill.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 10px; background: transparent; border: none;")
            if hasattr(self, "status_dot"):
                self.status_dot.setStyleSheet("background-color: #38bdf8; border-radius: 4px;")
        elif self.status == StreamStatus.CONNECTING:
            self.status_pill.setText("CONNECTING")
            self.status_pill.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 10px; background: transparent; border: none;")
            if hasattr(self, "status_dot"):
                self.status_dot.setStyleSheet("background-color: #38bdf8; border-radius: 4px;")
        elif self.status == StreamStatus.RECONNECTING:
            self.status_pill.setText("RECONNECTING")
            self.status_pill.setStyleSheet("color: #7dd3fc; font-weight: 700; font-size: 10px; background: transparent; border: none;")
            if hasattr(self, "status_dot"):
                self.status_dot.setStyleSheet("background-color: #60a5fa; border-radius: 4px;")
        elif self.status == StreamStatus.ERROR:
            self.status_pill.setText("OFFLINE")
            self.status_pill.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 10px; background: transparent; border: none;")
            if hasattr(self, "status_dot"):
                self.status_dot.setStyleSheet("background-color: #64748b; border-radius: 4px;")
        else:
            self.status_pill.setText("IDLE")
            self.status_pill.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 10px; background: transparent; border: none;")
            if hasattr(self, "status_dot"):
                self.status_dot.setStyleSheet("background-color: #64748b; border-radius: 4px;")

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._update_border()
        self._update_controls_visibility()

    def _update_border(self):
        if self.is_selected:
            self.setStyleSheet("""
                VideoTile {
                    background-color: #080c16;
                    border: 2px solid #3b82f6;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                VideoTile {
                    background-color: #080c16;
                    border: 1px solid #1e293b;
                    border-radius: 6px;
                }
            """)

    def paintEvent(self, event):
        if not self.isVisible() or self.isHidden():
            return

        rect = self.rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self.current_frame and not self.current_frame.isNull():
            img = self.current_frame
            img_w = img.width()
            img_h = img.height()

            aspect = (img_w / img_h) if img_h > 0 else 16.0 / 9.0
            widget_aspect = rect.width() / max(rect.height(), 1)

            if widget_aspect > aspect:
                dest_h = rect.height()
                dest_w = int(dest_h * aspect)
                dest_x = (rect.width() - dest_w) // 2
                dest_y = 0
            else:
                dest_w = rect.width()
                dest_h = int(dest_w / aspect)
                dest_x = 0
                dest_y = (rect.height() - dest_h) // 2

            if self.zoom_level > 1.0:
                crop_w = img_w / self.zoom_level
                crop_h = img_h / self.zoom_level
                center_x = (img_w / 2.0) - (self.pan_offset.x() * (img_w / max(rect.width(), 1)))
                center_y = (img_h / 2.0) - (self.pan_offset.y() * (img_h / max(rect.height(), 1)))
                crop_x = max(0.0, min(img_w - crop_w, center_x - crop_w / 2.0))
                crop_y = max(0.0, min(img_h - crop_h, center_y - crop_h / 2.0))
                src_rect = QRectF(crop_x, crop_y, crop_w, crop_h)
                dest_rect = QRectF(dest_x, dest_y, dest_w, dest_h)
                painter.drawImage(dest_rect, img, src_rect)
            else:
                crop_x = 0.0
                crop_y = 0.0
                crop_w = float(img_w)
                crop_h = float(img_h)
                dest_rect_i = QRect(dest_x, dest_y, dest_w, dest_h)
                src_rect_i = QRect(0, 0, img_w, img_h)
                painter.drawImage(dest_rect_i, img, src_rect_i)

            norm_crop_x = (crop_x / img_w) if img_w > 0 else 0.0
            norm_crop_y = (crop_y / img_h) if img_h > 0 else 0.0
            norm_crop_w = (crop_w / img_w) if img_w > 0 else 1.0
            norm_crop_h = (crop_h / img_h) if img_h > 0 else 1.0

            self._last_crop_norm = (norm_crop_x, norm_crop_y, norm_crop_w, norm_crop_h)
            self._last_dest_rect = (dest_x, dest_y, dest_w, dest_h)

            # --- Draw Configured Exclusion / Ignore Zones (Anchored to scene under Digital PTZ Zoom) ---
            if self.exclusion_zones and (self.is_drawing_zone_mode or getattr(self, "show_exclusion_zones", False)):
                painter.save()
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                # Clip strictly to the displayed video rectangle so zoomed zones do not bleed onto black borders or dock
                painter.setClipRect(QRectF(dest_x, dest_y, dest_w, dest_h))

                for z_idx, zone in enumerate(self.exclusion_zones):
                    if len(zone) < 4:
                        continue
                    zx1, zy1, zx2, zy2 = zone[:4]
                    min_x = min(zx1, zx2)
                    max_x = max(zx1, zx2)
                    min_y = min(zy1, zy2)
                    max_y = max(zy1, zy2)

                    # Project full-image normalized coordinates into zoomed/panned viewport
                    px_x1 = dest_x + ((min_x - norm_crop_x) / norm_crop_w) * dest_w
                    px_y1 = dest_y + ((min_y - norm_crop_y) / norm_crop_h) * dest_h
                    px_x2 = dest_x + ((max_x - norm_crop_x) / norm_crop_w) * dest_w
                    px_y2 = dest_y + ((max_y - norm_crop_y) / norm_crop_h) * dest_h

                    px_x = int(round(px_x1))
                    px_y = int(round(px_y1))
                    px_w = int(round(px_x2 - px_x1))
                    px_h = int(round(px_y2 - px_y1))
                    z_rect = QRect(px_x, px_y, px_w, px_h)

                    # Translucent red overlay
                    painter.fillRect(z_rect, QColor(239, 68, 68, 45))

                    # High-visibility red dashed border
                    pen_zone = QPen(QColor(239, 68, 68, 220), 2, Qt.PenStyle.DashLine)
                    painter.setPen(pen_zone)
                    painter.drawRect(z_rect)

                    # Sleek HUD label tag
                    lbl_text = f" IGNORE #{z_idx + 1} "
                    painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    tag_w = 85
                    tag_h = 18
                    tag_y = max(dest_y, px_y - tag_h)
                    tag_x = max(dest_x, px_x)
                    painter.fillRect(QRect(tag_x, tag_y, tag_w, tag_h), QColor(220, 38, 38, 230))
                    painter.setPen(QColor(255, 255, 255))
                    painter.drawText(QRect(tag_x + 2, tag_y, tag_w - 2, tag_h), Qt.AlignmentFlag.AlignVCenter, lbl_text)

                painter.restore()

            # --- Draw Currently Dragged Rectangle while in Drawing Mode ---
            if self.is_drawing_zone_mode and self.zone_current_rect:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.fillRect(self.zone_current_rect, QColor(245, 158, 11, 70))
                pen_drag = QPen(QColor(245, 158, 11, 240), 2, Qt.PenStyle.DashLine)
                painter.setPen(pen_drag)
                painter.drawRect(self.zone_current_rect)

                w_px = self.zone_current_rect.width()
                h_px = self.zone_current_rect.height()
                dim_text = f" NEW ZONE: {w_px}x{h_px}px "
                b_y = max(dest_y, self.zone_current_rect.top() - 18)
                painter.fillRect(QRect(self.zone_current_rect.left(), b_y, 140, 18), QColor(217, 119, 6, 230))
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.drawText(QRect(self.zone_current_rect.left() + 4, b_y, 136, 18), Qt.AlignmentFlag.AlignVCenter, dim_text)

            # Motion pulse border highlight (Electric Cyan Glass)
            if self.is_motion_active and self.motion_pulse_alpha > 0:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                pen = QPen(QColor(56, 189, 248, min(255, self.motion_pulse_alpha)), 2.5)
                painter.setPen(pen)
                painter.drawRoundedRect(QRectF(dest_x, dest_y, dest_w, dest_h), 6, 6)
            # Direct hardware border blit to avoid secondary QFrame stylesheet pass & DWM compositing spikes
            border_col = QColor("#3b82f6") if self.is_selected else QColor("#1e293b")
            painter.setPen(QPen(border_col, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
        else:
            painter.fillRect(rect, QColor("#080c16"))

            if self.worker and self.status in [StreamStatus.CONNECTING, StreamStatus.RECONNECTING]:
                painter.setPen(QColor("#94a3b8"))
                painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.status_msg}")
            elif self.stream_id:
                painter.setPen(QColor("#94a3b8"))
                painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"Connecting to {self.stream_name}...")
            else:
                pass  # Sleek Apple Glass circle plus UI is rendered by self.empty_slot_widget

        # Snapshot flash effect
        if self.flash_alpha > 0:
            painter.fillRect(rect, QColor(255, 255, 255, self.flash_alpha))

        has_frame = bool(self.current_frame and not self.current_frame.isNull())
        painter.end()
        if not has_frame:
            super().paintEvent(event)

    def _step_flash(self):
        self.flash_alpha = max(0, self.flash_alpha - 30)
        if self.flash_alpha == 0:
            self.flash_timer.stop()
        self.update()

    def take_snapshot(self):
        if self.worker:
            self.worker.trigger_snapshot()
            self.flash_alpha = 180
            self.flash_timer.start()

    def toggle_recording(self):
        if self.worker:
            if self.is_recording:
                self.worker.stop_recording()
            else:
                self.worker.start_recording()

    def toggle_solo(self):
        self.is_solo = not self.is_solo
        self.btn_solo.setIcon(create_tile_icon("restore" if self.is_solo else "solo"))
        self.solo_toggled.emit(self.tile_index, self.is_solo)

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.pan_offset = QPoint(0, 0)
        self.zoom_badge.hide()
        self.btn_reset_zoom.hide()
        self.update()

    # --- Mouse and Drag Events ---
    def mousePressEvent(self, event):
        self.tile_selected.emit(self.tile_index)
        self.setFocus()
        self._update_controls_visibility()

        if self.is_drawing_zone_mode and event.button() == Qt.MouseButton.LeftButton:
            self.zone_drag_start = event.pos()
            self.zone_current_rect = None
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self.zoom_level > 1.0:
            self.is_panning = True
            self.pan_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_drawing_zone_mode and self.zone_drag_start:
            self.zone_current_rect = QRect(self.zone_drag_start, event.pos()).normalized()
            self.update()
            event.accept()
            return

        if self.is_panning and self.zoom_level > 1.0:
            delta = event.pos() - self.pan_start_pos
            self.pan_offset += delta
            self.pan_start_pos = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_drawing_zone_mode and self.zone_drag_start:
            drag = QRect(self.zone_drag_start, event.pos()).normalized()
            self.zone_drag_start = None
            self.zone_current_rect = None

            dest_x, dest_y, dest_w, dest_h = getattr(self, "_last_dest_rect", (0, 0, self.width(), self.height()))
            norm_crop_x, norm_crop_y, norm_crop_w, norm_crop_h = getattr(self, "_last_crop_norm", (0.0, 0.0, 1.0, 1.0))
            if dest_w > 0 and dest_h > 0 and drag.width() >= 15 and drag.height() >= 15:
                rx1 = max(dest_x, min(dest_x + dest_w, drag.left()))
                ry1 = max(dest_y, min(dest_y + dest_h, drag.top()))
                rx2 = max(dest_x, min(dest_x + dest_w, drag.right()))
                ry2 = max(dest_y, min(dest_y + dest_h, drag.bottom()))

                # Inverse project from zoomed/panned screen viewport to full-frame normalized coords [0.0 - 1.0]
                zx1 = norm_crop_x + ((rx1 - dest_x) / dest_w) * norm_crop_w
                zy1 = norm_crop_y + ((ry1 - dest_y) / dest_h) * norm_crop_h
                zx2 = norm_crop_x + ((rx2 - dest_x) / dest_w) * norm_crop_w
                zy2 = norm_crop_y + ((ry2 - dest_y) / dest_h) * norm_crop_h

                zx1 = max(0.0, min(1.0, zx1))
                zy1 = max(0.0, min(1.0, zy1))
                zx2 = max(0.0, min(1.0, zx2))
                zy2 = max(0.0, min(1.0, zy2))

                if abs(zx2 - zx1) > 0.02 and abs(zy2 - zy1) > 0.02:
                    new_zone = [
                        round(min(zx1, zx2), 4),
                        round(min(zy1, zy2), 4),
                        round(max(zx1, zx2), 4),
                        round(max(zy1, zy2), 4)
                    ]
                    self.exclusion_zones.append(new_zone)
                    if self.worker:
                        self.worker.set_exclusion_zones(self.exclusion_zones)
                    self._save_exclusion_zones()
                    self._update_zone_count_label()
                    self._update_ignore_zone_btn_style()

            self.update()
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.stream_id:
                self.prompt_assign_camera()
                event.accept()
                return
            self.tile_double_clicked.emit(self.tile_index)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_level = min(5.0, self.zoom_level + 0.25)
        else:
            self.zoom_level = max(1.0, self.zoom_level - 0.25)

        if self.zoom_level > 1.0:
            self.zoom_badge.setText(f"{self.zoom_level:.1f}x")
            self.zoom_badge.show()
            self.btn_reset_zoom.show()
        else:
            self.zoom_level = 1.0
            self.pan_offset = QPoint(0, 0)
            self.zoom_badge.hide()
            self.btn_reset_zoom.hide()

        self.update()
        event.accept()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-camera-stream"):
            event.acceptProposedAction()
            self.setStyleSheet("""
                VideoTile {
                    background-color: #050811;
                    border: 2px dashed #38bdf8;
                    border-radius: 4px;
                }
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._update_border()
        event.accept()

    def dropEvent(self, event):
        self._update_border()
        if event.mimeData().hasFormat("application/x-camera-stream"):
            raw_data = event.mimeData().data("application/x-camera-stream").data().decode("utf-8")
            import json
            try:
                stream_dict = json.loads(raw_data)
                self.stream_requested.emit(self.tile_index, stream_dict)
                event.acceptProposedAction()
            except Exception as e:
                print(f"Drop error: {e}")

    def _toggle_stream_flip(self, h=None, v=None):
        if not self.worker:
            return
        if h is not None:
            self.worker.flip_horizontal = bool(h)
        if v is not None:
            self.worker.flip_vertical = bool(v)

        # Save to device_manager config
        parent_win = self.window()
        dev_mgr = getattr(parent_win, "device_manager", None)
        if dev_mgr and self.stream_info:
            cam_id = self.stream_info.get("camera_id")
            if cam_id:
                cur = dev_mgr.get_camera_settings(cam_id)
                cur["flip_horizontal"] = self.worker.flip_horizontal
                cur["flip_vertical"] = self.worker.flip_vertical
                dev_mgr.update_camera_settings(cam_id, cur)
        if parent_win and hasattr(parent_win, "statusBar"):
            status_txt = f"Orientation for '{self.stream_name}': Mirror={self.worker.flip_horizontal}, Invert={self.worker.flip_vertical}"
            parent_win.statusBar().showMessage(status_txt, 3500)

    def _set_stream_night_mode(self, mode: str):
        if not self.worker:
            return
        self.worker.set_night_vision(mode)
        self.color_night_active = (mode == NightVisionMode.COLOR_NIGHT)
        self.btn_color_night.setText("")
        self.btn_color_night.setIcon(create_tile_icon("color", active=self.color_night_active, size=24))
        if self.color_night_active:
            self.btn_color_night.setStyleSheet("background-color: rgba(245, 158, 11, 0.28); border-radius: 14px; border: 1px solid #f59e0b;")
        else:
            self.btn_color_night.setStyleSheet(TILE_ACTION_BTN_STYLE)
        parent_win = self.window()
        dev_mgr = getattr(parent_win, "device_manager", None)
        if dev_mgr and self.stream_info:
            cam_id = self.stream_info.get("camera_id")
            if cam_id:
                cur = dev_mgr.get_camera_settings(cam_id)
                cur["night_mode"] = mode
                dev_mgr.update_camera_settings(cam_id, cur)
        if parent_win and hasattr(parent_win, "statusBar"):
            parent_win.statusBar().showMessage(f"Night vision for '{self.stream_name}' set to: {mode}", 3500)

    def _reset_this_camera_defaults(self, cam_id: str):
        parent_win = self.window()
        dev_mgr = getattr(parent_win, "device_manager", None)
        if dev_mgr and cam_id:
            dev_mgr.update_camera_settings(cam_id, {
                "quality": "2K",
                "night_mode": "auto",
                "flip_horizontal": False,
                "flip_vertical": False,
                "motion_enabled": True,
                "motion_sensitivity": 6,
                "afara_person_threshold": 0.70,
                "afara_animal_threshold": 0.70,
                "wind_filter_enabled": True,
                "audio_enabled": True,
                "audio_volume": 100
            })
            eff = dev_mgr.get_effective_camera_settings(cam_id)
            if self.worker:
                self.worker.apply_camera_settings(eff)
            if parent_win and hasattr(parent_win, "statusBar"):
                parent_win.statusBar().showMessage(f"Camera '{self.stream_name}' reset to unmirrored defaults.", 3500)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
                color: #f8fafc;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 28px 6px 14px;
                border-radius: 5px;
                margin: 2px 0px;
            }
            QMenu::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #334155;
                margin: 4px 6px;
            }
        """)

        parent_win = self.window()
        dev_mgr = getattr(parent_win, "device_manager", None)
        cam = None
        cam_id = None
        if dev_mgr and self.stream_info:
            cam_id = self.stream_info.get("camera_id")
            if cam_id:
                cam = dev_mgr.get_camera_by_id(cam_id)

        if self.stream_id:
            # 1. Fullscreen / Solo View
            act_solo = menu.addAction(
                create_tile_icon("restore" if self.is_solo else "solo", size=18, custom_color="#38bdf8"),
                "Restore Grid" if self.is_solo else "Fullscreen View"
            )
            act_solo.triggered.connect(self.toggle_solo)

            # 2. Night Vision & HUD toggles
            act_night = menu.addAction(create_tile_icon("color", self.color_night_active, 18, custom_color="#fb923c"), "Full Color Night Mode")
            act_night.setCheckable(True)
            act_night.setChecked(self.color_night_active)
            act_night.triggered.connect(self.toggle_color_night_mode)

            act_boost = menu.addAction(create_tile_icon("night", self.night_boost_active, 18, custom_color="#f59e0b"), "Night Vision Contrast Boost")
            act_boost.setCheckable(True)
            act_boost.setChecked(self.night_boost_active)
            act_boost.triggered.connect(self.toggle_night_boost)

            show_hud = getattr(self, "show_fps_hud", False)
            act_hud = menu.addAction(create_tile_icon("camera", show_hud, 18, custom_color="#38bdf8"), "Show Resolution & FPS HUD")
            act_hud.setCheckable(True)
            act_hud.setChecked(show_hud)
            act_hud.triggered.connect(lambda chk: self.toggle_fps_hud(chk))

            radar_active = getattr(self, "movement_view_active", False)
            act_radar = menu.addAction(create_tile_icon("radar", radar_active, 18, custom_color="#38bdf8"), "Movement Vector Debug")
            act_radar.setCheckable(True)
            act_radar.setChecked(radar_active)
            act_radar.triggered.connect(self.toggle_movement_view)

            # 3. Audio stream toggle
            act_audio = menu.addAction(
                create_tile_icon("audio", self.is_audio_enabled, 18, custom_color="#ef4444" if self.is_audio_enabled else "#38bdf8"),
                "Mute Audio" if self.is_audio_enabled else "Unmute Audio"
            )
            act_audio.setCheckable(True)
            act_audio.setChecked(self.is_audio_enabled)
            act_audio.triggered.connect(self.toggle_audio)

            # 4. Stream Quality Submenu
            q_menu = menu.addMenu(create_tile_icon("quality", False, 18, custom_color="#38bdf8"), f"Quality ({self.current_quality})")
            act_qmax = q_menu.addAction(create_tile_icon("quality", False, 16, custom_color="#38bdf8"), "MAX (Pristine App Clarity)")
            act_qmax.triggered.connect(lambda: self.set_quality(QualityMode.ULTRA_MAX))
            act_q2k = q_menu.addAction(create_tile_icon("quality", False, 16, custom_color="#0284c7"), "2K Ultra HD (Native Raw)")
            act_q2k.triggered.connect(lambda: self.set_quality(QualityMode.ULTRA_2K))
            act_qmid = q_menu.addAction(create_tile_icon("quality", False, 16, custom_color="#94a3b8"), "720p HD (Balanced)")
            act_qmid.triggered.connect(lambda: self.set_quality(QualityMode.MID_HD))
            act_qlow = q_menu.addAction(create_tile_icon("quality", False, 16, custom_color="#64748b"), "360p SD (Sub-stream)")
            act_qlow.triggered.connect(lambda: self.set_quality(QualityMode.LOW_SD))

            # 5. Snapshot & Recording
            act_snap = menu.addAction(create_tile_icon("snapshot", False, 18, custom_color="#38bdf8"), "Take Snapshot")
            act_snap.triggered.connect(self.take_snapshot)

            rec_text = "Stop Recording" if self.is_recording else "Start Recording"
            act_rec = menu.addAction(
                create_tile_icon("record", self.is_recording, 18, custom_color="#ef4444" if self.is_recording else "#38bdf8"),
                rec_text
            )
            act_rec.triggered.connect(self.toggle_recording)

            # Exclusion Zones
            act_zone = menu.addAction(create_tile_icon("zone_draw", False, 18, custom_color="#38bdf8"), "Draw Exclusion Zone...")
            act_zone.triggered.connect(self.toggle_draw_ignore_zone)

            if self.exclusion_zones:
                is_showing = getattr(self, "show_exclusion_zones", False)
                act_show_zones = menu.addAction(create_tile_icon("eye", is_showing, 18, custom_color="#60a5fa"), "Show Exclusion Zones Overlay")
                act_show_zones.setCheckable(True)
                act_show_zones.setChecked(is_showing)
                act_show_zones.triggered.connect(lambda chk: self.toggle_show_exclusion_zones(chk))

            if self.zoom_level > 1.0:
                act_zoom = menu.addAction(create_tile_icon("zoom_reset", False, 18, custom_color="#38bdf8"), "Reset Zoom (1:1)")
                act_zoom.triggered.connect(self.reset_zoom)

            menu.addSeparator()

            # 6. Settings for this camera (Sanitized: friendly names only, strictly zero IP addresses)
            raw_title = cam.get("name") if cam else self.stream_name
            cam_title = format_clean_camera_title(raw_title)
            cam_title = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "", cam_title).strip(" •-:")
            settings_label = f"Camera Settings: {cam_title}..." if cam_title and cam_title.lower() != "camera" else "Camera Settings..."
            act_settings = menu.addAction(create_tile_icon("settings", False, 18, custom_color="#38bdf8"), settings_label)
            act_settings.triggered.connect(lambda: parent_win.open_settings_dialog(selected_camera_id=cam_id))

            if cam_id and hasattr(parent_win, "prompt_rename_camera"):
                act_rename = menu.addAction(create_tile_icon("rename", False, 18, custom_color="#38bdf8"), "Rename Camera...")
                act_rename.triggered.connect(lambda: parent_win.prompt_rename_camera(cam_id))

            if self.stream_id and hasattr(parent_win, "prompt_rename_lens"):
                act_rename_lens = menu.addAction(create_tile_icon("lens", False, 18, custom_color="#38bdf8"), "Rename Lens...")
                act_rename_lens.triggered.connect(lambda: parent_win.prompt_rename_lens(self.stream_id))

            # 7. Close Feed
            act_close = menu.addAction(create_tile_icon("close_feed", False, 18, custom_color="#ef4444"), "Close Feed")
            act_close.triggered.connect(self.close_stream)

        else:
            # Empty slot context menu
            act_assign = menu.addAction(create_tile_icon("plus", size=18, custom_color="#38bdf8"), "Assign Camera to Slot...")
            act_assign.triggered.connect(self.prompt_assign_camera)
            menu.addSeparator()

            if dev_mgr:
                sub_menu = menu.addMenu(create_tile_icon("video", False, 18, custom_color="#38bdf8"), "Quick Stream Select")
                streams = dev_mgr.get_all_streams()
                if streams:
                    for s in streams:
                        raw_cname = s.get('camera_name', 'Camera')
                        cam_name = format_clean_camera_title(raw_cname)
                        cam_name = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "", cam_name).strip(" •-:") or "Camera"
                        raw_lname = s.get('name', 'Stream')
                        lens_name = format_clean_camera_title(raw_lname)
                        lens_name = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "", lens_name).strip(" •-:") or "Stream"
                        act = sub_menu.addAction(create_tile_icon("video", False, 16, custom_color="#38bdf8"), f"{cam_name} • {lens_name}")
                        act.triggered.connect(lambda ch, st=s: self.stream_requested.emit(self.tile_index, st))
                else:
                    act_empty = sub_menu.addAction("No cameras configured")
                    act_empty.setEnabled(False)

            act_solo = menu.addAction(
                create_tile_icon("restore" if self.is_solo else "solo", size=18, custom_color="#38bdf8"),
                "Restore Grid" if self.is_solo else "Fullscreen Slot"
            )
            act_solo.triggered.connect(self.toggle_solo)

            menu.addSeparator()

            act_settings = menu.addAction(create_tile_icon("settings", False, 18, custom_color="#38bdf8"), "Application Settings...")
            act_settings.triggered.connect(lambda: parent_win.open_settings_dialog())

        menu.exec(self.mapToGlobal(pos))

    def prompt_assign_camera(self):
        """Presents modern Apple glass modal dialog asking to pick an active camera stream or add a new one."""
        parent_win = self.window()
        dev_mgr = getattr(parent_win, "device_manager", None)
        streams = dev_mgr.get_all_streams() if dev_mgr else []

        active_assignments = {}
        if parent_win and hasattr(parent_win, "video_tiles"):
            for idx, tile in enumerate(parent_win.video_tiles):
                if tile.stream_id:
                    active_assignments[tile.stream_id] = idx + 1

        dlg = CameraAssignDialog(self.tile_index, streams, active_assignments, parent=self)
        if dlg.exec():
            if getattr(dlg, "request_configure_cam_id", None):
                target_cid = dlg.request_configure_cam_id
                if parent_win and hasattr(parent_win, "open_settings_dialog"):
                    parent_win.open_settings_dialog(selected_camera_id=target_cid)
                    refreshed_cam = dev_mgr.get_camera_by_id(target_cid) if dev_mgr else None
                    if refreshed_cam and hasattr(dev_mgr, "is_camera_configured") and dev_mgr.is_camera_configured(refreshed_cam):
                        refreshed_streams = refreshed_cam.get("streams", [])
                        if refreshed_streams:
                            s = dict(refreshed_streams[0])
                            s["camera_id"] = refreshed_cam.get("id")
                            s["camera_name"] = refreshed_cam.get("name")
                            s["camera_ip"] = refreshed_cam.get("ip")
                            self.stream_requested.emit(self.tile_index, s)
            elif dlg.request_add_new:
                if parent_win and hasattr(parent_win, "open_add_camera_dialog"):
                    parent_win.open_add_camera_dialog()
            elif dlg.selected_stream:
                self.stream_requested.emit(self.tile_index, dlg.selected_stream)
        else:
            # User canceled or chose "Keep Slot Empty" -> slot remains empty
            pass

    def set_ai_overlays_enabled(self, enabled: bool):
        if self.worker:
            self.worker.show_ai_overlays = bool(enabled)
            self.update()
