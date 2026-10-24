# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The player of the Audio CD Ripper tab: a toolbar, the volume and the position in the track.

ezcd leaves them to the mouse: neither the toolbar nor the sliders are Tab stops. They are stops right
before the Tab stop right of the player, Options: the toolbar, then the sliders from left to right. While
the metadata panel is left or right of the list, the player is at the bottom with no Tab stop right of it
or below it, and its stops are at the end of the tab (``tab_end``). Without a disc the buttons are
disabled and the stops stay.
"""

from collections.abc import Hashable
from ctypes.wintypes import RECT
from dataclasses import dataclass

import winUser
from NVDAObjects.IAccessible import IAccessible
from scriptHandler import script

from . import panels, toolbar, toolbar_stops, version
from .captions import SLIDER_CLASSES
from .language import LanguageFiles, OwnString
from .top_panel import main_tab
from .windows import child_windows, descendants, parent, rect

_QUIET = OwnString("quiet")
_LOUD = OwnString("loud")


@dataclass(frozen=True)
class PlayerToolbar(toolbar_stops.ToolbarStop):
    @property
    def key(self) -> Hashable:
        return "player"

    def overlay_class(self, button: toolbar_stops.StopButton | None) -> type:
        return PlayerToolbarWindow if button is None else PlayerButton


def _panel(hwnd: int) -> int:
    """The player holding the window, its toolbar inside a panel of its own; 0 if none."""
    holder = parent(hwnd)
    if not panels.is_player_panel(holder):
        holder = parent(holder)
    return holder if panels.is_player_panel(holder) else 0


def is_player_slider(hwnd: int) -> bool:
    return winUser.getClassName(hwnd) in SLIDER_CLASSES and bool(_panel(hwnd))


def stop_of(hwnd: int, process_handle: int, language: LanguageFiles) -> PlayerToolbar | None:
    """The player's toolbar, if the window is it."""
    if winUser.getClassName(hwnd) != "TToolBar" or not winUser.isWindowVisible(hwnd) or not _panel(hwnd):
        return None
    buttons = toolbar_stops.read_buttons([hwnd], process_handle)
    return PlayerToolbar(buttons) if buttons else None


def stops(panel: int) -> list[int]:
    """The player's stops in the Tab order: its toolbar, then its sliders from left to right."""
    toolbars = [t for holder in child_windows(panel, "TPanel") for t in child_windows(holder, "TToolBar")]
    sliders = sorted(
        (w for w in child_windows(panel) if winUser.getClassName(w) in SLIDER_CLASSES),
        key=lambda w: rect(w).left,
    )
    return [w for w in (*toolbars, *sliders) if winUser.isWindowVisible(w)]


def next_control(panel: int) -> int:
    """The control after the player's stops in the Tab order: the Tab stop right of the player or below
    it; 0 if none."""
    tab = main_tab(panel)
    return panels.stop_after(tab, panel) if tab else 0


def stop_target(window: int, previous: int, tab_key: int) -> int:
    """The player's stop that Tab or Shift+Tab from ``previous`` to ``window`` passed by: the toolbar
    after Tab, the last slider after Shift+Tab; 0 if none."""
    if not previous or not tab_key:
        return 0
    after = window if tab_key > 0 else previous
    tab = main_tab(after)
    panel = next((w for w in descendants(tab) if panels.is_player_panel(w)), 0) if tab else 0
    found = stops(panel) if panel and winUser.isWindowVisible(panel) else []
    if not found or window in found or previous in found or next_control(panel) != after:
        return 0
    return found[0] if tab_key > 0 else found[-1]


def icon_name(holder: int, edge: RECT) -> OwnString | str:
    """The name of the player's picture at the rectangle on the screen; empty if the window is not the
    player."""
    volume = child_windows(holder, "TTrackBar") if panels.is_player_panel(holder) else []
    if not volume:
        return ""
    return _QUIET if edge.left < rect(volume[0]).left else _LOUD


class _PlayerStop(IAccessible):
    """A stop of the player: Tab and Shift+Tab go through the player's stops in their order."""

    def _move(self, gesture, step: int):
        panel = _panel(self.windowHandle)
        found = stops(panel) if panel else []
        if self.windowHandle not in found:
            gesture.send()
            return
        index = found.index(self.windowHandle) + step
        if 0 <= index < len(found):
            # The toolbar window redirects focus to the remembered button.
            if not toolbar.set_focus(found[index]):
                gesture.send()
            return
        after = next_control(panel)
        if not after:
            if not self.appModule.leave_tab_end(self.windowHandle, step > 0, self.processHandle):
                gesture.send()
            return
        if step > 0:
            if not toolbar.set_focus(after):
                gesture.send()
            return
        # ezcd moves from the control after the player to the one before it.
        self.appModule.pass_focus(after)
        gesture.send()

    @script(gesture="kb:tab")
    def script_next_control(self, gesture):
        self._move(gesture, 1)

    @script(gesture="kb:shift+tab")
    def script_previous_control(self, gesture):
        self._move(gesture, -1)


class PlayerToolbarWindow(toolbar_stops.ToolbarWindow):
    find_stop = staticmethod(stop_of)


class PlayerButton(_PlayerStop, toolbar_stops.ToolbarButton):
    find_stop = staticmethod(stop_of)

    def _image_strings(self):
        return version.facts.player.button_strings


class PlayerSlider(_PlayerStop):
    """The volume or the position in the track."""
