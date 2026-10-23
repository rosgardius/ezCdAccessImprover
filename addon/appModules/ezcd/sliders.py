# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Sliders that show their value in a field right next to them, as in DSP.

MSAA gives such a slider only its position as a percentage of its range, which says nothing of the value
and repeats on small steps (0.1 dB of 24 dB); the field shows the value.
"""

import winUser

from . import remote
from .captions import Layout
from .names import Captioned

_TEXT_LENGTH = 64


def value_field(hwnd: int) -> int:
    """The field right next to the slider, the top one of several; 0 if none."""
    field = Layout(hwnd).right_window()
    if field and winUser.getClassName(field) == "TEdit" and Layout(field).adjoins(hwnd):
        return field
    return 0


class FieldSlider(Captioned):
    """A slider with the name and the value of the field that shows its value."""

    def _caption_window(self) -> int:
        return value_field(self.windowHandle) or self.windowHandle

    def _get_value(self):
        field = value_field(self.windowHandle)
        return (remote.text(field, _TEXT_LENGTH) if field else "") or super()._get_value()
