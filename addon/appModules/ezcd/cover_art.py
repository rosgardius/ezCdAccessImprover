# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The cover art: in the metadata panel, in its view window and in the panel the mouse brings up over it.

ezcd offers the actions on the cover art only in context menus and on a panel that shows while the mouse
pointer rests on the cover art. The cover art of the metadata panel is a Tab stop before the panel's
fields, where Applications opens its menu.
"""

from ctypes.wintypes import RECT

import winUser
from NVDAObjects.IAccessible import IAccessible
from scriptHandler import script

from . import remote, screen, vcl
from .dialogs import ClosedByEscape
from .language import LanguageFiles
from .windows import child_windows, parent, rect

COVER_CLASS = "TDropPanel"
_MENU_GESTURES = ("kb:applications", "kb:shift+f10")


def cover_info(cover: int, binding_handle, process_handle: int, language: LanguageFiles) -> str:
    """The text beside the cover art: its size and format, if there is a cover.

    ezcd draws it under the cover art, or left of it while the metadata panel is left or right of the
    list of files; then the fields are under the cover art, and the "/" before a total among them.
    """
    panel = parent(cover)
    bounds = screen.logical_rect(panel, panel)
    edge = screen.logical_rect(cover, panel)
    siblings = [
        screen.logical_rect(window, panel)
        for window in child_windows(panel)
        if window != cover and winUser.isWindowVisible(window)
    ]
    under_bottom = min(
        (o.top for o in siblings if o.top >= edge.bottom and o.left < edge.right and edge.left < o.right),
        default=bounds.bottom,
    )
    areas = (
        RECT(bounds.left, edge.top, edge.left, edge.bottom),
        RECT(edge.left, edge.bottom, edge.right, under_bottom),
    )
    labels = vcl.label_texts(panel, process_handle, language)
    if labels:
        texts = [
            t
            for t in labels
            for area in areas
            if area.left <= (t.left + t.right) // 2 < area.right
            and area.top <= (t.top + t.bottom) // 2 < area.bottom
        ]
    else:
        texts = [text for area in areas for text in screen.texts(panel, binding_handle, area)]
    return " ".join(screen.joined(line) for line in screen.lines(texts))


def open_menu(window: int):
    """Has ezcd open the window's context menu at its centre, as a right click does."""
    edge = rect(window)
    remote.post_context_menu(window, (edge.left + edge.right) // 2, (edge.top + edge.bottom) // 2)


def _is_shown(window: int) -> bool:
    return winUser.isWindowVisible(window) and winUser.isWindowEnabled(window)


def stop_target(window: int, previous: int, tab_key: int) -> int:
    """The cover art if Tab from ``previous`` to ``window`` entered the metadata panel or Shift+Tab left it;
    0 if not."""
    if not tab_key or not previous:
        return 0
    inside, outside = (window, previous) if tab_key > 0 else (previous, window)
    panel = parent(inside)
    cover = next(iter(child_windows(panel, COVER_CLASS)), 0)
    if not cover or inside == cover or outside == panel or parent(outside) == panel:
        return 0
    return cover if _is_shown(cover) else 0


class CoverArt(IAccessible):
    """The cover art of the metadata panel, with its size and format as the description."""

    def _get_name(self):
        return winUser.getWindowText(self.windowHandle)

    def _get_description(self):
        return cover_info(
            self.windowHandle,
            self.appModule.helperLocalBindingHandle,
            self.processHandle,
            self.appModule.language,
        )

    @script(gestures=_MENU_GESTURES)
    def script_open_menu(self, gesture):
        open_menu(self.windowHandle)


class CoverView(ClosedByEscape):
    """The view of the cover art (``TCoverArtWnd2``): its actions are in the menu of the picture."""

    @script(gestures=_MENU_GESTURES, canPropagate=True)
    def script_open_menu(self, gesture):
        # The picture is the larger of the two panels, the other is the line of text under it.
        panels = [w for w in child_windows(self.windowHandle, "TPanel") if winUser.isWindowVisible(w)]
        if not panels:
            gesture.send()
            return
        edges = {w: rect(w) for w in panels}
        open_menu(
            max(panels, key=lambda w: (edges[w].right - edges[w].left) * (edges[w].bottom - edges[w].top))
        )


class CoverPanel(ClosedByEscape):
    """The panel that shows over the cover art while the mouse pointer rests on it (``TCoverArtWnd``).

    It is modal and has no close box; with the pointer still on the cover art it shows again, so Escape
    moves the pointer off it.
    """

    def close(self):
        super().close()
        # Onto the title bar of the main window.
        main = winUser.getWindow(self.windowHandle, winUser.GW_OWNER)
        if main:
            edge = rect(main)
            _x, client_top = winUser.ClientToScreen(main, 0, 0)
            winUser.setCursorPos((edge.left + edge.right) // 2, (edge.top + client_top) // 2)


DIALOG_CLASSES = {"TCoverArtWnd2": CoverView, "TCoverArtWnd": CoverPanel}
"""Overlay classes of the cover art's windows, by form class."""
