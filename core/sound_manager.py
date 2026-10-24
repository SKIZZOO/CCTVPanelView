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
        os.makedirs(self.sounds_dir, exist_ok=True)
        self.sample_rate = 44100
        self._lock = threading.Lock()
        self._ensure_default_sounds()

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

    def get_sound_file_path(self, profile_name: str, custom_path: Optional[str] = None) -> Optional[str]:
        if profile_name == SoundProfile.CUSTOM and custom_path and os.path.isfile(custom_path):
            return custom_path

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
        return None

    def play_sound(self, profile_name: str = SoundProfile.CYBER_CHIME, volume: int = 100, custom_path: Optional[str] = None):
        """
        Plays the selected sound profile asynchronously in a separate thread.
        """
        if not HAS_WINSOUND or volume <= 0:
            return

        def _do_play():
            with self._lock:
                try:
                    wav_path = self.get_sound_file_path(profile_name, custom_path)
                    if wav_path and os.path.isfile(wav_path):
                        # Play WAV file asynchronously
                        winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    else:
                        # Fallback synthesized tone
                        winsound.Beep(1800, 180)
                except Exception as e:
                    # Final safety fallback
                    try:
                        winsound.Beep(1500, 100)
                    except Exception:
                        pass

        threading.Thread(target=_do_play, daemon=True).start()

    def play_test_tone(self, profile_name: str = SoundProfile.CYBER_CHIME, volume: int = 100, custom_path: Optional[str] = None):
        """Plays test tone for settings preview."""
        self.play_sound(profile_name=profile_name, volume=volume, custom_path=custom_path)

    def play_motion_pip(self, volume: int = 60):
        """Quick subtle pip on motion trigger."""
        if not HAS_WINSOUND or volume <= 0:
            return
        def _pip():
            try:
                winsound.Beep(1200, 50)
            except Exception:
                pass
        threading.Thread(target=_pip, daemon=True).start()

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
