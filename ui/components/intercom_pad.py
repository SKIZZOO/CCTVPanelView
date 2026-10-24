import time
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider, QFrame, QComboBox, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QPainter, QBrush

from core.audio_talk_controller import AudioTalkController


class AudioVUMeter(QFrame):
    """
    Sleek Tactical Segmented LED VU Meter for live microphone audio monitoring.
    Renders 16 high-contrast glowing LED segments (Green -> Amber -> Red).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level: float = 0.0
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

            if i < 10:
                col = QColor("#38bdf8") if is_active else QColor("#0c4a6e")
            elif i < 14:
                col = QColor("#f59e0b") if is_active else QColor("#78350f")
            else:
                col = QColor("#ef4444") if is_active else QColor("#7f1d1d")

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(col))
            painter.drawRoundedRect(QRectF(x, y, seg_w, seg_h), 1.5, 1.5)

        painter.end()


class IntercomPad(QFrame):
    """
    Dedicated Two-Way Audio Intercom & Voice Broadcast Panel.
    Completely decoupled from PTZ movement controls.
    """
    close_requested = pyqtSignal()
    camera_target_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.talk_controller = AudioTalkController(self)
        self.camera_ip: Optional[str] = None
        self.stream_id: Optional[str] = None
        self.cameras_data: List[Dict[str, Any]] = []

        self.setObjectName("intercom_panel")
        self._setup_ui()
        self._connect_talk_controller()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 1. Header Card
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

        self.title_lbl = QLabel("Intercom: Camera")
        self.title_lbl.setStyleSheet("font-weight: 700; color: #38bdf8; font-size: 11px;")
        self.status_badge = QLabel("READY")
        self.status_badge.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 10px; background: rgba(148, 163, 184, 0.12); padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(148, 163, 184, 0.25);")

        h_layout.addWidget(self.title_lbl)
        h_layout.addWidget(self.status_badge)
        h_layout.addStretch()

        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip("Close intercom panel (ESC)")
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

        # 2. Camera Destination Dropdown
        lbl_cam = QLabel("TARGET CAMERA SPEAKER:")
        lbl_cam.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 0.5px;")
        layout.addWidget(lbl_cam)

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
        layout.addWidget(self.combo_camera)

        # 3. Intercom Control Card
        self.card_intercom = QFrame()
        self.card_intercom.setStyleSheet("""
            QFrame {
                background: #0b1120;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        ic_lay = QVBoxLayout(self.card_intercom)
        ic_lay.setContentsMargins(8, 8, 8, 8)
        ic_lay.setSpacing(8)

        # Detected Windows Microphone Indicator
        mic_name = self.talk_controller.get_default_device_name()
        display_mic = mic_name if len(mic_name) <= 30 else mic_name[:27] + "..."
        self.lbl_mic_dev = QLabel(f"Microphone: {display_mic}")
        self.lbl_mic_dev.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 600;")
        self.lbl_mic_dev.setToolTip(f"Windows Microphone: {mic_name}")
        ic_lay.addWidget(self.lbl_mic_dev)

        # Live Dynamic Segmented VU Level Meter
        self.vu_meter = AudioVUMeter()
        self.vu_meter.setToolTip("Real-time microphone input volume level")
        ic_lay.addWidget(self.vu_meter)

        # Large Tactical Broadcast / Push-to-Talk Button
        self.btn_talk = QPushButton("PUSH TO TALK (SPEAKER)")
        self.btn_talk.setToolTip("Broadcast microphone audio directly to camera speaker")
        self._style_talk_button(active=False)
        self.btn_talk.pressed.connect(self._on_talk_pressed)
        self.btn_talk.released.connect(self._on_talk_released)
        self.btn_talk.clicked.connect(self._on_talk_clicked)
        ic_lay.addWidget(self.btn_talk)

        # Hands-free checkbox
        self.chk_hands_free = QCheckBox("Hands-Free Mode (Toggle)")
        self.chk_hands_free.setStyleSheet("color: #94a3b8; font-size: 10px;")
        self.chk_hands_free.setToolTip("Press once to start broadcast and once again to stop")
        ic_lay.addWidget(self.chk_hands_free)

        # Speaker gain row
        gain_row = QHBoxLayout()
        gain_row.setSpacing(6)
        lbl_gain = QLabel("Speaker Volume:")
        lbl_gain.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600;")
        self.gain_val_lbl = QLabel("1.2x")
        self.gain_val_lbl.setMinimumWidth(32)
        self.gain_val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gain_val_lbl.setStyleSheet("color: #38bdf8; font-weight: 600; font-size: 10px;")
        self.slider_gain = QSlider(Qt.Orientation.Horizontal)
        self.slider_gain.setRange(10, 30)
        self.slider_gain.setValue(12)
        self.slider_gain.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #1e293b; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #2563eb; border-radius: 2px; }
            QSlider::handle:horizontal {
                background: #3b82f6;
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 4px;
            }
        """)
        self.slider_gain.valueChanged.connect(self._on_gain_changed)

        gain_row.addWidget(lbl_gain)
        gain_row.addWidget(self.slider_gain)
        gain_row.addWidget(self.gain_val_lbl)
        ic_lay.addLayout(gain_row)

        layout.addWidget(self.card_intercom)

    def _connect_talk_controller(self):
        self.talk_controller.state_changed.connect(self._on_talk_state_changed)
        self.talk_controller.audio_level_updated.connect(self.vu_meter.set_level)
        self.talk_controller.error_occurred.connect(self._on_talk_error)

    def populate_cameras(self, cameras_list: List[Dict[str, Any]]):
        self.cameras_data = cameras_list or []
        self.combo_camera.blockSignals(True)
        self.combo_camera.clear()

        preferred_idx = 0
        current_count = 0

        for cam in self.cameras_data:
            cam_name = cam.get("name", "Camera")
            cam_ip = cam.get("ip", "")
            streams = cam.get("streams", [])

            for s in streams:
                s_id = s.get("id", "")
                s_name = s.get("name", "Main")
                is_ptz = s.get("is_ptz", False)
                tag = "[PTZ]" if is_ptz else "[FIX]"
                label = f"{cam_name} ({s_name}) {tag}"
                self.combo_camera.addItem(label, {
                    "camera_ip": cam_ip,
                    "stream_id": s_id,
                    "stream_name": f"{cam_name} ({s_name})",
                    "username": cam.get("username", "admin"),
                    "password": cam.get("password", ""),
                    "rtsp_port": cam.get("port", 554),
                    "stream_path": f"/live/ch0{s.get('channel', 0)}_0"
                })
                current_count += 1

        if self.combo_camera.count() > 0:
            self.combo_camera.setCurrentIndex(preferred_idx)
            self._on_camera_dropdown_changed(preferred_idx)

        self.combo_camera.blockSignals(False)

    def sync_to_stream(self, camera_ip: str, stream_id: str):
        if not camera_ip:
            return
        self.camera_ip = camera_ip
        self.stream_id = stream_id

        self.combo_camera.blockSignals(True)
        for i in range(self.combo_camera.count()):
            d = self.combo_camera.itemData(i)
            if d and d.get("camera_ip") == camera_ip:
                if stream_id and d.get("stream_id") == stream_id:
                    self.combo_camera.setCurrentIndex(i)
                    break
                elif not stream_id:
                    self.combo_camera.setCurrentIndex(i)
                    break
        self.combo_camera.blockSignals(False)

        current_data = self.combo_camera.currentData() or {}
        s_name = current_data.get("stream_name", camera_ip)
        disp_title = s_name if len(s_name) <= 20 else s_name[:18] + ".."
        self.title_lbl.setText(f"Interfon: {disp_title}")

    def clear_camera(self):
        if self.talk_controller and self.talk_controller.is_broadcasting:
            self.talk_controller.stop_broadcast()
        self.camera_ip = None
        self.stream_id = None
        self.status_badge.setText("NO SIGNAL")
        self.status_badge.setStyleSheet("color: #94a3b8; font-size: 10px;")

    def _style_talk_button(self, active: bool):
        if active:
            self.btn_talk.setText("BROADCASTING (SPEAKER LIVE)")
            self.btn_talk.setStyleSheet("""
                QPushButton {
                    background: #dc2626;
                    color: #ffffff;
                    font-weight: 700;
                    font-size: 11px;
                    letter-spacing: 0.5px;
                    border: 1px solid #ef4444;
                    border-radius: 4px;
                    min-height: 38px;
                    padding: 6px;
                }
                QPushButton:hover { background: #b91c1c; }
            """)
        else:
            self.btn_talk.setText("PUSH TO TALK (SPEAKER)")
            self.btn_talk.setStyleSheet("""
                QPushButton {
                    background: #1e293b;
                    color: #38bdf8;
                    font-weight: 700;
                    font-size: 11px;
                    letter-spacing: 0.5px;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    min-height: 38px;
                    padding: 6px;
                }
                QPushButton:hover {
                    background: #2563eb;
                    color: #ffffff;
                    border-color: #3b82f6;
                }
            """)

    def _on_talk_pressed(self):
        if self.chk_hands_free.isChecked():
            return
        self._start_talking()

    def _on_talk_released(self):
        if self.chk_hands_free.isChecked():
            return
        self._stop_talking()

    def _on_talk_clicked(self):
        if not self.chk_hands_free.isChecked():
            return
        if self.talk_controller.is_broadcasting:
            self._stop_talking()
        else:
            self._start_talking()

    def _start_talking(self):
        curr_data = self.combo_camera.currentData() or {}
        ip = curr_data.get("camera_ip", self.camera_ip or "")
        user = curr_data.get("username", "admin")
        pwd = curr_data.get("password", "")
        port = curr_data.get("rtsp_port", 554)
        path = curr_data.get("stream_path", "/live/ch00_0")

        if not ip:
            self.status_badge.setText("NO CAMERA")
            return

        self._style_talk_button(active=True)
        self.status_badge.setText("CONNECTING...")
        self.status_badge.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 10px;")
        self.talk_controller.start_broadcast(ip, user, pwd, rtsp_port=port, stream_path=path)

    def _stop_talking(self):
        self._style_talk_button(active=False)
        self.talk_controller.stop_broadcast()

    def _on_talk_state_changed(self, is_broadcasting: bool, status_msg: str):
        if is_broadcasting:
            self.status_badge.setText("BROADCASTING")
            self.status_badge.setStyleSheet("color: #ef4444; font-weight: 900; font-size: 10px; background: rgba(239, 68, 68, 0.15); padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(239, 68, 68, 0.3);")
            self._style_talk_button(active=True)
        else:
            self.status_badge.setText("READY")
            self.status_badge.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 10px; background: rgba(148, 163, 184, 0.12); padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(148, 163, 184, 0.25);")
            self._style_talk_button(active=False)

    def _on_talk_error(self, err_msg: str):
        self.status_badge.setText("AUDIO ERROR")
        self.status_badge.setStyleSheet("color: #f87171; font-weight: bold; font-size: 10px;")
        self._style_talk_button(active=False)

    def _on_gain_changed(self, val: int):
        gain = float(val) / 10.0
        self.gain_val_lbl.setText(f"{gain:.1f}x")
        self.talk_controller.set_gain(gain)

    def _on_camera_dropdown_changed(self, index: int):
        data = self.combo_camera.itemData(index)
        if not data:
            return
        cam_ip = data.get("camera_ip", "")
        s_id = data.get("stream_id", "")
        s_name = data.get("stream_name", cam_ip)
        self.camera_ip = cam_ip
        self.stream_id = s_id
        disp_title = s_name if len(s_name) <= 20 else s_name[:18] + ".."
        self.title_lbl.setText(f"Intercom: {disp_title}")
        self.camera_target_changed.emit(cam_ip, s_id)
