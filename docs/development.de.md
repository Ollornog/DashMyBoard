# Entwicklung

*[English version](development.md)*

```bash
pip install -e ".[dev]"
git config core.hooksPath .githooks
./scripts/check.sh
```

## Die Suite

| Suite | Was sie beweist |
|-------|-----------------|
| `tests/test_data.py` | Migrationen, Seitenarten und -adressen, Verschachtelungstiefe, Adressregeln, Rechteprüfung. Ohne Netz. |
| `tests/test_browser.py` | Was der Nutzer wirklich sieht: headless Chrome über das DevTools-Protokoll. Startet seinen eigenen Server. Wird übersprungen (nicht rot), wenn Chrome oder `websockets` fehlt. |
| `tests/test_repo.py` | Hygiene: Pflichtdateien, Versionsgleichstand, keine Artefakte, keine Geheimnisse, **keine persönlichen Namen**. |

`tests/run_all.py` findet jede `test_*.py` von selbst — eine neue Suite muss nirgends eingetragen
werden.

## Wiederholbarkeit ist eine harte Regel

Jede Suite legt ihr eigenes temporäres Datenverzeichnis an, startet, was sie braucht, und räumt es
ab. `./scripts/check.sh` zweimal muss zweimal grün sein. Ein Test, der von Rückständen des
vorherigen Laufs lebt, ist kaputt — auch wenn er beim ersten Mal durchgeht.

Der Browser-Test fährt die Anwendung über `tests/_fakeauth.py`, das die OIDC-Sitzung durch einen
festen Administrator ersetzt. Diese Datei wird nie ausgeliefert: sie liegt unter `tests/`, nicht im
Image.

## Keine persönlichen Namen

`tests/test_repo.py` durchsucht jede versionierte Datei nach privaten Hostnamen, Firmendomains und
Kundennamen und lässt als Beispieladressen nur `example.com` und Verwandte zu. Das ist keine
Höflichkeit — es verhindert, dass ein öffentliches Repo die interne Topologie verrät.

## Architektur in drei Sätzen

`app/main.py` enthält den ganzen Server: Datenzugriff, Prüfung, Routen und eine kleine API für den
Bearbeiten-Modus. `links.json` ist die einzige Wahrheit und wird atomar geschrieben. Der Browser
bekommt drei Skripte: `ui.js` (Klappen, Menüs, Meldungen) für alle, `frames.js` für Reiter-Seiten
und `admin.js` (Bearbeiten-Modus, Einstellungs-Schublade) nur für Administratoren.
