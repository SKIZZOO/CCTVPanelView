import os
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap


def create_vector_icon(icon_type: str, color: str = "#38bdf8", size: int = 24) -> QPixmap:
    """Renders crisp vector iconography matching CCTVPanelView top-bar design language."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color), 1.9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    if icon_type == "tray":
        # System Tray: High-tech workstation tray bracket with arrow pointing down
        p.drawLine(int(size * 0.18), int(size * 0.52), int(size * 0.18), int(size * 0.78))
        p.drawLine(int(size * 0.18), int(size * 0.78), int(size * 0.82), int(size * 0.78))
        p.drawLine(int(size * 0.82), int(size * 0.78), int(size * 0.82), int(size * 0.52))
        # Arrow pointing down into tray
        p.drawLine(int(size * 0.50), int(size * 0.16), int(size * 0.50), int(size * 0.54))
        p.drawLine(int(size * 0.33), int(size * 0.38), int(size * 0.50), int(size * 0.54))
        p.drawLine(int(size * 0.67), int(size * 0.38), int(size * 0.50), int(size * 0.54))
    elif icon_type == "power":
        # Power / Shutdown symbol (IEC 5009 standard, gap centered at 12 o'clock)
        rect = QRectF(size * 0.18, size * 0.18, size * 0.64, size * 0.64)
        p.drawArc(rect, int(125 * 16), int(290 * 16))
        p.drawLine(int(size * 0.50), int(size * 0.10), int(size * 0.50), int(size * 0.48))
    elif icon_type == "chevron":
        # Crisp right chevron
        p.drawLine(int(size * 0.38), int(size * 0.26), int(size * 0.64), int(size * 0.50))
        p.drawLine(int(size * 0.64), int(size * 0.50), int(size * 0.38), int(size * 0.74))
    elif icon_type == "close":
        # Window close cross
        p.drawLine(int(size * 0.28), int(size * 0.28), int(size * 0.72), int(size * 0.72))
        p.drawLine(int(size * 0.72), int(size * 0.28), int(size * 0.28), int(size * 0.72))

    p.end()
    return pix


class ExitOptionCard(QFrame):
    """
    Clean, elegant workstation option card without clashing colors or pill shapes.
    Uses the unified Sky Blue & Slate design theme with crisp 8px-10px radii.
    """
    clicked = pyqtSignal()

    def __init__(self, mode: str, title: str, description: str, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName(f"exit_card_{mode}")
        self.setMinimumHeight(86)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._update_style(hover=False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 18, 14)
        layout.setSpacing(16)

        # 1. Left Icon Container (Unified Sky Blue theme, NO clashing colors)
        self.icon_badge = QFrame(self)
        self.icon_badge.setFixedSize(46, 46)
        self.icon_badge.setStyleSheet("""
            QFrame {
                background-color: rgba(56, 189, 248, 0.10);
                border: 1px solid rgba(56, 189, 248, 0.30);
                border-radius: 10px;
            }
        """)
        badge_layout = QVBoxLayout(self.icon_badge)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon = QLabel(self.icon_badge)
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        ic_type = "tray" if mode == "tray" else "power"
        self.lbl_icon.setPixmap(create_vector_icon(ic_type, color="#38bdf8", size=24))
        badge_layout.addWidget(self.lbl_icon)
        layout.addWidget(self.icon_badge)

        # 2. Middle Content (Title + Description, NO pill badges)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        lbl_title = QLabel(title, self)
        lbl_title.setStyleSheet("color: #f8fafc; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        text_layout.addWidget(lbl_title)

        lbl_desc = QLabel(description, self)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 11.5px; background: transparent; border: none; line-height: 1.4;")
        text_layout.addWidget(lbl_desc)

        layout.addLayout(text_layout, stretch=1)

        # 3. Right Chevron Indicator (clean and minimalist)
        self.lbl_chev = QLabel(self)
        self.lbl_chev.setStyleSheet("background: transparent; border: none;")
        self.lbl_chev.setPixmap(create_vector_icon("chevron", color="#64748b", size=18))
        layout.addWidget(self.lbl_chev)

    def _update_style(self, hover: bool):
        if hover:
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(15, 23, 42, 0.95);
                    border: 1px solid #38bdf8;
                    border-radius: 10px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(15, 23, 42, 0.70);
                    border: 1px solid rgba(255, 255, 255, 0.09);
                    border-radius: 10px;
                }
            """)

    def enterEvent(self, event):
        self._update_style(hover=True)
        self.lbl_chev.setPixmap(create_vector_icon("chevron", color="#38bdf8", size=18))
        self.icon_badge.setStyleSheet("""
            QFrame {
                background-color: rgba(56, 189, 248, 0.18);
                border: 1px solid #38bdf8;
                border-radius: 10px;
            }
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_style(hover=False)
        self.lbl_chev.setPixmap(create_vector_icon("chevron", color="#64748b", size=18))
        self.icon_badge.setStyleSheet("""
            QFrame {
                background-color: rgba(56, 189, 248, 0.10);
                border: 1px solid rgba(56, 189, 248, 0.30);
                border-radius: 10px;
            }
        """)
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


class CloseConfirmDialog(QDialog):
    """
    Sleek workstation modal dialog prompting user upon closing the window:
    - Minimize to system tray (maintain 24/7 background recording, AI detection & quick restore)
    - Full application shutdown (disconnect streams and stop surveillance)
    - 'Remember my choice' checkbox to persist preference cleanly in app configuration
    - Uses unified Sky Blue theme with zero contrasting colored pills.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exit CCTVPanelView")
        self.setFixedSize(560, 430)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)

        self._action = "cancel"
        self._remember = False

        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(0)

        # Outer obsidian glass container
        self.container = QFrame(self)
        self.container.setObjectName("dialog_container")
        self.container.setStyleSheet("""
            QFrame#dialog_container {
                background-color: #080c16;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 14px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 245))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(self.container)
        c_layout.setContentsMargins(24, 18, 24, 20)
        c_layout.setSpacing(14)

        # --- 1. Top Header Bar (Clean brand capsule, NO colored pill badges!) ---
        hdr_layout = QHBoxLayout()
        hdr_layout.setContentsMargins(0, 0, 0, 0)
        hdr_layout.setSpacing(8)

        # Brand capsule frame matching topbar
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

        # Clean circular aperture logo with zero background box or border
        lbl_logo = QLabel(capsule_brand)
        lbl_logo.setObjectName("lbl_brand_logo")
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
        btn_close.setToolTip("Cancel (ESC)")
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

        # Subtle divider
        sep = QFrame(self.container)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.07); border: none;")
        c_layout.addWidget(sep)

        # Prompt & Context Description
        prompt_box = QVBoxLayout()
        prompt_box.setContentsMargins(0, 2, 0, 0)
        prompt_box.setSpacing(3)

        lbl_prompt_title = QLabel("Surveillance Workstation is Active", self.container)
        lbl_prompt_title.setStyleSheet("color: #f1f5f9; font-size: 15px; font-weight: 700; letter-spacing: 0.2px;")
        lbl_prompt_sub = QLabel("Camera feeds, motion alerts, and background recording are operating. Choose an action:", self.container)
        lbl_prompt_sub.setStyleSheet("color: #94a3b8; font-size: 11.5px;")
        prompt_box.addWidget(lbl_prompt_title)
        prompt_box.addWidget(lbl_prompt_sub)
        c_layout.addLayout(prompt_box)

        # --- 2. Action Option Cards (Unified Theme, NO pill shapes or clashing colors) ---
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(10)

        # Card A: System Tray
        self.card_tray = ExitOptionCard(
            mode="tray",
            title="Minimize to System Tray",
            description="Keeps 24/7 background recording, AI motion detection, and alerts active in the taskbar. Double-click icon to restore.",
            parent=self.container
        )
        self.card_tray.clicked.connect(self._on_tray_clicked)
        self.btn_opt_tray = self.card_tray
        cards_layout.addWidget(self.card_tray)

        # Card B: Full Application Shutdown
        self.card_quit = ExitOptionCard(
            mode="quit",
            title="Shut Down Application",
            description="Disconnects all camera streams, finalizes active MP4 recordings safely, and terminates surveillance processes.",
            parent=self.container
        )
        self.card_quit.clicked.connect(self._on_quit_clicked)
        self.btn_opt_quit = self.card_quit
        cards_layout.addWidget(self.card_quit)

        c_layout.addLayout(cards_layout)

        # --- 3. Remember Preference Checkbox ---
        chk_container = QVBoxLayout()
        chk_container.setContentsMargins(2, 2, 2, 0)
        chk_container.setSpacing(3)

        self.chk_remember = QCheckBox("Remember my choice and do not ask again", self.container)
        self.chk_remember.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_remember.setStyleSheet("""
            QCheckBox {
                color: #cbd5e1;
                font-size: 12px;
                font-weight: 600;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
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
        chk_container.addWidget(self.chk_remember)

        lbl_hint = QLabel("Preference can be changed or reset anytime in Settings > Visual Theme & Layout.", self.container)
        lbl_hint.setStyleSheet("color: #64748b; font-size: 10.5px; padding-left: 26px;")
        chk_container.addWidget(lbl_hint)
        c_layout.addLayout(chk_container)

        # --- 4. Footer ---
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 4, 0, 0)

        lbl_esc = QLabel("Press ESC to dismiss", self.container)
        lbl_esc.setStyleSheet("color: #475569; font-size: 11px; font-weight: 500;")
        footer_layout.addWidget(lbl_esc)

        footer_layout.addStretch()

        btn_cancel = QPushButton("Cancel", self.container)
        btn_cancel.setFixedSize(96, 32)
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
        c_layout.addLayout(footer_layout)

        root.addWidget(self.container)

    def _on_tray_clicked(self):
        self._action = "tray"
        self._remember = self.chk_remember.isChecked()
        self.accept()

    def _on_quit_clicked(self):
        self._action = "quit"
        self._remember = self.chk_remember.isChecked()
        self.accept()

    def exec_dialog(self) -> tuple[str, bool]:
        """
        Shows modal dialog and returns (action, remember_choice):
        - action: 'tray', 'quit', or 'cancel'
        - remember_choice: True if user checked 'Remember my choice', else False
        """
        res = self.exec()
        if res == QDialog.DialogCode.Accepted:
            return (self._action, self._remember)
        return ("cancel", False)
