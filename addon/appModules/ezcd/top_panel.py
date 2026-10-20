# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The top panel of the converter and ripper tabs: a row of single-button toolbars."""

import contextlib
import ctypes
from ctypes.wintypes import RECT
from dataclasses import dataclass

import controlTypes
import winUser
from logHandler import log
from NVDAObjects.IAccessible import IAccessible
from scriptHandler import script
from winBindings import user32

from . import toolbar
from .language import LanguageFiles

TOOLBAR_CLASS = "TToolBar"
PAGE_CONTROL_CLASS = "TPageControl"
TAB_CLASS = "TTabSheet"
PANEL_CLASS = "TPanel"
_MAIN_WINDOW_CLASS = "TMainform"
_GW_CHILD = 5

# The tab's main action, recognised by the ImageIndex of its button and its caption in the language file.
_MAIN_BUTTONS = (
    (1, (232, 406)),  # Audio Converter: "Convert"
    (0, (176,)),  # Audio CD Ripper: "Rip CD"
)
# Images of the buttons that open a menu, by ``TopPanel.key``.
_MENU_BUTTONS = {
    1: frozenset((0, 4, 15, 19)),  # Audio Converter ▼, Metadata ▼, View, Help
    0: frozenset((1, 3, 4, 15, 19)),  # CD Ripper ▼, Disc ▼, Metadata ▼, View, Help
}
_MENU_MARK = "▼"


@dataclass(frozen=True)
class TopPanel:
    buttons: dict[int, toolbar.ToolButton]
    """The button of each single-button toolbar of the panel, by toolbar window."""
    main: int
    """The toolbar window of the main action."""

    @property
    def key(self) -> int:
        """Tells the converter's panel from the ripper's: the image of the main button."""
        return self.buttons[self.main].image

    def has_menu(self, hwnd: int) -> bool:
        return self.buttons[hwnd].image in _MENU_BUTTONS.get(self.key, ())

    def entry(self, remembered: dict[int, int]) -> int:
        """The toolbar to enter the panel at: the remembered button while it is shown, else the main one."""
        image = remembered.get(self.key)
        return next(
            (
                hwnd
                for hwnd, button in self.buttons.items()
                if button.image == image and winUser.isWindowVisible(hwnd)
            ),
            self.main,
        )


def _child_windows(hwnd: int, class_name: str) -> list[int]:
    children = []
    child = winUser.getWindow(hwnd, _GW_CHILD)
    while child:
        if winUser.getClassName(child) == class_name:
            children.append(child)
        child = winUser.getWindow(child, winUser.GW_HWNDNEXT)
    return children


def _parent(hwnd: int) -> int:
    return winUser.getAncestor(hwnd, winUser.GA_PARENT)


def _is_main(button: toolbar.ToolButton, language: LanguageFiles) -> bool:
    return any(
        button.image == image and button.text.strip() in language.texts(*numbers)
        for image, numbers in _MAIN_BUTTONS
    )


def _read_panel(panel: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    buttons = {}
    try:
        for hwnd in _child_windows(panel, TOOLBAR_CLASS):
            toolbar_buttons = toolbar.read_buttons(hwnd, process_handle)
            if len(toolbar_buttons) == 1:
                buttons[hwnd] = toolbar_buttons[0]
    except OSError:
        log.debugWarning("Cannot read toolbar buttons of ezcd", exc_info=True)
        return None
    main = next((hwnd for hwnd, button in buttons.items() if _is_main(button, language)), None)
    return None if main is None else TopPanel(buttons, main)


def read_top_panel(panel: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    """The top panel, if the panel window is one."""
    if winUser.getClassName(panel) != PANEL_CLASS or winUser.getClassName(_parent(panel)) != TAB_CLASS:
        return None
    return _read_panel(panel, process_handle, language)


def panel_of(hwnd: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    """The top panel that the toolbar window is one of the single-button toolbars of."""
    found = read_top_panel(_parent(hwnd), process_handle, language)
    return found if found is not None and hwnd in found.buttons else None


def panel_of_tab(tab: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    for panel in _child_windows(tab, PANEL_CLASS):
        found = _read_panel(panel, process_handle, language)
        if found is not None:
            return found
    return None


def is_main_window_tab(hwnd: int) -> bool:
    return winUser.getClassName(_parent(_parent(hwnd))) == _MAIN_WINDOW_CLASS


def active_tab(page_control: int) -> int | None:
    return next(
        (tab for tab in _child_windows(page_control, TAB_CLASS) if winUser.isWindowVisible(tab)), None
    )


def panel_left_by_tab(
    page_control: int, previous_focus: int, process_handle: int, language: LanguageFiles
) -> TopPanel | None:
    """The tab's top panel, if Tab from ``previous_focus`` left the tab's other controls for its labels."""
    if not winUser.isDescendantWindow(page_control, previous_focus):
        return None
    tab = previous_focus
    while (parent := _parent(tab)) != page_control:
        tab = parent
    if winUser.getClassName(tab) != TAB_CLASS:
        return None
    found = panel_of_tab(tab, process_handle, language)
    if found is None or winUser.isDescendantWindow(_parent(found.main), previous_focus):
        return None
    return found


def _left(hwnd: int) -> int:
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left


def panel_toolbars(hwnd: int) -> list[int]:
    """Visible toolbars of the panel holding the toolbar window, from left to right."""
    toolbars = [t for t in _child_windows(_parent(hwnd), TOOLBAR_CLASS) if winUser.isWindowVisible(t)]
    return sorted(toolbars, key=_left)


class TopPanelWindow(IAccessible):
    """The panel itself, an unnamed pane: presented as a toolbar, so its buttons are known to be a group."""

    def _get_role(self):
        return controlTypes.Role.TOOLBAR


class _SingleButtonToolbar(IAccessible):
    def isDuplicateIAccessibleEvent(self, obj):
        # Focus on the toolbar arrives for the window or its button, and is fired again on entering menu mode
        # (Alt); NVDA never treats an event for a child id as a duplicate.
        return obj.event_windowHandle == self.event_windowHandle and obj.event_objectID == self.event_objectID


class TopPanelToolbarWindow(_SingleButtonToolbar):
    """The toolbar window: focus goes on to its only button."""

    # Its name is a design-time caption such as "ToolBar9".
    isPresentableFocusAncestor = False

    def _get_focusRedirect(self):
        return self.firstChild


class TopPanelButton(_SingleButtonToolbar):
    """The button of a top panel toolbar, exposed by the toolbar's MSAA proxy."""

    @property
    def button_index(self) -> int:
        return self.IAccessibleChildID - 1

    def _get_states(self):
        states = super().states
        try:
            buttons = toolbar.read_buttons(self.windowHandle, self.processHandle)
        except OSError:
            log.debugWarning("Cannot read toolbar button state", exc_info=True)
            return states
        if self.button_index < len(buttons) and not buttons[self.button_index].enabled:
            states.add(controlTypes.State.UNAVAILABLE)
        return states

    def _get_positionInfo(self):
        # The proxy's "1 of 1" is the position within the button's own toolbar.
        return {}

    def event_gainFocus(self):
        panel = panel_of(self.windowHandle, self.processHandle, self.appModule.language)
        if panel is not None:
            self.appModule.remembered_buttons[panel.key] = panel.buttons[self.windowHandle].image
        super().event_gainFocus()

    def setFocus(self):
        if not toolbar.set_focus(self.windowHandle):
            log.debugWarning("ezcd is not responding, focus not moved")

    def doAction(self, index=None):
        if index:
            raise NotImplementedError
        try:
            pressed = toolbar.click(self.windowHandle, self.processHandle, self.button_index)
        except OSError:
            log.debugWarning("Cannot press toolbar button", exc_info=True)
            pressed = False
        if not pressed:
            raise NotImplementedError

    @script(gestures=("kb:enter", "kb:numpadEnter", "kb:space"))
    def script_press(self, gesture):
        try:
            self.doAction()
        except NotImplementedError:
            gesture.send()

    def _move_focus(self, step: int, to_end: bool = False):
        toolbars = panel_toolbars(self.windowHandle)
        if self.windowHandle not in toolbars:
            return
        if to_end:
            index = 0 if step < 0 else len(toolbars) - 1
        else:
            index = min(max(toolbars.index(self.windowHandle) + step, 0), len(toolbars) - 1)
        if toolbars[index] != self.windowHandle and not toolbar.set_focus(toolbars[index]):
            log.debugWarning("ezcd is not responding, focus not moved")

    @script(gesture="kb:leftArrow")
    def script_previous_button(self, gesture):
        self._move_focus(-1)

    @script(gesture="kb:rightArrow")
    def script_next_button(self, gesture):
        self._move_focus(1)

    @script(gesture="kb:home")
    def script_first_button(self, gesture):
        self._move_focus(-1, to_end=True)

    @script(gesture="kb:end")
    def script_last_button(self, gesture):
        self._move_focus(1, to_end=True)

    @script(gestures=("kb:upArrow", "kb:downArrow"))
    def script_stay(self, gesture):
        # VCL would cycle through the panel's toolbars in tab order.
        pass


class MainButton(TopPanelButton):
    """Convert or Rip CD, pressed by F8 anywhere in the main window."""

    def _get_keyboardShortcut(self):
        return "F8"


class MenuButton(TopPanelButton):
    """A button that opens a menu: on the press of the mouse, so a posted click opens it too."""

    def _get_role(self):
        return controlTypes.Role.MENUBUTTON

    def _get_name(self):
        # The role tells about the menu; the caption marks it with a trailing triangle.
        name = super().name
        return name.replace(_MENU_MARK, "").strip() if name else name

    @script(gesture="kb:downArrow")
    def script_open_menu(self, gesture):
        # Unlike Enter, the arrow is not sent on if the click fails: VCL would move focus to another toolbar.
        with contextlib.suppress(NotImplementedError):
            self.doAction()


class TabLabels(IAccessible):
    """The tab labels of the main window: Shift+Tab goes back to the tab's top panel."""

    @script(gesture="kb:shift+tab")
    def script_previous_control(self, gesture):
        tab = active_tab(self.windowHandle)
        panel = None if tab is None else panel_of_tab(tab, self.processHandle, self.appModule.language)
        if panel is None or not toolbar.set_focus(panel.entry(self.appModule.remembered_buttons)):
            gesture.send()


class MainWindowTab(IAccessible):
    """A tab of the main window."""

    def _get_description(self):
        # NVDA's Dialog behaviour of a property page collects its text from every panel of the tab,
        # which takes about 250 ms in the main window and finds nothing.
        return IAccessible._get_description(self)
