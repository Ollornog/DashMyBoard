"""Der Doku-Schnellpfad der CI: Urteil, Verdrahtung, Fail-closed.

Bei einer Änderung, die AUSSCHLIESSLICH Doku berührt, lässt die CI die teuren
Schritte weg (Installation, Browser-Test, Abbild-Bau) und fährt nur die Hygiene.
Drei Dinge müssen dafür stimmen, und alle drei prüft diese Suite:

1. **Das Urteil.** `scripts/_nur_doku.sh` muss jede Dateiklasse richtig einordnen —
   und im Zweifel `false` sagen. Die Grenzen und ihre Begründung stehen im Skript;
   hier stehen die Fälle, die sie festhalten. Wer eine Grenze verschiebt, muss hier
   einen Fall dazuschreiben.
2. **Die Verdrahtung.** Ein Urteil, das kein Workflow liest, wirkt nicht. Geprüft
   wird nicht, ob die `if:`-Zeilen „da sind", sondern dass **jeder Schritt entweder
   in der Liste der immer laufenden steht oder am Urteil hängt** — ein neu
   hinzugefügter teurer Schritt ohne `if:` wird damit rot, statt still mitzulaufen.
3. **Der Hygiene-Pfad lässt keine Prüfung weg.** `run_all.py --nur-hygiene` nimmt
   nur Suiten heraus, die die Anwendung brauchen; die Hygiene-Suite selbst muss
   drin bleiben.

Warum das überhaupt eine Suite bekommt: Der Schnellpfad ist die einzige Stelle in
diesem Repo, an der eine Prüfung planmäßig NICHT läuft. Wenn dieses Urteil falsch
ist, fällt der Fachtest aus, ohne dass etwas rot wird.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Report  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SKRIPT = ROOT / "scripts/_nur_doku.sh"
WORKFLOW = ROOT / ".github/workflows/ci.yml"

r = Report("Doku-Schnellpfad der CI")


def urteil(dateien: list[str]) -> str:
    """Das Skript mit einer Dateiliste auf stdin befragen."""
    p = subprocess.run([str(SKRIPT)], input="\n".join(dateien), cwd=ROOT,
                       capture_output=True, text=True)
    if p.returncode != 0:
        return f"<exit {p.returncode}: {p.stderr.strip()}>"
    return p.stdout.strip()


# ---------------------------------------------------------------------------
# 1. Das Urteil
# ---------------------------------------------------------------------------
# Doku — darf den Schnellpfad nehmen, WEIL die Hygiene mitfährt.
DOKU = [
    "README.md",                       # Prosa
    "CHANGELOG.md",                    # Prosa; Versionsgleichstand prüft die Hygiene
    "TODO.md",
    "docs/configuration.md",
    "docs/logo.png",                   # Bild im Doku-Baum
    "i18n/README.de.md",
    "i18n/docs/pages.de.md",
    "backlog/M-1-durchstich-multi-site.md",
    "LICENSE",
    "app/README.md",                   # eine README bleibt Prosa, auch neben Code
]
for name in DOKU:
    r.check(f"Doku: {name}", urteil([name]) == "true")

# Keine Doku — volle Suite. Jeder Eintrag mit dem Grund, der im Skript steht.
CODE = [
    ("app/main.py", "Anwendungscode"),
    ("app/Dockerfile", "Bauanweisung"),
    ("app/links.default.json", "Beispieldaten, die ein Fachtest liest"),
    ("tests/test_repo.py", "die Prüfung selbst"),
    ("tests/_kit/hygiene.py", "die Prüfung selbst"),
    ("scripts/check.sh", "das Tor selbst"),
    ("scripts/_nur_doku.sh", "das Urteil selbst"),
    ("pyproject.toml", "Version, Abhängigkeiten, requires-python"),
    (".gitignore", "verschiebt, WAS der Test sieht"),
    (".gitattributes", "export-ignore nahm schon einmal .github/ aus der Dateiliste"),
    (".github/workflows/ci.yml", "die Prüfung selbst"),
    (".github/dependabot.yml", "Automatik, keine Prosa"),
    (".ci-image", "Steuerdatei der CI"),
    (".ci-allow-dirty", "Steuerdatei der CI"),
    (".env.example", "Konfigurationsbeispiel, das ein Test liest"),
    ("compose.example.yml", "Betriebsbeispiel mit gepinntem Abbild"),
]
for name, grund in CODE:
    r.check(f"kein Schnellpfad: {name} ({grund})", urteil([name]) == "false")

# Ein einziger Code-Treffer kippt den ganzen Satz.
r.check("gemischt (Doku + Code) ⇒ volle Suite",
        urteil(["README.md", "docs/pages.md", "app/main.py"]) == "false")
r.check("viel Doku, eine Zeile Code ⇒ volle Suite",
        urteil(["README.md", "CHANGELOG.md", "i18n/README.de.md", "pyproject.toml"]) == "false")
r.check("mehrere Doku-Dateien ⇒ Schnellpfad",
        urteil(["README.md", "i18n/README.de.md", "docs/pages.md"]) == "true")


# ---------------------------------------------------------------------------
# 2. Fail-closed: wer nicht weiß, fährt voll
# ---------------------------------------------------------------------------
r.check("leere Dateiliste ⇒ volle Suite", urteil([]) == "false")
r.check("nur Leerzeilen ⇒ volle Suite", urteil(["", "", ""]) == "false")


def seit(ref: str, ziel: str | None = None) -> str:
    argv = [str(SKRIPT), "--seit", ref] + ([ziel] if ziel else [])
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else f"<exit {p.returncode}>"


# Die vier Wege, auf denen GitHub keine brauchbare Basis liefert.
r.check("--seit '' (workflow_dispatch ohne Basis) ⇒ volle Suite", seit("") == "false")
r.check("--seit Null-SHA (erster Push eines Branches) ⇒ volle Suite",
        seit("0" * 40) == "false")
r.check("--seit unbekanntem Commit (flacher Klon, Force-Push) ⇒ volle Suite",
        seit("deadbeef" * 5) == "false")
r.check("--seit Unsinn ⇒ volle Suite und kein Abbruch", seit("kein-ref-1234") == "false")

# Gegen die echte Historie: HEAD gegen HEAD ist ein leerer Diff — nichts zu
# entscheiden, also voller Lauf. Belegt gleichzeitig, dass der git-Zweig überhaupt
# läuft und nicht bloß immer „false" sagt, weil er scheitert.
r.check("--seit HEAD (leerer Diff) ⇒ volle Suite", seit("HEAD") == "false")

# Der git-Zweig muss auch „true" sagen KÖNNEN. Ohne diesen Fall wäre „immer false,
# weil git scheitert" von einem funktionierenden Skript nicht zu unterscheiden —
# und alle Prüfungen darüber wären grün, ohne etwas zu belegen.
def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT,
                          capture_output=True, text=True).stdout


def _finde_commit(nur_doku: bool) -> str | None:
    """Ersten Commit der letzten 300 finden, dessen Diff (nur) Doku berührt."""
    for sha in _git("log", "-n", "300", "--format=%H", "--no-merges").split():
        dateien = [f for f in _git("diff", "--name-only", "--no-renames",
                                   f"{sha}~1", sha).splitlines() if f]
        if not dateien:
            continue
        ist = all(re.search(r"\.md$|^docs/|^i18n/|^backlog/|^LICENSE$", f) for f in dateien)
        if ist is nur_doku:
            return sha
    return None


_doku_commit = _finde_commit(nur_doku=True)
if _doku_commit:
    r.check("--seit gegen einen echten Doku-Commit ⇒ Schnellpfad",
            seit(f"{_doku_commit}~1", _doku_commit) == "true",
            f"Commit {_doku_commit[:8]}")
else:
    r.skip("--seit gegen echten Doku-Commit", "keiner in den letzten 300 Commits")

_code_commit = _finde_commit(nur_doku=False)
if _code_commit:
    r.check("--seit gegen einen echten Code-Commit ⇒ volle Suite",
            seit(f"{_code_commit}~1", _code_commit) == "false",
            f"Commit {_code_commit[:8]}")
else:
    r.skip("--seit gegen echten Code-Commit", "keiner in den letzten 300 Commits")

# Umbenennung — der gefährlichste Randfall, und der einzige, den man NUR durch
# Ausführen erwischt: git zeigt mit Umbenennungserkennung nur das ZIEL. Ohne
# `--no-renames` sähe `app/x.py` → `docs/x.py` wie eine reine Doku-Änderung aus,
# obwohl Code aus der Anwendung verschwindet.
#
# Geprüft wird im WEGWERF-REPO, nicht am Dateitext: Ein `"--no-renames" in text`
# bleibt grün, solange das Wort noch im Kommentar darüber steht — genau so hat
# diese Prüfung ihre erste Mutation überlebt.
def _umbenennungs_probe() -> str:
    import shutil
    import tempfile

    g = ["git", "-c", "user.email=t@example.com", "-c", "user.name=Test",
         "-c", "core.hooksPath=", "-c", "commit.gpgsign=false"]
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "scripts").mkdir()
        (tmp / "app").mkdir()
        shutil.copy2(SKRIPT, tmp / "scripts" / SKRIPT.name)
        (tmp / "app" / "x.py").write_text("print('code')\n", encoding="utf-8")
        subprocess.run([*g, "init", "-q"], cwd=tmp, check=True)
        subprocess.run([*g, "add", "-A"], cwd=tmp, check=True)
        subprocess.run([*g, "commit", "-qm", "start"], cwd=tmp, check=True)
        (tmp / "docs").mkdir()
        subprocess.run([*g, "mv", "app/x.py", "docs/x.py"], cwd=tmp, check=True)
        subprocess.run([*g, "commit", "-qm", "verschiebe Code nach docs/"], cwd=tmp, check=True)
        p = subprocess.run([str(tmp / "scripts" / SKRIPT.name), "--seit", "HEAD~1", "HEAD"],
                           cwd=tmp, capture_output=True, text=True)
        return p.stdout.strip() if p.returncode == 0 else f"<exit {p.returncode}: {p.stderr.strip()}>"


r.check("Code nach docs/ verschoben ⇒ volle Suite (Umbenennung täuscht nicht)",
        _umbenennungs_probe() == "false")


# ---------------------------------------------------------------------------
# 3. Die Verdrahtung im Workflow
# ---------------------------------------------------------------------------
# Grobparser für unsere Schreibweise: Jobs auf Einrückung 2, Schritte als
# '      - ' (6 Leerzeichen). Findet er nichts, ist der Anker weg — dann MUSS die
# Suite rot werden und eine neue Quelle verlangen, statt still durchzuwinken.
JOB = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
SCHRITT = re.compile(r"^      - ")


def schritte_je_job(text: str) -> dict[str, list[str]]:
    jobs: dict[str, list[str]] = {}
    job = None
    block: list[str] | None = None
    for line in text.splitlines():
        m = JOB.match(line)
        if m and not line.startswith("    "):
            job, block = m.group(1), None
            jobs[job] = []
            continue
        if job is None:
            continue
        if SCHRITT.match(line):
            block = [line]
            jobs[job].append("")
            jobs[job][-1] = line
            continue
        if block is not None and (line.startswith("        ") or not line.strip()):
            jobs[job][-1] += "\n" + line
            continue
        if line.strip() and not line.startswith("    "):
            job, block = None, None
    return jobs


WF = WORKFLOW.read_text(encoding="utf-8")
JOBS = schritte_je_job(WF)

# Dass der Parser trägt, ist Voraussetzung für alles darunter — erst prüfen.
r.check("Workflow-Parser findet die Jobs tests und image",
        {"tests", "image"} <= set(JOBS), str(sorted(JOBS)))
r.check("Workflow-Parser findet die Schritte des tests-Jobs (>= 6)",
        len(JOBS.get("tests", [])) >= 6, f"{len(JOBS.get('tests', []))} Schritte")

# Schritte, die IMMER laufen — mit Grund. Alles andere muss am Urteil hängen.
IMMER = {
    "actions/checkout": "ohne Klon gibt es nichts zu prüfen",
    "actions/setup-python": "kostet 0 s und benennt das Matrix-Bein",
    "Umfang der Änderung": "fällt das Urteil",
    "Vorher-Stand des Baums": "macht den Rückstands-Check entscheidbar",
    "Arbeitsverzeichnis ist unverändert geblieben": "Rückstands-Check gilt in jedem Pfad",
}
URTEIL = "steps.umfang.outputs.nur_doku"

ungebunden = []
for jobname, bloecke in JOBS.items():
    for b in bloecke:
        kennung = ""
        m = re.search(r"^      - (?:name|uses):\s*(.+)$", b, re.M)
        if m:
            kennung = m.group(1).split("#")[0].strip().strip('"\'')
        kurz = kennung.split("@")[0]
        if any(kurz.startswith(k) or kennung.startswith(k) for k in IMMER):
            continue
        if re.search(r"^\s+if:.*" + re.escape(URTEIL), b, re.M):
            continue
        ungebunden.append(f"{jobname}: {kennung or '<ohne Namen>'}")

r.check("jeder Schritt läuft entweder immer (begründet) oder hängt am Urteil",
        not ungebunden, " | ".join(ungebunden[:4]))

# Die drei teuren Schritte namentlich — der Test soll auch dann etwas sagen, wenn
# jemand die Liste IMMER erweitert, statt den Schritt zu binden.
for name in ("Chrome (nur für den Browser-Test)", "Abhängigkeiten",
             "Suite (Fach + Browser + Hygiene)", "Image bauen (nicht veröffentlichen)"):
    block = [b for bl in JOBS.values() for b in bl if f"- name: {name}" in b or f"name: {name}" in b]
    r.check(f"teurer Schritt hängt am Urteil: {name}",
            bool(block) and any(re.search(r"if:.*" + re.escape(URTEIL) + r"\s*!=\s*'true'", b) for b in block))

# ... und die Hygiene läuft im Schnellpfad WIRKLICH, nicht nur „nicht ausgeschlossen".
r.check("Hygiene-Schritt existiert und greift genau im Schnellpfad",
        any(re.search(r"if:.*" + re.escape(URTEIL) + r"\s*==\s*'true'", b)
            and "--nur-hygiene" in b
            for bl in JOBS.values() for b in bl))

# Der Diff braucht Historie; mit Tiefe 1 fällt der Schnellpfad immer auf voll zurück.
r.check("checkout holt die volle Historie (fetch-depth: 0)", "fetch-depth: 0" in WF)

# Das Skript wird tatsächlich gerufen — an genau den Stellen, die das Urteil brauchen.
r.check("Workflow ruft scripts/_nur_doku.sh", "_nur_doku.sh --seit" in WF)
r.check("Skript ist ausführbar", bool(SKRIPT.stat().st_mode & 0o111))


# ---------------------------------------------------------------------------
# 4. Der Hygiene-Pfad lässt keine Prüfung weg
# ---------------------------------------------------------------------------
RUN_ALL = (ROOT / "tests/run_all.py").read_text(encoding="utf-8")
r.check("run_all.py kennt --nur-hygiene", "--nur-hygiene" in RUN_ALL)
r.check("check.sh kennt --nur-hygiene",
        "--nur-hygiene" in (ROOT / "scripts/check.sh").read_text(encoding="utf-8"))

# Die Liste nennt, was WEGFÄLLT (Fail-safe-Richtung): eine neue Suite ist damit
# automatisch im Schnellpfad dabei.
_m = re.search(r"BRAUCHT_APP\s*=\s*\(([^)]*)\)", RUN_ALL, re.S)
r.check("run_all.py führt die Ausnahmeliste als BRAUCHT_APP", _m is not None)
raus = set(re.findall(r'"([^"]+)"', _m.group(1))) if _m else set()
vorhanden = {p.name for p in (ROOT / "tests").glob("test_*.py")}

r.check("jede Suite der Ausnahmeliste existiert wirklich",
        raus <= vorhanden, " | ".join(sorted(raus - vorhanden)))
r.check("die Hygiene-Suite ist NICHT ausgenommen", "test_repo.py" not in raus)
r.check("diese Suite ist NICHT ausgenommen", "test_doku_schnellpfad.py" not in raus)
r.check("der Schnellpfad lässt überhaupt etwas übrig", bool(vorhanden - raus),
        f"vorhanden={len(vorhanden)}, ausgenommen={len(raus)}")

# Gegenprobe durch AUSFÜHRUNG, nicht durch Lesen: der Schnellpfad muss die
# Hygiene-Suite nennen und die App-Suiten nicht.
#
# Der Marker bricht die Rekursion: run_all --nur-hygiene fährt DIESE Suite mit, die
# sonst wieder run_all aufrufen würde. Ohne ihn läuft das endlos.
if os.environ.get("SCHNELLPFAD_IM_UNTERLAUF") == "1":
    r.skip("Gegenprobe durch Ausführung", "läuft bereits im verschachtelten Lauf")
else:
    _p = subprocess.run([sys.executable, "tests/run_all.py", "--nur-hygiene"],
                        cwd=ROOT, capture_output=True, text=True,
                        env={**os.environ, "SCHNELLPFAD_IM_UNTERLAUF": "1"})
    r.check("--nur-hygiene läuft grün", _p.returncode == 0, _p.stdout[-300:])
    r.check("--nur-hygiene fährt die Hygiene-Suite", "test_repo.py" in _p.stdout)
    for name in sorted(raus):
        r.check(f"--nur-hygiene fährt {name} nicht", name not in _p.stdout)

sys.exit(r.done())
