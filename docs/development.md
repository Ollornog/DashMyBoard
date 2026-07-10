# Development

*[Deutsche Fassung](development.de.md)*

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

`tests/run_all.py` finds every `test_*.py` automatically — a new suite needs no registration.

## Repeatability is a hard rule

Every suite creates its own temporary data directory, starts what it needs, and removes it.
`./scripts/check.sh` twice must be green twice. A test that depends on leftovers from the previous
run is broken, even if it passes the first time.

The browser test runs the application through `tests/_fakeauth.py`, which replaces the OIDC session
with a fixed administrator. That file never ships: it lives under `tests/`, not in the image.

## No personal names

`tests/test_repo.py` greps every tracked file for private hostnames, company domains and customer
names, and it restricts example URLs to `example.com` and friends. This is not politeness — it is
what keeps a public repository from leaking an internal topology.

## Architecture in three sentences

`app/main.py` holds the whole server: data access, validation, routes, and a small API for the edit
mode. `links.json` is the single source of truth and is written atomically. The browser gets three
scripts: `ui.js` (collapsing, menus, toasts) for everyone, `frames.js` for tab pages, and
`admin.js` (edit mode, settings drawer) only for administrators.
