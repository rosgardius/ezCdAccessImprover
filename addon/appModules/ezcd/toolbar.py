# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Cross-process access to the buttons of a VCL TToolBar (a comctl32 toolbar)."""

import ctypes
from ctypes.wintypes import BOOL, HWND, RECT
from dataclasses import dataclass

import winUser
from logHandler import log
from winBindings import kernel32, user32

from . import remote

TB_GETBUTTON = 0x417
TB_BUTTONCOUNT = 0x418
TB_GETITEMRECT = 0x41D
TB_GETBUTTONTEXTW = 0x44B
TBSTATE_ENABLED = 0x04
TBSTATE_HIDDEN = 0x08
TBSTYLE_SEP = 0x01
TBSTYLE_DROPDOWN = 0x08
# Within the drop-down arrow of a button at any DPI: the arrow is wider than twice this.
_ARROW_INSET = 4

_MAX_TEXT_LENGTH = remote.BUFFER_SIZE // 2 - 1

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
    state: int
    style: int
    text: str

    @property
    def enabled(self) -> bool:
        return bool(self.state & TBSTATE_ENABLED)

    @property
    def hidden(self) -> bool:
        return bool(self.state & TBSTATE_HIDDEN)

    @property
    def separator(self) -> bool:
        return bool(self.style & TBSTYLE_SEP)

    @property
    def dropdown(self) -> bool:
        """Whether the button has a drop-down arrow, which opens its menu."""
        return bool(self.style & TBSTYLE_DROPDOWN)


def read_buttons(hwnd: int, process_handle: int) -> list[ToolButton]:
    """All buttons of the toolbar; none if ezcd's memory is not accessible."""
    buttons = []
    try:
        with remote.buffer(process_handle) as address:
            for index in range(remote.send(hwnd, TB_BUTTONCOUNT)):
                if not remote.send(hwnd, TB_GETBUTTON, index, address):
                    continue
                head = _ButtonHead()
                remote.read(process_handle, address, head)
                text = ""
                length = remote.send(hwnd, TB_GETBUTTONTEXTW, head.idCommand, 0)
                if (
                    0 < length <= _MAX_TEXT_LENGTH
                    and remote.send(hwnd, TB_GETBUTTONTEXTW, head.idCommand, address) > 0
                ):
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    remote.read(process_handle, address, buffer)
                    text = buffer.value
                buttons.append(ToolButton(index, head.iBitmap, head.fsState, head.fsStyle, text))
    except OSError:
        log.debugWarning("Cannot read toolbar buttons of ezcd", exc_info=True)
        return []
    return buttons


def item_rect(hwnd: int, process_handle: int, index: int) -> RECT | None:
    """The button's rectangle in the toolbar's client coordinates; ``None`` if ezcd did not tell."""
    rect = RECT()
    try:
        with remote.buffer(process_handle) as address:
            if not remote.send(hwnd, TB_GETITEMRECT, index, address):
                return None
            remote.read(process_handle, address, rect)
    except OSError:
        log.debugWarning("Cannot read the rectangle of a toolbar button of ezcd", exc_info=True)
        return None
    return rect


def click(hwnd: int, process_handle: int, index: int, arrow: bool = False) -> bool:
    """Posts a left click to the button's centre or its drop-down arrow."""
    rect = item_rect(hwnd, process_handle, index)
    if rect is None:
        return False
    x = rect.right - _ARROW_INSET if arrow else (rect.left + rect.right) // 2
    return remote.post_click(hwnd, x, (rect.top + rect.bottom) // 2)


def open_context_menu(hwnd: int, process_handle: int, index: int) -> bool:
    """Has ezcd open the button's context menu at its centre, as a right click does.

    The Applications key gives no point, and the toolbar then opens no menu of a button.
    """
    rect = item_rect(hwnd, process_handle, index)
    if rect is None:
        return False
    x, y = winUser.ClientToScreen(hwnd, (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
    return remote.post_context_menu(hwnd, x, y)


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
