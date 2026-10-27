"""Offline checks for packaged builds. Never opens a camera or alters user settings."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def run_update_check(argv):
    """Read-only packaged HTTPS check against the fixed official release API."""
    from core.updates import check_latest
    report = {"passed": False}
    try:
        release = check_latest()
        report.update(passed=True, latest_version=release.version, installer_sha256=release.sha256)
    except Exception as error:
        report["error_type"] = type(error).__name__
    output = next((arg.split("=", 1)[1] for arg in argv if arg.startswith("--update-check-report=")), None)
    if output:
        Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["passed"] else 1


def run_camera_diagnostics(argv):
    """Explicit read-only camera checks; reports omit URLs and credentials."""
    from core.device_manager import DeviceManager
    config = next((a.split("=", 1)[1] for a in argv if a.startswith("--camera-config=")), "cameras_config.json")
    output = next((a.split("=", 1)[1] for a in argv if a.startswith("--camera-report=")), "camera-diagnostics.json")
    results = []
    try:
        cameras = json.loads(Path(config).read_text(encoding="utf-8")).get("cameras", [])
        for camera_index, camera in enumerate(cameras):
            for stream_index, stream in enumerate(camera.get("streams", [])):
                started = time.monotonic()
                result = DeviceManager.test_connection(stream.get("url", ""))
                results.append(dict(camera_index=camera_index, stream_index=stream_index,
                                    elapsed_sec=round(time.monotonic() - started, 2), **result))
        report = {"passed": bool(results) and all(r["success"] for r in results), "streams": results}
    except Exception:
        report = {"passed": False, "error": "Camera configuration could not be tested.", "streams": results}
    Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["passed"] else 1


def run_self_test(argv):
    checks = {}
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    try:
        for name in ("core.camera_stream", "core.web_server", "cctv_server", "ui.main_window", "PyQt6.QtMultimedia"):
            importlib.import_module(name)
            checks[name] = True
        import cv2
        import numpy as np
        net = cv2.dnn.readNetFromONNX(str(root / "yolov5n.onnx"))
        net.setInput(cv2.dnn.blobFromImage(np.zeros((640, 640, 3), np.uint8), 1/255, (640, 640), swapRB=True))
        checks["model_inference"] = bool(net.forward().size)
        for binary in ("ffmpeg", "ffplay", "ffprobe"):
            result = subprocess.run([binary, "-version"], capture_output=True, timeout=30,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            checks[binary] = result.returncode == 0
        from core.sound_manager import SoundManager, SoundProfile
        import io, wave
        sounds = SoundManager()
        sound_path = sounds.get_sound_file_path(SoundProfile.SIREN)
        with wave.open(io.BytesIO(sounds.scaled_wav(sound_path, 25)), "rb") as sound:
            checks["scaled_alert_audio"] = sound.getnframes() > 100
        from core.rtsp_audio import select_audio_track
        from core.audio_talk_controller import encode_g711
        checks["intercom_audio_codec"] = encode_g711(b"\x00\x00", "PCMU") == b"\xff"
        track = select_audio_track("m=audio 0 RTP/AVP 8\r\na=control:talk\r\na=sendonly\r\n", "rtsp://127.0.0.1/camera/")
        checks["intercom_track_selection"] = track[0].endswith("/camera/talk")
        from core.device_manager import DeviceManager
        from core.updates import version_tuple, parse_release
        from core.installation import preserve_upgrade_profile
        from core.version import APP_VERSION
        checks["update_version_ordering"] = version_tuple("2.10.0") > version_tuple("2.9.0")
        checks["installed_version"] = version_tuple(APP_VERSION) >= (2, 3, 0)
        import ssl
        from core.network_tls import verified_tls_context
        context = verified_tls_context()
        checks["ntfy_tls_context"] = context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname and context.cert_store_stats()["x509_ca"] > 0
        from core.notification_dispatcher import NotificationDispatcher
        import core.notification_dispatcher as notification_module
        class OfflineNtfyResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit): return b'{"id":"offline-fixture","event":"message"}'
        original_open = notification_module.urllib.request.urlopen
        try:
            requests = []
            def offline_open(request, timeout, context=None):
                if context is None or context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
                    raise ValueError("Notification request lacks verified TLS context")
                requests.append(request)
                return OfflineNtfyResponse()
            notification_module.urllib.request.urlopen = offline_open
            notifier = NotificationDispatcher({"ntfy_enabled": True, "ntfy_topic": "offline-fixture"})
            notifier._send_ntfy("Fixture", "PERSON", .9, "Offline fixture", "12:00", "fixture", b"jpeg-fixture")
            notifier._send_ntfy_video("Fixture", "PERSON", .9, "Offline fixture", "12:00", b"video-fixture", "fixture.mp4")
            checks["ntfy_photo_video_requests"] = [request.get_method() for request in requests] == ["PUT", "PUT"]
        finally:
            notification_module.urllib.request.urlopen = original_open
        with tempfile.TemporaryDirectory() as temp:
            # Exercise the same spawned native decoder used by real cameras.
            # This also catches frozen multiprocessing/bootstrap regressions.
            from core.capture_process import IsolatedCapture
            video = str(Path(temp) / "decoder.avi")
            writer = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*"MJPG"), 15, (64, 48))
            if not writer.isOpened():
                raise RuntimeError("Cannot create decoder diagnostic video")
            for value in range(30):
                writer.write(np.full((48, 64, 3), value * 5, np.uint8))
            writer.release()
            capture = IsolatedCapture(open_timeout=15)
            try:
                opened = capture.open(video)
                ok, frame = capture.read() if opened else (False, None)
                checks["isolated_decoder"] = bool(ok and frame.shape == (48, 64, 3))
            finally:
                capture.release()
            path = Path(temp) / "config.json"
            manager = DeviceManager(str(path))
            manager.config["app_settings"]["default_layout"] = "3x3"
            manager.save_config()
            checks["configuration_roundtrip"] = DeviceManager(str(path)).config["app_settings"]["default_layout"] == "3x3"
            manager.config["app_settings"]["session_slot_assignments"] = {"0": "fixture-stream", "1": ""}
            manager.save_config()
            before = path.read_bytes()
            # The installer uses this same backup/preservation path.
            installed_path = Path(temp) / "cameras_config.json"
            installed_path.write_bytes(before)
            preserve_upgrade_profile(temp)
            checks["upgrade_profile_preserved"] = installed_path.read_bytes() == before and bool(list((Path(temp) / "config-backups").glob("*.json")))
    except Exception as error:
        checks["error"] = str(error)
        import traceback
        checks["error_traceback"] = traceback.format_exc()
    passed = bool(checks) and "error" not in checks and all(checks.values())
    report = {"passed": passed, "checks": checks}
    output = next((a.split("=", 1)[1] for a in argv if a.startswith("--self-test-report=")), None)
    if output:
        Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if passed else 1
