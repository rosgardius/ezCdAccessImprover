# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Facts about ezcd that the app module relies on: one set for each version of ezcd that changed any of them.

The package imports only the standard library and itself, so that the checker in ``ezcheck`` loads it
without NVDA.
"""

import enum
import re
from dataclasses import dataclass

from .objects import Vcl


@dataclass(frozen=True)
class Facts:
    since: tuple[int, ...]
    """The version of ezcd from which the set holds."""
    vcl: Vcl


# From the oldest version to the newest; a newer set is ``dataclasses.replace`` of the one before it.
VERSIONS: tuple[Facts, ...] = (
    Facts(
        since=(13, 2, 1, 1),
        vcl=Vcl(
            vmt_class_name=-136,
            controls=0x398,
            list_items=8,
            list_count=16,
            bounds=0x90,
            visible_enabled=0xA9,
            on_click=0x1F8,
            text=0x2D0,
            rating_stars=0x340,
            check_state=16,
        ),
    ),
)
LAST_TESTED = (13, 2, 1, 1)


class Match(enum.Enum):
    """How the set was chosen for the version."""

    KNOWN = enum.auto()
    """The version lies between the first set and the last tested version."""
    NEWER = enum.auto()
    """Newer than the last tested version: the last set."""
    OLDER = enum.auto()
    """Older than the first set: the first set."""
    UNKNOWN = enum.auto()
    """The version could not be read: the last set."""


@dataclass(frozen=True)
class Selection:
    facts: Facts
    match: Match
    version: tuple[int, ...]
    """The version as read, empty if it could not be."""


def parse(product_version: str | None) -> tuple[int, ...]:
    """The numbers of the version, as ``(13, 2, 1, 1)`` for ``"13.2.1.1"``; empty if it has none."""
    return tuple(int(number) for number in re.findall(r"\d+", product_version or ""))


def select(product_version: str | None) -> Selection:
    """The set of facts for the version of ezcd."""
    version = parse(product_version)
    if not version:
        return Selection(VERSIONS[-1], Match.UNKNOWN, version)
    if version < VERSIONS[0].since:
        return Selection(VERSIONS[0], Match.OLDER, version)
    if version > LAST_TESTED:
        return Selection(VERSIONS[-1], Match.NEWER, version)
    facts = next(f for f in reversed(VERSIONS) if f.since <= version)
    return Selection(facts, Match.KNOWN, version)
