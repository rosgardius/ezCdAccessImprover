"""ezcd's popup menus, opened by a posted click and closed without choosing anything.

ezcd draws its menu items itself: their texts are in neither the menu nor MSAA outside its process, only
their command IDs.
"""

import ctypes
import ctypes.wintypes as W
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

from . import win
from .ezcd import Ezcd

_Proc = ctypes.WINFUNCTYPE(None, W.HANDLE, W.DWORD, W.HWND, W.LONG, W.LONG, W.DWORD, W.DWORD)
_EVENT_SYSTEM_MENUPOPUPSTART = 0x0006
_WINEVENT_OUTOFCONTEXT = 0
_MN_GETHMENU = 0x01E1
_WM_CANCELMODE = 0x001F
_PM_REMOVE = 1
_GUI_INMENUMODE, _GUI_POPUPMENUMODE = 0x4, 0x10
_OPEN_TIMEOUT = 2.0
_CLOSE_TIMEOUT = 1.0
_POLL = 0.02
# How long the user has to leave ezcd's foreground before a menu opens.
_FOREGROUND_WAIT = 30.0

win.user32.SetWinEventHook.restype = W.HANDLE
win.user32.SetWinEventHook.argtypes = (W.DWORD, W.DWORD, W.HMODULE, _Proc, W.DWORD, W.DWORD, W.DWORD)
win.user32.UnhookWinEvent.argtypes = (W.HANDLE,)
win.user32.GetMenuItemCount.argtypes = (W.HMENU,)
win.user32.GetMenuItemID.restype = W.UINT
win.user32.GetMenuItemID.argtypes = (W.HMENU, ctypes.c_int)
win.user32.PeekMessageW.argtypes = (ctypes.POINTER(W.MSG), W.HWND, W.UINT, W.UINT, W.UINT)
win.user32.DispatchMessageW.argtypes = (ctypes.POINTER(W.MSG),)


class Foreground(Exception):
    """ezcd stayed in the foreground: a menu would open on the user's screen."""


@dataclass(frozen=True)
class Menu:
    ids: tuple[int, ...]
    """The command IDs of the items."""
    owner: int
    """The window that gets the command of the item chosen."""


def _in_menu(ezcd: Ezcd) -> bool:
    return bool(win.gui_info(ezcd.thread_id).flags & (_GUI_INMENUMODE | _GUI_POPUPMENUMODE))


def _pump(seconds: float):
    message = W.MSG()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        while win.user32.PeekMessageW(ctypes.byref(message), None, 0, 0, _PM_REMOVE):
            win.user32.DispatchMessageW(ctypes.byref(message))
        time.sleep(0.01)


def leave_foreground(ezcd: Ezcd):
    """Waits until ezcd is not in the foreground, asking the user to switch away; raises ``Foreground`` if
    it stays."""
    if not ezcd.is_foreground():
        return
    print("Switch away from EZ CD Audio Converter: the checker opens its menus.", file=sys.stderr, flush=True)
    end = time.monotonic() + _FOREGROUND_WAIT
    while ezcd.is_foreground():
        if time.monotonic() > end:
            raise Foreground("ezcd stayed in the foreground: its menus would open on the screen")
        time.sleep(0.2)


def peek(ezcd: Ezcd, click: Callable[[], object]) -> Menu | None:
    """Opens a menu by the click, reads its items and closes it; ``None`` if no menu opened."""
    leave_foreground(ezcd)
    found: list[int] = []

    def callback(_hook, _event, hwnd, _object, _child, _thread, _time):
        menu = win.send(hwnd, _MN_GETHMENU)
        if menu and not found:
            found.extend(
                win.user32.GetMenuItemID(menu, i) for i in range(max(win.user32.GetMenuItemCount(menu), 0))
            )

    procedure = _Proc(callback)
    hook = win.user32.SetWinEventHook(
        _EVENT_SYSTEM_MENUPOPUPSTART,
        _EVENT_SYSTEM_MENUPOPUPSTART,
        None,
        procedure,
        ezcd.process_id,
        0,
        _WINEVENT_OUTOFCONTEXT,
    )
    owner = 0
    try:
        click()
        end = time.monotonic() + _OPEN_TIMEOUT
        while not found and time.monotonic() < end:
            _pump(_POLL)
        owner = win.gui_info(ezcd.thread_id).hwndMenuOwner or 0
    finally:
        win.user32.UnhookWinEvent(hook)
        close(ezcd, owner)
    return Menu(tuple(found), owner) if found and owner else None


def close(ezcd: Ezcd, owner: int):
    """Closes ezcd's open menu without choosing anything."""
    if owner:
        win.send(owner, _WM_CANCELMODE)
    end = time.monotonic() + _CLOSE_TIMEOUT
    while _in_menu(ezcd) and time.monotonic() < end:
        time.sleep(_POLL)
