# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Editing the cells of the main window's list of files as in a table editor.

The tree's cell editor is a ``TVTEdit`` child window. The tree opens it in the new column whenever Left
or Right Arrow moves its focused column, and does not tell which column is focused. F2 opens it in the
focused column or, if that one cannot be edited, in the column edited last, leaving the focused one
where it was. ezcd's own Alt+Left and Alt+Right in the editor check the real state of Alt and finish
after the key has been handled, so the add-on moves the editor with the plain arrow keys. The column
header is painted in the tree's non-client area without a window of its own, so the captions come from
the display model.
"""

import ctypes
import time
from ctypes.wintypes import BOOL, HWND
from dataclasses import dataclass
from typing import ClassVar

import addonHandler
import api
import controlTypes
import core
import eventHandler
import speech
import textInfos
import winUser
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent
from NVDAObjects.window.edit import Edit
from scriptHandler import script

from . import commands, file_lists, remote, screen
from .language import LanguageFiles
from .windows import parent, root

addonHandler.initTranslation()

_LYRICS_STRING = 474
_SB_HORZ = 0
_SIF_RANGE = 0x1
_SIF_PAGE = 0x2
_SIF_POS = 0x4
_WM_HSCROLL = 0x114
_SB_LINELEFT = 0
_SB_LINERIGHT = 1
_SB_PAGELEFT = 2
_SB_PAGERIGHT = 3
# More than the distance from a column's edge to its caption.
_CAPTION_MARGIN = 10
# Each step moves the focused column by one; a list has a few dozen columns at most.
_MAX_STEPS = 100
# Captions of the same column read before and after scrolling may start a pixel apart.
_SAME_LEFT = 2
# A walk lets NVDA work after this long; its watchdog acts on a script running for 0.5 s.
_WALK_SLICE_SECONDS = 0.25
_BETWEEN_EDITORS_SECONDS = 1.0


class _ScrollInfo(ctypes.Structure):
    _fields_ = (
        ("cbSize", ctypes.c_uint),
        ("fMask", ctypes.c_uint),
        ("nMin", ctypes.c_int),
        ("nMax", ctypes.c_int),
        ("nPage", ctypes.c_uint),
        ("nPos", ctypes.c_int),
        ("nTrackPos", ctypes.c_int),
    )


# Not in winBindings; a private library object keeps these declarations away from ctypes.windll.
_get_scroll_info = ctypes.WinDLL("user32").GetScrollInfo
_get_scroll_info.argtypes = (HWND, ctypes.c_int, ctypes.POINTER(_ScrollInfo))
_get_scroll_info.restype = BOOL


@dataclass(frozen=True)
class Column:
    left: int
    """Where the caption starts, counted from the start of the row: it stays when the list scrolls."""
    caption: str


def _scroll_info(tree: int) -> _ScrollInfo | None:
    info = _ScrollInfo(cbSize=ctypes.sizeof(_ScrollInfo), fMask=_SIF_RANGE | _SIF_PAGE | _SIF_POS)
    return info if _get_scroll_info(tree, _SB_HORZ, ctypes.byref(info)) else None


def _scroll_position(tree: int) -> int:
    # The position is in the units of the display model's coordinates.
    info = _scroll_info(tree)
    return info.nPos if info else 0


def _more_columns(tree: int, direction: int) -> bool:
    """Whether columns are scrolled out of view in the direction."""
    info = _scroll_info(tree)
    if info is None:
        return False
    if direction > 0:
        return info.nPos + info.nPage <= info.nMax
    return info.nPos > info.nMin


_painted_scroll: dict[int, int] = {}
"""The scroll position of each tree when its header was last painted for reading."""


def header(tree: int, binding_handle, repaint: bool = False) -> list[Column]:
    """The captions of the columns in view, from left to right.

    After the list scrolls, the display model has the header only once it is painted again; ``repaint``
    paints it anyway, after a dialog covered it.
    """
    if not binding_handle:
        return []
    scroll = _scroll_position(tree)
    if repaint or _painted_scroll.get(tree) != scroll:
        screen.redraw(tree, frame=True)
        _painted_scroll[tree] = scroll
    area = screen.logical_rect(tree, tree)
    area.bottom = screen.client_rect(tree).top
    texts = screen.texts(tree, binding_handle, area)
    return [Column(t.left + scroll, t.text) for t in sorted(texts, key=lambda t: (t.left, t.top))]


def _editor_index(tree: int, editor: int, columns: list[Column]) -> int | None:
    """The column of the cell editor: its caption starts within the editor or, if none does, before it."""
    rect = screen.logical_rect(editor, tree)
    scroll = _scroll_position(tree)
    left, right = rect.left + scroll, rect.right + scroll
    for index, column in enumerate(columns):
        if left <= column.left < right:
            return index
    return max((index for index, column in enumerate(columns) if column.left < left), default=None)


def editor_column(tree: int, editor: int, binding_handle, repaint: bool = False) -> str:
    """The caption of the cell editor's column; empty if the display model does not have it."""
    columns = header(tree, binding_handle, repaint)
    index = _editor_index(tree, editor, columns)
    return columns[index].caption if index is not None else ""


def _neighbour(columns: list[Column], left: int, direction: int) -> int | None:
    """The column next to the one whose caption starts at ``left``, in the direction."""
    if direction > 0:
        return next((index for index, column in enumerate(columns) if column.left > left + _SAME_LEFT), None)
    return max(
        (index for index, column in enumerate(columns) if column.left < left - _SAME_LEFT), default=None
    )


def _in_menu(tree: int) -> bool:
    # Keys sent to the tree while ezcd is in a menu loop can make it fail.
    flags = winUser.getGUIThreadInfo(winUser.getWindowThreadProcessID(tree)[1]).flags
    return bool(flags & (winUser.GUI_INMENUMODE | winUser.GUI_SYSTEMMENUMODE | winUser.GUI_POPUPMENUMODE))


def _arrow(direction: int) -> int:
    return winUser.VK_RIGHT if direction > 0 else winUser.VK_LEFT


@dataclass
class _Cursor:
    """The tree's focused column, by where its caption starts, and the header it is in."""

    tree: int
    binding_handle: object
    columns: list[Column]
    left: int
    scroll: int

    def follow_scroll(self):
        # The header is read again only when the list scrolled and other columns came into view.
        position = _scroll_position(self.tree)
        if position != self.scroll:
            self.columns = header(self.tree, self.binding_handle)
            self.scroll = position

    def reveal(self, direction: int):
        """Scrolls the columns beyond the edge into view as far as the focused column stays in view.

        A key in a column scrolled partly out of view only brings it back into view. The tree scrolls
        by pages or by lines of a few pixels, so this is a page and then lines back.
        """
        view = screen.client_rect(self.tree)
        if direction > 0:
            room = self.left - _CAPTION_MARGIN - self.scroll - view.left
        else:
            index = _neighbour(self.columns, self.left, 1)
            if index is None:
                return
            room = view.right - (self.columns[index].left - _CAPTION_MARGIN - self.scroll)
        if room <= 0:
            return
        start = _scroll_position(self.tree)
        remote.send(self.tree, _WM_HSCROLL, _SB_PAGERIGHT if direction > 0 else _SB_PAGELEFT)
        back = abs(_scroll_position(self.tree) - start) - room
        line = _SB_LINELEFT if direction > 0 else _SB_LINERIGHT
        while back > 0:
            position = _scroll_position(self.tree)
            remote.send(self.tree, _WM_HSCROLL, line)
            step = abs(_scroll_position(self.tree) - position)
            if not step:
                break
            back -= step
        self.follow_scroll()


@dataclass
class _Walk:
    """Alt+Home or Alt+End on its way through the columns."""

    cursor: _Cursor
    direction: int
    moved: bool = False
    stopped: bool = False
    """Whether a key was pressed meanwhile, which ends the walk."""


@dataclass
class _DialogReturn:
    """What happens to the focused column when focus comes back to the list from the lyrics dialog."""

    tree: int
    """The list; 0 for the one focus comes back to."""
    direction: int
    """Where the lyrics column is from the column to come back to."""
    steps: int
    """How many columns the lyrics column is from it."""
    origin: str | None
    """The caption of the column to come back to and edit; ``None`` for any, empty to edit none."""
    dialog_seen: bool = False


class CellTable:
    """The state of cell editing in the main window's list of files."""

    def __init__(self, language: LanguageFiles):
        self._language = language
        self.last_cell: tuple[int, int, str] | None = None
        """The tree, node and column caption of the cell editor reported last."""
        self._return: _DialogReturn | None = None
        self._walk: _Walk | None = None
        self.activity_time = 0.0
        """When the user pressed a key or ezcd focused an editor last."""

    def handle_focus(self, obj, binding_handle) -> bool:
        """Notes a focus event in ezcd; ``True`` if the add-on handled it and NVDA should not report it.

        When focus comes back to the list from the lyrics dialog, the focused column moves off the
        lyrics column, which would show the dialog on every move to another file.
        """
        if obj.windowClassName != "TVTEdit":
            self.last_cell = None
        form = root(obj.windowHandle)
        if winUser.getClassName(form) == "TLyricsEditor":
            if self._return is None:
                # Shown by ezcd itself: the lyrics column was focused, and another file got focus.
                self._return = _DialogReturn(0, 1, 1, "")
            self._return.dialog_seen = True
            return False
        back = self._return
        if back is None:
            return False
        is_list = (
            obj.windowHandle == back.tree if back.tree else file_lists.is_main_window_list(obj.windowHandle)
        )
        if not is_list:
            if obj.windowHandle != form:
                self._return = None
                return False
            # The main window itself gets focus first when the dialog closes.
            return back.dialog_seen
        if not back.dialog_seen:
            return False
        self._return = None
        return self._come_back(obj.windowHandle, back, binding_handle)

    def is_coming_back(self, obj) -> bool:
        """Whether focus is on its way back to the list from the lyrics dialog.

        NVDA would report the main window and the controls around the list on the way.
        """
        return (
            self._return is not None
            and self._return.dialog_seen
            and winUser.getClassName(root(obj.windowHandle)) != "TLyricsEditor"
        )

    def _come_back(self, tree: int, back: _DialogReturn, binding_handle) -> bool:
        # Whether the focused column is still the lyrics column or back in the one the user came from
        # depends on how the dialog was closed.
        moved = 0
        editor = 0
        while moved < back.steps and not editor:
            if not remote.press(tree, _arrow(-back.direction)):
                return False
            moved += 1
            editor = file_lists.cell_editor(tree)
        if editor and (
            back.origin is None or editor_column(tree, editor, binding_handle, repaint=True) == back.origin
        ):
            # The editor's focus event reports it.
            return True
        # Escape closes the editor without changing the focused column.
        if editor and not remote.press(editor, winUser.VK_ESCAPE):
            return False
        if not back.origin:
            return False
        for _step in range(moved):
            if not remote.press(tree, _arrow(back.direction)) or file_lists.cell_editor(tree):
                break
        return bool(file_lists.cell_editor(tree))

    def _cursor(self, tree: int, binding_handle, editor: int) -> _Cursor | None:
        columns = header(tree, binding_handle)
        index = _editor_index(tree, editor, columns)
        if index is None:
            return None
        return _Cursor(tree, binding_handle, columns, columns[index].left, _scroll_position(tree))

    def _seek(self, cursor: _Cursor, editor: int, direction: int, past_lyrics: bool) -> int | None:
        """Moves the focused column from the cursor's in the direction until the tree opens an editor.

        The lyrics column opens its dialog if ``past_lyrics``, otherwise it ends the row. Returns
        ``None`` once the editor or the dialog is due, otherwise the number of columns moved; the cursor
        follows the focused column.
        """
        tree = cursor.tree
        origin = next((column.caption for column in cursor.columns if column.left == cursor.left), "")
        arrow = _arrow(direction)
        steps = 0
        while steps < _MAX_STEPS:
            index = _neighbour(cursor.columns, cursor.left, direction)
            edge = len(cursor.columns) - 1 if direction > 0 else 0
            if index in (None, edge) and _more_columns(tree, direction):
                # The caption at the edge may be cut off: bring the columns beyond it into view.
                if editor and not remote.press(editor, winUser.VK_RETURN):
                    return None
                editor = 0
                cursor.reveal(direction)
                index = _neighbour(cursor.columns, cursor.left, direction)

            if index is None:
                break
            target = cursor.columns[index]
            is_lyrics = target.caption in self._language.texts(_LYRICS_STRING)
            if is_lyrics and not past_lyrics:
                break
            # The tree moves its focused column only while the editor is closed; Enter keeps the text.
            if editor and not remote.press(editor, winUser.VK_RETURN):
                return None
            editor = 0
            if is_lyrics:
                # Moving there opens the lyrics dialog in ezcd's handling of the key.
                remote.post_press(tree, arrow)
                self._return = _DialogReturn(tree, direction, steps + 1, origin)
                return None
            if not remote.press(tree, arrow):
                # A dialog keeps the key from returning.
                self._return = _DialogReturn(tree, direction, steps + 1, origin)
                return None
            steps += 1
            cursor.left = target.left
            cursor.follow_scroll()
            if file_lists.cell_editor(tree):
                return None
        return steps

    def move(self, editor: int, binding_handle, direction: int) -> bool:
        """Moves the cell editor to the nearest column in the direction that can be edited.

        Returns ``False`` if there is none and the editor stays.
        """
        tree = parent(editor)
        if _in_menu(tree):
            return True
        cursor = self._cursor(tree, binding_handle, editor)
        if cursor is None:
            return False
        steps = self._seek(cursor, editor, direction, past_lyrics=True)
        return steps is None or self._settle(tree, binding_handle, direction, steps)

    def _settle(self, tree: int, binding_handle, direction: int, steps: int) -> bool:
        """Brings the editor back after ``_seek`` found no column; ``False`` if it is still open there."""
        if file_lists.cell_editor(tree):
            return False
        # The tree opens the editor again when the focused column comes back to the one it was in.
        for _step in range(steps):
            if not remote.press(tree, _arrow(-direction)):
                return True
        # Without a move, the editor was only closed to scroll.
        if not file_lists.cell_editor(tree):
            self.open_editor(tree, binding_handle)
        return True

    def walk(self, editor: int, binding_handle, direction: int):
        """Moves the cell editor to the farthest column in the direction that can be edited, short of Lyrics.

        It moves one column per core cycle, which also keeps a long row from taking a script longer than
        NVDA's watchdog allows. The editors on the way are not reported.
        """
        tree = parent(editor)
        if _in_menu(tree) or self._walk is not None:
            return
        cursor = self._cursor(tree, binding_handle, editor)
        if cursor is None:
            return
        self._walk = _Walk(cursor, direction)
        self._walk_on(editor)

    @property
    def walking(self) -> bool:
        return self._walk is not None

    def note_key(self, vk: int):
        # Called in NVDA's keyboard hook thread for every key; Alt+Home or Alt+End held down repeats.
        self.activity_time = time.monotonic()
        if self._walk is not None and vk not in (winUser.VK_HOME, winUser.VK_END):
            self._walk.stopped = True

    def _walk_on(self, editor: int):
        try:
            self._walk_step(editor)
        except Exception:
            # Without the walk ended, the focus of every editor would go unreported.
            self._walk = None
            raise

    def _walk_step(self, editor: int):
        walk = self._walk
        if walk is None:
            return
        tree = walk.cursor.tree
        started = time.monotonic()
        while True:
            if walk.stopped or file_lists.cell_editor(tree) != editor:
                self._end_walk(editor if walk.moved else 0)
                return
            steps = self._seek(walk.cursor, editor, walk.direction, past_lyrics=False)
            opened = file_lists.cell_editor(tree)
            if steps is not None or not opened:
                break
            walk.moved = True
            editor = opened
            if time.monotonic() - started > _WALK_SLICE_SECONDS:
                core.callLater(0, self._walk_on, editor)
                return
        if steps is None:
            # The lyrics dialog is due.
            self._end_walk(0)
            return
        self._end_walk(opened if walk.moved else 0)
        if self._settle(tree, walk.cursor.binding_handle, walk.direction, steps):
            return
        if not walk.moved:
            # Already the farthest column.
            focus = api.getFocusObject()
            if isinstance(focus, CellEditor) and focus.windowHandle == editor:
                focus.reportFocus()

    def _end_walk(self, editor: int):
        """Ends the walk; the focus of the editor it stopped in, not reported on the way, is reported now."""
        self._walk = None
        if not editor:
            return
        obj = getNVDAObjectFromEvent(editor, winUser.OBJID_CLIENT, 0)
        if obj is not None:
            eventHandler.queueEvent("gainFocus", obj)

    def open_editor(self, tree: int, binding_handle):
        """Opens the cell editor in the focused column or, if it cannot be edited, in the nearest one.

        F2 could open it in another column than the focused one, which the arrow keys move from: moving
        the focused column to the left and back opens it in the focused column.
        """
        if _in_menu(tree):
            return
        if not remote.press(tree, winUser.VK_LEFT):
            # The lyrics column is to the left: its dialog is shown.
            self._return = _DialogReturn(tree, -1, 1, "")
            return
        editor = file_lists.cell_editor(tree)
        # Escape closes the editor without changing the focused column.
        if editor and not remote.press(editor, winUser.VK_ESCAPE):
            return
        if not remote.press(tree, winUser.VK_RIGHT):
            # The focused column is the lyrics column: its dialog is shown.
            self._return = _DialogReturn(tree, 1, 1, None)
            return
        if file_lists.cell_editor(tree):
            return
        # Most columns that cannot be edited are the file's properties, at the end of the row.
        count = max(len(header(tree, binding_handle)), 1)
        for direction, steps in ((-1, count), (1, 2 * count)):
            for _step in range(steps):
                if not remote.press(tree, _arrow(direction)):
                    self._return = _DialogReturn(tree, direction, 1, None)
                    return
                if file_lists.cell_editor(tree):
                    return


class CellEditor(Edit):
    """The cell editor of the main window's list of files, named by its column."""

    scriptCategory = commands.CATEGORY
    # NVDA takes the editor for one with the text object model, which it lacks.
    editAPIVersion = 0
    # The tree moves the editor to another file; NVDA would read the line of this one as it closes. Not
    # caught, the keys also get to ezcd without waiting for NVDA.
    __gestures: ClassVar[dict[str, None]] = {"kb:upArrow": None, "kb:downArrow": None}

    def initOverlayClass(self):
        # Every editor is a window of its own, destroyed when it closes.
        self.tree = parent(self.windowHandle)

    def _get_parent(self):
        if winUser.isWindow(self.windowHandle):
            return super()._get_parent()
        # Without its ancestors, NVDA would report all of them for the next editor.
        return getNVDAObjectFromEvent(self.tree, winUser.OBJID_CLIENT, 0)

    def _get_column(self) -> str:
        return editor_column(self.tree, self.windowHandle, self.appModule.helperLocalBindingHandle)

    def _get_name(self):
        return self.column or super()._get_name()

    def _get_description(self):
        # NVDA+Tab reports it, after the column.
        return file_lists.focused_file_name(self.tree)

    def _get_shouldAllowIAccessibleFocusEvent(self):
        self.appModule.cells.activity_time = time.monotonic()
        # Moving to another cell closes one editor and opens another; the focus event of the first comes late.
        return (
            not self.appModule.cells.walking
            and winUser.getGUIThreadInfo(self.windowThreadID).hwndFocus == self.windowHandle
            and super().shouldAllowIAccessibleFocusEvent
        )

    def _get_states(self):
        # The tree makes every editor multiline.
        return super()._get_states() - {controlTypes.State.MULTILINE}

    def reportFocus(self):
        cells = self.appModule.cells
        cell = (self.tree, remote.next_node(self.tree, remote.TVGN_CARET), self.column)
        if self.is_closed:
            # ezcd moved on while the column was read.
            return
        last, cells.last_cell = cells.last_cell, cell
        if last is not None and last[0] == cell[0] and last[1] != cell[1]:
            # Up and Down Arrow move the editor to another file in the same column.
            label = file_lists.focused_file_name(self.tree)
        else:
            label = cell[2]
        if label:
            speech.speakMessage(label)
        # The tree selects the whole text of a new editor.
        selection = self.makeTextInfo(textInfos.POSITION_SELECTION)
        if not selection.isCollapsed:
            speech.speakTextSelected(selection.text)
            return
        speech.speakTextInfo(
            self.makeTextInfo(textInfos.POSITION_ALL),
            unit=textInfos.UNIT_LINE,
            reason=controlTypes.OutputReason.CARET,
        )

    def _open_editor(self) -> int:
        # A held key repeats before NVDA reports the editor the previous press opened; this one is closed.
        return file_lists.cell_editor(self.tree)

    @property
    def is_closed(self) -> bool:
        """Whether the editor closed before NVDA got to its focus event, as on a held key."""
        return self._open_editor() != self.windowHandle

    def event_caret(self):
        # Moving to another cell closes the editor with Enter, which drops its selection. NVDA would report
        # the selection as gone: its focus stays on this editor until the focus event of the next one, which
        # the walk of Alt+Home and Alt+End holds back until it ends.
        if not self.is_closed:
            super().event_caret()

    def _move(self, direction: int):
        editor = self._open_editor()
        if not editor:
            return
        stays = not self.appModule.cells.move(editor, self.appModule.helperLocalBindingHandle, direction)
        # Otherwise the focus event of the editor reports it.
        if stays and editor == self.windowHandle:
            self.reportFocus()

    @script(gesture="kb:tab")
    def script_next_column(self, gesture):
        self._move(1)

    @script(gesture="kb:shift+tab")
    def script_previous_column(self, gesture):
        self._move(-1)

    @script(
        # Translators: Describes a command in the cell editor of the list of files of EZ CD Audio Converter.
        description=_("Moves the editor to the first column of the file that can be edited"),
        gesture="kb:alt+home",
    )
    def script_first_column(self, gesture):
        editor = self._open_editor()
        if editor:
            self.appModule.cells.walk(editor, self.appModule.helperLocalBindingHandle, -1)

    @script(
        # Translators: Describes a command in the cell editor of the list of files of EZ CD Audio Converter.
        description=_("Moves the editor to the last column of the file that can be edited, before Lyrics"),
        gesture="kb:alt+end",
    )
    def script_last_column(self, gesture):
        editor = self._open_editor()
        if editor:
            self.appModule.cells.walk(editor, self.appModule.helperLocalBindingHandle, 1)


class BetweenEditors(IAccessible):
    """What ezcd focuses for a moment while the cell editor moves: the main window, the list, a file."""

    def _get_shouldAllowIAccessibleFocusEvent(self):
        if not super().shouldAllowIAccessibleFocusEvent:
            return False
        editor = eventHandler.lastQueuedFocusObject
        if isinstance(editor, CellEditor):
            # NVDA would report it, then its descendants down to the next editor.
            self._place = None
            self._report_if_kept(editor.tree)
            return False
        return True

    def _report_if_kept(self, tree: int):
        """Reports the object if it keeps the focus once ezcd is done with the keys it was given.

        NVDA sees only some of the editors ezcd opens on held keys; the focused cell shows it is still busy.
        """
        if not (
            isinstance(eventHandler.lastQueuedFocusObject, CellEditor)
            and winUser.getGUIThreadInfo(self.windowThreadID).hwndFocus == self.windowHandle
        ):
            return
        place = (remote.next_node(tree, remote.TVGN_CARET), _scroll_position(tree))
        idle = time.monotonic() - self.appModule.cells.activity_time
        if place != self._place or idle < _BETWEEN_EDITORS_SECONDS:
            self._place = place
            core.callLater(int(_BETWEEN_EDITORS_SECONDS * 1000), self._report_if_kept, tree)
            return
        eventHandler.queueEvent("gainFocus", self)
