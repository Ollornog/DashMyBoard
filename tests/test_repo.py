"""Hygiene: was man beim Aufräumen vergisst, prüft eine Maschine besser.

Pflichtdateien, Versionsgleichstand, keine Artefakte, keine Geheimnisse — und
**keine persönlichen Namen**: kein eigener Host, keine eigene Domain, kein Kundenname.
Das Repo ist öffentlich; die Regel darf nicht am Vorsatz hängen.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Report  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
r = Report("Hygiene — Repo")


def tracked() -> list[Path]:
    """Nur versionierte Dateien; alles andere geht das Repo nichts an."""
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [ROOT / n for n in out.stdout.decode().split("\0") if n]


FILES = tracked()
TEXT = {".py", ".js", ".css", ".html", ".md", ".json", ".yml", ".yaml", ".toml", ".sh", ".example", ""}


def texts():
    for f in FILES:
        if f.suffix.lower() in TEXT and f.is_file():
            try:
                yield f, f.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue


# ---- Pflichtdateien (zweisprachig, wo es den Leser betrifft)
PFLICHT = [
    "README.md", "README.de.md", "LICENSE", "CHANGELOG.md",
    "CONTRIBUTING.md", "CONTRIBUTING.de.md", "SECURITY.md", "SECURITY.de.md",
    ".env.example", "compose.example.yml", "pyproject.toml", ".ci-image",
    "scripts/check.sh", ".githooks/pre-push", ".github/workflows/ci.yml",
    "docs/configuration.md", "docs/configuration.de.md",
    "docs/pages.md", "docs/pages.de.md",
    "app/Dockerfile", "app/main.py", "app/links.default.json",
]
for name in PFLICHT:
    r.check(f"{name} vorhanden", (ROOT / name).exists())

# ---- Keine persönlichen Namen (CLAUDE.md-Regel, siehe docs/development.md)
# Eigene Hosts, Domains und Kundennamen. Produktnamen (Pocket ID, NetBird, Nextcloud …)
# sind erlaubt — sie verraten keine Topologie.
VERBOTEN = re.compile(
    r"ollornog\.(de|com)|drog-tower|\bdrog\b|specdoor|brunpower|"
    r"\bhetz\b|backmox|rasbox|paperlaiss|chatwisme|\bloco\b|\bbp-(gw|cloud|stage)\b",
    re.IGNORECASE)
# Ausnahme: die Bezugsquelle von TinySesam und der Repo-Pfad selbst.
ERLAUBT = re.compile(r"github\.com/Ollornog/(TinySesam|DashMyBoard)", re.IGNORECASE)

SELBST = Path(__file__).resolve()   # diese Datei führt die Wortliste, sie darf sie enthalten

treffer = []
for f, text in texts():
    if f.resolve() == SELBST:
        continue
    for i, line in enumerate(text.splitlines(), 1):
        if VERBOTEN.search(ERLAUBT.sub("", line)):
            treffer.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()[:70]}")
r.check("keine persönlichen Namen (Hosts, Domains, Kunden)", not treffer,
        " | ".join(treffer[:4]))

# ---- Keine echten Beispieladressen außer example.com/.org/localhost
adressen = []
URL = re.compile(r"https?://([a-z0-9.-]+)", re.IGNORECASE)
ERLAUBTE_HOSTS = re.compile(
    r"(^|\.)(example\.(com|org|net)|localhost|127\.0\.0\.1|github\.com|"
    r"keepachangelog\.com|semver\.org|www\.w3\.org|dl\.google\.com)$", re.IGNORECASE)
for f, text in texts():
    if f.resolve() == SELBST:
        continue
    for host in URL.findall(text):
        # Regex-Literale im Frontend enthalten "https?://" ohne echten Host.
        if "." not in host or not re.search(r"[a-z]", host, re.IGNORECASE):
            continue
        if not ERLAUBTE_HOSTS.search(host):
            adressen.append(f"{f.relative_to(ROOT)}: {host}")
r.check("nur neutrale Beispieladressen", not adressen, " | ".join(sorted(set(adressen))[:4]))

# ---- Version steht überall gleich
pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
version = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M).group(1)
changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
r.check(f"CHANGELOG kennt Version {version}", f"[{version}]" in changelog or f"## {version}" in changelog)

# ---- Keine Artefakte, keine Geheimnisse
r.check("keine .pyc/__pycache__ versioniert",
        not [f for f in FILES if "__pycache__" in f.parts or f.suffix == ".pyc"])
r.check("kein Datenverzeichnis versioniert", not [f for f in FILES if f.parts[len(ROOT.parts)] == "data"]
        if any(f.parts[len(ROOT.parts):] for f in FILES) else True)
r.check("keine .env versioniert", not [f for f in FILES if f.name == ".env"])

GEHEIM = re.compile(r"(client_secret|password|token|api[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9/+_-]{16,}",
                    re.IGNORECASE)
lecks = [f"{f.relative_to(ROOT)}" for f, t in texts() if GEHEIM.search(t)]
r.check("keine Geheimnisse im Klartext", not lecks, " | ".join(lecks[:3]))

# ---- Anwendungscode: keine vergessenen Ausgaben
prints = []
for f in [f for f in FILES if f.suffix == ".py" and f.parts[len(ROOT.parts)] == "app"]:
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if re.match(r"\s*print\(", line):
            prints.append(f"{f.relative_to(ROOT)}:{i}")
r.check("kein vergessenes print() in app/", not prints, " | ".join(prints[:3]))

# ---- Konfiguration kommt aus der Umgebung, nicht aus Vorgabewerten
main = (ROOT / "app/main.py").read_text(encoding="utf-8")
r.check("BASE_URL hat keinen Vorgabewert", 'os.environ["BASE_URL"]' in main)
r.check("OIDC_ISSUER hat keinen Vorgabewert", 'os.environ["OIDC_ISSUER"]' in main)
r.check("Rechteprüfung bleibt hart (admin_implies_roles)", "admin_implies_roles=False" in main)
r.check("Fail-Fast auf sicherheitsrelevante Felder", "REQUIRED_CONFIG" in main)

# ---- Jede Suite läuft im Sammellauf mit
run_all = (ROOT / "tests/run_all.py").read_text(encoding="utf-8")
suiten = sorted(p.name for p in (ROOT / "tests").glob("test_*.py"))
r.check("run_all.py findet die Suiten automatisch", "glob(" in run_all or "iterdir" in run_all,
        f"Suiten: {suiten}")

# ---- Ausführbarkeit
r.check("scripts/check.sh ist ausführbar", (ROOT / "scripts/check.sh").stat().st_mode & 0o111)
r.check(".githooks/pre-push ist ausführbar", (ROOT / ".githooks/pre-push").stat().st_mode & 0o111)

sys.exit(r.done())
