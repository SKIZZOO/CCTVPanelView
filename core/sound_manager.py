"""
Sound Manager for Cam720 Revamped.
Provides synthesized alert sound profiles (Cyber Chime, Tactical Radar, Sonar Ping,
High-Pitch Siren, Discreet Beep, Sci-Fi Pulse) and custom WAV playback with
volume scaling and live audio preview.
"""

import os
import wave
import struct
import math
import threading
import io
import sys
import queue
import numpy as np
from typing import List, Optional

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


class SoundProfile:
    CYBER_CHIME = "Cyber Chime"
    TACTICAL_RADAR = "Tactical Radar"
    SONAR_PING = "Sonar Ping"
    SIREN = "High-Pitch Siren"
    DISCREET_BEEP = "Discreet Beep"
    SCIFI_PULSE = "Sci-Fi Pulse"
    CUSTOM = "Custom WAV File"

    ALL = [
        CYBER_CHIME,
        TACTICAL_RADAR,
        SONAR_PING,
        SIREN,
        DISCREET_BEEP,
        SCIFI_PULSE,
        CUSTOM
    ]


class SoundManager:
    """
    Manages sound generation, caching, and playback for alarms, motion detection,
    and UI feedback.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SoundManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, sounds_dir: str = "sounds"):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.sounds_dir = os.path.abspath(sounds_dir)
        self.sample_rate = 44100
        self._lock = threading.Lock()
        self._requests = queue.Queue(maxsize=1)
        self._playback_thread = None
        self.last_error = ""

    def get_available_profiles(self) -> List[str]:
        return list(SoundProfile.ALL)

    def _ensure_default_sounds(self):
        """Generates studio-quality 16-bit PCM WAV assets on first run."""
        profile_generators = {
            SoundProfile.CYBER_CHIME: ("cyber_chime.wav", self._synth_cyber_chime),
            SoundProfile.TACTICAL_RADAR: ("tactical_radar.wav", self._synth_tactical_radar),
            SoundProfile.SONAR_PING: ("sonar_ping.wav", self._synth_sonar_ping),
            SoundProfile.SIREN: ("high_pitch_siren.wav", self._synth_siren),
            SoundProfile.DISCREET_BEEP: ("discreet_beep.wav", self._synth_discreet_beep),
            SoundProfile.SCIFI_PULSE: ("scifi_pulse.wav", self._synth_scifi_pulse),
        }

        for profile, (fname, generator) in profile_generators.items():
            path = os.path.join(self.sounds_dir, fname)
            if not os.path.exists(path) or os.path.getsize(path) < 1000:
                try:
                    samples = generator()
                    self._write_wav(path, samples)
                except Exception as e:
                    print(f"Error generating sound {profile}: {e}")

    def _write_wav(self, path: str, samples: List[float], volume: float = 1.0):
        with wave.open(path, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            packed = bytearray()
            vol = max(0.0, min(1.0, volume))
            for s in samples:
                val = int(max(-1.0, min(1.0, s * vol)) * 32767)
                packed.extend(struct.pack('<h', val))
            wav.writeframes(packed)

    # --- Synthesizers ---
    def _synth_cyber_chime(self) -> List[float]:
        dur = 0.65
        n = int(self.sample_rate * dur)
        samples = []
        for i in range(n):
            t = i / self.sample_rate
            env = math.exp(-5.5 * t)
            # Harmonic chime: 880Hz + 1320Hz + 1760Hz
            s = (0.5 * math.sin(2 * math.pi * 880 * t) +
                 0.35 * math.sin(2 * math.pi * 1320 * t) +
                 0.15 * math.sin(2 * math.pi * 1760 * t)) * env
            samples.append(s)
        return samples

    def _synth_tactical_radar(self) -> List[float]:
        dur = 0.5
        n = int(self.sample_rate * dur)
        samples = []
        for i in range(n):
            t = i / self.sample_rate
            env = math.exp(-4.0 * t)
            # Chirp sweep from 700Hz to 1900Hz
            freq = 700 + 2400 * (t ** 1.3)
            phase = 2 * math.pi * (700 * t + 1200 * (t ** 2.3) / 2.3)
            s = math.sin(phase) * env
            samples.append(s)
        return samples

    def _synth_sonar_ping(self) -> List[float]:
        dur = 0.75
        n = int(self.sample_rate * dur)
        samples = []
        freq = 940.0
        for i in range(n):
            t = i / self.sample_rate
            # Sharp attack, ringing resonance decay
            attack = min(1.0, t / 0.005)
            env = attack * math.exp(-4.2 * t)
            s = (0.8 * math.sin(2 * math.pi * freq * t) +
                 0.2 * math.sin(2 * math.pi * freq * 2.0 * t)) * env
            samples.append(s)
        return samples

    def _synth_siren(self) -> List[float]:
        dur = 0.6
        n = int(self.sample_rate * dur)
        samples = []
        for i in range(n):
            t = i / self.sample_rate
            # Rapid alternating two-tone: 1600Hz and 2200Hz
            freq = 1600.0 if (int(t * 8) % 2 == 0) else 2200.0
            phase = 2 * math.pi * freq * t
            s = 0.85 * (1.0 if math.sin(phase) > 0 else -1.0)  # slightly sharp square-ish tone
            samples.append(s * 0.7)
        return samples

    def _synth_discreet_beep(self) -> List[float]:
        dur = 0.25
        n = int(self.sample_rate * dur)
        samples = []
        # Two short 40ms pips separated by 30ms silence
        pip1_end = 0.045
        gap_end = 0.075
        pip2_end = 0.120
        freq = 1200.0
        for i in range(n):
            t = i / self.sample_rate
            if t < pip1_end:
                t_pip = t / pip1_end
                env = math.sin(math.pi * t_pip)
                s = math.sin(2 * math.pi * freq * t) * env
            elif t < gap_end:
                s = 0.0
            elif t < pip2_end:
                t_pip = (t - gap_end) / (pip2_end - gap_end)
                env = math.sin(math.pi * t_pip)
                s = math.sin(2 * math.pi * (freq * 1.25) * t) * env
            else:
                s = 0.0
            samples.append(s * 0.7)
        return samples

    def _synth_scifi_pulse(self) -> List[float]:
        dur = 0.55
        n = int(self.sample_rate * dur)
        samples = []
        for i in range(n):
            t = i / self.sample_rate
            mod = 1.0 + 0.3 * math.sin(2 * math.pi * 12.0 * t)
            freq = (600.0 + 900.0 * (t / dur)) * mod
            phase = 2 * math.pi * freq * t
            env = math.exp(-3.5 * t)
            s = (0.7 * math.sin(phase) + 0.3 * math.sin(2.0 * phase)) * env
            samples.append(s)
        return samples

    @staticmethod
    def normalize_profile(name):
        return {"classic_beep": SoundProfile.DISCREET_BEEP,
                "tactical_siren": SoundProfile.SIREN, "modern_chime": SoundProfile.CYBER_CHIME,
                "military_laser": SoundProfile.TACTICAL_RADAR, "cyber_chime": SoundProfile.CYBER_CHIME}.get(name, name)

    @staticmethod
    def volume_from_settings(settings):
        if "sound_volume" in settings:
            return max(0, min(100, int(settings["sound_volume"])))
        old = float(settings.get("alert_volume", .8))
        return max(0, min(100, round(old * 100 if old <= 1 else old)))

    @staticmethod
    def scaled_wav(path, volume):
        with wave.open(path, "rb") as source:
            channels, width, rate, count, compression, _ = source.getparams()
            if compression != "NONE" or width not in (1, 2, 3, 4):
                raise ValueError("Choose an uncompressed PCM WAV file")
            raw = source.readframes(count)
        gain = max(0, min(100, float(volume))) / 100
        if width == 3:
            triples = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32)
            values = triples[:, 0] | (triples[:, 1] << 8) | (triples[:, 2] << 16)
            values = (values ^ 0x800000) - 0x800000
            scaled = np.rint(values * gain).astype(np.int32)
            data = np.column_stack((scaled & 255, (scaled >> 8) & 255, (scaled >> 16) & 255)).astype(np.uint8).tobytes()
        else:
            dtype = {1: np.uint8, 2: np.dtype("<i2"), 4: np.dtype("<i4")}[width]
            values = np.frombuffer(raw, dtype).astype(np.float64)
            offset = 128 if width == 1 else 0
            data = np.rint((values - offset) * gain + offset).astype(dtype).tobytes()
        output = io.BytesIO()
        with wave.open(output, "wb") as target:
            target.setnchannels(channels); target.setsampwidth(width); target.setframerate(rate)
            target.writeframes(data)
        return output.getvalue()

    def get_sound_file_path(self, profile_name: str, custom_path: Optional[str] = None) -> Optional[str]:
        profile_name = self.normalize_profile(profile_name)
        if profile_name == SoundProfile.CUSTOM:
            return custom_path if custom_path and os.path.isfile(custom_path) else None

        file_map = {
            SoundProfile.CYBER_CHIME: "cyber_chime.wav",
            SoundProfile.TACTICAL_RADAR: "tactical_radar.wav",
            SoundProfile.SONAR_PING: "sonar_ping.wav",
            SoundProfile.SIREN: "high_pitch_siren.wav",
            SoundProfile.DISCREET_BEEP: "discreet_beep.wav",
            SoundProfile.SCIFI_PULSE: "scifi_pulse.wav",
        }
        fname = file_map.get(profile_name, "cyber_chime.wav")
        path = os.path.join(self.sounds_dir, fname)
        if os.path.isfile(path):
            return path
        bundled = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__))), "sounds", fname)
        if os.path.isfile(bundled):
            return bundled
        os.makedirs(self.sounds_dir, exist_ok=True)
        self._ensure_default_sounds()
        return path if os.path.isfile(path) else None

    def play_sound(self, profile_name: str = SoundProfile.CYBER_CHIME, volume: int = 100, custom_path: Optional[str] = None):
        if not HAS_WINSOUND:
            self.last_error = "Windows sound playback is unavailable"
            return
        if volume <= 0:
            self.stop()
            return
        request = (profile_name, max(0, min(100, volume)), custom_path)
        with self._lock:
            try:
                self._requests.get_nowait()
            except queue.Empty:
                pass
            self._requests.put_nowait(request)
            if self._playback_thread is None or not self._playback_thread.is_alive():
                self._playback_thread = threading.Thread(target=self._play_pending, daemon=True)
                self._playback_thread.start()

    def _play_pending(self):
        while True:
            with self._lock:
                try:
                    profile, volume, custom = self._requests.get_nowait()
                except queue.Empty:
                    self._playback_thread = None
                    return
            try:
                path = self.get_sound_file_path(profile, custom)
                if not path:
                    raise ValueError("Sound file not found")
                data = self.scaled_wav(path, volume)
                # Windows does not support asynchronous SND_MEMORY. This bounded
                # background worker owns the buffer until synchronous playback ends.
                winsound.PlaySound(data, winsound.SND_MEMORY | winsound.SND_NODEFAULT)
                self.last_error = ""
            except Exception as error:
                self.last_error = str(error)

    def stop(self):
        with self._lock:
            try:
                self._requests.get_nowait()
            except queue.Empty:
                pass
        if HAS_WINSOUND:
            winsound.PlaySound(None, 0)

    def play_test_tone(self, profile_name: str = SoundProfile.CYBER_CHIME, volume: int = 100, custom_path: Optional[str] = None):
        """Plays test tone for settings preview."""
        self.play_sound(profile_name=profile_name, volume=volume, custom_path=custom_path)

    def play_motion_pip(self, volume: int = 60):
        self.play_sound(SoundProfile.DISCREET_BEEP, volume=volume)

    def test_sound(self, profile_name: str, volume: int = 100, custom_path: Optional[str] = None):
        """Live test for the settings dialog."""
        self.play_sound(profile_name, volume=volume, custom_path=custom_path)


# Global singleton instance helper
_sound_manager_instance = None

def get_sound_manager() -> SoundManager:
    global _sound_manager_instance
    if _sound_manager_instance is None:
        _sound_manager_instance = SoundManager()
    return _sound_manager_instance
