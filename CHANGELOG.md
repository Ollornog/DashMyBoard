# Changelog

Alle nennenswerten Änderungen an diesem Projekt. Das Format folgt lose
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), die Versionen
[Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Geändert

- **Seiten werden dort bearbeitet, wo sie stehen.** Die Verwaltung ist aus den Einstellungen in die
  Navigation gewandert: im Bearbeiten-Modus lassen sich Seiten waagerecht ziehen, per Klick im Dialog
  ändern und über „+“ anlegen. Gelieferte Seiten (Startseite, eingebaute Ansichten) bleiben
  unveränderlich und sagen das, statt einen Dialog zu öffnen.

### Hinzugefügt

- **Ordner als Seitenart.** Ein Ordner ist keine Seite, sondern ein Auswahlmenü in der Navigation;
  er trägt Seiten, hat selbst weder Adresse noch Inhalt und darf keine Ordner enthalten. Solange er
  leer ist, sehen ihn nur Administratoren — ein totes Menü hilft niemandem.

### Geändert

- **Ein Bleistift statt zwei.** Der schwebende Knopf im Inhalt und der in der Lesezeichenleiste
  sind entfallen; in der Titelleiste steht nun ein Schalter, der beide Bereiche zugleich öffnet.
  Getrennte Modi waren eine Unterscheidung ohne Nutzen.
- **Die Kopfzeile rechts trägt keine Rahmen mehr.** Symbole und Kontoname sind größer, die
  Abgrenzung übernimmt eine Fläche beim Überfahren. Der aktive Bleistift bleibt eingefärbt.

### Geändert

- **Die Einstellungen-Schublade verkleinert die Seite, statt sie umzubrechen.** Zuvor rückte der
  Rumpf um ihre Breite ein: die Kopfzeile brach in zwei Zeilen um, Container sprangen in eine
  Spalte, rechts blieb Leere. Jetzt wird der ganze Rumpf maßstäblich verkleinert (`transform:
  scale`), die Anordnung bleibt erhalten. Unter 900 px liegt die Schublade weiterhin darüber.
- **Der Hygiene-Test nennt keine Namen mehr.** Statt einer wörtlichen Verbotsliste prüft er
  generische Muster (Dienst-Subdomains, private Adressbereiche, Container-Nummern) und trägt die
  wenigen Eigennamen nur als Anfang ihrer SHA256-Summe. Eine Liste im Klartext hätte in einem
  öffentlichen Repo genau das veröffentlicht, was sie schützen soll. Für Dokumentation reservierte
  Werte (RFC 2606, RFC 5737) bleiben erlaubt — sonst ließe sich die Regel nicht erklären.

- **Der pre-push-Hook prüft auch im nativen Lauf auf Rückstände.** Den Vergleich macht sonst nur die
  Container-CI; wer ohne sie auf `main` pusht, bekam ihn nie — eine Suite, die Dateien liegen lässt,
  wäre erst in der entfernten CI aufgefallen.

- **Zwei Regeln aus der ersten Schubladen-Fassung entfernt.** Sie rückten Titelleiste,
  Lesezeichenleiste und Inhalt einzeln um die Breite der Schublade ein. Zusammen mit dem neuen
  Maßstab schob das die Seite ein zweites Mal — sichtbar als breiter Streifen neben den Leisten.
  Der Browser-Test verlangt jetzt **Bündigkeit** statt bloß „keine Überlappung"; genau diese
  Lücke hatte er durchgelassen.
- **Der Maßstab wird nach dem Umbruch neu gemessen.** Der verkleinerte Rumpf wird höher und holt
  damit oft erst die senkrechte Bildlaufleiste ins Fenster; die schmälert die nutzbare Breite, und
  die Seite ragte vier Pixel unter die Schublade.

### Entfernt

- Zwei Notbehelfe in `scripts/check.sh` (eigener Paket-Cache, Zurücksetzen einer Umgebungsvariablen).
  Sie umgingen Fehler des Container-Abbilds, die dort inzwischen behoben sind. Der Interpreter wird
  weiterhin explizit angegeben, weil `VIRTUAL_ENV` allein nicht genügt.

### Hinzugefügt

- `.ci-network` — steuert, ob die lokale Container-CI Netzzugang bekommt. Nötig, weil `check.sh` die
  gepinnte Auth-Bibliothek selbst installiert.

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

[Unreleased]: https://github.com/Ollornog/DashMyBoard/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Ollornog/DashMyBoard/releases/tag/v0.1.0
