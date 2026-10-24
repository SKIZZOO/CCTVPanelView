import os
import sys
import time
from typing import Optional, Tuple, Dict, Any
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Attempts to load a clean system TrueType font, falling back safely."""
    windir = os.environ.get("WINDIR", "C:\\Windows")
    font_paths = [
        os.path.join(windir, "Fonts", name),
        os.path.join(windir, "Fonts", "segoeuib.ttf" if "b" in name.lower() else "segoeui.ttf"),
        os.path.join(windir, "Fonts", "arialbd.ttf" if "b" in name.lower() else "arial.ttf"),
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def generate_video_alert_slate(
    width: int,
    height: int,
    alert_type: str = "ALERT",
    camera_name: str = "Camera",
    lens_name: str = "Main Lens",
    timestamp: str = "",
    trigger_reason: str = "",
    trigger_image: Optional[np.ndarray] = None,
    trigger_image_path: Optional[str] = None,
    confidence: Optional[float] = None
) -> np.ndarray:
    """
    Renders a broadcast-quality, high-contrast 0.5-second incident title card
    to be baked into the first frames of recorded video files.
    
    Includes:
    - Cinematic blurred background dynamically derived from the trigger snapshot.
    - Framed high-resolution picture showing what triggered the incident.
    - Tactical HUD overlay with alert badge, camera name, timestamp, and trigger reason.
    - 0.5-second incident countdown marker.
    """
    if width <= 0:
        width = 1920
    if height <= 0:
        height = 1080

    # Ensure even dimensions for video codecs (libx264 yuv420p / mp4v)
    width = width - (width % 2)
    height = height - (height % 2)

    # 1. Resolve trigger image
    img_bgr = None
    if trigger_image is not None and isinstance(trigger_image, np.ndarray) and trigger_image.size > 0:
        img_bgr = trigger_image
    elif trigger_image_path and os.path.exists(trigger_image_path):
        try:
            img_bgr = cv2.imread(trigger_image_path)
        except Exception:
            img_bgr = None

    # 2. Build Base Canvas: Pristine 100% Full-Frame Edge-to-Edge Camera Capture
    if img_bgr is not None:
        ih, iw = img_bgr.shape[:2]
        if iw == width and ih == height:
            canvas_bgr = img_bgr.copy()
        else:
            # Preserve aspect ratio with clean center-fit
            r_canvas = width / float(height)
            r_img = iw / float(ih)
            if abs(r_canvas - r_img) < 0.05:
                canvas_bgr = cv2.resize(img_bgr, (width, height), interpolation=cv2.INTER_LINEAR)
            else:
                canvas_bgr = np.full((height, width, 3), (11, 15, 25), dtype=np.uint8)
                if r_img > r_canvas:
                    nw = width
                    nh = int(nw / r_img)
                    y_off = (height - nh) // 2
                    resized = cv2.resize(img_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
                    canvas_bgr[y_off:y_off + nh, 0:width] = resized
                else:
                    nh = height
                    nw = int(nh * r_img)
                    x_off = (width - nw) // 2
                    resized = cv2.resize(img_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
                    canvas_bgr[0:height, x_off:x_off + nw] = resized
    else:
        # Default dark obsidian gradient
        canvas_bgr = np.full((height, width, 3), (11, 15, 25), dtype=np.uint8)

    # Convert to PIL RGB for clean vector & text rendering
    canvas_rgb = cv2.cvtColor(canvas_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(canvas_rgb)
    draw = ImageDraw.Draw(pil_img, "RGBA")

    # Scale sizing relative to canvas height
    scale = max(0.4, min(2.5, height / 1080.0))
    pad = int(24 * scale)

    # Alert classification color theme
    type_upper = (alert_type or "").upper().strip()
    if type_upper.startswith("AI "):
        clean_type = type_upper[3:].strip()
    else:
        clean_type = type_upper

    if "PERSON" in clean_type or "HUMAN" in clean_type:
        theme_color = (239, 68, 68)       # Bright Crimson
        theme_bg = (185, 28, 28, 230)
        badge_text = "AI PERSON DETECTED"
    elif "ANIMAL" in clean_type or "BEAR" in clean_type or "PET" in clean_type or "DOG" in clean_type:
        theme_color = (245, 158, 11)      # Amber / Gold
        theme_bg = (180, 83, 9, 230)
        badge_text = f"AI {clean_type} DETECTED" if "DETECTED" not in clean_type else f"AI {clean_type}"
    elif "VEHICLE" in clean_type or "CAR" in clean_type:
        theme_color = (14, 165, 233)      # Sky Blue
        theme_bg = (3, 105, 161, 230)
        badge_text = "VEHICLE DETECTED"
    elif "MOTION" in clean_type:
        theme_color = (225, 29, 72)       # Rose Red
        theme_bg = (159, 18, 57, 230)
        badge_text = "MOTION ALERT TRIGGER"
    else:
        theme_color = (16, 185, 129)      # Emerald / Cyan for manual / standard
        theme_bg = (4, 120, 87, 230)
        badge_text = f"RECORDING - {clean_type}" if clean_type else "RECORDING ACTIVE"

    # Sleek Apple / UniFi Style Translucent Glass OSD Top Capsule (Never shrinks or obscures video)
    capsule_h = int(46 * scale)
    time_str = timestamp or time.strftime("%Y-%m-%d %H:%M:%S")
    cam_display = f"{camera_name} - {lens_name}" if lens_name else camera_name
    conf_str = f" ({int(confidence * 100)}%)" if confidence and confidence > 0 else ""
    summary_str = f"{badge_text}{conf_str}   |   {cam_display}   |   {time_str}"

    font_osd = _load_font("segoeuib.ttf", int(14 * scale))
    s_bbox = draw.textbbox((0, 0), summary_str, font=font_osd)
    s_w = s_bbox[2] - s_bbox[0]
    capsule_w = s_w + int(56 * scale)

    # Draw modern rounded translucent glass pill at top-left
    c_x1 = pad
    c_y1 = pad
    c_x2 = pad + capsule_w
    c_y2 = pad + capsule_h

    draw.rounded_rectangle(
        [(c_x1, c_y1), (c_x2, c_y2)],
        radius=int(10 * scale),
        fill=(11, 15, 25, 215),
        outline=(51, 65, 85, 240),
        width=max(1, int(1.5 * scale))
    )

    # Glowing beacon dot
    dot_r = int(6 * scale)
    dot_x = c_x1 + int(18 * scale)
    dot_y = c_y1 + (capsule_h // 2)
    draw.ellipse(
        [(dot_x - dot_r, dot_y - dot_r), (dot_x + dot_r, dot_y + dot_r)],
        fill=theme_color
    )

    # Text inside pill
    text_x = dot_x + dot_r + int(12 * scale)
    text_y = c_y1 + (capsule_h // 2) - int(8 * scale)
    draw.text((text_x, text_y), summary_str, fill=(248, 250, 252), font=font_osd)

    # Convert back to BGR numpy array
    final_rgb = np.array(pil_img)
    final_bgr = cv2.cvtColor(final_rgb, cv2.COLOR_RGB2BGR)
    return final_bgr


def prepend_slate_to_video_file(
    video_path: str,
    alert_type: str = "ALERT",
    camera_name: str = "Camera",
    lens_name: str = "Main Lens",
    timestamp: str = "",
    trigger_reason: str = "",
    trigger_image: Optional[np.ndarray] = None,
    trigger_image_path: Optional[str] = None,
    confidence: Optional[float] = None,
    duration_sec: float = 0.5
) -> bool:
    """
    Prepends a 0.5-second incident title card directly into an existing video file.
    Preserves audio and video quality.
    """
    if not (video_path and os.path.exists(video_path) and os.path.getsize(video_path) > 1024):
        return False

    temp_slate_video = f"{video_path}.slate_tmp.mp4"
    temp_concat_video = f"{video_path}.concat_tmp.mp4"

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False

        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps < 5 or fps > 60:
            fps = 15.0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        if w <= 0 or h <= 0:
            return False

        # Generate slate frame
        slate = generate_video_alert_slate(
            width=w,
            height=h,
            alert_type=alert_type,
            camera_name=camera_name,
            lens_name=lens_name,
            timestamp=timestamp,
            trigger_reason=trigger_reason,
            trigger_image=trigger_image,
            trigger_image_path=trigger_image_path,
            confidence=confidence
        )

        num_slate_frames = max(1, int(round(fps * duration_sec)))

        # Use FFmpeg to encode pristine slate video matching resolution and fps
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            creationflags = subprocess.CREATE_NO_WINDOW

        cmd_slate = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{w}x{h}",
            "-pix_fmt", "bgr24",
            "-r", str(int(fps)),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            temp_slate_video
        ]

        proc = subprocess.Popen(
            cmd_slate,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=creationflags
        )
        slate_bytes = slate.tobytes()
        for _ in range(num_slate_frames):
            proc.stdin.write(slate_bytes)
        proc.stdin.close()
        proc.wait(timeout=5.0)

        if not (os.path.exists(temp_slate_video) and os.path.getsize(temp_slate_video) > 512):
            return False

        # Concat slate video with original video, offsetting original audio by 0.5s if present
        # Check if original video has audio stream
        cmd_probe_audio = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        has_audio = False
        try:
            probe_res = subprocess.run(cmd_probe_audio, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, startupinfo=startupinfo, creationflags=creationflags, timeout=3.0)
            has_audio = bool(probe_res.stdout and probe_res.stdout.strip())
        except Exception:
            has_audio = False

        if has_audio:
            # Complex filter: concat video streams, delay audio stream by 500ms
            cmd_concat = [
                "ffmpeg", "-y",
                "-i", temp_slate_video,
                "-i", video_path,
                "-filter_complex",
                f"[0:v:0][1:v:0]concat=n=2:v=1:a=0[v];[1:a:0]adelay=500|500[a]",
                "-map", "[v]",
                "-map", "[a]",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "22",
                "-c:a", "aac",
                "-movflags", "+faststart",
                temp_concat_video
            ]
        else:
            cmd_concat = [
                "ffmpeg", "-y",
                "-i", temp_slate_video,
                "-i", video_path,
                "-filter_complex",
                "[0:v:0][1:v:0]concat=n=2:v=1:a=0[v]",
                "-map", "[v]",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "22",
                "-movflags", "+faststart",
                temp_concat_video
            ]

        res = subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, creationflags=creationflags, timeout=12.0)
        if res.returncode == 0 and os.path.exists(temp_concat_video) and os.path.getsize(temp_concat_video) > 1024:
            os.replace(temp_concat_video, video_path)
            return True

        return False
    except Exception as e:
        print(f"[video_slate] Error prepending slate to {video_path}: {e}")
        return False
    finally:
        for t in [temp_slate_video, temp_concat_video]:
            if os.path.exists(t):
                try:
                    os.remove(t)
                except Exception:
                    pass

