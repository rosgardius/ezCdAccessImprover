# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Names of controls: from the captions on screen, else from ezcd's strings or the add-on's own.

A control ezcd shows without any caption, as a button with only an image, is named by the string ezcd
has for it, or else by the add-on's own string. A button or check box whose caption repeats in its
window gets the caption of its row added, and so does a split button showing the value of a setting.
"""

import ctypes

import addonHandler
import characterProcessing
import controlTypes
import winUser
from NVDAObjects.IAccessible import IAccessible
from speech.speech import getCurrentLanguage

from . import captions, remote
from .language import LanguageFiles
from .windows import child_windows, descendants

addonHandler.initTranslation()

BUTTON_CLASSES = frozenset(("TButton", "TBitBtn", "TPngBitBtn", "TCheckBox", "TRadioButton"))
_BUTTON_CLASS = "TButton"
_CHECK_BOX_CLASS = "TCheckBox"
_EDIT_CLASS = "TEdit"
_COMBO_BOX_CLASS = "TComboBox"
_COMBO_BOX_EDIT_CLASS = "Edit"
_ROW_SEPARATOR = ", "
_TEXT_LENGTH = 256

# Strings of the language files.
_FILENAME_PREVIEW = 266
_MOVE_UP = 241
_MOVE_DOWN = 242
_PROFILE = 582
_FILENAMES = 180
_FILES = 494
_METADATA = 101
_FIELD_NAME = 834
_FIELD_VALUE = 835
_COVER_ART = 349
_TRACKLIST = 137

# A name is a string number of the language files or the add-on's own string.
type _Name = int | str | None


def _image_button(hwnd: int) -> _Name:
    """A button with only an image, right next to the field it serves."""
    layout = captions.Layout(hwnd, None, texts=[])
    _texts, neighbour = layout.left_texts()
    if not neighbour or not layout.adjoins(neighbour):
        return None
    neighbour_class = winUser.getClassName(neighbour)
    if neighbour_class == _EDIT_CLASS:
        # Translators: The name of a button that opens a dialog to choose a folder or a file.
        return _("Browse")
    if neighbour_class == _COMBO_BOX_CLASS:
        return _FILENAME_PREVIEW
    return None


def _button(hwnd: int) -> _Name:
    text = winUser.getWindowText(hwnd)
    if text and not text.strip():
        # A tag button of the file name template that inserts a space.
        language = getCurrentLanguage()
        return " ".join(characterProcessing.processSpeechSymbol(language, c) for c in text)
    return _image_button(hwnd)


def _check_box(hwnd: int) -> _Name:
    """A check box that switches on the effect chosen in the combo box right of it, as in DSP."""
    combo_box = captions.Layout(hwnd, None, texts=[]).right_window()
    if winUser.getClassName(combo_box) != _COMBO_BOX_CLASS:
        return None
    buffer = ctypes.create_unicode_buffer(_TEXT_LENGTH)
    if not remote.send(combo_box, winUser.WM_GETTEXT, _TEXT_LENGTH, ctypes.addressof(buffer)):
        return None
    return buffer.value


def _move_button(hwnd: int) -> _Name:
    """Edit profiles: two buttons with only an image right of the list, one above the other."""
    layout = captions.Layout(hwnd, None, texts=[])
    for sibling, rect in layout.siblings.items():
        if winUser.getClassName(sibling) == _BUTTON_CLASS and not winUser.getWindowText(sibling):
            return _MOVE_UP if layout.rect.top < rect.top else _MOVE_DOWN
    return None


def _metadata_tree(hwnd: int) -> _Name:
    """Metadata editor: the list of files lies in a panel of the form, the list of fields deeper."""
    panel = winUser.getAncestor(hwnd, winUser.GA_PARENT)
    form = winUser.getAncestor(hwnd, winUser.GA_ROOT)
    return _FILES if winUser.getAncestor(panel, winUser.GA_PARENT) == form else _METADATA


def _metadata_combo_box(hwnd: int) -> _Name:
    """Metadata editor: the name of a field to add is typed, the type of a picture is chosen."""
    if child_windows(hwnd, _COMBO_BOX_EDIT_CLASS):
        return _FIELD_NAME
    # Translators: The name of the list of picture types (front cover, back cover, ...)
    # in the metadata editor.
    return _("Picture type")


_ANY_FORM = {_BUTTON_CLASS: _button, _CHECK_BOX_CLASS: _check_box}
# Translators: The name of the list of settings pages.
_CATEGORIES = _("Categories")
# Translators: The name of the list of file name templates used before.
_TEMPLATES = _("Templates")
# Translators: The name of the field for the release code (catalogue number) in the manual search of
# metadata.
_RELEASE_CODE = _("Release code")
# Translators: The name of the list of releases found by the manual search of metadata.
_RESULTS = _("Results")
_FORMS = {
    "TProfile_Editor": {"TVirtualStringTree": _PROFILE, _BUTTON_CLASS: _move_button},
    # The caption of the last field lies below the edge of its panel and is not drawn.
    "TMBManual": {_EDIT_CLASS: _RELEASE_CODE, "TListView": _RESULTS},
    "TFC_GetMetadata": {"TVirtualStringTree": _TRACKLIST},
    "TSettings2Form": {"TTreeView": _CATEGORIES},
    "TNamePreview": {_EDIT_CLASS: _FILENAMES, "TListBox": _TEMPLATES, "TListView": _FILENAME_PREVIEW},
    "TTMetadata": {
        "TVirtualStringTree": _metadata_tree,
        _COMBO_BOX_CLASS: _metadata_combo_box,
        "TMemo": _FIELD_VALUE,
        "TListView": _COVER_ART,
    },
}


def _shown_texts(window: int) -> set[str]:
    texts = {winUser.getWindowText(window)}
    texts.update(winUser.getWindowText(w) for w in descendants(window) if winUser.isWindowVisible(w))
    return texts


def fixed_name(hwnd: int, language: LanguageFiles) -> str:
    """The name of a control ezcd shows without a caption; empty if none is known for it."""
    form = winUser.getAncestor(hwnd, winUser.GA_ROOT)
    control_class = winUser.getClassName(hwnd)
    rule = _FORMS.get(winUser.getClassName(form), {}).get(control_class) or _ANY_FORM.get(control_class)
    name = rule(hwnd) if callable(rule) else rule
    if not isinstance(name, int):
        return name or ""
    strings = language.strings_of(_shown_texts(form))
    return strings.get(name, "") if strings else ""


def _repeats(hwnd: int, caption: str) -> bool:
    """Whether another button or check box in the window has the same caption."""
    return any(
        other != hwnd
        and winUser.getClassName(other) in BUTTON_CLASSES
        and winUser.getWindowText(other) == caption
        and winUser.isWindowVisible(other)
        for other in descendants(winUser.getAncestor(hwnd, winUser.GA_ROOT))
    )


def _row_caption(layout: captions.Layout, language: LanguageFiles, choice_only: bool) -> str:
    """The text nearest to the control on its row, else the caption or name of the row's first window."""
    if not choice_only:
        text = layout.row_text()
        if text:
            return text
    first = next(iter(layout.row_windows()), 0)
    if not first:
        return ""
    return captions.choice_caption(first) or ("" if choice_only else fixed_name(first, language))


def row_caption(hwnd: int, binding_handle, language: LanguageFiles, choice_only: bool = False) -> str:
    """The caption of the control's row; with ``choice_only``, only a check box or radio button opening it."""
    if not binding_handle:
        return ""
    caption = _row_caption(captions.Layout(hwnd, binding_handle), language, choice_only)
    if not caption and not choice_only:
        # The display model has only what was drawn since the parent last filled its background.
        caption = _row_caption(captions.Layout(hwnd, binding_handle, repaint=True), language, choice_only)
    return caption


class Captioned(IAccessible):
    """A control without an MSAA name, named by the caption ezcd draws beside it or else by a string."""

    _screen_name: str | None = None

    def _own_name(self) -> str:
        return super()._get_name() or ""

    def _get_name(self):
        name = self._own_name()
        if name:
            return name
        if self._screen_name is None:
            self._screen_name = captions.caption(
                self.windowHandle, self.appModule.helperLocalBindingHandle
            ) or fixed_name(self.windowHandle, self.appModule.language)
        return self._screen_name


class CaptionedButton(IAccessible):
    """A button, check box or radio button, named by a string when it has no caption.

    Its caption gets the caption of its row when it repeats in the window, and on a split button,
    whose caption is the value of the setting its row's check box names.
    """

    _full_name: str | None = None

    def _get_name(self):
        if self._full_name is None:
            self._full_name = self._compute_name(super()._get_name() or "")
        return self._full_name

    def _compute_name(self, name: str) -> str:
        if not name.strip():
            return fixed_name(self.windowHandle, self.appModule.language)
        split = self.role == controlTypes.Role.SPLITBUTTON
        if not split and not _repeats(self.windowHandle, winUser.getWindowText(self.windowHandle)):
            return name
        row = row_caption(
            self.windowHandle, self.appModule.helperLocalBindingHandle, self.appModule.language, split
        )
        return f"{name}{_ROW_SEPARATOR}{row}" if row and row != name else name
