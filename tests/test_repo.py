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
import subprocess  # noqa: E402
from _kit import backlog, hygiene, manifest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
r = Report("Hygiene — Repo")

POLICY = hygiene.lade_policy()
PROJEKTE = ["TinySesam", "DashMyBoard"]

# Die geteilten Prüfungen arbeiten mit relativen Pfaden (Strings); die repo-eigenen
# Checks unten mit Path-Objekten. Beide Sichten auf dieselbe Liste.
DATEIEN = hygiene.getrackte_dateien(str(ROOT))
FILES = [ROOT / n for n in DATEIEN]


# ---- Die gevendorte Testbasis ist unverändert
# Steht bewusst VOR allem anderen: jede folgende Prüfung kommt aus genau diesen Dateien.
# Wer hier in der Kopie nachbessert statt im Kit, schwächt den Wächter still — und genau
# das ist am 2026-09-21 passiert (derselbe Backlog-Fehler zweimal behoben, das zweite Mal
# von Hand auf main). Bis 2026-09-22 gab es die Prüfung nur als `repokit check` auf dem
# Tower; hier lief sie nie (repokit#9).
_kit_drift = manifest.pruefe(str(ROOT))
r.check(f"tests/_kit unverändert (Kit {manifest.version(str(ROOT))}; sonst: repokit sync .)",
        not _kit_drift, " | ".join(_kit_drift[:3]))

# ---- Sieht die Suite überhaupt alle Dateien? (Kit 0.14.0)
# Eine leere oder verkürzte Liste macht JEDE folgende Prüfung grün, ohne dass etwas
# geprüft wurde — `pruefe_geheimnisse([], …)` ist von "alles sauber" nicht zu
# unterscheiden. Der echte Fall war nicht leer: unter `ci-local` fehlte das ganze
# `.github/`, weil `.gitattributes` es per `export-ignore` aus `git archive` nimmt —
# ausgerechnet die Workflows, die unten auf SHA-Pins und `permissions:` geprüft werden.
_liste = hygiene.pruefe_dateiliste_plausibel(DATEIEN, root=str(ROOT))
r.check(f"Dateiliste ist vollständig ({len(DATEIEN)} Dateien)",
        not _liste, " | ".join(_liste[:3]))

# ---- Pflichtdateien (zweisprachig, wo es den Leser betrifft)
PFLICHT = [
    "README.md", "i18n/README.de.md", "LICENSE", "CHANGELOG.md",
    "CONTRIBUTING.md", "i18n/CONTRIBUTING.de.md", "SECURITY.md", "i18n/SECURITY.de.md",
    ".env.example", "compose.example.yml", "pyproject.toml", ".ci-image",
    "scripts/check.sh", ".githooks/pre-push", ".github/workflows/ci.yml",
    "docs/configuration.md", "i18n/docs/configuration.de.md",
    "docs/pages.md", "i18n/docs/pages.de.md",
    "app/Dockerfile", ".dockerignore", "app/main.py", "app/links.default.json",
    "TODO.md", ".github/workflows/release.yml",
    "scripts/_residue_check.sh", "tests/_kit/hygiene.py",
    "scripts/_backlog.py", "tests/_kit/backlog.py", "backlog/README-KONVENTION.md",
    "tests/_kit/manifest.py",
    ".github/dependabot.yml",
    "CODE_OF_CONDUCT.md", "i18n/CODE_OF_CONDUCT.de.md",
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

# ---- ... und keine blanken Hostnamen OHNE Schema davor (Kit 0.14.0)
# Die Prüfung darüber sieht nur URLs MIT `https://`; ein nacktes `firma.tld` fällt
# durch sie UND durch das Infrastruktur-Muster, das drei Namensteile verlangt. Genau so
# standen in einem öffentlichen Repo ein realer Firmenname und zwei registrierte
# Domains als Fixtures.
#
# Der Grundstock ist die von Hand DURCHGESEHENE und freigegebene Liste der Hosts, die
# hier schon stehen und in Ordnung sind — nicht automatisch erzeugt. Ab jetzt wird jede
# NEUE Adresse rot; wer eine aufnimmt, hat sie vorher angesehen.
_blank = hygiene.pruefe_blanke_adressen(str(ROOT), DATEIEN, POLICY,
                                        grundstock=["python.org", "devguide.python.org",
                                                    "flaticon.com", "ghcr.io"])
r.check("keine blanken fremden Hostnamen", not _blank, " | ".join(_blank[:3]))

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
for name in ("README.md", "i18n/README.de.md", "compose.example.yml"):
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
# Kommentare AUSNEHMEN, sonst verbietet die Pruefung, ihre eigene Regel zu erklaeren:
# der Hinweis "setup-qemu-action zieht per Vorgabe tonistiigi/binfmt:latest" machte sie
# rot (2026-09-22). Dieselbe Falle, die das Kit bei `self-hosted` schon geloest hat —
# eine Wortsuche im Zeilentext trifft den Kommentar mit, der die Regel begruendet.
_release_code = "\n".join(
    re.sub(r"(^|\s)#.*$", "", ln) for ln in release.splitlines())
r.check("kein latest-Tag im Release", ":latest" not in _release_code)
# Gegenprobe: die Pruefung muss einen ECHTEN Treffer weiterhin finden.
r.check("Selbsttest — ein echtes :latest im Code wuerde auffallen",
        ":latest" in "\n".join(re.sub(r"(^|\s)#.*$", "", ln)
                                for ln in ["  tags: ghcr.io/x/y:latest"]))
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

# EIGENE Härtung, kein belegter Standard (Kit 0.14.0) — GitHub empfiehlt
# `persist-credentials: false` nirgends ausdrücklich. Seit checkout@v6 liegt das Token
# in $RUNNER_TEMP statt in .git/config; es zählt damit weiter dort, wo nach dem
# Checkout fremder Code läuft (`pip install -e`, Dritt-Actions). Kein Job in diesem
# Repo pusht über die git-Credentials — deshalb gibt es null Ausnahmen.
_pc = hygiene.pruefe_persist_credentials(str(ROOT), DATEIEN)
r.check("jeder actions/checkout setzt `persist-credentials: false`",
        not _pc, " | ".join(_pc[:3]))

# Keep a Changelog 1.1.0 — fester Satz Kategorien, eine Sprache je Repo.
kategorien = hygiene.pruefe_changelog_kategorien(str(ROOT), POLICY)
r.check("CHANGELOG nutzt gültige Kategorien", not kategorien, " | ".join(kategorien[:2]))

# GitHub wählt die README nach ORT aus, nicht nach Sprache — eine Übersetzung veraltet still.
uebersetzung = hygiene.pruefe_uebersetzungs_struktur(str(ROOT), [("README.md", "i18n/README.de.md")])
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

# ---- Backlog: Struktur, Verweise, generierter Index
# Der Backlog gehoert zum Repo, also prueft ihn die Suite. Einer, der nur "meistens
# stimmt", wird nicht geglaubt — und dann nicht gepflegt.
for v in backlog.alle_pruefungen(str(ROOT)):
    r.check(f"Backlog: {v}", False)
r.check("Backlog hat Eintraege", bool(backlog.lade(str(ROOT))))
_idx = subprocess.run([sys.executable, "scripts/_backlog.py", "index", "--dry-run"],
                      cwd=ROOT, capture_output=True, text=True)
r.check("backlog/README.md ist aktuell (sonst: scripts/_backlog.py index)", _idx.returncode == 0)

# ---- Python-Matrix: EINE Quelle, mechanisch gehalten (Kit 0.12.0, 2026-09-22)
# Bis 2026-09-22 stand die Matrix an drei Stellen — im Abbild (/opt/ci-matrix), in
# dieser ci.yml und implizit in requires-python. Gemessen am 2026-09-21 waren alle
# drei VERSCHIEDEN; jede sah für sich richtig aus, zusammen war die Zusage "wir
# testen, was wir versprechen" unbelegt. Die Quelle ist jetzt
# tests/_kit/python_matrix.json, und diese drei Prüfungen halten alles daran.
#
# Die Prüffunktionen lagen seit dem Kit-Sync in tests/_kit/, wurden aber von
# KEINEM Repo aufgerufen — gefunden beim Nachzählen am 2026-09-22. Eine Prüfung,
# die niemand ruft, ist keine.
_mx = hygiene.pruefe_python_matrix(str(ROOT), DATEIEN)
r.check("ci.yml-Matrix entspricht der geführten Python-Matrix", not _mx, " | ".join(_mx[:3]))

_rp = hygiene.pruefe_requires_python(str(ROOT))
r.check("requires-python nennt die Untergrenze der Matrix", not _rp, " | ".join(_rp[:3]))

# Die Rolling-Regel MELDET, sie ändert nichts: sonst zöge ein Python-Release die
# Flotte ungefragt mit. Sie wird erst rot, wenn das Prüfdatum in der Quelle
# verstrichen ist (naechste_pruefung) — dann ist eine Entscheidung fällig.
_rr = hygiene.pruefe_python_matrix_regel()
r.check("geführte Matrix widerspricht der Rolling-Regel nicht", not _rr, " | ".join(_rr[:3]))

# ---- Was hier bis 2026-09-22 FEHLTE, obwohl das Kit es mitbrachte.
# Nachgezählt beim Bau des Aufruf-Wächters: von 17 ausgelieferten Prüfungen rief
# dieses Repo 12. Die fünf Fehlenden waren kein bewusster Verzicht — sie sind beim
# Wachsen der Datei nie nachgezogen worden, und nichts hat es gemerkt.

# Das Repo ist ÖFFENTLICH: ein self-hosted Runner liefe hier unter fremden Fork-PRs.
_sh = hygiene.pruefe_kein_self_hosted_runner(str(ROOT), DATEIEN)
r.check("kein self-hosted Runner im öffentlichen Repo", not _sh, " | ".join(_sh[:3]))

_pf = hygiene.pruefe_pflichtdateien(str(ROOT), [
    "README.md", "LICENSE", "CHANGELOG.md",
    "CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "SECURITY.md"])
r.check("Community-Dateien vollständig", not _pf, " | ".join(_pf[:3]))

_ex = hygiene.pruefe_ausfuehrbar(str(ROOT), [
    "scripts/check.sh", "scripts/_residue_check.sh"])
r.check("Skripte sind ausführbar", not _ex, " | ".join(_ex[:3]))

# Eine Suite, die run_all nicht einsammelt, läuft in der CI nie mit.
_ra = hygiene.pruefe_run_all_sammelt_automatisch(str(ROOT))
r.check("run_all.py findet die Suiten automatisch", not _ra, " | ".join(_ra[:3]))

# ---- cancel-in-progress darf auf dem Default-Branch nicht unbedingt greifen
# Gemessen, nicht befürchtet: DashMyBoard verlor am 2026-07-10 drei main-Läufe,
# paperlaiss am 2026-09-21 vier in 33 Sekunden.
_cip = hygiene.pruefe_kein_abbruch_auf_default_branch(str(ROOT), DATEIEN)
r.check("kein unbedingtes cancel-in-progress auf main", not _cip, " | ".join(_cip[:3]))

# ---- Der Wächter über den Wächtern (repokit 0.13.0)
# ---- Die Ausnahmen und die Policy selbst werden geprüft (Kit 0.17.x)
# Beide gegen dieselbe Falle: eine Ausnahme oder ein Vorgabewert, den niemand ansieht,
# verdeckt irgendwann den nächsten echten Befund. `belegstellen` ist hier leer — dieses
# Repo hat kein Zitatverzeichnis; der Aufruf steht trotzdem, damit ein späterer Eintrag
# geprüft wird, statt still zu gelten.
_beleg = hygiene.pruefe_belegstellen_eng(str(ROOT), DATEIEN, [])
r.check("Belegstellen-Muster treffen keinen Code", not _beleg, " | ".join(_beleg[:3]))
_tab = hygiene.pruefe_tabelle_vollstaendig()
r.check("jede Kit-Prüfung steht in genau einer Liste", not _tab, " | ".join(_tab[:3]))
_pk = hygiene.pruefe_policy_schluessel_gelesen(POLICY)
r.check("jeder Policy-Schlüssel wird gelesen", not _pk, " | ".join(_pk[:3]))

# ---- Nichts wird von Dritten nachgeladen (Kit 0.18.0, PO-Regel 2026-09-23)
# Die Trennlinie: ein Link ist eine Tür, ein `src` ist ein Bote, den wir ungefragt
# losschicken. Die Ausnahmeliste ist LEER und soll es bleiben — eine Freigabe für eine
# Stelle, die man beseitigen könnte, wäre keine Ausnahme, sondern eine Billigung.
_fremd = hygiene.pruefe_keine_fremdressourcen(str(ROOT), DATEIEN, POLICY)
r.check("nichts wird von Dritten nachgeladen", not _fremd, " | ".join(_fremd[:3]))

# ---- Wird jede Testdatei überhaupt gerufen? (Kit 0.21.0)
# Von AUSSEN gefragt: ein nicht verkabelter Hygiene-Test besteht seine eigene
# Aufruf-Prüfung dadurch, dass er schweigt. Autodiscovery (run_all+glob, pytest)
# erkennt die Prüfung und schweigt dann.
_td = hygiene.pruefe_testdateien_gerufen(str(ROOT))
r.check("jede Testdatei wird von einem Läufer gerufen", not _td, " | ".join(_td[:3]))

_ng = hygiene.pruefe_kit_prueffunktionen_gerufen(str(ROOT))
r.check("jede Kit-Prüfung wird gerufen oder ist begründet ausgenommen",
        not _ng, " | ".join(_ng[:3]))

sys.exit(r.done())
