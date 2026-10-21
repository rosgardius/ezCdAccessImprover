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
# Messages go from NVDA's main thread: a hung ezcd must not freeze NVDA.
_TIMEOUT_MS = 500


def send(hwnd: int, msg: int, wparam: int = 0, lparam: int = 0) -> int:
    """Sends the message; 0 if ezcd did not answer in time."""
    res = watchdog.cancellableSendMessage(
        hwnd, msg, wparam, lparam, flags=winUser.SMTO_ABORTIFHUNG, timeout=_TIMEOUT_MS
    )
    return ctypes.c_ssize_t(res).value


def press(hwnd: int, vk: int) -> bool:
    """Sends a press of the key to the window; ``False`` if ezcd did not handle it in time.

    The window handles the key before this returns, together with what ezcd does in response.
    """
    for msg, data in ((_WM_KEYDOWN, _KEY_DOWN_DATA), (_WM_KEYUP, _KEY_UP_DATA)):
        try:
            if not _send_key(hwnd, msg, vk, data):
                return False
        except CallCancelled:
            return False
    return True


def _send_key(hwnd: int, msg: int, vk: int, data: int) -> bool:
    # When another window comes to the foreground meanwhile, a dialog of ezcd for one, NVDA's watchdog
    # cancels the wait and raises CallCancelled as this function returns.
    result = ctypes.c_size_t()
    return bool(
        user32.SendMessageTimeout(
            hwnd, msg, vk, data, winUser.SMTO_ABORTIFHUNG, _TIMEOUT_MS, ctypes.byref(result)
        )
    )


def post_press(hwnd: int, vk: int):
    winUser.PostMessage(hwnd, _WM_KEYDOWN, vk, _KEY_DOWN_DATA)
    winUser.PostMessage(hwnd, _WM_KEYUP, vk, _KEY_UP_DATA)


@contextmanager
def buffer(process_handle: int) -> Iterator[int]:
    """A buffer of ``BUFFER_SIZE`` bytes in ezcd's memory."""
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
