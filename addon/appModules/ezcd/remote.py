# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Window messages to ezcd and buffers in its memory for their structures."""

import ctypes
from collections.abc import Iterator
from contextlib import contextmanager

import watchdog
import winKernel
import winUser
from exceptions import CallCancelled
from winBindings import user32

BUFFER_SIZE = 1024
_WM_KEYDOWN = 0x100
_WM_KEYUP = 0x101
_KEY_DOWN_DATA = 0x1
_KEY_UP_DATA = 0xC0000001
_WM_LBUTTONDOWN = 0x201
_WM_LBUTTONUP = 0x202
_MK_LBUTTON = 0x1
# Messages go from NVDA's main thread: a hung ezcd must not freeze NVDA.
_TIMEOUT_MS = 500


def send(hwnd: int, msg: int, wparam: int = 0, lparam: int = 0) -> int:
    """Sends the message; 0 if ezcd did not answer in time."""
    res = watchdog.cancellableSendMessage(
        hwnd, msg, wparam, lparam, flags=winUser.SMTO_ABORTIFHUNG, timeout=_TIMEOUT_MS
    )
    return ctypes.c_ssize_t(res).value


def handled(hwnd: int, msg: int, wparam: int, lparam: int, timeout_ms: int = _TIMEOUT_MS) -> bool:
    """Sends the message; whether ezcd handled it in time, for messages whose result tells nothing."""
    result = ctypes.c_size_t()
    return bool(
        user32.SendMessageTimeout(
            hwnd, msg, wparam, lparam, winUser.SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(result)
        )
    )


def text(hwnd: int, length: int, timeout_ms: int = _TIMEOUT_MS) -> str:
    """The window's text as the window itself gives it; empty if ezcd does not answer.

    The window text Windows keeps for an edit is not updated when its text changes.
    """
    buffer = ctypes.create_unicode_buffer(length)
    if not handled(hwnd, winUser.WM_GETTEXT, length, ctypes.addressof(buffer), timeout_ms):
        return ""
    return buffer.value


def press(hwnd: int, vk: int) -> bool:
    """Sends a press of the key to the window; ``False`` if ezcd did not handle it in time.

    The window handles the key before this returns, together with what ezcd does in response.
    """
    # When another window comes to the foreground meanwhile, a dialog of ezcd for one, NVDA's watchdog
    # cancels the wait and raises CallCancelled as the call returns.
    try:
        return handled(hwnd, _WM_KEYDOWN, vk, _KEY_DOWN_DATA) and handled(hwnd, _WM_KEYUP, vk, _KEY_UP_DATA)
    except CallCancelled:
        return False


def post_press(hwnd: int, vk: int):
    winUser.PostMessage(hwnd, _WM_KEYDOWN, vk, _KEY_DOWN_DATA)
    winUser.PostMessage(hwnd, _WM_KEYUP, vk, _KEY_UP_DATA)


def click(hwnd: int, x: int, y: int, timeout_ms: int = _TIMEOUT_MS) -> bool:
    """Sends a left click at the client point; ``False`` if ezcd did not handle it in time.

    The mouse pointer does not move. Unlike a posted click, the click is handled when this returns.
    """
    lparam = winUser.MAKELONG(x, y)
    pressed = handled(hwnd, _WM_LBUTTONDOWN, _MK_LBUTTON, lparam, timeout_ms)
    # A press that timed out is still handled later; without the release the button would stay down.
    released = handled(hwnd, _WM_LBUTTONUP, 0, lparam, timeout_ms)
    return pressed and released


def post_click(hwnd: int, x: int, y: int) -> bool:
    """Posts a left click at the client point; the mouse pointer does not move."""
    lparam = winUser.MAKELONG(x, y)
    return bool(user32.PostMessage(hwnd, _WM_LBUTTONDOWN, _MK_LBUTTON, lparam)) and bool(
        user32.PostMessage(hwnd, _WM_LBUTTONUP, 0, lparam)
    )


@contextmanager
def buffer(process_handle: int) -> Iterator[int]:
    """A buffer of ``BUFFER_SIZE`` bytes in ezcd's memory. Raises ``OSError`` if it cannot be made."""
    address = winKernel.virtualAllocEx(
        process_handle, None, BUFFER_SIZE, winKernel.MEM_COMMIT, winKernel.PAGE_READWRITE
    )
    try:
        yield address
    finally:
        winKernel.virtualFreeEx(process_handle, address, 0, winKernel.MEM_RELEASE)


def read(process_handle: int, address: int, target: ctypes.Array | ctypes.Structure) -> None:
    if not winKernel.readProcessMemory(
        process_handle, address, ctypes.byref(target), ctypes.sizeof(target), None
    ):
        raise ctypes.WinError()


def write(process_handle: int, address: int, source: ctypes.Array | ctypes.Structure) -> None:
    if not winKernel.writeProcessMemory(
        process_handle, address, ctypes.byref(source), ctypes.sizeof(source), None
    ):
        raise ctypes.WinError()
