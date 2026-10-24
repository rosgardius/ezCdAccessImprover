# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The file explorer on the Audio Converter and Disc Burner tabs.

Above the explorer, each toolbar is a Tab stop right before the control right of it on the screen: the
navigation before the breadcrumb bar, the view of the list before the filter of file types, or at the end
of the tab while ezcd hides the filter (``tab_end``). While the explorer is hidden, a row of toolbars
takes its place (View Explorer, Add files, ...): one Tab stop right before the control below it.

The breadcrumb bar is the path of the folder, edited in a field that ezcd shows on a click into the bar.
A click into the arrow of a crumb shows a popup list of the folders in it.

View > Folder tree off makes the tree zero wide, but it stays a Tab stop; Tab and Shift+Tab go on past
it.
"""

import builtins
import time
from collections.abc import Hashable
from dataclasses import dataclass

import api
import controlTypes
import core
import ui
import winUser
from NVDAObjects.IAccessible import IAccessible
from NVDAObjects.IAccessible.sysListView32 import LVM_GETITEMCOUNT, LVM_GETNEXTITEM
from scriptHandler import script

from . import captions, list_items, names, panels, remote, screen, toolbar, toolbar_stops
from .language import LanguageFiles, OwnString
from .top_panel import main_tab
from .windows import child_windows, descendants, parent, rect, tab_stop_below

_PATH = OwnString("path")

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


def is_hidden_explorer_row(panel: int) -> bool:
    """Whether the panel is the row of toolbars shown while the explorer is hidden.

    It holds only toolbars and takes the place of the row above the explorer, its sibling. The top panel
    of the Disc Burner tab, too, holds only toolbars and is a sibling of that row, but lies above it.
    """
    children = child_windows(panel)
    if (
        winUser.getClassName(panel) != "TPanel"
        or not children
        or any(winUser.getClassName(c) != "TToolBar" for c in children)
    ):
        return False
    top = rect(panel).top
    return any(
        p != panel and panels.is_explorer_bar(p) and rect(p).top <= top
        for p in child_windows(parent(panel), "TPanel")
    )


def stop_toolbars(hwnd: int) -> tuple[list[int], bool]:
    """The toolbars of the stop the toolbar is on, and whether they are the row of the hidden explorer."""
    if winUser.getClassName(hwnd) != "TToolBar" or not winUser.isWindowVisible(hwnd):
        return [], False
    row = parent(hwnd)
    if panels.is_explorer_bar(row):
        return [hwnd], False
    if is_hidden_explorer_row(row):
        return _shown_toolbars(row), True
    return [], False


def stop_of(hwnd: int, process_handle: int, language: LanguageFiles) -> ExplorerToolbar | None:
    """The explorer toolbar or the row of the hidden explorer, if the window is a toolbar of either."""
    toolbars, row = stop_toolbars(hwnd)
    tab = main_tab(hwnd) if toolbars else 0
    buttons = toolbar_stops.read_buttons(toolbars, process_handle) if tab else ()
    return ExplorerToolbar(buttons, winUser.getWindowText(tab), row) if buttons else None


def is_hidden_tree(hwnd: int) -> bool:
    """Whether the window is the folder tree that View > Folder tree hides."""
    edge = rect(hwnd)
    return winUser.getClassName(hwnd) == "TJamShellTree" and edge.right <= edge.left


def _first_below(panel: int) -> int:
    """The Tab stop of the tab nearest below the panel."""
    tab = main_tab(panel)
    return tab_stop_below(tab, rect(panel)) if tab else 0


def next_control(hwnd: int) -> int:
    """The control after the toolbar's stop in the Tab order: the Tab stop right of it or below its row."""
    row = parent(hwnd)
    if panels.is_explorer_bar(row):
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
    if panels.is_explorer_bar(row):
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
        return controlTypes.Role.TOGGLEBUTTON if self._is_toggle() else super().role

    def _get_states(self):
        states = super()._get_states()
        if self._is_toggle():
            # Pressed while the explorer is shown: ezcd does not always press the button again when the
            # button in the explorer's place shows it.
            states.discard(controlTypes.State.PRESSED)
            if panels.is_explorer_bar(parent(self.windowHandle)):
                states.add(controlTypes.State.PRESSED)
        return states

    def doAction(self, index=None):
        if not index and self._is_toggle():
            # ezcd hides the button with the focus: focus goes on to View Explorer in the other place.
            self.appModule.explorer_toggled(self.windowHandle)
        super().doAction(index)


class ExplorerMenuButton(toolbar_stops.ToolbarMenuButton, ExplorerButton):
    """The view of the list: a button whose drop-down arrow opens the menu, while the button does nothing."""

    def _click(self) -> bool:
        return toolbar.click(self.windowHandle, self.processHandle, self.button_index, arrow=True)


# Milliseconds from the new path of the breadcrumb bar to the list of the new folder.
_FOLDER_FILL_DELAY = 150
# Seconds from Enter in the field of the path to the moment that ezcd would have left it for the folder.
_PATH_ENTER_TIME = 0.5
_MAX_PATH_LENGTH = 32767
_LVNI_FOCUSED = 0x1
CRUMB_LIST_CLASSES = ("TJamShellPopupMenu", "TJamShellOverflowListView")


def _item_count(folder_list: int) -> str:
    count = remote.send(folder_list, LVM_GETITEMCOUNT)
    # NVDA's own translations, which it installs as builtins.
    return builtins.ngettext("%s item", "%s items", count) % count if count else builtins._("blank")


def _last_crumb(bar: int, binding_handle, repaint: bool = False) -> str:
    """The current folder as the breadcrumb bar draws it; empty if the display model has nothing."""
    if repaint:
        screen.redraw(bar)
    found = screen.texts(bar, binding_handle)
    if not found and not repaint and screen.redraw(bar):
        found = screen.texts(bar, binding_handle)
    return max(found, key=lambda t: t.left).text if found else ""


def _folder(bar: int, binding_handle, process_handle: int, repaint: bool = False) -> str:
    """The current folder as the breadcrumb bar draws it, in full; empty if neither the display model nor
    the tree has it.

    A narrow bar cuts the last crumb. ezcd selects the folder it goes to in the tree of the explorer, which
    has it in full, also while View hides the tree.
    """
    crumb = _last_crumb(bar, binding_handle, repaint)
    tab = main_tab(bar)
    tree = next((w for w in descendants(tab) if winUser.getClassName(w) == "TJamShellTree"), 0) if tab else 0
    node = remote.next_node(tree, remote.TVGN_CARET) if tree else 0
    selected = remote.node_text(tree, process_handle, node) if node else ""
    return selected if selected and selected.startswith(crumb) else crumb


def is_folder_list_focus(bar: int) -> bool:
    """Whether the focus is in the list of the folder whose path the breadcrumb bar shows."""
    focus = api.getFocusObject()
    return focus.windowClassName == "TJamShellList" and main_tab(focus.windowHandle) == main_tab(bar)


def announce_folder(bar: int, binding_handle, process_handle: int):
    """Reports the folder that the list in focus went to and the number of its items, once ezcd has
    filled the list."""

    def announce():
        if is_folder_list_focus(bar):
            folder_list = api.getFocusObject().windowHandle
            ui.message(
                f"{_folder(bar, binding_handle, process_handle, repaint=True)}, {_item_count(folder_list)}"
            )

    core.callLater(_FOLDER_FILL_DELAY, announce)


class FolderList(names.Captioned):
    """The list of the folder's files and folders. Without a focused item, its value is the number of
    items: NVDA reports the list itself then."""

    def _get_value(self):
        return _item_count(self.windowHandle)


def is_path_field(hwnd: int) -> bool:
    """Whether the window is the combo box of the path or its edit, shown while the breadcrumb bar is
    edited."""
    return "TBreadCrumbComboBox" in (
        winUser.getClassName(parent(hwnd)),
        winUser.getClassName(parent(parent(hwnd))),
    )


class _Path(IAccessible):
    """The breadcrumb bar or the field of the path, both named Path."""

    def _get_name(self):
        return self.appModule.language.own_string(self.windowHandle, _PATH)


class PathBar(_Path):
    """The breadcrumb bar, presented as a button named Path whose value is the folder: pressing it shows
    the field of the path."""

    role = controlTypes.Role.BUTTON

    def _get_value(self):
        # A folder without a path, as This PC, is only drawn as the last crumb.
        return winUser.getWindowText(self.windowHandle) or _folder(
            self.windowHandle, self.appModule.helperLocalBindingHandle, self.processHandle
        )

    def doAction(self, index=None):
        # The empty space left of the drop-down arrow at the right end.
        client = winUser.getClientRect(self.windowHandle)
        x = client.right - 2 * client.bottom
        if index or not remote.post_click(self.windowHandle, x, client.bottom // 2):
            raise NotImplementedError

    @script(gestures=("kb:enter", "kb:numpadEnter", "kb:space"))
    def script_edit(self, gesture):
        try:
            self.doAction()
        except NotImplementedError:
            gesture.send()

    @script(gestures=("kb:upArrow", "kb:downArrow", "kb:leftArrow", "kb:rightArrow"))
    def script_stay(self, gesture):
        # VCL would move focus to the next or previous window of the bar's parent.
        pass


def is_crumb_popup(hwnd: int) -> bool:
    """Whether the window is the popup form of the breadcrumb bar, which ezcd shows on a click into the
    arrow of a crumb."""
    return winUser.getClassName(hwnd) == "TForm" and bool(child_windows(hwnd, "TJamShellPopupMenu"))


class CrumbPopup(IAccessible):
    """The popup form of the breadcrumb bar: only its list is reported. The form gets focus right before
    its list."""

    isPresentableFocusAncestor = False
    shouldAllowIAccessibleFocusEvent = False


class CrumbList(IAccessible):
    """A list of the breadcrumb bar's popup form: the folders in a crumb, or the crumbs the bar has no
    room for. It opens without a focused item; the first one gets focus, as in a menu opened from the
    keyboard. Enter goes to the folder, Escape closes the list and focus goes back to the bar."""

    def event_gainFocus(self):
        super().event_gainFocus()
        if remote.send(self.windowHandle, LVM_GETNEXTITEM, -1, _LVNI_FOCUSED) < 0:
            remote.post_press(self.windowHandle, winUser.VK_DOWN)


class CrumbItem(list_items.ListItem):
    """An item of a list of the breadcrumb bar's popup form. Its first column is empty: the folder is in the
    second one, which MSAA gives as the description."""

    def _get_name(self):
        return super().name or super().description

    def _get_description(self):
        return super().description if super().name else None


class PathComboBox(IAccessible):
    """The combo box of the path, presented by its edit alone."""

    isPresentableFocusAncestor = False


class PathEdit(_Path):
    """The field of the path. Enter goes to the path, Escape cancels; ezcd then hides the field and moves
    focus elsewhere in the main window, so focus goes back to the bar.

    For a path it cannot go to, ezcd keeps the field and selects the path typed: the current path, with
    which ezcd opened the field, is reported instead of the selection.
    """

    _entered_at = 0.0
    _opened_path = ""

    def event_gainFocus(self):
        self._opened_path = remote.text(self.windowHandle, _MAX_PATH_LENGTH)
        super().event_gainFocus()

    @property
    def _bar(self) -> int:
        # The edit is in a combo box in the bar's own combo box.
        return parent(parent(parent(self.windowHandle)))

    @script(gesture="kb:escape")
    def script_cancel(self, gesture):
        self.appModule.return_focus(self._bar)
        gesture.send()

    @script(gesture="kb:shift+tab")
    def script_previous_control(self, gesture):
        # ezcd goes back to the bar, while Tab goes on past it: Shift+Tab, too, leaves the bar, for the
        # toolbar right before it.
        toolbars = _toolbars_before(self._bar)
        stop = stop_of(toolbars[0], self.processHandle, self.appModule.language) if toolbars else None
        if stop is None or not toolbar_stops.focus_button(
            self.appModule, stop, stop.entry(self.appModule.remembered_buttons)
        ):
            gesture.send()

    @script(gestures=("kb:enter", "kb:numpadEnter"))
    def script_go(self, gesture):
        self.appModule.return_focus(self._bar)
        self._entered_at = time.monotonic()
        gesture.send()
        core.callLater(int(_PATH_ENTER_TIME * 1000), self._report_kept_path)

    def _report_kept_path(self):
        if api.getFocusObject() is not self or not winUser.isWindowVisible(self.windowHandle):
            return
        self.initAutoSelectDetection()
        ui.message(self._opened_path)

    def event_caret(self):
        if time.monotonic() - self._entered_at < _PATH_ENTER_TIME:
            return
        super().event_caret()
