# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Strings of ezcd's language files (``Language\\*.uni`` next to ``ezcd.exe``), the add-on's own strings in
the same languages (``strings\\*.txt``) and the language ezcd shows."""

import functools
import os
import re
import winreg
from collections.abc import Callable
from dataclasses import dataclass

from logHandler import log

from . import windows

_ENTRY = re.compile(r"^\[(\d+)\][ \t]*\n(.*)$", re.MULTILINE)
_SETTINGS_KEY = r"Software\Poikosoft\EZ CD Audio Converter"
# The language of ezcd's settings, as string 0 of its file names it: "English (customizable)".
_LANGUAGE_VALUE = "k82"
_LANGUAGE_NAME = 0
# The captions of the main window's tabs: Audio Converter, Audio CD Ripper, Disc Burner.
_TAB_STRINGS = (172, 171, 390)
_OWN_STRINGS = os.path.join(os.path.dirname(__file__), "strings")
# The language of the add-on's own strings and of their keys, said where they have no translation.
_OWN_BASE = "english"

type MainWindowTexts = Callable[[], tuple[set[str], set[str]]]
"""The captions of the main window's tabs and all texts the window shows; empty if it has no tabs yet."""


def _parse(path: str) -> dict[int, str]:
    """The strings of the file; an empty one is left out, as it would match any window without text."""
    with open(path, encoding="utf-16") as file:
        entries = _ENTRY.findall(file.read())
    return {int(number): text.strip() for number, text in entries if text.strip()}


@functools.cache
def _own_strings(language: str) -> dict[str, str]:
    """The add-on's own strings translated to the language of ezcd's file ``language.uni``, by key; empty
    if they are not."""
    path = os.path.join(_OWN_STRINGS, f"{language}.txt")
    try:
        with open(path, encoding="utf-8-sig") as file:
            lines = file.read().splitlines()
    except (OSError, UnicodeError):
        log.debugWarning(f"No own strings in {path}", exc_info=True)
        return {}
    pairs = (line.partition("=") for line in lines if line.strip() and not line.lstrip().startswith("#"))
    return {key.strip(): value.strip() for key, equals, value in pairs if equals and value.strip()}


@dataclass(frozen=True)
class OwnString:
    """A string of the add-on's own, by its key in ``strings\\english.txt``: said in the language ezcd
    shows, as ezcd's strings around it are."""

    key: str


def _matches(strings: dict[int, str], texts: set[str], numbers: tuple[int, ...] = ()) -> int:
    """How many of the texts are strings of the language, or among its given strings."""
    return len(texts.intersection(map(strings.get, numbers) if numbers else strings.values()))


class LanguageFiles:
    """Translations of ezcd's strings in every language it ships, and the one place that tells which of
    them ezcd shows."""

    def __init__(self, app_path: str | None, main_window: MainWindowTexts):
        self._app_path = app_path
        self._main_window = main_window
        self._files: dict[str, dict[int, str]] | None = None
        """The strings of each language file, by the file's name without ``.uni``."""
        self._tabs_compared = False
        self._by_tabs = False
        """The tabs told another language than the settings: ``_tab_language``."""
        self._tab_language: dict[int, str] | None = None
        """The language of the tabs' captions; ``None`` if it is not known."""

    def _load(self) -> dict[str, dict[int, str]]:
        if self._files is None:
            self._files = {}
            if not self._app_path:
                log.debugWarning("Path of ezcd.exe unknown, no language files")
                return self._files
            directory = os.path.join(os.path.dirname(self._app_path), "Language")
            try:
                names = sorted(os.listdir(directory))
            except OSError:
                log.debugWarning(f"No language files in {directory}", exc_info=True)
                names = []
            for name in names:
                stem, extension = os.path.splitext(name)
                if extension.lower() != ".uni":
                    continue
                try:
                    self._files[stem] = _parse(os.path.join(directory, name))
                except (OSError, UnicodeError):
                    log.debugWarning(f"Unreadable language file {name}", exc_info=True)
        return self._files

    @functools.cached_property
    def _configured(self) -> dict[int, str] | None:
        """The strings of the language of ezcd's settings; ``None`` if it is not known.

        ezcd writes a language switched while it runs to its settings only later, and the built-in English
        (no file) not at all, so the language is read once for the ezcd process and compared with the
        captions of the tabs (``tabs_captioned``).
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _SETTINGS_KEY) as key:
                name, _type = winreg.QueryValueEx(key, _LANGUAGE_VALUE)
        except OSError:
            log.debugWarning("ezcd's language not in the registry", exc_info=True)
            return None
        found = next((s for s in self._load().values() if s.get(_LANGUAGE_NAME) == str(name).strip()), None)
        if found is None:
            log.debugWarning(f"No language file for ezcd's language {name!r}")
        return found

    def _known(self) -> dict[int, str] | None:
        if not self._tabs_compared:
            self.tabs_captioned()
        return self._tab_language if self._by_tabs else self._configured

    def tabs_captioned(self):
        """Compares the known language with the captions of the main window's tabs, as when ezcd captions
        them anew on a switch of its language; again later if the window has no tabs yet.

        The language is the one with the most of the captions among its captions of the tabs; of several,
        the language known so far, else the one with the most of the texts the window shows. Captions of
        no language tell nothing.
        """
        captions, shown_texts = self._main_window()
        files = self._load().values()
        most = max((_matches(s, captions, _TAB_STRINGS) for s in files), default=0)
        if not most:
            return
        self._tabs_compared = True
        candidates = [s for s in files if _matches(s, captions, _TAB_STRINGS) == most]
        known = self._tab_language if self._by_tabs else self._configured
        if any(c is known for c in candidates):
            return
        self._by_tabs = True
        self._tab_language = max(candidates, key=lambda s: _matches(s, shown_texts))
        log.debug(f"ezcd's language by its tabs: {self._tab_language.get(_LANGUAGE_NAME)!r}")

    def knows_any(self, texts: set[str]) -> bool:
        """Whether any of the texts is a string of a language file."""
        return any(_matches(strings, texts) for strings in self._load().values())

    def texts(self, *numbers: int) -> set[str]:
        """All translations of the given strings, to tell a caption in any language."""
        return {strings[n] for strings in self._load().values() for n in numbers if strings.get(n)}

    def strings(self, shown_texts: set[str], numbers: tuple[int, ...] = ()) -> dict[int, str]:
        """The strings of the language ezcd shows; empty if none is known.

        It is the language of ezcd's settings, or that of the main window's tabs, unless more of the texts
        ezcd shows, or of those among the given strings, are strings of another language. Languages share
        many short strings, such as Number in Russian and Bulgarian, so a tie keeps the known language.
        """
        best = max(self._load().values(), key=lambda s: _matches(s, shown_texts, numbers), default=None)
        known = self._known()
        if known is not None and (
            best is None or _matches(known, shown_texts, numbers) >= _matches(best, shown_texts, numbers)
        ):
            return known
        return best if best is not None and _matches(best, shown_texts, numbers) else {}

    def window_strings(self, hwnd: int) -> dict[int, str]:
        """The strings in the language of the control's window; empty if none fits."""
        return self.strings(windows.shown_texts(hwnd))

    def own_string(self, hwnd: int, string: OwnString) -> str:
        """The add-on's string in the language of the control's window, else in English."""
        strings = self.window_strings(hwnd)
        language = next((name for name, s in self._load().items() if s is strings), _OWN_BASE)
        return _own_strings(language).get(string.key) or _own_strings(_OWN_BASE)[string.key]
