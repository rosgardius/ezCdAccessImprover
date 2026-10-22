# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Names of controls: from the captions on screen, else from ezcd's strings or the add-on's own.

A control ezcd shows without any caption, as a button with only an image, is named by the string ezcd
has for it, or else by the add-on's own string; a parameter of the codec, by what its items are. A
button or check box whose caption repeats in its window gets the caption of its row added, and so does
a split button showing the value of a setting.
"""

import ctypes
import re

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
_COMBO_BOX_EX_CLASS = "TComboBoxEx"
# The combo box of a TComboBoxEx, which gets focus, is its child window.
COMBO_BOX_EX_CHILD_CLASS = "ComboBox"
_TOOLBAR_CLASS = "TToolBar"
_DRIVE_SETTINGS_CLASS = "TSettings2AudioCDRipperDriveForm"
_CB_GETCOUNT = 0x146
_CB_GETLBTEXT = 0x148
_CB_GETLBTEXTLEN = 0x149
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
_SOURCE_DRIVE = 462
_READ_SPEED = 463
_DISC_WRITER = 235
_WRITE_SPEED = 236

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


def _combo_box_items(hwnd: int) -> list[str]:
    items = []
    for index in range(remote.send(hwnd, _CB_GETCOUNT)):
        length = remote.send(hwnd, _CB_GETLBTEXTLEN, index)
        if length <= 0:
            continue
        buffer = ctypes.create_unicode_buffer(length + 1)
        if remote.send(hwnd, _CB_GETLBTEXT, index, ctypes.addressof(buffer)) > 0:
            items.append(buffer.value)
    return items


# The items of a codec's parameters are the codec's own, not translated: values with units, modes,
# levels. The first kind that any of its items has names the parameter.
_CODEC_PARAMETERS = (
    # Translators: The short name of the list of sample rates of a codec (44100 Hz, ...).
    (re.compile(r"\d\s*Hz$|^DSD\d+$"), _("Rate")),
    # Translators: The short name of the list of bit rates of a codec (~128 kbit/s, ...).
    (re.compile("kbit/s"), _("Bitrate")),
    # Translators: The short name of the list of channel layouts of a codec (Stereo, Mono, 5.1, ...).
    (re.compile("^(Joint )?Stereo$|^Mono$"), _("Channels")),
    # Translators: The short name of the list of bit depths of a codec (16-bit, 24-bit, ...).
    (re.compile(r"^\d+-bit"), _("Bits")),
    # Translators: The short name of the list of bit rate modes of a codec (VBR, CBR, ...).
    (re.compile("^C?[ACV]BR$"), _("Mode")),
)
# Translators: The short name of any other list of a codec's parameters: compression level,
# encoder quality, kind of signal.
_CODEC_LEVEL = _("Level")
# The format and its extension are named alike the parameters of the codec next to them, not by
# ezcd's "Format".
# Translators: The name of the list of output formats (MP3 | LAME, FLAC, ...).
_FORMAT = _("Format")
# Translators: The name of the list of file name extensions of the output format (.m4a, .aac, ...).
_EXTENSION = _("Extension")


def _codec_parameter(hwnd: int) -> _Name:
    items = _combo_box_items(hwnd)
    if not items:
        return None
    for pattern, name in _CODEC_PARAMETERS:
        if any(pattern.search(item) for item in items):
            return name
    return _CODEC_LEVEL


def _output_combo_box(hwnd: int) -> _Name:
    """The output panel: the format, with its extension right next to it."""
    layout = captions.Layout(hwnd, None, texts=[])
    _texts, left = layout.left_texts()
    if left and winUser.getClassName(left) == _COMBO_BOX_CLASS and layout.adjoins(left):
        return _EXTENSION
    right = layout.right_window()
    if (
        right
        and winUser.getClassName(right) == _COMBO_BOX_CLASS
        and captions.Layout(right, None, texts=[]).adjoins(hwnd)
    ):
        return _FORMAT
    return None


def _drive_combo_box(hwnd: int) -> _Name:
    """The drive and its speed: side by side on the ripper's tab, one above the other on the burner's."""
    layout = captions.Layout(hwnd, None, texts=[])
    others = [s for s in layout.siblings if winUser.getClassName(s) == _COMBO_BOX_CLASS]
    if len(others) != 1:
        return None
    other = layout.siblings[others[0]]
    if other.top < layout.rect.bottom and layout.rect.top < other.bottom:
        return _SOURCE_DRIVE if layout.rect.left < other.left else _READ_SPEED
    return _DISC_WRITER if layout.rect.top < other.top else _WRITE_SPEED


def _main_combo_box(hwnd: int) -> _Name:
    panel = winUser.getAncestor(hwnd, winUser.GA_PARENT)
    if child_windows(panel, _COMBO_BOX_EX_CLASS):
        return _output_combo_box(hwnd)
    if child_windows(winUser.getAncestor(panel, winUser.GA_PARENT), _COMBO_BOX_EX_CLASS):
        # The parameters of the codec lie in a panel of their own inside the output panel.
        return _codec_parameter(hwnd)
    if child_windows(panel, _TOOLBAR_CLASS) and len(child_windows(panel, _COMBO_BOX_CLASS)) == 2:
        # The toolbar opens and closes the drive's tray.
        return _drive_combo_box(hwnd)
    return None


def _settings_combo_box(hwnd: int) -> _Name:
    """Drive settings: the drive is chosen at the top of the page."""
    if winUser.getClassName(winUser.getAncestor(hwnd, winUser.GA_PARENT)) != _DRIVE_SETTINGS_CLASS:
        return None
    _texts, above = captions.Layout(hwnd, None, texts=[]).above_texts()
    return None if above else _SOURCE_DRIVE


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
    "TMainform": {_COMBO_BOX_EX_CLASS: _PROFILE, _COMBO_BOX_CLASS: _main_combo_box},
    "TSettings2Form": {"TTreeView": _CATEGORIES, _COMBO_BOX_CLASS: _settings_combo_box},
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
    return ezcd_string(hwnd, name, language) if isinstance(name, int) else name or ""


def ezcd_string(hwnd: int, number: int, language: LanguageFiles) -> str:
    """The string of the language files in the language of the control's window; empty if it has none."""
    strings = language.strings_of(_shown_texts(winUser.getAncestor(hwnd, winUser.GA_ROOT)))
    # Some strings are captions of labels: "Disc writer :".
    return strings.get(number, "").rstrip(" :") if strings else ""


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


def is_combo_box_ex_child(hwnd: int) -> bool:
    return winUser.getClassName(winUser.getAncestor(hwnd, winUser.GA_PARENT)) == _COMBO_BOX_EX_CLASS


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
            window = self.windowHandle
            if self.windowClassName == COMBO_BOX_EX_CHILD_CLASS:
                window = winUser.getAncestor(window, winUser.GA_PARENT)
            self._screen_name = captions.caption(
                window, self.appModule.helperLocalBindingHandle
            ) or fixed_name(window, self.appModule.language)
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
