# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The window shown while files are converted."""

import collections
import enum
import re
import time
from dataclasses import dataclass

import addonHandler
import winUser
from logHandler import log
from NVDAObjects.IAccessible import IAccessible

from . import screen
from .language import LanguageFiles
from .windows import child_windows, parent, root

addonHandler.initTranslation()

_WINDOW_CLASSES = ("TConvertWnd", "TConvertWnd_Single")
_RESUME_STRING = 145

# The summary panel in design units (DFM): the row of the total bar and the percentage right of it, and
# the grid of label and value pairs under it.
_BAR_ROW = 16
_ROWS = (0, 16, 37, 53, 69)
_COLUMNS = (0, 128, 264, 384, 528, 648)

_SPEED_INTERVAL = 0.5
_SPEED_PERIOD = 5.0
_STATUS_REUSE = 0.5
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


class Bar(enum.Enum):
    CONVERTER = enum.auto()
    TOTAL = enum.auto()


class Field(enum.Enum):
    """A label and value pair of the summary panel: its row and the columns of the label and the value."""

    CONVERTED = (37, 0, 128)
    ELAPSED = (37, 264, 384)
    ERRORS = (53, 0, 128)
    REMAINING = (53, 264, 384)
    SKIPPED = (69, 0, 128)
    SPEED = (69, 264, 384)


class State(enum.Enum):
    RUNNING = enum.auto()
    PAUSED = enum.auto()
    FINISHED = enum.auto()


def is_conversion_window(window: int) -> bool:
    return winUser.getClassName(window) in _WINDOW_CLASSES


def bar_kind(hwnd: int) -> Bar | None:
    """Which bar of the conversion window a progress bar window is, ``None`` if it is in another window."""
    if not is_conversion_window(root(hwnd)):
        return None
    # The total bar is in the summary panel, inside the panel with the file list. A converter bar is in
    # the grid panel, or, in the window for one converter, in a panel right on the form.
    panel = parent(hwnd)
    if winUser.getClassName(panel) == "TPanel" and winUser.getClassName(parent(panel)) == "TPanel":
        return Bar.TOTAL
    return Bar.CONVERTER


def summary_panel(window: int) -> int | None:
    """The summary panel of a conversion window, the parent of the total bar."""
    if not is_conversion_window(window):
        return None
    for outer in child_windows(window, "TPanel"):
        for panel in child_windows(outer, "TPanel"):
            if child_windows(panel, "TProgressBar"):
                return panel
    return None


def state(window: int, language: LanguageFiles) -> State:
    buttons = [b for panel in child_windows(window, "TPanel") for b in child_windows(panel, "TButton")]
    # After the end, Pause is disabled; while paused, it says Resume.
    if any(not winUser.isWindowEnabled(b) for b in buttons):
        return State.FINISHED
    resume = language.texts(_RESUME_STRING)
    if any(winUser.getWindowText(b).replace("&", "") in resume for b in buttons):
        return State.PAUSED
    return State.RUNNING


def _nearest(value: float, anchors: tuple[int, ...]) -> int:
    return min(anchors, key=lambda anchor: abs(anchor - value))


@dataclass(frozen=True)
class Summary:
    percent: str
    cells: dict[tuple[int, int], str]
    """Texts of the panel's grid by row and column in design units."""

    def label(self, field: Field) -> str:
        row, label, _value = field.value
        return self.cells.get((row, label), "")

    def value(self, field: Field) -> str:
        row, _label, value = field.value
        return self.cells.get((row, value), "")


def read_summary(panel: int, binding_handle) -> Summary | None:
    """Reads the texts the display model has for the summary panel; ``None`` if it has none."""
    bars = child_windows(panel, "TProgressBar")
    found = screen.texts(panel, binding_handle) if bars else []
    if not found:
        return None
    area = screen.logical_rect(panel, panel)
    bar = screen.logical_rect(bars[0], panel)
    # The labels stay where the form designer put them, scaled with the form; the bar and the percentage
    # stretch with the window.
    scale = screen.dpi_scale(panel)
    pieces: dict[tuple[int, int], list[screen.Text]] = collections.defaultdict(list)
    percent = []
    for text in sorted(found, key=lambda t: t.left):
        row = _nearest((text.top - area.top) / scale, _ROWS)
        if row == _BAR_ROW and text.left >= bar.right:
            percent.append(text)
        elif row > _BAR_ROW:
            pieces[row, _nearest((text.left - area.left) / scale, _COLUMNS)].append(text)
    return Summary(screen.joined(percent), {cell: screen.joined(texts) for cell, texts in pieces.items()})


class SpeedAverage:
    """The conversion speed averaged over the last seconds: the shown speed jumps between files."""

    def __init__(self):
        self._samples: collections.deque[tuple[float, float]] = collections.deque()
        self._last_try = 0.0

    def due(self) -> bool:
        return time.monotonic() - self._last_try >= _SPEED_INTERVAL

    def add(self, speed_text: str):
        self._last_try = time.monotonic()
        match = _NUMBER.search(speed_text)
        if match:
            self._samples.append((self._last_try, float(match.group().replace(",", "."))))

    def average(self, speed_text: str) -> str:
        """The speed text with the average in place of the shown number."""
        self.add(speed_text)
        now = time.monotonic()
        while self._samples and now - self._samples[0][0] > _SPEED_PERIOD:
            self._samples.popleft()
        match = _NUMBER.search(speed_text)
        if not match or not self._samples:
            return speed_text
        average = sum(speed for _time, speed in self._samples) / len(self._samples)
        number = f"{average:.0f}" if average >= 10 else f"{average:.1f}"
        if "," in match.group():
            number = number.replace(".", ",")
        return speed_text[: match.start()] + number + speed_text[match.end() :]


def _compose(summary: Summary, current: State, speed: SpeedAverage) -> str:
    parts = []
    if current == State.PAUSED:
        # Translators: Reported first in the status of a paused conversion in EZ CD Audio Converter.
        parts.append(_("Paused"))
    elif current == State.FINISHED:
        # Translators: Reported first in the status of a finished conversion in EZ CD Audio Converter.
        parts.append(_("Finished"))
    if current != State.FINISHED:
        parts.append(summary.percent)
    fields = [Field.CONVERTED, Field.ERRORS, Field.SKIPPED]
    fields += [Field.ELAPSED] if current == State.FINISHED else [Field.REMAINING]
    if current == State.RUNNING:
        fields.append(Field.SPEED)
    for field in fields:
        value = summary.value(field)
        if field in (Field.ERRORS, Field.SKIPPED) and value in ("", "0"):
            continue
        if field == Field.SPEED:
            value = speed.average(value)
        parts.append(f"{summary.label(field)} {value}".strip())
    return ", ".join(p for p in parts if p)


class ConversionStatus:
    """What NVDA+End says in the conversion window."""

    def __init__(self):
        self._speed = SpeedAverage()
        self._last: tuple[int, float, str] | None = None

    def sample_speed(self, bar: int, binding_handle):
        """Notes the speed on a change of the total bar.

        No full redraw here: the speed changes on nearly every update, so the display model mostly has it.
        """
        if not self._speed.due():
            return
        summary = read_summary(parent(bar), binding_handle)
        self._speed.add(summary.value(Field.SPEED) if summary is not None else "")

    def text(self, window: int, binding_handle, language: LanguageFiles) -> str:
        """The status of the conversion; empty when the panel has no text yet."""
        panel = summary_panel(window)
        if panel is None:
            return ""
        # NVDA asks for the status bar text twice on one press.
        if self._last is not None:
            last_panel, last_time, last_text = self._last
            if last_panel == panel and time.monotonic() - last_time < _STATUS_REUSE:
                return last_text
        # ezcd fills the panel's background on every change and draws only the changed labels again.
        if not screen.redraw(panel):
            log.debugWarning("The summary panel of the conversion window was not redrawn in time")
        summary = read_summary(panel, binding_handle)
        if summary is None:
            log.debugWarning("No text in the summary panel of the conversion window")
            return ""
        text = _compose(summary, state(window, language), self._speed)
        self._last = (panel, time.monotonic(), text)
        return text


class TotalProgressBar(IAccessible):
    """The progress of the whole conversion; its caption is a label without a window."""

    # Translators: The name of the progress bar of the whole conversion in EZ CD Audio Converter.
    name = _("Total progress")
