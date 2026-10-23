# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Strings of ezcd's language files (``Language\\*.uni`` next to ``ezcd.exe``) and the language ezcd shows."""

import functools
import os
import re
import winreg
from collections.abc import Callable

from logHandler import log

_ENTRY = re.compile(r"^\[(\d+)\][ \t]*\n(.*)$", re.MULTILINE)
_SETTINGS_KEY = r"Software\Poikosoft\EZ CD Audio Converter"
# The language of ezcd's settings, as string 0 of its file names it: "English (customizable)".
_LANGUAGE_VALUE = "k82"
_LANGUAGE_NAME = 0
# The captions of the main window's tabs: Audio Converter, Audio CD Ripper, Disc Burner.
_TAB_STRINGS = (172, 171, 390)

type MainWindowTexts = Callable[[], tuple[set[str], set[str]]]
"""The captions of the main window's tabs and all texts the window shows; empty if it has no tabs yet."""


def _parse(path: str) -> dict[int, str]:
    """The strings of the file; an empty one is left out, as it would match any window without text."""
    with open(path, encoding="utf-16") as file:
        entries = _ENTRY.findall(file.read())
    return {int(number): text.strip() for number, text in entries if text.strip()}


def _matches(strings: dict[int, str], texts: set[str], numbers: tuple[int, ...] = ()) -> int:
    """How many of the texts are strings of the language, or among its given strings."""
    return len(texts.intersection(map(strings.get, numbers) if numbers else strings.values()))


class LanguageFiles:
    """Translations of ezcd's strings in every language it ships, and the one place that tells which of
    them ezcd shows."""

    def __init__(self, app_path: str | None, main_window: MainWindowTexts):
        self._app_path = app_path
        self._main_window = main_window
        self._files: list[dict[int, str]] | None = None
        self._tabs_compared = False
        self._by_tabs = False
        """The tabs told another language than the settings: ``_tab_language``."""
        self._tab_language: dict[int, str] | None = None
        """The language of the tabs' captions; ``None`` if it is not known."""

    def _load(self) -> list[dict[int, str]]:
        if self._files is None:
            self._files = []
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
                if not name.lower().endswith(".uni"):
                    continue
                try:
                    self._files.append(_parse(os.path.join(directory, name)))
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
        found = next((s for s in self._load() if s.get(_LANGUAGE_NAME) == str(name).strip()), None)
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
        files = self._load()
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

    def texts(self, *numbers: int) -> set[str]:
        """All translations of the given strings, to tell a caption in any language."""
        return {strings[n] for strings in self._load() for n in numbers if strings.get(n)}

    def strings(self, shown_texts: set[str], numbers: tuple[int, ...] = ()) -> dict[int, str]:
        """The strings of the language ezcd shows; empty if none is known.

        It is the language of ezcd's settings, or that of the main window's tabs, unless more of the texts
        ezcd shows, or of those among the given strings, are strings of another language. Languages share
        many short strings, such as Number in Russian and Bulgarian, so a tie keeps the known language.
        """
        best = max(self._load(), key=lambda s: _matches(s, shown_texts, numbers), default=None)
        known = self._known()
        if known is not None and (
            best is None or _matches(known, shown_texts, numbers) >= _matches(best, shown_texts, numbers)
        ):
            return known
        return best if best is not None and _matches(best, shown_texts, numbers) else {}
