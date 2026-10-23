# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Filename preview: the tag buttons and the button opening the File name settings.

The tag buttons lie in rows between the template field and the list of templates, almost all outside the
Tab order; they are one stop of the screen order, with the arrows moving through the rows. A tag inserts
itself into the field at its caret, and ezcd moves focus to the field: focus goes back to the tag, and the
template is reported. The settings button has no window; its stop is the panel holding it.
"""

import functools

import braille
import controlTypes
import winUser
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent
from scriptHandler import script
from speech.speech import speakMessage

from . import remote, toolbar, vcl
from .names import ezcd_string
from .windows import descendants, parent, rect, root, rows

FORM = "TNamePreview"
_SETTINGS_CLASS = "TPngSpeedButton"
# "Filename generation", the page of Settings the button opens.
_SETTINGS_CAPTION = 576


def _shown(form: int, class_name: str) -> int:
    return next(
        (
            w
            for w in descendants(form)
            if winUser.getClassName(w) == class_name and winUser.isWindowVisible(w)
        ),
        0,
    )


def _template_field(form: int) -> int:
    return _shown(form, "TEdit")


def tag_rows(form: int) -> list[list[int]]:
    """The tag buttons by rows, each from left to right; none if the form is not Filename preview."""
    if winUser.getClassName(form) != FORM:
        return []
    field, templates = _template_field(form), _shown(form, "TListBox")
    if not field or not templates:
        return []
    top, bottom = rect(field).bottom, rect(templates).top
    tags = []
    for window in descendants(form):
        if winUser.getClassName(window) == "TButton" and winUser.isWindowVisible(window):
            edge = rect(window)
            if top <= (edge.top + edge.bottom) // 2 < bottom:
                tags.append(window)
    return rows(tags)


def _tags(form: int) -> list[int]:
    return [tag for row in tag_rows(form) for tag in row]


def _middle(hwnd: int) -> int:
    edge = rect(hwnd)
    return (edge.left + edge.right) // 2


def is_tag(hwnd: int) -> bool:
    return hwnd in _tags(root(hwnd))


def _settings_button(panel: int, process_handle: int) -> vcl.Control | None:
    return next(
        (c for c in vcl.controls(panel, process_handle, _SETTINGS_CLASS) if c.visible and c.enabled), None
    )


def _settings_panel(form: int, process_handle: int) -> int:
    """The panel holding the settings button, 0 if it is not shown."""
    field = _template_field(form)
    panel = parent(field) if field else 0
    return panel if panel and _settings_button(panel, process_handle) else 0


def screen_stops(form: int, stops: list[int], remembered: int, process_handle: int) -> list[int]:
    """The form's Tab stops in screen order with the tags as one stop, their ``remembered`` index or the
    first, and the settings button's panel right before it."""
    tags = _tags(form)
    if not tags:
        return stops
    entry = tags[remembered] if remembered < len(tags) else tags[0]
    stops = [stop for stop in stops if stop not in tags]
    tags_top = rect(tags[0]).top
    index = next((i for i, stop in enumerate(stops) if rect(stop).top >= tags_top), len(stops))
    panel = _settings_panel(form, process_handle)
    return [*stops[:index], *([panel] if panel else []), entry, *stops[index:]]


def is_settings_stop(panel: int) -> bool:
    """Whether the window is the panel of the settings button with ezcd's focus, which only its stop gives
    it."""
    if winUser.getClassName(root(panel)) != FORM:
        return False
    _process_id, thread_id = winUser.getWindowThreadProcessID(panel)
    return (
        winUser.getGUIThreadInfo(thread_id).hwndFocus == panel
        and parent(_template_field(root(panel))) == panel
    )


class TagStop:
    """The tag remembered for the stop, and reporting the template after a tag was inserted.

    A tag button moves focus to the template field, which goes back to the tag; an item of its menu leaves
    focus on it and only changes the field.
    """

    def __init__(self):
        self.remembered = 0
        """The index of the last focused tag."""
        self._pressed = 0
        self._menu = False
        self.returned = 0
        """The tag that got focus back after it was inserted, until it is reported."""

    def press(self, tag: int, menu: bool = False):
        """The tag, or an item of its menu, is about to be inserted."""
        self._pressed = tag
        self._menu = menu

    def focus_back(self, obj) -> int:
        """The tag to move focus back to as focus comes to the object, 0 if none."""
        if obj.windowHandle != self.returned:
            self.returned = 0
        pressed = self._pressed
        if not pressed or obj.windowHandle == pressed or obj.windowClassName == "#32768":
            return 0
        self._pressed = 0
        if self._menu or obj.windowHandle != _template_field(root(pressed)):
            return 0
        self.returned = pressed
        return pressed

    def note_change(self, obj):
        """The object changed its value: if it is the template field changed by an item of a tag's menu,
        the tag reports it as focus comes back from the menu."""
        if self._menu and self._pressed and obj.windowHandle == _template_field(root(self._pressed)):
            self.returned, self._pressed = self._pressed, 0


class TagButton(IAccessible):
    """A tag button of the tags' stop; Alt+Down opens the menu of a split button."""

    @functools.cached_property
    def _rows(self) -> list[list[int]]:
        return tag_rows(root(self.windowHandle))

    def _row(self) -> int:
        """The index of the tag's row; -1 if it is in none."""
        return next((i for i, row in enumerate(self._rows) if self.windowHandle in row), -1)

    def _index(self) -> int:
        """The index of the tag among all tags; -1 if it is in none."""
        tags = [tag for row in self._rows for tag in row]
        return tags.index(self.windowHandle) if self.windowHandle in tags else -1

    def _get_positionInfo(self):
        index = self._index()
        if index < 0:
            return {}
        return {"indexInGroup": index + 1, "similarItemsInGroup": sum(len(row) for row in self._rows)}

    def event_gainFocus(self):
        tag_stop = self.appModule.tag_stop
        tag_stop.remembered = max(self._index(), 0)
        if tag_stop.returned != self.windowHandle:
            super().event_gainFocus()
            return
        tag_stop.returned = 0
        braille.handler.handleGainFocus(self)
        field = _template_field(root(self.windowHandle))
        template = getNVDAObjectFromEvent(field, winUser.OBJID_CLIENT, 0) if field else None
        if template is not None:
            speakMessage(template.value or "")

    def event_stateChange(self):
        # A split button changes its states as it is pressed and its menu opens ("submenu"); a tag has no
        # state to report.
        pass

    def _focus(self, tag: int):
        if tag != self.windowHandle:
            toolbar.set_focus(tag)

    def _step_in_row(self, step: int, to_end: bool = False):
        index = self._row()
        if index < 0:
            return
        row = self._rows[index]
        if to_end:
            self._focus(row[0 if step < 0 else -1])
        else:
            self._focus(row[min(max(row.index(self.windowHandle) + step, 0), len(row) - 1)])

    def _step_rows(self, step: int):
        row = self._row()
        if row < 0 or not 0 <= row + step < len(self._rows):
            return
        middle = _middle(self.windowHandle)
        self._focus(min(self._rows[row + step], key=lambda tag: abs(_middle(tag) - middle)))

    @script(gesture="kb:leftArrow")
    def script_previous_tag(self, gesture):
        self._step_in_row(-1)

    @script(gesture="kb:rightArrow")
    def script_next_tag(self, gesture):
        self._step_in_row(1)

    @script(gesture="kb:home")
    def script_first_tag(self, gesture):
        self._step_in_row(-1, to_end=True)

    @script(gesture="kb:end")
    def script_last_tag(self, gesture):
        self._step_in_row(1, to_end=True)

    @script(gesture="kb:upArrow")
    def script_row_above(self, gesture):
        self._step_rows(-1)

    @script(gesture="kb:downArrow")
    def script_row_below(self, gesture):
        # Not sent on: a split button would open its menu.
        self._step_rows(1)

    @script(gestures=("kb:enter", "kb:numpadEnter", "kb:space"))
    def script_insert(self, gesture):
        self.appModule.tag_stop.press(self.windowHandle)
        gesture.send()

    @script(gesture="kb:alt+downArrow")
    def script_open_menu(self, gesture):
        if self.role == controlTypes.Role.SPLITBUTTON:
            self.appModule.tag_stop.press(self.windowHandle, menu=True)
            # A split button opens its menu on Down.
            remote.post_press(self.windowHandle, winUser.VK_DOWN)


class SettingsButton(IAccessible):
    """The stop of the button opening the File name settings: the panel holding it, with ezcd's focus."""

    role = controlTypes.Role.BUTTON

    @functools.cached_property
    def _caption(self) -> str:
        return ezcd_string(self.windowHandle, _SETTINGS_CAPTION, self.appModule.language)

    def _get_name(self):
        return self._caption

    def doAction(self, index=None):
        button = None if index else _settings_button(self.windowHandle, self.processHandle)
        # Posted: ezcd shows Settings modally while it handles the click.
        if button is None or not remote.post_click(
            self.windowHandle, button.left + button.width // 2, button.top + button.height // 2
        ):
            raise NotImplementedError

    @script(gestures=("kb:enter", "kb:numpadEnter", "kb:space"))
    def script_press(self, gesture):
        try:
            self.doAction()
        except NotImplementedError:
            gesture.send()
