# Pages, tabs and the limits of embedding

*[Deutsche Fassung](pages.de.md)*

Pages live in `links.json`, not in code. An administrator creates them under
**Settings (gear) → Pages**.

## The three kinds

### Link tree (`links`)

Containers, groups, entries. Entries may nest **three levels deep** below the top one; the server
refuses more (`MAX_LINK_DEPTH`) and the editor does not even offer a deeper drop — when you drag
a branch, its own height counts.

An entry without an address is allowed: it renders as a label, not a link. Addresses without a
scheme get `https://` prepended; foreign schemes (`javascript:`, `data:`) are rejected.

### Tabs (`frames`)

The bookmark bar becomes a tab bar and the content loads in an `iframe`. There is no content to
edit on such a page, so no content pencil appears — only the tabs themselves are editable.

Per page you choose which tab loads on arrival (*start tab*). The open tab is remembered in the
URL fragment (`#r=1`), so a reload keeps it.

### Built-in (`builtin`)

A view shipped with the application: `news` and `status` (both are mock-ups, see `app/mockups.py`).
They cannot be edited or deleted, only reordered. Adding one means writing a template and one
entry in `BUILTIN_VIEWS`.

The start page (empty slug) and the built-in pages are **locked**: only their order can change.

## Roles

Any page, container, group entry or bookmark may carry `role`. Only members of that OIDC group
see it. A page someone may not see answers `404`, so its existence is not disclosed.

## Reserved addresses

`api`, `auth`, `static`, `icons`, `bg`, `healthz` — those paths belong to the application. The
generic page route is registered **last**, otherwise it would swallow them.

## Why your service probably will not embed

Measured on a typical self-hosted stack:

| Service | Header | Embeddable |
|---------|--------|------------|
| Identity provider (Pocket ID) | `X-Frame-Options: SAMEORIGIN` + `frame-ancestors 'none'` | no |
| Nextcloud, Paperless, Rocket.Chat, Vaultwarden | `X-Frame-Options: SAMEORIGIN` | no |
| AFFiNE, Immich | none | yes |

`X-Frame-Options: SAMEORIGIN` means: only pages on the service's own domain may frame it. Your
dashboard is a different domain, so the frame stays blank. This is a defence against clickjacking,
and it cannot be removed from the outside — stripping the header in a proxy would only disable the
protection for your users.

**What actually works:**

- **Public share links.** Many tools (wikis, boards, photo albums) can publish a page without a
  login. Those usually embed fine.
- **Your own applications**, where you control the headers.
- **A new tab.** Every tab bar has a button for it, and DashMyBoard warns you at creation time:
  `GET /api/embeddable?url=…` reads the target's headers and tells you what will happen.

Even when a service *allows* framing, a page that requires a login may still show the login
screen: browsers increasingly block third-party cookies, and the session cookie of the embedded
site is exactly that. Public share links avoid the problem entirely.
