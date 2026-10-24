"""The audit of what in ezcd is not accessible by itself, against the baseline of the nearest version.

A finding not in the baseline fails the check; one of the baseline no longer found is a note.
"""

from collections.abc import Callable

from .. import audit, baseline, msaa, win
from ..core import Context, Findings, Scope, Skip, check

_UNTABBED_CLASSES = frozenset(("TToolBar", "TTrackBar", "TMyTrackBar", "TButton", "TBitBtn", "TPngBitBtn"))
_SPEED_BUTTONS = frozenset(("TSpeedButton", "TPngSpeedButton"))
_CLICKED = frozenset(("TLabel", "TImage"))
_SECTIONS = {
    "unnamed": "Controls without captions",
    "windowless": "Cover art and rating",
    "untabbed": "Keyboard",
}


def _windows(top: int) -> list[int]:
    return [w for w in win.descendants(top) if win.is_visible(w)]


def _unnamed(context: Context, top: int, name: str) -> set[str]:
    """Windows in the Tab order that MSAA gives no name."""
    return {
        audit.path(top, name, w)
        for w in _windows(top)
        if win.style(w) & win.WS_TABSTOP and not msaa.name(w).strip()
    }


def _windowless(context: Context, top: int, name: str) -> set[str]:
    """Controls without windows that take clicks: speed buttons, and labels and images with a handler."""
    found = set()
    for holder in [top, *_windows(top)]:
        try:
            controls = context.ezcd.controls(holder, _SPEED_BUTTONS | _CLICKED, context.facts.vcl)
        except OSError:
            continue
        clicked = [c for c in controls if c.visible and (c.class_name in _SPEED_BUTTONS or c.on_click)]
        for control in clicked:
            same = sorted(
                (c for c in clicked if c.class_name == control.class_name), key=lambda c: (c.top, c.left)
            )
            found.add(f"{audit.path(top, name, holder)}/{control.class_name}[{same.index(control)}]")
    return found


def _untabbed(context: Context, top: int, name: str) -> set[str]:
    """Toolbars, sliders and buttons that Tab does not reach."""
    return {
        audit.path(top, name, w)
        for w in _windows(top)
        if win.class_name(w) in _UNTABBED_CLASSES and not win.style(w) & win.WS_TABSTOP
    }


def _audit(kind: str, find: Callable[[Context, int, str], set[str]], context: Context, findings: Findings):
    top, name = audit.root(context)
    found = find(context, top, name)
    context.cache.setdefault("audit", {}).setdefault(kind, set()).update(found)
    if context.cache.get("writing baseline"):
        findings.notes.append(f"{len(found)} found")
        return
    path = baseline.nearest(context.ezcd.version)
    if path is None:
        raise Skip("no baseline in ezcheck/baselines")
    new, gone = baseline.compare(baseline.load(path)[kind], found, name)
    for finding in new:
        findings.require(
            "", False, f"as in the baseline of ezcd {path.stem}", f"new: {finding}", _SECTIONS[kind]
        )
    findings.notes.extend(f"no longer found: {finding}" for finding in gone)


@check("audit.unnamed", "accessibility", Scope.TAB | Scope.DIALOG)
def _audit_unnamed(context: Context, findings: Findings):
    """Windows in the Tab order without an MSAA name, against the baseline."""
    _audit("unnamed", _unnamed, context, findings)


@check("audit.windowless", "accessibility", Scope.TAB | Scope.DIALOG)
def _audit_windowless(context: Context, findings: Findings):
    """Controls without windows that take clicks, which no screen reader sees by itself, against the
    baseline."""
    _audit("windowless", _windowless, context, findings)


@check("audit.untabbed", "accessibility", Scope.TAB | Scope.DIALOG)
def _audit_untabbed(context: Context, findings: Findings):
    """Toolbars, sliders and buttons that Tab does not reach, against the baseline."""
    _audit("untabbed", _untabbed, context, findings)
