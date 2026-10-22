# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The number of converters in the conversion window: an edit between "-" and "+" buttons without windows."""

import contextlib
import ctypes
import enum
import queue
import threading
import time
from ctypes.wintypes import POINT, RECT

import addonHandler
import api
import braille
import controlTypes
import queueHandler
import ui
import windowUtils
import winUser
from locationHelper import RectLTWH
from logHandler import log
from NVDAObjects import NVDAObjectTextInfo
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent
from NVDAObjects.window import Window
from scriptHandler import script
from winBindings import user32

from . import remote, screen, windows

addonHandler.initTranslation()

# The buttons in design units (DFM): squares beside the edit, level with its top.
_BUTTON_SIZE = 23
_BUTTON_GAP = 3

# While converting, ezcd handles messages seconds late.
_CLICK_TIMEOUT_MS = 5000
_READ_TIMEOUT_MS = 1000
_TEXT_LENGTH = 16
_JOIN_TIMEOUT = 1.0


class Step(enum.Enum):
    LESS = enum.auto()
    MORE = enum.auto()


def is_converters_edit(hwnd: int) -> bool:
    return (
        winUser.getClassName(windows.parent(hwnd)) == "TPanel"
        and winUser.getClassName(windows.root(hwnd)) == "TConvertWnd"
    )


def _button_rect(edit: int, step: Step) -> RECT:
    """The button's rectangle on the screen."""
    rect = windows.rect(edit)
    scale = screen.dpi_scale(edit)
    size = round(_BUTTON_SIZE * scale)
    gap = round(_BUTTON_GAP * scale)
    left = rect.left - gap - size if step == Step.LESS else rect.right + gap
    return RECT(left, rect.top, left + size, rect.top + size)


def click(edit: int, step: Step) -> bool:
    """Clicks the button's centre and waits until ezcd has handled the click: then the new number can be
    read. Waits for ezcd: not for NVDA's main thread."""
    panel = windows.parent(edit)
    rect = _button_rect(edit, step)
    point = POINT((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
    return bool(user32.ScreenToClient(panel, ctypes.byref(point))) and remote.click(
        panel, point.x, point.y, _CLICK_TIMEOUT_MS
    )


def read_label(edit: int, binding_handle) -> str:
    """The caption left of the "-" button, from the display model; empty if it has none."""
    panel = windows.parent(edit)
    area = screen.logical_rect(panel, panel)
    edit_rect = screen.logical_rect(edit, panel)
    minus = _button_rect(edit, Step.LESS)
    area.top, area.bottom = edit_rect.top, edit_rect.bottom
    area.right = windowUtils.physicalToLogicalPoint(panel, minus.left, minus.top)[0]
    texts = screen.texts(panel, binding_handle, area)
    if not texts and binding_handle:
        screen.redraw(panel)
        texts = screen.texts(panel, binding_handle, area)
    return screen.joined(sorted(texts, key=lambda t: t.left)).rstrip(" :")


class StepAnnouncer:
    """Presses the buttons in a background thread and says the number of converters after each press.

    A press waits while ezcd is busy with the previous one; further presses meanwhile are dropped, so the
    number stops changing soon after the key is released.
    """

    def __init__(self):
        self._requests: queue.Queue[tuple[int, Step] | None] = queue.Queue(maxsize=1)
        self._thread: threading.Thread | None = None
        self._terminated = False

    def press(self, edit: int, step: Step):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="ezcdConverterSteps", daemon=True)
            self._thread.start()
        with contextlib.suppress(queue.Full):
            self._requests.put_nowait((edit, step))

    def _run(self):
        while (request := self._requests.get()) is not None:
            edit, step = request
            start = time.monotonic()
            if not click(edit, step):
                log.debugWarning("ezcd did not handle the click on a converters button in time")
                continue
            value = remote.text(edit, _TEXT_LENGTH, _READ_TIMEOUT_MS)
            log.debug(f"Converters {value}, {time.monotonic() - start:.3f} s")
            if value:
                last = self._requests.empty()
                queueHandler.queueFunction(queueHandler.eventQueue, self._say, edit, value, last)

    def _say(self, edit: int, value: str, last: bool):
        if self._terminated:
            return
        ui.message(value)
        # The edit's events are dropped; braille shows the new number once the presses are over.
        focus = api.getFocusObject()
        if last and isinstance(focus, ConvertersSpinBox) and focus.windowHandle == edit:
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


class ConvertersSpinBox(IAccessible):
    """The edit with the number of converters; ezcd makes it read-only and changes it with its buttons."""

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

    def _get_name(self):
        return read_label(self.windowHandle, self.appModule.helperLocalBindingHandle) or super()._get_name()

    def _get_previous(self):
        return ConverterButton(edit=self.windowHandle, step=Step.LESS)

    def _get_next(self):
        return ConverterButton(edit=self.windowHandle, step=Step.MORE)

    @script(gesture="kb:upArrow")
    def script_increase(self, gesture):
        self.appModule.converter_steps.press(self.windowHandle, Step.MORE)

    @script(gesture="kb:downArrow")
    def script_decrease(self, gesture):
        self.appModule.converter_steps.press(self.windowHandle, Step.LESS)


class ConvertersSpinWindow(IAccessible):
    """The window object of the edit: in object navigation the buttons are around the edit inside it."""

    def _get_firstChild(self):
        return ConverterButton(edit=self.windowHandle, step=Step.LESS)

    def _get_lastChild(self):
        return ConverterButton(edit=self.windowHandle, step=Step.MORE)

    def _get_children(self):
        return [
            self.firstChild,
            getNVDAObjectFromEvent(self.windowHandle, winUser.OBJID_CLIENT, 0),
            self.lastChild,
        ]

    def _get_childCount(self):
        return len(self.children)


class _ButtonTextInfo(NVDAObjectTextInfo):
    def activate(self):
        # The base class clicks with the real mouse at the start of the text.
        self.obj.doAction()


class ConverterButton(Window):
    """The "-" or "+" button beside the edit: a speed button without a window, drawn on the panel."""

    TextInfo = _ButtonTextInfo
    role = controlTypes.Role.BUTTON
    firstChild = None
    lastChild = None
    actionCount = 1

    def __init__(self, edit: int, step: Step):
        self.edit = edit
        self.step = step
        super().__init__(windowHandle=windows.parent(edit))

    def _isEqual(self, other):
        return super()._isEqual(other) and other.edit == self.edit and other.step == self.step

    def _get_name(self):
        if self.step == Step.LESS:
            # Translators: The button that lowers the number of converters in EZ CD Audio Converter.
            return _("Decrease")
        # Translators: The button that raises the number of converters in EZ CD Audio Converter.
        return _("Increase")

    def _get_states(self):
        return set()

    def _get_location(self):
        return RectLTWH.fromCompatibleType(_button_rect(self.edit, self.step))

    def _get_parent(self):
        return getNVDAObjectFromEvent(self.edit, winUser.OBJID_WINDOW, 0)

    def _get_next(self):
        if self.step == Step.LESS:
            return getNVDAObjectFromEvent(self.edit, winUser.OBJID_CLIENT, 0)
        return None

    def _get_previous(self):
        if self.step == Step.MORE:
            return getNVDAObjectFromEvent(self.edit, winUser.OBJID_CLIENT, 0)
        return None

    def doAction(self, index=None):
        self.appModule.converter_steps.press(self.edit, self.step)
