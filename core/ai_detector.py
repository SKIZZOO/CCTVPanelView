import cv2
import numpy as np
import time
import os
import sys
from typing import List, Dict, Any, Tuple, Optional, Union


COCO_CLASSES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
    'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
    'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
    'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
    'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
    'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
    'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake',
    'chair', 'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop',
    'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
    'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
]

PERSON_CLASSES = {'person'}
ANIMAL_CLASSES = {'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe'}
VEHICLE_CLASSES = {'car', 'motorcycle', 'bus', 'truck'}
EXCLUDED_CLASSES = {'bicycle'}


class AIDetection:
    """Represents a single detected object."""
    def __init__(
        self,
        label: str,
        category: str,
        confidence: float,
        box: Tuple[int, int, int, int],
        description: str = "",
        track_id: Optional[int] = None,
        is_confirmed: bool = True,
        is_static: bool = False,
        stationary_count: int = 1,
        stationary_duration: float = 0.0,
        visual_alpha: float = 1.0,
        has_alerted: bool = False
    ):
        self.label = label             # e.g. "person", "dog"
        self.category = category       # "person", "animal", "vehicle", "other"
        self.confidence = confidence   # 0.0 to 1.0
        self.box = box                 # (x, y, w, h)
        self.description = description # Human-readable short description
        self.track_id = track_id
        self.is_confirmed = is_confirmed
        self.is_static = is_static
        self.stationary_count = stationary_count
        self.stationary_duration = stationary_duration
        self.visual_alpha = float(visual_alpha)
        self.has_alerted = has_alerted


def extract_dominant_color_name(bgr_crop: np.ndarray) -> str:
    """
    High-speed, robust HSV color classifier for real-world surveillance crops.
    Accurately identifies white, black, grey, blue, red, brown, yellow, green, etc.
    """
    if bgr_crop is None or bgr_crop.size == 0:
        return "dark"
    h, w = bgr_crop.shape[:2]
    # Sample central 60% width and 70% height to avoid background edges
    y1, y2 = max(0, int(h * 0.15)), min(h, int(h * 0.85))
    x1, x2 = max(0, int(w * 0.20)), min(w, int(w * 0.80))
    crop = bgr_crop[y1:y2, x1:x2]
    if crop.size == 0:
        crop = bgr_crop

    # Resize to standardized patch for instant microsecond analysis
    patch = cv2.resize(crop, (32, 32), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)

    H = hsv[:, :, 0]
    S = hsv[:, :, 1]
    V = hsv[:, :, 2]

    med_s = float(np.median(S))
    med_v = float(np.median(V))

    # Neutral / Achromatic colors
    if med_v < 55:
        return "black"
    if med_s < 38:
        if med_v > 190:
            return "white"
        elif med_v < 115:
            return "dark grey"
        else:
            return "grey"

    # Saturated pixels
    mask = (S >= 36) & (V >= 45)
    if not np.any(mask):
        return "dark" if med_v < 100 else "light"

    sat_h = H[mask]
    sat_v = V[mask]
    sat_s = S[mask]
    med_h = float(np.median(sat_h))

    if med_h < 10 or med_h >= 170:
        return "red" if med_v > 105 else "dark red"
    elif med_h < 25:
        if med_v < 120 and med_s > 40:
            return "brown"
        return "orange"
    elif med_h < 36:
        return "beige/tan" if med_s < 90 else "yellow"
    elif med_h < 85:
        return "green" if med_v > 110 else "dark green"
    elif med_h < 102:
        return "teal"
    elif med_h < 132:
        if med_v < 90:
            return "navy blue"
        elif med_v > 175 and med_s < 120:
            return "light blue"
        return "blue"
    elif med_h < 155:
        return "purple"
    else:
        return "pink"


def generate_detection_description(
    detection: AIDetection,
    frame_or_shape: Union[np.ndarray, Tuple[int, ...]],
    camera_name: str = ""
) -> str:
    """
    Generates rich visual-attribute natural language descriptions of detected objects.
    Describes visual colors, clothing (e.g. white shirt, black pants), and vehicle/animal shapes
    instead of frame screen coordinates.
    """
    full_frame = None
    if isinstance(frame_or_shape, np.ndarray):
        full_frame = frame_or_shape
        h_frame, w_frame = full_frame.shape[:2]
    elif isinstance(frame_or_shape, (tuple, list)) and len(frame_or_shape) >= 2:
        h_frame, w_frame = frame_or_shape[:2]
    else:
        h_frame, w_frame = 1080, 1920

    x, y, w, h = [int(v) for v in detection.box]
    cat = detection.category
    lbl = detection.label.lower()

    # If full image frame is available, perform computer vision color and silhouette extraction
    if full_frame is not None and full_frame.size > 0:
        bx = max(0, min(w_frame - 1, x))
        by = max(0, min(h_frame - 1, y))
        bw = max(1, min(w_frame - bx, w))
        bh = max(1, min(h_frame - by, h))
        crop = full_frame[by:by + bh, bx:bx + bw]

        if crop.size > 0:
            aspect = bh / max(1, bw)

            # --- 1. PERSON: Clothing & Posture Breakdown ---
            if cat == "person":
                if bh >= 24 and bw >= 10:
                    upper_crop = crop[int(bh * 0.16):int(bh * 0.50), :]
                    lower_crop = crop[int(bh * 0.50):int(bh * 0.88), :]
                    top_color = extract_dominant_color_name(upper_crop)
                    bottom_color = extract_dominant_color_name(lower_crop)

                    if aspect >= 2.2:
                        posture = "standing"
                    elif aspect >= 1.6:
                        posture = "upright"
                    elif aspect < 1.3:
                        posture = "crouching"
                    else:
                        posture = "walking"

                    bottom_garment = "jeans" if "blue" in bottom_color else "pants"
                    top_garment = "shirt" if top_color in ["white", "blue", "red", "yellow", "orange"] else "jacket"

                    if top_color == bottom_color:
                        return f"Person: {top_color} outfit ({posture})"
                    else:
                        return f"Person: {top_color} {top_garment}, {bottom_color} {bottom_garment} ({posture})"
                else:
                    overall_color = extract_dominant_color_name(crop)
                    return f"Person: {overall_color} silhouette (distant)"

            # --- 2. VEHICLE: Color & Body Silhouette Breakdown ---
            elif cat == "vehicle":
                veh_color = extract_dominant_color_name(crop)
                w_h = bw / max(1, bh)
                if lbl in ["motorcycle", "bicycle"]:
                    return f"{lbl.capitalize()}: {veh_color} frame"
                elif lbl == "truck":
                    return f"Truck: {veh_color} body"
                elif lbl == "bus":
                    return f"Bus: {veh_color} body"
                else:
                    if w_h >= 1.9:
                        form = "sedan profile"
                    elif w_h >= 1.3:
                        form = "SUV/compact"
                    else:
                        form = "front/rear view"
                    return f"Car: {veh_color} {form}"

            # --- 3. ANIMAL: Coat Color & Stance Breakdown ---
            elif cat == "animal":
                coat_color = extract_dominant_color_name(crop)
                w_h = bw / max(1, bh)
                if w_h >= 1.2:
                    form = "quadruped stance"
                elif w_h < 0.9:
                    form = "sitting/compact"
                else:
                    form = "medium build"
                return f"{lbl.capitalize()}: {coat_color} coat ({form})"

            # --- 4. OTHER OBJECTS ---
            else:
                obj_color = extract_dominant_color_name(crop)
                return f"{lbl.capitalize()}: {obj_color} form"

    # Fallback if frame pixels are not available: describe shape/silhouette without coordinates
    aspect = h / max(1, w)
    if cat == "person":
        posture = "standing" if aspect >= 2.0 else "upright silhouette"
        return f"Person: {posture}"
    elif cat == "vehicle":
        form = "sedan profile" if (w / max(1, h)) >= 1.8 else "vehicle profile"
        return f"{lbl.capitalize()}: {form}"
    elif cat == "animal":
        return f"{lbl.capitalize()}: quadruped silhouette"
    else:
        return f"{lbl.capitalize()}: detected object"


class AIDetector:
    """
    High-performance AI Object Detection engine using YOLOv5 ONNX with OpenCV DNN.
    Accurately detects Persons, Animals, and Vehicles in real-time.
    """
    def __init__(self, model_path: str = "yolov5n.onnx", conf_threshold: float = 0.38, nms_threshold: float = 0.45):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.net = None
        self.is_ready = False

        # Detection toggles
        self.detect_person = True
        self.detect_animal = True
        self.detect_vehicle = True
        self.VEHICLE_CLASSES = VEHICLE_CLASSES
        self.EXCLUDED_CLASSES = EXCLUDED_CLASSES

        self._load_model()

    def _load_model(self):
        candidate_paths = [
            self.model_path,
        ]
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", "")
            if meipass:
                candidate_paths.append(os.path.join(meipass, "yolov5n.onnx"))
                candidate_paths.append(os.path.join(meipass, os.path.basename(self.model_path)))
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            candidate_paths.append(os.path.join(exe_dir, "yolov5n.onnx"))
            candidate_paths.append(os.path.join(exe_dir, os.path.basename(self.model_path)))

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate_paths.append(os.path.join(base_dir, "yolov5n.onnx"))
        candidate_paths.append(os.path.join(base_dir, os.path.basename(self.model_path)))
        candidate_paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "yolov5n.onnx"))

        resolved = None
        for p in candidate_paths:
            if p and os.path.exists(p):
                resolved = p
                break

        if resolved:
            try:
                self.model_path = resolved
                self.net = cv2.dnn.readNetFromONNX(resolved)
                self.is_ready = True
                print(f"[AIDetector] Successfully loaded YOLOv5 AI model from: {resolved}")
            except Exception as e:
                print(f"[AIDetector] Error loading model from {resolved}: {e}")
                self.is_ready = False
        else:
            print(f"[AIDetector] Model file not found. Checked: {candidate_paths}")
            self.is_ready = False

    def detect(self, frame: np.ndarray, camera_name: str = "") -> List[AIDetection]:
        """
        Runs inference on an OpenCV BGR frame.
        Returns a list of AIDetection objects matching active filters.
        """
        if not self.is_ready or self.net is None or frame is None:
            return []

        h, w = frame.shape[:2]
        if h == 0 or w == 0:
            return []

        # YOLOv5 expects 640x640 normalized RGB input
        blob = cv2.dnn.blobFromImage(frame, 1.0 / 255.0, (640, 640), [0, 0, 0], swapRB=True, crop=False)
        self.net.setInput(blob)
        
        try:
            outputs = self.net.forward()
        except Exception as e:
            print(f"[AIDetector] Inference error: {e}")
            return []

        if len(outputs) == 0:
            return []

        rows = outputs[0]
        boxes = []
        confidences = []
        class_ids = []

        x_factor = w / 640.0
        y_factor = h / 640.0

        for r in rows:
            obj_conf = r[4]
            if obj_conf >= self.conf_threshold:
                scores = r[5:]
                cid = int(np.argmax(scores))
                score = float(scores[cid] * obj_conf)

                if score >= self.conf_threshold and cid < len(COCO_CLASSES):
                    class_name = COCO_CLASSES[cid]
                    # Exclude blacklisted classes (bicycles per user request)
                    if class_name in EXCLUDED_CLASSES or class_name.lower() == 'bicycle':
                        continue

                    # Filter by category
                    is_p = class_name in PERSON_CLASSES
                    is_a = class_name in ANIMAL_CLASSES
                    is_v = class_name in VEHICLE_CLASSES

                    if (is_p and self.detect_person) or (is_a and self.detect_animal) or (is_v and self.detect_vehicle):
                        cx, cy, bw, bh = r[0], r[1], r[2], r[3]
                        left = int((cx - 0.5 * bw) * x_factor)
                        top = int((cy - 0.5 * bh) * y_factor)
                        width = int(bw * x_factor)
                        height = int(bh * y_factor)

                        # Clamp to frame bounds
                        left = max(0, min(w - 1, left))
                        top = max(0, min(h - 1, top))
                        width = max(10, min(w - left, width))
                        height = max(10, min(h - top, height))

                        boxes.append([left, top, width, height])
                        confidences.append(score)
                        class_ids.append(cid)

        if not boxes:
            return []

        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.nms_threshold)
        detections = []

        for i in indices:
            idx = i if isinstance(i, (int, np.integer)) else i[0]
            cid = class_ids[idx]
            cname = COCO_CLASSES[cid]
            conf = confidences[idx]
            box = tuple(boxes[idx])

            cat = "other"
            if cname in PERSON_CLASSES:
                cat = "person"
            elif cname in ANIMAL_CLASSES:
                cat = "animal"
            elif cname in VEHICLE_CLASSES:
                cat = "vehicle"

            det = AIDetection(label=cname, category=cat, confidence=conf, box=box)
            det.description = generate_detection_description(det, frame, camera_name)
            detections.append(det)

        return detections

    def _draw_single_detection(self, out: np.ndarray, det: AIDetection, h_frame: int, w_frame: int):
        """Renders styled bounding box and HUD tags for a single detection."""
        x, y, w, h = det.box
        conf_pct = int(det.confidence * 100)

        # Color scheme
        lbl_upper = det.label.upper()
        if det.category == "person":
            color = (40, 50, 240)      # Crimson Red (BGR)
            accent = (0, 100, 255)
            icon = "PERSON"
        elif det.category == "animal":
            color = (20, 180, 250)     # Amber / Gold (BGR)
            accent = (0, 230, 255)
            icon = lbl_upper if det.label in ("dog", "cat", "bird") else f"ANIMAL ({lbl_upper})"
        elif det.category == "vehicle":
            color = (250, 200, 20)     # Cyan / Turquoise (BGR)
            accent = (255, 255, 100)
            icon = lbl_upper if det.label in ("car", "truck", "bus", "motorcycle") else f"VEHICLE ({lbl_upper})"
        else:
            color = (180, 180, 180)
            accent = (220, 220, 220)
            icon = lbl_upper

        # Main bounding rectangle
        cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)

        # Sleek corner brackets for cyberpunk HUD look
        clen = min(22, w // 4, h // 4)
        # Top-left
        cv2.line(out, (x, y), (x + clen, y), accent, 3)
        cv2.line(out, (x, y), (x, y + clen), accent, 3)
        # Top-right
        cv2.line(out, (x + w, y), (x + w - clen, y), accent, 3)
        cv2.line(out, (x + w, y), (x + w, y + clen), accent, 3)
        # Bottom-left
        cv2.line(out, (x, y + h), (x + clen, y + h), accent, 3)
        cv2.line(out, (x, y + h), (x, y + h - clen), accent, 3)
        # Bottom-right
        cv2.line(out, (x + w, y + h), (x + w - clen, y + h), accent, 3)
        cv2.line(out, (x + w, y + h), (x + w, y + h - clen), accent, 3)

        # Label badge
        label_text = f" {icon} {conf_pct}% "
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.55
        thickness = 1
        (tw, th), baseline = cv2.getTextSize(label_text, font, font_scale, thickness)

        badge_y1 = max(0, y - th - 8)
        badge_y2 = y
        badge_x1 = x
        badge_x2 = x + tw + 4

        # Background pill
        cv2.rectangle(out, (badge_x1, badge_y1), (badge_x2, badge_y2), color, -1)
        # Text
        cv2.putText(out, label_text, (badge_x1 + 2, badge_y2 - 4), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

        # Sub-badge with description for high-confidence Persons, Animals & Vehicles
        if det.description and det.category in ["person", "animal", "vehicle"] and det.confidence >= 0.45:
            desc_text = f" {det.description} "
            d_scale = 0.40
            (dw, dh), _ = cv2.getTextSize(desc_text, font, d_scale, 1)
            dy1 = min(h_frame - dh - 8, y + h + 4)
            dy2 = dy1 + dh + 6
            dx1 = max(0, x)
            dx2 = min(w_frame - 1, x + dw + 6)
            cv2.rectangle(out, (dx1, dy1), (dx2, dy2), (15, 23, 42), -1)
            cv2.rectangle(out, (dx1, dy1), (dx2, dy2), color, 1)
            cv2.putText(out, desc_text, (dx1 + 2, dy2 - 4), font, d_scale, (255, 255, 255), 1, cv2.LINE_AA)

    def draw_detections(self, frame: np.ndarray, detections: List[AIDetection]) -> np.ndarray:
        """
        Draws styled, flicker-free bounding boxes and HUD tags on the frame for confirmed targets.
        """
        if not detections or frame is None:
            return frame

        out = frame.copy()
        h_frame, w_frame = out.shape[:2]

        for det in detections:
            # Skip unconfirmed candidates or static suppressed targets
            if not getattr(det, "is_confirmed", True) or getattr(det, "is_static", False):
                continue
            alpha = float(getattr(det, "visual_alpha", 1.0))
            if alpha < 0.2:
                continue

            # Draw solid, crisp, flicker-free HUD box directly
            self._draw_single_detection(out, det, h_frame, w_frame)

        return out


def compute_box_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    """Calculates Intersection-over-Union (IoU) between two bounding boxes (x, y, w, h)."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

    inter_w = max(0, xB - xA)
    inter_h = max(0, yB - yA)
    inter_area = inter_w * inter_h
    if inter_area == 0:
        return 0.0

    boxA_area = boxA[2] * boxA[3]
    boxB_area = boxB[2] * boxB[3]
    union_area = float(boxA_area + boxB_area - inter_area)
    if union_area <= 0:
        return 0.0
    return inter_area / union_area


def is_box_in_exclusion_zone(
    box: Tuple[int, int, int, int],
    exclusion_zones: List[List[float]],
    frame_w: int,
    frame_h: int
) -> bool:
    """
    Checks if a bounding box (x, y, w, h) falls inside or significantly overlaps
    any defined normalized exclusion zone [x1, y1, x2, y2] (0.0 - 1.0).
    """
    if not exclusion_zones or frame_w <= 0 or frame_h <= 0:
        return False

    bx, by, bw, bh = box
    bcx = bx + bw / 2.0
    bcy = by + bh / 2.0

    for zone in exclusion_zones:
        if len(zone) < 4:
            continue
        zx1, zy1, zx2, zy2 = zone[:4]
        min_x = min(zx1, zx2) * frame_w
        max_x = max(zx1, zx2) * frame_w
        min_y = min(zy1, zy2) * frame_h
        max_y = max(zy1, zy2) * frame_h

        # 1. Centroid check: center of the person/target is in the exclusion zone
        if min_x <= bcx <= max_x and min_y <= bcy <= max_y:
            return True

        # 2. Significant overlap check: > 35% of the detection box is inside the exclusion zone
        ix1 = max(bx, min_x)
        iy1 = max(by, min_y)
        ix2 = min(bx + bw, max_x)
        iy2 = min(by + bh, max_y)
        if ix2 > ix1 and iy2 > iy1:
            inter_area = (ix2 - ix1) * (iy2 - iy1)
            box_area = max(1.0, float(bw * bh))
            if (inter_area / box_area) >= 0.35:
                return True

    return False


class TrackedTarget:
    """Represents an ongoing temporal track of an object."""
    def __init__(self, track_id: int, detection: AIDetection, timestamp: float):
        self.track_id = track_id
        self.label = detection.label
        self.category = detection.category
        self.confidence = float(detection.confidence)
        self.smoothed_box = [float(v) for v in detection.box]  # [x, y, w, h]
        self.description = detection.description

        self.first_seen = timestamp
        self.last_seen = timestamp
        self.detection_count = 1

        # 1-second confirmation debounce state
        self.is_confirmed = False

        # Stationary / static object suppression state
        self.is_static = False
        x, y, w, h = detection.box
        self.anchor_cx = x + w / 2.0
        self.anchor_cy = y + h / 2.0
        self.anchor_box = [float(x), float(y), float(w), float(h)]
        self.stationary_detections = 1
        self.stationary_start_time = timestamp
        self.stationary_duration = 0.0

        # Visual fade animation opacity (0.0 to 1.0)
        self.visual_alpha = 0.0

        # One-time alert dispatch per confirmed object
        self.has_alerted = False
        self.alert_timestamp = 0.0

    @property
    def cx(self) -> float:
        return self.smoothed_box[0] + self.smoothed_box[2] / 2.0

    @property
    def cy(self) -> float:
        return self.smoothed_box[1] + self.smoothed_box[3] / 2.0

    def to_ai_detection(self) -> AIDetection:
        return AIDetection(
            label=self.label,
            category=self.category,
            confidence=self.confidence,
            box=(
                int(round(self.smoothed_box[0])),
                int(round(self.smoothed_box[1])),
                int(round(self.smoothed_box[2])),
                int(round(self.smoothed_box[3])),
            ),
            description=self.description,
            track_id=self.track_id,
            is_confirmed=self.is_confirmed,
            is_static=self.is_static,
            stationary_count=self.stationary_detections,
            stationary_duration=self.stationary_duration,
            visual_alpha=self.visual_alpha,
            has_alerted=self.has_alerted
        )


class TemporalDetectionTracker:
    """
    Temporal tracking, anti-flicker smoothing, and static suppression engine.

    Guarantees:
    1. Confirmation Delay (1.0s): Targets must persist for >= 1.0 second before confirmation.
       Prevents transient 1-frame glitches from flickering boxes and firing false alarms.
    2. Anti-Flicker Smoothing: Bounding box coordinates and confidence are smoothed via EMA,
       and confirmed targets are held across small detection dropouts (persistence window)
       eliminating flashy disappearance and reappearance between skipped AI frames.
    3. Static Object Suppression: Objects stationary in the same location for >= 30 detections
       OR >= 3600 seconds (1 hour) are suppressed (no bounding box, no alarms).
       If the object moves significantly, suppression resets immediately.
    """
    def __init__(
        self,
        confirm_delay: float = 0.25,
        static_count_threshold: int = 150,
        static_time_threshold: float = 300.0,
        persistence_timeout: float = 2.0,
        lost_timeout: float = 8.0,
        position_tolerance_px: float = 45.0,
        alpha_smooth: float = 0.75,
        min_hits_for_confirm: int = 2
    ):
        self.confirm_delay = confirm_delay
        self.static_count_threshold = static_count_threshold
        self.static_time_threshold = static_time_threshold
        self.persistence_timeout = persistence_timeout
        self.lost_timeout = lost_timeout
        self.position_tolerance_px = position_tolerance_px
        self.alpha_smooth = alpha_smooth
        self.min_hits_for_confirm = min_hits_for_confirm

        self._next_track_id = 1
        self._tracks: Dict[int, TrackedTarget] = {}
        self._static_anchors: List[Dict[str, Any]] = []
        self._last_time = 0.0
        self.exclusion_zones: List[List[float]] = []

    def set_exclusion_zones(self, zones: List[List[float]]):
        """Sets normalized [x1, y1, x2, y2] zones (0.0 to 1.0) to ignore from AI tracking & alarms."""
        self.exclusion_zones = [list(z) for z in (zones or []) if len(z) >= 4]

    def _register_static_anchor(self, track: TrackedTarget, now: float):
        """Remembers location of confirmed static objects (vehicles/inanimate items) so brief flickering dropouts never re-alarm."""
        # Humans are dynamic living beings; NEVER register a person as an immovable static anchor!
        if track.category == "person":
            return
        self._static_anchors = [a for a in self._static_anchors if (now - a.get("time", 0.0)) < 600.0]
        for a in self._static_anchors:
            if a["category"] == track.category and a["label"] == track.label:
                d = ((track.anchor_cx - a["cx"]) ** 2 + (track.anchor_cy - a["cy"]) ** 2) ** 0.5
                if d < max(self.position_tolerance_px * 1.5, 55.0):
                    a["time"] = now
                    return
        self._static_anchors.append({
            "category": track.category,
            "label": track.label,
            "cx": track.anchor_cx,
            "cy": track.anchor_cy,
            "box": list(track.anchor_box),
            "time": now
        })

    def _is_near_static_anchor(self, det: AIDetection, now: float) -> bool:
        """Checks if a new detection falls within a known static/stationary zone."""
        # Humans are NEVER treated as static anchors!
        if det.category == "person":
            return False
        if not self._static_anchors:
            return False
        cx = det.box[0] + det.box[2] / 2.0
        cy = det.box[1] + det.box[3] / 2.0
        for a in self._static_anchors:
            if (now - a.get("time", 0.0)) > 600.0:
                continue
            if a["category"] == det.category and a["label"] == det.label:
                d = ((cx - a["cx"]) ** 2 + (cy - a["cy"]) ** 2) ** 0.5
                if d < max(self.position_tolerance_px * 1.5, 55.0):
                    a["time"] = now
                    return True
        return False

    def update(
        self,
        raw_detections: Optional[List[AIDetection]],
        now: Optional[float] = None,
        frame_shape: Tuple[int, ...] = (1080, 1920)
    ) -> List[AIDetection]:
        if now is None:
            now = time.time()
        dt = max(0.01, min(0.2, now - self._last_time)) if self._last_time > 0 else 0.033
        self._last_time = now

        frame_h, frame_w = frame_shape[:2] if len(frame_shape) >= 2 else (1080, 1920)

        # Case 1: Frame where raw inference was skipped (None passed)
        if raw_detections is None:
            # Maintain persistent confirmed tracks across frame intervals without flickering
            for t in self._tracks.values():
                if t.is_confirmed:
                    in_ex = self.exclusion_zones and is_box_in_exclusion_zone(
                        tuple(int(round(v)) for v in t.smoothed_box), self.exclusion_zones, frame_w, frame_h
                    )
                    if in_ex or (now - t.last_seen) > self.persistence_timeout:
                        t.visual_alpha = 0.0
                    elif t.is_static:
                        t.visual_alpha = 0.85
                    else:
                        t.visual_alpha = 1.0
                else:
                    t.visual_alpha = 0.0

            # Check for dead tracks
            to_remove = [tid for tid, t in self._tracks.items() if (now - t.last_seen) > max(3.0, self.persistence_timeout * 2.0)]
            for tid in to_remove:
                del self._tracks[tid]

            # Return active confirmed tracks with non-zero visual alpha
            return [
                t.to_ai_detection() for t in self._tracks.values()
                if t.is_confirmed and t.visual_alpha > 0.01
            ]

        # Case 2: Raw inference was run (list of detections, might be empty)
        # Filter out bicycles and any detections located inside user exclusion zones
        clean_raw = [
            d for d in raw_detections
            if getattr(d, 'label', '') != 'bicycle' and not is_box_in_exclusion_zone(d.box, self.exclusion_zones, frame_w, frame_h)
        ]

        matched_tracks = set()
        matched_detections = set()

        # Build candidate matches with IoU and centroid distance
        candidates = []
        for d_idx, det in enumerate(clean_raw):
            det_box = det.box
            det_cx = det_box[0] + det_box[2] / 2.0
            det_cy = det_box[1] + det_box[3] / 2.0

            for tid, track in self._tracks.items():
                # Prefer same category; allow same label
                if det.category != track.category and det.label != track.label:
                    continue

                # If existing track was marked static but has not been seen for > 1.5s,
                # do NOT match a fresh incoming detection to the dormant static track!
                if track.is_static and (now - track.last_seen) > 1.5:
                    continue

                track_box = tuple(int(round(v)) for v in track.smoothed_box)
                iou = compute_box_iou(det_box, track_box)
                dist = ((det_cx - track.cx) ** 2 + (det_cy - track.cy) ** 2) ** 0.5
                max_dim = max(det_box[2], det_box[3], track.smoothed_box[2], track.smoothed_box[3])
                dist_thresh = max(self.position_tolerance_px * 3.0, 2.0 * max_dim, 150.0)

                if iou >= 0.10 or dist <= dist_thresh:
                    score = (iou * 2.5) + max(0.0, 1.0 - (dist / max(1.0, dist_thresh)))
                    candidates.append((score, d_idx, tid, dist, iou))

        # Sort candidates descending by score
        candidates.sort(key=lambda c: c[0], reverse=True)

        for score, d_idx, tid, dist, iou in candidates:
            if d_idx in matched_detections or tid in matched_tracks:
                continue

            matched_detections.add(d_idx)
            matched_tracks.add(tid)
            det = clean_raw[d_idx]
            track = self._tracks[tid]

            # Update timing & hit count
            track.last_seen = now
            track.detection_count += 1
            if det.description:
                track.description = det.description

            # Coordinate & Confidence EMA smoothing
            alpha = self.alpha_smooth
            for i in range(4):
                track.smoothed_box[i] = (alpha * det.box[i]) + ((1.0 - alpha) * track.smoothed_box[i])
            track.confidence = (alpha * det.confidence) + ((1.0 - alpha) * track.confidence)

            # Stationary / Static object evaluation
            cx = det.box[0] + det.box[2] / 2.0
            cy = det.box[1] + det.box[3] / 2.0
            anchor_dist = ((cx - track.anchor_cx) ** 2 + (cy - track.anchor_cy) ** 2) ** 0.5
            anchor_box_t = tuple(int(round(v)) for v in track.anchor_box)
            anchor_iou = compute_box_iou(det.box, anchor_box_t)

            # Did the object move significantly?
            move_dist_thresh = max(self.position_tolerance_px * 1.5, 55.0)
            if anchor_dist > move_dist_thresh or anchor_iou < 0.35:
                # Target has actively moved away! Reset stationary anchor and static flag
                track.anchor_cx = cx
                track.anchor_cy = cy
                track.anchor_box = [float(v) for v in det.box]
                track.stationary_detections = 1
                track.stationary_start_time = now
                track.stationary_duration = 0.0
                track.is_static = False
                track.is_confirmed = True
                track.has_alerted = False  # Moved significantly, can alert again if confirmed in new position
            else:
                # Target remains in the same spot!
                track.stationary_detections += 1
                track.stationary_duration = now - track.stationary_start_time
                min_static_sec = 0.0 if self.static_count_threshold < 30 else (300.0 if track.category == "person" else 30.0)
                if (track.stationary_detections >= self.static_count_threshold and track.stationary_duration >= min_static_sec) or track.stationary_duration >= self.static_time_threshold:
                    track.is_static = True
                    self._register_static_anchor(track, now)

            # Confirmation evaluation (1-second debounce)
            time_elapsed = now - track.first_seen
            if time_elapsed >= self.confirm_delay and track.detection_count >= self.min_hits_for_confirm:
                track.is_confirmed = True

        # Create new tracks for unmatched clean detections
        for d_idx, det in enumerate(clean_raw):
            if d_idx not in matched_detections:
                tid = self._next_track_id
                self._next_track_id += 1
                track = TrackedTarget(tid, det, now)
                if self._is_near_static_anchor(det, now):
                    # Immediately recognized as an established stationary object
                    track.is_static = True
                    track.is_confirmed = True
                    track.has_alerted = True
                    track.stationary_detections = self.static_count_threshold
                    track.visual_alpha = 0.85
                elif self.confirm_delay <= 0.0:
                    track.is_confirmed = True
                    track.visual_alpha = 1.0
                self._tracks[tid] = track

        # Update visual alpha for all confirmed tracks without flickering
        for tid, t in self._tracks.items():
            if t.is_confirmed:
                in_ex = self.exclusion_zones and is_box_in_exclusion_zone(
                    tuple(int(round(v)) for v in t.smoothed_box), self.exclusion_zones, frame_w, frame_h
                )
                if in_ex or (now - t.last_seen) > self.persistence_timeout:
                    t.visual_alpha = 0.0
                elif t.is_static:
                    t.visual_alpha = 0.85
                else:
                    t.visual_alpha = 1.0
            else:
                t.visual_alpha = 0.0

        # Prune dead tracks
        to_remove = [tid for tid, t in self._tracks.items() if (now - t.last_seen) > max(3.0, self.persistence_timeout * 2.0)]
        for tid in to_remove:
            del self._tracks[tid]

        # Return confirmed detections with non-zero visual alpha
        return [
            t.to_ai_detection() for t in self._tracks.values()
            if t.is_confirmed and t.visual_alpha > 0.01
        ]

    def reset(self):
        """Resets all tracks."""
        self._tracks.clear()
        self._static_anchors.clear()
        self._next_track_id = 1
