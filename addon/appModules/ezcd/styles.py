# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Windows that VCL styles add to ezcd's own: in the dark themes, a window over each scroll bar of a list,
tree or scroll box, which draws the bar in the colours of the theme."""

from NVDAObjects.IAccessible import IAccessible

SCROLL_BAR_COVER_CLASSES = frozenset(
    ("TScrollingStyleHook.TScrollWindow", "TVclStyleScrollBarsHook.TScrollWindow")
)


class ScrollBarCover(IAccessible):
    """A window over a scroll bar: no content of its own, as the scroll bar under it is the control's.

    Without this, simple review mode stops at it before the scroll bar and NVDA says "unknown".
    """

    presentationType = IAccessible.presType_unavailable
