import os
import sys
import time
import threading

# Zero-overhead thread and math environment to prevent background CPU spin-waiting & latency spikes
os.environ["OMP_WAIT_POLICY"] = "PASSIVE"
os.environ["KMP_BLOCKTIME"] = "0"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
if "OPENCV_FFMPEG_CAPTURE_OPTIONS" not in os.environ:
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
        "rtsp_transport;tcp|"
        "stimeout;5000000|"
        "timeout;5000000|"
        "fflags;nobuffer|"
        "flags;low_delay|"
        "max_delay;0|"
        "buffer_size;102400|"
        "threads;1"
    )

import cv2
from typing import Dict, Any, List, Optional, Union
from enum import Enum

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import ctypes
    import ctypes.wintypes as wt
    HAS_CTYPES_WIN = sys.platform == "win32"
    if HAS_CTYPES_WIN:
        class _NVMLUtilization(ctypes.Structure):
            _fields_ = [('gpu', ctypes.c_uint), ('memory', ctypes.c_uint)]

        class _NVMLMemory(ctypes.Structure):
            _fields_ = [('total', ctypes.c_ulonglong), ('free', ctypes.c_ulonglong), ('used', ctypes.c_ulonglong)]
except ImportError:
    HAS_CTYPES_WIN = False


class PerformanceProfile(str, Enum):
    GAMER = "gamer"     # Gamer Mode (Ryzen 5900X Chiplet 2 / CCD1 Isolated)
    LOW = "low"         # Low Usage (Eco / 2 Cores on Chiplet 2)
    MEDIUM = "medium"   # Medium Usage (Balanced / 4 Cores on Chiplet 2)
    HIGH = "high"       # Full performance
    CUSTOM = "custom"   # Custom Manual Settings


def query_system_cpu_topology() -> Dict[str, Any]:
    """
    Detects CPU model name and L3 cache / chiplet (CCD) architecture.
    Accurately identifies multi-chiplet CPUs such as AMD Ryzen 9 5900X, 5950X, 3900X, 7900X, 7950X.
    """
    cpu_name = "Generic Multi-Core Processor"
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            cpu_name = name.strip()
            winreg.CloseKey(key)
        except Exception:
            pass

    total_logical = os.cpu_count() or 24
    chiplets = []

    # Query Windows Logical Processor Information for L3 caches
    if sys.platform == "win32":
        try:
            k32 = ctypes.windll.kernel32
            RelationCache = 2
            size = wt.DWORD(0)
            k32.GetLogicalProcessorInformationEx(RelationCache, None, ctypes.byref(size))
            if size.value > 0:
                buf = (ctypes.c_ubyte * size.value)()
                if k32.GetLogicalProcessorInformationEx(RelationCache, buf, ctypes.byref(size)):
                    raw = bytes(buf)
                    offset = 0
                    while offset < size.value:
                        entry_size = int.from_bytes(raw[offset+4:offset+8], "little")
                        if entry_size < 8 or offset + entry_size > len(raw):
                            break
                        level = raw[offset+8]
                        cache_size = int.from_bytes(raw[offset+12:offset+16], "little")
                        mask = int.from_bytes(raw[offset+40:offset+48], "little")
                        if level == 3 and mask > 0:
                            cores = [c for c in range(64) if (mask & (1 << c))]
                            chiplets.append({
                                "cache_size_kb": cache_size // 1024,
                                "mask": mask,
                                "cores": cores
                            })
                        offset += entry_size
        except Exception as e:
            print(f"[ResourceManager] Topology detection error: {e}")

    # Fallback if L3 cache enumeration yielded 0
    if not chiplets:
        if "5900" in cpu_name or "5950" in cpu_name or "3900" in cpu_name or "3950" in cpu_name or total_logical == 24:
            half = total_logical // 2
            chiplets = [
                {"cache_size_kb": 32768, "mask": (1 << half) - 1, "cores": list(range(0, half))},
                {"cache_size_kb": 32768, "mask": ((1 << half) - 1) << half, "cores": list(range(half, total_logical))}
            ]
        else:
            chiplets = [
                {"cache_size_kb": 32768, "mask": (1 << total_logical) - 1, "cores": list(range(total_logical))}
            ]

    has_dual_chiplets = len(chiplets) >= 2
    chiplet1 = chiplets[0]["cores"] if len(chiplets) >= 1 else list(range(min(12, total_logical)))
    chiplet2 = chiplets[1]["cores"] if len(chiplets) >= 2 else list(range(min(12, total_logical), total_logical))

    return {
        "cpu_name": cpu_name,
        "is_ryzen_dual_ccd": has_dual_chiplets,
        "chiplet_count": len(chiplets),
        "chiplet1_cores": chiplet1,
        "chiplet2_cores": chiplet2,
        "total_cores": total_logical
    }


# Default profile settings
PROFILE_DEFAULTS = {
    PerformanceProfile.GAMER: {
        "label": "Background / gaming",
        "description": "Limits background processing and uses the secondary CPU chiplet when available. Performance depends on camera streams and hardware.",
        "affinity_target": "chiplet2_balanced",
        "priority": "below_normal",
        "display_fps_cap": 25,
        "grid_substream": True,
        "ai_skip_frames": 6,
        "ai_motion_gated_only": False,
        "motion_skip_frames": 1,
        "motion_downscale_width": 480,
        "opencv_threads": 4
    },
    PerformanceProfile.LOW: {
        "label": "Low resource use",
        "description": "Lower display frame rate and reduced detection work to conserve CPU. Uses substreams where configured.",
        "affinity_target": "chiplet2_eco",
        "priority": "below_normal",
        "display_fps_cap": 10,
        "grid_substream": True,
        "ai_skip_frames": 10,
        "ai_motion_gated_only": False,
        "motion_skip_frames": 2,
        "motion_downscale_width": 320,
        "opencv_threads": 2
    },
    PerformanceProfile.MEDIUM: {
        "label": "Balanced",
        "description": "4 Cores on Chiplet 2 (Cores 12-15) | 15 FPS | Mid-HD Grid | Responsive AI. Balances surveillance and gaming.",
        "affinity_target": "chiplet2_balanced",
        "priority": "normal",
        "display_fps_cap": 15,
        "grid_substream": True,
        "ai_skip_frames": 6,
        "ai_motion_gated_only": False,
        "motion_skip_frames": 1,
        "motion_downscale_width": 480,
        "opencv_threads": 4
    },
    PerformanceProfile.HIGH: {
        "label": "Full performance",
        "description": "All 24 Cores across both Chiplets | Native 2K | Uncapped FPS | Continuous AI. Full hardware potential, maximum surveillance fidelity.",
        "affinity_target": "all",
        "priority": "normal",
        "display_fps_cap": 0,
        "grid_substream": False,
        "ai_skip_frames": 3,
        "ai_motion_gated_only": False,
        "motion_skip_frames": 0,
        "motion_downscale_width": 640,
        "opencv_threads": 0
    }
}


class ResourceManager:
    """
    Central controller for CPU affinity, multi-chiplet Ryzen topology,
    thread allocation, process priority, frame rendering throttling,
    and live CPU performance monitoring.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.topology = query_system_cpu_topology()
        self.total_cores = self.topology["total_cores"]
        self.cpu_name = self.topology["cpu_name"]
        self.is_ryzen_dual_ccd = self.topology["is_ryzen_dual_ccd"]
        self.chiplet1_cores = self.topology["chiplet1_cores"]
        self.chiplet2_cores = self.topology["chiplet2_cores"]

        # Default profile is Gamer / Chiplet 2 on Ryzen 5900X!
        self.current_profile = PerformanceProfile.GAMER if self.is_ryzen_dual_ccd else PerformanceProfile.MEDIUM
        self.effective_settings = dict(PROFILE_DEFAULTS.get(self.current_profile, PROFILE_DEFAULTS[PerformanceProfile.MEDIUM]))
        self.active_affinity = list(range(self.total_cores))

        # Initialize process handle
        self._psutil_proc = None
        if HAS_PSUTIL:
            try:
                self._psutil_proc = psutil.Process()
                self._psutil_proc.cpu_percent(interval=None) # Baseline
            except Exception as e:
                print(f"[ResourceManager] psutil init error: {e}")

        # Base CPU clock frequency for accurate cycle-based CPU measurement
        self._base_clock_hz: float = 3.7e9
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                mhz, _ = winreg.QueryValueEx(key, "~MHz")
                winreg.CloseKey(key)
                if mhz and mhz > 500:
                    self._base_clock_hz = float(mhz) * 1e6
            except Exception:
                pass

        # Real-time cycle tracking state
        self._last_cycles: int = 0
        self._last_cycle_time: float = 0.0
        self._proc_cpu_percent: float = 0.0
        self._proc_core_equiv: float = 0.0
        self._child_cpu_percent: float = 0.0
        self._last_children_cycles: Dict[int, int] = {}
        self._cpu_samples = {}
        self._cpu_sample_lock = threading.Lock()

        # Windows Kernel32 ctypes setup
        self._k32 = None
        if HAS_CTYPES_WIN:
            try:
                self._k32 = ctypes.windll.kernel32
                self._k32.GetCurrentProcess.restype = ctypes.c_void_p
                self._k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
                self._k32.SetProcessAffinityMask.restype = wt.BOOL
                self._k32.QueryProcessCycleTime.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
                self._k32.QueryProcessCycleTime.restype = ctypes.c_bool
                self._k32.OpenProcess.restype = ctypes.c_void_p

                c = ctypes.c_uint64(0)
                if self._k32.QueryProcessCycleTime(self._k32.GetCurrentProcess(), ctypes.byref(c)):
                    self._last_cycles = c.value
                    self._last_cycle_time = time.perf_counter()
            except Exception as e:
                print(f"[ResourceManager] ctypes init error: {e}")

        # Live GPU telemetry setup via direct NVML ctypes
        self._nvml_dll = None
        self._nvml_device = None
        self._gpu_name = None
        if HAS_CTYPES_WIN:
            try:
                self._nvml_dll = ctypes.CDLL("nvml.dll")
                if self._nvml_dll.nvmlInit_v2() == 0:
                    dev = ctypes.c_void_p()
                    if self._nvml_dll.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev)) == 0:
                        self._nvml_device = dev
                        buf = ctypes.create_string_buffer(64)
                        if self._nvml_dll.nvmlDeviceGetName(dev, buf, 64) == 0:
                            self._gpu_name = buf.value.decode("utf-8")
            except Exception:
                self._nvml_dll = None
                self._nvml_device = None

    def get_system_core_count(self) -> int:
        return self.total_cores

    def apply_profile(self, profile: str, custom_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Applies a performance profile: 'gamer', 'low', 'medium', 'high', or 'custom'.
        Configures CPU affinity, process priority, OpenCV threads, and returns effective settings.
        """
        profile = {"balanced": "medium", "performance": "gamer", "eco": "low", "extreme": "high"}.get(profile, profile)
        try:
            perf_profile = PerformanceProfile(profile)
        except ValueError:
            perf_profile = PerformanceProfile.GAMER if self.is_ryzen_dual_ccd else PerformanceProfile.MEDIUM

        self.current_profile = perf_profile

        if perf_profile in PROFILE_DEFAULTS:
            settings = dict(PROFILE_DEFAULTS[perf_profile])
        else:
            settings = dict(PROFILE_DEFAULTS[PerformanceProfile.MEDIUM])

        if custom_settings:
            settings.update(custom_settings)

        self.effective_settings = settings

        # 1. Apply CPU Affinity
        affinity_target = settings.get("affinity_target") or settings.get("cpu_affinity_cores")
        if affinity_target is None:
            affinity_target = "chiplet2_balanced" if self.is_ryzen_dual_ccd else 4

        self.set_cpu_affinity(affinity_target)

        # 2. Apply Process Priority
        priority_val = settings.get("priority", "below_normal" if perf_profile == PerformanceProfile.GAMER else "normal")
        self.set_process_priority(priority_val)

        # 3. Apply OpenCV Thread Count
        cv_threads = settings.get("opencv_threads", 4)
        self.set_opencv_threads(cv_threads)

        return self.effective_settings

    def set_cpu_affinity(self, target: Union[int, str, List[int]]) -> bool:
        """
        Pins CAM720 process execution to target CPU cores.
        Supports:
        - List of core IDs: e.g. [12, 13, 14, 15] (Chiplet 2)
        - Named string presets:
          * 'chiplet2', 'chiplet2_balanced': 4 cores on Chiplet 2 [12, 13, 14, 15]
          * 'chiplet2_eco': 2 cores on Chiplet 2 [12, 13]
          * 'chiplet2_full': all 12 threads on Chiplet 2 [12..23]
          * 'chiplet1', 'chiplet1_full': Chiplet 1 [0..11] (Gaming Chiplet)
          * 'all': all cores [0..23]
        - Integer core count:
          * If on dual-chiplet Ryzen: automatically pins to that number of cores on Chiplet 2!
          * e.g. 2 -> [12, 13], 4 -> [12, 13, 14, 15]
          * -1 or >= total_cores -> all cores
        """
        target_cores = []

        if isinstance(target, list):
            target_cores = [int(c) for c in target if 0 <= int(c) < self.total_cores]
        elif isinstance(target, str):
            t_lower = target.lower().strip()
            if t_lower in ["chiplet2", "chiplet2_balanced", "gamer"]:
                target_cores = self.chiplet2_cores[:4] if self.chiplet2_cores else list(range(4))
            elif t_lower in ["chiplet2_eco", "eco"]:
                target_cores = self.chiplet2_cores[:2] if self.chiplet2_cores else list(range(2))
            elif t_lower in ["chiplet2_full", "ccd1", "ccd2"]:
                target_cores = list(self.chiplet2_cores) if self.chiplet2_cores else list(range(self.total_cores))
            elif t_lower in ["chiplet1", "chiplet1_full", "ccd0"]:
                target_cores = list(self.chiplet1_cores) if self.chiplet1_cores else list(range(self.total_cores))
            elif t_lower in ["all", "uncapped", "-1"]:
                target_cores = list(range(self.total_cores))
            else:
                # Try parsing numeric string
                try:
                    num = int(target)
                    return self.set_cpu_affinity(num)
                except ValueError:
                    target_cores = self.chiplet2_cores[:4] if self.is_ryzen_dual_ccd else list(range(4))
        elif isinstance(target, int):
            if target <= 0 or target >= self.total_cores:
                target_cores = list(range(self.total_cores))
            else:
                # On Ryzen dual-CCD, place requested core count on Chiplet 2 to protect gaming!
                if self.is_ryzen_dual_ccd and len(self.chiplet2_cores) >= target:
                    target_cores = self.chiplet2_cores[:target]
                else:
                    target_cores = list(range(min(target, self.total_cores)))

        if not target_cores:
            target_cores = list(range(self.total_cores))

        self.active_affinity = target_cores
        success = False

        # Attempt via psutil
        if self._psutil_proc is not None:
            try:
                self._psutil_proc.cpu_affinity(target_cores)
                success = True
            except Exception as e:
                print(f"[ResourceManager] psutil.cpu_affinity error: {e}")

        # Fallback via Windows Win32 API
        if not success and self._k32 is not None:
            try:
                mask = sum(1 << c for c in target_cores)
                h_proc = self._k32.GetCurrentProcess()
                res = self._k32.SetProcessAffinityMask(h_proc, ctypes.c_size_t(mask))
                success = bool(res)
            except Exception as e:
                print(f"[ResourceManager] Win32 SetProcessAffinityMask error: {e}")

        return success

    def is_chiplet2_isolated(self) -> bool:
        """Returns True if process execution is strictly contained within Chiplet 2 (CCD1)."""
        if not self.is_ryzen_dual_ccd or not self.chiplet1_cores:
            return False
        # Isolated if no cores from Chiplet 1 are in active affinity
        return not any(c in self.chiplet1_cores for c in self.active_affinity)

    def get_affinity_label(self) -> str:
        """Returns a user-friendly label for current core affinity."""
        if len(self.active_affinity) >= self.total_cores:
            return f"All {self.total_cores} Cores"
        
        if self.is_ryzen_dual_ccd:
            if self.is_chiplet2_isolated():
                count = len(self.active_affinity)
                first = min(self.active_affinity)
                last = max(self.active_affinity)
                return f"Chiplet 2: {count} Cores ({first}-{last})"
            elif all(c in self.chiplet1_cores for c in self.active_affinity):
                count = len(self.active_affinity)
                return f"Chiplet 1: {count} Cores"

        return f"{len(self.active_affinity)} Cores"

    def set_process_priority(self, priority_name: str) -> bool:
        """
        Configures Windows process scheduling priority:
        'low' (idle), 'below_normal', 'normal', 'above_normal'.
        """
        if self._psutil_proc is None:
            return False

        priority_name = str(priority_name).lower().strip()
        try:
            if sys.platform == "win32":
                p_map = {
                    "idle": psutil.IDLE_PRIORITY_CLASS,
                    "low": psutil.IDLE_PRIORITY_CLASS,
                    "below_normal": psutil.BELOW_NORMAL_PRIORITY_CLASS,
                    "normal": psutil.NORMAL_PRIORITY_CLASS,
                    "above_normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS
                }
                target_p = p_map.get(priority_name, psutil.NORMAL_PRIORITY_CLASS)
                self._psutil_proc.nice(target_p)

                # Set process I/O priority so disk/socket traffic doesn't stall games/apps
                if hasattr(self._psutil_proc, "ionice"):
                    try:
                        if priority_name in ["idle", "low", "below_normal"]:
                            self._psutil_proc.ionice(psutil.IOPRIO_LOW)
                        else:
                            self._psutil_proc.ionice(psutil.IOPRIO_NORMAL)
                    except Exception:
                        pass

                return True
            else:
                unix_map = {"idle": 19, "low": 10, "below_normal": 5, "normal": 0, "above_normal": -5}
                self._psutil_proc.nice(unix_map.get(priority_name, 0))
                return True
        except Exception as e:
            print(f"[ResourceManager] Failed to set process priority: {e}")
            return False

    @staticmethod
    def set_current_thread_low_priority():
        """Sets the calling background thread to below-normal scheduling priority on Windows."""
        if sys.platform == "win32":
            try:
                k32 = ctypes.windll.kernel32
                k32.SetThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
                k32.SetThreadPriority.restype = ctypes.c_bool
                k32.SetThreadPriority(k32.GetCurrentThread(), -1)
            except Exception:
                pass

    def set_opencv_threads(self, thread_count: int):
        """Controls internal thread pool size for OpenCV matrix & computer vision operations."""
        try:
            if thread_count <= 0:
                cv2.setNumThreads(0)
            else:
                cv2.setNumThreads(max(1, int(thread_count)))
        except Exception as e:
            print(f"[ResourceManager] cv2.setNumThreads error: {e}")

    def get_process_cpu_percent(self) -> float:
        """
        Returns the mathematically accurate CPU usage percentage of CCTVPanelView (0.0 to 100.0% of system).
        Uses Windows kernel process times (psutil) normalized across total logical cores.
        Also tracks single-core equivalent and helper child processes (FFmpeg / FFplay).
        Guarantees that App Footprint <= Total Windows System CPU at all times.
        """
        if self._psutil_proc is None:
            return 0.0

        with self._cpu_sample_lock:
            now = time.monotonic()
            samples = {}
            parent_core = child_core = 0.0
            try:
                processes = [self._psutil_proc] + self._psutil_proc.children(recursive=True)
            except Exception:
                processes = [self._psutil_proc]
            for process in processes:
                try:
                    key = (process.pid, process.create_time())
                    cpu = process.cpu_times()
                    used = float(cpu.user + cpu.system)
                    previous = self._cpu_samples.get(key)
                    samples[key] = (used, now)
                    percent = 0.0
                    if previous and now > previous[1]:
                        percent = max(0.0, (used - previous[0]) / (now - previous[1]) * 100)
                    if process.pid == self._psutil_proc.pid:
                        parent_core = percent
                    else:
                        child_core += percent
                except Exception:
                    continue
            self._cpu_samples = samples
            cores = max(1, self.total_cores)
            self._proc_core_equiv = round(parent_core + child_core, 1)
            self._child_cpu_percent = round(child_core / cores, 1)
            self._proc_cpu_percent = round(min(100.0, (parent_core + child_core) / cores), 1)
            try:
                self._last_sys_cpu = max(float(psutil.cpu_percent(interval=None)), self._proc_cpu_percent)
            except Exception:
                self._last_sys_cpu = self._proc_cpu_percent
            return self._proc_cpu_percent

    def get_process_core_equivalent(self) -> float:
        """Returns the equivalent CPU percentage of a single physical core (0 to 100% * cores)."""
        return getattr(self, "_proc_core_equiv", 0.0)

    def get_child_cpu_percent(self) -> float:
        """Returns CPU percentage of spawned helper processes (FFmpeg, FFplay)."""
        return getattr(self, "_child_cpu_percent", 0.0)

    def get_system_cpu_percent(self) -> float:
        """Returns the overall system-wide CPU usage percentage, guaranteed >= process usage."""
        return round(getattr(self, "_last_sys_cpu", 0.0), 1)

    def get_memory_usage_mb(self) -> float:
        """Returns process memory footprint in megabytes (MB)."""
        if self._psutil_proc is not None:
            try:
                mem = self._psutil_proc.memory_info()
                return float(mem.rss / (1024 * 1024))
            except Exception:
                return 0.0
        return 0.0

    def get_hardware_telemetry_snapshot(self, storage_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Gathers live, comprehensive hardware metrics across:
        - CPU: Total System %, App Footprint %, Core Equivalent, Model name, Priority, Affinity
        - RAM: Total System Used/Total GB and %, App Footprint in MB (including helper processes)
        - GPU: Model name, 3D Engine Load %, Dedicated VRAM Used/Total MB and %
        - Storage: Free GB, Total GB, Used % for the active app / recordings drive
        """
        # 1. CPU Telemetry
        app_cpu = self.get_process_cpu_percent()
        sys_cpu = self.get_system_cpu_percent()
        core_equiv = self.get_process_core_equivalent()
        child_cpu = self.get_child_cpu_percent()
        other_sys = max(0.0, round(sys_cpu - app_cpu, 1))

        # 2. RAM Telemetry
        ram_sys_used_gb = 0.0
        ram_sys_total_gb = 0.0
        ram_sys_pct = 0.0
        app_ram_mb = 0.0
        app_ram_pct = 0.0
        if HAS_PSUTIL:
            try:
                vm = psutil.virtual_memory()
                ram_sys_used_gb = vm.used / (1024**3)
                ram_sys_total_gb = vm.total / (1024**3)
                ram_sys_pct = vm.percent

                if self._psutil_proc is not None:
                    app_bytes = self._psutil_proc.memory_info().rss
                    try:
                        for child in self._psutil_proc.children(recursive=True):
                            try:
                                app_bytes += child.memory_info().rss
                            except Exception:
                                pass
                    except Exception:
                        pass
                    app_ram_mb = app_bytes / (1024**2)
                    if vm.total > 0:
                        app_ram_pct = (app_bytes / vm.total) * 100.0
            except Exception:
                pass

        # 3. GPU Telemetry (Direct NVML via ctypes)
        gpu_name = self._gpu_name or "N/A"
        gpu_available = False
        gpu_util_pct = 0.0
        vram_used_mb = 0.0
        vram_total_mb = 0.0
        vram_pct = 0.0
        if getattr(self, "_nvml_dll", None) is not None and getattr(self, "_nvml_device", None) is not None:
            try:
                util = _NVMLUtilization()
                if self._nvml_dll.nvmlDeviceGetUtilizationRates(self._nvml_device, ctypes.byref(util)) == 0:
                    gpu_util_pct = float(util.gpu)
                    gpu_available = True

                mem = _NVMLMemory()
                if self._nvml_dll.nvmlDeviceGetMemoryInfo(self._nvml_device, ctypes.byref(mem)) == 0:
                    vram_used_mb = float(mem.used) / (1024**2)
                    vram_total_mb = float(mem.total) / (1024**2)
                    if vram_total_mb > 0:
                        vram_pct = (vram_used_mb / vram_total_mb) * 100.0
                    gpu_available = True
            except Exception:
                pass

        # 4. Storage Telemetry
        drive_target = storage_path or os.path.abspath(".")
        drive_letter = os.path.splitdrive(drive_target)[0] or "C:"
        storage_free_gb = 0.0
        storage_total_gb = 0.0
        storage_used_pct = 0.0
        if HAS_PSUTIL:
            try:
                disk = psutil.disk_usage(drive_letter + "\\")
                storage_free_gb = disk.free / (1024**3)
                storage_total_gb = disk.total / (1024**3)
                storage_used_pct = disk.percent
            except Exception:
                pass

        return {
            "cpu": {
                "model": self.cpu_name,
                "total_cores": self.total_cores,
                "sys_pct": sys_cpu,
                "app_pct": app_cpu,
                "child_pct": child_cpu,
                "core_equiv_pct": core_equiv,
                "other_pct": other_sys,
                "affinity_label": self.get_affinity_label(),
                "is_chiplet2_isolated": self.is_chiplet2_isolated(),
            },
            "ram": {
                "sys_used_gb": round(ram_sys_used_gb, 1),
                "sys_total_gb": round(ram_sys_total_gb, 1),
                "sys_pct": round(ram_sys_pct, 1),
                "app_mb": round(app_ram_mb, 1),
                "app_sys_pct": round(app_ram_pct, 1),
            },
            "gpu": {
                "name": gpu_name,
                "available": gpu_available,
                "util_pct": round(gpu_util_pct, 0),
                "vram_used_mb": round(vram_used_mb, 0),
                "vram_total_mb": round(vram_total_mb, 0),
                "vram_pct": round(vram_pct, 1),
            },
            "storage": {
                "drive": drive_letter,
                "free_gb": round(storage_free_gb, 1),
                "total_gb": round(storage_total_gb, 1),
                "used_pct": round(storage_used_pct, 1),
            }
        }


    def trim_memory(self):
        """Trims unreferenced heap memory and flushes process working set pages back to Windows kernel."""
        trim_process_memory()


def trim_process_memory():
    """Performs garbage collection and flushes unused working set pages to Windows OS."""
    try:
        import gc
        gc.collect()
        if sys.platform == "win32":
            import ctypes
            h_proc = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.psapi.EmptyWorkingSet(h_proc)
    except Exception:
        pass


# Global singleton instance helper
_resource_manager_singleton: Optional[ResourceManager] = None

def get_resource_manager() -> ResourceManager:
    global _resource_manager_singleton
    if _resource_manager_singleton is None:
        _resource_manager_singleton = ResourceManager()
    return _resource_manager_singleton
