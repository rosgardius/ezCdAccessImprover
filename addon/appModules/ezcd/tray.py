# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The toolbar of the drive's tray on the Audio CD Ripper and Disc Burner tabs.

It ends the row of the drive and its speed. It is a Tab stop right before the Tab stop right of it on the
screen, else the one below it: Options on the Disc Burner tab, the list of tracks on the Audio CD Ripper
tab; without either, at the end of the tab (``tab_end``). Without a drive, ezcd disables both lists and
the buttons; Tab skips the lists, but not the stop.

Open tray and Close tray take turns: ezcd hides the one pressed, and focus goes on to the other.
"""

import threading
import time
from collections.abc import Hashable
from dataclasses import dataclass

import api
import queueHandler
import winUser
from logHandler import log

from . import panels, toolbar, toolbar_stops
from .language import LanguageFiles
from .top_panel import main_tab
from .windows import descendants, parent, rect, tab_stop_below, tab_stop_right

# ezcd's strings for the buttons, by image.
_NAMES = {
    8: 191,  # Open tray
    7: 192,  # Close tray, hidden
    9: 434,  # Drive settings: a gear without a hint, on the Audio CD Ripper tab only
}
# Open tray and Close tray, each by the image of the other.
_PAIRS = {8: 7, 7: 8}
# ezcd may wait for the drive to move the tray before it shows the other button.
_PAIR_TIMEOUT = 10.0
_POLL_SECONDS = 0.1
_JOIN_TIMEOUT = 1.0


@dataclass(frozen=True)
class TrayToolbar(toolbar_stops.ToolbarStop):
    tab: str
    """The caption of the main window's tab: VCL reorders the tabs' windows as they are switched."""

    @property
    def key(self) -> Hashable:
        return self.tab

    def overlay_class(self, button: toolbar_stops.StopButton | None) -> type:
        return TrayToolbarWindow if button is None else TrayButton


def is_tray(hwnd: int) -> bool:
    return (
        winUser.getClassName(hwnd) == "TToolBar"
        and winUser.isWindowVisible(hwnd)
        and panels.is_drive_panel(parent(hwnd))
    )


def stop_of(hwnd: int, process_handle: int, language: LanguageFiles) -> TrayToolbar | None:
    """The tray's toolbar, if the window is it."""
    tab = main_tab(hwnd) if is_tray(hwnd) else 0
    buttons = toolbar_stops.read_buttons([hwnd], process_handle) if tab else ()
    return TrayToolbar(buttons, winUser.getWindowText(tab)) if buttons else None


def next_control(hwnd: int) -> int:
    """The control after the tray's stop in the Tab order: the Tab stop right of it or below it."""
    tab = main_tab(hwnd)
    if not tab:
        return 0
    edge = rect(hwnd)
    return tab_stop_right(tab, edge) or tab_stop_below(tab, edge)


def toolbar_passed(window: int, previous: int, forward: bool) -> int:
    """The tray's toolbar if Tab or Shift+Tab from ``previous`` to ``window`` passed by its stop."""
    after = window if forward else previous
    tab = main_tab(after)
    tray = next((w for w in descendants(tab) if is_tray(w)), 0) if tab else 0
    return tray if tray and tray not in (window, previous) and next_control(tray) == after else 0


class TrayToolbarWindow(toolbar_stops.ToolbarWindow):
    find_stop = staticmethod(stop_of)


class PairFocus:
    """Moves focus from Open tray or Close tray, once pressed, to the other one when ezcd shows it.

    ezcd hides the pressed button within the same toolbar window, so no focus event comes. The buttons are
    read in a background thread: ezcd answers no messages while the drive moves the tray.
    """

    def __init__(self):
        self._stopped = threading.Event()
        self._thread: threading.Thread | None = None

    def follow(self, button: "TrayButton", pressed: toolbar.ToolButton):
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._wait, args=(button, pressed), name="ezcdTrayPair", daemon=True
        )
        self._thread.start()

    def _wait(self, button: "TrayButton", pressed: toolbar.ToolButton):
        # The object keeps its process handle open.
        hwnd, process_handle = button.windowHandle, button.processHandle
        deadline = time.monotonic() + _PAIR_TIMEOUT
        while not self._stopped.wait(_POLL_SECONDS) and time.monotonic() < deadline:
            buttons = toolbar.read_buttons(hwnd, process_handle)
            if any(b.index == pressed.index and not b.hidden for b in buttons):
                continue
            pair = next((b for b in buttons if b.image == _PAIRS[pressed.image] and not b.hidden), None)
            if pair is not None:
                queueHandler.queueFunction(queueHandler.eventQueue, self._focus, button, pair.index)
                return
        log.debugWarning("ezcd did not show the other button of the tray")

    def _focus(self, pressed: "TrayButton", pair: int):
        # Unless focus has left the pressed button meanwhile.
        if self._stopped.is_set() or api.getFocusObject() != pressed:
            return
        stop = stop_of(pressed.windowHandle, pressed.processHandle, pressed.appModule.language)
        button = None if stop is None else stop.find(pressed.windowHandle, pair)
        if button is not None:
            toolbar_stops.focus_button(pressed.appModule, stop, button, pressed.windowHandle)

    def terminate(self):
        self._stopped.set()
        if self._thread is not None:
            self._thread.join(_JOIN_TIMEOUT)


class TrayButton(toolbar_stops.ButtonBeforeControl):
    find_stop = staticmethod(stop_of)
    next_control = staticmethod(next_control)
    image_names = _NAMES

    def doAction(self, index=None):
        pressed = self._tool_button()
        super().doAction(index)
        if not index and pressed is not None and pressed.image in _PAIRS:
            self.appModule.tray_pair.follow(self, pressed)
