# Contributing

Thanks for helping. This extension runs as root inside Harness Maxxing and talks to a production Dokploy, so the bar
is: small, tested, and nothing that weakens the safety rules below.

## Before you code

- **Bug**: open an issue with the bug form (Harness and Dokploy versions, what happened, steps).
- **Feature or bigger change**: open an issue with the feature form first and wait for a maintainer's go. A pull
  request with no agreed issue may be closed.
- **Security problem**: never in an issue; see [SECURITY.md](SECURITY.md).

## Rules

- **Standard library only** (Python 3.11+): no dependency in `api.py`, `dokploy_core.py` or `dokploy.py`. `page.js`
  is a plain ES module, no build step, using Harness's `ui-*` classes.
- **Writes ask first**: every Dokploy write goes through a confirmation on the page and `--yes` in the CLI, and is
  refused on a protected service. Never print, log or return the API key, nor anything from `docker inspect` but the
  routing labels.
- **One destination**: calls go only to the Dokploy address the user checked; no telemetry, no redirect followed.
- **Backward compatible**: a user on an older version must keep working after `git pull` (the extension updates
  itself). Keep the `"api": 1` contract of Harness page extensions.
- **English** for code, comments, docs and commits; UI texts in English **and** French (`page.js`).
- **Tests for every change**, against the fake Dokploy in `tests/conftest.py`; a bug fix comes with a test that fails
  without it. Tests never touch a real Dokploy, `/root` or `/var/lib`.

## Workflow

1. Fork, then branch from `main`: `fix/<short-name>` or `features/<short-name>`.
2. Commit messages start with `fix:` or `feat:`.
3. Run the checks (CI runs the same):

   ```bash
   uv run --no-project --with ruff ruff check . && uv run --no-project --with ruff ruff format --check .
   uv run --no-project --with pytest pytest -q
   cp page.js /tmp/page.mjs && node --check /tmp/page.mjs   # .js hides ESM syntax errors
   ```

4. For a user-visible change: a `CHANGELOG.md` entry and the version bumped in `manifest.json` and `pyproject.toml`
   (semver: `fix` → patch, `feat` → minor); update `README.md` and `skill/dokploy/SKILL.md` when behavior changes.
5. Open the pull request against `main` with the template filled in. It is squash-merged once CI passes and a
   maintainer approves.

## Testing on a real Dokploy

Use a throwaway server or VM, never production. Copy your files into its `extensions/dokploy` folder (Harness reloads
them by itself) and say in the pull request which Dokploy version you checked.
