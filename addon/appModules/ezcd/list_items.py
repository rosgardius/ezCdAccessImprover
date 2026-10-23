# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Items of the application's list boxes and list views."""

import ctypes
import time
from ctypes.wintypes import POINT

import addonHandler
import api
import core
import eventHandler
import winUser
from controlTypes import State
from logHandler import log
from NVDAObjects.IAccessible import IAccessible
from NVDAObjects.IAccessible.sysListView32 import LVM_GETITEMCOUNT
from scriptHandler import script
from winBindings import user32

from . import commands, remote, screen
from .windows import parent, rect

addonHandler.initTranslation()

CLASSES = ("TListBox", "TCheckListBox", "TListView", "TJamShellList")
_LIST_VIEW_CLASSES = ("TListView", "TJamShellList", "TJamShellPopupMenu", "TJamShellOverflowListView")
_REPEAT_WINDOW = 0.1
"""Seconds after an item's focus event within which a focus event for the same item repeats it."""
_LB_GETITEMDATA = 0x199
# VCL keeps the check box of a TCheckListBox item in an object whose address is the item's data: after
# the pointer to its class and the item's own data comes the state, 0 unchecked, 1 checked, 2 grayed.
_CHECK_STATE_OFFSET = 16
_CHECK_STATES = {0: set(), 1: {State.CHECKED}, 2: {State.HALFCHECKED}}
_TOGGLE_POLL_MS = 20
_TOGGLE_POLLS = 25
# The buttons that move the selected service, image speed buttons without windows, in design units
# (DFM): one under the other, right of the list and level with its top.
_MOVE_BUTTON_LEFT = 4
_MOVE_BUTTON_WIDTH = 23
_MOVE_BUTTON_HEIGHT = 22


class ListItem(IAccessible):
    """An item of a list box or list view.

    When the list gets focus, ezcd fires focus on the list, which NVDA takes for the list's focused item,
    and right after on the item itself. A first arrow key in a list without a selection fires focus on
    the same item too, but later and with the item now selected: it is not a repeat.
    """

    def initOverlayClass(self):
        self._made = time.monotonic()

    def isDuplicateIAccessibleEvent(self, obj):
        elapsed = time.monotonic() - self._made
        if elapsed < _REPEAT_WINDOW and obj == self:
            log.debug(f"Repeated focus on a list item after {elapsed * 1000:.0f} ms")
            return True
        return super().isDuplicateIAccessibleEvent(obj)

    def _get_positionInfo(self):
        info = super().positionInfo
        if "similarItemsInGroup" in info and self.windowClassName in _LIST_VIEW_CLASSES:
            # NVDA counts the children of the list, the column header among them.
            info["similarItemsInGroup"] = (
                remote.send(self.windowHandle, LVM_GETITEMCOUNT) or info["similarItemsInGroup"]
            )
        return info


class CheckListItem(ListItem):
    """An item of a ``TCheckListBox``, whose check box has no MSAA state and changes without an event."""

    def _check_state(self) -> int | None:
        """The state of the check box as VCL keeps it; ``None`` if it cannot be read."""
        # 0 also when ezcd does not answer; every item of ezcd's list has its object.
        wrapper = remote.send(self.windowHandle, _LB_GETITEMDATA, self.IAccessibleChildID - 1)
        if wrapper <= 0:
            return None
        state = ctypes.c_ubyte()
        try:
            remote.read(self.processHandle, wrapper + _CHECK_STATE_OFFSET, state)
        except OSError:
            log.debugWarning("Check state of a TCheckListBox item not read", exc_info=True)
            return None
        return state.value if state.value in _CHECK_STATES else None

    def _get_states(self):
        states = super()._get_states()
        check_state = self._check_state()
        if check_state is not None:
            states |= {State.CHECKABLE, *_CHECK_STATES[check_state]}
        return states

    @script(gesture="kb:space")
    def script_toggle(self, gesture):
        before = self._check_state()
        gesture.send()
        if before is not None:
            self._report_when_toggled(before, _TOGGLE_POLLS)

    def _report_when_toggled(self, before: int, polls: int):
        # The list changes the state in its own handling of the key, some time after it was sent.
        if self is not api.getFocusObject():
            return
        if self._check_state() != before:
            self.invalidateCache()
            eventHandler.executeEvent("stateChange", self)
        elif polls > 0:
            core.callLater(_TOGGLE_POLL_MS, self._report_when_toggled, before, polls - 1)


class ServiceItem(CheckListItem):
    """An item of the list of metadata services in Settings, moved up and down by buttons right of it.

    ezcd fires focus on the item at its new place.
    """

    scriptCategory = commands.CATEGORY

    def _press_move_button(self, down: bool):
        lst = self.windowHandle
        panel = parent(lst)
        edge = rect(lst)
        scale = screen.dpi_scale(lst)
        point = POINT(
            edge.right + round((_MOVE_BUTTON_LEFT + _MOVE_BUTTON_WIDTH / 2) * scale),
            edge.top + round((_MOVE_BUTTON_HEIGHT * (1.5 if down else 0.5)) * scale),
        )
        if user32.ScreenToClient(panel, ctypes.byref(point)):
            remote.post_click(panel, point.x, point.y)

    @script(
        # Translators: Describes a command in the list of metadata services in the settings of
        # EZ CD Audio Converter.
        description=_("Moves the service up in the list"),
        gesture="kb:alt+upArrow",
    )
    def script_move_up(self, gesture):
        self._press_move_button(down=False)

    @script(
        # Translators: Describes a command in the list of metadata services in the settings of
        # EZ CD Audio Converter.
        description=_("Moves the service down in the list"),
        gesture="kb:alt+downArrow",
    )
    def script_move_down(self, gesture):
        self._press_move_button(down=True)


def item_class(hwnd: int) -> type[ListItem]:
    """The overlay class of an item of the list."""
    if winUser.getClassName(hwnd) != "TCheckListBox":
        return ListItem
    if winUser.getClassName(parent(parent(hwnd))) == "TSettings2GeneralInternetDiscDatabaseForm":
        return ServiceItem
    return CheckListItem
