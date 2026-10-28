"""Bounded, temporary H.264/AAC previews for notification attachments."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

MAX_PREVIEW_BYTES = 1_800_000


def prepare_phone_video(path):
    """Keep the source untouched; return a complete MP4 preview under 2 MB."""
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "json", str(path)], capture_output=True, timeout=15,
                           check=True, **options)
    duration = float(json.loads(probe.stdout)["format"]["duration"])
    if not 0 < duration < 86400:
        raise ValueError("Invalid clip duration")
    # Bound CPU work and size. Longer recordings remain available locally.
    duration = min(duration, 60.0)
    bitrate = min(900_000, int(MAX_PREVIEW_BYTES * 8 * .85 / duration) - 32_000)
    with tempfile.TemporaryDirectory(prefix="cctv-phone-") as temp:
        output = Path(temp) / "preview.mp4"
        for factor in (1.0, .65):
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(path),
                            "-t", str(duration), "-map", "0:v:0", "-map", "0:a:0?",
                            "-vf", "scale=640:360:force_original_aspect_ratio=decrease:force_divisible_by=2,fps=12",
                            "-c:v", "libx264", "-preset", "veryfast", "-threads", "1",
                            "-b:v", str(max(64_000, int(bitrate * factor))), "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "32k", "-ac", "1", "-movflags", "+faststart",
                            str(output)], capture_output=True, timeout=120, check=True, **options)
            if 1024 < output.stat().st_size <= MAX_PREVIEW_BYTES:
                return output.read_bytes()
    raise ValueError("Clip preview exceeds the attachment limit")
