"""The Win32 calls of the checker, declared once with 64-bit types."""

import contextlib
import ctypes
import ctypes.wintypes as W
from collections.abc import Iterator

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_version = ctypes.WinDLL("version", use_last_error=True)

_EnumProc = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)

for _library, _name, _restype, _argtypes in (
    (user32, "GetForegroundWindow", W.HWND, ()),
    (user32, "GetWindow", W.HWND, (W.HWND, W.UINT)),
    (user32, "GetAncestor", W.HWND, (W.HWND, W.UINT)),
    (user32, "GetClassNameW", ctypes.c_int, (W.HWND, W.LPWSTR, ctypes.c_int)),
    (user32, "InternalGetWindowText", ctypes.c_int, (W.HWND, W.LPWSTR, ctypes.c_int)),
    (user32, "GetWindowThreadProcessId", W.DWORD, (W.HWND, ctypes.POINTER(W.DWORD))),
    (user32, "GetWindowRect", W.BOOL, (W.HWND, ctypes.POINTER(W.RECT))),
    (user32, "GetWindowLongW", ctypes.c_long, (W.HWND, ctypes.c_int)),
    (user32, "GetWindowLongPtrW", ctypes.c_ssize_t, (W.HWND, ctypes.c_int)),
    (user32, "GetPropW", W.HANDLE, (W.HWND, W.LPCWSTR)),
    (user32, "IsWindowVisible", W.BOOL, (W.HWND,)),
    (user32, "IsWindowEnabled", W.BOOL, (W.HWND,)),
    (user32, "EnumWindows", W.BOOL, (_EnumProc, W.LPARAM)),
    (user32, "PostMessageW", W.BOOL, (W.HWND, W.UINT, W.WPARAM, W.LPARAM)),
    (
        user32,
        "SendMessageTimeoutW",
        W.LPARAM,
        (W.HWND, W.UINT, W.WPARAM, W.LPARAM, W.UINT, W.UINT, ctypes.POINTER(ctypes.c_size_t)),
    ),
    (user32, "GetDpiForWindow", W.UINT, (W.HWND,)),
    (user32, "SetProcessDpiAwarenessContext", W.BOOL, (W.HANDLE,)),
    (user32, "ClientToScreen", W.BOOL, (W.HWND, ctypes.POINTER(W.POINT))),
    (kernel32, "OpenProcess", W.HANDLE, (W.DWORD, W.BOOL, W.DWORD)),
    (
        kernel32,
        "VirtualAllocEx",
        ctypes.c_void_p,
        (W.HANDLE, ctypes.c_void_p, ctypes.c_size_t, W.DWORD, W.DWORD),
    ),
    (kernel32, "VirtualFreeEx", W.BOOL, (W.HANDLE, ctypes.c_void_p, ctypes.c_size_t, W.DWORD)),
    (kernel32, "CloseHandle", W.BOOL, (W.HANDLE,)),
    (kernel32, "QueryFullProcessImageNameW", W.BOOL, (W.HANDLE, W.DWORD, W.LPWSTR, ctypes.POINTER(W.DWORD))),
    (
        kernel32,
        "ReadProcessMemory",
        W.BOOL,
        (W.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)),
    ),
    (_version, "GetFileVersionInfoSizeW", W.DWORD, (W.LPCWSTR, ctypes.POINTER(W.DWORD))),
    (_version, "GetFileVersionInfoW", W.BOOL, (W.LPCWSTR, W.DWORD, W.DWORD, ctypes.c_void_p)),
    (
        _version,
        "VerQueryValueW",
        W.BOOL,
        (ctypes.c_void_p, W.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(W.UINT)),
    ),
):
    _function = getattr(_library, _name)
    _function.restype = _restype
    _function.argtypes = _argtypes


class GuiThreadInfo(ctypes.Structure):
    _fields_ = (
        ("cbSize", W.DWORD),
        ("flags", W.DWORD),
        ("hwndActive", W.HWND),
        ("hwndFocus", W.HWND),
        ("hwndCapture", W.HWND),
        ("hwndMenuOwner", W.HWND),
        ("hwndMoveSize", W.HWND),
        ("hwndCaret", W.HWND),
        ("rc", W.RECT),
    )


user32.GetGUIThreadInfo.argtypes = (W.DWORD, ctypes.POINTER(GuiThreadInfo))
user32.GetGUIThreadInfo.restype = W.BOOL

GW_CHILD, GW_HWNDNEXT = 5, 2
GA_PARENT, GA_ROOT = 1, 2
GWL_STYLE = -16
GWLP_HINSTANCE = -6
WS_VISIBLE, WS_DISABLED, WS_TABSTOP = 0x10000000, 0x08000000, 0x00010000
WM_NULL = 0x0000
SMTO_ABORTIFHUNG = 2
SEND_TIMEOUT_MS = 500
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_VM_READ = 0x0010
PROCESS_VM_OPERATION = 0x0008
BUFFER_SIZE = 4096
_MEM_COMMIT_RESERVE, _MEM_RELEASE, _PAGE_READWRITE = 0x3000, 0x8000, 0x04
# Coordinates in physical pixels, also those of other processes' windows.
_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4


def be_dpi_aware():
    user32.SetProcessDpiAwarenessContext(_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)


def class_name(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def text(hwnd: int) -> str:
    """The window text Windows keeps; it does not ask the window, so it cannot hang."""
    buffer = ctypes.create_unicode_buffer(1024)
    user32.InternalGetWindowText(hwnd, buffer, 1024)
    return buffer.value


def rect(hwnd: int) -> W.RECT:
    """The window's rectangle on the screen, in physical pixels."""
    result = W.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(result))
    return result


def style(hwnd: int) -> int:
    return user32.GetWindowLongW(hwnd, GWL_STYLE) & 0xFFFFFFFF


def is_visible(hwnd: int) -> bool:
    return bool(user32.IsWindowVisible(hwnd))


def is_enabled(hwnd: int) -> bool:
    return bool(user32.IsWindowEnabled(hwnd))


def parent(hwnd: int) -> int:
    return user32.GetAncestor(hwnd, GA_PARENT) or 0


def thread_and_process(hwnd: int) -> tuple[int, int]:
    process = W.DWORD()
    thread = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process))
    return thread, process.value


def gui_info(thread: int) -> GuiThreadInfo:
    info = GuiThreadInfo(cbSize=ctypes.sizeof(GuiThreadInfo))
    user32.GetGUIThreadInfo(thread, ctypes.byref(info))
    return info


def children(hwnd: int, window_class: str | None = None) -> list[int]:
    """The direct child windows of the class, or of any class, in z-order."""
    found = []
    child = user32.GetWindow(hwnd, GW_CHILD)
    while child:
        if window_class is None or class_name(child) == window_class:
            found.append(child)
        child = user32.GetWindow(child, GW_HWNDNEXT)
    return found


def descendants(hwnd: int) -> Iterator[int]:
    """All windows inside the window, each followed by its own."""
    for child in children(hwnd):
        yield child
        yield from descendants(child)


def top_level_windows() -> list[int]:
    found = []

    def callback(hwnd, _parameter):
        found.append(hwnd)
        return True

    user32.EnumWindows(_EnumProc(callback), 0)
    return found


def send(hwnd: int, message: int, wparam: int = 0, lparam: int = 0) -> int | None:
    """Sends the message and waits ``SEND_TIMEOUT_MS`` at most; ``None`` if the window did not answer."""
    result = ctypes.c_size_t()
    if not user32.SendMessageTimeoutW(
        hwnd, message, wparam, lparam, SMTO_ABORTIFHUNG, SEND_TIMEOUT_MS, ctypes.byref(result)
    ):
        return None
    return result.value


def post(hwnd: int, message: int, wparam: int = 0, lparam: int = 0) -> bool:
    return bool(user32.PostMessageW(hwnd, message, wparam, lparam))


def dpi(hwnd: int) -> int:
    return user32.GetDpiForWindow(hwnd) or 96


def process_path(process: int) -> str:
    """The full path of the executable of the process handle; empty if Windows does not give it."""
    size = W.DWORD(32768)
    buffer = ctypes.create_unicode_buffer(size.value)
    if not kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size)):
        return ""
    return buffer.value


def open_process(process_id: int, access: int) -> int:
    """A handle to the process; 0 if Windows refuses it."""
    return kernel32.OpenProcess(access, False, process_id) or 0


def close(handle: int):
    kernel32.CloseHandle(handle)


def read_memory(process: int, address: int, target: ctypes.Array | ctypes.Structure):
    """Reads the process's memory at the address into the object; raises ``OSError`` if it cannot."""
    size = ctypes.sizeof(target)
    done = ctypes.c_size_t()
    if not kernel32.ReadProcessMemory(process, address, ctypes.byref(target), size, ctypes.byref(done)):
        raise ctypes.WinError(ctypes.get_last_error())
    if done.value != size:
        raise OSError(f"{done.value} of {size} bytes read at {address:#x}")


@contextlib.contextmanager
def buffer(process: int) -> Iterator[int]:
    """``BUFFER_SIZE`` bytes in the process's memory, for messages that write their answer there; raises
    ``OSError`` if they cannot be had."""
    address = kernel32.VirtualAllocEx(process, None, BUFFER_SIZE, _MEM_COMMIT_RESERVE, _PAGE_READWRITE)
    if not address:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield address
    finally:
        kernel32.VirtualFreeEx(process, address, 0, _MEM_RELEASE)


def product_version(path: str) -> str | None:
    """The ProductVersion of the executable's version resource; ``None`` if it has none."""
    size = _version.GetFileVersionInfoSizeW(path, None)
    if not size:
        return None
    data = ctypes.create_string_buffer(size)
    if not _version.GetFileVersionInfoW(path, 0, size, data):
        return None
    value = ctypes.c_void_p()
    length = W.UINT()
    if not _version.VerQueryValueW(
        data, r"\VarFileInfo\Translation", ctypes.byref(value), ctypes.byref(length)
    ):
        return None
    language, codepage = (ctypes.c_uint16 * 2).from_address(value.value)
    key = rf"\StringFileInfo\{language:04x}{codepage:04x}\ProductVersion"
    if not _version.VerQueryValueW(data, key, ctypes.byref(value), ctypes.byref(length)) or not length.value:
        return None
    return ctypes.wstring_at(value.value, length.value).rstrip("\0")


def client_origin(hwnd: int) -> tuple[int, int]:
    """The top left corner of the window's client area on the screen."""
    point = W.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    return point.x, point.y
