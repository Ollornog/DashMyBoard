# Contributing

*[Deutsche Fassung](CONTRIBUTING.de.md)*

Thanks for taking the time. This project is small on purpose; a change that keeps it small is
usually the better change.

## Ground rules

1. **Tests belong to the change, not to the cleanup.** If you change behaviour, change a test in
   the same commit. Documentation and `CHANGELOG.md` move with it too.
2. **The suite must be repeatable.** Every suite creates its own fresh data directory, starts the
   services it needs, and removes them. Run `./scripts/check.sh` twice — both runs green. A test
   that fails on the second run is broken, not the code.
3. **No personal names in the repository.** No private hostnames, no company domains, no customer
   names — not in code, sample data, tests, docs or commit messages. Use `example.com` and
   configure real values through environment variables. `tests/test_repo.py` enforces this.
4. **Configuration comes from the environment.** `BASE_URL` and `OIDC_ISSUER` have no defaults on
   purpose: a dashboard that silently starts with someone else's URL is worse than one that
   refuses to start.

## Workflow

Work on a feature branch. CI does not run there — `ci-local` (or `./scripts/check.sh`) is your
safety net. Open a pull request; CI runs on the PR and on `main`.

```bash
git switch -c my-change
pip install -e ".[dev]"
git config core.hooksPath .githooks    # once per clone
# ... edit, then:
./scripts/check.sh
git commit -am "Describe the change, not the diff"
git push -u origin my-change
```

## Style

- Comments explain **why**, never what the next line does. If a line needs a comment to be read,
  rewrite the line.
- German is the language of the user interface; code identifiers are English.
- Files are UTF-8 without BOM. Umlauts are written as umlauts.
- No new dependency without a reason that fits in one sentence.

## Reporting bugs

Include what you expected, what happened, and the smallest `links.json` that reproduces it.
Screenshots help for layout issues; the browser console helps for everything else.
