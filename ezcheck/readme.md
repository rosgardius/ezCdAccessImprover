# ezcheck: checking a version of EZ CD Audio Converter

The add-on relies on facts about EZ CD Audio Converter (ezcd) that a new version of it may change: string
numbers of its language files, images of toolbar buttons, offsets in its memory, sizes of controls. They
are kept in `addon/appModules/ezcd/facts/`, one set for each version of ezcd that changed any of them.
`ezcheck` tells which of those facts do not hold in the ezcd running on this computer. It needs neither
NVDA nor the add-on installed, and changes nothing in ezcd.

## Running it

Start ezcd with its main window and no dialog open, then from the repository root:

```sh
uv run python -m ezcheck
```

- `--list`: the checks, with what each one checks.
- `--only ID ...`: only these checks; a group name such as `strings` takes all of its checks.
- `--json`: the report as JSON.

ezcd running as administrator can only be checked by a checker running as administrator too.

## The report

The header names the version of ezcd, its path, the set of facts used for it, the language ezcd shows,
the DPI of its main window and its theme. Then each check is:

- `PASSED`: every fact it checks holds;
- `FAILED`: some do not. Each line names the field of the set of facts, what it holds, what ezcd has,
  and the section of `docs/ezcd-ui.md` about it;
- `SKIPPED`: it cannot run here, for the reason given (no disc drive, a hidden panel, ...).

Notes under a check tell what does not fail it, such as strings missing from a translation of ezcd.

Exit codes: 0 every fact holds, 1 some do not, 2 ezcd could not be checked (not running, a dialog
open, no access to its memory).
