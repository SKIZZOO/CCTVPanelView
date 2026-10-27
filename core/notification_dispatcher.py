"""
Unified Mobile & Phone Notification Dispatcher for CCTVPanelView.

Supports:
1. ntfy.sh - Zero-setup, instant mobile push notifications for iOS & Android
   (sends high-priority alerts with snapshot photos, visual descriptions, and click-to-view links).
2. Telegram Bot - Sends instant high-res photo snapshots with detailed visual captions.
3. Discord Webhook - Optional rich embeds for Discord channels.
"""

import os
import io
import time
import json
import uuid
import socket
import urllib.request
import urllib.error
import threading
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from core.notification_policy import allows_notification


def get_local_lan_ip() -> str:
    """Discovers the active local LAN IPv4 address (e.g. 192.168.1.50)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def encode_multipart_formdata(fields: Dict[str, str], files: Dict[str, Tuple[str, bytes, str]]) -> Tuple[bytes, str]:
    """Encodes form fields and binary files into multipart/form-data for Telegram/Discord."""
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    buffer = io.BytesIO()

    for key, value in fields.items():
        buffer.write(f"--{boundary}\r\n".encode("utf-8"))
        buffer.write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        buffer.write(str(value).encode("utf-8"))
        buffer.write(b"\r\n")

    for key, (filename, file_bytes, content_type) in files.items():
        buffer.write(f"--{boundary}\r\n".encode("utf-8"))
        buffer.write(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode("utf-8"))
        buffer.write(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        buffer.write(file_bytes)
        buffer.write(b"\r\n")

    buffer.write(f"--{boundary}--\r\n".encode("utf-8"))
    content_type_header = f"multipart/form-data; boundary={boundary}"
    return buffer.getvalue(), content_type_header


def generate_secret_ntfy_topic() -> str:
    """Generates an unguessable 24-character cryptographic secret topic for ntfy.sh."""
    import secrets
    return f"cctv_pv_{secrets.token_hex(12)}"


def to_header_safe(text: str) -> str:
    """Transliterates Romanian/Unicode characters to clean ASCII for HTTP headers."""
    table = {
        ord('ă'): 'a', ord('Ă'): 'A',
        ord('â'): 'a', ord('Â'): 'A',
        ord('î'): 'i', ord('Î'): 'I',
        ord('ș'): 's', ord('Ș'): 'S',
        ord('ş'): 's', ord('Ş'): 'S',
        ord('ț'): 't', ord('Ț'): 'T',
        ord('ţ'): 't', ord('Ţ'): 'T',
    }
    translit = text.translate(table)
    return translit.encode("ascii", "ignore").decode("ascii")


def resolve_gdrive_file_id(filename: Optional[str] = None, max_retries: int = 2) -> Optional[str]:
    """Resolves the direct Google Drive cloud_id for a given file name."""
    if not filename:
        return None
    base = os.path.basename(filename)
    import glob
    import sqlite3

    for attempt in range(max_retries + 1):
        account_dirs = glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Google\DriveFS\*"))
        for adir in account_dirs:
            db_path = os.path.join(adir, "mirror_metadata_sqlite.db")
            if not os.path.exists(db_path):
                continue
            try:
                con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                cur = con.cursor()
                row = cur.execute("""
                    SELECT s.cloud_id
                    FROM stable_ids s
                    JOIN item_properties p ON s.stable_id = p.item_stable_id
                    WHERE p.key='local-title' AND p.value = ?
                """, (base,)).fetchone()
                con.close()
                if row and row[0]:
                    return str(row[0])
            except Exception:
                pass
        if attempt < max_retries:
            time.sleep(0.6)
    return None


def resolve_gdrive_url(filename: Optional[str] = None, fallback_folder: str = "alarms") -> str:
    """
    Resolves the direct Google Drive cloud URL for a given file or folder.
    First checks mirror_metadata_sqlite.db for the file's cloud_id.
    If not yet synced, returns direct search query URL for that exact file name.
    """
    gdrive_alarms_id = "1xBSjjmOZXHTu19gfDbB2Y6H2Lns9sqXk"     # alarms folder on Google Drive

    if filename:
        cloud_id = resolve_gdrive_file_id(filename, max_retries=1)
        if cloud_id:
            return f"https://drive.google.com/file/d/{cloud_id}/view"
        base = os.path.basename(filename)
        encoded_fn = urllib.parse.quote(base)
        return f"https://drive.google.com/drive/u/0/search?q={encoded_fn}"

    return f"https://drive.google.com/drive/folders/{gdrive_alarms_id}"


class NotificationDispatcher:
    """
    Manages non-blocking asynchronous mobile notifications to user's phone.
    Performs delivery outside RTSP capture and PyQt GUI event loops.
    """

    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        self.settings: Dict[str, Any] = settings or {}
        self._last_alert_sent_times: Dict[str, float] = {}
        self._lock = threading.Lock()
        self.lan_ip = get_local_lan_ip()

    def update_settings(self, new_settings: Dict[str, Any]):
        with self._lock:
            self.settings.update(new_settings)

    @property
    def is_phone_enabled(self) -> bool:
        return bool(self.settings.get("phone_notifications_enabled", False)) and bool(self.settings.get("master_alerts_enabled", True))

    @property
    def notify_video_enabled(self) -> bool:
        return bool(self.settings.get("phone_notify_video", self.settings.get("send_video_to_phone", True)))

    @property
    def ntfy_enabled(self) -> bool:
        return bool(self.settings.get("ntfy_enabled", False))

    @property
    def ntfy_topic(self) -> str:
        return self.settings.get("ntfy_topic", "").strip()

    @property
    def ntfy_server(self) -> str:
        srv = self.settings.get("ntfy_server", "").strip()
        return srv.rstrip("/") if srv else "https://ntfy.sh"

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.settings.get("telegram_enabled", False))

    @property
    def telegram_token(self) -> str:
        return self.settings.get("telegram_token", self.settings.get("telegram_bot_token", "")).strip()

    @property
    def telegram_chat_id(self) -> str:
        return str(self.settings.get("telegram_chat_id", "")).strip()

    @property
    def discord_enabled(self) -> bool:
        return bool(self.settings.get("discord_enabled", False))

    @property
    def discord_webhook(self) -> str:
        return self.settings.get("discord_webhook_url", "").strip()

    @property
    def cooldown_sec(self) -> float:
        return float(self.settings.get("phone_alert_cooldown_sec", 10.0))

    def should_notify_label(self, label: str, alert_entry: Optional[Dict[str, Any]] = None) -> bool:
        """
        Strict user notification filter for mobile push (ntfy / Telegram / Discord).
        Ensures users receive ONLY the categories they explicitly chose.
        """
        entry = dict(alert_entry or {})
        entry["label"] = label
        with self._lock:
            return allows_notification(self.settings, entry)

    def send_alert(self, alert_entry: Dict[str, Any]):
        """Dispatches immediate snapshot alert to phone in a background daemon thread."""
        if not self.is_phone_enabled:
            return

        label = alert_entry.get("label", "ALARM")
        if not self.should_notify_label(label, alert_entry):
            return

        stream_id = alert_entry.get("stream_id", "default")
        now = time.time()

        with self._lock:
            last_time = self._last_alert_sent_times.get(stream_id, 0.0)
            if now - last_time < self.cooldown_sec:
                # Suppress spam within cooldown window for this stream
                return
            self._last_alert_sent_times[stream_id] = now

        # Launch dispatch in background thread
        thread = threading.Thread(
            target=self._dispatch_worker,
            args=(alert_entry.copy(),),
            daemon=True,
            name=f"Notify-{stream_id}"
        )
        thread.start()

    def send_video_alert(self, alert_entry: Dict[str, Any]):
        """Dispatches recorded MP4 video clip to phone once encoding is complete."""
        if not self.is_phone_enabled or not self.notify_video_enabled:
            return

        label = alert_entry.get("label", "ALARM")
        if not self.should_notify_label(label, alert_entry):
            return

        stream_id = alert_entry.get("stream_id", "default")
        thread = threading.Thread(
            target=self._dispatch_video_worker,
            args=(alert_entry.copy(),),
            daemon=True,
            name=f"NotifyVideo-{stream_id}"
        )
        thread.start()

    def _dispatch_worker(self, alert_entry: Dict[str, Any]):
        """Runs on background thread; executes HTTP requests with short timeouts."""
        # Recheck after queueing: disarming or changing categories also applies
        # to work that has not started delivery yet.
        if not self.is_phone_enabled or not self.should_notify_label(alert_entry.get("label", ""), alert_entry):
            return
        cam_name = alert_entry.get("camera_name", "Camera")
        label = alert_entry.get("label", "ALARM")
        conf = alert_entry.get("confidence", 0.0)
        desc = alert_entry.get("description", "")
        time_str = alert_entry.get("time_short", datetime.now().strftime("%H:%M:%S"))
        snap_path = alert_entry.get("snapshot_path", "")
        trigger_reason = alert_entry.get("trigger_reason", "")

        # Read snapshot JPEG bytes if file exists
        snap_bytes: Optional[bytes] = None
        if snap_path and os.path.exists(snap_path):
            try:
                with open(snap_path, "rb") as f:
                    snap_bytes = f.read()
            except Exception as e:
                print(f"[Notifier] Failed reading snapshot file: {e}")

        # 1. ntfy.sh Mobile Push
        if self.ntfy_enabled and self.ntfy_topic:
            try:
                snap_fn = os.path.basename(snap_path) if snap_path else ""
                self._send_ntfy(cam_name, label, conf, desc, time_str, trigger_reason, snap_bytes, snap_filename=snap_fn)
            except Exception as e:
                print(f"[Notifier] ntfy push error: {e}")

        # 2. Telegram Bot
        if self.telegram_enabled and self.telegram_token and self.telegram_chat_id:
            try:
                self._send_telegram(cam_name, label, conf, desc, time_str, trigger_reason, snap_bytes)
            except Exception as e:
                print(f"[Notifier] Telegram send error: {e}")

        # 3. Discord Webhook
        if self.discord_enabled and self.discord_webhook:
            try:
                self._send_discord(cam_name, label, conf, desc, time_str, trigger_reason, snap_bytes)
            except Exception as e:
                print(f"[Notifier] Discord send error: {e}")

    def _dispatch_video_worker(self, alert_entry: Dict[str, Any]):
        """Runs on background thread; uploads recorded MP4 clip to phone services."""
        if not self.notify_video_enabled:
            return
        # Recheck after queueing: disarming or changing categories also applies
        # to work that has not started delivery yet.
        if not self.is_phone_enabled or not self.should_notify_label(alert_entry.get("label", ""), alert_entry):
            return
        cam_name = alert_entry.get("camera_name", "Camera")
        label = alert_entry.get("label", "ALARM")
        conf = alert_entry.get("confidence", 0.0)
        desc = alert_entry.get("description", "")
        time_str = alert_entry.get("time_short", datetime.now().strftime("%H:%M:%S"))

        video_path = (
            alert_entry.get("video_highlighted_path") or
            alert_entry.get("video_path") or
            alert_entry.get("video_raw_path")
        )
        if not video_path or not os.path.exists(video_path):
            return

        try:
            file_size = os.path.getsize(video_path)
            # Require at least 2KB and maximum 15MB (ntfy upload limit)
            if file_size <= 2048 or file_size > 15 * 1024 * 1024:
                return
            with open(video_path, "rb") as f:
                video_bytes = f.read()
        except Exception as e:
            print(f"[Notifier] Failed reading video file for dispatch: {e}")
            return

        filename = os.path.basename(video_path)

        # 1. ntfy.sh Video Push
        if self.ntfy_enabled and self.ntfy_topic:
            try:
                self._send_ntfy_video(cam_name, label, conf, desc, time_str, video_bytes, filename)
            except Exception as e:
                print(f"[Notifier] ntfy video push error: {e}")

        # 2. Telegram Bot sendVideo
        if self.telegram_enabled and self.telegram_token and self.telegram_chat_id:
            try:
                self._send_telegram_video(cam_name, label, conf, desc, time_str, video_bytes, filename)
            except Exception as e:
                print(f"[Notifier] Telegram video send error: {e}")

        # 3. Discord Webhook Video
        if self.discord_enabled and self.discord_webhook:
            try:
                self._send_discord_video(cam_name, label, conf, desc, time_str, video_bytes, filename)
            except Exception as e:
                print(f"[Notifier] Discord video send error: {e}")

    def _send_ntfy(
        self,
        cam_name: str,
        label: str,
        conf: float,
        desc: str,
        time_str: str,
        trigger_reason: str,
        snap_bytes: Optional[bytes],
        snap_filename: str = ""
    ):
        """Sends rich push notification via ntfy.sh."""
        topic = self.ntfy_topic
        server = self.ntfy_server
        url = f"{server}/{topic}"

        conf_str = f" ({int(conf * 100)}%)" if conf > 0 else ""
        clean_cam = cam_name.split(" (")[0].strip()
        title = f"[ALERT] {clean_cam}: {label.title()}{conf_str}"

        # Clean ASCII-safe title & message for HTTP headers
        safe_title = to_header_safe(title) or title
        message = desc or f"{label.title()} detected at {time_str}"
        safe_message = to_header_safe(message) or message

        port = self.settings.get("web_port", 8080)
        web_url = f"http://{self.lan_ip}:{port}/"
        gdrive_url = resolve_gdrive_url(snap_filename, "alarms")

        headers = {
            "Title": safe_title,
            "Priority": "urgent" if "PERSON" in label.upper() else "high",
            "Tags": "warning,camera",
            "Click": gdrive_url,
            "Actions": f"view, Open in Google Drive, {gdrive_url}; view, Live Camera, {web_url}"
        }

        if snap_bytes:
            headers["Filename"] = "snapshot.jpg"
            headers["Message"] = safe_message
            req = urllib.request.Request(url, data=snap_bytes, headers=headers, method="PUT")
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    pass
                return
            except urllib.error.HTTPError as he:
                if he.code == 413:
                    # Daily quota or file size limit exceeded on ntfy: fallback to text push
                    fallback_headers = {
                        "Title": safe_title,
                        "Priority": headers.get("Priority", "high"),
                        "Tags": headers.get("Tags", "warning"),
                        "Click": gdrive_url,
                        "Actions": f"view, Open in Google Drive, {gdrive_url}; view, Live Camera, {web_url}"
                    }
                    req_fb = urllib.request.Request(url, data=safe_message.encode("utf-8"), headers=fallback_headers, method="POST")
                    with urllib.request.urlopen(req_fb, timeout=8) as resp:
                        pass
                    return
                raise
        else:
            data = safe_message.encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=8) as resp:
                pass

    def _send_telegram(
        self,
        cam_name: str,
        label: str,
        conf: float,
        desc: str,
        time_str: str,
        trigger_reason: str,
        snap_bytes: Optional[bytes]
    ):
        """Sends photo or text message to Telegram chat via Bot API."""
        token = self.telegram_token
        chat_id = self.telegram_chat_id
        conf_str = f" ({int(conf * 100)}%)" if conf > 0 else ""

        caption = (
            f"[DETECTION ALERT] {cam_name}\n"
            f"Target: {label.title()}{conf_str}\n"
            f"Detection: `{desc}`\n"
            f"Time: {time_str}\n"
        )
        if trigger_reason:
            caption += f"Trigger: {trigger_reason}\n"

        if snap_bytes:
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            fields = {
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "Markdown"
            }
            files = {
                "photo": ("snapshot.jpg", snap_bytes, "image/jpeg")
            }
            body, content_type = encode_multipart_formdata(fields, files)
            req = urllib.request.Request(url, data=body, headers={"Content-Type": content_type}, method="POST")
        else:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": caption,
                "parse_mode": "Markdown"
            }
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")

        with urllib.request.urlopen(req, timeout=10) as resp:
            pass

    def _send_discord(
        self,
        cam_name: str,
        label: str,
        conf: float,
        desc: str,
        time_str: str,
        trigger_reason: str,
        snap_bytes: Optional[bytes]
    ):
        """Sends rich embed with snapshot to Discord Webhook."""
        webhook_url = self.discord_webhook
        conf_str = f" ({int(conf * 100)}%)" if conf > 0 else ""

        embed = {
            "title": f"[CCTV Alert] {cam_name}",
            "description": f"**Detection:** {desc}\n**Target:** {label.title()}{conf_str}\n**Time:** {time_str}",
            "color": 0xef4444 if "PERSON" in label.upper() else 0x38bdf8,
            "footer": {"text": "CCTVPanelView Mobile Alert"}
        }

        if snap_bytes:
            embed["image"] = {"url": "attachment://snapshot.jpg"}
            fields = {"payload_json": json.dumps({"embeds": [embed]})}
            files = {"file": ("snapshot.jpg", snap_bytes, "image/jpeg")}
            body, content_type = encode_multipart_formdata(fields, files)
            req = urllib.request.Request(webhook_url, data=body, headers={"Content-Type": content_type}, method="POST")
        else:
            payload = {"embeds": [embed]}
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(webhook_url, data=body, headers={"Content-Type": "application/json"}, method="POST")

        with urllib.request.urlopen(req, timeout=8) as resp:
            pass

    def _send_ntfy_video(
        self,
        cam_name: str,
        label: str,
        conf: float,
        desc: str,
        time_str: str,
        video_bytes: bytes,
        filename: str
    ):
        """Sends recorded MP4 video attachment via ntfy.sh."""
        topic = self.ntfy_topic
        server = self.ntfy_server
        url = f"{server}/{topic}"

        conf_str = f" ({int(conf * 100)}%)" if conf > 0 else ""
        clean_cam = cam_name.split(" (")[0].strip()
        # Clean ASCII-safe title & message for HTTP headers
        title = f"[Video Clip] {clean_cam} - {label.title()}{conf_str}"
        safe_title = to_header_safe(title) or title
        message = f"Play recorded incident clip (10s): {desc or label}"
        safe_message = to_header_safe(message) or message

        port = self.settings.get("web_port", 8080)
        cloud_id = resolve_gdrive_file_id(filename)
        if cloud_id:
            direct_gdrive_url = f"https://drive.google.com/file/d/{cloud_id}/view"
        else:
            direct_gdrive_url = ""
        gdrive_url = direct_gdrive_url or resolve_gdrive_url(filename, "alarms")

        headers = {
            "Title": safe_title,
            "Priority": "high",
            "Tags": "movie_camera,warning",
            "Filename": filename if filename.endswith(".mp4") else "alert_clip.mp4",
            "Message": safe_message,
            "Actions": f"view, Watch on Google Drive, {gdrive_url}; view, Live Feed, {web_url}"
        }
        if direct_gdrive_url:
            headers["Click"] = direct_gdrive_url

        try:
            req = urllib.request.Request(url, data=video_bytes, headers=headers, method="PUT")
            with urllib.request.urlopen(req, timeout=20) as resp:
                pass
        except urllib.error.HTTPError as he:
            if he.code == 413:
                # Video file exceeds ntfy public limit (2MB) or daily quota: send link notification
                fallback_headers = {
                    "Title": safe_title,
                    "Priority": "high",
                    "Tags": "movie_camera,warning",
                    "Click": gdrive_url,
                    "Actions": f"view, Watch on Google Drive, {gdrive_url}; view, Live Feed, {web_url}"
                }
                fb_msg = f"Alert clip saved to Google Drive ({len(video_bytes) // 1024} KB). Tap to watch or download."
                req_fb = urllib.request.Request(url, data=fb_msg.encode("utf-8"), headers=fallback_headers, method="POST")
                with urllib.request.urlopen(req_fb, timeout=10) as resp:
                    pass
                return
            raise

    def _send_telegram_video(
        self,
        cam_name: str,
        label: str,
        conf: float,
        desc: str,
        time_str: str,
        video_bytes: bytes,
        filename: str
    ):
        """Sends native playable MP4 video to Telegram chat."""
        token = self.telegram_token
        chat_id = self.telegram_chat_id
        conf_str = f" ({int(conf * 100)}%)" if conf > 0 else ""

        caption = (
            f"[VIDEO CLIP ALERT] {cam_name}\n"
            f"Target: {label.title()}{conf_str}\n"
            f"Detection: `{desc}`\n"
            f"Time: {time_str}\n"
        )

        url = f"https://api.telegram.org/bot{token}/sendVideo"
        fields = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "Markdown",
            "supports_streaming": "true"
        }
        files = {
            "video": (filename if filename.endswith(".mp4") else "clip.mp4", video_bytes, "video/mp4")
        }
        body, content_type = encode_multipart_formdata(fields, files)
        req = urllib.request.Request(url, data=body, headers={"Content-Type": content_type}, method="POST")
        with urllib.request.urlopen(req, timeout=25) as resp:
            pass

    def _send_discord_video(
        self,
        cam_name: str,
        label: str,
        conf: float,
        desc: str,
        time_str: str,
        video_bytes: bytes,
        filename: str
    ):
        """Sends MP4 video attachment to Discord Webhook."""
        webhook_url = self.discord_webhook
        conf_str = f" ({int(conf * 100)}%)" if conf > 0 else ""

        content = f"**Video Clip Alert: {cam_name}** - {label.title()}{conf_str}\n{desc}"
        fields = {"content": content}
        files = {"file": (filename if filename.endswith(".mp4") else "clip.mp4", video_bytes, "video/mp4")}
        body, content_type = encode_multipart_formdata(fields, files)
        req = urllib.request.Request(webhook_url, data=body, headers={"Content-Type": content_type}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            pass

    def send_test_notification(self, service: str = "all") -> Tuple[bool, str]:
        """Sends an immediate test push alert to verify phone reception."""
        results = []
        now_str = datetime.now().strftime("%H:%M:%S")

        # Minimal valid 1x1 test JPEG
        sample_jpg = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06'
            b'\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c'
            b' $.#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f'
            b'\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08'
            b'\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9'
        )

        test_cam = "Front Entrance (Dual-Lens 2K)"
        test_desc = "Person: white shirt, blue jeans (standing)"

        # Test ntfy
        if service in ["all", "ntfy"]:
            if self.ntfy_enabled and self.ntfy_topic:
                try:
                    self._send_ntfy(
                        cam_name=test_cam,
                        label="TEST_PERSON",
                        conf=0.95,
                        desc=test_desc,
                        time_str=now_str,
                        trigger_reason="Manual Test Trigger",
                        snap_bytes=sample_jpg
                    )
                    results.append("[OK] ntfy.sh: Notification dispatched successfully!")
                except Exception as e:
                    results.append(f"[ERROR] ntfy.sh error: {e}")
            else:
                results.append("[WARNING] ntfy.sh is disabled or topic name is unset.")

        # Test Telegram
        if service in ["all", "telegram"]:
            if self.telegram_enabled and self.telegram_token and self.telegram_chat_id:
                try:
                    self._send_telegram(
                        cam_name=test_cam,
                        label="TEST_PERSON",
                        conf=0.95,
                        desc=test_desc,
                        time_str=now_str,
                        trigger_reason="Manual Test Trigger",
                        snap_bytes=sample_jpg
                    )
                    results.append("[OK] Telegram: Message and snapshot dispatched successfully!")
                except Exception as e:
                    results.append(f"[ERROR] Telegram error: {e}")
            else:
                results.append("[WARNING] Telegram is not configured (missing Token or Chat ID).")

        # Test Discord
        if service in ["all", "discord"]:
            if self.discord_enabled and self.discord_webhook:
                try:
                    self._send_discord(
                        cam_name=test_cam,
                        label="TEST_PERSON",
                        conf=0.95,
                        desc=test_desc,
                        time_str=now_str,
                        trigger_reason="Manual Test Trigger",
                        snap_bytes=sample_jpg
                    )
                    results.append("[OK] Discord: Notification dispatched successfully!")
                except Exception as e:
                    results.append(f"[ERROR] Discord error: {e}")

        success = any("[OK]" in r for r in results)
        return success, "\n".join(results)
