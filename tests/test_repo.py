"""Hygiene: was man beim Aufräumen vergisst, prüft eine Maschine besser.

Pflichtdateien, Versionsgleichstand, keine Artefakte, keine Geheimnisse — und
**keine persönlichen Namen**: kein eigener Host, keine eigene Domain, kein Kundenname.
Das Repo ist öffentlich; die Regel darf nicht am Vorsatz hängen.
"""
from __future__ import annotations

import hashlib
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
    "app/Dockerfile", ".dockerignore", "app/main.py", "app/links.default.json",
    "TODO.md", ".github/workflows/release.yml",
]
for name in PFLICHT:
    r.check(f"{name} vorhanden", (ROOT / name).exists())

# ---- Keine private Infrastruktur (siehe docs/development.md)
#
# `admin@example.de` ist harmlos — `paperless.example.de` verrät, wo ein Paperless läuft.
#
# Die Muster sind bewusst **generisch**. Eine wörtliche Verbotsliste („mein-server", „kunde-x")
# würde in einem öffentlichen Repo genau das veröffentlichen, was sie schützen soll. Für die
# Handvoll Eigennamen, die sich nicht generisch fassen lassen, steht deshalb nur der Anfang
# ihrer SHA256-Summe hier: der Wächter erkennt den Namen, verrät ihn aber nicht.
#
# Für Doku reservierte Werte bleiben erlaubt (RFC 2606: example.*; RFC 5737: 192.0.2.0/24,
# 198.51.100.0/24, 203.0.113.0/24) — sonst ließe sich die Regel nicht einmal erklären.
PRIVATE = (
    r"(?<![\w.])/home/[a-z_][a-z0-9_-]*",                       # Heimatverzeichnis des Betreibers
    r"\b[a-z0-9-]+\.(?!example\b)[a-z0-9-]{3,}\.(?:de|at|ch|eu)\b",   # Dienst-Subdomain
    r"\b10\.\d+\.\d+\.\d+(?!/)",                               # private Netze (ohne CIDR-Maske)
    r"\b192\.168\.\d+\.\d+(?!/)",
    r"\b172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+(?!/)",
    r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d+\.\d+",     # CGNAT / Overlay-Netz
    r"\bCT ?\d{3}\b",                                          # Container-Nummern
    r"[a-z0-9_-]+@pve![a-z0-9_-]+",                             # Hypervisor-API-Token
)

# Interne Hostnamen, Betreiber- und Kundennamen — nur als Prüfsumme, nie im Klartext.
PRIVATE_HASHED = frozenset((
    "e71b5222584b6528", "6bb8c80cfa0e95ae", "84ef0efe0a878ba1", "3a06e0b732af4a2e",
    "cb034381b0eee532", "41b8e6744905305f", "a994ffcab684f9e2", "e177ac5b0aa46203",
    "a227c36a926bd7f6", "252a8452a103b022", "5b41917ea3e5cd80", "3e2559984ba426c0",
    "061429fadd2701e3",
))

WORT = re.compile(r"[a-z][a-z0-9-]{3,}")
# Der Eigentümer-Pfad ist öffentlich und unvermeidlich — auf GitHub wie in der Registry.
# Identität (Konto, Repo) ist erlaubt; Infrastruktur (Hosts, Subdomains, private Netze) nicht.
ERLAUBT = re.compile(
    r"github\.com/[A-Za-z0-9-]+/(TinySesam|DashMyBoard)"
    r"|ghcr\.io/[a-z0-9-]+/[a-z0-9-]+"
    r"|GITHUB_REPOSITORY_OWNER|github\.repository_owner|OWNER_LC",
    re.IGNORECASE)
SELBST = Path(__file__).resolve()   # diese Datei führt die Muster, sie darf sie enthalten

treffer = []
for f, text in texts():
    if f.resolve() == SELBST:
        continue
    for i, line in enumerate(text.splitlines(), 1):
        sauber = ERLAUBT.sub("", line)
        for muster in PRIVATE:
            if re.search(muster, sauber, re.IGNORECASE):
                treffer.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()[:60]}")
        for wort in WORT.findall(sauber.lower()):
            if hashlib.sha256(wort.encode()).hexdigest()[:16] in PRIVATE_HASHED:
                treffer.append(f"{f.relative_to(ROOT)}:{i}: verbotener Name")
r.check(f"keine private Infrastruktur ({len(PRIVATE)} Muster + {len(PRIVATE_HASHED)} Namen)",
        not treffer, " | ".join(sorted(set(treffer))[:4]))

# ---- Nur neutrale Beispieladressen
adressen = []
URL = re.compile(r"https?://([a-z0-9.-]+)", re.IGNORECASE)
ERLAUBTE_HOSTS = re.compile(
    r"(^|\.)(example\.(com|org|net|de)|localhost|127\.0\.0\.1|github\.com|"
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

# ---- Beispiel-Pins sind Code: sie altern still, weil niemand sie ausführt
dockerfile = (ROOT / "app/Dockerfile").read_text(encoding="utf-8")
PIN = re.compile(r"TinySesam(?:\.git)?@(v\d+\.\d+\.\d+)")
pins = set(PIN.findall(dockerfile)) | set(PIN.findall(pyproject))
r.check("Dockerfile und pyproject pinnen dieselbe Auth-Version", len(pins) == 1, str(sorted(pins)))
r.check("kein ungepinnter Hauptzweig im Dockerfile", "@main" not in dockerfile and "@master" not in dockerfile)

# Beispiel-Tags in README und compose zeigen auf die aktuelle Version — sonst empfiehlt
# die Doku ein Abbild, das es nie gab.
BILD = re.compile(r"dashmyboard:v(\d+\.\d+\.\d+)")
for name in ("README.md", "README.de.md", "compose.example.yml"):
    gefunden = set(BILD.findall((ROOT / name).read_text(encoding="utf-8")))
    r.check(f"{name} pinnt v{version}", gefunden in ({version}, set()), str(sorted(gefunden)))

# ---- Das Endabbild lädt keinen Code nach
r.check("Abbild ist mehrstufig", dockerfile.count("FROM ") >= 2)
r.check("Endabbild entfernt pip", "pip uninstall" in dockerfile or "rm -f /usr/local/bin/pip" in dockerfile)
r.check("Abbild läuft nicht als root", re.search(r"^USER 1000", dockerfile, re.M) is not None)
r.check("Abbild hat einen HEALTHCHECK", "HEALTHCHECK" in dockerfile)

# ---- Release-Workflow: kein latest, Registry-Name kleingeschrieben
release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
r.check("Release-Workflow existiert", bool(release))
r.check("kein latest-Tag im Release", ":latest" not in release)
tags_zeile = [ln for ln in release.splitlines() if ln.strip().startswith("tags:")]
r.check("repository_owner steht nicht in der tags-Zeile",
        not any("repository_owner" in ln for ln in tags_zeile), str(tags_zeile))
r.check("Release prüft den Tag gegen die Paketversion", "Tag und Paketversion" in release)
r.check("Release nutzt gh release create --verify-tag", "--verify-tag" in release)

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
