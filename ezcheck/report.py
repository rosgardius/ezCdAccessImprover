"""The report of a run: text for people, JSON for programs."""

import json

from .core import Context, Result, Status

_MARKS = {Status.PASSED: "PASSED ", Status.FAILED: "FAILED ", Status.SKIPPED: "SKIPPED"}


def header(context: Context) -> dict[str, object]:
    """What was checked: ezcd and its state."""
    ezcd = context.ezcd
    return {
        "version": ezcd.version,
        "path": ezcd.path,
        "facts": ".".join(map(str, context.facts.since)),
        "match": context.selection.match.name.lower(),
        "language": ezcd.language,
        "dpi": ezcd.dpi,
        "theme": ezcd.theme,
    }


def text(context: Context, results: list[Result]) -> str:
    about = header(context)
    lines = [
        f"EZ CD Audio Converter {about['version'] or '(no version)'} at {about['path']}",
        f"Facts of ezcd {about['facts']} ({about['match']} version); "
        f"language {about['language'] or 'unknown'}, {about['dpi']} DPI, {about['theme']} theme",
        "",
    ]
    for result in results:
        reason = f": {result.reason}" if result.reason else ""
        lines.append(f"{_MARKS[result.status]} {result.check.id}{reason}")
        for found in result.findings.discrepancies:
            where = f" ({found.section})" if found.section else ""
            lines.append(f"    {found.field or '-'}: expected {found.expected}, found {found.found}{where}")
        lines.extend(f"    note: {note}" for note in result.findings.notes)
    counts = {status: sum(r.status == status for r in results) for status in Status}
    lines += ["", ", ".join(f"{count} {status.value}" for status, count in counts.items())]
    return "\n".join(lines)


def as_json(context: Context, results: list[Result], exit_code: int) -> str:
    return json.dumps(
        {
            "ezcd": header(context),
            "results": [
                {
                    "id": r.check.id,
                    "part": r.check.part,
                    "status": r.status.value,
                    "reason": r.reason,
                    "discrepancies": [vars(d) for d in r.findings.discrepancies],
                    "notes": r.findings.notes,
                }
                for r in results
            ],
            "exit_code": exit_code,
        },
        ensure_ascii=False,
        indent=2,
    )
