# Development

*[Deutsche Fassung](../i18n/docs/development.de.md)*

```bash
pip install -e ".[dev]"
git config core.hooksPath .githooks
./scripts/check.sh
```

## The suite

| Suite | What it proves |
|-------|----------------|
| `tests/test_data.py` | Migrations, page kinds and addresses, nesting depth, URL rules, role checks. No network. |
| `tests/test_browser.py` | What the user actually sees: headless Chrome over the DevTools protocol. Starts its own server. Skipped (not failed) when Chrome or `websockets` is missing. |
| `tests/test_repo.py` | Hygiene: required files, version consistency, no artefacts, no secrets, **no personal names**. |
| `tests/test_doku_schnellpfad.py` | The documentation fast path: which files count as documentation, that the workflow is actually wired to that verdict, and that it falls back to the full suite whenever the verdict is unclear. |

`tests/run_all.py` finds every `test_*.py` automatically — a new suite needs no registration.

## The documentation fast path

A change that touches **only** documentation does not need the browser test, the dependency
install or the image build. The CI leaves those out and runs the hygiene suite instead:

```bash
./scripts/check.sh --nur-hygiene      # ~0.3 s instead of ~40 s
```

`scripts/_nur_doku.sh` decides. It lists which files count as documentation and gives a reason
for every boundary — `*.md` anywhere, `docs/`, `i18n/`, `backlog/`, `LICENSE`; everything else,
including `pyproject.toml`, `.gitignore` and the workflows themselves, means the full suite.

Two things are deliberate:

* **Hygiene never gets skipped.** A service subdomain, a home directory path or a customer name
  in a README is the same violation as one in code. Documentation may take the short route
  *because* the hygiene suite comes along, not because documentation is harmless.
* **When in doubt, the full suite runs.** An empty diff, a missing base commit, a shallow clone,
  a force push or a manual `workflow_dispatch` all resolve to "not only documentation".

The decision sits on **step** conditions inside the existing jobs, never on `paths-ignore`. A
workflow suppressed by a path filter never creates its checks at all — they stay `Pending` and
block the pull request forever. GitHub says so itself: *"Associated checks stay in a 'Pending'
state and block merging … Avoid requiring workflows that can be skipped."*

## Repeatability is a hard rule

Every suite creates its own temporary data directory, starts what it needs, and removes it.
`./scripts/check.sh` twice must be green twice. A test that depends on leftovers from the previous
run is broken, even if it passes the first time.

The browser test runs the application through `tests/_fakeauth.py`, which replaces the OIDC session
with a fixed administrator. That file never ships: it lives under `tests/`, not in the image.

## No private infrastructure

`tests/test_repo.py` scans every tracked file for private hostnames, service subdomains, RFC 1918
addresses and container numbers, and it restricts example URLs to `example.com` and friends.

Two details make the guard work in a **public** repository:

- The patterns are **generic**. A literal blocklist (`my-server`, `customer-x`) would publish
  exactly what it protects.
- The handful of names that cannot be expressed generically are stored as the first 16 hex digits
  of their SHA256. The guard recognises a name without revealing it.

Values reserved for documentation stay allowed — `example.*` (RFC 2606) and the ranges from
RFC 5737. Otherwise the rule could not even be explained without breaking it.

Write examples with placeholders (`service.<domain>`, `10.x.x.x`, `CT <nnn>`) rather than with
real-looking values; that needs no exception at all.

## Architecture in three sentences

`app/main.py` holds the whole server: data access, validation, routes, and a small API for the edit
mode. `links.json` is the single source of truth and is written atomically. The browser gets three
scripts: `ui.js` (collapsing, menus, toasts) for everyone, `frames.js` for tab pages, and
`admin.js` (edit mode, settings drawer) only for administrators.
