# Changelog

Alle nennenswerten Änderungen an diesem Projekt. Das Format folgt lose
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), die Versionen
[Semantic Versioning](https://semver.org/lang/de/).

## [0.1.0] — 2026-07-10

Erste Veröffentlichung.

### Enthalten

- **Dashboard hinter Single Sign-On** (OIDC über TinySesam). Ohne Sitzung führt `/` direkt
  zum Anbieter; die Anmeldekarte erscheint nur nach dem Abmelden.
- **Seiten als Daten**: Startseite, weitere Linktree-Seiten, Reiter-Seiten mit eingebettetem
  Inhalt (`iframe`) und eingebaute Ansichten (News, Status). Anlegen, sortieren, löschen in
  der Oberfläche — kein Code nötig.
- **Bearbeiten auf der Seite**: Texte inline, Ziehen und Ablegen bis zu drei Verschachtelungs-
  ebenen, Dialoge für Adresse, Logo, Abzeichen, Rolle und Startzustand.
- **Lesezeichenleiste** je Seite, mit Ordnern, Import und Export im Browser-Format.
- **Drei Designs** (hell, ambient, dunkel), Hintergrund-Diashow je Seite, Flächenfarben und
  Deckkraft je Design, Größen für Titelleiste, Lesezeichenleiste und Inhalt.
- **Rollen aus der OIDC-Gruppe**: Container, Lesezeichen und ganze Seiten lassen sich auf eine
  Rolle beschränken. Ein lokaler Administrator erbt keine Rollen (`admin_implies_roles=False`).
- **Einbettbarkeits-Prüfung** (`GET /api/embeddable`): warnt beim Anlegen eines Reiters, wenn
  das Ziel `X-Frame-Options` oder `frame-ancestors` setzt und deshalb leer bliebe.
- **Testsuite**: Fachtests, Browser-Test über das DevTools-Protokoll, Hygiene-Test.
  Jede Suite bringt ihr eigenes Datenverzeichnis mit und ist wiederholbar.

[0.1.0]: https://github.com/Ollornog/DashMyBoard/releases/tag/v0.1.0
