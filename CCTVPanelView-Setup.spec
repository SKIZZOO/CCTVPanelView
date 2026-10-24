# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path
dist_dir = Path(os.environ['CCTVPANELVIEW_DIST_DIR'])


a = Analysis(
    ['installer.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), (str(dist_dir / 'CCTVPanelView.exe'), '.'), (str(dist_dir / 'CCTVPanelView-Uninstall.exe'), '.')],
    hiddenimports=['winreg'],
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
    a.binaries,
    a.datas,
    [],
    name='CCTVPanelView-Setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
