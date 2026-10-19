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

## NVDA updates

Every `YYYY.1` release raises `BACK_COMPAT_TO`: NVDA 2027.1 will refuse to load
the add-on until `lastTestedNVDAVersion` is raised to 2027.1 after testing.
