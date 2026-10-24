import os
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QProgressBar, QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QFont, QCursor


class SleekAlertNotification(QFrame):
    """
    Sleek, modern floating surveillance toast notification.
    Features:
    - Translucent glassmorphism dark theme with color-coded threat indicator
    - Keyframe snapshot thumbnail preview
    - Camera name, lens, AI confidence badge, detection zone description
    - Smooth slide-in and slide-out position & opacity animations
    - Interactive action buttons (Play Clip in Studio, View on Google Drive)
    - Auto-dismiss progress countdown with pause on mouse hover
    """

    action_clicked = pyqtSignal(dict)
    dismissed = pyqtSignal()

    def __init__(self, alert_entry: Dict[str, Any], parent=None, duration_ms: int = 6500):
        super().__init__(parent)
        self.alert_entry = alert_entry
        self.duration_ms = duration_ms
        self.remaining_ms = duration_ms
        self.is_paused = False
        self.is_closing = False

        self.setObjectName("sleek_alert_toast")
        self.setFixedSize(440, 105)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self._setup_ui()
        self._setup_animations()
        self._setup_timer()

    def _setup_ui(self):
        # Color coding by detection category
        label = self.alert_entry.get("label", "ALARM").upper()
        if "PERSON" in label:
            accent_color = "#ef4444"  # Crimson Red
            badge_bg = "rgba(239, 68, 68, 0.20)"
            badge_fg = "#f87171"
            badge_border = "#ef4444"
        elif "VEHICLE" in label or "CAR" in label:
            accent_color = "#06b6d4"  # Cyan
            badge_bg = "rgba(6, 182, 212, 0.20)"
            badge_fg = "#38bdf8"
            badge_border = "#0284c7"
        elif "ANIMAL" in label or "DOG" in label:
            accent_color = "#38bdf8"
            badge_bg = "rgba(56, 189, 248, 0.20)"
            badge_fg = "#38bdf8"
            badge_border = "#0284c7"
        else:
            accent_color = "#f59e0b"  # Amber / Motion
            badge_bg = "rgba(245, 158, 11, 0.20)"
            badge_fg = "#fbbf24"
            badge_border = "#d97706"

        self.setStyleSheet(f"""
            QFrame#sleek_alert_toast {{
                background-color: rgba(15, 23, 42, 0.96);
                border: 1px solid rgba(59, 130, 246, 0.35);
                border-left: 5px solid {accent_color};
                border-radius: 8px;
            }}
            QLabel {{
                background: transparent;
            }}
        """)

        # Drop shadow for floating elevation
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

        # Main Layout
        root_vbox = QVBoxLayout(self)
        root_vbox.setContentsMargins(10, 8, 10, 6)
        root_vbox.setSpacing(6)

        # Content Row
        content_row = QHBoxLayout()
        content_row.setSpacing(10)

        # 1. Left Thumbnail Snapshot
        self.lbl_thumb = QLabel(self)
        self.lbl_thumb.setFixedSize(70, 70)
        self.lbl_thumb.setStyleSheet(f"""
            QLabel {{
                background-color: #020617;
                border: 1px solid #334155;
                border-radius: 6px;
            }}
        """)
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)

        snap_path = self.alert_entry.get("snapshot_path") or self.alert_entry.get("snap_path")
        if snap_path and os.path.exists(snap_path):
            pix = QPixmap(snap_path)
            if not pix.isNull():
                self.lbl_thumb.setPixmap(pix.scaled(68, 68, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        else:
            self.lbl_thumb.setText("<span style='font-size:10px; color:#64748b; font-weight:700;'>CCTV</span>")
        content_row.addWidget(self.lbl_thumb)

        # 2. Center Telemetry & Description
        center_vbox = QVBoxLayout()
        center_vbox.setSpacing(3)

        # Top line: Badge + Camera Name + Time
        top_h = QHBoxLayout()
        top_h.setSpacing(6)

        conf = float(self.alert_entry.get("confidence", 0.0))
        conf_str = f" {int(conf * 100)}%" if conf > 0 else ""
        badge_text = f"{label}{conf_str}"
        lbl_badge = QLabel(badge_text, self)
        lbl_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                color: {badge_fg};
                border: 1px solid {badge_border};
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }}
        """)
        top_h.addWidget(lbl_badge)

        cam_name = self.alert_entry.get("camera_name", "Camera")
        lens = self.alert_entry.get("lens", "")
        lens_text = f" • {lens}" if lens else ""
        lbl_cam = QLabel(f"{cam_name}{lens_text}", self)
        lbl_cam.setStyleSheet("color: #f8fafc; font-weight: 700; font-size: 12px;")
        top_h.addWidget(lbl_cam, stretch=1)

        time_str = self.alert_entry.get("time_short", "")
        lbl_time = QLabel(time_str, self)
        lbl_time.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600;")
        top_h.addWidget(lbl_time)
        center_vbox.addLayout(top_h)

        # Middle line: Short detection description & zone
        desc = self.alert_entry.get("description", "Motion event detected")
        lbl_desc = QLabel(desc, self)
        lbl_desc.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        center_vbox.addWidget(lbl_desc)

        # Bottom line: Storage & Quick action
        bot_h = QHBoxLayout()
        lbl_storage = QLabel("Saved to CCTV Storage Archives", self)
        lbl_storage.setStyleSheet("color: #38bdf8; font-size: 9px; font-weight: 600;")
        bot_h.addWidget(lbl_storage, stretch=1)

        self.btn_view = QPushButton("Play Video" if self.alert_entry.get("video_ready") else "Play Clip", self)
        self.btn_view.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: 1px solid #3b82f6;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.btn_view.clicked.connect(self._on_action_clicked)
        bot_h.addWidget(self.btn_view)

        btn_close = QPushButton("✕", self)
        btn_close.setFixedSize(18, 18)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748b;
                border: none;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                color: #f8fafc;
            }
        """)
        btn_close.clicked.connect(self.dismiss)
        bot_h.addWidget(btn_close)

        center_vbox.addLayout(bot_h)
        content_row.addLayout(center_vbox, stretch=1)

        root_vbox.addLayout(content_row)

        # 3. Bottom Animated Countdown Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, self.duration_ms)
        self.progress_bar.setValue(self.duration_ms)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 1px;
            }}
            QProgressBar::chunk {{
                background-color: {accent_color};
                border-radius: 1px;
            }}
        """)
        root_vbox.addWidget(self.progress_bar)

    def _setup_animations(self):
        # Opacity animation effect
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)

        self.anim_opacity = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_opacity.setDuration(320)
        self.anim_opacity.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Geometry slide animation
        self.anim_pos = QPropertyAnimation(self, b"pos")
        self.anim_pos.setDuration(350)
        self.anim_pos.setEasingCurve(QEasingCurve.Type.OutBack)

    def _setup_timer(self):
        self.step_timer = QTimer(self)
        self.step_timer.setInterval(50)
        self.step_timer.timeout.connect(self._on_tick)

    def slide_in(self, target_pos: QPoint):
        """Plays smooth slide-in and fade-in animation to target coordinates."""
        start_pos = QPoint(target_pos.x() + 80, target_pos.y())
        self.move(start_pos)
        self.show()
        self.raise_()

        self.anim_pos.stop()
        self.anim_pos.setStartValue(start_pos)
        self.anim_pos.setEndValue(target_pos)
        self.anim_pos.start()

        self.anim_opacity.stop()
        self.anim_opacity.setStartValue(0.0)
        self.anim_opacity.setEndValue(1.0)
        self.anim_opacity.start()

        self.step_timer.start()

    def _on_tick(self):
        if not self.is_paused and not self.is_closing:
            self.remaining_ms -= 50
            self.progress_bar.setValue(max(0, self.remaining_ms))
            if self.remaining_ms <= 0:
                self.step_timer.stop()
                self.dismiss()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.is_paused = True  # Pause dismiss timer on hover

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.is_paused = False  # Resume dismiss timer when mouse leaves

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_action_clicked()
        super().mousePressEvent(event)

    def _on_action_clicked(self):
        self.action_clicked.emit(self.alert_entry)
        self.dismiss()

    def update_video_ready(self, video_path: str, raw_path: str = ""):
        """Dynamically updates the toast alert entry and button when video encoding completes."""
        if not video_path:
            return
        self.alert_entry["video_path"] = video_path
        self.alert_entry["video_highlighted_path"] = video_path
        if raw_path:
            self.alert_entry["video_raw_path"] = raw_path
        self.alert_entry["video_ready"] = True
        self.alert_entry["video_recording"] = False

        if hasattr(self, "btn_view") and self.btn_view:
            self.btn_view.setText("Play Video")
            self.btn_view.setStyleSheet("""
                QPushButton {
                    background-color: #0284c7;
                    color: #ffffff;
                    border: 1px solid #38bdf8;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 10px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #0369a1;
                }
            """)

    def dismiss(self):
        """Slides out and fades out smoothly before destroying widget."""
        if self.is_closing:
            return
        self.is_closing = True
        self.step_timer.stop()

        cur_pos = self.pos()
        end_pos = QPoint(cur_pos.x() + 90, cur_pos.y())

        self.anim_pos.stop()
        self.anim_pos.setDuration(260)
        self.anim_pos.setEasingCurve(QEasingCurve.Type.InCubic)
        self.anim_pos.setStartValue(cur_pos)
        self.anim_pos.setEndValue(end_pos)

        self.anim_opacity.stop()
        self.anim_opacity.setDuration(240)
        self.anim_opacity.setEasingCurve(QEasingCurve.Type.InCubic)
        self.anim_opacity.setStartValue(self.opacity_effect.opacity())
        self.anim_opacity.setEndValue(0.0)

        self.anim_opacity.finished.connect(self._cleanup)
        self.anim_pos.start()
        self.anim_opacity.start()

    def _cleanup(self):
        self.dismissed.emit()
        self.hide()
        self.deleteLater()
