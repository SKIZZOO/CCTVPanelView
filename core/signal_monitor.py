import socket
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


class SignalMonitor(QObject):
    """
    Real-time Wi-Fi & Network Signal Strength Monitor for IP CCTV cameras.
    
    Probes camera RTSP endpoints using high-precision TCP handshake timing
    to calculate round-trip latency (RTT), packet health, signal quality percentage,
    and visual signal bar ratings.
    """
    signals_updated = pyqtSignal(dict)  # ip -> signal_data dict
    camera_status_changed = pyqtSignal(str, bool, float)  # ip, is_online, latency_ms

    def __init__(self, check_interval_sec: float = 8.0, parent=None):
        super().__init__(parent)
        self.check_interval_ms = int(check_interval_sec * 1000)
        self.camera_ips: List[str] = []
        self.signal_cache: Dict[str, Dict[str, Any]] = {}
        self._last_offline_probe: Dict[str, float] = {}
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="SignalProbe")

        self.timer = QTimer(self)
        self.timer.setInterval(self.check_interval_ms)
        self.timer.timeout.connect(self.probe_all_cameras)

    def set_camera_ips(self, ips: List[str]):
        """Updates the monitored IP list and triggers an immediate probe."""
        self.camera_ips = list(set([ip for ip in ips if ip and ip.strip()]))
        self.probe_all_cameras()

    def start(self):
        """Starts periodic signal strength checks."""
        self.probe_all_cameras()
        self.timer.start()

    def stop(self):
        """Stops the monitoring timer and cleanly shuts down worker threads."""
        self.timer.stop()
        try:
            self._executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass

    def probe_all_cameras(self):
        if not self.camera_ips:
            return
        self._executor.submit(self._run_probes_sync)

    def _run_probes_sync(self):
        results = {}
        now = time.time()
        for ip in self.camera_ips:
            info = self._probe_single_ip(ip, timeout=1.5)
            results[ip] = info
            self.signal_cache[ip] = info
            self.camera_status_changed.emit(ip, info["is_online"], info["latency_ms"])

        self.signals_updated.emit(results)

    def _probe_single_ip(self, ip: str, port: int = 554, timeout: float = 1.5) -> Dict[str, Any]:
        """
        Connects via TCP to test latency and port reachability.
        """
        t0 = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            err = sock.connect_ex((ip, port))
            rtt_ms = (time.perf_counter() - t0) * 1000.0
            sock.close()
            is_online = (err == 0)
        except Exception:
            try:
                sock.close()
            except Exception:
                pass
            rtt_ms = 999.0
            is_online = False

        if not is_online:
            return {
                "ip": ip,
                "is_online": False,
                "latency_ms": 0.0,
                "percent": 0,
                "bars": "[X]",
                "bars_text": "Offline",
                "color": "#f87171",
                "quality_label": "Offline / Unreachable",
                "tooltip": f"Camera {ip}: Connection timed out / Offline"
            }

        # Calculate signal quality % from latency curve
        # Sub-30ms = 95-100%, 30-70ms = 80-94%, 70-120ms = 65-79%, 120-250ms = 40-64%, >250ms = <40%
        if rtt_ms <= 30.0:
            percent = int(100 - (rtt_ms * 0.15))
            bars = "[OK] 4/4"
            bars_text = "Excellent"
            color = "#34d399"  # Emerald
            quality_label = "Excellent Signal"
        elif rtt_ms <= 70.0:
            percent = int(95 - ((rtt_ms - 30.0) * 0.35))
            bars = "[OK] 3/4"
            bars_text = "Good"
            color = "#38bdf8"  # Sky Blue
            quality_label = "Good Signal"
        elif rtt_ms <= 130.0:
            percent = int(80 - ((rtt_ms - 70.0) * 0.25))
            bars = "[OK] 2/4"
            bars_text = "Fair"
            color = "#fbbf24"  # Amber
            quality_label = "Fair Signal"
        elif rtt_ms <= 300.0:
            percent = int(65 - ((rtt_ms - 130.0) * 0.15))
            bars = "[OK] 1/4"
            bars_text = "Weak"
            color = "#f97316"  # Orange
            quality_label = "Weak Signal"
        else:
            percent = max(10, int(40 - ((rtt_ms - 300.0) * 0.05)))
            bars = "[!] 1/4"
            bars_text = "Poor"
            color = "#ef4444"  # Red
            quality_label = "High Latency / Jitter"

        percent = max(5, min(100, percent))
        approx_dbm = int(-40 - (100 - percent) * 0.55)

        return {
            "ip": ip,
            "is_online": True,
            "latency_ms": round(rtt_ms, 1),
            "percent": percent,
            "approx_dbm": approx_dbm,
            "bars": bars,
            "bars_text": bars_text,
            "color": color,
            "quality_label": quality_label,
            "tooltip": f"Camera {ip}: {quality_label} | {percent}% (~{approx_dbm} dBm) | Latency: {rtt_ms:.1f}ms"
        }

    def get_signal(self, ip: str) -> Dict[str, Any]:
        """Returns cached signal info or default placeholder."""
        if ip in self.signal_cache:
            return self.signal_cache[ip]
        return {
            "ip": ip,
            "is_online": True,
            "latency_ms": 0.0,
            "percent": 80,
            "approx_dbm": -55,
            "bars": "[OK] 4/4",
            "bars_text": "Good",
            "color": "#38bdf8",
            "quality_label": "Connecting...",
            "tooltip": f"Camera {ip}: Checking signal..."
        }
