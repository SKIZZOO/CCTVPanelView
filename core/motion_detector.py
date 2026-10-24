import cv2
import numpy as np
import time
from typing import List, Tuple, Dict, Any, Optional


class MotionDetector:
    """
    High-performance real-time motion detection and object tracking engine.
    Uses Gaussian filtering, adaptive thresholding, and contour analysis
    to detect moving targets, extract bounding boxes, and trigger alerts.
    """
    def __init__(self, sensitivity: int = 5, min_area: int = 2800, downscale_width: int = 480):
        # sensitivity 1 (low) to 10 (ultra high)
        self.sensitivity = max(1, min(10, sensitivity))
        self.min_area = max(200, min_area)
        self.downscale_width = max(160, int(downscale_width))
        var_thresh = max(8.0, 32.0 - (self.sensitivity * 1.8))
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=300, varThreshold=var_thresh, detectShadows=False
        )
        self.last_motion_time = 0.0
        self.is_motion_active = False
        self.motion_cooldown = 3.0  # seconds to stay active after motion stops

        # Temporal confirmation debounce & stationary zone suppression
        self.confirm_delay = 1.2  # seconds of continuous solid motion before confirmation (filters wind gusts)
        self.foliage_filter_enabled: bool = True  # Intelligent anti-leaf & wind oscillation rejection
        self._motion_candidate_start = None
        self.warmup_sec = 1.5
        self._warmup_started = None
        self._frame_shape = None
        self.static_count_threshold = 30
        self.static_time_threshold = 3600.0
        self._motion_zones: Dict[int, Dict[str, Any]] = {}
        self._next_zone_id = 1

        # Movement View & Trigger Diagnostics State
        self.movement_view: bool = False
        self.latest_motion_area: int = 0
        self.latest_max_contour_area: int = 0
        self.latest_fg_ratio: float = 0.0
        self.latest_trigger_status: str = "IDLE"
        self.latest_boxes_detail: List[Dict[str, Any]] = []
        self.show_heatmap: bool = False
        self.show_radar_hud: bool = True
        self.exclusion_zones: List[List[float]] = []

    def set_exclusion_zones(self, zones: List[List[float]]):
        """Sets normalized [x1, y1, x2, y2] zones (0.0 to 1.0) to zero out from motion detection."""
        self.exclusion_zones = [list(z) for z in (zones or []) if len(z) >= 4]

    def set_movement_view(self, enabled: bool):
        """Toggles real-time movement diagnostics & trigger visualization overlay."""
        self.movement_view = bool(enabled)

    def update_settings(
        self,
        sensitivity: int,
        min_area: int,
        downscale_width: Optional[int] = None,
        confirm_delay: Optional[float] = None,
        motion_cooldown: Optional[float] = None,
        static_count_threshold: Optional[int] = None,
        foliage_filter_enabled: Optional[bool] = None
    ):
        old_sensitivity = self.sensitivity
        self.sensitivity = max(1, min(10, int(sensitivity)))
        self.min_area = max(200, int(min_area))
        if downscale_width is not None:
            self.downscale_width = max(160, int(downscale_width))
        if confirm_delay is not None:
            self.confirm_delay = max(0.0, float(confirm_delay))
        if motion_cooldown is not None:
            self.motion_cooldown = max(0.5, float(motion_cooldown))
        if static_count_threshold is not None:
            self.static_count_threshold = max(5, int(static_count_threshold))
        if foliage_filter_enabled is not None:
            self.foliage_filter_enabled = bool(foliage_filter_enabled)
        if old_sensitivity != self.sensitivity:
            self.reset_background()

    def reset_activity(self):
        self._motion_candidate_start = None
        self.is_motion_active = False
        self.last_motion_time = 0.0

    def reset_background(self):
        var_thresh = max(8.0, 32.0 - self.sensitivity * 1.8)
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=300, varThreshold=var_thresh, detectShadows=False)
        self._warmup_started = None
        self._motion_zones.clear()
        self.reset_activity()

    def process_frame(
        self,
        frame: np.ndarray,
        draw_boxes: bool = True,
        movement_view: Optional[bool] = None
    ) -> Tuple[np.ndarray, bool, List[Tuple[int, int, int, int]]]:
        """
        Analyzes a BGR frame for movement.
        Returns:
            - processed_frame: frame with visual bounding boxes, HUD, and optional Movement View diagnostics
            - motion_detected: True if target movement exceeds threshold
            - boxes: List of (x, y, w, h) bounding boxes that meet trigger criteria
        """
        if frame is None:
            return frame, False, []

        is_mview = self.movement_view if movement_view is None else bool(movement_view)
        h, w = frame.shape[:2]
        now = time.monotonic()
        if self._frame_shape != (h, w):
            self.reset_background()
            self._frame_shape = (h, w)
        if self._warmup_started is None:
            self._warmup_started = now

        # Downsample for ultra-fast motion processing without high CPU
        target_w = getattr(self, "downscale_width", 480)
        if target_w > 0 and w > target_w:
            scale = float(target_w) / float(w)
            small_frame = cv2.resize(frame, (target_w, int(h * scale)), interpolation=cv2.INTER_NEAREST)
        else:
            scale = 1.0
            small_frame = frame

        # Convert to grayscale and blur with lightweight (7, 7) kernel
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        # Apply MOG2 background subtraction
        fg_mask = self.bg_subtractor.apply(blurred)
        if now - self._warmup_started < self.warmup_sec:
            self.reset_activity()
            self.latest_trigger_status = "WARMING UP BACKGROUND"
            self.latest_boxes_detail = []
            return frame, False, []

        # Remove noise: first apply morphological opening (erodes small fluttering leaf speckles)
        # then dilate to reconnect solid body contours (persons, cars, animals)
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        opened = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_open, iterations=1)

        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dilated = cv2.dilate(opened, kernel_dilate, iterations=1)
        thresh = cv2.threshold(dilated, 128, 255, cv2.THRESH_BINARY)[1]

        # Zero out user-defined exclusion zones so motion in those zones is completely ignored
        if self.exclusion_zones:
            th_h, th_w = thresh.shape[:2]
            for zone in self.exclusion_zones:
                if len(zone) >= 4:
                    zx1 = int(round(min(zone[0], zone[2]) * th_w))
                    zx2 = int(round(max(zone[0], zone[2]) * th_w))
                    zy1 = int(round(min(zone[1], zone[3]) * th_h))
                    zy2 = int(round(max(zone[1], zone[3]) * th_h))
                    zx1 = max(0, min(th_w, zx1))
                    zx2 = max(0, min(th_w, zx2))
                    zy1 = max(0, min(th_h, zy1))
                    zy2 = max(0, min(th_h, zy2))
                    thresh[zy1:zy2, zx1:zx2] = 0

        # Calculate global foreground ratio to reject camera shake and sudden lighting shifts
        total_pixels = small_frame.shape[0] * small_frame.shape[1]
        fg_pixels = cv2.countNonZero(thresh)
        fg_ratio = fg_pixels / max(1, total_pixels)
        self.latest_fg_ratio = fg_ratio

        out_frame = frame
        inv_scale = 1.0 / scale

        # Check for sudden global lighting surge or violent camera shake
        if fg_ratio > 0.24:
            self.reset_activity()
            self.latest_trigger_status = "[REJECTED] LIGHTING SHIFT / CAMERA SHAKE"
            self.latest_max_contour_area = 0
            self.latest_motion_area = 0
            if is_mview:
                out_frame = frame.copy()
                if hasattr(self, "_mview_cached_boxes") and self._mview_cached_boxes:
                    for item in self._mview_cached_boxes[:6]:
                        bx, by, bw, bh = item["box"]
                        area = item.get("area", 0)
                        box_col = (0, 215, 255)
                        tag_text = f"IGNORED: LIGHT SHIFT ({area:,}px)"
                        cv2.rectangle(out_frame, (bx, by), (bx + bw, by + bh), box_col, 1)
                        label_y = max(18, by - 6)
                        cv2.putText(out_frame, tag_text, (bx + 3, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, box_col, 1, cv2.LINE_AA)
                self._draw_movement_hud(out_frame, w, h, 0, self.latest_trigger_status, is_warning=True)
            return out_frame, False, []

        # Find contours of moving objects
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # If too many fragmented contours scattered across the screen, camera is shaking / foliage vibration
        if len(contours) > 25:
            self.reset_activity()
            self.latest_trigger_status = "[REJECTED] CAMERA VIBRATION / WIND (>25 CONTOURS)"
            self.latest_max_contour_area = 0
            self.latest_motion_area = 0
            if is_mview:
                out_frame = frame.copy()
                # Smoothly render top contours as ignored so the screen doesn't flicker or flash empty
                sorted_c = sorted(contours, key=lambda c: cv2.contourArea(c), reverse=True)[:6]
                for c in sorted_c:
                    c_area = int(cv2.contourArea(c) * (inv_scale ** 2))
                    if c_area >= 80:
                        x, y, bw, bh = cv2.boundingRect(c)
                        bx, by, bw, bh = int(x * inv_scale), int(y * inv_scale), int(bw * inv_scale), int(bh * inv_scale)
                        box_col = (0, 215, 255)
                        tag_text = f"IGNORED: WIND/VIBRATION ({c_area:,}px)"
                        cv2.rectangle(out_frame, (bx, by), (bx + bw, by + bh), box_col, 1)
                        label_y = max(18, by - 6)
                        cv2.putText(out_frame, tag_text, (bx + 3, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, box_col, 1, cv2.LINE_AA)
                self._draw_movement_hud(out_frame, w, h, 0, self.latest_trigger_status, is_warning=True)
            return out_frame, False, []

        detected_boxes = []
        all_boxes_detail = []
        max_contour_area = 0
        total_motion_area = 0

        for c in contours:
            c_area_small = cv2.contourArea(c)
            orig_area = int(c_area_small * (inv_scale ** 2))
            if orig_area < 120:
                continue

            x, y, bw, bh = cv2.boundingRect(c)
            orig_box = (int(x * inv_scale), int(y * inv_scale), int(bw * inv_scale), int(bh * inv_scale))

            # Anti-Wind Foliage & Leaf Flutter Filter:
            # Leaves and twigs moving in wind produce porous, highly jagged, non-solid contours.
            # Solid objects (persons, vehicles, animals) maintain solidity >= 0.45 and compactness <= 55.
            is_foliage_flutter = False
            foliage_tag = ""
            if getattr(self, "foliage_filter_enabled", True) and orig_area < 35000:
                hull = cv2.convexHull(c)
                hull_area = cv2.contourArea(hull)
                solidity = c_area_small / max(1.0, hull_area)
                perimeter = cv2.arcLength(c, True)
                compactness = (perimeter * perimeter) / max(1.0, c_area_small)

                if solidity < 0.38:
                    is_foliage_flutter = True
                    foliage_tag = f"LOW SOLIDITY ({solidity:.2f} < 0.38)"
                elif compactness > 65.0:
                    is_foliage_flutter = True
                    foliage_tag = f"JAGGED LEAF ({compactness:.0f} > 65)"

            is_qualifying = (orig_area >= self.min_area) and not is_foliage_flutter

            if is_qualifying and orig_area > max_contour_area:
                max_contour_area = orig_area
            if is_qualifying:
                total_motion_area += orig_area

            box_detail = {
                "box": orig_box,
                "area": orig_area,
                "is_trigger": is_qualifying,
                "is_foliage": is_foliage_flutter,
                "foliage_tag": foliage_tag,
                "contour": c
            }
            all_boxes_detail.append(box_detail)

            if is_qualifying:
                detected_boxes.append(orig_box)

        self.latest_max_contour_area = max_contour_area
        self.latest_motion_area = total_motion_area
        self.latest_boxes_detail = all_boxes_detail

        valid_boxes = self._filter_stationary_motion_boxes(detected_boxes, now)
        has_current_motion = len(valid_boxes) > 0

        if has_current_motion:
            if self._motion_candidate_start is None:
                self._motion_candidate_start = now
            deb_elapsed = now - self._motion_candidate_start
            if deb_elapsed >= self.confirm_delay:
                self.last_motion_time = now
                self.is_motion_active = True
                self.latest_trigger_status = f"[ACTIVE] TRIGGER: {max_contour_area:,}px (Min: {self.min_area:,}px)"
            else:
                self.latest_trigger_status = f"[DEBOUNCING] {deb_elapsed:.1f}s / {self.confirm_delay:.1f}s ({max_contour_area:,}px)"
        else:
            self._motion_candidate_start = None
            if (now - self.last_motion_time) > self.motion_cooldown:
                self.is_motion_active = False
                if max_contour_area > 0:
                    self.latest_trigger_status = f"[STANDBY] BELOW THRESHOLD: {max_contour_area:,}px < {self.min_area:,}px"
                else:
                    self.latest_trigger_status = "[STANDBY] (No movement detected)"
            else:
                remain = max(0.0, self.motion_cooldown - (now - self.last_motion_time))
                self.latest_trigger_status = f"[COOLDOWN] ({remain:.1f}s remaining)"

        # --- Visual Rendering ---
        if is_mview:
            # Full diagnostic Movement View: Motion heatmap glow, diagnostic contour boxes, area labels, and radar HUD
            out_frame = frame.copy()

            # Temporal persistence to eliminate single-frame contour flicker
            if not hasattr(self, "_mview_cached_boxes"):
                self._mview_cached_boxes = []
                self._mview_cached_time = 0.0

            if all_boxes_detail:
                self._mview_cached_boxes = all_boxes_detail
                self._mview_cached_time = now
            elif (now - getattr(self, "_mview_cached_time", 0.0)) < 0.60:
                all_boxes_detail = getattr(self, "_mview_cached_boxes", [])

            # 1. Subtle soft motion highlight (only on qualifying trigger contours, never raw noisy pixel static)
            if self.show_heatmap and all_boxes_detail:
                try:
                    overlay = out_frame.copy()
                    has_fill = False
                    for item in all_boxes_detail:
                        if item.get("is_trigger", False):
                            bx, by, bw, bh = item["box"]
                            cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), (0, 230, 160), -1)
                            has_fill = True
                    if has_fill:
                        cv2.addWeighted(out_frame, 0.88, overlay, 0.12, 0, out_frame)
                except Exception:
                    pass

            # 2. Draw all motion boxes with area and trigger qualification tags
            for item in all_boxes_detail:
                bx, by, bw, bh = item["box"]
                area = item["area"]
                qualifies = item["is_trigger"]

                if qualifies:
                    # Neon emerald green for qualifying trigger box (or red if active)
                    box_col = (0, 70, 255) if self.is_motion_active else (0, 255, 128)
                    tag_text = f"REC TRIGGER: {area:,}px >= {self.min_area:,}px"
                    cv2.rectangle(out_frame, (bx, by), (bx + bw, by + bh), box_col, 2)
                    corner_len = min(16, bw // 4, bh // 4)
                    cv2.line(out_frame, (bx, by), (bx + corner_len, by), (0, 210, 255), 3)
                    cv2.line(out_frame, (bx, by), (bx, by + corner_len), (0, 210, 255), 3)
                    cv2.line(out_frame, (bx + bw, by), (bx + bw - corner_len, by), (0, 210, 255), 3)
                    cv2.line(out_frame, (bx + bw, by), (bx + bw, by + corner_len), (0, 210, 255), 3)
                elif item.get("is_foliage", False):
                    # Distinct Amber/Orange tag for foliage rejected by wind filter
                    box_col = (0, 165, 255)
                    tag_text = f"IGNORED: LEAF/WIND ({item.get('foliage_tag', 'FOLIAGE')})"
                    cv2.rectangle(out_frame, (bx, by), (bx + bw, by + bh), box_col, 1)
                else:
                    # Amber/yellow for sub-threshold movement
                    box_col = (0, 215, 255)
                    tag_text = f"IGNORED: {area:,}px < {self.min_area:,}px"
                    cv2.rectangle(out_frame, (bx, by), (bx + bw, by + bh), box_col, 1)

                # Pill background for crisp readability
                label_y = max(18, by - 6)
                font_scale = 0.42
                (tw, th), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
                cv2.rectangle(out_frame, (bx, label_y - th - 3), (bx + tw + 6, label_y + 3), (15, 23, 42), -1)
                cv2.rectangle(out_frame, (bx, label_y - th - 3), (bx + tw + 6, label_y + 3), box_col, 1)
                cv2.putText(out_frame, tag_text, (bx + 3, label_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, box_col, 1, cv2.LINE_AA)

            # 3. Draw Top Movement Radar HUD
            self._draw_movement_hud(out_frame, w, h, max_contour_area, self.latest_trigger_status)

        elif draw_boxes and self.is_motion_active:
            out_frame = frame.copy()
            for (bx, by, bw, bh) in valid_boxes:
                # Neon emerald / amber tracking rectangle
                cv2.rectangle(out_frame, (bx, by), (bx + bw, by + bh), (0, 255, 128), 2)
                corner_len = min(15, bw // 4, bh // 4)
                cv2.line(out_frame, (bx, by), (bx + corner_len, by), (0, 210, 255), 3)
                cv2.line(out_frame, (bx, by), (bx, by + corner_len), (0, 210, 255), 3)
                cv2.line(out_frame, (bx + bw, by), (bx + bw - corner_len, by), (0, 210, 255), 3)
                cv2.line(out_frame, (bx + bw, by), (bx + bw, by + corner_len), (0, 210, 255), 3)

        return out_frame, self.is_motion_active, valid_boxes

    def _draw_movement_hud(self, out_frame: np.ndarray, w: int, h: int, max_area: int, status_str: str, is_warning: bool = False):
        """Renders the top Movement Radar diagnostic HUD bar onto the frame."""
        hud_h = 28
        bar_w = min(w - 20, 680)
        bar_x = (w - bar_w) // 2
        bar_y = 10

        # Dark glass pill background
        hud_bg = out_frame[bar_y:bar_y + hud_h, bar_x:bar_x + bar_w]
        if hud_bg.shape[0] == hud_h and hud_bg.shape[1] == bar_w:
            dark_mask = np.full_like(hud_bg, (15, 23, 42))
            cv2.addWeighted(hud_bg, 0.20, dark_mask, 0.80, 0, hud_bg)
            out_frame[bar_y:bar_y + hud_h, bar_x:bar_x + bar_w] = hud_bg

        border_col = (0, 70, 255) if is_warning or self.is_motion_active else (56, 189, 248)
        cv2.rectangle(out_frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + hud_h), border_col, 1)

        # Draw status text
        foliage_txt = "LeafFilter: ON" if getattr(self, "foliage_filter_enabled", True) else "LeafFilter: OFF"
        hud_text = f"RADAR: Max {max_area:,}px (Min: {self.min_area:,}px) | {foliage_txt} | {status_str}"
        cv2.putText(out_frame, hud_text, (bar_x + 10, bar_y + 19), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (248, 250, 252), 1, cv2.LINE_AA)

    def _filter_stationary_motion_boxes(
        self, detected_boxes: List[Tuple[int, int, int, int]], now: float
    ) -> List[Tuple[int, int, int, int]]:
        """
        Suppresses stationary motion artifacts in the same location
        after >= 30 detections or >= 3600 seconds (1 hour).
        """
        valid_boxes = []
        for box in detected_boxes:
            bx, by, bw, bh = box
            cx = bx + bw / 2.0
            cy = by + bh / 2.0

            best_zid = None
            best_dist = 999999.0

            for zid, zone in self._motion_zones.items():
                z_cx, z_cy = zone["anchor_center"]
                dist = ((cx - z_cx) ** 2 + (cy - z_cy) ** 2) ** 0.5
                if dist < 40.0 and dist < best_dist:
                    best_dist = dist
                    best_zid = zid

            if best_zid is not None:
                z = self._motion_zones[best_zid]
                z["count"] += 1
                z["last_seen"] = now
                z["duration"] = now - z["first_seen"]
                if (z["count"] >= self.static_count_threshold and z["duration"] >= max(30.0, self.confirm_delay + self.motion_cooldown)) or z["duration"] >= self.static_time_threshold:
                    z["is_static"] = True

                if not z["is_static"]:
                    valid_boxes.append(box)
            else:
                zid = self._next_zone_id
                self._next_zone_id += 1
                self._motion_zones[zid] = {
                    "anchor_center": (cx, cy),
                    "anchor_box": box,
                    "first_seen": now,
                    "last_seen": now,
                    "count": 1,
                    "duration": 0.0,
                    "is_static": False
                }
                valid_boxes.append(box)

        # Prune zones that have been absent for > 30 seconds
        to_del = [zid for zid, z in self._motion_zones.items() if (now - z["last_seen"]) > 30.0]
        for zid in to_del:
            del self._motion_zones[zid]

        return valid_boxes


def _strip_diacritics(text: str) -> str:
    """Replaces Romanian diacritics with plain Latin characters for cv2.putText rendering."""
    trans_map = {
        'ă': 'a', 'Ă': 'A',
        'â': 'a', 'Â': 'A',
        'î': 'i', 'Î': 'I',
        'ș': 's', 'Ș': 'S',
        'ş': 's', 'Ş': 'S',
        'ț': 't', 'Ț': 'T',
        'ţ': 't', 'Ţ': 'T'
    }
    return "".join(trans_map.get(ch, ch) for ch in text)


def generate_motion_description(
    boxes: List[Tuple[int, int, int, int]],
    frame: Optional[np.ndarray],
    camera_name: str = "",
    ai_detections: Optional[List[Any]] = None
) -> Tuple[str, str, Tuple[int, int, int, int]]:
    """
    Generates rich natural language descriptions of WHAT moved and WHERE in the frame.
    Returns:
        (what, where, primary_box)
        - what: Visual description of the moving entity (colors, silhouette, vehicle/person/animal)
        - where: Natural language quadrant/zone (e.g. 'Bottom-Left Zone', 'Center Zone')
        - primary_box: The largest/primary motion bounding box (x, y, w, h)
    """
    if not boxes:
        return "Motion Detected", "Unknown Zone", (0, 0, 0, 0)

    # 1. Identify primary bounding box (largest moving area)
    primary_box = max(boxes, key=lambda b: int(b[2]) * int(b[3]))
    bx, by, bw, bh = primary_box

    # 2. Compute spatial location (WHERE)
    h_f, w_f = (frame.shape[:2]) if (frame is not None and frame.size > 0) else (1080, 1920)
    cx = bx + bw / 2.0
    cy = by + bh / 2.0
    nx = cx / max(1.0, float(w_f))
    ny = cy / max(1.0, float(h_f))

    # Horizontal 3-way partition
    if nx < 0.35:
        h_part = "Left"
    elif nx > 0.65:
        h_part = "Right"
    else:
        h_part = "Center"

    # Vertical 3-way partition
    if ny < 0.35:
        v_part = "Top"
    elif ny > 0.65:
        v_part = "Bottom"
    else:
        v_part = "Middle"

    # Assemble natural zone descriptor
    if h_part == "Center" and v_part == "Middle":
        where = "Center Zone"
    elif h_part == "Center":
        where = f"{v_part}-Center Zone"
    elif v_part == "Middle":
        where = f"{h_part} Zone"
    else:
        where = f"{v_part}-{h_part} Zone"

    # 3. Analyze content (WHAT)
    what = ""
    # A. Check for correlation with confirmed AI detections (Person, Animal, Vehicle)
    if ai_detections:
        best_overlap = 0.0
        matched_ai = None
        for d in ai_detections:
            if not getattr(d, "is_confirmed", True) or getattr(d, "is_static_suppressed", False):
                continue
            dx, dy, dw, dh = [int(v) for v in d.box]
            ix1, iy1 = max(bx, dx), max(by, dy)
            ix2, iy2 = min(bx + bw, dx + dw), min(by + bh, dy + dh)
            iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
            inter = iw * ih
            if inter > 0:
                min_area = max(1.0, float(min(bw * bh, dw * dh)))
                overlap = inter / min_area
                if overlap > 0.20 and overlap > best_overlap:
                    best_overlap = overlap
                    matched_ai = d

        if matched_ai:
            cat = matched_ai.category.lower()
            lbl = matched_ai.label.lower()
            ai_desc = getattr(matched_ai, "description", "")
            if cat == "person":
                what = f"Person ({ai_desc})" if ai_desc else "Person Silhouette"
            elif cat == "animal":
                what = f"Animal ({ai_desc})" if ai_desc else f"Animal ({lbl})"
            elif cat == "vehicle":
                what = f"Vehicle ({ai_desc})" if ai_desc else f"Vehicle ({lbl})"
            else:
                what = f"{lbl.capitalize()} ({ai_desc})" if ai_desc else f"Object: {lbl}"

    # B. If no active AI correlation, extract visual color & silhouette features from image crop
    if not what and frame is not None and frame.size > 0:
        crop_y1 = max(0, by)
        crop_y2 = min(h_f, by + bh)
        crop_x1 = max(0, bx)
        crop_x2 = min(w_f, bx + bw)
        crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]

        if crop.size > 0:
            try:
                from core.ai_detector import extract_dominant_color_name
                dom_color = extract_dominant_color_name(crop)
            except Exception:
                dom_color = "unspecified"

            aspect = bh / max(1.0, float(bw))
            rel_area = (bw * bh) / max(1.0, float(w_f * h_f))

            if aspect >= 1.6 and bh >= 35:
                what = f"Vertical Silhouette / Person ({dom_color})"
            elif aspect <= 0.65 and bw >= 40:
                what = f"Horizontal Object / Vehicle ({dom_color})"
            elif 0.7 <= aspect <= 1.5 and rel_area >= 0.025:
                what = f"Compact Moving Body ({dom_color})"
            elif bw * bh >= 3500:
                what = f"Moving Object ({dom_color})"
            else:
                what = f"Localized Motion ({dom_color})"

    if not what:
        what = "Active Motion Detected"

    if len(boxes) > 1:
        what += f" (+{len(boxes) - 1} zones)"

    return what, where, primary_box


def draw_motion_overlay(
    frame: np.ndarray,
    boxes: List[Tuple[int, int, int, int]],
    what: str,
    where: str,
    primary_box: Optional[Tuple[int, int, int, int]] = None
) -> np.ndarray:
    """
    Renders high-tech tactical motion tracking bounding boxes, corner reticles,
    and a prominent translucent HUD badge [MOTION: WHAT | ZONE] directly onto the frame.
    """
    if frame is None or frame.size == 0 or not boxes:
        return frame

    out_frame = frame
    h_f, w_f = out_frame.shape[:2]

    # If no primary box specified, pick largest
    if primary_box is None and boxes:
        primary_box = max(boxes, key=lambda b: int(b[2]) * int(b[3]))

    # 1. Draw corner reticles on all detected motion zones
    for box in boxes:
        bx, by, bw, bh = box
        is_pri = (primary_box is not None and box == primary_box)
        border_col = (0, 220, 255) if is_pri else (0, 255, 128)
        reticle_col = (0, 255, 255) if is_pri else (56, 189, 248)
        thick = 2 if is_pri else 1

        cv2.rectangle(out_frame, (bx, by), (bx + bw, by + bh), border_col, thick)

        # Corner bracket lengths
        clen = min(18, max(5, bw // 4), max(5, bh // 4))
        # Top-left
        cv2.line(out_frame, (bx, by), (bx + clen, by), reticle_col, 2)
        cv2.line(out_frame, (bx, by), (bx, by + clen), reticle_col, 2)
        # Top-right
        cv2.line(out_frame, (bx + bw, by), (bx + bw - clen, by), reticle_col, 2)
        cv2.line(out_frame, (bx + bw, by), (bx + bw, by + clen), reticle_col, 2)
        # Bottom-left
        cv2.line(out_frame, (bx, by + bh), (bx + clen, by + bh), reticle_col, 2)
        cv2.line(out_frame, (bx, by + bh), (bx, by + bh - clen), reticle_col, 2)
        # Bottom-right
        cv2.line(out_frame, (bx + bw, by + bh), (bx + bw - clen, by + bh), reticle_col, 2)
        cv2.line(out_frame, (bx + bw, by + bh), (bx + bw, by + bh - clen), reticle_col, 2)

    # 2. Render prominent HUD badge displaying WHAT and ZONE
    if primary_box:
        pbx, pby, pbw, pbh = primary_box
    else:
        pbx, pby, pbw, pbh = boxes[0]

    # Convert text to ASCII safe for Hershey font
    safe_what = _strip_diacritics(what)
    safe_where = _strip_diacritics(where)

    line1 = f"MOTION: {safe_what}"
    line2 = f"ZONE:   {safe_where}"

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.50
    thick = 1

    (tw1, th1), _ = cv2.getTextSize(line1, font, scale, thick)
    (tw2, th2), _ = cv2.getTextSize(line2, font, scale, thick)
    badge_w = max(tw1, tw2) + 20
    badge_h = th1 + th2 + 18

    # Determine badge position (above primary box, or below if near top)
    pos_x = max(10, min(w_f - badge_w - 10, pbx))
    if pby - badge_h - 6 >= 10:
        pos_y = pby - badge_h - 6
    elif pby + pbh + badge_h + 6 < h_f - 10:
        pos_y = pby + pbh + 6
    else:
        pos_y = max(10, pby + 8)

    # Dark translucent HUD pill
    bg_patch = out_frame[pos_y:pos_y + badge_h, pos_x:pos_x + badge_w]
    if bg_patch.shape[0] == badge_h and bg_patch.shape[1] == badge_w:
        dark_overlay = np.full_like(bg_patch, (15, 23, 42))
        cv2.addWeighted(bg_patch, 0.25, dark_overlay, 0.75, 0, bg_patch)
        out_frame[pos_y:pos_y + badge_h, pos_x:pos_x + badge_w] = bg_patch

    # Badge frame and neon indicator tag
    cv2.rectangle(out_frame, (pos_x, pos_y), (pos_x + badge_w, pos_y + badge_h), (0, 210, 255), 1)
    cv2.rectangle(out_frame, (pos_x, pos_y), (pos_x + 4, pos_y + badge_h), (0, 255, 255), -1)

    # Text rendering
    cv2.putText(out_frame, line1, (pos_x + 10, pos_y + th1 + 5), font, scale, (255, 255, 255), thick, cv2.LINE_AA)
    cv2.putText(out_frame, line2, (pos_x + 10, pos_y + th1 + th2 + 11), font, scale, (56, 189, 248), thick, cv2.LINE_AA)

    return out_frame

