# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Panels of the main window, recognised by the windows they hold."""

from .windows import child_windows


def is_drive_panel(panel: int) -> bool:
    """Whether the panel holds the drive, its speed and the toolbar of the drive's tray."""
    return bool(child_windows(panel, "TToolBar")) and len(child_windows(panel, "TComboBox")) == 2


def is_explorer_bar(panel: int) -> bool:
    """Whether the panel is the row above the explorer, with the breadcrumb bar."""
    return bool(child_windows(panel, "TJamShellBreadCrumbBar"))


def is_player_panel(panel: int) -> bool:
    """Whether the panel is the player of the Audio CD Ripper tab, with the volume and the position."""
    return bool(child_windows(panel, "TTrackBar")) and bool(child_windows(panel, "TMyTrackBar"))
