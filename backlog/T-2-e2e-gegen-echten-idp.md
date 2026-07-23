---
id: T-2
type: Task
title: End-to-End gegen einen echten Identitätsanbieter
status: offen
milestone: M-1
tags: [testing, oidc]
created: 2026-07-23
---

# T-2 — Echter OIDC-Fluss

Die Suite fährt mit **gefälschter Anmeldung**. Der echte Fluss — Rücksprung, Gruppen-Claim,
Abmeldung — ist damit nicht abgedeckt.

Gehört als **Smoke-Test hinter ein Deployment**, nicht in die CI: dort fehlen Domain, Zertifikat
und Anbieter. Ein Test, der das vortäuscht, prüft die Attrappe.
