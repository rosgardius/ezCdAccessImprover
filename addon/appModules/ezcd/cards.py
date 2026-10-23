# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Controls on the cards of a ``TCardPanel``, which shows the card of the item chosen in the combo box
above it, as the effects of DSP.

A card has only scales and units on screen; the chosen item names its controls, up to its " | ": modes
of one effect share a card ("Loudness normalization | Integrated").
"""

import functools

import winUser
from NVDAObjects.IAccessible import IAccessible

from . import remote
from .captions import Layout
from .windows import parent

_NAME_SEPARATOR = ", "
_MODE_SEPARATOR = " | "
_TEXT_LENGTH = 256


def choice(card_panel: int) -> int:
    """The combo box choosing the card: the nearest one above the card panel; 0 if none."""
    layout = Layout(card_panel)
    above = [
        s
        for s, rect in layout.siblings.items()
        if winUser.getClassName(s) == "TComboBox" and rect.bottom <= layout.rect.top
    ]
    return max(above, key=lambda s: layout.siblings[s].bottom, default=0)


def card_name(card_panel: int) -> str:
    """The chosen item without its mode; empty if there is no choice."""
    combo_box = choice(card_panel)
    return remote.text(combo_box, _TEXT_LENGTH).split(_MODE_SEPARATOR)[0] if combo_box else ""


def card_panel_of(hwnd: int) -> int:
    """The card panel of a control on a card; 0 if the control is not on a card."""
    card = parent(hwnd)
    return parent(card) if winUser.getClassName(card) == "TCard" else 0


class CardControl(IAccessible):
    """A control on a card, named by the card before its own caption, as "Gain, dB"."""

    @functools.cached_property
    def _card_name(self) -> str:
        return card_name(card_panel_of(self.windowHandle))

    def _get_name(self):
        return _NAME_SEPARATOR.join(part for part in (self._card_name, super()._get_name()) if part)
