# Konfiguration

*[English version](configuration.md)*

Alles wird über Umgebungsvariablen gesetzt. `BASE_URL` und `OIDC_ISSUER` haben **keinen
Vorgabewert**: ein Dashboard, das stillschweigend mit fremder Adresse startet, ist schlimmer als
eines, das den Start verweigert.

| Variable | Pflicht | Bedeutung |
|----------|---------|-----------|
| `BASE_URL` | ja | Öffentliche Adresse, z. B. `https://dashboard.example.com`. Dient dem OIDC-Rücksprung und der Passkey-Kennung. |
| `OIDC_ISSUER` | ja | Der Anbieter, z. B. `https://id.example.com`. |
| `OIDC_CLIENT_ID` | ja | Beim Anbieter registrierte Client-Kennung. |
| `OIDC_CLIENT_SECRET` | ja | Client-Geheimnis. Nicht ins Image; `.env` oder eingehängtes Secret. |
| `OIDC_NAME` | nein | Name auf der Anmeldekarte. Vorgabe `Single Sign-On`. |
| `ADMIN_ROLE` | nein | Die OIDC-**Gruppe**, die zur Bearbeitungsrolle wird. Vorgabe `admin`. |
| `DATA_DIR` | nein | Inhalte, Logos, Hintergrundbilder. Vorgabe `/data`. |
| `DB_PATH` | nein | Sitzungen und Nutzer (SQLite). Vorgabe `/data/tinysesam.db`. |
| `HTTPS_MODE` | nein | `warn` hinter einem TLS-Proxy, `require` bei direktem HTTPS. |
| `TRUSTED_PROXIES` | nein | Kommaliste von CIDRs, deren `X-Forwarded-For` geglaubt wird. Die Vorgabe deckt localhost und das Docker-Bridge-Netz ab. |

## Der Anbieter

Genau diese Rücksprungadresse eintragen:

```
https://dashboard.example.com/auth/oidc/callback
```

TinySesam legt den Pfad fest. Ein falscher fällt erst **nach** der Anmeldung auf — ein
unangenehmer Ort, um einen Tippfehler zu entdecken.

Die Bereiche `openid profile email groups` anfordern. Erst der `groups`-Claim macht aus der
`ADMIN_ROLE`-Gruppe die Bearbeitungsrolle. Ohne ihn kann niemand bearbeiten.

## Reverse-Proxy

Die Anwendung spricht einfaches HTTP auf Port 8000 und erwartet TLS davor. uvicorn **nicht** mit
`--proxy-headers` starten: TinySesam liest `X-Forwarded-For` selbst, aber nur von
`TRUSTED_PROXIES`. Mit `--proxy-headers` wäre die Client-Adresse fälschbar.

Beispiel (Caddy):

```
dashboard.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

## Daten

Alles, was der Administrator ändert, landet in `$DATA_DIR/links.json` und wird atomar geschrieben
(daneben schreiben, dann umbenennen). Deshalb **nicht die Datei selbst einhängen**, sondern das
Verzeichnis. Logos liegen in `$DATA_DIR/icons`, Hintergrundbilder in `$DATA_DIR/backgrounds`.

Beim ersten Start wird das Verzeichnis aus dem Image befüllt und danach nie überschrieben. Ältere
Dateien werden beim Start an Ort und Stelle migriert.

## Sicherung

`links.json`, `icons/`, `backgrounds/` und `tinysesam.db` — mehr Zustand gibt es nicht. Die
Datenbank hält Sitzungen und Nutzer; geht sie verloren, sind alle abgemeldet, mehr nicht.
