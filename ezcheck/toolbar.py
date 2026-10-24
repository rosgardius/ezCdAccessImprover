"""The buttons of ezcd's toolbars, comctl32 toolbars read with ``TB_*`` messages."""

import ctypes
import ctypes.wintypes as W
from dataclasses import dataclass

from . import win
from .ezcd import Ezcd

TOOLBAR_CLASS = "TToolBar"
TB_GETBUTTON, TB_BUTTONCOUNT, TB_GETITEMRECT, TB_GETBUTTONTEXTW = 0x417, 0x418, 0x41D, 0x44B
TBSTATE_ENABLED, TBSTATE_HIDDEN = 0x04, 0x08
TBSTYLE_SEP, TBSTYLE_DROPDOWN = 0x01, 0x08
_MAX_TEXT_LENGTH = win.BUFFER_SIZE // 2 - 1


class _ButtonHead(ctypes.Structure):
    # The leading fields of TBBUTTON.
    _fields_ = (
        ("iBitmap", ctypes.c_int),
        ("idCommand", ctypes.c_int),
        ("fsState", ctypes.c_ubyte),
        ("fsStyle", ctypes.c_ubyte),
    )


@dataclass(frozen=True)
class Button:
    toolbar: int
    index: int
    image: int
    """``iBitmap``, the ``ImageIndex`` of the ``TToolButton``."""
    state: int
    style: int
    text: str
    rect: tuple[int, int, int, int]
    """In the toolbar's client pixels."""

    @property
    def enabled(self) -> bool:
        return bool(self.state & TBSTATE_ENABLED)

    @property
    def hidden(self) -> bool:
        return bool(self.state & TBSTATE_HIDDEN)

    @property
    def separator(self) -> bool:
        return bool(self.style & TBSTYLE_SEP)

    @property
    def dropdown(self) -> bool:
        return bool(self.style & TBSTYLE_DROPDOWN)

    def describe(self) -> str:
        caption = f" {self.text!r}" if self.text else ""
        return f"image {self.image}{caption}"


def buttons(ezcd: Ezcd, hwnd: int) -> list[Button]:
    """All buttons of the toolbar, separators and hidden ones too; raises ``OSError`` if ezcd's memory
    cannot be used."""
    found = []
    with win.buffer(ezcd.process) as address:
        for index in range(win.send(hwnd, TB_BUTTONCOUNT) or 0):
            if not win.send(hwnd, TB_GETBUTTON, index, address):
                continue
            head = _ButtonHead()
            ezcd.read(address, head)
            text = ""
            length = win.send(hwnd, TB_GETBUTTONTEXTW, head.idCommand, 0) or 0
            if 0 < length <= _MAX_TEXT_LENGTH and win.send(hwnd, TB_GETBUTTONTEXTW, head.idCommand, address):
                chars = ctypes.create_unicode_buffer(length + 1)
                ezcd.read(address, chars)
                text = chars.value
            rect = W.RECT()
            if win.send(hwnd, TB_GETITEMRECT, index, address):
                ezcd.read(address, rect)
            found.append(
                Button(
                    hwnd,
                    index,
                    head.iBitmap,
                    head.fsState,
                    head.fsStyle,
                    text,
                    (rect.left, rect.top, rect.right, rect.bottom),
                )
            )
    return found


def shown_buttons(ezcd: Ezcd, toolbars: list[int]) -> list[Button]:
    """The shown buttons of the toolbars without separators, from left to right on the screen."""
    found = [
        (win.rect(hwnd).left + button.rect[0], button)
        for hwnd in toolbars
        for button in buttons(ezcd, hwnd)
        if not button.hidden and not button.separator
    ]
    return [button for _left, button in sorted(found, key=lambda item: item[0])]
