# Configuration

*[Deutsche Fassung](configuration.de.md)*

Everything is set through environment variables. `BASE_URL` and `OIDC_ISSUER` have **no default**:
a dashboard that silently starts with a stranger's URL is worse than one that refuses to start.

| Variable | Required | Meaning |
|----------|----------|---------|
| `BASE_URL` | yes | Public address, e.g. `https://dashboard.example.com`. Used for the OIDC redirect and the passkey relying-party id. |
| `OIDC_ISSUER` | yes | Your provider, e.g. `https://id.example.com`. |
| `OIDC_CLIENT_ID` | yes | Client id registered with the provider. |
| `OIDC_CLIENT_SECRET` | yes | Client secret. Keep it out of the image; use `.env` or a secret mount. |
| `OIDC_NAME` | no | Name shown on the sign-in card. Default `Single Sign-On`. |
| `ADMIN_ROLE` | no | The OIDC **group** that becomes the editing role. Default `admin`. |
| `DATA_DIR` | no | Content, logos, backgrounds. Default `/data`. |
| `DB_PATH` | no | Sessions and users (SQLite). Default `/data/tinysesam.db`. |
| `HTTPS_MODE` | no | `warn` behind a TLS proxy, `require` when serving HTTPS directly. |
| `TRUSTED_PROXIES` | no | Comma-separated CIDRs whose `X-Forwarded-For` is believed. Default covers localhost and the Docker bridge. |

## The provider

Register exactly this redirect URI:

```
https://dashboard.example.com/auth/oidc/callback
```

TinySesam fixes that path. A wrong one fails **after** the login, which is a confusing place to
discover a typo.

Ask for the scopes `openid profile email groups`. The `groups` claim is what turns your
`ADMIN_ROLE` group into the editing role. Without it nobody can edit.

## Reverse proxy

The application speaks plain HTTP on port 8000 and expects TLS in front of it. Do **not** run
uvicorn with `--proxy-headers`: TinySesam reads `X-Forwarded-For` itself, but only from
`TRUSTED_PROXIES`. With `--proxy-headers` the client IP becomes forgeable.

Example (Caddy):

```
dashboard.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

## Data

Everything the administrator edits lands in `$DATA_DIR/links.json`, written atomically
(write next to it, then rename). For that reason **do not bind-mount the file itself** — mount
the directory. Logos live in `$DATA_DIR/icons`, backgrounds in `$DATA_DIR/backgrounds`.

On first start the directory is seeded from the image and never overwritten afterwards. Older
files are migrated in place on start.

## Backup

`links.json`, `icons/`, `backgrounds/` and `tinysesam.db` — that is the whole state. The database
holds sessions and users; losing it logs everyone out, nothing more.
