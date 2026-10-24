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
    env["CCTVPANELVIEW_FFMPEG_DIR"] = str(args.ffmpeg_dir.resolve())
    env["CCTVPANELVIEW_DIST_DIR"] = str(args.dist_dir.resolve())
    args.dist_dir.mkdir(parents=True, exist_ok=True)
    for spec in ("CCTVPanelView.spec", "CCTVPanelView-Uninstall.spec", "CCTVPanelView-Setup.spec"):
        subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", str(args.dist_dir.resolve()),
                        "--workpath", str(args.build_dir.resolve()), spec], cwd=root, env=env, check=True)
    report = args.dist_dir.resolve() / "packaged-self-test.json"
    result = subprocess.run([str(args.dist_dir.resolve() / "CCTVPanelView.exe"), "--self-test", f"--self-test-report={report}"],
                            cwd=args.dist_dir.resolve(), timeout=180)
    if result.returncode or not report.is_file():
        raise SystemExit("Packaged application self-test failed")
    print("Installer built:", args.dist_dir.resolve() / "CCTVPanelView-Setup.exe")


if __name__ == "__main__":
    main()
