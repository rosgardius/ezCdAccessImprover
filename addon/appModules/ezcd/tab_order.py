# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Tab in screen order in dialogs where ezcd's own order jumps around or leaves controls out: Options of
the Audio Converter and Audio CD Ripper tabs, DSP, and Filename preview.

Rows top to bottom, each from left to right, round; the field showing a slider's value right after the
slider, also where it lies higher (the top field of loudness in DSP); the tags of Filename preview as one
stop.
"""

import winUser
from NVDAObjects.IAccessible import IAccessible
from scriptHandler import script

from . import captions, filename_preview, sliders, toolbar, windows
from .windows import parent, tab_stop_rows

_FORMS = frozenset(("TConverterOptions", "TRipperOptions", "TDSPForm", filename_preview.FORM))


def form_of(hwnd: int) -> int:
    """The form with Tab in screen order holding the window, 0 if it is in none."""
    return windows.form_of(hwnd, _FORMS)


def _stops(form: int, remembered_tag: int, process_handle: int) -> list[int]:
    stops = [stop for row in tab_stop_rows(form) for stop in row]
    for slider in [s for s in stops if winUser.getClassName(s) in captions.SLIDER_CLASSES]:
        field = sliders.value_field(slider)
        if field in stops:
            stops.remove(field)
            stops.insert(stops.index(slider) + 1, field)
    return filename_preview.screen_stops(form, stops, remembered_tag, process_handle)


class ScreenOrderControl(IAccessible):
    """A control of such a form or a window inside one, as the edit of a combo box."""

    def _move_focus(self, gesture, step: int):
        form = form_of(self.windowHandle)
        # A focused tag is the remembered one.
        stops = _stops(form, self.appModule.tag_stop.remembered, self.processHandle)
        control = self.windowHandle
        # The stop holding the window, as the combo box holding its edit.
        while control not in stops and control != form:
            control = parent(control)
        if control not in stops or not toolbar.set_focus(stops[(stops.index(control) + step) % len(stops)]):
            gesture.send()

    @script(gesture="kb:tab")
    def script_next_control(self, gesture):
        self._move_focus(gesture, 1)

    @script(gesture="kb:shift+tab")
    def script_previous_control(self, gesture):
        self._move_focus(gesture, -1)
