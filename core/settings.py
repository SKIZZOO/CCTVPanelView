"""Validation shared by saved global settings and per-camera overrides."""
import math

NUMERIC_LIMITS = {
    "motion_sensitivity": (1, 10, 5, int),
    "motion_min_area": (200, 1000000, 2800, int),
    "motion_confirm_delay": (0, 10, 1.2, float),
    "detection_confirm_sec": (0, 10, 0.8, float),
    "motion_hold_sec": (0.5, 30, 3, float),
    "motion_cooldown_sec": (1, 300, 5, float),
    "alert_cooldown_sec": (1, 300, 5, float),
    "ai_conf_threshold": (0.1, 0.99, 0.45, float),
    "vehicle_conf_threshold": (0.1, 0.99, 0.45, float),
    "static_suppress_count": (5, 100000, 150, int),
    "static_suppress_sec": (30, 86400, 300, float),
    "motion_downscale_width": (160, 1920, 480, int),
}


def normalize_settings(settings):
    result = dict(settings) if isinstance(settings, dict) else {}
    for key, (low, high, default, cast) in NUMERIC_LIMITS.items():
        if key not in result:
            continue
        try:
            value = float(result[key])
            if not math.isfinite(value):
                raise ValueError("non-finite setting")
            result[key] = cast(max(low, min(high, value)))
        except (ValueError, TypeError, OverflowError):
            result[key] = cast(default)
    if result.get("default_layout", "2x2") not in {"1x1", "2x1", "1x2", "2x2", "1+5", "3x3", "4x4", "custom"}:
        result["default_layout"] = "2x2"
    return result
