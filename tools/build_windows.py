"""Build the GUI app, GUI uninstaller and self-contained Windows setup executable."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg-dir", type=Path, required=True, help="Directory containing ffmpeg.exe, ffplay.exe and ffprobe.exe")
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument("--build-dir", type=Path, default=Path("build"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    for name in ("ffmpeg.exe", "ffplay.exe", "ffprobe.exe"):
        if not (args.ffmpeg_dir / name).is_file():
            parser.error(f"Missing {name}")
    env = os.environ.copy()
    # Dependency scanning must use Python's DLLs, not unrelated tools on the host PATH.
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    env["PATH"] = os.pathsep.join(str(path) for path in (
        Path(sys.prefix) / "Scripts", Path(sys.base_prefix) / "DLLs", Path(sys.base_prefix),
        windows / "System32", windows))
    env["PYINSTALLER_CONFIG_DIR"] = str(args.build_dir.resolve() / ".config")
    env.pop("QT_PLUGIN_PATH", None)
    env.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
    env["CCTVPANELVIEW_FFMPEG_DIR"] = str(args.ffmpeg_dir.resolve())
    env["CCTVPANELVIEW_DIST_DIR"] = str(args.dist_dir.resolve())
    args.dist_dir.mkdir(parents=True, exist_ok=True)
    for spec in ("CCTVPanelView.spec", "CCTVPanelView-Uninstall.spec", "CCTVPanelView-Setup.spec"):
        subprocess.run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "--distpath", str(args.dist_dir.resolve()),
                        "--workpath", str(args.build_dir.resolve()), spec], cwd=root, env=env, check=True)
    report = args.dist_dir.resolve() / "packaged-self-test.json"
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    result = subprocess.run([str(args.dist_dir.resolve() / "CCTVPanelView.exe"), "--self-test", f"--self-test-report={report}"],
                            cwd=args.dist_dir.resolve(), env=env, timeout=180)
    if result.returncode or not report.is_file():
        raise SystemExit("Packaged application self-test failed")
    print("Installer built:", args.dist_dir.resolve() / "CCTVPanelView-Setup.exe")


if __name__ == "__main__":
    main()
