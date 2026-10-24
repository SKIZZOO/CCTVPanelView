"""
Modern iOS / Windows 11 style Animated Toggle Switch for PyQt6.
Clean, smooth sliding switch with crisp typography and accessibility.
"""

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen


class ToggleSwitch(QWidget):
    """
    Animated Toggle Switch (iOS / Windows 11 style).
    - Off: Neutral dark grey track with white thumb
    - On: Modern vibrant blue/green track with white thumb
    - Smooth position animation when clicked
    """
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None, active_color: str = "#0284c7"):
        super().__init__(parent)
        self._checked = bool(checked)
        self._thumb_position = 1.0 if self._checked else 0.0
        self._active_color = QColor(active_color)
        self._inactive_color = QColor("#334155")
        self._track_hover_color = QColor("#475569")
        self._thumb_color = QColor("#ffffff")
        self._is_hovered = False

        self.setFixedSize(46, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    @pyqtProperty(float)
    def thumb_position(self) -> float:
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos: float):
        self._thumb_position = pos
        self.update()

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        checked = bool(checked)
        if self._checked == checked:
            return
        self._checked = checked
        self._anim.stop()
        self._anim.setStartValue(self._thumb_position)
        self._anim.setEndValue(1.0 if self._checked else 0.0)
        self._anim.start()
        self.toggled.emit(self._checked)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h / 2.0

        # Background track color interpolation
        if self._checked:
            bg_color = self._active_color
        else:
            bg_color = self._track_hover_color if self._is_hovered else self._inactive_color

        # Draw pill-shaped track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # Thumb dimensions
        thumb_margin = 2.5
        thumb_diameter = h - (thumb_margin * 2)
        min_x = thumb_margin
        max_x = w - thumb_diameter - thumb_margin
        thumb_x = min_x + self._thumb_position * (max_x - min_x)
        thumb_y = thumb_margin

        # Draw white thumb circle
        painter.setBrush(QBrush(self._thumb_color))
        painter.drawEllipse(QRectF(thumb_x, thumb_y, thumb_diameter, thumb_diameter))
