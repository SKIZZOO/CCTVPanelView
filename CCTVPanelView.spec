# -*- mode: python ; coding: utf-8 -*-
import os
import ssl
from pathlib import Path
ffmpeg_dir = Path(os.environ['CCTVPANELVIEW_FFMPEG_DIR'])
runtime_ca = Path(ssl.__file__).with_name('codex-rejected-cas.pem')
# Preserve certificate policy data required by the build's Python distribution.
tls_data = [(str(runtime_ca), '.')] if runtime_ca.is_file() else []


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[(str(ffmpeg_dir / name), '.') for name in ('ffmpeg.exe', 'ffplay.exe', 'ffprobe.exe')],
    datas=[('assets', 'assets'), ('sounds', 'sounds'), ('mobilenet.caffemodel', '.'), ('deploy.prototxt', '.'), ('yolov5n.onnx', '.')] + tls_data,
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
