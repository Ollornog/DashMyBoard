"""Fachtests der Datenschicht: Migrationen, Seitenarten und -adressen, Verschachtelungs-
tiefe, Adressregeln. Läuft ohne Netz gegen ein frisches, temporäres Datenverzeichnis."""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Report, fresh_data_dir, import_app, seed  # noqa: E402

# Altbestand, wie ihn frühere Fassungen schrieben: pages als Wörterbuch, sections global,
# Größen an der Seite, Adressen ohne Schema. Genau das muss die Migration auffangen.
LEGACY = {
    "site": {"title": "Altes Dashboard", "subtitle": "Intranet"},
    "pages": {
        "": {"layout": {"bar": {"height": 72}}, "interval": 12,
             "bookmarks": [{"name": "Alt", "url": "alt.example.com"}]},
        "news": {"layout": {"bar": {"height": 99}}},           # verliert: erste Seite gewinnt
        "status": {},
    },
    "sections": [{"title": "Infrastruktur",
                  "groups": [{"links": [{"name": "A", "url": "a.example.com"}]}]}],
}

data_dir = fresh_data_dir()
seed(data_dir, LEGACY)
main = import_app(data_dir)
from fastapi import HTTPException  # noqa: E402

r = Report("Fachtests — Datenschicht")


def eq(actual, expected):
    if actual != expected:
        raise AssertionError(f"{actual!r} != {expected!r}")


def raises(fn, needle=""):
    try:
        fn()
    except HTTPException as exc:
        if needle not in str(exc.detail):
            raise AssertionError(f"andere Meldung: {exc.detail}") from None
        return
    raise AssertionError("kein Fehler ausgelöst")


def base(pages=None, site=None):
    return {
        "site": site if site is not None else {"title": "T"},
        "pages": pages if pages is not None else [{"slug": "", "title": "Start", "type": "links"}],
    }


def linkpage(links):
    return base([{"slug": "", "title": "Start", "type": "links",
                  "sections": [{"title": "S", "groups": [{"links": links}]}]}])


def nest(depth):
    node = {"name": f"E{depth}"}
    for i in range(depth - 1, 0, -1):
        node = {"name": f"E{i}", "children": [node]}
    return linkpage([node])


stored = json.loads((data_dir / "links.json").read_text(encoding="utf-8"))

# ---- Migration des Altbestands
r.run("pages wird zur Liste", lambda: eq(type(stored["pages"]).__name__, "list"))
r.run("Reihenfolge Start, News, Status",
      lambda: eq([p["slug"] for p in stored["pages"]], ["", "news", "status"]))
r.run("Startseite ist ein Linktree", lambda: eq(stored["pages"][0]["type"], "links"))
r.run("News und Status sind eingebaut",
      lambda: eq([p["type"] for p in stored["pages"][1:]], ["builtin", "builtin"]))
r.run("Status bleibt der Administratorrolle vorbehalten",
      lambda: eq(stored["pages"][2]["role"], main.ADMIN_ROLE))
r.run("Container wandern in die Startseite",
      lambda: eq(stored["pages"][0]["sections"][0]["title"], "Infrastruktur"))
r.run("Container stehen nicht mehr im Wurzelobjekt", lambda: eq("sections" in stored, False))
r.run("Größen wandern nach site.layout", lambda: eq(stored["site"]["layout"], {"bar": {"height": 72}}))
r.run("keine Seite hat mehr eigene Größen",
      lambda: eq(any("layout" in p for p in stored["pages"]), False))
r.run("Adressen ohne Schema werden ergänzt",
      lambda: eq(stored["pages"][0]["sections"][0]["groups"][0]["links"][0]["url"], "https://a.example.com"))
r.run("auch in Lesezeichen",
      lambda: eq(stored["pages"][0]["bookmarks"][0]["url"], "https://alt.example.com"))
r.run("find_page findet die Startseite", lambda: eq(main.find_page(stored, "")["title"], "Start"))
r.run("page_config liest site.layout",
      lambda: eq(main.page_config(stored, main.find_page(stored, ""))["layout"]["bar"]["height"], 72))

# ---- Seiten
r.run("Reiter-Seite ist gültig", lambda: main.validate_links(base([
    {"slug": "", "title": "Start", "type": "links"},
    {"slug": "team", "title": "Team", "type": "frames",
     "bookmarks": [{"name": "Wiki", "url": "https://wiki.example.com"}], "start": "0"}])))
r.run("Reiter-Seite verliert Container", lambda: eq("sections" in main.validate_links(base([
    {"slug": "", "title": "Start", "type": "links"},
    {"slug": "t", "title": "T", "type": "frames", "sections": [{"title": "X"}]}]))["pages"][1], False))
r.run("unbekannte Seitenart wird abgelehnt", lambda: raises(lambda: main.validate_links(base([
    {"slug": "", "title": "Start", "type": "zauber"}])), "Seitenart"))
r.run("eingebaute Seite braucht bekannte Ansicht", lambda: raises(lambda: main.validate_links(base([
    {"slug": "", "title": "Start", "type": "links"},
    {"slug": "x", "title": "X", "type": "builtin", "view": "gibtsnicht"}])), "Ansicht"))
r.run("Seite ohne Titel wird abgelehnt", lambda: raises(lambda: main.validate_links(base([
    {"slug": "", "title": "", "type": "links"}])), "Titel"))
r.run("doppelte Adresse wird abgelehnt", lambda: raises(lambda: main.validate_links(base([
    {"slug": "", "title": "Start", "type": "links"},
    {"slug": "a", "title": "A", "type": "links"},
    {"slug": "a", "title": "B", "type": "links"}])), "doppelt"))
r.run("reservierte Adresse wird abgelehnt", lambda: raises(lambda: main.validate_links(base([
    {"slug": "", "title": "Start", "type": "links"},
    {"slug": "api", "title": "API", "type": "links"}])), "Ungültige Seiten-Adresse"))
r.run("Adresse mit Schrägstrich wird abgelehnt", lambda: raises(lambda: main.validate_links(base([
    {"slug": "", "title": "Start", "type": "links"},
    {"slug": "a/b", "title": "AB", "type": "links"}])), "Ungültige Seiten-Adresse"))
r.run("Startseite darf nicht fehlen", lambda: raises(lambda: main.validate_links(base([
    {"slug": "news", "title": "News", "type": "builtin", "view": "news"}])), "Startseite"))
r.run("leere Seitenliste wird abgelehnt",
      lambda: raises(lambda: main.validate_links(base([])), "mindestens eine Seite"))
r.run("Container im Wurzelobjekt werden abgelehnt",
      lambda: raises(lambda: main.validate_links({**base(), "sections": []}), "gehören zu einer Seite"))

# ---- Verschachtelung
r.run("drei Ebenen sind erlaubt", lambda: main.validate_links(nest(3)))
r.run("vier Ebenen sind erlaubt (dreimal verschachtelt)", lambda: main.validate_links(nest(4)))
r.run("fünf Ebenen werden abgelehnt", lambda: raises(lambda: main.validate_links(nest(5)), "tief verschachtelt"))

# ---- Einträge und Adressen
r.run("Eintrag ohne Adresse ist erlaubt", lambda: main.validate_links(linkpage([{"name": "Nur Text"}])))
r.run("Untereintrag ohne Adresse ist erlaubt",
      lambda: main.validate_links(linkpage([{"name": "A", "children": [{"name": "B"}]}])))
r.run("fehlendes Schema wird ergänzt", lambda: eq(
    main.validate_links(linkpage([{"name": "A", "url": "a.example.com"}]))
    ["pages"][0]["sections"][0]["groups"][0]["links"][0]["url"], "https://a.example.com"))
r.run("javascript: wird abgelehnt", lambda: raises(
    lambda: main.validate_links(linkpage([{"name": "A", "url": "javascript:alert(1)"}])), "nicht erlaubt"))
r.run("data: wird abgelehnt", lambda: raises(
    lambda: main.validate_links(linkpage([{"name": "A", "url": "data:text/html,x"}])), "nicht erlaubt"))

# ---- site
r.run("Größen werden gegen ihre Grenzen geprüft", lambda: raises(lambda: main.validate_links(
    base(site={"title": "T", "layout": {"bar": {"height": 9999}}})), "zwischen"))
r.run("site ohne Titel wird abgelehnt", lambda: raises(lambda: main.validate_links(base(site={})), "Titel"))

# ---- Rollen: ein lokaler Administrator erbt KEINE Rollen
r.run("has_role prüft nur die OIDC-Rolle",
      lambda: eq(main.has_role({"roles": [], "is_admin": 1}, main.ADMIN_ROLE), False))

shutil.rmtree(data_dir, ignore_errors=True)
sys.exit(r.done())
