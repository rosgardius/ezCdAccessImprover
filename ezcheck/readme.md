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
- `--write-baseline`: run only the audit and keep what it finds as the baseline of this version of ezcd,
  in `ezcheck/baselines/<version>.json`.

ezcd running as administrator can only be checked by a checker running as administrator too.

A full run takes some 15 seconds. It shows each tab of the main window, opens the windows that only show
something (the buttons ending in » or ..., Settings and its pages, Filename preview, Encoder
information) and closes them as their close box does, so that nothing in them is kept; at the end the
tab shown at the start is shown again, also after Ctrl+C. Do not use ezcd meanwhile. It opens menus too:
while ezcd is in the foreground they would open on the screen, so the checker asks you to switch away
and waits up to 30 seconds. It never chooses anything that converts, rips, burns or saves.

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

## The audit

Besides the facts the add-on relies on, the checks `audit.*` look in every tab and dialog for what a
screen reader does not get from ezcd by itself: windows in the Tab order without an MSAA name, controls
without windows that take clicks (speed buttons, labels and images with a handler), and toolbars,
sliders and buttons that Tab does not reach. What is found is compared with the baseline of the nearest
version of ezcd (the newest not newer than the one checked): a new finding fails the check, a finding of
the baseline no longer there is a note. An element is named by its form (or the tab of the main window)
and the classes of the windows down to it with their indexes, so the names hold in every language.

Some findings depend on the settings shown, such as the fields of the effect chosen in DSP: on another
computer they may differ from the baseline without any change in ezcd.
