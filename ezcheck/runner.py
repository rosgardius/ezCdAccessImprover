"""The run of the chosen checks: each where its scope says, every window opened for them closed again and
the tab shown at the start shown again, also on an error or Ctrl+C."""

import contextlib

from . import main_window, windows
from .core import Check, Context, Result, Scope, Skip, run, skipped
from .main_window import Tab


def _in_dialog(context: Context, opener: windows.Opener, checks: list[Check], results: list[Result]):
    try:
        with windows.opened(context, opener) as dialog:
            context.dialog, context.dialog_classes = dialog, opener.classes
            results.extend(run(c, context, opener.name) for c in checks)
    except Skip as skip:
        results.extend(skipped(c, opener.name, str(skip)) for c in checks)
    finally:
        context.dialog, context.dialog_classes = 0, frozenset()


def _openers(context: Context, tab: Tab) -> list[windows.Opener]:
    """What opens the dialogs of the tab: its buttons that only open a window, and Encoder information on
    the Audio Converter tab, Filename preview on the Audio CD Ripper tab, where it is enabled."""
    found = windows.button_openers(context, tab)
    extra = {Tab.CONVERTER: windows.encoder_information_opener, Tab.RIPPER: windows.filename_preview_opener}
    if tab in extra:
        with contextlib.suppress(Skip):
            found.append(extra[tab](context))
    return found


def run_checks(context: Context, chosen: list[Check]) -> list[Result]:
    by_scope = {scope: [c for c in chosen if c.scope == scope] for scope in Scope}
    results = [run(c, context) for c in by_scope[Scope.ONCE]]
    if not (by_scope[Scope.TAB] or by_scope[Scope.DIALOG] or by_scope[Scope.SETTINGS]):
        return results
    ezcd = context.ezcd
    start = main_window.tab_kind(ezcd, context.facts, main_window.active_tab(ezcd))
    try:
        for tab in Tab:
            where = f"{tab.name.lower()} tab"
            try:
                windows.switch_tab(context, tab)
            except Skip as skip:
                results.extend(skipped(c, where, str(skip)) for c in by_scope[Scope.TAB])
                continue
            results.extend(run(c, context, where) for c in by_scope[Scope.TAB])
            if by_scope[Scope.DIALOG]:
                for opener in _openers(context, tab):
                    _in_dialog(context, opener, by_scope[Scope.DIALOG], results)
        if by_scope[Scope.SETTINGS] or by_scope[Scope.DIALOG]:
            try:
                opener = windows.settings_opener(context)
            except Skip as skip:
                results.extend(skipped(c, "Settings", str(skip)) for c in by_scope[Scope.SETTINGS])
            else:
                _in_dialog(context, opener, by_scope[Scope.DIALOG] + by_scope[Scope.SETTINGS], results)
    finally:
        if start is not None:
            try:
                windows.switch_tab(context, start)
            except Skip:
                print("The tab shown at the start could not be shown again.")
    return results
