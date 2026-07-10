"""Browser-Test über das DevTools-Protokoll (CDP): prüft, was der Nutzer wirklich sieht.

Startet die Anwendung selbst (frisches Datenverzeichnis, gefälschte Anmeldung) und fährt
headless Chrome dagegen. Ohne Chrome wird die Suite übersprungen, nicht rot.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Report, Server, find_chrome  # noqa: E402

try:
    import websockets
except ImportError:  # pragma: no cover
    print("skip test_browser: websockets fehlt (pip install '.[dev]')")
    sys.exit(0)

CHROME = find_chrome()
if not CHROME:
    print("skip test_browser: kein Chrome gefunden")
    sys.exit(0)

r = Report("Browser-Test — Oberfläche")


class Page:
    def __init__(self, ws) -> None:
        self.ws = ws
        self.n = 0
        self.errors: list[str] = []

    async def send(self, method, **params):
        self.n += 1
        await self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("method") == "Runtime.exceptionThrown":
                detail = msg["params"]["exceptionDetails"]
                self.errors.append(detail.get("text", "") + " " +
                                   str(detail.get("exception", {}).get("description", "")))
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})

    async def js(self, expr):
        res = await self.send("Runtime.evaluate", expression=expr,
                              returnByValue=True, awaitPromise=True)
        if res.get("exceptionDetails"):
            raise RuntimeError(res["exceptionDetails"].get("text", "JS-Fehler") + ": " +
                               str(res["exceptionDetails"].get("exception", {}).get("description", "")))
        return res["result"].get("value")

    async def goto(self, url):
        await self.send("Page.navigate", url=url)
        for _ in range(80):
            await asyncio.sleep(0.1)
            if await self.js("document.readyState") == "complete":
                await asyncio.sleep(0.35)   # defer-Skripte
                return
        raise RuntimeError(f"Seite lädt nicht: {url}")


async def chrome_port(profile: Path, proc: subprocess.Popen, timeout: float = 30.0) -> int:
    """Port 0 lässt Chrome selbst wählen; er schreibt ihn in DevToolsActivePort.

    Ein fester Port kollidiert mit allem, was schon lauscht, und ein festes Profil-
    verzeichnis mit einem zweiten Lauf. Beides kostete einen roten CI-Job.
    """
    port_file = profile / "DevToolsActivePort"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Chrome beendete sich sofort (Code {proc.returncode})")
        if port_file.exists():
            first = port_file.read_text().splitlines()
            if first and first[0].strip().isdigit():
                return int(first[0])
        await asyncio.sleep(0.15)
    raise RuntimeError("Chrome schrieb keinen DevTools-Port")


async def run(base: str) -> None:
    profile = Path(tempfile.mkdtemp(prefix="dmb-chrome-"))
    chrome = subprocess.Popen(
        [CHROME, "--headless=new", "--remote-debugging-port=0", "--no-first-run",
         "--no-sandbox", "--disable-dev-shm-usage",   # Container haben ein winziges /dev/shm
         f"--user-data-dir={profile}", "--window-size=1400,900", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        port = await chrome_port(profile, chrome)

        ws_url = None
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2))
                ws_url = next(t["webSocketDebuggerUrl"] for t in targets if t["type"] == "page")
                break
            except Exception:  # noqa: BLE001
                await asyncio.sleep(0.2)
        if not ws_url:
            raise RuntimeError("Chrome antwortet nicht auf dem DevTools-Port")

        async with websockets.connect(ws_url, max_size=20_000_000) as ws:
            page = Page(ws)
            await page.send("Page.enable")
            await page.send("Runtime.enable")
            await page.goto(base + "/")

            # ---- Grundgerüst
            r.check("Startseite lädt", await page.js("!!document.querySelector('#tree')"))
            r.check("Titel steht in der Titelleiste",
                    await page.js("document.querySelector('.brand-title').textContent") == "DashMyBoard")
            r.check("Titel ist nicht inline editierbar",
                    await page.js("!document.querySelector('[data-edit=\"site-title\"]')"))
            r.check("Verschachtelungsgrenze kommt im Browser an", await page.js("window.GO_MAX_DEPTH") == 4)

            # ---- Rollen: Container mit role sind für Admins sichtbar
            r.check("rollenbeschränkter Container ist für Administratoren sichtbar",
                    await page.js("[...document.querySelectorAll('.sec-head h2')]"
                                  ".some(h => h.textContent === 'Infrastruktur')"))

            # ---- Bearbeiten-Modus: Zeile ist der Anker
            await page.js("document.querySelector('.pencil-float').click()")
            await asyncio.sleep(0.2)
            r.check("Inhalts-Modus an", await page.js("document.body.classList.contains('edit-content')"))
            r.check("Lesezeichen-Modus bleibt aus",
                    await page.js("!document.body.classList.contains('edit-marks')"))
            pad = await page.js("getComputedStyle(document.querySelector('.tile-row')).paddingLeft")
            r.check("Zeile greift über den Ziehgriff hinaus", pad == "20px", f"padding-left={pad}")
            r.check("Ziehgriff liegt innerhalb der Zeile",
                    await page.js("getComputedStyle(document.querySelector('.tile-row > .drag-handle')).left") == "4px")
            r.check("Punkt links in der Zeile gehört zur Zeile", await page.js("""
              (() => { const b = document.querySelector('.tile-row').getBoundingClientRect();
                       const el = document.elementFromPoint(b.left + 6, b.top + b.height/2);
                       return !!el && !!el.closest('.tile-row'); })()
            """))
            r.check("Kachel zeichnet keinen zweiten Kasten", await page.js("""
              (() => { const t = document.querySelector('.tile');
                       return getComputedStyle(t).borderTopColor === 'rgba(0, 0, 0, 0)'; })()
            """))
            r.check("Akzentstrich des Containers bleibt stehen", await page.js("""
              (() => { const h = document.querySelector('.sec-head');
                       return getComputedStyle(h).marginLeft === '0px'; })()
            """))
            await page.js("document.querySelector('.pencil-float').click()")
            await asyncio.sleep(0.1)

            # ---- Kopier-Knopf schwebt, statt Text zu verdrängen
            r.check("Kopier-Knopf ist absolut positioniert",
                    await page.js("getComputedStyle(document.querySelector('.copy')).position") == "absolute")

            # ---- Sonnen-Menü: nur Darstellung
            await page.js("document.querySelector('.menu [data-menu-btn]').click()")
            await asyncio.sleep(0.15)
            r.check("Sonnen-Menü öffnet", await page.js("!!document.querySelector('.menu.open')"))
            r.check("Sonnen-Menü hat genau zwei Zeilen",
                    await page.js("document.querySelectorAll('.menu-rows .menu-row').length") == 2)
            r.check("Einstellungen stehen nicht im Sonnen-Menü",
                    await page.js("!document.querySelector('.menu-panel [data-act=\"page-design\"]')"))
            await page.js("document.body.click()")
            await asyncio.sleep(0.1)

            # ---- Zahnrad → Einstellungen
            await page.js("document.querySelector('.who > [data-act=\"page-design\"]').click()")
            await asyncio.sleep(0.9)
            r.check("Zahnrad öffnet die Einstellungen", await page.js("!!document.querySelector('.drawer')"))
            r.check("Schublade heißt „Einstellungen“",
                    await page.js("document.querySelector('.drawer header h3').textContent") == "Einstellungen")
            tabs = await page.js("[...document.querySelectorAll('.tabs button')].map(b => b.textContent)")
            r.check("vier Reiter", tabs == ["Allgemein", "Seiten", "Hintergrund", "Transparenz"], str(tabs))

            # Die Schublade überdeckt nichts: die Seite wird als Ganzes verkleinert,
            # statt ihren Inhalt neu umzubrechen.
            r.check("Rumpf ist verkleinert, nicht eingerückt",
                    await page.js("getComputedStyle(document.body).paddingRight") == "0px")
            r.check("Maßstab liegt an", await page.js("""
              (() => { const t = getComputedStyle(document.getElementById('shell')).transform;
                       const m = t.match(/matrix\((\d?\.\d+)/);
                       return !!m && +m[1] > 0.5 && +m[1] < 1; })()
            """))
            r.check("Kopfzeile bleibt einzeilig", await page.js("""
              (() => { const bar = document.querySelector('.topbar');
                       return bar.getBoundingClientRect().height < 90; })()
            """))
            for sel, label in ((".topbar", "Titelleiste"), ("#bookmarks", "Lesezeichenleiste"), ("#tree", "Inhalt")):
                gap = await page.js(f"""
                  (() => {{ const a = document.querySelector('{sel}').getBoundingClientRect();
                            const d = document.querySelector('.drawer').getBoundingClientRect();
                            return Math.round(d.left - a.right); }})()
                """)
                r.check(f"{label} endet vor der Schublade", gap >= 0, f"Überlappung {-gap}px")

            # ---- Seitenverwaltung
            await page.js("document.querySelectorAll('.tabs button')[1].click()")
            await asyncio.sleep(0.25)
            rows = await page.js("[...document.querySelectorAll('.pagerow .pagename')].map(e => e.textContent)")
            r.check("Seitenliste zeigt alle Seiten", rows == ["Start", "News", "Status"], str(rows))
            r.check("gelieferte Seiten sind gesperrt",
                    await page.js("document.querySelectorAll('.pagelock').length") == 3)
            r.check("gesperrte Seiten haben keinen Bleistift",
                    await page.js("!document.querySelector('.pagerow .pageedit')"))
            r.check("Seiten lassen sich ziehen", await page.js("document.querySelector('.pagerow').draggable"))
            r.check("„+ Seite“ ist sichtbar", await page.js("!!document.querySelector('.drawer .add')?.offsetParent"))

            # Seite über den Dialog anlegen und speichern
            await page.js("document.querySelector('.drawer .add').click()")
            await asyncio.sleep(0.3)
            r.check("Dialog „Neue Seite“ öffnet",
                    await page.js("document.querySelector('.modal h3')?.textContent") == "Neue Seite")
            await page.js("""
              (() => { const f = document.querySelectorAll('.modal input[type=text]');
                       f[0].value = 'Team'; f[1].value = 'Team';
                       document.querySelector('.modal select').value = 'frames'; })()
            """)
            await page.js("document.querySelector('.modal .primary').click()")
            await asyncio.sleep(0.3)
            r.check("neue Seite steht in der Liste", await page.js(
                "[...document.querySelectorAll('.pagerow .pagename')].some(e => e.textContent === 'Team')"))
            r.check("Adresse wurde aus dem Titel gebildet",
                    await page.js("[...document.querySelectorAll('.pageslug')].pop().textContent") == "/team")
            r.check("neue Seite ist nicht gesperrt",
                    await page.js("document.querySelectorAll('.pagelock').length") == 3)

            await page.js("document.querySelector('[data-save]').click()")
            await asyncio.sleep(1.4)   # speichern + Neuaufbau
            r.check("neue Seite steht in der Navigation",
                    await page.js("[...document.querySelectorAll('.pagelink')].some(a => a.textContent === 'Team')"))
            r.check("nach dem Schließen ist der Maßstab wieder aufgehoben",
                    await page.js("getComputedStyle(document.getElementById('shell')).transform") == "none")

            # ---- Meldungen statt Browser-Kästen
            await page.js("window.goToast('Testfehler')")
            await asyncio.sleep(0.15)
            r.check("Fehler erscheint als Einblendung", await page.js("!!document.querySelector('#toasts .toast')"))
            r.check("Einblendung lässt sich wegklicken", await page.js("""
              (() => { document.querySelector('.toast-x').click();
                       return !document.querySelector('#toasts .toast'); })()
            """))
            r.check("kein alert/confirm im Skript", await page.js("""
              fetch('/static/admin.js').then(r => r.text())
                .then(t => !/[^a-zA-Z]alert\\(/.test(t) && !/[^a-zA-Z]confirm\\(/.test(t))
            """))

            # ---- Reiter-Seite: Lesezeichen werden Reiter, Inhalt landet im Rahmen
            csrf = "document.cookie.match(/tinysesam_csrf=([^;]+)/)[1]"
            status = await page.js("""
              (async () => {
                const m = await (await fetch('/api/links', {credentials:'same-origin'})).json();
                const team = m.pages.find(p => p.slug === 'team');
                team.start = '0';
                team.bookmarks = [{name:'Erster', url:'%s/healthz'},
                                  {name:'Zweiter', url:'%s/healthz?b=1'}];
                const res = await fetch('/api/links', {method:'PUT', credentials:'same-origin',
                  headers:{'Content-Type':'application/json','X-CSRF-Token': %s},
                  body: JSON.stringify(m)});
                return res.status;
              })()
            """ % (base, base, csrf))
            r.check("Reiter speichern wird angenommen", status == 200, f"HTTP {status}")

            embed = await page.js(
                "fetch('/api/embeddable?url=' + encodeURIComponent('%s/healthz'),"
                "{credentials:'same-origin'}).then(r => r.json())" % base)
            r.check("Einbettbarkeit wird geprüft", embed and embed.get("embeddable") is True, str(embed))

            await page.goto(base + "/team")
            r.check("Reiterleiste ist markiert",
                    await page.js("document.querySelector('#bookmarks').classList.contains('as-tabs')"))
            r.check("kein Inhalts-Bleistift auf Reiter-Seiten",
                    await page.js("!document.querySelector('.pencil-float')"))
            r.check("Reiter-Bleistift ist vorhanden", await page.js("!!document.querySelector('.pencil-inline')"))
            await asyncio.sleep(0.5)
            r.check("Startreiter ist geladen",
                    (await page.js("document.getElementById('frame').src") or "").endswith("/healthz"))
            r.check("Rahmen ist sichtbar", await page.js("!document.getElementById('frame').hidden"))
            r.check("offener Reiter ist hervorgehoben",
                    await page.js("document.querySelector('#bookmarks .bm.current .bm-label').textContent") == "Erster")

            await page.js("document.querySelectorAll('#bookmarks .bm-wrap a.bm')[1].click()")
            await asyncio.sleep(0.4)
            r.check("Klick lädt in den Rahmen, statt zu navigieren",
                    await page.js("location.pathname") == "/team")
            r.check("Fragment merkt sich den Reiter", await page.js("location.hash") == "#r=1")

            await page.goto(base + "/team#r=1")
            await asyncio.sleep(0.4)
            r.check("nach dem Neuladen ist derselbe Reiter offen",
                    (await page.js("document.getElementById('frame').src") or "").endswith("?b=1"))

            # ---- Eingebaute Seiten und Fehlerfall
            await page.goto(base + "/news")
            r.check("eingebaute Seite lädt", await page.js("!!document.querySelector('main')"))
            r.check("kein Inhalts-Bleistift auf eingebauten Seiten",
                    await page.js("!document.querySelector('.pencil-float')"))

            await page.goto(base + "/gibtsnicht")
            body = (await page.js("document.body.textContent")) or ""
            r.check("unbekannte Seite endet im Fehler", "404" in body or "nicht" in body.lower())

            r.check("keine unbehandelten JavaScript-Fehler", not page.errors, "; ".join(page.errors[:3]))
    finally:
        chrome.terminate()
        try:
            chrome.wait(timeout=10)
        except subprocess.TimeoutExpired:
            chrome.kill()
        shutil.rmtree(profile, ignore_errors=True)


with Server() as server:
    asyncio.run(run(server.url))

sys.exit(r.done())
