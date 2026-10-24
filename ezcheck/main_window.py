"""The parts of ezcd's main window, recognised by their windows as the add-on recognises them."""

import enum
from dataclasses import dataclass

from . import win
from .ezcd import Ezcd


class Tab(enum.IntEnum):
    """The main window's tabs, by their place in ``Facts.top_panels``."""

    CONVERTER = 0
    RIPPER = 1
    BURNER = 2


@dataclass(frozen=True)
class Parts:
    """The parts of the active tab that it shows; 0 for one it does not."""

    tab: int
    top_panel: int
    explorer_bar: int
    """The row above the explorer, with the breadcrumb bar."""
    hidden_explorer_row: int
    """The row of toolbars in place of the hidden explorer."""
    drive_panel: int
    player: int
    metadata_panel: int
    burner_pages: int


def page_control(ezcd: Ezcd) -> int:
    return next(iter(win.children(ezcd.main, "TPageControl")), 0)


def active_tab(ezcd: Ezcd) -> int:
    return next((t for t in win.children(page_control(ezcd), "TTabSheet") if win.is_visible(t)), 0)


def tab_kind(ezcd: Ezcd, facts, tab: int) -> Tab | None:
    """Which tab the window is, by its caption in any language; ``None`` if none."""
    strings = facts.strings
    caption = win.text(tab)
    for kind, string in zip(
        Tab, (strings.converter_tab, strings.ripper_tab, strings.burner_tab), strict=True
    ):
        if any(s.get(string.number) == caption for s in ezcd.language_files.values()):
            return kind
    return None


def _toolbars_only(panel: int) -> bool:
    children = win.children(panel)
    return bool(children) and all(win.class_name(c) == "TToolBar" for c in children)


def _shown(windows: list[int]) -> list[int]:
    return [w for w in windows if win.is_visible(w)]


def parts(tab: int) -> Parts:
    panels = [w for w in win.descendants(tab) if win.class_name(w) == "TPanel" and win.is_visible(w)]

    def first(condition) -> int:
        return next((p for p in panels if condition(p)), 0)

    explorer_bar = first(lambda p: bool(win.children(p, "TJamShellBreadCrumbBar")))
    # The panels of toolbars alone right in the tab: the top panel above, the row of the hidden explorer.
    rows = sorted(
        (p for p in _shown(win.children(tab, "TPanel")) if _toolbars_only(p)), key=lambda p: win.rect(p).top
    )
    hidden_row = next(
        (
            p
            for p in panels
            if p not in rows[:1]
            and _toolbars_only(p)
            and any(
                q != p and win.children(q, "TJamShellBreadCrumbBar") and win.rect(q).top <= win.rect(p).top
                for q in win.children(win.parent(p), "TPanel")
            )
        ),
        0,
    )
    burner_pages = next(
        (w for w in win.descendants(tab) if win.class_name(w) == "TPageControl" and win.is_visible(w)), 0
    )
    return Parts(
        tab=tab,
        top_panel=rows[0] if rows else 0,
        explorer_bar=explorer_bar,
        hidden_explorer_row=hidden_row,
        drive_panel=first(
            lambda p: bool(win.children(p, "TToolBar")) and len(win.children(p, "TComboBox")) == 2
        ),
        player=first(lambda p: bool(win.children(p, "TTrackBar")) and bool(win.children(p, "TMyTrackBar"))),
        metadata_panel=first(lambda p: bool(win.children(p, "TDropPanel"))),
        burner_pages=burner_pages,
    )


def shown_toolbars(panel: int) -> list[int]:
    return _shown(win.children(panel, "TToolBar"))
