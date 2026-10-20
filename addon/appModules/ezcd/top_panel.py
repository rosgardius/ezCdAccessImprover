# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The top panel of the main window's tabs: a row of toolbars, most of them with a single button."""

import contextlib
import ctypes
from ctypes.wintypes import RECT
from dataclasses import dataclass

import api
import controlTypes
import eventHandler
import winUser
from logHandler import log
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent
from scriptHandler import script
from winBindings import user32

from . import toolbar
from .language import LanguageFiles
from .windows import child_windows

TOOLBAR_CLASS = "TToolBar"
PAGE_CONTROL_CLASS = "TPageControl"
TAB_CLASS = "TTabSheet"
PANEL_CLASS = "TPanel"
_MAIN_WINDOW_CLASS = "TMainform"

# The tab's main action, recognised by the ImageIndex of its button and its caption in the language file,
# and whether F8 presses it.
_MAIN_BUTTONS = (
    (1, (232, 406), True),  # Audio Converter: "Convert"
    (0, (176,), True),  # Audio CD Ripper: "Rip CD"
    (13, (392,), False),  # Disc Burner: "Burn disc"
)
# Buttons that open a menu, by ``TopPanel.key``.
_MENU_BUTTONS = {
    1: frozenset(((0, 0), (4, 0), (15, 0), (19, 0))),  # Audio Converter ▼, Metadata ▼, View, Help
    0: frozenset(((1, 0), (3, 0), (4, 0), (15, 0), (19, 0))),  # CD Ripper ▼, Disc ▼, Metadata ▼, View, Help
    13: frozenset(((2, 0), (15, 0), (19, 0))),  # Disc Burner ▼ (Settings is (2, 1)), View, Help
}
_MENU_MARK = "▼"


@dataclass(frozen=True)
class PanelButton:
    toolbar: int
    """The toolbar window holding the button."""
    button: toolbar.ToolButton
    key: tuple[int, int]
    """The image and the number of buttons with the same image to the left: images repeat on a panel."""


@dataclass(frozen=True)
class TopPanel:
    buttons: tuple[PanelButton, ...]
    """The shown buttons, from left to right; the first one switches the tab."""
    main: PanelButton
    """The tab's main action."""
    main_shortcut: bool
    """Whether F8 presses the main action."""

    @property
    def key(self) -> int:
        """Tells the panels apart: the image of the main button."""
        return self.main.button.image

    def find(self, hwnd: int, index: int) -> PanelButton | None:
        return next((b for b in self.buttons if b.toolbar == hwnd and b.button.index == index), None)

    def has_menu(self, button: PanelButton) -> bool:
        return button.key in _MENU_BUTTONS.get(self.key, ())

    def entry(self, remembered: dict[int, tuple[int, int]]) -> PanelButton:
        """The button to enter the panel at: the remembered one while it is shown, else the first one."""
        key = remembered.get(self.key)
        return next((b for b in self.buttons if b.key == key), self.buttons[0])

    def toolbar_entry(self, hwnd: int, remembered: dict[int, tuple[int, int]]) -> PanelButton | None:
        """The button that focus on the toolbar window means: the remembered one if it is there."""
        buttons = [b for b in self.buttons if b.toolbar == hwnd]
        key = remembered.get(self.key)
        return next((b for b in buttons if b.key == key), buttons[0] if buttons else None)


def _parent(hwnd: int) -> int:
    return winUser.getAncestor(hwnd, winUser.GA_PARENT)


def _left(hwnd: int) -> int:
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left


def _main_shortcut(button: toolbar.ToolButton, language: LanguageFiles) -> bool | None:
    """Whether F8 presses the button if it is the main action, ``None`` if it is not."""
    return next(
        (
            shortcut
            for image, numbers, shortcut in _MAIN_BUTTONS
            if button.image == image and button.text.strip() in language.texts(*numbers)
        ),
        None,
    )


def _read_panel(panel: int, process_handle: int, language: LanguageFiles) -> TopPanel | None:
    shown = []
    try:
        for hwnd in child_windows(panel, TOOLBAR_CLASS):
            if winUser.isWindowVisible(hwnd):
                left = _left(hwnd)
                shown += [
                    (left, b.index, hwnd, b)
                    for b in toolbar.read_buttons(hwnd, process_handle)
                    if not b.hidden
                ]
    except OSError:
        log.debugWarning("Cannot read toolbar buttons of ezcd", exc_info=True)
        return None
    buttons = []
    seen: dict[int, int] = {}
    for _left_edge, _index, hwnd, button in sorted(shown, key=lambda item: item[:2]):
        buttons.append(PanelButton(hwnd, button, (button.image, seen.get(button.image, 0))))
        seen[button.image] = seen.get(button.image, 0) + 1
    for candidate in buttons:
        # The main action has a toolbar of its own.
        if sum(b.toolbar == candidate.toolbar for b in buttons) != 1:
            continue
        shortcut = _main_shortcut(candidate.button, language)
        if shortcut is not None:
            return TopPanel(tuple(buttons), candidate, shortcut)
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
    return winUser.getClassName(_parent(_parent(hwnd))) == _MAIN_WINDOW_CLASS


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


def _button_object(button: PanelButton) -> IAccessible | None:
    return getNVDAObjectFromEvent(button.toolbar, winUser.OBJID_CLIENT, button.button.index + 1)


def focus_button(app_module, panel: TopPanel, button: PanelButton, focused_toolbar: int = 0) -> bool:
    """Moves focus to the button; ``focused_toolbar`` is the toolbar window that has focus now."""
    app_module.remembered_buttons[panel.key] = button.key
    if button.toolbar != focused_toolbar:
        # The toolbar window redirects focus to the remembered button.
        return toolbar.set_focus(button.toolbar)
    # VCL's focus stays on the window, the button changes only for NVDA.
    obj = _button_object(button)
    if obj is None:
        return False
    eventHandler.queueEvent("gainFocus", obj)
    return True


class TopPanelWindow(IAccessible):
    """The panel itself, an unnamed pane: presented as a toolbar, so its buttons are known to be a group."""

    def _get_role(self):
        return controlTypes.Role.TOOLBAR


class _PanelToolbar(IAccessible):
    def isDuplicateIAccessibleEvent(self, obj):
        # Focus on the toolbar arrives for the window or its button, and is fired again on entering menu mode
        # (Alt); NVDA never treats an event for a child id as a duplicate.
        return obj.event_windowHandle == self.event_windowHandle and obj.event_objectID == self.event_objectID


class TopPanelToolbarWindow(_PanelToolbar):
    """The toolbar window: focus goes on to its remembered or first button."""

    # Its name is a design-time caption such as "ToolBar9".
    isPresentableFocusAncestor = False

    def _get_focusRedirect(self):
        panel = panel_of(self.windowHandle, self.processHandle, self.appModule.language)
        button = (
            None
            if panel is None
            else panel.toolbar_entry(self.windowHandle, self.appModule.remembered_buttons)
        )
        return self.firstChild if button is None else _button_object(button)


class TopPanelButton(_PanelToolbar):
    """A button of a top panel toolbar, exposed by the toolbar's MSAA proxy."""

    @property
    def button_index(self) -> int:
        return self.IAccessibleChildID - 1

    def _get_focusRedirect(self):
        # After focus on the window, the toolbar fires focus for its first button too.
        panel, button = self._panel()
        target = (
            None
            if panel is None
            else panel.toolbar_entry(self.windowHandle, self.appModule.remembered_buttons)
        )
        return None if target is None or target == button else _button_object(target)

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
        # The proxy's position is within the button's own toolbar.
        return {}

    def _panel(self) -> tuple[TopPanel, PanelButton] | tuple[None, None]:
        panel = panel_of(self.windowHandle, self.processHandle, self.appModule.language)
        button = None if panel is None else panel.find(self.windowHandle, self.button_index)
        return (None, None) if button is None else (panel, button)

    def event_gainFocus(self):
        panel, button = self._panel()
        if panel is not None:
            self.appModule.remembered_buttons[panel.key] = button.key
        super().event_gainFocus()

    def setFocus(self):
        panel, button = self._panel()
        if panel is None or not focus_button(
            self.appModule, panel, button, api.getFocusObject().windowHandle
        ):
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
        panel, button = self._panel()
        if panel is None:
            return
        if to_end:
            index = 0 if step < 0 else len(panel.buttons) - 1
        else:
            index = min(max(panel.buttons.index(button) + step, 0), len(panel.buttons) - 1)
        target = panel.buttons[index]
        if target != button and not focus_button(self.appModule, panel, target, self.windowHandle):
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

    def doAction(self, index=None):
        panel, button = self._panel()
        if not index and panel is not None and button == panel.buttons[0]:
            # The menu of the first button switches the tab: focus goes to the new tab's first button.
            self.appModule.tab_menu_opened(_parent(_parent(self.windowHandle)))
        super().doAction(index)

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
        if panel is None or not focus_button(
            self.appModule, panel, panel.entry(self.appModule.remembered_buttons)
        ):
            gesture.send()


class MainWindowTab(IAccessible):
    """A tab of the main window."""

    def _get_description(self):
        # NVDA's Dialog behaviour of a property page collects its text from every panel of the tab,
        # which takes about 250 ms in the main window and finds nothing.
        return IAccessible._get_description(self)
