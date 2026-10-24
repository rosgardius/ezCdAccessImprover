"""Baselines of the audit: what it found in a version of ezcd, by kind (``baselines/<version>.json``)."""

import json
from pathlib import Path

from .addon import facts

BASELINES = Path(__file__).resolve().parent / "baselines"
KINDS = ("unnamed", "windowless", "untabbed")


def nearest(version: str | None, directory: Path = BASELINES) -> Path | None:
    """The baseline of the newest version not newer than the one given, else of the oldest; ``None`` if
    there is none."""
    files = sorted(directory.glob("*.json"), key=lambda p: facts.parse(p.stem))
    current = facts.parse(version)
    older = [p for p in files if facts.parse(p.stem) <= current]
    return older[-1] if older else (files[0] if files else None)


def load(path: Path) -> dict[str, list[str]]:
    with path.open(encoding="utf-8") as file:
        found = json.load(file)
    return {kind: found.get(kind, []) for kind in KINDS}


def write(version: str, found: dict[str, set[str]], directory: Path = BASELINES) -> Path:
    directory.mkdir(exist_ok=True)
    target = directory / f"{version}.json"
    with target.open("w", encoding="utf-8", newline="\n") as file:
        json.dump({kind: sorted(found.get(kind, ())) for kind in KINDS}, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return target


def compare(known: list[str], found: set[str], root: str) -> tuple[list[str], list[str]]:
    """The findings under the root not in the baseline, and those of the baseline under it no longer found."""
    expected = {f for f in known if f == root or f.startswith(f"{root}/")}
    return sorted(found - expected), sorted(expected - found)
