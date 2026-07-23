---
id: ADR-1
type: Decision
title: Das Artefakt ist das Container-Abbild, nicht ein Paket
status: erledigt
tags: [release, container]
created: 2026-07-10
---

# ADR-1 — Abbild statt Paket

## Kontext

Für eine Python-Codebasis liegt nahe, Wheel und sdist zu bauen und auf PyPI zu veröffentlichen.

## Entscheidung

**Kein Wheel, kein sdist, kein PyPI.** Das Artefakt ist das **Container-Abbild**, gebaut aus dem
Git-Tag. `pyproject.toml` liefert bewusst kein Paket.

## Begründung

Dies ist eine **Anwendung, keine Bibliothek**. Niemand bindet sie in eigenen Code ein; sie wird
betrieben. Ein Paket würde eine Einbindungsform versprechen, die es nicht gibt.

## Konsequenzen

- **Kein `latest`-Tag.** Genau ein Abbild-Tag, gleich dem Git-Tag — ein wandernder Tag macht jeden
  Neustart zum Glücksspiel.
- **Kein Selbst-Update:** Die Anwendung lädt zur Laufzeit keinen Code nach. Der Pin steht beim
  Betreiber, nicht in der Software.
