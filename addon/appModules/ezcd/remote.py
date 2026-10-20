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

BUFFER_SIZE = 1024
# Messages go from NVDA's main thread: a hung ezcd must not freeze NVDA.
_TIMEOUT_MS = 500


def send(hwnd: int, msg: int, wparam: int = 0, lparam: int = 0) -> int:
    """Sends the message; 0 if ezcd did not answer in time."""
    res = watchdog.cancellableSendMessage(
        hwnd, msg, wparam, lparam, flags=winUser.SMTO_ABORTIFHUNG, timeout=_TIMEOUT_MS
    )
    return ctypes.c_ssize_t(res).value


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
