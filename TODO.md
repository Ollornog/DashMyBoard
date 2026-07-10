# TODO

Offen ≠ erledigt ≠ entschieden. Entscheidungen stehen als **entschieden** hier, damit sie nicht
alle drei Monate neu aufgerollt werden.

## Offen

- **Screenshots** in `docs/` — die README verweist darauf, es gibt noch keine.
- **Ordner tiefer als eine Ebene?** Aktuell verboten. Erst bauen, wenn jemand es vermisst; ein Menü
  aus Menüs ist eine Navigation, die niemand überblickt.
- **Abbild-Signatur / SBOM** (`cosign`, Provenance). Ein Digest belegt Unverändertheit, nicht
  Herkunft. Sinnvoll, sobald Fremde das Abbild produktiv einsetzen.
- **End-to-End gegen einen echten Identitätsanbieter.** Die Suite fährt mit gefälschter Anmeldung;
  der echte OIDC-Fluss (Rücksprung, Gruppen-Claim, Abmeldung) ist damit nicht abgedeckt. Gehört als
  Smoke-Test hinter ein Deployment, nicht in die CI — dort fehlen Domain, Zertifikat und Anbieter.
- **Mehrere Mandanten in einer Instanz.** Bewusst nicht gebaut; siehe „entschieden".

## Entschieden

- **Kein Wheel, kein sdist.** DashMyBoard ist eine Anwendung, keine Bibliothek: `pyproject.toml`
  liefert kein Paket. Das Artefakt ist das **Container-Abbild**, gebaut aus dem Git-Tag.
- **Kein PyPI.** Aus demselben Grund. (Für Bibliotheken gilt: nicht vor 1.0.)
- **Kein `latest`-Tag.** Genau ein Abbild-Tag, gleich dem Git-Tag. Ein wandernder Tag macht jeden
  Neustart zum Glücksspiel.
- **Kein Selbst-Update.** Die Anwendung lädt zur Laufzeit keinen Code nach. Der Pin steht beim
  Betreiber (Abbild-Tag), nicht in der Software.
- **Eine Instanz je Mandant** statt Mandantentrennung im Code. Keine Vermischung von Daten, Rechten
  und Uploads; ein Fehler trifft einen Kunden, nicht alle.
- **Ordner sind keine Seiten.** Sie haben keine Adresse und keinen Inhalt — sonst wäre unklar, was
  ein Klick auf den Ordner bedeutet.
