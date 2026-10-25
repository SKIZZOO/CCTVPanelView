"""
CCTVPanelView - Standalone Headless 24/7 Surveillance & Recording Server
Designed for always-on servers, remote PCs, and background CCTV workstations.

Capabilities:
- 100% Headless: Runs with zero GUI overhead (QCoreApplication, no display/monitor needed).
- 24/7 Continuous & Motion AI Recording with Google Drive sync.
- Mobile Push Notifications (ntfy.sh & Telegram) with instant video clips.
- Integrated Web Dashboard (http://<server-ip>:8080) for phone/remote browser live monitoring.
- Windows Sleep Prevention: Uses Win32 SetThreadExecutionState to keep recording active.
"""

import os
import sys
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
import time
import signal
import ctypes
from typing import Dict, List, Any, Optional

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt6.QtCore import QCoreApplication, QTimer
from core.device_manager import DeviceManager
from core.camera_stream import CameraStreamWorker, StreamStatus, QualityMode
from core.alert_manager import AlertManager
from core.web_server import WebStreamingServer
from core.resource_manager import get_resource_manager


def enable_windows_sleep_prevention():
    """Tells Windows not to suspend system while CCTV recording daemon is active."""
    if sys.platform == "win32":
        try:
            # ES_CONTINUOUS = 0x80000000 | ES_SYSTEM_REQUIRED = 0x00000001 | ES_AWAYMODE_REQUIRED = 0x00000040
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000040)
            print("[CCTV Server] Windows execution state: System sleep prevented (24/7 recording enabled).")
        except Exception as e:
            print(f"[CCTV Server] Warning: Could not set execution state: {e}")


def restore_windows_sleep():
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        except Exception:
            pass


class CCTVHeadlessServer:
    def __init__(self, config_path: str = "cameras_config.json"):
        self.device_manager = DeviceManager(config_path)
        self.app_settings = self.device_manager.config.get("app_settings", {})
        self.alert_manager = AlertManager(
            snapshot_dir=self.app_settings.get("snapshot_dir", "snapshots"),
            recording_dir=self.app_settings.get("recording_dir", "recordings"),
        )
        # AlertManager dispatches both snapshot and completed-video notifications.
        self.alert_manager.set_app_settings(self.app_settings)

        self.active_workers: Dict[str, CameraStreamWorker] = {}
        self.web_server: Optional[WebStreamingServer] = None
        self._is_shutting_down = False

    def start(self):
        print("=================================================================")
        print("  CCTVPanelView - Standalone 24/7 Headless NVR Server")
        print("=================================================================")

        # 1. Apply performance optimizations
        rm = get_resource_manager()
        profile_key = self.app_settings.get("performance_profile", "medium")
        rm.apply_profile(profile_key, custom_settings=self.app_settings)
        enable_windows_sleep_prevention()

        # 2. Start Web Streaming & Dashboard Server
        web_port = int(self.app_settings.get("web_port", self.app_settings.get("web_server_port", 8080)))
        self.web_server = WebStreamingServer(self, port=web_port)
        if self.web_server.start():
            # Treat this link as a password. It expires when the server restarts.
            print(f"[CCTV Server] Private dashboard access link: {self.web_server.get_local_url()}")

        # 3. Start Camera Streams
        all_streams = self.device_manager.get_all_streams()
        print(f"[CCTV Server] Discovered {len(all_streams)} camera stream(s) in configuration.")

        for stream_info in all_streams:
            stream_id = stream_info.get("id")
            name = stream_info.get("display_title", "Stream")
            main_url = stream_info.get("url")
            sub_url = stream_info.get("sub_url", "")
            camera_ip = stream_info.get("camera_ip", "")
            camera_name = stream_info.get("camera_name", "Camera")
            cam_id = stream_info.get("camera_id", "")

            # Lens Tag
            is_lens2 = (
                stream_info.get("channel") == 1
                or "lens2" in stream_id.lower()
                or "lens 2" in name.lower()
                or "ptz" in stream_id.lower()
                or "ch01" in main_url
            )
            lens_tag = "Lens2" if is_lens2 else "Lens1"

            worker = CameraStreamWorker(stream_id, name, main_url, sub_url=sub_url)
            worker.set_alert_manager(self.alert_manager)
            worker.set_camera_ip(camera_ip)
            worker.set_camera_context(camera_name, lens_tag)

            # Apply effective settings & overrides
            eff_settings = self.device_manager.get_effective_camera_settings(cam_id)
            worker.apply_camera_settings(eff_settings)

            # Headless optimization: Run in GUI-paused mode so no OpenGL/widget memory is wasted
            worker.set_gui_rendering_paused(True)

            # Throttling
            worker.set_performance_throttling(
                display_fps_cap=15,
                ai_skip_frames=self.app_settings.get("ai_skip_frames", 6),
                ai_motion_gated_only=self.app_settings.get("ai_motion_gated_only", False),
                motion_skip_frames=self.app_settings.get("motion_skip_frames", 1),
                motion_downscale_width=self.app_settings.get("motion_downscale_width", 480)
            )

            # Quality
            worker.set_quality(QualityMode.ULTRA_2K if not self.app_settings.get("grid_substream", False) else QualityMode.LOW_SD)

            self.active_workers[stream_id] = worker
            worker.start()
            print(f"[CCTV Server] Started 24/7 worker for '{name}' ({stream_id})")

        print("-----------------------------------------------------------------")
        print(f"[CCTV Server] Started {len(self.active_workers)} workers; camera connections are asynchronous.")
        print("[CCTV Server] Press Ctrl+C at any time to stop safely.")
        print("=================================================================")

    def stop(self):
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        print("\n[CCTV Server] Graceful shutdown initiated...")

        if self.web_server:
            self.web_server.stop()

        for s_id, worker in list(self.active_workers.items()):
            try:
                print(f"[CCTV Server] Stopping worker {s_id}...")
                worker.flush_pending_snapshots()
                worker.stop_recording(wait=True, timeout=2.0)
                worker.stop()
            except Exception as e:
                print(f"[CCTV Server] Warning stopping worker {s_id}: {e}")

        self.alert_manager.flush_and_save_sync()
        restore_windows_sleep()
        print("[CCTV Server] All recordings flushed. Server terminated cleanly.")


def main():
    app = QCoreApplication(sys.argv)
    server = CCTVHeadlessServer()

    def handle_sig(sig, frame):
        server.stop()
        QTimer.singleShot(100, app.quit)

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    server.start()
    exit_code = app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
