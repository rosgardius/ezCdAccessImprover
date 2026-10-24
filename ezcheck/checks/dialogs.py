"""Checks of the dialogs the checker opens, and of the pages of Settings."""

import ctypes

from .. import win, windows
from ..core import Context, Findings, Scope, Skip, check

_LABEL = frozenset(("TLabel",))
_SPEED_BUTTONS = frozenset(("TSpeedButton", "TPngSpeedButton"))
LB_GETCOUNT, LB_GETITEMDATA = 0x018B, 0x0199
# The pages of Settings the add-on knows.
_CONVERTER_PAGE = "TSettings2AudioConverterForm"
_SERVICES_PAGE = "TSettings2GeneralInternetDiscDatabaseForm"
_DRIVE_PAGE = "TSettings2AudioCDRipperDriveForm"
# Forms whose labels are values and scales: DSP's sliders, the encoder's information.
_UNCAPTIONED_FORMS = frozenset(("TDSPForm", "TEncoderInfo"))
# How far off a size or a position may be in pixels, after scaling by the DPI.
_PIXELS = 2


def _controls(context: Context, hwnd: int, classes: frozenset[str]) -> list:
    try:
        return context.ezcd.controls(hwnd, classes, context.facts.vcl)
    except OSError:
        return []


def _client_rect(hwnd: int, of: int) -> tuple[int, int, int, int]:
    """The window's rectangle in the client pixels of the window ``of``."""
    edge, origin = win.rect(hwnd), win.client_origin(of)
    return edge.left - origin[0], edge.top - origin[1], edge.right - origin[0], edge.bottom - origin[1]


@check("dialog.form", "dialogs", Scope.DIALOG)
def _form(context: Context, findings: Findings):
    """The dialog is of a form class the add-on expects of it."""
    found = win.class_name(context.dialog)
    expected = " or ".join(sorted(context.dialog_classes))
    findings.require("", found in context.dialog_classes, expected, found, "Dialogs")


@check("dialog.captions", "dialogs", Scope.DIALOG)
def _captions(context: Context, findings: Findings):
    """Captions of the dialog's labels without windows, read from ezcd's memory, are strings of ezcd."""
    if win.class_name(context.dialog) in _UNCAPTIONED_FORMS:
        raise Skip("its labels are values and scales, not strings of ezcd")
    windows_ = [context.dialog, *win.descendants(context.dialog)]
    captions = {c.text.strip() for w in windows_ for c in _controls(context, w, _LABEL) if c.visible} - {""}
    if not captions:
        raise Skip("the dialog has no label with a caption")
    known = {t for s in context.ezcd.language_files.values() for t in s.values()}
    findings.require(
        "vcl.text", bool(known & captions), "captions that are strings of ezcd", sorted(captions)[:5]
    )


@check("settings.pages", "Settings", Scope.SETTINGS)
def _pages(context: Context, findings: Findings):
    """Settings has the pages the add-on knows: the converter's, the metadata services', the drive's."""
    for form_class in (_CONVERTER_PAGE, _SERVICES_PAGE, _DRIVE_PAGE):
        try:
            windows.settings_page(context, form_class)
        except Skip as skip:
            findings.require("", False, f"the page {form_class}", skip, "Dialogs")


def _counter_buttons(context: Context, findings: Findings, edit: int):
    """The buttons of the counter of the edit: squares of counter.button_size beside it, counter.button_gap
    from it, level with its top."""
    panel = win.parent(edit)
    buttons = _controls(context, panel, _SPEED_BUTTONS)
    left, top, right, _bottom = _client_rect(edit, panel)
    known = context.facts.counter
    scale = context.ezcd.dpi / 96
    size, gap = known.button_size * scale, known.button_gap * scale
    for side, edge in (("left", left), ("right", right)):
        # ezcd puts the buttons 1 to 3 units from the edit, by the window.
        if side == "left":
            beside = [b for b in buttons if abs(edge - (b.left + b.width) - gap) <= scale + _PIXELS]
        else:
            beside = [b for b in buttons if abs(b.left - edge - gap) <= scale + _PIXELS]
        level = [b for b in beside if abs(b.top - top) <= _PIXELS]
        found = ", ".join(f"{b.width} x {b.height} at {b.left}, {b.top}" for b in buttons) or "none"
        findings.require(
            "counter.button_gap",
            bool(level),
            f"a button {gap:.0f} pixels {side} of the edit at {left}, {top}",
            found,
        )
        for button in level:
            square = abs(button.width - size) <= _PIXELS and abs(button.height - size) <= _PIXELS
            found = f"{button.width} x {button.height}"
            findings.require(
                "counter.button_size", square, f"a button of {size:.0f} x {size:.0f} pixels", found
            )


@check("settings.counters", "Settings", Scope.SETTINGS)
def _counters(context: Context, findings: Findings):
    """The counters of Settings (converters and scanners, the limit of metadata results) have their buttons
    where counter says."""
    found = 0
    for form_class in (_CONVERTER_PAGE, _SERVICES_PAGE):
        # A hidden page has no place on the screen: each is measured while shown.
        page = windows.settings_page(context, form_class)
        for panel in win.children(page, "TPanel"):
            if form_class == _SERVICES_PAGE and not win.children(panel, "TCheckListBox"):
                continue
            for edit in win.children(panel, "TEdit"):
                if win.is_visible(edit):
                    found += 1
                    _counter_buttons(context, findings, edit)
    if not found:
        raise Skip("Settings shows no counter")


def _service_list(context: Context) -> int:
    page = windows.settings_page(context, _SERVICES_PAGE)
    lists = [w for w in win.descendants(page) if win.class_name(w) == "TCheckListBox" and win.is_visible(w)]
    if not lists:
        raise Skip("the page of the metadata services shows no list")
    return lists[0]


@check("settings.services", "Settings", Scope.SETTINGS)
def _services(context: Context, findings: Findings):
    """The buttons moving a metadata service lie where service_buttons says: right of the list, one under the
    other, level with its top."""
    services = _service_list(context)
    panel = win.parent(services)
    _left, top, right, _bottom = _client_rect(services, panel)
    known = context.facts.service_buttons
    scale = context.ezcd.dpi / 96
    buttons = sorted(
        (b for b in _controls(context, panel, _SPEED_BUTTONS) if b.visible and b.left >= right),
        key=lambda b: b.top,
    )
    found = ", ".join(f"{b.width} x {b.height} at {b.left}, {b.top}" for b in buttons) or "none"
    expected = (
        f"two buttons of {known.width * scale:.0f} x {known.height * scale:.0f} pixels "
        f"{known.left * scale:.0f} right of the list, the first at its top"
    )
    holds = (
        len(buttons) == 2
        and all(abs(b.left - right - known.left * scale) <= _PIXELS for b in buttons)
        and all(abs(b.width - known.width * scale) <= _PIXELS for b in buttons)
        and all(abs(b.height - known.height * scale) <= _PIXELS for b in buttons)
        and abs(buttons[0].top - top) <= _PIXELS
        and abs(buttons[1].top - buttons[0].top - known.height * scale) <= _PIXELS
    )
    findings.require("service_buttons", holds, expected, found)


@check("vcl.check_state", "Settings", Scope.SETTINGS)
def _check_state(context: Context, findings: Findings):
    """The check boxes of the list of metadata services are read at vcl.check_state: 0, 1 or 2 for every
    item, some of them checked."""
    services = _service_list(context)
    states = []
    for index in range(win.send(services, LB_GETCOUNT) or 0):
        data = win.send(services, LB_GETITEMDATA, index) or 0
        state = ctypes.c_ubyte()
        try:
            context.ezcd.read(data + context.facts.vcl.check_state, state)
        except OSError:
            states.append(None)
            continue
        states.append(state.value)
    if not states:
        raise Skip("the list of metadata services is empty")
    findings.require("vcl.check_state", set(states) <= {0, 1, 2}, "states 0, 1 or 2", states)
    findings.require("vcl.check_state", 1 in states, "some services checked", states)
