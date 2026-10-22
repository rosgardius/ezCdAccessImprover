# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The toolbar of the drive's tray on the Audio CD Ripper and Disc Burner tabs.

It ends the row of the drive and its speed. It is a Tab stop right before the Tab stop right of it on the
screen, else the one below it: Options on the Disc Burner tab, the list of tracks on the Audio CD Ripper
tab; without either, at the end of the tab (``tab_end``). Without a drive, ezcd disables both lists and
the buttons; Tab skips the lists, but not the stop.
"""

from collections.abc import Hashable
from dataclasses import dataclass

import winUser

from . import panels, toolbar_stops
from .language import LanguageFiles
from .top_panel import main_tab
from .windows import descendants, parent, rect, tab_stop_below, tab_stop_right

# ezcd's strings for the buttons, by image.
_NAMES = {
    8: 191,  # Open tray
    7: 192,  # Close tray, hidden
    9: 434,  # Drive settings: a gear without a hint, on the Audio CD Ripper tab only
}


@dataclass(frozen=True)
class TrayToolbar(toolbar_stops.ToolbarStop):
    tab: str
    """The caption of the main window's tab: VCL reorders the tabs' windows as they are switched."""

    @property
    def key(self) -> Hashable:
        return self.tab

    def overlay_class(self, button: toolbar_stops.StopButton | None) -> type:
        return TrayToolbarWindow if button is None else TrayButton


def is_tray(hwnd: int) -> bool:
    return (
        winUser.getClassName(hwnd) == "TToolBar"
        and winUser.isWindowVisible(hwnd)
        and panels.is_drive_panel(parent(hwnd))
    )


def stop_of(hwnd: int, process_handle: int, language: LanguageFiles) -> TrayToolbar | None:
    """The tray's toolbar, if the window is it."""
    tab = main_tab(hwnd) if is_tray(hwnd) else 0
    buttons = toolbar_stops.read_buttons([hwnd], process_handle) if tab else ()
    return TrayToolbar(buttons, winUser.getWindowText(tab)) if buttons else None


def next_control(hwnd: int) -> int:
    """The control after the tray's stop in the Tab order: the Tab stop right of it or below it."""
    tab = main_tab(hwnd)
    if not tab:
        return 0
    edge = rect(hwnd)
    return tab_stop_right(tab, edge) or tab_stop_below(tab, edge)


def toolbar_passed(window: int, previous: int, forward: bool) -> int:
    """The tray's toolbar if Tab or Shift+Tab from ``previous`` to ``window`` passed by its stop."""
    after = window if forward else previous
    tab = main_tab(after)
    tray = next((w for w in descendants(tab) if is_tray(w)), 0) if tab else 0
    return tray if tray and tray not in (window, previous) and next_control(tray) == after else 0


class TrayToolbarWindow(toolbar_stops.ToolbarWindow):
    find_stop = staticmethod(stop_of)


class TrayButton(toolbar_stops.ButtonBeforeControl):
    find_stop = staticmethod(stop_of)
    next_control = staticmethod(next_control)
    image_names = _NAMES
