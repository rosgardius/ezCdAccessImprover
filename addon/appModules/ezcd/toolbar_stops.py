# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Toolbars of the main window as stops in the Tab order.

VCL's toolbars are not tab stops and keep no current button. A stop holds the buttons of one or more
toolbar windows from left to right: focus comes to the button it had last, the arrows move between the
buttons, and Enter presses them with a posted click. Where a stop lies in the Tab order is up to its kind.
"""

import contextlib
import ctypes
from collections.abc import Callable, Hashable
from ctypes.wintypes import RECT
from dataclasses import dataclass

import api
import controlTypes
import eventHandler
import oleacc
import winUser
from logHandler import log
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent
from scriptHandler import script
from winBindings import user32

from . import toolbar
from .language import LanguageFiles

_MENU_MARK = "▼"


@dataclass(frozen=True)
class StopButton:
    toolbar: int
    """The toolbar window holding the button."""
    button: toolbar.ToolButton
    key: tuple[int, int]
    """The image and the number of buttons with the same image to the left: images repeat on a panel."""


def _left(hwnd: int) -> int:
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left


def read_buttons(
    toolbars: list[int], process_handle: int, image_key: Callable[[int], int] | None = None
) -> tuple[StopButton, ...]:
    """The shown buttons of the toolbars from left to right, without separators.

    ``image_key`` gives buttons that stand for one another the same image. Raises ``OSError`` if ezcd's
    memory is not accessible.
    """
    shown = []
    for hwnd in toolbars:
        left = _left(hwnd)
        shown += [
            (left, b.index, hwnd, b)
            for b in toolbar.read_buttons(hwnd, process_handle)
            if not b.hidden and not b.separator
        ]
    buttons = []
    seen: dict[int, int] = {}
    for _left_edge, _index, hwnd, button in sorted(shown, key=lambda item: item[:2]):
        image = image_key(button.image) if image_key else button.image
        buttons.append(StopButton(hwnd, button, (image, seen.get(image, 0))))
        seen[image] = seen.get(image, 0) + 1
    return tuple(buttons)


@dataclass(frozen=True)
class ToolbarStop:
    buttons: tuple[StopButton, ...]
    """The shown buttons, from left to right."""

    @property
    def key(self) -> Hashable:
        """Tells the stops apart: each remembers its own button."""
        raise NotImplementedError

    def find(self, hwnd: int, index: int) -> StopButton | None:
        return next((b for b in self.buttons if b.toolbar == hwnd and b.button.index == index), None)

    def has_menu(self, button: StopButton) -> bool:
        return False

    def entry(self, remembered: dict[Hashable, tuple[int, int]]) -> StopButton:
        """The button to enter the stop at: the remembered one while it is shown, else the first one."""
        key = remembered.get(self.key)
        return next((b for b in self.buttons if b.key == key), self.buttons[0])

    def toolbar_entry(self, hwnd: int, remembered: dict[Hashable, tuple[int, int]]) -> StopButton | None:
        """The button that focus on the toolbar window means: the remembered one if it is there."""
        buttons = [b for b in self.buttons if b.toolbar == hwnd]
        key = remembered.get(self.key)
        return next((b for b in buttons if b.key == key), buttons[0] if buttons else None)


# Finds the stop that the toolbar window is on: (toolbar, process handle, language files).
type StopFinder = Callable[[int, int, LanguageFiles], ToolbarStop | None]


def _button_object(button: StopButton) -> IAccessible | None:
    return getNVDAObjectFromEvent(button.toolbar, winUser.OBJID_CLIENT, button.button.index + 1)


def focus_button(app_module, stop: ToolbarStop, button: StopButton, focused_toolbar: int = 0) -> bool:
    """Moves focus to the button; ``focused_toolbar`` is the toolbar window that has focus now."""
    app_module.remembered_buttons[stop.key] = button.key
    if button.toolbar != focused_toolbar:
        # The toolbar window redirects focus to the remembered button.
        return toolbar.set_focus(button.toolbar)
    # VCL's focus stays on the window, the button changes only for NVDA.
    obj = _button_object(button)
    if obj is None:
        return False
    eventHandler.queueEvent("gainFocus", obj)
    return True


def button_child_id(obj: IAccessible) -> int:
    """The child id of the toolbar button, 0 for the toolbar itself.

    The proxy gives a button with a drop-down arrow an object of its own, a split button with child id 0;
    the id of the button is then that of the event it came for.
    """
    if obj.IAccessibleChildID:
        return obj.IAccessibleChildID
    return (obj.event_childID or 0) if obj.IAccessibleRole == oleacc.ROLE_SYSTEM_SPLITBUTTON else 0


class _StopToolbar(IAccessible):
    find_stop: StopFinder

    def _stop(self) -> ToolbarStop | None:
        return self.find_stop(self.windowHandle, self.processHandle, self.appModule.language)

    def isDuplicateIAccessibleEvent(self, obj):
        # Focus on the toolbar arrives for the window or its button, and is fired again on entering menu mode
        # (Alt); NVDA never treats an event for a child id as a duplicate.
        return obj.event_windowHandle == self.event_windowHandle and obj.event_objectID == self.event_objectID


class ToolbarWindow(_StopToolbar):
    """The toolbar window: focus goes on to its remembered or first button."""

    def _get_focusRedirect(self):
        stop = self._stop()
        button = (
            None if stop is None else stop.toolbar_entry(self.windowHandle, self.appModule.remembered_buttons)
        )
        return self.firstChild if button is None else _button_object(button)


class ToolbarButton(_StopToolbar):
    """A button of a toolbar stop, exposed by the toolbar's MSAA proxy."""

    @property
    def button_index(self) -> int:
        return button_child_id(self) - 1

    def _get_focusRedirect(self):
        # After focus on the window, the toolbar fires focus for its first button too.
        stop, button = self._find()
        target = (
            None if stop is None else stop.toolbar_entry(self.windowHandle, self.appModule.remembered_buttons)
        )
        return None if target is None or target == button else _button_object(target)

    def _tool_button(self) -> toolbar.ToolButton | None:
        try:
            buttons = toolbar.read_buttons(self.windowHandle, self.processHandle)
        except OSError:
            log.debugWarning("Cannot read toolbar button state", exc_info=True)
            return None
        return buttons[self.button_index] if self.button_index < len(buttons) else None

    def _get_states(self):
        states = super().states
        button = self._tool_button()
        if button is not None and not button.enabled:
            states.add(controlTypes.State.UNAVAILABLE)
        return states

    def _get_positionInfo(self):
        # The proxy's position is within the button's own toolbar, separators included.
        return {}

    def _find(self) -> tuple[ToolbarStop, StopButton] | tuple[None, None]:
        stop = self._stop()
        button = None if stop is None else stop.find(self.windowHandle, self.button_index)
        return (None, None) if button is None else (stop, button)

    def event_gainFocus(self):
        stop, button = self._find()
        if stop is not None:
            self.appModule.remembered_buttons[stop.key] = button.key
        super().event_gainFocus()

    def setFocus(self):
        stop, button = self._find()
        if stop is None or not focus_button(self.appModule, stop, button, api.getFocusObject().windowHandle):
            log.debugWarning("ezcd is not responding, focus not moved")

    def _click(self) -> bool:
        return toolbar.click(self.windowHandle, self.processHandle, self.button_index)

    def doAction(self, index=None):
        if index:
            raise NotImplementedError
        try:
            pressed = self._click()
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
        stop, button = self._find()
        if stop is None:
            return
        if to_end:
            index = 0 if step < 0 else len(stop.buttons) - 1
        else:
            index = min(max(stop.buttons.index(button) + step, 0), len(stop.buttons) - 1)
        target = stop.buttons[index]
        if target != button and not focus_button(self.appModule, stop, target, self.windowHandle):
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
        # VCL would move focus to the next or previous window of the toolbar's parent.
        pass


class ToolbarMenuButton(ToolbarButton):
    """A button that opens a menu."""

    def _get_role(self):
        return controlTypes.Role.MENUBUTTON

    def _get_name(self):
        # The role tells about the menu; a caption may mark it with a trailing triangle.
        name = super().name
        return name.replace(_MENU_MARK, "").strip() if name else name

    @script(gesture="kb:downArrow")
    def script_open_menu(self, gesture):
        # Unlike Enter, the arrow is not sent on if the click fails: VCL would move focus to another window.
        with contextlib.suppress(NotImplementedError):
            self.doAction()
