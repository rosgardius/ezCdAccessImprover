"""Runs the checker: ``uv run python -m ezcheck [--list] [--only ID ...] [--json]``.

Exit codes: 0 every fact holds, 1 some do not, 2 ezcd could not be checked.
"""

import argparse
import sys

from . import report, win
from .checks import CHECKS
from .core import Context, Status
from .ezcd import Ezcd, Unavailable
from .runner import run_checks

EXIT_PASSED, EXIT_FAILED, EXIT_UNAVAILABLE = 0, 1, 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ezcheck",
        description="Checks that the facts about EZ CD Audio Converter the add-on relies on hold in the "
        "running ezcd. Changes nothing in ezcd.",
    )
    parser.add_argument("--list", action="store_true", help="list the checks and exit")
    parser.add_argument("--only", nargs="+", metavar="ID", help="run only these checks or groups (strings)")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    return parser


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = _parser().parse_args()
    if args.list:
        for found in CHECKS:
            print(f"{found.id:24} {found.part:16} {found.description}")
        return EXIT_PASSED
    chosen = [c for c in CHECKS if not args.only or any(c.matches(wanted) for wanted in args.only)]
    if not chosen:
        print(f"No check matches {' '.join(args.only)}; see --list.", file=sys.stderr)
        return EXIT_UNAVAILABLE
    win.be_dpi_aware()
    try:
        ezcd = Ezcd.find()
    except Unavailable as unavailable:
        print(unavailable, file=sys.stderr)
        return EXIT_UNAVAILABLE
    try:
        context = Context(ezcd)
        results = run_checks(context, chosen)
    except KeyboardInterrupt:
        print("Interrupted; the windows the checker opened are closed.", file=sys.stderr)
        return EXIT_UNAVAILABLE
    finally:
        ezcd.close()
    code = EXIT_FAILED if any(r.status == Status.FAILED for r in results) else EXIT_PASSED
    print(report.as_json(context, results, code) if args.json else report.text(context, results))
    return code


if __name__ == "__main__":
    sys.exit(main())
