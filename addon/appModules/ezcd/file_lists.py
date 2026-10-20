# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Lists of files: ``TVirtualStringTree`` windows with the tree's own MSAA implementation."""

import controlTypes
import winUser
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent

from . import convert_window

TREE_CLASS = "TVirtualStringTree"
_FILES_STRING = 494
_CONVERTING_STRING = 476


def is_conversion_list(hwnd: int) -> bool:
    return convert_window.is_conversion_window(winUser.getAncestor(hwnd, winUser.GA_ROOT))


def _is_client_event_with_focus(obj, focus, role: controlTypes.Role) -> bool:
    return (
        isinstance(focus, IAccessible)
        and focus.windowHandle == obj.windowHandle
        and focus.role == role
        and obj.event_objectID == winUser.OBJID_CLIENT
        and obj.event_childID == 0
    )


def is_focused_file_event(obj, focus) -> bool:
    """Whether an event of the tree is about its focused file, which has focus.

    The tree reports changes of its focused file on its own client object, and NVDA may give the event
    to another cached object for it than the focus.
    """
    return _is_client_event_with_focus(obj, focus, controlTypes.Role.TREEVIEWITEM)


def is_list_focus_event(obj, focus) -> bool:
    """Whether an event of the tree comes while the tree itself has focus, without a focused file."""
    return _is_client_event_with_focus(obj, focus, controlTypes.Role.TREEVIEW)


def focused_file(hwnd: int) -> IAccessible | None:
    """The tree's focused file; ``None`` if no file has focus."""
    obj = getNVDAObjectFromEvent(hwnd, winUser.OBJID_CLIENT, 0)
    if obj is None or obj.role != controlTypes.Role.TREEVIEWITEM or not obj.name:
        return None
    return obj


class FileListItem(IAccessible):
    def _get_focusRedirect(self):
        # Without a focused file, the tree reports an item without a name.
        if self.name:
            return None
        parent = self.parent
        if parent is not None and parent.role == controlTypes.Role.TREEVIEW:
            return parent
        return None

    def _get_description(self):
        # The description repeats the name without its first column.
        description = super()._get_description()
        if description and description in (self.name or ""):
            return None
        return description


class ConversionFileList(IAccessible):
    """The list of the conversion window, named Format by ezcd."""

    def _get_name(self):
        window = winUser.getAncestor(self.windowHandle, winUser.GA_ROOT)
        name = self.appModule.language.text_in_language_of(
            _FILES_STRING, _CONVERTING_STRING, winUser.getWindowText(window)
        )
        return name or super()._get_name()
