# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The pages of the Disc Burner tab: Audio CD, MP3 disc and Data disc.

The tab holds a page control whose tab labels ezcd hides; speed buttons without windows on a panel right
above it switch the pages. The page control is presented as the tab of its active page.
"""

import time
from collections.abc import Callable

import api
import controlTypes
import core
import eventHandler
import winUser
from inputCore import InputGesture
from logHandler import log
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent
from scriptHandler import script
from speech.speech import speakObject

from . import remote, vcl, version
from .language import LanguageFiles
from .top_panel import active_tab, main_tab
from .windows import child_windows, descendants, parent, rect

# Audio CD, MP3 disc, Data disc.
PAGE_COUNT = 3
_BUTTON_CLASSES = frozenset(("TPngSpeedButton",))
# The panel of the buttons ends a pixel above the page control.
_EDGE_TOLERANCE = 2
_POLL_MS = 20
_SHOW_TIMEOUT = 3.0


def is_pages(hwnd: int) -> bool:
    """Whether the window is the page control of the Disc Burner tab."""
    # The main window's page control is not inside a tab.
    return winUser.getClassName(hwnd) == "TPageControl" and bool(main_tab(hwnd))


def pages_in_tab(tab: int) -> int:
    """The page control of the Disc Burner tab, if the main window's tab is it; 0 if not."""
    return next((w for w in descendants(tab) if is_pages(w)), 0)


def page_index(pages: int, language: LanguageFiles) -> int | None:
    """The position of the active page among the buttons; ``None`` if not known."""
    page = active_tab(pages)
    caption = winUser.getWindowText(page) if page else ""
    strings = version.facts.strings
    # The captions of the pages' buttons from left to right.
    buttons = (strings.audio_cd_page, strings.mp3_disc_page, strings.data_disc_page)
    return next((i for i, string in enumerate(buttons) if caption in language.texts(string)), None)


def _button_panel(pages: int) -> int:
    edge = rect(pages)
    return next(
        (
            panel
            for panel in child_windows(parent(pages), "TPanel")
            if abs(rect(panel).bottom - edge.top) <= _EDGE_TOLERANCE and not child_windows(panel)
        ),
        0,
    )


def _click(pages: int, index: int, process_handle: int) -> bool:
    """Posts a click on the page's button; ``False`` if the button is not found."""
    panel = _button_panel(pages)
    if not panel:
        return False
    # ezcd widens the buttons to their captions, side by side from the left.
    buttons = sorted(
        (c for c in vcl.controls(panel, process_handle, _BUTTON_CLASSES) if c.visible), key=lambda c: c.left
    )
    if len(buttons) != PAGE_COUNT:
        return False
    button = buttons[index]
    return remote.post_click(panel, button.left + button.width // 2, button.top + button.height // 2)


class PageSwitcher:
    """Switches the pages and reports the page once ezcd shows it, unless focus has moved meanwhile.

    ezcd takes up to half a second to show a page. Keys that switch pages meanwhile go on from the page
    asked for last; Tab and Shift+Tab from the page control wait, so that the page is reported before the
    control they move to.
    """

    def __init__(self, language: LanguageFiles, note_gesture: Callable[[InputGesture], object]):
        self._language = language
        self._note_gesture = note_gesture
        """Tells the app module of a key, as NVDA does when the key is pressed."""
        self._held: list[InputGesture] = []
        self._pages = 0
        self._target: int | None = None
        """The page asked for last, until ezcd shows it."""
        self._old_page = 0
        self._focus = 0
        """The window with the focus at the first click of a series."""
        self._deadline = 0.0
        self._timer = None

    def move(self, pages: int, process_handle: int, target: Callable[[int], int]):
        """Shows the page at the position ``target`` gives for the current page's, if that is another page."""
        current = self._target if self._target is not None and pages == self._pages else None
        if current is None:
            current = page_index(pages, self._language)
        if current is None:
            return
        index = target(current)
        if index == current or not 0 <= index < PAGE_COUNT or not _click(pages, index, process_handle):
            return
        if self._target is None or pages != self._pages:
            self._old_page = active_tab(pages)
            self._focus = api.getFocusObject().windowHandle
        self._pages, self._target = pages, index
        self._deadline = time.monotonic() + _SHOW_TIMEOUT
        if self._timer is None:
            self._timer = core.callLater(_POLL_MS, self._poll)

    def hold(self, pages: int, gesture: InputGesture) -> bool:
        """Keeps the key from the page control until ezcd shows the page; ``False`` if no page is coming."""
        if self._target is None or pages != self._pages:
            return False
        self._held.append(gesture)
        return True

    def _poll(self):
        self._timer = None
        if self._target is None:
            return
        if page_index(self._pages, self._language) == self._target:
            self._target = None
            self._report()
        elif time.monotonic() > self._deadline:
            log.debugWarning(f"ezcd did not show Disc Burner page {self._target}")
            self._target = None
        else:
            self._timer = core.callLater(_POLL_MS, self._poll)
            return
        held, self._held = self._held, []
        for gesture in held:
            self._note_gesture(gesture)
            gesture.send()

    def _report(self):
        # VCL moves focus from a control of the old page to the first control of the new one.
        if self._old_page and winUser.isDescendantWindow(self._old_page, self._focus):
            return
        # Other keys have moved focus meanwhile.
        if api.getFocusObject().windowHandle != self._focus:
            return
        obj = getNVDAObjectFromEvent(self._pages, winUser.OBJID_CLIENT, 0)
        if obj is None:
            return
        if self._focus == self._pages:
            # Not queued: the name is read now, before a key that follows shows another page.
            eventHandler.executeEvent("gainFocus", obj)
        else:
            speakObject(obj, controlTypes.OutputReason.FOCUS)

    def terminate(self):
        self._target = None
        self._held = []
        if self._timer is not None:
            self._timer.Stop()
            self._timer = None


class BurnerPages(IAccessible):
    """The page control of the Disc Burner tab, presented as the tab of the active page."""

    role = controlTypes.Role.TAB
    # Entering a page presents the page itself, a property page.
    isPresentableFocusAncestor = False

    def _get_name(self):
        page = active_tab(self.windowHandle)
        return winUser.getWindowText(page) if page else ""

    def _get_positionInfo(self):
        index = page_index(self.windowHandle, self.appModule.language)
        return {} if index is None else {"indexInGroup": index + 1, "similarItemsInGroup": PAGE_COUNT}

    def _move(self, target: Callable[[int], int]):
        self.appModule.page_switcher.move(self.windowHandle, self.processHandle, target)

    @script(gesture="kb:leftArrow")
    def script_previous_page(self, gesture):
        self._move(lambda current: current - 1)

    @script(gesture="kb:rightArrow")
    def script_next_page(self, gesture):
        self._move(lambda current: current + 1)

    @script(gesture="kb:home")
    def script_first_page(self, gesture):
        self._move(lambda current: 0)

    @script(gesture="kb:end")
    def script_last_page(self, gesture):
        self._move(lambda current: PAGE_COUNT - 1)

    @script(gestures=("kb:tab", "kb:shift+tab"))
    def script_leave(self, gesture):
        if not self.appModule.page_switcher.hold(self.windowHandle, gesture):
            gesture.send()
