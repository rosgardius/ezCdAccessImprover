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
import functools
import re
from collections.abc import Callable

import controlTypes
import winUser
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent

from . import captions, cards, panels, remote, screen, version
from .captions import Layout
from .facts.groups import String, Strings
from .language import LanguageFiles, OwnString
from .windows import child_windows, descendants, parent, root

BUTTON_CLASSES = frozenset(("TButton", "TBitBtn", "TPngBitBtn", "TCheckBox", "TRadioButton"))
_CB_GETCOUNT = 0x146
_CB_GETLBTEXT = 0x148
_CB_GETLBTEXTLEN = 0x149
_ROW_SEPARATOR = ", "
_TEXT_LENGTH = 256

type Name = String | OwnString | str | None
"""A string of the language files, the add-on's own string or the name itself."""


def _image_button(hwnd: int) -> Name:
    """A button with only an image, right next to the field it serves."""
    layout = Layout(hwnd)
    _texts, neighbour = layout.left()
    if not neighbour or not layout.adjoins(neighbour):
        return None
    neighbour_class = winUser.getClassName(neighbour)
    if neighbour_class == "TEdit":
        return OwnString("browse")
    if neighbour_class == "TComboBox":
        return version.facts.strings.filename_preview
    return None


def _button(hwnd: int) -> Name:
    text = winUser.getWindowText(hwnd)
    if text and not text.strip():
        # A tag button of the file name template that inserts a space.
        return captions.symbol_names(text)
    return _image_button(hwnd)


def _check_box(hwnd: int) -> Name:
    """A check box that switches on the effect chosen in the combo box right of it, as in DSP."""
    combo_box = Layout(hwnd).right_window()
    if winUser.getClassName(combo_box) != "TComboBox":
        return None
    return remote.text(combo_box, _TEXT_LENGTH) or None


def _move_button(hwnd: int) -> Name:
    """Edit profiles: two buttons with only an image right of the list, one above the other."""
    layout = Layout(hwnd)
    for sibling, rect in layout.siblings.items():
        if winUser.getClassName(sibling) == "TButton" and not winUser.getWindowText(sibling):
            strings = version.facts.strings
            return strings.move_up if layout.rect.top < rect.top else strings.move_down
    return None


def _metadata_tree(hwnd: int) -> Name:
    """Metadata editor: the list of files lies in a panel of the form, the list of fields deeper."""
    strings = version.facts.strings
    return strings.files if parent(parent(hwnd)) == root(hwnd) else strings.metadata


def _metadata_combo_box(hwnd: int) -> Name:
    """Metadata editor: the name of a field to add is typed, the type of a picture is chosen."""
    if child_windows(hwnd, "Edit"):
        return version.facts.strings.field_name
    return OwnString("picture_type")


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
    (re.compile(r"\d\s*Hz$|^DSD\d+$"), OwnString("rate")),
    (re.compile("kbit/s"), OwnString("bitrate")),
    (re.compile("^(Joint )?Stereo$|^Mono$"), OwnString("channels")),
    (re.compile(r"^\d+-bit"), OwnString("bits")),
    (re.compile("^C?[ACV]BR$"), OwnString("mode")),
)
_CODEC_LEVEL = OwnString("level")
# The format and its extension are named alike the parameters of the codec next to them, not by
# ezcd's "Format".
_FORMAT = OwnString("format")
_EXTENSION = OwnString("extension")
_FILE_TYPES = OwnString("file_types")
_EFFECT = OwnString("effect")


def _codec_parameter(hwnd: int) -> Name:
    items = _combo_box_items(hwnd)
    if not items:
        return None
    for pattern, name in _CODEC_PARAMETERS:
        if any(pattern.search(item) for item in items):
            return name
    return _CODEC_LEVEL


def _output_combo_box(hwnd: int) -> Name:
    """The output panel: the format, with its extension right next to it."""
    layout = Layout(hwnd)
    _texts, left = layout.left()
    if left and winUser.getClassName(left) == "TComboBox" and layout.adjoins(left):
        return _EXTENSION
    right = layout.right_window()
    if right and winUser.getClassName(right) == "TComboBox" and Layout(right).adjoins(hwnd):
        return _FORMAT
    return None


def _drive_combo_box(hwnd: int) -> Name:
    """The drive and its speed: side by side on the ripper's tab, one above the other on the burner's."""
    layout = Layout(hwnd)
    others = [s for s in layout.siblings if winUser.getClassName(s) == "TComboBox"]
    if len(others) != 1:
        return None
    other = layout.siblings[others[0]]
    strings = version.facts.strings
    if other.top < layout.rect.bottom and layout.rect.top < other.bottom:
        return strings.source_drive if layout.rect.left < other.left else strings.read_speed
    return strings.disc_writer if layout.rect.top < other.top else strings.write_speed


def _main_combo_box(hwnd: int) -> Name:
    panel = parent(hwnd)
    if child_windows(panel, "TComboBoxEx"):
        return _output_combo_box(hwnd)
    if child_windows(parent(panel), "TComboBoxEx"):
        # The parameters of the codec lie in a panel of their own inside the output panel.
        return _codec_parameter(hwnd)
    if panels.is_drive_panel(panel):
        return _drive_combo_box(hwnd)
    if panels.is_explorer_bar(panel):
        return _FILE_TYPES
    return None


def _dsp_combo_box(hwnd: int) -> Name:
    """DSP: the effect, and the kind of peak of peak normalization, named by the effect."""
    card_panels = child_windows(parent(hwnd), "TCardPanel")
    if not card_panels:
        return None
    return _EFFECT if cards.choice(card_panels[0]) == hwnd else cards.card_name(card_panels[0]) or None


def _settings_combo_box(hwnd: int) -> Name:
    """Drive settings: the drive is chosen at the top of the page."""
    if winUser.getClassName(parent(hwnd)) != "TSettings2AudioCDRipperDriveForm":
        return None
    _texts, above = Layout(hwnd).above()
    return None if above else version.facts.strings.source_drive


_ANY_FORM = {"TButton": _button, "TCheckBox": _check_box}
_CATEGORIES = OwnString("categories")
_TEMPLATES = OwnString("templates")
_RELEASE_CODE = OwnString("release_code")
_RESULTS = OwnString("results")
_FOLDER_CONTENTS = OwnString("folder_contents")
_POSITION = OwnString("position")


def _form_rules(strings: Strings) -> dict[str, dict[str, Name | Callable[[int], Name]]]:
    """The names of controls without captions by the class of their form and their own class: a name, or a
    function of the control's window giving it."""
    return {
        "TProfile_Editor": {"TVirtualStringTree": strings.profile, "TButton": _move_button},
        # The caption of the last field lies below the edge of its panel and is not drawn.
        "TMBManual": {"TEdit": _RELEASE_CODE, "TListView": _RESULTS},
        "TFC_GetMetadata": {"TVirtualStringTree": strings.tracklist},
        "TAmazon": {"TListView": _RESULTS},
        "TMainform": {
            "TComboBoxEx": strings.profile,
            "TComboBox": _main_combo_box,
            "TJamShellTree": strings.folders,
            "TJamShellList": _FOLDER_CONTENTS,
            # The player's volume and position: the only sliders of the main window.
            "TTrackBar": strings.volume_control,
            "TMyTrackBar": _POSITION,
        },
        "TSettings2Form": {"TTreeView": _CATEGORIES, "TComboBox": _settings_combo_box},
        "TDSPForm": {"TComboBox": _dsp_combo_box},
        "TNamePreview": {
            "TEdit": strings.filenames,
            "TListBox": _TEMPLATES,
            "TListView": strings.filename_preview,
        },
        "TTMetadata": {
            "TVirtualStringTree": _metadata_tree,
            "TComboBox": _metadata_combo_box,
            "TMemo": strings.field_value,
            "TListView": strings.cover_art,
        },
    }


def fixed_name(hwnd: int, language: LanguageFiles) -> str:
    """The name of a control ezcd shows without a caption; empty if none is known for it."""
    control_class = winUser.getClassName(hwnd)
    form_rules = _form_rules(version.facts.strings).get(winUser.getClassName(root(hwnd)), {})
    rule = form_rules.get(control_class) or _ANY_FORM.get(control_class)
    return name_text(hwnd, rule(hwnd) if callable(rule) else rule, language)


def ezcd_string(hwnd: int, string: String, language: LanguageFiles) -> str:
    """The string of the language files in the language of the control's window; empty if it has none."""
    # Some strings are captions of labels: "Disc writer :".
    return language.window_strings(hwnd).get(string.number, "").rstrip(" :")


def name_text(hwnd: int, name: Name, language: LanguageFiles) -> str:
    """The name in the language of the control's window; empty if there is none."""
    if isinstance(name, String):
        return ezcd_string(hwnd, name, language)
    if isinstance(name, OwnString):
        return language.own_string(hwnd, name)
    return name or ""


def _repeats(hwnd: int, caption: str) -> bool:
    """Whether another button or check box in the window has the same caption."""
    return any(
        other != hwnd
        and winUser.getClassName(other) in BUTTON_CLASSES
        and winUser.getWindowText(other) == caption
        and winUser.isWindowVisible(other)
        for other in descendants(root(hwnd))
    )


def _row_caption(layout: Layout, language: LanguageFiles) -> str:
    """The text nearest to the control on its row, else the caption or name of the row's first window."""
    text = layout.row_text()
    if text:
        return text
    first = layout.row_start()
    return (captions.choice_caption(first) or fixed_name(first, language)) if first else ""


def is_combo_box_ex_child(hwnd: int) -> bool:
    return winUser.getClassName(parent(hwnd)) == "TComboBoxEx"


def is_combo_box_edit(hwnd: int) -> bool:
    """Whether the window is the edit of a combo box where a value is typed, which has focus in place of the
    combo box."""
    return winUser.getClassName(parent(hwnd)) == "TComboBox"


class Captioned(IAccessible):
    """A control without an MSAA name, named by the caption ezcd draws beside it or else by a string."""

    def _own_name(self) -> str:
        return super()._get_name() or ""

    def _get_name(self):
        return self._own_name() or self._screen_name

    def _caption_window(self) -> int:
        """The window whose caption names the control."""
        if self.windowClassName == "ComboBox":
            # The combo box of a TComboBoxEx, which gets focus, is its child window.
            return parent(self.windowHandle)
        return self.windowHandle

    @functools.cached_property
    def _screen_name(self) -> str:
        window = self._caption_window()
        language = self.appModule.language
        return captions.caption(
            window, self.appModule.helperLocalBindingHandle, self.processHandle, language
        ) or fixed_name(window, language)


class ComboBoxEdit(IAccessible):
    """The edit of a combo box where a value is typed, presented as the combo box.

    NVDA would report the combo box as an ancestor of the edit, and the edit without a name.
    """

    role = controlTypes.Role.COMBOBOX

    @functools.cached_property
    def _combo_box(self) -> IAccessible | None:
        return getNVDAObjectFromEvent(parent(self.windowHandle), winUser.OBJID_CLIENT, 0)

    def _get_name(self):
        return self._combo_box.name if self._combo_box is not None else super()._get_name()

    def _get_states(self):
        # NVDA reads the text of an object that is not an edit only if it is editable.
        states = super()._get_states() | {controlTypes.State.EDITABLE}
        if self._combo_box is not None:
            states |= self._combo_box.states & {controlTypes.State.EXPANDED, controlTypes.State.COLLAPSED}
        return states

    def _get_container(self):
        return self._combo_box.container if self._combo_box is not None else super()._get_container()


class CaptionedButton(IAccessible):
    """A button, check box or radio button, named by a string when it has no caption.

    Its caption gets the caption of its row when it repeats in the window, and on a split button,
    whose caption is the value of the setting its row's check box names.
    """

    @functools.cached_property
    def _full_name(self) -> str:
        name = super()._get_name() or ""
        if not name.strip():
            return fixed_name(self.windowHandle, self.appModule.language)
        # A tag of Filename preview inserting a separator, as \ or -.
        name = captions.spoken(name)
        if self.role == controlTypes.Role.SPLITBUTTON:
            row = captions.choice_caption(Layout(self.windowHandle).row_start())
        elif _repeats(self.windowHandle, winUser.getWindowText(self.windowHandle)):
            row = captions.from_screen(
                self.windowHandle,
                self.appModule.helperLocalBindingHandle,
                lambda layout: _row_caption(layout, self.appModule.language),
            )
        else:
            return name
        return f"{name}{_ROW_SEPARATOR}{row}" if row and row != name else name

    def _get_name(self):
        return self._full_name

    def event_nameChange(self):
        # ezcd changes some captions, as Cancel to Close when the check for updates ends.
        self.__dict__.pop("_full_name", None)
        super().event_nameChange()

    def event_stateChange(self):
        super().event_stateChange()
        if self.windowClassName in captions.CHOICE_CLASSES:
            # ezcd fills the background of the whole parent as a check box enables controls, and draws
            # again only what changed: the display model loses the other captions and units.
            screen.redraw(parent(self.windowHandle))
