# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Windows of ezcd other than the main and the conversion window, presented as dialogs with their text.

The text of a dialog is in labels without windows, visible only in the display model of the form and its
panels. The labels that caption a control are said with the control, so they are left out.
"""

import controlTypes
import winUser
from NVDAObjects.behaviors import Dialog
from NVDAObjects.IAccessible import IAccessible

from . import captions, convert_window, screen
from .windows import child_windows, root

_NOT_DIALOG_CLASSES = frozenset(("TMainform", "TApplication", "THintWindow", "#32768", "#32770"))
# Windows that hold labels; the texts of other windows are their own content.
_CONTAINER_CLASSES = frozenset(
    ("TPanel", "TGroupBox", "TRadioGroup", "TTabSheet", "TScrollBox", "TGridPanel", "TCardPanel", "TCard")
)
# Windows that hold containers but draw only their own texts, as the tab labels.
_PASS_THROUGH_CLASSES = frozenset(("TPageControl",))
_CAPTIONED_CLASSES = captions.CLASSES | frozenset(
    (*captions.CHOICE_CLASSES, "TVirtualStringTree", "TComboBoxEx")
)


def is_dialog(hwnd: int) -> bool:
    return (
        root(hwnd) == hwnd
        and winUser.getClassName(hwnd) not in _NOT_DIALOG_CLASSES
        and not convert_window.is_conversion_window(hwnd)
    )


def _containers(window: int) -> list[int]:
    """The visible containers in the window, the window itself first if it is one."""
    found = [window] if winUser.getClassName(window) not in _PASS_THROUGH_CLASSES else []
    for child in child_windows(window):
        child_class = winUser.getClassName(child)
        if child_class in _CONTAINER_CLASSES | _PASS_THROUGH_CLASSES and winUser.isWindowVisible(child):
            found += _containers(child)
    return found


def _container_text(container: int, binding_handle) -> list[str]:
    texts = screen.texts(container, binding_handle)
    if not texts:
        return []
    left_out = {t for t in texts if t.text in captions.BUTTON_TEXTS}
    for child in child_windows(container):
        if not winUser.isWindowVisible(child):
            continue
        child_class = winUser.getClassName(child)
        if child_class in _CAPTIONED_CLASSES:
            left_out.update(captions.Layout(child, texts=texts).caption_texts())
        if child_class in captions.SLIDER_CLASSES:
            slider = screen.logical_rect(child, container)
            left_out.update(t for t in texts if captions.is_scale(t, slider))
    return [screen.joined(line) for line in screen.lines([t for t in texts if t not in left_out])]


def _comparable(text: str) -> str:
    return "".join(text.split()).casefold()


def dialog_text(window: int, binding_handle) -> str:
    """The text of the dialog from the screen, line by line; empty if the display model has none.

    A line repeating the title, as in Checking filenames, is left out: NVDA says the title already.
    """
    rects = {c: screen.logical_rect(c, window) for c in _containers(window)[1:]}
    containers = sorted(rects, key=lambda c: (rects[c].top, rects[c].left))
    title = _comparable(winUser.getWindowText(window))
    lines = [line for c in (window, *containers) for line in _container_text(c, binding_handle)]
    return "\n".join(line for line in lines if _comparable(line) != title)


class EzcdDialog(Dialog, IAccessible):
    """A form of ezcd other than the main and the conversion window; its text is in labels without windows."""

    role = controlTypes.Role.DIALOG

    def _get_description(self):
        return dialog_text(self.windowHandle, self.appModule.helperLocalBindingHandle)
