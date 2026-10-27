import os
import sys
import time
import socket
import psutil
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QWidget, QLineEdit, QFileDialog,
    QProgressBar, QGraphicsDropShadowEffect, QGridLayout, QScrollArea,
    QCheckBox
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPixmap, QPainterPath

from core.resource_manager import get_resource_manager, PerformanceProfile
from core.device_manager import DeviceManager
from ui.components.device_dialog import DeviceDialog


def create_vector_icon(icon_type: str, color: str = "#38bdf8", size: int = 24) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color), 1.9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    if icon_type == "welcome":
        path = QPainterPath()
        path.moveTo(size * 0.50, size * 0.14)
        path.lineTo(size * 0.82, size * 0.28)
        path.lineTo(size * 0.82, size * 0.58)
        path.cubicTo(size * 0.82, size * 0.80, size * 0.50, size * 0.90, size * 0.50, size * 0.90)
        path.cubicTo(size * 0.50, size * 0.90, size * 0.18, size * 0.80, size * 0.18, size * 0.58)
        path.lineTo(size * 0.18, size * 0.28)
        path.closeSubpath()
        p.drawPath(path)
        p.drawEllipse(QPointF(size * 0.50, size * 0.50), size * 0.16, size * 0.16)
    elif icon_type == "storage":
        p.drawRoundedRect(QRectF(size * 0.16, size * 0.24, size * 0.68, size * 0.54), 2.5, 2.5)
        p.drawEllipse(QPointF(size * 0.50, size * 0.48), size * 0.14, size * 0.14)
        p.drawLine(int(size * 0.26), int(size * 0.68), int(size * 0.74), int(size * 0.68))
    elif icon_type == "hardware":
        p.drawRoundedRect(QRectF(size * 0.22, size * 0.22, size * 0.56, size * 0.56), 2, 2)
        p.drawRect(QRectF(size * 0.38, size * 0.38, size * 0.24, size * 0.24))
        for offset in (size * 0.35, size * 0.65):
            p.drawLine(int(offset), int(size * 0.10), int(offset), int(size * 0.22))
            p.drawLine(int(offset), int(size * 0.78), int(offset), int(size * 0.90))
            p.drawLine(int(size * 0.10), int(offset), int(size * 0.22), int(offset))
            p.drawLine(int(size * 0.78), int(offset), int(size * 0.90), int(offset))
    elif icon_type == "camera":
        p.drawRoundedRect(QRectF(size * 0.16, size * 0.28, size * 0.68, size * 0.52), 2.5, 2.5)
        p.drawEllipse(QPointF(size * 0.50, size * 0.54), size * 0.16, size * 0.16)
        p.drawRoundedRect(QRectF(size * 0.32, size * 0.16, size * 0.36, size * 0.14), 1.5, 1.5)
    elif icon_type == "launch":
        p.drawEllipse(QPointF(size * 0.50, size * 0.50), size * 0.36, size * 0.36)
        p.drawLine(int(size * 0.34), int(size * 0.50), int(size * 0.46), int(size * 0.62))
        p.drawLine(int(size * 0.46), int(size * 0.62), int(size * 0.66), int(size * 0.38))
    elif icon_type == "check":
        p.drawLine(int(size * 0.28), int(size * 0.50), int(size * 0.44), int(size * 0.66))
        p.drawLine(int(size * 0.44), int(size * 0.66), int(size * 0.74), int(size * 0.34))
    elif icon_type == "close":
        p.drawLine(int(size * 0.28), int(size * 0.28), int(size * 0.72), int(size * 0.72))
        p.drawLine(int(size * 0.72), int(size * 0.28), int(size * 0.28), int(size * 0.72))
    elif icon_type == "radar":
        p.drawEllipse(QPointF(size * 0.50, size * 0.50), size * 0.40, size * 0.40)
        p.drawEllipse(QPointF(size * 0.50, size * 0.50), size * 0.24, size * 0.24)
        p.drawPoint(QPointF(size * 0.50, size * 0.50))
        p.drawLine(int(size * 0.50), int(size * 0.50), int(size * 0.78), int(size * 0.24))

    p.end()
    return pix


class RadarSweepWidget(QWidget):
    """Animated high-tech radar scanning animation for camera discovery."""
    def __init__(self, size: int = 110, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
        self.timer.start(30)

    def _rotate(self):
        self.angle = (self.angle + 4) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.44

        # Background grid circles
        pen = QPen(QColor(56, 189, 248, 45), 1)
        p.setPen(pen)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.drawEllipse(QPointF(cx, cy), r * 0.66, r * 0.66)
        p.drawEllipse(QPointF(cx, cy), r * 0.33, r * 0.33)

        # Crosshairs
        p.drawLine(int(cx - r), int(cy), int(cx + r), int(cy))
        p.drawLine(int(cx), int(cy - r), int(cx), int(cy + r))

        # Sweep beam
        import math
        rad = math.radians(self.angle)
        x2 = cx + math.cos(rad) * r
        y2 = cy + math.sin(rad) * r

        pen_sweep = QPen(QColor("#38bdf8"), 2)
        p.setPen(pen_sweep)
        p.drawLine(int(cx), int(cy), int(x2), int(y2))

        # Sweep glow gradient fan
        path = QPainterPath()
        path.moveTo(cx, cy)
        for d in range(25):
            a_rad = math.radians((self.angle - d) % 360)
            path.lineTo(cx + math.cos(a_rad) * r, cy + math.sin(a_rad) * r)
        path.closeSubpath()
        p.fillPath(path, QBrush(QColor(56, 189, 248, 25)))

        # Center emitter
        p.setBrush(QBrush(QColor("#38bdf8")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), 3, 3)
        p.end()


class OnboardingWizard(QDialog):
    """
    Out-Of-Box Experience (OOBE) installation & setup wizard for CCTVPanelView:
    - Stage 1: Welcome & Workstation Introduction
    - Stage 2: Storage & Recording Location Setup (Drive Health, Free Space, Folder Creation)
    - Stage 3: Hardware Profile & CPU Core Allocation (Gamer Mode, Low, Balanced, High)
    - Stage 4: Camera Discovery, Network Radar Scan & Stream Verification
    - Stage 5: Final Summary & Workstation Launch
    """
    wizard_finished = pyqtSignal(dict)  # emits configured settings

    def __init__(self, is_demo: bool = True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CCTVPanelView - Workstation Setup Wizard")
        self.setFixedSize(880, 650)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)

        self.is_demo = is_demo
        self.rm = get_resource_manager()
        self.current_stage = 0

        # Accumulated setup parameters
        self.setup_data = {
            "recording_dir": "",
            "snapshot_dir": "",
            "performance_profile": PerformanceProfile.GAMER.value if self.rm.is_ryzen_dual_ccd else PerformanceProfile.MEDIUM.value,
            "cameras": [],
            "autostart": False,
            "minimize_to_tray": True,
        }

        self._setup_ui()
        self._goto_stage(0)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(0)

        # Outer obsidian glass frame
        self.container = QFrame(self)
        self.container.setObjectName("wizard_container")
        self.container.setStyleSheet("""
            QFrame#wizard_container {
                background-color: #080c16;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 245))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(self.container)
        c_layout.setContentsMargins(26, 18, 26, 20)
        c_layout.setSpacing(14)

        # --- 1. Top Header Bar (Brand Capsule + Close Control) ---
        hdr_layout = QHBoxLayout()
        hdr_layout.setContentsMargins(0, 0, 0, 0)
        hdr_layout.setSpacing(8)

        capsule_brand = QFrame(self.container)
        capsule_brand.setObjectName("capsule_brand")
        capsule_brand.setStyleSheet("""
            QFrame#capsule_brand {
                background-color: rgba(15, 23, 42, 0.78);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 17px;
            }
        """)
        brand_layout = QHBoxLayout(capsule_brand)
        brand_layout.setContentsMargins(10, 4, 14, 4)
        brand_layout.setSpacing(8)

        lbl_logo = QLabel(capsule_brand)
        lbl_logo.setStyleSheet("background: transparent; border: none;")
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "app_icon_clean.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "app_icon_clean.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "app_icon.png")

        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_logo.setPixmap(pix)
            lbl_logo.setFixedSize(22, 22)
            brand_layout.addWidget(lbl_logo)

        lbl_brand_text = QLabel(capsule_brand)
        lbl_brand_text.setStyleSheet("background: transparent; border: none;")
        lbl_brand_text.setText(
            '<span style="font-family: \'Segoe UI Variable Display\', \'Segoe UI\', sans-serif; font-size: 14px; font-weight: 750; letter-spacing: 0.6px; color: #f8fafc;">CCTV</span> '
            '<span style="font-family: \'Segoe UI Variable Display\', \'Segoe UI\', sans-serif; font-size: 14px; font-weight: 350; letter-spacing: 0.6px; color: #38bdf8;">PanelView</span>'
        )
        brand_layout.addWidget(lbl_brand_text)
        hdr_layout.addWidget(capsule_brand)

        hdr_layout.addSpacing(6)
        mode_text = "SETUP WIZARD (DEMO PREVIEW)" if self.is_demo else "WORKSTATION INITIAL SETUP"
        self.lbl_mode = QLabel(mode_text, self.container)
        self.lbl_mode.setStyleSheet("color: #64748b; font-size: 10.5px; font-weight: 700; letter-spacing: 1px;")
        hdr_layout.addWidget(self.lbl_mode)

        hdr_layout.addStretch()

        # Frameless window close button
        capsule_ctrl = QFrame(self.container)
        capsule_ctrl.setObjectName("capsule_ctrl")
        capsule_ctrl.setStyleSheet("""
            QFrame#capsule_ctrl {
                background-color: rgba(15, 23, 42, 0.78);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 17px;
            }
        """)
        ctrl_layout = QHBoxLayout(capsule_ctrl)
        ctrl_layout.setContentsMargins(3, 3, 3, 3)
        ctrl_layout.setSpacing(0)

        btn_close = QPushButton(capsule_ctrl)
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setToolTip("Exit Setup (ESC)")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.14);
            }
        """)
        btn_close_layout = QVBoxLayout(btn_close)
        btn_close_layout.setContentsMargins(0, 0, 0, 0)
        btn_close_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_close_icon = QLabel(btn_close)
        lbl_close_icon.setStyleSheet("background: transparent; border: none;")
        lbl_close_icon.setPixmap(create_vector_icon("close", color="#94a3b8", size=14))
        btn_close_layout.addWidget(lbl_close_icon)
        btn_close.clicked.connect(self.reject)
        ctrl_layout.addWidget(btn_close)
        hdr_layout.addWidget(capsule_ctrl)

        c_layout.addLayout(hdr_layout)

        # --- 2. Spacious Horizontal Stepper Bar ---
        self.stepper_container = QFrame(self.container)
        self.stepper_container.setObjectName("stepper_container")
        self.stepper_container.setStyleSheet("""
            QFrame#stepper_container {
                background-color: rgba(15, 23, 42, 0.50);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 4px;
            }
        """)
        self.stepper_layout = QHBoxLayout(self.stepper_container)
        self.stepper_layout.setContentsMargins(14, 6, 14, 6)
        self.stepper_layout.setSpacing(10)

        self.step_widgets = []
        stages = [
            ("1", "Welcome"),
            ("2", "Storage Location"),
            ("3", "Hardware Profile"),
            ("4", "Camera Setup"),
            ("5", "Launch"),
        ]
        for idx, (num, name) in enumerate(stages):
            node = QWidget(self.stepper_container)
            n_layout = QHBoxLayout(node)
            n_layout.setContentsMargins(0, 0, 0, 0)
            n_layout.setSpacing(6)

            badge = QFrame(node)
            badge.setFixedSize(22, 22)
            b_box = QVBoxLayout(badge)
            b_box.setContentsMargins(0, 0, 0, 0)
            b_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_badge = QLabel(num, badge)
            lbl_badge.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 750; background: transparent; border: none;")
            b_box.addWidget(lbl_badge)
            n_layout.addWidget(badge)

            lbl_name = QLabel(name, node)
            lbl_name.setStyleSheet("color: #cbd5e1; font-size: 11.5px; font-weight: 600; background: transparent; border: none;")
            n_layout.addWidget(lbl_name)

            self.step_widgets.append((badge, lbl_badge, lbl_name))
            self.stepper_layout.addWidget(node)

            if idx < len(stages) - 1:
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.12);")
                self.stepper_layout.addWidget(sep, stretch=1)

        c_layout.addWidget(self.stepper_container)

        # Divider
        sep_mid = QFrame(self.container)
        sep_mid.setFixedHeight(1)
        sep_mid.setStyleSheet("background-color: rgba(255, 255, 255, 0.07); border: none;")
        c_layout.addWidget(sep_mid)

        # --- 3. Stacked Pages for the 5 Stages ---
        self.stack = QStackedWidget(self.container)
        self.page1_welcome = self._create_page_welcome()
        self.page2_storage = self._create_page_storage()
        self.page3_hardware = self._create_page_hardware()
        self.page4_cameras = self._create_page_cameras()
        self.page5_summary = self._create_page_summary()

        self.stack.addWidget(self.page1_welcome)
        self.stack.addWidget(self.page2_storage)
        self.stack.addWidget(self.page3_hardware)
        self.stack.addWidget(self.page4_cameras)
        self.stack.addWidget(self.page5_summary)

        c_layout.addWidget(self.stack, stretch=1)

        # --- 4. Navigation Action Buttons ---
        self.nav_layout = QHBoxLayout()
        self.nav_layout.setContentsMargins(0, 4, 0, 0)

        self.btn_back = QPushButton("Back", self.container)
        self.btn_back.setFixedSize(90, 34)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 41, 59, 0.7);
                color: #cbd5e1;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)
        self.btn_back.clicked.connect(self._on_back_clicked)
        self.nav_layout.addWidget(self.btn_back)

        self.nav_layout.addStretch()

        self.btn_next = QPushButton("Continue", self.container)
        self.btn_next.setFixedSize(140, 34)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #0369a1;
                border-color: #60a5fa;
            }
            QPushButton:pressed {
                background-color: #075985;
            }
        """)
        self.btn_next.clicked.connect(self._on_next_clicked)
        self.nav_layout.addWidget(self.btn_next)

        c_layout.addLayout(self.nav_layout)
        root.addWidget(self.container)

    # -------------------------------------------------------------
    # Stage 1: Welcome & Overview
    # -------------------------------------------------------------
    def _create_page_welcome(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(14)

        # Hero Banner
        hero = QFrame(w)
        hero.setObjectName("hero_frame")
        hero.setStyleSheet("""
            QFrame#hero_frame {
                background-color: rgba(15, 23, 42, 0.75);
                border: 1px solid rgba(56, 189, 248, 0.30);
                border-radius: 12px;
            }
            QFrame#hero_frame QLabel {
                background: transparent;
                border: none;
            }
        """)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 16, 20, 16)
        hero_layout.setSpacing(20)

        # Left: Large Icon
        lbl_hero_icon = QLabel(hero)
        lbl_hero_icon.setStyleSheet("background: transparent; border: none;")
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "app_icon_clean.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "app_icon_clean.png")
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_hero_icon.setPixmap(pix)
            lbl_hero_icon.setFixedSize(64, 64)
        hero_layout.addWidget(lbl_hero_icon)

        # Right: Hero Titles
        txt_box = QVBoxLayout()
        txt_box.setSpacing(4)
        lbl_h1 = QLabel("Welcome to CCTVPanelView Workstation", hero)
        lbl_h1.setStyleSheet("color: #f8fafc; font-size: 18px; font-weight: 750;")
        lbl_h2 = QLabel("Professional Local-First AI Surveillance Suite", hero)
        lbl_h2.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 600;")
        lbl_h3 = QLabel("High-speed 2K monitoring, on-device AI computer vision, and continuous 24/7 recording with zero subscription fees and zero cloud dependencies.", hero)
        lbl_h3.setWordWrap(True)
        lbl_h3.setStyleSheet("color: #94a3b8; font-size: 11.5px; line-height: 1.4;")
        txt_box.addWidget(lbl_h1)
        txt_box.addWidget(lbl_h2)
        txt_box.addWidget(lbl_h3)
        hero_layout.addLayout(txt_box, stretch=1)
        layout.addWidget(hero)

        # Feature Cards Grid
        features_grid = QGridLayout()
        features_grid.setSpacing(10)

        features = [
            ("100% Local Privacy & Storage", "All live video feeds and 24/7 MP4 recordings remain exclusively on your workstation's high-speed NVMe/HDD storage."),
            ("On-Device AI Computer Vision", "Real-time human, vehicle, and animal detection running directly on your CPU/GPU hardware without cloud latency."),
            ("Dual-Lens & PTZ Synchronization", "Simultaneous wide panoramic and optical PTZ zoom tracking seamlessly integrated into high-framerate grids."),
            ("Workstation Hardware Isolation", "Dedicated CPU affinity profiling ensures 24/7 surveillance never impacts your gaming FPS or productivity."),
        ]

        for i, (f_title, f_desc) in enumerate(features):
            card = QFrame(w)
            card.setObjectName(f"feat_card_{i}")
            card.setStyleSheet(f"""
                QFrame#feat_card_{i} {{
                    background-color: rgba(15, 23, 42, 0.60);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 10px;
                }}
                QFrame#feat_card_{i} QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
            c_box = QVBoxLayout(card)
            c_box.setContentsMargins(14, 12, 14, 12)
            c_box.setSpacing(4)
            lbl_t = QLabel(f_title, card)
            lbl_t.setStyleSheet("color: #38bdf8; font-size: 12.5px; font-weight: 700;")
            lbl_d = QLabel(f_desc, card)
            lbl_d.setWordWrap(True)
            lbl_d.setStyleSheet("color: #94a3b8; font-size: 11px; line-height: 1.35;")
            c_box.addWidget(lbl_t)
            c_box.addWidget(lbl_d)
            features_grid.addWidget(card, i // 2, i % 2)

        layout.addLayout(features_grid)
        layout.addStretch()
        return w

    # -------------------------------------------------------------
    # Stage 2: Storage & Recording Location
    # -------------------------------------------------------------
    def _create_page_storage(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        lbl_title = QLabel("Surveillance Storage & Recording Location", w)
        lbl_title.setStyleSheet("color: #f1f5f9; font-size: 16px; font-weight: 700;")
        lbl_desc = QLabel(
            "Select where continuous 24/7 video streams, smart AI event clips, and snapshots will be saved.\n"
            "High-bitrate 2K surveillance typically consumes 15–25 GB per camera stream per day.",
            w
        )
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 11.5px; line-height: 1.4;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)

        # Drive Detection List
        lbl_drives_header = QLabel("DETECTED WORKSTATION STORAGE DRIVES:", w)
        lbl_drives_header.setStyleSheet("color: #64748b; font-size: 10.5px; font-weight: 700; letter-spacing: 0.8px;")
        layout.addWidget(lbl_drives_header)

        self.drive_cards_layout = QHBoxLayout()
        self.drive_cards_layout.setSpacing(8)
        self.detected_drives = []

        try:
            for p in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    free_gb = usage.free / (1024**3)
                    total_gb = usage.total / (1024**3)
                    self.detected_drives.append({
                        "letter": p.device.replace("\\", ""),
                        "mount": p.mountpoint,
                        "free_gb": free_gb,
                        "total_gb": total_gb,
                        "used_pct": usage.percent
                    })
                except Exception:
                    pass
        except Exception:
            pass

        self.detected_drives.sort(key=lambda d: d["free_gb"], reverse=True)
        recommended_drive = self.detected_drives[0]["letter"] if self.detected_drives else "C:"

        self.drive_buttons = {}
        for d in self.detected_drives[:4]:
            let = d["letter"]
            btn = QPushButton(w)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(64)
            is_rec = (let == recommended_drive)
            rec_tag = " (Recommended)" if is_rec else ""
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'rgba(56, 189, 248, 0.12)' if is_rec else 'rgba(15, 23, 42, 0.70)'};
                    border: 1px solid {'#38bdf8' if is_rec else 'rgba(255, 255, 255, 0.10)'};
                    border-radius: 8px;
                    text-align: left;
                    padding: 8px 12px;
                }}
                QPushButton:hover {{
                    border-color: #38bdf8;
                }}
            """)
            d_box = QVBoxLayout(btn)
            d_box.setContentsMargins(6, 4, 6, 4)
            d_box.setSpacing(2)
            lbl_d_let = QLabel(f"Drive {let}{rec_tag}", btn)
            lbl_d_let.setStyleSheet(f"color: {'#38bdf8' if is_rec else '#f8fafc'}; font-weight: 700; font-size: 12px; background: transparent;")
            lbl_d_sp = QLabel(f"{d['free_gb']:.0f} GB Free / {d['total_gb']:.0f} GB", btn)
            lbl_d_sp.setStyleSheet("color: #94a3b8; font-size: 10.5px; background: transparent;")
            d_box.addWidget(lbl_d_let)
            d_box.addWidget(lbl_d_sp)

            btn.clicked.connect(lambda ch, l=let: self._select_drive(l))
            self.drive_buttons[let] = btn
            self.drive_cards_layout.addWidget(btn)

        layout.addLayout(self.drive_cards_layout)

        # Path input row
        layout.addSpacing(6)
        path_box = QVBoxLayout()
        path_box.setSpacing(4)
        lbl_path_title = QLabel("Surveillance Root Directory:", w)
        lbl_path_title.setStyleSheet("color: #cbd5e1; font-size: 11.5px; font-weight: 600;")
        path_box.addWidget(lbl_path_title)

        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)

        gdrive_sub = os.path.join(recommended_drive + "\\", "My Drive")
        if os.path.exists(gdrive_sub):
            default_root = os.path.join(gdrive_sub, "CCTV_Surveillance")
        else:
            default_root = os.path.join(recommended_drive + "\\", "CCTV_Surveillance")
        self.txt_storage_path = QLineEdit(default_root, w)
        self.txt_storage_path.setStyleSheet("""
            QLineEdit {
                background-color: rgba(15, 23, 42, 0.90);
                color: #f8fafc;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 8px;
                padding: 7px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
            }
        """)
        picker_row.addWidget(self.txt_storage_path, stretch=1)

        btn_browse = QPushButton("Browse...", w)
        btn_browse.setFixedSize(96, 34)
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 8px;
                font-size: 11.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #ffffff;
            }
        """)
        btn_browse.clicked.connect(self._browse_storage_folder)
        picker_row.addWidget(btn_browse)
        path_box.addLayout(picker_row)
        layout.addLayout(path_box)

        # Folder structure explanation card
        layout.addSpacing(4)
        info_card = QFrame(w)
        info_card.setObjectName("info_card")
        info_card.setStyleSheet("""
            QFrame#info_card {
                background-color: rgba(15, 23, 42, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            QFrame#info_card QLabel {
                background: transparent;
                border: none;
            }
        """)
        ic_layout = QVBoxLayout(info_card)
        ic_layout.setContentsMargins(14, 12, 14, 12)
        ic_layout.setSpacing(4)
        lbl_struct_title = QLabel("AUTOMATIC FOLDER STRUCTURE & RETENTION:", info_card)
        lbl_struct_title.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
        lbl_struct_desc = QLabel(
            "• \\recordings\\  — Continuous 24/7 cyclic MP4 footage (auto-recycled when disk headroom drops below 20 GB)\n"
            "• \\alerts\\       — 10-second high-priority smart AI detection clips (motion, persons, pets)\n"
            "• \\snapshots\\    — Timestamped high-resolution capture frames for incident verification",
            info_card
        )
        lbl_struct_desc.setStyleSheet("color: #94a3b8; font-size: 11px; line-height: 1.45;")
        ic_layout.addWidget(lbl_struct_title)
        ic_layout.addWidget(lbl_struct_desc)
        layout.addWidget(info_card)

        layout.addStretch()
        return w

    def _select_drive(self, drive_letter: str):
        gdrive_sub = os.path.join(drive_letter + "\\", "My Drive")
        if os.path.exists(gdrive_sub):
            target = os.path.join(gdrive_sub, "CCTV_Surveillance")
        else:
            target = os.path.join(drive_letter + "\\", "CCTV_Surveillance")
        self.txt_storage_path.setText(target)
        for let, btn in self.drive_buttons.items():
            is_active = (let == drive_letter)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'rgba(56, 189, 248, 0.12)' if is_active else 'rgba(15, 23, 42, 0.70)'};
                    border: 1px solid {'#38bdf8' if is_active else 'rgba(255, 255, 255, 0.10)'};
                    border-radius: 8px;
                    text-align: left;
                    padding: 8px 12px;
                }}
            """)

    def _browse_storage_folder(self):
        curr = self.txt_storage_path.text()
        folder = QFileDialog.getExistingDirectory(self, "Select Surveillance Root Directory", curr)
        if folder:
            self.txt_storage_path.setText(folder)

    # -------------------------------------------------------------
    # Stage 3: Hardware Profile & CPU Allocation
    # -------------------------------------------------------------
    def _create_page_hardware(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        lbl_title = QLabel("Hardware Architecture & CPU Core Allocation", w)
        lbl_title.setStyleSheet("color: #f1f5f9; font-size: 16px; font-weight: 700;")
        lbl_desc = QLabel(
            f"Detected Hardware: {self.rm.cpu_name} ({self.rm.total_cores} Logical Cores)\n"
            "Select an operational preset to balance camera stream framerates with workstation responsiveness.",
            w
        )
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 11.5px; line-height: 1.4;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)

        self.hw_profile_cards = {}
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(8)

        if self.rm.is_ryzen_dual_ccd:
            profiles = [
                (
                    PerformanceProfile.GAMER.value,
                    "Gamer Mode (Chiplet 2 / CCD1 Only) - Recommended",
                    "Cores 12-15 (Gaming Isolated)",
                    "Locks CCTVPanelView strictly to Chiplet 2 (Cores 12-15). Keeps Chiplet 1 (Cores 0-11) & its 32MB L3 Cache 100% untouched for gaming with zero stutter."
                ),
                (
                    PerformanceProfile.LOW.value,
                    "Low Usage (Eco Mode / Chiplet 2)",
                    "Cores 12-13 (Max 6% CPU)",
                    "Locks to 2 cores on Chiplet 2, 10 FPS grid with lightweight sub-streams, motion-gated AI. Zero CPU impact on games."
                ),
                (
                    PerformanceProfile.MEDIUM.value,
                    "Medium Usage (Balanced / Chiplet 2)",
                    "Cores 12-15 (15-20% CPU)",
                    "4 cores on Chiplet 2, 15 FPS monitoring with Mid-HD feeds, responsive AI animal/person detection."
                ),
                (
                    PerformanceProfile.HIGH.value,
                    "High Usage (Max Performance / All Cores)",
                    f"All {self.rm.total_cores} Cores (Full Power)",
                    "Unrestricted native 2K feeds on all tiles, full 25-30 FPS across both Chiplets, continuous AI detection."
                )
            ]
        else:
            profiles = [
                (
                    PerformanceProfile.LOW.value,
                    "Low Usage (Eco Mode)",
                    "2 Cores (Max 8% CPU)",
                    "Locks CCTVPanelView to 2 CPU cores, runs 10 FPS grid with lightweight sub-streams, and gates AI inference only when motion occurs."
                ),
                (
                    PerformanceProfile.MEDIUM.value,
                    "Medium Usage (Balanced) - Recommended",
                    "4 Cores (15-25% CPU)",
                    "Smooth 15 FPS monitoring with Mid-HD feeds, responsive AI alarms, and balanced 4-core multi-threading."
                ),
                (
                    PerformanceProfile.HIGH.value,
                    "High Usage (Max Performance)",
                    f"All {self.rm.total_cores} Cores (Full Power)",
                    "Unrestricted native 2K feeds on all tiles, full 25-30 FPS, continuous AI detection and zero downscaling."
                )
            ]

        for p_key, title, tag, desc in profiles:
            btn = QPushButton(w)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName(f"hw_opt_{p_key}")
            btn.setFixedHeight(68)
            b_layout = QHBoxLayout(btn)
            b_layout.setContentsMargins(14, 8, 14, 8)
            b_layout.setSpacing(12)

            dot = QFrame(btn)
            dot.setFixedSize(14, 14)
            dot.setObjectName("dot")
            b_layout.addWidget(dot)

            t_box = QVBoxLayout()
            t_box.setSpacing(2)
            row = QHBoxLayout()
            lbl_t = QLabel(title, btn)
            lbl_t.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: 700; background: transparent;")
            lbl_tag = QLabel(tag, btn)
            lbl_tag.setStyleSheet("color: #38bdf8; font-size: 9.5px; font-weight: 700; background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 4px; padding: 1px 6px;")
            row.addWidget(lbl_t)
            row.addStretch()
            row.addWidget(lbl_tag)
            t_box.addLayout(row)

            lbl_d = QLabel(desc, btn)
            lbl_d.setWordWrap(True)
            lbl_d.setStyleSheet("color: #94a3b8; font-size: 10.5px; background: transparent;")
            t_box.addWidget(lbl_d)

            b_layout.addLayout(t_box, stretch=1)
            btn.clicked.connect(lambda ch, k=p_key: self._select_hw_profile(k))
            self.hw_profile_cards[p_key] = (btn, dot)
            cards_layout.addWidget(btn)

        layout.addLayout(cards_layout)
        self._highlight_hw_profile()

        layout.addStretch()
        return w

    def _select_hw_profile(self, profile_key: str):
        self.setup_data["performance_profile"] = profile_key
        self._highlight_hw_profile()

    def _highlight_hw_profile(self):
        sel = self.setup_data["performance_profile"]
        for k, (btn, dot) in self.hw_profile_cards.items():
            if k == sel:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(15, 23, 42, 0.95);
                        border: 1px solid #38bdf8;
                        border-radius: 10px;
                        text-align: left;
                    }
                """)
                dot.setStyleSheet("background-color: #38bdf8; border: 2px solid #0284c7; border-radius: 7px;")
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(15, 23, 42, 0.65);
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 10px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        border-color: rgba(56, 189, 248, 0.45);
                    }
                """)
                dot.setStyleSheet("background-color: rgba(11, 15, 25, 0.8); border: 2px solid rgba(255, 255, 255, 0.20); border-radius: 7px;")

    # -------------------------------------------------------------
    # Stage 4: Camera Discovery & Stream Testing
    # -------------------------------------------------------------
    def _create_page_cameras(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        lbl_title = QLabel("Surveillance Cameras & Stream Verification", w)
        lbl_title.setStyleSheet("color: #f1f5f9; font-size: 16px; font-weight: 700;")
        lbl_desc = QLabel(
            "Scan your local network for active ONVIF and RTSP cameras, or connect to test feeds.\n"
            "Each camera will be tested for connection and added to your multi-tile monitoring grid.",
            w
        )
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 11.5px; line-height: 1.4;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)

        # Radar scanner & manual adder layout
        middle_box = QHBoxLayout()
        middle_box.setSpacing(14)

        # Left: Network Radar Scanner Box
        scanner_frame = QFrame(w)
        scanner_frame.setFixedWidth(200)
        scanner_frame.setObjectName("scanner_frame")
        scanner_frame.setStyleSheet("""
            QFrame#scanner_frame {
                background-color: rgba(15, 23, 42, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            QFrame#scanner_frame QLabel {
                background: transparent;
                border: none;
            }
        """)
        s_layout = QVBoxLayout(scanner_frame)
        s_layout.setContentsMargins(14, 14, 14, 14)
        s_layout.setSpacing(10)
        s_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.radar_widget = RadarSweepWidget(size=96, parent=scanner_frame)
        s_layout.addWidget(self.radar_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        sub_row = QHBoxLayout()
        sub_row.setSpacing(6)
        lbl_sub = QLabel("Subnet:", scanner_frame)
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 11px;")
        sub_row.addWidget(lbl_sub)

        def_subnet = "192.168.0"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            def_subnet = ".".join(s.getsockname()[0].split(".")[:3])
            s.close()
        except Exception:
            pass

        self.txt_subnet = QLineEdit(def_subnet, scanner_frame)
        self.txt_subnet.setStyleSheet("""
            QLineEdit {
                background-color: rgba(11, 15, 25, 0.9);
                color: #f8fafc;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
            }
        """)
        sub_row.addWidget(self.txt_subnet)
        s_layout.addLayout(sub_row)

        self.btn_radar_scan = QPushButton("Scan Local Network", scanner_frame)
        self.btn_radar_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_radar_scan.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_radar_scan.clicked.connect(self._run_network_scan)
        s_layout.addWidget(self.btn_radar_scan)

        self.lbl_scan_status = QLabel("Ready to scan", scanner_frame)
        self.lbl_scan_status.setStyleSheet("color: #64748b; font-size: 10.5px;")
        s_layout.addWidget(self.lbl_scan_status, alignment=Qt.AlignmentFlag.AlignCenter)

        middle_box.addWidget(scanner_frame)

        # Right: Configured Cameras List
        list_frame = QFrame(w)
        list_frame.setObjectName("list_frame")
        list_frame.setStyleSheet("""
            QFrame#list_frame {
                background-color: rgba(15, 23, 42, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            QFrame#list_frame QLabel {
                background: transparent;
                border: none;
            }
        """)
        l_layout = QVBoxLayout(list_frame)
        l_layout.setContentsMargins(14, 14, 14, 14)
        l_layout.setSpacing(8)

        l_hdr = QHBoxLayout()
        l_hdr.setSpacing(8)
        lbl_list_t = QLabel("CAMERA INVENTORY", list_frame)
        lbl_list_t.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 750; letter-spacing: 0.6px;")
        l_hdr.addWidget(lbl_list_t)
        l_hdr.addStretch()

        btn_add_manual = QPushButton("+ Add Camera Manually", list_frame)
        btn_add_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_manual.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                font-size: 10.5px;
                font-weight: 700;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        btn_add_manual.clicked.connect(self._add_manual_camera)
        l_hdr.addWidget(btn_add_manual)

        btn_add_demo = QPushButton("+ Add Demo Feeds", list_frame)
        btn_add_demo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_demo.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 6px;
                font-size: 10.5px;
                font-weight: 600;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.15);
            }
        """)
        btn_add_demo.clicked.connect(self._add_demo_cameras)
        l_hdr.addWidget(btn_add_demo)
        l_layout.addLayout(l_hdr)

        # Guidance Banner Card
        tip_frame = QFrame(list_frame)
        tip_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(56, 189, 248, 0.08);
                border: 1px solid rgba(56, 189, 248, 0.22);
                border-radius: 6px;
            }
        """)
        tip_box = QHBoxLayout(tip_frame)
        tip_box.setContentsMargins(10, 6, 10, 6)
        lbl_tip = QLabel(
            "<b>Camera Setup Guide:</b> Surveillance cameras require local credentials (admin & password set during camera mobile setup) to unlock the live RTSP stream. Click <b>Configure</b> on each camera below to set credentials and verify video connectivity.",
            tip_frame
        )
        lbl_tip.setWordWrap(True)
        lbl_tip.setStyleSheet("color: #cbd5e1; font-size: 10.5px; line-height: 1.4; background: transparent; border: none;")
        tip_box.addWidget(lbl_tip)
        l_layout.addWidget(tip_frame)

        self.scroll_cameras = QScrollArea(list_frame)
        self.scroll_cameras.setWidgetResizable(True)
        self.scroll_cameras.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_cameras.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(15, 23, 42, 0.3);
                width: 6px;
                border-radius: 3px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(56, 189, 248, 0.35);
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #38bdf8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self.cameras_container = QWidget()
        self.cameras_container_layout = QVBoxLayout(self.cameras_container)
        self.cameras_container_layout.setContentsMargins(0, 0, 10, 0)
        self.cameras_container_layout.setSpacing(6)
        self.scroll_cameras.setWidget(self.cameras_container)
        l_layout.addWidget(self.scroll_cameras, stretch=1)

        middle_box.addWidget(list_frame, stretch=1)
        layout.addLayout(middle_box, stretch=1)

        self._refresh_cameras_list()
        return w

    def _add_manual_camera(self):
        dlg = DeviceDialog(parent=self)
        if dlg.exec():
            new_cam = dlg.result_data
            new_cam["configured"] = True
            # Check duplicate ID/IP
            self.setup_data["cameras"] = [c for c in self.setup_data["cameras"] if c.get("ip") != new_cam.get("ip")]
            self.setup_data["cameras"].append(new_cam)
            self._refresh_cameras_list()

    def _configure_camera(self, cam_id: str):
        target_cam = next((c for c in self.setup_data["cameras"] if c.get("id") == cam_id), None)
        if not target_cam:
            return
        dlg = DeviceDialog(camera_data=dict(target_cam), parent=self)
        if dlg.exec():
            updated = dlg.result_data
            updated["configured"] = True
            for idx, c in enumerate(self.setup_data["cameras"]):
                if c.get("id") == cam_id:
                    self.setup_data["cameras"][idx] = updated
                    break
            self._refresh_cameras_list()

    def _run_network_scan(self):
        self.lbl_scan_status.setText("Scanning subnet...")
        self.btn_radar_scan.setEnabled(False)
        subnet = self.txt_subnet.text().strip() or DeviceManager.get_local_subnet()

        class ScanThread(QThread):
            scan_complete = pyqtSignal(list)
            def run(self):
                res = DeviceManager.scan_local_subnet(subnet, 1, 254)
                self.scan_complete.emit(res)

        self.scan_worker = ScanThread(self)
        self.scan_worker.scan_complete.connect(self._on_scan_finished)
        self.scan_worker.start()

    def _on_scan_finished(self, found_devices: list):
        self.btn_radar_scan.setEnabled(True)
        count = len(found_devices)
        self.lbl_scan_status.setText(f"Scan complete: {count} device(s) found.")
        for dev in found_devices:
            ip = dev.get("ip")
            cam_entry = {
                "id": f"cam_{ip.replace('.', '_')}",
                "name": f"Camera {ip}",
                "ip": ip,
                "port": dev.get("port", 554),
                "username": "admin",
                "password": "",
                "is_dual_lens": False,
                "model": "CAM720 / Jooan Single Lens (2K HD)",
                "lens1_path": "/live/ch00_0",
                "lens2_path": "",
                "configured": False
            }
            if not any(c.get("ip") == ip for c in self.setup_data["cameras"]):
                self.setup_data["cameras"].append(cam_entry)
        self._refresh_cameras_list()

    def _add_demo_cameras(self):
        demo_cams = [
            {
                "id": "cam_front_dual",
                "name": "Front Yard (Dual-Lens PTZ)",
                "ip": "192.0.2.10",
                "port": 554,
                "username": "admin",
                "password": "",
                "is_dual_lens": True,
                "lens1_path": "/live/ch00_0",
                "lens2_path": "/live/ch01_0",
                "configured": True
            },
            {
                "id": "cam_driveway",
                "name": "Driveway & Entrance",
                "ip": "192.0.2.20",
                "port": 554,
                "username": "admin",
                "password": "",
                "is_dual_lens": False,
                "lens1_path": "/live/ch00_0",
                "lens2_path": "",
                "configured": True
            },
            {
                "id": "cam_backyard",
                "name": "Backyard Garden",
                "ip": "192.0.2.30",
                "port": 554,
                "username": "admin",
                "password": "",
                "is_dual_lens": False,
                "lens1_path": "/live/ch00_0",
                "lens2_path": "",
                "configured": True
            }
        ]
        for c in demo_cams:
            if not any(x.get("id") == c["id"] for x in self.setup_data["cameras"]):
                self.setup_data["cameras"].append(c)
        self._refresh_cameras_list()

    def _refresh_cameras_list(self):
        while self.cameras_container_layout.count():
            item = self.cameras_container_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        if not self.setup_data["cameras"]:
            lbl_empty = QLabel("No cameras added yet.\nClick 'Scan Local Network', '+ Add Camera Manually', or '+ Add Demo Feeds' to populate.", self.cameras_container)
            lbl_empty.setStyleSheet("color: #64748b; font-size: 11px; padding: 20px;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cameras_container_layout.addWidget(lbl_empty)
            return

        for cam in self.setup_data["cameras"]:
            cam_id = cam.get("id", "")
            row = QFrame(self.cameras_container)
            row.setObjectName(f"cam_row_{cam_id}")
            row.setStyleSheet(f"""
                QFrame#cam_row_{cam_id} {{
                    background-color: rgba(11, 15, 25, 0.85);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                }}
                QFrame#cam_row_{cam_id} QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
            r_box = QHBoxLayout(row)
            r_box.setContentsMargins(10, 6, 6, 6)
            r_box.setSpacing(6)

            lbl_ic = QLabel(row)
            lbl_ic.setStyleSheet("background: transparent; border: none;")
            lbl_ic.setPixmap(create_vector_icon("camera", color="#38bdf8", size=18))
            r_box.addWidget(lbl_ic, alignment=Qt.AlignmentFlag.AlignVCenter)

            info_box = QVBoxLayout()
            info_box.setSpacing(2)
            lbl_c_name = QLabel(cam.get("name", "Camera"), row)
            lbl_c_name.setStyleSheet("color: #f8fafc; font-weight: 700; font-size: 12px; background: transparent;")
            lens_info = "Dual-Lens" if cam.get("is_dual_lens") else "Single"
            user_info = f"User: {cam.get('username', 'admin')}"
            lbl_c_sub = QLabel(f"IP: {cam.get('ip')}:{cam.get('port', 554)}  •  {user_info}  •  {lens_info}", row)
            lbl_c_sub.setStyleSheet("color: #94a3b8; font-size: 10px; background: transparent;")
            info_box.addWidget(lbl_c_name)
            info_box.addWidget(lbl_c_sub)
            r_box.addLayout(info_box, stretch=1)

            # Verification / Setup Status Pill
            is_configured = cam.get("configured", False) or bool(cam.get("password"))
            lbl_status = QLabel("Configured" if is_configured else "Needs Setup", row)
            lbl_status.setFixedHeight(20)
            lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_configured:
                lbl_status.setStyleSheet("color: #10b981; font-size: 9.5px; font-weight: 750; background: rgba(16, 185, 129, 0.14); border: 1px solid rgba(16, 185, 129, 0.38); border-radius: 4px; padding: 1px 6px;")
            else:
                lbl_status.setStyleSheet("color: #f59e0b; font-size: 9.5px; font-weight: 750; background: rgba(245, 158, 11, 0.14); border: 1px solid rgba(245, 158, 11, 0.38); border-radius: 4px; padding: 1px 6px;")
            r_box.addWidget(lbl_status, alignment=Qt.AlignmentFlag.AlignVCenter)

            # Interactive Configure Button
            btn_cfg = QPushButton("Configure", row)
            btn_cfg.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cfg.setFixedSize(68, 24)
            btn_cfg.setStyleSheet("""
                QPushButton {
                    background-color: rgba(56, 189, 248, 0.12);
                    color: #38bdf8;
                    border: 1px solid rgba(56, 189, 248, 0.40);
                    border-radius: 5px;
                    font-size: 10.5px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #0284c7;
                    color: #ffffff;
                    border-color: #38bdf8;
                }
            """)
            btn_cfg.clicked.connect(lambda ch, c_id=cam_id: self._configure_camera(c_id))
            r_box.addWidget(btn_cfg, alignment=Qt.AlignmentFlag.AlignVCenter)

            # Remove Button
            btn_del = QPushButton("✕", row)
            btn_del.setFixedSize(20, 20)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #64748b;
                    border: none;
                    font-size: 12px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    color: #ef4444;
                }
            """)
            btn_del.clicked.connect(lambda ch, c_id=cam_id: self._remove_camera(c_id))
            r_box.addWidget(btn_del, alignment=Qt.AlignmentFlag.AlignVCenter)

            self.cameras_container_layout.addWidget(row)

    def _remove_camera(self, cam_id: str):
        self.setup_data["cameras"] = [c for c in self.setup_data["cameras"] if c.get("id") != cam_id]
        self._refresh_cameras_list()

    # -------------------------------------------------------------
    # Stage 5: Summary & Launch
    # -------------------------------------------------------------
    def _create_page_summary(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        lbl_title = QLabel("Setup Complete - Workstation Ready to Launch", w)
        lbl_title.setStyleSheet("color: #f1f5f9; font-size: 16px; font-weight: 700;")
        lbl_desc = QLabel("Your surveillance configuration is verified. Review settings before launching:", w)
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 11.5px;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)

        # Summary Grid Card
        self.summary_card = QFrame(w)
        self.summary_card.setObjectName("summary_card")
        self.summary_card.setStyleSheet("""
            QFrame#summary_card {
                background-color: rgba(15, 23, 42, 0.75);
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 12px;
            }
            QFrame#summary_card QLabel {
                background: transparent;
                border: none;
            }
        """)
        sum_layout = QVBoxLayout(self.summary_card)
        sum_layout.setContentsMargins(18, 16, 18, 16)
        sum_layout.setSpacing(10)

        self.lbl_sum_storage = QLabel("", self.summary_card)
        self.lbl_sum_storage.setStyleSheet("color: #f8fafc; font-size: 12px;")
        sum_layout.addWidget(self.lbl_sum_storage)

        self.lbl_sum_hw = QLabel("", self.summary_card)
        self.lbl_sum_hw.setStyleSheet("color: #f8fafc; font-size: 12px;")
        sum_layout.addWidget(self.lbl_sum_hw)

        self.lbl_sum_cams = QLabel("", self.summary_card)
        self.lbl_sum_cams.setStyleSheet("color: #f8fafc; font-size: 12px;")
        sum_layout.addWidget(self.lbl_sum_cams)

        layout.addWidget(self.summary_card)

        # System Integration Checkboxes
        opts_box = QVBoxLayout()
        opts_box.setSpacing(6)

        self.chk_tray = QCheckBox("Minimize to system tray on close (maintain 24/7 background surveillance)", w)
        self.chk_tray.setChecked(True)
        self.chk_tray.setStyleSheet("color: #cbd5e1; font-size: 11.5px; font-weight: 600;")
        opts_box.addWidget(self.chk_tray)

        self.chk_autostart = QCheckBox("Launch CCTVPanelView automatically when Windows starts", w)
        self.chk_autostart.setChecked(False)
        self.chk_autostart.setStyleSheet("color: #cbd5e1; font-size: 11.5px; font-weight: 600;")
        opts_box.addWidget(self.chk_autostart)

        if self.is_demo:
            self.chk_save_real = QCheckBox("Apply these settings to live workstation configuration (Demo Preview mode)", w)
            self.chk_save_real.setChecked(False)
            self.chk_save_real.setStyleSheet("color: #38bdf8; font-size: 11.5px; font-weight: 600;")
            opts_box.addWidget(self.chk_save_real)

        layout.addLayout(opts_box)
        layout.addStretch()
        return w

    def _update_summary_card(self):
        s_path = self.txt_storage_path.text().strip()
        self.setup_data["recording_dir"] = os.path.join(s_path, "recordings")
        self.setup_data["snapshot_dir"] = os.path.join(s_path, "snapshots")

        cams_count = len(self.setup_data["cameras"])
        hw_prof = self.setup_data["performance_profile"].title()

        self.lbl_sum_storage.setText(f"<b>Surveillance Storage:</b> {s_path}<br><span style='color:#94a3b8; font-size:11px;'>24/7 continuous recordings and AI alert snapshots</span>")
        self.lbl_sum_hw.setText(f"<b>Hardware Architecture Profile:</b> {hw_prof} Mode<br><span style='color:#94a3b8; font-size:11px;'>Optimized core isolation ({self.rm.cpu_name})</span>")
        self.lbl_sum_cams.setText(f"<b>Surveillance Inventory:</b> {cams_count} Camera Feed(s) Configured<br><span style='color:#94a3b8; font-size:11px;'>Ready for 2K quad and multi-lens monitoring</span>")

    # -------------------------------------------------------------
    # Navigation & Stepper Transitions
    # -------------------------------------------------------------
    def _goto_stage(self, stage_idx: int):
        self.current_stage = stage_idx
        self.stack.setCurrentIndex(stage_idx)

        # Update Stepper Indicators
        for idx, (badge, lbl_badge, lbl_name) in enumerate(self.step_widgets):
            if idx == stage_idx:
                badge.setStyleSheet("""
                    QFrame {
                        background-color: rgba(56, 189, 248, 0.20);
                        border: 2px solid #38bdf8;
                        border-radius: 11px;
                    }
                """)
                lbl_badge.setText(str(idx + 1))
                lbl_badge.setStyleSheet("color: #38bdf8; font-weight: 800; font-size: 11px; background: transparent;")
                lbl_name.setStyleSheet("color: #f8fafc; font-weight: 750; font-size: 11.5px; background: transparent;")
            elif idx < stage_idx:
                badge.setStyleSheet("""
                    QFrame {
                        background-color: #0284c7;
                        border: 1px solid #38bdf8;
                        border-radius: 11px;
                    }
                """)
                lbl_badge.setText("✓")
                lbl_badge.setStyleSheet("color: #ffffff; font-weight: 800; font-size: 11px; background: transparent;")
                lbl_name.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 11.5px; background: transparent;")
            else:
                badge.setStyleSheet("""
                    QFrame {
                        background-color: rgba(15, 23, 42, 0.70);
                        border: 1px solid rgba(255, 255, 255, 0.12);
                        border-radius: 11px;
                    }
                """)
                lbl_badge.setText(str(idx + 1))
                lbl_badge.setStyleSheet("color: #64748b; font-weight: 700; font-size: 11px; background: transparent;")
                lbl_name.setStyleSheet("color: #64748b; font-weight: 500; font-size: 11.5px; background: transparent;")

        self.btn_back.setVisible(stage_idx > 0)

        if stage_idx == 4:
            self._update_summary_card()
            self.btn_next.setText("Complete && Launch")
            self.btn_next.setFixedWidth(160)
        elif stage_idx == 0:
            self.btn_next.setText("Get Started")
            self.btn_next.setFixedWidth(120)
        else:
            self.btn_next.setText("Continue")
            self.btn_next.setFixedWidth(120)

    def _on_next_clicked(self):
        if self.current_stage == 1:
            raw_path = self.txt_storage_path.text().strip()
            if not raw_path:
                return
            drive = os.path.splitdrive(raw_path)[0]
            gdrive = os.path.join(drive + "\\", "My Drive")
            if os.path.exists(gdrive) and "My Drive" not in raw_path:
                raw_path = os.path.join(gdrive, "CCTV_Surveillance")
                self.txt_storage_path.setText(raw_path)
            try:
                os.makedirs(raw_path, exist_ok=True)
            except Exception as e:
                fallback = r"G:\CCTV_Surveillance" if os.path.exists("G:\\") else r"C:\CCTV_Surveillance"
                self.txt_storage_path.setText(fallback)
                try:
                    os.makedirs(fallback, exist_ok=True)
                except Exception:
                    pass

        if self.current_stage < 4:
            self._goto_stage(self.current_stage + 1)
        else:
            self._finish_setup()

    def _on_back_clicked(self):
        if self.current_stage > 0:
            self._goto_stage(self.current_stage - 1)

    def _finish_setup(self):
        self.setup_data["minimize_to_tray"] = self.chk_tray.isChecked()
        self.setup_data["autostart"] = self.chk_autostart.isChecked()

        if not self.is_demo or (hasattr(self, "chk_save_real") and self.chk_save_real.isChecked()):
            rec_dir = self.setup_data.get("recording_dir", "")
            snap_dir = self.setup_data.get("snapshot_dir", "")
            try:
                os.makedirs(rec_dir, exist_ok=True)
            except Exception:
                rec_dir = os.path.abspath("recordings")
                try:
                    os.makedirs(rec_dir, exist_ok=True)
                except Exception:
                    pass
                self.setup_data["recording_dir"] = rec_dir

            try:
                os.makedirs(snap_dir, exist_ok=True)
            except Exception:
                snap_dir = os.path.abspath("snapshots")
                try:
                    os.makedirs(snap_dir, exist_ok=True)
                except Exception:
                    pass
                self.setup_data["snapshot_dir"] = snap_dir

            try:
                from core.device_manager import DeviceManager
                dm = DeviceManager()
                if "app_settings" not in dm.config:
                    dm.config["app_settings"] = {}
                dm.config["app_settings"]["recording_dir"] = self.setup_data["recording_dir"]
                dm.config["app_settings"]["snapshot_dir"] = self.setup_data["snapshot_dir"]
                dm.config["app_settings"]["close_action"] = "tray" if self.setup_data["minimize_to_tray"] else "ask"
                dm.config["app_settings"]["performance_profile"] = self.setup_data.get("performance_profile", "gamer")
                dm.config["app_settings"]["has_completed_onboarding"] = True

                from core.onboarding_profiles import merge_setup_cameras
                self.setup_data["cameras"] = merge_setup_cameras(self.setup_data.get("cameras", []), dm.get_cameras())

                if self.setup_data["cameras"]:
                    dm.config["cameras"] = self.setup_data["cameras"]
                dm.save_config()
            except Exception as e:
                print(f"[Onboarding] Failed to save config: {e}")

        self.wizard_finished.emit(self.setup_data)
        self.accept()
