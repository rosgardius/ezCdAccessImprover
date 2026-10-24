"""Opening ezcd's windows without the foreground, and closing them as their close box does.

A button, a menu item or a point of a click is chosen by ezcd's strings, a window class and VCL objects,
never by its place alone. Only windows that change nothing are opened; a dialog closes with ``WM_CLOSE``,
which keeps none of its changes.
"""

import contextlib
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from . import main_window, menus, toolbar, win
from .core import Context, Skip
from .main_window import Tab

WM_CLOSE, WM_COMMAND, BM_CLICK = 0x0010, 0x0111, 0x00F5
WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON = 0x0201, 0x0202, 0x0001
# Settings on every top panel.
_SETTINGS_STRING = 274
_OPENS_WINDOW = ("»", "...", "…")
_OPEN_TIMEOUT = 3.0
_CLOSE_TIMEOUT = 3.0
_TAB_TIMEOUT = 3.0
_POLL = 0.05
_NOT_DIALOGS = frozenset(("TMainform", "TApplication", "THintWindow", "#32768"))
_SPEED_BUTTONS = frozenset(("TSpeedButton", "TPngSpeedButton"))
_MENU_MARK = "▼"


@dataclass(frozen=True)
class Opener:
    name: str
    """What is opened, as the report names it."""
    classes: frozenset[str]
    """The form classes the add-on expects of it."""
    open: Callable[[], object]
    """Clicks what opens it, without waiting."""
    tab: Tab | None = None
    """The tab it is opened from, if what it shows depends on the tab."""


def _dialogs(context: Context) -> set[int]:
    ezcd = context.ezcd
    return {
        w
        for w in win.top_level_windows()
        if win.is_visible(w)
        and win.thread_and_process(w)[1] == ezcd.process_id
        and win.class_name(w) not in _NOT_DIALOGS
    }


@contextlib.contextmanager
def opened(context: Context, opener: Opener) -> Iterator[int]:
    """The dialog the opener opens, closed again when done; raises ``Skip`` if none opens in time."""
    before = _dialogs(context)
    opener.open()
    end = time.monotonic() + _OPEN_TIMEOUT
    new: set[int] = set()
    while not new and time.monotonic() < end:
        time.sleep(_POLL)
        new = _dialogs(context) - before
    if not new:
        raise Skip(f"{opener.name} did not open")
    dialog = next(iter(new))
    try:
        # The form shows before its controls are made.
        time.sleep(0.3)
        yield dialog
    finally:
        for window in new:
            win.post(window, WM_CLOSE)
        end = time.monotonic() + _CLOSE_TIMEOUT
        while (_dialogs(context) - before) and time.monotonic() < end:
            time.sleep(_POLL)


def _top_buttons(context: Context) -> list[toolbar.Button]:
    parts = main_window.parts(main_window.active_tab(context.ezcd))
    if not parts.top_panel:
        raise Skip("the active tab shows no top panel")
    return toolbar.shown_buttons(context.ezcd, main_window.shown_toolbars(parts.top_panel))


def _click_button(button: toolbar.Button):
    left, top, right, bottom = button.rect
    point = (((top + bottom) // 2) << 16) | ((left + right) // 2)
    win.post(button.toolbar, WM_LBUTTONDOWN, MK_LBUTTON, point)
    win.post(button.toolbar, WM_LBUTTONUP, 0, point)


def tab_menu(context: Context) -> menus.Menu:
    """The menu of the first button of the top panel, which switches the tabs; raises ``Skip`` if it does not
    open."""
    buttons = [b for b in _top_buttons(context) if _MENU_MARK in b.text]
    if not buttons:
        raise Skip("the top panel has no menu button")
    try:
        menu = menus.peek(context.ezcd, lambda: _click_button(buttons[0]))
    except menus.Foreground as error:
        raise Skip(str(error)) from error
    if menu is None or len(menu.ids) != len(Tab):
        raise Skip(f"the first button of the top panel opened no menu of {len(Tab)} items")
    return menu


def switch_tab(context: Context, tab: Tab):
    """Shows the tab of the main window as its item of the tab menu does; raises ``Skip`` if it cannot.

    The items have no text outside ezcd: each is tried until the tab with the caption of the wanted one
    shows. Which item shows which tab is kept for the run.
    """
    ezcd = context.ezcd

    def shown() -> Tab | None:
        return main_window.tab_kind(ezcd, context.facts, main_window.active_tab(ezcd))

    if shown() == tab:
        return
    if "tab items" not in context.cache:
        menu = tab_menu(context)
        context.cache["tab items"] = (menu.owner, {}, list(menu.ids))
    owner, known, untried = context.cache["tab items"]
    for item in [known[tab]] if tab in known else list(untried):
        before = shown()
        # The window owning the menus takes the command of any item, the menu closed.
        win.post(owner, WM_COMMAND, item)
        end = time.monotonic() + _TAB_TIMEOUT
        while shown() == before and time.monotonic() < end:
            time.sleep(_POLL)
        now = shown()
        if now is not None:
            known[now] = item
        if item in untried:
            untried.remove(item)
        if now == tab:
            return
    raise Skip(f"the tab menu did not show the {tab.name.lower()} tab")


def _opens_window(text: str) -> bool:
    return text.rstrip().endswith(_OPENS_WINDOW)


def button_openers(context: Context, tab: Tab) -> list[Opener]:
    """The buttons of the active tab whose captions end in » or ...: they only open a window."""
    parts = main_window.parts(main_window.active_tab(context.ezcd))
    expected = {
        Tab.CONVERTER: frozenset(("TConverterOptions", "TDSPForm", "TProfile_Editor")),
        Tab.RIPPER: frozenset(("TRipperOptions", "TDSPForm", "TProfile_Editor")),
        Tab.BURNER: frozenset(("TAudioCDOptions",)),
    }[tab]
    return [
        Opener(
            f"{win.text(b)!r} of the {tab.name.lower()} tab", expected, lambda b=b: win.post(b, BM_CLICK), tab
        )
        for b in win.descendants(parts.tab)
        if win.class_name(b) == "TButton"
        and win.is_visible(b)
        and win.is_enabled(b)
        and _opens_window(win.text(b))
    ]


def settings_opener(context: Context) -> Opener:
    """Settings, the button of the top panel captioned so."""
    captions = {s.get(_SETTINGS_STRING) for s in context.ezcd.language_files.values()} - {None}
    button = next((b for b in _top_buttons(context) if b.text.strip() in captions), None)
    if button is None:
        raise Skip("the top panel has no Settings")
    return Opener("Settings", frozenset(("TSettings2Form",)), lambda: _click_button(button))


def filename_preview_opener(context: Context, tab: Tab) -> Opener:
    """Filename preview: the button with only an image right next to the template of the file names, a combo
    box where the template is typed."""
    sheet = main_window.active_tab(context.ezcd)
    for combo in win.descendants(sheet):
        if (
            win.class_name(combo) != "TComboBox"
            or not win.children(combo, "Edit")
            or not win.is_visible(combo)
        ):
            continue
        edge = win.rect(combo)
        for button in win.children(win.parent(combo), "TButton"):
            other = win.rect(button)
            beside = 0 <= other.left - edge.right <= 10 and abs(other.top - edge.top) <= 4
            if beside and not win.text(button) and win.is_visible(button) and win.is_enabled(button):
                return Opener(
                    "Filename preview",
                    frozenset(("TNamePreview",)),
                    lambda b=button: win.post(b, BM_CLICK),
                    tab,
                )
    raise Skip("no enabled button of Filename preview on the active tab")


def encoder_information_opener(context: Context, tab: Tab) -> Opener:
    """Encoder information: the speed button without a window in the output panel, the panel of the format."""
    sheet = main_window.active_tab(context.ezcd)
    panel = next(
        (
            p
            for p in win.descendants(sheet)
            if win.class_name(p) == "TPanel" and win.children(p, "TComboBoxEx")
        ),
        0,
    )
    controls = context.ezcd.controls(panel, _SPEED_BUTTONS, context.facts.vcl) if panel else []
    buttons = [c for c in controls if c.visible and c.enabled]
    if len(buttons) != 1:
        raise Skip("no single speed button in the output panel")
    button = buttons[0]
    point = ((button.top + button.height // 2) << 16) | (button.left + button.width // 2)

    def click():
        win.post(panel, WM_LBUTTONDOWN, MK_LBUTTON, point)
        win.post(panel, WM_LBUTTONUP, 0, point)

    return Opener("Encoder information", frozenset(("TEncoderInfo",)), click, tab)


_TVM_GETNEXTITEM, _TVM_SELECTITEM = 0x110A, 0x110B
_TVGN_ROOT, _TVGN_NEXT, _TVGN_CHILD, _TVGN_CARET = 0x0, 0x1, 0x4, 0x9
_PAGE_TIMEOUT = 2.0


def _tree_items(tree: int) -> list[int]:
    """All items of the tree view, each followed by its children."""
    found = []

    def walk(item: int):
        while item:
            found.append(item)
            walk(win.send(tree, _TVM_GETNEXTITEM, _TVGN_CHILD, item) or 0)
            item = win.send(tree, _TVM_GETNEXTITEM, _TVGN_NEXT, item) or 0

    walk(win.send(tree, _TVM_GETNEXTITEM, _TVGN_ROOT, 0) or 0)
    return found


def _shown_page(dialog: int) -> int:
    return next(
        (
            w
            for w in win.descendants(dialog)
            if win.class_name(w).startswith("TSettings2") and win.is_visible(w)
        ),
        0,
    )


def settings_page(context: Context, form_class: str) -> int:
    """The page of the open Settings of the form class, shown by selecting its item in the tree of pages, as a
    click on it does; raises ``Skip`` if no item shows it. Changes no setting."""
    dialog = context.dialog
    tree = next(iter(win.children(dialog, "TTreeView")), 0)
    if not tree:
        raise Skip("Settings has no tree of pages")
    known: dict[str, int] = context.cache.setdefault(f"pages of {dialog:#x}", {})
    items = [known[form_class]] if form_class in known else _tree_items(tree)
    for item in items:
        win.send(tree, _TVM_SELECTITEM, _TVGN_CARET, item)
        end = time.monotonic() + _PAGE_TIMEOUT
        page = _shown_page(dialog)
        while not page and time.monotonic() < end:
            time.sleep(_POLL)
            page = _shown_page(dialog)
        if page:
            known[win.class_name(page)] = item
            if win.class_name(page) == form_class:
                # Its controls are made as it shows.
                time.sleep(0.2)
                return page
    raise Skip(f"no page {form_class} in Settings")
