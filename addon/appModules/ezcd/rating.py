# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The rating of the metadata panel: five stars without a window, which ezcd sets only with the mouse.

The rating is a Tab stop right before the Tab stop below it, presented as a slider. Its focus is on the
metadata panel, which ezcd itself never focuses. The value is read from ezcd's memory and set by a click
on a star.
"""

import builtins
import ctypes
import functools
from ctypes.wintypes import RECT

import controlTypes
import eventHandler
import winUser
from logHandler import log
from NVDAObjects.IAccessible import IAccessible
from scriptHandler import script

from . import remote, screen, toolbar, vcl
from .cover_art import COVER_CLASS
from .names import ezcd_string
from .windows import child_windows, parent, tab_stop_below

_RATING_CLASS = "TRating"
_STARS = 5
# A star in design units; a click at the rating's left edge sets no stars.
_STAR_WIDTH = 16
# TRating: the number of stars.
_VALUE = 0x340
_CAPTION = 592


def _rating(panel: int, process_handle: int) -> vcl.Control | None:
    """The shown rating of the metadata panel, if it can be set."""
    if not child_windows(panel, COVER_CLASS):
        return None
    return next(
        (c for c in vcl.controls(panel, process_handle, _RATING_CLASS) if c.visible and c.enabled), None
    )


def _screen_rect(panel: int, rating: vcl.Control) -> RECT:
    left, top = winUser.ClientToScreen(panel, rating.left, rating.top)
    return RECT(left, top, left + rating.width, top + rating.height)


def next_control(panel: int, process_handle: int) -> int:
    """The control after the rating's stop in the Tab order, the Tab stop below it; 0 if none."""
    rating = _rating(panel, process_handle)
    return tab_stop_below(panel, _screen_rect(panel, rating)) if rating else 0


def stop_target(window: int, previous: int, tab_key: int, process_handle: int) -> int:
    """The panel holding the rating if Tab or Shift+Tab from ``previous`` to ``window`` passed by its stop;
    0 if not."""
    if not previous:
        return 0
    after = window if tab_key > 0 else previous if tab_key < 0 else 0
    panel = parent(after) if after else 0
    if not panel or panel in (window, previous):
        return 0
    return panel if next_control(panel, process_handle) == after else 0


def is_stop(panel: int) -> bool:
    """Whether the window is the metadata panel with ezcd's focus, which only the rating's stop gives it."""
    _process_id, thread_id = winUser.getWindowThreadProcessID(panel)
    return winUser.getGUIThreadInfo(thread_id).hwndFocus == panel and bool(child_windows(panel, COVER_CLASS))


class RatingSlider(IAccessible):
    """The rating's stop: the metadata panel with ezcd's focus, presented as a slider of the stars."""

    role = controlTypes.Role.SLIDER

    @functools.cached_property
    def _caption(self) -> str:
        return ezcd_string(self.windowHandle, _CAPTION, self.appModule.language)

    def _get_name(self):
        return self._caption

    def _value(self) -> int | None:
        """The number of stars; ``None`` if it cannot be read."""
        rating = _rating(self.windowHandle, self.processHandle)
        if rating is None:
            return None
        stars = (ctypes.c_int32 * 1)()
        try:
            remote.read(self.processHandle, rating.address + _VALUE, stars)
        except OSError:
            log.debugWarning("Rating of ezcd not read", exc_info=True)
            return None
        return stars[0] if 0 <= stars[0] <= _STARS else None

    def _get_value(self):
        stars = self._value()
        return "" if stars is None else builtins._("{number} of {total}").format(number=stars, total=_STARS)

    def _set_stars(self, stars: int):
        current = self._value()
        rating = _rating(self.windowHandle, self.processHandle)
        if current is None or rating is None:
            return
        stars = min(max(stars, 0), _STARS)
        if stars == current:
            return
        star = _STAR_WIDTH * screen.dpi_scale(self.windowHandle)
        x = rating.left + (round((stars - 0.5) * star) if stars else 0)
        if remote.click(self.windowHandle, x, rating.top + rating.height // 2):
            eventHandler.executeEvent("valueChange", self)

    def _step(self, step: int):
        current = self._value()
        if current is not None:
            self._set_stars(current + step)

    @script(gestures=("kb:rightArrow", "kb:upArrow"))
    def script_more(self, gesture):
        self._step(1)

    @script(gestures=("kb:leftArrow", "kb:downArrow"))
    def script_less(self, gesture):
        self._step(-1)

    @script(gesture="kb:home")
    def script_none(self, gesture):
        self._set_stars(0)

    @script(gesture="kb:end")
    def script_all(self, gesture):
        self._set_stars(_STARS)

    @script(gesture="kb:tab")
    def script_next_control(self, gesture):
        after = next_control(self.windowHandle, self.processHandle)
        if not after or not toolbar.set_focus(after):
            gesture.send()

    @script(gesture="kb:shift+tab")
    def script_previous_control(self, gesture):
        # ezcd moves from the control after the stop to the one before it.
        after = next_control(self.windowHandle, self.processHandle)
        if after:
            self.appModule.pass_focus(after)
        gesture.send()
