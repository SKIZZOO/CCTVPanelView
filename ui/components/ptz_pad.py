import time
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QSlider, QRadioButton, QButtonGroup, QFrame, QComboBox,
    QCheckBox, QGraphicsDropShadowEffect, QProgressBar, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRectF
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QLinearGradient

from core.ptz_controller import PTZController
from core.audio_talk_controller import AudioTalkController


class AudioVUMeter(QFrame):
    """
    Sleek Tactical Segmented LED VU Meter for live microphone audio monitoring.
    Renders 16 high-contrast glowing LED segments (Green -> Yellow -> Amber -> Red).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level: float = 0.0  # 0.0 to 1.0
        self.num_segments: int = 16
        self.setFixedHeight(14)
        self.setStyleSheet("background: #060b13; border: 1px solid #1e293b; border-radius: 4px;")

    def set_level(self, level: float):
        self.level = max(0.0, min(1.0, float(level)))
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        num_segments = self.num_segments
        gap = 2
        seg_w = max(2, (w - (num_segments + 1) * gap) / num_segments)
        seg_h = h - 6
        active_count = int(round(self.level * num_segments))

        for i in range(num_segments):
            x = gap + i * (seg_w + gap)
            y = 3
            is_active = i < active_count

            # Determine segment color band
            if i < 10:
                # Cyan band
                col = QColor("#38bdf8") if is_active else QColor("#0c4a6e")
            elif i < 14:
                # Amber band
                col = QColor("#f59e0b") if is_active else QColor("#78350f")
            else:
                # Red peak band
                col = QColor("#ef4444") if is_active else QColor("#7f1d1d")

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(col))
            painter.drawRoundedRect(QRectF(x, y, seg_w, seg_h), 1.5, 1.5)

        painter.end()


class PTZPad(QFrame):
    """
    Advanced Tactical PTZ Control & Two-Way Intercom Pad (Agent DVR / iSpy Standard).
    
    Features:
    - Independent Dual-Engine: Hardware Motor PTZ (ONVIF/CGI) vs Digital Viewport Zoom/Pan.
    - Two-Way Audio Intercom: Broadcasts Windows default mic live to camera speaker via RTSP backchannel.
    - Real-Time Animated Tactical VU Meter: Dynamic visual audio feedback while speaking.
    - Integrated Camera & Lens Target Selector with instant active stream sync.
    - Tactical 8-Way HUD Joystick: Press-and-hold continuous movement + calibrated 350ms tap-to-nudge.
    - Fixed-Lens Intelligent Detection & 1-Click Redirect to PTZ Zoom Lens.
    - Speed Regulator (1 to 10) & Volume Gain Slider (1.0x to 3.0x).
    - Preset Recall & Storage (P1-P4) with visual confirmation status.
    - Automated Patrol / Touring between presets.
    """
    ptz_command_issued = pyqtSignal(str, int)     # direction, speed
    ptz_zoom_issued = pyqtSignal(float)           # delta (+0.25 / -0.25)
    ptz_stop_issued = pyqtSignal()
    preset_goto_issued = pyqtSignal(int)
    preset_save_issued = pyqtSignal(int)
    patrol_step_issued = pyqtSignal(int)
    reset_zoom_issued = pyqtSignal()
    camera_target_changed = pyqtSignal(str, str)  # camera_ip, stream_id
    close_requested = pyqtSignal()
    settings_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller: Optional[PTZController] = None
        self.camera_ip: Optional[str] = None
        self.stream_id: Optional[str] = None
        self.current_speed: int = 5
        self.is_motor_mode: bool = True  # True: Hardware Motor, False: Digital Viewport
        self.cameras_data: List[Dict[str, Any]] = []

        # Press timing for tap-vs-hold detection
        self._press_start_time: float = 0.0
        self._active_direction: Optional[str] = None

        # Digital pan continuous timer
        self._digital_pan_timer = QTimer(self)
        self._digital_pan_timer.setInterval(60)
        self._digital_pan_timer.timeout.connect(self._on_digital_pan_tick)

        # Auto-patrol timer
        self._patrol_timer = QTimer(self)
        self._patrol_timer.setInterval(4500)
        self._patrol_timer.timeout.connect(self._on_patrol_tick)
        self._patrol_index = 0

        self.setObjectName("ptz_panel")
        self._setup_ui()

    # =========================================================================
    # PUBLIC API & SYNC METHODS
    # =========================================================================

    def populate_cameras(self, cameras_list: List[Dict[str, Any]]):
        """Populates the camera dropdown with available cameras and streams."""
        self.cameras_data = cameras_list or []
        self.combo_camera.blockSignals(True)
        self.combo_camera.clear()

        preferred_idx = 0
        current_item_count = 0

        for cam in self.cameras_data:
            cam_name = cam.get("name", "Camera")
            cam_ip = cam.get("ip", "")
            streams = cam.get("streams", [])

            if cam.get("is_dual_lens") and len(streams) >= 2:
                for s in streams:
                    s_id = s.get("id", "")
                    s_name = s.get("name", "")
                    is_ptz = s.get("is_ptz", False)
                    type_str = "PTZ Zoom" if is_ptz else "Panoramă Fixă"
                    tag = "[PTZ]" if is_ptz else "[FIX]"
                    label = f"{cam_name} - {s_name} {tag}"
                    self.combo_camera.addItem(label, {
                        "camera_ip": cam_ip,
                        "stream_id": s_id,
                        "stream_name": f"{cam_name} ({s_name})",
                        "username": cam.get("username", "admin"),
                        "password": cam.get("password", ""),
                        "onvif_port": cam.get("onvif_port", 8899),
                        "rtsp_port": cam.get("port", 554),
                        "stream_path": f"/live/ch0{s.get('channel', 0)}_0",
                        "is_ptz": is_ptz,
                        "channel": s.get("channel", 0)
                    })
                    if is_ptz and preferred_idx == 0:
                        preferred_idx = current_item_count
                    current_item_count += 1
            else:
                for s in streams:
                    s_id = s.get("id", "")
                    s_name = s.get("name", "Main")
                    is_ptz = s.get("is_ptz", True)
                    tag = "[PTZ]" if is_ptz else "[FIX]"
                    label = f"{cam_name} ({cam_ip}) {tag}"
                    self.combo_camera.addItem(label, {
                        "camera_ip": cam_ip,
                        "stream_id": s_id,
                        "stream_name": cam_name,
                        "username": cam.get("username", "admin"),
                        "password": cam.get("password", ""),
                        "onvif_port": cam.get("onvif_port", 8899),
                        "rtsp_port": cam.get("port", 554),
                        "stream_path": f"/live/ch0{s.get('channel', 0)}_0",
                        "is_ptz": is_ptz,
                        "channel": s.get("channel", 0)
                    })
                    if is_ptz and preferred_idx == 0:
                        preferred_idx = current_item_count
                    current_item_count += 1

        if self.combo_camera.count() > 0:
            self.combo_camera.setCurrentIndex(preferred_idx)
            self._on_camera_dropdown_changed(preferred_idx)

        self.combo_camera.blockSignals(False)

    def set_camera(self, camera_ip: str, username: str = "admin", password: str = "",
                   port: int = 8899, stream_id: str = "", stream_name: str = ""):
        """Attaches PTZController to camera and updates UI status."""
        if self.controller and self.controller.is_patrolling():
            self.controller.stop_patrol()

        self.camera_ip = str(camera_ip).strip()
        self.stream_id = stream_id or self.stream_id
        p_val = int(port) if (1 <= int(port) <= 65535) else 8899

        self.controller = PTZController(self.camera_ip, username, password, port=p_val)
        if stream_id and ("lens2" in stream_id.lower() or "ch01" in stream_id.lower()):
            self.controller.set_profile("profile_1")
        else:
            self.controller.set_profile("profile_0")

        disp_title = stream_name or camera_ip or "Camera"
        if len(disp_title) > 20:
            disp_title = disp_title[:18] + ".."
        self.title_lbl.setText(f"PTZ: {disp_title}")
        self.title_lbl.setToolTip(f"Active camera: {stream_name or camera_ip} ({camera_ip})")
        self.status_badge.setText("● LIVE")
        self.status_badge.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 10px; background: rgba(56, 189, 248, 0.12); padding: 2px 5px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.3);")
        self.btn_patrol.setEnabled(True)
        self.btn_patrol.setText("Auto Patrol (P1-P4)")
        self.btn_patrol.setStyleSheet("")
        self.setEnabled(True)

        self._check_fixed_lens_warning()

    def sync_to_stream(self, camera_ip: str, stream_id: str = ""):
        """Called when a video tile is clicked in main window to keep PTZ target synchronized."""
        if not camera_ip:
            return

        self.combo_camera.blockSignals(True)
        for i in range(self.combo_camera.count()):
            data = self.combo_camera.itemData(i)
            if data and data.get("camera_ip") == camera_ip:
                if stream_id and data.get("stream_id") == stream_id:
                    self.combo_camera.setCurrentIndex(i)
                    break
                elif not stream_id:
                    self.combo_camera.setCurrentIndex(i)
                    break
        self.combo_camera.blockSignals(False)

        current_data = self.combo_camera.currentData() or {}
        user = current_data.get("username", "admin")
        pwd = current_data.get("password", "")
        port = current_data.get("onvif_port", 8899)
        s_name = current_data.get("stream_name", camera_ip)
        self.set_camera(camera_ip, user, pwd, port=port, stream_id=stream_id, stream_name=s_name)

    def clear_camera(self):
        """Clears active camera binding."""
        if self.controller and self.controller.is_patrolling():
            self.controller.stop_patrol()
        self.controller = None
        self.camera_ip = None
        self.stream_id = None
        self.status_badge.setText("● DISCONNECTED")
        self.status_badge.setStyleSheet("color: #94a3b8; font-size: 10px;")
        self.setEnabled(False)

    def is_digital_mode(self) -> bool:
        """Returns True if user currently has Digital Viewport mode selected."""
        return not self.is_motor_mode

    def is_settings_expanded(self) -> bool:
        """Returns True if advanced settings container is currently visible."""
        return self.settings_container.isVisible() if hasattr(self, "settings_container") else False

    def toggle_settings(self):
        """Toggles the visibility of advanced settings, camera selector, and intercom."""
        self.set_settings_expanded(not self.is_settings_expanded())

    def set_settings_expanded(self, expanded: bool):
        """Expands or collapses the advanced settings container and updates button labels."""
        if hasattr(self, "settings_container"):
            self.settings_container.setVisible(expanded)
        if hasattr(self, "btn_toggle_settings"):
            self.btn_toggle_settings.setChecked(expanded)
            self.btn_toggle_settings.setText("Settings ▲" if expanded else "Settings ▼")
        if hasattr(self, "btn_toggle_settings_bottom"):
            self.btn_toggle_settings_bottom.setChecked(expanded)
            self.btn_toggle_settings_bottom.setText("Hide Settings ▲" if expanded else "Motion Settings ▼")
        self.settings_toggled.emit(expanded)

    # =========================================================================
    # UI SETUP & LAYOUT
    # =========================================================================

    def _setup_ui(self):
        # Top-level ScrollArea container so the panel is comfortably scrollable on any resolution
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # 1. Tactical Header Card
        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(6, 4, 6, 4)
        h_layout.setSpacing(6)
        self.title_lbl = QLabel("PTZ: Camera")
        self.title_lbl.setStyleSheet("font-weight: 700; color: #38bdf8; font-size: 11px;")
        self.status_badge = QLabel("● LIVE")
        self.status_badge.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 10px; background: rgba(56, 189, 248, 0.12); padding: 2px 5px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.3);")
        h_layout.addWidget(self.title_lbl)
        h_layout.addWidget(self.status_badge)
        h_layout.addStretch()

        self.btn_toggle_settings = QPushButton("Settings ▼")
        self.btn_toggle_settings.setToolTip("Show/Hide advanced settings, speed, presets, and controls")
        self.btn_toggle_settings.setCheckable(True)
        self.btn_toggle_settings.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #2563eb;
                color: #ffffff;
                border-color: #3b82f6;
            }
            QPushButton:checked {
                background: #2563eb;
                color: #ffffff;
                border-color: #60a5fa;
            }
        """)
        self.btn_toggle_settings.clicked.connect(self.toggle_settings)
        h_layout.addWidget(self.btn_toggle_settings)

        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip("Close panel (ESC)")
        self.btn_close.setFixedSize(18, 18)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #94a3b8;
                border: none;
                border-radius: 9px;
                font-size: 10px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #ef4444;
                color: #ffffff;
            }
        """)
        self.btn_close.clicked.connect(self.close_requested.emit)
        h_layout.addWidget(self.btn_close)
        layout.addWidget(header_card)

        # 2. Modern Tactical 8-Way HUD Joystick Cluster
        self.joystick_frame = QFrame()
        self.joystick_frame.setObjectName("joystick_frame")
        self.joystick_frame.setStyleSheet("""
            QFrame#joystick_frame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f1624, stop:1 #080d16);
                border: 1px solid #1e293b;
                border-radius: 10px;
                padding: 4px;
            }
        """)
        grid = QGridLayout(self.joystick_frame)
        grid.setSpacing(4)
        grid.setContentsMargins(4, 4, 4, 4)

        cardinal_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a2333, stop:1 #0f1622);
                color: #38bdf8;
                font-weight: 800;
                font-size: 18px;
                border: 1px solid #283955;
                border-top: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 8px;
                min-height: 44px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);
                border: 1px solid #60a5fa;
                color: #ffffff;
            }
            QPushButton:pressed {
                background: #1e40af;
                color: #ffffff;
            }
        """

        diag_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #131a26, stop:1 #0c111a);
                color: #cbd5e1;
                font-weight: 700;
                font-size: 17px;
                border: 1px solid #1e2a3c;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                min-height: 44px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1d4ed8, stop:1 #1e3a8a);
                border: 1px solid #38bdf8;
                color: #ffffff;
            }
            QPushButton:pressed {
                background: #1e3a8a;
                color: #ffffff;
            }
        """

        stop_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(220, 38, 38, 0.28), stop:1 rgba(153, 27, 27, 0.38));
                color: #fca5a5;
                font-weight: 900;
                font-size: 11px;
                letter-spacing: 1.2px;
                border: 1px solid rgba(239, 68, 68, 0.55);
                border-top: 1px solid rgba(248, 113, 113, 0.4);
                border-radius: 8px;
                min-height: 44px;
            }
            QPushButton:hover {
                background: #dc2626;
                border-color: #ef4444;
                color: #ffffff;
            }
            QPushButton:pressed {
                background: #991b1b;
                color: #ffffff;
            }
        """

        self.btn_ul = self._create_dir_btn("↖", "up_left", diag_style)
        self.btn_u  = self._create_dir_btn("▲", "up", cardinal_style)
        self.btn_ur = self._create_dir_btn("↗", "up_right", diag_style)
        self.btn_l  = self._create_dir_btn("◀", "left", cardinal_style)

        # Center Emergency Stop Button
        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setToolTip("Emergency Stop PTZ Movement")
        self.btn_stop.setStyleSheet(stop_style)
        self.btn_stop.clicked.connect(self._stop_ptz)

        self.btn_r  = self._create_dir_btn("▶", "right", cardinal_style)
        self.btn_dl = self._create_dir_btn("↙", "down_left", diag_style)
        self.btn_d  = self._create_dir_btn("▼", "down", cardinal_style)
        self.btn_dr = self._create_dir_btn("↘", "down_right", diag_style)

        grid.addWidget(self.btn_ul, 0, 0)
        grid.addWidget(self.btn_u,  0, 1)
        grid.addWidget(self.btn_ur, 0, 2)
        grid.addWidget(self.btn_l,  1, 0)
        grid.addWidget(self.btn_stop, 1, 1)
        grid.addWidget(self.btn_r,  1, 2)
        grid.addWidget(self.btn_dl, 2, 0)
        grid.addWidget(self.btn_d,  2, 1)
        grid.addWidget(self.btn_dr, 2, 2)

        layout.addWidget(self.joystick_frame)

        # 3. Zoom & Viewport Reset Controls
        zoom_row = QHBoxLayout()
        zoom_row.setSpacing(4)
        zoom_btn_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #161d2c, stop:1 #0f1420);
                color: #cbd5e1;
                font-weight: 700;
                font-size: 11px;
                border: 1px solid #202b3e;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                min-height: 30px;
                padding: 4px 6px;
            }
            QPushButton:hover {
                background: #2563eb;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """
        self.btn_zoom_out = QPushButton("Zoom -")
        self.btn_reset_zoom = QPushButton("Reset 1.0x")
        self.btn_zoom_in = QPushButton("Zoom +")

        self.btn_zoom_out.setStyleSheet(zoom_btn_style)
        self.btn_zoom_in.setStyleSheet(zoom_btn_style)
        self.btn_reset_zoom.setStyleSheet(zoom_btn_style.replace("#cbd5e1", "#38bdf8"))
        self.btn_reset_zoom.setToolTip("Resetează zoom-ul digital la imaginea completă inițială (1.0x)")

        self.btn_zoom_in.clicked.connect(self._zoom_in)
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        self.btn_reset_zoom.clicked.connect(self._reset_zoom)

        zoom_row.addWidget(self.btn_zoom_out)
        zoom_row.addWidget(self.btn_reset_zoom)
        zoom_row.addWidget(self.btn_zoom_in)
        layout.addLayout(zoom_row)

        # Quick Toggle Bar for Advanced Options
        self.btn_toggle_settings_bottom = QPushButton("Motion Settings ▼")
        self.btn_toggle_settings_bottom.setCheckable(True)
        self.btn_toggle_settings_bottom.setStyleSheet("""
            QPushButton {
                background: #101522;
                color: #94a3b8;
                border: 1px solid #1c2638;
                border-radius: 6px;
                padding: 5px;
                font-size: 11px;
                font-weight: 600;
                min-height: 28px;
            }
            QPushButton:hover {
                background: #172033;
                color: #38bdf8;
                border-color: #38bdf8;
            }
            QPushButton:checked {
                background: #1d2538;
                color: #38bdf8;
                border-color: #38bdf8;
            }
        """)
        self.btn_toggle_settings_bottom.clicked.connect(self.toggle_settings)
        layout.addWidget(self.btn_toggle_settings_bottom)

        # =====================================================================
        # 4. COLLAPSIBLE ADVANCED SETTINGS & INTERCOM CONTAINER
        # =====================================================================
        self.settings_container = QWidget()
        settings_lay = QVBoxLayout(self.settings_container)
        settings_lay.setContentsMargins(0, 2, 0, 0)
        settings_lay.setSpacing(8)

        # Camera Target Selector Dropdown
        cam_sel_lbl = QLabel("SELECTED CAMERA / LENS:")
        cam_sel_lbl.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 0.5px;")
        settings_lay.addWidget(cam_sel_lbl)

        self.combo_camera = QComboBox()
        self.combo_camera.setStyleSheet("""
            QComboBox {
                background: #1e293b;
                color: #f1f5f9;
                font-weight: 600;
                font-size: 11px;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 5px 10px;
                min-height: 24px;
            }
            QComboBox:hover { border-color: #3b82f6; }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid #334155;
            }
            QComboBox QAbstractItemView {
                background: #0f172a;
                color: #f1f5f9;
                border: 1px solid #334155;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
                outline: none;
            }
        """)
        self.combo_camera.currentIndexChanged.connect(self._on_camera_dropdown_changed)
        settings_lay.addWidget(self.combo_camera)

        # Fixed Lens Warning Banner
        self.card_fixed_lens = QFrame()
        self.card_fixed_lens.setStyleSheet("""
            QFrame {
                background: rgba(245, 158, 11, 0.12);
                border: 1px solid rgba(245, 158, 11, 0.35);
                border-radius: 4px;
                padding: 4px;
            }
        """)
        fixed_layout = QVBoxLayout(self.card_fixed_lens)
        fixed_layout.setContentsMargins(6, 6, 6, 6)
        fixed_layout.setSpacing(4)
        lbl_fixed_info = QLabel("Fixed Lens: Lens 2 is panoramic fixed.\nLens 1 controls the motorized physical PTZ.")
        lbl_fixed_info.setStyleSheet("color: #fcd34d; font-size: 10px; font-weight: 600; background: transparent; border: none;")
        self.btn_switch_to_ptz = QPushButton("Switch to Lens 1 (PTZ Zoom)")
        self.btn_switch_to_ptz.setStyleSheet("""
            QPushButton {
                background: #d97706;
                color: #ffffff;
                font-weight: 600;
                font-size: 10px;
                border: none;
                border-radius: 4px;
                padding: 5px 8px;
            }
            QPushButton:hover { background: #b45309; }
        """)
        self.btn_switch_to_ptz.clicked.connect(self._switch_to_lens1_ptz)
        fixed_layout.addWidget(lbl_fixed_info)
        fixed_layout.addWidget(self.btn_switch_to_ptz)
        self.card_fixed_lens.hide()
        settings_lay.addWidget(self.card_fixed_lens)

        # Mode Switcher (Hardware Motor vs Digital Viewport)
        mode_box = QHBoxLayout()
        mode_box.setSpacing(4)
        self.btn_mode_motor = QPushButton("Hardware PTZ")
        self.btn_mode_digital = QPushButton("Digital Pan && Zoom")
        self.btn_mode_motor.setCheckable(True)
        self.btn_mode_digital.setCheckable(True)
        self.btn_mode_motor.setChecked(True)

        mode_style = """
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 5px 8px;
            }
            QPushButton:checked {
                background: #2563eb;
                color: #ffffff;
                border: 1px solid #3b82f6;
            }
            QPushButton:hover:!checked { background: #334155; color: #f1f5f9; }
        """
        self.btn_mode_motor.setStyleSheet(mode_style)
        self.btn_mode_digital.setStyleSheet(mode_style)

        self.btn_mode_motor.clicked.connect(lambda: self._set_control_mode(motor=True))
        self.btn_mode_digital.clicked.connect(lambda: self._set_control_mode(motor=False))
        mode_box.addWidget(self.btn_mode_motor)
        mode_box.addWidget(self.btn_mode_digital)
        settings_lay.addLayout(mode_box)

        self.lbl_mode_desc = QLabel("Controls physical camera pan/tilt motors via ONVIF.")
        self.lbl_mode_desc.setStyleSheet("color: #64748b; font-size: 9px;")
        settings_lay.addWidget(self.lbl_mode_desc)

        # Speed Regulator Slider
        speed_row = QHBoxLayout()
        speed_row.setSpacing(6)
        speed_lbl = QLabel("Speed:")
        speed_lbl.setFixedWidth(40)
        speed_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        self.speed_val_lbl = QLabel("5 / 10")
        self.speed_val_lbl.setFixedWidth(46)
        self.speed_val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speed_val_lbl.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 11px; background: rgba(56, 189, 248, 0.1); padding: 2px 2px; border-radius: 4px;")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        self.speed_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #1e293b; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #2563eb; border-radius: 2px; }
            QSlider::handle:horizontal {
                background: #3b82f6;
                border: 1px solid #ffffff;
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 4px;
            }
        """)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        speed_row.addWidget(speed_lbl)
        speed_row.addWidget(self.speed_slider)
        speed_row.addWidget(self.speed_val_lbl)
        settings_lay.addLayout(speed_row)

        self.chk_tap_nudge = QCheckBox("Tap-to-Nudge (Short Step)")
        self.chk_tap_nudge.setChecked(True)
        self.chk_tap_nudge.setStyleSheet("color: #94a3b8; font-size: 10px;")
        self.chk_tap_nudge.setToolTip("A short click sends a 350ms pulse; hold down to rotate continuously")
        settings_lay.addWidget(self.chk_tap_nudge)

        # Presets (1 to 4)
        preset_header = QHBoxLayout()
        preset_header.setSpacing(6)
        p_title = QLabel("PRESETS")
        p_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        self.radio_goto = QRadioButton("Go To")
        self.radio_goto.setChecked(True)
        self.radio_save = QRadioButton("Save")
        self.radio_goto.setStyleSheet("font-size: 10px; color: #cbd5e1; spacing: 3px;")
        self.radio_save.setStyleSheet("font-size: 10px; color: #cbd5e1; spacing: 3px;")
        preset_header.addWidget(p_title)
        preset_header.addStretch()
        preset_header.addWidget(self.radio_goto)
        preset_header.addWidget(self.radio_save)
        settings_lay.addLayout(preset_header)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(4)
        for i in range(1, 5):
            btn = QPushButton(f"P{i}")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    color: #38bdf8;
                    font-weight: 700;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    padding: 5px 6px;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #2563eb; color: #ffffff; border-color: #3b82f6; }
                QPushButton:pressed { background-color: #1d4ed8; }
            """)
            btn.clicked.connect(lambda checked, idx=i: self._on_preset_clicked(idx))
            preset_row.addWidget(btn)
        settings_lay.addLayout(preset_row)

        # Auto-Patrol Button
        self.btn_patrol = QPushButton("Auto Patrol (P1 -> P4)")
        self.btn_patrol.setToolTip("Automatically cycles camera between saved presets 1 to 4")
        self.btn_patrol.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #38bdf8;
                font-weight: 600;
                font-size: 11px;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover { background: #2563eb; color: #ffffff; border-color: #3b82f6; }
        """)
        self.btn_patrol.clicked.connect(self._toggle_patrol)
        settings_lay.addWidget(self.btn_patrol)

        # Hidden by default - reveals on clicking "Settings"
        self.settings_container.hide()
        layout.addWidget(self.settings_container)

        # Set scroll container into main layout
        scroll.setWidget(container)
        self.scroll_area = scroll
        self.scroll_container = container
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    # =========================================================================
    # EVENT HANDLERS & INTERNAL LOGIC
    # =========================================================================

    def _create_dir_btn(self, icon_text: str, direction: str, style: str) -> QPushButton:
        btn = QPushButton(icon_text)
        btn.setStyleSheet(style)
        btn.pressed.connect(lambda: self._on_dir_pressed(direction))
        btn.released.connect(lambda: self._on_dir_released(direction))
        return btn

    def _set_control_mode(self, motor: bool):
        self.is_motor_mode = motor
        self.btn_mode_motor.setChecked(motor)
        self.btn_mode_digital.setChecked(not motor)

        if motor:
            self.lbl_mode_desc.setText("Controls physical camera pan/tilt motors via ONVIF.")
            self.btn_reset_zoom.setEnabled(False)
        else:
            self.lbl_mode_desc.setText("Digital Viewport: Crop & Pan within active live video frame.")
            self.btn_reset_zoom.setEnabled(True)

    def _on_camera_dropdown_changed(self, index: int):
        data = self.combo_camera.itemData(index)
        if not data:
            return

        cam_ip = data.get("camera_ip", "")
        s_id = data.get("stream_id", "")
        s_name = data.get("stream_name", cam_ip)
        user = data.get("username", "admin")
        pwd = data.get("password", "")
        port = data.get("onvif_port", 8899)

        self.set_camera(cam_ip, user, pwd, port=port, stream_id=s_id, stream_name=s_name)
        self.camera_target_changed.emit(cam_ip, s_id)

    def _switch_to_lens1_ptz(self):
        """1-Click switch to Lens 1 (the PTZ Zoom lens) on Fata Dual-Lens camera."""
        for i in range(self.combo_camera.count()):
            d = self.combo_camera.itemData(i)
            if d and d.get("is_ptz") and ("lens1" in str(d.get("stream_id", "")).lower() or "45" in str(d.get("camera_ip", ""))):
                self.combo_camera.setCurrentIndex(i)
                break

    def _check_fixed_lens_warning(self):
        curr_data = self.combo_camera.currentData() or {}
        is_ptz = curr_data.get("is_ptz", True)
        if not is_ptz:
            self.card_fixed_lens.show()
        else:
            self.card_fixed_lens.hide()

    def _on_dir_pressed(self, direction: str):
        self._press_start_time = time.time()
        self._active_direction = direction

        if self.is_motor_mode:
            if self.controller:
                self.controller.move(direction, self.current_speed)
        else:
            self._digital_pan_timer.start()

        self.ptz_command_issued.emit(direction, self.current_speed)

    def _on_dir_released(self, direction: str):
        elapsed = time.time() - self._press_start_time
        self._digital_pan_timer.stop()

        if self.is_motor_mode:
            if self.chk_tap_nudge.isChecked() and elapsed < 0.22:
                if self.controller:
                    self.controller.step_move(direction, self.current_speed, duration_sec=0.35)
            else:
                self._stop_ptz()
        else:
            if elapsed < 0.22:
                self.ptz_command_issued.emit(direction, self.current_speed)

        self._active_direction = None

    def _on_digital_pan_tick(self):
        if self._active_direction:
            self.ptz_command_issued.emit(self._active_direction, self.current_speed)

    def _zoom_in(self):
        if self.is_motor_mode:
            if self.controller:
                self.controller.zoom_in()
        else:
            self.ptz_zoom_issued.emit(0.25)

    def _zoom_out(self):
        if self.is_motor_mode:
            if self.controller:
                self.controller.zoom_out()
        else:
            self.ptz_zoom_issued.emit(-0.25)

    def _reset_zoom(self):
        self.reset_zoom_issued.emit()

    def _stop_ptz(self):
        self._digital_pan_timer.stop()
        self.ptz_stop_issued.emit()
        if self.controller:
            self.controller.stop()

    def _on_speed_changed(self, val: int):
        self.current_speed = val
        self.speed_val_lbl.setText(f"{val} / 10")
        if self.controller:
            self.controller.speed = val

    def _on_preset_clicked(self, preset_idx: int):
        if self.radio_save.isChecked():
            self.preset_save_issued.emit(preset_idx)
            if self.is_motor_mode and self.controller:
                self.controller.set_preset(preset_idx)
        else:
            self.preset_goto_issued.emit(preset_idx)
            if self.is_motor_mode and self.controller:
                self.controller.goto_preset(preset_idx)

    def _toggle_patrol(self):
        if self._patrol_timer.isActive():
            self._patrol_timer.stop()
            if self.controller and self.controller.is_patrolling():
                self.controller.stop_patrol()
            self.btn_patrol.setText("Auto Patrol (P1 -> P4)")
            self.btn_patrol.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e293b, stop:1 #0f172a);
                    color: #38bdf8;
                    font-weight: bold;
                    font-size: 11px;
                    border: 1px solid #0369a1;
                    border-radius: 6px;
                    padding: 6px;
                }
            """)
        else:
            self._patrol_index = 1
            self.preset_goto_issued.emit(self._patrol_index)
            self._patrol_timer.start()
            if self.is_motor_mode and self.controller:
                self.controller.start_patrol([1, 2, 3, 4], interval_sec=5.0)
            self.btn_patrol.setText("Stop Patrol")
            self.btn_patrol.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0284c7, stop:1 #0369a1);
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 11px;
                    border: 1px solid #00e5ff;
                    border-radius: 6px;
                    padding: 6px;
                }
            """)

    def _on_patrol_tick(self):
        self._patrol_index = (self._patrol_index % 4) + 1
        self.preset_goto_issued.emit(self._patrol_index)
        self.patrol_step_issued.emit(self._patrol_index)
