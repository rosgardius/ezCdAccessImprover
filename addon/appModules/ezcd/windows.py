# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Walking ezcd's window tree."""

import ctypes
from collections.abc import Callable, Hashable, Iterator
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


def top_level_windows(process_id: int, class_name: str) -> list[int]:
    """The process's top-level windows of the class, in z-order."""
    return [
        w
        for w in child_windows(winUser.getDesktopWindow(), class_name)
        if winUser.getWindowThreadProcessID(w)[0] == process_id
    ]


def descendants(hwnd: int) -> Iterator[int]:
    """All windows inside the window, each followed by its own."""
    for child in child_windows(hwnd):
        yield child
        yield from descendants(child)


def rows[T: Hashable](controls: list[T], edge_of: Callable[[T], RECT] = rect) -> list[list[T]]:
    """The controls, windows by default, by rows of the screen, top to bottom, each row from left to
    right."""
    edges = {control: edge_of(control) for control in controls}
    found: list[list[T]] = []
    row_bottom = 0
    for control in sorted(edges, key=lambda c: edges[c].top + edges[c].bottom):
        edge = edges[control]
        # A control is on the row whose first control its middle lies beside.
        if found and (edge.top + edge.bottom) // 2 < row_bottom:
            found[-1].append(control)
        else:
            found.append([control])
            row_bottom = edge.bottom
    return [sorted(row, key=lambda c: edges[c].left) for row in found]


def tab_stop_rows(hwnd: int) -> list[list[int]]:
    """The Tab stops inside the window by rows of the screen, top to bottom, each row from left to right."""
    return rows(list(_tab_stops(hwnd)))


def _tab_stops(hwnd: int, outside: int = 0) -> dict[int, RECT]:
    """The Tab stops inside the window, without those inside ``outside``."""
    return {
        window: rect(window)
        for window in descendants(hwnd)
        if is_tab_stop(window) and not (outside and winUser.isDescendantWindow(outside, window))
    }


def tab_stop_right(hwnd: int, edge: RECT, outside: int = 0) -> int:
    """The Tab stop inside the window nearest right of the rectangle on its line, 0 if none; none inside
    ``outside``."""
    right = {
        window: other.left
        for window, other in _tab_stops(hwnd, outside).items()
        if other.left >= edge.right and other.top < edge.bottom and edge.top < other.bottom
    }
    return min(right, key=right.get, default=0)


def tab_stop_below(hwnd: int, edge: RECT, outside: int = 0) -> int:
    """The Tab stop inside the window nearest below the rectangle, the leftmost of those at the same
    height; 0 if none; none inside ``outside``."""
    below = {
        window: (other.top, other.left)
        for window, other in _tab_stops(hwnd, outside).items()
        if other.top >= edge.bottom - _ROW_OVERLAP and other.left < edge.right and edge.left < other.right
    }
    return min(below, key=below.get, default=0)
