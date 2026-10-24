"""The audit: what in ezcd is not accessible by itself, compared with a baseline of an earlier version.

An element is named without language and window handles: by the form, or the tab of the main window, and
the classes of the windows down to it, each with its index among the visible windows of its class under
the same parent, by their places on the screen, as VCL reorders windows and makes them anew.
"""

import json
from pathlib import Path

from . import main_window, win
from .addon import facts
from .core import Context, Skip

BASELINES = Path(__file__).resolve().parent / "baselines"
KINDS = ("unnamed", "windowless", "untabbed")


def root(context: Context) -> tuple[int, str]:
    """The window the audit looks into and its name: the open dialog, else the active tab."""
    if context.dialog:
        tab = f"[{context.dialog_tab.name.lower()}]" if context.dialog_tab is not None else ""
        return context.dialog, f"{win.class_name(context.dialog)}{tab}"
    ezcd = context.ezcd
    tab = main_window.active_tab(ezcd)
    kind = main_window.tab_kind(ezcd, context.facts, tab)
    if kind is None:
        raise Skip("the active tab of the main window is not known")
    return tab, f"TMainform[{kind.name.lower()}]"


def _index(hwnd: int) -> int:
    """The window's index among the visible windows of its class under its parent, by place on the screen."""
    window_class = win.class_name(hwnd)
    siblings = [w for w in win.children(win.parent(hwnd), window_class) if win.is_visible(w)]

    def place(w: int) -> tuple[int, int, int]:
        edge = win.rect(w)
        return edge.top, edge.left, siblings.index(w)

    return sorted(siblings, key=place).index(hwnd) if hwnd in siblings else 0


def path(top: int, name: str, hwnd: int) -> str:
    """The element's name for the window inside ``top``, named ``name``."""
    steps = []
    while hwnd and hwnd != top:
        steps.insert(0, f"{win.class_name(hwnd)}[{_index(hwnd)}]")
        hwnd = win.parent(hwnd)
    return "/".join([name, *steps])


def _version_key(name: str) -> tuple[int, ...]:
    return facts.parse(name)


def baseline(version: str | None) -> tuple[str, dict[str, list[str]]]:
    """The baseline of the nearest version: the newest not newer than ezcd's, else the oldest; its version
    and findings by kind. Raises ``Skip`` if there is none."""
    files = sorted(BASELINES.glob("*.json"), key=lambda p: _version_key(p.stem))
    if not files:
        raise Skip("no baseline in ezcheck/baselines")
    current = facts.parse(version)
    older = [p for p in files if _version_key(p.stem) <= current]
    chosen = older[-1] if older else files[0]
    with chosen.open(encoding="utf-8") as file:
        found = json.load(file)
    return chosen.stem, {kind: found.get(kind, []) for kind in KINDS}


def write_baseline(version: str, found: dict[str, set[str]]) -> Path:
    BASELINES.mkdir(exist_ok=True)
    target = BASELINES / f"{version}.json"
    with target.open("w", encoding="utf-8", newline="\n") as file:
        json.dump({kind: sorted(found.get(kind, ())) for kind in KINDS}, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return target
