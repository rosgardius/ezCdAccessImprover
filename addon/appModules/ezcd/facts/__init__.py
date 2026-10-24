# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Facts about ezcd that the app module relies on: one set for each version of ezcd that changed any of them.

The package imports only the standard library and itself, so that the checker in ``ezcheck`` loads it
without NVDA.
"""

import enum
import re
from dataclasses import dataclass

from .groups import (
    ConvertWindow,
    Counter,
    Explorer,
    Language,
    Metadata,
    Player,
    Rating,
    ServiceButtons,
    String,
    Strings,
    SummaryField,
    TopPanel,
    Tray,
)
from .objects import Vcl


@dataclass(frozen=True)
class Facts:
    since: tuple[int, ...]
    """The version of ezcd from which the set holds."""
    vcl: Vcl
    language: Language
    strings: Strings
    top_panels: tuple[TopPanel, ...]
    """Of the Audio Converter, Audio CD Ripper and Disc Burner tabs."""
    explorer: Explorer
    tray: Tray
    player: Player
    metadata: Metadata
    rating: Rating
    counter: Counter
    service_buttons: ServiceButtons
    convert_window: ConvertWindow


# From the oldest version to the newest; a newer set is ``dataclasses.replace`` of the one before it.
VERSIONS: tuple[Facts, ...] = (
    Facts(
        since=(13, 2, 1),
        vcl=Vcl(
            vmt_class_name=-136,
            controls=0x398,
            list_items=8,
            list_count=16,
            bounds=0x90,
            visible_enabled=0xA9,
            on_click=0x1F8,
            text=0x2D0,
            rating_stars=0x340,
            check_state=16,
        ),
        language=Language(
            name=String(0, "English (customizable)"),
            registry_key=r"Software\Poikosoft\EZ CD Audio Converter",
            registry_value="k82",
        ),
        strings=Strings(
            converter_tab=String(172, "Audio Converter"),
            ripper_tab=String(171, "Audio CD Ripper"),
            burner_tab=String(390, "Disc Burner"),
            audio_cd_page=String(470, "Audio CD"),
            mp3_disc_page=String(471, "MP3 disc"),
            data_disc_page=String(472, "Data disc"),
            files=String(494, "Files"),
            tracklist=String(137, "Tracklist"),
            filelist=String(141, "Filelist"),
            disc=String(486, "Disc"),
            lyrics=String(474, "Lyrics"),
            resume=String(145, "Resume"),
            filename_generation=String(576, "Filename generation"),
            filename_preview=String(266, "Filename preview"),
            move_up=String(241, "Move up"),
            move_down=String(242, "Move down"),
            profile=String(582, "Profile"),
            filenames=String(180, "Filenames"),
            metadata=String(101, "Metadata"),
            field_name=String(834, "Name"),
            field_value=String(835, "Value"),
            cover_art=String(349, "Cover Art"),
            source_drive=String(462, "Source drive"),
            read_speed=String(463, "Read speed"),
            disc_writer=String(235, "Disc writer"),
            write_speed=String(236, "Write speed"),
            folders=String(380, "Folders"),
            volume_control=String(109, "Volume Control"),
        ),
        top_panels=(
            TopPanel(
                main_images=(1,),
                main_strings=(String(232, "Convert"), String(406, "Convert")),
                main_shortcut=True,
                # Audio Converter ▼, Metadata ▼, View, Help
                menu_buttons=frozenset(((0, 0), (4, 0), (15, 0), (19, 0))),
                # Save metadata: modified files, all files
                context_menu_buttons=frozenset(((7, 0),)),
            ),
            TopPanel(
                main_images=(0,),
                main_strings=(String(176, "Rip CD"),),
                main_shortcut=True,
                # CD Ripper ▼, Disc ▼, Metadata ▼, View, Help
                menu_buttons=frozenset(((1, 0), (3, 0), (4, 0), (15, 0), (19, 0))),
                context_menu_buttons=frozenset(),
            ),
            TopPanel(
                # On the Audio CD, MP3 disc and Data disc pages.
                main_images=(13, 14, 10),
                main_strings=(String(239, "Burn CD"), String(391, "Burn DVD"), String(392, "Burn disc")),
                main_shortcut=False,
                # Disc Burner ▼ (Settings is (2, 1)), View, Help
                menu_buttons=frozenset(((2, 0), (15, 0), (19, 0))),
                context_menu_buttons=frozenset(),
            ),
        ),
        explorer=Explorer(
            view_explorer=29,
            button_strings={
                # Pressed while the explorer is shown.
                29: String(704, "View Explorer"),
                33: String(327, "Add files..."),
                32: String(328, "Add folder..."),
                25: String(489, "Go to Computer"),
                26: String(490, "Go to Music"),
                30: String(701, "Move backward in history"),
                31: String(702, "Move forward in history"),
                3: String(703, "Go up"),
                # The menu of the list's view: List, Details, Icons, Large icons.
                4: String(346, "View"),
            },
        ),
        tray=Tray(
            open_tray=8,
            close_tray=7,
            button_strings={
                8: String(191, "Open tray"),
                7: String(192, "Close tray"),
                # A gear without a hint, on the Audio CD Ripper tab only.
                9: String(434, "Drive settings"),
            },
        ),
        player=Player(
            button_strings={
                1: String(185, "Previous track"),
                2: String(186, "Rewind"),
                0: String(184, "Play"),
                3: String(187, "Forward"),
                4: String(188, "Next track"),
                5: String(189, "Stop"),
                6: String(190, "Pause"),
            },
        ),
        metadata=Metadata(
            number=String(590, "Number:"),
            disc_number=String(598, "Disc number:"),
            total_tracks=String(801, "<Total Tracks>"),
            total_discs=String(503, "<Total Discs>"),
            captions=(
                String(588, "Track artist:"),
                String(589, "Title:"),
                String(590, "Number:"),
                String(591, "Composer:"),
                String(592, "Rating:"),
                String(593, "Part of compilation:"),
                String(594, "Album artist:"),
                String(595, "Album:"),
                String(596, "Year:"),
                String(597, "Genre:"),
                String(598, "Disc number:"),
                String(599, "Publisher:"),
                String(600, "Copyright:"),
                String(601, "Encoded by:"),
                String(602, "URL:"),
                String(603, "Comment:"),
                String(608, "Track artist:"),
                String(609, "Compilation:"),
                String(900, "Lyrics:"),
                String(901, "Label:"),
                String(902, "Catalog number:"),
                String(903, "Lyricist:"),
                String(904, "Arranger:"),
                String(905, "Conductor:"),
                String(906, "Language:"),
                String(934, "Mixer:"),
                String(935, "Engineer:"),
                String(936, "Producer:"),
            ),
        ),
        rating=Rating(caption=String(592, "Rating:"), stars=5, star_width=16),
        counter=Counter(button_size=23, button_gap=2),
        service_buttons=ServiceButtons(left=4, width=23, height=22),
        convert_window=ConvertWindow(
            bar_row=16,
            rows=(0, 16, 37, 53, 69),
            columns=(0, 128, 264, 384, 528, 648),
            converted=SummaryField(37, 0, 128),
            elapsed=SummaryField(37, 264, 384),
            errors=SummaryField(53, 0, 128),
            remaining=SummaryField(53, 264, 384),
            skipped=SummaryField(69, 0, 128),
            speed=SummaryField(69, 264, 384),
        ),
    ),
)
LAST_TESTED = (13, 2, 1, 1)


class Match(enum.Enum):
    """How the set was chosen for the version."""

    KNOWN = enum.auto()
    """The version lies between the first set and the last tested version."""
    NEWER = enum.auto()
    """Newer than the last tested version: the last set."""
    OLDER = enum.auto()
    """Older than the first set: the first set."""
    UNKNOWN = enum.auto()
    """The version could not be read: the last set."""


@dataclass(frozen=True)
class Selection:
    facts: Facts
    match: Match
    version: tuple[int, ...]
    """The version as read, empty if it could not be."""


def parse(product_version: str | None) -> tuple[int, ...]:
    """The numbers of the version, as ``(13, 2, 1, 1)`` for ``"13.2.1.1"``; empty if it has none."""
    return tuple(int(number) for number in re.findall(r"\d+", product_version or ""))


def select(product_version: str | None) -> Selection:
    """The set of facts for the version of ezcd."""
    version = parse(product_version)
    if not version:
        return Selection(VERSIONS[-1], Match.UNKNOWN, version)
    if version < VERSIONS[0].since:
        return Selection(VERSIONS[0], Match.OLDER, version)
    if version > LAST_TESTED:
        return Selection(VERSIONS[-1], Match.NEWER, version)
    facts = next(f for f in reversed(VERSIONS) if f.since <= version)
    return Selection(facts, Match.KNOWN, version)
