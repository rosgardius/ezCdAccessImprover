"""Checks, their results and the context they run in."""

import dataclasses
import enum
import functools
from collections.abc import Callable
from dataclasses import dataclass

from .addon import facts
from .ezcd import Ezcd


class Status(enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Discrepancy:
    """A fact the add-on relies on that does not hold in the running ezcd."""

    field: str
    """The field of the set of facts, as ``explorer.button_strings[29]``; empty if the fact is no field."""
    expected: str
    found: str
    section: str = ""
    """The section of ``docs/ezcd-ui.md`` about it; empty if none."""


@dataclass
class Findings:
    """What a check found: its discrepancies and notes that do not fail it."""

    discrepancies: list[Discrepancy] = dataclasses.field(default_factory=list)
    notes: list[str] = dataclasses.field(default_factory=list)

    def expect(self, field: str, expected: object, found: object, section: str | None = None):
        """Notes a discrepancy unless what was found is what was expected; the section is by default that of
        the field's group (``SECTIONS``)."""
        if found != expected:
            if section is None:
                section = SECTIONS.get(field.split(".")[0].split("[")[0], "")
            self.discrepancies.append(Discrepancy(field, str(expected), str(found), section))


# The sections of docs/ezcd-ui.md about the groups of the set of facts.
SECTIONS = {
    "vcl": "Cover art and rating",
    "language": "Language files",
    "strings": "Language files",
    "top_panels": "Top panels of the main window's tabs",
    "explorer": "Toolbars of the explorer",
    "tray": "Toolbar of the drive's tray",
    "player": "Player of the Audio CD Ripper tab",
    "metadata": "Metadata fields",
    "rating": "Cover art and rating",
    "counter": "Number of converters",
    "service_buttons": "List boxes and list views",
    "convert_window": "Conversion window",
}


class Skip(Exception):
    """The check cannot run on this ezcd or in its state; the message says why."""


@dataclass(frozen=True)
class Result:
    check: "Check"
    status: Status
    reason: str
    """Why the check was skipped; empty otherwise."""
    findings: Findings


class Context:
    """The running ezcd and the set of facts for its version."""

    def __init__(self, ezcd: Ezcd):
        self.ezcd = ezcd

    @functools.cached_property
    def selection(self):
        """``facts.Selection`` for the version of ezcd."""
        return facts.select(self.ezcd.version)

    @property
    def facts(self):
        """The set of facts chosen for the version of ezcd."""
        return self.selection.facts


@dataclass(frozen=True)
class Check:
    id: str
    part: str
    """The part of ezcd it checks."""
    run: Callable[[Context, Findings], None]

    @property
    def description(self) -> str:
        return " ".join((self.run.__doc__ or "").split())

    def matches(self, wanted: str) -> bool:
        """Whether the check is the one wanted or in its group: ``strings`` takes ``strings.english``."""
        return self.id == wanted or self.id.startswith(f"{wanted}.")


CHECKS: list[Check] = []


def check(id: str, part: str):
    """Registers the function as a check: ``run(context, findings)``, raising ``Skip`` when it cannot run."""

    def register(function: Callable[[Context, Findings], None]):
        CHECKS.append(Check(id, part, function))
        return function

    return register


def run(found: Check, context: Context) -> Result:
    findings = Findings()
    try:
        found.run(context, findings)
    except Skip as skip:
        return Result(found, Status.SKIPPED, str(skip), findings)
    status = Status.FAILED if findings.discrepancies else Status.PASSED
    return Result(found, status, "", findings)
