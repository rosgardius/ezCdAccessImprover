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

from . import captions, convert_window, top_panel
from .windows import child_windows

_NOT_DIALOG_CLASSES = frozenset(
    (top_panel.MAIN_WINDOW_CLASS, "TApplication", "THintWindow", "#32768", "#32770")
)
# Windows that hold labels; the texts of other windows are their own content.
_CONTAINER_CLASSES = frozenset(
    ("TPanel", "TGroupBox", "TRadioGroup", "TTabSheet", "TScrollBox", "TGridPanel", "TCardPanel", "TCard")
)
# Windows that hold containers but draw only their own texts, as the tab labels.
_PASS_THROUGH_CLASSES = frozenset(("TPageControl",))
_CAPTIONED_CLASSES = captions.CLASSES | frozenset(
    (*captions.CHOICE_CLASSES, "TVirtualStringTree", "TComboBoxEx")
)
_LINE_TOLERANCE = 8


def is_dialog(hwnd: int) -> bool:
    return (
        winUser.getAncestor(hwnd, winUser.GA_ROOT) == hwnd
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


def _lines(texts: list[captions.Text]) -> list[str]:
    """The texts by lines, top to bottom, each line from left to right."""
    lines: list[list[captions.Text]] = []
    for text in sorted(texts, key=lambda t: t.top):
        if lines and text.top - lines[-1][0].top < _LINE_TOLERANCE:
            lines[-1].append(text)
        else:
            lines.append([text])
    return [captions.joined(sorted(line, key=lambda t: t.left)) for line in lines]


def _container_text(container: int, binding_handle) -> list[str]:
    texts = captions.read_texts(container, binding_handle)
    if not texts:
        return []
    left_out = {t for t in texts if t.text in captions.BUTTON_TEXTS}
    for child in child_windows(container):
        if not winUser.isWindowVisible(child):
            continue
        child_class = winUser.getClassName(child)
        if child_class in _CAPTIONED_CLASSES:
            left_out.update(captions.Layout(child, None, texts=texts).caption_texts())
        if child_class in captions.SLIDER_CLASSES:
            slider = convert_window.logical_rect(child, container)
            left_out.update(t for t in texts if captions.is_scale(t, slider))
    return _lines([t for t in texts if t not in left_out])


def _comparable(text: str) -> str:
    return "".join(text.split()).casefold()


def dialog_text(window: int, binding_handle) -> str:
    """The text of the dialog from the screen, line by line; empty if the display model has none.

    A line repeating the title, as in Checking filenames, is left out: NVDA says the title already.
    """
    if not binding_handle:
        return ""
    rects = {c: convert_window.logical_rect(c, window) for c in _containers(window)[1:]}
    containers = sorted(rects, key=lambda c: (rects[c].top, rects[c].left))
    title = _comparable(winUser.getWindowText(window))
    lines = [line for c in (window, *containers) for line in _container_text(c, binding_handle)]
    return "\n".join(line for line in lines if _comparable(line) != title)


class EzcdDialog(Dialog, IAccessible):
    """A form of ezcd other than the main and the conversion window; its text is in labels without windows."""

    def _get_role(self):
        return controlTypes.Role.DIALOG

    def _get_description(self):
        return dialog_text(self.windowHandle, self.appModule.helperLocalBindingHandle)
