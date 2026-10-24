"""Checks of ezcd's files: its version and its language files."""

import dataclasses
import os
from collections.abc import Iterator

from ..addon import facts
from ..core import Context, Findings, Skip, check


def _version_text(version: tuple[int, ...]) -> str:
    return ".".join(map(str, version))


def strings_of(value: object, path: str = "") -> Iterator[tuple[str, facts.groups.String]]:
    """Every string of the language files in a set of facts or a group of it, with its field."""
    if isinstance(value, facts.groups.String):
        yield path, value
    elif dataclasses.is_dataclass(value):
        for item in dataclasses.fields(value):
            yield from strings_of(getattr(value, item.name), f"{path}.{item.name}" if path else item.name)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from strings_of(item, f"{path}[{key}]")
    elif isinstance(value, tuple | list):
        for index, item in enumerate(value):
            yield from strings_of(item, f"{path}[{index}]")


@check("version.known", "version")
def _known_version(context: Context, findings: Findings):
    """The version of ezcd has a set of facts: it is not older than the first set nor newer than the last
    tested version."""
    selection = context.selection
    first, last = _version_text(facts.VERSIONS[0].since), _version_text(facts.LAST_TESTED)
    if selection.match != facts.Match.KNOWN:
        field = "LAST_TESTED" if selection.match == facts.Match.NEWER else "VERSIONS[0].since"
        found = context.ezcd.version or "no version"
        findings.expect(field, f"{first} to {last}", found, "")
    findings.notes.append(f"facts of ezcd {_version_text(context.facts.since)} used")


@check("strings.english", "language files")
def _english_strings(context: Context, findings: Findings):
    """Every string of the set of facts has its number in english.uni with the same text; a translation
    without it is a note."""
    files = context.ezcd.language_files
    english = files.get(facts.language.ENGLISH)
    if not english:
        raise Skip(f"no readable Language\\{facts.language.ENGLISH}.uni next to ezcd.exe")
    strings = list(strings_of(context.facts))
    for field, string in strings:
        findings.expect(field, repr(string.english), repr(english.get(string.number, "")))
    numbers = sorted({string.number for _field, string in strings})
    for name, found in files.items():
        if not found:
            findings.notes.append(f"{name}.uni cannot be read")
            continue
        missing = [str(n) for n in numbers if n not in found]
        if missing:
            findings.notes.append(f"{name}.uni has no strings {', '.join(missing)}")


@check("strings.own", "language files")
def _own_strings(context: Context, findings: Findings):
    """Every translation of the add-on's own strings, strings\\<name>.txt, has ezcd's language file
    Language\\<name>.uni: the add-on finds it by that name."""
    files = context.ezcd.language_files
    for name in sorted(os.listdir(facts.language.OWN_STRINGS)):
        stem, extension = os.path.splitext(name)
        if extension.lower() == ".txt":
            findings.expect(
                f"strings\\{name}",
                f"Language\\{stem}.uni",
                f"Language\\{stem}.uni" if stem in files else "none",
                "Language files",
            )
