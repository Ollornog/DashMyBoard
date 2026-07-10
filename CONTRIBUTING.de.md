<p align="center"><img src="docs/logo.png" alt="DashMyBoard" width="60"></p>

<h1 align="center">Mitwirken</h1>

<p align="center"><a href="CONTRIBUTING.md">English</a> · <b>Deutsch</b></p>

Danke für die Zeit. Dieses Projekt ist absichtlich klein; eine Änderung, die es klein lässt, ist
meistens die bessere.

## Grundregeln

1. **Tests gehören zur Änderung, nicht zur Nachbereitung.** Wer Verhalten ändert, ändert im selben
   Commit den Test. Doku und `CHANGELOG.md` wandern mit.
2. **Die Suite muss wiederholbar sein.** Jede Suite legt ihr eigenes, frisches Datenverzeichnis an,
   startet die Dienste, die sie braucht, und räumt sie ab. `./scripts/check.sh` zweimal laufen
   lassen — beide Läufe grün. Ein Test, der beim zweiten Lauf rot wird, ist kaputt, nicht der Code.
3. **Keine persönlichen Namen im Repo.** Keine privaten Hostnamen, keine Firmendomains, keine
   Kundennamen — weder im Code noch in Beispieldaten, Tests, Doku oder Commit-Messages. Stattdessen
   `example.com` und echte Werte über Umgebungsvariablen. `tests/test_repo.py` prüft das.
4. **Konfiguration kommt aus der Umgebung.** `BASE_URL` und `OIDC_ISSUER` haben bewusst keinen
   Vorgabewert: ein Dashboard, das stillschweigend mit fremder Adresse startet, ist schlimmer als
   eines, das den Start verweigert.

## Ablauf

Gearbeitet wird auf einem Feature-Branch. Dort läuft keine CI — `ci-local` bzw.
`./scripts/check.sh` ist das Sicherheitsnetz. Dann ein Pull Request; die CI läuft am PR und auf
`main`.

```bash
git switch -c meine-aenderung
pip install -e ".[dev]"
git config core.hooksPath .githooks    # einmal pro Klon
# ... bauen, dann:
./scripts/check.sh
git commit -am "Beschreibe die Änderung, nicht den Diff"
git push -u origin meine-aenderung
```

## Stil

- Kommentare erklären das **Warum**, nie was die nächste Zeile tut. Braucht eine Zeile einen
  Kommentar, um lesbar zu sein, gehört die Zeile umgeschrieben.
- Die Oberfläche spricht Deutsch; Bezeichner im Code sind englisch.
- Dateien sind UTF-8 ohne BOM. Umlaute werden als Umlaute geschrieben.
- Keine neue Abhängigkeit ohne einen Grund, der in einen Satz passt.

## Fehler melden

Was war erwartet, was passierte, und die kleinste `links.json`, die es reproduziert. Bei
Layout-Fehlern helfen Screenshots, bei allem anderen die Browser-Konsole.
