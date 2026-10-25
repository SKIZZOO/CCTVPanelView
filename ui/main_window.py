import os
import sys
import re
import json
import time
import threading
from datetime import datetime, timedelta
import winsound
import ctypes
from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QFrame,
    QSplitter, QStatusBar, QMessageBox, QMenu, QComboBox, QApplication,
    QListWidget, QTabWidget, QScrollArea, QDialog, QSizePolicy, QProgressBar,
    QGraphicsDropShadowEffect, QInputDialog, QLineEdit, QSystemTrayIcon
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QMimeData, QPoint, QPointF, QRectF, QEvent
from PyQt6.QtGui import QIcon, QFont, QKeySequence, QShortcut, QDrag, QPixmap, QColor, QBrush, QPainter, QPen, QPainterPath

from core.device_manager import DeviceManager
from core.camera_stream import CameraStreamWorker, StreamStatus, QualityMode, NightVisionMode
from core.alert_manager import AlertManager
from core.signal_monitor import SignalMonitor
from core.web_server import WebStreamingServer
from core.sound_manager import get_sound_manager, SoundProfile
from core.resource_manager import get_resource_manager, PerformanceProfile, PROFILE_DEFAULTS
from ui.components.video_tile import VideoTile, create_tile_icon, format_clean_camera_title, TILE_ACTION_BTN_STYLE
from ui.components.ptz_pad import PTZPad
from ui.components.intercom_pad import IntercomPad
from ui.components.ptz_dialog import PTZControlDialog
from ui.components.alert_card import AlertCardWidget
from ui.components.gallery_dialog import GalleryDialog
from ui.components.device_dialog import DeviceDialog
from ui.components.scanner_dialog import ScannerDialog
from ui.components.settings_dialog import SettingsDialog, CameraSetupPromptDialog
from ui.components.startup_performance_dialog import StartupPerformanceDialog
from ui.components.custom_layout_dialog import CustomLayoutDialog
from ui.components.sleek_alert_notification import SleekAlertNotification
from ui.components.modern_sidebar import (
    ModernSideTabWidget,
    ModernDraggableCameraTree,
    CameraHeaderCardWidget,
    StreamRowCardWidget,
    ModernSidebarTelemetryWidget,
    PersistentSlimFooter,
)
from ui.styles import DARK_THEME_QSS, get_theme_qss, AVAILABLE_THEMES


def enable_windows_sleep_prevention():
    """Tells Windows not to suspend system while CCTV workstation is running."""
    if sys.platform == "win32":
        try:
            import ctypes
            # ES_CONTINUOUS = 0x80000000 | ES_SYSTEM_REQUIRED = 0x00000001 | ES_AWAYMODE_REQUIRED = 0x00000040
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000040)
        except Exception:
            pass


def restore_windows_sleep():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        except Exception:
            pass


def create_topbar_icon(icon_type: str, active: bool = False, size: int = 18, custom_color: Optional[str] = None) -> QIcon:
    """Renders high-definition vector icons for the modern workstation top bar."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    fg = QColor(custom_color) if custom_color else (QColor("#38bdf8") if active else QColor("#94a3b8"))
    pen = QPen(fg, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    if icon_type == "sidebar":
        p.drawRoundedRect(QRectF(size * 0.14, size * 0.14, size * 0.72, size * 0.72), 2.5, 2.5)
        p.drawLine(int(size * 0.38), int(size * 0.14), int(size * 0.38), int(size * 0.86))
    elif icon_type == "1x1":
        p.drawRoundedRect(QRectF(size * 0.18, size * 0.18, size * 0.64, size * 0.64), 2.5, 2.5)
    elif icon_type == "2x2":
        s = size * 0.28
        p.drawRoundedRect(QRectF(size * 0.16, size * 0.16, s, s), 1.5, 1.5)
        p.drawRoundedRect(QRectF(size * 0.56, size * 0.16, s, s), 1.5, 1.5)
        p.drawRoundedRect(QRectF(size * 0.16, size * 0.56, s, s), 1.5, 1.5)
        p.drawRoundedRect(QRectF(size * 0.56, size * 0.56, s, s), 1.5, 1.5)
    elif icon_type == "3x3":
        s = size * 0.18
        for r in range(3):
            for c in range(3):
                p.drawRoundedRect(QRectF(size * (0.14 + c * 0.26), size * (0.14 + r * 0.26), s, s), 1, 1)
    elif icon_type == "custom":
        p.drawRoundedRect(QRectF(size * 0.14, size * 0.14, size * 0.72, size * 0.72), 2.5, 2.5)
        p.drawLine(int(size * 0.14), int(size * 0.50), int(size * 0.86), int(size * 0.50))
        p.drawLine(int(size * 0.55), int(size * 0.50), int(size * 0.55), int(size * 0.86))
    elif icon_type == "dual_lens":
        p.drawEllipse(QPointF(size * 0.34, size * 0.50), size * 0.22, size * 0.22)
        p.drawEllipse(QPointF(size * 0.66, size * 0.50), size * 0.22, size * 0.22)
    elif icon_type == "snapshot":
        p.drawRoundedRect(QRectF(size * 0.14, size * 0.30, size * 0.72, size * 0.54), 2.5, 2.5)
        p.drawRoundedRect(QRectF(size * 0.34, size * 0.18, size * 0.32, size * 0.14), 1.5, 1.5)
        p.drawEllipse(QPointF(size * 0.50, size * 0.57), size * 0.16, size * 0.16)
    elif icon_type == "alerts":
        path = QPainterPath()
        path.moveTo(size * 0.50, size * 0.16)
        path.cubicTo(size * 0.32, size * 0.22, size * 0.26, size * 0.55, size * 0.20, size * 0.72)
        path.lineTo(size * 0.80, size * 0.72)
        path.cubicTo(size * 0.74, size * 0.55, size * 0.68, size * 0.22, size * 0.50, size * 0.16)
        p.drawPath(path)
        p.drawLine(int(size * 0.42), int(size * 0.82), int(size * 0.58), int(size * 0.82))
    elif icon_type == "shield":
        path = QPainterPath()
        path.moveTo(size * 0.50, size * 0.16)
        path.lineTo(size * 0.80, size * 0.28)
        path.cubicTo(size * 0.80, size * 0.60, size * 0.50, size * 0.84, size * 0.50, size * 0.84)
        path.cubicTo(size * 0.50, size * 0.84, size * 0.20, size * 0.60, size * 0.20, size * 0.28)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(int(size * 0.40), int(size * 0.50), int(size * 0.48), int(size * 0.58))
        p.drawLine(int(size * 0.48), int(size * 0.58), int(size * 0.62), int(size * 0.42))
    elif icon_type == "quality":
        p.drawRoundedRect(QRectF(size * 0.16, size * 0.22, size * 0.68, size * 0.56), 2.5, 2.5)
        path = QPainterPath()
        path.moveTo(size * 0.50, size * 0.34)
        path.lineTo(size * 0.62, size * 0.50)
        path.lineTo(size * 0.50, size * 0.66)
        path.lineTo(size * 0.38, size * 0.50)
        path.closeSubpath()
        p.drawPath(path)
    elif icon_type == "ptz":
        p.drawEllipse(QPointF(size * 0.50, size * 0.50), 2, 2)
        p.drawLine(int(size * 0.50), int(size * 0.14), int(size * 0.50), int(size * 0.86))
        p.drawLine(int(size * 0.14), int(size * 0.50), int(size * 0.86), int(size * 0.50))
        p.drawLine(int(size * 0.50), int(size * 0.14), int(size * 0.42), int(size * 0.26))
        p.drawLine(int(size * 0.50), int(size * 0.14), int(size * 0.58), int(size * 0.26))
        p.drawLine(int(size * 0.50), int(size * 0.86), int(size * 0.42), int(size * 0.74))
        p.drawLine(int(size * 0.50), int(size * 0.86), int(size * 0.58), int(size * 0.74))
        p.drawLine(int(size * 0.14), int(size * 0.50), int(size * 0.26), int(size * 0.42))
        p.drawLine(int(size * 0.14), int(size * 0.50), int(size * 0.26), int(size * 0.58))
        p.drawLine(int(size * 0.86), int(size * 0.50), int(size * 0.74), int(size * 0.42))
        p.drawLine(int(size * 0.86), int(size * 0.50), int(size * 0.74), int(size * 0.58))
    elif icon_type == "intercom":
        p.drawRoundedRect(QRectF(size * 0.35, size * 0.15, size * 0.30, size * 0.46), 3, 3)
        path = QPainterPath()
        path.moveTo(size * 0.24, size * 0.44)
        path.cubicTo(size * 0.24, size * 0.74, size * 0.76, size * 0.74, size * 0.76, size * 0.44)
        p.drawPath(path)
        p.drawLine(int(size * 0.50), int(size * 0.74), int(size * 0.50), int(size * 0.88))
        p.drawLine(int(size * 0.36), int(size * 0.88), int(size * 0.64), int(size * 0.88))
    elif icon_type == "night_color":
        c = QPointF(size * 0.50, size * 0.50)
        p.drawEllipse(c, size * 0.18, size * 0.18)
        import math
        for a in (0, 45, 90, 135, 180, 225, 270, 315):
            rad = math.radians(a)
            p1 = QPointF(c.x() + math.cos(rad) * size * 0.26, c.y() + math.sin(rad) * size * 0.26)
            p2 = QPointF(c.x() + math.cos(rad) * size * 0.38, c.y() + math.sin(rad) * size * 0.38)
    elif icon_type == "cameras":
        p.drawRoundedRect(QRectF(size * 0.16, size * 0.28, size * 0.68, size * 0.52), 2.5, 2.5)
        p.drawEllipse(QPointF(size * 0.50, size * 0.54), size * 0.16, size * 0.16)
        p.drawRoundedRect(QRectF(size * 0.32, size * 0.16, size * 0.36, size * 0.14), 1.5, 1.5)
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
        p.drawRoundedRect(QRectF(size * 0.14, size * 0.18, size * 0.72, size * 0.64), 2.5, 2.5)
        p.drawLine(int(size * 0.48), int(size * 0.18), int(size * 0.48), int(size * 0.82))
        p.drawLine(int(size * 0.62), int(size * 0.44), int(size * 0.72), int(size * 0.50))
        p.drawLine(int(size * 0.72), int(size * 0.50), int(size * 0.62), int(size * 0.56))
    elif icon_type == "add":
        p.drawLine(int(size * 0.50), int(size * 0.22), int(size * 0.50), int(size * 0.78))
        p.drawLine(int(size * 0.22), int(size * 0.50), int(size * 0.78), int(size * 0.50))
    elif icon_type == "stream":
        path = QPainterPath()
        path.moveTo(size * 0.36, size * 0.26)
        path.lineTo(size * 0.72, size * 0.50)
        path.lineTo(size * 0.36, size * 0.74)
        path.closeSubpath()
        p.fillPath(path, QBrush(fg))
    elif icon_type == "manage":
        p.drawLine(int(size * 0.20), int(size * 0.34), int(size * 0.80), int(size * 0.34))
        p.drawEllipse(QPointF(size * 0.40, size * 0.34), size * 0.10, size * 0.10)
        p.drawLine(int(size * 0.20), int(size * 0.66), int(size * 0.80), int(size * 0.66))
        p.drawEllipse(QPointF(size * 0.60, size * 0.66), size * 0.10, size * 0.10)
    elif icon_type == "search":
        p.drawEllipse(QPointF(size * 0.44, size * 0.44), size * 0.24, size * 0.24)
        p.drawLine(int(size * 0.61), int(size * 0.61), int(size * 0.82), int(size * 0.82))
    elif icon_type == "siren":
        path = QPainterPath()
        path.moveTo(size * 0.20, size * 0.38)
        path.lineTo(size * 0.34, size * 0.38)
        path.lineTo(size * 0.52, size * 0.24)
        path.lineTo(size * 0.52, size * 0.76)
        path.lineTo(size * 0.34, size * 0.62)
        path.lineTo(size * 0.20, size * 0.62)
        path.closeSubpath()
        p.drawPath(path)
        p.drawArc(QRectF(size * 0.46, size * 0.32, size * 0.32, size * 0.36), -45 * 16, 90 * 16)
        p.drawArc(QRectF(size * 0.58, size * 0.22, size * 0.36, size * 0.56), -45 * 16, 90 * 16)
    elif icon_type == "cpu":
        p.drawRoundedRect(QRectF(size * 0.24, size * 0.24, size * 0.52, size * 0.52), 2, 2)
        p.drawRect(QRectF(size * 0.40, size * 0.40, size * 0.20, size * 0.20))
        for offset in (size * 0.35, size * 0.65):
            p.drawLine(int(offset), int(size * 0.12), int(offset), int(size * 0.24))
            p.drawLine(int(offset), int(size * 0.76), int(offset), int(size * 0.88))
            p.drawLine(int(size * 0.12), int(offset), int(size * 0.24), int(offset))
            p.drawLine(int(size * 0.76), int(offset), int(size * 0.88), int(offset))
    elif icon_type == "scanner":
        p.drawEllipse(QPointF(size * 0.50, size * 0.50), 2, 2)
        p.drawArc(QRectF(size * 0.24, size * 0.24, size * 0.52, size * 0.52), 45 * 16, 90 * 16)
        p.drawArc(QRectF(size * 0.12, size * 0.12, size * 0.76, size * 0.76), 45 * 16, 90 * 16)
        p.drawArc(QRectF(size * 0.24, size * 0.24, size * 0.52, size * 0.52), 225 * 16, 90 * 16)
        p.drawArc(QRectF(size * 0.12, size * 0.12, size * 0.76, size * 0.76), 225 * 16, 90 * 16)
    elif icon_type == "retention":
        p.drawEllipse(QRectF(size * 0.20, size * 0.18, size * 0.60, size * 0.18))
        path = QPainterPath()
        path.moveTo(size * 0.20, size * 0.27)
        path.lineTo(size * 0.20, size * 0.72)
        path.arcTo(QRectF(size * 0.20, size * 0.63, size * 0.60, size * 0.18), 180, -180)
        path.lineTo(size * 0.80, size * 0.27)
        p.drawPath(path)
        p.drawArc(QRectF(size * 0.20, size * 0.45, size * 0.60, size * 0.18), 180, 180)
    elif icon_type == "mobile":
        p.drawRoundedRect(QRectF(size * 0.26, size * 0.14, size * 0.48, size * 0.72), 3, 3)
        p.drawLine(int(size * 0.42), int(size * 0.78), int(size * 0.58), int(size * 0.78))
    elif icon_type == "recordings":
        p.drawRoundedRect(QRectF(size * 0.14, size * 0.18, size * 0.72, size * 0.64), 2.5, 2.5)
        path = QPainterPath()
        path.moveTo(size * 0.42, size * 0.34)
        path.lineTo(size * 0.66, size * 0.50)
        path.lineTo(size * 0.42, size * 0.66)
        path.closeSubpath()
        p.fillPath(path, QBrush(fg))
    elif icon_type == "settings":
        import math
        cx, cy = size * 0.50, size * 0.50
        r_root = size * 0.30
        r_tip = size * 0.44
        r_hole = size * 0.14
        num_teeth = 8
        step = 2 * math.pi / num_teeth
        half_tooth = step * 0.24

        path = QPainterPath()
        for i in range(num_teeth):
            angle = i * step
            a0 = angle - step * 0.25
            a1 = angle - half_tooth
            a2 = angle + half_tooth
            a3 = angle + step * 0.25

            p0 = QPointF(cx + math.cos(a0) * r_root, cy + math.sin(a0) * r_root)
            p1 = QPointF(cx + math.cos(a1) * r_tip, cy + math.sin(a1) * r_tip)
            p2 = QPointF(cx + math.cos(a2) * r_tip, cy + math.sin(a2) * r_tip)
            p3 = QPointF(cx + math.cos(a3) * r_root, cy + math.sin(a3) * r_root)

            if i == 0:
                path.moveTo(p0)
            else:
                path.lineTo(p0)
            path.lineTo(p1)
            path.lineTo(p2)
            path.lineTo(p3)

        path.closeSubpath()
        p.drawPath(path)
        p.drawEllipse(QPointF(cx, cy), r_hole, r_hole)
    elif icon_type == "fullscreen":
        m, e, l = size * 0.20, size * 0.80, size * 0.18
        p.drawLine(int(m), int(m + l), int(m), int(m))
        p.drawLine(int(m), int(m), int(m + l), int(m))
        p.drawLine(int(e - l), int(m), int(e), int(m))
        p.drawLine(int(e), int(m), int(e), int(m + l))
        p.drawLine(int(m), int(e - l), int(m), int(e))
        p.drawLine(int(m), int(e), int(m + l), int(e))
        p.drawLine(int(e - l), int(e), int(e), int(e))
        p.drawLine(int(e), int(e - l), int(e), int(e))
    elif icon_type in ("edit", "rename"):
        p.drawLine(int(size * 0.24), int(size * 0.76), int(size * 0.44), int(size * 0.76))
        p.drawLine(int(size * 0.24), int(size * 0.76), int(size * 0.24), int(size * 0.56))
        p.drawLine(int(size * 0.24), int(size * 0.56), int(size * 0.64), int(size * 0.16))
        p.drawLine(int(size * 0.44), int(size * 0.76), int(size * 0.84), int(size * 0.36))
        p.drawLine(int(size * 0.64), int(size * 0.16), int(size * 0.84), int(size * 0.36))
    elif icon_type in ("clear", "trash"):
        p.drawLine(int(size * 0.22), int(size * 0.32), int(size * 0.78), int(size * 0.32))
        p.drawLine(int(size * 0.38), int(size * 0.20), int(size * 0.62), int(size * 0.20))
        p.drawRoundedRect(QRectF(size * 0.28, size * 0.32, size * 0.44, size * 0.54), 1.5, 1.5)
        p.drawLine(int(size * 0.42), int(size * 0.44), int(size * 0.42), int(size * 0.72))
        p.drawLine(int(size * 0.58), int(size * 0.44), int(size * 0.58), int(size * 0.72))
    elif icon_type == "win_min":
        p.drawLine(int(size * 0.22), int(size * 0.50), int(size * 0.78), int(size * 0.50))
    elif icon_type == "win_max":
        p.drawRoundedRect(QRectF(size * 0.22, size * 0.22, size * 0.56, size * 0.56), 1.5, 1.5)
    elif icon_type == "win_restore":
        p.drawRoundedRect(QRectF(size * 0.34, size * 0.18, size * 0.48, size * 0.48), 1.5, 1.5)
        p.fillRect(int(size * 0.18), int(size * 0.34), int(size * 0.48), int(size * 0.48), QColor('#0f172a'))
        p.drawRoundedRect(QRectF(size * 0.18, size * 0.34, size * 0.48, size * 0.48), 1.5, 1.5)
    elif icon_type == "win_close":
        p.drawLine(int(size * 0.26), int(size * 0.26), int(size * 0.74), int(size * 0.74))
        p.drawLine(int(size * 0.74), int(size * 0.26), int(size * 0.26), int(size * 0.74))

    p.end()
    return QIcon(pix)


class DraggableCameraTree(ModernDraggableCameraTree):
    """
    QTreeWidget supporting drag & drop of camera streams onto video tiles.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        if self.header():
            self.header().setStretchLastSection(True)

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

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class SlimStatusBarProxy:
    """Proxies QMainWindow.statusBar().showMessage() directly to the sleek custom bottom bar."""
    def __init__(self, label: QLabel, dot: QLabel = None):
        self.label = label
        self.dot = dot
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._reset_msg)

    def _reset_msg(self):
        if self.label:
            self.label.setText("System Ready")
        if self.dot:
            self.dot.setStyleSheet("color: #38bdf8; font-size: 11px;")

    def showMessage(self, msg: str, timeout: int = 4000):
        if self.label:
            clean_msg = re.sub(r'[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff]', '', str(msg)).strip()
            self.label.setText(clean_msg)
            if self.dot:
                self.dot.setStyleSheet("color: #38bdf8; font-size: 11px;")
            if timeout > 0:
                self._timer.stop()
                self._timer.start(timeout)


class MainWindow(QMainWindow):
    """
    CCTVPanelView Workstation - Professional Next-Gen AI CCTV Suite.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCTVPanelView - Professional AI Surveillance Suite")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.resize(1420, 890)
        self.setMinimumSize(960, 600)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Core state
        self.device_manager = DeviceManager()
        self.app_settings = self.device_manager.config.get("app_settings", {})
        self.sound_manager = get_sound_manager()

        # Apply saved or default theme
        theme_name = self.app_settings.get("theme", "Cyber Dark")
        self.setStyleSheet(get_theme_qss(theme_name))

        # Set high-res window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "cctv_logo.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "app_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.active_workers = {}  # stream_id: CameraStreamWorker
        self.video_tiles = []
        self.selected_tile_idx = 0
        self.current_layout = self.app_settings.get("default_layout", "2x2")
        self.is_fullscreen = False
        self.is_sidebar_visible = bool(self.app_settings.get("sidebar_visible", True))

        # Global features state
        self.global_quality = self.app_settings.get("default_quality", QualityMode.ULTRA_MAX)
        self.master_alerts_enabled = bool(self.app_settings.get("master_alerts_enabled", True))
        self.global_motion_enabled = self.app_settings.get("motion_enabled", True)
        self.motion_sound_enabled = self.app_settings.get("motion_sound", False)
        self.sound_alarms_enabled = not self.app_settings.get("mute_on_startup", False)

        # Alert Coordinator (Instant snapshot + 10s video with audio recording)
        self.alert_cards = {}
        self.alert_count = 0
        self.alert_manager = AlertManager(
            snapshot_dir=self.app_settings.get("snapshot_dir", "snapshots"),
            recording_dir=self.app_settings.get("recording_dir", "recordings"),
            parent=self
        )
        self.alert_manager.set_app_settings(self.app_settings)
        self.alert_manager.alert_triggered.connect(self._on_alert_triggered_from_manager)
        self.alert_manager.alert_video_ready.connect(self._on_alert_video_ready)
        self.alert_manager.alerts_purged.connect(self._on_alerts_purged)

        # Real-time Wi-Fi & Network Signal Monitor
        self.signal_monitor = SignalMonitor(check_interval_sec=4.0, parent=self)
        self.signal_monitor.signals_updated.connect(self._on_signals_updated)

        self._restoring_session = True
        self._setup_ui()
        self.restore_window_state()
        if self.app_settings.get("sidebar_position") == "right":
            self.toggle_sidebar_position()
        self._setup_shortcuts()
        self._populate_camera_tree()

        # Start live Wi-Fi signal & latency monitoring
        self._refresh_signal_monitor_cameras()
        self.signal_monitor.start()

        # Load persisted alarm history into the live feed
        self._load_initial_alerts()

        # Live CPU telemetry monitor timer
        self.cpu_monitor_timer = QTimer(self)
        self.cpu_monitor_timer.timeout.connect(self._update_cpu_monitor)
        self.cpu_monitor_timer.start(2000)
        QTimer.singleShot(50, self._update_cpu_monitor)

        # Integrated Mobile Web Streaming Server (Port 8080)
        web_port = int(self.app_settings.get("web_port", 8080))
        self.web_server = WebStreamingServer(self, port=web_port)
        self.web_server.start()

        # Performance mode prompt & 4 Quad startup launcher
        rm = get_resource_manager()
        initial_prof = self.app_settings.get("performance_profile", "gamer" if rm.is_ryzen_dual_ccd else "medium")
        self.apply_performance_profile(initial_prof)

        QTimer.singleShot(150, self._check_startup_performance_mode)
        if self.app_settings.get("auto_clean_on_startup", True):
            QTimer.singleShot(2500, lambda: self.check_old_alerts_retention(silent_if_none=True))

        quota_gb = self.app_settings.get("storage_quota_gb", 0)
        if quota_gb > 0 and self.app_settings.get("auto_purge_on_quota", False):
            QTimer.singleShot(3000, lambda: self.alert_manager.enforce_quota(quota_gb))

        # Enable 24/7 background recording & prevent Windows sleep
        enable_windows_sleep_prevention()

        # System tray icon for 24/7 background operation
        self._allow_force_quit = False
        self._tray_notified_once = False
        self._setup_system_tray()

        # Connect application termination hook to synchronously persist session state and camera slots
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.aboutToQuit.connect(self.save_session_state)

    def _setup_system_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return

        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "cctvpanelview_logo.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "cctv_logo.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "app_icon.png")

        tray_icon = QIcon(icon_path) if os.path.exists(icon_path) else self.windowIcon()
        self.tray_icon = QSystemTrayIcon(tray_icon, self)
        self.tray_icon.setToolTip("CCTVPanelView - 24/7 Recording Active")

        tray_menu = QMenu()
        show_action = tray_menu.addAction("Open CCTVPanelView")
        show_action.triggered.connect(self._restore_from_tray)

        status_action = tray_menu.addAction("Status: 24/7 Recording Active")
        status_action.setEnabled(False)

        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("Quit and Stop Application")
        quit_action.triggered.connect(self._force_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _restore_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.isVisible() and not self.isMinimized():
                self.hide()
            else:
                self._restore_from_tray()

    def _force_quit(self):
        self._allow_force_quit = True
        self.close()

    def _setup_ui(self):
        self._is_custom_maximized = False
        self._normal_geometry = None
        self._current_responsive_mode = None

        central_widget = QWidget(self)
        central_widget.setObjectName("central_widget")
        central_widget.setMouseTracking(True)
        self.central_widget = central_widget
        self.setCentralWidget(central_widget)

        # Draw sleek rounded window background & glass rim when windowed via paintEvent (zero stylesheet invalidation / zero resize freeze)
        orig_cw_paint = central_widget.paintEvent
        def _cw_paint(event):
            orig_cw_paint(event)
            p = QPainter(self.central_widget)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            rect = QRectF(self.central_widget.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            if not self.is_window_maximized() and not getattr(self, "is_fullscreen", False):
                radius = 14.0
                path = QPainterPath()
                path.addRoundedRect(rect, radius, radius)
                p.fillPath(path, QColor("#080c16"))
                p.setPen(QPen(QColor(56, 189, 248, 80), 1))
                p.drawPath(path)
            else:
                p.fillRect(rect.toRect(), QColor("#080c16"))
        central_widget.paintEvent = _cw_paint

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(1, 0, 1, 1)
        root_layout.setSpacing(0)

        # --- 1. Top Control Bar (Integrated Frameless Header) ---
        top_bar = QFrame(self)
        top_bar.setObjectName("top_bar")
        self.top_bar = top_bar
        top_bar.setFixedHeight(64)
        top_bar.installEventFilter(self)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 8, 10, 8)
        top_layout.setSpacing(8)

        def create_capsule_divider():
            sep = QFrame()
            sep.setFixedSize(1, 14)
            sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.14); border: none;")
            return sep

        # --- Capsule 1: Brand & Sidebar Navigation ---
        self.capsule_brand = QFrame(top_bar)
        self.capsule_brand.setObjectName("capsule_brand")
        self.capsule_brand.setProperty("class", "top-bar-capsule")
        brand_layout = QHBoxLayout(self.capsule_brand)
        brand_layout.setContentsMargins(8, 2, 8, 2)
        brand_layout.setSpacing(6)

        lbl_logo_icon = QLabel(self.capsule_brand)
        lbl_logo_icon.setStyleSheet("background: transparent; border: none;")
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "app_icon_clean.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_logo_icon.setPixmap(pix)
            lbl_logo_icon.setFixedSize(22, 22)
            brand_layout.addWidget(lbl_logo_icon)

        self.lbl_brand_text = QLabel(self.capsule_brand)
        self.lbl_brand_text.setStyleSheet("background: transparent; border: none;")
        self.lbl_brand_text.setText('<span style="font-family: \'Segoe UI Variable Display\', \'Segoe UI\', sans-serif; font-size: 14px; font-weight: 750; letter-spacing: 0.8px; color: #f8fafc;">CCTV</span> <span style="font-family: \'Segoe UI Variable Display\', \'Segoe UI\', sans-serif; font-size: 14px; font-weight: 350; letter-spacing: 0.8px; color: #38bdf8;">PanelView</span> <span style="font-size:9px; font-weight:700; color:#38bdf8; background:rgba(56,189,248,0.18); border:1px solid #38bdf8; padding:1px 6px; border-radius:8px; vertical-align:middle;">LIVE</span>')
        self.lbl_brand_text.setToolTip("CCTVPanelView - Professional Surveillance Workstation")
        brand_layout.addWidget(self.lbl_brand_text)

        brand_layout.addWidget(create_capsule_divider())

        self.btn_toggle_sidebar = QPushButton(" Sidebar", self.capsule_brand)
        self.btn_toggle_sidebar.setIcon(create_topbar_icon("sidebar", size=16))
        self.btn_toggle_sidebar.setIconSize(QSize(16, 16))
        self.btn_toggle_sidebar.setToolTip("Toggle cameras and alerts sidebar (Ctrl+B / F10)")
        self.btn_toggle_sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)
        brand_layout.addWidget(self.btn_toggle_sidebar)

        top_layout.addWidget(self.capsule_brand)
        top_layout.addStretch(1)

        # --- Capsule 2: Segmented Layout Controls ---
        self.capsule_layout = QFrame(top_bar)
        self.capsule_layout.setObjectName("capsule_layout")
        self.capsule_layout.setProperty("class", "top-bar-capsule")
        layout_capsule_box = QHBoxLayout(self.capsule_layout)
        layout_capsule_box.setContentsMargins(4, 2, 4, 2)
        layout_capsule_box.setSpacing(2)

        self.layout_btns = {}
        for text, key, tip, ic_name in [
            ("1x1", "1x1", "1 Camera (Solo View)", "1x1"),
            ("2x2", "2x2", "4 Cameras (Quad View)", "2x2"),
            ("3x3", "3x3", "9 Cameras (Grid View)", "3x3"),
            ("Custom", "custom", "Custom Layout Studio: Configure grid & camera assignments", "custom"),
        ]:
            btn = QPushButton(f" {text}", self.capsule_layout)
            btn.setIcon(create_topbar_icon(ic_name, size=15))
            btn.setIconSize(QSize(15, 15))
            btn.setCheckable(True)
            btn.setToolTip(tip)
            btn.setProperty("class", "grid-layout-btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda ch, k=key: self._on_layout_btn_clicked(k))
            if key == "custom":
                btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                btn.customContextMenuRequested.connect(self._show_custom_layout_context_menu)
            self.layout_btns[key] = btn
            layout_capsule_box.addWidget(btn)

        self.btn_dual_hero = QPushButton(" Dual-Lens", self.capsule_layout)
        self.btn_dual_hero.setIcon(create_topbar_icon("dual_lens", size=15))
        self.btn_dual_hero.setIconSize(QSize(15, 15))
        self.btn_dual_hero.setCheckable(True)
        self.btn_dual_hero.setProperty("class", "grid-layout-btn")
        self.btn_dual_hero.setToolTip("View Dual-Lens (PTZ + Wide) simultaneously")
        self.btn_dual_hero.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dual_hero.clicked.connect(self.activate_dual_lens_mode)
        layout_capsule_box.addWidget(self.btn_dual_hero)

        cur_lay = self.app_settings.get("default_layout", "2x2")
        if cur_lay in self.layout_btns:
            self.layout_btns[cur_lay].setChecked(True)
        elif cur_lay == "2x1":
            self.btn_dual_hero.setChecked(True)
        else:
            self.layout_btns["2x2"].setChecked(True)

        top_layout.addWidget(self.capsule_layout)
        top_layout.addStretch(1)

        # --- Capsule 3: Surveillance Tools & Workstation System ---
        self.capsule_tools = QFrame(top_bar)
        self.capsule_tools.setObjectName("capsule_tools")
        self.capsule_tools.setProperty("class", "top-bar-capsule")
        tools_capsule_box = QHBoxLayout(self.capsule_tools)
        tools_capsule_box.setContentsMargins(4, 2, 4, 2)
        tools_capsule_box.setSpacing(2)

        # Aliases for compatibility
        self.capsule_camera = self.capsule_tools
        self.capsule_system = self.capsule_tools

        # Group 1: Camera Actions & Security
        self.btn_master_alerts = QPushButton(self.capsule_tools)
        self.btn_master_alerts.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_master_alerts.clicked.connect(lambda: self.toggle_master_alerts())
        tools_capsule_box.addWidget(self.btn_master_alerts)

        self.btn_trigger_settings = QPushButton(" Feed", self.capsule_tools)
        self.btn_trigger_settings.setIcon(create_topbar_icon("alerts", size=16))
        self.btn_trigger_settings.setIconSize(QSize(16, 16))
        self.btn_trigger_settings.setCheckable(True)
        self.btn_trigger_settings.setToolTip("Toggle incident events feed sidebar (Click to show / hide)")
        self.btn_trigger_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_trigger_settings.clicked.connect(self._open_alerts_tab)
        tools_capsule_box.addWidget(self.btn_trigger_settings)

        self.btn_global_quality_btn = QPushButton(self.capsule_tools)
        self.btn_global_quality_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_global_quality_btn.clicked.connect(self._cycle_global_quality)
        tools_capsule_box.addWidget(self.btn_global_quality_btn)

        self.btn_snap_all = QPushButton(" Snapshot", self.capsule_tools)
        self.btn_snap_all.setIcon(create_topbar_icon("snapshot", size=16))
        self.btn_snap_all.setIconSize(QSize(16, 16))
        self.btn_snap_all.setToolTip("Instant photo snapshot on selected camera (Ctrl+S)")
        self.btn_snap_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_snap_all.clicked.connect(self.snapshot_all)
        tools_capsule_box.addWidget(self.btn_snap_all)

        self.btn_ptz_panel = QPushButton(" PTZ", self.capsule_tools)
        self.btn_ptz_panel.setIcon(create_topbar_icon("ptz", size=16))
        self.btn_ptz_panel.setIconSize(QSize(16, 16))
        self.btn_ptz_panel.setCheckable(True)
        self.btn_ptz_panel.setToolTip("Open floating PTZ camera controls (D-Pad, Speed, Presets)")
        self.btn_ptz_panel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ptz_panel.clicked.connect(self.toggle_ptz_window)
        tools_capsule_box.addWidget(self.btn_ptz_panel)

        self.btn_intercom_panel = QPushButton(" Intercom", self.capsule_tools)
        self.btn_intercom_panel.setIcon(create_topbar_icon("intercom", size=16))
        self.btn_intercom_panel.setIconSize(QSize(16, 16))
        self.btn_intercom_panel.setCheckable(True)
        self.btn_intercom_panel.setToolTip("Open floating two-way audio intercom panel (Voice Talk)")
        self.btn_intercom_panel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_intercom_panel.clicked.connect(self.toggle_intercom_window)
        tools_capsule_box.addWidget(self.btn_intercom_panel)

        self.global_color_night_active = False
        self.btn_global_color_night = QPushButton(" Night Color", self.capsule_tools)
        self.btn_global_color_night.setIcon(create_topbar_icon("night_color", size=16))
        self.btn_global_color_night.setIconSize(QSize(16, 16))
        self.btn_global_color_night.setCheckable(True)
        self.btn_global_color_night.setToolTip("Toggle Full-Color Night Mode for all cameras (White Light & Color Restore)")
        self.btn_global_color_night.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_global_color_night.clicked.connect(self.toggle_global_color_night)
        tools_capsule_box.addWidget(self.btn_global_color_night)

        tools_capsule_box.addWidget(create_capsule_divider())

        self.btn_sound_alarm = QPushButton(" Siren: ON" if self.sound_alarms_enabled else " Siren: OFF", self.capsule_tools)
        self.btn_sound_alarm.setIcon(create_topbar_icon("siren", active=self.sound_alarms_enabled, size=16, custom_color="#f87171" if self.sound_alarms_enabled else "#94a3b8"))
        self.btn_sound_alarm.setIconSize(QSize(16, 16))
        self.btn_sound_alarm.setToolTip("Toggle audible siren alarms for incident detections")
        self.btn_sound_alarm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sound_alarm.clicked.connect(self.toggle_sound_alarms)
        tools_capsule_box.addWidget(self.btn_sound_alarm)

        tools_capsule_box.addWidget(create_capsule_divider())

        # Group 2: System Telemetry & Workstation
        self.btn_cpu_monitor = QPushButton(" CPU", self.capsule_tools)
        self.btn_cpu_monitor.setIcon(create_topbar_icon("cpu", size=15, custom_color="#38bdf8"))
        self.btn_cpu_monitor.setIconSize(QSize(15, 15))
        self.btn_cpu_monitor.setToolTip("Real-time CPU telemetry monitor (Click to open Performance Settings)")
        self.btn_cpu_monitor.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cpu_monitor.clicked.connect(self.open_performance_dialog)
        tools_capsule_box.addWidget(self.btn_cpu_monitor)

        self.btn_scanner = QPushButton(" Scanner", self.capsule_tools)
        self.btn_scanner.setIcon(create_topbar_icon("scanner", size=16))
        self.btn_scanner.setIconSize(QSize(16, 16))
        self.btn_scanner.setToolTip("Scan local network for ONVIF and Cam720 cameras")
        self.btn_scanner.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scanner.clicked.connect(self.open_scanner_dialog)
        tools_capsule_box.addWidget(self.btn_scanner)

        self.btn_retention = QPushButton(" Retention", self.capsule_tools)
        self.btn_retention.setIcon(create_topbar_icon("retention", size=16))
        self.btn_retention.setIconSize(QSize(16, 16))
        self.btn_retention.setToolTip("Storage Retention & Auto-Cleaner Manager")
        self.btn_retention.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_retention.clicked.connect(lambda: self.check_old_alerts_retention(silent_if_none=False))
        tools_capsule_box.addWidget(self.btn_retention)

        self.btn_phone = QPushButton(" Mobile", self.capsule_tools)
        self.btn_phone.setIcon(create_topbar_icon("mobile", size=16))
        self.btn_phone.setIconSize(QSize(16, 16))
        self.btn_phone.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_phone.customContextMenuRequested.connect(self._show_phone_btn_context_menu)
        self.btn_phone.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_phone.clicked.connect(self.open_phone_access_dialog)
        tools_capsule_box.addWidget(self.btn_phone)

        self.btn_player = QPushButton(" Recordings", self.capsule_tools)
        self.btn_player.setIcon(create_topbar_icon("recordings", size=16))
        self.btn_player.setIconSize(QSize(16, 16))
        self.btn_player.setToolTip("Open video recordings & incident clips browser (Key P)")
        self.btn_player.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_player.clicked.connect(self.open_gallery_dialog)
        tools_capsule_box.addWidget(self.btn_player)

        tools_capsule_box.addWidget(create_capsule_divider())

        # Group 3: Window Settings & Fullscreen
        self.btn_settings = QPushButton(self.capsule_tools)
        self.btn_settings.setIcon(create_topbar_icon("settings", size=16))
        self.btn_settings.setIconSize(QSize(16, 16))
        self.btn_settings.setToolTip("Application settings (Themes, Mobile notifications, AI, Storage)")
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(lambda: self.open_settings_dialog())
        tools_capsule_box.addWidget(self.btn_settings)

        self.btn_fullscreen = QPushButton(self.capsule_tools)
        self.btn_fullscreen.setIcon(create_topbar_icon("fullscreen", size=16))
        self.btn_fullscreen.setIconSize(QSize(16, 16))
        self.btn_fullscreen.setToolTip("Fullscreen (F11)")
        self.btn_fullscreen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        tools_capsule_box.addWidget(self.btn_fullscreen)

        # Keep frequent commands visible; secondary controls share an accessible menu.
        self._overflow_buttons = [
            (self.btn_intercom_panel, "Intercom"),
            (self.btn_global_color_night, "Night color"),
            (self.btn_sound_alarm, "Audible alarms"),
            (self.btn_scanner, "Discover cameras"),
            (self.btn_retention, "Storage retention"),
            (self.btn_phone, "Mobile access"),
        ]
        for button, title in self._overflow_buttons:
            tools_capsule_box.removeWidget(button)
            button.hide()
            button.setAccessibleName(title)
        self.btn_more_tools = QPushButton(" More", self.capsule_tools)
        self.btn_more_tools.setAccessibleName("More workstation tools")
        self.btn_more_tools.setToolTip("More workstation tools")
        self.btn_more_tools.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tools_menu = QMenu(self.btn_more_tools)
        self.tools_menu.aboutToShow.connect(self._populate_tools_menu)
        self.btn_more_tools.setMenu(self.tools_menu)
        tools_capsule_box.insertWidget(tools_capsule_box.indexOf(self.btn_settings), self.btn_more_tools)
        for button in top_bar.findChildren(QPushButton):
            if not button.accessibleName():
                button.setAccessibleName(button.toolTip() or button.text().strip())

        top_layout.addWidget(self.capsule_tools)

        # --- Capsule 4: Integrated Windows Window Controls ---
        self.capsule_win_controls = QFrame(top_bar)
        self.capsule_win_controls.setObjectName("capsule_win_controls")
        self.capsule_win_controls.setProperty("class", "top-bar-capsule")
        win_ctrl_layout = QHBoxLayout(self.capsule_win_controls)
        win_ctrl_layout.setContentsMargins(4, 2, 4, 2)
        win_ctrl_layout.setSpacing(3)

        self.btn_win_min = QPushButton(self.capsule_win_controls)
        self.btn_win_min.setIcon(create_topbar_icon("win_min", size=16))
        self.btn_win_min.setIconSize(QSize(16, 16))
        self.btn_win_min.setFixedSize(28, 28)
        self.btn_win_min.setToolTip("Minimize Window")
        self.btn_win_min.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_win_min.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.14);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.22);
            }
        """)
        self.btn_win_min.clicked.connect(self.showMinimized)
        win_ctrl_layout.addWidget(self.btn_win_min)

        self.btn_win_max = QPushButton(self.capsule_win_controls)
        self.btn_win_max.setIcon(create_topbar_icon("win_max", size=16))
        self.btn_win_max.setIconSize(QSize(16, 16))
        self.btn_win_max.setFixedSize(28, 28)
        self.btn_win_max.setToolTip("Maximize Window")
        self.btn_win_max.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_win_max.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.14);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.22);
            }
        """)
        self.btn_win_max.clicked.connect(self._toggle_maximize_restore)
        win_ctrl_layout.addWidget(self.btn_win_max)

        self.btn_win_close = QPushButton(self.capsule_win_controls)
        self.btn_win_close.setIcon(create_topbar_icon("win_close", size=16))
        self.btn_win_close.setIconSize(QSize(16, 16))
        self.btn_win_close.setFixedSize(28, 28)
        self.btn_win_close.setToolTip("Close Application (Alt+F4)")
        self.btn_win_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_win_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.85);
            }
            QPushButton:pressed {
                background-color: #dc2626;
            }
        """)
        self.btn_win_close.clicked.connect(self.close)
        win_ctrl_layout.addWidget(self.btn_win_close)

        top_layout.addWidget(self.capsule_win_controls)

        # Non-visual references for existing callback compatibility
        self.btn_stream_all = QPushButton(self)
        self.btn_stream_all.hide()
        self.cmb_global_quality = QComboBox(self)
        self.cmb_global_quality.addItem("MAX", QualityMode.ULTRA_MAX)
        self.cmb_global_quality.addItem("2K", QualityMode.ULTRA_2K)
        self.cmb_global_quality.addItem("HD", QualityMode.MID_HD)
        self.cmb_global_quality.addItem("SD", QualityMode.LOW_SD)
        idx_q = self.cmb_global_quality.findData(self.global_quality)
        if idx_q >= 0:
            self.cmb_global_quality.setCurrentIndex(idx_q)
        self.cmb_global_quality.currentIndexChanged.connect(self._on_global_quality_changed)
        self.cmb_global_quality.hide()
        self.cmb_perf_profile_bar = QComboBox(self)
        self.cmb_perf_profile_bar.hide()
        self.btn_global_motion = QPushButton(self)
        self.btn_global_motion.hide()
        self.btn_movement_view = QPushButton(self)
        self.btn_movement_view.hide()
        self.btn_rec_all = QPushButton(self)
        self.btn_rec_all.hide()

        # Update initial states of security and quality topbar buttons
        self._update_master_alerts_btn_style()
        self._update_global_quality_btn_style()

        root_layout.addWidget(top_bar)

        # High-visibility Alarm Notification Toast Overlay (Floats over top of central widget with zero layout shift)
        self.alarm_banner = QLabel(central_widget)
        self.alarm_banner.setStyleSheet("""
            QLabel {
                background-color: #dc2626;
                color: #ffffff;
                font-weight: 700;
                font-size: 12px;
                padding: 6px 16px;
                border-radius: 4px;
                border: 1px solid #ef4444;
            }
        """)
        self.alarm_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alarm_banner.hide()
        # NOT added to root_layout to prevent camera displacement or layout shifts!

        self.alarm_banner_timer = QTimer(self)
        self.alarm_banner_timer.setSingleShot(True)
        self.alarm_banner_timer.setInterval(int(self.app_settings.get("banner_duration_sec", 6) * 1000))
        self.alarm_banner_timer.timeout.connect(self.alarm_banner.hide)

        # Floating Fullscreen Exit Button
        self.btn_exit_fullscreen_float = QPushButton("[ ] Exit Fullscreen (ESC)", central_widget)
        self.btn_exit_fullscreen_float.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #3b82f6;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2563eb;
                border-color: #60a5fa;
            }
        """)
        self.btn_exit_fullscreen_float.clicked.connect(self.exit_fullscreen)
        self.btn_exit_fullscreen_float.hide()

        # --- 2. Main Content Splitter ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setContentsMargins(0, 0, 0, 0)
        self.splitter.setHandleWidth(8)
        self.splitter.setChildrenCollapsible(True)

        # --- Left / Right Dockable Sidebar with Modern Tabs ---
        self.sidebar = QFrame(self.splitter)
        self.sidebar.setObjectName("left_sidebar")
        self.sidebar.setMinimumWidth(0)
        self.sidebar.setMaximumWidth(1400)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(6, 6, 6, 6)
        side_layout.setSpacing(6)

        # Seamless Drop-in Segmented Capsule Switcher + Stacked Pages
        self.side_tabs = ModernSideTabWidget(self.sidebar)
        self.btn_dock_side = self.side_tabs.btn_dock_side
        self.btn_dock_side.clicked.connect(self.toggle_sidebar_position)
        self.side_tabs.currentChanged.connect(self._on_sidebar_tab_changed)
        side_layout.addWidget(self.side_tabs, stretch=1)

        # === TAB 0: Cameras Workspace ===
        tab_cam = QWidget()
        cam_layout = QVBoxLayout(tab_cam)
        cam_layout.setContentsMargins(2, 4, 2, 4)
        cam_layout.setSpacing(6)

        # Quick Search & Filter Bar with Vector Search Icon
        self.cam_search_input = QLineEdit(tab_cam)
        self.cam_search_input.setPlaceholderText("Filter cameras or streams...")
        self.cam_search_input.setClearButtonEnabled(True)
        self.cam_search_input.addAction(create_topbar_icon("search", size=13, custom_color="#64748b"), QLineEdit.ActionPosition.LeadingPosition)
        self.cam_search_input.setFixedHeight(30)
        self.cam_search_input.setStyleSheet("""
            QLineEdit {
                background-color: #070b14;
                color: #f8fafc;
                border: 1px solid #1a2336;
                border-radius: 7px;
                padding: 4px 8px 4px 26px;
                font-size: 11px;
                selection-background-color: #2563eb;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
                background-color: #0b1120;
            }
        """)

        # Quick Action Strip (Add, Scan, Stream All) with Vector Icons
        cam_actions_strip = QHBoxLayout()
        cam_actions_strip.setSpacing(6)

        self.btn_add_cam = QPushButton(" Add", tab_cam)
        self.btn_add_cam.setIcon(create_topbar_icon("add", size=13, custom_color="#ffffff"))
        self.btn_add_cam.setToolTip("Manually add camera (IP, RTSP, ONVIF)")
        self.btn_add_cam.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_cam.setFixedHeight(28)
        self.btn_add_cam.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);
                color: #ffffff;
                font-weight: 700;
                font-size: 11px;
                border: 1px solid #3b82f6;
                border-radius: 6px;
                padding: 4px 9px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3b82f6, stop:1 #2563eb);
                border-color: #60a5fa;
            }
        """)
        self.btn_add_cam.clicked.connect(self.open_add_camera_dialog)
        cam_actions_strip.addWidget(self.btn_add_cam)

        self.btn_scan = QPushButton(" Scan", tab_cam)
        self.btn_scan.setIcon(create_topbar_icon("scanner", size=13, custom_color="#94a3b8"))
        self.btn_scan.setToolTip("Auto-discover cameras on local network")
        self.btn_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan.setFixedHeight(28)
        self.btn_scan.setStyleSheet("""
            QPushButton {
                background-color: #0c1220;
                color: #cbd5e1;
                font-weight: 600;
                font-size: 11px;
                border: 1px solid #1a2336;
                border-radius: 6px;
                padding: 4px 9px;
            }
            QPushButton:hover {
                background-color: #162035;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.btn_scan.clicked.connect(self.open_scanner_dialog)
        cam_actions_strip.addWidget(self.btn_scan)

        self.btn_stream_all = QPushButton(" Stream All", tab_cam)
        self.btn_stream_all.setIcon(create_topbar_icon("stream", size=13, custom_color="#cbd5e1"))
        self.btn_stream_all.setToolTip("Automatically populate grid with all cameras")
        self.btn_stream_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stream_all.setFixedHeight(28)
        self.btn_stream_all.setStyleSheet("""
            QPushButton {
                background-color: #0c1220;
                color: #cbd5e1;
                border: 1px solid #1a2336;
                border-radius: 6px;
                padding: 4px 9px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #162035;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.btn_stream_all.clicked.connect(self.stream_all_cameras)
        cam_actions_strip.addWidget(self.btn_stream_all)

        cam_layout.addWidget(self.cam_search_input)
        cam_layout.addLayout(cam_actions_strip)

        # Draggable Camera Cards Tree
        self.cam_tree = ModernDraggableCameraTree(tab_cam)
        self.cam_search_input.textChanged.connect(self.cam_tree.filter_cameras)
        self.cam_tree.itemClicked.connect(self._on_tree_item_clicked)
        self.cam_tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self.cam_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        cam_layout.addWidget(self.cam_tree, stretch=1)

        self.side_tabs.addTab(tab_cam, "Cameras (0)")

        # === TAB 1: Live Alerts Feed ===
        tab_alerts = QWidget()
        alerts_layout = QVBoxLayout(tab_alerts)
        alerts_layout.setContentsMargins(4, 4, 4, 4)
        alerts_layout.setSpacing(6)

        # Header Row 1: Title + Count Badge
        hdr_row1 = QHBoxLayout()
        lbl_alert_title = QLabel("INCIDENT FEED", tab_alerts)
        lbl_alert_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
        hdr_row1.addWidget(lbl_alert_title)

        self.lbl_alert_count_badge = QLabel("0 Events", tab_alerts)
        self.lbl_alert_count_badge.setStyleSheet("""
            background-color: rgba(37, 99, 235, 0.15);
            color: #60a5fa;
            font-size: 10px;
            font-weight: 700;
            border: 1px solid #2563eb;
            border-radius: 4px;
            padding: 2px 7px;
        """)
        hdr_row1.addWidget(self.lbl_alert_count_badge)
        hdr_row1.addStretch()
        alerts_layout.addLayout(hdr_row1)

        # Header Row 2: Management Actions (30d Retention, Clips, Clear All) with Vector Icons
        hdr_row2 = QHBoxLayout()
        hdr_row2.setSpacing(5)

        self.btn_retention_clean = QPushButton(" Clean 30d", tab_alerts)
        self.btn_retention_clean.setIcon(create_topbar_icon("retention", size=12, custom_color="#94a3b8"))
        self.btn_retention_clean.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_retention_clean.setFixedHeight(26)
        self.btn_retention_clean.setStyleSheet("""
            QPushButton {
                background-color: #0c1220;
                color: #94a3b8;
                border: 1px solid #1a2336;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #162035;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.btn_retention_clean.clicked.connect(lambda: self.check_old_alerts_retention(silent_if_none=False))
        self._update_retention_button_label()
        hdr_row2.addWidget(self.btn_retention_clean)

        self.btn_clips_gallery = QPushButton(" Video Clips", tab_alerts)
        self.btn_clips_gallery.setIcon(create_topbar_icon("recordings", size=12, custom_color="#94a3b8"))
        self.btn_clips_gallery.setToolTip("Open incident recordings and video clips gallery")
        self.btn_clips_gallery.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clips_gallery.setFixedHeight(26)
        self.btn_clips_gallery.setStyleSheet("""
            QPushButton {
                background-color: #0c1220;
                color: #94a3b8;
                border: 1px solid #1a2336;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #162035;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.btn_clips_gallery.clicked.connect(self.open_gallery_dialog)
        hdr_row2.addWidget(self.btn_clips_gallery)

        self.btn_clear_alerts = QPushButton(" Clear All", tab_alerts)
        self.btn_clear_alerts.setIcon(create_topbar_icon("clear", size=12, custom_color="#f87171"))
        self.btn_clear_alerts.setToolTip("Clear all displayed incident alerts from history")
        self.btn_clear_alerts.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_alerts.setFixedHeight(26)
        self.btn_clear_alerts.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.08);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.25);
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.18);
                color: #ffffff;
                border-color: #ef4444;
            }
        """)
        self.btn_clear_alerts.clicked.connect(self._on_clear_alerts_clicked)
        hdr_row2.addWidget(self.btn_clear_alerts)

        alerts_layout.addLayout(hdr_row2)

        # ScrollArea containing rich AlertCardWidgets (stabilized scrollbar policy prevents layout width twitching)
        self.alerts_scroll = QScrollArea(tab_alerts)
        self.alerts_scroll.setWidgetResizable(True)
        self.alerts_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.alerts_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.alerts_scroll.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.alerts_scroll.setStyleSheet("background: transparent; border: none;")
        self.alerts_scroll_content = QWidget()
        self.alerts_scroll_content.setStyleSheet("background: transparent;")
        self.alerts_feed_layout = QVBoxLayout(self.alerts_scroll_content)
        self.alerts_feed_layout.setContentsMargins(2, 2, 2, 2)
        self.alerts_feed_layout.setSpacing(6)
        self.alerts_feed_layout.addStretch()
        self.alerts_scroll.setWidget(self.alerts_scroll_content)
        alerts_layout.addWidget(self.alerts_scroll)

        self.side_tabs.addTab(tab_alerts, "Alerts (0)")

        # === TAB 2: System Telemetry & Cloud Storage Hub ===
        self.sidebar_telemetry = ModernSidebarTelemetryWidget(self.sidebar)
        self.sidebar_telemetry.open_folder_requested.connect(self._open_cctv_gdrive_folder)
        self.sidebar_telemetry.open_web_requested.connect(self._open_web_stream_in_browser)

        # Backward compatibility aliases
        self.lbl_sidebar_storage = self.sidebar_telemetry.lbl_storage_path
        self.lbl_sidebar_storage_sub = self.sidebar_telemetry.lbl_storage_sub
        self.sidebar_storage_bar = self.sidebar_telemetry.storage_bar
        self.lbl_sidebar_ai = self.sidebar_telemetry.lbl_ai_model
        self.lbl_sidebar_web = self.sidebar_telemetry.lbl_web_url
        self.lbl_sidebar_ret = self.sidebar_telemetry.lbl_cloud_status

        self.side_tabs.addTab(self.sidebar_telemetry, "System HUD")

        # Hidden Slim Footer proxy across tabs (zero vertical space, not added to layout)
        self.sidebar_footer = PersistentSlimFooter(self.sidebar)
        self.sidebar_footer.open_drive_requested.connect(self._open_cctv_gdrive_folder)
        self.sidebar_footer.open_web_requested.connect(self.open_phone_access_dialog)
        self.sidebar_footer.hide()

        # Responsive Sidebar resize listener (collapses button text to icons when narrow)
        orig_side_resize = self.sidebar.resizeEvent
        def _side_resize_wrapper(event):
            orig_side_resize(event)
            self._on_sidebar_resized(event)
        self.sidebar.resizeEvent = _side_resize_wrapper

        # Notification-Style Flyout Panel for PTZ Controls (Anchored at top-right, drops down like a notification)
        self.ptz_flyout = QFrame(central_widget)
        self.ptz_flyout.setObjectName("ptz_flyout")
        self.ptz_flyout.setStyleSheet("""
            QFrame#ptz_flyout {
                background-color: #0b0f19;
                border: 1px solid #1e293b;
                border-top: 2px solid #38bdf8;
                border-radius: 8px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self.ptz_flyout)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 220))
        shadow.setOffset(0, 8)
        self.ptz_flyout.setGraphicsEffect(shadow)

        flyout_layout = QVBoxLayout(self.ptz_flyout)
        flyout_layout.setContentsMargins(6, 6, 6, 6)
        flyout_layout.setSpacing(0)

        self.ptz_dock = PTZPad(self.ptz_flyout)
        self.ptz_dock.ptz_command_issued.connect(self._on_ptz_command_issued)
        self.ptz_dock.ptz_zoom_issued.connect(self._on_ptz_zoom_issued)
        self.ptz_dock.preset_goto_issued.connect(self._on_ptz_preset_goto)
        self.ptz_dock.preset_save_issued.connect(self._on_ptz_preset_save)
        self.ptz_dock.patrol_step_issued.connect(self._on_ptz_patrol_step)
        self.ptz_dock.reset_zoom_issued.connect(self._on_ptz_reset_zoom)
        self.ptz_dock.camera_target_changed.connect(self._on_ptz_camera_target_changed)
        self.ptz_dock.close_requested.connect(self.hide_ptz_flyout)
        self.ptz_dock.settings_toggled.connect(lambda exp: self._reposition_ptz_flyout())
        flyout_layout.addWidget(self.ptz_dock)

        self.ptz_flyout.hide()

        # Notification-Style Flyout Panel for Two-Way Audio Intercom (Anchored at top-right)
        self.intercom_flyout = QFrame(central_widget)
        self.intercom_flyout.setObjectName("intercom_flyout")
        self.intercom_flyout.setStyleSheet("""
            QFrame#intercom_flyout {
                background-color: #0b0f19;
                border: 1px solid #1e293b;
                border-top: 2px solid #0284c7;
                border-radius: 8px;
            }
        """)
        shadow_ic = QGraphicsDropShadowEffect(self.intercom_flyout)
        shadow_ic.setBlurRadius(28)
        shadow_ic.setColor(QColor(0, 0, 0, 220))
        shadow_ic.setOffset(0, 8)
        self.intercom_flyout.setGraphicsEffect(shadow_ic)

        ic_flyout_layout = QVBoxLayout(self.intercom_flyout)
        ic_flyout_layout.setContentsMargins(6, 6, 6, 6)
        ic_flyout_layout.setSpacing(0)

        self.intercom_dock = IntercomPad(self.intercom_flyout)
        self.intercom_dock.close_requested.connect(self.hide_intercom_flyout)
        ic_flyout_layout.addWidget(self.intercom_dock)

        self.intercom_flyout.hide()

        self.splitter.addWidget(self.sidebar)

        # --- Center: Video Grid Container ---
        grid_container = QWidget(self.splitter)
        grid_container.setObjectName("grid_container")
        self.grid_container = grid_container
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setContentsMargins(6, 6, 6, 6)
        self.grid_layout.setSpacing(6)

        # Create 16 video tiles
        for i in range(16):
            tile = VideoTile(tile_index=i, parent=grid_container)
            tile.tile_selected.connect(self._on_tile_selected)
            tile.solo_toggled.connect(self._on_tile_solo_toggled)
            tile.tile_double_clicked.connect(self._on_tile_double_clicked)
            tile.stream_requested.connect(self._on_tile_stream_requested)
            tile.dual_lens_requested.connect(self.activate_dual_lens_mode)
            tile.stream_closed.connect(self._on_tile_closed)
            tile.ai_alarm_triggered.connect(self.on_ai_alarm_triggered)
            self.video_tiles.append(tile)

        self.video_tiles[0].set_selected(True)
        self.splitter.addWidget(grid_container)

        # Proportions: restore saved sidebar width (default 380px) & visibility state
        saved_sidebar_w = max(340, int(self.app_settings.get("sidebar_width", 380)))
        sidebar_vis = self.app_settings.get("sidebar_visible", True)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setChildrenCollapsible(True)
        sidebar_idx = self.splitter.indexOf(self.sidebar)
        grid_idx = 1 if sidebar_idx == 0 else 0
        self.splitter.setCollapsible(sidebar_idx, True)
        self.splitter.setCollapsible(grid_idx, False)
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        root_layout.addWidget(self.splitter, stretch=1)

        if not sidebar_vis:
            self.sidebar.hide()
            if hasattr(self, "btn_toggle_sidebar"):
                self.btn_toggle_sidebar.setChecked(False)
            if sidebar_idx == 0:
                self.splitter.setSizes([0, max(600, self.width())])
            else:
                self.splitter.setSizes([max(600, self.width()), 0])
        else:
            if sidebar_idx == 0:
                self.splitter.setSizes([saved_sidebar_w, max(600, self.width() - saved_sidebar_w)])
            else:
                self.splitter.setSizes([max(600, self.width() - saved_sidebar_w), saved_sidebar_w])

        # --- 3. Sleek Bottom Status Bar (Dedicated Frame, Zero Clipping, High-End Styling) ---
        self.setStatusBar(None)

        self.bottom_bar = QFrame(central_widget)
        self.bottom_bar.setObjectName("main_bottom_bar")
        self.bottom_bar.setFixedHeight(28)
        self.bottom_bar.setStyleSheet("""
            QFrame#main_bottom_bar {
                background-color: #0b0c10;
                border-top: 1px solid #1a1d26;
            }
        """)
        bottom_layout = QHBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(14, 0, 14, 0)
        bottom_layout.setSpacing(10)

        # Left: Live operational indicator & system status message
        self.lbl_system_dot = QLabel("●", self.bottom_bar)
        self.lbl_system_dot.setStyleSheet("color: #38bdf8; font-size: 11px;")
        bottom_layout.addWidget(self.lbl_system_dot)

        self.lbl_status_msg = QLabel("System Ready", self.bottom_bar)
        self.lbl_status_msg.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500;")
        bottom_layout.addWidget(self.lbl_status_msg)

        bottom_layout.addStretch(1)

        # Right: Telemetry chips with guaranteed spacing and zero clipping
        self.lbl_active_info = QLabel("Slot #1", self.bottom_bar)
        self.lbl_active_info.setStyleSheet("background-color: #141620; border: 1px solid #222534; border-radius: 4px; padding: 2px 8px; color: #94a3b8; font-weight: 500; font-size: 11px;")
        bottom_layout.addWidget(self.lbl_active_info)

        self.lbl_motion_status = QLabel("AI: Active", self.bottom_bar)
        self.lbl_motion_status.setStyleSheet("background-color: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 4px; padding: 2px 8px; color: #38bdf8; font-weight: 600; font-size: 11px;")
        bottom_layout.addWidget(self.lbl_motion_status)

        self.lbl_stream_count = QLabel("0 Cameras", self.bottom_bar)
        self.lbl_stream_count.setStyleSheet("background-color: #141620; border: 1px solid #222534; border-radius: 4px; padding: 2px 8px; color: #cbd5e1; font-weight: 500; font-size: 11px;")
        bottom_layout.addWidget(self.lbl_stream_count)

        self.lbl_total_fps = QLabel("0.0 FPS", self.bottom_bar)
        self.lbl_total_fps.setStyleSheet("background-color: #141620; border: 1px solid #222534; border-radius: 4px; padding: 2px 8px; color: #cbd5e1; font-weight: 500; font-size: 11px;")
        bottom_layout.addWidget(self.lbl_total_fps)

        self.lbl_storage_status = QLabel("Drive CCTV", self.bottom_bar)
        self.lbl_storage_status.setStyleSheet("background-color: #141620; border: 1px solid #222534; border-radius: 4px; padding: 2px 8px; color: #94a3b8; font-weight: 500; font-size: 11px;")
        bottom_layout.addWidget(self.lbl_storage_status)

        # Removed per user request: "Scoate bara de jos din poza a 2-a"
        self.bottom_bar.hide()

        self._status_proxy = SlimStatusBarProxy(self.lbl_status_msg, self.lbl_system_dot)

        self.set_grid_layout(self.current_layout)

        # Stats timer
        self.stats_timer = QTimer(self)
        self.stats_timer.setInterval(1000)
        self.stats_timer.timeout.connect(self._update_global_stats)
        self.stats_timer.start()

    def statusBar(self):
        """Returns the sleek status bar proxy."""
        return getattr(self, "_status_proxy", None)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self, self._exit_fullscreen_or_solo)
        QShortcut(QKeySequence("Ctrl+B"), self, self.toggle_sidebar)
        QShortcut(QKeySequence("F10"), self, self.toggle_sidebar)
        QShortcut(QKeySequence("1"), self, lambda: self.set_grid_layout("1x1"))
        QShortcut(QKeySequence("2"), self, lambda: self.set_grid_layout("2x1"))
        QShortcut(QKeySequence("4"), self, lambda: self.set_grid_layout("2x2"))
        QShortcut(QKeySequence("6"), self, lambda: self.set_grid_layout("1+5"))
        QShortcut(QKeySequence("9"), self, lambda: self.set_grid_layout("3x3"))
        QShortcut(QKeySequence("0"), self, lambda: self.set_grid_layout("4x4"))
        QShortcut(QKeySequence("M"), self, self._toggle_movement_view)

    def toggle_sidebar(self):
        """Toggles sidebar visibility and expands camera grid across full window."""
        if not hasattr(self, "sidebar") or not hasattr(self, "splitter"):
            return

        sidebar_idx = self.splitter.indexOf(self.sidebar)
        cur_w = self.sidebar.width()
        is_effectively_visible = getattr(self, "is_sidebar_visible", True) and self.sidebar.isVisible() and cur_w > 30

        self.is_sidebar_visible = not is_effectively_visible
        saved_w = max(340, int(self.app_settings.get("sidebar_width", 380)))
        total_w = max(800, self.width())

        if not self.is_sidebar_visible:
            if cur_w >= 260:
                self.app_settings["sidebar_width"] = cur_w
            self.sidebar.hide()
            if hasattr(self, "btn_toggle_sidebar"):
                self.btn_toggle_sidebar.setChecked(False)
            self.app_settings["sidebar_visible"] = False
            if sidebar_idx == 0:
                self.splitter.setSizes([0, total_w])
            else:
                self.splitter.setSizes([total_w, 0])
            if hasattr(self, "btn_trigger_settings"):
                self.btn_trigger_settings.setChecked(False)
        else:
            self.sidebar.show()
            if hasattr(self, "btn_toggle_sidebar"):
                self.btn_toggle_sidebar.setChecked(True)
            self.app_settings["sidebar_visible"] = True
            if sidebar_idx == 0:
                self.splitter.setSizes([saved_w, max(400, total_w - saved_w)])
            else:
                self.splitter.setSizes([max(400, total_w - saved_w), saved_w])
            if hasattr(self, "btn_trigger_settings"):
                is_alerts = (hasattr(self, "side_tabs") and self.side_tabs.currentIndex() == 1)
                self.btn_trigger_settings.setChecked(is_alerts)

        self.device_manager.config["app_settings"] = self.app_settings
        self.device_manager.save_config()

    def toggle_sidebar_position(self):
        """Swaps the sidebar position between the left and right sides of the workstation."""
        if not hasattr(self, "sidebar") or not hasattr(self, "splitter"):
            return
        is_on_left = (self.splitter.indexOf(self.sidebar) == 0)
        cur_sizes = self.splitter.sizes()
        if is_on_left:
            # Move to right side
            self.splitter.insertWidget(1, self.sidebar)
            self.splitter.setCollapsible(0, False)
            self.splitter.setCollapsible(1, True)
            if hasattr(self, "btn_dock_side"):
                self.btn_dock_side.setToolTip("Dock sidebar on Left side of workstation")
            self.app_settings["sidebar_position"] = "right"
            if len(cur_sizes) >= 2:
                self.splitter.setSizes([cur_sizes[1], cur_sizes[0]])
        else:
            # Move to left side
            self.splitter.insertWidget(0, self.sidebar)
            self.splitter.setCollapsible(0, True)
            self.splitter.setCollapsible(1, False)
            if hasattr(self, "btn_dock_side"):
                self.btn_dock_side.setToolTip("Dock sidebar on Right side of workstation")
            self.app_settings["sidebar_position"] = "left"
            if len(cur_sizes) >= 2:
                self.splitter.setSizes([cur_sizes[1], cur_sizes[0]])

        self.device_manager.config["app_settings"] = self.app_settings
        self.device_manager.save_config()
        self._apply_window_corners()

    def _on_sidebar_tab_changed(self, idx: int):
        """Synchronizes top bar Alerts button checked state with the active sidebar tab."""
        if hasattr(self, "btn_trigger_settings"):
            is_alerts = (idx == 1 and getattr(self, "is_sidebar_visible", True))
            self.btn_trigger_settings.setChecked(is_alerts)

    def _open_alerts_tab(self):
        """Toggles the Alerts panel: shows when hidden or on another tab; hides when currently active."""
        is_sidebar_visible = getattr(self, "is_sidebar_visible", True)
        current_tab = self.side_tabs.currentIndex() if hasattr(self, "side_tabs") else 0

        if is_sidebar_visible and current_tab == 1:
            # Alerts feed is already showing on screen -> hide it!
            self.toggle_sidebar()
            if hasattr(self, "btn_trigger_settings"):
                self.btn_trigger_settings.setChecked(False)
        else:
            # Alerts feed is either hidden or on another tab -> show it!
            if not is_sidebar_visible:
                self.toggle_sidebar()
            if hasattr(self, "side_tabs"):
                self.side_tabs.setCurrentIndex(1)
            if hasattr(self, "btn_trigger_settings"):
                self.btn_trigger_settings.setChecked(True)

    def _open_ptz_tab(self):
        """Toggles the notification-style PTZ flyout panel."""
        self.toggle_ptz_window()

    def toggle_ptz_window(self):
        """Toggles visibility of the notification-style PTZ flyout panel."""
        if hasattr(self, "ptz_flyout") and self.ptz_flyout.isVisible():
            self.hide_ptz_flyout()
        else:
            self.show_ptz_flyout()

    def show_ptz_flyout(self):
        """Displays the notification-style PTZ flyout panel at the top-right."""
        if hasattr(self, "intercom_flyout") and self.intercom_flyout.isVisible():
            self.hide_intercom_flyout()
        if hasattr(self, "ptz_flyout") and self.ptz_flyout:
            self._reposition_ptz_flyout()
            self.ptz_flyout.show()
            self.ptz_flyout.raise_()
        if hasattr(self, "btn_ptz_panel"):
            self.btn_ptz_panel.setChecked(True)

    def hide_ptz_flyout(self):
        """Hides the notification-style PTZ flyout panel."""
        if hasattr(self, "ptz_flyout") and self.ptz_flyout:
            self.ptz_flyout.hide()
        if hasattr(self, "btn_ptz_panel"):
            self.btn_ptz_panel.setChecked(False)

    def _reposition_ptz_flyout(self):
        """Positions the notification flyout panel strictly in the top-right corner."""
        cw = self.centralWidget()
        if not cw or not hasattr(self, "ptz_flyout") or not self.ptz_flyout:
            return

        is_expanded = self.ptz_dock.is_settings_expanded() if hasattr(self, "ptz_dock") and self.ptz_dock else False
        panel_w = 345 if not is_expanded else 365
        top_offset = 82 if (hasattr(self, "top_bar") and self.top_bar and self.top_bar.isVisible()) else 8
        bottom_offset = 36 if (hasattr(self, "bottom_bar") and self.bottom_bar and self.bottom_bar.isVisible()) else 8
        avail_h = cw.height() - top_offset - bottom_offset

        if is_expanded:
            panel_h = min(max(340, avail_h), 625)
        else:
            panel_h = 368

        # Pin to TOP-RIGHT corner (like a Windows/macOS notification, NEVER in the left!)
        panel_x = max(10, cw.width() - panel_w - 14)
        panel_y = top_offset

        self.ptz_flyout.setGeometry(panel_x, panel_y, panel_w, panel_h)
        self.ptz_flyout.raise_()

    def toggle_intercom_window(self):
        """Toggles visibility of the notification-style Intercom flyout panel."""
        if hasattr(self, "intercom_flyout") and self.intercom_flyout.isVisible():
            self.hide_intercom_flyout()
        else:
            self.show_intercom_flyout()

    def show_intercom_flyout(self):
        """Displays the notification-style Intercom flyout panel at the top-right."""
        if hasattr(self, "ptz_flyout") and self.ptz_flyout.isVisible():
            self.hide_ptz_flyout()
        if hasattr(self, "intercom_flyout") and self.intercom_flyout:
            self._reposition_intercom_flyout()
            self.intercom_flyout.show()
            self.intercom_flyout.raise_()
        if hasattr(self, "btn_intercom_panel"):
            self.btn_intercom_panel.setChecked(True)

    def hide_intercom_flyout(self):
        """Hides the notification-style Intercom flyout panel."""
        if hasattr(self, "intercom_flyout") and self.intercom_flyout:
            self.intercom_flyout.hide()
        if hasattr(self, "btn_intercom_panel"):
            self.btn_intercom_panel.setChecked(False)

    def _reposition_intercom_flyout(self):
        """Positions the Intercom flyout panel strictly in the top-right corner."""
        cw = self.centralWidget()
        if not cw or not hasattr(self, "intercom_flyout") or not self.intercom_flyout:
            return

        panel_w = 345
        panel_h = 330
        top_offset = 82 if (hasattr(self, "top_bar") and self.top_bar and self.top_bar.isVisible()) else 8
        panel_x = max(10, cw.width() - panel_w - 14)
        panel_y = top_offset

        self.intercom_flyout.setGeometry(panel_x, panel_y, panel_w, panel_h)
        self.intercom_flyout.raise_()

    def _on_status_bar_message(self, message: str):
        """Routes transient status bar messages to the slim bottom status label."""
        if message:
            self.lbl_active_info.setText(message)
        else:
            sel_idx = getattr(self, "selected_tile_idx", 0)
            self.lbl_active_info.setText(f"System Active | Slot #{sel_idx + 1}")

    def _on_sidebar_resized(self, event=None):
        if not hasattr(self, "sidebar"):
            return
        w = self.sidebar.width()
        compact = (w < 280)
        if compact != getattr(self, "_sidebar_compact_mode", None):
            self._sidebar_compact_mode = compact
            if hasattr(self, "btn_add_cam"):
                self.btn_add_cam.setText("" if compact else " Add")
            if hasattr(self, "btn_scan"):
                self.btn_scan.setText("" if compact else " Scan")
            if hasattr(self, "btn_stream_all"):
                self.btn_stream_all.setText("" if compact else " Stream All")
            if hasattr(self, "btn_retention_clean"):
                self.btn_retention_clean.setText("" if compact else " Clean 30d")
            if hasattr(self, "btn_clips_gallery"):
                self.btn_clips_gallery.setText("" if compact else " Video Clips")
            if hasattr(self, "btn_clear_alerts"):
                self.btn_clear_alerts.setText("" if compact else " Clear All")

    def _on_splitter_moved(self, pos: int, index: int):
        sizes = self.splitter.sizes()
        if not hasattr(self, "sidebar") or not sizes:
            return
        sidebar_idx = self.splitter.indexOf(self.sidebar)
        if sidebar_idx >= len(sizes):
            return
        side_w = sizes[sidebar_idx]
        total_w = sum(sizes) if sum(sizes) > 0 else max(800, self.width())

        # Auto-hide threshold: when resized below ~17% (approx 15% like user requested)
        collapse_threshold = max(200, int(total_w * 0.17))

        if side_w <= collapse_threshold:
            # User resized to <= 15-17%: automatically snap-hide sidebar!
            if getattr(self, "is_sidebar_visible", True):
                self.is_sidebar_visible = False
                self.sidebar.hide()
                if sidebar_idx == 0:
                    self.splitter.setSizes([0, total_w])
                else:
                    self.splitter.setSizes([total_w, 0])
                if hasattr(self, "btn_toggle_sidebar"):
                    self.btn_toggle_sidebar.setChecked(False)
                if hasattr(self, "btn_trigger_settings"):
                    self.btn_trigger_settings.setChecked(False)
                self.app_settings["sidebar_visible"] = False
                self.device_manager.config["app_settings"] = self.app_settings
        else:
            if not getattr(self, "is_sidebar_visible", True) and side_w > collapse_threshold + 40:
                self.is_sidebar_visible = True
                self.sidebar.show()
                if hasattr(self, "btn_toggle_sidebar"):
                    self.btn_toggle_sidebar.setChecked(True)
                self.app_settings["sidebar_visible"] = True
            if side_w >= 280:
                self.app_settings["sidebar_width"] = side_w
                self.device_manager.config["app_settings"] = self.app_settings

    def _populate_camera_tree(self):
        self.cam_tree.clear()
        cameras = self.device_manager.get_cameras()

        for cam in cameras:
            cam_name = cam.get("name", "Camera")
            is_dual = cam.get("is_dual_lens", False)
            ip = cam.get("ip", "")

            cam_item = QTreeWidgetItem(self.cam_tree)
            cam_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "camera", "data": cam})
            cam_item.setSizeHint(0, QSize(0, 46))
            cam_item.setExpanded(True)

            is_online = any(
                w.isRunning() and w.status == "LIVE"
                for w in self.active_workers.values()
                if getattr(w, "camera_id", None) == cam.get("id")
            )
            hdr_card = CameraHeaderCardWidget(cam, is_online=is_online, parent=self.cam_tree)
            hdr_card.play_all_requested.connect(self.add_camera_to_grid)
            hdr_card.menu_requested.connect(lambda c_data, pos: self._on_camera_card_menu(c_data, pos))
            self.cam_tree.setItemWidget(cam_item, 0, hdr_card)

            streams = cam.get("streams", [])
            for s in streams:
                s_item = QTreeWidgetItem(cam_item)
                s_data = dict(s)
                s_data["camera_id"] = cam.get("id")
                s_data["camera_name"] = cam_name
                s_data["camera_ip"] = ip
                s_data["display_title"] = f"{cam_name} - {s.get('name')}"
                s_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "stream", "data": s_data})
                s_item.setSizeHint(0, QSize(0, 36))

                row_card = StreamRowCardWidget(s_data, parent=self.cam_tree)
                row_card.stream_requested.connect(lambda d: self.assign_stream_smart(d))
                row_card.rename_requested.connect(lambda d: self.prompt_rename_lens(d.get("id")))
                row_card.menu_requested.connect(lambda d, pos: self._on_stream_card_menu(d, pos))
                self.cam_tree.setItemWidget(s_item, 0, row_card)

        if hasattr(self, "side_tabs"):
            self.side_tabs.setTabText(0, f"Cameras ({len(cameras)})")

        if hasattr(self, "ptz_dock") and self.ptz_dock is not None:
            self.ptz_dock.populate_cameras(cameras)
        if hasattr(self, "intercom_dock") and self.intercom_dock is not None:
            self.intercom_dock.populate_cameras(cameras)

        self._update_sidebar_telemetry()

    def _on_camera_card_menu(self, cam_data: dict, pos: QPoint):
        """Displays modern contextual actions when clicking menu on a camera card."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #f1f5f9;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 20px 6px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: #1e293b;
                margin: 4px 6px;
            }
        """)
        act_add_all = menu.addAction(create_topbar_icon("stream", size=15, custom_color="#38bdf8"), "Stream Camera to Grid (Empty Slot(s))")
        act_add_all.triggered.connect(lambda: self.add_camera_to_grid(cam_data))

        if cam_data.get("is_dual_lens"):
            act_dual_side = menu.addAction(create_topbar_icon("dual_lens", size=15, custom_color="#38bdf8"), "Stream Both Lenses Side-by-Side (2-Split)")
            act_dual_side.triggered.connect(self.activate_dual_lens_mode)

        act_indiv = menu.addAction(create_topbar_icon("settings", size=15, custom_color="#38bdf8"), "Camera Settings & Night Vision")
        act_indiv.triggered.connect(lambda: self.open_settings_dialog(selected_camera_id=cam_data.get("id")))

        act_rename = menu.addAction(create_topbar_icon("edit", size=15, custom_color="#94a3b8"), "Rename Camera...")
        act_rename.triggered.connect(lambda: self.prompt_rename_camera(cam_data.get("id")))

        streams = cam_data.get("streams", [])
        if streams:
            sub_rename = menu.addMenu("Rename Lens")
            sub_rename.setIcon(create_topbar_icon("rename", size=15, custom_color="#94a3b8"))
            for s in streams:
                s_id = s.get("id")
                s_name = s.get("name", "Lens")
                act_lens_r = sub_rename.addAction(create_topbar_icon("rename", size=14, custom_color="#94a3b8"), s_name)
                act_lens_r.triggered.connect(lambda ch, sid=s_id: self.prompt_rename_lens(sid))

        menu.addSeparator()

        act_edit = menu.addAction(create_topbar_icon("manage", size=15, custom_color="#94a3b8"), "Edit Connection Parameters (Credentials & Port)")
        act_edit.triggered.connect(lambda: self._edit_camera(cam_data))

        act_del = menu.addAction(create_topbar_icon("trash", size=15, custom_color="#ef4444"), "Remove Camera")
        act_del.triggered.connect(lambda: self._delete_camera(cam_data))

        menu.exec(pos)

    def _on_stream_card_menu(self, s_data: dict, pos: QPoint):
        """Displays modern contextual actions when clicking or right-clicking a stream/lens card."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #1e293b; border: 1px solid #334155; color: #f1f5f9; padding: 4px; }
            QMenu::item:selected { background-color: #0284c7; }
        """)
        act_smart = menu.addAction("Stream to Grid (Empty Slot)")
        act_smart.triggered.connect(lambda: self.assign_stream_smart(s_data))

        act_play = menu.addAction(f"Stream in Selected Slot (#{self.selected_tile_idx + 1})")
        act_play.triggered.connect(lambda: self.start_stream_on_tile(self.selected_tile_idx, s_data))

        menu.addSeparator()

        act_rename_lens = menu.addAction("Rename Lens...")
        act_rename_lens.triggered.connect(lambda: self.prompt_rename_lens(s_data.get("id")))

        act_rename_cam = menu.addAction("Rename Camera...")
        act_rename_cam.triggered.connect(lambda: self.prompt_rename_camera(s_data.get("camera_id")))

        act_indiv = menu.addAction("Camera Settings & Night Vision")
        act_indiv.triggered.connect(lambda: self.open_settings_dialog(selected_camera_id=s_data.get("camera_id")))

        menu.exec(pos)

    def _open_cctv_gdrive_folder(self):
        """Opens the recordings storage folder in Windows File Explorer."""
        folder = os.path.abspath(self.app_settings.get("recording_dir", "recordings"))
        if not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception:
                pass
        try:
            os.startfile(folder)
        except Exception as e:
            self.statusBar().showMessage(f"Cannot open folder: {e}", 3000)

    def _open_web_stream_in_browser(self):
        """Opens the mobile web stream hub in the default browser."""
        import webbrowser
        if hasattr(self, "web_server") and self.web_server:
            webbrowser.open(self.web_server.get_local_url())

    def _update_sidebar_telemetry(self):
        """Updates storage and system health HUD indicators in the sidebar."""
        if not hasattr(self, "lbl_sidebar_storage"):
            return
        storage_dir = os.path.abspath(self.app_settings.get("recording_dir", "recordings"))
        if len(storage_dir) > 22:
            disp_path = storage_dir[:10] + "..." + storage_dir[-10:]
        else:
            disp_path = storage_dir
        self.lbl_sidebar_storage.setText(disp_path)
        self.lbl_sidebar_storage.setToolTip(f"Full path: {storage_dir}")

        ai_tracking = self.app_settings.get("ai_auto_tracking", True)
        self.lbl_sidebar_ai.setText("YOLOv8 Real-Time Neural Net" if ai_tracking else "Motion Sensor")

        r_days = int(self.app_settings.get("retention_days", 30))
        self.lbl_sidebar_ret.setText("SYNC ACTIVE" if r_days > 0 else "PERMANENT")
        if hasattr(self, "lbl_sidebar_storage_sub"):
            self.lbl_sidebar_storage_sub.setText(f"Active storage • Auto retention {r_days} days" if r_days > 0 else "Active storage • Indefinite retention")

        if hasattr(self, "sidebar_footer") and self.sidebar_footer:
            self.sidebar_footer.lbl_drive.setText("Drive: " + ("Synced" if os.path.exists(storage_dir) else "Active"))
            self.sidebar_footer.lbl_ai.setText("YOLOv8" if ai_tracking else "Motion")
            if hasattr(self, "web_server") and self.web_server:
                self.sidebar_footer.lbl_web.setText(f":{self.web_server.port} Live")

        if hasattr(self, "sidebar_telemetry") and self.sidebar_telemetry:
            self.sidebar_telemetry.lbl_storage_path.setText(storage_dir)
            if hasattr(self, "web_server") and self.web_server:
                self.sidebar_telemetry.lbl_web_url.setText(self.web_server.get_local_url())

    def _check_startup_performance_mode(self):
        if not self.isVisible():
            return
        show_prompt = self.app_settings.get("show_performance_prompt_on_startup", True)
        rm = get_resource_manager()
        default_prof = PerformanceProfile.GAMER.value if rm.is_ryzen_dual_ccd else PerformanceProfile.MEDIUM.value
        curr_prof = self.app_settings.get("performance_profile", default_prof)

        if show_prompt:
            dlg = StartupPerformanceDialog(current_profile=curr_prof, remember_default=False, parent=self)
            if dlg.exec():
                chosen_profile = dlg.selected_profile
                remember = dlg.chk_remember.isChecked()

                self.apply_performance_profile(chosen_profile)

                if remember:
                    self.app_settings["show_performance_prompt_on_startup"] = False
                    self.app_settings["performance_profile"] = chosen_profile
                    self.device_manager.config["app_settings"] = self.app_settings
                    self.device_manager.save_config()
            else:
                self.apply_performance_profile(curr_prof)
        else:
            self.apply_performance_profile(curr_prof)

        # Launch 4 Quad startup view once performance profile is set
        self.activate_startup_view()

    def open_performance_dialog(self):
        """Opens the Performance & Hardware Telemetry dialog to switch profiles or adjust affinity."""
        curr_prof = self.app_settings.get("performance_profile", "medium")
        dlg = StartupPerformanceDialog(current_profile=curr_prof, remember_default=True, parent=self)
        if dlg.exec():
            chosen_profile = dlg.selected_profile
            remember = dlg.chk_remember.isChecked()
            self.apply_performance_profile(chosen_profile)
            if remember:
                self.app_settings["performance_profile"] = chosen_profile
                self.device_manager.config["app_settings"] = self.app_settings
                self.device_manager.save_config()

    def apply_performance_profile(self, profile_key: str):
        """Applies CPU core affinity, process priority, OpenCV threads, and worker throttles."""
        rm = get_resource_manager()
        eff = rm.apply_profile(profile_key, custom_settings=self.app_settings)

        self.app_settings["performance_profile"] = profile_key

        if hasattr(self, "cmb_perf_profile_bar"):
            idx = self.cmb_perf_profile_bar.findData(profile_key)
            if idx >= 0:
                self.cmb_perf_profile_bar.blockSignals(True)
                self.cmb_perf_profile_bar.setCurrentIndex(idx)
                self.cmb_perf_profile_bar.blockSignals(False)

        # Apply throttling settings to all active stream workers
        for worker in self.active_workers.values():
            worker.set_performance_throttling(
                display_fps_cap=eff.get("display_fps_cap", 15),
                ai_skip_frames=eff.get("ai_skip_frames", 6),
                ai_motion_gated_only=eff.get("ai_motion_gated_only", False),
                motion_skip_frames=eff.get("motion_skip_frames", 1),
                motion_downscale_width=eff.get("motion_downscale_width", 480)
            )

        self._update_cpu_monitor()
        self.statusBar().showMessage(f" Performance Profile: {eff.get('label', profile_key)} Active", 4000)

    def _on_topbar_perf_profile_changed(self, idx: int):
        p_key = self.cmb_perf_profile_bar.currentData()
        self.apply_performance_profile(p_key)
        self.app_settings["performance_profile"] = p_key
        self.device_manager.config["app_settings"] = self.app_settings
        self.device_manager.save_config()

    def _update_cpu_monitor(self):
        if not hasattr(self, "btn_cpu_monitor"):
            return
        rm = get_resource_manager()
        rec_dir = self.app_settings.get("recording_dir", "recordings")
        snap = rm.get_hardware_telemetry_snapshot(rec_dir)

        # Periodic working set memory trim every 30 seconds to reclaim unreferenced RAM
        now_ts = time.time()
        if (now_ts - getattr(self, "_last_memory_trim_time", 0.0)) >= 30.0:
            self._last_memory_trim_time = now_ts
            rm.trim_memory()

        c = snap["cpu"]
        r = snap["ram"]
        g = snap["gpu"]
        s = snap["storage"]

        w = self.width() if hasattr(self, "width") else 1600
        if w >= 1550:
            self.btn_cpu_monitor.setText(f" {c['app_pct']:.0f}% CPU")
        elif w >= 980:
            self.btn_cpu_monitor.setText(f" {c['app_pct']:.0f}%")
        else:
            self.btn_cpu_monitor.setText("")

        # Live GPU line
        if g.get("available", False):
            gpu_desc = (
                f"- GPU: {g['name']}\n"
                f"  3D Graphics Load: {g['util_pct']:.0f}%\n"
                f"  Dedicated VRAM: {g['vram_used_mb']:,.0f} MB / {g['vram_total_mb']:,.0f} MB ({g['vram_pct']:.1f}%)"
            )
        else:
            gpu_desc = f"- GPU: {g.get('name', 'Standard / Integrated GPU')}"

        tooltip_text = (
            f" SYSTEM HARDWARE & TELEMETRY BREAKDOWN\n\n"
            f"- CPU: {c['model']} ({c['total_cores']} Logical Cores)\n"
            f"  Total Windows System CPU: {c['sys_pct']:.1f}%\n"
            f"  CCTVPanelView Footprint: {c['app_pct']:.1f}% ({c['core_equiv_pct']:.1f}% of 1 Core)\n"
            f"  Helper Tasks (FFmpeg/FFplay): {c['child_pct']:.1f}%\n"
            f"  Other System Processes: {c['other_pct']:.1f}%\n\n"
            f"- RAM (System Memory):\n"
            f"  CCTVPanelView Footprint: {r['app_mb']:,.1f} MB ({r['app_sys_pct']:.1f}% of System)\n"
            f"  Total Windows System RAM: {r['sys_used_gb']:.1f} GB / {r['sys_total_gb']:.1f} GB ({r['sys_pct']:.1f}%)\n\n"
            f"{gpu_desc}\n\n"
            f"- STORAGE (Drive {s['drive']}):\n"
            f"  Storage & App Drive: {s['free_gb']:,.1f} GB Free / {s['total_gb']:,.1f} GB ({s['used_pct']:.1f}% Used)\n\n"
            f"- PROCESS AFFINITY & GAMING SHIELD:\n"
            f"  Core Affinity: {c['affinity_label']}\n"
            f"  Gaming Shield (CCD0): {'ACTIVE (CCTV isolated on Chiplet 2)' if c['is_chiplet2_isolated'] else 'Off (All Cores)'}\n\n"
            f" Click to open Performance & CPU Settings"
        )
        self.btn_cpu_monitor.setToolTip(tooltip_text)

        proc_cpu = c['app_pct']
        if proc_cpu < 15.0:
            border_col = "rgba(56, 189, 248, 0.45)"
            text_col = "#38bdf8"
        elif proc_cpu < 50.0:
            border_col = "#0284c7"
            text_col = "#38bdf8"
        else:
            border_col = "#ef4444"
            text_col = "#f87171"

        self.btn_cpu_monitor.setIcon(create_topbar_icon("cpu", size=15, custom_color=text_col))
        self.btn_cpu_monitor.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(15, 23, 42, 0.92), stop:1 rgba(7, 11, 20, 0.98));
                color: {text_col};
                border: 1px solid {border_col};
                border-radius: 14px;
                padding: 2px 8px;
                min-height: 26px;
                max-height: 26px;
                font-weight: 700;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(56, 189, 248, 0.20);
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 14px;
            }}
            QPushButton:pressed {{
                background-color: rgba(56, 189, 248, 0.32);
                border-radius: 14px;
            }}
        """)

    def save_session_state(self):
        """
        Persists full session state to configuration:
        - Active grid layout key
        - Exact camera stream ID assigned to each individual visible grid slot
        """
        if getattr(self, "_restoring_session", False):
            return
        if not hasattr(self, "app_settings") or self.app_settings is None:
            return

        layout_key = getattr(self, "current_layout", "2x2")
        self.app_settings["default_layout"] = layout_key

        # Keep hidden tile assignments too, so shrinking the grid is reversible.
        slot_map = {str(idx): (getattr(tile, "stream_id", None) or "")
                    for idx, tile in enumerate(self.video_tiles)}
        rect = self.normalGeometry() if self.isMaximized() or self.isFullScreen() else self.geometry()
        self.app_settings["window_rect"] = [rect.x(), rect.y(), rect.width(), rect.height()]
        self.app_settings["window_maximized"] = self.isMaximized()
        self.app_settings["sidebar_visible"] = self.is_sidebar_visible
        sizes = self.splitter.sizes()
        sidebar_idx = self.splitter.indexOf(self.sidebar)
        if 0 <= sidebar_idx < len(sizes) and sizes[sidebar_idx] > 0:
            self.app_settings["sidebar_width"] = sizes[sidebar_idx]
        self.app_settings["selected_tile"] = self.selected_tile_idx

        self.app_settings["session_slot_assignments"] = slot_map
        if hasattr(self, "device_manager") and self.device_manager:
            self.device_manager.config["app_settings"] = self.app_settings
            self.device_manager.save_config()

    def restore_window_state(self):
        rect = self.app_settings.get("window_rect")
        if isinstance(rect, list) and len(rect) == 4:
            try:
                x, y, w, h = [int(v) for v in rect]
                screen = QApplication.screenAt(QPoint(x + w // 2, y + h // 2)) or QApplication.primaryScreen()
                area = screen.availableGeometry()
                w, h = min(max(960, w), area.width()), min(max(600, h), area.height())
                self.setGeometry(max(area.left(), min(x, area.right() - w + 1)),
                                 max(area.top(), min(y, area.bottom() - h + 1)), w, h)
            except (ValueError, TypeError):
                pass
        if self.app_settings.get("window_maximized", False):
            self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    def activate_startup_view(self):
        """
        Restores full session state on startup:
        - Restores the last active grid layout
        - Restores the exact camera stream assigned to each individual slot
        - Auto-fills remaining visible slots with unassigned streams (e.g. wide lens on dual-lens cameras)
        """
        saved_selection = self.app_settings.get("selected_tile", 0)
        self._restoring_session = True
        try:
            if "default_layout" in self.app_settings:
                layout_key = self.app_settings["default_layout"]
            else:
                cams = self.device_manager.get_cameras()
                if len(cams) == 1 and (cams[0].get("is_dual_lens") or len(cams[0].get("streams", [])) == 2):
                    layout_key = "2x1"
                else:
                    layout_key = "2x2"

            self.set_grid_layout(layout_key)

            all_streams = self.device_manager.get_all_streams()
            if not all_streams:
                return

            layout_slot_map = {"1x1": 1, "2x1": 2, "1x2": 2, "2x2": 4, "1+5": 6, "3x3": 9, "4x4": 16}
            if layout_key == "custom":
                cfg = self.app_settings.get("custom_layout", {})
                num_slots = len(cfg.get("slots", [])) or 4
            else:
                num_slots = layout_slot_map.get(layout_key, 4)

            saved_assignments = self.app_settings.get("session_slot_assignments", {})
            stream_by_id = {s.get("id"): s for s in all_streams if s.get("id")}

            restored_count = 0
            if isinstance(saved_assignments, dict) and saved_assignments:
                for slot_idx in range(min(len(self.video_tiles), 16)):
                    s_id = saved_assignments.get(str(slot_idx), "")
                    if s_id in stream_by_id:
                        self.start_stream_on_tile(slot_idx, stream_by_id[s_id])
                        restored_count += 1
            elif "session_slot_assignments" not in self.app_settings:
                # Only a first run gets automatic assignments. Explicit blanks stay blank.
                for idx, stream in enumerate(all_streams[:num_slots]):
                    self.start_stream_on_tile(idx, stream)
                    restored_count += 1
        finally:
            self._restoring_session = False
            self.save_session_state()

        self._on_tile_selected(min(max(0, int(saved_selection)), num_slots - 1))
        self.statusBar().showMessage(f"Session restored ({layout_key}) - {restored_count} live cameras active", 5000)

    def activate_dual_lens_mode(self):
        """
        Specialized 1-click launcher for the user's JA-A12 Dual Lens camera (Fata).
        Sets layout to 2x1 (Side-by-Side) and starts both Lens 1 and Lens 2 concurrently!
        """
        self.set_grid_layout("2x1")
        cameras = self.device_manager.get_cameras()
        dual_cam = next((c for c in cameras if c.get("is_dual_lens")), None)

        if not dual_cam and cameras:
            dual_cam = cameras[0]

        if not dual_cam:
            return

        streams = dual_cam.get("streams", [])
        if len(streams) >= 1:
            s1 = dict(streams[0])
            s1["camera_id"] = dual_cam.get("id")
            s1["camera_name"] = dual_cam.get("name")
            s1["camera_ip"] = dual_cam.get("ip")
            s1["display_title"] = f"{dual_cam.get('name')} - {s1.get('name')}"
            self.start_stream_on_tile(0, s1)

        if len(streams) >= 2:
            s2 = dict(streams[1])
            s2["camera_id"] = dual_cam.get("id")
            s2["camera_name"] = dual_cam.get("name")
            s2["camera_ip"] = dual_cam.get("ip")
            s2["display_title"] = f"{dual_cam.get('name')} - {s2.get('name')}"
            self.start_stream_on_tile(1, s2)

        self._on_tile_selected(0)
        self.save_session_state()
        self.statusBar().showMessage("Dual-Lens Mode: PTZ Zoom + Wide Overview streaming concurrently!", 5000)

    def stream_all_cameras(self):
        """Streams all configured cameras in a quad or 9-grid view."""
        all_streams = self.device_manager.get_all_streams()
        if not all_streams:
            return

        count = len(all_streams)
        if count <= 2:
            self.set_grid_layout("2x1")
        elif count <= 4:
            self.set_grid_layout("2x2")
        elif count <= 9:
            self.set_grid_layout("3x3")
        else:
            self.set_grid_layout("4x4")

        for idx, s in enumerate(all_streams[:len(self.video_tiles)]):
            self.start_stream_on_tile(idx, s)

        self.save_session_state()
        self.statusBar().showMessage(f"Streaming {min(count, 16)} feeds simultaneously!", 4000)

    def set_grid_layout(self, layout_key: str):
        self.current_layout = layout_key
        for k, btn in self.layout_btns.items():
            btn.setChecked(k == layout_key)

        if hasattr(self, "btn_dual_hero"):
            self.btn_dual_hero.setChecked(layout_key == "2x1")

        # Persist last chosen grid layout for next application startup
        if layout_key in ["1x1", "2x1", "1x2", "2x2", "1+5", "3x3", "4x4", "custom"]:
            if hasattr(self, "app_settings") and self.app_settings is not None:
                self.app_settings["default_layout"] = layout_key

        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item.widget():
                item.widget().hide()
                self.grid_layout.removeWidget(item.widget())

        # Reset previous row and column stretches to prevent residual layout bias
        for r in range(6):
            self.grid_layout.setRowStretch(r, 0)
        for c in range(6):
            self.grid_layout.setColumnStretch(c, 0)

        if layout_key == "1x1":
            visible_count = 1
            self.grid_layout.addWidget(self.video_tiles[0], 0, 0)
            self.grid_layout.setRowStretch(0, 1)
            self.grid_layout.setColumnStretch(0, 1)
            self.video_tiles[0].show()

        elif layout_key == "2x1":  # Dual-lens side-by-side
            visible_count = 2
            self.grid_layout.addWidget(self.video_tiles[0], 0, 0)
            self.grid_layout.addWidget(self.video_tiles[1], 0, 1)
            self.grid_layout.setRowStretch(0, 1)
            self.grid_layout.setColumnStretch(0, 1)
            self.grid_layout.setColumnStretch(1, 1)
            self.video_tiles[0].show()
            self.video_tiles[1].show()

        elif layout_key == "1x2":  # Dual-lens stacked
            visible_count = 2
            self.grid_layout.addWidget(self.video_tiles[0], 0, 0)
            self.grid_layout.addWidget(self.video_tiles[1], 1, 0)
            self.grid_layout.setRowStretch(0, 1)
            self.grid_layout.setRowStretch(1, 1)
            self.grid_layout.setColumnStretch(0, 1)
            self.video_tiles[0].show()
            self.video_tiles[1].show()

        elif layout_key == "2x2":  # 4 quad
            visible_count = 4
            for idx in range(4):
                r = idx // 2
                c = idx % 2
                self.grid_layout.addWidget(self.video_tiles[idx], r, c)
                self.video_tiles[idx].show()
            for r in range(2):
                self.grid_layout.setRowStretch(r, 1)
            for c in range(2):
                self.grid_layout.setColumnStretch(c, 1)

        elif layout_key == "1+5":  # 1 hero + 5 sub
            visible_count = 6
            self.grid_layout.addWidget(self.video_tiles[0], 0, 0, 2, 2)
            self.video_tiles[0].show()
            positions = [(0, 2), (1, 2), (2, 0), (2, 1), (2, 2)]
            for i, (r, c) in enumerate(positions):
                self.grid_layout.addWidget(self.video_tiles[i + 1], r, c)
                self.video_tiles[i + 1].show()
            for r in range(3):
                self.grid_layout.setRowStretch(r, 1)
            for c in range(3):
                self.grid_layout.setColumnStretch(c, 1)

        elif layout_key == "3x3":  # 9 split
            visible_count = 9
            for idx in range(9):
                r = idx // 3
                c = idx % 3
                self.grid_layout.addWidget(self.video_tiles[idx], r, c)
                self.video_tiles[idx].show()
            for r in range(3):
                self.grid_layout.setRowStretch(r, 1)
            for c in range(3):
                self.grid_layout.setColumnStretch(c, 1)

        elif layout_key == "4x4":  # 16 grid
            visible_count = 16
            for idx in range(16):
                r = idx // 4
                c = idx % 4
                self.grid_layout.addWidget(self.video_tiles[idx], r, c)
                self.video_tiles[idx].show()
            for r in range(4):
                self.grid_layout.setRowStretch(r, 1)
            for c in range(4):
                self.grid_layout.setColumnStretch(c, 1)

        elif layout_key == "custom":
            visible_count = self.apply_custom_layout()

        else:
            visible_count = 1
            self.grid_layout.addWidget(self.video_tiles[0], 0, 0)
            self.grid_layout.setRowStretch(0, 1)
            self.grid_layout.setColumnStretch(0, 1)
            self.video_tiles[0].show()

        use_substream = self.app_settings.get("grid_substream", True) and visible_count > 1
        for i, tile in enumerate(self.video_tiles):
            if i < visible_count:
                tile.show()
                if tile.worker:
                    tile.worker.set_gui_rendering_paused(False)
                    tile.worker.set_solo_view(visible_count == 1)
                    if use_substream:
                        tile.worker.set_quality(QualityMode.LOW_SD)
                    elif visible_count == 1:
                        tile.worker.set_quality(self.global_quality)
            else:
                tile.hide()
                if tile.worker:
                    tile.worker.set_gui_rendering_paused(True)

        if self.selected_tile_idx >= visible_count:
            self._on_tile_selected(0)

        if not getattr(self, "_restoring_session", False):
            self.save_session_state()

    def _show_custom_layout_context_menu(self, pos):
        btn = self.layout_btns.get("custom")
        if not btn:
            return
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
        """)
        act_edit = menu.addAction("Configure Custom Layout Studio...")
        act_edit.triggered.connect(self.open_custom_layout_dialog)

        cfg = self.app_settings.get("custom_layout")
        if cfg and cfg.get("slots"):
            tmpl = cfg.get("template_name", "Custom")
            act_apply = menu.addAction(f"Reapply '{tmpl}' Layout")
            act_apply.triggered.connect(lambda: self.set_grid_layout("custom"))

        menu.exec(btn.mapToGlobal(pos))

    def _on_layout_btn_clicked(self, key: str):
        if key == "custom":
            cfg = self.app_settings.get("custom_layout")
            # If no layout configured or already in custom mode, open the layout designer
            if not cfg or not cfg.get("slots") or self.current_layout == "custom":
                self.open_custom_layout_dialog()
            else:
                self.set_grid_layout("custom")
        else:
            self.set_grid_layout(key)

    def open_custom_layout_dialog(self):
        """Opens Custom Camera Layout Studio dialog to design tailored multiview grid."""
        all_streams = self.device_manager.get_all_streams()
        saved_custom = self.app_settings.get("custom_layout", {})
        dlg = CustomLayoutDialog(all_streams, current_config=saved_custom, parent=self)
        dlg.layout_applied.connect(self._on_custom_layout_applied)
        res = dlg.exec()
        if res != QDialog.DialogCode.Accepted:
            # Restore checked button state if dialog was dismissed without applying
            for k, btn in self.layout_btns.items():
                btn.setChecked(k == self.current_layout)

    def _on_custom_layout_applied(self, layout_config: dict):
        self.app_settings["custom_layout"] = layout_config
        self.device_manager.config["app_settings"] = self.app_settings
        self.device_manager.save_config()
        self.set_grid_layout("custom")

    def apply_custom_layout(self) -> int:
        """Positions video tiles according to saved custom layout and binds camera streams cleanly."""
        cfg = self.app_settings.get("custom_layout")
        if not cfg or not cfg.get("slots"):
            cfg = {
                "template_name": "2x2 Quad",
                "rows": 2, "cols": 2,
                "slots": [
                    {"slot": 0, "r": 0, "c": 0, "rspan": 1, "cspan": 1},
                    {"slot": 1, "r": 0, "c": 1, "rspan": 1, "cspan": 1},
                    {"slot": 2, "r": 1, "c": 0, "rspan": 1, "cspan": 1},
                    {"slot": 3, "r": 1, "c": 1, "rspan": 1, "cspan": 1},
                ],
                "assignments": []
            }
            self.app_settings["custom_layout"] = cfg

        slots = cfg.get("slots", [])
        assignments = cfg.get("assignments", [])
        num_rows = max(1, cfg.get("rows", 2))
        num_cols = max(1, cfg.get("cols", 2))
        num_slots = len(slots)

        # 1. Reset row and column stretch factors
        for r in range(24):
            self.grid_layout.setRowStretch(r, 0)
        for c in range(24):
            self.grid_layout.setColumnStretch(c, 0)

        # 2. Map target assignments
        target_assignments = {}
        for s_idx in range(num_slots):
            if s_idx < len(assignments) and assignments[s_idx]:
                target_assignments[s_idx] = assignments[s_idx]
            else:
                target_assignments[s_idx] = None

        # 3. Cleanly detach streams that don't belong on tiles or are being moved, and hide unused tiles
        for idx, tile in enumerate(self.video_tiles):
            if idx >= num_slots:
                if tile.stream_info:
                    old_id = tile.stream_id
                    tile.detach_stream()
                    self._cleanup_worker_if_unused(old_id)
                tile.hide()
            else:
                expected_sid = target_assignments.get(idx)
                if tile.stream_info and tile.stream_info.get("id") != expected_sid:
                    old_id = tile.stream_id
                    tile.detach_stream()
                    self._cleanup_worker_if_unused(old_id)

        # 4. Position tiles into grid layout
        for s_idx, slot in enumerate(slots):
            if s_idx >= len(self.video_tiles):
                break
            tile = self.video_tiles[s_idx]
            r = slot.get("r", 0)
            c = slot.get("c", 0)
            rspan = max(1, slot.get("rspan", 1))
            cspan = max(1, slot.get("cspan", 1))

            self.grid_layout.addWidget(tile, r, c, rspan, cspan)
            tile.show()

            # Start assigned camera stream if configured
            s_id = target_assignments.get(s_idx)
            if s_id:
                stream_obj = self.device_manager.get_stream_by_id(s_id)
                if stream_obj:
                    if not tile.stream_info or tile.stream_info.get("id") != s_id:
                        self.start_stream_on_tile(s_idx, stream_obj)

        # 5. Apply row and column stretches
        for r in range(num_rows):
            self.grid_layout.setRowStretch(r, 1)
        for c in range(num_cols):
            self.grid_layout.setColumnStretch(c, 1)

        tmpl_name = cfg.get("template_name", "Custom")
        if hasattr(self, "lbl_status_msg") and self.lbl_status_msg:
            self.lbl_status_msg.setText(f"Custom layout '{tmpl_name}' active ({num_slots} windows configured)")
        return num_slots

    def _prompt_unconfigured_camera(self, stream_or_cam: dict, target_tile_idx: Optional[int] = None) -> bool:
        """
        Validates whether a camera is configured. If unconfigured, displays an Obsidian Glass
        prompt modal offering 1-click navigation to Camera Settings.
        Returns True if configured and safe to stream, False otherwise.
        """
        if getattr(self, "_in_prompt_unconfigured", False):
            return False

        if not stream_or_cam:
            return False

        cam = None
        if "streams" in stream_or_cam and "ip" in stream_or_cam:
            cam = stream_or_cam
        else:
            cam_id = stream_or_cam.get("camera_id")
            if cam_id:
                cam = self.device_manager.get_camera_by_id(cam_id)
            if not cam and "id" in stream_or_cam:
                sid = stream_or_cam.get("id")
                for c in self.device_manager.get_cameras():
                    for s in c.get("streams", []):
                        if s.get("id") == sid:
                            cam = c
                            break
            if not cam:
                target_ip = stream_or_cam.get("camera_ip") or stream_or_cam.get("ip")
                if target_ip:
                    for c in self.device_manager.get_cameras():
                        if c.get("ip") == target_ip:
                            cam = c
                            break

        if not cam:
            url = stream_or_cam.get("url", "")
            return bool(url and url.startswith(("rtsp://", "rtsps://")))

        if hasattr(self.device_manager, "is_camera_configured") and self.device_manager.is_camera_configured(cam):
            return True

        # Restore configured streams, but never open setup modals during startup.
        if getattr(self, "_restoring_session", False):
            return False

        self._in_prompt_unconfigured = True
        try:
            cname = cam.get("name") or cam.get("id") or "Camera"
            dlg = CameraSetupPromptDialog(camera_name=cname, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                target_cid = cam.get("id")
                self.open_settings_dialog(selected_camera_id=target_cid)

                refreshed_cam = self.device_manager.get_camera_by_id(target_cid)
                if refreshed_cam and self.device_manager.is_camera_configured(refreshed_cam):
                    streams = refreshed_cam.get("streams", [])
                    if streams:
                        target_stream = None
                        orig_sid = stream_or_cam.get("id")
                        for s in streams:
                            if s.get("id") == orig_sid:
                                target_stream = s
                                break
                        if not target_stream:
                            target_stream = streams[0]

                        s_info = dict(target_stream)
                        s_info["camera_id"] = refreshed_cam.get("id")
                        s_info["camera_name"] = refreshed_cam.get("name")
                        s_info["camera_ip"] = refreshed_cam.get("ip")

                        # Setup has completed. The subsequent assignment must pass the guard.
                        self._in_prompt_unconfigured = False

                        if target_tile_idx is not None:
                            self.start_stream_on_tile(target_tile_idx, s_info)
                        else:
                            self.assign_stream_smart(s_info)
                else:
                    self.statusBar().showMessage(f"Camera '{cname}' remains unconfigured.", 3000)
                return False
            else:
                self.statusBar().showMessage("Camera setup postponed.", 2500)
                return False
        finally:
            self._in_prompt_unconfigured = False

    def assign_stream_smart(self, stream_info: dict, target_tile_idx: int = None) -> Optional[int]:
        """
        Intelligently routes a stream to an empty / non-existent slot without clobbering existing feeds.
        If all visible slots are occupied, expands the grid layout to reveal new empty slots.
        Returns the tile index where the stream was started, or None.
        """
        stream_id = stream_info.get("id")
        if not stream_id:
            return None

        if not self._prompt_unconfigured_camera(stream_info, target_tile_idx):
            return None

        # 1. Target tile explicitly specified (e.g. drag & drop onto specific slot)
        if target_tile_idx is not None and 0 <= target_tile_idx < len(self.video_tiles):
            if self.video_tiles[target_tile_idx].isHidden():
                self._ensure_tile_visible(target_tile_idx)
            self.start_stream_on_tile(target_tile_idx, stream_info)
            self._on_tile_selected(target_tile_idx)
            return target_tile_idx

        # 2. Check if this stream is ALREADY playing on any visible tile
        for tile in self.video_tiles:
            if not tile.isHidden() and tile.stream_id == stream_id:
                self._on_tile_selected(tile.tile_index)
                title = stream_info.get("display_title", stream_id)
                self.statusBar().showMessage(
                    f"Camera '{title}' is already active on Slot #{tile.tile_index + 1}",
                    3000
                )
                return tile.tile_index

        # 3. Check if currently selected tile is visible and empty
        selected_tile = self.video_tiles[self.selected_tile_idx]
        if not selected_tile.isHidden() and not selected_tile.stream_id:
            self.start_stream_on_tile(self.selected_tile_idx, stream_info)
            self._on_tile_selected(self.selected_tile_idx)
            return self.selected_tile_idx

        # 4. Search for the first empty visible tile in the current layout
        visible_tiles = [t for t in self.video_tiles if not t.isHidden()]
        empty_tile = next((t for t in visible_tiles if not t.stream_id), None)
        if empty_tile is not None:
            self.start_stream_on_tile(empty_tile.tile_index, stream_info)
            self._on_tile_selected(empty_tile.tile_index)
            return empty_tile.tile_index

        # 5. All visible slots are occupied! Expand grid layout to make room.
        if self._expand_grid_layout():
            visible_tiles = [t for t in self.video_tiles if not t.isHidden()]
            empty_tile = next((t for t in visible_tiles if not t.stream_id), None)
            if empty_tile is not None:
                self.start_stream_on_tile(empty_tile.tile_index, stream_info)
                self._on_tile_selected(empty_tile.tile_index)
                return empty_tile.tile_index

        # 6. Fallback if all 16 slots are completely occupied
        QMessageBox.warning(
            self,
            "Grid Full",
            "All 16 video slots are currently in use!\nPlease close a feed or choose a slot to replace."
        )
        return None

    def _expand_grid_layout(self) -> bool:
        """
        Expands the current grid layout to the next size up to make room for more cameras.
        Progression: 1x1 -> 2x1 -> 2x2 -> 3x3 -> 4x4
        """
        progression = ["1x1", "2x1", "2x2", "3x3", "4x4"]
        current = self.current_layout
        if current == "1x2":
            next_layout = "2x2"
        elif current == "1+5":
            next_layout = "3x3"
        elif current in progression:
            curr_idx = progression.index(current)
            if curr_idx + 1 < len(progression):
                next_layout = progression[curr_idx + 1]
            else:
                return False  # Already at max 4x4
        else:
            next_layout = "2x2"

        self.set_grid_layout(next_layout)
        return True

    def _ensure_tile_visible(self, tile_index: int):
        """Ensures that the requested tile index is visible by expanding layout if needed."""
        if tile_index < 1:
            return
        elif tile_index < 2:
            if self.current_layout == "1x1":
                self.set_grid_layout("2x1")
        elif tile_index < 4:
            if self.current_layout in ["1x1", "2x1", "1x2"]:
                self.set_grid_layout("2x2")
        elif tile_index < 6:
            if self.current_layout in ["1x1", "2x1", "1x2", "2x2"]:
                self.set_grid_layout("1+5")
        elif tile_index < 9:
            if self.current_layout in ["1x1", "2x1", "1x2", "2x2", "1+5"]:
                self.set_grid_layout("3x3")
        else:
            self.set_grid_layout("4x4")

    def add_camera_to_grid(self, cam_data: dict) -> list:
        """
        Adds all streams of a camera to non-existent / empty slots in the grid.
        Expands grid layout automatically if needed so NO existing feeds are clobbered!
        Returns a list of tile indices where the streams were placed.
        """
        if not cam_data:
            return []

        if not self._prompt_unconfigured_camera(cam_data, None):
            return []

        streams = cam_data.get("streams", [])
        if not streams:
            return []

        cam_name = cam_data.get("name", "Camera")
        cam_id = cam_data.get("id")
        cam_ip = cam_data.get("ip")
        is_dual = cam_data.get("is_dual_lens", False)

        assigned_indices = []
        for s in streams:
            s_data = dict(s)
            s_data["camera_id"] = cam_id
            s_data["camera_name"] = cam_name
            s_data["camera_ip"] = cam_ip
            s_data["is_dual_lens"] = is_dual
            s_data["display_title"] = f"{cam_name} - {s.get('name', 'Stream')}"

            idx = self.assign_stream_smart(s_data)
            if idx is not None:
                assigned_indices.append(idx)

        if assigned_indices:
            slots_str = ", ".join(f"#{i + 1}" for i in assigned_indices)
            self.statusBar().showMessage(
                f"Camera '{cam_name}' streaming in Slot(s): {slots_str}",
                5000
            )
        return assigned_indices

    def _stream_selected_tree_item(self):
        """Streams the currently highlighted camera or stream from the tree into empty grid slot(s)."""
        item = self.cam_tree.currentItem()
        if not item:
            cameras = self.device_manager.get_cameras()
            if cameras:
                self.add_camera_to_grid(cameras[0])
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data.get("type") == "stream":
            self.assign_stream_smart(data.get("data"))
        elif data.get("type") == "camera":
            self.add_camera_to_grid(data.get("data"))

    def start_stream_on_tile(self, tile_index: int, stream_info: dict):
        if tile_index < 0 or tile_index >= len(self.video_tiles):
            return

        if not self._prompt_unconfigured_camera(stream_info, target_tile_idx=tile_index):
            return

        tile = self.video_tiles[tile_index]
        stream_id = stream_info.get("id")
        main_url = stream_info.get("url")
        sub_url = stream_info.get("sub_url", "")
        name = stream_info.get("display_title", "Stream")
        camera_ip = stream_info.get("camera_ip", "")
        camera_name = stream_info.get("camera_name", "Camera")

        # Determine lens tag
        is_lens2 = (
            stream_info.get("channel") == 1
            or "lens2" in stream_id.lower()
            or "lens 2" in name.lower()
            or "wide" in name.lower()
            or "ch01" in main_url
        )
        lens_tag = "Lens2" if is_lens2 else "Lens1"

        tile.camera_ip = camera_ip
        tile.lens_tag = lens_tag

        if tile.worker and tile.stream_id != stream_id:
            old_id = tile.stream_id
            tile.detach_stream()
            self._cleanup_worker_if_unused(old_id)

        if stream_id in self.active_workers and self.active_workers[stream_id].isRunning():
            worker = self.active_workers[stream_id]
            worker.set_camera_context(camera_name, lens_tag)
            cam_id = stream_info.get("camera_id", "")
            worker.apply_camera_settings(self.device_manager.get_effective_camera_settings(cam_id))
        else:
            worker = CameraStreamWorker(stream_id, name, main_url, sub_url=sub_url, parent=self)
            worker.set_alert_manager(self.alert_manager)
            worker.set_camera_ip(camera_ip)
            worker.set_camera_context(camera_name, lens_tag)

            # Apply effective settings (Individual Camera Overrides + Global Fallback)
            cam_id = stream_info.get("camera_id", "")
            eff_settings = self.device_manager.get_effective_camera_settings(cam_id)
            worker.apply_camera_settings(eff_settings)

            # Apply performance throttling settings
            worker.set_performance_throttling(
                display_fps_cap=self.app_settings.get("display_fps_cap", 15),
                ai_skip_frames=self.app_settings.get("ai_skip_frames", 6),
                ai_motion_gated_only=self.app_settings.get("ai_motion_gated_only", False),
                motion_skip_frames=self.app_settings.get("motion_skip_frames", 1),
                motion_downscale_width=self.app_settings.get("motion_downscale_width", 480)
            )

            # Auto Sub-stream in multi-camera grid mode (saves ~80% decoding CPU)
            if self.app_settings.get("grid_substream", True) and self.current_layout in ["2x2", "3x3", "4x4", "1+5"]:
                worker.set_quality(QualityMode.LOW_SD)

            # Wind Shake Filter configuration (enabled by default for Fata dual-lens)
            cam_name_lower = name.lower()
            is_fata = "fata" in cam_name_lower or stream_info.get("is_dual_lens", False) or "wide" in cam_name_lower
            wind_enabled = eff_settings.get("wind_filter_enabled", self.app_settings.get("wind_filter_fata", True) if is_fata else False)
            wind_tol = eff_settings.get("wind_tolerance", 1.1)
            worker.set_wind_filter(enabled=wind_enabled, tolerance=wind_tol)
            worker.wind_shake_detected.connect(tile.on_wind_shake_detected)

            worker.motion_event.connect(self._on_motion_alert)
            self.active_workers[stream_id] = worker
            worker.start()

        tile.assign_stream(stream_info, worker)

        # Apply live signal status immediately if cached
        if camera_ip and camera_ip in self.signal_monitor.signal_cache:
            tile.update_signal_info(self.signal_monitor.signal_cache[camera_ip])

        self._on_tile_selected(tile_index)
        if not getattr(self, "_restoring_session", False):
            self.save_session_state()

    def _retire_worker(self, worker):
        # Keep QThread alive until cleanup finishes, without blocking UI paint for
        # every healthy camera while a broken camera's decoder is being reaped.
        if not hasattr(self, "_retiring_workers"):
            self._retiring_workers = set()
        self._retiring_workers.add(worker)
        worker.finished.connect(lambda w=worker: self._retiring_workers.discard(w))
        worker.stop(wait=False)
        if not worker.isRunning():
            self._retiring_workers.discard(worker)

    def _cleanup_worker_if_unused(self, stream_id: str):
        if not stream_id or stream_id not in self.active_workers:
            return
        is_used = any(t.stream_id == stream_id for t in self.video_tiles)
        if not is_used:
            worker = self.active_workers.pop(stream_id, None)
            if worker:
                self._retire_worker(worker)

    def _on_tile_stream_requested(self, tile_index: int, stream_data: dict):
        self.start_stream_on_tile(tile_index, stream_data)

    def _on_tile_closed(self, tile_index: int):
        tile = self.video_tiles[tile_index]
        old_id = tile.stream_id
        tile.detach_stream()
        self._cleanup_worker_if_unused(old_id)
        if not getattr(self, "_restoring_session", False):
            self.save_session_state()

    def _on_tile_selected(self, tile_index: int):
        self.selected_tile_idx = tile_index
        for i, t in enumerate(self.video_tiles):
            t.set_selected(i == tile_index)

        tile = self.video_tiles[tile_index]
        self.lbl_active_info.setText(f"Slot #{tile_index + 1}")
        self.lbl_active_info.setToolTip(f"Slot #{tile_index + 1}: {tile.stream_name}")

        if tile.camera_ip:
            cam = next((c for c in self.device_manager.get_cameras() if c.get("ip") == tile.camera_ip), None)
            pwd = cam.get("password", "") if cam else ""
            user = cam.get("username", "admin") if cam else "admin"
            port = int(cam.get("onvif_port", 8899)) if cam else 8899
            self.ptz_dock.sync_to_stream(tile.camera_ip, tile.stream_id)
            if hasattr(self, "intercom_dock") and self.intercom_dock:
                self.intercom_dock.sync_to_stream(tile.camera_ip, tile.stream_id)
        else:
            self.ptz_dock.status_badge.setText(f" SLOT #{tile_index + 1} (NO FEED)")
            self.ptz_dock.setEnabled(True)
            if hasattr(self, "intercom_dock") and self.intercom_dock:
                self.intercom_dock.clear_camera()

    def _on_ptz_command_issued(self, direction: str, speed: int):
        tile = self.video_tiles[self.selected_tile_idx]
        if self.ptz_dock.is_digital_mode():
            step = int(35 * (max(1, min(10, speed)) / 5.0))
            dir_map = {
                "up": (0, -step),
                "down": (0, step),
                "left": (-step, 0),
                "right": (step, 0),
                "up_left": (-int(step * 0.7), -int(step * 0.7)),
                "up_right": (int(step * 0.7), -int(step * 0.7)),
                "down_left": (-int(step * 0.7), int(step * 0.7)),
                "down_right": (int(step * 0.7), int(step * 0.7))
            }
            if direction in dir_map:
                dx, dy = dir_map[direction]
                if tile.zoom_level > 1.0:
                    tile.pan_by(dx, dy)
                    self.statusBar().showMessage(f" Digital Pan: {direction.upper()} ({tile.stream_name})", 1500)
                else:
                    self.statusBar().showMessage(" Digital PTZ: Zoom in first (+0.25x) to pan digital viewport, or switch to Hardware Motor PTZ", 2500)
            elif direction == "zoom_in":
                tile.zoom_by(0.25)
            elif direction == "zoom_out":
                tile.zoom_by(-0.25)
        else:
            # Hardware Motor Mode: command already dispatched to camera motors by PTZPad!
            # Video tile image is NOT zoomed or cropped.
            self.statusBar().showMessage(f" PTZ Motor: {direction.upper()} (Speed {speed}/10)  {tile.stream_name}", 2000)

    def _on_ptz_zoom_issued(self, delta: float):
        tile = self.video_tiles[self.selected_tile_idx]
        if self.ptz_dock.is_digital_mode():
            tile.zoom_by(delta)
            self.statusBar().showMessage(f" Digital Zoom: {tile.zoom_level:.1f}x ({tile.stream_name})", 1500)
        else:
            self.statusBar().showMessage(f" Hardware PTZ Optical Zoom ({tile.stream_name})", 1500)

    def _on_ptz_reset_zoom(self):
        tile = self.video_tiles[self.selected_tile_idx]
        tile.reset_zoom()
        self.statusBar().showMessage(f"Zoom digital resetat la 1.0x ({tile.stream_name})", 1500)

    def _on_ptz_camera_target_changed(self, camera_ip: str, stream_id: str):
        # Focus the matching tile in the grid when user picks a camera in the PTZ dropdown
        for i, t in enumerate(self.video_tiles):
            if stream_id and t.stream_id == stream_id:
                self.selected_tile_idx = i
                for j, tile in enumerate(self.video_tiles):
                    tile.set_selected(j == i)
                self.lbl_active_info.setText(f"Slot #{i + 1}")
                self.lbl_active_info.setToolTip(f"Slot #{i + 1}: {t.stream_name}")
                break
            elif camera_ip and t.camera_ip == camera_ip:
                self.selected_tile_idx = i
                for j, tile in enumerate(self.video_tiles):
                    tile.set_selected(j == i)
                self.lbl_active_info.setText(f"Slot #{i + 1}")
                self.lbl_active_info.setToolTip(f"Slot #{i + 1}: {t.stream_name}")
                break

    def _on_ptz_preset_goto(self, preset_idx: int):
        tile = self.video_tiles[self.selected_tile_idx]
        if self.ptz_dock.is_digital_mode():
            tile.goto_preset(preset_idx)
        self.statusBar().showMessage(f" PTZ Preset #{preset_idx} Applied ({tile.stream_name})", 2000)

    def _on_ptz_preset_save(self, preset_idx: int):
        tile = self.video_tiles[self.selected_tile_idx]
        if self.ptz_dock.is_digital_mode():
            tile.save_preset(preset_idx)
        self.statusBar().showMessage(f" PTZ Preset #{preset_idx} Saved ({tile.stream_name})", 2000)

    def _on_ptz_patrol_step(self, preset_idx: int):
        tile = self.video_tiles[self.selected_tile_idx]
        if self.ptz_dock.is_digital_mode():
            tile.goto_preset(preset_idx)

    def _load_initial_alerts(self):
        recent = self.alert_manager.get_recent_alerts(limit=200)
        # Avoid duplicate cards if called more than once
        for card in list(self.alert_cards.values()):
            self.alerts_feed_layout.removeWidget(card)
            card.deleteLater()
        self.alert_cards.clear()

        for alert in reversed(recent):
            self._add_alert_card(alert)
        self.alert_count = len(self.alert_cards)
        self.side_tabs.setTabText(1, f"Alerts ({self.alert_count})")
        if hasattr(self, "lbl_alert_count_badge"):
            self.lbl_alert_count_badge.setText(f"{self.alert_count} Events")

    def _add_alert_card(self, alert_entry: dict):
        alert_id = alert_entry.get("id")
        if alert_id and alert_id in self.alert_cards:
            return
        card = AlertCardWidget(alert_entry, parent=self.alerts_scroll_content)
        card.delete_requested.connect(self._on_single_alert_delete)
        self.alert_cards[alert_id] = card
        self.alerts_feed_layout.insertWidget(0, card)

    def _on_single_alert_delete(self, alert_id: str):
        if not alert_id:
            return
        self.alert_manager.remove_alerts([alert_id])
        if alert_id in self.alert_cards:
            card = self.alert_cards.pop(alert_id)
            self.alerts_feed_layout.removeWidget(card)
            card.deleteLater()
        self.alert_count = len(self.alert_cards)
        self.side_tabs.setTabText(1, f"Alerts ({self.alert_count})")
        if hasattr(self, "lbl_alert_count_badge"):
            self.lbl_alert_count_badge.setText(f"{self.alert_count} Events")
        self.statusBar().showMessage("Alert removed.", 2000)

    def _on_alerts_purged(self, purged_ids: list):
        """Automatically updates UI cards when storage quota purges older incident clips."""
        if not purged_ids:
            return
        purged_set = set(purged_ids)
        removed_any = False
        for aid in list(self.alert_cards.keys()):
            if aid in purged_set:
                card = self.alert_cards.pop(aid)
                self.alerts_feed_layout.removeWidget(card)
                card.deleteLater()
                removed_any = True
        if removed_any:
            self.alert_count = len(self.alert_cards)
            self.side_tabs.setTabText(1, f"Alerts ({self.alert_count})")
            if hasattr(self, "lbl_alert_count_badge"):
                self.lbl_alert_count_badge.setText(f"{self.alert_count} Events")

    def _on_clear_alerts_clicked(self):
        self.alert_manager.clear_history()
        for card in list(self.alert_cards.values()):
            self.alerts_feed_layout.removeWidget(card)
            card.deleteLater()
        self.alert_cards.clear()
        self.alert_count = 0
        self.side_tabs.setTabText(1, "Alerts (0)")
        if hasattr(self, "lbl_alert_count_badge"):
            self.lbl_alert_count_badge.setText("0 Events")
        self.statusBar().showMessage("Alert history cleared.", 2500)

    def _show_sleek_alert_toast(self, alert_entry: dict):
        """Spawns sleek floating animated toast notification at top-right of surveillance window."""
        cw = self.centralWidget()
        if not cw:
            return

        # Dismiss any existing toast first
        if hasattr(self, "active_alert_toast") and self.active_alert_toast:
            try:
                self.active_alert_toast.dismiss()
            except Exception:
                pass
            self.active_alert_toast = None

        toast = SleekAlertNotification(alert_entry, parent=cw, duration_ms=6500)
        self.active_alert_toast = toast

        toast.action_clicked.connect(lambda ae: self._on_toast_action_clicked(ae))
        toast.dismissed.connect(self._on_toast_dismissed)

        margin_right = 24
        margin_top = 60 if (hasattr(self, "top_bar") and self.top_bar and self.top_bar.isVisible()) else 18
        x = cw.width() - toast.width() - margin_right
        y = margin_top
        toast.slide_in(QPoint(x, y))

    def _on_toast_action_clicked(self, alert_entry: dict):
        """Routes user directly to video playback when toast action is clicked."""
        self.open_video_player(alert_entry)

    def _on_toast_dismissed(self):
        self.active_alert_toast = None

    def _reposition_alarm_toast(self):
        """Positions the floating alert toast and floating exit fullscreen button without altering grid layout."""
        cw = self.centralWidget()
        if not cw:
            return

        if hasattr(self, "active_alert_toast") and self.active_alert_toast and self.active_alert_toast.isVisible():
            margin_right = 24
            margin_top = 84 if (hasattr(self, "top_bar") and self.top_bar and self.top_bar.isVisible()) else 18
            x = cw.width() - self.active_alert_toast.width() - margin_right
            y = margin_top
            self.active_alert_toast.move(x, y)
            self.active_alert_toast.raise_()

        if hasattr(self, "alarm_banner") and self.alarm_banner:
            banner_w = min(max(400, cw.width() - 80), 850)
            banner_h = 36
            banner_x = (cw.width() - banner_w) // 2
            top_bar_vis = hasattr(self, "top_bar") and self.top_bar and self.top_bar.isVisible()
            banner_y = 82 if top_bar_vis else 18
            self.alarm_banner.setGeometry(banner_x, banner_y, banner_w, banner_h)
            self.alarm_banner.raise_()

        if hasattr(self, "btn_exit_fullscreen_float") and self.btn_exit_fullscreen_float:
            if getattr(self, "is_fullscreen", False):
                btn_w = 175
                btn_h = 32
                self.btn_exit_fullscreen_float.setGeometry(cw.width() - btn_w - 20, 16, btn_w, btn_h)
                self.btn_exit_fullscreen_float.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_alarm_toast()
        if hasattr(self, "_reposition_ptz_flyout"):
            self._reposition_ptz_flyout()
        if hasattr(self, "_reposition_intercom_flyout"):
            self._reposition_intercom_flyout()
        self._adjust_responsive_ui(event.size().width())

    def _populate_tools_menu(self):
        self.tools_menu.clear()
        buttons = list(self._overflow_buttons)
        for button, title in [(self.btn_snap_all, "Snapshot"), (self.btn_ptz_panel, "PTZ controls"),
                              (self.btn_global_quality_btn, "Video quality"), (self.btn_cpu_monitor, "Performance")]:
            if button.isHidden():
                buttons.append((button, title))
        for button, title in buttons:
            action = self.tools_menu.addAction(button.icon(), title)
            action.setEnabled(button.isEnabled())
            action.setToolTip(button.toolTip())
            if button.isCheckable():
                action.setCheckable(True)
                action.setChecked(button.isChecked())
            action.triggered.connect(lambda checked=False, target=button: target.click())

    def _adjust_responsive_ui(self, win_width: int):
        if not hasattr(self, "btn_more_tools"):
            return
        mode = "wide" if win_width >= 1500 else ("balanced" if win_width >= 1200 else "compact")
        # Include the brand breakpoint in the cache key, even within compact mode.
        key = (mode, win_width < 1050)
        if getattr(self, "_current_responsive_mode", None) == key:
            return
        self._current_responsive_mode = key
        labels = mode == "wide"
        self.lbl_brand_text.setText("CCTV" if win_width < 1050 else "CCTV <span style='color:#38bdf8'>PanelView</span>")
        self.lbl_brand_text.setStyleSheet("background:transparent; border:none; font-size:14px; font-weight:600;")
        self.btn_toggle_sidebar.setText(" Sidebar" if labels else "")
        for name, button in self.layout_btns.items():
            button.setText(" " + ("Custom" if name == "custom" else name) if labels else "")
        self.btn_dual_hero.setText(" Dual" if labels else "")
        self.btn_trigger_settings.setText(" Events" if mode != "compact" else "")
        self.btn_snap_all.setText(" Snapshot" if labels else "")
        self.btn_ptz_panel.setText(" PTZ" if labels else "")
        self.btn_player.setText(" Recordings" if mode != "compact" else "")
        self.btn_more_tools.setText(" More")
        for button in (self.btn_snap_all, self.btn_ptz_panel, self.btn_global_quality_btn, self.btn_cpu_monitor):
            button.setVisible(mode != "compact")
        self._update_master_alerts_btn_style()
        self._update_global_quality_btn_style()
        self.top_bar.layout().invalidate()

    def _on_alert_triggered_from_manager(self, alert_entry: dict):
        try:
            target = alert_entry.get("label", "Detection").upper()
            conf_pct = int(alert_entry.get("confidence", 0.0) * 100)
            s_name = alert_entry.get("camera_name", "Camera")
            lens_tag = alert_entry.get("lens", "Lens1")
            now_str = alert_entry.get("time_short", datetime.now().strftime("%H:%M:%S"))
            desc = alert_entry.get("description", "")
            silent = bool(alert_entry.get("silent", False))

            # 1. Spawn sleek animated on-screen alert notification toast (suppressed if silent recording)
            if not silent:
                self._show_sleek_alert_toast(alert_entry)
            else:
                self.statusBar().showMessage(f"{desc or f'{target} clip saved on {s_name} ({lens_tag})'}", 4000)

            # 2. Add AlertCardWidget to top of live alerts feed
            self._add_alert_card(alert_entry)
            self.alert_count = len(self.alert_cards)
            self.side_tabs.setTabText(1, f"Alerts ({self.alert_count})")
            if hasattr(self, "lbl_alert_count_badge"):
                self.lbl_alert_count_badge.setText(f"{self.alert_count} Events")

            # 3. Sound Alarm (Audible Siren in background thread) - only for unmuted, non-silent events
            if self.sound_alarms_enabled and not silent:
                threading.Thread(target=self._play_siren_sound, daemon=True).start()
        except Exception as e:
            print(f"[MainWindow] Error handling alert trigger: {e}")

    def _on_alert_video_ready(self, alert_entry: dict):
        try:
            alert_id = alert_entry.get("id")
            uid = alert_entry.get("unique_id", "")
            video_path = alert_entry.get("video_path")
            raw_path = alert_entry.get("video_raw_path", "")
            is_ready = bool(alert_entry.get("video_ready"))

            # 1. Update active open VideoPlayerDialog if it is buffering this incident
            if hasattr(self, "active_video_player") and self.active_video_player:
                p_aid = getattr(self.active_video_player, "alert_id", "")
                p_uid = getattr(self.active_video_player, "unique_id", "")
                if (alert_id and p_aid == alert_id) or (uid and p_uid == uid):
                    if is_ready and video_path and os.path.exists(video_path):
                        self.active_video_player.set_video_ready(video_path, raw_path=raw_path)
                    else:
                        self.active_video_player.set_video_failed()

            # 2. Update active on-screen alert toast if currently visible
            if hasattr(self, "active_alert_toast") and self.active_alert_toast:
                t_aid = self.active_alert_toast.alert_entry.get("id")
                t_uid = self.active_alert_toast.alert_entry.get("unique_id", "")
                if (alert_id and t_aid == alert_id) or (uid and t_uid == uid):
                    if hasattr(self.active_alert_toast, "update_video_ready"):
                        self.active_alert_toast.update_video_ready(video_path, raw_path=raw_path)

            # 3. Update sidebar alert card
            if alert_id in self.alert_cards:
                if is_ready and video_path and os.path.exists(video_path):
                    self.alert_cards[alert_id].set_video_ready(video_path, raw_path=raw_path)
                else:
                    self.alert_cards[alert_id].set_video_failed()

            if is_ready:
                fname = alert_entry.get("filename") or (os.path.basename(video_path) if video_path else "")
                self.statusBar().showMessage(f" 10s Incident Clip Ready: {fname}", 5000)
            else:
                self.statusBar().showMessage(" Snapshot saved successfully.", 4000)
        except Exception as e:
            print(f"[MainWindow] Error handling video ready signal: {e}")

    def check_old_alerts_retention(self, silent_if_none: bool = True):
        """
        Storage Retention Monitor:
        Detects alerts older than the configured retention period (default 30 days) and calculates storage footprint.
        Prompts user with RetentionCleanupDialog to either confirm removal or decline to keep.
        Under no circumstances are files deleted without user explicit consent.
        """
        retention_days = int(self.app_settings.get("retention_days", 7))
        # Background check also prunes unindexed / orphaned snapshots older than 3 days to keep disk size lean
        if silent_if_none and hasattr(self.alert_manager, "prune_orphaned_snapshots"):
            try:
                self.alert_manager.prune_orphaned_snapshots(max_age_days=3, max_count=1000)
            except Exception as e:
                print(f"[MainWindow] Background snapshot prune warning: {e}")

        if retention_days <= 0:
            if not silent_if_none:
                QMessageBox.information(
                    self, "Storage Retention",
                    "Retention is set to 'Keep All'.\nAlerts will not be deleted automatically."
                )
            return

        expired = self.alert_manager.get_alerts_older_than(days=retention_days)
        if not expired:
            if not silent_if_none:
                QMessageBox.information(
                    self, "Storage Retention",
                    f"No alerts older than {retention_days} days found.\nStorage space is optimal."
                )
            return

        # Check if user previously snoozed notifications (only for automatic checks)
        if silent_if_none:
            snooze_until = self.app_settings.get("retention_snooze_until")
            if snooze_until:
                try:
                    snooze_dt = datetime.fromisoformat(snooze_until)
                    if datetime.now() < snooze_dt:
                        return
                except Exception:
                    pass

        prompt_required = self.app_settings.get("retention_prompt_before_delete", True)
        if silent_if_none and not prompt_required:
            # Auto-clean without prompt when user configured silent cleanup
            ids_to_remove = [a.get("id") for a in expired if a.get("id")]
            deleted_count, bytes_freed = self.alert_manager.remove_alerts(ids_to_remove)
            for aid in ids_to_remove:
                if aid in self.alert_cards:
                    card = self.alert_cards.pop(aid)
                    self.alerts_feed_layout.removeWidget(card)
                    card.deleteLater()

            self.alert_count = len(self.alert_cards)
            self.side_tabs.setTabText(1, f"Alerts ({self.alert_count})")
            if hasattr(self, "lbl_alert_count_badge"):
                self.lbl_alert_count_badge.setText(f"{self.alert_count} Events")
            freed_mb = bytes_freed / (1024 * 1024)
            self.statusBar().showMessage(f"Auto-cleaned {deleted_count} alerts older than {retention_days} days ({freed_mb:.1f} MB freed).", 5000)
            return

        try:
            from ui.components.retention_dialog import RetentionCleanupDialog
            dlg = RetentionCleanupDialog(expired, retention_days=retention_days, parent=self)
            res = dlg.exec()

            if res == QDialog.DialogCode.Accepted and not dlg.user_declined:
                # User approved deletion!
                ids_to_remove = [a.get("id") for a in expired if a.get("id")]
                deleted_count, bytes_freed = self.alert_manager.remove_alerts(ids_to_remove)

                # Remove from live UI cards if present
                for aid in ids_to_remove:
                    if aid in self.alert_cards:
                        card = self.alert_cards.pop(aid)
                        self.alerts_feed_layout.removeWidget(card)
                        card.deleteLater()

                self.alert_count = len(self.alert_cards)
                self.side_tabs.setTabText(1, f"Alerts ({self.alert_count})")
                if hasattr(self, "lbl_alert_count_badge"):
                    self.lbl_alert_count_badge.setText(f"{self.alert_count} Events")

                freed_mb = bytes_freed / (1024 * 1024)
                self.statusBar().showMessage(f"Cleaned {deleted_count} old alerts ({freed_mb:.1f} MB freed).", 5000)
                QMessageBox.information(
                    self, "Cleanup Complete",
                    f"Removed {deleted_count} alerts older than {retention_days} days.\nFreed {freed_mb:.1f} MB on disk."
                )
            else:
                # User declined or snoozed
                if dlg.snooze_days > 0:
                    snooze_dt = datetime.now() + timedelta(days=dlg.snooze_days)
                    self.app_settings["retention_snooze_until"] = snooze_dt.isoformat()
                    self.device_manager.save_config()
                self.statusBar().showMessage("Alert cleanup declined: All alerts preserved.", 3500)
        except Exception as e:
            print(f"[RetentionCheck] Error executing cleanup dialog: {e}")

    def _update_retention_button_label(self):
        if hasattr(self, "btn_retention_clean"):
            r_days = int(self.app_settings.get("retention_days", 7))
            if r_days <= 0:
                self.btn_retention_clean.setText("Keep All")
                self.btn_retention_clean.setToolTip("Storage Retention: Keep all alerts without auto-deletion")
            else:
                self.btn_retention_clean.setText(f"Clean {r_days}d")
                self.btn_retention_clean.setToolTip(f"Review and clean alerts older than {r_days} days")

    def on_ai_alarm_triggered(self, tile_idx: int, s_id: str, s_name: str, target_desc: str, conf: float, frame: object):
        pass

    def _refresh_signal_monitor_cameras(self):
        cameras = self.device_manager.get_cameras()
        from core.camera_urls import camera_endpoint
        endpoints = {}
        for camera in cameras:
            key = camera.get("ip")
            if not key:
                continue
            for stream in camera.get("streams", []):
                try:
                    endpoints.setdefault(key, []).append(camera_endpoint(stream.get("url", "")))
                except ValueError:
                    pass
            if not endpoints.get(key):
                endpoints[key] = [(key, int(camera.get("port", 554)))]
        self.signal_monitor.set_camera_endpoints(endpoints)

    def _on_signals_updated(self, results: dict):
        results = {key: dict(value) for key, value in results.items()}
        # Only fresh video can override an unsuccessful endpoint probe.
        for tile in self.video_tiles:
            if tile.camera_ip and tile.worker and tile.worker.has_recent_frame():
                ip = tile.camera_ip
                if ip not in results or not results[ip].get("is_online"):
                    results[ip] = {
                        "ip": ip,
                        "is_online": True,
                        "latency_ms": 0.0,
                        "percent": 95,
                        "bars": "[OK] 4/4",
                        "bars_text": "Live Streaming",
                        "color": "#38bdf8",
                        "quality_label": "Live Stream Active",
                        "tooltip": f"Camera {ip}: Streaming Live ({tile.fps:.0f} FPS)"
                    }

        # 1. Update Video Tiles
        for tile in self.video_tiles:
            if tile.camera_ip and tile.camera_ip in results:
                tile.update_signal_info(results[tile.camera_ip])

        # 2. Update Draggable Camera Tree Items
        for i in range(self.cam_tree.topLevelItemCount()):
            item = self.cam_tree.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "camera":
                cam = data.get("data", {})
                ip = cam.get("ip", "")
                if ip in results:
                    sig = results[ip]
                    is_online = sig.get("is_online", False)
                    pct = sig.get("percent", 0)
                    is_dual = cam.get("is_dual_lens", False)
                    name = cam.get("name", "Camera")
                    tag = " [Dual-Lens 2K]" if (is_dual and "dual" not in name.lower()) else ""
                    sig_str = f" {pct}%" if is_online else " Offline"
                    item.setText(0, f" {name} • {ip} • {sig_str}{tag}")
                    item.setToolTip(0, f"Camera: {name}\nIP: {ip}\nStatus: {sig_str}\nModel: {cam.get('model', 'N/A')}\nType: {'Dual-Lens (Fixed Wide + PTZ)' if is_dual else 'Standard'}")

    def _play_siren_sound(self):
        if not self.sound_alarms_enabled:
            return
        profile = self.app_settings.get("sound_profile", SoundProfile.CYBER_CHIME)
        vol = self.app_settings.get("sound_volume", 100)
        custom_wav = self.app_settings.get("custom_sound_path")
        self.sound_manager.play_sound(profile, volume=vol, custom_path=custom_wav)

    def toggle_sound_alarms(self):
        self.sound_alarms_enabled = not self.sound_alarms_enabled
        is_wide = (self.width() >= 1550) if hasattr(self, "width") else True
        if self.sound_alarms_enabled:
            self.btn_sound_alarm.setText(" Siren: ON" if is_wide else "")
            self.btn_sound_alarm.setIcon(create_topbar_icon("siren", active=True, size=16, custom_color="#f87171"))
            self.btn_sound_alarm.setStyleSheet("")
            self.btn_sound_alarm.setToolTip("Audio sirens active (Click to Mute)")
            self.statusBar().showMessage("Audible Alarms Enabled", 3000)
        else:
            self.btn_sound_alarm.setText(" Siren: OFF" if is_wide else "")
            self.btn_sound_alarm.setIcon(create_topbar_icon("siren", active=False, size=16, custom_color="#94a3b8"))
            self.btn_sound_alarm.setStyleSheet("background-color: rgba(127, 29, 29, 0.45); color: #fca5a5; border-color: #ef4444;")
            self.btn_sound_alarm.setToolTip("Audio sirens muted (Click to Enable)")
            self.statusBar().showMessage("Audible Alarms Muted", 3000)

    def toggle_global_color_night(self):
        """Toggles Full-Color Night Mode across all active camera streams simultaneously."""
        self.global_color_night_active = not getattr(self, "global_color_night_active", False)
        is_wide = (self.width() >= 1550) if hasattr(self, "width") else True

        if self.global_color_night_active:
            self.btn_global_color_night.setText(" Night Color: ON" if is_wide else "")
            self.btn_global_color_night.setChecked(True)
            self.btn_global_color_night.setStyleSheet("""
                QPushButton {
                    background-color: rgba(56, 189, 248, 0.22);
                    color: #38bdf8;
                    font-weight: 700;
                    border: 1px solid #0284c7;
                }
                QPushButton:hover {
                    background-color: rgba(56, 189, 248, 0.35);
                    color: #bae6fd;
                }
            """)
        else:
            self.btn_global_color_night.setText(" Night Color" if is_wide else "")
            self.btn_global_color_night.setChecked(False)
            self.btn_global_color_night.setStyleSheet("")

        # Apply to all video tiles
        for tile in self.video_tiles:
            tile.color_night_active = self.global_color_night_active
            if tile.worker:
                tile.worker.set_color_night_mode(self.global_color_night_active)
            if hasattr(tile, "btn_color_night"):
                tile.btn_color_night.setText("")
                tile.btn_color_night.setIcon(create_tile_icon("color", active=tile.color_night_active, size=24))
                if tile.color_night_active:
                    tile.btn_color_night.setStyleSheet("background-color: rgba(245, 158, 11, 0.28); border-radius: 14px; border: 1px solid #f59e0b;")
                else:
                    tile.btn_color_night.setStyleSheet(TILE_ACTION_BTN_STYLE)
                tile._update_controls_visibility()
                tile.update()

        # Dispatch hardware floodlight commands
        self._dispatch_hardware_white_light(self.global_color_night_active)

    def _dispatch_hardware_white_light(self, enable: bool):
        from core.ptz_controller import PTZController
        for cam in self.device_manager.get_cameras():
            ip = cam.get("ip")
            user = cam.get("username", "admin")
            pwd = cam.get("password", "")
            port = int(cam.get("onvif_port", 8899))
            if ip:
                try:
                    ctrl = PTZController(ip, user, pwd, port=port)
                    ctrl.set_white_light(enable)
                except Exception:
                    pass

    def _on_tile_double_clicked(self, tile_index: int):
        """Called when a camera tile is double-clicked: toggles solo in-app view for that camera."""
        if tile_index < 0 or tile_index >= len(self.video_tiles):
            return
        target_tile = self.video_tiles[tile_index]
        is_currently_solo = getattr(target_tile, "is_solo", False)
        self._on_tile_solo_toggled(tile_index, not is_currently_solo)

    def toggle_camera_fullscreen(self, tile_index: int):
        """Toggles true OS fullscreen for the double-clicked camera tile."""
        if self.is_fullscreen:
            self.exit_fullscreen()
        else:
            self.enter_camera_fullscreen(tile_index)

    def enter_camera_fullscreen(self, tile_index: int):
        """Maximizes the camera across the entire monitor without borders, sidebars, or toolbars."""
        if tile_index < 0 or tile_index >= len(self.video_tiles):
            return
        target_tile = self.video_tiles[tile_index]
        if not target_tile.stream_id:
            self.statusBar().showMessage("This slot is empty. Assign a camera first.", 2500)
            return

        self.pre_fullscreen_layout = self.current_layout
        self.pre_fullscreen_sidebar_visible = getattr(self, "is_sidebar_visible", True)
        self.pre_fullscreen_tile_idx = tile_index

        # 1. Hide surrounding UI elements
        if hasattr(self, "sidebar"):
            self.sidebar.hide()
            if hasattr(self, "splitter"):
                self.splitter.setSizes([0, self.width()])
        if hasattr(self, "top_bar"):
            self.top_bar.hide()
        if hasattr(self, "bottom_bar"):
            self.bottom_bar.hide()

        # 2. Solo target tile across 100% of grid canvas
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item.widget():
                self.grid_layout.removeWidget(item.widget())

        for r in range(6):
            self.grid_layout.setRowStretch(r, 0)
        for c in range(6):
            self.grid_layout.setColumnStretch(c, 0)

        for i, t in enumerate(self.video_tiles):
            if i != tile_index:
                t.hide()
                t.is_solo = False
                t.btn_solo.setIcon(create_tile_icon("solo"))
                if t.worker:
                    t.worker.set_gui_rendering_paused(True)

        target_tile.is_solo = True
        target_tile.btn_solo.setIcon(create_tile_icon("restore"))
        self.grid_layout.addWidget(target_tile, 0, 0)
        self.grid_layout.setRowStretch(0, 1)
        self.grid_layout.setColumnStretch(0, 1)
        target_tile.show()

        # 3. Boost resolution to full 2K
        if target_tile.worker:
            target_tile.worker.set_gui_rendering_paused(False)
            target_tile.worker.set_solo_view(True)
            target_tile.worker.set_quality(QualityMode.ULTRA_2K)

        self._on_tile_selected(tile_index)

        # 4. OS Fullscreen
        self.is_fullscreen = True
        self.showFullScreen()
        self._apply_window_corners()
        if hasattr(self, "btn_fullscreen"):
            self.btn_fullscreen.setText("[ ] Exit Full")

        # 5. Position exit button and show toast
        self._reposition_alarm_toast()
        if hasattr(self, "btn_exit_fullscreen_float"):
            self.btn_exit_fullscreen_float.show()
            self.btn_exit_fullscreen_float.raise_()

        if hasattr(self, "alarm_banner"):
            self.alarm_banner.setText(f"[ ] Fullscreen: {target_tile.stream_name} - Double-click or ESC to exit")
            self.alarm_banner.show()
            self.alarm_banner_timer.start(2500)

    def exit_fullscreen(self):
        """Cleanly exits fullscreen and restores previous layout, toolbars, and sidebar."""
        self.is_fullscreen = False
        self.showNormal()
        self._apply_window_corners()

        if hasattr(self, "btn_exit_fullscreen_float"):
            self.btn_exit_fullscreen_float.hide()

        if hasattr(self, "top_bar"):
            self.top_bar.show()
        if hasattr(self, "bottom_bar"):
            self.bottom_bar.hide()
        if hasattr(self, "btn_fullscreen"):
            self.btn_fullscreen.setText("[ ]")

        # Restore sidebar
        if getattr(self, "pre_fullscreen_sidebar_visible", True):
            if hasattr(self, "sidebar"):
                self.sidebar.show()
                self.is_sidebar_visible = True
            if hasattr(self, "btn_toggle_sidebar"):
                self.btn_toggle_sidebar.setText(" Side")
            saved_w = int(self.app_settings.get("sidebar_width", 380))
            self.splitter.setSizes([saved_w, max(400, self.width() - saved_w)])
        else:
            if hasattr(self, "sidebar"):
                self.sidebar.hide()
                self.is_sidebar_visible = False
            if hasattr(self, "btn_toggle_sidebar"):
                self.btn_toggle_sidebar.setText(" Side")
            self.splitter.setSizes([0, self.width()])

        # Restore grid layout
        prev_layout = getattr(self, "pre_fullscreen_layout", self.app_settings.get("default_layout", "2x2"))
        if prev_layout == "1x1":
            prev_layout = "2x2"
        self.set_grid_layout(prev_layout)

        for t in self.video_tiles:
            t.is_solo = False
            t.btn_solo.setIcon(create_tile_icon("solo"))

        self._reposition_alarm_toast()
        self.statusBar().showMessage("Fullscreen exited.", 2500)

    def _on_tile_solo_toggled(self, tile_index: int, is_solo: bool):
        if is_solo:
            self.previous_layout = self.current_layout
            for i in reversed(range(self.grid_layout.count())):
                item = self.grid_layout.itemAt(i)
                if item.widget():
                    self.grid_layout.removeWidget(item.widget())

            for r in range(6):
                self.grid_layout.setRowStretch(r, 0)
            for c in range(6):
                self.grid_layout.setColumnStretch(c, 0)

            for i, t in enumerate(self.video_tiles):
                if i != tile_index:
                    t.hide()
                    t.is_solo = False
                    t.btn_solo.setIcon(create_tile_icon("solo"))
                    if t.worker:
                        t.worker.set_gui_rendering_paused(True)

            target_tile = self.video_tiles[tile_index]
            target_tile.is_solo = True
            target_tile.btn_solo.setIcon(create_tile_icon("restore"))
            self.grid_layout.addWidget(target_tile, 0, 0)
            self.grid_layout.setRowStretch(0, 1)
            self.grid_layout.setColumnStretch(0, 1)
            target_tile.show()

            solo_worker = target_tile.worker
            if solo_worker:
                solo_worker.set_gui_rendering_paused(False)
                solo_worker.set_solo_view(True)
                solo_worker.set_quality(self.global_quality)

            self._on_tile_selected(tile_index)
            self.statusBar().showMessage(f"Solo View: {target_tile.stream_name} (Press ESC, Double-Click, or 1-4 to restore)", 3500)
        else:
            prev = getattr(self, "previous_layout", self.app_settings.get("default_layout", "2x2"))
            if prev == "1x1":
                prev = "2x2"
            for t in self.video_tiles:
                t.is_solo = False
                t.btn_solo.setIcon(create_tile_icon("solo"))
            self.set_grid_layout(prev)

    def _exit_fullscreen_or_solo(self):
        if hasattr(self, "ptz_flyout") and self.ptz_flyout.isVisible():
            self.hide_ptz_flyout()
            return
        if hasattr(self, "intercom_flyout") and self.intercom_flyout.isVisible():
            self.hide_intercom_flyout()
            return
        if self.is_fullscreen:
            self.exit_fullscreen()
        else:
            any_solo = any(t.is_solo for t in self.video_tiles)
            if any_solo:
                prev = getattr(self, "previous_layout", self.app_settings.get("default_layout", "2x2"))
                if prev == "1x1":
                    prev = "2x2"
                for t in self.video_tiles:
                    t.is_solo = False
                    t.btn_solo.setIcon(create_tile_icon("solo"))
                self.set_grid_layout(prev)

    def _on_tree_item_clicked(self, item, col):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data.get("type") == "stream":
            s_data = data.get("data")
            self.lbl_active_info.setText(f"Ready: {s_data.get('display_title')} (Double-click or drag to slot)")
        elif data.get("type") == "camera":
            cam = data.get("data")
            self.lbl_active_info.setText(f"Camera: {cam.get('name')} (Double-click to stream to grid)")

    def _on_tree_item_double_clicked(self, item, col):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data.get("type") == "stream":
            self.assign_stream_smart(data.get("data"))

        elif data.get("type") == "camera":
            cam = data.get("data")
            self.add_camera_to_grid(cam)

    def _on_tree_context_menu(self, pos):
        item = self.cam_tree.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #f1f5f9;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 20px 6px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: #1e293b;
                margin: 4px 6px;
            }
        """)

        if data.get("type") == "stream":
            s_data = data.get("data")
            act_smart = menu.addAction(create_topbar_icon("stream", size=15, custom_color="#38bdf8"), "Stream to Grid (Empty Slot)")
            act_smart.triggered.connect(lambda: self.assign_stream_smart(s_data))

            act_play = menu.addAction(create_topbar_icon("stream", size=15, custom_color="#38bdf8"), f"Stream in Selected Slot (#{self.selected_tile_idx + 1})")
            act_play.triggered.connect(lambda: self.start_stream_on_tile(self.selected_tile_idx, s_data))

            menu.addSeparator()

            act_rename_lens = menu.addAction(create_topbar_icon("edit", size=15, custom_color="#94a3b8"), "Rename Lens...")
            act_rename_lens.triggered.connect(lambda: self.prompt_rename_lens(s_data.get("id")))

            act_rename = menu.addAction(create_topbar_icon("edit", size=15, custom_color="#94a3b8"), "Rename Camera...")
            act_rename.triggered.connect(lambda: self.prompt_rename_camera(s_data.get("camera_id")))

            act_indiv = menu.addAction(create_topbar_icon("settings", size=15, custom_color="#38bdf8"), "Camera Settings & Night Vision")
            act_indiv.triggered.connect(lambda: self.open_settings_dialog(selected_camera_id=s_data.get("camera_id")))

        elif data.get("type") == "camera":
            cam = data.get("data")
            act_add_all = menu.addAction(create_topbar_icon("stream", size=15, custom_color="#38bdf8"), "Stream Camera to Grid (Empty Slot(s))")
            act_add_all.triggered.connect(lambda: self.add_camera_to_grid(cam))

            if cam.get("is_dual_lens"):
                act_dual_side = menu.addAction(create_topbar_icon("dual_lens", size=15, custom_color="#38bdf8"), "Stream Both Lenses Side-by-Side (2-Split)")
                act_dual_side.triggered.connect(self.activate_dual_lens_mode)

            act_indiv = menu.addAction(create_topbar_icon("settings", size=15, custom_color="#38bdf8"), "Camera Settings & Night Vision")
            act_indiv.triggered.connect(lambda: self.open_settings_dialog(selected_camera_id=cam.get("id")))

            act_rename = menu.addAction(create_topbar_icon("edit", size=15, custom_color="#94a3b8"), "Rename Camera...")
            act_rename.triggered.connect(lambda: self.prompt_rename_camera(cam.get("id")))

            streams = cam.get("streams", [])
            if streams:
                sub_rename = menu.addMenu("Rename Lens")
                sub_rename.setIcon(create_topbar_icon("rename", size=15, custom_color="#94a3b8"))
                for s in streams:
                    s_id = s.get("id")
                    s_name = s.get("name", "Lens")
                    act_l = sub_rename.addAction(create_topbar_icon("rename", size=14, custom_color="#94a3b8"), s_name)
                    act_l.triggered.connect(lambda ch, sid=s_id: self.prompt_rename_lens(sid))

            menu.addSeparator()

            act_edit = menu.addAction(create_topbar_icon("manage", size=15, custom_color="#94a3b8"), "Edit Connection Parameters (Credentials & Port)")
            act_edit.triggered.connect(lambda: self._edit_camera(cam))

            act_del = menu.addAction(create_topbar_icon("trash", size=15, custom_color="#ef4444"), "Remove Camera")
            act_del.triggered.connect(lambda: self._delete_camera(cam))

        menu.exec(self.cam_tree.mapToGlobal(pos))

    def prompt_rename_camera(self, camera_id: Optional[str] = None):
        """Prompts user to rename camera and propagates changes across the entire application."""
        if not camera_id:
            return
        cam = self.device_manager.get_camera_by_id(camera_id)
        if not cam:
            return

        current_name = cam.get("name", "Camera")
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Camera",
            f"Enter new name for camera '{current_name}':",
            text=current_name
        )
        if ok and new_name and new_name.strip():
            new_name = new_name.strip()
            self.rename_camera(camera_id, new_name)

    def rename_camera(self, camera_id: str, new_name: str):
        """Renames camera and immediately reflects change across configs, active streams, tiles, sidebar, and web server."""
        cam = self.device_manager.get_camera_by_id(camera_id)
        if not cam:
            return
        old_name = cam.get("name", "Camera")
        cam["name"] = new_name

        # 1. Update in device_manager and cameras_config.json
        self.device_manager.save_config()

        # 2. Update all active camera workers
        for s in cam.get("streams", []):
            s_id = s.get("id")
            s["camera_name"] = new_name
            s["display_title"] = f"{new_name} - {s.get('name', 'Stream')}"
            if s_id in self.active_workers:
                worker = self.active_workers[s_id]
                worker.camera_name = new_name
                worker.stream_name = f"{new_name} - {s.get('name', 'Stream')}"
                worker.set_camera_context(new_name, worker.lens_tag)

        # 3. Update all video tiles
        for tile in self.video_tiles:
            if tile.stream_info and tile.stream_info.get("camera_id") == camera_id:
                tile.stream_info["camera_name"] = new_name
                lens_name = tile.stream_info.get("name", "Stream")
                raw_display = f"{new_name} - {lens_name}"
                tile.stream_info["display_title"] = raw_display
                clean_title = format_clean_camera_title(raw_display)
                tile.stream_name = clean_title
                if hasattr(tile, "title_label"):
                    tile.title_label.setText(clean_title)
                    tile.title_label.setToolTip(f"Camera Stream: {raw_display}")

        # 4. Refresh Sidebar Tree
        self._populate_camera_tree()

        # 5. Refresh signal monitor
        self._refresh_signal_monitor_cameras()

        # 6. Status message
        self.statusBar().showMessage(f"Camera '{old_name}' renamed to '{new_name}' everywhere.", 4000)

    def prompt_rename_lens(self, stream_id: Optional[str] = None):
        """Prompts user to rename an individual stream/lens and propagates changes across the entire app."""
        if not stream_id:
            return
        stream_info = self.device_manager.get_stream_by_id(stream_id)
        if not stream_info:
            return

        current_lens_name = stream_info.get("name", "Stream")
        camera_name = stream_info.get("camera_name", "Camera")
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Lens",
            f"Enter new name for lens ({camera_name} - Stream ID: {stream_id}):",
            text=current_lens_name
        )
        if ok and new_name and new_name.strip():
            new_name = new_name.strip()
            self.rename_lens(stream_id, new_name)

    def rename_lens(self, stream_id: str, new_lens_name: str):
        """Renames a camera lens/stream and immediately reflects change across configs, active streams, tiles, sidebar, and web server."""
        stream_info = self.device_manager.get_stream_by_id(stream_id)
        if not stream_info:
            return
        old_name = stream_info.get("name", "Stream")
        cam_id = stream_info.get("camera_id")
        cam = self.device_manager.get_camera_by_id(cam_id)
        cam_name = cam.get("name", "Camera") if cam else stream_info.get("camera_name", "Camera")

        # 1. Update in device_manager and cameras_config.json
        success = self.device_manager.update_stream_name(stream_id, new_lens_name)
        if not success:
            return

        new_display_title = f"{cam_name} - {new_lens_name}"

        # 2. Update active camera worker
        if stream_id in self.active_workers:
            worker = self.active_workers[stream_id]
            worker.stream_name = new_display_title
            worker.lens_tag = new_lens_name
            worker.set_camera_context(cam_name, new_lens_name)

        # 3. Update all video tiles assigned to this stream
        for tile in self.video_tiles:
            if tile.stream_id == stream_id:
                if tile.stream_info:
                    tile.stream_info["name"] = new_lens_name
                    tile.stream_info["display_title"] = new_display_title
                clean_title = format_clean_camera_title(new_display_title)
                tile.stream_name = clean_title
                tile.lens_tag = new_lens_name
                if hasattr(tile, "title_label"):
                    tile.title_label.setText(clean_title)
                    tile.title_label.setToolTip(f"Camera Stream: {new_display_title}")

        # 4. Refresh Sidebar Tree
        self._populate_camera_tree()

        # 5. Status message
        self.statusBar().showMessage(f"Lens '{old_name}' renamed to '{new_lens_name}' everywhere.", 4000)

    def _stream_dual_stacked(self, cam):
        self.set_grid_layout("1x2")
        streams = cam.get("streams", [])
        if len(streams) >= 1:
            s1 = dict(streams[0])
            s1["camera_id"] = cam.get("id")
            s1["camera_name"] = cam.get("name")
            s1["camera_ip"] = cam.get("ip")
            s1["display_title"] = f"{cam.get('name')} - {s1.get('name')}"
            self.start_stream_on_tile(0, s1)
        if len(streams) >= 2:
            s2 = dict(streams[1])
            s2["camera_id"] = cam.get("id")
            s2["camera_name"] = cam.get("name")
            s2["camera_ip"] = cam.get("ip")
            s2["display_title"] = f"{cam.get('name')} - {s2.get('name')}"
            self.start_stream_on_tile(1, s2)

    def _update_master_alerts_btn_style(self):
        """Updates Master Security Alerts button style based on armed/disarmed status."""
        if not hasattr(self, "btn_master_alerts"):
            return
        is_wide = (self.width() >= 1550) if hasattr(self, "width") else True
        is_balanced = (self.width() >= 1200) if hasattr(self, "width") else True
        armed = getattr(self, "master_alerts_enabled", True)

        if armed:
            txt = " Security: ARMED" if (is_wide or is_balanced) else ""
            self.btn_master_alerts.setText(txt)
            self.btn_master_alerts.setIcon(create_topbar_icon("shield", active=True, size=16, custom_color="#10b981"))
            self.btn_master_alerts.setStyleSheet("""
                QPushButton {
                    background-color: rgba(16, 185, 129, 0.20);
                    color: #34d399;
                    border: 1px solid rgba(16, 185, 129, 0.60);
                    font-weight: 700;
                    border-radius: 6px;
                    padding: 3px 8px;
                }
                QPushButton:hover {
                    background-color: rgba(16, 185, 129, 0.32);
                    border-color: #10b981;
                }
            """)
            self.btn_master_alerts.setToolTip("Security System ARMED (Click to Disarm All AI & Motion Alerts)")
        else:
            txt = " Security: OFF" if (is_wide or is_balanced) else ""
            self.btn_master_alerts.setText(txt)
            self.btn_master_alerts.setIcon(create_topbar_icon("shield", active=False, size=16, custom_color="#f87171"))
            self.btn_master_alerts.setStyleSheet("""
                QPushButton {
                    background-color: rgba(127, 29, 29, 0.30);
                    color: #fca5a5;
                    border: 1px solid rgba(239, 68, 68, 0.50);
                    font-weight: 600;
                    border-radius: 6px;
                    padding: 3px 8px;
                }
                QPushButton:hover {
                    background-color: rgba(127, 29, 29, 0.45);
                    border-color: #ef4444;
                }
            """)
            self.btn_master_alerts.setToolTip("Security System DISARMED (Click to 1-Click Arm Security & AI Detections)")

    def toggle_master_alerts(self, *args, force_state: Optional[bool] = None):
        """1-Click Master Security Toggle: arms or disarms all AI & motion detection, banners, chimes, and clips."""
        if force_state is not None:
            self.master_alerts_enabled = bool(force_state)
        else:
            self.master_alerts_enabled = not getattr(self, "master_alerts_enabled", False)

        self.app_settings["master_alerts_enabled"] = self.master_alerts_enabled

        # Arming is a gate; it must not overwrite the user's detection/recording preferences.
        self.global_motion_enabled = self.master_alerts_enabled and self.app_settings.get("motion_enabled", True)
        self.alert_manager.set_app_settings(self.app_settings)
        self.device_manager.save_config()
        self._update_master_alerts_btn_style()

        if hasattr(self, "btn_sound_alarm"):
            self.btn_sound_alarm.setText(" Siren: ON" if self.sound_alarms_enabled else " Siren: OFF")
            self.btn_sound_alarm.setIcon(create_topbar_icon("siren", active=self.sound_alarms_enabled, size=16, custom_color="#f87171" if self.sound_alarms_enabled else "#94a3b8"))
            if not self.sound_alarms_enabled:
                self.btn_sound_alarm.setStyleSheet("background-color: rgba(127, 29, 29, 0.45); color: #fca5a5; border-color: #ef4444;")
            else:
                self.btn_sound_alarm.setStyleSheet("")

        # Broadcast instantly to all active stream workers
        for s_id, worker in self.active_workers.items():
            cam = next((c for c in self.device_manager.get_cameras() if any(s.get("id") == s_id for s in c.get("streams", []))), None)
            cam_id = cam.get("id") if cam else ""
            eff = self.device_manager.get_effective_camera_settings(cam_id)
            eff["master_alerts_enabled"] = self.master_alerts_enabled
            worker.apply_camera_settings(eff)

        msg = "Security Armed: AI Person, Vehicle & Motion Detection Active" if self.master_alerts_enabled else "Security Disarmed: All Alerts Muted"
        self.statusBar().showMessage(msg, 4000)

    def _update_global_quality_btn_style(self):
        """Updates Global Quality button text and styling based on active quality mode."""
        if not hasattr(self, "btn_global_quality_btn"):
            return
        q = getattr(self, "global_quality", QualityMode.ULTRA_MAX)
        is_wide = (self.width() >= 1550) if hasattr(self, "width") else True
        is_balanced = (self.width() >= 1200) if hasattr(self, "width") else True
        txt = f" {q}" if (is_wide or is_balanced) else ""
        self.btn_global_quality_btn.setText(txt)
        color = "#00d2ff" if q == QualityMode.ULTRA_MAX else "#38bdf8"
        self.btn_global_quality_btn.setIcon(create_topbar_icon("quality", active=True, size=16, custom_color=color))
        tip = f"Global Quality: {q} (Click to cycle MAX -> 2K -> HD -> SD)"
        self.btn_global_quality_btn.setToolTip(tip)

    def _cycle_global_quality(self):
        """Cycles global quality across all cameras: MAX -> 2K -> MID -> LOW -> MAX."""
        curr = getattr(self, "global_quality", QualityMode.ULTRA_MAX)
        if curr == QualityMode.ULTRA_MAX:
            new_q = QualityMode.ULTRA_2K
        elif curr == QualityMode.ULTRA_2K:
            new_q = QualityMode.MID_HD
        elif curr == QualityMode.MID_HD:
            new_q = QualityMode.LOW_SD
        else:
            new_q = QualityMode.ULTRA_MAX
        self.set_global_quality(new_q)

    def set_global_quality(self, mode: str):
        """Sets global camera quality across all active workers and video tiles."""
        self.global_quality = mode
        self.app_settings["default_quality"] = mode
        self.device_manager.save_config()

        if hasattr(self, "cmb_global_quality"):
            idx = self.cmb_global_quality.findData(mode)
            if idx >= 0:
                self.cmb_global_quality.blockSignals(True)
                self.cmb_global_quality.setCurrentIndex(idx)
                self.cmb_global_quality.blockSignals(False)

        self._update_global_quality_btn_style()

        for worker in self.active_workers.values():
            worker.set_quality(mode)

        for tile in self.video_tiles:
            tile.on_quality_changed(mode)

        labels = {
            QualityMode.ULTRA_MAX: "MAX (Pristine App Quality)",
            QualityMode.ULTRA_2K: "2K (Raw Native Stream)",
            QualityMode.MID_HD: "720p HD (Balanced)",
            QualityMode.LOW_SD: "360p SD (Low Overhead)"
        }
        self.statusBar().showMessage(f"Global Stream Quality: {labels.get(mode, mode)}", 3000)

    def _on_global_quality_changed(self, idx):
        mode = self.cmb_global_quality.currentData()
        if mode:
            self.set_global_quality(mode)

    def _toggle_global_motion(self):
        self.global_motion_enabled = not self.global_motion_enabled
        self.app_settings["motion_enabled"] = self.global_motion_enabled
        self.device_manager.save_config()

        self._update_motion_btn_style()
        sens = self.app_settings.get("motion_sensitivity", 6)
        auto_rec = self.app_settings.get("auto_record_on_motion", False)

        for worker in self.active_workers.values():
            worker.set_motion_detection(self.global_motion_enabled, sensitivity=sens, auto_record=auto_rec)

        status_text = "AI: Active" if self.global_motion_enabled else "AI: Inactive"
        self.lbl_motion_status.setText(status_text)
        if self.global_motion_enabled:
            self.lbl_motion_status.setStyleSheet("background-color: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 4px; padding: 2px 8px; color: #38bdf8; font-weight: 600; font-size: 11px;")
        else:
            self.lbl_motion_status.setStyleSheet("background-color: rgba(100, 116, 139, 0.12); border: 1px solid #334155; border-radius: 4px; padding: 2px 8px; color: #94a3b8; font-weight: 600; font-size: 11px;")

    def _update_motion_btn_style(self):
        if self.global_motion_enabled:
            self.btn_global_motion.setText("Motion")
            self.btn_global_motion.setStyleSheet("background-color: rgba(56, 189, 248, 0.18); color: #38bdf8; border: 1px solid #0284c7; font-weight: 700; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
        else:
            self.btn_global_motion.setText("Pause")
            self.btn_global_motion.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; font-weight: 600; border-radius: 4px; padding: 4px 8px; font-size: 11px;")

    def _toggle_movement_view(self):
        """Toggles Movement View (motion heatmap & contour radar diagnostics) across all active cameras."""
        self.movement_view_active = not getattr(self, "movement_view_active", False)
        for worker in self.active_workers.values():
            if hasattr(worker, "set_movement_view"):
                worker.set_movement_view(self.movement_view_active)
        for tile in self.video_tiles:
            if hasattr(tile, "_update_movement_view_btn_style"):
                tile._update_movement_view_btn_style(self.movement_view_active)
            if hasattr(tile, "_update_controls_visibility"):
                tile._update_controls_visibility()
        self._update_movement_view_btn_style()
        status_msg = "Motion Radar: ENABLED" if self.movement_view_active else "Motion Radar: DISABLED"
        self.statusBar().showMessage(status_msg, 3500)

    def _update_movement_view_btn_style(self):
        if getattr(self, "movement_view_active", False):
            self.btn_movement_view.setText("Radar Active")
            self.btn_movement_view.setStyleSheet("""
                QPushButton {
                    background-color: #2563eb;
                    color: #ffffff;
                    border: 1px solid #3b82f6;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-weight: 700;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #1d4ed8;
                    border-color: #60a5fa;
                }
            """)
        else:
            self.btn_movement_view.setText("Motion Radar")
            self.btn_movement_view.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    color: #94a3b8;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-weight: 600;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #ffffff;
                    border-color: #3b82f6;
            """)

    def _on_motion_alert(self, stream_id: str, is_motion: bool, num_targets: int):
        if is_motion and self.motion_sound_enabled:
            self.sound_manager.play_motion_pip()

    def snapshot_all(self):
        count = 0
        for t in self.video_tiles:
            if t.worker and t.isVisible():
                t.take_snapshot()
                count += 1
        if count > 0:
            self.statusBar().showMessage(f" Captured snapshots from {count} active cameras!", 4000)

    def toggle_record_all(self):
        any_recording = any(t.is_recording for t in self.video_tiles if t.isVisible())
        for t in self.video_tiles:
            if t.worker and t.isVisible():
                if any_recording and t.is_recording:
                    t.toggle_recording()
                elif not any_recording and not t.is_recording:
                    t.toggle_recording()

        if any_recording:
            self.btn_rec_all.setText(" Rec")
            self.btn_rec_all.setStyleSheet("")
        else:
            self.btn_rec_all.setText(" Stop")
            self.btn_rec_all.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f87171, stop:1 #dc2626); color: white; border: 1px solid #ef4444; border-top: 1px solid rgba(255, 255, 255, 0.25); font-weight: 800; border-radius: 6px;")

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.exit_fullscreen()
        else:
            sel_idx = getattr(self, "selected_tile_idx", 0)
            if 0 <= sel_idx < len(self.video_tiles) and self.video_tiles[sel_idx].stream_id:
                self.enter_camera_fullscreen(sel_idx)
            else:
                active_tile = next((t for t in self.video_tiles if t.stream_id and not t.isHidden()), None)
                if active_tile:
                    self.enter_camera_fullscreen(active_tile.tile_index)
                else:
                    self.enter_camera_fullscreen(0)

    def _update_global_stats(self):
        active_count = len([w for w in self.active_workers.values() if w.status == StreamStatus.LIVE])
        total_fps = sum(w.fps for w in self.active_workers.values() if w.status == StreamStatus.LIVE)
        self.lbl_stream_count.setText(f"{active_count} Cameras" if active_count != 1 else "1 Camera")
        self.lbl_total_fps.setText(f"{total_fps:.1f} FPS")
        self._update_cpu_monitor()

        # Automatic Stream Watchdog: Detects stalled feeds or dead worker threads and recovers them seamlessly
        now = time.time()
        for stream_id, worker in list(self.active_workers.items()):
            try:
                # 1. Recover worker if thread died unexpectedly
                if getattr(worker, "_running", False) and not worker.isRunning():
                    print(f"[Watchdog] Worker thread for {worker.stream_name} died. Reviving worker...")
                    worker.start()
                    continue

                # 2. Recover worker if feed stalled (no frames received for > 6 seconds while supposed to be LIVE)
                if hasattr(worker, "is_feed_stalled") and worker.is_feed_stalled(threshold=6.0):
                    last_rec = getattr(worker, "_last_watchdog_reconnect_time", 0.0)
                    if (now - last_rec) >= 8.0:
                        worker._last_watchdog_reconnect_time = now
                        print(f"[Watchdog] Feed stalled on {worker.stream_name} (no frames > 6s). Reconnecting stream...")
                        worker.request_reconnect("Watchdog: Feed stalled")
            except Exception as e:
                print(f"[Watchdog] Error checking worker {stream_id}: {e}")

    def open_settings_dialog(self, selected_camera_id: Optional[str] = None, initial_tab_index: Optional[int] = None):
        if isinstance(selected_camera_id, bool):
            selected_camera_id = None

        dlg = SettingsDialog(
            current_settings=self.app_settings,
            cameras=self.device_manager.get_cameras(),
            selected_camera_id=selected_camera_id,
            parent=self
        )
        if initial_tab_index is not None and 0 <= initial_tab_index < dlg.stack.count():
            dlg.sidebar.setCurrentRow(initial_tab_index)
            dlg.stack.setCurrentIndex(initial_tab_index)
        elif selected_camera_id is not None:
            dlg.sidebar.setCurrentRow(4)  # Individual Camera Settings tab
            dlg.stack.setCurrentIndex(4)
        dlg.settings_saved.connect(self._on_settings_saved)
        dlg.camera_connection_updated.connect(self.apply_camera_connection_update)
        dlg.exec()

    def _on_settings_saved(self, new_settings: dict):
        # 1. Persist camera-specific overrides and updated camera connection profiles
        cam_overrides = new_settings.pop("camera_overrides", {})
        if cam_overrides:
            self.device_manager.batch_update_camera_settings(cam_overrides)

        updated_cams = new_settings.pop("updated_cameras", None)

        # 2. Update and save global app settings immediately to guarantee persistence
        layout_req = new_settings.get("default_layout")
        self.app_settings.update(new_settings)
        self.device_manager.config["app_settings"] = self.app_settings
        self.device_manager.save_config()

        # 3. Apply layout change immediately if updated in settings dialog
        if layout_req and layout_req != getattr(self, "current_layout", "2x2"):
            self.set_grid_layout(layout_req)

        # 4. Safely apply live camera reconnects
        if updated_cams:
            for c in updated_cams:
                try:
                    self.apply_camera_connection_update(c)
                except Exception as e:
                    print(f"Notice: Background stream refresh for camera {c.get('name', 'Camera')}: {e}")

        # 3. Dynamic Theme Switching (only if actually changed)
        theme_name = new_settings.get("theme", "Cyber Dark")
        if getattr(self, "_current_theme_name", None) != theme_name:
            self._current_theme_name = theme_name
            self.setStyleSheet(get_theme_qss(theme_name))

        # 4. Banner duration & cooldown
        if "banner_duration_sec" in new_settings:
            self.alarm_banner_timer.setInterval(int(new_settings["banner_duration_sec"] * 1000))

        # 5. Update Quality & Motion state
        q = new_settings.get("default_quality", QualityMode.ULTRA_MAX)
        self.set_global_quality(q)

        if "master_alerts_enabled" in new_settings:
            self.master_alerts_enabled = bool(new_settings["master_alerts_enabled"])
            self._update_master_alerts_btn_style()

        self.global_motion_enabled = new_settings.get("motion_enabled", True)
        self.motion_sound_enabled = new_settings.get("motion_sound", False)
        self._update_motion_btn_style()

        # 6. Audible Alarms State
        self.sound_alarms_enabled = new_settings.get("sound_alarms_enabled", True)
        if hasattr(self, "btn_sound_alarm"):
            is_wide = (self.width() >= 1550) if hasattr(self, "width") else True
            if self.sound_alarms_enabled:
                self.btn_sound_alarm.setText(" Siren: ON" if is_wide else "")
                self.btn_sound_alarm.setIcon(create_topbar_icon("siren", active=True, size=16, custom_color="#f87171"))
                self.btn_sound_alarm.setStyleSheet("")
                self.btn_sound_alarm.setToolTip("Audio sirens active (Click to Mute)")
            else:
                self.btn_sound_alarm.setText(" Siren: OFF" if is_wide else "")
                self.btn_sound_alarm.setIcon(create_topbar_icon("siren", active=False, size=16, custom_color="#94a3b8"))
                self.btn_sound_alarm.setStyleSheet("background-color: rgba(127, 29, 29, 0.45); color: #fca5a5; border-color: #ef4444;")
                self.btn_sound_alarm.setToolTip("Audio sirens muted (Click to Enable)")

        # 6.5 Apply layout change if modified
        new_lay = new_settings.get("default_layout")
        if new_lay and new_lay != self.current_layout:
            self.set_grid_layout(new_lay)

        # 7. Apply effective individual settings to all active stream workers
        for s_id, worker in self.active_workers.items():
            cam = next((c for c in self.device_manager.get_cameras() if any(s.get("id") == s_id for s in c.get("streams", []))), None)
            cam_id = cam.get("id") if cam else ""
            eff = self.device_manager.get_effective_camera_settings(cam_id)
            worker.apply_camera_settings(eff)
            worker.flip_horizontal = eff.get("flip_horizontal", False)
            worker.flip_vertical = eff.get("flip_vertical", False)

        # Update exclusion zones and overlays on all active video tiles
        for tile in self.video_tiles:
            if tile.stream_id:
                cam_id = tile.stream_info.get("camera_id") if tile.stream_info else None
                tile.exclusion_zones = self.device_manager.get_stream_exclusion_zones(tile.stream_id, cam_id)
                tile._update_zone_count_label()
                tile._update_ignore_zone_btn_style()
                tile.update()

        # 6.8 Apply Performance & CPU Throttling
        perf_prof = new_settings.get("performance_profile", "medium")
        rm = get_resource_manager()
        eff_perf = rm.apply_profile(perf_prof, custom_settings=new_settings)
        if hasattr(self, "cmb_perf_profile_bar"):
            idx = self.cmb_perf_profile_bar.findData(perf_prof)
            if idx >= 0:
                self.cmb_perf_profile_bar.blockSignals(True)
                self.cmb_perf_profile_bar.setCurrentIndex(idx)
                self.cmb_perf_profile_bar.blockSignals(False)

        # Apply throttling settings to all active stream workers
        for worker in self.active_workers.values():
            worker.set_performance_throttling(
                display_fps_cap=new_settings.get("display_fps_cap", 15),
                ai_skip_frames=new_settings.get("ai_skip_frames", 6),
                ai_motion_gated_only=new_settings.get("ai_motion_gated_only", False),
                motion_skip_frames=new_settings.get("motion_skip_frames", 1),
                motion_downscale_width=new_settings.get("motion_downscale_width", 480)
            )
        self._update_cpu_monitor()

        # 6.9 Storage Paths & Storage Quota
        snap_dir = new_settings.get("snapshot_dir")
        rec_dir = new_settings.get("recording_dir")
        if snap_dir or rec_dir:
            self.alert_manager.update_storage_paths(snapshot_dir=snap_dir, recording_dir=rec_dir)

        quota_gb = new_settings.get("storage_quota_gb", 0)
        auto_purge = new_settings.get("auto_purge_on_quota", False)
        if quota_gb > 0 and auto_purge:
            def _async_quota_worker():
                try:
                    purged, freed = self.alert_manager.enforce_quota(quota_gb)
                    if purged > 0:
                        freed_mb = freed / (1024 * 1024)
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(0, lambda: self.statusBar().showMessage(f" Quota Enforced: purged {purged} oldest alerts ({freed_mb:.1f} MB freed).", 5000))
                except Exception as e:
                    print(f"[QuotaWorker] Error: {e}")
            threading.Thread(target=_async_quota_worker, daemon=True, name="AsyncQuotaWorker").start()

        self.alert_manager.set_app_settings(self.app_settings)
        self._update_retention_button_label()

        self.statusBar().showMessage(f"Settings & Performance Profile successfully saved and applied!", 4000)

    def apply_camera_connection_update(self, cam_data: dict):
        """
        Dynamically applies updated IP, port, credentials, and stream URLs to
        active streaming workers, updates video tiles, and signals live reconnects
        without requiring application restart or re-adding the camera.
        """
        if not cam_data:
            return

        cid = cam_data.get("id")
        if not cid:
            return

        # 1. Update device manager inventory and save configuration
        if not self.device_manager.update_camera(cid, cam_data):
            QMessageBox.critical(self, "Camera could not be saved",
                                 "The camera update was not saved. " + self.device_manager.last_save_error)
            return

        # 2. Refresh sidebar camera tree and signal monitor
        self._populate_camera_tree()
        self._refresh_signal_monitor_cameras()

        # 3. Update active workers and tiles for all streams belonging to this camera
        cam_name = cam_data.get("name", "Camera")
        cam_ip = cam_data.get("ip", "")
        streams = cam_data.get("streams", [])

        reconnected_stream_ids = []
        is_any_stream_on_grid = False

        for s in streams:
            s_id = s.get("id")
            s_url = s.get("url")
            s_name = f"{cam_name} - {s.get('name', 'Stream')}"
            is_lens2 = (
                s.get("channel") == 1
                or "lens2" in s_id.lower()
                or "wide" in s.get("name", "").lower()
            )
            lens_tag = "Lens2" if is_lens2 else "Lens1"

            # Check if running worker exists
            if s_id in self.active_workers:
                worker = self.active_workers[s_id]
                worker.update_connection_details(main_url=s_url, ip=cam_ip, name=s_name)
                worker.set_camera_context(cam_name, lens_tag)
                reconnected_stream_ids.append(s_id)

            # Update all video tiles assigned to this stream
            for tile in self.video_tiles:
                if getattr(tile, "stream_id", "") == s_id:
                    is_any_stream_on_grid = True
                    tile.camera_ip = cam_ip
                    tile.camera_name = cam_name
                    tile.lens_tag = lens_tag
                    try:
                        tile.update_status(f"Reconnecting to {cam_name}...", "#38bdf8")
                    except Exception:
                        pass

        # 4. If none of the camera's streams are currently streaming on the grid,
        # automatically stream them to empty slots on the grid so the user sees live video immediately!
        if not is_any_stream_on_grid and streams:
            self.add_camera_to_grid(cam_data)
        elif reconnected_stream_ids:
            self.statusBar().showMessage(f"Camera '{cam_name}' ({cam_ip}) reconnected with updated credentials.", 4000)

    def _edit_camera(self, cam):
        dlg = DeviceDialog(camera_data=cam, parent=self)
        if dlg.exec():
            updated = dlg.result_data
            self.apply_camera_connection_update(updated)
            QMessageBox.information(self, "Updated", f"Camera '{updated['name']}' updated and reconnected successfully!")

    def _delete_camera(self, cam):
        if not cam:
            return
        self.delete_camera_by_id(cam.get("id"), prompt_confirm=True)

    def delete_camera_by_id(self, camera_id: str, prompt_confirm: bool = False) -> bool:
        """Completely removes a camera from inventory, stops its streams, and clears its tiles."""
        cam = self.device_manager.get_camera_by_id(camera_id)
        if not cam:
            return False

        if prompt_confirm:
            confirm = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to remove camera '{cam.get('name')}' ({cam.get('ip')}) from the system?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return False

        # Stop workers and detach tiles for all streams belonging to this camera
        for s in cam.get("streams", []):
            s_id = s.get("id")
            if s_id in self.active_workers:
                worker = self.active_workers.pop(s_id)
                try:
                    self._retire_worker(worker)
                except Exception:
                    pass
            for tile in self.video_tiles:
                if getattr(tile, "stream_id", "") == s_id:
                    tile.clear_tile()

        self.device_manager.delete_camera(camera_id)
        self._populate_camera_tree()
        self._refresh_signal_monitor_cameras()
        if hasattr(self, "ptz_dock") and self.ptz_dock:
            self.ptz_dock.populate_cameras(self.device_manager.get_cameras())
        if hasattr(self, "intercom_dock") and self.intercom_dock:
            self.intercom_dock.populate_cameras(self.device_manager.get_cameras())
        self.statusBar().showMessage(f"Camera '{cam.get('name')}' removed from system.", 4000)
        return True

    def open_add_camera_dialog(self):
        dlg = DeviceDialog(parent=self)
        if dlg.exec():
            new_cam = dlg.result_data
            if not self.device_manager.add_camera(new_cam):
                QMessageBox.critical(self, "Camera could not be saved",
                                     "The camera was not added. " + self.device_manager.last_save_error)
                return
            self._populate_camera_tree()
            self._refresh_signal_monitor_cameras()
            assigned = self.add_camera_to_grid(new_cam)
            if assigned:
                slots_str = ", ".join(f"#{i + 1}" for i in assigned)
                self.statusBar().showMessage(f"Camera '{new_cam['name']}' added to empty Slot(s): {slots_str}", 6000)
            else:
                self.statusBar().showMessage(f"Camera '{new_cam['name']}' added successfully!", 4000)

    def open_scanner_dialog(self):
        dlg = ScannerDialog(parent=self)
        dlg.camera_selected.connect(self._on_scanner_device_selected)
        dlg.exec()

    def _on_scanner_device_selected(self, dev):
        ip = dev.get("ip")
        template = {
            "name": f"Camera ({ip})",
            "ip": ip,
            "port": 554,
            "username": "admin",
            "password": "",
            "is_dual_lens": False
        }
        dlg = DeviceDialog(camera_data=template, parent=self)
        if dlg.exec():
            new_cam = dlg.result_data
            if not self.device_manager.add_camera(new_cam):
                QMessageBox.critical(self, "Camera could not be saved",
                                     "The camera was not added. " + self.device_manager.last_save_error)
                return
            self._populate_camera_tree()
            self._refresh_signal_monitor_cameras()
            self.add_camera_to_grid(new_cam)

    def open_gallery_dialog(self):
        from ui.components.gallery_dialog import GalleryDialog
        rec_dir = self.app_settings.get("recording_dir", "recordings")
        snap_dir = self.app_settings.get("snapshot_dir", "snapshots")
        gdrive_folder = self.app_settings.get("google_drive_folder")
        dlg = GalleryDialog(
            snapshot_dir=snap_dir,
            recording_dir=rec_dir,
            google_drive_dir=gdrive_folder or rec_dir,
            alert_manager=self.alert_manager,
            parent=self
        )
        dlg.exec()

    def open_video_player(self, media_source: Any = None):
        """Launches the integrated in-client video player dialog."""
        if not media_source:
            self.open_gallery_dialog()
            return
        try:
            from ui.components.video_player_dialog import VideoPlayerDialog
            dlg = VideoPlayerDialog(media_source, parent=self)
            self.active_video_player = dlg
            dlg.exec()
            self.active_video_player = None
        except Exception as e:
            self.active_video_player = None
            QMessageBox.warning(self, "Player Error", f"Failed to open in-client video player:\n{e}")

    def open_phone_access_dialog(self):
        """Launches the tactical Phone Access & Remote Streaming Hub dialog."""
        try:
            from ui.components.phone_access_dialog import PhoneAccessDialog
            dlg = PhoneAccessDialog(self, parent=self)
            dlg.notifications_toggled.connect(lambda v: self._update_phone_btn_status())
            dlg.exec()
            self._update_phone_btn_status()
        except Exception as e:
            QMessageBox.warning(self, "Phone Hub Error", f"Failed to open Phone Access Hub:\n{e}")

    def _show_phone_btn_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0d1527;
                color: #f8fafc;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
        """)
        is_on = bool(self.app_settings.get("phone_notifications_enabled", True))
        toggle_label = "Mute Mobile Notifications" if is_on else "Activate Mobile Notifications"
        act_toggle = menu.addAction(f"{toggle_label}")
        act_open = menu.addAction("Open Mobile Hub & QR Code...")

        chosen = menu.exec(self.btn_phone.mapToGlobal(pos))
        if chosen == act_toggle:
            self.toggle_mobile_notifications()
        elif chosen == act_open:
            self.open_phone_access_dialog()

    def toggle_mobile_notifications(self, enabled: Optional[bool] = None) -> bool:
        """Toggles global mobile notifications (ntfy & Telegram) and saves state."""
        if enabled is None:
            enabled = not bool(self.app_settings.get("phone_notifications_enabled", True))
        self.app_settings["phone_notifications_enabled"] = bool(enabled)
        if hasattr(self, "device_manager") and self.device_manager:
            self.device_manager.save_config()
        if hasattr(self, "alert_manager") and self.alert_manager:
            self.alert_manager.set_app_settings(self.app_settings)
        self._update_phone_btn_status()
        status_txt = "Active (Broadcasting alerts & video clips)" if enabled else "Muted (Mobile alerts paused)"
        self.statusBar().showMessage(f"Mobile Notifications: {status_txt}", 4000)
        return bool(enabled)

    def _update_phone_btn_status(self):
        """Updates the top-bar Mobile Access button text & tooltip based on push state."""
        if not hasattr(self, "btn_phone"):
            return
        is_on = bool(self.app_settings.get("phone_notifications_enabled", True))
        is_wide = (self.width() >= 1550) if hasattr(self, "width") else True
        if is_on:
            self.btn_phone.setText(" Mobile" if is_wide else "")
            self.btn_phone.setToolTip("Mobile Phone Hub & Notifications: ACTIVE\nClick to open | Right-click to mute notifications")
            self.btn_phone.setIcon(create_topbar_icon("mobile", size=16, custom_color="#38bdf8"))
        else:
            self.btn_phone.setText(" Muted" if is_wide else "")
            self.btn_phone.setToolTip("Mobile Phone Hub & Notifications: MUTED\nClick to open | Right-click to activate notifications")
            self.btn_phone.setIcon(create_topbar_icon("mobile", size=16, custom_color="#94a3b8"))


    def _apply_window_corners(self):
        """
        Applies smooth anti-aliased rounded window corners when floating/windowed,
        and seamlessly restores sharp 0px flush corners when maximized or fullscreen.
        Integrates Windows 11 DWM native corner preferences (DWMWA_WINDOW_CORNER_PREFERENCE).
        """
        is_max = self.is_window_maximized() or getattr(self, "is_fullscreen", False)
        if sys.platform == "win32":
            try:
                DWMWA_WINDOW_CORNER_PREFERENCE = 33
                DWMWCP_ROUND = 2
                DWMWCP_DONOTROUND = 1
                pref = ctypes.c_int(DWMWCP_DONOTROUND if is_max else DWMWCP_ROUND)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    int(self.winId()),
                    DWMWA_WINDOW_CORNER_PREFERENCE,
                    ctypes.byref(pref),
                    ctypes.sizeof(pref)
                )
            except Exception:
                pass

        if hasattr(self, "central_widget") and self.central_widget and self.central_widget.layout():
            if is_max:
                self.central_widget.layout().setContentsMargins(0, 0, 0, 0)
            else:
                self.central_widget.layout().setContentsMargins(1, 0, 1, 1)

        if hasattr(self, "top_bar") and self.top_bar:
            r_top = "0px" if is_max else "14px"
            self.top_bar.setStyleSheet(f"#top_bar {{ border-top-left-radius: {r_top}; border-top-right-radius: {r_top}; }}")

        if hasattr(self, "sidebar") and self.sidebar:
            r_side = "0px" if is_max else "13px"
            pos = self.app_settings.get("sidebar_position", "left")
            if pos == "right":
                self.sidebar.setStyleSheet(f"#left_sidebar {{ border-bottom-right-radius: {r_side}; border-bottom-left-radius: 0px; }}")
            else:
                self.sidebar.setStyleSheet(f"#left_sidebar {{ border-bottom-left-radius: {r_side}; border-bottom-right-radius: 0px; }}")

        if hasattr(self, "grid_container") and self.grid_container:
            r_grid = "0px" if is_max else "13px"
            pos = self.app_settings.get("sidebar_position", "left")
            if pos == "right":
                self.grid_container.setStyleSheet(f"QWidget#grid_container {{ border-bottom-left-radius: {r_grid}; border-bottom-right-radius: 0px; background-color: transparent; }}")
            else:
                self.grid_container.setStyleSheet(f"QWidget#grid_container {{ border-bottom-right-radius: {r_grid}; border-bottom-left-radius: 0px; background-color: transparent; }}")

        if hasattr(self, "central_widget") and self.central_widget:
            self.central_widget.update()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_window_corners()

    def is_window_maximized(self) -> bool:
        return getattr(self, "_is_custom_maximized", False) or self.isMaximized()

    def _toggle_maximize_restore(self):
        """
        Smooth, glitch-free window maximization honoring desktop work area.
        Bypasses Windows DWM 8px frameless off-screen bleed and eliminates stylesheet recalculations.
        """
        if self.is_window_maximized():
            # Restore down smoothly
            if hasattr(self, "_normal_geometry") and self._normal_geometry:
                self.setGeometry(self._normal_geometry)
            else:
                self.resize(1360, 820)
            self._is_custom_maximized = False
            if hasattr(self, "btn_win_max"):
                self.btn_win_max.setIcon(create_topbar_icon("win_max", size=16))
                self.btn_win_max.setToolTip("Maximize Window")
        else:
            # Maximize cleanly to current screen's available geometry (fits perfectly within taskbar area)
            self._normal_geometry = self.geometry()
            screen = self.screen() or QApplication.primaryScreen()
            if screen:
                avail = screen.availableGeometry()
                self.setGeometry(avail)
            self._is_custom_maximized = True
            if hasattr(self, "btn_win_max"):
                self.btn_win_max.setIcon(create_topbar_icon("win_restore", size=16))
                self.btn_win_max.setToolTip("Restore Down")

        self._apply_window_corners()

    def changeEvent(self, event):
        """
        Smart Window State & Inactivity Optimization:
        - When minimized: Pauses all GUI rendering & paint emissions to 0 FPS, leaving 100% of GPU/DWM to games.
        - When unfocused/background: Throttles display rate to 5 FPS to protect active apps and games.
        - When focused: Instantly restores full configured framerate.
        - Tracks maximized / normal window state without destructive stylesheet resets.
        """
        if event.type() == QEvent.Type.WindowStateChange:
            is_min = self.isMinimized()
            is_max = self.is_window_maximized()
            if hasattr(self, "btn_win_max"):
                self.btn_win_max.setIcon(create_topbar_icon("win_restore" if is_max else "win_max", size=16))
                self.btn_win_max.setToolTip("Restore Down" if is_max else "Maximize Window")
            self._apply_window_corners()
            for worker in self.active_workers.values():
                worker.set_gui_rendering_paused(is_min)
            if hasattr(self, "stats_timer"):
                self.stats_timer.setInterval(5000 if is_min else 1000)
        elif event.type() == QEvent.Type.ActivationChange:
            is_active = self.isActiveWindow()
            for worker in self.active_workers.values():
                worker.set_background_throttle(not is_active)
        super().changeEvent(event)

    def eventFilter(self, watched, event):
        if watched == getattr(self, "top_bar", None):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                child = self.top_bar.childAt(event.pos())
                if not (child and isinstance(child, (QPushButton, QComboBox, QLineEdit))):
                    if self.is_window_maximized():
                        # Dragging from maximized restores normal window geometry under mouse smoothly
                        self._is_custom_maximized = False
                        if hasattr(self, "btn_win_max"):
                            self.btn_win_max.setIcon(create_topbar_icon("win_max", size=16))
                            self.btn_win_max.setToolTip("Maximize Window")
                        if hasattr(self, "_normal_geometry") and self._normal_geometry:
                            norm_w = self._normal_geometry.width()
                            click_x = event.pos().x()
                            ratio = click_x / max(self.width(), 1)
                            new_x = int(event.globalPosition().x() - (norm_w * ratio))
                            new_y = int(event.globalPosition().y() - event.pos().y())
                            self.setGeometry(new_x, new_y, norm_w, self._normal_geometry.height())
                        self._apply_window_corners()
                    wh = self.windowHandle()
                    if wh and not getattr(self, "is_fullscreen", False):
                        wh.startSystemMove()
                        return True
            elif event.type() == QEvent.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
                child = self.top_bar.childAt(event.pos())
                if not (child and isinstance(child, (QPushButton, QComboBox, QLineEdit))):
                    if not getattr(self, "is_fullscreen", False):
                        self._toggle_maximize_restore()
                        return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_window_maximized() and not getattr(self, "is_fullscreen", False):
            edge = self._get_resize_edge(event.pos())
            if edge:
                wh = self.windowHandle()
                if wh:
                    wh.startSystemResize(edge)
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.is_window_maximized() and not getattr(self, "is_fullscreen", False):
            edge = self._get_resize_edge(event.pos())
            self._update_resize_cursor(edge)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def _get_resize_edge(self, pos: QPoint):
        w = self.width()
        h = self.height()
        b = 6
        x = pos.x()
        y = pos.y()

        edge_val = 0
        if x < b:
            edge_val |= Qt.Edge.LeftEdge.value
        elif x > w - b:
            edge_val |= Qt.Edge.RightEdge.value

        if y < b:
            edge_val |= Qt.Edge.TopEdge.value
        elif y > h - b:
            edge_val |= Qt.Edge.BottomEdge.value

        return Qt.Edge(edge_val) if edge_val != 0 else None

    def _update_resize_cursor(self, edge: Optional[Qt.Edge]):
        if edge is None:
            self.unsetCursor()
            return
        val = edge.value
        left = bool(val & Qt.Edge.LeftEdge.value)
        right = bool(val & Qt.Edge.RightEdge.value)
        top = bool(val & Qt.Edge.TopEdge.value)
        bottom = bool(val & Qt.Edge.BottomEdge.value)

        if (top and left) or (bottom and right):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif (top and right) or (bottom and left):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif left or right:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif top or bottom:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.unsetCursor()

    def _minimize_to_tray(self, event):
        """Hides the workstation to the system tray while keeping 24/7 background recording active."""
        self.save_session_state()
        event.ignore()
        self.hide()
        if getattr(self, "tray_icon", None) and self.tray_icon.isVisible():
            if not getattr(self, "_tray_notified_once", False):
                self._tray_notified_once = True
                self.tray_icon.showMessage(
                    "CCTVPanelView",
                    "Application continues running and recording 24/7 in the background.\nDouble-click the tray icon to restore the window.",
                    QSystemTrayIcon.MessageIcon.Information,
                    3500
                )

    def _execute_full_quit(self, event):
        """Safely stops all worker threads, flushes pending recordings and configs, and quits the application."""
        restore_windows_sleep()

        # 1. Stop background servers and timers
        if hasattr(self, "web_server") and self.web_server:
            self.web_server.stop()
        if hasattr(self, "cpu_monitor_timer") and self.cpu_monitor_timer.isActive():
            self.cpu_monitor_timer.stop()
        if hasattr(self, "signal_monitor") and self.signal_monitor:
            self.signal_monitor.stop()
        if hasattr(self, "ptz_dock") and self.ptz_dock:
            self.ptz_dock.clear_camera()
        if hasattr(self, "intercom_dock") and self.intercom_dock:
            self.intercom_dock.clear_camera()

        # 2. Smart Graceful Media Finalization: Save any pending snapshots, active clips, and recordings
        workers = list(self.active_workers.values()) + list(getattr(self, "_retiring_workers", ()))
        for worker in workers:
            try:
                worker.flush_pending_snapshots()
            except Exception:
                pass
            try:
                worker.stop_recording(wait=True, timeout=1.5)
            except Exception:
                pass
            try:
                worker.stop_all_alert_sessions(wait=True)
            except Exception:
                pass
            worker._running = False
            capture = worker._capture
            if capture is not None:
                capture.interrupt()

        # 3. Synchronously persist full session state, alert history, cards, and camera configurations to disk
        self.save_session_state()
        if hasattr(self, "alert_manager") and self.alert_manager:
            try:
                self.alert_manager.flush_and_save_sync()
            except Exception:
                pass

        if hasattr(self, "device_manager") and self.device_manager:
            try:
                self.device_manager.save_config()
            except Exception:
                pass

        # 4. Parallel worker thread join with bounded safety timeout
        for worker in workers:
            try:
                worker.wait(400)
            except Exception:
                pass

        event.accept()
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.quit()

    def closeEvent(self, event):
        """
        Handles workstation close (X button or Alt+F4):
        - If force quit from tray menu: quits immediately.
        - If user checked 'Remember my choice': performs remembered action ('tray' or 'quit').
        - Otherwise: presents CloseConfirmDialog with 'Hide in Tray' or 'Quit Completely' options.
        """
        if getattr(self, "_allow_force_quit", False):
            self._execute_full_quit(event)
            return

        remember = bool(self.app_settings.get("remember_close_action", False))
        close_action = self.app_settings.get("close_action", "ask")

        if remember and close_action == "tray":
            self._minimize_to_tray(event)
            return
        elif remember and close_action == "quit":
            self._execute_full_quit(event)
            return

        from ui.components.close_confirm_dialog import CloseConfirmDialog
        dlg = CloseConfirmDialog(parent=self)
        action, remember_choice = dlg.exec_dialog()

        if action == "cancel":
            event.ignore()
            return

        if remember_choice:
            self.app_settings["remember_close_action"] = True
            self.app_settings["close_action"] = action
            self.device_manager.config["app_settings"] = self.app_settings
            self.device_manager.save_config()

        if action == "tray":
            self._minimize_to_tray(event)
        elif action == "quit":
            self._execute_full_quit(event)
        else:
            event.ignore()
