import os
import sys
import re
import socket
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTabWidget, QWidget, QFrame, QScrollArea,
    QApplication, QMessageBox, QGridLayout, QCheckBox, QMenu
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QImage, QDesktopServices, QIcon, QFont, QColor

from ui.components.toggle_switch import ToggleSwitch


def get_tailscale_ip() -> Optional[str]:
    """Detects if Tailscale is active on this host and returns its 100.x.y.z IP."""
    try:
        import psutil
        for iface, addrs in psutil.net_if_addrs().items():
            if "tailscale" in iface.lower():
                for addr in addrs:
                    if addr.family == socket.AF_INET and addr.address.startswith("100."):
                        return addr.address
    except Exception:
        pass
    return None


def generate_qr_bytes(url: str) -> Optional[bytes]:
    """Generates crisp PNG bytes for a QR code."""
    try:
        import qrcode
        import io
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#000000", back_color="#ffffff")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        print(f"[PhoneAccess] QR error: {e}")
        return None


def mask_rtsp_password(url: str) -> str:
    """Masks credentials in RTSP URL for safe visual display."""
    if not url:
        return ""
    m = re.match(r"^(rtsp://[^:@]+):([^@]+)@(.*)$", url)
    if m:
        prefix, pwd, rest = m.groups()
        masked_pwd = "•" * min(max(len(pwd), 6), 12)
        return f"{prefix}:{masked_pwd}@{rest}"
    return url


class PhoneAccessDialog(QDialog):
    """
    Dedicated Mobile Phone Access & Push Notification Center for CCTVPanelView.
    Features:
    - Master Toggle for Mobile Phone Push Notifications (ntfy.sh & Telegram)
    - Quick Filters for mobile alerts (Persons, Vehicles, Animals, Motion)
    - Video Clip delivery toggle
    - Zero-setup ntfy.sh push channel with QR code and instant test alert
    - Secure RTSP Stream catalog with masked passwords (no destructive delete button)
    - Interactive Tailscale, Cloudflare, and Port Forwarding remote access guides
    """
    notifications_toggled = pyqtSignal(bool)

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.web_server = getattr(main_window, "web_server", None)

        self.lan_ip = self.web_server.lan_ip if self.web_server else "127.0.0.1"
        self.port = self.web_server.port if self.web_server else 8080
        self.local_url = self.web_server.get_local_url() if self.web_server else ""
        self.tailscale_ip = get_tailscale_ip()

        self.setWindowTitle("CCTVPanelView - Mobile Phone Access & Notifications")
        self.resize(840, 680)
        self.setMinimumSize(740, 560)

        # Set dialog icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.stream_password_visible: Dict[int, bool] = {}
        self.stream_url_edits: Dict[int, QLineEdit] = {}
        self.stream_raw_urls: Dict[int, str] = {}

        self._apply_styling()
        self._init_ui()

    def _apply_styling(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #070b14;
                color: #f1f5f9;
            }
            QLabel {
                color: #cbd5e1;
                background: transparent;
                border: none;
            }
            QTabWidget::pane {
                border: 1px solid #1e293b;
                border-radius: 8px;
                background: #090e1a;
                top: -1px;
            }
            QTabBar::tab {
                background: #0b1120;
                color: #94a3b8;
                font-weight: 700;
                font-size: 11px;
                padding: 10px 20px;
                border: 1px solid #162032;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #090e1a;
                color: #00e5ff;
                border-color: #1e293b;
                border-top: 2px solid #00e5ff;
            }
            QTabBar::tab:hover:!selected {
                background: #111e33;
                color: #f1f5f9;
            }
            QLineEdit {
                background: #060913;
                color: #38bdf8;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: 600;
                font-size: 12px;
                font-family: Consolas, 'Segoe UI', monospace;
            }
            QLineEdit:focus {
                border-color: #00e5ff;
                background: #070e1c;
            }
            QScrollBar:vertical {
                border: none;
                background: #090e1a;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #1e293b;
                min-height: 24px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #38bdf8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QCheckBox {
                color: #e2e8f0;
                font-size: 11px;
                font-weight: 600;
                spacing: 8px;
                background: transparent;
                border: none;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #334155;
                border-radius: 4px;
                background-color: #0f172a;
            }
            QCheckBox::indicator:hover {
                border-color: #00e5ff;
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border-color: #00e5ff;
            }
            /* Explicit Card Styling to avoid child border inheritance */
            QFrame#card_master {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0a1324, stop:1 #0c172e);
                border: 1px solid #1e3a5f;
                border-radius: 10px;
            }
            QFrame#card_ntfy {
                background: #090f1d;
                border: 1px solid #1e293b;
                border-radius: 10px;
            }
            QFrame#card_telegram {
                background: #090f1d;
                border: 1px solid #1e293b;
                border-radius: 10px;
            }
            QFrame#card_info {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #091325, stop:1 #0c1a33);
                border: 1px solid #1e3a5f;
                border-radius: 8px;
            }
            QFrame#card_tailscale {
                background: #090f1d;
                border: 1px solid #0284c7;
                border-radius: 8px;
            }
            QFrame#card_cloudflare {
                background: #090f1d;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
            QFrame#card_portforward {
                background: #090f1d;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
            QFrame#card_stream {
                background: #090f1d;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
            QFrame#card_local_qr {
                background: #090f1d;
                border: 1px solid #1e293b;
                border-radius: 10px;
            }
            QFrame#card_guide {
                background: #090f1d;
                border: 1px solid #1e293b;
                border-radius: 10px;
            }
        """)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(14)

        # -------------------------------------------------------------
        # 1. Header Row (Brand Logo + Title + Status Badges)
        # -------------------------------------------------------------
        head_frame = QFrame(self)
        head_frame.setStyleSheet("background: transparent; border: none;")
        head_row = QHBoxLayout(head_frame)
        head_row.setContentsMargins(0, 0, 0, 0)
        head_row.setSpacing(12)

        # Minimalist Logo Icon
        icon_png = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.png")
        if os.path.exists(icon_png):
            lbl_logo = QLabel(head_frame)
            lbl_logo.setPixmap(QPixmap(icon_png).scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            lbl_logo.setFixedSize(34, 34)
            lbl_logo.setStyleSheet("background: transparent; border: none;")
            head_row.addWidget(lbl_logo)

        # Title & Subtitle (Clean, anti-aliased, zero dark bounding boxes)
        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        lbl_title = QLabel("Mobile Phone Hub & Notifications", head_frame)
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #f8fafc; letter-spacing: 0.3px; border: none; background: transparent;")
        lbl_sub = QLabel("Instant mobile alerts, live Wi-Fi camera streaming, and secure remote tunnels", head_frame)
        lbl_sub.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 500; border: none; background: transparent;")
        v_head.addWidget(lbl_title)
        v_head.addWidget(lbl_sub)
        head_row.addLayout(v_head)
        head_row.addStretch()

        # Push Notification Master Capsule on Header
        is_push_on = self._is_mobile_notifications_enabled()
        self.header_push_capsule = QFrame(head_frame)
        self.header_push_capsule.setStyleSheet(self._get_push_capsule_style(is_push_on))
        hpc_layout = QHBoxLayout(self.header_push_capsule)
        hpc_layout.setContentsMargins(8, 4, 8, 4)
        hpc_layout.setSpacing(6)

        self.lbl_header_push_dot = QLabel(self.header_push_capsule)
        self.lbl_header_push_dot.setFixedSize(8, 8)
        self.lbl_header_push_dot.setStyleSheet(f"background-color: {'#38bdf8' if is_push_on else '#f59e0b'}; border-radius: 4px; border: none;")
        hpc_layout.addWidget(self.lbl_header_push_dot)

        self.lbl_header_push_text = QLabel(f"ALERTS: {'ACTIVE' if is_push_on else 'PAUSED'}", self.header_push_capsule)
        self.lbl_header_push_text.setStyleSheet(f"color: {'#38bdf8' if is_push_on else '#fbbf24'}; font-weight: 800; font-size: 10px; letter-spacing: 0.6px; border: none; background: transparent;")
        hpc_layout.addWidget(self.lbl_header_push_text)
        head_row.addWidget(self.header_push_capsule)

        # Server Status Capsule
        server_capsule = QFrame(head_frame)
        server_capsule.setStyleSheet("""
            QFrame {
                background-color: rgba(2, 132, 199, 0.12);
                border: 1px solid rgba(2, 132, 199, 0.35);
                border-radius: 6px;
                padding: 4px 10px;
            }
        """)
        sc_layout = QHBoxLayout(server_capsule)
        sc_layout.setContentsMargins(8, 4, 8, 4)
        sc_layout.setSpacing(6)

        dot = QLabel(server_capsule)
        dot.setFixedSize(8, 8)
        dot.setStyleSheet("background-color: #00e5ff; border-radius: 4px; border: none;")
        sc_layout.addWidget(dot)

        self.lbl_server_status = QLabel(f"SERVER : {self.port} LIVE", server_capsule)
        self.lbl_server_status.setStyleSheet("color: #38bdf8; font-weight: 800; font-size: 10px; letter-spacing: 0.6px; border: none; background: transparent;")
        sc_layout.addWidget(self.lbl_server_status)
        head_row.addWidget(server_capsule)

        root_layout.addWidget(head_frame)

        # -------------------------------------------------------------
        # 2. Main Tabs
        # -------------------------------------------------------------
        self.tabs = QTabWidget(self)
        self.tabs.addTab(self._build_notifications_tab(), "Push Notifications")
        self.tabs.addTab(self._build_local_tab(), "Local Network (Wi-Fi)")
        self.tabs.addTab(self._build_rtsp_tab(), "Mobile Apps (RTSP)")
        self.tabs.addTab(self._build_remote_tab(), "Remote Access (4G / 5G)")
        root_layout.addWidget(self.tabs, stretch=1)

        # -------------------------------------------------------------
        # 3. Footer
        # -------------------------------------------------------------
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 4, 0, 0)
        footer.addStretch()

        btn_close = QPushButton("Close", self)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #162032;
                color: #e2e8f0;
                font-weight: 700;
                font-size: 11px;
                padding: 9px 26px;
                border: 1px solid #27354f;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #ffffff;
                border-color: #00e5ff;
            }
        """)
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        root_layout.addLayout(footer)

    # =========================================================================
    # TAB 1: PUSH NOTIFICATIONS (Completely Reworked with Master Toggle & Filters)
    # =========================================================================
    def _build_notifications_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # 1. Master Toggle Switch Card
        master_card = QFrame(content)
        master_card.setObjectName("card_master")
        mc_layout = QVBoxLayout(master_card)
        mc_layout.setContentsMargins(16, 14, 16, 14)
        mc_layout.setSpacing(12)

        # Top row: Icon Badge + Title + ToggleSwitch
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(12)

        bell_badge = QLabel("PUSH", master_card)
        bell_badge.setFixedSize(48, 28)
        bell_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bell_badge.setStyleSheet("""
            background: rgba(0, 229, 255, 0.12);
            color: #00e5ff;
            border: 1px solid rgba(0, 229, 255, 0.35);
            border-radius: 6px;
            font-size: 10px;
            font-weight: 800;
        """)
        toggle_row.addWidget(bell_badge)

        desc_v = QVBoxLayout()
        desc_v.setSpacing(2)
        lbl_master_title = QLabel("Mobile Push Notifications", master_card)
        lbl_master_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #f8fafc; border: none; background: transparent;")
        
        self.lbl_master_desc = QLabel(master_card)
        self.lbl_master_desc.setStyleSheet("font-size: 11px; color: #94a3b8; border: none; background: transparent;")
        desc_v.addWidget(lbl_master_title)
        desc_v.addWidget(self.lbl_master_desc)
        toggle_row.addLayout(desc_v, stretch=1)

        # Dynamic Status Pill
        self.lbl_toggle_status_pill = QLabel(master_card)
        toggle_row.addWidget(self.lbl_toggle_status_pill)

        # Animated Toggle Switch
        is_enabled = self._is_mobile_notifications_enabled()
        self.sw_mobile_notifications = ToggleSwitch(checked=is_enabled, active_color="#0284c7", parent=master_card)
        self.sw_mobile_notifications.toggled.connect(self._on_mobile_notifications_toggled)
        toggle_row.addWidget(self.sw_mobile_notifications)
        mc_layout.addLayout(toggle_row)

        self._update_toggle_card_ui(is_enabled)

        # Separator line
        sep = QFrame(master_card)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #1e293b; max-height: 1px; border: none;")
        mc_layout.addWidget(sep)

        # Sub-row: Quick Category Filters & Video Delivery Checkbox
        filters_label = QLabel("DISPATCH TRIGGER CATEGORIES:", master_card)
        filters_label.setStyleSheet("font-size: 10px; font-weight: 800; color: #38bdf8; letter-spacing: 0.5px; border: none; background: transparent;")
        mc_layout.addWidget(filters_label)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(16)

        app_settings = getattr(self.main_window, "app_settings", {})
        self.chk_person = QCheckBox("Persons (Intruders)")
        self.chk_person.setChecked(bool(app_settings.get("notify_person", True)))
        self.chk_person.toggled.connect(lambda v: self._update_filter_setting("notify_person", v))
        chips_row.addWidget(self.chk_person)

        self.chk_vehicle = QCheckBox("Vehicles")
        self.chk_vehicle.setChecked(bool(app_settings.get("notify_vehicle", False)))
        self.chk_vehicle.toggled.connect(lambda v: self._update_filter_setting("notify_vehicle", v))
        chips_row.addWidget(self.chk_vehicle)

        self.chk_animal = QCheckBox("Animals & Wildlife")
        self.chk_animal.setChecked(bool(app_settings.get("notify_animal", False)))
        self.chk_animal.toggled.connect(lambda v: self._update_filter_setting("notify_animal", v))
        chips_row.addWidget(self.chk_animal)

        self.chk_motion = QCheckBox("General Motion")
        self.chk_motion.setChecked(bool(app_settings.get("notify_motion", False)))
        self.chk_motion.toggled.connect(lambda v: self._update_filter_setting("notify_motion", v))
        chips_row.addWidget(self.chk_motion)
        chips_row.addStretch()
        mc_layout.addLayout(chips_row)

        # Video Clip Attachment Row
        self.chk_attach_video = QCheckBox("Attach 10-Second MP4 Video Clip for instant playback on phone")
        self.chk_attach_video.setChecked(bool(app_settings.get("phone_notify_video", app_settings.get("send_video_to_phone", True))))
        self.chk_attach_video.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 11px; border: none;")
        self.chk_attach_video.toggled.connect(self._on_video_attach_toggled)
        mc_layout.addWidget(self.chk_attach_video)

        layout.addWidget(master_card)

        # -------------------------------------------------------------
        # 2. Card: ntfy.sh (Zero-Setup Push Channel)
        # -------------------------------------------------------------
        ntfy_card = QFrame(content)
        ntfy_card.setObjectName("card_ntfy")
        nc_layout = QVBoxLayout(ntfy_card)
        nc_layout.setContentsMargins(16, 14, 16, 14)
        nc_layout.setSpacing(12)

        ntfy_head = QHBoxLayout()
        lbl_ntfy_title = QLabel("1. INSTANT PUSH NOTIFICATIONS (ntfy.sh - Zero Account Required)", ntfy_card)
        lbl_ntfy_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #00e5ff; letter-spacing: 0.5px; border: none; background: transparent;")
        ntfy_head.addWidget(lbl_ntfy_title)
        ntfy_head.addStretch()

        badge_free = QLabel("100% FREE & UNLIMITED", ntfy_card)
        badge_free.setStyleSheet("background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; font-size: 9px; font-weight: 800; padding: 2px 6px;")
        ntfy_head.addWidget(badge_free)
        nc_layout.addLayout(ntfy_head)

        center_h = QHBoxLayout()
        center_h.setSpacing(18)

        # High-Contrast QR Code container with modern slate bezel
        qr_frame = QFrame(ntfy_card)
        qr_frame.setFixedSize(148, 148)
        qr_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 2px solid #0284c7;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        qf_layout = QVBoxLayout(qr_frame)
        qf_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_ntfy_qr = QLabel(qr_frame)
        self.lbl_ntfy_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_ntfy_qr.setStyleSheet("border: none; background: transparent;")
        qf_layout.addWidget(self.lbl_ntfy_qr)
        center_h.addWidget(qr_frame)

        # Right Column: Topic details & Step instructions
        info_v = QVBoxLayout()
        info_v.setSpacing(8)

        topic = app_settings.get("ntfy_topic", "cctv_pv_alerts")
        
        # Secret Topic Channel Pill Box
        topic_box = QFrame(ntfy_card)
        topic_box.setStyleSheet("background: #060912; border: 1px solid #1e293b; border-radius: 6px; padding: 6px 10px;")
        tb_layout = QHBoxLayout(topic_box)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(8)

        tb_lbl = QLabel("Secret Channel:", topic_box)
        tb_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 600; border: none; background: transparent;")
        tb_layout.addWidget(tb_lbl)

        self.lbl_topic_value = QLabel(topic, topic_box)
        self.lbl_topic_value.setStyleSheet("font-size: 12px; color: #00e5ff; font-weight: 800; font-family: Consolas, monospace; border: none; background: transparent;")
        tb_layout.addWidget(self.lbl_topic_value, stretch=1)

        btn_copy_topic_quick = QPushButton("Copy", topic_box)
        btn_copy_topic_quick.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_topic_quick.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                font-weight: 700;
                font-size: 10px;
                padding: 4px 10px;
                border: 1px solid #334155;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0284c7;
                border-color: #00e5ff;
            }
        """)
        btn_copy_topic_quick.clicked.connect(lambda: self._copy_to_clipboard(self._get_current_topic(), "Topic copied to clipboard!"))
        tb_layout.addWidget(btn_copy_topic_quick)
        info_v.addWidget(topic_box)

        # Steps text
        self.lbl_ntfy_steps = QLabel(
            "<span style='color:#e2e8f0; font-size:11px;'><b>3-Step Setup:</b></span><br>"
            "<span style='color:#94a3b8; font-size:11px; line-height:1.5;'>"
            "1. Install the free <b>ntfy</b> app from the App Store (iOS) or Google Play (Android).<br>"
            "2. Scan the QR code or subscribe to the secret channel above.<br>"
            "3. Receive instant photos, descriptions, and 10s video clips on your phone!"
            "</span>",
            ntfy_card
        )
        self.lbl_ntfy_steps.setWordWrap(True)
        self.lbl_ntfy_steps.setStyleSheet("border: none; background: transparent;")
        info_v.addWidget(self.lbl_ntfy_steps)

        # Action Buttons (Clean, modern, properly styled)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_test_ntfy = QPushButton("Send Test Notification", ntfy_card)
        self.btn_test_ntfy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test_ntfy.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #2563eb);
                color: #ffffff;
                font-weight: 700;
                font-size: 11px;
                padding: 7px 16px;
                border: 1px solid #38bdf8;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #1d4ed8);
                border-color: #7dd3fc;
            }
        """)
        self.btn_test_ntfy.clicked.connect(self._test_ntfy_push)
        btn_row.addWidget(self.btn_test_ntfy)

        self.btn_copy_full_url = QPushButton("Copy Channel URL", ntfy_card)
        self.btn_copy_full_url.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_full_url.setStyleSheet("""
            QPushButton {
                background-color: #162032;
                color: #cbd5e1;
                font-weight: 600;
                font-size: 11px;
                padding: 7px 14px;
                border: 1px solid #27354f;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #27354f;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.btn_copy_full_url.clicked.connect(lambda: self._copy_to_clipboard(f"https://ntfy.sh/{self._get_current_topic()}", "Full ntfy.sh URL copied to clipboard!"))
        btn_row.addWidget(self.btn_copy_full_url)

        self.btn_gen_secret = QPushButton("New Secret Topic", ntfy_card)
        self.btn_gen_secret.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gen_secret.setStyleSheet("""
            QPushButton {
                background-color: #162032;
                color: #94a3b8;
                font-weight: 600;
                font-size: 11px;
                padding: 7px 12px;
                border: 1px solid #27354f;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #27354f;
                color: #f8fafc;
                border-color: #f59e0b;
            }
        """)
        self.btn_gen_secret.setToolTip("Generate a new unguessable secret topic channel")
        self.btn_gen_secret.clicked.connect(self._generate_new_secret_topic)
        btn_row.addWidget(self.btn_gen_secret)

        btn_row.addStretch()
        info_v.addLayout(btn_row)

        center_h.addLayout(info_v, stretch=1)
        nc_layout.addLayout(center_h)
        layout.addWidget(ntfy_card)

        # -------------------------------------------------------------
        # 3. Card: Telegram Bot Notifications (Optional)
        # -------------------------------------------------------------
        tg_card = QFrame(content)
        tg_card.setObjectName("card_telegram")
        tg_layout = QVBoxLayout(tg_card)
        tg_layout.setContentsMargins(16, 14, 16, 14)
        tg_layout.setSpacing(10)

        tg_head = QHBoxLayout()
        lbl_tg_title = QLabel("2. TELEGRAM BOT NOTIFICATIONS (OPTIONAL)", tg_card)
        lbl_tg_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #229ed9; letter-spacing: 0.5px; border: none; background: transparent;")
        tg_head.addWidget(lbl_tg_title)
        tg_head.addStretch()

        has_tg = bool(app_settings.get("telegram_enabled", False) and app_settings.get("telegram_bot_token"))
        tg_status_pill = QLabel("CONFIGURED" if has_tg else "OPTIONAL", tg_card)
        tg_status_pill.setStyleSheet(f"""
            background: {'rgba(56, 189, 248, 0.12)' if has_tg else 'rgba(148, 163, 184, 0.12)'};
            color: {'#38bdf8' if has_tg else '#94a3b8'};
            border: 1px solid {'#0284c7' if has_tg else '#334155'};
            border-radius: 4px;
            font-size: 9px;
            font-weight: 800;
            padding: 2px 6px;
        """)
        tg_head.addWidget(tg_status_pill)
        tg_layout.addLayout(tg_head)

        lbl_tg_desc = QLabel(
            "If you prefer receiving alerts directly into a private Telegram chat or channel, configure your bot token and chat ID in Settings.",
            tg_card
        )
        lbl_tg_desc.setWordWrap(True)
        lbl_tg_desc.setStyleSheet("color: #94a3b8; font-size: 11px; border: none; background: transparent;")
        tg_layout.addWidget(lbl_tg_desc)

        btn_open_settings = QPushButton("Open Telegram Configuration in Settings", tg_card)
        btn_open_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_settings.setStyleSheet("""
            QPushButton {
                background-color: #162032;
                color: #38bdf8;
                font-weight: 600;
                font-size: 11px;
                padding: 7px 16px;
                border: 1px solid #27354f;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #27354f;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        btn_open_settings.clicked.connect(self._open_notifications_settings)
        tg_layout.addWidget(btn_open_settings)

        layout.addWidget(tg_card)
        layout.addStretch()

        scroll.setWidget(content)
        self._update_ntfy_qr_image(topic)
        return scroll

    def _is_mobile_notifications_enabled(self) -> bool:
        settings = getattr(self.main_window, "app_settings", {})
        return bool(settings.get("phone_notifications_enabled", True))

    def _get_current_topic(self) -> str:
        settings = getattr(self.main_window, "app_settings", {})
        return settings.get("ntfy_topic", "cctv_pv_alerts")

    def _get_push_capsule_style(self, is_on: bool) -> str:
        if is_on:
            return "background-color: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 6px;"
        return "background-color: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 6px;"

    def _update_toggle_card_ui(self, is_enabled: bool):
        if is_enabled:
            self.lbl_master_desc.setText("Status: Active. Broadcasting photos, AI detections, and 10s video clips directly to your phone.")
            self.lbl_toggle_status_pill.setText("ACTIVE")
            self.lbl_toggle_status_pill.setStyleSheet("background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid #0284c7; font-size: 10px; font-weight: 800; border-radius: 4px; padding: 3px 8px;")
        else:
            self.lbl_master_desc.setText("Status: PAUSED. Mobile phone notifications are temporarily muted.")
            self.lbl_toggle_status_pill.setText("PAUSED")
            self.lbl_toggle_status_pill.setStyleSheet("background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #f59e0b; font-size: 10px; font-weight: 800; border-radius: 4px; padding: 3px 8px;")

        # Update header capsule
        if hasattr(self, "header_push_capsule"):
            self.header_push_capsule.setStyleSheet(self._get_push_capsule_style(is_enabled))
            self.lbl_header_push_dot.setStyleSheet(f"background-color: {'#38bdf8' if is_enabled else '#f59e0b'}; border-radius: 4px; border: none;")
            self.lbl_header_push_text.setText(f"ALERTS: {'ACTIVE' if is_enabled else 'PAUSED'}")
            self.lbl_header_push_text.setStyleSheet(f"color: {'#38bdf8' if is_enabled else '#fbbf24'}; font-weight: 800; font-size: 10px; letter-spacing: 0.6px; border: none; background: transparent;")

    def _on_mobile_notifications_toggled(self, checked: bool):
        settings = getattr(self.main_window, "app_settings", {})
        settings["phone_notifications_enabled"] = checked
        self._update_toggle_card_ui(checked)

        # Propagate to MainWindow, DeviceManager and AlertManager
        if hasattr(self.main_window, "device_manager") and self.main_window.device_manager:
            self.main_window.device_manager.save_config()
        if hasattr(self.main_window, "alert_manager") and self.main_window.alert_manager:
            self.main_window.alert_manager.set_app_settings(settings)
        if hasattr(self.main_window, "_update_phone_btn_status"):
            self.main_window._update_phone_btn_status()

        self.notifications_toggled.emit(checked)
        msg = "Mobile phone notifications activated!" if checked else "Mobile phone notifications muted."
        if hasattr(self.main_window, "statusBar") and self.main_window.statusBar():
            self.main_window.statusBar().showMessage(msg, 3500)

    def _update_filter_setting(self, key: str, value: bool):
        settings = getattr(self.main_window, "app_settings", {})
        settings[key] = bool(value)
        if hasattr(self.main_window, "device_manager") and self.main_window.device_manager:
            self.main_window.device_manager.save_config()
        if hasattr(self.main_window, "alert_manager") and self.main_window.alert_manager:
            self.main_window.alert_manager.set_app_settings(settings)

    def _on_video_attach_toggled(self, checked: bool):
        settings = getattr(self.main_window, "app_settings", {})
        settings["phone_notify_video"] = bool(checked)
        settings["send_video_to_phone"] = bool(checked)
        if hasattr(self.main_window, "device_manager") and self.main_window.device_manager:
            self.main_window.device_manager.save_config()
        if hasattr(self.main_window, "alert_manager") and self.main_window.alert_manager:
            self.main_window.alert_manager.set_app_settings(settings)

    # =========================================================================
    # TAB 2: MOBILE APPS (RTSP) - Cleaned, Masked Passwords, NO Delete Button
    # =========================================================================
    def _build_rtsp_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Top Information Banner
        info_card = QFrame(tab)
        info_card.setObjectName("card_info")
        ic_layout = QVBoxLayout(info_card)
        ic_layout.setContentsMargins(14, 12, 14, 12)
        ic_layout.setSpacing(6)

        hdr_h = QHBoxLayout()
        lbl_info_title = QLabel("DIRECT RTSP STREAMS FOR MOBILE CCTV APPS", info_card)
        lbl_info_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #00e5ff; letter-spacing: 0.5px; border: none; background: transparent;")
        hdr_h.addWidget(lbl_info_title)
        hdr_h.addStretch()

        app_pills = QLabel("Recommended: TinyCam PRO • VLC • ONVIF Viewer • IPCview", info_card)
        app_pills.setStyleSheet("font-size: 10px; color: #94a3b8; font-weight: 600; border: none; background: transparent;")
        hdr_h.addWidget(app_pills)
        ic_layout.addLayout(hdr_h)

        lbl_desc = QLabel(
            "Use the direct RTSP addresses below to connect third-party mobile surveillance apps directly to any camera lens. "
            "Passwords are kept securely masked until revealed.",
            info_card
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #cbd5e1; font-size: 11px; border: none; background: transparent;")
        ic_layout.addWidget(lbl_desc)
        layout.addWidget(info_card)

        # Streams Scroll Area
        scroll = QScrollArea(tab)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        s_widget = QWidget()
        s_layout = QVBoxLayout(s_widget)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(10)

        stream_idx = 0
        if hasattr(self.main_window, "device_manager") and self.main_window.device_manager:
            for s in self.main_window.device_manager.get_all_streams():
                stream_card = self._build_single_rtsp_card(s, stream_idx)
                s_layout.addWidget(stream_card)
                stream_idx += 1

        if stream_idx == 0:
            lbl_empty = QLabel("No active camera streams configured yet.", s_widget)
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet("color: #64748b; font-size: 12px; padding: 40px; border: none; background: transparent;")
            s_layout.addWidget(lbl_empty)

        s_layout.addStretch()
        scroll.setWidget(s_widget)
        layout.addWidget(scroll)
        return tab

    def _build_single_rtsp_card(self, s: Dict[str, Any], idx: int) -> QFrame:
        card = QFrame()
        card.setObjectName("card_stream")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setSpacing(8)

        # Header Row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        is_ptz = s.get("is_ptz", False)
        badge = QLabel("PTZ ZOOM" if is_ptz else "FIXED WIDE", card)
        badge.setStyleSheet(f"""
            background-color: {'rgba(56, 189, 248, 0.15)' if is_ptz else 'rgba(99, 102, 241, 0.15)'};
            color: {'#38bdf8' if is_ptz else '#a5b4fc'};
            font-size: 9px;
            font-weight: 800;
            border: 1px solid {'#0284c7' if is_ptz else '#6366f1'};
            border-radius: 4px;
            padding: 2px 6px;
        """)
        title_row.addWidget(badge)

        cam_name = s.get("camera_name", "Camera")
        s_name = s.get("name", "Stream")
        lbl_t = QLabel(f"<b>{cam_name}</b> <span style='color:#94a3b8;'>• {s_name}</span>", card)
        lbl_t.setStyleSheet("font-size: 12px; color: #f8fafc; border: none; background: transparent;")
        title_row.addWidget(lbl_t)
        title_row.addStretch()

        # Telemetry Pill
        res_info = QLabel("2K RTSP • H.264/H.265", card)
        res_info.setStyleSheet("font-size: 10px; color: #64748b; font-weight: 600; border: none; background: transparent;")
        title_row.addWidget(res_info)
        c_layout.addLayout(title_row)

        # URL Input Field + Toggle Password Reveal + Copy Button Row
        url_row = QHBoxLayout()
        url_row.setSpacing(8)

        raw_url = s.get("url", "")
        self.stream_raw_urls[idx] = raw_url
        self.stream_password_visible[idx] = False

        masked = mask_rtsp_password(raw_url)
        txt_url = QLineEdit(masked, card)
        txt_url.setReadOnly(True)
        txt_url.setStyleSheet("""
            QLineEdit {
                background: #060912;
                color: #38bdf8;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 6px 10px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
        self.stream_url_edits[idx] = txt_url
        url_row.addWidget(txt_url, stretch=1)

        # Reveal Password Toggle Button
        btn_eye = QPushButton("Show", card)
        btn_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye.setFixedWidth(64)
        btn_eye.setStyleSheet("""
            QPushButton {
                background-color: #162032;
                color: #94a3b8;
                font-weight: 600;
                font-size: 11px;
                padding: 6px 8px;
                border: 1px solid #27354f;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #27354f;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        btn_eye.clicked.connect(lambda ch, i=idx, b=btn_eye: self._toggle_rtsp_password_reveal(i, b))
        url_row.addWidget(btn_eye)

        # Copy RTSP URL Button
        btn_copy = QPushButton("Copy RTSP", card)
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #2563eb);
                color: #ffffff;
                font-weight: 700;
                font-size: 11px;
                padding: 6px 14px;
                border: 1px solid #38bdf8;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #1d4ed8);
                border-color: #7dd3fc;
            }
        """)
        btn_copy.clicked.connect(lambda ch, u=raw_url, b=btn_copy: self._copy_rtsp_with_animation(u, b))
        url_row.addWidget(btn_copy)

        c_layout.addLayout(url_row)
        return card

    def _toggle_rtsp_password_reveal(self, idx: int, btn: QPushButton):
        curr = self.stream_password_visible.get(idx, False)
        new_state = not curr
        self.stream_password_visible[idx] = new_state
        raw = self.stream_raw_urls.get(idx, "")
        edit = self.stream_url_edits.get(idx)
        if edit:
            if new_state:
                edit.setText(raw)
                btn.setText("Hide")
                btn.setStyleSheet("background-color: #1e293b; color: #f59e0b; border: 1px solid #d97706; border-radius: 6px; padding: 6px 8px; font-size: 11px; font-weight: 600;")
            else:
                edit.setText(mask_rtsp_password(raw))
                btn.setText("Show")
                btn.setStyleSheet("background-color: #162032; color: #94a3b8; border: 1px solid #27354f; border-radius: 6px; padding: 6px 8px; font-size: 11px; font-weight: 600;")

    def _copy_rtsp_with_animation(self, url: str, btn: QPushButton):
        self._copy_to_clipboard(url, "RTSP address copied to clipboard!")
        btn.setText("Copied!")
        btn.setStyleSheet("background-color: #0284c7; color: #ffffff; border: 1px solid #38bdf8; font-weight: 700; border-radius: 6px; padding: 6px 14px; font-size: 11px;")
        QTimer.singleShot(1800, lambda: self._restore_copy_btn(btn))

    def _restore_copy_btn(self, btn: QPushButton):
        btn.setText("Copy RTSP")
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #2563eb);
                color: #ffffff;
                font-weight: 700;
                font-size: 11px;
                padding: 6px 14px;
                border: 1px solid #38bdf8;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #1d4ed8);
                border-color: #7dd3fc;
            }
        """)

    # =========================================================================
    # TAB 3: REMOTE ACCESS (4G / 5G) - Cleaned, Modern Step Architecture
    # =========================================================================
    def _build_remote_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Overview Header
        info_card = QFrame(content)
        info_card.setObjectName("card_info")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(6)

        lbl_info_title = QLabel("REMOTE ACCESS ARCHITECTURE (4G / 5G CELLULAR)", info_card)
        lbl_info_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #00e5ff; letter-spacing: 0.6px; border: none; background: transparent;")
        info_layout.addWidget(lbl_info_title)

        lbl_info_desc = QLabel(
            "When on mobile data (4G / 5G) or away from home, your smartphone is outside the local Wi-Fi subnet. "
            "Because most residential internet uses CGNAT without static public IPs, below are the 3 proven, secure methods:",
            info_card
        )
        lbl_info_desc.setWordWrap(True)
        lbl_info_desc.setStyleSheet("color: #cbd5e1; font-size: 11px; line-height: 1.4; border: none; background: transparent;")
        info_layout.addWidget(lbl_info_desc)
        layout.addWidget(info_card)

        # Option 1: Tailscale (Recommended)
        t_card = QFrame(content)
        t_card.setObjectName("card_tailscale")
        t_layout = QVBoxLayout(t_card)
        t_layout.setContentsMargins(14, 12, 14, 12)
        t_layout.setSpacing(10)

        t_head = QHBoxLayout()
        lbl_t_title = QLabel("METHOD #1: TAILSCALE WIREGUARD MESH", t_card)
        lbl_t_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #38bdf8; letter-spacing: 0.5px; border: none; background: transparent;")
        t_head.addWidget(lbl_t_title)

        rec_pill = QLabel("RECOMMENDED • 100% FREE", t_card)
        rec_pill.setStyleSheet("background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; font-size: 9px; font-weight: 800; padding: 2px 6px;")
        t_head.addWidget(rec_pill)
        t_head.addStretch()

        btn_open_tailscale = QPushButton("Download Tailscale", t_card)
        btn_open_tailscale.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_tailscale.setStyleSheet("""
            QPushButton {
                background-color: #0369a1;
                color: #e0f2fe;
                font-weight: 700;
                font-size: 11px;
                padding: 6px 14px;
                border: 1px solid #38bdf8;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0284c7;
                color: #ffffff;
            }
        """)
        btn_open_tailscale.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://tailscale.com/download")))
        t_head.addWidget(btn_open_tailscale)
        t_layout.addLayout(t_head)

        lbl_t_desc = QLabel(
            "<b>Why it is the best choice:</b> Establishes an end-to-end encrypted WireGuard tunnel between your PC and phone. "
            "<b>Zero router port forwarding required</b>, bypasses cellular CGNAT effortlessly, and takes 2 minutes to set up.",
            t_card
        )
        lbl_t_desc.setWordWrap(True)
        lbl_t_desc.setStyleSheet("color: #cbd5e1; font-size: 11px; line-height: 1.4; border: none; background: transparent;")
        t_layout.addWidget(lbl_t_desc)

        # 4 Step Badges Grid
        t_grid = QGridLayout()
        t_grid.setSpacing(8)
        t1 = self._build_step_capsule("01", "Install on PC", "Install Tailscale on this PC from tailscale.com and log in.", "#38bdf8")
        t2 = self._build_step_capsule("02", "Install on Phone", "Install Tailscale app on iOS/Android and log into the same account.", "#38bdf8")
        t3 = self._build_step_capsule("03", "Connect Tunnel", "Enable Tailscale on phone; your devices form a private secure mesh.", "#38bdf8")
        
        ts_url = f"http://{self.tailscale_ip}:{self.port}" if self.tailscale_ip else f"http://[TAILSCALE-IP]:{self.port}"
        t4 = self._build_step_capsule("04", "Open Feeds", f"In Safari/Chrome on phone, open: {ts_url}", "#38bdf8")
        t_grid.addWidget(t1, 0, 0)
        t_grid.addWidget(t2, 0, 1)
        t_grid.addWidget(t3, 1, 0)
        t_grid.addWidget(t4, 1, 1)
        t_layout.addLayout(t_grid)

        # Detected Tailscale IP banner (if active)
        if self.tailscale_ip:
            ts_bar = QFrame(t_card)
            ts_bar.setStyleSheet("background: rgba(2, 132, 199, 0.20); border: 1px solid #0284c7; border-radius: 6px; padding: 6px 12px;")
            ts_bar_l = QHBoxLayout(ts_bar)
            ts_bar_l.setContentsMargins(6, 4, 6, 4)
            ts_bar_lbl = QLabel(f"Detected Tailscale IP: <b style='color:#7dd3fc;'>{self.tailscale_ip}</b> (Port {self.port})", ts_bar)
            ts_bar_lbl.setStyleSheet("font-size: 11px; color: #f0f9ff; border: none; background: transparent;")
            ts_bar_l.addWidget(ts_bar_lbl, stretch=1)

            btn_copy_ts = QPushButton("Copy Remote Link", ts_bar)
            btn_copy_ts.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_copy_ts.setStyleSheet("background: #0284c7; color: #fff; font-weight: 700; border-radius: 4px; padding: 4px 10px; font-size: 10px;")
            btn_copy_ts.clicked.connect(lambda: self._copy_to_clipboard(ts_url, "Tailscale remote URL copied!"))
            ts_bar_l.addWidget(btn_copy_ts)
            t_layout.addWidget(ts_bar)

        layout.addWidget(t_card)

        # Option 2: Cloudflare Tunnel
        cf_card = QFrame(content)
        cf_card.setObjectName("card_cloudflare")
        cf_layout = QVBoxLayout(cf_card)
        cf_layout.setContentsMargins(14, 12, 14, 12)
        cf_layout.setSpacing(8)

        cf_head = QHBoxLayout()
        lbl_cf_title = QLabel("METHOD #2: CLOUDFLARE TUNNEL (cloudflared)", cf_card)
        lbl_cf_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #0284c7; letter-spacing: 0.5px; border: none; background: transparent;")
        cf_head.addWidget(lbl_cf_title)
        cf_head.addStretch()

        cf_pill = QLabel("HTTPS DOMAIN • NO VPN APP", cf_card)
        cf_pill.setStyleSheet("background: rgba(2, 132, 199, 0.12); color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; font-size: 9px; font-weight: 800; padding: 2px 6px;")
        cf_head.addWidget(cf_pill)
        cf_layout.addLayout(cf_head)

        lbl_cf_desc = QLabel(
            "Exposes port 8080 through a custom domain (e.g. <code>https://cctv.yourdomain.com</code>) using free Cloudflare Tunnels. "
            "Requires no router port forwarding and works natively in Safari and Chrome without any mobile client installed.",
            cf_card
        )
        lbl_cf_desc.setWordWrap(True)
        lbl_cf_desc.setStyleSheet("color: #94a3b8; font-size: 11px; line-height: 1.4; border: none; background: transparent;")
        cf_layout.addWidget(lbl_cf_desc)
        layout.addWidget(cf_card)

        # Option 3: Port Forwarding
        pf_card = QFrame(content)
        pf_card.setObjectName("card_portforward")
        pf_layout = QVBoxLayout(pf_card)
        pf_layout.setContentsMargins(14, 12, 14, 12)
        pf_layout.setSpacing(8)

        pf_head = QHBoxLayout()
        lbl_pf_title = QLabel("REMOTE ACCESS: TRANSPORT SECURITY", pf_card)
        lbl_pf_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #f59e0b; letter-spacing: 0.5px; border: none; background: transparent;")
        pf_head.addWidget(lbl_pf_title)
        pf_head.addStretch()

        pf_pill = QLabel("REQUIRES PUBLIC IP", pf_card)
        pf_pill.setStyleSheet("background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid #d97706; border-radius: 4px; font-size: 9px; font-weight: 800; padding: 2px 6px;")
        pf_head.addWidget(pf_pill)
        pf_layout.addLayout(pf_head)

        lbl_pf_desc = QLabel(
            "Use a VPN or an HTTPS reverse proxy for remote viewing. Open the remote address and paste the "
            "access code from the local link when prompted. Keep the embedded HTTP server on your trusted network.",
            pf_card
        )
        lbl_pf_desc.setWordWrap(True)
        lbl_pf_desc.setStyleSheet("color: #94a3b8; font-size: 11px; line-height: 1.4; border: none; background: transparent;")
        pf_layout.addWidget(lbl_pf_desc)
        layout.addWidget(pf_card)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # =========================================================================
    # TAB 4: LOCAL NETWORK (WI-FI)
    # =========================================================================
    def _build_local_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # 1. QR Code & Direct URL Card
        qr_card = QFrame(tab)
        qr_card.setObjectName("card_local_qr")
        qr_layout = QVBoxLayout(qr_card)
        qr_layout.setContentsMargins(16, 14, 16, 14)
        qr_layout.setSpacing(10)

        top_h = QHBoxLayout()
        lbl_step = QLabel("QUICK CONNECT • LOCAL WI-FI (LAN)", qr_card)
        lbl_step.setStyleSheet("font-size: 11px; font-weight: 800; color: #00e5ff; letter-spacing: 0.6px; border: none; background: transparent;")
        top_h.addWidget(lbl_step)
        top_h.addStretch()

        lbl_badge = QLabel("INSTANT BROWSER LAUNCH", qr_card)
        lbl_badge.setStyleSheet("color: #94a3b8; font-size: 9px; font-weight: 700; background: #162032; border: 1px solid #27354f; border-radius: 4px; padding: 2px 6px;")
        top_h.addWidget(lbl_badge)
        qr_layout.addLayout(top_h)

        center_h = QHBoxLayout()
        center_h.setSpacing(16)

        # Live QR Code Image Container
        qr_frame = QFrame(qr_card)
        qr_frame.setFixedSize(154, 154)
        qr_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 2px solid #0284c7;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        qf_layout = QVBoxLayout(qr_frame)
        qf_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_qr = QLabel(qr_frame)
        self.lbl_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_qr.setStyleSheet("border: none; background: transparent;")
        qf_layout.addWidget(self.lbl_qr)
        center_h.addWidget(qr_frame)

        # URL and Actions
        url_v = QVBoxLayout()
        url_v.setSpacing(10)

        lbl_url_desc = QLabel("Scan the QR code with your phone camera, or open this local URL in Safari / Chrome:", qr_card)
        lbl_url_desc.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 600; line-height: 1.4; border: none; background: transparent;")
        lbl_url_desc.setWordWrap(True)
        url_v.addWidget(lbl_url_desc)

        self.txt_url = QLineEdit(self.local_url, qr_card)
        self.txt_url.setReadOnly(True)
        url_v.addWidget(self.txt_url)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_copy_url = QPushButton("Copy Link", qr_card)
        self.btn_copy_url.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_url.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #2563eb);
                color: #ffffff;
                font-weight: 700;
                font-size: 11px;
                padding: 7px 16px;
                border: 1px solid #38bdf8;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #1d4ed8);
                border-color: #7dd3fc;
            }
        """)
        self.btn_copy_url.clicked.connect(self._copy_local_url)
        btn_row.addWidget(self.btn_copy_url)

        btn_open_browser = QPushButton("Open on PC Browser", qr_card)
        btn_open_browser.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_browser.setStyleSheet("""
            QPushButton {
                background-color: #162032;
                color: #cbd5e1;
                font-weight: 600;
                font-size: 11px;
                padding: 7px 14px;
                border: 1px solid #27354f;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #27354f;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        btn_open_browser.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.local_url)))
        btn_row.addWidget(btn_open_browser)
        url_v.addLayout(btn_row)

        center_h.addLayout(url_v, stretch=1)
        qr_layout.addLayout(center_h)
        layout.addWidget(qr_card)

        # 2. Modern 3-Step Setup Guide
        guide_card = QFrame(tab)
        guide_card.setObjectName("card_guide")
        guide_layout = QVBoxLayout(guide_card)
        guide_layout.setContentsMargins(16, 14, 16, 14)
        guide_layout.setSpacing(10)

        lbl_guide_title = QLabel("3-STEP CONNECTIVITY WORKFLOW", guide_card)
        lbl_guide_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #f8fafc; letter-spacing: 0.6px; border: none; background: transparent;")
        guide_layout.addWidget(lbl_guide_title)

        steps_grid = QGridLayout()
        steps_grid.setSpacing(10)

        s1 = self._build_step_capsule("01", "Verify Wi-Fi Network", "Ensure your mobile phone is connected to the same local Wi-Fi router as this surveillance PC.", "#0284c7")
        steps_grid.addWidget(s1, 0, 0)

        s2 = self._build_step_capsule("02", "Scan QR Code", "Open Camera app on iPhone or Android, aim at the QR code, and tap the instant link banner.", "#38bdf8")
        steps_grid.addWidget(s2, 0, 1)

        s3 = self._build_step_capsule("03", "Full Feeds & PTZ", "Enjoy high-speed live streams, PTZ motor navigation, dual-lens switching, and snapshot downloads.", "#8b5cf6")
        steps_grid.addWidget(s3, 0, 2)

        guide_layout.addLayout(steps_grid)
        layout.addWidget(guide_card)
        layout.addStretch()

        self._update_qr_image()
        return tab

    def _build_step_capsule(self, step_num: str, title: str, desc: str, color_hex: str) -> QFrame:
        """Constructs a sleek, segmented modern card for step instructions."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #060912;
                border: 1px solid #162032;
                border-top: 2px solid {color_hex};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        v = QVBoxLayout(card)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        hdr = QHBoxLayout()
        badge = QLabel(step_num, card)
        badge.setStyleSheet(f"""
            background-color: {color_hex}22;
            color: {color_hex};
            font-size: 10px;
            font-weight: 900;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid {color_hex}55;
        """)
        hdr.addWidget(badge)

        t_lbl = QLabel(title, card)
        t_lbl.setStyleSheet("color: #f1f5f9; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        hdr.addWidget(t_lbl, stretch=1)
        v.addLayout(hdr)

        d_lbl = QLabel(desc, card)
        d_lbl.setWordWrap(True)
        d_lbl.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 500; line-height: 1.4; border: none; background: transparent;")
        v.addWidget(d_lbl)
        return card

    # =========================================================================
    # Helpers
    # =========================================================================
    def _update_qr_image(self):
        """Generates high-contrast QR Pixmap and renders onto lbl_qr."""
        png_bytes = generate_qr_bytes(self.local_url)
        if png_bytes:
            qimg = QImage.fromData(png_bytes)
            pixmap = QPixmap.fromImage(qimg).scaled(146, 146, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_qr.setPixmap(pixmap)

    def _update_ntfy_qr_image(self, topic: str):
        ntfy_url = f"https://ntfy.sh/{topic}"
        png_bytes = generate_qr_bytes(ntfy_url)
        if png_bytes:
            qimg = QImage.fromData(png_bytes)
            pixmap = QPixmap.fromImage(qimg).scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_ntfy_qr.setPixmap(pixmap)

    def _copy_local_url(self):
        self._copy_to_clipboard(self.local_url, "Local link copied to clipboard!")
        self.btn_copy_url.setText("Copied!")
        self.btn_copy_url.setStyleSheet("background: #0284c7; color: #fff; border: 1px solid #38bdf8; font-weight: 700; border-radius: 6px; padding: 7px 16px; font-size: 11px;")
        QTimer.singleShot(1800, lambda: self._restore_local_copy_btn())

    def _restore_local_copy_btn(self):
        self.btn_copy_url.setText("Copy Link")
        self.btn_copy_url.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #2563eb);
                color: #ffffff;
                font-weight: 700;
                font-size: 11px;
                padding: 7px 16px;
                border: 1px solid #38bdf8;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #1d4ed8);
                border-color: #7dd3fc;
            }
        """)

    def _copy_to_clipboard(self, text: str, toast_msg: str):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            if hasattr(self.main_window, "statusBar") and self.main_window.statusBar():
                self.main_window.statusBar().showMessage(toast_msg, 2500)

    def _generate_new_secret_topic(self):
        from core.notification_dispatcher import generate_secret_ntfy_topic
        new_topic = generate_secret_ntfy_topic()
        settings = getattr(self.main_window, "app_settings", {})
        settings["ntfy_topic"] = new_topic
        if hasattr(self.main_window, "device_manager") and self.main_window.device_manager:
            self.main_window.device_manager.save_config()
        if hasattr(self.main_window, "alert_manager") and self.main_window.alert_manager:
            self.main_window.alert_manager.set_app_settings(settings)

        self.lbl_topic_value.setText(new_topic)
        self._update_ntfy_qr_image(new_topic)
        QMessageBox.information(
            self,
            "Secret Topic Generated",
            f"Your new secret ntfy channel:\n\n{new_topic}\n\nThe QR code has been regenerated! Scan directly with your phone camera."
        )

    def _test_ntfy_push(self):
        from core.notification_dispatcher import NotificationDispatcher
        settings = getattr(self.main_window, "app_settings", {})
        topic = settings.get("ntfy_topic", "").strip()
        dispatcher = NotificationDispatcher({
            "phone_notifications_enabled": True,
            "ntfy_enabled": True,
            "ntfy_topic": topic,
            "ntfy_server": settings.get("ntfy_server", "")
        })
        ok, msg = dispatcher.send_test_notification("ntfy")
        if ok:
            QMessageBox.information(self, "Notification Test", f"Test push alert dispatched to secret topic:\n'{topic}'\n\nCheck your mobile phone!")
        else:
            QMessageBox.warning(self, "Notification Test", f"Notification delivery report:\n\n{msg}")

    def _open_notifications_settings(self):
        self.accept()
        if hasattr(self.main_window, "open_settings_dialog"):
            self.main_window.open_settings_dialog()
