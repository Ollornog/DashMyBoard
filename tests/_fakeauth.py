"""Die Anwendung mit gefälschter Anmeldung — ausschließlich für den Browser-Test.

Der echte Weg führt über einen OIDC-Anbieter; den gibt es im Test nicht. Statt ihn
nachzubauen, wird die Sitzung durch einen festen Administrator ersetzt. Diese Datei
wird nie ausgeliefert (sie liegt unter tests/ und nicht im Image).
"""
import main

USER = {
    "username": "testadmin",
    "display_name": "Test Admin",
    "roles": [main.ADMIN_ROLE],
    "is_admin": 0,
}

# Über http würde der Browser ein Secure-Cookie verwerfen — dann fehlte das CSRF-Token.
main.auth.cfg.cookie_secure = False
main.auth.current_user = lambda request: USER
main.auth.require_user = lambda request: USER
main.auth.require_csrf = lambda request, token: None
main.has_role = lambda user, role: role in user["roles"]

app = main.app
