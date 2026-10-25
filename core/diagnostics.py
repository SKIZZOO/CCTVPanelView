"""Offline checks for packaged builds. Never opens a camera or alters user settings."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


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
        from core.device_manager import DeviceManager
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
    except Exception as error:
        checks["error"] = str(error)
    passed = bool(checks) and "error" not in checks and all(checks.values())
    report = {"passed": passed, "checks": checks}
    output = next((a.split("=", 1)[1] for a in argv if a.startswith("--self-test-report=")), None)
    if output:
        Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if passed else 1
