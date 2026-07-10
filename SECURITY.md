# Security Policy

*[Deutsche Fassung](SECURITY.de.md)*

## Reporting a vulnerability

Please report privately through GitHub's
[private vulnerability reporting](https://github.com/Ollornog/DashMyBoard/security/advisories/new)
rather than opening a public issue. Expect a first reply within a week.

## Scope and design decisions worth knowing

- **Authentication is delegated** to [TinySesam](https://github.com/Ollornog/TinySesam) and your
  OIDC provider. DashMyBoard stores no passwords.
- **A local TinySesam administrator inherits no roles** (`admin_implies_roles=False`), and the
  first-admin token is disabled (`admin_claim_ttl_min=0`). `REQUIRED_CONFIG` makes the app refuse
  to start if a TinySesam version does not know these switches — a silent downgrade would weaken
  authorisation without any visible sign.
- **Write endpoints require the admin role and a CSRF token.** On upload routes the guard runs as
  a FastAPI dependency, otherwise an unauthenticated caller would get `422` (body validation)
  instead of `401`.
- **`X-Forwarded-For` is only trusted from `TRUSTED_PROXIES`.** Do not start uvicorn with
  `--proxy-headers`; TinySesam evaluates the header itself, and only for those peers.
- **Pages a role may not see return `404`**, not `403` — their existence is not disclosed.
- **`GET /api/embeddable` fetches an arbitrary URL** on behalf of an administrator. It is
  restricted to administrators for that reason. Treat it as an authenticated, deliberate
  server-side request, and keep the admin role small.
- **SVG uploads are rejected if they contain `<script>`.** Uploaded files are served from a
  dedicated static mount, never rendered inline.

## Not in scope

Denial of service through an administrator uploading very large images, and anything an
administrator can do by design (they can point a link anywhere, including at internal hosts).
