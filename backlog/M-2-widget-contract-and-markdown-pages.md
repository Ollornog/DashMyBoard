---
type: Milestone
title: Widget contract and markdown pages
status: offen
id: M-2
created: '2026-11-22'
---
# M-2 — Widget contract and markdown pages

Widgets are URLs: a server-rendered HTML fragment behind /w/{type}/{id}, loaded via HTMX, with its own Cache-Control. Two entries, one contract: JSON dashboard pages and :::widget{...} directives in markdown pages create the same object. Done when a markdown page shows a live widget and the built-in widgets run through the contract. Migrated from the old framework plan (central wiki, written 2026-07-10), closed 2026-11-22. Status not re-verified against the code; check before starting.
