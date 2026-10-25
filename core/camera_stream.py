from core.capture_process import IsolatedCapture
import cv2
import time
import os
import re
import uuid
import threading
import numpy as np
from datetime import datetime
import collections
import concurrent.futures
from typing import Optional, List, Dict, Any, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtGui import QImage

from core.motion_detector import MotionDetector
from core.ai_detector import AIDetector, AIDetection, generate_detection_description, TemporalDetectionTracker
from core.wind_filter import WindShakeFilter
from core.alert_manager import format_media_filename
from core.async_recorder import AsyncVideoRecorder

# Configure FFmpeg options for OpenCV with fast timeout, zero latency, and thread limits
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|stimeout;5000000|timeout;5000000|fflags;nobuffer|flags;low_delay|max_delay;0|buffer_size;102400|threads;1"
)


class StreamStatus:
    IDLE = "IDLE"
    CONNECTING = "CONNECTING"
    LIVE = "LIVE"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


class QualityMode:
    ULTRA_MAX = "MAX"  # Pristine 2K/4K Native Resolution + Studio App Clarity Engine
    ULTRA_2K = "2K"    # Full Native Raw Stream (Uncompressed)
    MID_HD = "MID"     # 720p HD (Balanced CPU)
    LOW_SD = "LOW"     # 360p Sub-stream (Low Bandwidth)


class NightVisionMode:
    OFF = "off"
    AUTO = "auto"
    COLOR_BOOST = "color_boost"
    BW_IR = "bw_ir"
    COLOR_NIGHT = "color_night"

    ALL = [OFF, AUTO, COLOR_BOOST, BW_IR, COLOR_NIGHT]


class CameraStreamWorker(QThread):
    """
    Dedicated background worker thread for capturing RTSP/ONVIF streams.
    Includes Quality switching (2K / Mid / Low Sub-stream), real-time Motion Detection,
    AI Person and Animal Recognition with Alarms, Multi-mode Night Vision (Auto, Color Boost, BW IR),
    snapshots, and MP4 recording.
    """
    frame_ready = pyqtSignal(str, QImage, int, int, float)  # stream_id, qimage, width, height, fps
    status_changed = pyqtSignal(str, str, str)  # stream_id, status, message
    stats_updated = pyqtSignal(str, float, int, int)  # stream_id, fps, width, height
    recording_status = pyqtSignal(str, bool, str)  # stream_id, is_recording, elapsed_str
    snapshot_saved = pyqtSignal(str, str)  # stream_id, filepath
    motion_event = pyqtSignal(str, bool, int)  # stream_id, is_motion, num_targets
    quality_changed = pyqtSignal(str, str)  # stream_id, quality_mode
    ai_alarm_detected = pyqtSignal(str, str, str, float, object)  # stream_id, stream_name, target_desc, confidence, frame
    wind_shake_detected = pyqtSignal(str, bool)  # stream_id, is_shaking
    trigger_event = pyqtSignal(str, bool, str, dict)  # stream_id, is_active, trigger_reason, details

    def __init__(self, stream_id: str, name: str, main_url: str, sub_url: str = "", parent=None):
        super().__init__(parent)
        self.stream_id = stream_id
        self.stream_name = name
        self.main_url = main_url
        self.sub_url = sub_url or self._derive_sub_url(main_url)
        self.current_url = self.main_url
        self.quality_mode = QualityMode.ULTRA_2K
        self.camera_ip = ""
        self.camera_name = ""
        self.lens_tag = "Lens1"
        self.alert_manager = None

        self._capture = None
        self._running = False
        self._paused = False
        self._reconnect_requested = False

        # Motion Detection
        self.alerts_armed = True
        self.motion_detection_enabled = True
        self.auto_record_on_motion = False
        self.detector = MotionDetector(sensitivity=5, min_area=2800)

        # Wind Shake Rejection Filter (automatically shields cameras like Fata from wind gusts)
        self.wind_filter = WindShakeFilter(tolerance=1.1, enabled=True)
        self.is_wind_shaking = False

        # AI Person & Animal Detection & Alarms
        self.ai_detection_enabled = True
        self.ai_alarm_cooldown = 4.0  # seconds between alarm triggers
        self._last_ai_alarm_time = 0.0
        self._last_motion_alarm_time = 0.0
        self.motion_alarm_cooldown = 4.0
        self.ai_conf_threshold = 0.38
        self.afara_person_threshold = 0.50
        self.afara_animal_threshold = 0.50
        self.notify_person = True
        self.notify_animal = True
        self.notify_vehicle = True
        self.notify_motion = True
        self._frame_count = 0
        self._last_ai_detections = []
        self.ai_detector = AIDetector()
        self.ai_tracker = TemporalDetectionTracker(
            confirm_delay=0.25,
            static_count_threshold=150,
            static_time_threshold=300.0,
            persistence_timeout=2.0,
            position_tolerance_px=45.0,
            alpha_smooth=0.75,
            min_hits_for_confirm=2
        )
        self._alerted_track_ids: Dict[int, float] = {}
        self.vehicle_conf_threshold = 0.38
        self.alarm_snapshot_dir = os.path.join("snapshots", "alarms")
        os.makedirs(self.alarm_snapshot_dir, exist_ok=True)

        # Asynchronous non-blocking AI detection executor (Zero Latency Video)
        self._ai_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix=f"AI_{self.stream_id}"
        )
        self._ai_future: Optional[concurrent.futures.Future] = None
        self._last_ai_infer_time = 0.0

        # Multi-mode Night Vision Engine (Off, Auto Low-Light, Color Boost, B&W IR Boost)
        self.night_mode = NightVisionMode.OFF
        self.night_gamma = 1.8
        self.night_contrast = 3.0
        self.night_auto_threshold = 45.0
        self._gamma_lut = self._build_gamma_lut(self.night_gamma)
        self.clahe = cv2.createCLAHE(clipLimit=self.night_contrast, tileGridSize=(8, 8))
        self._color_night_lut = self._build_color_night_lut()

        # Individual Camera Orientation & OSD Overlays (Hardware timestamp already embedded in stream)
        self.flip_horizontal = False
        self.flip_vertical = False
        self.osd_timestamp = False
        self.osd_camera_name = False

        # Performance Throttling & CPU Optimization
        self.display_fps_cap = 25
        self.configured_display_fps = 25
        self.min_render_interval = 0.0
        self._last_render_time = 0.0
        self._gui_rendering_paused = False
        self._background_throttle = False
        self.is_solo_view = False
        self.ai_skip_frames = 6
        self.ai_motion_gated_only = False
        self.motion_skip_frames = 1
        self._motion_frame_count = 0
        self.motion_downscale_width = 480
        if hasattr(self.detector, "downscale_width"):
            self.detector.downscale_width = 480

        # Recording state
        self._recording = False
        self._motion_triggered_rec = False
        self._async_recorder: Optional[AsyncVideoRecorder] = None
        self._record_filename = None
        self._record_start_time = 0
        self._last_motion_detected_time = 0.0
        self._output_record_dir = "recordings"
        self.configured_recording_dir = "recordings"

        # Snapshot state
        self._snapshot_requested = False
        self._snapshot_dir = "snapshots"
        self.configured_snapshot_dir = "snapshots"

        # Motion Overlay and Tracking Description for Recordings & Alerts
        self.motion_overlay_in_recordings = True
        self._current_motion_desc = None
        self._current_motion_boxes = []
        self._current_motion_primary_box = None
        self._current_motion_time = 0.0

        # Alert Dual-Version Recording Sessions & Pre-alarm buffer
        self.record_dual_clips = True
        self.show_ai_overlays = True
        self._active_alert_sessions = []
        self._is_alert_recording = False
        self.pre_alarm_buffer_sec = 3.0
        self._frame_ring_buffer = collections.deque(maxlen=30)
        self._last_ring_buffer_time = 0.0

        # Mobile Web Streaming Cache & Real-Time Frame Access
        self._latest_bgr_frame: Optional[np.ndarray] = None
        self._latest_raw_bgr_frame: Optional[np.ndarray] = None
        self._jpeg_lock = threading.Lock()
        self._latest_jpeg_quality = None
        self._latest_raw_jpeg_quality = None
        self._latest_jpeg_cache: Optional[bytes] = None
        self._latest_jpeg_time: float = 0.0
        self._latest_raw_jpeg_cache: Optional[bytes] = None
        self._latest_raw_jpeg_time: float = 0.0
        self._web_streaming_active: bool = False

        # Stream metrics & Watchdog health tracking
        self.width = 0
        self.height = 0
        self.fps = 0.0
        self.status = StreamStatus.IDLE
        self._last_frame_received_time = time.time()
        self._last_watchdog_reconnect_time = 0.0

        # Movement View & Trigger Diagnostics
        self.movement_view_enabled = False
        self.latest_trigger_reason = "Standby"
        self._record_trigger_reason = "Motion Activity"

        # Exclusion / Ignore Zones (Normalized [x1, y1, x2, y2] 0.0 - 1.0)
        self.exclusion_zones: List[List[float]] = []

    def set_exclusion_zones(self, zones: List[List[float]]):
        """Sets normalized [x1, y1, x2, y2] zones (0.0 to 1.0) to ignore from AI tracking & motion."""
        self.exclusion_zones = [list(z) for z in (zones or []) if len(z) >= 4]
        if hasattr(self, "ai_tracker") and self.ai_tracker:
            self.ai_tracker.set_exclusion_zones(self.exclusion_zones)
        if hasattr(self, "detector") and self.detector:
            self.detector.set_exclusion_zones(self.exclusion_zones)

    def set_movement_view(self, enabled: bool):
        """Toggles Movement View diagnostic radar and trigger HUD on this stream."""
        self.movement_view_enabled = bool(enabled)
        if hasattr(self, "detector") and hasattr(self.detector, "set_movement_view"):
            self.detector.set_movement_view(enabled)

    def start_alert_clip_session(self, session):
        """Attaches an AlertClipSession and flushes up to 3 seconds of pre-alarm frames."""
        try:
            now = time.time()
            cutoff = now - self.pre_alarm_buffer_sec
            buffered = [(data, stamp) for data, stamp in list(self._frame_ring_buffer)
                        if stamp >= cutoff and self.pre_alarm_buffer_sec > 0]
            session.set_prebuffer(buffered)
            self._active_alert_sessions.append(session)
            self._is_alert_recording = True
        except Exception as e:
            print(f"[CameraStreamWorker] Error starting alert session: {e}")

    def _derive_sub_url(self, main_url: str) -> str:
        """Derives sub-stream URL from main stream if not explicitly set."""
        if not main_url:
            return ""
        if "/live/ch00_0" in main_url:
            return main_url.replace("/live/ch00_0", "/live/ch00_1")
        elif "/live/ch01_0" in main_url:
            return main_url.replace("/live/ch01_0", "/live/ch01_1")
        elif "/stream0" in main_url:
            return main_url.replace("/stream0", "/stream1")
        elif "subtype=0" in main_url:
            return main_url.replace("subtype=0", "subtype=1")
        return main_url

    def set_quality(self, mode: str):
        """
        Dynamically changes stream quality:
        - ULTRA_MAX: Pristine Native (2304x1296) + Studio App Clarity Engine (Phone App Look)
        - ULTRA_2K: Native main stream (2304x1296) Raw
        - MID_HD: Downsampled 720p balanced stream
        - LOW_SD: Native sub-stream (640x360) for low bandwidth
        """
        if mode == self.quality_mode:
            return

        old_mode = self.quality_mode
        self.quality_mode = mode

        # Determine target URL: LOW_SD uses sub_url if available; MAX, 2K, MID use main_url
        if mode == QualityMode.LOW_SD and self.sub_url:
            target_url = self.sub_url
        else:
            target_url = self.main_url

        if target_url != self.current_url:
            self.current_url = target_url
            self._reconnect_requested = True
            capture = self._capture
            if capture is not None:
                capture.interrupt()
        
        self.quality_changed.emit(self.stream_id, mode)

    def _apply_app_clarity(self, frame: np.ndarray) -> np.ndarray:
        """
        Studio App Clarity Engine:
        Applies subtle unsharp masking and micro-contrast LUT curve to match smartphone
        surveillance app ISP rendering (crisp text, tack-sharp optic edges, rich detail).
        """
        if not hasattr(self, "_clarity_kernel"):
            self._clarity_kernel = np.array([
                [ 0,    -0.20,  0   ],
                [-0.20,  1.80, -0.20],
                [ 0,    -0.20,  0   ]
            ], dtype=np.float32)
            self._clarity_lut = np.array([
                np.clip((i / 255.0) ** 0.95 * 255.0 + (5 if i > 30 else 0), 0, 255)
                for i in range(256)
            ], dtype=np.uint8)

        sharpened = cv2.filter2D(frame, -1, self._clarity_kernel)
        return cv2.LUT(sharpened, self._clarity_lut)

    def has_recent_frame(self, max_age: float = 10.0) -> bool:
        return (self._running and not self._paused and self.status == StreamStatus.LIVE
                and 0 <= time.time() - self._last_frame_received_time < max_age)

    def is_feed_stalled(self, threshold: float = 6.0) -> bool:
        """Returns True if the stream claims to be LIVE but has not received any frame for threshold seconds."""
        if not self._running or self._paused or self.status != StreamStatus.LIVE:
            return False
        capture = self._capture
        threshold = max(threshold, getattr(capture, "read_timeout", 8.0) + 2.0)
        return (time.time() - self._last_frame_received_time) > threshold

    def request_reconnect(self, reason: str = ""):
        """Safely signals the streaming thread to cleanly break and reconnect."""
        if reason:
            print(f"[{self.stream_name}] Reconnect requested: {reason}")
        self._reconnect_requested = True
        capture = self._capture
        if capture is not None:
            capture.interrupt()

    def update_connection_details(self, main_url: str, sub_url: str = "", ip: str = "", name: str = ""):
        """Updates connection credentials/URLs and triggers an immediate live reconnect."""
        if main_url:
            self.main_url = main_url
        self.sub_url = sub_url or self._derive_sub_url(self.main_url)
        if ip:
            self.camera_ip = ip
        if name:
            self.stream_name = name
        if self.quality_mode == QualityMode.LOW_SD and self.sub_url:
            self.current_url = self.sub_url
        else:
            self.current_url = self.main_url
        self._reconnect_requested = True
        capture = self._capture
        if capture is not None:
            capture.interrupt()

    def set_web_streaming_active(self, active: bool = True):
        """Notifies the worker that a web/mobile client is streaming this camera."""
        self._web_streaming_active = active

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Returns the most recent decoded video frame as a BGR numpy array."""
        if self._latest_bgr_frame is not None:
            return self._latest_bgr_frame.copy()
        return None

    def get_latest_jpeg(self, quality: int = 65, raw: bool = False) -> Optional[bytes]:
        """Share JPEG work across viewers while respecting their requested quality."""
        quality = max(20, min(95, int(quality)))
        # Only HTTP viewers acquire this lock; capture/display never wait for encoding.
        with self._jpeg_lock:
            frame = self._latest_raw_bgr_frame if raw else self._latest_bgr_frame
            if frame is None:
                frame = self._latest_bgr_frame if raw else self._latest_raw_bgr_frame
            if frame is None:
                return None
            prefix = "_latest_raw_jpeg" if raw else "_latest_jpeg"
            cached = getattr(self, prefix + "_cache")
            if (cached is not None and getattr(self, prefix + "_quality") == quality
                    and time.monotonic() - getattr(self, prefix + "_time") < 0.030):
                return cached
            try:
                ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
                if ok:
                    encoded = buf.tobytes()
                    setattr(self, prefix + "_cache", encoded)
                    setattr(self, prefix + "_quality", quality)
                    setattr(self, prefix + "_time", time.monotonic())
                    return encoded
            except Exception:
                pass
        return None

    @staticmethod
    def _build_gamma_lut(gamma: float) -> np.ndarray:
        inv_gamma = 1.0 / max(0.1, gamma)
        table = [int(((i / 255.0) ** inv_gamma) * 255.0) for i in range(256)]
        return np.array(table, dtype=np.uint8)

    @staticmethod
    def _build_color_night_lut() -> np.ndarray:
        """
        Builds a realistic 256-entry 3-channel (BGR) twilight/night colorization LUT.
        Smoothly maps grayscale luminance to realistic nocturnal chromaticity:
        - 0..45: Deep midnight navy / cool shadow
        - 46..120: Neutral earthy slate / nocturnal foliage
        - 121..190: Warm ambient streetlight glow (3000K amber)
        - 191..255: Crisp bright highlight / incandescent light
        """
        lut = np.zeros((256, 1, 3), dtype=np.uint8)
        for i in range(256):
            norm = i / 255.0
            if norm < 0.2:
                t = norm / 0.2
                b = int(32 + t * 38)
                g = int(20 + t * 35)
                r = int(14 + t * 24)
            elif norm < 0.55:
                t = (norm - 0.2) / 0.35
                b = int(70 + t * 35)
                g = int(55 + t * 65)
                r = int(38 + t * 84)
            elif norm < 0.85:
                t = (norm - 0.55) / 0.30
                b = int(105 + t * 60)
                g = int(120 + t * 75)
                r = int(122 + t * 105)
            else:
                t = (norm - 0.85) / 0.15
                b = int(165 + t * 90)
                g = int(195 + t * 60)
                r = int(227 + t * 28)
            lut[i, 0, 0] = min(255, max(0, b))
            lut[i, 0, 1] = min(255, max(0, g))
            lut[i, 0, 2] = min(255, max(0, r))
        return lut

    def set_color_night_mode(self, enabled: bool):
        """Forces full color night vision mode."""
        self.night_mode = NightVisionMode.COLOR_NIGHT if enabled else NightVisionMode.OFF

    def set_night_boost(self, enabled: bool):
        """Legacy / simple toggle support."""
        self.night_mode = NightVisionMode.COLOR_BOOST if enabled else NightVisionMode.OFF

    def set_night_vision(self, mode: str, gamma: float = 1.8, contrast: float = 3.0, auto_threshold: float = 45.0):
        """
        Advanced multi-mode night vision configuration:
        - mode: 'off', 'auto', 'color_boost', 'bw_ir'
        - gamma: shadow luminance lifting curve (0.5 to 3.5)
        - contrast: CLAHE clip limit (1.0 to 8.0)
        - auto_threshold: low-light luminance trigger level (10.0 to 120.0)
        """
        self.night_mode = str(mode).lower()
        self.night_gamma = max(0.5, min(3.5, float(gamma)))
        self.night_contrast = max(1.0, min(8.0, float(contrast)))
        self.night_auto_threshold = max(10.0, min(120.0, float(auto_threshold)))
        self._gamma_lut = self._build_gamma_lut(self.night_gamma)
        self.clahe = cv2.createCLAHE(clipLimit=self.night_contrast, tileGridSize=(8, 8))

    def set_video_transform(self, flip_h: bool = False, flip_v: bool = False, osd_time: bool = False, osd_name: bool = True):
        """Controls hardware mirror flips (ceiling mounts) and HUD OSD text overlays."""
        self.flip_horizontal = flip_h
        self.flip_vertical = flip_v
        self.osd_timestamp = osd_time
        self.osd_camera_name = osd_name

    def apply_camera_settings(self, settings: dict):
        """Applies individual camera configuration overrides on the fly."""
        if not settings:
            return

        if "quality" in settings:
            self.set_quality(settings["quality"])

        self.alerts_armed = bool(settings.get("master_alerts_enabled", True))

        # Night vision
        n_mode = settings.get("night_mode", settings.get("night_vision_mode"))
        if n_mode is not None:
            gamma = settings.get("night_gamma", 1.8)
            contrast = settings.get("night_contrast", 3.0)
            auto_th = settings.get("night_auto_threshold", 45.0)
            self.set_night_vision(n_mode, gamma, contrast, auto_th)
        elif "night_boost" in settings:
            self.set_night_boost(settings["night_boost"])

        # Motion detection & Movement view
        m_en = self.alerts_armed and settings.get("motion_enabled", self.motion_detection_enabled)
        m_sens = settings.get("motion_sensitivity", 5)
        m_min_area = settings.get("motion_min_area", getattr(self.detector, "min_area", 2800))
        m_confirm_delay = settings.get("motion_confirm_delay", getattr(self.detector, "confirm_delay", 1.2))
        m_foliage = settings.get("motion_foliage_filter", getattr(self.detector, "foliage_filter_enabled", True))
        m_auto_rec = settings.get("auto_record_on_motion", self.auto_record_on_motion)
        self.set_motion_detection(m_en, sensitivity=m_sens, auto_record=m_auto_rec)
        if hasattr(self.detector, "update_settings"):
            self.detector.update_settings(
                sensitivity=m_sens,
                min_area=m_min_area,
                confirm_delay=m_confirm_delay,
                motion_cooldown=settings.get("motion_hold_sec", 3.0),
                foliage_filter_enabled=m_foliage
            )
        if "movement_view_enabled" in settings:
            self.set_movement_view(settings["movement_view_enabled"])

        # AI Object Detection
        ai_en = self.alerts_armed and settings.get("ai_detection_enabled", self.ai_detection_enabled)
        ai_p = settings.get("ai_detect_person", True)
        ai_a = settings.get("ai_detect_animal", True)
        ai_v = settings.get("ai_detect_vehicle", True)
        ai_c = float(settings.get("ai_conf_threshold", 0.38))
        self.ai_conf_threshold = ai_c
        if "afara_person_threshold" in settings:
            self.afara_person_threshold = float(settings["afara_person_threshold"])
        if "afara_animal_threshold" in settings:
            self.afara_animal_threshold = float(settings["afara_animal_threshold"])
        if "notify_person" in settings:
            self.notify_person = bool(settings["notify_person"])
        if "notify_animal" in settings:
            self.notify_animal = bool(settings["notify_animal"])
        if "notify_vehicle" in settings:
            self.notify_vehicle = bool(settings["notify_vehicle"])
        if "vehicle_conf_threshold" in settings:
            self.vehicle_conf_threshold = float(settings["vehicle_conf_threshold"])
        else:
            self.vehicle_conf_threshold = ai_c
        if "notify_motion" in settings:
            self.notify_motion = bool(settings["notify_motion"])
        if "alert_cooldown_sec" in settings or "motion_cooldown_sec" in settings:
            cd = max(1.0, float(settings.get("alert_cooldown_sec", settings.get("motion_cooldown_sec", 5.0))))
            self.ai_alarm_cooldown = cd
            self.motion_alarm_cooldown = cd
        self.set_ai_detection(enabled=ai_en, person=ai_p, animal=ai_a, vehicle=ai_v, conf=ai_c)

        # Wind shake filter
        w_en = settings.get("wind_filter_enabled", True)
        w_tol = settings.get("wind_tolerance", 1.1)
        self.set_wind_filter(enabled=w_en, tolerance=w_tol)

        # Transforms & OSD
        self.flip_horizontal = settings.get("flip_horizontal", False)
        self.flip_vertical = settings.get("flip_vertical", False)
        self.osd_timestamp = settings.get("osd_timestamp", False)
        self.osd_camera_name = settings.get("osd_camera_name", False)

        # Confirmation debounce & static object suppression
        if "detection_confirm_sec" in settings:
            d_sec = float(settings["detection_confirm_sec"])
            self.ai_tracker.confirm_delay = max(0.0, min(10.0, d_sec))
        if "static_suppress_count" in settings:
            s_cnt = int(settings["static_suppress_count"])
            self.ai_tracker.static_count_threshold = s_cnt
            if hasattr(self.detector, "static_count_threshold"):
                self.detector.static_count_threshold = s_cnt
        if "static_suppress_sec" in settings:
            s_sec = float(settings["static_suppress_sec"])
            self.ai_tracker.static_time_threshold = s_sec
            if hasattr(self.detector, "static_time_threshold"):
                self.detector.static_time_threshold = s_sec

        if "pre_alarm_buffer_sec" in settings:
            self.pre_alarm_buffer_sec = max(0.0, min(10.0, float(settings["pre_alarm_buffer_sec"])))
            self._frame_ring_buffer = collections.deque(
                self._frame_ring_buffer, maxlen=max(1, int(self.pre_alarm_buffer_sec * 10)))

        # Dual clips & AI Overlay view preferences
        if "record_dual_clips" in settings:
            self.record_dual_clips = bool(settings["record_dual_clips"])
        if "show_ai_overlays" in settings:
            self.show_ai_overlays = bool(settings["show_ai_overlays"])
        if "motion_overlay_in_recordings" in settings:
            self.motion_overlay_in_recordings = bool(settings["motion_overlay_in_recordings"])
        if "snapshot_dir" in settings:
            self.configured_snapshot_dir = str(settings["snapshot_dir"])
        if "recording_dir" in settings:
            self.configured_recording_dir = str(settings["recording_dir"])

        # Exclusion / Ignore Zones
        if "exclusion_zones" in settings:
            self.set_exclusion_zones(settings["exclusion_zones"])

        # Performance Throttling overrides
        if any(k in settings for k in ("display_fps_cap", "ai_skip_frames", "ai_motion_gated_only", "motion_skip_frames", "motion_downscale_width")):
            self.set_performance_throttling(
                display_fps_cap=settings.get("display_fps_cap", self.display_fps_cap),
                ai_skip_frames=settings.get("ai_skip_frames", self.ai_skip_frames),
                ai_motion_gated_only=settings.get("ai_motion_gated_only", self.ai_motion_gated_only),
                motion_skip_frames=settings.get("motion_skip_frames", self.motion_skip_frames),
                motion_downscale_width=settings.get("motion_downscale_width", self.motion_downscale_width)
            )

    def set_performance_throttling(
        self,
        display_fps_cap: int = 15,
        ai_skip_frames: int = 6,
        ai_motion_gated_only: bool = False,
        motion_skip_frames: int = 1,
        motion_downscale_width: int = 480
    ):
        """Dynamically tunes frame rate, AI frequency, and motion detection scaling for CPU savings."""
        self.display_fps_cap = max(0, int(display_fps_cap))
        self.configured_display_fps = self.display_fps_cap
        if self._background_throttle:
            self.min_render_interval = max(1.0 / 5.0, (1.0 / self.display_fps_cap) if self.display_fps_cap > 0 else 0.0)
        else:
            self.min_render_interval = (1.0 / self.display_fps_cap) if (0 < self.display_fps_cap < 25) else 0.0
        self.ai_skip_frames = max(1, int(ai_skip_frames))
        self.ai_motion_gated_only = bool(ai_motion_gated_only)
        self.motion_skip_frames = max(0, int(motion_skip_frames))
        self.motion_downscale_width = max(160, int(motion_downscale_width))
        if hasattr(self.detector, "downscale_width"):
            self.detector.downscale_width = self.motion_downscale_width

    def set_gui_rendering_paused(self, paused: bool):
        """Pauses GUI frame emission (e.g. when minimized or tile is hidden) to completely eliminate paint overhead."""
        self._gui_rendering_paused = bool(paused)

    def set_background_throttle(self, is_background: bool):
        """When app is in background (unfocused), throttles GUI refresh to 5 FPS to protect games and active apps."""
        self._background_throttle = bool(is_background)
        if self._background_throttle:
            self.min_render_interval = max(self.min_render_interval, 1.0 / 5.0)
        else:
            self.min_render_interval = (1.0 / self.display_fps_cap) if (0 < self.display_fps_cap < 25) else 0.0

    def set_solo_view(self, solo: bool):
        """Indicates whether this feed is currently maximized/soloed on screen."""
        self.is_solo_view = bool(solo)

    def set_motion_detection(self, enabled: bool, sensitivity: int = 5, auto_record: bool = False):
        enabled = bool(enabled and self.alerts_armed)
        if not enabled:
            self.detector.reset_activity()
        self.motion_detection_enabled = enabled
        self.auto_record_on_motion = bool(auto_record and self.alerts_armed)
        cur_area = getattr(self.detector, "min_area", 2800)
        self.detector.update_settings(sensitivity, cur_area)

    def set_ai_detection(self, enabled: bool = True, person: bool = True, animal: bool = True, vehicle: bool = True, conf: float = 0.38):
        enabled = bool(enabled and self.alerts_armed)
        self.ai_detection_enabled = enabled
        if not enabled:
            self._last_ai_detections = []
            self._alerted_track_ids.clear()
            if hasattr(self, "ai_tracker"):
                self.ai_tracker.reset()
        if self.ai_detector:
            self.ai_detector.detect_person = person
            self.ai_detector.detect_animal = animal
            self.ai_detector.detect_vehicle = vehicle
            self.ai_detector.conf_threshold = conf

    def set_ai_tracking(self, confirm_delay: float = 1.0, static_count: int = 150, static_time: float = 300.0):
        """Configures temporal confirmation delay (1.0s) and stationary object suppression thresholds."""
        if hasattr(self, "ai_tracker"):
            self.ai_tracker.confirm_delay = max(0.0, min(10.0, float(confirm_delay)))
            self.ai_tracker.static_count_threshold = int(static_count)
            self.ai_tracker.static_time_threshold = float(static_time)
        if hasattr(self.detector, "confirm_delay"):
            self.detector.confirm_delay = float(confirm_delay)
            self.detector.static_count_threshold = int(static_count)
            self.detector.static_time_threshold = float(static_time)

    def set_wind_filter(self, enabled: bool = True, tolerance: float = 1.1):
        """Controls wind shake suppression for outdoor/pole cameras."""
        self.wind_filter.set_enabled(enabled)
        self.wind_filter.set_tolerance(tolerance)

    def set_alert_manager(self, alert_manager):
        """Attaches alert manager for 10-second clip and snapshot recording."""
        self.alert_manager = alert_manager

    def set_camera_ip(self, ip: str):
        self.camera_ip = ip

    def set_camera_context(self, camera_name: str, lens_tag: str):
        """Sets the parent camera name and lens identifier for standardized media naming."""
        self.camera_name = camera_name
        self.lens_tag = lens_tag

    def run(self):
        self._running = True
        reconnect_delay = 2.0
        reconnect_attempts = 0

        # Set background thread priority on Windows so surveillance never starves foreground games/apps
        from core.resource_manager import ResourceManager
        ResourceManager.set_current_thread_low_priority()

        while self._running:
            try:
                if self._reconnect_requested:
                    self._reconnect_requested = False
                    reconnect_attempts = 0
                    reconnect_delay = 1.0

                def _interruptible_sleep(dur):
                    steps = max(1, int(dur / 0.1))
                    for _ in range(steps):
                        if not self._running or self._reconnect_requested:
                            break
                        time.sleep(0.1)

                self._update_status(StreamStatus.CONNECTING, f"Connecting to {self.stream_name} ({self.quality_mode})...")
    
                if not self.current_url or not str(self.current_url).strip():
                    self._update_status(StreamStatus.ERROR, "No RTSP stream URL configured")
                    _interruptible_sleep(reconnect_delay)
                    continue
    
                cap = None
                try:
                    cap = IsolatedCapture()
                    self._capture = cap
                    if not self._running or self._reconnect_requested:
                        cap.interrupt()
                    cap.open(self.current_url)
                except Exception as e:
                    self._update_status(StreamStatus.ERROR, f"Connection failed: {str(e)}")
                    _interruptible_sleep(reconnect_delay)
                    continue
    
                if not cap or not cap.isOpened():
                    reconnect_attempts += 1
                    reconnect_delay = min(25.0, 2.0 * (1.4 ** min(reconnect_attempts, 8)))
                    if reconnect_attempts >= 3:
                        self._update_status(StreamStatus.ERROR, f"Offline / Unreachable (retry in {int(reconnect_delay)}s)")
                    else:
                        self._update_status(StreamStatus.RECONNECTING, "Unable to open feed. Retrying...")
                    if cap:
                        cap.release()
                    _interruptible_sleep(reconnect_delay)
                    continue
    
                # Reset retry backoff only after a sustained healthy connection.
                connected_at = time.monotonic()
                self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
                self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
                stream_fps = cap.get(cv2.CAP_PROP_FPS)
                if stream_fps <= 0 or stream_fps > 120:
                    stream_fps = 15.0
    
                self._update_status(StreamStatus.LIVE, f"Live ({self.width}x{self.height} @ {int(stream_fps)}fps)")
    
                frame_times = []
                last_stats_time = time.time()
                last_motion_state = False
    
                while self._running and not self._reconnect_requested:
                    if self._paused:
                        time.sleep(0.05)
                        continue
    
                    if not cap.grab():
                        self._update_status(StreamStatus.RECONNECTING, "Feed interrupted. Reconnecting...")
                        break
                    now = time.time()
                    self._last_frame_received_time = now
                    if time.monotonic() - connected_at >= 5.0:
                        reconnect_attempts = 0
                        reconnect_delay = 2.0

                    # --- 0. Frame Timing & Display Throttling Check ---
                    should_render = not self._gui_rendering_paused
                    if should_render and self.min_render_interval > 0.0:
                        # Apply 15% tolerance window so network arrival jitter does not drop alternating frames!
                        tolerance = self.min_render_interval * 0.15
                        if (now - self._last_render_time) < (self.min_render_interval - tolerance):
                            should_render = False
    
                    # --- 0b. Motion Analysis Timing Check ---
                    should_detect_motion = self.motion_detection_enabled
                    if should_detect_motion and self.motion_skip_frames > 0:
                        if (self._motion_frame_count % (self.motion_skip_frames + 1) != 0):
                            should_detect_motion = False
    
                    # Selective Frame Retrieval:
                    # If not recording, and this frame is neither rendered nor analyzed:
                    # Skip copying the shared frame; the child keeps decoding at the live edge.
                    if not self._recording and not self._is_alert_recording and not should_render and not should_detect_motion and not self._web_streaming_active:
                        continue
    
                    ret, frame = cap.retrieve()
                    if not ret or frame is None:
                        continue
    
                    # --- 0. Hardware Flips (Ceiling / Inverted Mounts) ---
                    if self.flip_horizontal and self.flip_vertical:
                        frame = cv2.flip(frame, -1)
                    elif self.flip_horizontal:
                        frame = cv2.flip(frame, 1)
                    elif self.flip_vertical:
                        frame = cv2.flip(frame, 0)
    
                    # Dynamically calibrate stream dimensions from live frame if uninitialized
                    if self.width <= 0 or self.height <= 0:
                        self.height, self.width = frame.shape[:2]
    
                    # Capture pristine raw frame untouched by any annotations
                    clean_raw_frame = frame.copy()
                    self._latest_raw_bgr_frame = clean_raw_frame
    
                    # --- 1. Resolution Scaling (for Mid Quality) ---
                    if self.quality_mode == QualityMode.MID_HD and self.width > 1280:
                        frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_LINEAR)
    
                    # --- 2. Wind Shake & Vibration Analysis (Fata & Outdoor Cameras) ---
                    is_shaking, dx, dy = self.wind_filter.process(frame)
                    if is_shaking != self.is_wind_shaking:
                        self.is_wind_shaking = is_shaking
                        self.wind_shake_detected.emit(self.stream_id, is_shaking)
    
                    # --- 3. Motion Detection Engine (Throttled & Downscaled for CPU) ---
                    is_motion = False
                    boxes = []
                    if self.motion_detection_enabled or self.movement_view_enabled:
                        self._motion_frame_count += 1
                        # When movement_view_enabled is active, NEVER skip frames so overlay is 100% stable and flicker-free!
                        should_skip_motion = (
                            not self.movement_view_enabled and
                            self.motion_skip_frames > 0 and
                            (self._motion_frame_count % (self.motion_skip_frames + 1) != 0)
                        )
                        if should_skip_motion:
                            is_motion = last_motion_state
                        else:
                            # Suppress motion alarm if camera is physically shaking in the wind
                            if is_shaking and self.wind_filter.enabled:
                                self.detector.reset_activity()
                                is_motion = False
                            else:
                                frame, is_motion, boxes = self.detector.process_frame(
                                    frame,
                                    draw_boxes=self.movement_view_enabled,
                                    movement_view=self.movement_view_enabled
                                )
    
                        if is_motion != last_motion_state:
                            last_motion_state = is_motion
                            self.motion_event.emit(self.stream_id, is_motion, len(boxes))
                            if is_motion:
                                max_a = getattr(self.detector, "latest_max_contour_area", 0)
                                self.latest_trigger_reason = f"Motion ({max_a:,}px >= {self.detector.min_area:,}px)"
                                self.trigger_event.emit(self.stream_id, True, self.latest_trigger_reason, {"type": "motion", "area": max_a})
                            else:
                                self.trigger_event.emit(self.stream_id, False, "Standby", {})
    
                        # Auto-record on motion/AI trigger with dynamic duration up to 5 min
                        if self.auto_record_on_motion:
                            has_ai_activity = any(d.is_confirmed and not getattr(d, "is_static", False) and not getattr(d, "is_static_suppressed", False) for d in self._last_ai_detections)
                            has_activity = bool(is_motion or has_ai_activity)
                            if has_activity:
                                self._last_motion_detected_time = now
                                if not self._recording:
                                    self._motion_triggered_rec = True
                                    max_a = getattr(self.detector, "latest_max_contour_area", 0)
                                    self._record_trigger_reason = f"Motion ({max_a:,}px >= {self.detector.min_area:,}px)"
                                    self.start_recording()
                        # Motion Alert: trigger alert card if notify_motion is enabled and cooldown elapsed
                        if is_motion and boxes and self.motion_detection_enabled and self.notify_motion and (now - self._last_motion_alarm_time) >= self.motion_alarm_cooldown:
                            self._handle_motion_alarm(frame, boxes)
    
                    # --- 4. AI Person & Animal Detection Engine ---
                    if self.ai_detection_enabled and self.ai_detector and self.ai_detector.is_ready:
                        self._frame_count += 1
                        cam_ctx = self.camera_name or self.stream_name
    
                        # Eco mode: run AI ONLY when motion is active; Balanced/High mode: run periodically or on motion
                        if self.ai_motion_gated_only and self.motion_detection_enabled:
                            should_run_ai = is_motion and ((now - self._last_ai_infer_time) >= 0.12)
                        else:
                            if is_motion:
                                should_run_ai = ((now - self._last_ai_infer_time) >= 0.12)
                            else:
                                should_run_ai = (self._frame_count % self.ai_skip_frames == 0) and ((now - self._last_ai_infer_time) >= 0.35)
    
                        # 1. Harvest finished background AI inference without stalling video pipeline
                        if self._ai_future is not None and self._ai_future.done():
                            try:
                                raw_dets = self._ai_future.result()
                            except Exception:
                                raw_dets = []
                            self._last_ai_detections = self.ai_tracker.update(raw_dets, now, clean_raw_frame.shape)
                            self._ai_future = None
                        else:
                            # Intermediate frame: maintain persistent smoothed confirmed tracks at full frame rate
                            self._last_ai_detections = self.ai_tracker.update(None, now, clean_raw_frame.shape)

                        # 2. Dispatch AI inference in background thread pool so video display NEVER blocks or lags!
                        if self._ai_future is None and should_run_ai:
                            self._last_ai_infer_time = now
                            frame_input = clean_raw_frame.copy()
                            try:
                                self._ai_future = self._ai_executor.submit(self.ai_detector.detect, frame_input, cam_ctx)
                            except Exception:
                                self._ai_future = None
    
                        # Only draw detection boxes if show_ai_overlays is active
                        if self._last_ai_detections and should_render and getattr(self, "show_ai_overlays", True):
                            frame = self.ai_detector.draw_detections(frame, self._last_ai_detections)
                        if self._last_ai_detections:
                            person_thresh = self.ai_conf_threshold
                            animal_thresh = self.ai_conf_threshold
                            vehicle_thresh = max(self.vehicle_conf_threshold, self.ai_conf_threshold)

                            # If camera is currently vibrating from wind, raise threshold slightly (+0.03)
                            if is_shaking and self.wind_filter.enabled:
                                person_thresh = min(0.75, person_thresh + 0.03)
                                animal_thresh = min(0.75, animal_thresh + 0.03)
                                vehicle_thresh = min(0.80, vehicle_thresh + 0.03)

                            alarm_targets = []
                            for d in self._last_ai_detections:
                                if d.label == "bicycle" or d.category not in ("person", "animal", "vehicle"):
                                    continue
                                if not getattr(d, "is_confirmed", True):
                                    continue
                                if getattr(d, "is_static", False) or getattr(d, "is_static_suppressed", False):
                                    continue
                                if getattr(d, "has_alerted", False):
                                    continue

                                # De-duplicate alerts: each tracked object alerts once upon initial confirmation
                                tid = getattr(d, "track_id", None)
                                if tid is not None and tid in self._alerted_track_ids:
                                    if (now - self._alerted_track_ids[tid]) < 30.0:
                                        continue

                                if d.category == "person" and self.notify_person and d.confidence >= person_thresh:
                                    alarm_targets.append(d)
                                elif d.category == "animal" and self.notify_animal and d.confidence >= animal_thresh:
                                    alarm_targets.append(d)
                                elif d.category == "vehicle" and self.notify_vehicle and d.confidence >= vehicle_thresh:
                                    alarm_targets.append(d)
    
                            if alarm_targets and (now - self._last_ai_alarm_time) >= self.ai_alarm_cooldown:
                                self._last_ai_alarm_time = now
                                self._last_motion_alarm_time = now + 25.0  # Suppress duplicate motion alarms while AI target is active
                                top_target = max(alarm_targets, key=lambda x: x.confidence)
                                top_tid = getattr(top_target, "track_id", None)
                                if top_tid is not None:
                                    self._alerted_track_ids[top_tid] = now
                                    if hasattr(self, "ai_tracker") and top_tid in self.ai_tracker._tracks:
                                        self.ai_tracker._tracks[top_tid].has_alerted = True
    
                                if hasattr(self, "ai_tracker"):
                                    active_tids = set(self.ai_tracker._tracks.keys())
                                    self._alerted_track_ids = {k: v for k, v in self._alerted_track_ids.items() if k in active_tids or (now - v) < 30.0}
                                elif len(self._alerted_track_ids) > 50:
                                    self._alerted_track_ids = {k: v for k, v in self._alerted_track_ids.items() if (now - v) < 60.0}
    
                                short_desc = top_target.description or generate_detection_description(top_target, frame, cam_ctx)
                                cat_u = top_target.category.upper()
                                lbl_u = top_target.label.upper()
                                conf_pct = int(top_target.confidence * 100)
                                what_found = f"{lbl_u}_{conf_pct}PCT" if cat_u == lbl_u else f"{cat_u}_{lbl_u}_{conf_pct}PCT"
    
                                ai_reason = f"AI {top_target.label.upper()} ({conf_pct}%)"
                                self.latest_trigger_reason = ai_reason
                                self._record_trigger_reason = ai_reason
                                self.trigger_event.emit(self.stream_id, True, ai_reason, {"type": "ai", "label": top_target.label, "conf": top_target.confidence})

                                # Trigger snapshot + 10-second high-quality video with audio via AlertManager
                                if self.alert_manager:
                                    self.alert_manager.trigger_alert(
                                        stream_id=self.stream_id,
                                        camera_name=cam_ctx,
                                        camera_ip=self.camera_ip,
                                        rtsp_url=self.main_url or self.current_url,
                                        label=top_target.label.upper(),
                                        confidence=top_target.confidence,
                                        frame=frame,
                                        lens_tag=self.lens_tag,
                                        short_desc=short_desc,
                                        what_found=what_found,
                                        worker=self,
                                        trigger_reason=ai_reason
                                    )
                                else:
                                    # Fallback local snapshot save with standardized naming & 100% quality
                                    now_dt = datetime.now()
                                    snap_name, _ = format_media_filename("ALARM", self.lens_tag, cam_ctx, what_found, "jpg", dt=now_dt)
                                    alarm_path = os.path.join(self.alarm_snapshot_dir, snap_name)
                                    try:
                                        cv2.imwrite(alarm_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
                                    except Exception:
                                        pass
    
                                self.ai_alarm_detected.emit(
                                    self.stream_id,
                                    self.stream_name,
                                    short_desc,
                                    top_target.confidence,
                                    frame.copy()
                                )
    
                                if self.auto_record_on_motion:
                                    self._last_motion_detected_time = now
                                    if not self._recording:
                                        self._motion_triggered_rec = True
                                        self._record_trigger_reason = f"AI {top_target.label.title()} ({int(top_target.confidence * 100)}%)"
                                        self.start_recording(tag=f"AI_{top_target.label.upper()}")
    
                    frame_times.append(now)
                    frame_times = [t for t in frame_times if now - t <= 1.0]
                    current_fps = float(len(frame_times))
    
                    if self._recording and self._motion_triggered_rec:
                        ai_active = any(d.is_confirmed and not d.is_static for d in self._last_ai_detections)
                        if is_motion or ai_active:
                            self._last_motion_detected_time = now
                        elapsed = now - self._record_start_time
                        quiet = now - getattr(self, "_last_motion_detected_time", now)
                        if not self.alerts_armed or elapsed >= 300.0 or (elapsed >= 8.0 and quiet >= 5.0):
                            self.stop_recording()
                            self._motion_triggered_rec = False

                    # Handle snapshot request
                    if self._snapshot_requested:
                        self._save_snapshot_internal(frame)
                        self._snapshot_requested = False
    
                    # Handle recording (preserves all decoded frames in MP4)
                    if self._recording:
                        rec_f = frame
                        if self.motion_overlay_in_recordings and (now - getattr(self, "_current_motion_time", 0.0)) < 4.0:
                            m_desc = getattr(self, "_current_motion_desc", None)
                            m_boxes = getattr(self, "_current_motion_boxes", None)
                            if m_desc and m_boxes:
                                from core.motion_detector import draw_motion_overlay
                                m_pri = getattr(self, "_current_motion_primary_box", None)
                                rec_f = draw_motion_overlay(frame.copy(), m_boxes, m_desc[0], m_desc[1], m_pri)
                        self._write_recording_frame(rec_f)
    
                    # Emit stats periodically
                    if now - last_stats_time >= 1.0:
                        self.fps = current_fps
                        self.stats_updated.emit(self.stream_id, self.fps, frame.shape[1], frame.shape[0])
                        if self._recording:
                            elapsed = int(now - self._record_start_time)
                            mins, secs = divmod(elapsed, 60)
                            self.recording_status.emit(self.stream_id, True, f"{mins:02d}:{secs:02d}")
                        last_stats_time = now
    
                    # --- 5. Qt GUI Display Rendering & Alert Session Recording ---
                    if should_render:
                        self._last_render_time = now
    
                        # Night Vision Boost (Auto, Color Boost, or B&W IR)
                        render_frame = self._apply_night_vision(frame)
    
    
                        # Draw OSD Overlays (Timestamp & Camera Name)
                        if self.osd_timestamp or self.osd_camera_name:
                            render_frame = self._draw_osd(render_frame)

                        # Optional Motion Overlay on highlighted alert recording & display
                        if self.motion_overlay_in_recordings and (now - getattr(self, "_current_motion_time", 0.0)) < 4.0:
                            m_desc = getattr(self, "_current_motion_desc", None)
                            m_boxes = getattr(self, "_current_motion_boxes", None)
                            if m_desc and m_boxes:
                                from core.motion_detector import draw_motion_overlay
                                m_pri = getattr(self, "_current_motion_primary_box", None)
                                render_frame = draw_motion_overlay(render_frame, m_boxes, m_desc[0], m_desc[1], m_pri)
    
                        # Update pre-alarm buffer at 10 FPS (100ms) with lightweight JPEG compression
                        # Slashes RAM consumption from 1,800 MB down to < 2 MB per stream!
                        if (now - getattr(self, "_last_ring_buffer_time", 0.0)) >= 0.10:
                            self._last_ring_buffer_time = now
                            try:
                                _, f_jpg = cv2.imencode('.jpg', render_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75, int(cv2.IMWRITE_JPEG_OPTIMIZE), 0])
                                self._frame_ring_buffer.append((f_jpg, now))
                            except Exception:
                                pass
                        if self._active_alert_sessions:
                            has_ai_activity = any(d.is_confirmed and not getattr(d, "is_static", False) and not getattr(d, "is_static_suppressed", False) for d in self._last_ai_detections)
                            has_person = any(d.category == "person" and d.is_confirmed and not getattr(d, "is_static", False) and not getattr(d, "is_static_suppressed", False) for d in self._last_ai_detections)
                            has_activity = bool(is_motion or has_ai_activity)
                            surviving = []
                            for s in self._active_alert_sessions:
                                if s.active:
                                    lbl = s.alert_entry.get("label", "").upper()
                                    session_has_activity = has_person if "PERSON" in lbl else has_activity
                                    s.push_frame(clean_raw_frame, render_frame, has_activity=session_has_activity)
                                    surviving.append(s)
                            self._active_alert_sessions = surviving
                            self._is_alert_recording = len(surviving) > 0
    
                        # Convert frame to QImage for paint engine using 24-bit native Format_BGR888
                        # Direct zero-overhead pass-through avoids allocating 12MB BGRA buffer every frame
                        h, w, ch = render_frame.shape

                        # In ULTRA_MAX mode, apply Studio App Clarity Engine for smartphone camera app sharpness
                        if self.quality_mode == QualityMode.ULTRA_MAX:
                            render_frame = self._apply_app_clarity(render_frame)

                        # Scaling based on Quality Mode:
                        # - ULTRA_MAX & ULTRA_2K: 100% full pristine native resolution (never downscaled to 540p)
                        # - MID_HD: 720p (1280x720) for lower CPU usage
                        # - LOW_SD: 360p (640x360) for low bandwidth
                        if self.quality_mode == QualityMode.MID_HD and w > 1280:
                            render_disp = cv2.resize(render_frame, (1280, 720), interpolation=cv2.INTER_LINEAR)
                        elif self.quality_mode == QualityMode.LOW_SD and w > 640:
                            render_disp = cv2.resize(render_frame, (640, 360), interpolation=cv2.INTER_LINEAR)
                        else:
                            render_disp = render_frame

                        dh, dw = render_disp.shape[:2]
                        bytes_per_line = 3 * dw
                        q_img = QImage(render_disp.data, dw, dh, bytes_per_line, QImage.Format.Format_BGR888).copy()

                        self._latest_bgr_frame = render_frame
                        self.frame_ready.emit(self.stream_id, q_img, dw, dh, current_fps)
    
                    elif self._active_alert_sessions:
                        # In background/minimized mode, still record alert frames smoothly
                        render_frame = self._apply_night_vision(frame)
                        if self.osd_timestamp or self.osd_camera_name:
                            render_frame = self._draw_osd(render_frame)
                        if self.motion_overlay_in_recordings and (now - getattr(self, "_current_motion_time", 0.0)) < 4.0:
                            m_desc = getattr(self, "_current_motion_desc", None)
                            m_boxes = getattr(self, "_current_motion_boxes", None)
                            if m_desc and m_boxes:
                                from core.motion_detector import draw_motion_overlay
                                m_pri = getattr(self, "_current_motion_primary_box", None)
                                render_frame = draw_motion_overlay(render_frame, m_boxes, m_desc[0], m_desc[1], m_pri)
    
                        self._latest_bgr_frame = render_frame
                        if (now - getattr(self, "_last_ring_buffer_time", 0.0)) >= 0.10:
                            self._last_ring_buffer_time = now
                            try:
                                _, f_jpg = cv2.imencode('.jpg', render_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75, int(cv2.IMWRITE_JPEG_OPTIMIZE), 0])
                                self._frame_ring_buffer.append((f_jpg, now))
                            except Exception:
                                pass
                        has_ai_activity = any(d.is_confirmed and not getattr(d, "is_static", False) and not getattr(d, "is_static_suppressed", False) for d in self._last_ai_detections)
                        has_person = any(d.category == "person" and d.is_confirmed and not getattr(d, "is_static", False) and not getattr(d, "is_static_suppressed", False) for d in self._last_ai_detections)
                        has_activity = bool(is_motion or has_ai_activity)
                        surviving = []
                        for s in self._active_alert_sessions:
                            if s.active:
                                lbl = s.alert_entry.get("label", "").upper()
                                session_has_activity = has_person if "PERSON" in lbl else has_activity
                                s.push_frame(clean_raw_frame, render_frame, has_activity=session_has_activity)
                                surviving.append(s)
                        self._active_alert_sessions = surviving
                        self._is_alert_recording = len(surviving) > 0
                    else:
                        self._latest_bgr_frame = frame
    
                # Cleanup capture
                if self._recording and not self._running:
                    try:
                        self.stop_recording()
                    except Exception:
                        pass
    
                if cap:
                    try:
                        cap.release()
                    except Exception:
                        pass
    
                if self._running and not self._reconnect_requested:
                    reconnect_attempts += 1
                    reconnect_delay = min(25.0, 2.0 * (1.4 ** min(reconnect_attempts, 8)))
                    _interruptible_sleep(reconnect_delay)
    
            except Exception as stream_err:
                print(f"[{self.stream_name}] Stream loop exception: {stream_err}")
                _interruptible_sleep(1.0)
            finally:
                capture = self._capture
                self._capture = None
                if capture is not None:
                    capture.release()

        self._update_status(StreamStatus.STOPPED, "Stream stopped")

    def _apply_night_vision(self, frame: np.ndarray) -> np.ndarray:
        """Applies configured night vision enhancement (Auto, Color Boost, B&W IR Boost, or Full Color Night)."""
        if self.night_mode == NightVisionMode.OFF:
            return frame

        if self.night_mode == NightVisionMode.AUTO:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                mean_lum = float(np.mean(gray))
                if mean_lum < self.night_auto_threshold:
                    return self._apply_color_night(frame, is_auto=True)
                return frame
            except Exception:
                return frame

        elif self.night_mode == NightVisionMode.COLOR_NIGHT:
            return self._apply_color_night(frame, is_auto=False)

        elif self.night_mode == NightVisionMode.COLOR_BOOST:
            return self._apply_color_boost(frame, is_auto=False)

        elif self.night_mode == NightVisionMode.BW_IR:
            return self._apply_bw_ir(frame)

        return frame

    def _apply_color_night(self, frame: np.ndarray, is_auto: bool = False) -> np.ndarray:
        """
        Full-Color Night Vision Engine.
        Restores full, vivid color to nighttime camera feeds when cameras switch to B&W IR around 8 PM.
        """
        try:
            # 1. Check if frame is monochrome (B&W IR: channels are identical)
            diff1 = cv2.absdiff(frame[:, :, 0], frame[:, :, 1])
            diff2 = cv2.absdiff(frame[:, :, 1], frame[:, :, 2])
            is_monochrome = (float(np.mean(diff1)) + float(np.mean(diff2))) < 4.0

            if is_monochrome:
                # Infrared B&W feed: expand dynamic range with CLAHE + apply nocturnal colorization
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                eq = self.clahe.apply(gray)
                lum = cv2.LUT(eq, self._gamma_lut)
                twilight = cv2.applyColorMap(lum, cv2.COLORMAP_TWILIGHT)
                lut_color = cv2.LUT(cv2.merge([lum, lum, lum]), self._color_night_lut)
                result = cv2.addWeighted(twilight, 0.35, lut_color, 0.65, 0)
            else:
                # Low-light color feed: boost chromaticity, shadow luminance, and saturation
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                l_clahe = self.clahe.apply(l)
                l_boost = cv2.LUT(l_clahe, self._gamma_lut)
                a_boost = cv2.convertScaleAbs(a, alpha=1.35, beta=0)
                b_boost = cv2.convertScaleAbs(b, alpha=1.35, beta=0)
                lab_boost = cv2.merge((l_boost, a_boost, b_boost))
                bgr_boost = cv2.cvtColor(lab_boost, cv2.COLOR_LAB2BGR)
                hsv = cv2.cvtColor(bgr_boost, cv2.COLOR_BGR2HSV)
                h, s, v = cv2.split(hsv)
                s_boost = cv2.convertScaleAbs(s, alpha=2.2, beta=10)
                result = cv2.cvtColor(cv2.merge((h, s_boost, v)), cv2.COLOR_HSV2BGR)

            h, w = result.shape[:2]
            badge = "[ AUTO COLOR NIGHT ]" if is_auto else "[ COLOR NIGHT ]"
            cv2.putText(result, badge, (14, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(result, badge, (14, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (80, 255, 120), 1, cv2.LINE_AA)
            return result
        except Exception:
            return frame

    def _apply_color_boost(self, frame: np.ndarray, is_auto: bool = False) -> np.ndarray:
        """Adaptive histogram equalization + gamma correction on luminance channel."""
        try:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l_clahe = self.clahe.apply(l)
            l_boost = cv2.LUT(l_clahe, self._gamma_lut)
            lab = cv2.merge((l_boost, a, b))
            boosted = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            h, w = boosted.shape[:2]
            badge = "[ AUTO NIGHT ]" if is_auto else "[ COLOR BOOST ]"
            cv2.putText(boosted, badge, (14, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(boosted, badge, (14, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 220, 255), 1, cv2.LINE_AA)
            return boosted
        except Exception:
            return frame

    def _apply_bw_ir(self, frame: np.ndarray) -> np.ndarray:
        """Simulates razor-sharp monochrome Infrared Night Vision with high-contrast equalization."""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_eq = self.clahe.apply(gray)
            gray_boost = cv2.LUT(gray_eq, self._gamma_lut)
            bgr = cv2.cvtColor(gray_boost, cv2.COLOR_GRAY2BGR)
            h, w = bgr.shape[:2]
            cv2.putText(bgr, "[ IR NIGHT MODE ]", (14, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(bgr, "[ IR NIGHT MODE ]", (14, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (80, 255, 120), 1, cv2.LINE_AA)
            return bgr
        except Exception:
            return frame

    def _draw_osd(self, frame: np.ndarray) -> np.ndarray:
        """Draws clean antialiased on-screen display timestamp and camera/lens labels."""
        try:
            h, w = frame.shape[:2]
            if self.osd_timestamp:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Shadow outline + crisp white text
                cv2.putText(frame, now_str, (w - 195, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(frame, now_str, (w - 195, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1, cv2.LINE_AA)
            if self.osd_camera_name:
                raw_cam = self.camera_name or self.stream_name or "Camera"
                clean_cam = raw_cam.split(" (")[0].strip()
                tag = f" • {self.lens_tag}" if self.lens_tag else ""
                label = f"{clean_cam}{tag}"
                cv2.putText(frame, label, (14, h - 44), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(frame, label, (14, h - 44), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (56, 189, 248), 1, cv2.LINE_AA)
            return frame
        except Exception:
            return frame

    def _update_status(self, status: str, message: str):
        self.status = status
        self.status_changed.emit(self.stream_id, status, message)

    def _handle_motion_alarm(self, frame, boxes=None):
        """Triggers motion alarm if notify_motion is enabled and cooldown elapsed."""
        now = time.time()

        # Smart Alert Deduplication & Fusion:
        # If AI detection is active, do not fire generic motion alerts if:
        # 1) An AI alert (e.g. Person) occurred within the last 25s on this camera
        # 2) An AI object (person/animal/vehicle) is currently tracked on screen
        if self.ai_detection_enabled:
            if (now - getattr(self, "_last_ai_alarm_time", 0)) < 25.0:
                return
            if self._last_ai_detections and any(getattr(d, "is_confirmed", True) for d in self._last_ai_detections):
                return

        self._last_motion_alarm_time = now
        cam_ctx = self.camera_name or self.stream_name

        from core.motion_detector import generate_motion_description, draw_motion_overlay
        what, where, primary_box = generate_motion_description(
            boxes=boxes,
            frame=frame,
            camera_name=cam_ctx,
            ai_detections=self._last_ai_detections
        )
        self._current_motion_desc = (what, where)
        self._current_motion_boxes = list(boxes) if boxes else []
        self._current_motion_primary_box = primary_box
        self._current_motion_time = now

        m_desc = f"{what} in {where}"

        # Classify specific detected object (Person, Car, Truck, Motorcycle, Dog, Cat, etc.)
        what_lower = what.lower()
        if "person" in what_lower:
            alert_label = "PERSON"
        elif "car" in what_lower:
            alert_label = "CAR"
        elif "truck" in what_lower:
            alert_label = "TRUCK"
        elif "motorcycle" in what_lower:
            alert_label = "MOTORCYCLE"
        elif "bus" in what_lower:
            alert_label = "BUS"
        elif "vehicle" in what_lower:
            alert_label = "VEHICLE"
        elif "dog" in what_lower:
            alert_label = "DOG"
        elif "cat" in what_lower:
            alert_label = "CAT"
        elif "animal" in what_lower:
            alert_label = "ANIMAL"
        else:
            alert_label = "MOTION"

        from core.motion_detector import _strip_diacritics
        safe_combined = _strip_diacritics(f"{alert_label}_{where}").upper()
        clean_what = re.sub(r'[^A-Za-z0-9]', '_', safe_combined)
        clean_what = re.sub(r'_+', '_', clean_what).strip('_')[:35]
        if not clean_what:
            num_b = len(boxes) if boxes else 1
            clean_what = f"{alert_label}_{num_b}ZONES"

        alarm_frame = frame.copy() if frame is not None else None
        if alarm_frame is not None and self.motion_overlay_in_recordings and boxes:
            alarm_frame = draw_motion_overlay(alarm_frame, boxes, what, where, primary_box)

        trig_reason = f"{alert_label.title()}: {m_desc}"
        self.latest_trigger_reason = trig_reason

        if self.alert_manager:
            self.alert_manager.trigger_alert(
                stream_id=self.stream_id,
                camera_name=cam_ctx,
                camera_ip=self.camera_ip,
                rtsp_url=self.main_url or self.current_url,
                label=alert_label,
                confidence=0.85,
                frame=alarm_frame if alarm_frame is not None else frame,
                lens_tag=self.lens_tag,
                short_desc=m_desc,
                what_found=clean_what,
                worker=self,
                trigger_reason=trig_reason
            )
        self.ai_alarm_detected.emit(
            self.stream_id,
            self.stream_name,
            m_desc,
            0.85,
            alarm_frame if alarm_frame is not None else frame.copy()
        )
        return m_desc

    def trigger_snapshot(self, output_dir=None):
        if output_dir is None:
            output_dir = getattr(self, "configured_snapshot_dir", "snapshots")
        self._snapshot_dir = output_dir
        self._snapshot_requested = True

    def _save_snapshot_internal(self, frame):
        try:
            os.makedirs(self._snapshot_dir, exist_ok=True)
            now_dt = datetime.now()
            cam_ctx = self.camera_name or self.stream_name
            snap_name, _ = format_media_filename("SNAPSHOT", self.lens_tag, cam_ctx, "MANUAL", "jpg", dt=now_dt)
            filename = os.path.join(self._snapshot_dir, snap_name)
            # Highest quality (100% JPEG fidelity)
            cv2.imwrite(filename, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
            self.snapshot_saved.emit(self.stream_id, os.path.abspath(filename))
        except Exception as e:
            print(f"Error saving snapshot: {e}")

    def start_recording(self, output_dir=None, tag: Optional[str] = None):
        """Starts asynchronous, non-blocking video recording without stalling the capture loop or GUI."""
        if self._recording:
            return
        if output_dir is None:
            output_dir = getattr(self, "configured_recording_dir", "recordings")
        try:
            os.makedirs(output_dir, exist_ok=True)
            self._output_record_dir = output_dir
            now_dt = datetime.now()
            cam_ctx = self.camera_name or self.stream_name or "Camera"
            if tag is None:
                tag = "MOTION" if getattr(self, "_motion_triggered_rec", False) else "MANUAL"
            rec_name, uid = format_media_filename("REC", self.lens_tag, cam_ctx, tag, "mp4", dt=now_dt)
            self._record_filename = os.path.join(output_dir, rec_name)
            self._record_unique_id = uid
            self._record_tag = tag
            self._record_start_dt = now_dt

            # Capture snapshot at start of recording
            snap_frame = self.get_latest_frame()
            if snap_frame is not None:
                snap_dir = getattr(self.alert_manager, "snapshot_dir", os.path.join("snapshots", "alarms")) if self.alert_manager else os.path.join("snapshots", "alarms")
                os.makedirs(snap_dir, exist_ok=True)
                snap_name, _ = format_media_filename("ALARM", self.lens_tag, cam_ctx, tag, "jpg", dt=now_dt, unique_id=uid)
                self._record_snapshot_path = os.path.join(snap_dir, snap_name)
                try:
                    cv2.imwrite(self._record_snapshot_path, snap_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                except Exception:
                    self._record_snapshot_path = ""
            else:
                self._record_snapshot_path = ""

            fps = self.fps if self.fps > 5 else 15.0
            w = self.width if self.width > 0 else 1920
            h = self.height if self.height > 0 else 1080

            def _on_rec_status(is_active: bool, elapsed_str: str):
                self.recording_status.emit(self.stream_id, is_active, elapsed_str)

            intro_meta = {
                "alert_type": tag,
                "camera_name": cam_ctx,
                "lens_name": self.lens_tag,
                "timestamp": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "trigger_reason": getattr(self, "_record_trigger_reason", "") or f"{tag} Triggered Recording",
                "trigger_image": snap_frame.copy() if snap_frame is not None else None,
                "trigger_image_path": self._record_snapshot_path
            }

            self._async_recorder = AsyncVideoRecorder(
                output_path=self._record_filename,
                fps=fps,
                width=w,
                height=h,
                on_status_callback=_on_rec_status,
                intro_meta=intro_meta
            )
            self._async_recorder.start()
            self._record_start_time = time.time()
            self._recording = True
        except Exception as e:
            print(f"Error starting recording: {e}")

    def _write_recording_frame(self, frame):
        """Asynchronously dispatches frame to background recorder in <0.002ms."""
        if self._async_recorder and self._recording:
            self._async_recorder.write_frame(frame)

    def stop_recording(self, wait: bool = False, timeout: float = 2.0):
        """Signals background recorder to stop and finalize. If wait=True, waits for clean finalization."""
        if not self._recording:
            return
        self._recording = False
        was_motion_rec = getattr(self, "_motion_triggered_rec", False)
        rec_path = self._record_filename
        rec_uid = getattr(self, "_record_unique_id", None)
        rec_tag = getattr(self, "_record_tag", "REC")
        rec_start_dt = getattr(self, "_record_start_dt", datetime.now())
        snap_path = getattr(self, "_record_snapshot_path", "")
        rec_start = getattr(self, "_record_start_time", 0)
        elapsed = time.time() - rec_start if rec_start > 0 else 0

        if self._async_recorder:
            self._async_recorder.stop(wait=wait, timeout=timeout)
            self._async_recorder = None
        self.recording_status.emit(self.stream_id, False, "")
        self._motion_triggered_rec = False

        # Register completed motion or manual recording into AlertManager
        if rec_path and self.alert_manager and elapsed >= 2.0:
            def _finalize_and_register(is_sync: bool = False):
                try:
                    cam_ctx = self.camera_name or self.stream_name or "Camera"
                    if not is_sync:
                        for _ in range(15):
                            if os.path.exists(rec_path) and os.path.getsize(rec_path) > 1024:
                                break
                            time.sleep(0.1)

                    if not (os.path.exists(rec_path) and os.path.getsize(rec_path) > 1024):
                        return

                    final_snap = snap_path
                    if not (final_snap and os.path.exists(final_snap)):
                        cur_f = self.get_latest_frame()
                        if cur_f is not None:
                            s_dir = getattr(self.alert_manager, "snapshot_dir", os.path.join("snapshots", "alarms"))
                            os.makedirs(s_dir, exist_ok=True)
                            s_name, _ = format_media_filename("ALARM", self.lens_tag, cam_ctx, rec_tag, "jpg", dt=rec_start_dt, unique_id=rec_uid)
                            final_snap = os.path.join(s_dir, s_name)
                            try:
                                cv2.imwrite(final_snap, cur_f, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                            except Exception:
                                final_snap = ""

                    is_motion = (rec_tag == "MOTION" or was_motion_rec)
                    lbl = "MOTION" if is_motion else "MANUAL"
                    action_text = "Motion activity recorded" if is_motion else "Manual recording"
                    desc = f"{cam_ctx} ({self.lens_tag}) - {action_text} ({int(elapsed)}s clip)"

                    alert_entry = {
                        "id": f"rec_{rec_uid or int(time.time()*1000)}",
                        "unique_id": rec_uid or uuid.uuid4().hex[:4].upper(),
                        "stream_id": self.stream_id,
                        "camera_name": cam_ctx,
                        "camera_ip": self.camera_ip,
                        "lens": self.lens_tag,
                        "label": lbl,
                        "confidence": 0.85 if is_motion else 1.0,
                        "description": desc,
                        "what_found": rec_tag,
                        "trigger_reason": getattr(self, "_record_trigger_reason", "Motion Activity"),
                        "filename": os.path.basename(rec_path),
                        "timestamp": rec_start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "time_short": rec_start_dt.strftime("%H:%M:%S"),
                        "snapshot_path": final_snap if (final_snap and os.path.exists(final_snap)) else "",
                        "video_path": os.path.abspath(rec_path),
                        "video_raw_path": os.path.abspath(rec_path),
                        "video_highlighted_path": os.path.abspath(rec_path),
                        "video_ready": True,
                        "video_recording": False,
                        "video_failed": False,
                        "silent": not self.notify_motion if is_motion else True
                    }
                    self.alert_manager.register_completed_recording(alert_entry)
                except Exception as e:
                    print(f"[CameraStreamWorker] Error finalizing recording registration: {e}")

            try:
                if wait:
                    _finalize_and_register(is_sync=True)
                else:
                    threading.Thread(target=_finalize_and_register, args=(False,), daemon=True, name="RegisterRec").start()
            except Exception as thr_err:
                print(f"[CameraStreamWorker] Error launching registration thread: {thr_err}")

    def stop_all_alert_sessions(self, wait: bool = True):
        """Gracefully finalizes and saves all ongoing alert clip recordings on exit."""
        surviving = list(self._active_alert_sessions)
        for s in surviving:
            try:
                s.finish(wait=wait, timeout=2.5)
            except Exception as e:
                print(f"[CameraStreamWorker] Error finishing alert session: {e}")
        self._active_alert_sessions.clear()
        self._is_alert_recording = False

    def flush_pending_snapshots(self):
        """Immediately writes any pending requested snapshot before shutdown."""
        if getattr(self, "_snapshot_requested", False):
            frame = self.get_latest_frame()
            if frame is not None:
                self._save_snapshot_internal(frame)
            self._snapshot_requested = False

    @property
    def is_recording(self) -> bool:
        """Returns True if manual recording is currently running."""
        return bool(self._recording)

    @property
    def record_elapsed_seconds(self) -> int:
        """Returns elapsed recording duration in seconds."""
        if self._recording and self._record_start_time > 0:
            return int(time.time() - self._record_start_time)
        return 0

    def pause_stream(self):
        self._paused = True

    def resume_stream(self):
        self._paused = False

    def stop(self, wait: bool = True):
        self._running = False
        capture = self._capture
        if capture is not None:
            capture.interrupt()
        self.stop_recording()
        if hasattr(self, "_ai_executor"):
            try:
                self._ai_executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
        if wait:
            self.wait(1500)
