"""Fachtest: Cookie-Flags. Was die Anwendung an den Browser gibt, nicht was im Code steht.

DashMyBoard gibt genau ein Cookie selbst mit einer Seite aus — das Double-Submit-CSRF-Token
(`with_csrf`). Es ist ABSICHTLICH nicht HttpOnly: JS muss es lesen können, sonst funktioniert
Double-Submit nicht. Genau darum steht die Erwartung je Cookie und nicht als eine Regel für
alle — ein pauschales „alle Cookies HttpOnly" meckert hier das einzige, korrekt gebaute Cookie an.

Name, Flags und Wert kommen seit TinySesam 0.20 aus der Bibliothek (`auth.csrf_cookie_name`,
`auth.issue_csrf`). Bis dahin setzte die Anwendung das Cookie selbst unter `cfg.csrf_cookie` —
und dieser Test prüfte genau diesen Nachbau: Er blieb grün, während TinySesam das Cookie unter
`__Host-tinysesam_csrf` suchte und jede Schreib-Anfrage abwies. Deshalb steht hier jetzt der
Name, den TinySesam LIEST, und die Antwort einer echten Seite mit echter Sitzung.

Geprüft wird der rohe `Set-Cookie`-Header; Parser und Prüfregel kommen aus dem geteilten Kit
(`_kit/headers.py`, ab repokit 0.7.0).
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Report, angemeldet, fresh_data_dir, import_app  # noqa: E402
from _kit import headers  # noqa: E402

data_dir = fresh_data_dir()
main = import_app(data_dir)
r = Report("Cookie-Flags")

NAME = main.auth.csrf_cookie_name
# Das CSRF-Cookie MUSS für JS lesbar bleiben (kein HttpOnly), aber sonst dicht sein.
ERWARTUNG = {NAME: {"httponly": False, "secure": True, "samesite": "lax", "path": "/"}}


def gesetzt(resp) -> dict:
    return headers.parse_set_cookie(headers.rohe_set_cookie(resp))


# ---- Der Name ist der, den TinySesam liest — unter HTTPS mit `__Host-`-Präfix.
# Das Präfix hält Nachbar-Subdomains davon ab, ein eigenes Token unterzuschieben.
r.check("CSRF-Cookie heißt __Host-tinysesam_csrf (TinySesam, HTTPS-Vorgabe)",
        NAME == "__Host-tinysesam_csrf", NAME)

admin, _ = angemeldet(main, "anna", [main.ADMIN_ROLE])
seite = admin.get("/", follow_redirects=False)
r.check("Startseite liefert 200", seite.status_code == 200, f"HTTP {seite.status_code}")
cookies = gesetzt(seite)
r.check("die Seite setzt das CSRF-Cookie unter dem Namen, den TinySesam liest",
        NAME in cookies, str(list(cookies)))
verstoesse = headers.pruefe_cookie_flags(cookies, ERWARTUNG)
r.check("CSRF-Cookie: kein HttpOnly (JS liest es), aber Secure + SameSite + Path",
        not verstoesse, str(verstoesse))
r.check("CSRF-Cookie trägt einen Wert", bool(cookies.get(NAME, {}).get("_wert")))
r.check("kein Cookie unter dem alten Namen ohne Präfix", "tinysesam_csrf" not in cookies,
        str(list(cookies)))

# ---- Ein vorhandenes Token bleibt stehen: sonst würde jede neu geladene Seite das
# Abmelde-Formular in allen anderen offenen Tabs ungültig machen.
zweite = admin.get("/", follow_redirects=False)
r.check("zweiter Aufruf desselben Browsers setzt kein neues Token",
        NAME not in gesetzt(zweite), str(list(gesetzt(zweite))))

# ---- Zwei Browser, zwei Token: ein festes Token wäre kein Schutz
nutzer, _ = angemeldet(main, "bert", [])
b = gesetzt(nutzer.get("/", follow_redirects=False)).get(NAME, {}).get("_wert")
r.check("ein anderer Browser bekommt ein anderes Token", bool(b) and b != cookies[NAME]["_wert"])

# ---- Auch ohne Administratorrolle gibt es das Token — für das Abmelde-Formular.
# Es ist kein Recht: jede Schreib-Route prüft zuerst die Rolle (test_sitzung.py).
r.check("auch Nutzer ohne Admin-Rolle bekommen das Token (Abmelden)", bool(b))

shutil.rmtree(data_dir, ignore_errors=True)
sys.exit(r.done())
