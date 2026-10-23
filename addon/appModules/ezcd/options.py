# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Sections of Options of the Audio Converter and Audio CD Ripper tabs.

A section is headed by a label without a window, above its first check box; NVDA presents it as a
grouping between the form and the section's controls.
"""

import controlTypes
import winUser
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent
from NVDAObjects.window import Window

from . import screen, windows
from .windows import parent, tab_stop_rows

_FORMS = frozenset(("TConverterOptions", "TRipperOptions"))


def form_of(hwnd: int) -> int:
    """The Options form holding the window, 0 if it is in none."""
    return windows.form_of(hwnd, _FORMS)


def _dialog_buttons(rows: list[list[int]]) -> list[int]:
    """The last row if it holds only buttons, as OK: the dialog's own, in no section."""
    last = rows[-1] if rows else []
    return last if all(winUser.getClassName(w) == "TButton" for w in last) else []


def section_heading(control: int, form: int, binding_handle) -> str:
    """The heading of the section holding the form's child window; empty for the dialog's buttons, or if
    the display model has no headings."""
    if not binding_handle or control in _dialog_buttons(tab_stop_rows(form)):
        return ""
    # The form itself draws only the headings.
    headings = screen.texts(form, binding_handle)
    if not headings and screen.redraw(form):
        headings = screen.texts(form, binding_handle)
    top = screen.logical_rect(control, form).top
    above = [line for line in screen.lines(headings) if line[0].top <= top]
    return screen.joined(above[-1]) if above else ""


class Section(Window):
    """A section of Options, named by its heading."""

    role = controlTypes.Role.GROUPING

    def __init__(self, windowHandle: int, heading: str):
        super().__init__(windowHandle)
        self._heading = heading

    def _isEqual(self, other):
        return super()._isEqual(other) and other._heading == self._heading

    def _get_name(self):
        return self._heading

    def _get_parent(self):
        return getNVDAObjectFromEvent(self.windowHandle, winUser.OBJID_CLIENT, 0)


class OptionsControl(IAccessible):
    """A control of Options or a window inside one, as the edit of a combo box."""

    def _get_container(self):
        form = parent(self.windowHandle)
        heading = (
            section_heading(self.windowHandle, form, self.appModule.helperLocalBindingHandle)
            if form == form_of(self.windowHandle)
            else ""
        )
        if not heading:
            return super()._get_container()
        return Section(chooseBestAPI=False, windowHandle=form, heading=heading)
