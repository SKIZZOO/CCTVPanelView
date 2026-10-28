"""Consistent Windows identity and native Unicode shortcuts, without script files."""
import os
from pathlib import Path
import shutil
import sys

APP_USER_MODEL_ID = "cctvpanelview.studio.ai.cctv.v1"


def set_process_app_id():
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)


def restore_legacy_icons(target_dir):
    """Keep old pinned shortcuts pointing at assets/ working after onedir upgrades."""
    root = Path(target_dir)
    for name in ("cctv_logo.ico", "app_icon.ico", "cctvpanelview.ico"):
        source = root / "_internal" / "assets" / name
        if source.is_file():
            destination = root / "assets" / name
            destination.parent.mkdir(exist_ok=True)
            shutil.copy2(source, destination)


def create_shortcut(target, destination, working_dir, description, app_id=APP_USER_MODEL_ID):
    """IShellLink + IPropertyStore, including the same AppUserModelID as the GUI."""
    if sys.platform != "win32":
        raise OSError("Windows shortcuts require Windows")
    import ctypes as c
    from ctypes import wintypes as w
    import uuid

    class GUID(c.Structure):
        _fields_ = [("data", c.c_ubyte * 16)]
        def __init__(self, text):
            super().__init__()
            c.memmove(c.byref(self), uuid.UUID(text).bytes_le, 16)

    class PROPERTYKEY(c.Structure):
        _fields_ = [("fmtid", GUID), ("pid", w.DWORD)]

    class Value(c.Union):
        _fields_ = [("text", c.c_wchar_p), ("storage", c.c_ubyte * 16)]

    class PROPVARIANT(c.Structure):
        _fields_ = [("vt", w.WORD), ("r1", w.WORD), ("r2", w.WORD), ("r3", w.WORD), ("value", Value)]

    def check(hr):
        if hr < 0:
            raise OSError(f"Windows shortcut operation failed (0x{hr & 0xffffffff:08x})")

    def call(pointer, index, types, *args):
        table = c.cast(pointer, c.POINTER(c.POINTER(c.c_void_p))).contents
        return c.WINFUNCTYPE(c.c_long, c.c_void_p, *types)(table[index])(pointer, *args)

    ole = c.WinDLL("ole32")
    # ctypes' default int arguments would truncate COM pointer addresses on x64.
    ole.CoInitializeEx.argtypes = [c.c_void_p, w.DWORD]
    ole.CoInitializeEx.restype = c.c_long
    ole.CoCreateInstance.argtypes = [c.POINTER(GUID), c.c_void_p, w.DWORD, c.POINTER(GUID), c.POINTER(c.c_void_p)]
    ole.CoCreateInstance.restype = c.c_long
    initialized = ole.CoInitializeEx(None, 2)
    if initialized < 0 and initialized != -2147417850:  # existing different apartment is usable
        check(initialized)
    shell, persist, store = c.c_void_p(), c.c_void_p(), c.c_void_p()
    try:
        check(ole.CoCreateInstance(c.byref(GUID("00021401-0000-0000-C000-000000000046")), None, 1,
                                  c.byref(GUID("000214F9-0000-0000-C000-000000000046")), c.byref(shell)))
        for index, value in ((20, str(target)), (9, str(working_dir)), (7, description)):
            check(call(shell, index, [c.c_wchar_p], value))
        check(call(shell, 17, [c.c_wchar_p, c.c_int], str(target), 0))
        check(call(shell, 0, [c.POINTER(GUID), c.POINTER(c.c_void_p)],
                   c.byref(GUID("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")), c.byref(store)))
        key = PROPERTYKEY(GUID("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5)
        value = PROPVARIANT(); value.vt = 31; value.value.text = app_id
        check(call(store, 6, [c.POINTER(PROPERTYKEY), c.POINTER(PROPVARIANT)], c.byref(key), c.byref(value)))
        check(call(store, 7, []))
        check(call(shell, 0, [c.POINTER(GUID), c.POINTER(c.c_void_p)],
                   c.byref(GUID("0000010B-0000-0000-C000-000000000046")), c.byref(persist)))
        check(call(persist, 6, [c.c_wchar_p, w.BOOL], str(destination), True))
    finally:
        for pointer in (store, persist, shell):
            if pointer:
                call(pointer, 2, [])
        if initialized >= 0:
            ole.CoUninitialize()
