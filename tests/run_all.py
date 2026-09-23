#!/usr/bin/env python3
"""Sammellauf: führt jede tests/test_*.py aus und meldet eine Bilanz.

  python tests/run_all.py                 # alles
  python tests/run_all.py --no-browser    # ohne Browser-Test (kurze Schleife)
  python tests/run_all.py --nur-hygiene   # Doku-Schnellpfad: alles, was ohne
                                          # die Anwendung läuft

Exit 0 nur, wenn jede Suite grün ist. Übersprungene Suiten (fehlender Chrome,
fehlendes websockets) sind kein Fehler.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
skip_browser = "--no-browser" in sys.argv
nur_hygiene = "--nur-hygiene" in sys.argv

# Suiten, die die ANWENDUNG brauchen (fastapi, tinysesam, Chrome) und daher im
# Doku-Schnellpfad wegfallen.
#
# Die Liste zählt auf, was WEGFÄLLT — nicht, was bleibt. Das ist die
# Fail-safe-Richtung: eine neu angelegte Suite ist damit automatisch im
# Schnellpfad DABEI. Wer sie hier zu ergänzen vergisst, macht den Schnellpfad
# langsamer oder (wenn sie die Anwendung braucht) laut rot — niemals stiller.
# Die umgekehrte Liste („was gehört zur Hygiene") hätte eine neue Prüfung still
# aus dem Schnellpfad gelassen, und niemand hätte es gemerkt.
BRAUCHT_APP = ("test_browser.py", "test_cookies.py", "test_data.py")

suiten = sorted(HERE.glob("test_*.py"))
if skip_browser:
    suiten = [s for s in suiten if s.name != "test_browser.py"]
if nur_hygiene:
    suiten = [s for s in suiten if s.name not in BRAUCHT_APP]

rot: list[str] = []
for suite in suiten:
    print(f"\n\033[1m▸ {suite.name}\033[0m", flush=True)
    code = subprocess.run([sys.executable, str(suite)], cwd=HERE.parent).returncode
    if code != 0:
        rot.append(suite.name)

print("\n" + "─" * 60)
if rot:
    print(f"\033[31m✗ {len(rot)} von {len(suiten)} Suiten rot: {', '.join(rot)}\033[0m")
    sys.exit(1)
print(f"\033[32m✓ {len(suiten)} Suiten grün\033[0m")
