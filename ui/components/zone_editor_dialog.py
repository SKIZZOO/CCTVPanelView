import os
from typing import List, Optional, Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QListWidget, QListWidgetItem, QFrame, QSplitter,
    QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, QRect, QRectF, QSize
from PyQt6.QtGui import QPainter, QImage, QColor, QFont, QPen, QBrush, QIcon, QPixmap


class ZoneCanvasWidget(QWidget):
    """
    High-resolution interactive canvas for drawing and previewing ignore / exclusion zones.
    """
    def __init__(self, frame: Optional[QImage], zones: List[List[float]], parent=None):
        super().__init__(parent)
        self.frame = frame
        self.zones: List[List[float]] = [list(z) for z in zones if len(z) >= 4]
        self.selected_index: int = -1

        self.drag_start: Optional[QPoint] = None
        self.current_drag_rect: Optional[QRect] = None
        self._dest_rect: Tuple[int, int, int, int] = (0, 0, 0, 0)

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMinimumSize(480, 270)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_zones(self, zones: List[List[float]]):
        self.zones = [list(z) for z in zones if len(z) >= 4]
        self.update()

    def set_selected_index(self, idx: int):
        self.selected_index = idx
        self.update()

    def delete_selected_zone(self):
        if 0 <= self.selected_index < len(self.zones):
            del self.zones[self.selected_index]
            self.selected_index = -1
            self.update()

    def clear_all_zones(self):
        self.zones.clear()
        self.selected_index = -1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()

        # 1. Dark HUD canvas background
        painter.fillRect(rect, QColor("#050811"))

        if self.frame and not self.frame.isNull():
            img_w = self.frame.width()
            img_h = self.frame.height()
            aspect = (img_w / img_h) if img_h > 0 else 16.0 / 9.0
            w_aspect = rect.width() / max(1, rect.height())

            if w_aspect > aspect:
                dest_h = rect.height()
                dest_w = int(dest_h * aspect)
                dest_x = (rect.width() - dest_w) // 2
                dest_y = 0
            else:
                dest_w = rect.width()
                dest_h = int(dest_w / aspect)
                dest_x = 0
                dest_y = (rect.height() - dest_h) // 2

            self._dest_rect = (dest_x, dest_y, dest_w, dest_h)
            painter.drawImage(QRect(dest_x, dest_y, dest_w, dest_h), self.frame)
        else:
            dest_x, dest_y, dest_w, dest_h = 0, 0, rect.width(), rect.height()
            self._dest_rect = (dest_x, dest_y, dest_w, dest_h)
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No preview image\n(You can draw zones on screen)")

        dest_x, dest_y, dest_w, dest_h = self._dest_rect

        # 2. Draw existing exclusion zones
        for idx, z in enumerate(self.zones):
            if len(z) < 4:
                continue
            zx1, zy1, zx2, zy2 = z[:4]
            min_x = min(zx1, zx2)
            max_x = max(zx1, zx2)
            min_y = min(zy1, zy2)
            max_y = max(zy1, zy2)

            px_x = int(dest_x + min_x * dest_w)
            px_y = int(dest_y + min_y * dest_h)
            px_w = int((max_x - min_x) * dest_w)
            px_h = int((max_y - min_y) * dest_h)
            z_rect = QRect(px_x, px_y, px_w, px_h)

            is_sel = (idx == self.selected_index)

            # Fill
            fill_col = QColor(239, 68, 68, 80) if is_sel else QColor(239, 68, 68, 45)
            painter.fillRect(z_rect, fill_col)

            # Border
            border_col = QColor("#f87171") if is_sel else QColor("#ef4444")
            pen = QPen(border_col, 3 if is_sel else 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(z_rect)

            # Label badge
            lbl_bg = QColor("#b91c1c") if is_sel else QColor("#7f1d1d")
            badge_h = 18
            badge_w = 110
            badge_y = max(dest_y, px_y - badge_h)
            painter.fillRect(QRect(px_x, badge_y, badge_w, badge_h), lbl_bg)
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(QRect(px_x + 4, badge_y, badge_w - 4, badge_h), Qt.AlignmentFlag.AlignVCenter, f"ZONE #{idx + 1}")

        # 3. Draw live rubberband rectangle currently being dragged
        if self.current_drag_rect:
            painter.fillRect(self.current_drag_rect, QColor(245, 158, 11, 70))
            pen_drag = QPen(QColor(245, 158, 11, 240), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen_drag)
            painter.drawRect(self.current_drag_rect)

            w_px = self.current_drag_rect.width()
            h_px = self.current_drag_rect.height()
            dim_text = f" {w_px}x{h_px}px "
            b_y = max(dest_y, self.current_drag_rect.top() - 18)
            painter.fillRect(QRect(self.current_drag_rect.left(), b_y, 110, 18), QColor(217, 119, 6, 230))
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(QRect(self.current_drag_rect.left(), b_y, 110, 18), Qt.AlignmentFlag.AlignCenter, dim_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = event.pos()
            self.current_drag_rect = None
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_start:
            self.current_drag_rect = QRect(self.drag_start, event.pos()).normalized()
            self.update()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drag_start:
            drag = QRect(self.drag_start, event.pos()).normalized()
            self.drag_start = None
            self.current_drag_rect = None

            dest_x, dest_y, dest_w, dest_h = self._dest_rect
            if dest_w > 0 and dest_h > 0 and drag.width() >= 15 and drag.height() >= 15:
                # Clamp within video bounds
                rx1 = max(dest_x, min(dest_x + dest_w, drag.left()))
                ry1 = max(dest_y, min(dest_y + dest_h, drag.top()))
                rx2 = max(dest_x, min(dest_x + dest_w, drag.right()))
                ry2 = max(dest_y, min(dest_y + dest_h, drag.bottom()))

                zx1 = (rx1 - dest_x) / dest_w
                zy1 = (ry1 - dest_y) / dest_h
                zx2 = (rx2 - dest_x) / dest_w
                zy2 = (ry2 - dest_y) / dest_h

                if abs(zx2 - zx1) > 0.02 and abs(zy2 - zy1) > 0.02:
                    new_z = [round(min(zx1, zx2), 4), round(min(zy1, zy2), 4), round(max(zx1, zx2), 4), round(max(zy1, zy2), 4)]
                    self.zones.append(new_z)
                    self.selected_index = len(self.zones) - 1
                    if hasattr(self.parent(), "on_zones_updated"):
                        self.parent().on_zones_updated()
            self.update()
            event.accept()


class ZoneEditorDialog(QDialog):
    """
    Dedicated visual editor dialog for configuring tracking & motion ignore zones.
    """
    def __init__(self, camera_name: str, current_frame: Optional[QImage], current_zones: List[List[float]], parent=None):
        super().__init__(parent)
        self.camera_name = camera_name
        self.zones = [list(z) for z in current_zones if len(z) >= 4]

        self.setWindowTitle(f"CCTVPanelView - Motion Ignore Zones: {camera_name}")
        self.resize(1020, 680)
        self.setMinimumSize(780, 500)
        self._setup_ui(current_frame)

    def _setup_ui(self, current_frame: Optional[QImage]):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel(f"Configure Ignore Zones: {self.camera_name}")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #38bdf8;")
        header.addWidget(title)
        header.addStretch()

        desc = QLabel("Drag with the mouse on the image to define rectangular zones to ignore during motion tracking.")
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        root.addLayout(header)
        root.addWidget(desc)

        # Central Splitter (Canvas + Zone List)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left Canvas
        self.canvas = ZoneCanvasWidget(current_frame, self.zones, parent=self)
        splitter.addWidget(self.canvas)

        # Right Panel (List of zones & actions)
        right_panel = QFrame(self)
        right_panel.setFixedWidth(280)
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
            }
        """)
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(10, 10, 10, 10)
        rp_layout.setSpacing(8)

        lbl_list = QLabel("Configured Zones:")
        lbl_list.setStyleSheet("color: #f8fafc; font-weight: 600; font-size: 12px;")
        rp_layout.addWidget(lbl_list)

        self.list_widget = QListWidget(right_panel)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #050811;
                border: 1px solid #334155;
                border-radius: 4px;
                color: #f1f5f9;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #1e293b;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
        """)
        self.list_widget.currentRowChanged.connect(self._on_list_row_changed)
        rp_layout.addWidget(self.list_widget)

        # Action buttons for list
        btn_del_selected = QPushButton("Delete Selected Zone", right_panel)
        btn_del_selected.setStyleSheet("background: #7f1d1d; color: #fecaca; border: 1px solid #ef4444; border-radius: 4px; padding: 6px; font-weight: 600;")
        btn_del_selected.clicked.connect(self._delete_selected_zone)
        rp_layout.addWidget(btn_del_selected)

        btn_clear_all = QPushButton("Clear All Zones", right_panel)
        btn_clear_all.setStyleSheet("background: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 4px; padding: 6px; font-weight: 500;")
        btn_clear_all.clicked.connect(self._clear_all_zones)
        rp_layout.addWidget(btn_clear_all)

        rp_layout.addStretch()

        help_box = QLabel("How it works:<br>Any person, animal, vehicle, or motion inside the red zones will be <b>completely ignored</b> by AI detection and alert/recording triggers.")
        help_box.setWordWrap(True)
        help_box.setStyleSheet("color: #38bdf8; background: rgba(37, 99, 235, 0.12); border: 1px solid #2563eb; border-radius: 4px; padding: 8px; font-size: 11px;")
        rp_layout.addWidget(help_box)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        root.addWidget(splitter)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.setStyleSheet("background: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 4px; padding: 7px 16px; font-weight: 500;")
        btn_cancel.clicked.connect(self.reject)
        footer.addWidget(btn_cancel)

        btn_save = QPushButton("Save and Apply", self)
        btn_save.setStyleSheet("background: #2563eb; color: #ffffff; font-weight: 600; padding: 7px 18px; border: 1px solid #3b82f6; border-radius: 4px;")
        btn_save.clicked.connect(self._save_and_accept)
        footer.addWidget(btn_save)

        root.addLayout(footer)
        self._refresh_list()

    def on_zones_updated(self):
        self._refresh_list()

    def _refresh_list(self):
        self.list_widget.clear()
        for idx, z in enumerate(self.canvas.zones):
            zx1, zy1, zx2, zy2 = z[:4]
            w_pct = int(abs(zx2 - zx1) * 100)
            h_pct = int(abs(zy2 - zy1) * 100)
            item = QListWidgetItem(f"Zone #{idx + 1} ({w_pct}% x {h_pct}% of frame)")
            self.list_widget.addItem(item)
        if 0 <= self.canvas.selected_index < len(self.canvas.zones):
            self.list_widget.setCurrentRow(self.canvas.selected_index)

    def _on_list_row_changed(self, row: int):
        self.canvas.set_selected_index(row)

    def _delete_selected_zone(self):
        self.canvas.delete_selected_zone()
        self._refresh_list()

    def _clear_all_zones(self):
        res = QMessageBox.question(
            self,
            "Confirm Clear All",
            "Are you sure you want to remove all ignore zones for this camera?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self.canvas.clear_all_zones()
            self._refresh_list()

    def _save_and_accept(self):
        self.zones = [list(z) for z in self.canvas.zones if len(z) >= 4]
        self.accept()

    def get_configured_zones(self) -> List[List[float]]:
        return self.zones
