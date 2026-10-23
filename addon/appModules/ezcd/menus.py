# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""ezcd's popup menus (``#32768``).

A menu that ezcd opens on a click, as for the buttons with menus and the context menus, has no item
selected, and NVDA reports only the menu. MSAA numbers the separators among the items, and gives an item
with a submenu as an object of its own, without a number.
"""

import oleacc
import winUser
from comtypes import COMError
from logHandler import log
from NVDAObjects.IAccessible import IAccessible

from . import remote


def _has_selected_item(menu) -> bool:
    accessible = menu.IAccessibleObject
    try:
        return any(
            accessible.accState(child) & oleacc.STATE_SYSTEM_FOCUSED
            for child in range(1, accessible.accChildCount + 1)
        )
    except COMError:
        log.debugWarning("Items of a menu not read", exc_info=True)
        # Down would move a selection.
        return True


class Menu(IAccessible):
    """A menu with focus: one without a selected item gets its first item selected, as when it is opened from
    the keyboard."""

    def event_gainFocus(self):
        super().event_gainFocus()
        if not _has_selected_item(self):
            remote.post_press(self.windowHandle, winUser.VK_DOWN)


class MenuItem(IAccessible):
    """An item or a separator of a menu: the items are numbered without the separators."""

    def _get_positionInfo(self):
        menu = self.parent
        if menu is None or menu.IAccessibleRole != oleacc.ROLE_SYSTEM_MENUPOPUP:
            return {}
        accessible = menu.IAccessibleObject
        child = self.IAccessibleChildID
        try:
            count = accessible.accChildCount
            if not child:
                # An item with a submenu: found by its place.
                location = tuple(self.location or ())
                child = next((c for c in range(1, count + 1) if accessible.accLocation(c) == location), 0)
            items = [c for c in range(1, count + 1) if accessible.accRole(c) != oleacc.ROLE_SYSTEM_SEPARATOR]
        except COMError:
            log.debugWarning("Items of a menu not read", exc_info=True)
            return {}
        if child not in items:
            return {}
        return {"indexInGroup": items.index(child) + 1, "similarItemsInGroup": len(items)}

    def _get_keyboardShortcut(self):
        # An item without a mnemonic in its text is chosen by its first character, which MSAA gives as its
        # key: a sign such as "<" begins every variant of a tag of Filename preview and chooses none of them.
        shortcut = super().keyboardShortcut
        return None if shortcut and len(shortcut) == 1 and not shortcut.isalnum() else shortcut
