# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The top panel of the main window's tabs: a row of toolbars, most of them with a single button.

The panel is one Tab stop, between the last control of its tab and the tab labels.
"""

from dataclasses import dataclass

import controlTypes
import winUser
from NVDAObjects.IAccessible import IAccessible
from scriptHandler import script

from . import toolbar, toolbar_stops, version
from .facts import groups
from .language import LanguageFiles
from .toolbar_stops import StopButton
from .windows import child_windows, parent


@dataclass(frozen=True)
class TopPanel(toolbar_stops.ToolbarStop):
    """The shown buttons, from left to right, the first one switching the tab."""

    main: StopButton
    """The tab's main action."""
    known: groups.TopPanel
    """What the set of facts tells of the panel."""

    @property
    def key(self) -> int:
        """Tells the panels apart: the image of the main button."""
        return self.known.main_images[0]

    def has_menu(self, button: StopButton) -> bool:
        return button.key in self.known.menu_buttons

    def overlay_class(self, button: StopButton | None) -> type:
        if button is None:
            return TopPanelToolbarWindow
        if button == self.main and self.known.main_shortcut:
            return MainButton
        if self.has_menu(button):
            return MenuButton
        if button.key in self.known.context_menu_buttons:
            return ContextMenuButton
        return TopPanelButton


def _image_key(image: int) -> int:
    """The image by which the buttons of a top panel are told apart: one for all images of a main button."""
    return next((p.main_images[0] for p in version.facts.top_panels if image in p.main_images), image)


def is_main_tab_labels(hwnd: int) -> bool:
    """Whether the window is the page control of the main window's tabs."""
    return winUser.getClassName(hwnd) == "TPageControl" and winUser.getClassName(parent(hwnd)) == "TMainform"


def is_main_window_tab(hwnd: int) -> bool:
    return winUser.getClassName(hwnd) == "TTabSheet" and is_main_tab_labels(parent(hwnd))


def main_tab(hwnd: int) -> int:
    """The main window's tab that holds the window, or is the window; 0 if none."""
    while hwnd and not is_main_window_tab(hwnd):
        hwnd = parent(hwnd)
    return hwnd


def _known_panel(button: toolbar.ToolButton, language: LanguageFiles) -> groups.TopPanel | None:
    """The top panel whose main action the button is, recognised by its image and its caption; ``None`` if
    it is no main action."""
    return next(
        (
            panel
            for panel in version.facts.top_panels
            if button.image in panel.main_images
            and button.text.strip() in language.texts(*panel.main_strings)
        ),
        None,
    )


def _read_panel(panel: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    toolbars = [hwnd for hwnd in child_windows(panel, "TToolBar") if winUser.isWindowVisible(hwnd)]
    buttons = toolbar_stops.read_buttons(toolbars, process_handle, _image_key)
    for candidate in buttons:
        # The main action has a toolbar of its own.
        if sum(b.toolbar == candidate.toolbar for b in buttons) != 1:
            continue
        known = _known_panel(candidate.button, language)
        if known is not None:
            return TopPanel(buttons, candidate, known)
    return None


def read_top_panel(panel: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    """The top panel, if the panel window is one."""
    if winUser.getClassName(panel) != "TPanel" or winUser.getClassName(parent(panel)) != "TTabSheet":
        return None
    return _read_panel(panel, process_handle, language)


def panel_of(hwnd: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    """The top panel that the toolbar window is on."""
    found = read_top_panel(parent(hwnd), process_handle, language)
    return found if found is not None and any(b.toolbar == hwnd for b in found.buttons) else None


def panel_of_tab(tab: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    for panel in child_windows(tab, "TPanel"):
        found = _read_panel(panel, process_handle, language)
        if found is not None:
            return found
    return None


def active_tab(page_control: int) -> int | None:
    return next(
        (tab for tab in child_windows(page_control, "TTabSheet") if winUser.isWindowVisible(tab)), None
    )


def panel_left_by_tab(
    page_control: int, previous_focus: int, process_handle: int, language: LanguageFiles
) -> TopPanel | None:
    """The tab's top panel, if Tab from ``previous_focus`` left the tab's other controls for its labels."""
    tab = main_tab(previous_focus)
    if not tab or parent(tab) != page_control:
        return None
    found = panel_of_tab(tab, process_handle, language)
    # isDescendantWindow is true for the window itself.
    if found is None or winUser.isDescendantWindow(parent(found.main.toolbar), previous_focus):
        return None
    return found


def panel_after_tab_menu(old_tab: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    """The top panel of the tab active after the tab menu was opened on ``old_tab``."""
    tab = active_tab(parent(old_tab))
    return None if tab is None else panel_of_tab(tab, process_handle, language)


def is_beside_panel(panel: TopPanel, hwnd: int) -> bool:
    """Whether the window is in the panel's tab, but is neither the tab nor on the way to its first button."""
    first = panel.buttons[0].toolbar
    tab = parent(parent(first))
    # isDescendantWindow is true for the window itself.
    return (
        hwnd != tab and winUser.isDescendantWindow(tab, hwnd) and not winUser.isDescendantWindow(hwnd, first)
    )


class TopPanelWindow(IAccessible):
    """The panel itself, an unnamed pane: presented as a toolbar, so its buttons are known to be a group."""

    role = controlTypes.Role.TOOLBAR


class TopPanelToolbarWindow(toolbar_stops.ToolbarWindow):
    """A toolbar window of the panel."""

    find_stop = staticmethod(panel_of)
    # The panel is presented as the toolbar.
    isPresentableFocusAncestor = False


class TopPanelButton(toolbar_stops.ToolbarButton):
    """A button of a top panel toolbar."""

    find_stop = staticmethod(panel_of)


class MainButton(TopPanelButton):
    """Convert or Rip CD, pressed by F8 anywhere in the main window."""

    keyboardShortcut = "F8"


class MenuButton(toolbar_stops.ToolbarMenuButton, TopPanelButton):
    """A button that opens a menu: on the press of the mouse, so a posted click opens it too."""

    def doAction(self, index=None):
        panel, button = self._find()
        if not index and panel is not None and button == panel.buttons[0]:
            # The menu of the first button switches the tab: focus goes to the new tab's first button.
            self.appModule.tab_menu_opened(parent(parent(self.windowHandle)))
        super().doAction(index)


class ContextMenuButton(TopPanelButton):
    """A button with a context menu, opened by Applications or Shift+F10."""

    @script(gestures=("kb:applications", "kb:shift+f10"))
    def script_open_context_menu(self, gesture):
        if not toolbar.open_context_menu(self.windowHandle, self.processHandle, self.button_index):
            gesture.send()


class TabLabels(IAccessible):
    """The tab labels of the main window, a Tab stop without labels or keys of its own: named after the active
    tab, without a role, so it is not taken for tabs to switch. Shift+Tab goes back to the tab's top panel."""

    role = controlTypes.Role.PANE
    # The tab itself is reported with its name.
    isPresentableFocusAncestor = False

    def _get_name(self):
        tab = active_tab(self.windowHandle)
        return "" if tab is None else winUser.getWindowText(tab)

    @script(gesture="kb:shift+tab")
    def script_previous_control(self, gesture):
        tab = active_tab(self.windowHandle)
        panel = None if tab is None else panel_of_tab(tab, self.processHandle, self.appModule.language)
        if panel is None or not toolbar_stops.focus_button(
            self.appModule, panel, panel.entry(self.appModule.remembered_buttons)
        ):
            gesture.send()


class MainWindowTab(IAccessible):
    """A tab of the main window."""

    def _get_description(self):
        # NVDA's Dialog behaviour of a property page collects its text from every panel of the tab,
        # which takes about 250 ms in the main window and finds nothing.
        return IAccessible._get_description(self)
