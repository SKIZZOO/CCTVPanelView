"""
CCTVPanelView - Cybernetic Aperture Genesis Startup Loading Screen.
Features:
- Animated vector logo build-up:
  1. Squircle holographic shield materializes with glowing borders.
  2. Outer aperture ring with 4 caliper ticks spins into magnetic 12/3/6/9 alignment.
  3. Middle sapphire lens ring expands and aligns.
  4. Central camera eye iris pops in with elastic bloom and pupil hole.
  5. Cyan laser scanning sweep runs across the optic iris.
  6. High-tech telemetry status boot messages and glowing gradient progress bar.
- Seamless dissolve transition into MainWindow.
- Allows instant skip via Click or Esc key.
"""

import sys
import os
import math
from typing import Optional

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QFontMetrics, QRadialGradient,
    QLinearGradient, QPainterPath
)


def ease_out_cubic(x: float) -> float:
    return 1.0 - math.pow(1.0 - max(0.0, min(1.0, x)), 3.0)


def ease_out_back(x: float, c1: float = 1.70158) -> float:
    c3 = c1 + 1.0
    x = max(0.0, min(1.0, x))
    return 1.0 + c3 * math.pow(x - 1.0, 3.0) + c1 * math.pow(x - 1.0, 2.0)


def ease_out_elastic(x: float) -> float:
    x = max(0.0, min(1.0, x))
    if x == 0.0 or x == 1.0:
        return x
    c4 = (2.0 * math.pi) / 3.0
    return math.pow(2.0, -10.0 * x) * math.sin((x * 10.0 - 0.75) * c4) + 1.0


class CyberneticSplashScreen(QWidget):
    """
    State-of-the-art Cybernetic Aperture Genesis animated startup loading screen.
    """
    finished = pyqtSignal()

    def __init__(self, duration_sec: float = 2.2, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.setFixedSize(280, 280)
        self._center_on_screen()

        self.duration_sec = duration_sec
        self.elapsed = 0.0
        self.is_fading_out = False
        self.fade_opacity = 1.0

        # 60 FPS animation timer (every ~16 ms)
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)

    def _on_tick(self):
        dt = 0.016
        if not self.is_fading_out:
            self.elapsed += dt
            if self.elapsed >= self.duration_sec:
                self.is_fading_out = True
        else:
            self.fade_opacity -= dt * 4.0  # ~250ms smooth fade out
            if self.fade_opacity <= 0.0:
                self.fade_opacity = 0.0
                self.timer.stop()
                self.close()
                self.finished.emit()
                return

        self.update()

    def keyPressEvent(self, event):
        # Allow instant skip via Esc or Space or Enter
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Space, Qt.Key.Key_Return):
            self._skip_to_finish()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        # Allow instant skip via click
        self._skip_to_finish()

    def _skip_to_finish(self):
        if not self.is_fading_out:
            self.is_fading_out = True
            self.fade_opacity = 0.8

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.setOpacity(max(0.0, min(1.0, self.fade_opacity)))

        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0
        t = self.elapsed

        # --- Soft Background Optical Aura (No box, no borders - pure ambient glow) ---
        if t > 0.1:
            aura_prog = min(1.0, (t - 0.1) / 0.8)
            pulse = math.sin(t * 3.5) * 4.0 if t > 1.2 else 0.0
            aura_r = (85.0 + pulse) * aura_prog
            grad_aura = QRadialGradient(cx, cy, aura_r)
            grad_aura.setColorAt(0.0, QColor(0, 210, 255, int(50 * aura_prog)))
            grad_aura.setColorAt(0.5, QColor(0, 119, 254, int(25 * aura_prog)))
            grad_aura.setColorAt(1.0, QColor(0, 210, 255, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(grad_aura))
            p.drawEllipse(QPointF(cx, cy), aura_r, aura_r)

        # --- Stage 1: Outer Targeting Aperture Ring & 4 Caliper Ticks (t: 0.0 -> 0.9) ---
        out_prog = ease_out_cubic(min(1.0, t / 0.85))
        rot_deg = -180.0 * (1.0 - out_prog)
        rad_out = 64.0 * out_prog
        alpha_out = int(255 * out_prog)

        if out_prog > 0.02:
            p.save()
            p.translate(cx, cy)
            p.rotate(rot_deg)

            # Outer ring
            pen_ring = QPen(QColor(0, 210, 255, alpha_out), 4.5)
            p.setPen(pen_ring)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(0, 0), rad_out, rad_out)

            # 4 Caliper crosshair ticks
            tick_len = 15.0 * out_prog
            pen_tick = QPen(QColor(0, 210, 255, alpha_out), 4.5)
            p.setPen(pen_tick)
            # Top tick (12 o'clock)
            p.drawLine(QPointF(0, -rad_out), QPointF(0, -rad_out - tick_len))
            # Right tick (3 o'clock)
            p.drawLine(QPointF(rad_out, 0), QPointF(rad_out + tick_len, 0))
            # Bottom tick (6 o'clock)
            p.drawLine(QPointF(0, rad_out), QPointF(0, rad_out + tick_len))
            # Left tick (9 o'clock)
            p.drawLine(QPointF(-rad_out, 0), QPointF(-rad_out - tick_len, 0))

            p.restore()

        # --- Stage 2: Middle Sapphire Ring (t: 0.25 -> 1.1) ---
        if t >= 0.25:
            mid_prog = ease_out_cubic(min(1.0, (t - 0.25) / 0.70))
            rot_mid = 180.0 * (1.0 - mid_prog)
            rad_mid = 44.0 * mid_prog
            alpha_mid = int(245 * mid_prog)

            p.save()
            p.translate(cx, cy)
            p.rotate(rot_mid)

            pen_mid = QPen(QColor(0, 119, 254, alpha_mid), 3.5)
            p.setPen(pen_mid)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(0, 0), rad_mid, rad_mid)
            p.restore()

        # --- Stage 3: Central Camera Eye Iris & Pupil (t: 0.55 -> 1.3) ---
        if t >= 0.55:
            iris_prog = ease_out_elastic(min(1.0, (t - 0.55) / 0.65))
            rad_iris = 25.0 * iris_prog

            # Breathing glow pulse for t > 1.2
            if t > 1.2:
                pulse_phase = math.sin((t - 1.2) * 4.5)
                glow_r = rad_iris + 10.0 + 5.0 * pulse_phase
                grad_iris_glow = QRadialGradient(cx, cy, glow_r)
                grad_iris_glow.setColorAt(0.0, QColor(0, 210, 255, 170))
                grad_iris_glow.setColorAt(0.55, QColor(0, 119, 254, 80))
                grad_iris_glow.setColorAt(1.0, QColor(0, 210, 255, 0))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(grad_iris_glow))
                p.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

            # Solid cyan iris disc
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(0, 210, 255)))
            p.drawEllipse(QPointF(cx, cy), rad_iris, rad_iris)

            # Dark central pupil
            rad_pupil = 11.5 * iris_prog
            p.setBrush(QBrush(QColor(9, 13, 22)))
            p.drawEllipse(QPointF(cx, cy), rad_pupil, rad_pupil)

        # --- Stage 4: Soft Lens Glare Sheen (t > 0.85) ---
        if t >= 0.85:
            sweep_y_rel = math.sin((t - 0.85) * 4.0) * 48.0
            sweep_y = cy + sweep_y_rel
            sweep_w = 140.0

            grad_beam = QLinearGradient(cx - sweep_w / 2.0, sweep_y, cx + sweep_w / 2.0, sweep_y)
            grad_beam.setColorAt(0.0, QColor(56, 189, 248, 0))
            grad_beam.setColorAt(0.5, QColor(56, 189, 248, 160))
            grad_beam.setColorAt(1.0, QColor(56, 189, 248, 0))

            p.setPen(QPen(QBrush(grad_beam), 2.2))
            p.drawLine(QPointF(cx - sweep_w / 2.0, sweep_y), QPointF(cx + sweep_w / 2.0, sweep_y))
