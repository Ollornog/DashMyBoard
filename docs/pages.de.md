# Seiten, Reiter und die Grenzen der Einbettung

*[English version](pages.md)*

Seiten stehen in `links.json`, nicht im Code. Ein Administrator legt sie unter
**Einstellungen (Zahnrad) → Seiten** an.

## Die drei Arten

### Linktree (`links`)

Container, Gruppen, Einträge. Einträge lassen sich **dreimal verschachteln**; tiefer nimmt der
Server nichts an (`MAX_LINK_DEPTH`), und der Bearbeiten-Modus bietet eine zu tiefe Ablage gar
nicht erst an — beim Ziehen zählt die Höhe des mitgenommenen Astes.

Ein Eintrag ohne Adresse ist erlaubt: er wird zur Beschriftung, nicht zum Link. Adressen ohne
Schema bekommen `https://` vorangestellt; fremde Schemata (`javascript:`, `data:`) werden
abgelehnt.

### Reiter (`frames`)

Die Lesezeichenleiste wird zur Reiterleiste, der Inhalt lädt in einem `iframe`. Auf so einer Seite
gibt es keinen Inhalt zu bearbeiten, also erscheint auch kein Inhalts-Bleistift — editierbar sind
nur die Reiter selbst.

Je Seite legt man fest, welcher Reiter beim Aufruf lädt (*Startreiter*). Der offene Reiter steht
im Adress-Fragment (`#r=1`) und übersteht damit ein Neuladen.

### Eingebaut (`builtin`)

Eine mitgelieferte Ansicht: `news` und `status` (beides Attrappen, siehe `app/mockups.py`). Sie
lassen sich weder ändern noch löschen, nur umsortieren. Eine neue braucht ein Template und einen
Eintrag in `BUILTIN_VIEWS`.

Die Startseite (leere Adresse) und die eingebauten Seiten sind **gesperrt**: nur ihre Reihenfolge
ist änderbar.

## Rollen

Jede Seite, jeder Container, jeder Eintrag und jedes Lesezeichen kann ein `role` tragen. Nur
Mitglieder dieser OIDC-Gruppe sehen es. Eine Seite, die jemand nicht sehen darf, antwortet mit
`404` — ihre Existenz wird nicht verraten.

## Reservierte Adressen

`api`, `auth`, `static`, `icons`, `bg`, `healthz` gehören der Anwendung. Die generische Seitenroute
wird **zuletzt** registriert, sonst verschluckt sie diese Pfade.

## Warum sich der eigene Dienst meist nicht einbetten lässt

Gemessen an einem typischen selbst gehosteten Bestand:

| Dienst | Kopfzeile | Einbettbar |
|--------|-----------|------------|
| Identitätsanbieter (Pocket ID) | `X-Frame-Options: SAMEORIGIN` + `frame-ancestors 'none'` | nein |
| Nextcloud, Paperless, Rocket.Chat, Vaultwarden | `X-Frame-Options: SAMEORIGIN` | nein |
| AFFiNE, Immich | keine | ja |

`X-Frame-Options: SAMEORIGIN` heißt: nur Seiten auf der eigenen Domain des Dienstes dürfen ihn
rahmen. Das Dashboard ist eine andere Domain, also bleibt der Rahmen weiß. Das ist ein Schutz gegen
Clickjacking und lässt sich von außen nicht entfernen — die Kopfzeile im Proxy zu streichen würde
den Schutz nur für die eigenen Nutzer abschalten.

**Was wirklich funktioniert:**

- **Öffentliche Freigabelinks.** Viele Werkzeuge (Wikis, Boards, Fotoalben) können eine Seite ohne
  Anmeldung veröffentlichen. Die lassen sich meist problemlos einbetten.
- **Eigene Anwendungen**, bei denen man die Kopfzeilen selbst setzt.
- **Ein neuer Tab.** Jede Reiterleiste hat dafür einen Knopf, und DashMyBoard warnt schon beim
  Anlegen: `GET /api/embeddable?url=…` liest die Kopfzeilen des Ziels und sagt, was passieren wird.

Selbst wenn ein Dienst das Rahmen *erlaubt*, zeigt eine Seite mit Anmeldepflicht womöglich nur den
Anmeldebildschirm: Browser blockieren Drittanbieter-Cookies zunehmend, und das Sitzungs-Cookie der
eingebetteten Seite ist genau das. Öffentliche Freigabelinks umgehen das Problem vollständig.
