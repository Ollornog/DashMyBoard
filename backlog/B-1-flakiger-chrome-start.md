---
id: B-1
type: Bug
title: "Browser-Test flakig: Chrome schreibt den DevTools-Port nicht rechtzeitig"
status: offen
milestone: M-1
tags: [tests, browser, ci, flaky]
created: 2026-09-23
---

# Chrome schreibt den DevTools-Port nicht rechtzeitig — und sagt nicht, warum

## Repro

Nicht deterministisch herstellbar; tritt auf einem **belasteten** GitHub-Runner auf. Beobachtet
am 2026-09-23 in PR #17 (Dependabot-Bump `actions/checkout`), Bein `tests (3.14)`:

```
RuntimeError: Chrome schrieb keinen DevTools-Port
  tests/test_browser.py, chrome_port, Zeile 89
```

**Wiederholung desselben Commits: grün.** Am Code lag es also nicht.

## Erwartet vs. tatsächlich

**Erwartet:** Die Suite ist wiederholbar — ein Test, der beim zweiten Lauf grün wird, ist kaputt,
nicht der Code. Ein zufälliges Rot erzieht dazu, rote Läufe zu wiederholen statt zu lesen, und
damit geht der Wert des Gates verloren.

**Tatsächlich:** Chrome lief noch (der Zweig `proc.poll() is not None` wurde nicht genommen, es
kam keine Meldung „beendete sich sofort"). Er hatte `DevToolsActivePort` innerhalb der Frist nur
noch nicht geschrieben.

## Zwei Mängel, nicht einer

1. **Das Zeitfenster ist zu knapp.** `chrome_port(..., timeout: float = 30.0)` in
   `tests/test_browser.py:73`. 30 s reichen auf einem ausgelasteten Runner nicht zuverlässig.

2. **Der Fehler ist nicht diagnostizierbar — und das ist der schwerere Mangel.** Chrome wird in
   `tests/test_browser.py:98` mit `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL`
   gestartet. Wenn der Start hakt, steht **nirgends warum**. Die Meldung sagt nur, dass etwas
   nicht kam, nie was Chrome dazu zu sagen hatte. Ein Fehler, den man nur wiederholen, aber nicht
   verstehen kann, kommt wieder.

## Was zu tun ist

Beides, in dieser Reihenfolge — und **Punkt 2 zuerst**, sonst behebt man den ersten blind:

- **`stderr` in eine Datei umlenken** statt nach `DEVNULL`, und ihren Inhalt in die
  `RuntimeError`-Meldung aufnehmen. Danach weiß der nächste Lauf, was los war.
- **Erst dann** das Zeitfenster anheben — mit der dann bekannten Ursache als Begründung, nicht
  als Rateschluss.

⚠️ **Nicht** einfach das Timeout hochdrehen und weitergehen. Das ist das Pflaster, das die
Ursache verdeckt: der Test wird seltener rot, ohne dass jemand weiß, warum er es war. Falls sich
herausstellt, dass Chrome unter Last regelmäßig länger braucht, ist ein höheres Fenster die
richtige Antwort — aber dann als Entscheidung mit Beleg.

## Fertig, wenn

- Ein fehlgeschlagener Chrome-Start nennt in der Testausgabe die Ursache aus Chromes eigener
  Fehlerausgabe.
- Zwei aufeinanderfolgende vollständige Läufe von `scripts/check.sh` sind grün (die Prüfung auf
  Wiederholbarkeit).
