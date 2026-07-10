"""Gemeinsames Rüstzeug der Suiten.

Grundsatz (verbindlich): **jede Suite ist wiederholbar.** Sie bringt ihr eigenes,
pro Lauf frisches Datenverzeichnis mit, startet die Dienste, die sie braucht, selbst
und räumt sie ab. Kein Zustand aus einem Lauf darf den nächsten beeinflussen — ein
Test, der beim zweiten Lauf rot wird, ist kaputt, nicht der Code.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"

# Umgebung, ohne die die Anwendung bewusst nicht startet.
BASE_ENV = {
    "OIDC_ISSUER": "https://id.example.com",
    "OIDC_CLIENT_ID": "test",
    "OIDC_CLIENT_SECRET": "test-secret",
    "ADMIN_ROLE": "admin",
}


def fresh_data_dir(prefix: str = "dmb-test-") -> Path:
    """Leeres Datenverzeichnis; die Anwendung befüllt es beim Start aus der Vorlage."""
    return Path(tempfile.mkdtemp(prefix=prefix))


def seed(data_dir: Path, links: dict | None = None) -> None:
    """Optional eigene links.json vorlegen (sonst greift die Erstbefüllung)."""
    if links is not None:
        (data_dir / "links.json").write_text(json.dumps(links, ensure_ascii=False), encoding="utf-8")


def import_app(data_dir: Path):
    """main.py importieren — der Import löst seed_data() aus."""
    os.environ.update(BASE_ENV, DATA_DIR=str(data_dir), DB_PATH=str(data_dir / "t.db"),
                      BASE_URL="https://dash.example.com")
    sys.path.insert(0, str(APP))
    import main  # noqa: PLC0415
    return main


class Server:
    """Die Anwendung auf einem freien Port, mit gefälschter Anmeldung.

    Der echte OIDC-Fluss braucht einen Identitätsanbieter; für Browser-Tests wird die
    Sitzung deshalb durch einen festen Administrator ersetzt (siehe _fakeauth.py).
    """

    def __init__(self, port: int = 8199) -> None:
        self.port = port
        self.data_dir = fresh_data_dir("dmb-server-")
        self.proc: subprocess.Popen | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self, timeout: float = 30.0) -> "Server":
        env = {**os.environ, **BASE_ENV,
               "DATA_DIR": str(self.data_dir),
               "DB_PATH": str(self.data_dir / "t.db"),
               "BASE_URL": self.url,
               "PYTHONPATH": f"{APP}:{ROOT / 'tests'}"}
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "_fakeauth:app",
             "--host", "127.0.0.1", "--port", str(self.port), "--log-level", "warning"],
            cwd=ROOT / "tests", env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                err = (self.proc.stderr.read() or b"").decode()[-1500:]
                raise RuntimeError(f"Server beendete sich sofort:\n{err}")
            try:
                with urllib.request.urlopen(f"{self.url}/healthz", timeout=1) as r:
                    if r.status == 200:
                        return self
            except (urllib.error.URLError, OSError):
                time.sleep(0.2)
        self.stop()
        raise RuntimeError("Server wurde nicht gesund")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.proc and self.proc.stderr:
            self.proc.stderr.close()
        shutil.rmtree(self.data_dir, ignore_errors=True)

    def __enter__(self) -> "Server":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()


def find_chrome() -> str | None:
    """CI-Falle: setup-chrome legt die Datei als `chrome` ab, nicht als `google-chrome`."""
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


class Report:
    """Kleine Bilanz — jede Suite meldet Exit 0/1."""

    def __init__(self, title: str) -> None:
        self.title = title
        self.ok = 0
        self.fail = 0
        self.skipped = 0
        print(f"\n{title}")

    def check(self, name: str, passed: bool, info: str = "") -> bool:
        if passed:
            self.ok += 1
            print(f"  ok   {name}", flush=True)
        else:
            self.fail += 1
            print(f"  FEHL {name}{': ' + info if info else ''}", flush=True)
        return passed

    def run(self, name: str, fn) -> None:
        try:
            fn()
            self.check(name, True)
        except Exception as exc:  # noqa: BLE001
            self.check(name, False, str(exc))

    def skip(self, name: str, why: str) -> None:
        self.skipped += 1
        print(f"  skip {name}: {why}", flush=True)

    def done(self) -> int:
        extra = f", {self.skipped} übersprungen" if self.skipped else ""
        print(f"\n{self.ok} ok, {self.fail} Fehler{extra}", flush=True)
        return 1 if self.fail else 0
