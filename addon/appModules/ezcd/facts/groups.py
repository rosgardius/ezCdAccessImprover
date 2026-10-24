# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The groups of a set of facts, by parts of ezcd's UI. Sizes are in design units (DFM): forms keep them
scaled by the window's DPI / 96."""

from dataclasses import dataclass


@dataclass(frozen=True)
class String:
    """A string of ezcd's language files."""

    number: int
    english: str
    """Its text in ``english.uni``, which tells what the number means."""


@dataclass(frozen=True)
class Language:
    name: String
    """The string naming the language of its file, as ezcd's settings name it: "English (customizable)"."""
    registry_key: str
    """ezcd's settings under ``HKEY_CURRENT_USER``."""
    registry_value: str
    """The value of ezcd's settings naming the language."""


@dataclass(frozen=True)
class Strings:
    """Strings of the language files that name a part of ezcd or tell it apart."""

    converter_tab: String
    """The captions of the main window's tabs, as the following two."""
    ripper_tab: String
    burner_tab: String
    audio_cd_page: String
    """The captions of the pages of the Disc Burner tab and of their buttons, as the following two."""
    mp3_disc_page: String
    data_disc_page: String
    files: String
    """The list of files: of the Audio Converter tab, of the metadata editor."""
    tracklist: String
    """The list of tracks: of the Audio CD Ripper tab, of the Audio CD page, of Get metadata."""
    filelist: String
    """The list of the MP3 disc and Data disc pages."""
    disc: String
    """The disc, the only top-level node of the list of the MP3 disc and Data disc pages."""
    lyrics: String
    """The column of the lyrics in the list of files."""
    resume: String
    """The caption of Pause in the conversion window while it is paused."""
    filename_generation: String
    """The page of Settings that the button of Filename preview opens."""
    filename_preview: String
    move_up: String
    """The buttons moving an item of a list, as the following one."""
    move_down: String
    profile: String
    filenames: String
    """The template field of Filename preview."""
    metadata: String
    field_name: String
    """The metadata editor: the name of a field to add, as the value of the next."""
    field_value: String
    cover_art: String
    source_drive: String
    read_speed: String
    disc_writer: String
    write_speed: String
    folders: String
    """The folder tree of the explorer."""
    volume_control: String


@dataclass(frozen=True)
class TopPanel:
    """The top panel of one of the main window's tabs."""

    main_images: tuple[int, ...]
    """The images of the button of the tab's main action; one button for keys, by the first image."""
    main_strings: tuple[String, ...]
    """The captions of that button."""
    main_shortcut: bool
    """Whether F8 presses the main action."""
    menu_buttons: frozenset[tuple[int, int]]
    """The buttons that open a menu, by the image of the button and the number of buttons with that image to
    its left."""
    context_menu_buttons: frozenset[tuple[int, int]]
    """The buttons whose right click opens a menu of more actions, by the same key."""


@dataclass(frozen=True)
class Explorer:
    view_explorer: int
    """The image of View Explorer, which shows and hides the explorer."""
    button_strings: dict[int, String]
    """ezcd's strings for the buttons of its toolbars, by image."""


@dataclass(frozen=True)
class Tray:
    open_tray: int
    """The image of Open tray; it and Close tray take turns."""
    close_tray: int
    button_strings: dict[int, String]
    """ezcd's strings for the buttons, by image."""


@dataclass(frozen=True)
class Player:
    button_strings: dict[int, String]
    """ezcd's strings for the buttons, by image: their hints."""


@dataclass(frozen=True)
class Metadata:
    number: String
    """The captions of the number fields and the names of the totals right of them, as the following three."""
    disc_number: String
    total_tracks: String
    total_discs: String
    captions: tuple[String, ...]
    """All captions of the metadata panel; they tell the language, as short ones are the same in several."""


@dataclass(frozen=True)
class Rating:
    caption: String
    stars: int
    star_width: int
    """A star; a click at the rating's left edge sets no stars."""


@dataclass(frozen=True)
class Counter:
    """The buttons of a counter: squares beside the edit, level with its top."""

    button_size: int
    button_gap: int
    """From the edit, 1 to 3 units by the window."""


@dataclass(frozen=True)
class ServiceButtons:
    """The buttons that move the selected metadata service in Settings: one under the other, right of the list
    and level with its top."""

    left: int
    """From the right edge of the list."""
    width: int
    height: int


@dataclass(frozen=True)
class SummaryField:
    """A label and value pair of the summary panel of the conversion window."""

    row: int
    label: int
    """The column of the label, as ``value`` that of the value."""
    value: int


@dataclass(frozen=True)
class ConvertWindow:
    """The summary panel of the conversion window: the row of the total bar and the percentage right of it,
    and the grid of label and value pairs under it."""

    bar_row: int
    rows: tuple[int, ...]
    columns: tuple[int, ...]
    converted: SummaryField
    elapsed: SummaryField
    errors: SummaryField
    remaining: SummaryField
    skipped: SummaryField
    speed: SummaryField
