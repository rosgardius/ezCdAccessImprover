# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Panels of the main window, recognised by the windows they hold."""

from .cover_art import COVER_CLASS
from .windows import child_windows, descendants, rect, tab_stop_below, tab_stop_right


def is_drive_panel(panel: int) -> bool:
    """Whether the panel holds the drive, its speed and the toolbar of the drive's tray."""
    return bool(child_windows(panel, "TToolBar")) and len(child_windows(panel, "TComboBox")) == 2


def is_explorer_bar(panel: int) -> bool:
    """Whether the panel is the row above the explorer, with the breadcrumb bar."""
    return bool(child_windows(panel, "TJamShellBreadCrumbBar"))


def is_player_panel(panel: int) -> bool:
    """Whether the panel is the player of the Audio CD Ripper tab, with the volume and the position."""
    return bool(child_windows(panel, "TTrackBar")) and bool(child_windows(panel, "TMyTrackBar"))


def is_metadata_panel(panel: int) -> bool:
    """Whether the panel holds the metadata fields and the cover art."""
    return bool(child_windows(panel, COVER_CLASS))


def stop_after(tab: int, window: int) -> int:
    """The Tab stop of the tab after a window that VCL skips, by the screen: right of it on its line, else
    below it; 0 if none.

    While the metadata panel is left or right of the list, it is beside every row of the tab, but its
    fields come after none of them.
    """
    edge = rect(window)
    metadata = next((w for w in descendants(tab) if is_metadata_panel(w)), 0)
    return tab_stop_right(tab, edge, metadata) or tab_stop_below(tab, edge, metadata)
