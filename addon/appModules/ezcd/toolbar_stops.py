# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Toolbars of the main window as stops in the Tab order.

VCL's toolbars are not tab stops and keep no current button. A stop holds the buttons of one or more
toolbar windows from left to right: focus comes to the button it had last, the arrows move between the
buttons, and Enter presses them with a posted click. Where a stop lies in the Tab order is up to its kind.
"""

import collections
import contextlib
import functools
from collections.abc import Callable, Hashable
from dataclasses import dataclass

import api
import controlTypes
import eventHandler
import oleacc
import winUser
from logHandler import log
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent
from scriptHandler import script

from . import names, toolbar, windows
from .facts.groups import String
from .language import LanguageFiles

_MENU_MARK = "▼"


@dataclass(frozen=True)
class StopButton:
    toolbar: int
    """The toolbar window holding the button."""
    button: toolbar.ToolButton
    key: tuple[int, int]
    """The image and the number of buttons with the same image to the left: images repeat on a panel."""


def read_buttons(
    toolbars: list[int], process_handle: int, image_key: Callable[[int], int] | None = None
) -> tuple[StopButton, ...]:
    """The shown buttons of the toolbars from left to right, without separators.

    ``image_key`` gives buttons that stand for one another the same image.
    """
    shown = []
    for hwnd in toolbars:
        left = windows.rect(hwnd).left
        shown += [
            (left, b.index, hwnd, b)
            for b in toolbar.read_buttons(hwnd, process_handle)
            if not b.hidden and not b.separator
        ]
    buttons = []
    seen = collections.Counter()
    for _left, _index, hwnd, button in sorted(shown, key=lambda item: item[:2]):
        image = image_key(button.image) if image_key else button.image
        buttons.append(StopButton(hwnd, button, (image, seen[image])))
        seen[image] += 1
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

    def entry(self, remembered: dict[Hashable, tuple[int, int]], hwnd: int = 0) -> StopButton | None:
        """The button to enter the stop, or its toolbar window ``hwnd``, at: the remembered one if it is
        there, else the first one."""
        buttons = [b for b in self.buttons if not hwnd or b.toolbar == hwnd]
        key = remembered.get(self.key)
        return next((b for b in buttons if b.key == key), buttons[0] if buttons else None)

    def overlay_class(self, button: StopButton | None) -> type:
        """The overlay class of the button, or of a toolbar window of the stop for ``None``."""
        raise NotImplementedError


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
        log.debugWarning("No object for a toolbar button of ezcd, focus not moved")
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


def overlay_class(obj: IAccessible, stop: ToolbarStop) -> type | None:
    """The overlay class of a toolbar window of the stop or of one of its buttons."""
    child_id = button_child_id(obj)
    if not child_id:
        return stop.overlay_class(None)
    button = stop.find(obj.windowHandle, child_id - 1)
    return None if button is None else stop.overlay_class(button)


class _StopToolbar(IAccessible):
    find_stop: StopFinder

    def _stop(self) -> ToolbarStop | None:
        return self.find_stop(self.windowHandle, self.processHandle, self.appModule.language)

    def isDuplicateIAccessibleEvent(self, obj):
        # Focus on the toolbar arrives for the window or its button, and is fired again on entering menu mode
        # (Alt); NVDA never treats an event for a child id as a duplicate.
        return obj.event_windowHandle == self.event_windowHandle and obj.event_objectID == self.event_objectID


class ToolbarWindow(_StopToolbar):
    """The toolbar window: focus goes on to its remembered or first button.

    It is presented as a toolbar without its design-time caption ("ToolBar6"); a toolbar of a single
    button, as View, presents the button alone.
    """

    name = ""

    def _get_isPresentableFocusAncestor(self):
        if not super().isPresentableFocusAncestor:
            return False
        stop = self._stop()
        return stop is not None and len(stop.buttons) > 1

    def _get_focusRedirect(self):
        stop = self._stop()
        button = None if stop is None else stop.entry(self.appModule.remembered_buttons, self.windowHandle)
        return self.firstChild if button is None else _button_object(button)


class ToolbarButton(_StopToolbar):
    """A button of a toolbar stop, exposed by the toolbar's MSAA proxy.

    One that shows only an image is named by ezcd's string for the image.
    """

    @property
    def button_index(self) -> int:
        return button_child_id(self) - 1

    def _get_focusRedirect(self):
        # After focus on the window, the toolbar fires focus for its first button too.
        stop, button = self._find()
        target = None if stop is None else stop.entry(self.appModule.remembered_buttons, self.windowHandle)
        return None if target in (None, button) else _button_object(target)

    def _get_name(self):
        return super()._get_name() or self._image_name

    def _image_strings(self) -> dict[int, String]:
        """ezcd's strings for buttons without text, by image; none by default."""
        return {}

    @functools.cached_property
    def _image_name(self) -> str:
        strings = self._image_strings()
        button = self._tool_button() if strings else None
        string = None if button is None else strings.get(button.image)
        return "" if string is None else names.ezcd_string(self.windowHandle, string, self.appModule.language)

    def _tool_button(self) -> toolbar.ToolButton | None:
        buttons = toolbar.read_buttons(self.windowHandle, self.processHandle)
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
        if stop is not None:
            focus_button(self.appModule, stop, button, api.getFocusObject().windowHandle)

    def _click(self) -> bool:
        return toolbar.click(self.windowHandle, self.processHandle, self.button_index)

    def doAction(self, index=None):
        if index or not self._click():
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
        if target != button:
            focus_button(self.appModule, stop, target, self.windowHandle)

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


class ButtonBeforeControl(ToolbarButton):
    """A button of a stop that stands right before another control in the Tab order.

    ezcd's own Tab order does not always run so from a toolbar, so Tab and Shift+Tab leave the toolbar by
    way of that control.
    """

    next_control: Callable[[int], int]
    """The control after the stop of the toolbar window, 0 if none: the stop is at the end of its tab."""

    @script(gesture="kb:tab")
    def script_next_control(self, gesture):
        neighbour = self.next_control(self.windowHandle)
        if neighbour:
            moved = toolbar.set_focus(neighbour)
        else:
            moved = self.appModule.leave_tab_end(self.windowHandle, True, self.processHandle)
        if not moved:
            gesture.send()

    @script(gesture="kb:shift+tab")
    def script_previous_control(self, gesture):
        # ezcd moves from the control after the toolbar to the one before it.
        neighbour = self.next_control(self.windowHandle)
        if neighbour:
            self.appModule.pass_focus(neighbour)
        elif self.appModule.leave_tab_end(self.windowHandle, False, self.processHandle):
            return
        gesture.send()


class ToolbarMenuButton(ToolbarButton):
    """A button that opens a menu."""

    role = controlTypes.Role.MENUBUTTON

    def _get_name(self):
        # The role tells about the menu; a caption may mark it with a trailing triangle.
        name = super().name
        return name.replace(_MENU_MARK, "").strip() if name else name

    @script(gesture="kb:downArrow")
    def script_open_menu(self, gesture):
        # Unlike Enter, the arrow is not sent on if the click fails: VCL would move focus to another window.
        with contextlib.suppress(NotImplementedError):
            self.doAction()
