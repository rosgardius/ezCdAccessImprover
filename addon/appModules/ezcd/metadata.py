# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Metadata fields of the main window's tabs, captioned by labels without windows."""

import winUser
from NVDAObjects.IAccessible import IAccessible

from . import captions, screen, top_panel
from .cover_art import COVER_CLASS
from .language import LanguageFiles
from .windows import child_windows, parent

FIELD_CLASSES = ("TEdit", "TMemo", "TCheckBox")

# Strings of the language files: the captions of the number fields and the names of the totals right of them.
_NUMBER_STRING = 590
_DISC_NUMBER_STRING = 598
_TOTAL_TRACKS_STRING = 801
_TOTAL_DISCS_STRING = 503
_TOTALS = ((_NUMBER_STRING, _TOTAL_TRACKS_STRING), (_DISC_NUMBER_STRING, _TOTAL_DISCS_STRING))
# All captions of the metadata panel; they tell the language, as short ones are the same in several.
_CAPTION_STRINGS = (*range(588, 604), 608, 609, *range(900, 907), 934, 935, 936)


def is_metadata_field(hwnd: int) -> bool:
    """A field of the metadata panel of the converter or the ripper, or a CD-Text field of the burner."""
    panel = parent(hwnd)
    if winUser.getClassName(panel) != "TPanel":
        return False
    if child_windows(panel, COVER_CLASS):
        return True
    # The CD-Text panel is under the list of tracks, on a page of the Disc Burner tab's own page control.
    page = parent(panel)
    return (
        winUser.getClassName(page) == "TTabSheet"
        and not top_panel.is_main_window_tab(page)
        and bool(child_windows(page, "TVirtualStringTree"))
    )


def _caption_of(layout: captions.Layout, language: LanguageFiles) -> str:
    texts, neighbour = layout.left()
    caption = screen.joined(texts)
    if caption and neighbour and not any(c.isalnum() for c in caption):
        # The total right of a track or disc number is captioned only by "/" between the two.
        number = screen.joined(captions.Layout(neighbour, texts=layout.texts).left()[0])
        strings = language.strings({t.text for t in layout.texts}, _CAPTION_STRINGS)
        for number_string, total_string in _TOTALS:
            if strings.get(number_string) == number and strings.get(total_string):
                return strings[total_string].strip("<>")
        return f"{number.rstrip(' :')} {caption}".strip()
    return caption.rstrip(" :")


def field_name(field: int, binding_handle, language: LanguageFiles) -> str:
    """The caption of the field in the language of ezcd; empty if the display model has none."""
    # The layout depends on the fields chosen in ezcd's settings, so the caption is found by position.
    return captions.from_screen(field, binding_handle, lambda layout: _caption_of(layout, language))


class MetadataField(IAccessible):
    """A metadata field, named by its caption, which is a label without a window."""

    _field_name = ""

    def _get_name(self):
        if not self._field_name:
            self._field_name = field_name(
                self.windowHandle, self.appModule.helperLocalBindingHandle, self.appModule.language
            )
        return self._field_name
