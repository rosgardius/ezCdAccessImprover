# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Names of controls from the captions ezcd draws beside them, labels without windows.

No label of ezcd is tied to its control, so a control without an MSAA name is named by its position:
the text left of it on its line; otherwise the check box or radio button left of it, or the caption of
the control right next to it on the left, as a field takes the caption of its slider; otherwise the
text above it, or the check box or radio button above it. The text right of it, a unit, is added.
Text between two windows belongs to the nearer one.
"""

import re
from dataclasses import dataclass

import characterProcessing
import displayModel
import textUtils
import winUser
import XMLFormatting
from NVDAObjects.IAccessible import IAccessible
from speech.speech import getCurrentLanguage

from . import convert_window
from .windows import child_windows

CLASSES = frozenset(
    (
        "TEdit",
        "TMemo",
        "TComboBox",
        "TListBox",
        "TCheckListBox",
        "TListView",
        "TTreeView",
        "TTrackBar",
        "TMyTrackBar",
        "TJamShellTree",
        "TJamShellList",
    )
)
_CHOICE_CLASSES = ("TCheckBox", "TRadioButton")
# The arrows of a spin box, right of its edit.
_SPIN_CLASS = "TUpDown"
# Texts on one line differ in top by a few pixels at most.
_LINE_TOLERANCE = 8
# The numbers of a scale over or beside a slider.
_SCALE = re.compile("[-+\\u2212\\d\\s.,]*\\d[-+\\u2212\\d\\s.,]*")
_MAX_CAPTION_LENGTH = 80
# Further apart, two windows are not parts of one setting.
_ADJACENT = 10
# The - and + of a counter, buttons without windows drawn by the parent.
_BUTTON_TEXTS = frozenset(("-", "+"))
_UNIT_SEPARATOR = ", "


@dataclass(frozen=True)
class Text:
    left: int
    top: int
    right: int
    bottom: int
    text: str


def _is_caption(text: str) -> bool:
    return text not in _BUTTON_TEXTS and not _SCALE.fullmatch(text)


def _overlap(start: int, end: int, other_start: int, other_end: int) -> bool:
    return start < other_end and other_start < end


def _read_texts(window: int, binding_handle) -> list[Text]:
    """The pieces of text the display model has for the window itself, not its child windows."""
    area = convert_window.logical_rect(window, window)
    text, rects = displayModel.getWindowTextInRect(
        binding_handle, window, area.left, area.top, area.right, area.bottom, 8, 32, True, False
    )
    texts = []
    offset = 0
    for item in XMLFormatting.XMLTextParser().parse(f"<control>{text}</control>"):
        if not isinstance(item, str):
            continue
        start, offset = offset, offset + textUtils.WideStringOffsetConverter(item).encodedStringLength
        if item.strip() and offset <= len(rects):
            first, last = rects[start], rects[offset - 1]
            texts.append(Text(first.left, first.top, last.right, first.bottom, item.strip()))
    return texts


def _first_line(texts: list[Text], last: bool = False) -> str:
    """The texts of the top line, or of the bottom one if ``last``, from left to right."""
    if not texts:
        return ""
    top = max(t.top for t in texts) if last else min(t.top for t in texts)
    line = sorted((t for t in texts if abs(t.top - top) < _LINE_TOLERANCE), key=lambda t: t.left)
    return " ".join(t.text for t in line)


def _choice_caption(hwnd: int) -> str:
    if not hwnd or winUser.getClassName(hwnd) not in _CHOICE_CLASSES:
        return ""
    return re.sub("&(.)", r"\1", winUser.getWindowText(hwnd))


class Layout:
    """A control among the other child windows of its parent and the texts the parent draws.

    Coordinates are logical ones of the parent, as the display model has them.
    """

    def __init__(self, control: int, binding_handle, repaint: bool = False, texts: list[Text] | None = None):
        self.parent = winUser.getAncestor(control, winUser.GA_PARENT)
        self.rect = convert_window.logical_rect(control, self.parent)
        self.bounds = convert_window.logical_rect(self.parent, self.parent)
        self.siblings = {
            sibling: convert_window.logical_rect(sibling, self.parent)
            for sibling in child_windows(self.parent)
            if sibling != control and winUser.isWindowVisible(sibling)
        }
        if texts is None:
            if repaint:
                convert_window.redraw(self.parent)
            texts = _read_texts(self.parent, binding_handle)
        self.texts = texts

    def _on_line(self, text: Text) -> bool:
        return _overlap(text.top, text.bottom, self.rect.top, self.rect.bottom)

    def _beside(self, other) -> bool:
        return _overlap(other.top, other.bottom, self.rect.top, self.rect.bottom)

    def left(self, nearer: bool = False) -> tuple[str, int]:
        """The text left of the control up to the nearest window on its left, and that window, 0 if none.

        Beside a multi-line control, only the text on its first line. With ``nearer``, only the text
        nearer to the control than to that window: the text right next to a window is its unit.
        """
        rect = self.rect
        edge, neighbour = self.bounds.left, 0
        for sibling, other in self.siblings.items():
            if edge < other.right <= rect.left and self._beside(other):
                edge, neighbour = other.right, sibling
        texts = [
            t
            for t in self.texts
            if edge <= t.left < rect.left
            and self._on_line(t)
            and _is_caption(t.text)
            and not (nearer and neighbour and t.left - edge < rect.left - t.right)
        ]
        return _first_line(texts), neighbour

    def adjoins(self, neighbour: int) -> bool:
        """Whether the window on the left is right next to the control, as a field is to its slider."""
        return self.rect.left - self.siblings[neighbour].right < _ADJACENT

    def above(self) -> tuple[str, int]:
        """The bottom line of text over the control up to the nearest window above it, and that window."""
        rect = self.rect
        edge, neighbour = self.bounds.top, 0
        for sibling, other in self.siblings.items():
            if edge < other.bottom <= rect.top and _overlap(other.left, other.right, rect.left, rect.right):
                edge, neighbour = other.bottom, sibling
        texts = [
            t
            for t in self.texts
            if edge <= t.top
            and t.bottom <= rect.top + _LINE_TOLERANCE
            and _overlap(t.left, t.right, rect.left, rect.right)
            and _is_caption(t.text)
        ]
        line = _first_line(texts, last=True)
        if len(line) > _MAX_CAPTION_LENGTH:
            # An explanation over the control, such as the syntax of file name templates.
            return "", 0
        return line, neighbour

    def right(self) -> str:
        """The text right of the control nearer to it than to the next window on the line."""
        rect = self.rect
        start = rect.right
        for sibling, other in self.siblings.items():
            if (
                winUser.getClassName(sibling) == _SPIN_CLASS
                and self._beside(other)
                and rect.right - _ADJACENT <= other.left <= rect.right + _ADJACENT
            ):
                start = other.right
        end = None
        for other in self.siblings.values():
            if start <= other.left and self._beside(other) and (end is None or other.left < end):
                end = other.left
        texts = [
            t
            for t in self.texts
            if start <= t.left
            and (end is None or t.left - start <= end - t.right)
            and self._on_line(t)
            and _is_caption(t.text)
        ]
        return _first_line(texts)


def _spoken(caption: str) -> str:
    """The caption, with a caption of symbols alone, as ``/``, given by the names of the symbols.

    NVDA would not say most of them at its default punctuation level.
    """
    if not caption or any(c.isalnum() for c in caption):
        return caption
    language = getCurrentLanguage()
    return " ".join(characterProcessing.processSpeechSymbol(language, c) for c in caption if not c.isspace())


def _caption(layout: Layout, unit: bool = True) -> str:
    text, neighbour = layout.left(nearer=True)
    if not text and neighbour:
        text = _choice_caption(neighbour)
        if not text and winUser.getClassName(neighbour) in CLASSES and layout.adjoins(neighbour):
            # A field showing the value of the slider left of it, or a second list of one setting.
            text = _caption(Layout(neighbour, None, texts=layout.texts), unit=False)
    if not text:
        text, neighbour = layout.above()
        if not text:
            text = _choice_caption(neighbour)
    text = _spoken(text.rstrip(" :") or text.strip())
    return _UNIT_SEPARATOR.join(part for part in (text, layout.right() if unit else "") if part)


def caption(control: int, binding_handle) -> str:
    """The name of the control from the screen; empty if the display model has nothing for it."""
    if not binding_handle:
        return ""
    name = _caption(Layout(control, binding_handle))
    if not name:
        # The display model has only what was drawn since the parent last filled its background.
        name = _caption(Layout(control, binding_handle, repaint=True))
    return name


class Captioned(IAccessible):
    """A control without an MSAA name, named by the caption ezcd draws beside it."""

    _screen_name: str | None = None

    def _own_name(self) -> str:
        return super()._get_name() or ""

    def _get_name(self):
        name = self._own_name()
        if name:
            return name
        if self._screen_name is None:
            self._screen_name = caption(self.windowHandle, self.appModule.helperLocalBindingHandle)
        return self._screen_name
