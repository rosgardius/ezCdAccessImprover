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
# A control below a row may overlap it by a pixel or two.
_ROW_OVERLAP = 2


def parent(hwnd: int) -> int:
    return winUser.getAncestor(hwnd, winUser.GA_PARENT)


def root(hwnd: int) -> int:
    return winUser.getAncestor(hwnd, winUser.GA_ROOT)


def form_of(hwnd: int, classes: frozenset[str]) -> int:
    """The form of one of the classes holding the window, 0 if the window is not inside one."""
    form = root(hwnd)
    return form if form != hwnd and winUser.getClassName(form) in classes else 0


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


def tab_stop_rows(hwnd: int) -> list[list[int]]:
    """The Tab stops inside the window by rows of the screen, top to bottom, each row from left to right."""
    stops = _tab_stops(hwnd)
    rows: list[list[int]] = []
    row_bottom = 0
    for child in sorted(stops, key=lambda c: stops[c].top + stops[c].bottom):
        edge = stops[child]
        # A control is on the row whose first control its middle lies beside.
        if rows and (edge.top + edge.bottom) // 2 < row_bottom:
            rows[-1].append(child)
        else:
            rows.append([child])
            row_bottom = edge.bottom
    return [sorted(row, key=lambda c: stops[c].left) for row in rows]


def _tab_stops(hwnd: int) -> dict[int, RECT]:
    return {window: rect(window) for window in descendants(hwnd) if is_tab_stop(window)}


def tab_stop_right(hwnd: int, edge: RECT) -> int:
    """The Tab stop inside the window nearest right of the rectangle on its line, 0 if none."""
    right = {
        window: other.left
        for window, other in _tab_stops(hwnd).items()
        if other.left >= edge.right and other.top < edge.bottom and edge.top < other.bottom
    }
    return min(right, key=right.get, default=0)


def tab_stop_below(hwnd: int, edge: RECT) -> int:
    """The Tab stop inside the window nearest below the rectangle, the leftmost of those at the same
    height; 0 if none."""
    below = {
        window: (other.top, other.left)
        for window, other in _tab_stops(hwnd).items()
        if other.top >= edge.bottom - _ROW_OVERLAP and other.left < edge.right and edge.left < other.right
    }
    return min(below, key=below.get, default=0)
