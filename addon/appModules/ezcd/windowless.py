# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Controls without windows in object navigation: speed buttons, and labels and images that take clicks.

ezcd draws them on the window holding them, and MSAA does not know them. In object navigation they are
children of that window among its child windows, all in screen order, and NVDA+Numpad Enter clicks them.
They are not Tab stops: those that need the keyboard have their own stops and keys.
"""

import functools
from ctypes.wintypes import RECT

import controlTypes
import winUser
from locationHelper import RectLTWH
from NVDAObjects import NVDAObjectTextInfo
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent
from NVDAObjects.window import Window

from . import captions, counters, filename_preview, player, remote, screen, vcl, version
from .cover_art import COVER_CLASS
from .facts.objects import Control
from .language import OwnString
from .names import Name, name_text
from .windows import child_windows, parent, rect, root, rows

_BUTTON_CLASSES = frozenset(("TSpeedButton", "TPngSpeedButton"))
# Only with a handler of clicks: other labels and images are text and pictures.
_CLICKED_CLASSES = frozenset(("TLabel", "TImage"))
_CLASSES = _BUTTON_CLASSES | _CLICKED_CLASSES
_ENCODER_INFORMATION = OwnString("encoder_information")

type _Item = int | Control
"""A child window or a control without a window."""


def _controls(holder: int, process_handle: int) -> list[Control]:
    """The shown controls without windows of the window that take clicks."""
    # VCL keeps a control visible inside a hidden window, as on a hidden tab.
    if not winUser.isWindowVisible(holder):
        return []
    if winUser.getClassName(holder) == COVER_CLASS:
        # The pictures of the cover art, which is the control itself.
        return []
    return [
        c
        for c in vcl.controls(holder, process_handle, _CLASSES)
        if c.visible and (c.on_click or c.class_name in _BUTTON_CLASSES)
    ]


def _order(holder: int, process_handle: int) -> list[_Item]:
    """The window's shown child windows and controls without windows in screen order; empty if it has no
    such controls."""
    drawn = _controls(holder, process_handle)
    if not drawn:
        return []
    shown = [w for w in child_windows(holder) if winUser.isWindowVisible(w)]

    def edge(item: _Item) -> RECT:
        return rect(item) if isinstance(item, int) else vcl.screen_rect(holder, item)

    return [item for row in rows([*shown, *drawn], edge) for item in row]


def _object(holder: int, order: list[_Item], index: int):
    """The object of the item at the index; ``None`` past the ends."""
    if not 0 <= index < len(order):
        return None
    item = order[index]
    if isinstance(item, int):
        return getNVDAObjectFromEvent(item, winUser.OBJID_WINDOW, 0)
    # NVDA makes its objects with keyword arguments only.
    return DrawnControl(holder=holder, control=item)


class Holder(IAccessible):
    """The client object of a window, whose controls without windows are among its children."""

    def _get_firstChild(self):
        order = _order(self.windowHandle, self.processHandle)
        return _object(self.windowHandle, order, 0) if order else super()._get_firstChild()

    def _get_lastChild(self):
        order = _order(self.windowHandle, self.processHandle)
        return _object(self.windowHandle, order, len(order) - 1) if order else super()._get_lastChild()

    def _get_children(self):
        order = _order(self.windowHandle, self.processHandle)
        if not order:
            return super()._get_children()
        children = (_object(self.windowHandle, order, i) for i in range(len(order)))
        return [child for child in children if child is not None]

    def _get_childCount(self):
        order = _order(self.windowHandle, self.processHandle)
        return len(order) if order else super()._get_childCount()


class Sibling(IAccessible):
    """The window object of a window, whose parent's controls without windows are among its siblings."""

    def _sibling(self, step: int):
        holder = parent(self.windowHandle)
        order = _order(holder, self.processHandle)
        if self.windowHandle not in order:
            return super()._get_next() if step > 0 else super()._get_previous()
        return _object(holder, order, order.index(self.windowHandle) + step)

    def _get_next(self):
        return self._sibling(1)

    def _get_previous(self):
        return self._sibling(-1)


class _ActivatedTextInfo(NVDAObjectTextInfo):
    def activate(self):
        # The base class clicks with the real mouse at the start of the text.
        self.obj.doAction()


class DrawnControl(Window):
    """A control without a window: a button, or a link for a label."""

    TextInfo = _ActivatedTextInfo
    firstChild = None
    lastChild = None
    actionCount = 1

    def __init__(self, holder: int, control: Control):
        self.holder = holder
        self.control = control
        super().__init__(windowHandle=holder)

    def _isEqual(self, other):
        return super()._isEqual(other) and other.control.address == self.control.address

    @functools.cached_property
    def _rect(self) -> RECT:
        return vcl.screen_rect(self.holder, self.control)

    @functools.cached_property
    def _counter(self) -> tuple[int, counters.Step] | None:
        return counters.button_of(self.holder, self._rect) if self._is_button else None

    @property
    def _is_button(self) -> bool:
        return self.control.class_name in _BUTTON_CLASSES

    def _get_role(self):
        return controlTypes.Role.LINK if self.control.class_name == "TLabel" else controlTypes.Role.BUTTON

    def _get_name(self):
        return self._name

    @functools.cached_property
    def _name(self) -> str:
        name = counters.step_name(self._counter[1]) if self._counter else self._known_name()
        if isinstance(name, str):
            # A picture has no text on it.
            return name if name or self.control.class_name == "TImage" else self._drawn_text()
        return name_text(self.holder, name, self.appModule.language)

    def _known_name(self) -> Name:
        """The name of a control without a caption; empty if none is known for it."""
        form = winUser.getClassName(root(self.holder))
        strings = version.facts.strings
        if self.control.class_name == "TImage":
            # The picture of the panel over the cover art.
            return strings.cover_art if form == "TCoverArtWnd" else player.icon_name(self.holder, self._rect)
        if not self._is_button:
            return ""
        if child_windows(self.holder, "TComboBoxEx"):
            # The output panel: the button right of the format.
            return _ENCODER_INFORMATION
        if child_windows(self.holder, "TCheckListBox"):
            # The buttons moving a metadata service, one above the other.
            column = [
                c
                for c in _controls(self.holder, self.processHandle)
                if c.class_name in _BUTTON_CLASSES and c.left == self.control.left
            ]
            if len(column) == 2:
                return (
                    strings.move_up if self.control.top == min(c.top for c in column) else strings.move_down
                )
        if form == filename_preview.FORM:
            return strings.filename_generation
        return ""

    def _drawn_text(self) -> str:
        """What ezcd drew on the control: the caption of a button, the text of a label."""
        area = screen.to_logical(self._rect, self.holder)
        binding_handle = self.appModule.helperLocalBindingHandle
        found = screen.texts(self.holder, binding_handle, area)
        if not found and screen.redraw(self.holder):
            found = screen.texts(self.holder, binding_handle, area)
        return captions.spoken(" ".join(screen.joined(line) for line in screen.lines(found)))

    def _get_states(self):
        return set() if self.control.enabled else {controlTypes.State.UNAVAILABLE}

    def _get_location(self):
        return RectLTWH.fromCompatibleType(self._rect)

    def _get_parent(self):
        return getNVDAObjectFromEvent(self.holder, winUser.OBJID_CLIENT, 0)

    def _sibling(self, step: int):
        order = _order(self.holder, self.processHandle)
        index = next(
            (
                i
                for i, item in enumerate(order)
                if not isinstance(item, int) and item.address == self.control.address
            ),
            None,
        )
        return None if index is None else _object(self.holder, order, index + step)

    def _get_next(self):
        return self._sibling(1)

    def _get_previous(self):
        return self._sibling(-1)

    def doAction(self, index=None):
        if self._counter:
            # Says the new number.
            self.appModule.counter_steps.press(*self._counter)
            return
        control = self.control
        # Posted: ezcd shows a window modally while it handles the click.
        remote.post_click(self.holder, control.left + control.width // 2, control.top + control.height // 2)
