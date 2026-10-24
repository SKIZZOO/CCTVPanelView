import os
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QWidget, QGraphicsDropShadowEffect, QProgressBar, QGridLayout
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPixmap

from core.resource_manager import get_resource_manager, PerformanceProfile, PROFILE_DEFAULTS


def create_vector_icon(icon_type: str, color: str = "#38bdf8", size: int = 20) -> QPixmap:
    """Renders crisp vector iconography matching CCTVPanelView workstation aesthetic."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    if icon_type == "cpu":
        # CPU processor chip with contact pins
        p.drawRoundedRect(QRectF(size * 0.22, size * 0.22, size * 0.56, size * 0.56), 2, 2)
        p.drawRect(QRectF(size * 0.38, size * 0.38, size * 0.24, size * 0.24))
        for offset in (size * 0.35, size * 0.65):
            p.drawLine(int(offset), int(size * 0.10), int(offset), int(size * 0.22))
            p.drawLine(int(offset), int(size * 0.78), int(offset), int(size * 0.90))
            p.drawLine(int(size * 0.10), int(offset), int(size * 0.22), int(offset))
            p.drawLine(int(size * 0.78), int(offset), int(size * 0.90), int(offset))
    elif icon_type == "ram":
        # RAM Module with memory chips
        p.drawRoundedRect(QRectF(size * 0.14, size * 0.28, size * 0.72, size * 0.44), 2, 2)
        p.drawLine(int(size * 0.50), int(size * 0.60), int(size * 0.50), int(size * 0.72))
        p.drawRect(QRectF(size * 0.22, size * 0.36, size * 0.12, size * 0.18))
        p.drawRect(QRectF(size * 0.36, size * 0.36, size * 0.10, size * 0.18))
        p.drawRect(QRectF(size * 0.54, size * 0.36, size * 0.10, size * 0.18))
        p.drawRect(QRectF(size * 0.66, size * 0.36, size * 0.12, size * 0.18))
    elif icon_type == "gpu":
        # GPU graphics card with dual fans
        p.drawRoundedRect(QRectF(size * 0.14, size * 0.26, size * 0.72, size * 0.48), 2.5, 2.5)
        p.drawEllipse(QPointF(size * 0.36, size * 0.50), size * 0.14, size * 0.14)
        p.drawEllipse(QPointF(size * 0.64, size * 0.50), size * 0.14, size * 0.14)
        p.drawLine(int(size * 0.20), int(size * 0.74), int(size * 0.80), int(size * 0.74))
    elif icon_type == "storage":
        # Storage Drive
        p.drawRoundedRect(QRectF(size * 0.20, size * 0.20, size * 0.60, size * 0.60), 3, 3)
        p.drawEllipse(QPointF(size * 0.50, size * 0.46), size * 0.16, size * 0.16)
        p.drawPoint(QPointF(size * 0.50, size * 0.46))
        p.drawLine(int(size * 0.30), int(size * 0.68), int(size * 0.70), int(size * 0.68))
    elif icon_type == "close":
        p.drawLine(int(size * 0.28), int(size * 0.28), int(size * 0.72), int(size * 0.72))
        p.drawLine(int(size * 0.72), int(size * 0.28), int(size * 0.28), int(size * 0.72))

    p.end()
    return pix


class TelemetryCard(QFrame):
    """Sleek metric tile displaying real-time hardware usage."""
    def __init__(self, icon_type: str, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("telemetry_card")
        self.setStyleSheet("""
            QFrame#telemetry_card {
                background-color: rgba(15, 23, 42, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header: Icon + Title
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        lbl_icon = QLabel(self)
        lbl_icon.setStyleSheet("background: transparent; border: none;")
        lbl_icon.setPixmap(create_vector_icon(icon_type, color="#38bdf8", size=18))
        hdr.addWidget(lbl_icon)

        lbl_title = QLabel(title.upper(), self)
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 10.5px; font-weight: 700; letter-spacing: 0.8px; background: transparent; border: none;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()
        layout.addLayout(hdr)

        # Main Value
        self.lbl_value = QLabel("--", self)
        self.lbl_value.setStyleSheet("color: #f8fafc; font-size: 15.5px; font-weight: 750; background: transparent; border: none;")
        layout.addWidget(self.lbl_value)

        # Progress bar
        self.progress = QProgressBar(self)
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #38bdf8;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress)

        # Subtext details
        self.lbl_detail = QLabel("--", self)
        self.lbl_detail.setStyleSheet("color: #64748b; font-size: 10.5px; background: transparent; border: none;")
        layout.addWidget(self.lbl_detail)


class ProfileOptionCard(QFrame):
    """
    Performance preset option card matching the workstation theme.
    No rainbow pill badges! Clean unified Sky Blue & Slate aesthetic.
    """
    clicked = pyqtSignal()

    def __init__(self, key: str, title: str, core_tag: str, description: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.is_selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName(f"profile_card_{key}")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 16, 12)
        layout.setSpacing(14)

        # Radio selection indicator
        self.radio_box = QFrame(self)
        self.radio_box.setFixedSize(20, 20)
        self.radio_box.setStyleSheet("""
            QFrame {
                border: 2px solid rgba(255, 255, 255, 0.20);
                border-radius: 10px;
                background-color: rgba(11, 15, 25, 0.8);
            }
        """)
        rb_layout = QVBoxLayout(self.radio_box)
        rb_layout.setContentsMargins(0, 0, 0, 0)
        rb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.radio_dot = QFrame(self.radio_box)
        self.radio_dot.setFixedSize(8, 8)
        self.radio_dot.setStyleSheet("background: transparent; border-radius: 4px;")
        rb_layout.addWidget(self.radio_dot)
        layout.addWidget(self.radio_box)

        # Content
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        self.lbl_title = QLabel(title, self)
        self.lbl_title.setStyleSheet("color: #f8fafc; font-size: 13.5px; font-weight: 700; background: transparent; border: none;")
        title_row.addWidget(self.lbl_title)

        title_row.addStretch()

        self.lbl_tag = QLabel(core_tag, self)
        self.lbl_tag.setStyleSheet("""
            QLabel {
                color: #38bdf8;
                font-size: 10px;
                font-weight: 700;
                background-color: rgba(56, 189, 248, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 4px;
                padding: 1px 7px;
            }
        """)
        title_row.addWidget(self.lbl_tag)
        text_layout.addLayout(title_row)

        self.lbl_desc = QLabel(description, self)
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("color: #94a3b8; font-size: 11px; line-height: 1.35; background: transparent; border: none;")
        text_layout.addWidget(self.lbl_desc)

        layout.addLayout(text_layout, stretch=1)
        self.set_selected(False)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(15, 23, 42, 0.95);
                    border: 1px solid #38bdf8;
                    border-radius: 10px;
                }
            """)
            self.radio_box.setStyleSheet("""
                QFrame {
                    border: 2px solid #38bdf8;
                    border-radius: 10px;
                    background-color: rgba(56, 189, 248, 0.15);
                }
            """)
            self.radio_dot.setStyleSheet("background-color: #38bdf8; border-radius: 4px;")
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(15, 23, 42, 0.65);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 10px;
                }
            """)
            self.radio_box.setStyleSheet("""
                QFrame {
                    border: 2px solid rgba(255, 255, 255, 0.20);
                    border-radius: 10px;
                    background-color: rgba(11, 15, 25, 0.8);
                }
            """)
            self.radio_dot.setStyleSheet("background: transparent; border-radius: 4px;")

    def enterEvent(self, event):
        if not self.is_selected:
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(15, 23, 42, 0.85);
                    border: 1px solid rgba(56, 189, 248, 0.45);
                    border-radius: 10px;
                }
            """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.set_selected(self.is_selected)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
            return
        super().keyPressEvent(event)


class StartupPerformanceDialog(QDialog):
    """
    Workstation Performance & Live Telemetry Dialog.
    Allows viewing current real-time hardware usage (CPU, RAM, GPU, Storage)
    and selecting the CPU allocation preset.
    """
    profile_selected = pyqtSignal(str, bool)  # (profile_key, remember_choice)

    def __init__(self, current_profile: str = "medium", remember_default: bool = False, auto_countdown_sec: int = 6, is_startup: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CCTVPanelView - Hardware Telemetry & CPU Profiles")
        self.setFixedSize(760, 680)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)

        self.rm = get_resource_manager()
        self.total_cores = self.rm.get_system_core_count()

        valid_profiles = [p.value for p in PerformanceProfile]
        if current_profile in valid_profiles:
            self.selected_profile = current_profile
        else:
            self.selected_profile = PerformanceProfile.GAMER.value if self.rm.is_ryzen_dual_ccd else PerformanceProfile.MEDIUM.value

        # Auto-detect if app is already running (parent is visible)
        if parent is not None and getattr(parent, "isVisible", lambda: False)():
            self.is_startup = False
        else:
            self.is_startup = is_startup

        self.countdown_remaining = auto_countdown_sec if self.is_startup else 0
        self.user_interacted = not self.is_startup

        self._setup_ui(remember_default)
        self._update_telemetry()

        # Telemetry refresh timer (updates every 1000ms)
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self._update_telemetry)
        self.telemetry_timer.start(1000)

        if self.is_startup and self.countdown_remaining > 0:
            self._start_countdown()

    def _setup_ui(self, remember_default: bool):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(0)

        # Container
        self.container = QFrame(self)
        self.container.setObjectName("perf_container")
        self.container.setStyleSheet("""
            QFrame#perf_container {
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
        c_layout.setContentsMargins(22, 16, 22, 18)
        c_layout.setSpacing(14)

        # --- 1. Top Header Bar (Brand Capsule + Integrated Frameless Controls) ---
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
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "app_icon.png")

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
        lbl_sub_header = QLabel("HARDWARE TELEMETRY & CPU PROFILES", self.container)
        lbl_sub_header.setStyleSheet("color: #64748b; font-size: 10.5px; font-weight: 700; letter-spacing: 1px;")
        hdr_layout.addWidget(lbl_sub_header)

        hdr_layout.addStretch()

        # Frameless window control close button
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
        btn_close.setToolTip("Close dialog (ESC)")
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

        # Divider
        sep1 = QFrame(self.container)
        sep1.setFixedHeight(1)
        sep1.setStyleSheet("background-color: rgba(255, 255, 255, 0.07); border: none;")
        c_layout.addWidget(sep1)

        # --- 2. Live Hardware Telemetry Grid (Data with how much is using right now) ---
        telemetry_grid = QGridLayout()
        telemetry_grid.setContentsMargins(0, 0, 0, 0)
        telemetry_grid.setSpacing(10)

        self.card_cpu = TelemetryCard("cpu", "CPU Utilization", self.container)
        telemetry_grid.addWidget(self.card_cpu, 0, 0)

        self.card_ram = TelemetryCard("ram", "Memory (RAM)", self.container)
        telemetry_grid.addWidget(self.card_ram, 0, 1)

        self.card_gpu = TelemetryCard("gpu", "GPU & VRAM", self.container)
        telemetry_grid.addWidget(self.card_gpu, 1, 0)

        self.card_storage = TelemetryCard("storage", "Recordings Storage", self.container)
        telemetry_grid.addWidget(self.card_storage, 1, 1)

        c_layout.addLayout(telemetry_grid)

        # --- 3. Performance Presets Section ---
        c_layout.addSpacing(2)
        presets_header = QHBoxLayout()
        presets_header.setContentsMargins(0, 0, 0, 0)
        lbl_presets_title = QLabel("CPU ALLOCATION & PERFORMANCE PRESETS", self.container)
        lbl_presets_title.setStyleSheet("color: #f1f5f9; font-size: 12.5px; font-weight: 700; letter-spacing: 0.5px;")
        presets_header.addWidget(lbl_presets_title)
        presets_header.addStretch()
        c_layout.addLayout(presets_header)

        # Presets cards
        self.profile_cards = {}
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(8)

        if self.rm.is_ryzen_dual_ccd:
            profiles_data = [
                (
                    PerformanceProfile.GAMER.value,
                    "Gamer Mode (Chiplet 2 / CCD1 Only)",
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
                    f"All {self.total_cores} Cores (Full Power)",
                    "Unrestricted native 2K feeds on all tiles, full 25-30 FPS across both Chiplets, continuous AI detection."
                )
            ]
        else:
            profiles_data = [
                (
                    PerformanceProfile.LOW.value,
                    "Low Usage (Eco Mode)",
                    "2 Cores (Max 8% CPU)",
                    "Locks CCTVPanelView to 2 CPU cores, runs 10 FPS grid with lightweight sub-streams, and gates AI inference only when motion occurs."
                ),
                (
                    PerformanceProfile.MEDIUM.value,
                    "Medium Usage (Balanced)",
                    "4 Cores (15-25% CPU)",
                    "Smooth 15 FPS monitoring with Mid-HD feeds, responsive AI alarms, and balanced 4-core multi-threading."
                ),
                (
                    PerformanceProfile.HIGH.value,
                    "High Usage (Max Performance)",
                    f"All {self.total_cores} Cores (Full Power)",
                    "Unrestricted native 2K feeds on all tiles, full 25-30 FPS, continuous AI detection and zero downscaling."
                )
            ]

        for p_key, title, tag, desc in profiles_data:
            card = ProfileOptionCard(p_key, title, tag, desc, parent=self.container)
            card.clicked.connect(lambda k=p_key: self._on_card_selected(k))
            self.profile_cards[p_key] = card
            cards_layout.addWidget(card)

        c_layout.addLayout(cards_layout)
        self._highlight_active_card()

        # --- 4. Footer & Actions ---
        c_layout.addSpacing(2)
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(2, 0, 2, 0)

        self.chk_remember = QCheckBox("Remember preference as default profile", self.container)
        self.chk_remember.setChecked(remember_default)
        self.chk_remember.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_remember.setStyleSheet("""
            QCheckBox {
                color: #cbd5e1;
                font-size: 11.5px;
                font-weight: 600;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid rgba(56, 189, 248, 0.45);
                border-radius: 4px;
                background-color: #0b0f19;
            }
            QCheckBox::indicator:hover {
                border-color: #38bdf8;
                background-color: rgba(56, 189, 248, 0.12);
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border-color: #38bdf8;
                image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='white'><path d='M13.485 3.515a1 1 0 0 1 0 1.414l-7 7a1 1 0 0 1-1.414 0l-3.5-3.5a1 1 0 0 1 1.414-1.414L6.07 10.1l6.001-6.001a1 1 0 0 1 1.414 0z'/></svg>");
            }
        """)
        footer_layout.addWidget(self.chk_remember)

        self.lbl_countdown = QLabel("", self.container)
        self.lbl_countdown.setStyleSheet("color: #38bdf8; font-size: 11.5px; font-weight: 600;")
        footer_layout.addWidget(self.lbl_countdown)

        footer_layout.addStretch()

        btn_cancel = QPushButton("Close", self.container)
        btn_cancel.setFixedSize(86, 32)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
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
                border-color: rgba(255, 255, 255, 0.22);
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(btn_cancel)

        btn_text = "Start CCTVPanelView" if self.is_startup else "Apply Preset"
        self.btn_apply = QPushButton(btn_text, self.container)
        self.btn_apply.setFixedSize(140 if self.is_startup else 110, 32)
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.setStyleSheet("""
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
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        footer_layout.addWidget(self.btn_apply)

        c_layout.addLayout(footer_layout)
        root.addWidget(self.container)

    def _on_card_selected(self, key: str):
        self._on_user_interaction()
        self.selected_profile = key
        self._highlight_active_card()

    def _highlight_active_card(self):
        for k, card in self.profile_cards.items():
            card.set_selected(k == self.selected_profile)

    def _update_telemetry(self):
        snap = self.rm.get_hardware_telemetry_snapshot()
        c = snap["cpu"]
        r = snap["ram"]
        g = snap["gpu"]
        s = snap["storage"]

        # CPU Card
        self.card_cpu.lbl_value.setText(f"{c['sys_pct']:.0f}% Total  |  {c['app_pct']:.1f}% App")
        self.card_cpu.progress.setValue(min(100, int(c['sys_pct'])))
        self.card_cpu.lbl_detail.setText(f"{c['model']}  •  Affinity: {c['affinity_label']}")

        # RAM Card
        self.card_ram.lbl_value.setText(f"{r['sys_used_gb']:.1f} / {r['sys_total_gb']:.1f} GB ({r['sys_pct']:.0f}%)")
        self.card_ram.progress.setValue(min(100, int(r['sys_pct'])))
        self.card_ram.lbl_detail.setText(f"App Footprint: {r['app_mb']:.0f} MB ({r['app_sys_pct']:.1f}% of System)")

        # GPU Card
        if g.get("available", False):
            self.card_gpu.lbl_value.setText(f"{g['util_pct']:.0f}% Load  |  {g['vram_used_mb']/1024:.1f} / {g['vram_total_mb']/1024:.1f} GB")
            self.card_gpu.progress.setValue(min(100, int(g['vram_pct'])))
            self.card_gpu.lbl_detail.setText(f"{g['name']} (Dedicated VRAM: {g['vram_pct']:.0f}%)")
        else:
            self.card_gpu.lbl_value.setText("Integrated / Standard GPU")
            self.card_gpu.progress.setValue(0)
            self.card_gpu.lbl_detail.setText("Hardware Direct 3D engine")

        # Storage Card
        free_pct = (s['free_gb'] / s['total_gb'] * 100.0) if s.get('total_gb', 0) > 0 else 0
        self.card_storage.lbl_value.setText(f"{s['free_gb']:.0f} GB Free ({free_pct:.0f}% Available)")
        self.card_storage.progress.setValue(min(100, int(s.get('used_pct', 0))))
        self.card_storage.lbl_detail.setText(f"Recordings Drive {s['drive']} ({s['total_gb']:.0f} GB Total Capacity)")

    def _start_countdown(self):
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._on_timer_tick)
        self._update_countdown_label()
        self.countdown_timer.start(1000)

    def _on_timer_tick(self):
        if self.user_interacted:
            if hasattr(self, "countdown_timer") and self.countdown_timer.isActive():
                self.countdown_timer.stop()
            self.lbl_countdown.setText("")
            return

        self.countdown_remaining -= 1
        self._update_countdown_label()

        if self.countdown_remaining <= 0:
            if hasattr(self, "countdown_timer") and self.countdown_timer.isActive():
                self.countdown_timer.stop()
            self._on_apply_clicked()

    def _update_countdown_label(self):
        if not self.user_interacted and self.countdown_remaining > 0:
            self.lbl_countdown.setText(f"Auto-launching in {self.countdown_remaining}s...")
        else:
            self.lbl_countdown.setText("")

    def _on_user_interaction(self):
        if not self.user_interacted:
            self.user_interacted = True
            if hasattr(self, "countdown_timer") and self.countdown_timer.isActive():
                self.countdown_timer.stop()
            self.lbl_countdown.setText("")

    def _on_apply_clicked(self):
        if hasattr(self, "countdown_timer") and self.countdown_timer.isActive():
            self.countdown_timer.stop()
        if hasattr(self, "telemetry_timer") and self.telemetry_timer.isActive():
            self.telemetry_timer.stop()
        remember = self.chk_remember.isChecked()
        self.profile_selected.emit(self.selected_profile, remember)
        self.accept()

    def reject(self):
        if hasattr(self, "countdown_timer") and self.countdown_timer.isActive():
            self.countdown_timer.stop()
        if hasattr(self, "telemetry_timer") and self.telemetry_timer.isActive():
            self.telemetry_timer.stop()
        super().reject()
