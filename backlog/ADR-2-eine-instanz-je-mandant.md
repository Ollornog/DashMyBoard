---
id: ADR-2
type: Decision
title: Eine Instanz je Mandant statt Mandantentrennung im Code
status: erledigt
tags: [architektur, mandanten, sicherheit]
created: 2026-07-10
---

# ADR-2 — Eine Instanz je Mandant

## Kontext

Mehrere Mandanten könnten in einer Instanz laufen (Trennung über Datenmodell und Rechte) oder je
eine eigene Instanz bekommen.

## Entscheidung

**Eine Instanz je Mandant.** Mandantentrennung im Code wird bewusst nicht gebaut.

## Begründung

Keine Vermischung von Daten, Rechten und Uploads. Der entscheidende Satz: **ein Fehler trifft einen
Kunden, nicht alle.** Mandantentrennung im Code ist eine Sicherheitszusage, die man bei jeder neuen
Abfrage aufs Neue einlösen muss — ein vergessener Filter genügt.

## Konsequenzen

- Betrieb kostet mehr Instanzen; das ist der Preis und er ist bewusst gewählt.
- Multi-Site (mehrere Sites in einer Instanz) ist etwas anderes und bleibt möglich: gleiche Daten,
  verschiedene Aufmachung.
