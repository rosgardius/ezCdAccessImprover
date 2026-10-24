# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Metadata fields of the main window's tabs, captioned by labels without windows."""

import winUser
from NVDAObjects.IAccessible import IAccessible

from . import captions, panels, screen, top_panel, vcl, version
from .language import LanguageFiles
from .windows import child_windows, parent

FIELD_CLASSES = ("TEdit", "TMemo", "TCheckBox")


def is_metadata_field(hwnd: int) -> bool:
    """A field of the metadata panel of the converter or the ripper, or a CD-Text field of the burner."""
    panel = parent(hwnd)
    if winUser.getClassName(panel) != "TPanel":
        return False
    if panels.is_metadata_panel(panel):
        return True
    # The CD-Text panel is under the list of tracks, on a page of the Disc Burner tab's own page control.
    page = parent(panel)
    return (
        winUser.getClassName(page) == "TTabSheet"
        and not top_panel.is_main_window_tab(page)
        and bool(child_windows(page, "TVirtualStringTree"))
    )


def _own_caption(texts: list[screen.Text]) -> list[screen.Text]:
    """The texts after the last caption before the field's own: a control without a window, as the rating,
    may lie with its caption between the field and the window left of it. Every caption ends in a colon."""
    ends = [i for i, text in enumerate(texts[:-1]) if text.text.endswith(":")]
    return texts[ends[-1] + 1 :] if ends else texts


def _caption_of(layout: captions.Layout, language: LanguageFiles) -> str:
    texts, neighbour = layout.left()
    caption = screen.joined(_own_caption(texts))
    if caption and neighbour and not any(c.isalnum() for c in caption):
        # The total right of a track or disc number is captioned only by "/" between the two.
        number = screen.joined(_own_caption(captions.Layout(neighbour, texts=layout.texts).left()[0]))
        facts = version.facts.metadata
        strings = language.strings({t.text for t in layout.texts}, facts.captions)
        totals = ((facts.number, facts.total_tracks), (facts.disc_number, facts.total_discs))
        for number_string, total_string in totals:
            if strings.get(number_string.number) == number and strings.get(total_string.number):
                return strings[total_string.number].strip("<>")
        return f"{number.rstrip(' :')} {caption}".strip()
    return caption.rstrip(" :")


def field_name(field: int, binding_handle, process_handle: int, language: LanguageFiles) -> str:
    """The caption of the field in the language of ezcd, from the labels in ezcd's memory, else from the
    display model; empty if neither has it."""
    # The layout depends on the fields chosen in ezcd's settings, so the caption is found by position.
    labels = vcl.label_texts(parent(field), process_handle, language)
    caption = _caption_of(captions.Layout(field, texts=labels), language) if labels else ""
    return caption or captions.from_screen(
        field, binding_handle, lambda layout: _caption_of(layout, language)
    )


class MetadataField(IAccessible):
    """A metadata field, named by its caption, which is a label without a window."""

    _field_name = ""

    def _get_name(self):
        if not self._field_name:
            self._field_name = field_name(
                self.windowHandle,
                self.appModule.helperLocalBindingHandle,
                self.processHandle,
                self.appModule.language,
            )
        return self._field_name
