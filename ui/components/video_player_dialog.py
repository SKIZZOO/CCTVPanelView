import os
import sys
import re
import shutil
from datetime import datetime
from typing import Optional, Dict, Any, List

import cv2
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QWidget, QFrame, QSizePolicy, QMessageBox,
    QStackedLayout, QProgressBar, QStyle, QApplication, QFileDialog
)
from PyQt6.QtCore import Qt, QUrl, QTime, QTimer, pyqtSignal, QPoint, QObject, QEvent, QPointF, QSize, QRectF
from PyQt6.QtGui import (
    QIcon, QFont, QKeySequence, QPixmap, QShortcut, QImage,
    QMouseEvent, QPainter, QColor, QPainterPath, QPen, QBrush
)

try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    HAS_QT_MULTIMEDIA = True
except ImportError:
    HAS_QT_MULTIMEDIA = False


def create_player_icon(name: str, size: int = 18, color: str = "#e2e8f0", active: bool = False) -> QIcon:
    """
    Renders ultra-crisp vector micro-icons for Apple Glass & Windows 11 Fluent video player controls.
    Zero fuzzy raster emojis or pixelation.
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    c = QColor("#38bdf8" if active else color)
    pen = QPen(c, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    brush = QBrush(c)
    painter.setPen(pen)

    s = float(size)
    pad = s * 0.16
    w = s - 2 * pad
    h = s - 2 * pad

    if name == "play":
        path = QPainterPath()
        path.moveTo(pad + w * 0.22, pad)
        path.lineTo(pad + w * 0.9, pad + h * 0.5)
        path.lineTo(pad + w * 0.22, pad + h)
        path.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path)

    elif name == "pause":
        bar_w = w * 0.26
        gap = w * 0.22
        left1 = pad + (w - 2 * bar_w - gap) / 2
        left2 = left1 + bar_w + gap
        painter.setBrush(brush)
        painter.drawRoundedRect(QRectF(left1, pad, bar_w, h), 1.5, 1.5)
        painter.drawRoundedRect(QRectF(left2, pad, bar_w, h), 1.5, 1.5)

    elif name == "prev_clip":
        bar_w = w * 0.15
        painter.setBrush(brush)
        painter.drawRoundedRect(QRectF(pad, pad, bar_w, h), 1.0, 1.0)
        path = QPainterPath()
        path.moveTo(pad + w, pad)
        path.lineTo(pad + bar_w + w * 0.1, pad + h * 0.5)
        path.lineTo(pad + w, pad + h)
        path.closeSubpath()
        painter.drawPath(path)

    elif name == "next_clip":
        bar_w = w * 0.15
        path = QPainterPath()
        path.moveTo(pad, pad)
        path.lineTo(pad + w - bar_w - w * 0.1, pad + h * 0.5)
        path.lineTo(pad, pad + h)
        path.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path)
        painter.drawRoundedRect(QRectF(pad + w - bar_w, pad, bar_w, h), 1.0, 1.0)

    elif name == "frame_back":
        painter.drawLine(QPointF(pad, pad), QPointF(pad, pad + h))
        path = QPainterPath()
        path.moveTo(pad + w * 0.85, pad)
        path.lineTo(pad + w * 0.25, pad + h * 0.5)
        path.lineTo(pad + w * 0.85, pad + h)
        painter.drawPath(path)

    elif name == "frame_fwd":
        path = QPainterPath()
        path.moveTo(pad + w * 0.15, pad)
        path.lineTo(pad + w * 0.75, pad + h * 0.5)
        path.lineTo(pad + w * 0.15, pad + h)
        painter.drawPath(path)
        painter.drawLine(QPointF(pad + w, pad), QPointF(pad + w, pad + h))

    elif name == "step_back":
        path = QPainterPath()
        path.moveTo(pad + w * 0.5, pad + h * 0.1)
        path.lineTo(pad + w * 0.1, pad + h * 0.5)
        path.lineTo(pad + w * 0.5, pad + h * 0.9)
        path.moveTo(pad + w * 0.9, pad + h * 0.1)
        path.lineTo(pad + w * 0.5, pad + h * 0.5)
        path.lineTo(pad + w * 0.9, pad + h * 0.9)
        painter.drawPath(path)

    elif name == "step_fwd":
        path = QPainterPath()
        path.moveTo(pad + w * 0.1, pad + h * 0.1)
        path.lineTo(pad + w * 0.5, pad + h * 0.5)
        path.lineTo(pad + w * 0.1, pad + h * 0.9)
        path.moveTo(pad + w * 0.5, pad + h * 0.1)
        path.lineTo(pad + w * 0.9, pad + h * 0.5)
        path.lineTo(pad + w * 0.5, pad + h * 0.9)
        painter.drawPath(path)

    elif name == "clapper":
        painter.drawRoundedRect(QRectF(pad, pad + h * 0.35, w, h * 0.65), 2.0, 2.0)
        painter.drawLine(QPointF(pad, pad + h * 0.35), QPointF(pad + w, pad + h * 0.35))
        painter.drawLine(QPointF(pad, pad + h * 0.1), QPointF(pad + w, pad + h * 0.1))
        painter.drawLine(QPointF(pad + w * 0.3, pad + h * 0.1), QPointF(pad + w * 0.2, pad + h * 0.35))
        painter.drawLine(QPointF(pad + w * 0.6, pad + h * 0.1), QPointF(pad + w * 0.5, pad + h * 0.35))
        painter.drawLine(QPointF(pad + w * 0.9, pad + h * 0.1), QPointF(pad + w * 0.8, pad + h * 0.35))

    elif name == "camera":
        body_y = pad + h * 0.22
        body_h = h * 0.78
        painter.drawRoundedRect(QRectF(pad, body_y, w, body_h), 2.5, 2.5)
        painter.drawRoundedRect(QRectF(pad + w * 0.3, pad, w * 0.4, h * 0.25), 1.5, 1.5)
        lens_r = min(w, body_h) * 0.26
        painter.drawEllipse(QPointF(pad + w * 0.5, body_y + body_h * 0.5), lens_r, lens_r)

    elif name == "loop":
        arc_rect = QRectF(pad + 1, pad + 1, w - 2, h - 2)
        painter.drawArc(arc_rect, 45 * 16, 260 * 16)
        arrow_tip = QPointF(pad + w * 0.85, pad + h * 0.2)
        painter.drawLine(arrow_tip, QPointF(pad + w * 0.6, pad + h * 0.1))
        painter.drawLine(arrow_tip, QPointF(pad + w * 0.85, pad + h * 0.45))

    elif name == "volume":
        path = QPainterPath()
        path.moveTo(pad, pad + h * 0.3)
        path.lineTo(pad + w * 0.35, pad + h * 0.3)
        path.lineTo(pad + w * 0.6, pad + h * 0.05)
        path.lineTo(pad + w * 0.6, pad + h * 0.95)
        path.lineTo(pad + w * 0.35, pad + h * 0.7)
        path.lineTo(pad, pad + h * 0.7)
        path.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path)
        arc_rect = QRectF(pad + w * 0.4, pad + h * 0.2, w * 0.5, h * 0.6)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(arc_rect, -50 * 16, 100 * 16)

    elif name == "volume_mute":
        path = QPainterPath()
        path.moveTo(pad, pad + h * 0.3)
        path.lineTo(pad + w * 0.35, pad + h * 0.3)
        path.lineTo(pad + w * 0.6, pad + h * 0.05)
        path.lineTo(pad + w * 0.6, pad + h * 0.95)
        path.lineTo(pad + w * 0.35, pad + h * 0.7)
        path.lineTo(pad, pad + h * 0.7)
        path.closeSubpath()
        painter.setBrush(brush)
        painter.drawPath(path)
        slash_pen = QPen(QColor("#ef4444"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(slash_pen)
        painter.drawLine(QPointF(pad + w * 0.65, pad + h * 0.2), QPointF(pad + w * 0.95, pad + h * 0.8))

    elif name == "export":
        painter.drawLine(QPointF(pad, pad + h * 0.5), QPointF(pad, pad + h))
        painter.drawLine(QPointF(pad, pad + h), QPointF(pad + w, pad + h))
        painter.drawLine(QPointF(pad + w, pad + h), QPointF(pad + w, pad + h * 0.5))
        painter.drawLine(QPointF(pad + w * 0.5, pad), QPointF(pad + w * 0.5, pad + h * 0.7))
        painter.drawLine(QPointF(pad + w * 0.2, pad + h * 0.35), QPointF(pad + w * 0.5, pad))
        painter.drawLine(QPointF(pad + w * 0.8, pad + h * 0.35), QPointF(pad + w * 0.5, pad))

    elif name == "delete":
        painter.drawLine(QPointF(pad + w * 0.15, pad + h * 0.25), QPointF(pad + w * 0.85, pad + h * 0.25))
        painter.drawLine(QPointF(pad + w * 0.35, pad + h * 0.15), QPointF(pad + w * 0.65, pad + h * 0.15))
        path = QPainterPath()
        path.moveTo(pad + w * 0.22, pad + h * 0.25)
        path.lineTo(pad + w * 0.28, pad + h * 0.95)
        path.lineTo(pad + w * 0.72, pad + h * 0.95)
        path.lineTo(pad + w * 0.78, pad + h * 0.25)
        painter.drawPath(path)
        painter.drawLine(QPointF(pad + w * 0.42, pad + h * 0.4), QPointF(pad + w * 0.42, pad + h * 0.8))
        painter.drawLine(QPointF(pad + w * 0.58, pad + h * 0.4), QPointF(pad + w * 0.58, pad + h * 0.8))

    elif name == "folder":
        path = QPainterPath()
        path.moveTo(pad, pad + h * 0.25)
        path.lineTo(pad + w * 0.35, pad + h * 0.25)
        path.lineTo(pad + w * 0.48, pad + h * 0.4)
        path.lineTo(pad + w, pad + h * 0.4)
        path.lineTo(pad + w, pad + h * 0.95)
        path.lineTo(pad, pad + h * 0.95)
        path.closeSubpath()
        painter.drawPath(path)

    elif name == "fullscreen":
        arm = w * 0.28
        painter.drawLine(QPointF(pad, pad + arm), QPointF(pad, pad))
        painter.drawLine(QPointF(pad, pad), QPointF(pad + arm, pad))
        painter.drawLine(QPointF(pad + w - arm, pad), QPointF(pad + w, pad))
        painter.drawLine(QPointF(pad + w, pad), QPointF(pad + w, pad + arm))
        painter.drawLine(QPointF(pad, pad + h - arm), QPointF(pad, pad + h))
        painter.drawLine(QPointF(pad, pad + h), QPointF(pad + arm, pad + h))
        painter.drawLine(QPointF(pad + w - arm, pad + h), QPointF(pad + w, pad + h))
        painter.drawLine(QPointF(pad + w, pad + h), QPointF(pad + w, pad + h - arm))

    elif name == "fullscreen_exit":
        arm = w * 0.25
        painter.drawLine(QPointF(pad + arm, pad), QPointF(pad + arm, pad + arm))
        painter.drawLine(QPointF(pad + arm, pad + arm), QPointF(pad, pad + arm))
        painter.drawLine(QPointF(pad + w - arm, pad), QPointF(pad + w - arm, pad + arm))
        painter.drawLine(QPointF(pad + w - arm, pad + arm), QPointF(pad + w, pad + arm))
        painter.drawLine(QPointF(pad + arm, pad + h), QPointF(pad + arm, pad + h - arm))
        painter.drawLine(QPointF(pad + arm, pad + h - arm), QPointF(pad, pad + h - arm))
        painter.drawLine(QPointF(pad + w - arm, pad + h), QPointF(pad + w - arm, pad + h - arm))
        painter.drawLine(QPointF(pad + w - arm, pad + h - arm), QPointF(pad + w, pad + h - arm))

    elif name == "close":
        painter.drawLine(QPointF(pad + 1, pad + 1), QPointF(pad + w - 1, pad + h - 1))
        painter.drawLine(QPointF(pad + w - 1, pad + 1), QPointF(pad + 1, pad + h - 1))

    elif name == "zoom":
        r = min(w, h) * 0.32
        cx = pad + r + 1
        cy = pad + r + 1
        painter.drawEllipse(QPointF(cx, cy), r, r)
        painter.drawLine(QPointF(cx + r * 0.7, cy + r * 0.7), QPointF(pad + w, pad + h))

    painter.end()
    return QIcon(pix)


PLAYER_GLASS_BTN_STYLE = """
QPushButton {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 15px;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    padding: 0;
}
QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.18);
    border-color: rgba(255, 255, 255, 0.28);
}
QPushButton:pressed {
    background-color: rgba(56, 189, 248, 0.25);
    border-color: #38bdf8;
}
QPushButton:disabled {
    background-color: rgba(255, 255, 255, 0.02);
    border-color: rgba(255, 255, 255, 0.04);
}
"""

PLAYER_HERO_PLAY_STYLE = """
QPushButton#btn_play {
    background-color: #ffffff;
    border: none;
    border-radius: 21px;
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
    padding: 0;
}
QPushButton#btn_play:hover {
    background-color: #e0f2fe;
}
QPushButton#btn_play:pressed {
    background-color: #bae6fd;
}
QPushButton#btn_play:disabled {
    background-color: rgba(255, 255, 255, 0.2);
}
"""

PLAYER_PILL_BTN_STYLE = """
QPushButton {
    background-color: rgba(255, 255, 255, 0.08);
    color: #e2e8f0;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.18);
    border-color: rgba(255, 255, 255, 0.28);
    color: #ffffff;
}
QPushButton:pressed {
    background-color: rgba(56, 189, 248, 0.25);
    border-color: #38bdf8;
}
QPushButton:disabled {
    background-color: rgba(255, 255, 255, 0.02);
    color: #475569;
    border-color: rgba(255, 255, 255, 0.04);
}
"""


class SmartTimelineSlider(QSlider):
    """
    Forensic timeline scrubber:
    - Jumps directly to clicked playhead position instantly.
    - Hover tooltip previews exact timestamp and frame index.
    """
    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None, player=None):
        super().__init__(orientation, parent)
        self.player = player
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            val = int(QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(),
                int(event.position().x()), self.width()
            ))
            self.setValue(val)
            self.sliderMoved.emit(val)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.player and hasattr(self.player, "media_player") and self.player.media_player.duration() > 0:
            val = int(QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(),
                int(event.position().x()), self.width()
            ))
            dur = self.player.media_player.duration()
            pos = int((val / 1000.0) * dur)
            fps = getattr(self.player, "video_fps", 15.0)
            frame_idx = int(round((pos / 1000.0) * fps)) + 1
            time_str = self.player._format_ms_precise(pos)
            tot_frames = getattr(self.player, "total_frames", 0)
            frame_label = f"Frame {frame_idx}/{tot_frames}" if tot_frames else f"Frame {frame_idx}"
            self.setToolTip(f"Jump to {time_str} • {frame_label}")


class VideoSurfaceFilter(QObject):
    """
    Event filter on the video output surface:
    - Single click: Smart Toggle Play / Pause.
    - Double click: Toggle Fullscreen.
    - Scroll wheel: When paused, scrubs frames smoothly (+1 / -1 frame jog).
                    When playing, adjusts volume.
                    With Ctrl held: Smooth digital zoom on paused frame.
    """
    def __init__(self, player):
        super().__init__(player)
        self.player = player
        self.click_timer = QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.setInterval(220)
        self.click_timer.timeout.connect(self._on_single_click)
        self.is_double = False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.is_double = False
                self.click_timer.start()
                return True
        elif event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                self.is_double = True
                self.click_timer.stop()
                self.player._toggle_fullscreen()
                return True
        elif event.type() == QEvent.Type.Wheel:
            delta = event.angleDelta().y()
            if delta != 0:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self.player.adjust_zoom(0.25 if delta > 0 else -0.25)
                else:
                    self.player._on_video_wheel(delta)
            return True
        return False

    def _on_single_click(self):
        if not self.is_double:
            self.player.toggle_play_pause(user_clicked_surface=True)


class ZoomCanvasWidget(QWidget):
    """
    Forensic zoom and pan canvas for inspectable high-resolution freeze frames.
    Allows forensic zooming (1.0x - 4.0x) and mouse-drag panning.
    """
    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.player = player
        self.pixmap: Optional[QPixmap] = None
        self.zoom_level = 1.0
        self.pan_offset = QPoint(0, 0)
        self.is_panning = False
        self.drag_start = QPoint(0, 0)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def set_image(self, qimg: QImage, zoom: float, pan: QPoint):
        self.pixmap = QPixmap.fromImage(qimg)
        self.zoom_level = zoom
        self.pan_offset = pan
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = True
            self.drag_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.is_panning:
            delta = event.pos() - self.drag_start
            self.drag_start = event.pos()
            self.pan_offset += delta
            self.player.zoom_pan = self.pan_offset
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, event):
        self.player.reset_zoom()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.player.adjust_zoom(0.25 if delta > 0 else -0.25)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#000000"))
        if not self.pixmap or self.pixmap.isNull():
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scaled_w = int(self.width() * self.zoom_level)
        scaled_h = int(self.height() * self.zoom_level)
        scaled = self.pixmap.scaled(scaled_w, scaled_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        dest_x = (self.width() - scaled.width()) // 2 + self.pan_offset.x()
        dest_y = (self.height() - scaled.height()) // 2 + self.pan_offset.y()
        painter.drawPixmap(dest_x, dest_y, scaled)
        painter.end()



class VideoPlayerDialog(QDialog):
    """
    Sleek, integrated in-client video player for CAM720 Revamped.
    
    Features:
    - Plays videos directly within the application (no external players needed)
    - 1-Click Toggle between [Highlighted (AI)] and [Raw Video] at the exact same playhead timestamp
    - Play / Pause (Spacebar), Scrubber Timeline Slider with smooth seeking
    - Frame-by-frame / step stepping (-1s / +1s, Arrow Keys) for forensic inspection
    - Playback speed control (0.5x Slow-Mo, 1.0x Normal, 1.5x, 2.0x)
    - Seamless incident loop toggle (Loop ON / OFF)
    - Full volume control + mute toggle
    - Fullscreen mode (F11 or Double-Click)
    - File locator ("Show in Folder")
    - Incident telemetry banner with Camera, Lens, Confidence, and Detection Description
    """
    def __init__(self, media_source: Any, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CCTVPanelView - Incident Video Player")
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(960, 640)
        self.setMinimumSize(640, 420)

        # Parse input source: can be an alert_data dict, or a direct filepath string
        self.alert_data = {}
        self.alert_id = ""
        self.unique_id = ""
        self.raw_path = ""
        self.highlighted_path = ""
        self.current_video_path = ""
        self.is_showing_highlighted = True
        self.is_looping = True
        self._user_is_sliding = False
        self.is_buffering = False
        self.buffer_poll_timer = None
        self.buffer_poll_ticks = 0

        # Smart Forensic Metrics & Frame Navigation
        self.video_fps = 15.0
        self.total_frames = 0
        self.frame_interval_ms = 66
        self.video_width = 0
        self.video_height = 0

        # Playlist & Navigation State
        self.playlist_clips: List[str] = []
        self.current_playlist_idx: int = -1

        # Forensic Digital Zoom & Pan
        self.zoom_level: float = 1.0
        self.zoom_pan: QPoint = QPoint(0, 0)

        self._parse_media_source(media_source)
        self._build_playlist()
        self._setup_ui()
        self._update_playlist_buttons()
        self._setup_shortcuts()
        self._load_current_media()

    def _parse_media_source(self, media_source: Any):
        if isinstance(media_source, dict):
            self.alert_data = media_source
            self.alert_id = str(media_source.get("id", ""))
            self.unique_id = str(media_source.get("unique_id", ""))
            self.highlighted_path = media_source.get("video_highlighted_path", "") or media_source.get("video_path", "")
            self.raw_path = media_source.get("video_raw_path", "")
            
            # If only one was provided, or if raw_path == highlighted_path, see if paired file exists on disk
            if self.highlighted_path and (not self.raw_path or os.path.abspath(self.raw_path).lower() == os.path.abspath(self.highlighted_path).lower()):
                candidate_raw = self.highlighted_path.replace("_HIGHLIGHTED", "_RAW").replace("_AI_Boxed", "_Raw")
                if os.path.exists(candidate_raw) and os.path.abspath(candidate_raw).lower() != os.path.abspath(self.highlighted_path).lower():
                    self.raw_path = candidate_raw
                else:
                    self.raw_path = ""

            if self.raw_path and (not self.highlighted_path or os.path.abspath(self.highlighted_path).lower() == os.path.abspath(self.raw_path).lower()):
                candidate_hl = self.raw_path.replace("_RAW", "_HIGHLIGHTED").replace("_Raw", "_AI_Boxed")
                if os.path.exists(candidate_hl) and os.path.abspath(candidate_hl).lower() != os.path.abspath(self.raw_path).lower():
                    self.highlighted_path = candidate_hl
                    
        elif isinstance(media_source, str):
            fpath = os.path.abspath(media_source)
            if "_HIGHLIGHTED" in fpath or "_AI_Boxed" in fpath:
                self.highlighted_path = fpath
                candidate_raw = fpath.replace("_HIGHLIGHTED", "_RAW").replace("_AI_Boxed", "_Raw")
                if os.path.exists(candidate_raw):
                    self.raw_path = candidate_raw
            elif "_RAW" in fpath or "_Raw" in fpath:
                self.raw_path = fpath
                candidate_hl = fpath.replace("_RAW", "_HIGHLIGHTED").replace("_Raw", "_AI_Boxed")
                if os.path.exists(candidate_hl):
                    self.highlighted_path = candidate_hl
            else:
                self.highlighted_path = fpath
                candidate_raw = fpath.replace(".mp4", "_RAW.mp4").replace(".mp4", "_Raw.mp4")
                if os.path.exists(candidate_raw):
                    self.raw_path = candidate_raw

        # Default to whichever video path is available
        self.is_buffering = False
        if self.highlighted_path and os.path.exists(self.highlighted_path) and os.path.getsize(self.highlighted_path) > 1024:
            self.current_video_path = self.highlighted_path
            self.is_showing_highlighted = True
        elif self.raw_path and os.path.exists(self.raw_path) and os.path.getsize(self.raw_path) > 1024:
            self.current_video_path = self.raw_path
            self.is_showing_highlighted = False
        else:
            self.current_video_path = self.highlighted_path or self.raw_path
            if isinstance(media_source, dict):
                self.is_buffering = True

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #070c18;
                color: #f1f5f9;
            }
            QLabel {
                color: #e2e8f0;
            }
            QToolTip {
                background-color: #0f172a;
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 11px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # --- Top Apple Glass Header Capsule ---
        self.header_card = QFrame(self)
        self.header_card.setObjectName("header_card")
        self.header_card.setStyleSheet("""
            QFrame#header_card {
                background: rgba(15, 23, 42, 0.78);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 18px;
            }
        """)
        header_bar = QHBoxLayout(self.header_card)
        header_bar.setContentsMargins(14, 6, 14, 6)
        header_bar.setSpacing(10)

        # Incident title & badge
        cam_name = self.alert_data.get("camera_name", "")
        lens = self.alert_data.get("lens", "")
        label = self.alert_data.get("label", "").upper()
        conf = int(self.alert_data.get("confidence", 0) * 100)
        time_str = self.alert_data.get("timestamp", "")

        # Fallback parse from filename if launched with raw video file path
        if not cam_name and self.current_video_path:
            fn = os.path.basename(self.current_video_path)
            if "fata" in fn.lower():
                cam_name = "Fata (Dual-Lens 2K)"
            elif "afara" in fn.lower():
                cam_name = "Afara"
            elif "spate" in fn.lower():
                cam_name = "Spate"
            elif "camera9d85" in fn.lower():
                cam_name = "camera9D85"
            else:
                cam_name = "CCTV Camera"

            if "lens2" in fn.lower() or "fixedwide" in fn.lower():
                lens = "Lens 2 (Fixed Wide)"
            elif "lens1" in fn.lower() or "ptz" in fn.lower():
                lens = "Lens 1 (PTZ Zoom)"
            else:
                lens = "Main Stream"

            if "person" in fn.lower():
                label = "PERSON"
                m_pct = re.search(r'(\d+)pct', fn, re.IGNORECASE)
                conf = int(m_pct.group(1)) if m_pct else 50
            elif "vehicle" in fn.lower():
                label = "VEHICLE"
            elif "animal" in fn.lower():
                label = "ANIMAL"
            elif "motion" in fn.lower():
                label = "MOTION"
            else:
                label = "RECORDING"

            m_dt = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}|\d{8}_\d{6})', fn)
            if m_dt:
                time_str = m_dt.group(1).replace('_', ' ')
            elif os.path.exists(self.current_video_path):
                time_str = datetime.fromtimestamp(os.path.getmtime(self.current_video_path)).strftime("%Y-%m-%d %H:%M:%S")

        if not cam_name:
            cam_name = "CCTV Camera"
        if not lens:
            lens = "Main Stream"
        if not label:
            label = "RECORDING"

        is_person = "person" in label.lower()
        badge_color = "#ef4444" if is_person else "#38bdf8"
        badge_bg = "rgba(239, 68, 68, 0.20)" if is_person else "rgba(56, 189, 248, 0.20)"

        icon_png = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.png")
        if os.path.exists(icon_png):
            lbl_logo = QLabel(self)
            lbl_logo.setPixmap(QPixmap(icon_png).scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            lbl_logo.setFixedSize(22, 22)
            lbl_logo.setStyleSheet("background: transparent; margin-right: 2px;")
            header_bar.addWidget(lbl_logo)

        self.lbl_incident_badge = QLabel(f"● {label} {conf}%" if conf > 0 else f"● {label}", self)
        self.lbl_incident_badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_color};
            font-weight: 700;
            font-size: 11px;
            border: none;
            border-radius: 11px;
            padding: 3px 10px;
        """)
        header_bar.addWidget(self.lbl_incident_badge)

        self.lbl_cam_info = QLabel(f"<b>{cam_name}</b> <span style='color: #64748b;'>•</span> <span style='color: #cbd5e1;'>{lens}</span>  <span style='color: #64748b;'>({time_str})</span>", self)
        self.lbl_cam_info.setStyleSheet("font-size: 12px; color: #f1f5f9; background: transparent;")
        header_bar.addWidget(self.lbl_cam_info)

        header_bar.addStretch()

        # Version Switcher Pill (Highlighted vs Raw)
        self.btn_toggle_version = QPushButton(self)
        self._update_version_btn_label()
        self.btn_toggle_version.setToolTip("Toggle between AI bounding boxes and clean original video feed")
        self.btn_toggle_version.clicked.connect(self._toggle_version)
        header_bar.addWidget(self.btn_toggle_version)

        # Export MP4 button
        self.btn_export = QPushButton(self)
        self.btn_export.setIcon(create_player_icon("export", size=16))
        self.btn_export.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_export.setToolTip("Export MP4 recording to disk (Ctrl+S)")
        self.btn_export.clicked.connect(self.export_video)
        header_bar.addWidget(self.btn_export)

        # File locator button
        self.btn_folder = QPushButton(self)
        self.btn_folder.setIcon(create_player_icon("folder", size=16))
        self.btn_folder.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_folder.setToolTip("Open video location in Windows Explorer")
        self.btn_folder.clicked.connect(self._open_in_folder)
        header_bar.addWidget(self.btn_folder)

        # Delete clip button
        self.btn_delete = QPushButton(self)
        self.btn_delete.setIcon(create_player_icon("delete", size=16, color="#f87171"))
        self.btn_delete.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_delete.setToolTip("Permanently delete this incident clip from disk (Delete key)")
        self.btn_delete.clicked.connect(self.delete_current_clip)
        header_bar.addWidget(self.btn_delete)

        # Close Player button
        self.btn_close_header = QPushButton(self)
        self.btn_close_header.setIcon(create_player_icon("close", size=14))
        self.btn_close_header.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_close_header.setToolTip("Close Player (Esc)")
        self.btn_close_header.clicked.connect(self.close)
        header_bar.addWidget(self.btn_close_header)

        layout.addWidget(self.header_card)

        # Optional Scene Description Banner
        desc = self.alert_data.get("description", "")
        self.lbl_desc = QLabel(f"Note: {desc}" if desc else "", self)
        self.lbl_desc.setStyleSheet("""
            background-color: rgba(15, 23, 42, 0.75);
            color: #cbd5e1;
            font-size: 11px;
            border-left: 3px solid #38bdf8;
            padding: 5px 12px;
            border-radius: 6px;
        """)
        if desc:
            self.lbl_desc.show()
        else:
            self.lbl_desc.hide()
        layout.addWidget(self.lbl_desc)

        # --- Center Video View ---
        self.video_container = QFrame(self)
        self.video_container.setObjectName("video_container")
        self.video_container.setStyleSheet("background-color: #000000; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08);")
        self.stacked_video_layout = QStackedLayout(self.video_container)
        self.stacked_video_layout.setContentsMargins(0, 0, 0, 0)

        # Page 0: Active QtMultimedia Video Output Widget
        if HAS_QT_MULTIMEDIA:
            self.video_widget = QVideoWidget(self.video_container)
            self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.video_widget.setCursor(Qt.CursorShape.PointingHandCursor)

            # Install click & wheel filter on video surface
            self.video_surface_filter = VideoSurfaceFilter(self)
            self.video_widget.installEventFilter(self.video_surface_filter)

            self.stacked_video_layout.addWidget(self.video_widget)

            self.media_player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.media_player.setAudioOutput(self.audio_output)
            self.media_player.setVideoOutput(self.video_widget)

            self.media_player.positionChanged.connect(self._on_position_changed)
            self.media_player.durationChanged.connect(self._on_duration_changed)
            self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)
        else:
            self.lbl_no_mm = QLabel("QtMultimedia module is not available.", self.video_container)
            self.lbl_no_mm.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stacked_video_layout.addWidget(self.lbl_no_mm)

        # Glassmorphic OSD feedback badge on video surface
        self.lbl_osd = QLabel(self.video_container)
        self.lbl_osd.setObjectName("lbl_osd")
        self.lbl_osd.setStyleSheet("""
            QLabel#lbl_osd {
                background-color: rgba(15, 23, 42, 0.90);
                color: #f8fafc;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 12px;
                font-weight: 600;
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 14px;
                padding: 8px 18px;
            }
        """)
        self.lbl_osd.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_osd.hide()
        self._osd_timer = QTimer(self)
        self._osd_timer.setSingleShot(True)
        self._osd_timer.timeout.connect(self.lbl_osd.hide)

        # Page 1: Glassmorphic Buffering & Finalizing Overlay
        self.buffering_overlay = self._build_buffering_overlay(self.video_container)
        self.stacked_video_layout.addWidget(self.buffering_overlay)

        # Page 2: Failed/Timeout Overlay
        self.failed_overlay = self._build_failed_overlay(self.video_container)
        self.stacked_video_layout.addWidget(self.failed_overlay)

        # Page 3: Forensic Zoom & Pan Canvas
        self.zoom_canvas = ZoomCanvasWidget(self, self.video_container)
        self.stacked_video_layout.addWidget(self.zoom_canvas)

        if self.is_buffering:
            self.stacked_video_layout.setCurrentIndex(1)
        else:
            self.stacked_video_layout.setCurrentIndex(0)

        layout.addWidget(self.video_container, stretch=1)

        # --- Sleek Apple Glass Floating Transport Deck ---
        self.bottom_control_deck = QFrame(self)
        self.bottom_control_deck.setObjectName("bottom_control_deck")
        self.bottom_control_deck.setStyleSheet("""
            QFrame#bottom_control_deck {
                background: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 24px;
            }
        """)
        deck_vbox = QVBoxLayout(self.bottom_control_deck)
        deck_vbox.setContentsMargins(16, 10, 16, 10)
        deck_vbox.setSpacing(6)

        # --- Timeline Scrubber & Time Display ---
        time_row = QHBoxLayout()
        time_row.setSpacing(10)

        self.lbl_time_curr = QLabel("00:00", self)
        self.lbl_time_curr.setStyleSheet("""
            color: #38bdf8;
            font-family: 'Consolas', 'Segoe UI Mono', monospace;
            font-size: 11px;
            font-weight: 700;
            background: transparent;
        """)
        time_row.addWidget(self.lbl_time_curr)

        self.slider_timeline = SmartTimelineSlider(Qt.Orientation.Horizontal, self, player=self)
        self.slider_timeline.setObjectName("slider_timeline")
        self.slider_timeline.setRange(0, 1000)
        self.slider_timeline.setValue(0)
        self.slider_timeline.setStyleSheet("""
            QSlider#slider_timeline::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 0.12);
                border-radius: 2px;
            }
            QSlider#slider_timeline::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8);
                border-radius: 2px;
            }
            QSlider#slider_timeline::handle:horizontal {
                background: #38bdf8;
                border: 2px solid #ffffff;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
            QSlider#slider_timeline::handle:horizontal:hover {
                background: #7dd3fc;
                width: 16px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 8px;
            }
        """)
        self.slider_timeline.sliderMoved.connect(self._on_slider_moved)
        self.slider_timeline.sliderPressed.connect(self._on_slider_pressed)
        self.slider_timeline.sliderReleased.connect(self._on_slider_released)
        time_row.addWidget(self.slider_timeline, stretch=1)

        self.lbl_time_dur = QLabel("00:10", self)
        self.lbl_time_dur.setStyleSheet("""
            color: #94a3b8;
            font-family: 'Consolas', 'Segoe UI Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            background: transparent;
        """)
        time_row.addWidget(self.lbl_time_dur)

        deck_vbox.addLayout(time_row)

        # --- Playback Controls Bar ---
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(6)

        # === Left Group: Forensic Tools ===
        left_box = QHBoxLayout()
        left_box.setSpacing(6)

        # Clapperboard / 0.5s Slate Jump
        self.btn_jump_trigger = QPushButton(self)
        self.btn_jump_trigger.setIcon(create_player_icon("clapper", size=16))
        self.btn_jump_trigger.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_jump_trigger.setToolTip("Jump between Incident Action (0.5s) & Title Slate (0.0s) [Key: T]")
        self.btn_jump_trigger.clicked.connect(self.jump_trigger)
        left_box.addWidget(self.btn_jump_trigger)

        # Snap Frame Snapshot
        self.btn_snap_frame = QPushButton(self)
        self.btn_snap_frame.setIcon(create_player_icon("camera", size=16))
        self.btn_snap_frame.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_snap_frame.setToolTip("Capture full-resolution frame to disk & copy to clipboard [Key: S]")
        self.btn_snap_frame.clicked.connect(self.capture_current_frame)
        left_box.addWidget(self.btn_snap_frame)

        # Loop Toggle
        self.btn_loop = QPushButton(self)
        self.btn_loop.setIcon(create_player_icon("loop", size=16, active=self.is_looping))
        self.btn_loop.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_loop.setToolTip("Loop playback continuously")
        self.btn_loop.clicked.connect(self._toggle_loop)
        left_box.addWidget(self.btn_loop)

        ctrl_bar.addLayout(left_box)
        ctrl_bar.addStretch()

        # === Center Group: Apple Hero Transport ===
        center_box = QHBoxLayout()
        center_box.setSpacing(6)

        # Previous Clip
        self.btn_prev_clip = QPushButton(self)
        self.btn_prev_clip.setIcon(create_player_icon("prev_clip", size=15))
        self.btn_prev_clip.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_prev_clip.setToolTip("Previous Incident Clip (PageUp / Alt+Left)")
        self.btn_prev_clip.clicked.connect(lambda: self.navigate_clip(-1))
        center_box.addWidget(self.btn_prev_clip)

        # Step Back 1s
        self.btn_step_back = QPushButton(self)
        self.btn_step_back.setIcon(create_player_icon("step_back", size=15))
        self.btn_step_back.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_step_back.setToolTip("Step backward 1 second (Left Arrow)")
        self.btn_step_back.clicked.connect(lambda: self._seek_relative(-1000))
        center_box.addWidget(self.btn_step_back)

        # Step Back 1 FRAME
        self.btn_frame_back = QPushButton(self)
        self.btn_frame_back.setIcon(create_player_icon("frame_back", size=15))
        self.btn_frame_back.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_frame_back.setToolTip("Step 1 Frame Back (Comma ',' or Scroll Down)")
        self.btn_frame_back.clicked.connect(lambda: self.step_frame(-1))
        center_box.addWidget(self.btn_frame_back)

        # HERO Play / Pause circular button
        self.btn_play = QPushButton(self)
        self.btn_play.setObjectName("btn_play")
        self.btn_play.setStyleSheet(PLAYER_HERO_PLAY_STYLE)
        self.btn_play.setIcon(create_player_icon("pause", size=18, color="#0f172a"))
        self.btn_play.setToolTip("Play / Pause (Spacebar or Click Video)")
        self.btn_play.clicked.connect(self.toggle_play_pause)
        center_box.addWidget(self.btn_play)

        # Step Forward 1 FRAME
        self.btn_frame_fwd = QPushButton(self)
        self.btn_frame_fwd.setIcon(create_player_icon("frame_fwd", size=15))
        self.btn_frame_fwd.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_frame_fwd.setToolTip("Step 1 Frame Forward (Period '.' or Scroll Up)")
        self.btn_frame_fwd.clicked.connect(lambda: self.step_frame(1))
        center_box.addWidget(self.btn_frame_fwd)

        # Step Forward 1s
        self.btn_step_fwd = QPushButton(self)
        self.btn_step_fwd.setIcon(create_player_icon("step_fwd", size=15))
        self.btn_step_fwd.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_step_fwd.setToolTip("Step forward 1 second (Right Arrow)")
        self.btn_step_fwd.clicked.connect(lambda: self._seek_relative(1000))
        center_box.addWidget(self.btn_step_fwd)

        # Next Clip
        self.btn_next_clip = QPushButton(self)
        self.btn_next_clip.setIcon(create_player_icon("next_clip", size=15))
        self.btn_next_clip.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_next_clip.setToolTip("Next Incident Clip (PageDown / Alt+Right)")
        self.btn_next_clip.clicked.connect(lambda: self.navigate_clip(1))
        center_box.addWidget(self.btn_next_clip)

        ctrl_bar.addLayout(center_box)
        ctrl_bar.addStretch()

        # === Right Group: Utilities ===
        right_box = QHBoxLayout()
        right_box.setSpacing(6)

        # Zoom pill button (cycles 1.0x -> 1.5x -> 2.0x -> 3.0x -> 1.0x)
        self.btn_zoom = QPushButton("1.0x", self)
        self.btn_zoom.setIcon(create_player_icon("zoom", size=14))
        self.btn_zoom.setStyleSheet(PLAYER_PILL_BTN_STYLE)
        self.btn_zoom.setToolTip("Digital Zoom (Click to cycle 1.0x-3.0x, Right-Click to reset, Ctrl+Scroll to zoom)")
        self.btn_zoom.clicked.connect(self._cycle_zoom)
        right_box.addWidget(self.btn_zoom)

        # Backwards compatibility zoom aliases
        self.lbl_zoom = self.btn_zoom
        self.btn_zoom_in = QPushButton(self)
        self.btn_zoom_in.hide()
        self.btn_zoom_out = QPushButton(self)
        self.btn_zoom_out.hide()
        self.btn_zoom_reset = QPushButton(self)
        self.btn_zoom_reset.hide()

        # Speed pill button (cycles 0.5x -> 1.0x -> 1.5x -> 2.0x)
        self.btn_speed = QPushButton("1.0x", self)
        self.btn_speed.setIcon(create_player_icon("speed", size=14))
        self.btn_speed.setStyleSheet(PLAYER_PILL_BTN_STYLE)
        self.btn_speed.setToolTip("Playback Speed (Click to cycle: 0.5x, 1.0x, 1.5x, 2.0x)")
        self.btn_speed.clicked.connect(self._cycle_speed)
        right_box.addWidget(self.btn_speed)

        # Backwards compatibility cmb_speed
        self.cmb_speed = QComboBox(self)
        self.cmb_speed.addItem("0.25x", 0.25)
        self.cmb_speed.addItem("0.5x", 0.5)
        self.cmb_speed.addItem("1.0x", 1.0)
        self.cmb_speed.addItem("1.5x", 1.5)
        self.cmb_speed.addItem("2.0x", 2.0)
        self.cmb_speed.setCurrentIndex(2)
        self.cmb_speed.hide()
        self.cmb_speed.currentIndexChanged.connect(self._on_speed_changed)

        # Volume Mute button
        self.btn_mute = QPushButton(self)
        self.btn_mute.setIcon(create_player_icon("volume", size=16))
        self.btn_mute.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_mute.setToolTip("Audio Mute / Unmute (Key: M)")
        self.btn_mute.clicked.connect(self._toggle_mute)
        right_box.addWidget(self.btn_mute)

        # Volume Slider
        self.slider_volume = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_volume.setObjectName("slider_volume")
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(100)
        self.slider_volume.setFixedWidth(56)
        self.slider_volume.setStyleSheet("""
            QSlider#slider_volume::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 0.12);
                border-radius: 2px;
            }
            QSlider#slider_volume::sub-page:horizontal {
                background: #38bdf8;
                border-radius: 2px;
            }
            QSlider#slider_volume::handle:horizontal {
                background: #38bdf8;
                border: 1px solid #ffffff;
                width: 10px;
                margin-top: -3px;
                margin-bottom: -3px;
                border-radius: 5px;
            }
        """)
        self.slider_volume.valueChanged.connect(self._on_volume_changed)
        right_box.addWidget(self.slider_volume)

        # Fullscreen Toggle
        self.btn_fullscreen = QPushButton(self)
        self.btn_fullscreen.setIcon(create_player_icon("fullscreen", size=16))
        self.btn_fullscreen.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
        self.btn_fullscreen.setToolTip("Toggle Fullscreen (F11 or Double-Click)")
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        right_box.addWidget(self.btn_fullscreen)

        ctrl_bar.addLayout(right_box)
        deck_vbox.addLayout(ctrl_bar)
        layout.addWidget(self.bottom_control_deck)

        if self.is_buffering:
            self.slider_timeline.setEnabled(False)
            self.btn_play.setEnabled(False)
            self.btn_play.setText("Buffering...")
            self.btn_step_back.setEnabled(False)
            self.btn_step_fwd.setEnabled(False)
            if hasattr(self, "btn_frame_back"):
                self.btn_frame_back.setEnabled(False)
            if hasattr(self, "btn_frame_fwd"):
                self.btn_frame_fwd.setEnabled(False)
            if hasattr(self, "btn_jump_trigger"):
                self.btn_jump_trigger.setEnabled(False)
            if hasattr(self, "btn_snap_frame"):
                self.btn_snap_frame.setEnabled(False)
            self.btn_toggle_version.setEnabled(False)

            self.buffer_poll_timer = QTimer(self)
            self.buffer_poll_timer.setInterval(250)
            self.buffer_poll_ticks = 0
            self.buffer_poll_timer.timeout.connect(self._on_buffer_poll_tick)
            self.buffer_poll_timer.start()

    def _build_buffering_overlay(self, parent: QWidget) -> QWidget:
        overlay = QFrame(parent)
        overlay.setStyleSheet("""
            QFrame {
                background-color: #070c18;
                border-radius: 6px;
            }
        """)
        vbox = QVBoxLayout(overlay)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.setSpacing(12)
        vbox.setContentsMargins(24, 20, 24, 20)

        # Snapshot preview card (if available)
        snap_path = self.alert_data.get("snapshot_path") or ""
        if snap_path and os.path.exists(snap_path):
            lbl_buffer_thumb = QLabel(overlay)
            lbl_buffer_thumb.setFixedSize(320, 180)
            lbl_buffer_thumb.setStyleSheet("""
                background-color: #020617;
                border: 1px solid #334155;
                border-radius: 6px;
            """)
            lbl_buffer_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pix = QPixmap(snap_path)
            if not pix.isNull():
                lbl_buffer_thumb.setPixmap(pix.scaled(320, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            vbox.addWidget(lbl_buffer_thumb, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status badge pill
        badge = QLabel("FINALIZING 10s INCIDENT CLIP", overlay)
        badge.setStyleSheet("""
            background-color: rgba(6, 182, 212, 0.15);
            color: #38bdf8;
            border: 1px solid #0284c7;
            border-radius: 4px;
            padding: 4px 12px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
        """)
        vbox.addWidget(badge, alignment=Qt.AlignmentFlag.AlignCenter)

        # Telemetry & Camera
        cam = self.alert_data.get("camera_name", "Camera")
        lens = self.alert_data.get("lens", "")
        lbl_info = QLabel(f"{cam} • {lens} | Capturing HD recording...", overlay)
        lbl_info.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: 600;")
        vbox.addWidget(lbl_info, alignment=Qt.AlignmentFlag.AlignCenter)

        # Subtitle
        lbl_sub = QLabel("Direct playback begins automatically as soon as camera recording completes.", overlay)
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 11px;")
        vbox.addWidget(lbl_sub, alignment=Qt.AlignmentFlag.AlignCenter)

        # Animated progress bar
        self.buffer_progress = QProgressBar(overlay)
        self.buffer_progress.setFixedSize(280, 4)
        self.buffer_progress.setRange(0, 0)  # Indeterminate pulsating bar
        self.buffer_progress.setTextVisible(False)
        self.buffer_progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #00e5ff;
                border-radius: 2px;
            }
        """)
        vbox.addWidget(self.buffer_progress, alignment=Qt.AlignmentFlag.AlignCenter)

        return overlay

    def _build_failed_overlay(self, parent: QWidget) -> QWidget:
        overlay = QFrame(parent)
        overlay.setStyleSheet("background-color: #070c18; border-radius: 6px;")
        vbox = QVBoxLayout(overlay)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.setSpacing(12)
        vbox.setContentsMargins(24, 20, 24, 20)

        snap_path = self.alert_data.get("snapshot_path") or ""
        if snap_path and os.path.exists(snap_path):
            lbl_thumb = QLabel(overlay)
            lbl_thumb.setFixedSize(320, 180)
            lbl_thumb.setStyleSheet("border: 1px solid #334155; border-radius: 6px; background-color: #020617;")
            lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pix = QPixmap(snap_path)
            if not pix.isNull():
                lbl_thumb.setPixmap(pix.scaled(320, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            vbox.addWidget(lbl_thumb, alignment=Qt.AlignmentFlag.AlignCenter)

        lbl_msg = QLabel("Video clip recording was not finalized for this event.\nKeyframe snapshot remains preserved.", overlay)
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_msg.setStyleSheet("color: #f87171; font-size: 12px; font-weight: 600;")
        vbox.addWidget(lbl_msg, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_snap = QPushButton("View Snapshot", overlay)
        btn_snap.setStyleSheet("background-color: #1e293b; color: #f1f5f9; padding: 6px 14px; border: 1px solid #334155;")
        btn_snap.clicked.connect(self._open_snapshot)
        btn_row.addWidget(btn_snap)

        btn_close = QPushButton("Close Player", overlay)
        btn_close.setStyleSheet("background-color: #2563eb; color: #ffffff; padding: 6px 14px; border: 1px solid #3b82f6;")
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        vbox.addLayout(btn_row)

        return overlay

    def _open_snapshot(self):
        spath = self.alert_data.get("snapshot_path", "")
        if spath and os.path.exists(spath):
            try:
                os.startfile(spath)
            except Exception:
                pass

    def _on_buffer_poll_tick(self):
        self.buffer_poll_ticks += 1
        # 1. Check if highlighted_path or raw_path exists and is > 2KB
        for p in [self.highlighted_path, self.raw_path]:
            if p and os.path.exists(p) and os.path.getsize(p) > 2048:
                self.set_video_ready(p, self.raw_path if p == self.highlighted_path else self.highlighted_path)
                return

        # 2. Check alarms folder for matching unique_id
        uid = self.alert_data.get("unique_id", "")
        rec_dir = os.path.dirname(self.highlighted_path) if self.highlighted_path else ""
        if uid and rec_dir and os.path.exists(rec_dir):
            try:
                for fn in os.listdir(rec_dir):
                    if uid in fn and fn.lower().endswith(".mp4"):
                        full_p = os.path.join(rec_dir, fn)
                        if os.path.exists(full_p) and os.path.getsize(full_p) > 2048:
                            self.set_video_ready(full_p)
                            return
            except Exception:
                pass

        # 3. Timeout after ~18 seconds
        if self.buffer_poll_ticks >= 72:
            self.set_video_failed()

    def set_video_ready(self, video_path: str, raw_path: str = ""):
        """Called dynamically when alert video finishes encoding; smoothly transitions to playback."""
        if not video_path or not os.path.exists(video_path):
            return
        if hasattr(self, "buffer_poll_timer") and self.buffer_poll_timer and self.buffer_poll_timer.isActive():
            self.buffer_poll_timer.stop()

        self.highlighted_path = video_path
        if raw_path and os.path.exists(raw_path):
            self.raw_path = raw_path
        else:
            cand_raw = video_path.replace("_HIGHLIGHTED", "_RAW").replace("_AI_Boxed", "_Raw")
            if os.path.exists(cand_raw):
                self.raw_path = cand_raw

        self.current_video_path = video_path
        self.is_showing_highlighted = True
        self.is_buffering = False

        if hasattr(self, "stacked_video_layout"):
            self.stacked_video_layout.setCurrentIndex(0)
        self.slider_timeline.setEnabled(True)
        self.btn_play.setEnabled(True)
        self.btn_play.setIcon(create_player_icon("pause", size=18, color="#0f172a"))
        self.btn_play.setToolTip("Pause (Spacebar)")
        self.btn_step_back.setEnabled(True)
        self.btn_step_fwd.setEnabled(True)
        if hasattr(self, "btn_frame_back"):
            self.btn_frame_back.setEnabled(True)
        if hasattr(self, "btn_frame_fwd"):
            self.btn_frame_fwd.setEnabled(True)
        if hasattr(self, "btn_jump_trigger"):
            self.btn_jump_trigger.setEnabled(True)
        if hasattr(self, "btn_snap_frame"):
            self.btn_snap_frame.setEnabled(True)
        self._update_version_btn_label()
        self._load_current_media()

    def set_video_failed(self):
        """Called if video recording fails or times out."""
        if hasattr(self, "buffer_poll_timer") and self.buffer_poll_timer and self.buffer_poll_timer.isActive():
            self.buffer_poll_timer.stop()
        self.is_buffering = False
        if hasattr(self, "stacked_video_layout"):
            self.stacked_video_layout.setCurrentIndex(2)
        self.slider_timeline.setEnabled(False)
        self.btn_play.setEnabled(False)
        self.btn_play.setIcon(create_player_icon("play", size=18, color="#64748b"))
        self.btn_play.setToolTip("Unavailable")
        if hasattr(self, "btn_frame_back"):
            self.btn_frame_back.setEnabled(False)
        if hasattr(self, "btn_frame_fwd"):
            self.btn_frame_fwd.setEnabled(False)
        if hasattr(self, "btn_jump_trigger"):
            self.btn_jump_trigger.setEnabled(False)
        if hasattr(self, "btn_snap_frame"):
            self.btn_snap_frame.setEnabled(False)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self.toggle_play_pause)
        QShortcut(QKeySequence("K"), self, self.toggle_play_pause)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, lambda: self._seek_relative(-1000))
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, lambda: self._seek_relative(1000))
        QShortcut(QKeySequence(","), self, lambda: self.step_frame(-1))
        QShortcut(QKeySequence("<"), self, lambda: self.step_frame(-1))
        QShortcut(QKeySequence("."), self, lambda: self.step_frame(1))
        QShortcut(QKeySequence(">"), self, lambda: self.step_frame(1))
        QShortcut(QKeySequence("["), self, lambda: self.step_frame(-5))
        QShortcut(QKeySequence("]"), self, lambda: self.step_frame(5))
        QShortcut(QKeySequence(Qt.Key.Key_Home), self, lambda: self.media_player.setPosition(0) if HAS_QT_MULTIMEDIA else None)
        QShortcut(QKeySequence(Qt.Key.Key_End), self, lambda: self.media_player.setPosition(self.media_player.duration()) if HAS_QT_MULTIMEDIA else None)
        QShortcut(QKeySequence(Qt.Key.Key_PageUp), self, lambda: self.navigate_clip(-1))
        QShortcut(QKeySequence(Qt.Key.Key_PageDown), self, lambda: self.navigate_clip(1))
        QShortcut(QKeySequence("Alt+Left"), self, lambda: self.navigate_clip(-1))
        QShortcut(QKeySequence("Alt+Right"), self, lambda: self.navigate_clip(1))
        QShortcut(QKeySequence("Ctrl+S"), self, self.export_video)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self, self.delete_current_clip)
        QShortcut(QKeySequence("+"), self, lambda: self.adjust_zoom(0.25))
        QShortcut(QKeySequence("="), self, lambda: self.adjust_zoom(0.25))
        QShortcut(QKeySequence("-"), self, lambda: self.adjust_zoom(-0.25))
        QShortcut(QKeySequence("0"), self, self.reset_zoom)
        QShortcut(QKeySequence("T"), self, self.jump_trigger)
        QShortcut(QKeySequence("S"), self, self.capture_current_frame)
        QShortcut(QKeySequence("M"), self, self._toggle_mute)
        QShortcut(QKeySequence("F"), self, self._toggle_fullscreen)
        QShortcut(QKeySequence("F11"), self, self._toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self, self._on_escape)

    def _build_playlist(self):
        """Discovers neighboring incident recordings in the same directory for seamless navigation."""
        self.playlist_clips = []
        rec_dir = ""
        for p in [self.current_video_path, self.highlighted_path, self.raw_path]:
            if p and os.path.exists(p):
                rec_dir = os.path.dirname(os.path.abspath(p))
                break

        if rec_dir and os.path.exists(rec_dir):
            try:
                candidates = []
                for fn in os.listdir(rec_dir):
                    if fn.lower().endswith(".mp4") and not fn.startswith("."):
                        fp = os.path.join(rec_dir, fn)
                        if os.path.isfile(fp) and os.path.getsize(fp) > 2048:
                            candidates.append((os.path.getmtime(fp), fp))
                # Sort newest first
                candidates.sort(key=lambda x: x[0], reverse=True)
                self.playlist_clips = [c[1] for c in candidates]
            except Exception:
                pass

        if self.current_video_path:
            norm_curr = os.path.abspath(self.current_video_path).lower()
            for idx, p in enumerate(self.playlist_clips):
                if os.path.abspath(p).lower() == norm_curr:
                    self.current_playlist_idx = idx
                    break
            else:
                if self.playlist_clips:
                    self.playlist_clips.insert(0, self.current_video_path)
                    self.current_playlist_idx = 0

    def _update_playlist_buttons(self):
        """Enables or disables playlist Prev/Next buttons depending on current index."""
        if hasattr(self, "btn_prev_clip") and hasattr(self, "btn_next_clip"):
            has_prev = self.current_playlist_idx > 0
            has_next = 0 <= self.current_playlist_idx < len(self.playlist_clips) - 1
            self.btn_prev_clip.setEnabled(has_prev)
            self.btn_next_clip.setEnabled(has_next)

    def navigate_clip(self, delta: int):
        """Navigates to previous or next recording clip in playlist."""
        if not self.playlist_clips:
            self._build_playlist()
        if not self.playlist_clips:
            return

        new_idx = self.current_playlist_idx + delta
        if 0 <= new_idx < len(self.playlist_clips):
            self.current_playlist_idx = new_idx
            next_path = self.playlist_clips[new_idx]
            self.reset_zoom()
            self._parse_media_source(next_path)
            self._refresh_header_metadata()
            self._load_current_media()
            self._update_playlist_buttons()
            self._show_osd(f"Clip {new_idx + 1} of {len(self.playlist_clips)}", duration_ms=1300)

    def _refresh_header_metadata(self):
        """Updates header badges and labels when switching between playlist clips."""
        cam_name = self.alert_data.get("camera_name", "")
        lens = self.alert_data.get("lens", "")
        label = self.alert_data.get("label", "").upper()
        conf = int(self.alert_data.get("confidence", 0) * 100)
        time_str = self.alert_data.get("timestamp", "")

        if not cam_name and self.current_video_path:
            fn = os.path.basename(self.current_video_path)
            if "fata" in fn.lower():
                cam_name = "Fata (Dual-Lens 2K)"
            elif "afara" in fn.lower():
                cam_name = "Afara"
            elif "spate" in fn.lower():
                cam_name = "Spate"
            elif "camera9d85" in fn.lower():
                cam_name = "camera9D85"
            else:
                cam_name = "CCTV Camera"

            if "lens2" in fn.lower() or "fixedwide" in fn.lower():
                lens = "Lens 2 (Fixed Wide)"
            elif "lens1" in fn.lower() or "ptz" in fn.lower():
                lens = "Lens 1 (PTZ Zoom)"
            else:
                lens = "Main Stream"

            if "person" in fn.lower():
                label = "PERSON"
                m_pct = re.search(r'(\d+)pct', fn, re.IGNORECASE)
                conf = int(m_pct.group(1)) if m_pct else 50
            elif "vehicle" in fn.lower():
                label = "VEHICLE"
            elif "animal" in fn.lower():
                label = "ANIMAL"
            elif "motion" in fn.lower():
                label = "MOTION"
            else:
                label = "RECORDING"

            m_dt = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}|\d{8}_\d{6})', fn)
            if m_dt:
                time_str = m_dt.group(1).replace('_', ' ')
            elif os.path.exists(self.current_video_path):
                time_str = datetime.fromtimestamp(os.path.getmtime(self.current_video_path)).strftime("%Y-%m-%d %H:%M:%S")

        if not cam_name:
            cam_name = "CCTV Camera"
        if not lens:
            lens = "Main Stream"
        if not label:
            label = "RECORDING"

        is_person = "person" in label.lower()
        badge_color = "#ef4444" if is_person else "#38bdf8"
        badge_bg = "rgba(239, 68, 68, 0.20)" if is_person else "rgba(56, 189, 248, 0.20)"

        if hasattr(self, "lbl_incident_badge"):
            self.lbl_incident_badge.setText(f"● {label} {conf}%" if conf > 0 else f"● {label}")
            self.lbl_incident_badge.setStyleSheet(f"""
                background-color: {badge_bg};
                color: {badge_color};
                font-weight: 700;
                font-size: 11px;
                border: none;
                border-radius: 11px;
                padding: 3px 10px;
            """)

        if hasattr(self, "lbl_cam_info"):
            self.lbl_cam_info.setText(f"<b>{cam_name}</b> <span style='color: #64748b;'>•</span> <span style='color: #cbd5e1;'>{lens}</span>  <span style='color: #64748b;'>({time_str})</span>")

        desc = self.alert_data.get("description", "")
        if hasattr(self, "lbl_desc"):
            if desc:
                self.lbl_desc.setText(f"Note: {desc}")
                self.lbl_desc.show()
            else:
                self.lbl_desc.hide()

        self._update_version_btn_label()

    def export_video(self):
        """Allows exporting a copy of the current recording to any folder on disk."""
        if not self.current_video_path or not os.path.exists(self.current_video_path):
            QMessageBox.warning(self, "Export Video", "No active video recording file to export.")
            return

        default_fn = os.path.basename(self.current_video_path)
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        default_target = os.path.join(desktop_dir, default_fn)

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Video Recording",
            default_target,
            "MP4 Video (*.mp4);;All Files (*.*)"
        )
        if not save_path:
            return

        try:
            shutil.copy2(self.current_video_path, save_path)
            self._show_osd(f"Exported: {os.path.basename(save_path)}", duration_ms=2200)
            QMessageBox.information(
                self,
                "Export Complete",
                f"Video recording successfully exported to:\n{save_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export video:\n{str(e)}")

    def delete_current_clip(self):
        """Permanently deletes current recording clip with confirmation."""
        if not self.current_video_path or not os.path.exists(self.current_video_path):
            QMessageBox.information(self, "Delete Clip", "No active video recording found to delete.")
            return

        fn = os.path.basename(self.current_video_path)
        res = QMessageBox.question(
            self,
            "Delete Incident Recording",
            f"Are you sure you want to permanently delete this video clip from disk?\n\n{fn}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res != QMessageBox.StandardButton.Yes:
            return

        if HAS_QT_MULTIMEDIA and hasattr(self, "media_player"):
            self.media_player.stop()

        targets = set()
        if self.current_video_path:
            targets.add(self.current_video_path)
        if self.highlighted_path:
            targets.add(self.highlighted_path)
        if self.raw_path:
            targets.add(self.raw_path)

        for p in targets:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

        self._show_osd("Clip Deleted", duration_ms=1800)

        if 0 <= self.current_playlist_idx < len(self.playlist_clips):
            self.playlist_clips.pop(self.current_playlist_idx)

        if self.playlist_clips:
            if self.current_playlist_idx >= len(self.playlist_clips):
                self.current_playlist_idx = len(self.playlist_clips) - 1
            next_path = self.playlist_clips[self.current_playlist_idx]
            self.reset_zoom()
            self._parse_media_source(next_path)
            self._refresh_header_metadata()
            self._load_current_media()
            self._update_playlist_buttons()
        else:
            self.close()

    def _extract_frame_qimage(self, pos_ms: int) -> Optional[QImage]:
        """Extracts high-resolution QImage frame at specified millisecond position."""
        if not self.current_video_path or not os.path.exists(self.current_video_path):
            return None
        cap = cv2.VideoCapture(self.current_video_path)
        if not cap.isOpened():
            return None
        try:
            cap.set(cv2.CAP_PROP_POS_MSEC, float(pos_ms))
            ret, bgr_frame = cap.read()
            if not ret or bgr_frame is None:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, bgr_frame = cap.read()
            if not ret or bgr_frame is None:
                return None
            h, w, ch = bgr_frame.shape
            rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            bytes_per_line = ch * w
            return QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        finally:
            cap.release()

    def adjust_zoom(self, delta: float):
        """Adjusts digital zoom (1.0x - 4.0x) on paused freeze-frame."""
        if self.is_buffering or not self.current_video_path or not os.path.exists(self.current_video_path):
            return
        new_zoom = round(max(1.0, min(4.0, self.zoom_level + delta)), 2)
        if new_zoom == self.zoom_level:
            return
        self.zoom_level = new_zoom
        if hasattr(self, "btn_zoom"):
            self.btn_zoom.setText(f"{self.zoom_level:.1f}x")
            self.btn_zoom.setIcon(create_player_icon("zoom", size=14))
        elif hasattr(self, "lbl_zoom"):
            self.lbl_zoom.setText(f"{self.zoom_level:.1f}x")

        if self.zoom_level > 1.0:
            if HAS_QT_MULTIMEDIA and self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.media_player.pause()
                if hasattr(self, "btn_play"):
                    self.btn_play.setIcon(create_player_icon("play", size=18, color="#0f172a"))
                    self.btn_play.setToolTip("Play (Spacebar)")
                self._update_frame_btn_styles(is_paused=True)
            pos_ms = self.media_player.position() if HAS_QT_MULTIMEDIA else 0
            qimg = self._extract_frame_qimage(pos_ms)
            if qimg and not qimg.isNull():
                self.zoom_canvas.set_image(qimg, self.zoom_level, self.zoom_pan)
                self.stacked_video_layout.setCurrentIndex(3)
                self._show_osd(f"Zoom {self.zoom_level:.1f}x (Drag to pan)", duration_ms=1300)
        else:
            self.zoom_pan = QPoint(0, 0)
            self.stacked_video_layout.setCurrentIndex(0)
            self._show_osd("Zoom 1:1", duration_ms=900)

    def reset_zoom(self):
        """Resets digital zoom back to 1.0x normal view."""
        self.zoom_level = 1.0
        self.zoom_pan = QPoint(0, 0)
        if hasattr(self, "btn_zoom"):
            self.btn_zoom.setText("1.0x")
            self.btn_zoom.setIcon(create_player_icon("zoom", size=14))
        elif hasattr(self, "lbl_zoom"):
            self.lbl_zoom.setText("1.0x")
        if hasattr(self, "stacked_video_layout") and self.stacked_video_layout.currentIndex() == 3:
            self.stacked_video_layout.setCurrentIndex(0)
        self._show_osd("Zoom 1:1", duration_ms=800)

    def _cycle_zoom(self):
        """Cycles digital zoom through 1.0x -> 1.5x -> 2.0x -> 3.0x -> 1.0x."""
        levels = [1.0, 1.5, 2.0, 3.0]
        try:
            curr_idx = min(range(len(levels)), key=lambda i: abs(levels[i] - self.zoom_level))
            next_idx = (curr_idx + 1) % len(levels)
            target = levels[next_idx]
        except Exception:
            target = 1.0
        diff = target - self.zoom_level
        self.adjust_zoom(diff)

    def _cycle_speed(self):
        """Cycles playback speed: 0.5x -> 1.0x -> 1.5x -> 2.0x -> 0.5x."""
        speeds = [0.5, 1.0, 1.5, 2.0]
        cur_rate = 1.0
        if hasattr(self, "cmb_speed"):
            cur_rate = float(self.cmb_speed.currentData() or 1.0)
        try:
            idx = min(range(len(speeds)), key=lambda i: abs(speeds[i] - cur_rate))
            next_idx = (idx + 1) % len(speeds)
            target = speeds[next_idx]
        except Exception:
            target = 1.0
        if hasattr(self, "cmb_speed"):
            for i in range(self.cmb_speed.count()):
                if abs(self.cmb_speed.itemData(i) - target) < 0.05:
                    self.cmb_speed.setCurrentIndex(i)
                    break
        if hasattr(self, "btn_speed"):
            self.btn_speed.setText(f"{target:.1f}x")

    def _update_version_btn_label(self):
        has_both = bool(
            self.highlighted_path and self.raw_path and
            os.path.exists(self.highlighted_path) and os.path.exists(self.raw_path) and
            os.path.abspath(self.highlighted_path).lower() != os.path.abspath(self.raw_path).lower()
        )
        if self.is_showing_highlighted:
            self.btn_toggle_version.setText("AI Boxes" if not has_both else "AI Boxes • Switch")
            self.btn_toggle_version.setStyleSheet("""
                QPushButton {
                    background-color: rgba(56, 189, 248, 0.15);
                    color: #38bdf8;
                    border: 1px solid rgba(56, 189, 248, 0.35);
                    border-radius: 14px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(56, 189, 248, 0.25);
                    border-color: #38bdf8;
                    color: #ffffff;
                }
                QPushButton:disabled {
                    background-color: rgba(255, 255, 255, 0.03);
                    color: #64748b;
                    border-color: rgba(255, 255, 255, 0.06);
                }
            """)
        else:
            self.btn_toggle_version.setText("Clean Feed" if not has_both else "Clean Feed • Switch")
            self.btn_toggle_version.setStyleSheet("""
                QPushButton {
                    background-color: rgba(56, 189, 248, 0.15);
                    color: #38bdf8;
                    border: 1px solid rgba(56, 189, 248, 0.35);
                    border-radius: 14px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(56, 189, 248, 0.25);
                    border-color: #38bdf8;
                    color: #ffffff;
                }
                QPushButton:disabled {
                    background-color: rgba(255, 255, 255, 0.03);
                    color: #64748b;
                    border-color: rgba(255, 255, 255, 0.06);
                }
            """)
        self.btn_toggle_version.setEnabled(has_both)

    def _load_current_media(self, preserve_position: int = 0):
        if self.is_buffering:
            return

        if not HAS_QT_MULTIMEDIA or not self.current_video_path:
            return

        if not os.path.exists(self.current_video_path) or os.path.getsize(self.current_video_path) <= 1024:
            alt_path = self.raw_path if self.is_showing_highlighted else self.highlighted_path
            if alt_path and os.path.exists(alt_path) and os.path.getsize(alt_path) > 1024:
                self.current_video_path = alt_path
                self.is_showing_highlighted = not self.is_showing_highlighted
                self._update_version_btn_label()
            else:
                if self.alert_data:
                    self.set_video_failed()
                    return
                QMessageBox.information(
                    self,
                    "Video Clip Unavailable",
                    f"The video file for this incident is no longer available on disk.\n\n"
                    f"It was automatically removed to free space according to the storage quota.\n\n"
                    f"File: {os.path.basename(self.current_video_path)}"
                )
                self.close()
                return

        # Forensic OpenCV Metadata Probe
        try:
            cap = cv2.VideoCapture(self.current_video_path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                if fps and fps > 1.0:
                    self.video_fps = float(fps)
                if frames and frames > 0:
                    self.total_frames = frames
                self.video_width = w
                self.video_height = h
                cap.release()
        except Exception:
            pass

        self.frame_interval_ms = max(15, int(1000.0 / self.video_fps))

        try:
            self.media_player.stop()
        except Exception:
            pass

        url = QUrl.fromLocalFile(os.path.abspath(self.current_video_path))
        self.media_player.setSource(url)
        self.media_player.play()
        if hasattr(self, "btn_play"):
            self.btn_play.setIcon(create_player_icon("pause", size=18, color="#0f172a"))
            self.btn_play.setToolTip("Pause (Spacebar)")
        self._update_frame_btn_styles(is_paused=False)

        if preserve_position > 0:
            QTimer.singleShot(100, lambda: self.media_player.setPosition(preserve_position))

    def _toggle_version(self):
        curr_pos = self.media_player.position() if HAS_QT_MULTIMEDIA else 0
        if self.is_showing_highlighted:
            if self.raw_path and os.path.exists(self.raw_path) and os.path.abspath(self.raw_path).lower() != os.path.abspath(self.highlighted_path).lower():
                self.current_video_path = self.raw_path
                self.is_showing_highlighted = False
        else:
            if self.highlighted_path and os.path.exists(self.highlighted_path) and os.path.abspath(self.highlighted_path).lower() != os.path.abspath(self.raw_path).lower():
                self.current_video_path = self.highlighted_path
                self.is_showing_highlighted = True

        self._update_version_btn_label()
        self._load_current_media(preserve_position=curr_pos)

    def toggle_play_pause(self, user_clicked_surface: bool = False):
        """Toggles between Play and Pause. When pausing, illuminates frame navigation controls."""
        if not HAS_QT_MULTIMEDIA:
            return
        if self.zoom_level > 1.0:
            self.reset_zoom()
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            if hasattr(self, "btn_play"):
                self.btn_play.setIcon(create_player_icon("play", size=18, color="#0f172a"))
                self.btn_play.setToolTip("Play (Spacebar)")
            self._update_frame_btn_styles(is_paused=True)
            cur_pos = self.media_player.position()
            cur_frame = int(round((cur_pos / 1000.0) * self.video_fps)) + 1
            tot_str = f"/{self.total_frames}" if self.total_frames > 0 else ""
            self._show_osd(f"PAUSED • Frame {cur_frame}{tot_str}\n(Scroll wheel or |< >| to step frames)", duration_ms=1300)
        else:
            self.media_player.play()
            if hasattr(self, "btn_play"):
                self.btn_play.setIcon(create_player_icon("pause", size=18, color="#0f172a"))
                self.btn_play.setToolTip("Pause (Spacebar)")
            self._update_frame_btn_styles(is_paused=False)
            self._show_osd("PLAYING", duration_ms=600)

    def step_frame(self, delta_frames: int):
        """Steps exactly delta_frames (-1 or +1) forward or backward with forensic precision."""
        if not HAS_QT_MULTIMEDIA:
            return
        # Ensure player is paused when stepping frame-by-frame
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            if hasattr(self, "btn_play"):
                self.btn_play.setIcon(create_player_icon("play", size=18, color="#0f172a"))
                self.btn_play.setToolTip("Play (Spacebar)")
            self._update_frame_btn_styles(is_paused=True)

        dur = self.media_player.duration()
        cur_pos = self.media_player.position()

        # Compute current 0-indexed frame
        cur_frame = int(round((cur_pos / 1000.0) * self.video_fps))
        target_frame = cur_frame + delta_frames

        if self.total_frames > 0:
            target_frame = max(0, min(self.total_frames - 1, target_frame))
        else:
            target_frame = max(0, target_frame)

        new_pos = int(target_frame * (1000.0 / self.video_fps))
        if dur > 0:
            new_pos = min(dur, new_pos)

        self.media_player.setPosition(new_pos)
        tot_str = f"/{self.total_frames}" if self.total_frames > 0 else ""
        self.lbl_time_curr.setText(f"{self._format_ms_precise(new_pos)}  [F:{target_frame + 1}{tot_str}]")
        self._show_osd(f"Frame {target_frame + 1}{tot_str} • {self._format_ms_precise(new_pos)}", duration_ms=800)

        if self.zoom_level > 1.0:
            qimg = self._extract_frame_qimage(new_pos)
            if qimg and not qimg.isNull():
                self.zoom_canvas.set_image(qimg, self.zoom_level, self.zoom_pan)

    def _on_video_wheel(self, delta_y: int):
        """Mouse wheel handler on the video output surface."""
        if not HAS_QT_MULTIMEDIA:
            return
        is_playing = (self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
        if not is_playing:
            # Paused: jog frame forward or backward
            step = 1 if delta_y > 0 else -1
            self.step_frame(step)
        else:
            # Playing: smooth volume control
            cur_vol = int(self.audio_output.volume() * 100)
            diff = 5 if delta_y > 0 else -5
            new_vol = max(0, min(100, cur_vol + diff))
            self.slider_volume.setValue(new_vol)
            self._show_osd(f"Volume: {new_vol}%", duration_ms=700)

    def jump_trigger(self):
        """Jumps directly to the 0.5s alert action timestamp or back to the 0.0s title slate."""
        if not HAS_QT_MULTIMEDIA:
            return
        cur_pos = self.media_player.position()
        if cur_pos < 600:
            target_pos = 500
            self._show_osd("Jumping to Trigger Action (0.5s)", duration_ms=900)
        else:
            target_pos = 0
            self._show_osd("Jumping to Title Slate (0.0s)", duration_ms=900)
        self.media_player.setPosition(target_pos)

    def capture_current_frame(self):
        """Forensic snapshot of the exact current frame, saved to disk and copied to clipboard."""
        if not self.current_video_path or not os.path.exists(self.current_video_path):
            self._show_osd("Video source unavailable", duration_ms=1000)
            return

        cur_pos_ms = self.media_player.position() if HAS_QT_MULTIMEDIA else 0

        try:
            cap = cv2.VideoCapture(self.current_video_path)
            if not cap.isOpened():
                self._show_osd("Could not open video file", duration_ms=1000)
                return

            cap.set(cv2.CAP_PROP_POS_MSEC, cur_pos_ms)
            ret, bgr_frame = cap.read()
            cap.release()

            if not ret or bgr_frame is None:
                self._show_osd("Failed to read frame", duration_ms=1000)
                return

            snap_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "snapshots")
            os.makedirs(snap_dir, exist_ok=True)

            cam_name = self.alert_data.get("camera_name", "Incident")
            cam_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', cam_name)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            cur_frame = int(round((cur_pos_ms / 1000.0) * self.video_fps)) + 1
            filename = f"snapshot_{cam_slug}_{ts}_frame_{cur_frame}.jpg"
            save_path = os.path.join(snap_dir, filename)

            cv2.imwrite(save_path, bgr_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

            # Copy to clipboard
            h, w, ch = bgr_frame.shape
            rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            bytes_per_line = ch * w
            qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
            QApplication.clipboard().setImage(qimg)

            self._show_osd(f"Snapshot Copied & Saved!\nFrame {cur_frame} ({w}x{h})", duration_ms=1800)
        except Exception as e:
            self._show_osd(f"Snapshot error: {str(e)}", duration_ms=1500)

    def _show_osd(self, text: str, duration_ms: int = 900):
        """Displays centered on-screen display feedback."""
        if not hasattr(self, "lbl_osd") or not hasattr(self, "video_container"):
            return
        self.lbl_osd.setText(text)
        self.lbl_osd.adjustSize()
        vc_rect = self.video_container.rect()
        x = (vc_rect.width() - self.lbl_osd.width()) // 2
        y = (vc_rect.height() - self.lbl_osd.height()) // 2
        self.lbl_osd.move(max(10, x), max(10, y))
        self.lbl_osd.show()
        self.lbl_osd.raise_()
        if hasattr(self, "_osd_timer") and self._osd_timer.isActive():
            self._osd_timer.stop()
        self._osd_timer.start(duration_ms)

    def _update_frame_btn_styles(self, is_paused: bool):
        """Illuminates frame stepping buttons when video is paused."""
        if not hasattr(self, "btn_frame_back") or not hasattr(self, "btn_frame_fwd"):
            return
        if is_paused:
            self.btn_frame_back.setIcon(create_player_icon("frame_back", size=15, active=True))
            self.btn_frame_fwd.setIcon(create_player_icon("frame_fwd", size=15, active=True))
            active_style = """
                QPushButton {
                    background-color: rgba(56, 189, 248, 0.20);
                    border: 1px solid #38bdf8;
                    border-radius: 15px;
                    min-width: 30px;
                    max-width: 30px;
                    min-height: 30px;
                    max-height: 30px;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: rgba(56, 189, 248, 0.35);
                    border-color: #7dd3fc;
                }
            """
            self.btn_frame_back.setStyleSheet(active_style)
            self.btn_frame_fwd.setStyleSheet(active_style)
            self.btn_frame_back.setToolTip("Step -1 Frame (Comma ',' or Scroll Down)")
            self.btn_frame_fwd.setToolTip("Step +1 Frame (Period '.' or Scroll Up)")
        else:
            self.btn_frame_back.setIcon(create_player_icon("frame_back", size=15, active=False))
            self.btn_frame_fwd.setIcon(create_player_icon("frame_fwd", size=15, active=False))
            self.btn_frame_back.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
            self.btn_frame_fwd.setStyleSheet(PLAYER_GLASS_BTN_STYLE)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "lbl_osd") and hasattr(self, "video_container") and self.lbl_osd.isVisible():
            vc_rect = self.video_container.rect()
            x = (vc_rect.width() - self.lbl_osd.width()) // 2
            y = (vc_rect.height() - self.lbl_osd.height()) // 2
            self.lbl_osd.move(max(10, x), max(10, y))

        # Responsive collapse for compact dialog widths (< 720px)
        w = self.width()
        if hasattr(self, "btn_step_back") and hasattr(self, "btn_step_fwd"):
            is_compact = (w < 720)
            self.btn_step_back.setVisible(not is_compact)
            self.btn_step_fwd.setVisible(not is_compact)

    def _seek_relative(self, delta_ms: int):
        if not HAS_QT_MULTIMEDIA:
            return
        new_pos = max(0, min(self.media_player.duration(), self.media_player.position() + delta_ms))
        self.media_player.setPosition(new_pos)

    def _on_slider_pressed(self):
        self._user_is_sliding = True

    def _on_slider_moved(self, val):
        if HAS_QT_MULTIMEDIA and self.media_player.duration() > 0:
            dur = self.media_player.duration()
            pos = int((val / 1000.0) * dur)
            cur_frame = int(round((pos / 1000.0) * self.video_fps)) + 1
            tot_str = f"/{self.total_frames}" if self.total_frames > 0 else ""
            self.lbl_time_curr.setText(f"{self._format_ms_precise(pos)}  [F:{cur_frame}{tot_str}]")

    def _on_slider_released(self):
        self._user_is_sliding = False
        if HAS_QT_MULTIMEDIA and self.media_player.duration() > 0:
            val = self.slider_timeline.value()
            dur = self.media_player.duration()
            new_pos = int((val / 1000.0) * dur)
            self.media_player.setPosition(new_pos)

    def _on_position_changed(self, pos: int):
        if not self._user_is_sliding and HAS_QT_MULTIMEDIA:
            dur = self.media_player.duration()
            if dur > 0:
                self.slider_timeline.setValue(int((pos / float(dur)) * 1000))
            is_paused = (self.media_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState)
            cur_frame = int(round((pos / 1000.0) * self.video_fps)) + 1
            tot_str = f"/{self.total_frames}" if self.total_frames > 0 else ""
            if is_paused:
                self.lbl_time_curr.setText(f"{self._format_ms_precise(pos)}  [F:{cur_frame}{tot_str}]")
            else:
                self.lbl_time_curr.setText(self._format_ms_precise(pos))

    def _on_duration_changed(self, dur: int):
        tot_str = f" ({self.total_frames} frames)" if self.total_frames > 0 else ""
        self.lbl_time_dur.setText(f"{self._format_ms_precise(dur)}{tot_str}")

    def _on_media_status_changed(self, status):
        if HAS_QT_MULTIMEDIA and status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.is_looping:
                self.media_player.setPosition(0)
                self.media_player.play()
            else:
                if hasattr(self, "btn_play"):
                    self.btn_play.setIcon(create_player_icon("play", size=18, color="#0f172a"))
                    self.btn_play.setToolTip("Play (Spacebar)")
                self._update_frame_btn_styles(is_paused=True)

    def _on_speed_changed(self, idx):
        if HAS_QT_MULTIMEDIA:
            rate = self.cmb_speed.currentData()
            self.media_player.setPlaybackRate(float(rate))
            if hasattr(self, "btn_speed"):
                self.btn_speed.setText(f"{rate}x")
            self._show_osd(f"Speed: {rate}x", duration_ms=700)

    def _toggle_loop(self):
        self.is_looping = not self.is_looping
        if hasattr(self, "btn_loop"):
            self.btn_loop.setIcon(create_player_icon("loop", size=16, active=self.is_looping))
            if self.is_looping:
                self.btn_loop.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(56, 189, 248, 0.22);
                        border: 1px solid #38bdf8;
                        border-radius: 15px;
                        min-width: 30px;
                        max-width: 30px;
                        min-height: 30px;
                        max-height: 30px;
                        padding: 0;
                    }
                    QPushButton:hover { background-color: rgba(56, 189, 248, 0.35); }
                """)
                self.btn_loop.setToolTip("Loop playback continuously (ON)")
                self._show_osd("Loop: ON", duration_ms=600)
            else:
                self.btn_loop.setStyleSheet(PLAYER_GLASS_BTN_STYLE)
                self.btn_loop.setToolTip("Loop playback continuously (OFF)")
                self._show_osd("Loop: OFF", duration_ms=600)

    def _on_volume_changed(self, val):
        if HAS_QT_MULTIMEDIA:
            self.audio_output.setVolume(val / 100.0)
            if hasattr(self, "btn_mute"):
                ic = "volume_mute" if val == 0 else "volume"
                self.btn_mute.setIcon(create_player_icon(ic, size=16))

    def _toggle_mute(self):
        if HAS_QT_MULTIMEDIA:
            is_muted = self.audio_output.isMuted()
            self.audio_output.setMuted(not is_muted)
            if hasattr(self, "btn_mute"):
                ic = "volume_mute" if not is_muted else "volume"
                self.btn_mute.setIcon(create_player_icon(ic, size=16))
            self._show_osd("MUTED" if not is_muted else "UNMUTED", duration_ms=600)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            if hasattr(self, "btn_fullscreen"):
                self.btn_fullscreen.setIcon(create_player_icon("fullscreen", size=16))
                self.btn_fullscreen.setToolTip("Toggle Fullscreen (F11)")
        else:
            self.showFullScreen()
            if hasattr(self, "btn_fullscreen"):
                self.btn_fullscreen.setIcon(create_player_icon("fullscreen_exit", size=16))
                self.btn_fullscreen.setToolTip("Exit Fullscreen (F11 or Esc)")

    def _on_escape(self):
        if self.isFullScreen():
            self.showNormal()
            if hasattr(self, "btn_fullscreen"):
                self.btn_fullscreen.setIcon(create_player_icon("fullscreen", size=16))
                self.btn_fullscreen.setToolTip("Toggle Fullscreen (F11)")
        else:
            self.close()

    def _open_in_folder(self):
        if self.current_video_path and os.path.exists(self.current_video_path):
            folder = os.path.dirname(os.path.abspath(self.current_video_path))
            try:
                os.startfile(folder)
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    @staticmethod
    def _format_ms(ms: int) -> str:
        secs = int(ms / 1000)
        mins, s = divmod(secs, 60)
        return f"{mins:02d}:{s:02d}"

    @staticmethod
    def _format_ms_precise(ms: int) -> str:
        secs = int(ms / 1000)
        mins, s = divmod(secs, 60)
        fraction = int((ms % 1000) / 10)
        return f"{mins:02d}:{s:02d}.{fraction:02d}"

    def closeEvent(self, event):
        if hasattr(self, "buffer_poll_timer") and self.buffer_poll_timer:
            try:
                self.buffer_poll_timer.stop()
            except Exception:
                pass
        if HAS_QT_MULTIMEDIA and hasattr(self, "media_player"):
            try:
                self.media_player.stop()
            except Exception:
                pass
        event.accept()
