# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Items of the application's list boxes and list views."""

import time

from logHandler import log
from NVDAObjects.IAccessible import IAccessible
from NVDAObjects.IAccessible.sysListView32 import LVM_GETITEMCOUNT

from . import remote

CLASSES = ("TListBox", "TCheckListBox", "TListView", "TJamShellList")
_LIST_VIEW_CLASSES = ("TListView", "TJamShellList")
_REPEAT_WINDOW = 0.1
"""Seconds after an item's focus event within which a focus event for the same item repeats it."""


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
