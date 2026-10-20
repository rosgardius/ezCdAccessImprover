# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The window shown while files are converted."""

import enum

import addonHandler
import winUser
from NVDAObjects.IAccessible import IAccessible

addonHandler.initTranslation()

PROGRESS_BAR_CLASS = "TProgressBar"
_WINDOW_CLASSES = ("TConvertWnd", "TConvertWnd_Single")
_PANEL_CLASS = "TPanel"


class Bar(enum.Enum):
    CONVERTER = enum.auto()
    TOTAL = enum.auto()


def bar_kind(hwnd: int) -> Bar | None:
    """Which bar of the conversion window a progress bar window is, ``None`` if it is in another window."""
    if winUser.getClassName(winUser.getAncestor(hwnd, winUser.GA_ROOT)) not in _WINDOW_CLASSES:
        return None
    # The total bar is in the summary panel, inside the panel with the file list. A converter bar is in
    # the grid panel, or, in the window for one converter, in a panel right on the form.
    parent = winUser.getAncestor(hwnd, winUser.GA_PARENT)
    if (
        winUser.getClassName(parent) == _PANEL_CLASS
        and winUser.getClassName(winUser.getAncestor(parent, winUser.GA_PARENT)) == _PANEL_CLASS
    ):
        return Bar.TOTAL
    return Bar.CONVERTER


class TotalProgressBar(IAccessible):
    """The progress of the whole conversion; its caption is a label without a window."""

    def _get_name(self):
        # Translators: The name of the progress bar of the whole conversion in EZ CD Audio Converter.
        return _("Total progress")
