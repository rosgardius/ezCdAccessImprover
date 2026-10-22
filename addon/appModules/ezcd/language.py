# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Strings of ezcd's language files (``Language\\*.uni`` next to ``ezcd.exe``)."""

import os
import re

from logHandler import log

_ENTRY = re.compile(r"^\[(\d+)\][ \t]*\n(.*)$", re.MULTILINE)


def _parse(path: str) -> dict[int, str]:
    """The strings of the file; an empty one is left out, as it would match any window without text."""
    with open(path, encoding="utf-16") as file:
        entries = _ENTRY.findall(file.read())
    return {int(number): text.strip() for number, text in entries if text.strip()}


class LanguageFiles:
    """Translations of ezcd's strings in every language it ships.

    The language can be switched while ezcd runs, and the registry shows the new one only later,
    so a caption is matched against all languages.
    """

    def __init__(self, app_path: str | None):
        self._app_path = app_path
        self._files: list[dict[int, str]] | None = None

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

    def texts(self, *numbers: int) -> set[str]:
        """All translations of the given strings."""
        return {strings[n] for strings in self._load() for n in numbers if strings.get(n)}

    def strings_of(self, shown_texts: set[str], numbers: tuple[int, ...] = ()) -> dict[int, str] | None:
        """The strings of the language that has the most of the texts ezcd shows among its strings, or
        among the given ones: languages share many short strings, such as Number in Russian and Bulgarian.
        """

        def shown(strings: dict[int, str]) -> int:
            return len(shown_texts.intersection(map(strings.get, numbers) if numbers else strings.values()))

        best = max(self._load(), key=shown, default=None)
        return best if best is not None and shown(best) else None

    def text_in_language_of(self, number: int, shown_number: int, shown_text: str) -> str | None:
        """The string in the language whose string ``shown_number`` is the text ezcd shows."""
        for strings in self._load():
            if strings.get(shown_number) == shown_text and strings.get(number):
                return strings[number]
        return None
