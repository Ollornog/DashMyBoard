"""DashMyBoard — ein Dashboard hinter Single Sign-On (TinySesam/OIDC).

Ein Aufruf von "/" ohne Sitzung leitet direkt zum Identitätsanbieter weiter — kein Klick
nötig. Nur nach dem Abmelden (?abgemeldet=1) erscheint die Landing-Karte, sonst liefe man
sofort wieder in den Login und "Abmelden" bliebe wirkungslos.

Sektionen, Lesezeichen und Seiten mit "role" sehen nur Nutzer mit der passenden Rolle
(OIDC-Gruppe → TinySesam-Rolle). Inhalte, Logos und Hintergrundbilder liegen unter /data
(Volume), damit der Bearbeiten-Modus sie schreiben kann; beim ersten Start werden sie aus
dem Image geseedet.

Seiten legt der Administrator in der Oberfläche an (links.json). Eine neue *eingebaute*
Ansicht braucht ein Template und einen Eintrag in BUILTIN_VIEWS.

Konfiguration ausschließlich über Umgebungsvariablen — siehe .env.example.
"""
from __future__ import annotations

import dataclasses
import json
import os
import re
import secrets
import shutil
from html.parser import HTMLParser
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import (HTMLResponse, JSONResponse, PlainTextResponse,
                               RedirectResponse, Response)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from tinysesam import TinySesam, TinySesamConfig

from mockups import NEWS_ITEMS, STATUS_DATA

HERE = Path(__file__).parent
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
LINKS_PATH = DATA_DIR / "links.json"
ICONS_DIR = DATA_DIR / "icons"
BG_DIR = DATA_DIR / "backgrounds"

BASE_URL = os.environ["BASE_URL"].rstrip("/")
OIDC_ISSUER = os.environ["OIDC_ISSUER"].rstrip("/")   # für Profil-/Admin-Links zum Anbieter
OIDC_NAME = os.environ.get("OIDC_NAME", "Single Sign-On")
HOSTNAME = BASE_URL.split("://", 1)[-1].split("/")[0]

# Wer darf bearbeiten? Die OIDC-Gruppe dieses Namens wird zur gleichnamigen Rolle.
ADMIN_ROLE = os.environ.get("ADMIN_ROLE", "admin")

# Logo der Anwendung (Datei ohne Endung unter /data/icons).
DEFAULT_LOGO = "logo"

# Seiten stehen in links.json und werden im Bearbeiten-Modus angelegt (kein Code nötig).
# Drei Arten:
#   links   — Container/Gruppen/Einträge (die klassische Startseite)
#   frames  — die Lesezeichenleiste wird zur Reiterleiste, der Inhalt liegt in einem iframe
#   builtin — von der Anwendung mitgebracht (news, status); nicht löschbar, kein Inhalts-CRUD
#   folder  — keine Seite, sondern ein Auswahlmenü in der Navigation; enthält Seiten
PAGE_TYPES = ("links", "frames", "builtin", "folder")

# Eingebaute Ansichten: view-Name → (Template, Kontext)
BUILTIN_VIEWS = {
    "news": ("news.html", lambda: {"items": NEWS_ITEMS}),
    "status": ("status.html", lambda: dict(STATUS_DATA)),
}

# Pfade, die schon der Anwendung gehören — als Seiten-Adresse verboten.
RESERVED_SLUGS = {"api", "auth", "static", "icons", "bg", "healthz"}
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")

MAX_LINKS_BYTES = 256 * 1024
MAX_ICON_BYTES = 512 * 1024
MAX_BG_BYTES = 8 * 1024 * 1024
ICON_SUFFIXES = {".svg", ".png", ".webp"}
BG_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

THEMES = ("hell", "ambient", "dunkel")

# Einträge dürfen dreimal verschachtelt werden: Eintrag → Unter → Unter → Unter.
# Der Bearbeiten-Modus kennt die Zahl auch (GO_MAX_DEPTH) und bietet tiefere Ablagen
# gar nicht erst an — sonst käme die Absage erst vom Server.
MAX_LINK_DEPTH = 4

# Einstellbare Flächen je Design: Farbe + Deckkraft (0…1).
#   veil  = Maske über dem Hintergrundbild   card = Container
#   bar   = Titelleiste                      marks = Lesezeichenleiste
LAYERS = ("veil", "card", "bar", "marks")
_PAPER, _CARD = "#f6f1ec", "#fbf8f4"
_DARK_BG, _DARK_CARD = "#1a1922", "#221f2c"

THEME_DEFAULTS = {
    "hell": {
        "veil": {"color": _PAPER, "alpha": 0.72},
        "card": {"color": _CARD, "alpha": 1.0},
        "bar": {"color": _CARD, "alpha": 1.0},
        "marks": {"color": _CARD, "alpha": 0.72},
    },
    "ambient": {
        "veil": {"color": _PAPER, "alpha": 0.64},
        "card": {"color": _CARD, "alpha": 1.0},
        "bar": {"color": _CARD, "alpha": 1.0},
        "marks": {"color": _CARD, "alpha": 0.72},
    },
    "dunkel": {
        "veil": {"color": _DARK_BG, "alpha": 0.76},
        "card": {"color": _DARK_CARD, "alpha": 0.62},
        "bar": {"color": _DARK_CARD, "alpha": 0.62},
        "marks": {"color": _DARK_CARD, "alpha": 0.45},
    },
}

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

# Größen (px), unabhängig vom Design. Grenzen = was der Regler zulässt.
LAYOUT_DEFAULTS = {
    "bar": {"height": 64, "title": 22, "link": 14, "logo": 42},
    "marks": {"height": 40, "icon": 19, "text": 13},
    "content": {"title": 19, "name": 15, "desc": 12, "logo": 26},
}

LAYOUT_RANGE = {
    "bar": {"height": (40, 140), "title": (12, 48), "link": (10, 24), "logo": (16, 96)},
    "marks": {"height": (28, 90), "icon": (12, 40), "text": (9, 22)},
    "content": {"title": (12, 40), "name": (10, 28), "desc": (8, 20), "logo": (14, 56)},
}


SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def normalize_url(url: str) -> str | None:
    """'wiki.example.com' → 'https://wiki.example.com'. Fremde Schemata
    (javascript:, data:, …) werden verworfen — sie haben in einem Link nichts zu suchen."""
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith(("http://", "https://")):
        return u
    if SCHEME.match(u):
        return None
    return "https://" + u


def hex_to_rgb(value: str) -> str:
    """'#f6f1ec' → '246, 241, 236' (für rgba() in CSS-Variablen)."""
    v = value.lstrip("#")
    return ", ".join(str(int(v[i:i + 2], 16)) for i in (0, 2, 4))


def seed_data() -> None:
    """Erstbefüllung des Volumes aus dem Image (idempotent, überschreibt nie)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    default = json.loads((HERE / "links.default.json").read_text(encoding="utf-8"))

    if not LINKS_PATH.exists():
        shutil.copy(HERE / "links.default.json", LINKS_PATH)
    else:
        # Ältere Fassungen kennen "pages" noch nicht — sonst stünde die Seite ohne
        # Hintergrundbild da. Fehlende Schlüssel aus der Vorlage nachziehen.
        data = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        changed = False
        for key in ("site", "pages"):
            if key not in data:
                data[key] = default[key]
                changed = True

        # Lesezeichen lagen früher global, jetzt hängen sie an je einer Seite.
        if "bookmarks" in data and isinstance(data.get("pages"), dict):
            data["pages"].setdefault("", {})["bookmarks"] = data.pop("bookmarks")
            changed = True

        # Seiten waren ein Wörterbuch slug→Einstellungen und ihre Titel standen im Code;
        # jetzt sind sie eine geordnete Liste mit Titel und Art. Die Container (sections)
        # lagen global und gehören der Startseite — andere Seiten haben eigene.
        if isinstance(data.get("pages"), dict):
            titles = {"": "Start", "news": "News", "status": "Status"}
            order = [s for s in ("", "news", "status") if s in data["pages"]]
            order += [s for s in data["pages"] if s not in order]
            pages = []
            for slug in order:
                cfg = data["pages"][slug] or {}
                page = {"slug": slug, "title": titles.get(slug, slug.capitalize() or "Start")}
                page["type"] = "links" if slug == "" else "builtin"
                if slug in BUILTIN_VIEWS:
                    page["view"] = slug
                if slug == "status":
                    page["role"] = ADMIN_ROLE
                page.update(cfg)
                if slug == "":
                    page["sections"] = data.pop("sections", [])
                pages.append(page)
            data["pages"] = pages
            data.pop("sections", None)
            changed = True

        def alle_seiten(items):
            """Ordner sind Menüpunkte, keine Seiten — ihre Kinder aber schon."""
            for item in items:
                if item.get("type") == "folder":
                    yield from alle_seiten(item.get("children") or [])
                else:
                    yield item

        # Früher war "veil" nur eine Zahl je Design; jetzt hat jede Fläche Farbe + Deckkraft.
        for cfg in alle_seiten(data["pages"]):
            if isinstance(cfg.get("veil"), dict):
                theme = cfg.setdefault("theme", {})
                for name, alpha in cfg.pop("veil").items():
                    if name in THEMES and isinstance(alpha, (int, float)):
                        theme.setdefault(name, {})["veil"] = {
                            "color": THEME_DEFAULTS[name]["veil"]["color"], "alpha": float(alpha)
                        }
                changed = True

        # Größen (Titelleiste, Lesezeichen, Inhalt) lagen je Seite; jetzt gelten sie überall.
        # Die erste Seite, die welche hat, gibt sie vor — die übrigen werden verworfen.
        for cfg in alle_seiten(data["pages"]):
            layout = cfg.pop("layout", None)
            if layout:
                data.setdefault("site", {}).setdefault("layout", layout)
                changed = True

        # Adressen ohne Schema (Altbestand) ergänzen, sonst scheitert später jedes Speichern
        # an der Prüfung — auch das Ändern von Design oder Hintergrund.
        def fix_urls(items):
            nonlocal changed
            for item in items:
                if "children" in item:
                    fix_urls(item["children"])
                if not item.get("url"):
                    continue
                fixed = normalize_url(item["url"])
                if fixed != item["url"]:
                    if fixed:
                        item["url"] = fixed
                    else:
                        item.pop("url")   # unbrauchbares Schema: Eintrag bleibt als Beschriftung
                    changed = True

        for cfg in alle_seiten(data["pages"]):
            for sec in cfg.get("sections") or []:
                for grp in sec.get("groups") or []:
                    fix_urls(grp.get("links") or [])
            fix_urls(cfg.get("bookmarks") or [])

        if changed:
            LINKS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for target, source in ((ICONS_DIR, HERE / "icons_seed"), (BG_DIR, HERE / "bg_seed")):
        target.mkdir(parents=True, exist_ok=True)
        for src in source.glob("*"):
            dst = target / src.name
            if src.is_file() and not dst.exists():
                shutil.copy(src, dst)


seed_data()

# Ohne diese Schalter wäre die Rechteprüfung schwächer, als sie aussieht:
# admin_implies_roles=True ließe jeden lokalen TinySesam-Admin als "hoheit" durchgehen,
# und ein Erst-Admin-Token im Log wäre ein Weg dorthin. Fehlen sie, brechen wir ab,
# statt sie stillschweigend zu ignorieren.
REQUIRED_CONFIG = ("admin_implies_roles", "admin_claim_ttl_min")


def _config(**kwargs) -> TinySesamConfig:
    """Unkritische Felder, die die installierte TinySesam-Fassung nicht kennt, weglassen —
    sicherheitsrelevante dagegen einfordern (siehe REQUIRED_CONFIG)."""
    known = {f.name for f in dataclasses.fields(TinySesamConfig)}
    missing = [name for name in REQUIRED_CONFIG if name not in known]
    if missing:
        raise RuntimeError(
            "Diese TinySesam-Fassung kennt " + ", ".join(missing) + " nicht — mindestens v0.11.0 nötig."
        )
    for name in set(kwargs) - known:
        del kwargs[name]
    return TinySesamConfig(**kwargs)


auth = TinySesam(_config(
    db_path=os.environ.get("DB_PATH", "/data/tinysesam.db"),
    lang="de",
    base_url=BASE_URL,
    origin=BASE_URL,
    rp_id=HOSTNAME,
    # Einzige Anmeldemethode ist PocketID — alles andere bleibt aus.
    password_enabled=False,
    passkey_enabled=False,
    pin_enabled=False,
    apikey_enabled=False,
    totp_enabled=False,
    magiclink_enabled=False,
    admin_enabled=False,
    account_enabled=False,
    allow_signup=False,
    # Kein Einmal-Token für /auth/claim-admin ins Log schreiben: hier gibt es keinen
    # lokalen Admin, Rechte hängen ausschließlich an der PocketID-Gruppe.
    admin_claim_ttl_min=0,
    # Ein TinySesam-Admin soll NICHT automatisch jede Rolle erfüllen (seit v0.11.0).
    # Zusätzlich prüft has_role() unten selbst — das trägt auch mit älteren Fassungen.
    admin_implies_roles=False,
    oidc_enabled=True,
    oidc_name=OIDC_NAME,
    oidc_issuer=OIDC_ISSUER,
    oidc_client_id=os.environ["OIDC_CLIENT_ID"],
    oidc_client_secret=os.environ["OIDC_CLIENT_SECRET"],
    oidc_scopes="openid profile email groups",
    oidc_group_role_map={ADMIN_ROLE: ADMIN_ROLE},
    available_roles=[ADMIN_ROLE],
    login_path="/",
    login_redirect="/",
    logout_redirect="/?abgemeldet=1",
    https_mode=os.environ.get("HTTPS_MODE", "warn"),   # TLS terminiert der Reverse-Proxy davor
    # Nur diesen Gegenstellen wird X-Forwarded-For geglaubt. Der Standard deckt
    # localhost und das Docker-Bridge-Netz ab; alles andere wäre fälschbar.
    trusted_proxies=[p.strip() for p in os.environ.get(
        "TRUSTED_PROXIES", "127.0.0.1/32,::1/128,172.16.0.0/12").split(",") if p.strip()],
))

app = FastAPI(title="DashMyBoard", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(auth.router())
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
app.mount("/icons", StaticFiles(directory=ICONS_DIR), name="icons")
app.mount("/bg", StaticFiles(directory=BG_DIR), name="bg")
templates = Jinja2Templates(directory=str(HERE / "templates"))


# ---------------------------------------------------------------- Daten

def load_links() -> dict:
    return json.loads(LINKS_PATH.read_text(encoding="utf-8"))


def save_links(data: dict) -> None:
    """Atomar: erst daneben schreiben, dann umbenennen (gleiches Verzeichnis!)."""
    tmp = LINKS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(LINKS_PATH)


def icon_url(name: str | None) -> str | None:
    if not name:
        return None
    for suffix in (".svg", ".png", ".webp"):
        if (ICONS_DIR / f"{name}{suffix}").exists():
            return f"/icons/{name}{suffix}"
    return None


_COLOR_HEX = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
_COLOR_WORD = re.compile(r'(?:fill|stroke)\s*=\s*"([a-zA-Z]+)"')
_NEUTRAL_WORDS = {"none", "black", "white", "currentcolor", "transparent", "inherit"}
_mono_cache: dict[str, bool] = {}


def _is_monochrome(name: str, url: str) -> bool:
    """Ist das Logo ohnehin schwarz/weiß? Dann darf der Dunkel-Modus es umkehren,
    ohne dass Markenfarben verloren gehen (Pocket ID, AFFiNE, Vaultwarden …).
    Nur SVG lässt sich hier lesen; alles andere gilt als farbig."""
    if name in _mono_cache:
        return _mono_cache[name]

    result = False
    if url.endswith(".svg"):
        try:
            text = (ICONS_DIR / Path(url).name).read_text(encoding="utf-8", errors="ignore")
            greys = all(len(set(h if len(h) == 3 else (h[0:2], h[2:4], h[4:6]))) == 1
                        for h in _COLOR_HEX.findall(text))
            words = all(w.lower() in _NEUTRAL_WORDS for w in _COLOR_WORD.findall(text))
            result = greys and words
        except OSError:
            result = False

    _mono_cache[name] = result
    return result


def icon_variants(name: str | None) -> dict | None:
    """Farbiges Logo + optional eine helle und eine dunkle Fassung.

    Gibt es eigene Fassungen, werden sie je Theme eingeblendet. Fehlen sie, färbt das
    CSS das farbige Logo per Filter um ("auto"). Das trägt allerdings nur bei Logos
    ohne gefüllte Hintergrundfläche — sonst wird z.B. Nextclouds blaues Quadrat zu
    einem weißen Klotz. Darum haben die mitgelieferten Logos eigene Fassungen.

    "gray" = das Logo ist ohnehin einfarbig; dann kehrt der Dunkel-Modus es auch dann
    um, wenn die Logos sonst farbig bleiben sollen — sonst versänke es im Hintergrund.
    """
    color = icon_url(name)
    if not color:
        return None
    gray = _is_monochrome(name, color)
    light, dark = icon_url(f"{name}-light"), icon_url(f"{name}-dark")
    if not light and not dark:
        return {"mode": "auto", "color": color, "gray": gray}
    return {"mode": "set", "color": color, "light": light or color, "dark": dark or color, "gray": gray}


templates.env.globals["icon_variants"] = icon_variants


def pages_of(data: dict) -> list[dict]:
    return data.get("pages") or []


def walk_pages(pages: list[dict]):
    """Alle echten Seiten — Ordner sind nur Menüpunkte und werden übersprungen."""
    for page in pages:
        if page.get("type") == "folder":
            yield from walk_pages(page.get("children") or [])
        else:
            yield page


def find_page(data: dict, slug: str) -> dict | None:
    for page in walk_pages(pages_of(data)):
        if page.get("slug") == slug:
            return page
    return None


def page_config(data: dict, cfg: dict | None) -> dict:
    """Hintergrundbilder und Flächenfarben gehören der Seite, die Größen der ganzen
    Anwendung (site.layout) — sonst sprängen Titelleiste und Lesezeichen beim Blättern."""
    cfg = cfg or {}
    saved = cfg.get("theme") or {}

    theme = {}
    for name, layers in THEME_DEFAULTS.items():
        own = saved.get(name) or {}
        theme[name] = {
            layer: {**layers[layer], **(own.get(layer) or {})} for layer in LAYERS
        }

    own_layout = (data.get("site") or {}).get("layout") or {}
    layout = {group: {**sizes, **(own_layout.get(group) or {})}
              for group, sizes in LAYOUT_DEFAULTS.items()}

    files = [f for f in (cfg.get("backgrounds") or []) if (BG_DIR / f).exists()]
    return {
        "backgrounds": [f"/bg/{f}" for f in files],
        "theme": theme,
        "layout": layout,
        "css": {name: {layer: {"rgb": hex_to_rgb(v["color"]), "a": v["alpha"]}
                       for layer, v in layers.items()}
                for name, layers in theme.items()},
        "interval": int(cfg.get("interval") or 12),
    }


def page_bookmarks(page: dict | None) -> list[dict]:
    """Jede Seite hat ihre eigene Lesezeichenleiste — bei Reiter-Seiten ist sie die
    Reiterleiste, und ein Klick lädt den Inhalt in den Rahmen statt in einen neuen Tab."""
    return (page or {}).get("bookmarks") or []


def has_role(user: dict, role: str) -> bool:
    """Rolle aus der PocketID-Gruppe. `admin_implies=False` schließt aus, dass ein
    lokaler TinySesam-Admin jede Rolle miterfüllt (Config sagt dasselbe, doppelt hält)."""
    return auth.has_role(user, role, admin_implies=False)


def visible(items: list[dict], user: dict) -> list[dict]:
    """Einträge ohne "role" sehen alle, sonst entscheidet die TinySesam-Rolle.
    Ordner werden rekursiv gefiltert und fallen weg, wenn nichts übrig bleibt."""
    out = []
    for item in items:
        if item.get("role") and not has_role(user, item["role"]):
            continue
        if "children" in item:
            kids = visible(item["children"], user)
            if not kids:
                continue
            item = {**item, "children": kids}
        out.append(item)
    return out


def is_admin(user: dict) -> bool:
    return has_role(user, ADMIN_ROLE)


def nav_pages(data: dict, user: dict) -> list[dict]:
    """Der Navigationsbaum: Seiten und Ordner, gefiltert nach Rolle.

    Ein Ordner, dessen Seiten alle verborgen sind, verschwindet mit ihnen — sonst
    stünde ein leeres Menü in der Leiste.
    """
    def sichtbar(items):
        out = []
        for p in items:
            if p.get("role") and not has_role(user, p["role"]):
                continue
            if p.get("type") == "folder":
                kinder = sichtbar(p.get("children") or [])
                # Ein leerer Ordner ist erst im Bearbeiten-Modus nützlich (man zieht Seiten hinein).
                if not kinder and not is_admin(user):
                    continue
                out.append({"title": p.get("title") or "Ordner", "folder": True, "children": kinder})
            else:
                out.append({"slug": p.get("slug"), "title": p.get("title") or p.get("slug") or "",
                            "folder": False})
        return out

    return sichtbar(pages_of(data))


def flat_pages(data: dict, user: dict) -> list[dict]:
    """Flache Liste für Auswahlfelder („Transparenz kopieren von Seite …").

    Seiten ohne Adresse gehören nicht dazu: sie sind Beschriftungen, keine Ziele.
    """
    return [{"slug": p["slug"], "title": p.get("title") or p["slug"]}
            for p in walk_pages(pages_of(data))
            if p.get("slug") is not None and (not p.get("role") or has_role(user, p["role"]))]


def shell(request: Request, user: dict, page: dict, data: dict) -> dict:
    """Kontext, den jede Seite braucht: Kopfzeile, Navigation, Hintergrund, Rolle."""
    site = data.get("site") or {}
    admin = is_admin(user)
    marks = page_bookmarks(page)
    bookmarks = marks if admin else visible(marks, user)
    frames = page.get("type") == "frames"
    return {
        "site_title": site.get("title", "DashMyBoard"),
        "site_subtitle": site.get("subtitle", "Intranet"),
        "site_logo": icon_url(site.get("logo") or DEFAULT_LOGO) or f"/icons/{DEFAULT_LOGO}.svg",
        "display_name": user["display_name"] or user["username"],
        "admin": admin,
        "pages": nav_pages(data, user),
        "flat_pages": flat_pages(data, user),
        "active": page["slug"],
        "page_type": page.get("type", "links"),
        "bookmarks": bookmarks,
        # Bei Reiter-Seiten öffnen die Lesezeichen den Inhalt im Rahmen; "start" sagt,
        # welcher Reiter beim Aufruf schon geladen ist.
        "frames": frames,
        "start_mark": page.get("start", "") if frames else "",
        "page_cfg": page_config(data, page),
        "oidc_issuer": OIDC_ISSUER,
        "theme_defaults": THEME_DEFAULTS,
        "layout_defaults": LAYOUT_DEFAULTS,
        "layout_range": LAYOUT_RANGE,
        "max_depth": MAX_LINK_DEPTH,
    }


def with_csrf(resp, admin: bool):
    if admin:
        # Double-Submit-Token für die Schreib-Routen (JS liest das Cookie).
        token = secrets.token_urlsafe(24)
        resp.set_cookie(auth.cfg.csrf_cookie, token, secure=auth.cfg.cookie_secure,
                        samesite=auth.cfg.cookie_samesite, path="/")
    return resp


# ---------------------------------------------------------------- Guards

def require_admin(request: Request) -> dict:
    user = auth.require_user(request)
    if not is_admin(user):
        raise HTTPException(403, "Nur für Administratoren")
    return user


def require_csrf(request: Request) -> None:
    auth.require_csrf(request, request.headers.get("X-CSRF-Token"))


def validate_links(data) -> dict:
    """Struktur prüfen und behutsam glätten — die Datei steuert, was gerendert wird.

    Adressen ohne Schema bekommen `https://` vorangestellt (Komfort); fremde Schemata
    (`javascript:` …) sind ein Fehler. Das Objekt wird dabei verändert und genau so
    gespeichert, egal ob die Änderung aus der Oberfläche oder von einem Skript kam.
    """
    if not isinstance(data, dict):
        raise HTTPException(400, "Objekt erwartet")

    # PUT ersetzt die ganze Datei. Ein Teil-Dokument würde den Rest löschen
    # (etwa alle Seiten samt Lesezeichen) — deshalb müssen alle Bereiche mitkommen.
    for key, kind in (("site", dict), ("pages", list)):
        if not isinstance(data.get(key), kind):
            raise HTTPException(400, f"'{key}' fehlt oder hat den falschen Typ")

    def texts(entry, *keys):
        for k in keys:
            if k in entry and entry[k] is not None and not isinstance(entry[k], str):
                raise HTTPException(400, f"'{k}' muss Text sein")

    def flags(entry, *keys):
        for k in keys:
            if k in entry and not isinstance(entry[k], bool):
                raise HTTPException(400, f"'{k}' muss wahr/falsch sein")

    def check_layout(own):
        if not isinstance(own, dict):
            raise HTTPException(400, "'layout' muss ein Objekt sein")
        for group, sizes in own.items():
            if group not in LAYOUT_RANGE or not isinstance(sizes, dict):
                raise HTTPException(400, f"Unbekannter Bereich '{group}'")
            for key, value in sizes.items():
                if key not in LAYOUT_RANGE[group]:
                    raise HTTPException(400, f"Unbekannte Größe '{key}'")
                low, high = LAYOUT_RANGE[group][key]
                if not isinstance(value, int) or not low <= value <= high:
                    raise HTTPException(400, f"'{key}' muss zwischen {low} und {high} liegen")

    site = data.get("site") or {}
    if not isinstance(site, dict):
        raise HTTPException(400, "'site' muss ein Objekt sein")
    texts(site, "title", "subtitle", "logo")
    if site.get("logo") and not icon_url(site["logo"]):
        raise HTTPException(400, "Unbekanntes Seiten-Logo")
    if not site.get("title"):
        raise HTTPException(400, "Die Seite braucht einen Titel")
    check_layout(site.get("layout") or {})

    def check_bookmarks(items, depth=0):
        if depth > 4:
            raise HTTPException(400, "Lesezeichen zu tief verschachtelt")
        for bm in items:
            if not isinstance(bm, dict) or not bm.get("name"):
                raise HTTPException(400, "Lesezeichen braucht einen Namen")
            texts(bm, "name", "url", "icon", "role")
            if "children" in bm:
                if not isinstance(bm["children"], list):
                    raise HTTPException(400, "Ordnerinhalt muss eine Liste sein")
                flags(bm, "collapsed")
                check_bookmarks(bm["children"], depth + 1)
            elif not bm.get("url"):
                # Ohne Adresse bleibt das Lesezeichen stehen, ist aber kein Link.
                bm.pop("url", None)
            else:
                fixed = normalize_url(bm["url"])
                if fixed is None:
                    raise HTTPException(400, f"Adresse von '{bm['name']}' ist nicht erlaubt — nur http:// und https://")
                bm["url"] = fixed

    def check_links(items, depth=1):
        if depth > MAX_LINK_DEPTH:
            raise HTTPException(400, "Einträge zu tief verschachtelt")
        for link in items:
            # Die Adresse darf fehlen — dann ist der Eintrag nur eine Beschriftung.
            if not isinstance(link, dict) or not link.get("name"):
                raise HTTPException(400, "Eintrag braucht einen Namen")
            texts(link, "name", "url", "desc", "icon", "badge")
            if link.get("url"):
                # Fehlt das Schema, ergänzen wir es — nur fremde Schemata sind ein Fehler.
                fixed = normalize_url(link["url"])
                if fixed is None:
                    raise HTTPException(400, f"Adresse von '{link['name']}' ist nicht erlaubt — nur http:// und https://")
                link["url"] = fixed
            flags(link, "collapsed", "vpn")
            if "children" in link:
                if not isinstance(link["children"], list):
                    raise HTTPException(400, "Untereinträge müssen eine Liste sein")
                check_links(link["children"], depth + 1)

    def check_sections(sections):
        if not isinstance(sections, list):
            raise HTTPException(400, "'sections' muss eine Liste sein")
        for sec in sections:
            if not isinstance(sec, dict) or not sec.get("title"):
                raise HTTPException(400, "Sektion braucht einen Titel")
            texts(sec, "title", "subtitle", "role", "accent", "id")
            flags(sec, "collapsed")
            for grp in sec.get("groups") or []:
                if not isinstance(grp, dict):
                    raise HTTPException(400, "Gruppe muss ein Objekt sein")
                texts(grp, "label")
                flags(grp, "collapsed")
                check_links(grp.get("links") or [])

    pages = data["pages"]
    if not pages:
        raise HTTPException(400, "Es muss mindestens eine Seite geben")

    seen: set[str] = set()

    def check_page(page, in_folder=False):
        if not isinstance(page, dict):
            raise HTTPException(400, "Seite muss ein Objekt sein")
        texts(page, "slug", "title", "role", "view", "start")
        if not page.get("title"):
            raise HTTPException(400, "Seite braucht einen Titel")

        kind = page.get("type", "links")
        if kind not in PAGE_TYPES:
            raise HTTPException(400, f"Unbekannte Seitenart '{kind}'")

        # Ein Ordner ist keine Seite: kein Slug, kein Inhalt, keine Ordner in Ordnern.
        if kind == "folder":
            if in_folder:
                raise HTTPException(400, "Ordner dürfen keine Ordner enthalten")
            kinder = page.get("children")
            if not isinstance(kinder, list):
                raise HTTPException(400, "Ordnerinhalt muss eine Liste sein")
            for feld in ("slug", "sections", "bookmarks", "backgrounds", "theme", "view", "start"):
                page.pop(feld, None)
            for kind_page in kinder:
                check_page(kind_page, in_folder=True)
            return

        page.pop("children", None)

        # Fehlender Schlüssel = keine Adresse (die Seite ist dann eine Beschriftung und
        # nicht aufrufbar). Leerer Schlüssel = die Startseite. Das ist der Unterschied.
        slug = page.get("slug")
        if slug is not None and not isinstance(slug, str):
            raise HTTPException(400, "Adresse der Seite muss Text sein")

        if slug is None:
            if kind == "builtin":
                raise HTTPException(400, "Eine eingebaute Seite braucht eine Adresse")
        else:
            if slug and (not SLUG.match(slug) or slug in RESERVED_SLUGS):
                raise HTTPException(400, f"Ungültige Seiten-Adresse '{slug}' — Kleinbuchstaben, Ziffern, Bindestrich")
            if not slug and in_folder:
                raise HTTPException(400, "Die Startseite gehört nicht in einen Ordner")
            if slug in seen:
                raise HTTPException(400, f"Die Seiten-Adresse '{slug}' gibt es doppelt")
            seen.add(slug)

        if kind == "builtin":
            if page.get("view") not in BUILTIN_VIEWS:
                raise HTTPException(400, "Eingebaute Seite braucht eine bekannte Ansicht")
            page.pop("sections", None)
        elif kind == "frames":
            page.pop("sections", None)
        else:
            check_sections(page.get("sections") or [])

        check_bookmarks(page.get("bookmarks") or [])
        for name in page.get("backgrounds") or []:
            if not isinstance(name, str) or "/" in name or not (BG_DIR / name).exists():
                raise HTTPException(400, f"Unbekanntes Hintergrundbild '{name}'")

        for theme, layers in (page.get("theme") or {}).items():
            if theme not in THEMES or not isinstance(layers, dict):
                raise HTTPException(400, f"Unbekanntes Design '{theme}'")
            for layer, v in layers.items():
                if layer not in LAYERS or not isinstance(v, dict):
                    raise HTTPException(400, f"Unbekannte Fläche '{layer}'")
                if not HEX_COLOR.match(str(v.get("color", ""))):
                    raise HTTPException(400, "Farbe muss #rrggbb sein")
                alpha = v.get("alpha")
                if not isinstance(alpha, (int, float)) or not 0 <= alpha <= 1:
                    raise HTTPException(400, "Deckkraft muss zwischen 0 und 1 liegen")

        # Größen galten früher je Seite; jetzt stehen sie in site.layout.
        page.pop("layout", None)

    for page in pages:
        check_page(page)

    if "" not in seen:
        raise HTTPException(400, "Die Startseite (leere Adresse) darf nicht entfernt werden")
    if "bookmarks" in data or "sections" in data:
        raise HTTPException(400, "Lesezeichen und Container gehören zu einer Seite")
    return data


# ---------------------------------------------------------------- Seiten

@app.get("/healthz", response_class=PlainTextResponse)
def healthz() -> str:
    return "ok"


def render_page(request: Request, user: dict, page: dict, data: dict):
    """Eine Seite ausliefern — welche Vorlage, entscheidet ihre Art."""
    admin = is_admin(user)
    ctx = shell(request, user, page, data)
    kind = page.get("type", "links")

    if kind == "builtin":
        template, context = BUILTIN_VIEWS[page["view"]]
        ctx.update(context())
    elif kind == "frames":
        template = "frames.html"
    else:
        template = "home.html"
        # Admins sehen alles — so entsprechen die Render-Indizes denen in links.json,
        # auf die der Bearbeiten-Modus seine Änderungen abbildet.
        sections = page.get("sections") or []
        ctx["sections"] = sections if admin else visible(sections, user)

    return with_csrf(templates.TemplateResponse(request, template, ctx), admin)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, abgemeldet: int = 0):
    user = auth.current_user(request)
    data = load_links()

    if not user:
        if not abgemeldet:
            return RedirectResponse("/auth/oidc/start", 303)
        site = data.get("site") or {}
        return templates.TemplateResponse(request, "landing.html", {
            "site_title": site.get("title", "DashMyBoard"),
            "site_logo": icon_url(site.get("logo") or DEFAULT_LOGO) or f"/icons/{DEFAULT_LOGO}.svg",
            "abgemeldet": True,
            "page_cfg": page_config(data, find_page(data, "")),
        })

    page = find_page(data, "")
    if not page:
        raise HTTPException(500, "Die Startseite fehlt in links.json")
    return render_page(request, user, page, data)


# ---------------------------------------------------------------- Admin-API

@app.get("/api/links")
def api_links_get(request: Request):
    require_admin(request)
    return JSONResponse(load_links())


@app.put("/api/links")
async def api_links_put(request: Request):
    require_admin(request)
    require_csrf(request)
    raw = await request.body()
    if len(raw) > MAX_LINKS_BYTES:
        raise HTTPException(413, "Zu groß")
    try:
        data = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "Kein gültiges JSON")
    save_links(validate_links(data))
    return {"ok": True}


@app.get("/api/icons")
def api_icons_get(request: Request):
    require_admin(request)
    # -light/-dark sind Fassungen eines Logos, keine eigenen Einträge in der Galerie.
    names = sorted({p.stem for p in ICONS_DIR.iterdir()
                    if p.is_file() and p.suffix.lower() in ICON_SUFFIXES
                    and not p.stem.endswith(("-light", "-dark"))})
    return {"icons": [{"name": n, "url": icon_url(n)} for n in names]}


def _store_upload(blob: bytes, filename: str, folder: Path, suffixes: set[str]) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in suffixes:
        raise HTTPException(400, "Dateityp nicht erlaubt")
    name = Path(filename).stem.lower().replace(" ", "-")
    if not SAFE_NAME.match(name):
        raise HTTPException(400, "Ungültiger Dateiname")
    if suffix == ".svg" and b"<script" in blob.lower():
        raise HTTPException(400, "SVG mit Skript wird abgelehnt")
    (folder / f"{name}{suffix}").write_bytes(blob)
    return f"{name}{suffix}"


@app.post("/api/icons", dependencies=[Depends(require_admin)])
async def api_icons_post(request: Request, file: UploadFile = File(...)):
    # require_admin läuft als Dependency — sonst würde FastAPI erst den Datei-Body
    # validieren und Unangemeldeten 422 statt 401 antworten.
    require_csrf(request)
    blob = await file.read(MAX_ICON_BYTES + 1)
    if len(blob) > MAX_ICON_BYTES:
        raise HTTPException(413, "Logo zu groß (max. 512 KB)")
    stored = _store_upload(blob, file.filename or "", ICONS_DIR, ICON_SUFFIXES)
    name = Path(stored).stem
    return {"ok": True, "name": name, "url": icon_url(name)}


@app.delete("/api/icons/{name}")
def api_icons_delete(request: Request, name: str):
    require_admin(request)
    require_csrf(request)
    if not SAFE_NAME.match(name):
        raise HTTPException(400, "Ungültiger Name")
    removed = False
    for stem in (name, f"{name}-light", f"{name}-dark"):  # Fassungen mit entfernen
        for suffix in ICON_SUFFIXES:
            p = ICONS_DIR / f"{stem}{suffix}"
            if p.exists():
                p.unlink()
                removed = True
    if not removed:
        raise HTTPException(404, "Nicht gefunden")
    return {"ok": True}


@app.get("/api/bookmarks/export")
def api_bookmarks_export(request: Request, page: str = ""):
    """Netscape-Bookmark-Datei — dasselbe Format, das Browser exportieren."""
    require_admin(request)
    data = load_links()
    target = find_page(data, page)
    if not target:
        raise HTTPException(404, "Unbekannte Seite")

    def esc(text: str) -> str:
        return (text.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace('"', "&quot;"))

    def render(items: list[dict], depth: int) -> list[str]:
        pad = "    " * depth
        out = [f"{pad}<DL><p>"]
        for item in items:
            if "children" in item:
                out.append(f'{pad}    <DT><H3>{esc(item["name"])}</H3>')
                out.extend(render(item["children"], depth + 1))
            elif item.get("url"):
                out.append(f'{pad}    <DT><A HREF="{esc(item["url"])}">{esc(item["name"])}</A>')
        out.append(f"{pad}</DL><p>")
        return out

    body = "\n".join([
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>",
        "<H1>Bookmarks</H1>",
        *render(page_bookmarks(target), 0),
        "",
    ])
    name = f"lesezeichen-{page or 'start'}.html"
    return Response(body, media_type="text/html; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


class _BookmarkParser(HTMLParser):
    """Liest Netscape-Bookmark-HTML in unseren Baum. Ordner = H3, Einträge = A."""

    def __init__(self) -> None:
        super().__init__()
        self.root: list[dict] = []
        self.stack: list[list[dict]] = [self.root]
        self._href: str | None = None
        self._folder = False
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "dl":
            # Der zuletzt angelegte Ordner nimmt ab jetzt die Kinder auf.
            pending = getattr(self, "_pending", None)
            self.stack.append(pending["children"] if pending else self.stack[-1])
            self._pending = None
        elif tag == "h3":
            self._folder, self._text = True, []
        elif tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "dl" and len(self.stack) > 1:
            self.stack.pop()
        elif tag == "h3" and self._folder:
            folder = {"name": "".join(self._text).strip() or "Ordner", "children": []}
            self.stack[-1].append(folder)
            self._pending = folder
            self._folder = False
        elif tag == "a" and self._href:
            name = "".join(self._text).strip()
            if name and self._href.startswith(("http://", "https://")):
                self.stack[-1].append({"name": name, "url": self._href})
            self._href = None

    def handle_data(self, data):
        if self._folder or self._href:
            self._text.append(data)


@app.post("/api/bookmarks/import", dependencies=[Depends(require_admin)])
async def api_bookmarks_import(request: Request, page: str = "", mode: str = "replace",
                               file: UploadFile = File(...)):
    require_csrf(request)
    raw = await file.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(413, "Datei zu groß (max. 2 MB)")

    parser = _BookmarkParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    imported = parser.root
    if not imported:
        raise HTTPException(400, "Keine Lesezeichen gefunden")

    data = load_links()
    cfg = find_page(data, page)
    if not cfg:
        raise HTTPException(404, "Unbekannte Seite")
    cfg["bookmarks"] = imported if mode == "replace" else (cfg.get("bookmarks") or []) + imported
    save_links(validate_links(data))
    return {"ok": True, "count": len(imported)}


@app.get("/api/backgrounds")
def api_bg_get(request: Request):
    require_admin(request)
    names = sorted(p.name for p in BG_DIR.iterdir()
                   if p.is_file() and p.suffix.lower() in BG_SUFFIXES)
    return {"backgrounds": [{"name": n, "url": f"/bg/{n}"} for n in names]}


@app.post("/api/backgrounds", dependencies=[Depends(require_admin)])
async def api_bg_post(request: Request, file: UploadFile = File(...)):
    require_csrf(request)
    blob = await file.read(MAX_BG_BYTES + 1)
    if len(blob) > MAX_BG_BYTES:
        raise HTTPException(413, "Bild zu groß (max. 8 MB)")
    stored = _store_upload(blob, file.filename or "", BG_DIR, BG_SUFFIXES)
    return {"ok": True, "name": stored, "url": f"/bg/{stored}"}


@app.delete("/api/backgrounds/{name}")
def api_bg_delete(request: Request, name: str):
    require_admin(request)
    require_csrf(request)
    p = BG_DIR / name
    if "/" in name or ".." in name or not p.exists():
        raise HTTPException(404, "Nicht gefunden")
    p.unlink()

    # Auch aus allen Seiten-Konfigurationen entfernen, sonst zeigt links.json ins Leere.
    data = load_links()
    for cfg in walk_pages(pages_of(data)):
        if name in (cfg.get("backgrounds") or []):
            cfg["backgrounds"] = [b for b in cfg["backgrounds"] if b != name]
    save_links(data)
    return {"ok": True}


# ---------------------------------------------------------------- Reiter-Seiten

@app.get("/api/embeddable")
async def api_embeddable(request: Request, url: str):
    """Lässt sich diese Adresse in einen Rahmen einbetten?

    Viele Dienste verbieten es (X-Frame-Options, CSP frame-ancestors) — der Rahmen bliebe
    dann einfach weiß. Wir fragen einmal nach, damit der Dialog warnen kann, statt den
    Nutzer später vor eine leere Fläche zu setzen. Nur für Administratoren."""
    require_admin(request)
    target = normalize_url(url)
    if not target:
        raise HTTPException(400, "Adresse nicht erlaubt")

    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, verify=True) as client:
            resp = await client.get(target, headers={"User-Agent": "go-landing/1.0"})
    except Exception:
        # Nicht erreichbar heißt nicht "verboten" — der Rahmen kann trotzdem klappen.
        return {"embeddable": None, "reason": "Adresse war nicht erreichbar"}

    xfo = (resp.headers.get("x-frame-options") or "").strip().lower()
    csp = (resp.headers.get("content-security-policy") or "").lower()
    ancestors = ""
    for part in csp.split(";"):
        if part.strip().startswith("frame-ancestors"):
            ancestors = part.strip()

    if "deny" in xfo:
        return {"embeddable": False, "reason": "Der Dienst verbietet Rahmen (X-Frame-Options: DENY)"}
    if "sameorigin" in xfo:
        return {"embeddable": False, "reason": "Der Dienst erlaubt Rahmen nur auf der eigenen Domain"}
    if ancestors and "'none'" in ancestors:
        return {"embeddable": False, "reason": "Der Dienst verbietet Rahmen (frame-ancestors 'none')"}
    if ancestors and HOSTNAME not in ancestors and "*" not in ancestors:
        return {"embeddable": False, "reason": f"Der Dienst erlaubt Rahmen nur für: {ancestors}"}
    return {"embeddable": True, "reason": ""}


# Muss als LETZTE Route stehen, sonst verschluckt sie /api/… und /auth/….
@app.get("/{slug}", response_class=HTMLResponse)
def page_by_slug(request: Request, slug: str):
    user = auth.require_user(request)
    data = load_links()
    page = find_page(data, slug)
    if not page or not slug:
        raise HTTPException(404, "Diese Seite gibt es nicht")
    if page.get("role") and not has_role(user, page["role"]):
        raise HTTPException(404, "Diese Seite gibt es nicht")   # nicht verraten, dass es sie gibt
    return render_page(request, user, page, data)
