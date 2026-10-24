# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['installer.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('core', 'core'), ('ui', 'ui'), ('sounds', 'sounds'), ('main.py', '.'), ('cctv_server.py', '.'), ('CCTVPanelView.exe', '.'), ('CCTVPanelView-Uninstall.exe', '.'), ('uninstaller.py', '.'), ('mobilenet.caffemodel', '.'), ('deploy.prototxt', '.'), ('yolov5n.onnx', '.')],
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
