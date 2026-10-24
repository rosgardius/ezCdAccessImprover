# ezCdAccessImprover

NVDA add-on that improves accessibility of EZ CD Audio Converter (`ezcd.exe`).
App module in `addon/appModules/ezcd/`, built with nvda-addon-kit (`addon.toml`).

- NVDA: 2026.1 – 2026.2. Check every API used against the NVDA source of these versions
  (tags `release-2026.1`, `release-2026.2` of nvaccess/nvda).
- Development docs live in `docs/` (start with `docs/development.md`); keep them there, not here.
- Before writing or reviewing code, read "Code rules" and "Comments" in `docs/development.md`: look for
  an existing helper in its home module first, and remove what a change leaves unused.
- Keep this file short. Personal, machine-specific instructions go to `CLAUDE.local.md` (git-ignored).
- Before handing over code: `uv run ruff format addon ezcheck`, `uv run ruff check addon ezcheck`,
  `uv run python -m unittest discover -s ezcheck/tests -t .`, `uv run nvaddon check`, `uv run nvaddon build`.

## Writing

- Everything public (docs, committed files, code comments, commits, add-on metadata) is in English.
- Commits: imperative subject ≤72 chars, blank line, optional body of 2–3 lines. Short and to the point.
- Code comments: only what can't be read from the code itself.
- Docs: clear and to the point.
- Committed files describe only what is in the repository or anyone can set up themselves;
  nothing about local state (git-ignored files, paths and setup of a particular machine).
