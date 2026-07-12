<p align="center"><img src="docs/logo.png" alt="DashMyBoard" width="250" height="250"></p>

<h1 align="center">DashMyBoard</h1>

<p align="center"><b>English</b> · <a href="i18n/README.de.md">Deutsch</a></p>

<p align="right">
<a href="https://github.com/Ollornog/DashMyBoard/actions/workflows/ci.yml"><img src="https://github.com/Ollornog/DashMyBoard/actions/workflows/ci.yml/badge.svg" alt="tests"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-informational.svg" alt="License: MIT"></a>
<img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python">
</p>

> 🚧 **Work in progress** — under active development; interfaces and structure may still change before a stable `1.0` release.

### A self-hosted dashboard behind your single sign-on.

It gives a team one place to find its services: a grouped link tree, a bookmark bar, and pages
that embed other tools — all editable **in place**, without a separate admin panel.

Built with FastAPI, Jinja2 and [TinySesam](https://github.com/Ollornog/TinySesam) for OIDC.
No database server, no build step: content lives in a single `links.json` inside a volume.

---

## What it does

**Pages are data, not code.** An administrator creates them in the browser. Three kinds:

| Kind | What it is | Editable content |
|------|------------|------------------|
| **Link tree** | Containers, groups and entries — the classic start page | yes |
| **Tabs** | The bookmark bar becomes a tab bar; the content loads in an `iframe` | the tabs only |
| **Built-in** | A view shipped with the app (`news`, `status`) | no |

**Everything else is edited where you see it.** A pencil turns on edit mode: type into titles,
drag entries between groups and containers, nest them up to three levels deep, drop bookmarks
into folders. Structural changes are saved atomically and the page rebuilds; plain text changes
save without a reload.

**Roles come from your identity provider.** A group named `admin` (configurable) becomes the
role that may edit. Containers, bookmarks and whole pages can be restricted to a role — a page
someone may not see returns `404`, not `403`.

**Looks are configurable, not hard-coded.** Three themes (light, ambient, dark), a per-page
background slideshow, and per-theme colour and opacity for every surface: title bar, tab bar,
containers, and the mask over the background image.

## Screenshots

The interface ships in German. Screenshots live in [`docs/`](docs/).

## Requirements

- An OIDC provider (any: Keycloak, Authentik, Pocket ID, Authelia, …)
- A reverse proxy terminating TLS
- Docker, or Python 3.10+

## Quick start

```bash
git clone https://github.com/Ollornog/DashMyBoard.git
cd DashMyBoard
cp .env.example .env      # set BASE_URL, OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET
docker compose -f compose.example.yml up -d --build
```

Point your reverse proxy at `127.0.0.1:8000` and register the redirect URI in your provider:

```
https://dashboard.example.com/auth/oidc/callback
```

That path is fixed by TinySesam. A different one fails **after** the login, which is a
confusing place to discover a typo.

Then put your administrator into the OIDC group named in `ADMIN_ROLE` (default `admin`),
sign in, and the pencil appears.

Full configuration: [`docs/configuration.md`](docs/configuration.md).
Page kinds and the limits of embedding: [`docs/pages.md`](docs/pages.md).

## A warning about embedding

Most self-hosted services **refuse to be embedded**. They send `X-Frame-Options: SAMEORIGIN`
or `Content-Security-Policy: frame-ancestors 'none'`, and a tab pointing at them stays blank.
This is a security feature, not a bug, and it cannot be worked around honestly.

DashMyBoard therefore asks the target before you commit: `GET /api/embeddable?url=…` reads the
headers and the dialog warns you. Every tab also offers **open in a new tab** as the honest
fallback. Prefer **public share links** where a tool offers them — an embedded page that needs
a login will show you a login, because browsers increasingly block third-party cookies.

## Updating

Nothing updates itself. The version decides who installs.

| You run | Pin | Update | Rollback |
|---------|-----|--------|----------|
| Container | `image: ghcr.io/ollornog/dashmyboard:v0.3.0` | raise the tag, `docker compose pull && up -d` | put the old tag back |
| Immutable | `…@sha256:…` (digest, printed by the release workflow) | new digest | old digest |

Watch the [releases feed](https://github.com/Ollornog/DashMyBoard/releases) to learn about new
versions. There is no `latest` tag on purpose: a moving tag turns every restart into a lottery.

## Development

```bash
pip install -e ".[dev]"
./scripts/check.sh          # unit + browser + hygiene tests
./scripts/check.sh --fast   # skip the browser test
git config core.hooksPath .githooks
```

The suite starts its own server on a fresh data directory and is **repeatable**: running it
twice must be green twice. See [`docs/development.md`](docs/development.md) and
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Security

Report vulnerabilities privately — see [`SECURITY.md`](SECURITY.md).

## Licence

[MIT](LICENSE)

## Credits

Icon: <a href="https://www.flaticon.com/authors/iconjam" target="_blank" rel="noopener">Egg PNG Image by Iconjam - flaticon.com</a>
