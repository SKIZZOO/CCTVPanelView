"""Upgrade profile preservation, shared by the app and graphical installer."""
import json
import os
from pathlib import Path
import shutil
import tempfile
from datetime import datetime, timezone

CONFIG_NAME = "cameras_config.json"


def registered_install_dir():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\CCTVPanelView") as key:
            value = winreg.QueryValueEx(key, "InstallLocation")[0]
        path = Path(value)
        if path.is_absolute() and (path / "CCTVPanelView.exe").is_file():
            return str(path)
    except (ImportError, OSError, TypeError, ValueError):
        pass
    return None


def read_profile(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cameras"), list) or not isinstance(data.get("app_settings", {}), dict):
        raise ValueError("Existing camera configuration is invalid; restore its backup before updating.")
    return data


def backup_profile(path):
    path = Path(path)
    read_profile(path)  # Do not label corrupt input as a verified backup.
    folder = path.parent / "config-backups"
    folder.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-")
    fd, name = tempfile.mkstemp(prefix=stamp, suffix=".json", dir=folder)
    with os.fdopen(fd, "wb") as target:
        target.write(path.read_bytes()); target.flush(); os.fsync(target.fileno())
    return str(name)


def preserve_upgrade_profile(target_dir, previous_dir=None):
    """Back up existing config without rewriting it, or migrate when relocating."""
    target = Path(target_dir).resolve()
    destination = target / CONFIG_NAME
    if destination.exists():
        backup_profile(destination)
        return True
    if not previous_dir:
        return False
    previous = Path(previous_dir).resolve()
    source = previous / CONFIG_NAME
    if previous == target or not source.is_file():
        return False
    data = read_profile(source)
    backup_profile(source)
    # Existing media stays in place. Relative paths must keep referring to its
    # original location when the executable is installed in a different folder.
    settings = data.setdefault("app_settings", {})
    for key, default in (("recording_dir", "recordings"), ("snapshot_dir", "snapshots")):
        value = settings.get(key) or default
        if not os.path.isabs(value):
            settings[key] = str(previous / value)
    target.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".upgrade-profile-", dir=target)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(data, output, indent=2); output.flush(); os.fsync(output.fileno())
        # Do not replace a configuration created since the initial check.
        with destination.open("x", encoding="utf-8") as output:
            output.write(Path(name).read_text(encoding="utf-8")); output.flush(); os.fsync(output.fileno())
    finally:
        Path(name).unlink(missing_ok=True)
    return True
