# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The top panel of the main window's tabs: a row of toolbars, most of them with a single button.

The panel is one Tab stop, between the last control of its tab and the tab labels.
"""

from dataclasses import dataclass

import controlTypes
import winUser
from logHandler import log
from NVDAObjects.IAccessible import IAccessible
from scriptHandler import script

from . import toolbar, toolbar_stops
from .language import LanguageFiles
from .toolbar_stops import StopButton
from .windows import child_windows

TOOLBAR_CLASS = "TToolBar"
PAGE_CONTROL_CLASS = "TPageControl"
TAB_CLASS = "TTabSheet"
PANEL_CLASS = "TPanel"
MAIN_WINDOW_CLASS = "TMainform"

# The tab's main action, recognised by the ImageIndex of its button and its caption in the language file,
# and whether F8 presses it.
_MAIN_BUTTONS = (
    ((1,), (232, 406), True),  # Audio Converter: "Convert"
    ((0,), (176,), True),  # Audio CD Ripper: "Rip CD"
    ((13, 14), (239, 391, 392), False),  # Disc Burner: "Burn CD", "Burn DVD", "Burn disc"
)
# The Disc Burner's main button has image 13 on the Audio CD page and 14 on the others; one button for keys.
_SAME_IMAGES = {14: 13}
# Buttons that open a menu, by ``TopPanel.key``.
_MENU_BUTTONS = {
    1: frozenset(((0, 0), (4, 0), (15, 0), (19, 0))),  # Audio Converter ▼, Metadata ▼, View, Help
    0: frozenset(((1, 0), (3, 0), (4, 0), (15, 0), (19, 0))),  # CD Ripper ▼, Disc ▼, Metadata ▼, View, Help
    13: frozenset(((2, 0), (15, 0), (19, 0))),  # Disc Burner ▼ (Settings is (2, 1)), View, Help
}


@dataclass(frozen=True)
class TopPanel(toolbar_stops.ToolbarStop):
    """The shown buttons, from left to right, the first one switching the tab."""

    main: StopButton
    """The tab's main action."""
    main_shortcut: bool
    """Whether F8 presses the main action."""

    @property
    def key(self) -> int:
        """Tells the panels apart: the image of the main button."""
        return _image_key(self.main.button.image)

    def has_menu(self, button: StopButton) -> bool:
        return button.key in _MENU_BUTTONS.get(self.key, ())


def _image_key(image: int) -> int:
    return _SAME_IMAGES.get(image, image)


def _parent(hwnd: int) -> int:
    return winUser.getAncestor(hwnd, winUser.GA_PARENT)


def _main_shortcut(button: toolbar.ToolButton, language: LanguageFiles) -> bool | None:
    """Whether F8 presses the button if it is the main action, ``None`` if it is not."""
    return next(
        (
            shortcut
            for images, numbers, shortcut in _MAIN_BUTTONS
            if button.image in images and button.text.strip() in language.texts(*numbers)
        ),
        None,
    )


def _read_panel(panel: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    toolbars = [hwnd for hwnd in child_windows(panel, TOOLBAR_CLASS) if winUser.isWindowVisible(hwnd)]
    try:
        buttons = toolbar_stops.read_buttons(toolbars, process_handle, _image_key)
    except OSError:
        log.debugWarning("Cannot read toolbar buttons of ezcd", exc_info=True)
        return None
    for candidate in buttons:
        # The main action has a toolbar of its own.
        if sum(b.toolbar == candidate.toolbar for b in buttons) != 1:
            continue
        shortcut = _main_shortcut(candidate.button, language)
        if shortcut is not None:
            return TopPanel(buttons, candidate, shortcut)
    return None


def read_top_panel(panel: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    """The top panel, if the panel window is one."""
    if winUser.getClassName(panel) != PANEL_CLASS or winUser.getClassName(_parent(panel)) != TAB_CLASS:
        return None
    return _read_panel(panel, process_handle, language)


def panel_of(hwnd: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    """The top panel that the toolbar window is on."""
    found = read_top_panel(_parent(hwnd), process_handle, language)
    return found if found is not None and any(b.toolbar == hwnd for b in found.buttons) else None


def panel_of_tab(tab: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    for panel in child_windows(tab, PANEL_CLASS):
        found = _read_panel(panel, process_handle, language)
        if found is not None:
            return found
    return None


def is_main_window_tab(hwnd: int) -> bool:
    return winUser.getClassName(_parent(_parent(hwnd))) == MAIN_WINDOW_CLASS


def active_tab(page_control: int) -> int | None:
    return next((tab for tab in child_windows(page_control, TAB_CLASS) if winUser.isWindowVisible(tab)), None)


def panel_left_by_tab(
    page_control: int, previous_focus: int, process_handle: int, language: LanguageFiles
) -> TopPanel | None:
    """The tab's top panel, if Tab from ``previous_focus`` left the tab's other controls for its labels."""
    # isDescendantWindow is true for the window itself.
    if previous_focus == page_control or not winUser.isDescendantWindow(page_control, previous_focus):
        return None
    tab = previous_focus
    while (parent := _parent(tab)) != page_control:
        tab = parent
    if winUser.getClassName(tab) != TAB_CLASS:
        return None
    found = panel_of_tab(tab, process_handle, language)
    if found is None or winUser.isDescendantWindow(_parent(found.main.toolbar), previous_focus):
        return None
    return found


def panel_after_tab_menu(old_tab: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    """The top panel of the tab active after the tab menu was opened on ``old_tab``."""
    tab = active_tab(_parent(old_tab))
    return None if tab is None else panel_of_tab(tab, process_handle, language)


def is_beside_panel(panel: TopPanel, hwnd: int) -> bool:
    """Whether the window is in the panel's tab, but is neither the tab nor on the way to its first button."""
    first = panel.buttons[0].toolbar
    tab = _parent(_parent(first))
    # isDescendantWindow is true for the window itself.
    return (
        hwnd != tab and winUser.isDescendantWindow(tab, hwnd) and not winUser.isDescendantWindow(hwnd, first)
    )


class TopPanelWindow(IAccessible):
    """The panel itself, an unnamed pane: presented as a toolbar, so its buttons are known to be a group."""

    def _get_role(self):
        return controlTypes.Role.TOOLBAR


class TopPanelToolbarWindow(toolbar_stops.ToolbarWindow):
    """A toolbar window of the panel."""

    find_stop = staticmethod(panel_of)
    # Its name is a design-time caption such as "ToolBar9".
    isPresentableFocusAncestor = False


class TopPanelButton(toolbar_stops.ToolbarButton):
    """A button of a top panel toolbar."""

    find_stop = staticmethod(panel_of)


class MainButton(TopPanelButton):
    """Convert or Rip CD, pressed by F8 anywhere in the main window."""

    def _get_keyboardShortcut(self):
        return "F8"


class MenuButton(toolbar_stops.ToolbarMenuButton, TopPanelButton):
    """A button that opens a menu: on the press of the mouse, so a posted click opens it too."""

    def doAction(self, index=None):
        panel, button = self._find()
        if not index and panel is not None and button == panel.buttons[0]:
            # The menu of the first button switches the tab: focus goes to the new tab's first button.
            self.appModule.tab_menu_opened(_parent(_parent(self.windowHandle)))
        super().doAction(index)


class TabLabels(IAccessible):
    """The tab labels of the main window: Shift+Tab goes back to the tab's top panel."""

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
