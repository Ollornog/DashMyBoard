# Changelog

Alle nennenswerten Änderungen an diesem Projekt. Das Format folgt lose
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), die Versionen
[Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Hinzugefügt — die Flags des CSRF-Cookies stehen unter Aufsicht

Die Anwendung setzt genau ein eigenes Cookie: das Double-Submit-Token für die Schreib-Routen
(`with_csrf`). Seine Flags standen im Code richtig, aber kein Test hielt sie fest — fiele `secure`
bei einem Refactor weg, ginge das Token künftig auch über `http://` und niemand hätte es gemerkt.
`tests/test_cookies.py` nagelt es fest: Secure, SameSite, Path, ein frisches Token je Aufruf, und
kein Cookie für Nicht-Administratoren.

Das Cookie ist **absichtlich nicht HttpOnly** — JavaScript muss es lesen, sonst funktioniert
Double-Submit nicht. Genau darum steht die Erwartung je Cookie und nicht als eine Regel für alle:
Ein pauschales „alle Cookies HttpOnly" hätte hier das einzige, korrekt gebaute Cookie angemeckert.
Der Test hält beide Richtungen fest, das Fehlen *und* das fälschliche Vorhandensein.

Parser und Prüfregel kommen aus dem geteilten Kit (`_kit/headers.py`, repokit 0.7.0); die Suite
braucht weder Client noch laufenden Server, weil `with_csrf()` die Response direkt entgegennimmt.

### Geändert — Kit auf repokit 0.7.0

`repokit sync` zieht `_kit/headers.py` nach (Security-Header und Cookie-Flags) und bringt die
Sperrlisten auf den Stand von 0.7.0.

### Geändert — einheitliches Layout der Doku-Unterseiten

`CONTRIBUTING`, `SECURITY` und die deutschen `i18n/`-Fassungen tragen den Sprachwechsler jetzt
direkt unter der Überschrift und das Logo rechtsbündig am Fuß der Seite — dasselbe Muster in allen
eigenen Repos. Die englische `CODE_OF_CONDUCT.md` bleibt davon unberührt und **pur**, damit GitHub
sie als Contributor Covenant erkennt und nicht als „Other".

### Geändert — Bildnachweis verweist direkt auf die Autorenseite

Der Flaticon-Link zeigt jetzt auf die Autorenseite (Iconjam) statt auf die Suchseite und öffnet in
neuem Tab; die Beschreibung ist präzisiert (Ei). Format wie in den übrigen Repos:
`Icon: … PNG Image by … - flaticon.com`.

### Hinzugefügt — Repo-Logo

- **`docs/logo.png`** im README-Kopf beider Sprachfassungen (Logo und Titel zentriert), mit
  Flaticon-Attribution (Iconjam). `flaticon.com` ist damit ein erlaubter Attributions-Host in der
  Hygiene (wie `contributor-covenant.org`).

### Hinzugefügt — Verhaltenskodex

- **`CODE_OF_CONDUCT.md`** (+ deutsche Fassung): der Contributor Covenant 2.1, Kontakt
  `dashmyboard-github@ollornog.de`. Er steht auf GitHubs *community profile checklist* und fehlte bisher.
  (`contributor-covenant.org` ist als Attributions-Verweis nun ein erlaubter Host in der Hygiene.)

### Geändert — die Testbasis ist geteilt, nicht mehr kopiert

Die allgemeinen Hygiene-Prüfungen, die Sperrlisten und der Rückstands-Check standen in jedem
Projekt als eigene Kopie — und liefen auseinander. Jetzt liegen sie unter `tests/_kit/` als
eingecheckte, geteilte Basis: die Regeln als reine Daten (`hygiene_policy.json`), die Prüfungen
als stdlib-only Funktionen. Sie werden erzeugt, nicht von Hand geschrieben.

**Es kommt nichts hinzu, was geladen werden müsste.** Kein pip-Paket, kein Submodul, kein Netz zur
Testzeit — `tests/_kit/` liegt in jedem `git clone`, jedem ZIP und jedem Release-Tarball. Käme der
Wächter, der „keine private Infrastruktur" erzwingt, selbst über das Netz, wäre er das Leck, das er
verhindern soll.

Diese Suite behält ihren sammelnden `r.check()`-Stil: die geteilten Prüfungen geben Listen von
Verstößen zurück, statt zu werfen, und passen darum auch in das `assert`-Idiom des
Schwesterprojekts. 139 Zeilen weg, 53 dazu.

### Hinzugefügt — belegte Standards werden jetzt maschinell erzwungen

Vier Regeln aus einer Standards-Recherche (mit Primärquellen) prüft die Hygiene-Suite jetzt selbst:
Actions per vollem **Commit-SHA** gepinnt (nicht per Tag; `.github/dependabot.yml` hält sie aktuell),
**`permissions:`** auf oberster Ebene jedes Workflows, **CHANGELOG-Kategorien** aus Keep a Changelog,
und **`README.de.md` folgt der Struktur von `README.md`** — GitHub wählt die README nach Ort aus,
nicht nach Sprache, eine Übersetzung veraltet also unbemerkt. Der Check fand sofort, dass der
Abschnitt „Bildschirmfotos" auf Deutsch fehlte; er ist ergänzt.

Dazu aktiviert: Private Vulnerability Reporting und Dependabot Security Updates.

### Behoben — die CI ignorierte `.ci-allow-dirty`

Der Rückstands-Check existierte fünffach. Der `pre-push`-Hook und `ci-local` lasen
`.ci-allow-dirty`; die CI prüfte rohes `git status --porcelain` und kannte die Datei nicht. Das
verbindliche Gate widersprach damit dem lokalen Netz. Hook und CI fahren jetzt dieselbe Datei,
`scripts/_residue_check.sh`.

### Behoben — der eigene Name stand auf der Sperrliste

Die Namens-Sperrliste enthielt den GitHub-Owner. Der ist aber ausdrücklich erlaubt: Repo-URL,
Copyright-Zeile und Impressumsadresse müssen ihn nennen dürfen. Hier fiel das nie auf, weil die
Identitäts-Maskierung die URL-Zeilen zufällig traf — im Schwesterprojekt, das ein Impressum und
eine Pages-Adresse hat, schlug er sofort an. Der Eintrag ist entfernt; eine Dienst-Subdomain
trifft weiterhin das Subdomain-Muster, die nackte Domain nicht.

### Geändert

- **`pre-push` fährt wieder einen einfachen `ci-local`-Lauf** statt `--full`. Der Doppellauf, der
  die Wiederholbarkeit beweist, gehört in die CI und vor den Release — nicht in die kurze Schleife
  vor jedem Push.
- **Der Hook rät nicht mehr zum falschen Befehl, wenn Docker nicht antwortet.** Er unterscheidet
  jetzt drei Fälle: die Gruppe `docker` fehlt wirklich (dann ist `usermod` richtig), nur die
  aktuelle Shell kennt sie noch nicht (dann genügt `sg docker -c '…'` — es fehlt kein Recht), oder
  der Daemon läuft nicht. Bisher riet er zu `docker info`, das alle drei Ursachen gleich
  beantwortet, und bot als Ausweg nur `--no-verify` an.
- **Der native Rückstands-Check kennt `.ci-allow-dirty`** und vergleicht zeilenweise gegen den
  Zustand *vor* dem Lauf, statt den Arbeitsbaum als Ganzes. Ein schon vorher schmutziger Baum gilt
  damit nicht mehr als Rückstand der Suite — dasselbe Verhalten wie in `ci-local`.
- **Vor dem Container-Lauf prüft der Hook, ob Docker erreichbar ist**, statt `ci-local` blind zu
  starten. Auf Feature-Branches bricht er dann ab (dort läuft keine CI), auf `main` fällt er auf
  den nativen Lauf zurück, weil die CI anschließend als Gate greift.

## [0.3.0] — 2026-07-10

### Hinzugefügt

- **Ziehgriff an jeder Seite** in der Navigation, sobald der Bearbeiten-Modus läuft — dasselbe
  Zeichen wie im Linktree, damit erkennbar ist, was sich schieben lässt.
- **Adressen dürfen leer bleiben.** Eine Seite ohne Adresse ist eine Beschriftung in der Leiste,
  ein Lesezeichen ohne Adresse bleibt in der Leiste stehen — beides nicht anklickbar, im
  Bearbeiten-Modus dennoch änderbar. So verhält es sich schon lange bei Einträgen im Linktree.
  Der Export ins Browser-Format lässt Lesezeichen ohne Adresse aus, dort haben sie keinen Platz.
  Der Unterschied zur Startseite bleibt eindeutig: **fehlender** Schlüssel heißt „keine Adresse",
  **leerer** Schlüssel heißt „Startseite".

## [0.2.0] — 2026-07-10

### Geändert

- **Seiten werden dort bearbeitet, wo sie stehen.** Die Verwaltung ist aus den Einstellungen in die
  Navigation gewandert: im Bearbeiten-Modus lassen sich Seiten waagerecht ziehen, per Klick im Dialog
  ändern und über „+“ anlegen. Gelieferte Seiten (Startseite, eingebaute Ansichten) bleiben
  unveränderlich und sagen das, statt einen Dialog zu öffnen.

### Sicherheit

- **Auth-Bibliothek auf v0.13.1.** Deren 0.12.0 hat das Selbst-Update ersatzlos entfernt: Die
  Zielversion war ein Einstellungswert, im Admin-Panel frei setzbar — wer eine Admin-Sitzung
  übernahm, konnte auf eine alte Fassung mit bekannter Lücke zurückschalten, dauerhaft über
  Neustarts hinweg.

### Hinzugefügt

- **Ein Release-Workflow.** Ein Tag prüft die Paketversion, fährt die Suite, baut ein mehrarchiges
  Container-Abbild nach GHCR und legt das Release an. **Kein `latest`**: genau ein Abbild-Tag,
  gleich dem Git-Tag.
- **`TODO.md`** — offen, erledigt und *entschieden* getrennt, damit Entscheidungen nicht alle drei
  Monate neu aufgerollt werden.
- **`.dockerignore`** — kleiner Kontext, sicherer Kontext.

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

- **Das Container-Abbild ist mehrstufig** und trägt weder `pip` noch `git`. Wer im laufenden
  Container Code nachladen kann, hat gewonnen. Ein venv bringt sein eigenes `pip` mit; das wird
  eigens entfernt.
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

Erster Stand des Codes. **Nie veröffentlicht** — kein Tag, kein Abbild; die erste Fassung, die man
installieren kann, ist 0.2.0.

### Hinzugefügt

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

[0.3.0]: https://github.com/Ollornog/DashMyBoard/releases/tag/v0.3.0
[0.2.0]: https://github.com/Ollornog/DashMyBoard/releases/tag/v0.2.0
