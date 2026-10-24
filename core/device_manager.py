import json
import os
import sys
import socket
import tempfile
import uuid
import cv2
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

def get_config_path() -> str:
    """Returns the absolute path to cameras_config.json in the application root directory."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "cameras_config.json")

DEFAULT_CONFIG_FILE = get_config_path()

class DeviceManager:
    """
    Manages camera inventory, persistent configuration, dual-lens channel mapping,
    and network scanning.
    """
    def __init__(self, config_file: Optional[str] = None):
        if not config_file:
            self.config_file = get_config_path()
        elif not os.path.isabs(config_file):
            if getattr(sys, "frozen", False):
                base = os.path.dirname(os.path.abspath(sys.executable))
            else:
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_file = os.path.join(base, config_file)
        else:
            self.config_file = config_file

        self.config: Dict[str, Any] = {
            "version": "2.0",
            "app_settings": {
                "default_layout": "2x2",
                "default_quality": "MAX",
                "hardware_acceleration": True,
                "low_latency_mode": True,
                "master_alerts_enabled": True,
                "motion_enabled": True,
                "ai_detection_enabled": True,
                "notify_person": True,
                "notify_vehicle": True,
                "notify_animal": True,
                "notify_motion": True,
                "show_desktop_notifications": True,
                "sound_alarms_enabled": True,
                "auto_record_on_motion": True,
                "motion_min_area": 2800,
                "motion_confirm_delay": 1.2,
                "motion_foliage_filter": True,
                "motion_cooldown_sec": 5.0,
                "ai_conf_threshold": 0.38,
                "vehicle_conf_threshold": 0.38,
                "theme": "Cyber Dark",
                "has_completed_onboarding": False,
                "recording_dir": "recordings",
                "snapshot_dir": "snapshots",
                "ntfy_topic": "",
                "ntfy_enabled": False,
                "telegram_enabled": False,
                "discord_enabled": False,
                "close_action": "ask",
                "performance_profile": "balanced"
            },
            "cameras": []
        }
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Failed to load config {self.config_file}: {e}")
        else:
            self.save_config()

    def save_config(self):
        temp_path = None
        try:
            folder = os.path.dirname(os.path.abspath(self.config_file))
            os.makedirs(folder, exist_ok=True)
            # Write beside the destination so replacement stays on the same volume.
            # Serialization or disk failures leave the previous configuration intact.
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder,
                                             prefix=".camera-config-", suffix=".tmp", delete=False) as f:
                temp_path = f.name
                json.dump(self.config, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.config_file)
        except Exception as e:
            print(f"Failed to save config: {e}")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def get_cameras(self) -> List[Dict[str, Any]]:
        return self.config.get("cameras", [])

    def get_camera_by_id(self, camera_id: str) -> Optional[Dict[str, Any]]:
        for cam in self.get_cameras():
            if cam.get("id") == camera_id:
                return cam
        return None

    def is_camera_configured(self, cam_or_id: Any) -> bool:
        """
        Determines whether a camera is fully configured with valid security credentials.
        Surveillance cameras strictly require an RTSP authentication password to connect.
        """
        if isinstance(cam_or_id, str):
            cam = self.get_camera_by_id(cam_or_id)
        elif isinstance(cam_or_id, dict):
            cam = cam_or_id
        else:
            return False

        if not cam:
            return False

        # A camera CANNOT connect or stream without an authentication password
        pwd = str(cam.get("password", "")).strip()
        if not pwd:
            return False

        # If user explicitly marked configured: False, respect that
        if cam.get("configured") is False:
            return False

        return True

    def get_all_streams(self) -> List[Dict[str, Any]]:
        """
        Returns a flattened list of all streams across all cameras.
        For a dual-lens camera, this yields both Lens 1 and Lens 2.
        """
        streams = []
        for cam in self.get_cameras():
            cam_name = cam.get("name", "Unknown")
            is_dual = cam.get("is_dual_lens", False)
            is_cfg = self.is_camera_configured(cam)
            for s in cam.get("streams", []):
                stream_copy = dict(s)
                stream_copy["camera_id"] = cam.get("id")
                stream_copy["camera_name"] = cam_name
                stream_copy["camera_ip"] = cam.get("ip")
                stream_copy["is_dual_lens"] = is_dual
                stream_copy["display_title"] = f"{cam_name} - {s.get('name', 'Stream')}"
                stream_copy["configured"] = is_cfg
                stream_copy["has_password"] = bool(str(cam.get("password", "")).strip())
                stream_copy["is_configured"] = is_cfg
                streams.append(stream_copy)
        return streams

    def get_stream_by_id(self, stream_id: str) -> Optional[Dict[str, Any]]:
        for s in self.get_all_streams():
            if s.get("id") == stream_id:
                return s
        return None

    def add_camera(self, camera_data: Dict[str, Any]):
        cameras = self.config.setdefault("cameras", [])
        # Generate ID if missing
        if "id" not in camera_data or not camera_data["id"]:
            camera_data["id"] = f"cam_{uuid.uuid4().hex}"
        cameras.append(camera_data)
        self.save_config()

    def update_camera(self, camera_id: str, updated_data: Dict[str, Any]):
        cameras = self.config.setdefault("cameras", [])
        for idx, cam in enumerate(cameras):
            if cam.get("id") == camera_id:
                cameras[idx] = updated_data
                self.save_config()
                return True
        return False

    def update_stream_name(self, stream_id: str, new_name: str) -> bool:
        """Updates the friendly name and display_title for a specific stream/lens."""
        cameras = self.config.setdefault("cameras", [])
        for cam in cameras:
            cam_name = cam.get("name", "Camera")
            for s in cam.get("streams", []):
                if s.get("id") == stream_id:
                    s["name"] = new_name
                    s["display_title"] = f"{cam_name} - {new_name}"
                    self.save_config()
                    return True
        return False

    def delete_camera(self, camera_id: str):
        cameras = self.config.get("cameras", [])
        self.config["cameras"] = [c for c in cameras if c.get("id") != camera_id]
        self.save_config()

    def get_camera_settings(self, camera_id: str) -> Dict[str, Any]:
        """Returns the specific settings dict for a camera, or empty dict if default."""
        cam = self.get_camera_by_id(camera_id)
        if not cam:
            return {}
        return dict(cam.get("settings", {}))

    def update_camera_settings(self, camera_id: str, new_settings: Dict[str, Any]) -> bool:
        """Saves custom settings for a specific camera."""
        cam = self.get_camera_by_id(camera_id)
        if cam is not None:
            settings = cam.setdefault("settings", {})
            settings.update(new_settings)
            self.save_config()
            return True
        return False

    def batch_update_camera_settings(self, updates_dict: Dict[str, Dict[str, Any]]):
        """Atomically updates settings for multiple cameras and writes config to disk once."""
        modified = False
        for camera_id, new_settings in updates_dict.items():
            cam = self.get_camera_by_id(camera_id)
            if cam is not None:
                settings = cam.setdefault("settings", {})
                settings.update(new_settings)
                modified = True
        if modified:
            self.save_config()

    def get_effective_camera_settings(self, camera_id: str) -> Dict[str, Any]:
        """
        Returns merged settings for a camera: global app_settings overridden by
        the camera's specific settings.
        """
        merged = dict(self.config.get("app_settings", {}))
        cam_settings = self.get_camera_settings(camera_id)
        merged.update(cam_settings)
        return merged

    def get_stream_exclusion_zones(self, stream_id: str = "", camera_id: Optional[str] = None) -> List[List[float]]:
        """Returns normalized exclusion zones [[x1, y1, x2, y2], ...] for a stream or camera."""
        if stream_id:
            for cam in self.get_cameras():
                for s in cam.get("streams", []):
                    if s.get("id") == stream_id:
                        if "exclusion_zones" in s:
                            return [list(z) for z in s.get("exclusion_zones", []) if len(z) >= 4]
                if camera_id and cam.get("id") == camera_id:
                    if "exclusion_zones" in cam.get("settings", {}):
                        return [list(z) for z in cam["settings"].get("exclusion_zones", []) if len(z) >= 4]

        if camera_id:
            cam_settings = self.get_camera_settings(camera_id)
            if "exclusion_zones" in cam_settings:
                return [list(z) for z in cam_settings.get("exclusion_zones", []) if len(z) >= 4]
        return []

    def set_stream_exclusion_zones(self, stream_id: str, zones: List[List[float]], camera_id: Optional[str] = None) -> bool:
        """Saves normalized exclusion zones for a stream and/or camera."""
        saved = False
        clean_zones = [list(z) for z in (zones or []) if len(z) >= 4]
        for cam in self.config.get("cameras", []):
            for s in cam.get("streams", []):
                if stream_id and s.get("id") == stream_id:
                    s["exclusion_zones"] = clean_zones
                    saved = True
            if camera_id and cam.get("id") == camera_id:
                cam.setdefault("settings", {})["exclusion_zones"] = clean_zones
                saved = True

        if saved:
            self.save_config()
            return True
        return False

    @staticmethod
    def test_connection(rtsp_url: str, timeout_sec: float = 3.5) -> Dict[str, Any]:
        """
        Tests whether an RTSP stream can be opened and decoded.
        Waits for keyframe (I-frame) decoding up to timeout_sec.
        """
        import time
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;4000000|buffer_size;1024000"
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            return {"success": False, "error": "Could not connect to RTSP endpoint (Check IP, port, or password)."}
        
        start_t = time.time()
        ret = False
        frame = None
        while (time.time() - start_t) < timeout_sec:
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                break
            time.sleep(0.08)
            
        if not ret or frame is None or frame.size == 0:
            cap.release()
            return {"success": False, "error": "Connected to RTSP stream, but waiting for video keyframe timed out."}
            
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or (frame.shape[1] if frame is not None else 0)
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or (frame.shape[0] if frame is not None else 0)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        cap.release()
        
        return {
            "success": True,
            "width": w,
            "height": h,
            "fps": fps,
            "message": f"Successfully connected! {w}x{h} @ {fps:.1f}fps"
        }

    @staticmethod
    def get_local_subnet() -> str:
        """Determines the primary active local subnet base prefix (e.g. '192.168.0')."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            parts = local_ip.split(".")
            if len(parts) == 4 and not parts[0].startswith("127"):
                return ".".join(parts[:3])
        except Exception:
            pass
        try:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if not ip.startswith("127.") and not ip.startswith("169.254"):
                    return ".".join(ip.split(".")[:3])
        except Exception:
            pass
        return "192.168.0"

    @staticmethod
    def get_arp_ips(subnet_base: str = "") -> List[str]:
        """Extracts known IP addresses from the system ARP cache matching the subnet."""
        ips = []
        try:
            import subprocess, re
            out = subprocess.check_output(["arp", "-a"], text=True, stderr=subprocess.DEVNULL)
            pattern = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
            for line in out.splitlines():
                m = pattern.search(line)
                if m:
                    ip = m.group(1)
                    if not ip.endswith(".255") and not ip.startswith(("224.", "239.", "255.", "127.")):
                        if subnet_base:
                            if ip.startswith(subnet_base + "."):
                                ips.append(ip)
                        else:
                            ips.append(ip)
        except Exception:
            pass
        return list(dict.fromkeys(ips))

    @staticmethod
    def scan_local_subnet(subnet_base: Optional[str] = None, start: int = 1, end: int = 254) -> List[Dict[str, Any]]:
        """
        Fast multi-threaded scan for active RTSP / ONVIF surveillance cameras.
        Optimized with ARP cache pre-check and multi-port verification (554, 8899, 34567, 8000).
        """
        if not subnet_base:
            subnet_base = DeviceManager.get_local_subnet()

        arp_ips = set(DeviceManager.get_arp_ips(subnet_base))

        def check_host(ip_str):
            target_ports = [554, 8899, 34567, 8000]
            detected_port = None
            detected_proto = "RTSP"
            has_rtsp = False

            timeout = 0.9 if ip_str in arp_ips else 0.65

            for p in target_ports:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(timeout)
                    res = s.connect_ex((ip_str, p))
                    s.close()
                    if res == 0:
                        if p == 554:
                            has_rtsp = True
                            detected_port = 554
                            detected_proto = "RTSP"
                            break
                        elif p == 8899:
                            detected_port = p
                            detected_proto = "ONVIF"
                        elif p == 34567 and not detected_port:
                            detected_port = p
                            detected_proto = "CAM720 / NetSDK"
                        elif p == 8000 and not detected_port:
                            detected_port = p
                            detected_proto = "Hikvision"
                except Exception:
                    continue

            if detected_port is not None:
                return {
                    "ip": ip_str,
                    "port": 554 if has_rtsp else (554 if detected_port in (8899, 34567) else detected_port),
                    "protocol": detected_proto
                }
            return None

        subnet_ips = [f"{subnet_base}.{i}" for i in range(start, end + 1)]
        candidates = sorted(subnet_ips, key=lambda ip: 0 if ip in arp_ips else 1)

        results = []
        with ThreadPoolExecutor(max_workers=90) as ex:
            for item in ex.map(check_host, candidates):
                if item:
                    results.append(item)

        seen_ips = set()
        deduped = []
        for dev in results:
            if dev["ip"] not in seen_ips:
                seen_ips.add(dev["ip"])
                deduped.append(dev)

        def ip_sort_key(d):
            try:
                return int(d["ip"].split(".")[-1])
            except Exception:
                return 0

        deduped.sort(key=ip_sort_key)
        return deduped

