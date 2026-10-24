import os
from datetime import datetime
from typing import Optional
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QCursor


class AlertCardWidget(QFrame):
    """
    Sleek, modern CCTV incident alert card.
    Features:
    - High-visibility detection badge (PERSON 94% / ANIMAL / VEHICLE)
    - Camera name and lens indicator pill
    - Crisp timestamp and 1-click [X] dismiss button
    - Optional scene AI description quote bar
    - 16:9 snapshot thumbnail preview (clickable)
    - Real-time recording status indicator (Recording vs Ready)
    - 1-Click "Play Clip" button (opens in-client dual-version player)
    - 1-Click "Snapshot" button
    """
    delete_requested = pyqtSignal(str)  # Emits alert_id when dismissed

    def __init__(self, alert_data: dict, parent=None):
        super().__init__(parent)
        self.alert_data = alert_data
        self.setObjectName("alert_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Tooltip for forensic identification without cluttering UI
        fn = self.alert_data.get("filename", "")
        if fn:
            self.setToolTip(f"Incident File: {fn}\nID: {self.alert_data.get('id', '')}")

        # --- Row 1: Header (Badge + Lens + Spacer + Time + Dismiss) ---
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        label_text = self.alert_data.get("label", "Detection").upper()
        conf_pct = int(self.alert_data.get("confidence", 0) * 100)
        lens_text = self.alert_data.get("lens", "Lens1")

        lbl_lower = label_text.lower()
        is_person = "person" in lbl_lower
        is_car = "car" in lbl_lower
        is_truck = "truck" in lbl_lower
        is_bus = "bus" in lbl_lower
        is_motorcycle = "motorcycle" in lbl_lower
        is_vehicle = is_car or is_truck or is_bus or is_motorcycle or "vehicle" in lbl_lower
        is_dog = "dog" in lbl_lower
        is_cat = "cat" in lbl_lower
        is_animal = is_dog or is_cat or any(k in lbl_lower for k in ["animal", "bird", "horse"])

        if is_person:
            badge_color = "#f43f5e"
            badge_bg = "rgba(244, 63, 94, 0.18)"
            tag_label = "PERSON"
        elif is_car:
            badge_color = "#38bdf8"
            badge_bg = "rgba(56, 189, 248, 0.18)"
            tag_label = "CAR"
        elif is_truck:
            badge_color = "#38bdf8"
            badge_bg = "rgba(56, 189, 248, 0.18)"
            tag_label = "TRUCK"
        elif is_bus:
            badge_color = "#38bdf8"
            badge_bg = "rgba(56, 189, 248, 0.18)"
            tag_label = "BUS"
        elif is_motorcycle:
            badge_color = "#38bdf8"
            badge_bg = "rgba(56, 189, 248, 0.18)"
            tag_label = "MOTORCYCLE"
        elif is_vehicle:
            badge_color = "#38bdf8"
            badge_bg = "rgba(56, 189, 248, 0.18)"
            tag_label = "VEHICLE"
        elif is_dog:
            badge_color = "#f59e0b"
            badge_bg = "rgba(245, 158, 11, 0.18)"
            tag_label = "DOG"
        elif is_cat:
            badge_color = "#f59e0b"
            badge_bg = "rgba(245, 158, 11, 0.18)"
            tag_label = "CAT"
        elif is_animal:
            badge_color = "#f59e0b"
            badge_bg = "rgba(245, 158, 11, 0.18)"
            tag_label = "ANIMAL"
        else:
            badge_color = "#818cf8"
            badge_bg = "rgba(129, 140, 248, 0.18)"
            tag_label = "MOTION"

        self.setStyleSheet(f"""
            QFrame#alert_card {{
                background-color: #131d2e;
                border: 1px solid #1e293b;
                border-left: 3px solid {badge_color};
                border-radius: 5px;
                padding: 6px;
                margin: 2px 0px;
            }}
            QFrame#alert_card:hover {{
                border-color: #38bdf8;
                border-left: 3px solid {badge_color};
                background-color: #172338;
            }}
        """)

        conf_str = f" ({conf_pct}%)" if conf_pct > 0 else ""
        lbl_badge = QLabel(f"● {tag_label}{conf_str}", self)
        lbl_badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_color};
            font-weight: 700;
            font-size: 11px;
            border: 1px solid {badge_color};
            border-radius: 4px;
            padding: 2px 6px;
        """)
        row1.addWidget(lbl_badge)

        # Lens badge
        clean_lens = lens_text.replace("Lens ", "L").replace("Lens", "L")
        lbl_lens = QLabel(f"{clean_lens}", self)
        lbl_lens.setStyleSheet("""
            background-color: rgba(15, 23, 42, 0.90);
            color: #94a3b8;
            font-weight: 700;
            font-size: 10px;
            border: 1px solid #334155;
            border-radius: 4px;
            padding: 2px 6px;
        """)
        row1.addWidget(lbl_lens)

        row1.addStretch()

        # Timestamp
        time_str = self.alert_data.get("time_short", "")
        if not time_str and "timestamp" in self.alert_data:
            ts = self.alert_data.get("timestamp", "")
            time_str = ts.split(" ")[-1] if " " in ts else ts

        lbl_time = QLabel(time_str, self)
        lbl_time.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        row1.addWidget(lbl_time)

        # Dismiss / Delete Button
        btn_dismiss = QPushButton("✕", self)
        btn_dismiss.setToolTip("Dismiss alert from list")
        btn_dismiss.setFixedSize(18, 18)
        btn_dismiss.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_dismiss.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: none;
                font-size: 11px;
                font-weight: bold;
                border-radius: 3px;
                padding: 0px;
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.18);
            }
        """)
        btn_dismiss.clicked.connect(self._on_dismiss_clicked)
        row1.addWidget(btn_dismiss)

        layout.addLayout(row1)

        # --- Row 1.5: Trigger Reason (if present) ---
        trigger_text = self.alert_data.get("trigger_reason", "")
        if trigger_text:
            lbl_trig = QLabel(f"Trigger: {trigger_text}", self)
            lbl_trig.setWordWrap(True)
            lbl_trig.setStyleSheet("""
                color: #38bdf8;
                font-size: 10px;
                font-weight: 700;
                background-color: rgba(56, 189, 248, 0.12);
                border-left: 3px solid #38bdf8;
                padding: 3px 6px;
                border-radius: 2px;
            """)
            layout.addWidget(lbl_trig)

        # --- Row 2: Scene description / AI Explanation (if present) ---
        desc_text = self.alert_data.get("description", "")
        if desc_text and desc_text != trigger_text:
            lbl_desc = QLabel(f"{desc_text}", self)
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("""
                color: #e2e8f0;
                font-size: 11px;
                font-weight: 600;
                background-color: rgba(15, 23, 42, 0.7);
                border-left: 3px solid #64748b;
                padding: 4px 6px;
                border-radius: 2px;
            """)
            layout.addWidget(lbl_desc)

        # --- Row 3: Thumbnail + Camera & Status Info ---
        row3 = QHBoxLayout()
        row3.setSpacing(8)

        # 16:9 Thumbnail
        self.lbl_thumb = QLabel(self)
        self.lbl_thumb.setFixedSize(84, 48)
        self.lbl_thumb.setStyleSheet("""
            background-color: #050811;
            border-radius: 4px;
            border: 1px solid #1e293b;
            color: #64748b;
            font-size: 10px;
            font-weight: 700;
        """)
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thumb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.lbl_thumb.setToolTip("Click to view full-resolution photo snapshot")
        self.lbl_thumb.mousePressEvent = lambda e: self._open_snapshot()

        snap_path = self.alert_data.get("snapshot_path", "")
        if snap_path and os.path.exists(snap_path):
            pix = QPixmap(snap_path)
            if not pix.isNull():
                self.lbl_thumb.setPixmap(
                    pix.scaled(84, 48, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                )
        else:
            self.lbl_thumb.setText("PHOTO")
        row3.addWidget(self.lbl_thumb)

        # Info & Status column
        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        cam_name = self.alert_data.get("camera_name", "Camera")
        lbl_cam = QLabel(f"{cam_name}", self)
        lbl_cam.setStyleSheet("color: #f1f5f9; font-weight: 700; font-size: 11px;")
        info_col.addWidget(lbl_cam)

        vpath = self.alert_data.get("video_path") or self.alert_data.get("video_highlighted_path") or ""
        video_exists = bool(vpath and os.path.exists(vpath) and os.path.getsize(vpath) > 1024)
        if video_exists:
            self.alert_data["video_ready"] = True

        is_fresh = False
        ts_raw = self.alert_data.get("timestamp", "")
        if ts_raw:
            try:
                dt = datetime.fromisoformat(ts_raw) if "T" in ts_raw else datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S")
                if (datetime.now() - dt).total_seconds() < 15:
                    is_fresh = True
            except Exception:
                pass

        self.lbl_status = QLabel(self)
        self.recording_timeout_timer = None

        if self.alert_data.get("video_ready"):
            self.lbl_status.setText("Video Clip Available")
            self.lbl_status.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 600;")
        elif self.alert_data.get("video_recording") and is_fresh:
            self.lbl_status.setText("Recording clip...")
            self.lbl_status.setStyleSheet("color: #fbbf24; font-size: 10px; font-weight: 600;")
            self.recording_timeout_timer = QTimer(self)
            self.recording_timeout_timer.setSingleShot(True)
            self.recording_timeout_timer.setInterval(13000)
            self.recording_timeout_timer.timeout.connect(self._on_recording_timeout)
            self.recording_timeout_timer.start()
        else:
            snap_path = self.alert_data.get("snapshot_path", "")
            if snap_path and os.path.exists(snap_path):
                self.lbl_status.setText("Snapshot Saved")
            else:
                self.lbl_status.setText("Incident Logged")
            self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 500;")

        info_col.addWidget(self.lbl_status)

        row3.addLayout(info_col)
        row3.addStretch()
        layout.addLayout(row3)

        # --- Row 4: Action Buttons ([Play Clip] [Snapshot]) ---
        row4 = QHBoxLayout()
        row4.setSpacing(6)

        self.btn_play_clip = QPushButton("Play Clip", self)
        self.btn_play_clip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_play_clip.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: 700;
                font-size: 11px;
                padding: 5px 12px;
                border-radius: 4px;
                border: 1px solid #3b82f6;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
                border-color: #60a5fa;
            }
            QPushButton:disabled {
                background-color: #1e293b;
                color: #64748b;
                border: 1px solid #334155;
            }
        """)
        self.btn_play_clip.setToolTip("Watch 10s clip with audio and dual feeds")
        self.btn_play_clip.clicked.connect(self._open_clip)
        has_video = bool(self.alert_data.get("video_ready", False))
        is_rec = bool(self.alert_data.get("video_recording") and is_fresh)
        self.btn_play_clip.setEnabled(has_video or is_rec)
        if is_rec and not has_video:
            self.btn_play_clip.setText("Watch Video")
        elif not has_video:
            self.btn_play_clip.setText("No Clip")
            self.btn_play_clip.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    color: #64748b;
                    font-size: 10px;
                    border: 1px solid #334155;
                    padding: 5px 10px;
                    border-radius: 4px;
                }
            """)
        row4.addWidget(self.btn_play_clip)

        self.btn_view_snap = QPushButton("Snapshot", self)
        self.btn_view_snap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_view_snap.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                font-size: 11px;
                font-weight: 600;
                padding: 5px 10px;
                border-radius: 4px;
                border: 1px solid #334155;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #ffffff;
                border-color: #3b82f6;
            }
        """)
        self.btn_view_snap.setToolTip("View full-resolution photo snapshot")
        self.btn_view_snap.clicked.connect(self._open_snapshot)
        row4.addWidget(self.btn_view_snap)

        layout.addLayout(row4)

    def set_video_ready(self, video_path: str, raw_path: str = ""):
        if hasattr(self, "recording_timeout_timer") and self.recording_timeout_timer and self.recording_timeout_timer.isActive():
            self.recording_timeout_timer.stop()
        self.alert_data["video_ready"] = True
        self.alert_data["video_recording"] = False
        self.alert_data["video_path"] = video_path
        self.alert_data["video_highlighted_path"] = video_path
        if raw_path:
            self.alert_data["video_raw_path"] = raw_path
        self.lbl_status.setText("Video Clip Available")
        self.lbl_status.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 600;")
        self.btn_play_clip.setText("Play Clip")
        self.btn_play_clip.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: 700;
                font-size: 11px;
                padding: 5px 12px;
                border-radius: 4px;
                border: 1px solid #3b82f6;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
                border-color: #60a5fa;
            }
        """)
        self.btn_play_clip.setEnabled(True)

    def set_video_failed(self):
        if hasattr(self, "recording_timeout_timer") and self.recording_timeout_timer and self.recording_timeout_timer.isActive():
            self.recording_timeout_timer.stop()
        self.alert_data["video_recording"] = False
        snap_path = self.alert_data.get("snapshot_path", "")
        if snap_path and os.path.exists(snap_path):
            self.lbl_status.setText("Snapshot Saved (No Clip)")
        else:
            self.lbl_status.setText("Incident Logged")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 500;")
        self.btn_play_clip.setEnabled(False)
        self.btn_play_clip.setText("No Clip")
        self.btn_play_clip.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #64748b;
                font-size: 10px;
                border: 1px solid #334155;
                padding: 5px 10px;
                border-radius: 4px;
            }
        """)

    def _on_recording_timeout(self):
        vpath = self.alert_data.get("video_path") or self.alert_data.get("video_highlighted_path") or ""
        if vpath and os.path.exists(vpath) and os.path.getsize(vpath) > 1024:
            self.set_video_ready(vpath)
        else:
            self.set_video_failed()

    def _on_dismiss_clicked(self):
        alert_id = self.alert_data.get("id", "")
        self.delete_requested.emit(alert_id)

    def _open_clip(self):
        vpath = (
            self.alert_data.get("video_path", "")
            or self.alert_data.get("video_highlighted_path", "")
            or self.alert_data.get("video_raw_path", "")
        )
        if not vpath or not os.path.exists(vpath):
            raw_cand = self.alert_data.get("video_raw_path", "")
            if raw_cand and os.path.exists(raw_cand):
                self.alert_data["video_path"] = raw_cand
                vpath = raw_cand

        if not vpath or not os.path.exists(vpath):
            if bool(self.alert_data.get("video_recording")):
                try:
                    from ui.components.video_player_dialog import VideoPlayerDialog
                    dlg = VideoPlayerDialog(self.alert_data, parent=self.window())
                    dlg.exec()
                    return
                except Exception as e:
                    print(f"[AlertCard] Player error: {e}")

            self.alert_data["video_ready"] = False
            self.lbl_status.setText("Clip Expired (Cleared by quota)")
            self.lbl_status.setStyleSheet("color: #f59e0b; font-size: 10px; font-weight: 600;")
            self.btn_play_clip.setEnabled(False)
            self.btn_play_clip.setText("Expired Clip")
            self.btn_play_clip.setStyleSheet("""
                QPushButton {
                    background: #1e293b;
                    color: #94a3b8;
                    font-size: 10px;
                    border: 1px solid #334155;
                    padding: 5px 10px;
                    border-radius: 4px;
                }
            """)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self.window(),
                "Video Clip Unavailable",
                "This video clip is no longer available on disk.\n\n"
                "It was automatically removed by the storage quota manager "
                "to maintain disk space limits.\n\n"
                "Photo snapshot of the incident remains available."
            )
            return

        try:
            from ui.components.video_player_dialog import VideoPlayerDialog
            dlg = VideoPlayerDialog(self.alert_data, parent=self.window())
            dlg.exec()
        except Exception as e:
            print(f"[AlertCard] In-client player failed, falling back: {e}")
            if vpath and os.path.exists(vpath):
                try:
                    os.startfile(vpath)
                except Exception:
                    pass

    def _open_snapshot(self):
        spath = self.alert_data.get("snapshot_path", "")
        if spath and os.path.exists(spath):
            try:
                os.startfile(spath)
            except Exception as e:
                print(f"[AlertCard] Failed to open snapshot: {e}")
