# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Strings of ezcd's language files (``Language\\*.uni`` next to ``ezcd.exe``)."""

import os
import re

from logHandler import log

_ENTRY = re.compile(r"^\[(\d+)\][ \t]*\n(.*)$", re.MULTILINE)


def _parse(path: str) -> dict[int, str]:
    with open(path, encoding="utf-16") as file:
        return {int(number): text.strip() for number, text in _ENTRY.findall(file.read())}


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
