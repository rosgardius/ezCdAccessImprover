# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Toolbar stops at the end of a tab of the main window.

A stop of the explorer or the tray stands right before the control after it on the screen. One without
such a control stands at the end of its tab instead: after the tab's last control, before its top panel,
in the order of the screen. So it is on the MP3 disc and Data disc pages of the Disc Burner tab, where
ezcd hides the filter of file types and Options.
"""

import winUser

from . import explorer, tray
from .language import LanguageFiles
from .top_panel import main_tab, panel_of
from .windows import descendants, parent, rect


def end_toolbars(tab: int) -> list[int]:
    """A toolbar window of each stop at the end of the tab, in the order of the screen."""
    ends = set()
    for hwnd in descendants(tab):
        if tray.is_tray(hwnd):
            if not tray.next_control(hwnd):
                ends.add(hwnd)
            continue
        toolbars, _row = explorer.stop_toolbars(hwnd)
        if toolbars and not explorer.next_control(hwnd):
            ends.add(toolbars[0])
    return sorted(ends, key=lambda hwnd: (rect(hwnd).top, rect(hwnd).left))


def toolbar_passed(
    window: int, previous: int, forward: bool, process_handle: int, language: LanguageFiles
) -> int:
    """The toolbar of the stop at the end of the tab that Tab or Shift+Tab from ``previous`` to ``window``
    passed by: Tab from the tab's last control to the tab labels passes the first stop, Shift+Tab from the
    top panel to the last control the last stop."""
    if forward:
        tab = main_tab(previous)
        # The stops and the top panel leave by the add-on's own Tab.
        if not tab or parent(tab) != window or winUser.getClassName(previous) == "TToolBar":
            return 0
    else:
        tab = main_tab(window)
        if not tab or main_tab(previous) != tab or panel_of(previous, process_handle, language) is None:
            return 0
    ends = end_toolbars(tab)
    if not ends:
        return 0
    return ends[0] if forward else ends[-1]


def neighbour(toolbar_hwnd: int, forward: bool) -> int:
    """The window after or before the stop of the toolbar at the end of its tab: the toolbar of the next or
    previous stop there, or the tab labels; 0 if the stop is not at the end of its tab."""
    tab = main_tab(toolbar_hwnd)
    ends = end_toolbars(tab) if tab else []
    toolbars = explorer.stop_toolbars(toolbar_hwnd)[0] or [toolbar_hwnd]
    index = next((i for i, hwnd in enumerate(ends) if hwnd in toolbars), None)
    if index is None:
        return 0
    index += 1 if forward else -1
    return ends[index] if 0 <= index < len(ends) else parent(tab)
