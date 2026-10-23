# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Focus coming into a top-level window of ezcd: back where it was, without the chain of its ancestors.

When a dialog closes, ezcd gives focus to the control that opened it and moves it on to the main form; after
the conversion window, to the tab labels. Some dialogs open with focus on a control and move it on to their
form. NVDA would report each of these, and the main window with all its containers on the way.
"""

import time
from dataclasses import dataclass

import winUser

from . import top_panel
from .windows import root

# ezcd moves focus from the control it gave focus to on to the form within this; 10 to 110 ms seen.
_SETTLE_SECONDS = 0.5


@dataclass(frozen=True)
class Return:
    """Where focus goes back to from the form or the tab labels it came to."""

    target: int
    silent: bool
    """Whether NVDA reported the control already: the move is not reported either."""


def _is_usable(window: int, form: int) -> bool:
    return bool(
        window
        and winUser.isDescendantWindow(form, window)
        and winUser.isWindowVisible(window)
        and winUser.isWindowEnabled(window)
    )


class WindowFocus:
    """The focus of each top-level window of ezcd, and how focus came into the current one."""

    def __init__(self):
        self._last: dict[int, int] = {}
        """The last window with focus in each top-level window, other than the form itself."""
        self._entry: tuple[int, float] = (0, 0.0)
        """The window that got focus as it came into its top-level window, and when."""
        self._menu_focus = 0
        """The focus before the menu that has focus now, 0 if no menu has it."""
        self._foreground = 0
        """The main window, from its foreground event until the focus event that brought it."""
        self._quiet: tuple[int, int] | None = None
        """The top-level window whose containers of the focus are not reported, and the focus before the
        menu focus came back from (0 if it came to the main window from another window), until the next
        focus."""

    def note_foreground(self, obj):
        """A top-level window comes to the foreground: from another window of ezcd, another application or a
        menu."""
        form = root(obj.windowHandle)
        menu_focus = self._menu_focus if root(self._menu_focus) == form else 0
        if winUser.getClassName(form) == "TMainform":
            self._foreground = form
        elif not menu_focus:
            return
        self._quiet = (form, menu_focus)

    def is_quiet_ancestor(self, obj) -> bool:
        """Whether NVDA should not report the container of the focus.

        After a menu, those that held the focus before it; after another window, all but the main window
        itself.
        """
        if self._quiet is None:
            return False
        form, menu_focus = self._quiet
        hwnd = obj.windowHandle
        if root(hwnd) != form:
            return False
        if menu_focus:
            return winUser.isDescendantWindow(hwnd, menu_focus)
        return hwnd != form

    def note_focus(self, obj, previous: int) -> Return | None:
        """Notes the focus; where it goes back to, if ezcd moved it on to the form or the tab labels as it
        came into the window. ``previous`` is the focus before."""
        hwnd = obj.windowHandle
        form = root(hwnd)
        foreground, self._foreground = self._foreground, 0
        self._quiet = None
        if obj.windowClassName == "#32768":
            # Focus coming back to a menu from its submenu comes from a window already destroyed.
            if not self._menu_focus:
                self._menu_focus = previous
            return None
        self._menu_focus = 0
        last = self._last.get(form, 0)
        if hwnd != form:
            self._last[form] = hwnd
        entered = foreground == form or root(previous) != form
        if entered:
            self._entry = (hwnd, time.monotonic())
        if last == hwnd or not _is_usable(last, form):
            return None
        if hwnd != form and not top_panel.is_main_tab_labels(hwnd):
            return None
        entry, entered_at = self._entry
        if not entered and last == entry and time.monotonic() - entered_at < _SETTLE_SECONDS:
            return Return(last, True)
        if entered and winUser.getClassName(form) == "TMainform":
            return Return(last, False)
        return None

    def going_back(self, back: Return):
        """Focus goes back: NVDA reported the main window already, its containers are not reported."""
        self._quiet = (root(back.target), 0)
