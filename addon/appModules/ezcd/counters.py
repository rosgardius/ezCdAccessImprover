# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Counters: an edit between "-" and "+" buttons without windows.

The number of converters in the conversion window; in Settings, the numbers of converters and scanners
and the limit of metadata results.
"""

import contextlib
import ctypes
import enum
import queue
import threading
import time
from ctypes.wintypes import POINT, RECT

import api
import braille
import controlTypes
import queueHandler
import ui
import winUser
from logHandler import log
from scriptHandler import script
from winBindings import user32

from . import remote, screen, windows
from .language import OwnString
from .names import Captioned

# The buttons in design units (DFM): squares beside the edit, level with its top, 1 to 3 units from it
# by the window; a click goes to a button's centre.
_BUTTON_SIZE = 23
_BUTTON_GAP = 2

# While converting, ezcd handles messages seconds late.
_CLICK_TIMEOUT_MS = 5000
_READ_TIMEOUT_MS = 1000
_TEXT_LENGTH = 16
_JOIN_TIMEOUT = 1.0


class Step(enum.Enum):
    LESS = enum.auto()
    MORE = enum.auto()


def is_counter(hwnd: int) -> bool:
    """Whether the edit is the edit of a counter."""
    panel = windows.parent(hwnd)
    if winUser.getClassName(panel) != "TPanel":
        return False
    page = winUser.getClassName(windows.parent(panel))
    if page == "TSettings2AudioConverterForm":
        return True
    if page == "TSettings2GeneralInternetDiscDatabaseForm":
        # The limit of results, under the list of services; the fields of the proxy are in another panel.
        return bool(windows.child_windows(panel, "TCheckListBox"))
    return winUser.getClassName(windows.root(hwnd)) == "TConvertWnd"


def _button_rect(edit: int, step: Step) -> RECT:
    """The button's rectangle on the screen."""
    rect = windows.rect(edit)
    scale = screen.dpi_scale(edit)
    size = round(_BUTTON_SIZE * scale)
    gap = round(_BUTTON_GAP * scale)
    left = rect.left - gap - size if step == Step.LESS else rect.right + gap
    return RECT(left, rect.top, left + size, rect.top + size)


def button_of(panel: int, edge: RECT) -> tuple[int, Step] | None:
    """The counter's edit and the step of the button with the rectangle on the screen; ``None`` if it is
    no button of a counter."""
    x, y = (edge.left + edge.right) // 2, (edge.top + edge.bottom) // 2
    for edit in windows.child_windows(panel, "TEdit"):
        if not is_counter(edit):
            continue
        for step in Step:
            button = _button_rect(edit, step)
            if button.left <= x < button.right and button.top <= y < button.bottom:
                return edit, step
    return None


def step_name(step: Step) -> OwnString:
    return OwnString("decrease") if step == Step.LESS else OwnString("increase")


def click(edit: int, step: Step) -> bool:
    """Clicks the button's centre and waits until ezcd has handled the click: then the new number can be
    read. Waits for ezcd: not for NVDA's main thread."""
    panel = windows.parent(edit)
    rect = _button_rect(edit, step)
    point = POINT((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
    return bool(user32.ScreenToClient(panel, ctypes.byref(point))) and remote.click(
        panel, point.x, point.y, _CLICK_TIMEOUT_MS
    )


class StepAnnouncer:
    """Presses the buttons in a background thread and says the counter's number after each press.

    A press waits while ezcd is busy with the previous one; further presses meanwhile are dropped, so the
    number stops changing soon after the key is released.
    """

    def __init__(self):
        self._requests: queue.Queue[tuple[int, Step] | None] = queue.Queue(maxsize=1)
        self._thread: threading.Thread | None = None
        self._terminated = False

    def press(self, edit: int, step: Step):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="ezcdCounterSteps", daemon=True)
            self._thread.start()
        with contextlib.suppress(queue.Full):
            self._requests.put_nowait((edit, step))

    def _run(self):
        while (request := self._requests.get()) is not None:
            edit, step = request
            start = time.monotonic()
            if not click(edit, step):
                log.debugWarning("ezcd did not handle the click on a counter button in time")
                continue
            value = remote.text(edit, _TEXT_LENGTH, _READ_TIMEOUT_MS)
            log.debug(f"Counter {value}, {time.monotonic() - start:.3f} s")
            if value:
                last = self._requests.empty()
                queueHandler.queueFunction(queueHandler.eventQueue, self._say, edit, value, last)

    def _say(self, edit: int, value: str, last: bool):
        if self._terminated:
            return
        ui.message(value)
        # The edit's events are dropped; braille shows the new number once the presses are over.
        focus = api.getFocusObject()
        if last and isinstance(focus, CounterSpinBox) and focus.windowHandle == edit:
            braille.handler.handleUpdate(focus)

    def terminate(self):
        self._terminated = True
        if self._thread is None:
            return
        # Only the main thread puts requests, so the queue cannot fill up again in between.
        with contextlib.suppress(queue.Empty):
            self._requests.get_nowait()
        self._requests.put_nowait(None)
        self._thread.join(_JOIN_TIMEOUT)


class CounterSpinBox(Captioned):
    """The edit of a counter, changed by its buttons; ezcd makes some of them read-only."""

    role = controlTypes.Role.SPINBUTTON

    def initAutoSelectDetection(self):
        # ezcd replaces the text on every press, and the selection is reported as removed.
        pass

    # The number is said and brailled by StepAnnouncer. Handling these events, NVDA reads the edit from its
    # main thread right when ezcd, starting or stopping converters, does not answer.
    def event_caret(self):
        pass

    def event_valueChange(self):
        pass

    def event_textChange(self):
        pass

    def _get_states(self):
        return super()._get_states() - {controlTypes.State.READONLY}

    @script(gesture="kb:upArrow")
    def script_increase(self, gesture):
        self.appModule.counter_steps.press(self.windowHandle, Step.MORE)

    @script(gesture="kb:downArrow")
    def script_decrease(self, gesture):
        self.appModule.counter_steps.press(self.windowHandle, Step.LESS)
