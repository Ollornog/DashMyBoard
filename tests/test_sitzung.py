"""Fachtest: Sitzung, CSRF und Abmelden — gegen das echte TinySesam, ohne gefälschte Anmeldung.

Der Browser-Test ersetzt die Anmeldung durch einen festen Administrator (es gibt dort keinen
Identity Provider). Was er deshalb nicht zeigen kann, steht hier: Konto und Sitzung legt
TinySesam selbst an, jede Anfrage läuft durch die Prüfungen der Bibliothek, wie sie
ausgeliefert wird.

Anlass war TinySesam 0.20: Das CSRF-Cookie heißt unter HTTPS `__Host-tinysesam_csrf`, die
Prüfung schaut vor dem Token auf die Herkunft (Origin / Sec-Fetch-Site), und Abmelden ist
ein POST mit Token. Alle drei Brüche hätte keine der bisherigen Suiten bemerkt.
"""
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Report, angemeldet, fresh_data_dir, import_app  # noqa: E402

data_dir = fresh_data_dir()
main = import_app(data_dir)
auth = main.auth
r = Report("Fachtests — Sitzung, CSRF, Abmelden (echtes TinySesam)")

EIGEN = main.BASE_URL
FREMD = "https://fremd.example.org"


# ================================================================ Fassung
# Eine TinySesam-Fassung ohne die Cookie-Namen-API muss den Start verweigern, statt jede
# Seite mit 500 zu beantworten. Gegenprobe mit einer Klasse, der beides fehlt.
r.check("die installierte Fassung bringt die nötige API mit", main._fehlende_api(type(auth)) == [])
r.check("eine Fassung ohne csrf_cookie_name fiele beim Start auf",
        "csrf_cookie_name" in main._fehlende_api(object))


def formular_token(html: str) -> str | None:
    m = re.search(r'<form method="post" action="/auth/logout">\s*'
                  r'<input type="hidden" name="_csrf" value="([^"]*)">', html)
    return m.group(1) if m else None


# ================================================================ Administrator
admin, admin_sitzung = angemeldet(main, "anna", [main.ADMIN_ROLE])
seite = admin.get("/", follow_redirects=False)
token = admin.cookies.get(auth.csrf_cookie_name)
r.check("Administrator sieht die Startseite", seite.status_code == 200, f"HTTP {seite.status_code}")
r.check("CSRF-Cookie liegt unter dem Namen, den TinySesam liest", bool(token),
        str(dict(admin.cookies)))
r.check("das Bearbeiten-Skript bekommt den Cookie-Namen vom Server",
        f"window.GO_CSRF_COOKIE = {json.dumps(auth.csrf_cookie_name)};" in seite.text)
r.check("admin.js schreibt keinen Cookie-Namen fest",
        "tinysesam_csrf" not in (main.HERE / "static/admin.js").read_text(encoding="utf-8"))

modell = admin.get("/api/links").json()


def schreiben(client, kopf: dict) -> int:
    return client.put("/api/links", content=json.dumps(modell),
                      headers={"Content-Type": "application/json", **kopf}).status_code


r.check("Schreiben mit dem Token aus dem Cookie wird angenommen",
        schreiben(admin, {"X-CSRF-Token": token}) == 200)
r.check("… auch mit eigener Herkunft (Origin)",
        schreiben(admin, {"X-CSRF-Token": token, "Origin": EIGEN}) == 200)
r.check("Schreiben ohne Token wird abgewiesen", schreiben(admin, {}) == 403)
r.check("Schreiben mit falschem Token wird abgewiesen",
        schreiben(admin, {"X-CSRF-Token": "falsch"}) == 403)
# Die Herkunftsprüfung kommt VOR dem Token: ein richtiges Token von fremder Seite zählt nicht.
r.check("richtiges Token von fremder Herkunft wird abgewiesen (Origin)",
        schreiben(admin, {"X-CSRF-Token": token, "Origin": FREMD}) == 403)
r.check("richtiges Token aus der Nachbarschaft wird abgewiesen (Sec-Fetch-Site)",
        schreiben(admin, {"X-CSRF-Token": token, "Sec-Fetch-Site": "same-site"}) == 403)

# Ein Browser, der noch das Cookie von vor dem Update trägt (ohne Präfix), schreibt damit
# nichts mehr: TinySesam liest nur den neuen Namen.
alt, _ = angemeldet(main, "carla", [main.ADMIN_ROLE])
alt.cookies.set("tinysesam_csrf", "vom-alten-stand")
r.check("das Cookie unter dem alten Namen zählt nicht",
        schreiben(alt, {"X-CSRF-Token": "vom-alten-stand"}) == 403)

# ================================================================ Nutzer ohne Admin-Rolle
nutzer, nutzer_sitzung = angemeldet(main, "bert", [])
n_seite = nutzer.get("/", follow_redirects=False)
n_token = nutzer.cookies.get(auth.csrf_cookie_name)
r.check("Nutzer sieht die Startseite", n_seite.status_code == 200, f"HTTP {n_seite.status_code}")
r.check("Nutzer bekommt kein Bearbeiten-Skript", "/static/admin.js" not in n_seite.text)
r.check("Nutzer bekommt ein Abmelde-Formular mit seinem Token",
        bool(n_token) and formular_token(n_seite.text) == n_token)
# Das Token ist kein Recht: die Rolle wird zuerst geprüft.
r.check("mit gültigem Token darf ein Nutzer trotzdem nicht schreiben",
        schreiben(nutzer, {"X-CSRF-Token": n_token}) == 403)

# ================================================================ Abmelden
r.check("kein GET-Link zum Abmelden mehr", 'href="/auth/logout"' not in seite.text)
r.check("das Formular trägt das Token des Cookies", formular_token(seite.text) == token,
        str(formular_token(seite.text)))

ohne = admin.post("/auth/logout", follow_redirects=False)
r.check("Abmelden ohne Token wird abgewiesen", ohne.status_code == 403, f"HTTP {ohne.status_code}")
fremd = admin.post("/auth/logout", data={"_csrf": token}, headers={"Origin": FREMD},
                   follow_redirects=False)
r.check("Abmelden von fremder Seite wird abgewiesen", fremd.status_code == 403,
        f"HTTP {fremd.status_code}")
# Der alte Link, von einer fremden Seite ausgelöst, meldet nicht ab — TinySesam fragt nach.
quer = admin.get("/auth/logout", headers={"Sec-Fetch-Site": "cross-site"}, follow_redirects=False)
r.check("GET von fremder Seite meldet nicht ab (Rückfrage)", quer.status_code == 200,
        f"HTTP {quer.status_code}")
r.check("… die Sitzung lebt danach noch", admin.get("/", follow_redirects=False).status_code == 200)

aus = admin.post("/auth/logout", data={"_csrf": token}, follow_redirects=False)
r.check("Abmelden per Formular leitet auf die Abgemeldet-Adresse",
        aus.status_code == 303 and aus.headers.get("location") == "/?abgemeldet=1",
        f"HTTP {aus.status_code} → {aus.headers.get('location')}")
r.check("die Sitzung ist in TinySesam beendet", auth.store.get_session(admin_sitzung) is None)
admin.cookies.set(auth.session_cookie_name, admin_sitzung)   # das alte Cookie noch einmal vorlegen
danach = admin.get("/", follow_redirects=False)
r.check("mit dem alten Sitzungs-Cookie geht es zurück zur Anmeldung",
        danach.status_code == 303 and danach.headers.get("location") == "/auth/oidc/start",
        f"HTTP {danach.status_code} → {danach.headers.get('location')}")
r.check("fremde Sitzungen bleiben unberührt", auth.store.get_session(nutzer_sitzung) is not None)

shutil.rmtree(data_dir, ignore_errors=True)
sys.exit(r.done())
