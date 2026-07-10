#!/usr/bin/env bash
# Das Tor vor jedem Push: Fachtests + Browser-Test + Hygiene.
#
#   scripts/check.sh            # alles
#   scripts/check.sh --fast     # ohne Browser-Test (kurze Schleife)
#
# Der pre-push-Hook (.githooks/pre-push) ruft dieses Skript. Einmalig pro Klon:
#   git config core.hooksPath .githooks
set -euo pipefail

cd "$(dirname "$0")/.."
FAST=0
[[ "${1:-}" == "--fast" ]] && FAST=1

step() { printf '\n\033[1m▸ %s\033[0m\n' "$1"; }
fail() { printf '\n\033[31m✗ %s\033[0m\n' "$1" >&2; exit 1; }

# Einen Interpreter suchen, der die Anwendung auch importieren kann. Ohne das melden
# alle Suiten "FAIL", obwohl bloß eine Abhängigkeit im System-Python fehlt — das Tor
# blockte dann aus dem falschen Grund.
usable() { [[ -x "$1" ]] && "$1" -c "import fastapi, tinysesam" 2>/dev/null; }
PY=""
for cand in "${PYTHON:-}" .venv/bin/python "$(command -v python3 || true)"; do
    [[ -n "$cand" ]] && usable "$cand" && { PY="$cand"; break; }
done

if [[ -z "$PY" ]]; then
    command -v uv >/dev/null || fail "Kein Python mit fastapi+tinysesam und kein uv. → pip install -e '.[dev]'"
    step "Lege .venv an (einmalig)"
    uv venv .venv >/dev/null || fail "uv venv"
    # Interpreter explizit: `VIRTUAL_ENV=…` allein reicht uv nicht, wenn die Umgebung auf ein
    # systemweites Python zeigt.
    uv pip install -q --python .venv/bin/python -e ".[dev]" || fail "uv pip install"
    PY=".venv/bin/python"
fi
step "Interpreter: $("$PY" -c 'import sys; print(sys.executable)')"

if [[ $FAST -eq 1 ]]; then
    step "Suiten ohne Browser-Test (--fast)"
    "$PY" tests/run_all.py --no-browser || fail "Testsuite"
else
    step "Alle Suiten — Browser- und Hygiene-Test inklusive"
    "$PY" tests/run_all.py || fail "Testsuite"
fi

step "Beispieldaten sind gültiges JSON"
"$PY" -c "import json,sys; json.load(open('app/links.default.json'))" || fail "links.default.json"

printf '\n\033[32m✓ Alles grün\033[0m\n'
