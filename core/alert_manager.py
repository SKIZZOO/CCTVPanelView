import os
import sys
import json
import time
import subprocess
import threading
import queue
import collections
import re
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal


def format_media_filename(
    tag: str,
    lens: str,
    camera: str,
    what_it_found: str,
    ext: str = "mp4",
    dt: Optional[datetime] = None,
    unique_id: Optional[str] = None
) -> Tuple[str, str]:
    """
    Constructs standardized media filenames with rich, human-readable details:
    CCTV_[Camera]_[Lens]_[EventDetails]_[YYYY-MM-DD_HH-MM-SS]_[Variant]_[ID].[ext]

    Examples:
    CCTV_Fata_Lens1_PTZ_Person_85pct_2026-10-18_16-38-07_AI_Boxed_49C8.mp4
    CCTV_Fata_Lens1_PTZ_Person_85pct_2026-10-18_16-38-07_Raw_49C8.mp4
    CCTV_Snapshot_Fata_Lens1_PTZ_Person_85pct_2026-10-18_16-38-07_49C8.jpg
    CCTV_Manual_Afara_MainStream_2026-10-18_16-38-07_REC_60D0.mp4
    CCTV_Motion_Afara_MainStream_2026-10-18_16-38-07_REC_60D0.mp4

    Returns: (basename, unique_id)
    """
    if dt is None:
        dt = datetime.now()
    if unique_id is None:
        unique_id = uuid.uuid4().hex[:4].upper()

    # Clean camera name
    cam_clean = re.sub(r'\(.*?\)', '', camera).strip()
    safe_cam = re.sub(r'[^A-Za-z0-9]', '_', cam_clean).strip('_') or 'Camera'

    # Clean lens name
    lens_clean = lens.replace(' ', '').replace('(', '_').replace(')', '')
    safe_lens = re.sub(r'[^A-Za-z0-9_]', '', lens_clean).strip('_') or 'Lens1'

    what_raw = str(what_it_found).strip()
    is_hl = 'HIGHLIGHTED' in what_raw.upper() or 'AI_BOXED' in what_raw.upper()
    is_raw = '_RAW' in what_raw.upper() or '_Raw' in what_raw

    clean_what = what_raw.replace('_HIGHLIGHTED', '').replace('_RAW', '').replace('_AI_Boxed', '').replace('_Raw', '').strip('_')
    clean_what = re.sub(r'[^A-Za-z0-9_]', '_', clean_what).strip('_') or 'Detection'

    date_str = dt.strftime('%Y-%m-%d')
    time_str = dt.strftime('%H-%M-%S')
    ext_clean = ext.lstrip('.').lower()

    if ext_clean in ['jpg', 'jpeg', 'png']:
        basename = f'CCTV_Snapshot_{safe_cam}_{safe_lens}_{clean_what}_{date_str}_{time_str}_{unique_id}.{ext_clean}'
        return basename, unique_id

    tag_u = str(tag).upper()
    if 'REC' in tag_u or 'MANUAL' in clean_what.upper():
        event_tag = 'Motion' if 'MOTION' in clean_what.upper() else 'Manual'
        basename = f'CCTV_{event_tag}_{safe_cam}_{safe_lens}_{date_str}_{time_str}_REC_{unique_id}.{ext_clean}'
        return basename, unique_id

    variant = 'AI_Boxed' if is_hl else ('Raw' if is_raw else 'Clip')
    basename = f'CCTV_{safe_cam}_{safe_lens}_{clean_what}_{date_str}_{time_str}_{variant}_{unique_id}.{ext_clean}'
    return basename, unique_id


class AlertClipSession:
    """
    Asynchronous 10-second dual-version video recorder:
    Receives (raw_frame, highlighted_frame) pairs from CameraStreamWorker and encodes
    both versions via lightweight FFmpeg pipes at a smooth constant framerate (e.g. 15 FPS).
    In parallel, records synchronized audio track from camera's RTSP stream.
    At completion, muxes audio into both clips and emits alert_video_ready.
    """
    def __init__(
        self,
        manager: "AlertManager",
        stream_id: str,
        rtsp_url: str,
        alert_entry: dict,
        raw_output_path: str,
        highlighted_output_path: str,
        fps: float = 15.0,
        max_duration_sec: float = 300.0,
        record_dual_clips: bool = True,
        record_audio: bool = False,
        min_duration_sec: float = 8.0,
        quiet_timeout_sec: float = 5.0,
        trigger_frame: Optional[np.ndarray] = None
    ):
        self.manager = manager
        self.stream_id = stream_id
        self.rtsp_url = rtsp_url
        self.alert_entry = alert_entry
        self.raw_output_path = raw_output_path
        self.highlighted_output_path = highlighted_output_path
        self.fps = fps if (5.0 <= fps <= 60.0) else 15.0
        self.max_duration_sec = min(300.0, float(max_duration_sec))  # Capped strictly at 5 minutes
        self.min_duration_sec = min_duration_sec
        self.quiet_timeout_sec = quiet_timeout_sec
        self.last_activity_time = time.time()
        self.max_frames = int(self.fps * self.max_duration_sec)
        self.record_dual_clips = record_dual_clips
        self.record_audio = record_audio
        self.trigger_frame = trigger_frame

        # Bounded queue strictly limited to 45 frames to eliminate massive RAM consumption
        frame_bytes = int(trigger_frame.nbytes) if trigger_frame is not None else 1920 * 1080 * 3
        self.queue = queue.Queue(maxsize=max(1, min(45, (32 * 1024 * 1024) // max(1, frame_bytes * 2))))
        self.prebuffer = collections.deque()
        self.active = True
        self.frame_count = 0
        self.start_time = time.time()

        self.temp_dir = os.path.dirname(raw_output_path)
        uid = alert_entry.get("unique_id", uuid.uuid4().hex[:4].upper())
        self.temp_raw = os.path.join(self.temp_dir, f"tmp_{uid}_raw.mp4")
        self.temp_hl = os.path.join(self.temp_dir, f"tmp_{uid}_hl.mp4")
        self.temp_audio = os.path.join(self.temp_dir, f"tmp_{uid}_audio.aac")

        self.proc_raw = None
        self.proc_hl = None
        self.proc_audio = None
        self.width = 0
        self.height = 0

        self.thread = threading.Thread(target=self._worker, daemon=True, name=f"ClipSession_{stream_id}")
        self.thread.start()

        # Watchdog failsafe timer: ensures session terminates cleanly even if frame feed drops
        self._failsafe_timer = threading.Timer(self.max_duration_sec + 4.0, self._failsafe_timeout)
        self._failsafe_timer.daemon = True
        self._failsafe_timer.start()

        # Only connect to camera RTSP for audio if explicitly enabled by user
        if self.record_audio and self.rtsp_url:
            self._start_audio_capture()

    def _failsafe_timeout(self):
        if self.active:
            self.active = False
            try:
                self.queue.put_nowait((None, None))
            except Exception:
                pass

    def set_prebuffer(self, frames):
        """Keep compressed frames compressed until encoding; preserve their 10 Hz timing."""
        output = []
        for index, (data, stamp) in enumerate(frames):
            copies = max(1, round((index + 1) * self.fps / 10) - round(index * self.fps / 10))
            output.extend([data] * copies)
        self.prebuffer.extend(output)

    def push_frame(self, raw_frame: np.ndarray, highlighted_frame: np.ndarray, has_activity: bool = True):
        if not self.active:
            return
        if has_activity:
            self.last_activity_time = time.time()
        try:
            self.queue.put_nowait((raw_frame, highlighted_frame))
        except queue.Full:
            pass

    def finish(self, wait: bool = True, timeout: float = 3.0):
        """Immediately finishes recording and finalizes output files gracefully."""
        self.active = False
        try:
            self.queue.put_nowait(None)
        except Exception:
            pass
        if wait and hasattr(self, "thread") and self.thread.is_alive():
            try:
                self.thread.join(timeout=timeout)
            except Exception:
                pass

    def _start_audio_capture(self):
        cmd_audio = [
            "ffmpeg", "-y",
            "-use_wallclock_as_timestamps", "1",
            "-fflags", "+genpts+discardcorrupt",
            "-rtsp_transport", "tcp",
            "-timeout", "3000000",
            "-i", self.rtsp_url,
            "-t", str(int(self.max_duration_sec)),
            "-vn",
            "-af", "aresample=async=1000:first_pts=0",
            "-c:a", "aac",
            "-b:a", "128k",
            "-f", "adts",
            self.temp_audio
        ]
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            creationflags = subprocess.CREATE_NO_WINDOW
        try:
            self.proc_audio = subprocess.Popen(
                cmd_audio,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
        except Exception as e:
            print(f"[AlertClipSession] Audio capture failed to start: {e}")

    def _init_encoders(self, w: int, h: int):
        # Guarantee dimensions are even for libx264 yuv420p
        w = w - (w % 2)
        h = h - (h % 2)
        self.width = w
        self.height = h
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            creationflags = subprocess.CREATE_NO_WINDOW

        fps_str = str(int(self.fps))

        cmd_hl = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{w}x{h}",
            "-pix_fmt", "bgr24",
            "-r", fps_str,
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            self.temp_hl
        ]
        cmd_raw = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{w}x{h}",
            "-pix_fmt", "bgr24",
            "-r", fps_str,
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            self.temp_raw
        ]
        try:
            self.proc_hl = subprocess.Popen(cmd_hl, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, creationflags=creationflags)
        except Exception as e:
            print(f"[AlertClipSession] Highlighted video encoder init failed: {e}")

        if self.record_dual_clips:
            try:
                self.proc_raw = subprocess.Popen(cmd_raw, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, creationflags=creationflags)
            except Exception as e:
                print(f"[AlertClipSession] Raw video encoder init failed: {e}")

    def _worker(self):
        while self.active or not self.queue.empty():
            try:
                if self.prebuffer:
                    data = self.prebuffer.popleft()
                    decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if decoded is None:
                        continue
                    item = (decoded, decoded)
                else:
                    item = self.queue.get(timeout=0.1)
                if item is None or (isinstance(item, tuple) and item[0] is None):
                    self.active = False
                    break
                raw_frame, hl_frame = item
            except queue.Empty:
                now = time.time()
                elapsed = now - self.start_time
                quiet_dur = now - self.last_activity_time
                if elapsed >= self.max_duration_sec:
                    self.active = False
                    break
                if elapsed >= self.min_duration_sec and quiet_dur >= self.quiet_timeout_sec:
                    self.active = False
                    break
                continue

            if self.proc_hl is None:
                h, w = hl_frame.shape[:2]
                self._init_encoders(w, h)

                # Bake 0.5-second incident alert slate on video itself
                try:
                    from core.video_slate import generate_video_alert_slate
                    snap_p = self.alert_entry.get("snapshot_path", "")
                    slate = generate_video_alert_slate(
                        width=self.width,
                        height=self.height,
                        alert_type=self.alert_entry.get("label", "ALERT"),
                        camera_name=self.alert_entry.get("camera_name", "Camera"),
                        lens_name=self.alert_entry.get("lens", "Main Lens"),
                        timestamp=self.alert_entry.get("timestamp", ""),
                        trigger_reason=self.alert_entry.get("trigger_reason", "") or self.alert_entry.get("description", ""),
                        trigger_image=getattr(self, "trigger_frame", None) if getattr(self, "trigger_frame", None) is not None else hl_frame,
                        trigger_image_path=snap_p,
                        confidence=self.alert_entry.get("confidence", None)
                    )
                    slate_bytes = slate.tobytes()
                    num_slate_frames = max(1, int(round(self.fps * 0.5)))
                    for _ in range(num_slate_frames):
                        if self.proc_hl and self.proc_hl.stdin:
                            self.proc_hl.stdin.write(slate_bytes)
                        if self.record_dual_clips and self.proc_raw and self.proc_raw.stdin:
                            self.proc_raw.stdin.write(slate_bytes)
                except Exception as slate_err:
                    print(f"[AlertClipSession] Intro slate error: {slate_err}")

            if self.proc_hl and self.proc_hl.stdin:
                try:
                    self.proc_hl.stdin.write(hl_frame.tobytes())
                except Exception:
                    pass

            if self.record_dual_clips and self.proc_raw and self.proc_raw.stdin:
                try:
                    self.proc_raw.stdin.write(raw_frame.tobytes())
                except Exception:
                    pass

            self.frame_count += 1
            now = time.time()
            elapsed = now - self.start_time
            quiet_dur = now - self.last_activity_time
            if self.frame_count >= self.max_frames or elapsed >= self.max_duration_sec:
                self.active = False
                break
            if elapsed >= self.min_duration_sec and quiet_dur >= self.quiet_timeout_sec:
                self.active = False
                break

        # Finalize video encoding processes
        if self.proc_hl:
            try:
                if self.proc_hl.stdin:
                    self.proc_hl.stdin.close()
                self.proc_hl.wait(timeout=3.0)
            except Exception:
                try:
                    self.proc_hl.kill()
                except Exception:
                    pass

        if self.proc_raw:
            try:
                if self.proc_raw.stdin:
                    self.proc_raw.stdin.close()
                self.proc_raw.wait(timeout=3.0)
            except Exception:
                try:
                    self.proc_raw.kill()
                except Exception:
                    pass

        # Wait for audio process
        if self.proc_audio:
            try:
                self.proc_audio.terminate()
                self.proc_audio.wait(timeout=2.0)
            except Exception:
                try:
                    self.proc_audio.kill()
                except Exception:
                    pass

        self._finalize_outputs()

    def _finalize_outputs(self):
        if hasattr(self, "_failsafe_timer") and self._failsafe_timer:
            try:
                self._failsafe_timer.cancel()
            except Exception:
                pass
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            creationflags = subprocess.CREATE_NO_WINDOW

        has_audio = os.path.exists(self.temp_audio) and os.path.getsize(self.temp_audio) > 1024

        def mux_video_audio(src_vid: str, dst_vid: str):
            if not os.path.exists(src_vid) or os.path.getsize(src_vid) <= 1024:
                return False
            if has_audio:
                cmd_mux = [
                    "ffmpeg", "-y",
                    "-i", src_vid,
                    "-itsoffset", "0.5",
                    "-i", self.temp_audio,
                    "-c:v", "copy",
                    "-map", "0:v:0",
                    "-map", "1:a:0?",
                    "-c:a", "copy",
                    "-shortest",
                    "-movflags", "+faststart",
                    dst_vid
                ]
                try:
                    res = subprocess.run(cmd_mux, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, creationflags=creationflags, timeout=8.0)
                    if res.returncode == 0 and os.path.exists(dst_vid) and os.path.getsize(dst_vid) > 1024:
                        return True
                except Exception:
                    pass
            try:
                if os.path.exists(dst_vid):
                    try:
                        os.remove(dst_vid)
                    except Exception:
                        pass
                try:
                    os.replace(src_vid, dst_vid)
                except Exception:
                    import shutil
                    shutil.copy2(src_vid, dst_vid)
                    try:
                        os.remove(src_vid)
                    except Exception:
                        pass
                return os.path.exists(dst_vid) and os.path.getsize(dst_vid) > 0
            except Exception:
                return False

        hl_ok = mux_video_audio(self.temp_hl, self.highlighted_output_path)
        if self.record_dual_clips:
            raw_ok = mux_video_audio(self.temp_raw, self.raw_output_path)
        else:
            raw_ok = hl_ok
            self.raw_output_path = self.highlighted_output_path

        # Cleanup temporary audio and video encoding files
        for tmp_file in [self.temp_audio, self.temp_hl, self.temp_raw]:
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass

        # Update alert metadata - ALWAYS clear recording state so UI is never stuck!
        self.alert_entry["video_recording"] = False
        if hl_ok or raw_ok:
            self.alert_entry["video_ready"] = True
            self.alert_entry["video_failed"] = False
            if hl_ok:
                self.alert_entry["video_path"] = self.highlighted_output_path
                self.alert_entry["video_highlighted_path"] = self.highlighted_output_path
            else:
                self.alert_entry["video_path"] = self.raw_output_path
                self.alert_entry["video_highlighted_path"] = self.raw_output_path

            if raw_ok:
                self.alert_entry["video_raw_path"] = self.raw_output_path
            else:
                self.alert_entry["video_raw_path"] = self.highlighted_output_path
        else:
            self.alert_entry["video_ready"] = False
            self.alert_entry["video_failed"] = True

        if self.manager:
            with self.manager.lock:
                self.manager._save_history()

            # ALWAYS emit alert_video_ready so UI card transitions immediately out of recording!
            self.manager.alert_video_ready.emit(self.alert_entry)


class AlertManager(QObject):
    """
    Centralized Alert, Snapshot, and 10-Second High-Quality Video Recording Coordinator.
    
    When an AI or Motion alert is triggered:
    1. Immediately captures a pristine native-resolution snapshot (.jpg) at 100% quality.
    2. Spawns an asynchronous dual-version 10-second video recording:
       - HIGHLIGHTED: with AI target boxes, labels, and tracking overlays rendered smoothly.
       - RAW: pristine native video stream with synchronized audio.
    3. Files are named strictly using: TAG_LENS_CAMERA_WHAT IT FOUND_ DATE _ TIME _ID
    4. Manages persistent alert history with thumbnails, metadata, and instant client playback.
    """
    alert_triggered = pyqtSignal(dict)      # Emitted immediately with snapshot & pending clip
    alert_video_ready = pyqtSignal(dict)    # Emitted when the 10-second video recording finishes
    history_loaded = pyqtSignal()
    alerts_cleared = pyqtSignal()
    alerts_purged = pyqtSignal(list)        # Emitted when older alerts are removed by storage quota / retention

    def __init__(self, snapshot_dir: str = "snapshots", recording_dir: str = "recordings", parent=None, defer_history=False):
        super().__init__(parent)
        self.snapshot_dir = os.path.abspath(os.path.join(snapshot_dir, "alarms"))
        self.recording_dir = os.path.abspath(os.path.join(recording_dir, "alarms"))

        try:
            os.makedirs(self.snapshot_dir, exist_ok=True)
        except Exception as e:
            print(f"[AlertManager] Warning: failed to create snapshot dir {self.snapshot_dir}: {e}. Falling back to local directory.")
            self.snapshot_dir = os.path.abspath(os.path.join("snapshots", "alarms"))
            os.makedirs(self.snapshot_dir, exist_ok=True)

        try:
            os.makedirs(self.recording_dir, exist_ok=True)
        except Exception as e:
            print(f"[AlertManager] Warning: failed to create recording dir {self.recording_dir}: {e}. Falling back to local directory.")
            self.recording_dir = os.path.abspath(os.path.join("recordings", "alarms"))
            os.makedirs(self.recording_dir, exist_ok=True)

        self.history_file = os.path.join(self.recording_dir, "alerts_history.json")
        self.active_recordings = {}  # stream_id -> subprocess.Popen
        self.lock = threading.RLock()
        self.alerts_list: List[Dict[str, Any]] = []
        self.app_settings: Dict[str, Any] = {}
        self.notification_dispatcher = None
        try:
            from core.notification_dispatcher import NotificationDispatcher
            self.notification_dispatcher = NotificationDispatcher(self.app_settings)
        except Exception as e:
            print(f"[AlertManager] Could not initialize NotificationDispatcher: {e}")

        self.alert_video_ready.connect(self._on_alert_video_ready_notify)
        if defer_history:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self._start_history_loading)
        else:
            self._load_history()
        threading.Thread(target=self.clean_temp_files, daemon=True, name="StartupTempCleanup").start()

    def _start_history_loading(self):
        def load():
            try:
                with self.lock:
                    self._load_history()
            finally:
                try:
                    self.history_loaded.emit()
                except RuntimeError:
                    pass
        threading.Thread(target=load, daemon=True, name="AlertHistory").start()

    def _on_alert_video_ready_notify(self, alert_entry: dict):
        if self.notification_dispatcher and alert_entry.get("video_ready"):
            try:
                self.notification_dispatcher.send_video_alert(alert_entry)
            except Exception as e:
                print(f"[AlertManager] Error dispatching video notification: {e}")

    def set_app_settings(self, settings: dict):
        """Updates app settings for clip recording preferences and notification dispatch."""
        with self.lock:
            self.app_settings = dict(settings)
            if self.notification_dispatcher:
                self.notification_dispatcher.update_settings(self.app_settings)

    def update_storage_paths(self, snapshot_dir: str = None, recording_dir: str = None):
        """Updates storage directories dynamically when modified in settings."""
        with self.lock:
            if snapshot_dir:
                target_snap = snapshot_dir if os.path.basename(snapshot_dir).lower() == "alarms" else os.path.join(snapshot_dir, "alarms")
                try:
                    os.makedirs(os.path.abspath(target_snap), exist_ok=True)
                    self.snapshot_dir = os.path.abspath(target_snap)
                except Exception as e:
                    print(f"[AlertManager] Warning: cannot create {target_snap}: {e}")
            if recording_dir:
                target_rec = recording_dir if os.path.basename(recording_dir).lower() == "alarms" else os.path.join(recording_dir, "alarms")
                try:
                    os.makedirs(os.path.abspath(target_rec), exist_ok=True)
                    self.recording_dir = os.path.abspath(target_rec)
                    self.history_file = os.path.join(self.recording_dir, "alerts_history.json")
                    if not os.path.exists(self.history_file) and self.alerts_list:
                        self._save_history()
                except Exception as e:
                    print(f"[AlertManager] Warning: cannot create {target_rec}: {e}")

    def _load_history(self):
        loaded = False
        candidates = [self.history_file, f"{self.history_file}.bak"]
        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list) and data:
                        self.alerts_list = data
                        loaded = True
                        break
                except Exception as e:
                    print(f"[AlertManager] Failed loading history from {path}: {e}")

        if not loaded:
            self.alerts_list = []

        # Sanitize and verify video_ready status against actual files on disk
        for a in self.alerts_list:
            if a.get("video_recording"):
                a["video_recording"] = False
            vpath = a.get("video_path") or a.get("video_highlighted_path") or a.get("video_raw_path")
            if vpath and os.path.exists(vpath) and os.path.getsize(vpath) > 1024:
                a["video_ready"] = True

        # If history has fewer than 50 items, backfill from recent media on disk
        if len(self.alerts_list) < 50:
            self._index_recent_media_from_disk(max_items=100)

    def _index_recent_media_from_disk(self, max_items: int = 100):
        """
        Discovers existing alert videos/snapshots on disk and intelligently indexes them
        into alerts_list. Merges highlighted & raw pairs and pairs matching snapshots.
        Scans both recordings/alarms and the general recordings directory.
        """
        try:
            scan_dirs = []
            if os.path.exists(self.recording_dir):
                scan_dirs.append(self.recording_dir)
            parent_rec = os.path.dirname(self.recording_dir)
            if os.path.exists(parent_rec) and os.path.abspath(parent_rec) != os.path.abspath(self.recording_dir):
                scan_dirs.append(parent_rec)

            if not scan_dirs:
                return

            file_mtimes = []
            for s_dir in scan_dirs:
                for f in os.listdir(s_dir):
                    if f.lower().endswith(".mp4") and not f.startswith("tmp_") and not f.startswith(".tmp"):
                        p = os.path.join(s_dir, f)
                        if os.path.isfile(p):
                            try:
                                file_mtimes.append((f, p, os.path.getmtime(p)))
                            except Exception:
                                pass
            if not file_mtimes:
                return

            file_mtimes.sort(key=lambda x: x[2], reverse=True)
            # Only inspect the most recent media files to keep startup fast (< 20ms)
            file_mtimes = file_mtimes[:max_items * 2]

            snap_files = set(os.listdir(self.snapshot_dir)) if os.path.exists(self.snapshot_dir) else set()
            root_snap_dir = os.path.dirname(self.snapshot_dir)
            root_snaps = set(os.listdir(root_snap_dir)) if os.path.exists(root_snap_dir) and os.path.abspath(root_snap_dir) != os.path.abspath(self.snapshot_dir) else set()

            with self.lock:
                existing_uids = {a.get("unique_id") for a in self.alerts_list if a.get("unique_id")}
                existing_filenames = {a.get("filename") for a in self.alerts_list if a.get("filename")}
                existing_filenames.update({a.get("filename_raw") for a in self.alerts_list if a.get("filename_raw")})

            grouped = {}
            for fn, fpath, mtime in file_mtimes:
                base, _ = os.path.splitext(fn)
                clean = re.sub(r'^(CCTV_Snapshot_|CCTV_Manual_|CCTV_Motion_|CCTV_|ALARM_|REC_)', '', base, flags=re.IGNORECASE)

                m_time = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}|\d{8}_\d{6})(?:_([A-Za-z0-9_]{4,12}))?$', clean)
                dt = datetime.fromtimestamp(mtime)
                uid = None
                if m_time:
                    dt_str = m_time.group(1)
                    uid = m_time.group(2)
                    for fmt in ['%Y-%m-%d_%H-%M-%S', '%Y%m%d_%H%M%S']:
                        try:
                            dt = datetime.strptime(dt_str, fmt)
                            break
                        except Exception:
                            pass
                    prefix = clean[:m_time.start()].rstrip('_')
                else:
                    prefix = clean

                if not uid:
                    uid = hex(abs(hash(fn)))[2:10].upper()

                is_raw = bool(re.search(r'_(RAW|Raw)$', prefix, re.IGNORECASE))
                is_hl = bool(re.search(r'_(HIGHLIGHTED|AI_Boxed)$', prefix, re.IGNORECASE))
                prefix = re.sub(r'_(RAW|Raw|HIGHLIGHTED|AI_Boxed)$', '', prefix, flags=re.IGNORECASE)

                m_pct = re.search(r'_(\d+)PCT$', prefix, re.IGNORECASE)
                conf = 0.75
                if m_pct:
                    conf = float(m_pct.group(1)) / 100.0
                    prefix = prefix[:m_pct.start()].rstrip('_')

                lens = "Lens1"
                m_lens = re.match(r'^(Lens\d+)_?', prefix, re.IGNORECASE)
                if m_lens:
                    lens = m_lens.group(1).capitalize()
                    prefix = prefix[m_lens.end():].lstrip('_')

                parts = prefix.split('_')
                cam = parts[0].title() if parts else "Camera"
                what = '_'.join(parts[1:]) if len(parts) > 1 else "Motion"

                time_key = dt.strftime('%Y%m%d_%H%M%S')
                group_key = f"{cam}_{lens}_{time_key}_{uid}"

                if group_key not in grouped:
                    grouped[group_key] = {
                        "uid": uid,
                        "lens": lens,
                        "cam": cam,
                        "what": what,
                        "conf": conf,
                        "dt": dt,
                        "hl_path": fpath if is_hl else "",
                        "raw_path": fpath if is_raw else "",
                        "any_path": fpath,
                        "fn": fn,
                        "base": base
                    }
                else:
                    if is_hl:
                        grouped[group_key]["hl_path"] = fpath
                    if is_raw:
                        grouped[group_key]["raw_path"] = fpath

            new_entries = []
            for g in sorted(grouped.values(), key=lambda x: x["dt"].timestamp(), reverse=True):
                uid = g["uid"]
                if uid in existing_uids or g["fn"] in existing_filenames:
                    continue

                cam = g["cam"]
                lens = g["lens"]
                what = g["what"]
                conf = g["conf"]
                dt = g["dt"]
                hl_p = g["hl_path"]
                raw_p = g["raw_path"]
                main_video = hl_p or raw_p or g["any_path"]
                raw_video = raw_p or main_video

                base = g["base"]
                clean_base = re.sub(r'_(RAW|HIGHLIGHTED)', '', base)
                cand_jpg1 = base + ".jpg"
                cand_jpg2 = clean_base + ".jpg"
                snap_path = ""
                if cand_jpg1 in snap_files:
                    snap_path = os.path.join(self.snapshot_dir, cand_jpg1)
                elif cand_jpg2 in snap_files:
                    snap_path = os.path.join(self.snapshot_dir, cand_jpg2)
                elif cand_jpg1 in root_snaps:
                    snap_path = os.path.join(root_snap_dir, cand_jpg1)
                elif cand_jpg2 in root_snaps:
                    snap_path = os.path.join(root_snap_dir, cand_jpg2)

                if not snap_path and os.path.exists(main_video) and len(new_entries) < 3:
                    try:
                        cap_thumb = cv2.VideoCapture(main_video)
                        ret_t, frame_t = cap_thumb.read()
                        cap_thumb.release()
                        if ret_t and frame_t is not None:
                            snap_cand_name = os.path.splitext(os.path.basename(main_video))[0] + ".jpg"
                            snap_cand_path = os.path.join(self.snapshot_dir, snap_cand_name)
                            cv2.imwrite(snap_cand_path, frame_t, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                            if os.path.exists(snap_cand_path):
                                snap_path = snap_cand_path
                                snap_files.add(snap_cand_name)
                    except Exception:
                        pass

                what_lower = what.lower()
                if "person" in what_lower:
                    label = "Person"
                elif any(k in what_lower for k in ["dog", "cat", "animal", "horse", "elephant"]):
                    label = "Animal"
                elif any(k in what_lower for k in ["car", "vehicle", "truck", "motorcycle", "bus"]):
                    label = "Vehicle"
                else:
                    label = "Motion"

                aid = f"alert_{uid}_{int(dt.timestamp())}"
                new_entries.append({
                    "id": aid,
                    "unique_id": uid,
                    "stream_id": "",
                    "camera_name": cam,
                    "camera_ip": "",
                    "lens": lens,
                    "label": label,
                    "confidence": round(conf, 2),
                    "what_found": what,
                    "description": f"{cam} - {label} detected ({int(conf * 100)}%)",
                    "filename": os.path.basename(main_video),
                    "filename_raw": os.path.basename(raw_video),
                    "timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "time_short": dt.strftime("%H:%M:%S"),
                    "snapshot_path": snap_path,
                    "video_path": main_video,
                    "video_raw_path": raw_video,
                    "video_highlighted_path": hl_p or main_video,
                    "video_ready": True,
                    "video_recording": False
                })

                if len(new_entries) >= max_items:
                    break

            if new_entries:
                with self.lock:
                    self.alerts_list.extend(new_entries)
                    self.alerts_list.sort(key=lambda a: a.get("timestamp", ""), reverse=True)
                    self.alerts_list = self.alerts_list[:200]
                self.flush_and_save_sync()
        except Exception as e:
            print(f"[AlertManager] Error indexing media from disk: {e}")

    def _save_history(self):
        try:
            with self.lock:
                alerts_snapshot = list(self.alerts_list[:200])

            def _write_file():
                tmp_file = f"{self.history_file}.tmp_{threading.get_ident()}_{int(time.time()*1000)}"
                bak_file = f"{self.history_file}.bak"
                try:
                    with open(tmp_file, "w", encoding="utf-8") as f:
                        json.dump(alerts_snapshot, f, indent=2)
                    if os.path.exists(tmp_file):
                        replaced = False
                        for _ in range(5):
                            try:
                                os.replace(tmp_file, self.history_file)
                                replaced = True
                                break
                            except Exception:
                                time.sleep(0.05)
                        if not replaced:
                            with open(self.history_file, "w", encoding="utf-8") as f:
                                json.dump(alerts_snapshot, f, indent=2)
                            try:
                                os.remove(tmp_file)
                            except Exception:
                                pass
                        try:
                            import shutil
                            shutil.copy2(self.history_file, bak_file)
                        except Exception:
                            pass
                except Exception as e:
                    print(f"[AlertManager] Error saving history in background: {e}")
                    if os.path.exists(tmp_file):
                        try:
                            os.remove(tmp_file)
                        except Exception:
                            pass

            threading.Thread(target=_write_file, daemon=True, name="SaveAlertHistory").start()
        except Exception as e:
            print(f"[AlertManager] Failed to dispatch history save: {e}")

    def flush_and_save_sync(self):
        """Synchronously flushes history to disk so no alerts/metadata are lost on exit."""
        with self.lock:
            alerts_snapshot = list(self.alerts_list[:200])
        tmp_file = f"{self.history_file}.tmp_sync_{int(time.time()*1000)}"
        bak_file = f"{self.history_file}.bak"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(alerts_snapshot, f, indent=2)
            if os.path.exists(tmp_file):
                replaced = False
                for _ in range(5):
                    try:
                        os.replace(tmp_file, self.history_file)
                        replaced = True
                        break
                    except Exception:
                        time.sleep(0.05)
                if not replaced:
                    with open(self.history_file, "w", encoding="utf-8") as f:
                        json.dump(alerts_snapshot, f, indent=2)
                    try:
                        os.remove(tmp_file)
                    except Exception:
                        pass
                try:
                    import shutil
                    shutil.copy2(self.history_file, bak_file)
                except Exception:
                    pass
        except Exception as e:
            print(f"[AlertManager] Error saving history synchronously: {e}")
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass

    def register_completed_recording(self, alert_entry: dict):
        """
        Registers an asynchronous video recording (e.g. motion auto-record or manual clip)
        into alert history, persists it, and notifies the UI.
        """
        with self.lock:
            aid = alert_entry.get("id")
            if any(a.get("id") == aid for a in self.alerts_list):
                return
            self.alerts_list.insert(0, alert_entry)
            self.alerts_list = self.alerts_list[:200]
            self._save_history()

        self.alert_triggered.emit(alert_entry)
        self.alert_video_ready.emit(alert_entry)

    def get_recent_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.alerts_list[:limit])

    def clear_history(self):
        with self.lock:
            self.alerts_list.clear()
            self._save_history()
        self.alerts_cleared.emit()

    def get_alerts_older_than(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Scans alert history and on-disk media for entries older than the specified number of days.
        If days <= 0, retention is considered 'Never / Keep All', returning an empty list.
        Returns list of alert entries with calculated storage sizes.
        """
        if days <= 0:
            return []
        cutoff_sec = days * 86400.0
        now = datetime.now()
        expired = []

        with self.lock:
            all_known_paths = set()
            for alert in self.alerts_list:
                ts_str = alert.get("timestamp", "")
                if not ts_str:
                    continue
                try:
                    alert_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    age_sec = (now - alert_dt).total_seconds()
                    if age_sec >= cutoff_sec:
                        total_bytes = 0
                        seen_paths = set()
                        for key in ["snapshot_path", "video_path", "video_raw_path", "video_highlighted_path"]:
                            p = alert.get(key)
                            if p and p not in seen_paths and os.path.exists(p):
                                seen_paths.add(p)
                                all_known_paths.add(p)
                                try:
                                    total_bytes += os.path.getsize(p)
                                except Exception:
                                    pass
                        entry_copy = dict(alert)
                        entry_copy["total_bytes"] = total_bytes
                        entry_copy["age_days"] = int(age_sec / 86400.0)
                        expired.append(entry_copy)
                    else:
                        for key in ["snapshot_path", "video_path", "video_raw_path", "video_highlighted_path"]:
                            p = alert.get(key)
                            if p:
                                all_known_paths.add(p)
                except Exception:
                    continue

            # Also scan folders for files older than cutoff_sec not tracked in alerts_list
            for folder in [self.snapshot_dir, self.recording_dir]:
                if os.path.exists(folder):
                    for f in os.listdir(folder):
                        if f.lower() in ["alerts_history.json"] or f.startswith("."):
                            continue
                        p = os.path.join(folder, f)
                        if os.path.isfile(p) and p not in all_known_paths:
                            try:
                                mtime = os.path.getmtime(p)
                                age_sec = now.timestamp() - mtime
                                if age_sec >= cutoff_sec:
                                    sz = os.path.getsize(p)
                                    f_dt = datetime.fromtimestamp(mtime)
                                    is_mp4 = f.lower().endswith(".mp4")
                                    expired.append({
                                        "id": f"diskfile_{f}",
                                        "camera_name": "Archived Alert",
                                        "label": "Old Media",
                                        "timestamp": f_dt.strftime("%Y-%m-%d %H:%M:%S"),
                                        "filename": f,
                                        "snapshot_path": p if not is_mp4 else "",
                                        "video_path": p if is_mp4 else "",
                                        "video_highlighted_path": p if is_mp4 else "",
                                        "total_bytes": sz,
                                        "age_days": int(age_sec / 86400.0)
                                    })
                            except Exception:
                                pass

        return expired

    def remove_alerts(self, alert_ids: List[str]) -> Tuple[int, int]:
        """
        Permanently deletes specified alerts from history and removes associated
        video and snapshot files on disk.
        Returns: (num_alerts_deleted, total_bytes_freed)
        """
        target_set = set(alert_ids)
        deleted_count = 0
        bytes_freed = 0
        deleted_ids_list = []

        with self.lock:
            remaining = []
            for alert in self.alerts_list:
                aid = alert.get("id")
                if aid in target_set:
                    deleted_count += 1
                    deleted_ids_list.append(aid)
                    target_set.discard(aid)
                    seen_files = set()
                    for key in ["snapshot_path", "video_path", "video_raw_path", "video_highlighted_path"]:
                        p = alert.get(key)
                        if p and p not in seen_files and os.path.exists(p):
                            seen_files.add(p)
                            try:
                                sz = os.path.getsize(p)
                                os.remove(p)
                                bytes_freed += sz
                            except Exception as e:
                                print(f"[AlertManager] Failed to remove file {p}: {e}")
                else:
                    remaining.append(alert)

            # Handle any remaining diskfile_ IDs
            for aid in list(target_set):
                if aid.startswith("diskfile_"):
                    fn = aid.replace("diskfile_", "", 1)
                    deleted_ids_list.append(aid)
                    for folder in [self.snapshot_dir, self.recording_dir]:
                        p = os.path.join(folder, fn)
                        if os.path.exists(p):
                            try:
                                sz = os.path.getsize(p)
                                os.remove(p)
                                bytes_freed += sz
                                deleted_count += 1
                            except Exception as e:
                                print(f"[AlertManager] Failed to remove file {p}: {e}")

            self.alerts_list = remaining
            self._save_history()

        if deleted_ids_list:
            self.alerts_purged.emit(deleted_ids_list)

        return deleted_count, bytes_freed

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Calculates storage metrics:
        - Snapshots folder: total size in bytes, file count
        - Recordings folder: total size in bytes, file count
        - Total CAM720 storage used in bytes
        - Drive total, used, free space and percentage
        """
        import shutil

        def dir_stats(folder):
            total_sz = 0
            count = 0
            if os.path.exists(folder):
                for root, _, files in os.walk(folder):
                    for f in files:
                        p = os.path.join(root, f)
                        try:
                            total_sz += os.path.getsize(p)
                            count += 1
                        except Exception:
                            pass
            return total_sz, count

        snap_bytes, snap_count = dir_stats(self.snapshot_dir)
        rec_bytes, rec_count = dir_stats(self.recording_dir)
        total_cam_bytes = snap_bytes + rec_bytes

        # Drive statistics
        drive_path = os.path.splitdrive(self.recording_dir)[0] or os.path.abspath(self.recording_dir)
        if not drive_path.endswith("\\") and not drive_path.endswith("/"):
            drive_path += "\\"

        try:
            total_disk, used_disk, free_disk = shutil.disk_usage(drive_path)
            disk_pct = int((used_disk / total_disk) * 100) if total_disk > 0 else 0
        except Exception:
            total_disk, used_disk, free_disk, disk_pct = 0, 0, 0, 0

        return {
            "drive": drive_path,
            "total_disk": total_disk,
            "used_disk": used_disk,
            "free_disk": free_disk,
            "drive_total_gb": round(total_disk / (1024 ** 3), 1),
            "drive_used_gb": round(used_disk / (1024 ** 3), 1),
            "drive_free_gb": round(free_disk / (1024 ** 3), 1),
            "disk_pct": disk_pct,
            "snap_bytes": snap_bytes,
            "snap_count": snap_count,
            "rec_bytes": rec_bytes,
            "rec_count": rec_count,
            "total_cam_bytes": total_cam_bytes,
            "cam_total_bytes": total_cam_bytes,
            "cam_total_mb": round(total_cam_bytes / (1024 * 1024), 1)
        }

    def clean_temp_files(self) -> Tuple[int, int]:
        """Deletes dangling temporary encoder files (tmp_*.mp4, tmp_*.m4a). Returns (deleted_count, bytes_freed)."""
        deleted = 0
        bytes_freed = 0
        for folder in [self.recording_dir, self.snapshot_dir]:
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    if f.startswith("tmp_") and (f.endswith(".mp4") or f.endswith(".m4a")):
                        try:
                            fp = os.path.join(folder, f)
                            sz = os.path.getsize(fp)
                            os.remove(fp)
                            deleted += 1
                            bytes_freed += sz
                        except Exception:
                            pass
        return deleted, bytes_freed

    def prune_orphaned_snapshots(self, max_age_days: int = 2, max_count: int = 500) -> Tuple[int, int]:
        """
        Safely prunes unindexed / orphaned snapshot files in snapshots/alarms and snapshots/
        that are not tracked in active alerts_list.
        Keeps all active alert snapshots 100% safe.
        Returns: (files_removed, bytes_freed)
        """
        with self.lock:
            protected_paths = set()
            for a in self.alerts_list:
                for k in ["snapshot_path", "video_path", "video_raw_path", "video_highlighted_path"]:
                    p = a.get(k)
                    if p:
                        protected_paths.add(os.path.abspath(p))

        cutoff_ts = time.time() - (max_age_days * 86400.0)
        files_removed = 0
        bytes_freed = 0

        scan_dirs = [self.snapshot_dir]
        parent_snap = os.path.dirname(self.snapshot_dir)
        if os.path.exists(parent_snap) and os.path.abspath(parent_snap) != os.path.abspath(self.snapshot_dir):
            scan_dirs.append(parent_snap)

        for s_dir in scan_dirs:
            if not os.path.isdir(s_dir):
                continue
            candidates = []
            try:
                for entry in os.scandir(s_dir):
                    if not entry.is_file():
                        continue
                    fn_lower = entry.name.lower()
                    if not fn_lower.endswith((".jpg", ".jpeg", ".png")):
                        continue
                    ap = os.path.abspath(entry.path)
                    if ap in protected_paths:
                        continue
                    try:
                        st = entry.stat()
                        candidates.append((ap, st.st_mtime, st.st_size))
                    except Exception:
                        pass
            except Exception as e:
                print(f"[AlertManager] Error scanning for orphaned snapshots in {s_dir}: {e}")
                continue

            # Sort oldest first for deletion
            candidates.sort(key=lambda x: x[1])
            total_cand = len(candidates)

            for ap, mtime, sz in candidates:
                should_remove = (mtime < cutoff_ts) or ((total_cand - files_removed) > max_count)
                if should_remove:
                    try:
                        os.remove(ap)
                        files_removed += 1
                        bytes_freed += sz
                    except Exception:
                        pass

        if files_removed > 0:
            print(f"[AlertManager] Pruned {files_removed} orphaned snapshots, freeing {bytes_freed / (1024 * 1024):.1f} MB.")
        return files_removed, bytes_freed

    def prune_old_recordings(self, max_age_days: int = 7) -> Tuple[int, int]:
        """
        Prunes recordings older than max_age_days from recordings directory and recordings/alarms.
        Protects top 50 most recent alerts in alerts_list.
        Returns: (files_removed, bytes_freed)
        """
        with self.lock:
            protected_paths = set()
            for a in self.alerts_list[:50]:
                for k in ["snapshot_path", "video_path", "video_raw_path", "video_highlighted_path"]:
                    p = a.get(k)
                    if p:
                        protected_paths.add(os.path.abspath(p))

        cutoff_ts = time.time() - (max_age_days * 86400.0)
        files_removed = 0
        bytes_freed = 0

        scan_dirs = [self.recording_dir]
        parent_rec = os.path.dirname(self.recording_dir)
        if os.path.exists(parent_rec) and os.path.abspath(parent_rec) != os.path.abspath(self.recording_dir):
            scan_dirs.append(parent_rec)

        for s_dir in scan_dirs:
            if not os.path.isdir(s_dir):
                continue
            try:
                for entry in os.scandir(s_dir):
                    if not entry.is_file():
                        continue
                    fn_lower = entry.name.lower()
                    if not fn_lower.endswith((".mp4", ".mkv", ".avi", ".mov")):
                        continue
                    ap = os.path.abspath(entry.path)
                    if ap in protected_paths:
                        continue
                    try:
                        st = entry.stat()
                        if st.st_mtime < cutoff_ts:
                            os.remove(ap)
                            files_removed += 1
                            bytes_freed += st.st_size
                    except Exception:
                        pass
            except Exception as e:
                print(f"[AlertManager] Error pruning recordings in {s_dir}: {e}")

        # Clean up any removed entries from alerts_list
        if files_removed > 0:
            with self.lock:
                self.alerts_list = [
                    a for a in self.alerts_list
                    if not (a.get("video_path") and not os.path.exists(a["video_path"]))
                ]
                self._save_history()
            print(f"[AlertManager] Pruned {files_removed} old recordings, freeing {bytes_freed / (1024 * 1024 * 1024):.2f} GB.")
        return files_removed, bytes_freed

    def enforce_quota(self, max_quota_gb: float) -> Tuple[int, int]:
        """
        Enforces maximum storage quota limit. If total CAM720 storage exceeds max_quota_gb,
        intelligently prunes older unindexed files and archived alerts while strictly
        protecting recent active incident alerts (at least 100 most recent alerts are never touched).
        Returns: (files_removed, bytes_freed)
        """
        if max_quota_gb <= 0:
            return 0, 0
        max_bytes = int(max_quota_gb * (1024 ** 3))
        stats = self.get_storage_stats()
        cur_bytes = stats["total_cam_bytes"]
        if cur_bytes <= max_bytes:
            return 0, 0

        bytes_to_free = cur_bytes - max_bytes
        freed = 0
        files_removed = 0

        # Phase 1: Prune unindexed / orphaned files on disk older than 24h first
        # This frees gigabytes of space without touching any active alert in the UI
        with self.lock:
            protected_paths = set()
            for a in self.alerts_list:
                for k in ["snapshot_path", "video_path", "video_raw_path", "video_highlighted_path"]:
                    p = a.get(k)
                    if p:
                        protected_paths.add(os.path.abspath(p))

        now_ts = time.time()
        for folder in [self.recording_dir, self.snapshot_dir]:
            if not os.path.exists(folder):
                continue
            folder_files = []
            for f in os.listdir(folder):
                if f.lower() in ["alerts_history.json", "alerts_history.json.bak"] or f.startswith("."):
                    continue
                fp = os.path.abspath(os.path.join(folder, f))
                if fp not in protected_paths and os.path.isfile(fp):
                    try:
                        folder_files.append((fp, os.path.getmtime(fp), os.path.getsize(fp)))
                    except Exception:
                        pass
            folder_files.sort(key=lambda x: x[1])
            for fp, mtime, sz in folder_files:
                if (now_ts - mtime) > 86400:
                    try:
                        os.remove(fp)
                        freed += sz
                        files_removed += 1
                        if freed >= bytes_to_free:
                            break
                    except Exception:
                        pass
            if freed >= bytes_to_free:
                break

        # Phase 2: If still exceeding quota, prune ONLY alerts beyond the top 100 most recent alerts
        if freed < bytes_to_free:
            to_delete_ids = []
            with self.lock:
                if len(self.alerts_list) > 100:
                    candidates = list(self.alerts_list[100:])
                    candidates.sort(key=lambda a: a.get("timestamp", ""))
                    for a in candidates:
                        to_delete_ids.append(a.get("id"))
                        for k in ["snapshot_path", "video_path", "video_raw_path", "video_highlighted_path"]:
                            p = a.get(k)
                            if p and os.path.exists(p):
                                try:
                                    freed += os.path.getsize(p)
                                except Exception:
                                    pass
                        if freed >= bytes_to_free:
                            break

            if to_delete_ids:
                del_count, del_bytes = self.remove_alerts(to_delete_ids)
                files_removed += del_count

        return files_removed, freed

    def trigger_alert(
        self,
        stream_id: str,
        camera_name: str,
        camera_ip: str,
        rtsp_url: str,
        label: str,
        confidence: float,
        frame: Optional[np.ndarray] = None,
        lens_tag: str = "Lens1",
        short_desc: str = "",
        what_found: str = "",
        worker: Optional[Any] = None,
        trigger_reason: str = ""
    ) -> Dict[str, Any]:
        """
        Executes alert handling:
        - Saves instant 100% quality native snapshot.
        - Spawns background recorder producing BOTH:
          1. HIGHLIGHTED version with detection boxes & labels.
          2. RAW version with pristine native video stream.
        - Standardized naming format: TAG_LENS_CAMERA_WHAT IT FOUND_ DATE _ TIME _ID
        - Notifies UI with alert payload including short description.
        """
        if not self.app_settings.get("master_alerts_enabled", True):
            return {}
        now = datetime.now()
        time_display = now.strftime("%H:%M:%S")

        if not trigger_reason:
            if label.upper() == "MOTION":
                trigger_reason = "Motion threshold reached"
            else:
                trigger_reason = f"AI {label.title()} ({int(confidence * 100)}%)"

        # Smart Alert Deduplication & Fusion:
        now_ts = now.timestamp()
        clean_lbl = label.upper().strip()
        cam_key = f"{camera_name}_{lens_tag}"

        if not hasattr(self, "_recent_alert_dedup"):
            self._recent_alert_dedup = {}

        # Prune entries older than 60s
        cam_history = [h for h in self._recent_alert_dedup.get(cam_key, []) if (now_ts - h["ts"]) < 60.0]

        # If this is a generic MOTION alert and an AI alert (PERSON, VEHICLE, ANIMAL) occurred in last 25s, drop duplicate motion
        if clean_lbl == "MOTION":
            recent_ai = [h for h in cam_history if h["label"] in ("PERSON", "VEHICLE", "ANIMAL") and (now_ts - h["ts"]) < 25.0]
            if recent_ai:
                return {}

        # If this is an AI alert and the same AI label alerted in last 12s on this camera, drop duplicate
        if clean_lbl in ("PERSON", "VEHICLE", "ANIMAL"):
            recent_same = [h for h in cam_history if h["label"] == clean_lbl and (now_ts - h["ts"]) < 12.0]
            if recent_same:
                return {}

        cam_history.append({"ts": now_ts, "label": clean_lbl})
        self._recent_alert_dedup[cam_key] = cam_history

        if not what_found:
            clean_label = label.upper().replace(":", "").replace(" ", "_").strip()
            conf_pct = int(confidence * 100)
            what_found = f"{clean_label}_{conf_pct}PCT"

        if not short_desc:
            short_desc = f"{label.title()} ({int(confidence * 100)}%) detected"

        # Construct file basenames matching TAG_LENS_CAMERA_WHAT IT FOUND_ DATE _ TIME _ID
        snapshot_filename, unique_id = format_media_filename(
            tag="ALARM",
            lens=lens_tag,
            camera=camera_name,
            what_it_found=what_found,
            ext="jpg",
            dt=now
        )
        video_raw_filename, _ = format_media_filename(
            tag="ALARM",
            lens=lens_tag,
            camera=camera_name,
            what_it_found=f"{what_found}_RAW",
            ext="mp4",
            dt=now,
            unique_id=unique_id
        )
        video_hl_filename, _ = format_media_filename(
            tag="ALARM",
            lens=lens_tag,
            camera=camera_name,
            what_it_found=f"{what_found}_HIGHLIGHTED",
            ext="mp4",
            dt=now,
            unique_id=unique_id
        )

        alert_id = f"alert_{unique_id}_{int(now.timestamp())}"
        snapshot_path = os.path.join(self.snapshot_dir, snapshot_filename)
        video_raw_path = os.path.join(self.recording_dir, video_raw_filename)
        video_hl_path = os.path.join(self.recording_dir, video_hl_filename)

        # 1. Save Native High-Res Snapshot at 100% Quality
        if frame is not None:
            try:
                cv2.imwrite(snapshot_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
            except Exception as e:
                print(f"[AlertManager] Snapshot save failed: {e}")

        # 2. Build alert metadata entry
        alert_entry = {
            "id": alert_id,
            "unique_id": unique_id,
            "stream_id": stream_id,
            "camera_name": camera_name,
            "camera_ip": camera_ip,
            "lens": lens_tag,
            "label": label,
            "confidence": round(float(confidence), 2),
            "what_found": what_found,
            "description": short_desc,
            "trigger_reason": trigger_reason,
            "filename": video_hl_filename,
            "filename_raw": video_raw_filename,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "time_short": time_display,
            "snapshot_path": snapshot_path if os.path.exists(snapshot_path) else "",
            "video_path": video_hl_path,
            "video_highlighted_path": video_hl_path,
            "video_raw_path": video_raw_path,
            "video_ready": False,
            "video_recording": True
        }

        with self.lock:
            self.alerts_list.insert(0, alert_entry)
            self._save_history()

        # Emit immediate alert (UI displays banner and card with short description)
        self.alert_triggered.emit(alert_entry)

        # Dispatch immediate mobile push notification (ntfy / Telegram / Discord)
        if self.notification_dispatcher:
            self.notification_dispatcher.send_alert(alert_entry)

        # 3. Start high-quality video recording
        if worker is not None and hasattr(worker, "start_alert_clip_session"):
            dual_clips = self.app_settings.get("record_dual_clips", True)
            record_audio = self.app_settings.get("record_audio_in_clips", False)
            is_person = ("PERSON" in label.upper())
            clip_max_dur = float(self.app_settings.get("alert_clip_duration_sec", 15.0))
            clip_min_dur = 6.0 if is_person else float(self.app_settings.get("alert_clip_min_sec", 6.0))
            quiet_timeout = 3.0 if is_person else float(self.app_settings.get("alert_clip_quiet_timeout_sec", 3.0))
            session = AlertClipSession(
                manager=self,
                stream_id=stream_id,
                rtsp_url=rtsp_url,
                alert_entry=alert_entry,
                raw_output_path=video_raw_path,
                highlighted_output_path=video_hl_path,
                fps=getattr(worker, "fps", 15.0) or 15.0,
                max_duration_sec=clip_max_dur,
                min_duration_sec=clip_min_dur,
                quiet_timeout_sec=quiet_timeout,
                record_dual_clips=dual_clips,
                record_audio=record_audio,
                trigger_frame=frame.copy() if frame is not None else None
            )
            worker.start_alert_clip_session(session)
        elif rtsp_url:
            threading.Thread(
                target=self._record_10s_clip_worker,
                args=(stream_id, rtsp_url, video_raw_path, video_hl_path, alert_entry),
                daemon=True,
                name=f"AlertRec_{stream_id}"
            ).start()
        else:
            alert_entry["video_recording"] = False
            alert_entry["video_ready"] = False
            alert_entry["video_failed"] = True
            with self.lock:
                self._save_history()
            self.alert_video_ready.emit(alert_entry)

        return alert_entry

    def _record_10s_clip_worker(self, stream_id: str, rtsp_url: str, raw_output: str, hl_output: str, alert_entry: dict):
        """
        Fallback direct FFmpeg recorder:
        Captures pristine stream from RTSP with smoothed wallclock timestamps and resampled audio.
        """
        with self.lock:
            if stream_id in self.active_recordings:
                proc = self.active_recordings[stream_id]
                if proc.poll() is None:
                    return

        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            creationflags = subprocess.CREATE_NO_WINDOW

        cmd = [
            "ffmpeg",
            "-y",
            "-use_wallclock_as_timestamps", "1",
            "-fflags", "+genpts+discardcorrupt",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-t", "10",
            "-map", "0:v:0",
            "-map", "0:a?",
            "-c:v", "copy",
            "-af", "aresample=async=1000:first_pts=0",
            "-c:a", "aac",
            "-b:a", "128k",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            raw_output
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            with self.lock:
                self.active_recordings[stream_id] = proc

            proc.wait(timeout=14.0)

        except Exception as e:
            print(f"[AlertManager] FFmpeg fallback recording error for {stream_id}: {e}")
        finally:
            with self.lock:
                self.active_recordings.pop(stream_id, None)

            if os.path.exists(raw_output) and os.path.getsize(raw_output) > 1024:
                try:
                    from core.video_slate import prepend_slate_to_video_file
                    snap_p = alert_entry.get("snapshot_path", "")
                    prepend_slate_to_video_file(
                        video_path=raw_output,
                        alert_type=alert_entry.get("label", "ALERT"),
                        camera_name=alert_entry.get("camera_name", "Camera"),
                        lens_name=alert_entry.get("lens", "Main Lens"),
                        timestamp=alert_entry.get("timestamp", ""),
                        trigger_reason=alert_entry.get("trigger_reason", "") or alert_entry.get("description", ""),
                        trigger_image_path=snap_p,
                        confidence=alert_entry.get("confidence", None),
                        duration_sec=0.5
                    )
                except Exception as prep_err:
                    print(f"[AlertManager] Fallback slate prepend error: {prep_err}")

                # Also create highlighted output as copy if not already generated
                if not os.path.exists(hl_output):
                    try:
                        import shutil
                        shutil.copy2(raw_output, hl_output)
                    except Exception:
                        pass

                alert_entry["video_ready"] = True
                alert_entry["video_recording"] = False
                alert_entry["video_raw_path"] = raw_output
                alert_entry["video_highlighted_path"] = hl_output if os.path.exists(hl_output) else raw_output
                alert_entry["video_path"] = alert_entry["video_highlighted_path"]

                with self.lock:
                    self._save_history()
                self.alert_video_ready.emit(alert_entry)
            else:
                alert_entry["video_recording"] = False
                alert_entry["video_ready"] = False
                alert_entry["video_failed"] = True
                with self.lock:
                    self._save_history()
                self.alert_video_ready.emit(alert_entry)
