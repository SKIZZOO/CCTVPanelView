import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from core.phone_video import MAX_PREVIEW_BYTES, prepare_phone_video


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class PhoneVideoTests(unittest.TestCase):
    def test_real_preview_has_phone_codecs_faststart_size_and_preserves_original(self):
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.mp4"
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                            "testsrc2=size=1280x720:rate=20", "-f", "lavfi", "-i", "sine=frequency=440",
                            "-t", "5", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
                            str(source)], check=True, timeout=40, **options)
            original = source.read_bytes()
            preview = prepare_phone_video(source)
            self.assertEqual(source.read_bytes(), original)
            self.assertLessEqual(len(preview), MAX_PREVIEW_BYTES)
            self.assertLess(preview.index(b"moov"), preview.index(b"mdat"))
            output = Path(temp) / "preview.mp4"
            output.write_bytes(preview)
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(output)],
                                   capture_output=True, check=True, timeout=10, **options)
            streams = json.loads(probe.stdout)["streams"]
            video = next(s for s in streams if s["codec_type"] == "video")
            audio = next(s for s in streams if s["codec_type"] == "audio")
            self.assertEqual(video["codec_name"], "h264")
            self.assertEqual(video["pix_fmt"], "yuv420p")
            self.assertLessEqual(video["width"], 640)
            self.assertEqual(audio["codec_name"], "aac")
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(output), "-f", "null", "-"],
                           check=True, timeout=20, **options)
