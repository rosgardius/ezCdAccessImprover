# Development

## Overview

The `ezCdAccessImprover` NVDA add-on is an app module for EZ CD Audio Converter
(`ezcd.exe`). It is built with [nvda-addon-kit](https://github.com/addonfactory/NVDAAddonKit)
(`nvaddon`) from `addon.toml`.

- Supported NVDA versions: `minimumNVDAVersion = 2026.1`, `lastTestedNVDAVersion = 2026.2`
  (64-bit NVDA on Python 3.13 only).
- Tested with EZ CD Audio Converter 13.2.1.1.

## Layout

| Path | Contents |
|---|---|
| `addon.toml` | Add-on metadata and build settings; `addon/manifest.ini` is generated from it |
| `addon/appModules/ezcd/` | The app module: the package name is the executable name without `.exe` |
| `readme.md` | User documentation, rendered to `addon/doc/en/readme.html` |
| `changelog.md` | Change history, used as the GitHub release description |
| `docs/` | Development documentation (this file and notes on the application's UI) |
| `.github/` | CI: ruff, `nvaddon check`, build; on a tag, a release and add-on store submission |

Generated files (`addon/manifest.ini`, `addon/doc/`, `*.nvda-addon`, `*.pot`, `*.mo`)
are git-ignored and must not be edited by hand.

## Commands

```sh
uv sync                        # development environment
uv run ruff format addon       # formatting
uv run ruff check addon        # linting
uv run nvaddon check           # validate addon.toml against add-on store rules
uv run nvaddon build           # build ezCdAccessImprover-<version>.nvda-addon
uv run nvaddon install --link  # link addon/ into the installed NVDA (once)
```

After the first `install --link`, NVDA has to be restarted; after that, app module
changes are picked up with NVDA+Ctrl+F3. Log: `%TEMP%\nvda.log`.

## Code style

PEP 8, 4-space indentation, snake_case; names dictated by NVDA (`AppModule`,
`script_`, `event_`, `_get_*`) stay as they are.

The add-on's own names and words for ezcd's controls are said in the language ezcd shows, not in
NVDA's: they are `OwnString("key")` in the code and `key = text` lines in
`addon/appModules/ezcd/strings/english.txt`, with a `#` note for translators above each. A
translation is a file named as ezcd's language file (`Language\russian.uni` → `russian.txt`); a missing
file or key falls back to English. Only what belongs to NVDA's own UI (descriptions of commands and
their category in Input Gestures) goes through `_()` with a `# Translators:` comment.

## Code rules

The app module is a few thousand lines. These rules keep it from growing copies of itself.

- **One home for each helper.** Before writing a helper, look for it in its home:
  - `windows.py`: the window tree and window rectangles;
  - `screen.py`: what ezcd draws without windows (display model texts, logical coordinates, repaint);
  - `remote.py`: messages to ezcd and buffers in its memory;
  - `vcl.py`: VCL objects in ezcd's memory, such as controls without windows;
  - `captions.py`: captions found by position;
  - `panels.py`: panels of the main window, recognised by the windows they hold;
  - `language.py`: ezcd's strings and the add-on's own strings in the language ezcd shows (also in one
    window), and the choice of that language; `facts/language.py`: reading their files;
  - `facts/`: what depends on the version of ezcd (see [Versions of ezcd](#versions-of-ezcd));
    `version.py`: the set of facts chosen for the running ezcd;
  - `commands.py`: the category of the add-on's commands in Input Gestures.

  A second copy of a helper, even a one-line one such as `parent(hwnd)`, is a defect. A helper
  that a second module needs moves to its home, not into an import from an unrelated module.
- **A module is one concept**: one part of ezcd's UI or one mechanism. Split a module when it holds
  two concepts, not because of its length.
- **Window classes are string literals** where they are compared (`== "TPanel"`). A named constant
  only for a group with a meaning (`captions.CLASSES`) or for a class whose name does not say what the
  window is (`COVER_CLASS = "TDropPanel"`); never two names for one class.
- **NVDA's Win32 bindings first**: constants and functions from `winUser`, `winBindings` and
  `windowUtils`. Own constants and `ctypes.WinDLL` declarations only for what they lack.
- **ezcd's memory through an NVDAObject's `processHandle`.** The app module's own `processHandle` has
  no access to the memory of the process: a buffer made with it fails (`remote.buffer` raises `OSError`).
- **Errors are handled where the resource is.** A function that reads ezcd's memory or waits for ezcd
  catches `OSError` or the timeout itself, logs with `log.debugWarning` and returns an empty result;
  its callers do not repeat the `try`.
- **Fixed properties of overlay classes are class attributes** (`role = controlTypes.Role.TOOLBAR`,
  `keyboardShortcut = "F8"`), not `_get_` methods. A value that is expensive to compute and does not
  change while the object lives is a `functools.cached_property`.
- **No thin wrappers**: no function that only joins, renames or forwards another one's result, no
  parameter or return value that no caller uses.
- **Reading what ezcd drew**: what is missing in the display model is read again after a repaint
  through `captions.from_screen` or `screen.redraw`, not by a retry written anew.
- `chooseNVDAObjectOverlayClasses` stays one chain by window class. A kind of object with several
  classes chooses among them itself, as `ToolbarStop.overlay_class` does.

## Versions of ezcd

What the add-on relies on and a version of ezcd may change is a field of `facts.Facts`, not a constant of a
module: offsets in VCL objects, images of toolbar buttons, numbers of strings in the language files, sizes
in design units, where ezcd keeps its language setting. A string is its number and its text in
`english.uni` (`facts.groups.String`), which says what the number means.

- `facts.VERSIONS` holds one set for each version of ezcd that changed a fact, from the oldest to the
  newest. A new set is `dataclasses.replace` of the one before it, with `since` set to the version and only
  what changed. A version of ezcd that changed nothing gets no set: it only raises `facts.LAST_TESTED`.
- The oldest supported version is the `since` of the first set; raising it removes the older sets.
- Modules read the chosen set, `version.facts`, and never compare versions: a difference in behaviour is a
  named field of the set. Only `facts.select` compares them.
- A version newer than `LAST_TESTED`, or one that cannot be read, gets the last set; one older than the
  first set, the first. Either is one `log.info` line; the user is not told.
- Window classes stay string literals in the code; one moves into the set only when a version of ezcd
  changes it.
- `facts/` imports only the standard library and itself, so that it loads without NVDA. The reading of
  VCL objects through a function given (`facts.objects`) lives there with the offsets it uses.

## Comments

- A comment says what the code cannot: behaviour of ezcd, VCL, Windows or NVDA that the code relies on,
  a reason, a unit. Not what the next line does, not the history of a change.
- A docstring says what a function returns or what an object is, the empty case included ("0 if
  none"). A name that says all of it needs no docstring.
- Comments and docstrings are checked in the same change as their code: one that no longer matches is
  a bug. Facts about ezcd's UI that several places rely on go to [ezcd-ui.md](ezcd-ui.md).

## NVDA updates

Every `YYYY.1` release raises `BACK_COMPAT_TO`: NVDA 2027.1 will refuse to load
the add-on until `lastTestedNVDAVersion` is raised to 2027.1 after testing.
