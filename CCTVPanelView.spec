# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path
ffmpeg_dir = Path(os.environ['CCTVPANELVIEW_FFMPEG_DIR'])


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[(str(ffmpeg_dir / name), '.') for name in ('ffmpeg.exe', 'ffplay.exe', 'ffprobe.exe')],
    datas=[('assets', 'assets'), ('sounds', 'sounds'), ('mobilenet.caffemodel', '.'), ('deploy.prototxt', '.'), ('yolov5n.onnx', '.')],
    hiddenimports=['cctv_server', 'core.diagnostics', 'qrcode.image.pil'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CCTVPanelView',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/cctv_logo.ico'],
)
collection = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='CCTVPanelView')
