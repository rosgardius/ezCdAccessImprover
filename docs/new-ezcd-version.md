# Checking a new version of EZ CD Audio Converter

The add-on works with the versions of ezcd from the `since` of the first set of facts to
`facts.LAST_TESTED` (see [Versions of ezcd](development.md#versions-of-ezcd)). A newer version gets the
last set, which may no longer hold. To check one:

1. Install it, start it with its main window and no dialog open, and switch away from it.
2. Run the checker from the repository root: `uv run python -m ezcheck` (see
   [ezcheck/readme.md](../ezcheck/readme.md)). It shows each tab and opens and closes the dialogs that
   only show something; do not use ezcd meanwhile.
3. Each `FAILED` line names a field of the set of facts, what it holds, what the new version has, and
   the section of [ezcd-ui.md](ezcd-ui.md) about it.
   - A fact that changed: add a set to `facts.VERSIONS`, `dataclasses.replace` of the last one with
     `since` set to the new version and only the changed fields; correct `ezcd-ui.md`.
   - A difference in behaviour, not in a value: a named field of the set that the module reads; modules
     never compare versions.
   - A check that is wrong for the new version, not the add-on: correct the check.
4. Run the checker again until nothing fails. A `SKIPPED` check did not run (no disc drive, a panel
   hidden by the settings shown, ...): show what it needs and run it with `--only` if the fact matters.
5. The audit (`audit.*`) compares what a screen reader does not get by itself with the baseline of the
   nearest version: new findings are new controls or windows to look at with NVDA. Once they are
   understood, keep them as the baseline of the new version: `uv run python -m ezcheck --write-baseline`.
6. What the checker cannot see, check with NVDA: the order of events, where focus goes, and what NVDA
   says on Tab and Shift+Tab through the three tabs and the dialogs, as the readme describes it. Compare
   with the last tested version where in doubt.
7. Raise `facts.LAST_TESTED` and "Tested with" in [development.md](development.md) to the new version.
   A version that changed nothing gets no set of its own.

When the oldest supported version is raised, remove the sets older than it, set the readme's "EZ CD
Audio Converter compatibility", and remove the baselines of versions no longer supported.
