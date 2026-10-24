"""Checks of the main window on its active tab, without opening any window."""

import ctypes

from .. import main_window, toolbar, win
from ..core import Context, Findings, Skip, check
from ..main_window import Tab

_MENU_MARK = "▼"
# View and Help: the buttons of a top panel that open a menu without the mark.
_PLAIN_MENU_STRINGS = (346, 220, 222)
_LABEL = frozenset(("TLabel",))
_WINDOWLESS = frozenset(("TLabel", "TImage", "TSpeedButton", "TPngSpeedButton", "TRating", "TBevel"))
# How far off a size or a position may be in pixels, after scaling by the DPI.
_PIXELS = 2
_PART_SECTIONS = {
    "top panel": "Top panels of the main window's tabs",
    "explorer": "Toolbars of the explorer",
    "drive panel": "Toolbar of the drive's tray",
    "player": "Player of the Audio CD Ripper tab",
    "metadata panel": "Metadata fields",
    "pages": "Pages of the Disc Burner tab",
}


def _tab(context: Context) -> tuple[Tab, main_window.Parts]:
    """The kind and the parts of the active tab; raises ``Skip`` if it is not known."""
    tab = main_window.active_tab(context.ezcd)
    kind = main_window.tab_kind(context.ezcd, context.facts, tab) if tab else None
    if kind is None:
        raise Skip("the active tab of the main window is not known (see main.tabs)")
    return kind, main_window.parts(tab)


def _buttons(context: Context, toolbars: list[int], hidden: bool = False) -> list[toolbar.Button]:
    """The buttons of the toolbars without separators, from left to right; the hidden ones too if asked."""
    try:
        if not hidden:
            return toolbar.shown_buttons(context.ezcd, toolbars)
        return [b for t in toolbars for b in toolbar.buttons(context.ezcd, t) if not b.separator]
    except OSError as error:
        raise Skip(f"the toolbars cannot be read: {error}") from error


def _controls(context: Context, hwnd: int, classes: frozenset[str] = _WINDOWLESS) -> list:
    try:
        return context.ezcd.controls(hwnd, classes, context.facts.vcl)
    except OSError:
        return []


def _shown_holders(context: Context) -> list[tuple[int, list]]:
    """The visible windows of the active tab with their controls without windows, those that have any."""
    tab = main_window.active_tab(context.ezcd)
    found = [(w, _controls(context, w)) for w in [tab, *win.descendants(tab)] if win.is_visible(w)]
    return [(w, controls) for w, controls in found if controls]


def _described(buttons: list[toolbar.Button]) -> str:
    return ", ".join(b.describe() for b in buttons) or "none"


@check("main.tabs", "main window")
def _tabs(context: Context, findings: Findings):
    """The main window's page control holds three tabs captioned with strings.converter_tab, ripper_tab
    and burner_tab in the language ezcd shows."""
    pages = main_window.page_control(context.ezcd)
    captions = sorted(win.text(t) for t in win.children(pages, "TTabSheet")) if pages else []
    strings = context.facts.strings
    for field, string in (
        ("strings.converter_tab", strings.converter_tab),
        ("strings.ripper_tab", strings.ripper_tab),
        ("strings.burner_tab", strings.burner_tab),
    ):
        caption = context.shown(string)
        findings.require(field, caption in captions, f"a tab captioned {caption!r}", f"tabs {captions}")
    findings.notes.append(f"active tab: {win.text(main_window.active_tab(context.ezcd))!r}")


@check("main.parts", "main window")
def _parts(context: Context, findings: Findings):
    """The active tab shows the parts the add-on recognises by their windows: the top panel, the row above
    the explorer with the breadcrumb bar, the drive's panel, the player, the metadata panel with the cover
    art, the Disc Burner's pages."""
    kind, parts = _tab(context)
    explorer = parts.explorer_bar or parts.hidden_explorer_row
    shown = {
        "top panel": parts.top_panel,
        "explorer": explorer,
        "drive panel": parts.drive_panel,
        "player": parts.player,
        "metadata panel": parts.metadata_panel,
        "pages": parts.burner_pages,
    }
    expected = {
        Tab.CONVERTER: ("top panel", "explorer", "metadata panel"),
        Tab.RIPPER: ("top panel", "drive panel", "player", "metadata panel"),
        Tab.BURNER: ("top panel", "explorer", "drive panel", "pages"),
    }[kind]
    for part in expected:
        findings.require("", bool(shown[part]), f"the {part}", "none", _PART_SECTIONS[part])
    if parts.hidden_explorer_row and not parts.explorer_bar:
        findings.notes.append("the explorer is hidden: its row of toolbars stands in its place")


@check("top_panel.buttons", "top panels")
def _top_panel(context: Context, findings: Findings):
    """The top panel of the active tab has its main button (an image and a caption of top_panels[tab]),
    and the buttons of menu_buttons and context_menu_buttons; every button marked ▼ is in menu_buttons."""
    kind, parts = _tab(context)
    if not parts.top_panel:
        raise Skip("the active tab shows no top panel")
    known = context.facts.top_panels[kind]
    field = f"top_panels[{kind.value}]"
    buttons = _buttons(context, main_window.shown_toolbars(parts.top_panel))
    keys: dict[tuple[int, int], toolbar.Button] = {}
    for button in buttons:
        image = next(
            (p.main_images[0] for p in context.facts.top_panels if button.image in p.main_images),
            button.image,
        )
        keys[image, sum(key[0] == image for key in keys)] = button
    captions = {t for s in known.main_strings for t in context.translations(s)}
    main = [
        b
        for b in buttons
        if b.image in known.main_images
        and b.text.strip() in captions
        and sum(other.toolbar == b.toolbar for other in buttons) == 1
    ]
    shown_captions = " or ".join(sorted({repr(context.shown(s)) for s in known.main_strings}))
    images = " or ".join(map(str, known.main_images))
    findings.require(
        f"{field}.main_images",
        bool(main),
        f"a button of image {images} captioned {shown_captions} on a toolbar of its own",
        _described(buttons),
    )
    plain = {t for n in _PLAIN_MENU_STRINGS for s in context.ezcd.language_files.values() if (t := s.get(n))}
    for key in sorted(known.menu_buttons):
        button = keys.get(key)
        opens = button is not None and (_MENU_MARK in button.text or button.text.strip() in plain)
        found = "none" if button is None else button.describe()
        findings.require(f"{field}.menu_buttons", opens, f"a menu button at {key}", found)
    for key, button in sorted(keys.items()):
        if _MENU_MARK in button.text:
            findings.require(
                f"{field}.menu_buttons",
                key in known.menu_buttons,
                f"{key} among them",
                f"{button.describe()}",
            )
    for key in sorted(known.context_menu_buttons):
        findings.require(f"{field}.context_menu_buttons", key in keys, f"a button at {key}", "none")


def _named_images(findings: Findings, field: str, buttons: list[toolbar.Button], strings: dict):
    """Every button that shows only an image has a string in ``strings``."""
    for button in buttons:
        if not button.text:
            findings.require(field, button.image in strings, f"a string for image {button.image}", "none")


@check("explorer.buttons", "explorer")
def _explorer(context: Context, findings: Findings):
    """The toolbars of the explorer, or of the row in its place, have View Explorer and a string in
    explorer.button_strings for every button without text; one of them, the view, has a drop-down
    arrow."""
    _kind, parts = _tab(context)
    row = parts.explorer_bar or parts.hidden_explorer_row
    if not row:
        raise Skip("the active tab has no explorer")
    known = context.facts.explorer
    buttons = _buttons(context, main_window.shown_toolbars(row))
    findings.require(
        "explorer.view_explorer",
        any(b.image == known.view_explorer for b in buttons),
        f"a button of image {known.view_explorer}",
        _described(buttons),
    )
    _named_images(findings, "explorer.button_strings", buttons, known.button_strings)
    if parts.explorer_bar:
        views = [b for b in buttons if b.dropdown]
        findings.require(
            "explorer.button_strings", len(views) == 1, "one button with a drop-down arrow", _described(views)
        )


@check("tray.buttons", "drive")
def _tray(context: Context, findings: Findings):
    """The toolbar of the drive's tray has Open tray and Close tray, one of them hidden, and a string in
    tray.button_strings for every button without text."""
    _kind, parts = _tab(context)
    if not parts.drive_panel:
        raise Skip("the active tab has no drive")
    buttons = _buttons(context, main_window.shown_toolbars(parts.drive_panel), hidden=True)
    known = context.facts.tray
    for field, image in (("tray.open_tray", known.open_tray), ("tray.close_tray", known.close_tray)):
        findings.require(
            field, any(b.image == image for b in buttons), f"a button of image {image}", _described(buttons)
        )
    shown_pair = [b for b in buttons if b.image in (known.open_tray, known.close_tray) and not b.hidden]
    findings.require(
        "tray.open_tray", len(shown_pair) == 1, "Open tray or Close tray shown", _described(shown_pair)
    )
    _named_images(findings, "tray.button_strings", [b for b in buttons if not b.hidden], known.button_strings)


@check("player.buttons", "player")
def _player(context: Context, findings: Findings):
    """The toolbar of the player has a button for every image of player.button_strings and no other."""
    _kind, parts = _tab(context)
    if not parts.player:
        raise Skip("the active tab has no player")
    toolbars = [
        t for holder in win.children(parts.player, "TPanel") for t in main_window.shown_toolbars(holder)
    ]
    buttons = _buttons(context, toolbars)
    findings.expect(
        "player.button_strings", sorted(context.facts.player.button_strings), sorted(b.image for b in buttons)
    )


@check("vcl.controls", "memory")
def _vcl_controls(context: Context, findings: Findings):
    """The controls without windows of the active tab are read from ezcd's memory (vcl.controls,
    list_items, list_count, vmt_class_name, bounds, visible_enabled): there are some, the visible ones lie
    in their windows, FVisible and FEnabled are 0 or 1."""
    holders = _shown_holders(context)
    findings.require("vcl.controls", bool(holders), "controls without windows in the active tab", "none")
    offsets = context.facts.vcl
    for hwnd, controls in holders:
        edge = win.rect(hwnd)
        width, height = edge.right - edge.left, edge.bottom - edge.top
        for control in controls:
            where = f"{control.class_name} in {win.class_name(hwnd)}"
            if control.visible and control.width and control.height:
                inside = (
                    control.left >= 0
                    and control.top >= 0
                    and control.left + control.width <= width + _PIXELS
                    and control.top + control.height <= height + _PIXELS
                )
                found = f"{control.width} x {control.height} at {control.left}, {control.top}"
                findings.require("vcl.bounds", inside, f"{where} inside its window", found)
            flags = (ctypes.c_ubyte * 2)()
            try:
                context.ezcd.read(control.address + offsets.visible_enabled, flags)
            except OSError as error:
                findings.require("vcl.visible_enabled", False, f"{where}: flags read", error)
                continue
            findings.require(
                "vcl.visible_enabled", set(flags) <= {0, 1}, f"{where}: flags 0 or 1", list(flags)
            )


@check("vcl.text", "memory")
def _vcl_text(context: Context, findings: Findings):
    """Captions of the visible labels of the active tab, read at vcl.text, are strings of the language
    files."""
    labels = [
        c
        for _hwnd, controls in _shown_holders(context)
        for c in controls
        if c.class_name == "TLabel" and c.visible
    ]
    if not labels:
        raise Skip("the active tab shows no label")
    captions = {c.text.strip() for c in labels} - {""}
    known = {t for s in context.ezcd.language_files.values() for t in s.values()}
    findings.require(
        "vcl.text", bool(known & captions), "captions that are strings of ezcd", sorted(captions)[:5]
    )


@check("vcl.on_click", "memory")
def _vcl_on_click(context: Context, findings: Findings):
    """The handler of clicks, read at vcl.on_click, is set for every speed button without a window of the
    active tab and not for every control, as labels that are no links have none."""
    controls = [c for _hwnd, found in _shown_holders(context) for c in found if c.visible]
    buttons = [c for c in controls if c.class_name in ("TSpeedButton", "TPngSpeedButton")]
    if not buttons:
        raise Skip("the active tab shows no speed button")
    for button in buttons:
        findings.require(
            "vcl.on_click",
            button.on_click,
            f"a handler of clicks for {button.class_name} {button.text!r}",
            "none",
        )
    findings.require(
        "vcl.on_click", not all(c.on_click for c in controls), "controls without a handler too", "none"
    )


@check("rating", "metadata panel")
def _rating(context: Context, findings: Findings):
    """The rating of the metadata panel has 0 to rating.stars stars at vcl.rating_stars, its stars of
    rating.star_width design units fit it, and its caption, rating.caption, is left of it."""
    _kind, parts = _tab(context)
    if not parts.metadata_panel:
        raise Skip("the active tab has no metadata panel")
    controls = _controls(context, parts.metadata_panel, frozenset(("TRating", "TLabel")))
    rating = next((c for c in controls if c.class_name == "TRating" and c.visible), None)
    if rating is None:
        raise Skip("the metadata panel shows no rating: the Rating field is off in ezcd's settings")
    known = context.facts.rating
    stars = (ctypes.c_int32 * 1)()
    context.ezcd.read(rating.address + context.facts.vcl.rating_stars, stars)
    findings.require("vcl.rating_stars", 0 <= stars[0] <= known.stars, f"0 to {known.stars} stars", stars[0])
    star = known.star_width * context.ezcd.dpi / 96
    fits = rating.width >= known.stars * star - _PIXELS and abs(rating.height - star) <= _PIXELS
    found = f"a rating of {rating.width} x {rating.height} pixels"
    findings.require(
        "rating.star_width", fits, f"{known.stars} stars of {star:.0f} pixels in the rating", found
    )
    caption = context.shown(known.caption)
    beside = [
        c.text.strip()
        for c in controls
        if c.class_name == "TLabel"
        and c.visible
        and c.left < rating.left
        and abs(c.top - rating.top) <= _PIXELS
    ]
    findings.require("rating.caption", caption in beside, f"{caption!r} left of the rating", beside)


@check("metadata.captions", "metadata panel")
def _metadata_captions(context: Context, findings: Findings):
    """Every caption of the metadata panel is in metadata.captions in the language ezcd shows, and so are
    metadata.number and disc_number."""
    _kind, parts = _tab(context)
    if not parts.metadata_panel:
        raise Skip("the active tab has no metadata panel")
    labels = _controls(context, parts.metadata_panel, _LABEL)
    known = {context.shown(s) for s in context.facts.metadata.captions}
    shown = sorted({c.text.strip() for c in labels if c.visible and any(ch.isalpha() for ch in c.text)})
    if not shown:
        raise Skip("the metadata panel shows no caption")
    for caption in shown:
        findings.require("metadata.captions", caption in known, f"{caption!r} among them", "not among them")
    metadata = context.facts.metadata
    for field, string in (
        ("metadata.number", metadata.number),
        ("metadata.disc_number", metadata.disc_number),
    ):
        caption = context.shown(string)
        findings.require(field, caption in shown, f"{caption!r} on the panel", "none")


@check("burner.pages", "Disc Burner")
def _burner_pages(context: Context, findings: Findings):
    """The pages of the Disc Burner tab are switched by three speed buttons without windows right above
    them, captioned strings.audio_cd_page, mp3_disc_page and data_disc_page; the shown page has one of
    these captions."""
    kind, parts = _tab(context)
    if kind != Tab.BURNER or not parts.burner_pages:
        raise Skip("the Disc Burner tab is not active")
    strings = context.facts.strings
    shown = [context.shown(s) for s in (strings.audio_cd_page, strings.mp3_disc_page, strings.data_disc_page)]
    edge = win.rect(parts.burner_pages)
    panel = next(
        (
            p
            for p in win.children(win.parent(parts.burner_pages), "TPanel")
            if abs(win.rect(p).bottom - edge.top) <= _PIXELS and not win.children(p)
        ),
        0,
    )
    buttons = [c for c in _controls(context, panel) if c.class_name == "TPngSpeedButton" and c.visible]
    captions = [c.text for c in sorted(buttons, key=lambda c: c.left)]
    findings.expect(
        "strings.audio_cd_page",
        f"page buttons {shown}",
        f"page buttons {captions}",
        "Pages of the Disc Burner tab",
    )
    page = next((t for t in win.children(parts.burner_pages, "TTabSheet") if win.is_visible(t)), 0)
    findings.require(
        "strings.audio_cd_page",
        win.text(page) in shown,
        "the shown page with one of these captions",
        repr(win.text(page)),
        "Pages of the Disc Burner tab",
    )
