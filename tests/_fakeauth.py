"""Die Anwendung mit gefälschter Anmeldung — ausschließlich für den Browser-Test.

Der echte Weg führt über einen OIDC-Anbieter; den gibt es im Test nicht. Statt ihn
nachzubauen, wird die Sitzung durch einen festen Administrator ersetzt. Diese Datei
wird nie ausgeliefert (sie liegt unter tests/ und nicht im Image).

Gefälscht wird NUR, wer angemeldet ist. Die CSRF-Prüfung und die Cookie-Flags bleiben
echt (seit TinySesam 0.20): Bis dahin schaltete diese Datei beides ab — `require_csrf`
ließ alles durch, `cookie_secure=False` nahm dem Cookie das `__Host-`-Präfix. Damit hätte
der Browser-Test nie bemerkt, dass das Bearbeiten-Skript das CSRF-Cookie unter einem Namen
sucht, den es unter HTTPS nicht mehr gibt. Chrome nimmt `Secure`- und `__Host-`-Cookies
auch von `http://127.0.0.1` an (sicherer Kontext), deshalb geht das ohne Zertifikat.
"""
import main

USER = {
    "username": "testadmin",
    "display_name": "Test Admin",
    "roles": [main.ADMIN_ROLE],
    "is_admin": 0,
}

main.auth.current_user = lambda request: USER
main.auth.require_user = lambda request: USER
main.has_role = lambda user, role: role in user["roles"]

app = main.app
