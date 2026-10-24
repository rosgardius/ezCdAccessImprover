# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""VCL objects in ezcd's memory: the object of a window and its controls without windows."""

import ctypes
import functools
from ctypes.wintypes import HANDLE, HWND, LPCWSTR, RECT

import winUser
from logHandler import log

from . import remote, screen, version
from .facts import objects
from .facts.objects import Control
from .language import LanguageFiles
from .windows import descendants, top_level_windows

# Not in winBindings; a private library object keeps these declarations away from ctypes.windll.
_user32 = ctypes.WinDLL("user32")
_get_prop = _user32.GetPropW
_get_prop.argtypes = (HWND, LPCWSTR)
_get_prop.restype = HANDLE
_get_window_long_ptr = _user32.GetWindowLongPtrW
_get_window_long_ptr.argtypes = (HWND, ctypes.c_int)
_get_window_long_ptr.restype = ctypes.c_ssize_t
_GWLP_HINSTANCE = -6
_LABEL_CLASSES = frozenset(("TLabel",))

_trusted_processes: set[int] = set()
"""The ezcd processes whose captions turned out to be ezcd's strings."""


def window_object(hwnd: int) -> int:
    """The address of the window's VCL object; 0 if it has none."""
    instance = _get_window_long_ptr(hwnd, _GWLP_HINSTANCE)
    _process_id, thread_id = winUser.getWindowThreadProcessID(hwnd)
    return _get_prop(hwnd, objects.window_property(instance, thread_id)) or 0


def controls(hwnd: int, process_handle: int, class_names: frozenset[str]) -> list[Control]:
    """The window's controls without windows of the VCL classes; none if ezcd's memory cannot be read."""
    window = window_object(hwnd)
    if not window:
        return []
    try:
        return objects.controls(
            functools.partial(remote.read, process_handle), window, class_names, version.facts.vcl
        )
    except OSError:
        log.debugWarning("Controls of a VCL window of ezcd not read", exc_info=True)
        return []


def screen_rect(hwnd: int, control: Control) -> RECT:
    """The rectangle on the screen of the window's control."""
    left, top = winUser.ClientToScreen(hwnd, control.left, control.top)
    return RECT(left, top, left + control.width, top + control.height)


def _captions(hwnd: int, process_handle: int) -> set[str]:
    return {label.text.strip() for label in controls(hwnd, process_handle, _LABEL_CLASSES)} - {""}


def _text_offset_holds(hwnd: int, process_handle: int, language: LanguageFiles, texts: set[str]) -> bool:
    """Whether the captions read at ``Vcl.text`` are ezcd's: some of them, or of the labels of the main
    window, are strings of the language files. Another version of ezcd may keep the caption elsewhere, and
    what is read there is no string of ezcd."""
    process_id, _thread_id = winUser.getWindowThreadProcessID(hwnd)
    if process_id in _trusted_processes:
        return True
    holds = language.knows_any(texts) or any(
        language.knows_any(_captions(window, process_handle))
        for form in top_level_windows(process_id, "TMainform")
        for window in descendants(form)
    )
    if holds:
        _trusted_processes.add(process_id)
    return holds


def label_texts(hwnd: int, process_handle: int, language: LanguageFiles) -> list[screen.Text]:
    """The captions of the window's shown labels without windows, each on one line, at the labels'
    rectangles in the window's logical coordinates, as the display model has texts; none if ezcd's memory
    cannot be read, or if the captions there are not ezcd's (``_text_offset_holds``).

    Unlike the display model, they are there also scrolled out of view, and never painted only in part.
    """
    found = []
    for label in controls(hwnd, process_handle, _LABEL_CLASSES):
        text = " ".join(label.text.split())
        if label.visible and text:
            edge = screen.to_logical(screen_rect(hwnd, label), hwnd)
            found.append(screen.Text(edge.left, edge.top, edge.right, edge.bottom, text))
    if not found or not _text_offset_holds(hwnd, process_handle, language, {t.text for t in found}):
        return []
    return found
