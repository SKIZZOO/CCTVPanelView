import subprocess
import os
import sys
import threading
from typing import Optional


class AudioPlayer:
    """
    Ultra-low-latency real-time RTSP audio player.
    Leverages ffplay in headless daemon mode to stream live audio directly
    to Windows audio devices without freezing or blocking the GUI.
    """
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._current_url: Optional[str] = None
        self._volume: int = 100
        self._is_muted: bool = False

    def play(self, rtsp_url: str, volume: int = 100):
        """Starts real-time audio playback for the specified RTSP URL."""
        with self._lock:
            self.stop()
            self._current_url = rtsp_url
            self._volume = max(0, min(100, int(volume)))
            self._is_muted = False

            # Configure Windows hidden startup info
            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW

            cmd = [
                "ffplay",
                "-nodisp",
                "-autoexit",
                "-rtsp_transport", "tcp",
                "-fflags", "nobuffer",
                "-flags", "low_delay",
                "-max_delay", "100000",
                "-volume", str(self._volume),
                "-loglevel", "quiet",
                rtsp_url
            ]

            try:
                self._process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
            except Exception as e:
                print(f"[AudioPlayer] Failed to start audio: {e}")
                self._process = None

    def stop(self):
        """Stops the audio playback process immediately."""
        if self._process:
            try:
                self._process.terminate()
                self._process.kill()
            except Exception:
                pass
            self._process = None
        self._current_url = None

    def is_playing(self) -> bool:
        """Returns True if audio playback is currently running."""
        return self._process is not None and self._process.poll() is None

    def toggle_mute(self) -> bool:
        """Toggles audio mute state. Returns new muted state."""
        if self.is_playing():
            self.stop()
            self._is_muted = True
            return True
        elif self._current_url and self._is_muted:
            self.play(self._current_url, self._volume)
            self._is_muted = False
            return False
        return True
