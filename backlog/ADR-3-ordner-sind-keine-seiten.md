---
id: ADR-3
type: Decision
title: Ordner sind keine Seiten
status: erledigt
tags: [navigation, ux]
created: 2026-07-10
---

# ADR-3 — Ordner sind keine Seiten

## Entscheidung

Ordner haben **keine Adresse und keinen Inhalt**. Sie gruppieren, mehr nicht.

## Begründung

Sonst wäre unklar, was ein Klick auf den Ordner bedeutet — Inhalt anzeigen oder aufklappen? Jede
Oberfläche, die beides versucht, muss es an jeder Stelle neu erklären.

## Konsequenzen

- Verschachtelung tiefer als eine Ebene ist derzeit verboten. Erst bauen, wenn jemand sie vermisst:
  ein Menü aus Menüs ist eine Navigation, die niemand überblickt.
