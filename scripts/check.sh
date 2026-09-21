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

# ── Ein gesetztes $PYTHON ist VERBINDLICH (2026-09-21) ────────────────────────
# `ci-local --matrix` fährt die Suite je Python-Version und setzt dafür $PYTHON.
# Bis heute stand die Variable nur als erster KANDIDAT in der Schleife unten —
# und wurde immer verworfen, weil `tinysesam` in den Matrix-venvs des Abbilds
# fehlt (es kommt per git-URL, gehört also bewusst nicht ins Abbild). Die Suite
# fiel dann in den uv-Zweig und lief dreimal auf derselben Version, während die
# Matrix-Bilanz drei grüne Beine meldete.
#
# Jetzt gilt: Fehlt im gewünschten Interpreter etwas, wird es DORT nachgerüstet
# — ausweichen wäre nur eine verlagerte Lüge. Das venv liegt außerhalb des Repos
# und wird nach dem Lauf entfernt, damit der zweite Lauf denselben Stand
# vorfindet (Wiederholbarkeit) und der Rückstands-Check nichts findet.
if [[ -n "${PYTHON:-}" ]]; then
    [[ -x "$PYTHON" ]] || fail "\$PYTHON zeigt auf '$PYTHON' — das ist nicht ausführbar"
    if usable "$PYTHON"; then
        PY="$PYTHON"
    else
        command -v uv >/dev/null \
            || fail "\$PYTHON=$PYTHON hat fastapi/tinysesam nicht, und uv fehlt zum Nachrüsten"
        step "Rüste $("$PYTHON" -V 2>&1) in einem eigenen venv aus"
        MATRIX_VENV="$(mktemp -d)"
        # shellcheck disable=SC2064  # Pfad jetzt einsetzen, nicht erst beim EXIT
        trap "rm -rf '$MATRIX_VENV'" EXIT
        uv venv --python "$PYTHON" "$MATRIX_VENV" >/dev/null || fail "uv venv (--python $PYTHON)"
        uv pip install -q --python "$MATRIX_VENV/bin/python" -e ".[dev]" \
            || fail "uv pip install für $PYTHON"
        PY="$MATRIX_VENV/bin/python"
        usable "$PY" || fail "Auch nach der Installation fehlt fastapi/tinysesam in $PYTHON"
    fi
else
    for cand in .venv/bin/python "$(command -v python3 || true)"; do
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
fi
# Die VERSION gehört in die Zeile, nicht nur der Pfad: bei einem Matrix-Lauf
# liegt der Interpreter in einem tmp-venv, dessen Name nichts über die Version
# sagt — und genau die ist die Zusage, die belegt werden soll.
step "Interpreter: $("$PY" -c 'import sys; print(sys.version.split()[0], "@", sys.executable)')"

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
