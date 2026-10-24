# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""ezcd's language files (``Language\\*.uni`` next to ``ezcd.exe``) and the add-on's own strings in the same
languages (``strings\\*.txt``, a file named as ezcd's language file)."""

import os
import re

_ENTRY = re.compile(r"^\[(\d+)\][ \t]*\n(.*)$", re.MULTILINE)
_EXTENSION = ".uni"
OWN_STRINGS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "strings")
ENGLISH = "english"
"""ezcd's English file, ``english.uni``: ezcd shows its strings where a translation has none."""
OWN_BASE = ENGLISH
"""The language of the add-on's own strings and of their keys, said where they have no translation."""


def files(app_path: str) -> dict[str, str]:
    """The paths of the language files of the ``ezcd.exe`` at the path, by language: the file's name without
    ``.uni``. Raises ``OSError`` if there is no folder of them."""
    directory = os.path.join(os.path.dirname(app_path), "Language")
    return {
        os.path.splitext(name)[0]: os.path.join(directory, name)
        for name in sorted(os.listdir(directory))
        if os.path.splitext(name)[1].lower() == _EXTENSION
    }


def strings(path: str) -> dict[int, str]:
    """The strings of the language file by number; an empty one is left out, as it would match any window
    without text. Raises ``OSError`` or ``UnicodeError`` if the file cannot be read."""
    with open(path, encoding="utf-16") as file:
        entries = _ENTRY.findall(file.read())
    return {int(number): text.strip() for number, text in entries if text.strip()}


def own_strings(language: str) -> dict[str, str]:
    """The add-on's own strings translated to the language of ezcd's file ``language.uni``, by key. Raises
    ``OSError`` or ``UnicodeError`` if there is no such translation or it cannot be read."""
    with open(os.path.join(OWN_STRINGS, f"{language}.txt"), encoding="utf-8-sig") as file:
        lines = file.read().splitlines()
    pairs = (line.partition("=") for line in lines if line.strip() and not line.lstrip().startswith("#"))
    return {key.strip(): value.strip() for key, equals, value in pairs if equals and value.strip()}
