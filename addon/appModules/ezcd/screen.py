# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""What ezcd draws without windows: the texts NVDA's display model has, in logical coordinates.

ezcd's labels, column headers and summary values have no windows. The display model has only what was
drawn since a window last filled its background, so a window is painted again when its text is missing.
"""

import threading
from ctypes.wintypes import RECT
from dataclasses import dataclass

import displayModel
import textUtils
import windowUtils
import winUser
import XMLFormatting
from winBindings import user32

from .windows import rect as window_rect

# Texts on one line differ in top by a few pixels at most.
LINE_TOLERANCE = 8
_REDRAW_TIMEOUT = 0.3
_RDW_FRAME = 0x0400


@dataclass(frozen=True)
class Text:
    left: int
    top: int
    right: int
    bottom: int
    text: str


def logical_rect(hwnd: int, reference: int) -> RECT:
    """The window's rectangle in the logical coordinates of the reference window."""
    rect = window_rect(hwnd)
    rect.left, rect.top = windowUtils.physicalToLogicalPoint(reference, rect.left, rect.top)
    rect.right, rect.bottom = windowUtils.physicalToLogicalPoint(reference, rect.right, rect.bottom)
    return rect


def client_rect(hwnd: int) -> RECT:
    """The window's client area in its own logical coordinates."""
    client = winUser.getClientRect(hwnd)
    corners = (winUser.ClientToScreen(hwnd, 0, 0), winUser.ClientToScreen(hwnd, client.right, client.bottom))
    (left, top), (right, bottom) = (windowUtils.physicalToLogicalPoint(hwnd, *c) for c in corners)
    return RECT(left, top, right, bottom)


def dpi_scale(hwnd: int) -> float:
    """How much larger than at 96 DPI the window is drawn: forms keep their design units scaled by it."""
    return (user32.GetDpiForWindow(hwnd) or windowUtils.DEFAULT_DPI_LEVEL) / windowUtils.DEFAULT_DPI_LEVEL


def texts(window: int, binding_handle, area: RECT | None = None) -> list[Text]:
    """The pieces of text drawn by the window itself within the area, by default all of it."""
    if not binding_handle:
        return []
    if area is None:
        area = logical_rect(window, window)
    text, rects = displayModel.getWindowTextInRect(
        binding_handle, window, area.left, area.top, area.right, area.bottom, 8, 32, True, False
    )
    found = []
    offset = 0
    for item in XMLFormatting.XMLTextParser().parse(f"<control>{text}</control>"):
        if not isinstance(item, str):
            continue
        start, offset = offset, offset + textUtils.WideStringOffsetConverter(item).encodedStringLength
        if item.strip() and start < len(rects):
            first, last = rects[start], rects[min(offset, len(rects)) - 1]
            found.append(Text(first.left, first.top, last.right, first.bottom, item.strip()))
    return found


def lines(found: list[Text]) -> list[list[Text]]:
    """The texts by lines, top to bottom, each line from left to right."""
    result: list[list[Text]] = []
    for text in sorted(found, key=lambda t: t.top):
        if result and text.top - result[-1][0].top < LINE_TOLERANCE:
            result[-1].append(text)
        else:
            result.append([text])
    return [sorted(line, key=lambda t: t.left) for line in result]


def joined(found: list[Text]) -> str:
    return " ".join(t.text for t in found)


def redraw(window: int, frame: bool = False) -> bool:
    """Has ezcd paint the window, with its non-client area if ``frame``; ``False`` if it did not in time."""
    done = threading.Event()
    flags = winUser.RDW_INVALIDATE | winUser.RDW_UPDATENOW | (_RDW_FRAME if frame else 0)

    def paint():
        user32.RedrawWindow(window, None, None, flags)
        done.set()

    # A window of another thread is painted synchronously: a hung ezcd must not stop NVDA.
    threading.Thread(target=paint, name="ezcdRedraw", daemon=True).start()
    return done.wait(_REDRAW_TIMEOUT)
