# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Walking ezcd's window tree."""

import ctypes
from collections.abc import Iterator
from ctypes.wintypes import RECT

import winUser
from winBindings import user32

_GW_CHILD = 5
_WS_TABSTOP = 0x10000


def parent(hwnd: int) -> int:
    return winUser.getAncestor(hwnd, winUser.GA_PARENT)


def root(hwnd: int) -> int:
    return winUser.getAncestor(hwnd, winUser.GA_ROOT)


def rect(hwnd: int) -> RECT:
    """The window's rectangle on the screen, in physical coordinates."""
    result = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(result))
    return result


def is_tab_stop(hwnd: int) -> bool:
    return bool(
        winUser.getWindowStyle(hwnd) & _WS_TABSTOP
        and winUser.isWindowVisible(hwnd)
        and winUser.isWindowEnabled(hwnd)
    )


def child_windows(hwnd: int, class_name: str | None = None) -> list[int]:
    """The direct child windows of the class, or of any class, in z-order."""
    children = []
    child = winUser.getWindow(hwnd, _GW_CHILD)
    while child:
        if class_name is None or winUser.getClassName(child) == class_name:
            children.append(child)
        child = winUser.getWindow(child, winUser.GW_HWNDNEXT)
    return children


def descendants(hwnd: int) -> Iterator[int]:
    """All windows inside the window, each followed by its own."""
    for child in child_windows(hwnd):
        yield child
        yield from descendants(child)
