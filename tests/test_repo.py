"""Hygiene: was man beim Aufräumen vergisst, prüft eine Maschine besser.

Pflichtdateien, Versionsgleichstand, keine Artefakte, keine Geheimnisse — und
**keine persönlichen Namen**: kein eigener Host, keine eigene Domain, kein Kundenname.
Das Repo ist öffentlich; die Regel darf nicht am Vorsatz hängen.

Die allgemeinen Prüfungen und die Sperrlisten stehen in `tests/_kit/` — einer geteilten,
eingecheckten Basis, die `repokit sync` hierher schreibt. Sie ist stdlib-only und lädt zur
Testzeit nichts nach. Was hier steht, gilt nur für dieses Projekt.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Report  # noqa: E402
from _kit import hygiene  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
r = Report("Hygiene — Repo")

POLICY = hygiene.lade_policy()
PROJEKTE = ["TinySesam", "DashMyBoard"]

# Die geteilten Prüfungen arbeiten mit relativen Pfaden (Strings); die repo-eigenen
# Checks unten mit Path-Objekten. Beide Sichten auf dieselbe Liste.
DATEIEN = hygiene.getrackte_dateien(str(ROOT))
FILES = [ROOT / n for n in DATEIEN]


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
    "scripts/_residue_check.sh", "tests/_kit/hygiene.py",
    ".github/dependabot.yml",
    "CODE_OF_CONDUCT.md", "CODE_OF_CONDUCT.de.md",
]
for name in PFLICHT:
    r.check(f"{name} vorhanden", (ROOT / name).exists())

# ---- Keine private Infrastruktur (siehe docs/development.md)
#
# `admin@example.de` ist harmlos — `paperless.example.de` verrät, wo ein Paperless läuft.
#
# Muster und Sperrliste stehen in tests/_kit/hygiene_policy.json — einer Quelle für alle
# Repos. Vorher trug jedes Repo seine eigene Kopie, und sie liefen auseinander.
treffer = hygiene.pruefe_private_infrastruktur(str(ROOT), DATEIEN, POLICY, PROJEKTE)
r.check(f"keine private Infrastruktur ({len(POLICY['private_muster'])} Muster"
        f" + {len(POLICY['private_namen_sha256_16'])} Namen)",
        not treffer, " | ".join(sorted(set(treffer))[:4]))

# ---- Nur neutrale Beispieladressen
# dl.google.com lädt Chrome für den Browser-Test — nur hier nötig, nicht in der Policy.
adressen = hygiene.pruefe_adressen(str(ROOT), DATEIEN, POLICY,
                                   zusaetzliche_hosts=[r"dl\.google\.com", r"(www\.)?flaticon\.com", r"img\.shields\.io"])
r.check("nur neutrale Beispieladressen", not adressen, " | ".join(sorted(set(adressen))[:4]))

# ---- Version steht überall gleich
pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
version = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M).group(1)
versionsfehler = hygiene.pruefe_versionsgleichstand(str(ROOT))
r.check(f"Version {version}: pyproject, CHANGELOG und SemVer stimmen",
        not versionsfehler, " | ".join(versionsfehler))

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
# `pip install -e .` schreibt egg-info bei jedem Lauf neu — versioniert macht es die Suite
# unwiederholbar, und das fiel erst dem Rückstands-Check auf.
artefakte = hygiene.pruefe_artefakte(DATEIEN, POLICY)
r.check("keine generierten Artefakte versioniert", not artefakte, " | ".join(artefakte[:3]))

# Repo-eigen: dieses Projekt hat ein data/-Verzeichnis zur Laufzeit.
r.check("kein Datenverzeichnis versioniert", not [f for f in DATEIEN if f.startswith("data/")])
r.check("keine .env versioniert", not [f for f in DATEIEN if Path(f).name == ".env"])

lecks = hygiene.pruefe_geheimnisse(str(ROOT), DATEIEN, POLICY)
r.check("keine Geheimnisse im Klartext", not lecks, " | ".join(lecks[:3]))

# ---- Belegte Standards, maschinell erzwungen (context/repo-standards.md)
# Ein Tag lässt sich verschieben; ein Commit-SHA ist die einzige unveränderliche Referenz.
ungepinnt = hygiene.pruefe_actions_sha_gepinnt(str(ROOT), DATEIEN)
r.check("Actions per Commit-SHA gepinnt, nicht per Tag", not ungepinnt, " | ".join(ungepinnt[:3]))

# Es gibt keinen sicheren Default: die Ausgangsberechtigung kommt aus der Repo-Einstellung.
ohne_rechte = hygiene.pruefe_workflow_permissions(str(ROOT), DATEIEN)
r.check("jeder Workflow setzt `permissions:`", not ohne_rechte, " | ".join(ohne_rechte[:3]))

# Keep a Changelog 1.1.0 — fester Satz Kategorien, eine Sprache je Repo.
kategorien = hygiene.pruefe_changelog_kategorien(str(ROOT), POLICY)
r.check("CHANGELOG nutzt gültige Kategorien", not kategorien, " | ".join(kategorien[:2]))

# GitHub wählt die README nach ORT aus, nicht nach Sprache — eine Übersetzung veraltet still.
uebersetzung = hygiene.pruefe_uebersetzungs_struktur(str(ROOT), [("README.md", "README.de.md")])
r.check("README.de.md folgt der Struktur von README.md", not uebersetzung, " | ".join(uebersetzung[:2]))

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
