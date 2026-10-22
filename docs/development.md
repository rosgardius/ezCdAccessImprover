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
`script_`, `event_`, `_get_*`) stay as they are. User-visible strings go through
`_()` with a `# Translators:` comment.

## Code rules

The app module is a few thousand lines. These rules keep it from growing copies of itself.

- **One home for each helper.** Before writing a helper, look for it in its home:
  - `windows.py`: the window tree and window rectangles;
  - `screen.py`: what ezcd draws without windows (display model texts, logical coordinates, repaint);
  - `remote.py`: messages to ezcd and buffers in its memory;
  - `captions.py`: captions found by position;
  - `panels.py`: panels of the main window, recognised by the windows they hold;
  - `language.py`: ezcd's strings.

  A second copy of a helper, even a one-line one such as `parent(hwnd)`, is a defect. A helper
  that a second module needs moves to its home, not into an import from an unrelated module.
- **A module is one concept**: one part of ezcd's UI or one mechanism. Split a module when it holds
  two concepts, not because of its length.
- **Window classes are string literals** where they are compared (`== "TPanel"`). A named constant
  only for a group with a meaning (`captions.CLASSES`) or for a class whose name does not say what the
  window is (`COVER_CLASS = "TDropPanel"`); never two names for one class.
- **NVDA's Win32 bindings first**: constants and functions from `winUser`, `winBindings` and
  `windowUtils`. Own constants and `ctypes.WinDLL` declarations only for what they lack.
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
