# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The top panel of the converter and ripper tabs: a row of single-button toolbars."""

from dataclasses import dataclass

import controlTypes
import winUser
from logHandler import log
from NVDAObjects.IAccessible import IAccessible
from scriptHandler import script

from . import toolbar
from .language import LanguageFiles

TOOLBAR_CLASS = "TToolBar"
_PANEL_CLASS = "TPanel"
_TAB_CLASS = "TTabSheet"
_GW_CHILD = 5

# The tab's main action, recognised by the ImageIndex of its button and its caption in the language file.
_MAIN_BUTTONS = (
    (1, (232, 406)),  # Audio Converter: "Convert"
    (0, (176,)),  # Audio CD Ripper: "Rip CD"
)


@dataclass(frozen=True)
class TopPanelToolbar:
    is_main: bool


def _child_windows(hwnd: int) -> list[int]:
    children = []
    child = winUser.getWindow(hwnd, _GW_CHILD)
    while child:
        children.append(child)
        child = winUser.getWindow(child, winUser.GW_HWNDNEXT)
    return children


def _single_button(hwnd: int, process_handle: int) -> toolbar.ToolButton | None:
    buttons = toolbar.read_buttons(hwnd, process_handle)
    return buttons[0] if len(buttons) == 1 else None


def identify(hwnd: int, process_handle: int, language: LanguageFiles) -> TopPanelToolbar | None:
    """Tells whether the toolbar window is one of the top panel's and whether it holds the main action."""
    panel = winUser.getAncestor(hwnd, winUser.GA_PARENT)
    if winUser.getClassName(panel) != _PANEL_CLASS:
        return None
    if winUser.getClassName(winUser.getAncestor(panel, winUser.GA_PARENT)) != _TAB_CLASS:
        return None
    try:
        if _single_button(hwnd, process_handle) is None:
            return None
        for sibling in _child_windows(panel):
            if winUser.getClassName(sibling) != TOOLBAR_CLASS:
                continue
            button = _single_button(sibling, process_handle)
            if button is not None and _is_main(button, language):
                return TopPanelToolbar(is_main=sibling == hwnd)
    except OSError:
        log.debugWarning("Cannot read toolbar buttons of ezcd", exc_info=True)
    return None


def _is_main(button: toolbar.ToolButton, language: LanguageFiles) -> bool:
    return any(
        button.image == image and button.text.strip() in language.texts(*numbers)
        for image, numbers in _MAIN_BUTTONS
    )


class TopPanelToolbarWindow(IAccessible):
    """The toolbar window: focus goes on to its only button."""

    def _get_focusRedirect(self):
        return self.firstChild


class TopPanelButton(IAccessible):
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

    @script(gestures=("kb:enter", "kb:space"))
    def script_press(self, gesture):
        try:
            self.doAction()
        except NotImplementedError:
            gesture.send()


class MainButton(TopPanelButton):
    """Convert or Rip CD, pressed by F8 anywhere in the main window."""

    def _get_keyboardShortcut(self):
        return "F8"
