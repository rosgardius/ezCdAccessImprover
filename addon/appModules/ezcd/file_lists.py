# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Lists of files: ``TVirtualStringTree`` windows with the tree's own MSAA implementation.

The tree also answers some TreeView messages; a node handle there is VirtualTrees' node pointer.
"""

import functools
import re
import time
from collections.abc import Callable, Iterable, Iterator

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

from . import convert_window, names, remote, top_panel
from .language import OwnString
from .remote import (
    TVGN_CARET,
    TVGN_CHILD,
    TVGN_FIRSTVISIBLE,
    TVGN_LASTVISIBLE,
    TVGN_NEXT,
    TVGN_NEXTVISIBLE,
    TVGN_PARENT,
    TVGN_PREVIOUSVISIBLE,
    TVGN_ROOT,
    TVIF_HANDLE,
    TVIF_STATE,
    TVIS_SELECTED,
    TVM_GETITEMW,
    TreeItemStructure,
    next_node,
)
from .windows import parent, root

_FILES_STRING = 494
_TRACKLIST_STRING = 137
_FILELIST_STRING = 141
_DISC_STRING = 486
# The string naming a list of the main window, by the string of the caption of the page holding it: the
# Audio Converter and Audio CD Ripper tabs, the Audio CD, MP3 disc and Data disc pages of the Disc Burner tab.
_LIST_NAMES = {
    172: _FILES_STRING,
    171: _TRACKLIST_STRING,
    470: _TRACKLIST_STRING,
    471: _FILELIST_STRING,
    472: _FILELIST_STRING,
}
# The pages whose list holds the disc as its only top-level node.
_DISC_PAGE_STRINGS = (471, 472)
_DISC = OwnString("disc")

_SELECT_ALL_POLL_MS = 50
_SELECT_ALL_POLLS = 10
_CLOSED_EDITOR_EVENTS_SECONDS = 1.0
_COLUMN_SEPARATOR = "; "
# Such as VirtualStringTree1 or CDW_VirtualStringTree.
_COMPONENT_NAME = re.compile(r"\w*VirtualStringTree\d*")


def is_conversion_list(hwnd: int) -> bool:
    return convert_window.is_conversion_window(root(hwnd))


def is_main_window_list(hwnd: int) -> bool:
    """A list on a tab of the main window; the add-on leaves the trees of dialogs to NVDA."""
    return (
        winUser.getClassName(hwnd) == "TVirtualStringTree" and winUser.getClassName(root(hwnd)) == "TMainform"
    )


def is_main_list_editor(hwnd: int) -> bool:
    return winUser.getClassName(hwnd) == "TVTEdit" and is_main_window_list(parent(hwnd))


def _burner_page(hwnd: int) -> int:
    """The page of the Disc Burner tab holding a list of the main window; 0 for the lists of other tabs."""
    page = parent(hwnd)
    # The tabs of the main window hold their lists in panels.
    return page if winUser.getClassName(page) == "TTabSheet" else 0


def _page_caption(hwnd: int) -> str:
    """The caption of the page holding a list of the main window: its page of the Disc Burner tab, else its
    tab."""
    return winUser.getWindowText(_burner_page(hwnd) or top_panel.main_tab(hwnd))


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
    item = TreeItemStructure(mask=TVIF_HANDLE | TVIF_STATE, hItem=node, stateMask=TVIS_SELECTED)
    remote.write(process_handle, address, item)
    if not remote.send(hwnd, TVM_GETITEMW, 0, address):
        return None
    remote.read(process_handle, address, item)
    return bool(item.state & TVIS_SELECTED)


def _selected(hwnd: int, process_handle: int, nodes: Iterable[int]) -> list[bool] | None:
    """Whether each node is selected; ``None`` if ezcd did not tell."""
    states = []
    try:
        with remote.buffer(process_handle) as address:
            for node in nodes:
                state = _node_selected(hwnd, process_handle, address, node)
                if state is None:
                    return None
                states.append(state)
    except OSError:
        log.debugWarning("Tree item state unavailable", exc_info=True)
        return None
    return states


def is_selected(hwnd: int, process_handle: int, node: int) -> bool | None:
    """Whether the node is selected; ``None`` if ezcd did not tell."""
    states = _selected(hwnd, process_handle, (node,))
    return None if states is None else states[0]


def selection(hwnd: int, process_handle: int) -> tuple[set[int], int] | None:
    """The ``node_index`` of every selected node and the number of nodes; ``None`` if ezcd did not tell."""
    states = _selected(hwnd, process_handle, _walk(hwnd))
    return None if states is None else ({i for i, state in enumerate(states) if state}, len(states))


def node_index(hwnd: int, node: int) -> int | None:
    """The node's position among all nodes in the tree's own order, the child id of ``accSelect``."""
    for index, current in enumerate(_walk(hwnd)):
        if current == node:
            return index
    return None


def is_folder(hwnd: int) -> bool:
    """Whether the tree's focused node is a folder, with files in it."""
    node = next_node(hwnd, TVGN_CARET)
    return bool(node and next_node(hwnd, TVGN_CHILD, node))


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
    return focus if focus and winUser.getClassName(focus) == "TVTEdit" and parent(focus) == hwnd else 0


class ClosedEditor:
    """Cell editors the user did not ask for, closed as soon as the tree opens them.

    Once a column other than the file name has been edited, the tree opens the editor in that column
    whenever its focus moves, except on the plain arrow keys, Home, End, Page Up and Page Down, and when
    it gets the focus after files were added. An editor on a folder's row is never wanted: its cells are
    empty, and leaving it with Down Arrow leaves ezcd's focus on the main form.
    """

    def __init__(self):
        self._editor = 0
        self._until = 0.0
        self._key_time = 0.0
        self._key_beside_editor = False
        self._key_opens_editor = False
        self._report_time = 0.0

    def note_key(self, gesture: KeyboardInputGesture):
        # Called in NVDA's keyboard hook thread.
        focus = winUser.getGUIThreadInfo(0).hwndFocus
        # A key held in the editor repeats while the add-on moves it, with the tree focused in between.
        self._key_beside_editor = (
            bool(focus)
            and winUser.getClassName(root(focus)) == "TMainform"
            and not is_main_list_editor(focus)
            and api.getFocusObject().windowClassName != "TVTEdit"
        )
        self._key_opens_editor = gesture.vkCode == winUser.VK_F2 and not gesture.modifiers
        self._key_time = time.monotonic()

    def is_unasked(self, obj) -> bool:
        """Whether the focus event is of an editor the tree opened on a folder or on a key in the main
        window that is not meant to open it."""
        if not is_main_list_editor(obj.windowHandle):
            return False
        return is_folder(parent(obj.windowHandle)) or (
            self._key_beside_editor
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
        if obj.windowClassName == "TVirtualStringTree":
            self._editor = 0
            # NVDA may drop the name change for the new file when a focus event follows at once.
            return self._report_time >= self._key_time
        return False


def _is_focused_node(item: IAccessible) -> bool:
    """Whether the tree's item is a node: without a focused node, it has no name, or VirtualTrees' default
    text if the tree has nodes."""
    return bool(item.name) and bool(next_node(item.windowHandle, TVGN_CARET))


def focused_file(hwnd: int) -> IAccessible | None:
    """The tree's focused file; ``None`` if no file has focus."""
    obj = getNVDAObjectFromEvent(hwnd, winUser.OBJID_CLIENT, 0)
    if obj is None or obj.role != controlTypes.Role.TREEVIEWITEM or not _is_focused_node(obj):
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


class TreeItem(IAccessible):
    """The focused node of a ``TVirtualStringTree``, the only node its MSAA implementation shows."""

    def _get_focusRedirect(self):
        # Without a focused node, the tree reports an item all the same.
        if _is_focused_node(self):
            return None
        parent = self.parent
        if parent is not None and parent.role == controlTypes.Role.TREEVIEW:
            return parent
        return None

    def _get_name(self):
        # An empty first column leaves the separator in front.
        name = super()._get_name()
        return name.removeprefix(_COLUMN_SEPARATOR) if name else name

    def _get_description(self):
        # The description repeats the name without its first column.
        description = super()._get_description()
        if description and description in (self.name or ""):
            return None
        return description


class MainFileListItem(TreeItem):
    """A file of the main window's list, where several files can be selected."""

    def _get_shouldAllowIAccessibleFocusEvent(self):
        # The tree reports focus for its focused file also while its cell editor or a dialog has it.
        return (
            winUser.getGUIThreadInfo(self.windowThreadID).hwndFocus == self.windowHandle
            and super().shouldAllowIAccessibleFocusEvent
        )

    @functools.cached_property
    def _disc(self) -> str:
        """The word for the disc, the only top-level node of the lists of the MP3 disc and Data disc pages,
        named by its label; empty for other lists."""
        page = _burner_page(self.windowHandle)
        if not page:
            return ""
        strings = self.appModule.language.window_strings(self.windowHandle)
        if winUser.getWindowText(page) not in (strings.get(n) for n in _DISC_PAGE_STRINGS):
            return ""
        return strings.get(_DISC_STRING) or self.appModule.language.own_string(self.windowHandle, _DISC)

    def _get_name(self):
        name = super()._get_name()
        if not name or not self._disc:
            return name
        node = next_node(self.windowHandle, TVGN_CARET)
        if not node or next_node(self.windowHandle, TVGN_PARENT, node):
            return name
        return f"{self._disc} {name}"

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

    def _expand(self, gesture, expand: bool):
        """Left and Right Arrow as in a tree view.

        The tree would move its focused column and open the cell editor there, on a folder too; F2 opens
        it. It expands and collapses a folder on Numpad Plus and Minus.
        """
        if self._is_editing():
            gesture.send()
            return
        folder = is_folder(self.windowHandle)
        if folder and (controlTypes.State.EXPANDED in self.states) != expand:
            if remote.press(self.windowHandle, winUser.VK_ADD if expand else winUser.VK_SUBTRACT):
                self.invalidateCache()
                eventHandler.executeEvent("stateChange", self)
        elif not expand:
            self._move_focus(gesture, TVGN_PARENT, True)
        elif folder:
            self._move_focus(gesture, TVGN_CHILD, True)

    @script(gesture="kb:rightArrow")
    def script_expand(self, gesture):
        self._expand(gesture, True)

    @script(gesture="kb:leftArrow")
    def script_collapse(self, gesture):
        self._expand(gesture, False)

    @script(gesture="kb:f2")
    def script_edit_cell(self, gesture):
        if self._is_editing():
            gesture.send()
        elif not is_folder(self.windowHandle):
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


class MainWindowList(IAccessible):
    """A list on a tab of the main window; ezcd names it in English or by its class name."""

    @functools.cached_property
    def _name(self) -> str:
        # The captions of the pages repeat across languages, as Audio CD in Russian and Bulgarian.
        strings = self.appModule.language.window_strings(self.windowHandle)
        caption = _page_caption(self.windowHandle)
        name = next(
            (strings.get(n, "") for shown, n in _LIST_NAMES.items() if strings.get(shown) == caption), ""
        )
        # Some languages have Filelist in small letters.
        return name[:1].upper() + name[1:]

    def _get_name(self):
        return self._name


class ConversionFileList(IAccessible):
    """The list of the conversion window, named Format by ezcd."""

    def _get_name(self):
        name = self.appModule.language.window_strings(self.windowHandle).get(_FILES_STRING)
        return name or super()._get_name()


class DialogList(names.Captioned):
    """A ``TVirtualStringTree`` of a dialog, which ezcd names by its component name unless given a name."""

    def _own_name(self) -> str:
        name = super()._own_name()
        return "" if _COMPONENT_NAME.fullmatch(name) else name
