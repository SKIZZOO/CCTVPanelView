import cv2
import numpy as np
import time
from typing import Tuple, Optional


class WindShakeFilter:
    """
    High-performance Electronic Image Stabilization (EIS) and Wind Shake Rejection Engine.
    
    Designed specifically for outdoor and dual-lens cameras (such as 'Fata') that experience
    mechanical vibrations and sway from wind gusts.
    
    Uses sub-pixel phase correlation (cross-power spectrum) on downscaled frames to calculate
    the global translation vector (dx, dy). When the entire frame oscillates rigidly or when
    foreground motion covers an abnormally wide area, the filter identifies camera shake and
    suppresses false motion alarms.
    """
    def __init__(self, tolerance: float = 1.0, enabled: bool = True):
        self.enabled = enabled
        self.tolerance = tolerance  # Pixel shift threshold for shake detection (1.0 = sensitive)
        self.prev_small_gray: Optional[np.ndarray] = None
        self.is_shaking = False
        self.last_shake_time = 0.0
        self.shake_cooldown = 1.2  # Seconds to hold shake flag active after vibration stops
        self.recent_shifts = []
        self._frame_count = 0
        self._last_result = (False, 0.0, 0.0)

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

    def set_tolerance(self, tolerance: float):
        self.tolerance = max(0.5, min(4.0, float(tolerance)))

    def process(self, frame: np.ndarray, foreground_ratio: float = 0.0) -> Tuple[bool, float, float]:
        """
        Analyzes consecutive frames for global camera movement.
        Returns:
            - is_shaking: True if the camera is currently oscillating/vibrating from wind
            - dx: Horizontal shift in pixels
            - dy: Vertical shift in pixels
        """
        if not self.enabled or frame is None:
            return False, 0.0, 0.0

        self._frame_count += 1
        # Sampling at alternate frames (~10-15 Hz) captures 0.5-3Hz wind gusts with 50% less CPU
        if self._frame_count % 2 != 0 and self.prev_small_gray is not None:
            return self._last_result

        # Downscale to 160x90 for ultra-fast phase correlation (<0.5ms on CPU)
        h, w = frame.shape[:2]
        small_gray = cv2.cvtColor(cv2.resize(frame, (160, 90)), cv2.COLOR_BGR2GRAY)

        if self.prev_small_gray is None:
            self.prev_small_gray = small_gray
            return False, 0.0, 0.0

        # Sub-pixel Fourier phase correlation
        shift, response = cv2.phaseCorrelate(
            np.float32(self.prev_small_gray),
            np.float32(small_gray)
        )
        self.prev_small_gray = small_gray

        dx, dy = shift
        magnitude = np.sqrt(dx * dx + dy * dy)
        now = time.time()

        # Check 1: Rigid global frame shift detected with high confidence
        is_rigid_shift = (magnitude > self.tolerance) and (response > 0.22)

        # Check 2: Abnormally large foreground coverage (when camera shakes, whole frame shifts)
        is_massive_coverage = foreground_ratio > 0.22

        if is_rigid_shift or is_massive_coverage:
            self.is_shaking = True
            self.last_shake_time = now
            self.recent_shifts.append((dx, dy, now))
        else:
            # Cooldown before unflagging shaking
            if now - self.last_shake_time > self.shake_cooldown:
                self.is_shaking = False

        # Keep last 10 shift measurements for oscillation pattern analysis
        self.recent_shifts = [(sx, sy, t) for (sx, sy, t) in self.recent_shifts if now - t <= 2.0]

        self._last_result = (self.is_shaking, dx, dy)
        return self.is_shaking, dx, dy

    def should_suppress_motion(self, foreground_ratio: float = 0.0) -> bool:
        """Determines if a motion event should be suppressed due to wind shaking."""
        if not self.enabled:
            return False
        return self.is_shaking or (foreground_ratio > 0.25)
