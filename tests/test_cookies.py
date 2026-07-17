"""Fachtest: Cookie-Flags. Was die Anwendung an den Browser gibt, nicht was im Code steht.

DashMyBoard setzt genau ein eigenes Cookie — das Double-Submit-CSRF-Token für die
Schreib-Routen (`with_csrf`). Es ist ABSICHTLICH nicht HttpOnly: JS muss es lesen können,
sonst funktioniert Double-Submit nicht. Genau darum steht die Erwartung je Cookie und nicht
als eine Regel für alle — ein pauschales „alle Cookies HttpOnly" meckert hier das einzige,
korrekt gebaute Cookie an.

Geprüft wird der rohe `Set-Cookie`-Header; Parser und Prüfregel kommen aus dem geteilten Kit
(`_kit/headers.py`, ab repokit 0.7.0). `with_csrf()` nimmt die Response direkt entgegen —
darum braucht diese Suite weder Client noch laufenden Server und bleibt schnell.
"""
import sys
from pathlib import Path

from fastapi import Response

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Report, fresh_data_dir, import_app  # noqa: E402
from _kit import headers  # noqa: E402

# Das CSRF-Cookie MUSS für JS lesbar bleiben (kein HttpOnly), aber sonst dicht sein.
ERWARTUNG = {
    "tinysesam_csrf": {"httponly": False, "secure": True, "samesite": "lax", "path": "/"},
}

data_dir = fresh_data_dir()
main = import_app(data_dir)
r = Report("Cookie-Flags")


def gesetzt(resp) -> dict:
    return headers.parse_set_cookie(headers.rohe_set_cookie(resp))


# ---- Admin: CSRF-Cookie wird gesetzt und trägt die richtigen Flags
cookies = gesetzt(main.with_csrf(Response(), admin=True))
r.check("Admin bekommt das CSRF-Cookie", "tinysesam_csrf" in cookies, str(list(cookies)))
verstoesse = headers.pruefe_cookie_flags(cookies, ERWARTUNG)
r.check("CSRF-Cookie: kein HttpOnly (JS liest es), aber Secure + SameSite + Path",
        not verstoesse, str(verstoesse))
r.check("CSRF-Cookie trägt einen Wert", bool(cookies.get("tinysesam_csrf", {}).get("_wert")))

# ---- Kein Admin: kein Token. Sonst gäbe die Seite ein Schreib-Token an jeden Leser.
r.check("Ohne Admin wird gar kein Cookie gesetzt", gesetzt(main.with_csrf(Response(), admin=False)) == {})

# ---- Zwei Aufrufe, zwei Token: ein festes Token wäre kein Schutz
a = gesetzt(main.with_csrf(Response(), admin=True))["tinysesam_csrf"]["_wert"]
b = gesetzt(main.with_csrf(Response(), admin=True))["tinysesam_csrf"]["_wert"]
r.check("jeder Aufruf erzeugt ein frisches Token", a != b)

import shutil  # noqa: E402

shutil.rmtree(data_dir, ignore_errors=True)
sys.exit(r.done())
