# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Lists of files: ``TVirtualStringTree`` windows with the tree's own MSAA implementation.

The tree also answers some TreeView messages; a node handle there is VirtualTrees' node pointer.
"""

import ctypes
import time
from collections.abc import Callable, Iterator

import api
import braille
import controlTypes
import core
import eventHandler
import oleacc
import speech
import ui
import vision
import winUser
from comtypes import COMError
from keyboardHandler import KeyboardInputGesture
from logHandler import log
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent
from scriptHandler import script

from . import convert_window, remote

TREE_CLASS = "TVirtualStringTree"
EDITOR_CLASS = "TVTEdit"
_FILES_STRING = 494
_CONVERTING_STRING = 476

TVM_GETNEXTITEM = 0x110A
TVM_GETITEMW = 0x113E
TVGN_ROOT = 0x0
TVGN_NEXT = 0x1
TVGN_PARENT = 0x3
TVGN_CHILD = 0x4
TVGN_FIRSTVISIBLE = 0x5
TVGN_NEXTVISIBLE = 0x6
TVGN_PREVIOUSVISIBLE = 0x7
TVGN_CARET = 0x9
TVGN_LASTVISIBLE = 0xA
TVIF_STATE = 0x8
TVIF_HANDLE = 0x10
TVIS_SELECTED = 0x2
_SELECT_ALL_POLL_MS = 50
_SELECT_ALL_POLLS = 10
_CLOSED_EDITOR_EVENTS_SECONDS = 1.0
_COLUMN_SEPARATOR = "; "


class _TreeItem(ctypes.Structure):
    # TVITEMEXW; ezcd and NVDA are both 64-bit.
    _fields_ = (
        ("mask", ctypes.c_uint),
        ("hItem", ctypes.c_void_p),
        ("state", ctypes.c_uint),
        ("stateMask", ctypes.c_uint),
        ("pszText", ctypes.c_void_p),
        ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int),
        ("iSelectedImage", ctypes.c_int),
        ("cChildren", ctypes.c_int),
        ("lParam", ctypes.c_void_p),
        ("iIntegral", ctypes.c_int),
        ("uStateEx", ctypes.c_uint),
        ("hwnd", ctypes.c_void_p),
        ("iExpandedImage", ctypes.c_int),
        ("iReserved", ctypes.c_int),
    )


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


def next_node(hwnd: int, relation: int, node: int = 0) -> int:
    """The node in the ``TVGN_*`` relation to the node; 0 if there is none or ezcd did not answer."""
    return remote.send(hwnd, TVM_GETNEXTITEM, relation, node)


def _walk(hwnd: int) -> Iterator[int]:
    """All nodes in the tree's own order, where a node's descendants follow it."""
    current = next_node(hwnd, TVGN_ROOT)
    while current:
        yield current
        following = next_node(hwnd, TVGN_CHILD, current)
        while not following and current:
            following = next_node(hwnd, TVGN_NEXT, current)
            if not following:
                current = next_node(hwnd, TVGN_PARENT, current)
        current = following


def _node_selected(hwnd: int, process_handle: int, address: int, node: int) -> bool | None:
    # The tree does not check the node: it must come from next_node just before.
    item = _TreeItem(mask=TVIF_HANDLE | TVIF_STATE, hItem=node, stateMask=TVIS_SELECTED)
    remote.write(process_handle, address, item)
    if not remote.send(hwnd, TVM_GETITEMW, 0, address):
        return None
    remote.read(process_handle, address, item)
    return bool(item.state & TVIS_SELECTED)


def is_selected(hwnd: int, process_handle: int, node: int) -> bool | None:
    """Whether the node is selected; ``None`` if ezcd did not tell."""
    try:
        with remote.buffer(process_handle) as address:
            return _node_selected(hwnd, process_handle, address, node)
    except OSError:
        log.debugWarning("Tree item state unavailable", exc_info=True)
        return None


def selection(hwnd: int, process_handle: int) -> tuple[set[int], int] | None:
    """The ``node_index`` of every selected node and the number of nodes; ``None`` if ezcd did not tell."""
    selected = set()
    count = 0
    try:
        with remote.buffer(process_handle) as address:
            for index, node in enumerate(_walk(hwnd)):
                state = _node_selected(hwnd, process_handle, address, node)
                if state is None:
                    return None
                if state:
                    selected.add(index)
                count = index + 1
    except OSError:
        log.debugWarning("Tree item state unavailable", exc_info=True)
        return None
    return selected, count


def node_index(hwnd: int, node: int) -> int | None:
    """The node's position among all nodes in the tree's own order, the child id of ``accSelect``."""
    for index, current in enumerate(_walk(hwnd)):
        if current == node:
            return index
    return None


def descendant_count(hwnd: int, node: int) -> int:
    count = 0
    child = next_node(hwnd, TVGN_CHILD, node)
    while child:
        count += 1 + descendant_count(hwnd, child)
        child = next_node(hwnd, TVGN_NEXT, child)
    return count


def cell_editor(hwnd: int) -> int:
    """The tree's cell editor if it has the keyboard focus, otherwise 0."""
    focus = winUser.getGUIThreadInfo(winUser.getWindowThreadProcessID(hwnd)[1]).hwndFocus
    if (
        focus
        and winUser.getClassName(focus) == EDITOR_CLASS
        and winUser.getAncestor(focus, winUser.GA_PARENT) == hwnd
    ):
        return focus
    return 0


class ClosedEditor:
    """Cell editors the user did not ask for, closed as soon as the tree opens them.

    Once a column other than the file name has been edited, the tree opens the editor in that column
    whenever its focus moves, except on the plain arrow keys, Home, End, Page Up and Page Down.
    """

    def __init__(self):
        self._editor = 0
        self._until = 0.0
        self._key_time = 0.0
        self._key_in_tree = False
        self._key_opens_editor = False
        self._report_time = 0.0

    def note_key(self, gesture: KeyboardInputGesture):
        # Called in NVDA's keyboard hook thread.
        focus = winUser.getGUIThreadInfo(0).hwndFocus
        # A key held in the editor repeats while the add-on moves it, with the tree focused in between.
        self._key_in_tree = (
            bool(focus)
            and winUser.getClassName(focus) == TREE_CLASS
            and api.getFocusObject().windowClassName != EDITOR_CLASS
        )
        self._key_opens_editor = gesture.vkCode == winUser.VK_F2 and not gesture.modifiers
        self._key_time = time.monotonic()

    def is_unasked(self, obj) -> bool:
        """Whether the focus event is of an editor the tree opened on a key not meant to open it."""
        return (
            obj.windowClassName == EDITOR_CLASS
            and winUser.getClassName(winUser.getAncestor(obj.windowHandle, winUser.GA_PARENT)) == TREE_CLASS
            and self._key_in_tree
            and not self._key_opens_editor
            and time.monotonic() - self._key_time < _CLOSED_EDITOR_EVENTS_SECONDS
        )

    def close(self, editor: int):
        # The editor cancels on Escape; nothing was typed into it.
        remote.post_press(editor, winUser.VK_ESCAPE)
        self._editor = editor
        self._until = time.monotonic() + _CLOSED_EDITOR_EVENTS_SECONDS

    def file_reported(self):
        self._report_time = time.monotonic()

    def is_left_focus(self, obj) -> bool:
        """Whether the focus event is the closed editor's, or the tree's after it with the file reported."""
        if not self._editor:
            return False
        if time.monotonic() > self._until:
            self._editor = 0
            return False
        if obj.windowHandle == self._editor:
            return True
        if obj.windowClassName == TREE_CLASS:
            self._editor = 0
            # NVDA may drop the name change for the new file when a focus event follows at once.
            return self._report_time >= self._key_time
        return False


def focused_file(hwnd: int) -> IAccessible | None:
    """The tree's focused file; ``None`` if no file has focus."""
    obj = getNVDAObjectFromEvent(hwnd, winUser.OBJID_CLIENT, 0)
    if obj is None or obj.role != controlTypes.Role.TREEVIEWITEM or not obj.name:
        return None
    return obj


def focused_file_name(hwnd: int) -> str:
    """The name of the tree's focused file; empty if no file has focus."""
    item = focused_file(hwnd)
    if item is None:
        return ""
    try:
        others = item.IAccessibleObject.accDescription(item.IAccessibleChildID) or ""
    except COMError:
        others = ""
    # The description is the name without its first column, the file name.
    if others and item.name.endswith(others):
        return item.name[: -len(others)].removesuffix(_COLUMN_SEPARATOR)
    return item.name


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


class MainFileListItem(FileListItem):
    """A file of the main window's list, where several files can be selected."""

    def _get_shouldAllowIAccessibleFocusEvent(self):
        # The tree reports focus for its focused file also while its cell editor or a dialog has it.
        return (
            winUser.getGUIThreadInfo(self.windowThreadID).hwndFocus == self.windowHandle
            and super().shouldAllowIAccessibleFocusEvent
        )

    def _focused_node_selected(self) -> tuple[int, bool | None]:
        node = next_node(self.windowHandle, TVGN_CARET)
        return node, is_selected(self.windowHandle, self.processHandle, node) if node else None

    def _get_states(self):
        states = super()._get_states()
        _node, selected = self._focused_node_selected()
        if selected is not None:
            states.add(controlTypes.State.SELECTABLE)
            if selected:
                states.add(controlTypes.State.SELECTED)
        return states

    def event_nameChange(self):
        if self is not api.getFocusObject():
            super().event_nameChange()
            return
        # The tree reports moving its focus to another file as a name change of this object.
        speech.speakObjectProperties(self, name=True, states=True, reason=controlTypes.OutputReason.FOCUS)
        self.appModule.closed_editor.file_reported()
        braille.handler.handleUpdate(self)
        vision.handler.handleUpdate(self, property="name")

    def _is_editing(self) -> bool:
        # NVDA's focus may stay on the file while the tree's cell editor has the keyboard.
        return winUser.getGUIThreadInfo(self.windowThreadID).hwndFocus != self.windowHandle

    def _select(self, steps: list[tuple[int, int]]) -> bool:
        """Applies ``accSelect`` flags to nodes, given as pairs of flags and ``node_index``."""
        try:
            # AccessibleObjectFromWindow_safe fails in 64-bit NVDA on a wrong argument type.
            tree = oleacc.AccessibleObjectFromWindow(self.windowHandle, winUser.OBJID_CLIENT)
            for flags, index in steps:
                tree.accSelect(flags, index)
        except (OSError, COMError):
            log.debugWarning("accSelect failed", exc_info=True)
            return False
        return True

    def _report_selection(self, was_selected: bool | None):
        self.invalidateCache()
        _node, selected = self._focused_node_selected()
        # The state change event speaks only a change; a command that changed nothing still gets an answer.
        if selected is not None and selected == was_selected:
            state = controlTypes.State.SELECTED
            ui.message(state.displayString if selected else state.negativeDisplayString)
        eventHandler.executeEvent("stateChange", self)

    def _move_focus(self, gesture, relation: int, from_focus: bool):
        if self._is_editing():
            gesture.send()
            return
        focus = next_node(self.windowHandle, TVGN_CARET)
        if not focus:
            return
        node = next_node(self.windowHandle, relation, focus if from_focus else 0)
        index = node_index(self.windowHandle, node) if node and node != focus else None
        # The tree reports the new file with a name change.
        if index is not None and self._select([(oleacc.SELFLAG_TAKEFOCUS, index)]):
            editor = cell_editor(self.windowHandle)
            if editor:
                self.appModule.closed_editor.close(editor)

    @script(gestures=["kb:leftArrow", "kb:rightArrow"])
    def script_keep_column(self, gesture):
        # On a file the tree would move its focused column and open the cell editor there; F2 opens it.
        node = next_node(self.windowHandle, TVGN_CARET)
        if self._is_editing() or (node and next_node(self.windowHandle, TVGN_CHILD, node)):
            gesture.send()

    @script(gesture="kb:f2")
    def script_edit_cell(self, gesture):
        if self._is_editing():
            gesture.send()
            return
        self.appModule.cells.open_editor(self.windowHandle, self.appModule.helperLocalBindingHandle)

    @script(gesture="kb:control+upArrow")
    def script_previous_file(self, gesture):
        self._move_focus(gesture, TVGN_PREVIOUSVISIBLE, True)

    @script(gesture="kb:control+downArrow")
    def script_next_file(self, gesture):
        self._move_focus(gesture, TVGN_NEXTVISIBLE, True)

    @script(gesture="kb:control+home")
    def script_first_file(self, gesture):
        self._move_focus(gesture, TVGN_FIRSTVISIBLE, False)

    @script(gesture="kb:control+end")
    def script_last_file(self, gesture):
        self._move_focus(gesture, TVGN_LASTVISIBLE, False)

    def _change_selection(
        self,
        gesture,
        flags_for: Callable[[bool], tuple[int, ...]],
        descendant_flags_for: Callable[[bool], int] | None = None,
        changes: Callable[[set[int], set[int]], bool] | None = None,
    ):
        """Applies flags to the focused node and, for a folder, other flags to the files in it.

        ``changes`` tells from the selected nodes and the affected ones whether the command changes
        anything; a command that does not is silent.
        """
        if self._is_editing():
            gesture.send()
            return
        node, selected = self._focused_node_selected()
        if selected is None:
            return
        index = node_index(self.windowHandle, node)
        if index is None:
            return
        affected = {index}
        steps = [(flags, index) for flags in flags_for(selected)]
        if descendant_flags_for is not None:
            flags = descendant_flags_for(selected)
            descendants = range(index + 1, index + 1 + descendant_count(self.windowHandle, node))
            affected.update(descendants)
            steps.extend((flags, descendant) for descendant in descendants)
        if changes is not None:
            current = selection(self.windowHandle, self.processHandle)
            if current is None or not changes(current[0], affected):
                return
        if self._select(steps):
            self._report_selection(selected)

    @script(gesture="kb:space")
    def script_select_only(self, gesture):
        self._change_selection(
            gesture,
            lambda selected: (oleacc.SELFLAG_TAKESELECTION,),
            lambda selected: oleacc.SELFLAG_ADDSELECTION,
            lambda selected, affected: selected != affected,
        )

    @script(gesture="kb:control+space")
    def script_toggle_selection(self, gesture):
        def toggle(selected: bool) -> int:
            return oleacc.SELFLAG_REMOVESELECTION if selected else oleacc.SELFLAG_ADDSELECTION

        self._change_selection(gesture, lambda selected: (toggle(selected),), toggle)

    @script(gesture="kb:escape")
    def script_clear_selection(self, gesture):
        # The tree can only replace the selection with one file, which then leaves it.
        self._change_selection(
            gesture,
            lambda selected: (oleacc.SELFLAG_TAKESELECTION, oleacc.SELFLAG_REMOVESELECTION),
            changes=lambda selected, affected: bool(selected),
        )

    @script(gesture="kb:control+a")
    def script_select_all(self, gesture):
        _node, selected = self._focused_node_selected()
        current = selection(self.windowHandle, self.processHandle) if selected is not None else None
        gesture.send()
        if self._is_editing() or current is None or len(current[0]) == current[1]:
            return
        self._report_when_selected(selected, _SELECT_ALL_POLLS)

    def _report_when_selected(self, was_selected: bool, polls: int):
        # The tree selects all files in its own handling of the key, some time after it was sent.
        if self is not api.getFocusObject():
            return
        _node, selected = self._focused_node_selected()
        if selected or polls <= 0:
            self._report_selection(was_selected)
            return
        core.callLater(_SELECT_ALL_POLL_MS, self._report_when_selected, was_selected, polls - 1)


class ConversionFileList(IAccessible):
    """The list of the conversion window, named Format by ezcd."""

    def _get_name(self):
        window = winUser.getAncestor(self.windowHandle, winUser.GA_ROOT)
        name = self.appModule.language.text_in_language_of(
            _FILES_STRING, _CONVERTING_STRING, winUser.getWindowText(window)
        )
        return name or super()._get_name()
