# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Metadata fields of the main window's tabs, captioned by labels without windows."""

import winUser
from NVDAObjects.IAccessible import IAccessible

from . import captions, convert_window, file_lists, top_panel
from .language import LanguageFiles
from .windows import child_windows

FIELD_CLASSES = ("TEdit", "TMemo", "TCheckBox")
COVER_CLASS = "TDropPanel"

# Strings of the language files: the captions of the number fields and the names of the totals right of them.
_NUMBER_STRING = 590
_DISC_NUMBER_STRING = 598
_TOTAL_TRACKS_STRING = 801
_TOTAL_DISCS_STRING = 503
_TOTALS = ((_NUMBER_STRING, _TOTAL_TRACKS_STRING), (_DISC_NUMBER_STRING, _TOTAL_DISCS_STRING))
# All captions of the metadata panel; they tell the language, as short ones are the same in several.
_CAPTION_STRINGS = (*range(588, 604), 608, 609, *range(900, 907), 934, 935, 936)


def _parent(hwnd: int) -> int:
    return winUser.getAncestor(hwnd, winUser.GA_PARENT)


def is_metadata_field(hwnd: int) -> bool:
    """A field of the metadata panel of the converter or the ripper, or a CD-Text field of the burner."""
    panel = _parent(hwnd)
    if winUser.getClassName(panel) != top_panel.PANEL_CLASS:
        return False
    if child_windows(panel, COVER_CLASS):
        return True
    # The CD-Text panel is under the list of tracks, on a page of the Disc Burner tab's own page control.
    page = _parent(panel)
    return (
        winUser.getClassName(page) == top_panel.TAB_CLASS
        and not top_panel.is_main_window_tab(page)
        and bool(child_windows(page, file_lists.TREE_CLASS))
    )


def _clean(caption: str) -> str:
    return caption.rstrip(" :")


def field_name(field: int, binding_handle, language: LanguageFiles) -> str:
    """The caption of the field in the language of ezcd; empty if the display model has none."""
    if not binding_handle:
        return ""
    # The layout depends on the fields chosen in ezcd's settings, so the caption is found by position.
    layout = captions.Layout(field, binding_handle)
    caption, neighbour = layout.left()
    if not caption:
        layout = captions.Layout(field, binding_handle, repaint=True)
        caption, neighbour = layout.left()
    if caption and neighbour and not any(c.isalnum() for c in caption):
        # The total right of a track or disc number is captioned only by "/" between the two.
        number, _neighbour = captions.Layout(neighbour, binding_handle).left()
        strings = language.strings_showing(_CAPTION_STRINGS, {t.text for t in layout.texts}) or {}
        for number_string, total_string in _TOTALS:
            if strings.get(number_string) == number and strings.get(total_string):
                return strings[total_string].strip("<>")
        return f"{_clean(number)} {caption}".strip()
    return _clean(caption)


def cover_info(cover: int, binding_handle) -> str:
    """The text under the cover art: its size and format, if there is a cover."""
    if not binding_handle:
        return ""
    panel = _parent(cover)
    area = convert_window.logical_rect(panel, panel)
    rect = convert_window.logical_rect(cover, panel)
    area.left, area.top, area.right = rect.left, rect.bottom, rect.right
    texts = convert_window.display_texts(panel, area, binding_handle)
    return " ".join(text for _left, _top, text in sorted(texts, key=lambda item: (item[1], item[0])))


class MetadataField(IAccessible):
    """A metadata field, named by its caption, which is a label without a window."""

    _field_name = ""

    def _get_name(self):
        if not self._field_name:
            self._field_name = field_name(
                self.windowHandle, self.appModule.helperLocalBindingHandle, self.appModule.language
            )
        return self._field_name


class CoverArt(IAccessible):
    """The cover art of the metadata panel, with its size and format as the description."""

    def _get_name(self):
        return winUser.getWindowText(self.windowHandle)

    def _get_description(self):
        return cover_info(self.windowHandle, self.appModule.helperLocalBindingHandle)
