# Sicherheitsrichtlinie

## Schwachstellen melden

Bitte vertraulich über GitHubs
[private Meldung](https://github.com/Ollornog/DashMyBoard/security/advisories/new) statt über ein
öffentliches Issue. Eine erste Antwort kommt binnen einer Woche.

## Umfang und Entwurfsentscheidungen, die man kennen sollte

- **Die Anmeldung ist ausgelagert** an [TinySesam](https://github.com/Ollornog/TinySesam) und den
  eigenen OIDC-Anbieter. DashMyBoard speichert keine Passwörter.
- **Ein lokaler TinySesam-Administrator erbt keine Rollen** (`admin_implies_roles=False`), und das
  Erst-Admin-Token ist abgeschaltet (`admin_claim_ttl_min=0`). `REQUIRED_CONFIG` lässt die
  Anwendung den Start verweigern, wenn eine TinySesam-Fassung diese Schalter nicht kennt — ein
  stilles Downgrade würde die Rechteprüfung schwächen, ohne dass man es sähe.
- **Schreibende Endpunkte verlangen die Administratorrolle und ein CSRF-Token.** Bei Upload-Routen
  läuft die Prüfung als FastAPI-Abhängigkeit, sonst bekäme ein Unangemeldeter `422` (Prüfung des
  Rumpfs) statt `401`.
- **`X-Forwarded-For` wird nur von `TRUSTED_PROXIES` geglaubt.** uvicorn nicht mit
  `--proxy-headers` starten; TinySesam wertet die Kopfzeile selbst aus, und nur für diese
  Gegenstellen.
- **Seiten, die eine Rolle nicht sehen darf, antworten mit `404`**, nicht mit `403` — ihre Existenz
  wird nicht verraten.
- **`GET /api/embeddable` ruft eine beliebige Adresse ab**, im Auftrag eines Administrators. Genau
  deshalb ist der Endpunkt Administratoren vorbehalten. Er ist eine bewusste, angemeldete Anfrage
  vom Server aus; die Administratorrolle sollte klein bleiben.
- **SVG-Uploads mit `<script>` werden abgelehnt.** Hochgeladene Dateien werden über einen eigenen
  statischen Pfad ausgeliefert, nie inline eingebettet.

## Nicht im Umfang

Überlastung durch einen Administrator, der sehr große Bilder hochlädt, und alles, was ein
Administrator von Natur aus darf (er kann einen Link überallhin zeigen lassen, auch auf interne
Hosts).

---

<p align="right">
<a href="../SECURITY.md">English</a> · <b>Deutsch</b><br>
<img src="../docs/logo.png" alt="DashMyBoard" width="60">
</p>
