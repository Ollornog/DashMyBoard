"""Beispieldaten für die eingebauten Ansichten „News" und „Status".

Beides sind Attrappen mit fester Struktur. Wer echte Quellen anbinden will, ersetzt die
Werte hier (oder füllt sie in `render_page()` aus einer API) — die Templates lesen nur
die Form, nicht die Herkunft.
"""

NEWS_ITEMS = [
    {
        "title": "Dashboard eingerichtet",
        "source": "Intern",
        "date": "1. März 2026",
        "teaser": "Alle Dienste an einem Ort, hinter dem zentralen Single Sign-On. "
                  "Lesezeichen, Container und Gruppen lassen sich direkt auf der Seite bearbeiten.",
        "tag": "Plattform",
    },
    {
        "title": "Zweiter Standort angebunden",
        "source": "Infrastruktur",
        "date": "24. Februar 2026",
        "teaser": "Die Zweigstelle erreicht die internen Dienste jetzt über ein verschlüsseltes "
                  "Overlay-Netz statt über eine offene Weiterleitung.",
        "tag": "Netzwerk",
    },
    {
        "title": "Sicherungen laufen nächtlich",
        "source": "Betrieb",
        "date": "18. Februar 2026",
        "teaser": "Datenbanken werden vor der Sicherung konsistent abgezogen; eine Rücksicherung "
                  "wurde einmal vollständig geprobt.",
        "tag": "Backup",
    },
    {
        "title": "Wartungsfenster am Sonntag",
        "source": "Betrieb",
        "date": "10. Februar 2026",
        "teaser": "Zwischen 6 und 8 Uhr werden Betriebssystem-Pakete eingespielt. "
                  "Mit kurzen Unterbrechungen der Weboberflächen ist zu rechnen.",
        "tag": "Ankündigung",
    },
]

STATUS_DATA = {
    "summary": [
        {"label": "Hosts online", "value": "5 / 6", "hint": "worker-02 antwortet nicht"},
        {"label": "Dienste", "value": "14", "hint": "alle erreichbar"},
        {"label": "Updates offen", "value": "3", "hint": "davon 1 sicherheitsrelevant"},
        {"label": "Letztes Backup", "value": "03:00", "hint": "ohne Fehler"},
    ],
    "hosts": [
        {"name": "gateway", "role": "Gateway", "state": "ok", "cpu": 14, "ram": 41, "uptime": "101 Tage"},
        {"name": "hypervisor", "role": "Virtualisierung", "state": "ok", "cpu": 22, "ram": 63, "uptime": "88 Tage"},
        {"name": "app-01", "role": "Anwendungen", "state": "ok", "cpu": 9, "ram": 47, "uptime": "31 Tage"},
        {"name": "db-01", "role": "Datenbank", "state": "warn", "cpu": 71, "ram": 82, "uptime": "17 Tage"},
        {"name": "backup-01", "role": "Sicherung", "state": "ok", "cpu": 3, "ram": 19, "uptime": "63 Tage"},
        {"name": "worker-02", "role": "Hintergrundjobs", "state": "down", "cpu": 0, "ram": 0, "uptime": "—"},
    ],
    "backups": [
        {"job": "Hosts", "when": "heute, 03:00", "state": "ok", "detail": "8,8 GiB, 12 Min."},
        {"job": "Container", "when": "heute, 02:30", "state": "ok", "detail": "34 GiB, 41 Min."},
        {"job": "Datenbank-Dumps", "when": "heute, 03:10", "state": "ok", "detail": "4 Dumps"},
        {"job": "Dateiabgleich", "when": "laufend", "state": "ok", "detail": "ereignisgesteuert"},
    ],
}
