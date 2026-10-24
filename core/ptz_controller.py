import os
import sys
import re
import time
import base64
import hashlib
import threading
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any

ALLOWED_DIRECTIONS = {
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "up_left": "up_left",
    "up_right": "up_right",
    "down_left": "down_left",
    "down_right": "down_right",
    "zoom_in": "zoomin",
    "zoom_out": "zoomout",
    "stop": "stop"
}

IP_REGEX = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")


def create_ws_security_header(user: str, password: str) -> str:
    """Constructs standard ONVIF WS-Security UsernameToken header with SHA-1 password digest."""
    if not user:
        return ""
    created = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    nonce_raw = os.urandom(16)
    nonce_b64 = base64.b64encode(nonce_raw).decode('utf-8')
    sha1 = hashlib.sha1()
    sha1.update(nonce_raw + created.encode('utf-8') + password.encode('utf-8'))
    digest = base64.b64encode(sha1.digest()).decode('utf-8')

    return f"""  <s:Header>
    <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
      <wsse:UsernameToken>
        <wsse:Username>{user}</wsse:Username>
        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest}</wsse:Password>
        <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce_b64}</wsse:Nonce>
        <wsu:Created>{created}</wsu:Created>
      </wsse:UsernameToken>
    </wsse:Security>
  </s:Header>"""


class PTZController:
    """
    High-Performance, Asynchronous ONVIF & CGI PTZ Controller.

    Features:
    - 100% Non-Blocking: Dispatches all motor commands to a background thread pool,
      ensuring the Qt GUI event loop never hitches or freezes.
    - Native ONVIF PTZ Support: Targets ONVIF PTZ service on port 8899 with WS-Security
      UsernameToken authentication (ContinuousMove, Stop, GotoPreset, SetPreset).
    - Auto-port adaptation: Automatically routes to port 8899 for CAM720 ONVIF hardware,
      with fallback to legacy CGI on port 80.
    - 8-Way directional navigation + Zoom In / Zoom Out.
    - Speed scaling (1 to 10).
    - Presets & Automated Patrol / Auto-Touring.
    """
    def __init__(self, camera_ip: str, username: str = "admin", password: str = "", port: int = 8899):
        clean_ip = str(camera_ip).strip()
        if not IP_REGEX.match(clean_ip) and not clean_ip.replace("-", "").isalnum():
            raise ValueError(f"Invalid camera IP or hostname: {clean_ip}")

        self.camera_ip = clean_ip
        self.username = str(username)
        self.password = str(password)
        # Cam720 cameras run ONVIF on 8899. If caller passed 80, default to 8899 for ONVIF
        p_val = int(port) if (1 <= int(port) <= 65535) else 8899
        self.port = 8899 if p_val == 80 else p_val
        self.legacy_port = 80
        self.speed = 5  # 1 to 10
        self.profile_token = "profile_0"

        # Background worker executor to guarantee 0ms UI latency
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix=f"PTZ_{self.camera_ip}")
        self._last_command_time = 0.0

        # Patrol / Auto-Tour state
        self._patrol_running = False
        self._patrol_thread: Optional[threading.Thread] = None
        self._patrol_presets = [1, 2, 3, 4]
        self._patrol_interval = 6.0

    def move(self, direction: str, speed: Optional[int] = None):
        """
        Direction: 'up', 'down', 'left', 'right', 'up_left', 'up_right',
                   'down_left', 'down_right', 'zoom_in', 'zoom_out', 'stop'
        Executes asynchronously in background thread in <0.2ms.
        """
        dir_clean = str(direction).lower().strip()
        s = speed if speed is not None else self.speed
        s_clamped = max(1, min(10, int(s)))

        if dir_clean == "stop":
            self.stop()
            return

        self._executor.submit(self._do_move, dir_clean, s_clamped)

    def zoom_in(self):
        self.move("zoom_in")

    def zoom_out(self):
        self.move("zoom_out")

    def step_move(self, direction: str, speed: Optional[int] = None, duration_sec: float = 0.35):
        """
        Executes a timed pulse move (nudge / step mode):
        dispatches move, waits duration_sec in background thread, and stops.
        100% non-blocking to GUI thread.
        """
        dir_clean = str(direction).lower().strip()
        s = speed if speed is not None else self.speed
        s_clamped = max(1, min(10, int(s)))
        dur = max(0.1, min(2.0, float(duration_sec)))
        self._executor.submit(self._do_step_move, dir_clean, s_clamped, dur)

    def _do_step_move(self, direction: str, speed: int, duration_sec: float):
        self._do_move(direction, speed)
        time.sleep(duration_sec)
        self._do_stop()

    def set_profile(self, profile_token: str):
        """Sets the ONVIF profile token (e.g. 'profile_0' or 'profile_1')."""
        self.profile_token = str(profile_token).strip() or "profile_0"

    def stop(self):
        """Asynchronously stops camera motors in <0.2ms."""
        self._executor.submit(self._do_stop)

    def goto_preset(self, preset_num: int):
        p_safe = max(1, min(128, int(preset_num)))
        self._executor.submit(self._do_goto_preset, p_safe)

    def set_preset(self, preset_num: int):
        p_safe = max(1, min(128, int(preset_num)))
        self._executor.submit(self._do_set_preset, p_safe)

    def start_patrol(self, presets: List[int] = None, interval_sec: float = 6.0):
        """Starts automated touring between camera presets."""
        if self._patrol_running:
            return
        if presets:
            self._patrol_presets = presets
        self._patrol_interval = max(3.0, interval_sec)
        self._patrol_running = True
        self._patrol_thread = threading.Thread(target=self._patrol_loop, daemon=True, name=f"Patrol_{self.camera_ip}")
        self._patrol_thread.start()

    def stop_patrol(self):
        self._patrol_running = False
        if self._patrol_thread:
            self._patrol_thread.join(timeout=0.5)
            self._patrol_thread = None

    def is_patrolling(self) -> bool:
        return self._patrol_running

    def _patrol_loop(self):
        idx = 0
        while self._patrol_running:
            if not self._patrol_presets:
                break
            target_preset = self._patrol_presets[idx % len(self._patrol_presets)]
            self.goto_preset(target_preset)
            idx += 1
            # Sleep in small increments for responsive stop
            steps = int(self._patrol_interval * 10)
            for _ in range(steps):
                if not self._patrol_running:
                    break
                time.sleep(0.1)

    # =========================================================================
    # INTERNAL ASYNCHRONOUS WORKER METHODS (Run in background ThreadPool)
    # =========================================================================

    def _do_move(self, direction: str, speed: int):
        # Scale speed 1..10 to velocity 0.1..1.0
        vel = float(speed) / 10.0
        diag_vel = round(vel * 0.7071, 3)

        # Vector mapping
        vectors = {
            "up": (0.0, vel, 0.0),
            "down": (0.0, -vel, 0.0),
            "left": (-vel, 0.0, 0.0),
            "right": (vel, 0.0, 0.0),
            "up_left": (-diag_vel, diag_vel, 0.0),
            "up_right": (diag_vel, diag_vel, 0.0),
            "down_left": (-diag_vel, -diag_vel, 0.0),
            "down_right": (diag_vel, -diag_vel, 0.0),
            "zoom_in": (0.0, 0.0, vel),
            "zoom_out": (0.0, 0.0, -vel),
        }

        if direction not in vectors:
            self._do_stop()
            return

        vx, vy, vz = vectors[direction]

        # 1. Try ONVIF ContinuousMove on port 8899
        if vz != 0.0:
            body = f"""<tptz:ContinuousMove>
  <tptz:ProfileToken>{self.profile_token}</tptz:ProfileToken>
  <tptz:Velocity>
    <tt:Zoom x="{vz}" space="http://www.onvif.org/ver10/tptz/ZoomSpaces/VelocityGenericSpace"/>
  </tptz:Velocity>
</tptz:ContinuousMove>"""
        else:
            body = f"""<tptz:ContinuousMove>
  <tptz:ProfileToken>{self.profile_token}</tptz:ProfileToken>
  <tptz:Velocity>
    <tt:PanTilt x="{vx}" y="{vy}" space="http://www.onvif.org/ver10/tptz/PanTiltSpaces/VelocityGenericSpace"/>
  </tptz:Velocity>
</tptz:ContinuousMove>"""

        ok = self._send_onvif_request("/onvif/ptz_service", body)
        if not ok:
            # Fallback to legacy CGI
            cgi_act = ALLOWED_DIRECTIONS.get(direction, "stop")
            url = f"http://{self.camera_ip}:{self.legacy_port}/web/cgi-bin/hi3510/ptzctrl.cgi?-step=0&-act={cgi_act}&-speed={speed}"
            self._send_cgi_request(url)

    def _do_stop(self):
        body = f"""<tptz:Stop>
  <tptz:ProfileToken>{self.profile_token}</tptz:ProfileToken>
  <tptz:PanTilt>true</tptz:PanTilt>
  <tptz:Zoom>true</tptz:Zoom>
</tptz:Stop>"""
        ok = self._send_onvif_request("/onvif/ptz_service", body)
        if not ok:
            url = f"http://{self.camera_ip}:{self.legacy_port}/web/cgi-bin/hi3510/ptzctrl.cgi?-step=0&-act=stop&-speed=5"
            self._send_cgi_request(url)

    def _do_goto_preset(self, preset_num: int):
        body = f"""<tptz:GotoPreset>
  <tptz:ProfileToken>{self.profile_token}</tptz:ProfileToken>
  <tptz:PresetToken>{preset_num}</tptz:PresetToken>
</tptz:GotoPreset>"""
        ok = self._send_onvif_request("/onvif/ptz_service", body)
        if not ok:
            url = f"http://{self.camera_ip}:{self.legacy_port}/web/cgi-bin/hi3510/preset.cgi?-act=goto&-number={preset_num}"
            self._send_cgi_request(url)

    def _do_set_preset(self, preset_num: int):
        body = f"""<tptz:SetPreset>
  <tptz:ProfileToken>{self.profile_token}</tptz:ProfileToken>
  <tptz:PresetName>Preset{preset_num}</tptz:PresetName>
  <tptz:PresetToken>{preset_num}</tptz:PresetToken>
</tptz:SetPreset>"""
        ok = self._send_onvif_request("/onvif/ptz_service", body)
        if not ok:
            url = f"http://{self.camera_ip}:{self.legacy_port}/web/cgi-bin/hi3510/preset.cgi?-act=set&-number={preset_num}"
            self._send_cgi_request(url)

    def _send_onvif_request(self, endpoint: str, body_xml: str) -> bool:
        url = f"http://{self.camera_ip}:{self.port}{endpoint}"
        sec_header = create_ws_security_header(self.username, self.password)
        soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
            xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
{sec_header}
  <s:Body>
{body_xml}
  </s:Body>
</s:Envelope>"""
        req = urllib.request.Request(
            url,
            data=soap_envelope.encode('utf-8'),
            headers={"Content-Type": "application/soap+xml; charset=utf-8"}
        )
        try:
            with urllib.request.urlopen(req, timeout=1.8) as resp:
                return resp.status in (200, 201)
        except Exception:
            return False

    def _send_cgi_request(self, url: str) -> bool:
        try:
            req = urllib.request.Request(url)
            if self.username and self.password:
                auth = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
                req.add_header("Authorization", f"Basic {auth}")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False

    def set_white_light(self, enable: bool):
        """Asynchronously dispatches camera CGI and auxiliary commands to toggle white LED floodlight."""
        def _task():
            act = "lighton" if enable else "lightoff"
            mode = "on" if enable else "off"
            urls = [
                f"http://{self.camera_ip}:{self.legacy_port}/web/cgi-bin/hi3510/ptzctrl.cgi?-step=0&-act={act}",
                f"http://{self.camera_ip}:{self.legacy_port}/cgi-bin/hi3510/ptzctrl.cgi?-step=0&-act={act}",
                f"http://{self.camera_ip}:{self.legacy_port}/web/cgi-bin/hi3510/param.cgi?cmd=setwhiteled&-mode={mode}",
                f"http://{self.camera_ip}:{self.legacy_port}/cgi-bin/hi3510/param.cgi?cmd=setwhiteled&-mode={mode}",
            ]
            for u in urls:
                try:
                    self._send_cgi_request(u)
                except Exception:
                    pass
        self._executor.submit(_task)

    def shutdown(self):
        """Cleanly releases background threadpool executor and cancels pending tasks."""
        self._patrol_running = False
        try:
            self._executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            try:
                self._executor.shutdown(wait=False)
            except Exception:
                pass
