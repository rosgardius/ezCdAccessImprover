# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The toolbars of the file explorer on the Audio Converter and Disc Burner tabs.

Above the explorer, each toolbar is a Tab stop right before the control right of it on the screen: the
navigation before the breadcrumb bar, the view of the list before the filter of file types. While the
explorer is hidden, a row of toolbars takes its place (View Explorer, Add files, ...): one Tab stop right
before the control below it.
"""

from collections.abc import Hashable
from dataclasses import dataclass

import controlTypes
import winUser
from NVDAObjects.IAccessible import IAccessible

from . import captions, toolbar, toolbar_stops
from .language import LanguageFiles
from .top_panel import main_tab
from .windows import child_windows, descendants, parent, rect, tab_stop_below

# ezcd's strings for the buttons, by image.
_VIEW_EXPLORER = 29
_NAMES = {
    _VIEW_EXPLORER: 704,  # View Explorer: shows and hides the explorer, pressed while it is shown
    33: 327,  # Add files...
    32: 328,  # Add folder...
    25: 489,  # Go to Computer
    26: 490,  # Go to Music
    30: 701,  # Move backward in history
    31: 702,  # Move forward in history
    3: 703,  # Go up
    4: 346,  # View: the menu of the list's view (List, Details, Icons, Large icons)
}


@dataclass(frozen=True)
class ExplorerToolbar(toolbar_stops.ToolbarStop):
    tab: str
    """The caption of the main window's tab: VCL reorders the tabs' windows as they are switched."""
    row: bool
    """Whether it is the row of toolbars shown while the explorer is hidden."""

    @property
    def key(self) -> Hashable:
        return (self.tab, self.row, self.buttons[0].key)

    def overlay_class(self, button: toolbar_stops.StopButton | None) -> type:
        if button is None:
            return ExplorerToolbarWindow
        return ExplorerMenuButton if button.button.dropdown else ExplorerButton


def _shown_toolbars(panel: int) -> list[int]:
    return [t for t in child_windows(panel, "TToolBar") if winUser.isWindowVisible(t)]


def _is_bar_row(panel: int) -> bool:
    """Whether the panel is the row above the explorer, with the breadcrumb bar."""
    return bool(child_windows(panel, "TJamShellBreadCrumbBar"))


def is_hidden_explorer_row(panel: int) -> bool:
    """Whether the panel is the row of toolbars shown while the explorer is hidden.

    It holds only toolbars and lies next to the row above the explorer.
    """
    children = child_windows(panel)
    return (
        winUser.getClassName(panel) == "TPanel"
        and bool(children)
        and all(winUser.getClassName(c) == "TToolBar" for c in children)
        and any(p != panel and _is_bar_row(p) for p in child_windows(parent(panel), "TPanel"))
    )


def _stop_toolbars(hwnd: int) -> tuple[list[int], bool]:
    """The toolbars of the stop the toolbar is on, and whether they are the row of the hidden explorer."""
    if winUser.getClassName(hwnd) != "TToolBar" or not winUser.isWindowVisible(hwnd):
        return [], False
    row = parent(hwnd)
    if _is_bar_row(row):
        return [hwnd], False
    if is_hidden_explorer_row(row):
        return _shown_toolbars(row), True
    return [], False


def stop_of(hwnd: int, process_handle: int, language: LanguageFiles) -> ExplorerToolbar | None:
    """The explorer toolbar or the row of the hidden explorer, if the window is a toolbar of either."""
    toolbars, row = _stop_toolbars(hwnd)
    tab = main_tab(hwnd) if toolbars else 0
    buttons = toolbar_stops.read_buttons(toolbars, process_handle) if tab else ()
    return ExplorerToolbar(buttons, winUser.getWindowText(tab), row) if buttons else None


def _first_below(panel: int) -> int:
    """The Tab stop of the tab nearest below the panel."""
    tab = main_tab(panel)
    return tab_stop_below(tab, rect(panel)) if tab else 0


def next_control(hwnd: int) -> int:
    """The control after the toolbar's stop in the Tab order: the Tab stop right of it or below its row."""
    row = parent(hwnd)
    if _is_bar_row(row):
        return captions.Layout(hwnd).right_window(tab_stop=True)
    return _first_below(row)


def _hidden_explorer_row(hwnd: int) -> int:
    """The shown row of the hidden explorer in the window's tab, 0 if none."""
    tab = main_tab(hwnd)
    bars = [w for w in descendants(tab) if winUser.getClassName(w) == "TJamShellBreadCrumbBar"] if tab else []
    for bar in bars:
        for panel in child_windows(parent(parent(bar)), "TPanel"):
            if winUser.isWindowVisible(panel) and is_hidden_explorer_row(panel):
                return panel
    return 0


def _toolbars_before(hwnd: int) -> list[int]:
    """The toolbars of the explorer's stop that comes right before the window in the Tab order."""
    if not hwnd:
        return []
    row = parent(hwnd)
    if _is_bar_row(row):
        return [t for t in _shown_toolbars(row) if next_control(t) == hwnd][:1]
    hidden_row = _hidden_explorer_row(hwnd)
    return _shown_toolbars(hidden_row) if hidden_row and _first_below(hidden_row) == hwnd else []


def toolbar_passed(window: int, previous: int, forward: bool) -> int:
    """A toolbar of the explorer's stop that Tab or Shift+Tab from ``previous`` to ``window`` passed by."""
    toolbars = _toolbars_before(window if forward else previous)
    return toolbars[0] if toolbars and previous not in toolbars and window not in toolbars else 0


def toggle_button(
    hwnd: int, process_handle: int, language: LanguageFiles
) -> tuple[ExplorerToolbar, toolbar_stops.StopButton] | None:
    """View Explorer on the shown stop in the window's tab: above the explorer or in its place."""
    tab = main_tab(hwnd)
    for window in descendants(tab) if tab else ():
        stop = stop_of(window, process_handle, language)
        button = (
            None
            if stop is None
            else next((b for b in stop.buttons if b.button.image == _VIEW_EXPLORER), None)
        )
        if button is not None:
            return stop, button
    return None


class HiddenExplorerRow(IAccessible):
    """The row of the hidden explorer, an unnamed pane: presented as a toolbar, its buttons being a group."""

    role = controlTypes.Role.TOOLBAR


class ExplorerToolbarWindow(toolbar_stops.ToolbarWindow):
    """The toolbar window; in the row of the hidden explorer the row is the toolbar."""

    find_stop = staticmethod(stop_of)

    def _get_isPresentableFocusAncestor(self):
        return not is_hidden_explorer_row(parent(self.windowHandle)) and super().isPresentableFocusAncestor


class ExplorerButton(toolbar_stops.ButtonBeforeControl):
    """A button of an explorer toolbar."""

    find_stop = staticmethod(stop_of)
    next_control = staticmethod(next_control)
    image_names = _NAMES

    def _is_toggle(self) -> bool:
        button = self._tool_button()
        return button is not None and button.image == _VIEW_EXPLORER

    def _get_role(self):
        # The proxy reports the button pressed while the explorer is shown.
        return controlTypes.Role.TOGGLEBUTTON if self._is_toggle() else super().role

    def doAction(self, index=None):
        if not index and self._is_toggle():
            # ezcd hides the button with the focus: focus goes on to View Explorer in the other place.
            self.appModule.explorer_toggled(self.windowHandle)
        super().doAction(index)


class ExplorerMenuButton(toolbar_stops.ToolbarMenuButton, ExplorerButton):
    """The view of the list: a button whose drop-down arrow opens the menu, while the button does nothing."""

    def _click(self) -> bool:
        return toolbar.click(self.windowHandle, self.processHandle, self.button_index, arrow=True)
