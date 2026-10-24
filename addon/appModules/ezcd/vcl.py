# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""VCL objects in ezcd's memory: the object of a window and its controls without windows.

The offsets are those of ezcd 13.2.1.1, a 64-bit VCL program; another version may move them.
"""

import ctypes
from ctypes.wintypes import HANDLE, HWND, LPCWSTR, RECT
from dataclasses import dataclass

import winUser
from logHandler import log

from . import remote, screen
from .language import LanguageFiles

# Not in winBindings; a private library object keeps these declarations away from ctypes.windll.
_user32 = ctypes.WinDLL("user32")
_get_prop = _user32.GetPropW
_get_prop.argtypes = (HWND, LPCWSTR)
_get_prop.restype = HANDLE
_get_window_long_ptr = _user32.GetWindowLongPtrW
_get_window_long_ptr.argtypes = (HWND, ctypes.c_int)
_get_window_long_ptr.restype = ctypes.c_ssize_t
_GWLP_HINSTANCE = -6

# Before the virtual method table an object points to: the pointer to the class name, a short string.
_VMT_CLASS_NAME = -136
# TWinControl.FControls: a TList of the controls without windows.
_CONTROLS = 0x398
# TList: the pointer to the array of items, then their count.
_LIST_ITEMS = 8
_LIST_COUNT = 16
# TControl: FLeft, FTop, FWidth, FHeight in the parent's client pixels; FVisible, then FEnabled; the code
# pointer of FOnClick, nil without a handler.
_BOUNDS = 0x90
_VISIBLE_ENABLED = 0xA9
_ON_CLICK = 0x1F8
# TControl.FText: the caption, a null-terminated string made by StrAlloc, which keeps the size of the block
# in bytes, these 4 included, right before it.
_TEXT = 0x2D0
_MAX_TEXT_LENGTH = 1024
_LABEL_CLASSES = frozenset(("TLabel",))


class _Bounds(ctypes.Structure):
    _fields_ = (
        ("left", ctypes.c_int32),
        ("top", ctypes.c_int32),
        ("width", ctypes.c_int32),
        ("height", ctypes.c_int32),
    )


@dataclass(frozen=True)
class Control:
    """A control without a window."""

    address: int
    class_name: str
    left: int
    """In the client pixels of the window holding it, as ``top``."""
    top: int
    width: int
    height: int
    visible: bool
    enabled: bool
    on_click: bool
    """Whether the control has a handler of clicks."""
    text: str
    """The caption, empty if none."""


def window_object(hwnd: int) -> int:
    """The address of the window's VCL object; 0 if it has none."""
    # VCL keeps it in a property named after the module and the thread that made the window.
    instance = _get_window_long_ptr(hwnd, _GWLP_HINSTANCE)
    _process_id, thread_id = winUser.getWindowThreadProcessID(hwnd)
    return _get_prop(hwnd, f"ControlOfs{instance:08X}{thread_id:08X}") or 0


def _pointer(process_handle: int, address: int) -> int:
    value = (ctypes.c_uint64 * 1)()
    remote.read(process_handle, address, value)
    return value[0]


def _class_name(process_handle: int, address: int) -> str:
    name = _pointer(process_handle, _pointer(process_handle, address) + _VMT_CLASS_NAME)
    length = (ctypes.c_ubyte * 1)()
    remote.read(process_handle, name, length)
    text = (ctypes.c_char * length[0])()
    remote.read(process_handle, name + 1, text)
    return text.raw.decode("latin-1")


def _text(process_handle: int, address: int) -> str:
    """The control's caption; empty if none or if it cannot be read, as the offset may be another one in
    another version of ezcd."""
    try:
        text = _pointer(process_handle, address + _TEXT)
        if not text:
            return ""
        size = (ctypes.c_uint32 * 1)()
        remote.read(process_handle, text - 4, size)
        length = (size[0] - 4) // 2 - 1
        if not 0 < length <= _MAX_TEXT_LENGTH:
            return ""
        chars = (ctypes.c_wchar * length)()
        remote.read(process_handle, text, chars)
    except OSError:
        log.debugWarning("Caption of a VCL control of ezcd not read", exc_info=True)
        return ""
    return chars.value


def controls(hwnd: int, process_handle: int, class_names: frozenset[str]) -> list[Control]:
    """The window's controls without windows of the VCL classes; none if ezcd's memory cannot be read."""
    window = window_object(hwnd)
    if not window:
        return []
    found = []
    try:
        control_list = _pointer(process_handle, window + _CONTROLS)
        # VCL makes the list with the first control.
        if not control_list:
            return []
        count = (ctypes.c_int32 * 1)()
        remote.read(process_handle, control_list + _LIST_COUNT, count)
        if count[0] <= 0:
            return []
        items = (ctypes.c_uint64 * count[0])()
        remote.read(process_handle, _pointer(process_handle, control_list + _LIST_ITEMS), items)
        for address in items:
            class_name = _class_name(process_handle, address)
            if class_name not in class_names:
                continue
            bounds = _Bounds()
            remote.read(process_handle, address + _BOUNDS, bounds)
            flags = (ctypes.c_ubyte * 2)()
            remote.read(process_handle, address + _VISIBLE_ENABLED, flags)
            visible, enabled = (bool(flag) for flag in flags)
            on_click = bool(_pointer(process_handle, address + _ON_CLICK))
            text = _text(process_handle, address)
            found.append(
                Control(
                    address,
                    class_name,
                    bounds.left,
                    bounds.top,
                    bounds.width,
                    bounds.height,
                    visible,
                    enabled,
                    on_click,
                    text,
                )
            )
    except OSError:
        log.debugWarning("Controls of a VCL window of ezcd not read", exc_info=True)
        return []
    return found


def screen_rect(hwnd: int, control: Control) -> RECT:
    """The rectangle on the screen of the window's control."""
    left, top = winUser.ClientToScreen(hwnd, control.left, control.top)
    return RECT(left, top, left + control.width, top + control.height)


def label_texts(hwnd: int, process_handle: int, language: LanguageFiles) -> list[screen.Text]:
    """The captions of the window's shown labels without windows, each on one line, at the labels'
    rectangles in the window's logical coordinates, as the display model has texts; none if ezcd's memory
    cannot be read, or if no caption is a string of ezcd's language files.

    Unlike the display model, they are there also scrolled out of view, and never painted only in part.
    """
    found = []
    for label in controls(hwnd, process_handle, _LABEL_CLASSES):
        text = " ".join(label.text.split())
        if label.visible and text:
            edge = screen.to_logical(screen_rect(hwnd, label), hwnd)
            found.append(screen.Text(edge.left, edge.top, edge.right, edge.bottom, text))
    # Another version of ezcd may keep the caption elsewhere: what is read there is no string of ezcd.
    return found if language.knows_any({t.text for t in found}) else []
