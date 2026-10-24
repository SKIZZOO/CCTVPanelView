import os
import socket
import uuid
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit,
    QSpinBox, QCheckBox, QPushButton, QComboBox, QLabel, QMessageBox,
    QFrame, QWidget, QScrollArea, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap, QPainterPath

from core.device_manager import DeviceManager


def create_dialog_icon(icon_type: str, color: str = "#38bdf8", size: int = 20) -> QPixmap:
    """Renders crisp vector iconography for the Obsidian Glass dialog."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    if icon_type == "camera":
        p.drawRoundedRect(int(size * 0.14), int(size * 0.28), int(size * 0.72), int(size * 0.54), 2.5, 2.5)
        p.drawEllipse(int(size * 0.36), int(size * 0.42), int(size * 0.28), int(size * 0.28))
        p.drawRoundedRect(int(size * 0.30), int(size * 0.16), int(size * 0.40), int(size * 0.12), 1.5, 1.5)
    elif icon_type == "close":
        p.drawLine(int(size * 0.30), int(size * 0.30), int(size * 0.70), int(size * 0.70))
        p.drawLine(int(size * 0.70), int(size * 0.30), int(size * 0.30), int(size * 0.70))
    elif icon_type == "eye":
        path = QPainterPath()
        path.moveTo(size * 0.15, size * 0.50)
        path.quadTo(size * 0.50, size * 0.18, size * 0.85, size * 0.50)
        path.quadTo(size * 0.50, size * 0.82, size * 0.15, size * 0.50)
        p.drawPath(path)
        p.drawEllipse(int(size * 0.40), int(size * 0.40), int(size * 0.20), int(size * 0.20))
    elif icon_type == "eye_slash":
        path = QPainterPath()
        path.moveTo(size * 0.15, size * 0.50)
        path.quadTo(size * 0.50, size * 0.18, size * 0.85, size * 0.50)
        path.quadTo(size * 0.50, size * 0.82, size * 0.15, size * 0.50)
        p.drawPath(path)
        p.drawLine(int(size * 0.20), int(size * 0.80), int(size * 0.80), int(size * 0.20))
    elif icon_type == "network":
        p.drawEllipse(int(size * 0.38), int(size * 0.16), int(size * 0.24), int(size * 0.24))
        p.drawEllipse(int(size * 0.16), int(size * 0.60), int(size * 0.24), int(size * 0.24))
        p.drawEllipse(int(size * 0.60), int(size * 0.60), int(size * 0.24), int(size * 0.24))
        p.drawLine(int(size * 0.50), int(size * 0.40), int(size * 0.28), int(size * 0.60))
        p.drawLine(int(size * 0.50), int(size * 0.40), int(size * 0.72), int(size * 0.60))

    p.end()
    return pix


class AsyncConnectionTester(QThread):
    """Background worker for testing RTSP and network connectivity without locking UI."""
    test_finished = pyqtSignal(bool, str)

    def __init__(self, url: str, ip: str, port: int):
        super().__init__()
        self.url = url
        self.ip = ip
        self.port = port

    def run(self):
        # 1. Quick TCP socket probe
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.5)
            err = s.connect_ex((self.ip, self.port))
            s.close()
            if err != 0:
                self.test_finished.emit(False, f"Cannot reach {self.ip}:{self.port} (Port closed or device offline)")
                return
        except Exception as e:
            self.test_finished.emit(False, f"Network error: {str(e)}")
            return

        # 2. RTSP handshake test via DeviceManager
        try:
            res = DeviceManager.test_connection(self.url)
            if res.get("success"):
                self.test_finished.emit(True, res.get("message", "Stream active and verified"))
            else:
                self.test_finished.emit(False, res.get("error", "RTSP stream handshake failed"))
        except Exception as e:
            self.test_finished.emit(False, str(e))


class DeviceDialog(QDialog):
    """
    Next-Gen Obsidian Glass Camera Configuration Dialog.
    Fully in theme with CCTVPanelView workstation design:
    - Sleek frameless geometry with subtle cyan glow border
    - Draggable obsidian title bar with integrated close control
    - Guided input fields for Camera Name, Presets, IP, Port, Username, and Password
    - Interactive password show/hide toggle
    - Dual-Lens multi-feed management with auto-generated RTSP URLs
    - Non-blocking asynchronous connection tester with live status pill
    """

    def __init__(self, camera_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.camera_data = camera_data or {}
        self.is_edit_mode = bool(camera_data and camera_data.get("id"))
        self.result_data = {}
        self.drag_position = QPoint()
        self.test_worker: Optional[AsyncConnectionTester] = None

        self.setWindowTitle("Edit Camera Details" if self.is_edit_mode else "Configure Camera / Dual-Lens Feeds")
        self.setFixedSize(610, 750)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)

        self._setup_ui()
        self._populate_initial_data()

    def _create_masked_field(self, placeholder: str = "", text: str = "", on_text_changed=None, fixed_width: Optional[int] = None):
        """Creates a masked credential/stream input field with an interactive reveal eye button."""
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        txt = QLineEdit(container)
        txt.setEchoMode(QLineEdit.EchoMode.Password)
        txt.setPlaceholderText(placeholder)
        if text:
            txt.setText(text)
        if fixed_width:
            txt.setFixedWidth(fixed_width)
        if on_text_changed:
            txt.textChanged.connect(on_text_changed)

        btn_eye = QPushButton(container)
        btn_eye.setFixedSize(28, 28)
        btn_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye.setToolTip("Show / Hide sensitive content")
        btn_eye.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 41, 59, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #38bdf8;
            }
        """)
        t_box = QVBoxLayout(btn_eye)
        t_box.setContentsMargins(0, 0, 0, 0)
        t_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_eye = QLabel(btn_eye)
        lbl_eye.setPixmap(create_dialog_icon("eye", color="#94a3b8", size=14))
        lbl_eye.setStyleSheet("background: transparent; border: none;")
        t_box.addWidget(lbl_eye)

        def _toggle():
            if txt.echoMode() == QLineEdit.EchoMode.Password:
                txt.setEchoMode(QLineEdit.EchoMode.Normal)
                lbl_eye.setPixmap(create_dialog_icon("eye_slash", color="#38bdf8", size=14))
                btn_eye.setToolTip("Hide sensitive content")
            else:
                txt.setEchoMode(QLineEdit.EchoMode.Password)
                lbl_eye.setPixmap(create_dialog_icon("eye", color="#94a3b8", size=14))
                btn_eye.setToolTip("Show sensitive content")

        btn_eye.clicked.connect(_toggle)
        lay.addWidget(txt, stretch=1)
        lay.addWidget(btn_eye)
        return container, txt

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(0)

        # Outer Master Obsidian Frame
        self.container = QFrame(self)
        self.container.setObjectName("dialog_container")
        self.container.setStyleSheet("""
            QFrame#dialog_container {
                background-color: #080c16;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 14px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
            QLineEdit {
                background-color: rgba(11, 15, 25, 0.90);
                color: #f8fafc;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 7px;
                padding: 6px 10px;
                font-size: 11.5px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
                background-color: rgba(15, 23, 42, 0.98);
            }
            QComboBox {
                background-color: rgba(11, 15, 25, 0.90);
                color: #f8fafc;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 7px;
                padding: 6px 10px;
                font-size: 11.5px;
            }
            QComboBox:focus {
                border: 1px solid #38bdf8;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border-left: 1px solid rgba(255, 255, 255, 0.10);
            }
            QComboBox QAbstractItemView {
                background-color: #0b1120;
                color: #f8fafc;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }
            QSpinBox {
                background-color: rgba(11, 15, 25, 0.90);
                color: #f8fafc;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 7px;
                padding: 6px 10px;
                font-size: 11.5px;
            }
            QSpinBox:focus {
                border: 1px solid #38bdf8;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
                background: rgba(30, 41, 59, 0.6);
                border: none;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #0284c7;
            }
            QCheckBox {
                color: #e2e8f0;
                font-size: 11.5px;
                font-weight: 600;
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.20);
                background-color: rgba(15, 23, 42, 0.85);
            }
            QCheckBox::indicator:hover {
                border-color: #38bdf8;
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border-color: #38bdf8;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(15, 23, 42, 0.4);
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

        shadow = QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(0, 0, 0, 240))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(self.container)
        c_layout.setContentsMargins(20, 16, 20, 18)
        c_layout.setSpacing(12)

        # -------------------------------------------------------------
        # Header Bar: Brand + Title + Sleek Close Button
        # -------------------------------------------------------------
        hdr_bar = QHBoxLayout()
        hdr_bar.setContentsMargins(0, 0, 0, 0)
        hdr_bar.setSpacing(10)

        lbl_icon = QLabel(self.container)
        lbl_icon.setPixmap(create_dialog_icon("camera", color="#38bdf8", size=24))
        lbl_icon.setFixedSize(24, 24)
        hdr_bar.addWidget(lbl_icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("Edit Camera Details" if self.is_edit_mode else "Configure Camera / Dual-Lens Feeds", self.container)
        lbl_title.setStyleSheet("color: #f8fafc; font-size: 14.5px; font-weight: 750; letter-spacing: 0.3px;")
        lbl_subtitle = QLabel("Set camera identity, network credentials, and streaming feeds", self.container)
        lbl_subtitle.setStyleSheet("color: #94a3b8; font-size: 11px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_subtitle)
        hdr_bar.addLayout(title_box, stretch=1)

        btn_close = QPushButton(self.container)
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setToolTip("Close (ESC)")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 41, 59, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.25);
                border-color: #ef4444;
            }
        """)
        b_box = QVBoxLayout(btn_close)
        b_box.setContentsMargins(0, 0, 0, 0)
        b_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_x = QLabel(btn_close)
        lbl_x.setPixmap(create_dialog_icon("close", color="#94a3b8", size=14))
        lbl_x.setStyleSheet("background: transparent; border: none;")
        b_box.addWidget(lbl_x)
        btn_close.clicked.connect(self.reject)
        hdr_bar.addWidget(btn_close)

        c_layout.addLayout(hdr_bar)

        # Subtle Horizontal Separator
        sep1 = QFrame(self.container)
        sep1.setFixedHeight(1)
        sep1.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); border: none;")
        c_layout.addWidget(sep1)

        # -------------------------------------------------------------
        # Scrollable Content Body
        # -------------------------------------------------------------
        scroll = QScrollArea(self.container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(2, 4, 2, 4)
        body_layout.setSpacing(12)

        # Card 1: Identity & Preset
        card_id = self._create_card(body)
        layout_id = QVBoxLayout(card_id)
        layout_id.setContentsMargins(14, 12, 14, 12)
        layout_id.setSpacing(8)

        lbl_sec1 = QLabel("CAMERA IDENTITY & PRESET", card_id)
        lbl_sec1.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 750; letter-spacing: 0.8px;")
        layout_id.addWidget(lbl_sec1)

        row_name = QHBoxLayout()
        row_name.setSpacing(10)
        lbl_n = QLabel("Camera Name:", card_id)
        lbl_n.setStyleSheet("color: #cbd5e1; font-size: 11.5px; font-weight: 600; min-width: 95px;")
        self.txt_name = QLineEdit(card_id)
        self.txt_name.setPlaceholderText("e.g. Front Door, Driveway, Backyard PTZ")
        row_name.addWidget(lbl_n)
        row_name.addWidget(self.txt_name, stretch=1)
        layout_id.addLayout(row_name)

        row_preset = QHBoxLayout()
        row_preset.setSpacing(10)
        lbl_p = QLabel("Model Preset:", card_id)
        lbl_p.setStyleSheet("color: #cbd5e1; font-size: 11.5px; font-weight: 600; min-width: 95px;")
        self.cmb_preset = QComboBox(card_id)
        self.cmb_preset.addItems([
            "CAM720 / Jooan Single Lens (2K HD)",
            "CAM720 / Jooan Dual-Lens (Fixed + PTZ Feeds)",
            "Generic RTSP / ONVIF Profile S",
            "Xiongmai / XMTech ONVIF Profile S",
            "Dahua / Amcrest Dual-Feed RTSP",
            "Hikvision / Annke RTSP Stream",
            "Custom RTSP URL"
        ])
        self.cmb_preset.currentIndexChanged.connect(self._on_preset_changed)
        row_preset.addWidget(lbl_p)
        row_preset.addWidget(self.cmb_preset, stretch=1)
        layout_id.addLayout(row_preset)

        body_layout.addWidget(card_id)

        # Card 2: Network & Credentials
        card_net = self._create_card(body)
        layout_net = QVBoxLayout(card_net)
        layout_net.setContentsMargins(14, 12, 14, 12)
        layout_net.setSpacing(8)

        lbl_sec2 = QLabel("NETWORK & ACCESS CREDENTIALS", card_net)
        lbl_sec2.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 750; letter-spacing: 0.8px;")
        layout_net.addWidget(lbl_sec2)

        # IP Address & RTSP Port row
        grid_net = QGridLayout()
        grid_net.setContentsMargins(0, 0, 0, 0)
        grid_net.setHorizontalSpacing(10)
        grid_net.setVerticalSpacing(8)

        lbl_ip = QLabel("IP Address:", card_net)
        lbl_ip.setStyleSheet("color: #cbd5e1; font-size: 11.5px; font-weight: 600; min-width: 95px;")
        box_ip, self.txt_ip = self._create_masked_field(placeholder="192.168.1.100", on_text_changed=self._auto_update_urls)
        grid_net.addWidget(lbl_ip, 0, 0)
        grid_net.addWidget(box_ip, 0, 1)

        lbl_port = QLabel("RTSP Port:", card_net)
        lbl_port.setStyleSheet("color: #cbd5e1; font-size: 11.5px; font-weight: 600; min-width: 65px;")
        self.spin_port = QSpinBox(card_net)
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(554)
        self.spin_port.valueChanged.connect(self._auto_update_urls)
        grid_net.addWidget(lbl_port, 0, 2)
        grid_net.addWidget(self.spin_port, 0, 3)

        # Username & Password row
        lbl_user = QLabel("Username:", card_net)
        lbl_user.setStyleSheet("color: #cbd5e1; font-size: 11.5px; font-weight: 600; min-width: 95px;")
        box_user, self.txt_user = self._create_masked_field(placeholder="admin", text="admin", on_text_changed=self._auto_update_urls)
        grid_net.addWidget(lbl_user, 1, 0)
        grid_net.addWidget(box_user, 1, 1)

        lbl_pass = QLabel("Password:", card_net)
        lbl_pass.setStyleSheet("color: #cbd5e1; font-size: 11.5px; font-weight: 600; min-width: 65px;")
        box_pass, self.txt_pass = self._create_masked_field(placeholder="Leave blank if none", on_text_changed=self._auto_update_urls)
        self.txt_pass.returnPressed.connect(lambda: self._test_connection())
        grid_net.addWidget(lbl_pass, 1, 2)
        grid_net.addWidget(box_pass, 1, 3)

        layout_net.addLayout(grid_net)

        lbl_cred_hint = QLabel("Note: Enter the password set in your mobile app (CAM720 / iCSee / V380).", card_net)
        lbl_cred_hint.setStyleSheet("color: #64748b; font-size: 10.5px; font-style: italic;")
        layout_net.addWidget(lbl_cred_hint)

        # Dual Lens Toggle
        self.chk_dual = QCheckBox("Dual-Lens Hardware (2 simultaneous feeds: PTZ Zoom + Panoramic Fixed)", card_net)
        self.chk_dual.setChecked(False)
        self.chk_dual.stateChanged.connect(self._on_dual_toggled)
        layout_net.addWidget(self.chk_dual)

        body_layout.addWidget(card_net)

        # Card 3: Stream URLs & Lens Configuration
        card_streams = self._create_card(body)
        self.layout_streams = QVBoxLayout(card_streams)
        self.layout_streams.setContentsMargins(14, 12, 14, 12)
        self.layout_streams.setSpacing(10)

        lbl_sec3 = QLabel("RTSP VIDEO STREAMS", card_streams)
        lbl_sec3.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 750; letter-spacing: 0.8px;")
        self.layout_streams.addWidget(lbl_sec3)

        # Lens 1
        l1_box = QVBoxLayout()
        l1_box.setSpacing(4)
        lbl_l1_title = QLabel("Lens 1 / Primary Stream (PTZ)", card_streams)
        lbl_l1_title.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: 700;")
        l1_box.addWidget(lbl_l1_title)

        r1 = QHBoxLayout()
        r1.setSpacing(6)
        self.txt_stream1_name = QLineEdit("Lens 1 (PTZ Zoom)", card_streams)
        self.txt_stream1_name.setFixedWidth(130)
        box_url1, self.txt_stream1_url = self._create_masked_field(placeholder="rtsp://admin:pass@192.168.1.100:554/live/ch00_0")
        r1.addWidget(self.txt_stream1_name)
        r1.addWidget(box_url1, stretch=1)
        l1_box.addLayout(r1)
        self.layout_streams.addLayout(l1_box)

        # Lens 2 Container
        self.widget_lens2 = QWidget(card_streams)
        l2_box = QVBoxLayout(self.widget_lens2)
        l2_box.setContentsMargins(0, 4, 0, 0)
        l2_box.setSpacing(4)
        lbl_l2_title = QLabel("Lens 2 / Secondary Stream (Fixed Wide)", self.widget_lens2)
        lbl_l2_title.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: 700;")
        l2_box.addWidget(lbl_l2_title)

        r2 = QHBoxLayout()
        r2.setSpacing(6)
        self.txt_stream2_name = QLineEdit("Lens 2 (Fixed Wide)", self.widget_lens2)
        self.txt_stream2_name.setFixedWidth(130)
        box_url2, self.txt_stream2_url = self._create_masked_field(placeholder="rtsp://admin:pass@192.168.1.100:554/live/ch01_0")
        r2.addWidget(self.txt_stream2_name)
        r2.addWidget(box_url2, stretch=1)
        l2_box.addLayout(r2)
        self.layout_streams.addWidget(self.widget_lens2)

        body_layout.addWidget(card_streams)

        # Card 4: Connection Verification
        card_test = self._create_card(body)
        layout_test = QHBoxLayout(card_test)
        layout_test.setContentsMargins(14, 10, 14, 10)
        layout_test.setSpacing(12)

        self.btn_test = QPushButton("Test Connection", card_test)
        self.btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test.setFixedSize(130, 30)
        self.btn_test.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 41, 59, 0.85);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.18);
                border-color: #38bdf8;
            }
            QPushButton:disabled {
                color: #64748b;
                border-color: #334155;
            }
        """)
        self.btn_test.clicked.connect(self._test_connection)
        layout_test.addWidget(self.btn_test)

        self.lbl_test_result = QLabel("Ready to test live feed", card_test)
        self.lbl_test_result.setStyleSheet("color: #64748b; font-size: 11px;")
        layout_test.addWidget(self.lbl_test_result, stretch=1)

        body_layout.addWidget(card_test)

        scroll.setWidget(body)
        c_layout.addWidget(scroll, stretch=1)

        # -------------------------------------------------------------
        # Action Buttons Row: Cancel and Save Camera
        # -------------------------------------------------------------
        act_row = QHBoxLayout()
        act_row.setContentsMargins(0, 6, 0, 0)
        act_row.setSpacing(10)

        btn_cancel = QPushButton("Cancel", self.container)
        btn_cancel.setFixedSize(96, 34)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 41, 59, 0.7);
                color: #cbd5e1;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                font-size: 11.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        act_row.addWidget(btn_cancel)

        act_row.addStretch()

        self.btn_save = QPushButton("Save Camera", self.container)
        self.btn_save.setFixedSize(140, 34)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 750;
            }
            QPushButton:hover {
                background-color: #0369a1;
                border-color: #60a5fa;
            }
            QPushButton:pressed {
                background-color: #075985;
            }
        """)
        self.btn_save.clicked.connect(self._save_camera)
        act_row.addWidget(self.btn_save)

        c_layout.addLayout(act_row)
        root.addWidget(self.container)

    def _create_card(self, parent: QWidget) -> QFrame:
        card = QFrame(parent)
        card.setObjectName("dialog_card")
        card.setStyleSheet("""
            QFrame#dialog_card {
                background-color: rgba(15, 23, 42, 0.60);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 9px;
            }
        """)
        return card

    def _populate_initial_data(self):
        cam = self.camera_data
        if not cam:
            self.txt_name.setText("New Camera")
            self.txt_ip.setText("192.168.1.100")
            self.spin_port.setValue(554)
            self.txt_user.setText("admin")
            self.txt_pass.setText("")
            self.chk_dual.setChecked(False)
            self._auto_update_urls()
            return

        self.txt_name.setText(cam.get("name", "Camera"))
        self.txt_ip.setText(cam.get("ip", "192.168.1.100"))
        self.spin_port.setValue(int(cam.get("port", 554)))
        self.txt_user.setText(cam.get("username") or "admin")
        self.txt_pass.setText(cam.get("password", ""))

        preset_name = cam.get("model", "")
        idx = self.cmb_preset.findText(preset_name, Qt.MatchFlag.MatchContains)
        if idx >= 0:
            self.cmb_preset.setCurrentIndex(idx)

        is_dual = cam.get("is_dual_lens", False)
        self.chk_dual.setChecked(is_dual)
        self._on_dual_toggled()

        streams = cam.get("streams", [])
        if len(streams) >= 1:
            self.txt_stream1_name.setText(streams[0].get("name", "Lens 1 (PTZ Zoom)"))
            self.txt_stream1_url.setText(streams[0].get("url", ""))
        elif cam.get("lens1_path"):
            path = cam.get("lens1_path")
            auth = f"{cam.get('username')}:{cam.get('password')}@" if cam.get("username") and cam.get("password") else ""
            self.txt_stream1_url.setText(f"rtsp://{auth}{cam.get('ip')}:{cam.get('port', 554)}{path}")

        if len(streams) >= 2:
            self.txt_stream2_name.setText(streams[1].get("name", "Lens 2 (Fixed Wide)"))
            self.txt_stream2_url.setText(streams[1].get("url", ""))
        elif cam.get("lens2_path"):
            path = cam.get("lens2_path")
            auth = f"{cam.get('username')}:{cam.get('password')}@" if cam.get("username") and cam.get("password") else ""
            self.txt_stream2_url.setText(f"rtsp://{auth}{cam.get('ip')}:{cam.get('port', 554)}{path}")

        if not self.txt_stream1_url.text().strip() or (is_dual and not self.txt_stream2_url.text().strip()):
            self._auto_update_urls()

    def _on_dual_toggled(self):
        is_dual = self.chk_dual.isChecked()
        self.widget_lens2.setVisible(is_dual)
        if is_dual:
            curr_url = self.txt_stream2_url.text().strip()
            user = self.txt_user.text().strip()
            pwd = self.txt_pass.text().strip()
            if not curr_url or (user and pwd and f"{user}:{pwd}@" not in curr_url):
                self._auto_update_urls()

    def _on_preset_changed(self, idx: int):
        preset = self.cmb_preset.currentText()
        if "Dual-Lens" in preset:
            self.chk_dual.setChecked(True)
        elif "Single Lens" in preset:
            self.chk_dual.setChecked(False)
        self._auto_update_urls()

    def _auto_update_urls(self):
        ip = self.txt_ip.text().strip()
        port = self.spin_port.value()
        user = self.txt_user.text().strip()
        pwd = self.txt_pass.text().strip()
        auth = f"{user}:{pwd}@" if user and pwd else ""

        preset = self.cmb_preset.currentText()
        if "Xiongmai" in preset:
            path1 = "/cam/realmonitor?channel=1&subtype=0"
            path2 = "/cam/realmonitor?channel=2&subtype=0"
        elif "Dahua" in preset:
            path1 = "/cam/realmonitor?channel=1&subtype=0"
            path2 = "/cam/realmonitor?channel=2&subtype=0"
        elif "Hikvision" in preset:
            path1 = "/Streaming/Channels/101"
            path2 = "/Streaming/Channels/201"
        elif "Dual-Lens" in preset or "CAM720" in preset or "Jooan" in preset:
            path1 = "/live/ch00_0"
            path2 = "/live/ch01_0"
        else:
            path1 = "/live/ch00_0"
            path2 = "/live/ch01_0"

        if ip:
            self.txt_stream1_url.setText(f"rtsp://{auth}{ip}:{port}{path1}")
            self.txt_stream2_url.setText(f"rtsp://{auth}{ip}:{port}{path2}")

    def _test_connection(self):
        ip = self.txt_ip.text().strip()
        port = self.spin_port.value()
        user = self.txt_user.text().strip() or "admin"
        pwd = self.txt_pass.text().strip()

        if not ip:
            self.lbl_test_result.setText("Please enter an IP address first.")
            self.lbl_test_result.setStyleSheet("color: #ef4444; font-size: 11px;")
            return

        curr_url = self.txt_stream1_url.text().strip()
        auth = f"{user}:{pwd}@" if user and pwd else ""
        if curr_url.startswith("rtsp://"):
            after = curr_url[7:]
            slash_idx = after.find("/")
            path = after[slash_idx:] if slash_idx != -1 else "/live/ch00_0"
        else:
            path = "/live/ch00_0"
        url = f"rtsp://{auth}{ip}:{port}{path}"
        self.txt_stream1_url.setText(url)

        self.btn_test.setEnabled(False)
        self.lbl_test_result.setText("Connecting to camera stream...")
        self.lbl_test_result.setStyleSheet("color: #38bdf8; font-size: 11px;")

        self.test_worker = AsyncConnectionTester(url, ip, port)
        self.test_worker.test_finished.connect(self._on_test_finished)
        self.test_worker.start()

    def _on_test_finished(self, success: bool, message: str):
        self.btn_test.setEnabled(True)
        if success:
            self.lbl_test_result.setText(f"Connected: {message}")
            self.lbl_test_result.setStyleSheet("color: #10b981; font-weight: 700; font-size: 11px;")
        else:
            self.lbl_test_result.setText(f"Failed: {message}")
            self.lbl_test_result.setStyleSheet("color: #ef4444; font-weight: 600; font-size: 11px;")

    def _save_camera(self):
        name = self.txt_name.text().strip()
        ip = self.txt_ip.text().strip()

        if not name:
            self.lbl_test_result.setText("Validation error: Camera Name is required.")
            self.lbl_test_result.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.txt_name.setFocus()
            return

        if not ip:
            self.lbl_test_result.setText("Validation error: IP Address is required.")
            self.lbl_test_result.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.txt_ip.setFocus()
            return

        is_dual = self.chk_dual.isChecked()
        cam_id = self.camera_data.get("id") or f"cam_{uuid.uuid4().hex}"

        url1 = self.txt_stream1_url.text().strip()
        url2 = self.txt_stream2_url.text().strip() if is_dual else ""

        user = self.txt_user.text().strip() or "admin"
        pwd = self.txt_pass.text().strip()
        port = self.spin_port.value()
        auth = f"{user}:{pwd}@" if user and pwd else ""
        preset = self.cmb_preset.currentText()

        # Guarantee valid default RTSP paths if empty
        if not url1:
            path1 = "/live/ch00_0" if "Dual-Lens" in preset or "CAM720" in preset else "/live/ch0"
            url1 = f"rtsp://{auth}{ip}:{port}{path1}"
            self.txt_stream1_url.setText(url1)

        if is_dual and not url2:
            path2 = "/live/ch01_0" if "Dual-Lens" in preset or "CAM720" in preset else "/live/ch1"
            url2 = f"rtsp://{auth}{ip}:{port}{path2}"
            self.txt_stream2_url.setText(url2)

        def extract_path(u: str, default_p: str) -> str:
            if not u:
                return default_p
            if u.startswith("rtsp://"):
                u = u[7:]
            s_idx = u.find("/")
            if s_idx != -1:
                p = u[s_idx:]
                return p if p.startswith("/") else f"/{p}"
            return default_p

        path1 = extract_path(url1, "/live/ch00_0")
        path2 = extract_path(url2, "/live/ch01_0")

        url1 = f"rtsp://{auth}{ip}:{port}{path1}"
        url2 = f"rtsp://{auth}{ip}:{port}{path2}" if is_dual else ""

        self.txt_stream1_url.setText(url1)
        if is_dual:
            self.txt_stream2_url.setText(url2)

        streams = [
            {
                "id": f"{cam_id}_lens1",
                "name": self.txt_stream1_name.text().strip() or ("Lens 1 (PTZ Zoom)" if is_dual else "Main Stream"),
                "channel": 0,
                "url": url1,
                "is_ptz": True
            }
        ]
        if is_dual:
            streams.append({
                "id": f"{cam_id}_lens2",
                "name": self.txt_stream2_name.text().strip() or "Lens 2 (Fixed Wide)",
                "channel": 1,
                "url": url2,
                "is_ptz": False
            })

        self.result_data = {
            "id": cam_id,
            "configured": True,
            "name": name,
            "model": self.cmb_preset.currentText(),
            "ip": ip,
            "port": self.spin_port.value(),
            "username": user,
            "password": pwd,
            "is_dual_lens": is_dual,
            "lens1_path": path1,
            "lens2_path": path2 if is_dual else "",
            "streams": streams
        }
        self.accept()

    # Window dragging implementation
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.pos().y() <= 56:
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = QPoint()
