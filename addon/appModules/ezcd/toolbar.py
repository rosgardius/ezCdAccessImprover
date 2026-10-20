# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Cross-process access to the buttons of a VCL TToolBar (a comctl32 toolbar)."""

import ctypes
from collections.abc import Iterator
from contextlib import contextmanager
from ctypes.wintypes import BOOL, HWND, RECT
from dataclasses import dataclass

import watchdog
import winKernel
import winUser
from winBindings import kernel32, user32

TB_GETBUTTON = 0x417
TB_BUTTONCOUNT = 0x418
TB_GETITEMRECT = 0x41D
TB_GETBUTTONTEXTW = 0x44B
TBSTATE_ENABLED = 0x04
TBSTATE_HIDDEN = 0x08
WM_LBUTTONDOWN = 0x201
WM_LBUTTONUP = 0x202
MK_LBUTTON = 0x1

# Messages go from NVDA's main thread: a hung ezcd must not freeze NVDA.
_TIMEOUT_MS = 500
_BUFFER_SIZE = 1024
_MAX_TEXT_LENGTH = _BUFFER_SIZE // 2 - 1

# Not in winBindings; a private library object keeps these declarations away from ctypes.windll.
_is_hung_app_window = ctypes.WinDLL("user32").IsHungAppWindow
_is_hung_app_window.argtypes = (HWND,)
_is_hung_app_window.restype = BOOL


class _ButtonHead(ctypes.Structure):
    # The leading fields of TBBUTTON, laid out the same for 32- and 64-bit processes.
    _fields_ = (
        ("iBitmap", ctypes.c_int),
        ("idCommand", ctypes.c_int),
        ("fsState", ctypes.c_ubyte),
        ("fsStyle", ctypes.c_ubyte),
    )


@dataclass(frozen=True)
class ToolButton:
    index: int
    image: int
    """``iBitmap``, equal to ``ImageIndex`` of the ``TToolButton``."""
    command: int
    state: int
    text: str

    @property
    def enabled(self) -> bool:
        return bool(self.state & TBSTATE_ENABLED)

    @property
    def hidden(self) -> bool:
        return bool(self.state & TBSTATE_HIDDEN)


def _send(hwnd: int, msg: int, wparam: int = 0, lparam: int = 0) -> int:
    res = watchdog.cancellableSendMessage(
        hwnd, msg, wparam, lparam, flags=winUser.SMTO_ABORTIFHUNG, timeout=_TIMEOUT_MS
    )
    return ctypes.c_ssize_t(res).value


@contextmanager
def _remote_buffer(process_handle: int) -> Iterator[int]:
    address = winKernel.virtualAllocEx(
        process_handle, None, _BUFFER_SIZE, winKernel.MEM_COMMIT, winKernel.PAGE_READWRITE
    )
    try:
        yield address
    finally:
        winKernel.virtualFreeEx(process_handle, address, 0, winKernel.MEM_RELEASE)


def _read(process_handle: int, address: int, target: ctypes.Array | ctypes.Structure) -> None:
    if not winKernel.readProcessMemory(
        process_handle, address, ctypes.byref(target), ctypes.sizeof(target), None
    ):
        raise ctypes.WinError()


def button_count(hwnd: int) -> int:
    return max(_send(hwnd, TB_BUTTONCOUNT), 0)


def read_buttons(hwnd: int, process_handle: int) -> list[ToolButton]:
    """Reads all buttons of the toolbar. Raises ``OSError`` if ezcd's memory is not accessible."""
    buttons = []
    with _remote_buffer(process_handle) as address:
        for index in range(button_count(hwnd)):
            if not _send(hwnd, TB_GETBUTTON, index, address):
                continue
            head = _ButtonHead()
            _read(process_handle, address, head)
            text = ""
            length = _send(hwnd, TB_GETBUTTONTEXTW, head.idCommand, 0)
            if 0 < length <= _MAX_TEXT_LENGTH and _send(hwnd, TB_GETBUTTONTEXTW, head.idCommand, address) > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                _read(process_handle, address, buffer)
                text = buffer.value
            buttons.append(ToolButton(index, head.iBitmap, head.idCommand, head.fsState, text))
    return buttons


def item_rect(hwnd: int, process_handle: int, index: int) -> RECT | None:
    """The button's rectangle in the toolbar's client coordinates."""
    rect = RECT()
    with _remote_buffer(process_handle) as address:
        if not _send(hwnd, TB_GETITEMRECT, index, address):
            return None
        _read(process_handle, address, rect)
    return rect


def click(hwnd: int, process_handle: int, index: int) -> bool:
    """Posts a left click to the button's centre; the real mouse pointer does not move."""
    rect = item_rect(hwnd, process_handle, index)
    if rect is None:
        return False
    lparam = winUser.MAKELONG((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
    return bool(user32.PostMessage(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)) and bool(
        user32.PostMessage(hwnd, WM_LBUTTONUP, 0, lparam)
    )


def set_focus(hwnd: int) -> bool:
    # SetFocus sends focus messages to ezcd's thread and waits for them.
    if _is_hung_app_window(hwnd):
        return False
    _process_id, thread_id = winUser.getWindowThreadProcessID(hwnd)
    current_thread_id = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(current_thread_id, thread_id, True)
    try:
        user32.SetFocus(hwnd)
    finally:
        user32.AttachThreadInput(current_thread_id, thread_id, False)
    return True
