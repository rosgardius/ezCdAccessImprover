# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Walking ezcd's window tree."""

from collections.abc import Iterator

import winUser

_GW_CHILD = 5


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
