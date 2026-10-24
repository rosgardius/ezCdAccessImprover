# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Strings of ezcd's language files (``Language\\*.uni`` next to ``ezcd.exe``), the add-on's own strings in
the same languages (``strings\\*.txt``) and the language ezcd shows."""

import functools
import winreg
from collections.abc import Callable
from dataclasses import dataclass

from logHandler import log

from . import facts, version, windows
from .facts.groups import String
from .facts.language import ENGLISH, OWN_BASE

type MainWindowTexts = Callable[[], tuple[set[str], set[str]]]
"""The captions of the main window's tabs and all texts the window shows; empty if it has no tabs yet."""


@functools.cache
def _own_strings(language: str) -> dict[str, str]:
    """The add-on's own strings translated to the language of ezcd's file ``language.uni``, by key; empty
    if they are not."""
    try:
        return facts.language.own_strings(language)
    except (OSError, UnicodeError):
        log.debugWarning(f"No own strings for {language}", exc_info=True)
        return {}


@dataclass(frozen=True)
class OwnString:
    """A string of the add-on's own, by its key in ``strings\\english.txt``: said in the language ezcd
    shows, as ezcd's strings around it are."""

    key: str


def _matches(strings: dict[int, str], texts: set[str], given: tuple[String, ...] = ()) -> int:
    """How many of the texts are strings of the language, or among its given strings."""
    return len(texts.intersection((strings.get(s.number) for s in given) if given else strings.values()))


def _tabs() -> tuple[String, ...]:
    """The captions of the main window's tabs."""
    strings = version.facts.strings
    return strings.converter_tab, strings.ripper_tab, strings.burner_tab


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
            try:
                paths = facts.language.files(self._app_path)
            except OSError:
                log.debugWarning(f"No language files for {self._app_path}", exc_info=True)
                paths = {}
            for name, path in paths.items():
                try:
                    self._files[name] = facts.language.strings(path)
                except (OSError, UnicodeError):
                    log.debugWarning(f"Unreadable language file {path}", exc_info=True)
        return self._files

    @functools.cached_property
    def _configured(self) -> dict[int, str] | None:
        """The strings of the language of ezcd's settings; ``None`` if it is not known.

        ezcd writes a language switched while it runs to its settings only later, and the built-in English
        (no file) not at all, so the language is read once for the ezcd process and compared with the
        captions of the tabs (``tabs_captioned``).
        """
        settings = version.facts.language
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, settings.registry_key) as key:
                name, _type = winreg.QueryValueEx(key, settings.registry_value)
        except OSError:
            log.debugWarning("ezcd's language not in the registry", exc_info=True)
            return None
        number = settings.name.number
        found = next((s for s in self._load().values() if s.get(number) == str(name).strip()), None)
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
        tabs = _tabs()
        most = max((_matches(s, captions, tabs) for s in files), default=0)
        if not most:
            return
        self._tabs_compared = True
        candidates = [s for s in files if _matches(s, captions, tabs) == most]
        known = self._tab_language if self._by_tabs else self._configured
        if any(c is known for c in candidates):
            return
        self._by_tabs = True
        self._tab_language = max(candidates, key=lambda s: _matches(s, shown_texts))
        name = self._tab_language.get(version.facts.language.name.number)
        log.debug(f"ezcd's language by its tabs: {name!r}")

    def knows_any(self, texts: set[str]) -> bool:
        """Whether any of the texts is a string of a language file."""
        return any(_matches(strings, texts) for strings in self._load().values())

    def texts(self, *given: String) -> set[str]:
        """All translations of the given strings, to tell a caption in any language."""
        return {
            strings[s.number] for strings in self._load().values() for s in given if strings.get(s.number)
        }

    def strings(self, shown_texts: set[str], given: tuple[String, ...] = ()) -> dict[int, str]:
        """The strings of the language ezcd shows; empty if none is known.

        It is the language of ezcd's settings, or that of the main window's tabs, unless more of the texts
        ezcd shows, or of those among the given strings, are strings of another language. Languages share
        many short strings, such as Number in Russian and Bulgarian, so a tie keeps the known language.
        """
        best = max(self._load().values(), key=lambda s: _matches(s, shown_texts, given), default=None)
        known = self._known()
        if known is not None and (
            best is None or _matches(known, shown_texts, given) >= _matches(best, shown_texts, given)
        ):
            return known
        return best if best is not None and _matches(best, shown_texts, given) else {}

    def window_strings(self, hwnd: int) -> dict[int, str]:
        """The strings in the language of the control's window, and in English those it lacks, as ezcd
        shows them; empty if no language fits."""
        strings = self.strings(windows.shown_texts(hwnd))
        return {**self._load().get(ENGLISH, {}), **strings} if strings else {}

    def own_string(self, hwnd: int, string: OwnString) -> str:
        """The add-on's string in the language of the control's window, else in English."""
        strings = self.strings(windows.shown_texts(hwnd))
        language = next((name for name, s in self._load().items() if s is strings), OWN_BASE)
        return _own_strings(language).get(string.key) or _own_strings(OWN_BASE)[string.key]
