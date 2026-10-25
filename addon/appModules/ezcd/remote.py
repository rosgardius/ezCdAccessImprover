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
from logHandler import log
from winBindings import user32

BUFFER_SIZE = 1024
_WM_KEYDOWN = 0x100
_WM_KEYUP = 0x101
_KEY_DOWN_DATA = 0x1
_KEY_UP_DATA = 0xC0000001
_WM_LBUTTONDOWN = 0x201
_WM_LBUTTONUP = 0x202
_MK_LBUTTON = 0x1
_WM_CONTEXTMENU = 0x7B
# Messages go from NVDA's main thread: a hung ezcd must not freeze NVDA.
_TIMEOUT_MS = 500
# TreeView messages, which TVirtualStringTree answers too.
TVM_GETNEXTITEM = 0x110A
TVM_GETITEMW = 0x113E
TVGN_ROOT = 0x0
TVGN_NEXT = 0x1
TVGN_PARENT = 0x3
TVGN_CHILD = 0x4
TVGN_FIRSTVISIBLE = 0x5
TVGN_NEXTVISIBLE = 0x6
TVGN_PREVIOUSVISIBLE = 0x7
TVGN_CARET = 0x9
TVGN_LASTVISIBLE = 0xA
TVIF_STATE = 0x8
TVIF_HANDLE = 0x10
TVIS_SELECTED = 0x2
TVIF_TEXT = 0x1


def send(hwnd: int, msg: int, wparam: int = 0, lparam: int = 0) -> int:
    """Sends the message; 0 if ezcd did not answer in time."""
    res = watchdog.cancellableSendMessage(
        hwnd, msg, wparam, lparam, flags=winUser.SMTO_ABORTIFHUNG, timeout=_TIMEOUT_MS
    )
    return ctypes.c_ssize_t(res).value


def handled(hwnd: int, msg: int, wparam: int, lparam: int, timeout_ms: int = _TIMEOUT_MS) -> bool:
    """Sends the message; whether ezcd handled it in time, for messages whose result tells nothing."""
    result = ctypes.c_size_t()
    if not user32.SendMessageTimeout(
        hwnd, msg, wparam, lparam, winUser.SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(result)
    ):
        log.debugWarning(f"ezcd did not handle message 0x{msg:X} in time")
        return False
    return True


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


def post_context_menu(hwnd: int, x: int, y: int) -> bool:
    """Has ezcd open the window's context menu at the screen point, as a right click there does."""
    return bool(user32.PostMessage(hwnd, _WM_CONTEXTMENU, hwnd, (x & 0xFFFF) | (y & 0xFFFF) << 16))


@contextmanager
def buffer(process_handle: int) -> Iterator[int]:
    """A buffer of ``BUFFER_SIZE`` bytes in ezcd's memory. Raises ``OSError`` if it cannot be made.

    The process handle needs access to ezcd's memory: an NVDAObject's has it, the app module's has not.
    """
    address = winKernel.virtualAllocEx(
        process_handle, None, BUFFER_SIZE, winKernel.MEM_COMMIT, winKernel.PAGE_READWRITE
    )
    # winKernel checks the result against 0, but a failed allocation gives None: a message would then
    # have ezcd write to address 0.
    if not address:
        raise ctypes.WinError()
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


class TreeItemStructure(ctypes.Structure):
    # TVITEMEXW; ezcd and NVDA are both 64-bit.
    _fields_ = (
        ("mask", ctypes.c_uint),
        ("hItem", ctypes.c_void_p),
        ("state", ctypes.c_uint),
        ("stateMask", ctypes.c_uint),
        ("pszText", ctypes.c_void_p),
        ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int),
        ("iSelectedImage", ctypes.c_int),
        ("cChildren", ctypes.c_int),
        ("lParam", ctypes.c_void_p),
        ("iIntegral", ctypes.c_int),
        ("uStateEx", ctypes.c_uint),
        ("hwnd", ctypes.c_void_p),
        ("iExpandedImage", ctypes.c_int),
        ("iReserved", ctypes.c_int),
    )


def next_node(hwnd: int, relation: int, node: int = 0) -> int:
    """The node of a tree view in the ``TVGN_*`` relation to the node; 0 if there is none or ezcd did not
    answer."""
    return send(hwnd, TVM_GETNEXTITEM, relation, node)


def node_text(hwnd: int, process_handle: int, node: int) -> str:
    """The text of the tree view's node; empty if ezcd did not tell. The node must come from ``next_node``
    just before: the tree does not check it."""
    item = TreeItemStructure()
    chars = (BUFFER_SIZE - ctypes.sizeof(item)) // ctypes.sizeof(ctypes.c_wchar)
    text = (ctypes.c_wchar * chars)()
    try:
        with buffer(process_handle) as address:
            item = TreeItemStructure(
                mask=TVIF_HANDLE | TVIF_TEXT,
                hItem=node,
                pszText=address + ctypes.sizeof(item),
                cchTextMax=chars,
            )
            write(process_handle, address, item)
            if not send(hwnd, TVM_GETITEMW, 0, address):
                return ""
            read(process_handle, address + ctypes.sizeof(item), text)
    except OSError:
        log.debugWarning("Tree view node text unavailable", exc_info=True)
        return ""
    return text.value
