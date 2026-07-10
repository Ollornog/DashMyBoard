/* Bearbeiten-Modus der Intranet-Startseite (nur Rolle "hoheit").

   Texte werden direkt auf der Seite geändert (contenteditable, Speichern beim Verlassen).
   Sortiert wird per Ziehen; Adresse/Logo/Abzeichen und Startzustände liegen im ✎-Dialog.
   Strukturänderungen schreiben die ganze links.json zurück und laden neu — so können
   Ansicht und Datei nicht auseinanderlaufen. Reine Textänderungen sparen den Neuaufbau.

   Einträge und Lesezeichen sind Bäume; beide werden über Pfade adressiert ("1.0" =
   erster Untereintrag des zweiten Eintrags). Lesezeichen gehören je einer Seite. */
(function () {
  "use strict";

  var EDIT_KEY = "dmb-editing";         // gemerkt: welche Bereiche waren offen
  var DEFAULT_LOGO = "logo";
  var PAGE = window.GO_PAGE || "";
  var body = document.body;
  var pencils = document.querySelectorAll("[data-edit-scope]");
  if (!pencils.length) return;

  /* Zwei Bereiche mit eigenem Bleistift: "content" (Container, Gruppen, Einträge)
     und "marks" (Lesezeichenleiste). Sie lassen sich unabhängig ein- und ausschalten. */
  var SCOPES = ["content", "marks"];

  function on(scope) { return body.classList.contains("edit-" + scope); }

  /** Zu welchem Bereich gehört ein Element? */
  function scopeOf(el) {
    return el.closest("#bookmarks") ? "marks" : "content";
  }

  // ---------------------------------------------------------------- Meldungen

  /* Fehler und Bestätigungen laufen über eigene Einblendungen — die Kästen des
     Browsers (alert/confirm) halten das Skript an und passen nicht zur Seite. */

  /** Einblendung unten rechts; kommt aus ui.js, das vor dieser Datei geladen wird.
      kind: "error" (bleibt bis zum Klick) oder "ok" (verschwindet von selbst). */
  function toast(message, kind) {
    return window.goToast(message, kind);
  }

  /** Rückfrage vor dem Löschen. Liefert ein Versprechen auf true/false. */
  function askConfirm(question, confirmLabel) {
    return new Promise(function (resolve) {
      var back = document.createElement("div");
      back.className = "modal-back";
      var box = document.createElement("div");
      box.className = "modal modal-ask";
      box.innerHTML = "<h3></h3><p></p>";
      box.querySelector("h3").textContent = "Bitte bestätigen";
      box.querySelector("p").textContent = question;

      var actions = document.createElement("div");
      actions.className = "modal-actions";
      actions.innerHTML = '<span class="spacer"></span>' +
                          '<button type="button" class="ghost" data-no>Abbrechen</button>' +
                          '<button type="button" class="danger" data-yes></button>';
      actions.querySelector("[data-yes]").textContent = confirmLabel || "Löschen";
      box.appendChild(actions);

      function done(answer) { back.remove(); resolve(answer); }
      actions.querySelector("[data-no]").addEventListener("click", function () { done(false); });
      actions.querySelector("[data-yes]").addEventListener("click", function () { done(true); });
      back.addEventListener("mousedown", function (e) { if (e.target === back) done(false); });
      document.addEventListener("keydown", function esc(e) {
        if (e.key === "Escape") { document.removeEventListener("keydown", esc); done(false); }
      });

      back.appendChild(box);
      document.body.appendChild(back);
      actions.querySelector("[data-yes]").focus();
    });
  }

  // ---------------------------------------------------------------- Transport

  function csrf() {
    var m = document.cookie.match(/(?:^|;\s*)tinysesam_csrf=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  /** Die Antwort des Servers lesbar machen: {"detail":"…"} → "…". */
  async function problem(response, prefix) {
    var text = "";
    try { text = await response.text(); } catch (e) {}
    try {
      var body = JSON.parse(text);
      if (body && typeof body.detail === "string") text = body.detail;
    } catch (e) {}
    if (!text) text = "Fehler " + response.status;
    return prefix ? prefix + ": " + text : text;
  }

  async function loadModel() {
    var r = await fetch("/api/links", { credentials: "same-origin" });
    if (!r.ok) throw new Error(await problem(r, "Laden fehlgeschlagen"));
    return r.json();
  }

  async function saveModel(model) {
    var r = await fetch("/api/links", {
      method: "PUT",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
      body: JSON.stringify(model),
    });
    if (!r.ok) throw new Error(await problem(r, "Speichern fehlgeschlagen"));
  }

  /** Ändern + speichern + Seite neu aufbauen (Struktur, Reihenfolge, Löschen). */
  async function mutate(fn) {
    try {
      var model = await loadModel();
      if (fn(model) === false) return;
      await saveModel(model);
      rememberScopes();
      // Die eigene Seite kann gerade gelöscht worden sein — dann führt reload() ins 404.
      var alive = (model.pages || []).some(function (pg) { return (pg.slug || "") === PAGE; });
      if (alive) location.reload();
      else location.assign("/");
    } catch (err) { toast(err.message); }
  }

  /** Ändern + speichern, ohne neu zu laden. Liefert true, wenn es geklappt hat. */
  async function patch(fn) {
    try {
      var model = await loadModel();
      if (fn(model) === false) return false;
      await saveModel(model);
      return true;
    } catch (err) {
      toast(err.message);
      return false;
    }
  }

  /** Nur lesen — für Dialoge, die aktuelle Werte vorbelegen. */
  async function withModel(fn) {
    try { fn(await loadModel()); } catch (err) { toast(err.message); }
  }

  /** "wiki.example.com" → "https://wiki.example.com"; fremde Schemata gibt es nicht.
      Liefert null, wenn die Adresse unbrauchbar ist (javascript:, data:, …). */
  function normalizeUrl(url) {
    var u = (url || "").trim();
    if (!u) return "";
    if (/^https?:\/\//i.test(u)) return u;
    if (/^[a-z][a-z0-9+.-]*:/i.test(u)) return null;
    return "https://" + u;
  }

  /** Leere Werte nicht als "" ins JSON schreiben. */
  function put(obj, key, value) {
    if (value === "" || value === false || value == null) delete obj[key];
    else obj[key] = value;
  }

  /** Die Seite, auf der wir gerade stehen (Seiten sind eine geordnete Liste). */
  function pageCfg(model) {
    var pages = model.pages || (model.pages = []);
    for (var i = 0; i < pages.length; i++) {
      if ((pages[i].slug || "") === PAGE) return pages[i];
    }
    throw new Error("Diese Seite steht nicht mehr in den Daten — bitte neu laden.");
  }

  // ---------------------------------------------------------------- Adressierung

  function bmRoot(model) {
    var page = pageCfg(model);
    return page.bookmarks || (page.bookmarks = []);
  }

  /** Pfad "0.2.1" in einer verschachtelten Liste → { list, index }. */
  function slotIn(root, path) {
    var parts = String(path).split(".").map(Number);
    var list = root;
    for (var i = 0; i < parts.length - 1; i++) list = list[parts[i]].children;
    return { list: list, index: parts[parts.length - 1] };
  }

  function nodeIn(root, path) {
    var s = slotIn(root, path);
    return s.list[s.index];
  }

  function sections(model) {
    var page = pageCfg(model);
    return page.sections || (page.sections = []);
  }

  function linkRoot(model, c) { return sections(model)[c.s].groups[c.g].links; }

  function ctx(el) {
    var sec = el.closest("[data-sec]"), grp = el.closest("[data-grp]");
    var link = el.closest("[data-lpath]"), bm = el.closest("[data-path]");
    return {
      s: sec ? +sec.dataset.sec : -1,
      g: grp ? +grp.dataset.grp : -1,
      lpath: link ? link.dataset.lpath : null,
      path: bm ? bm.dataset.path : null,
    };
  }

  /** Zielpfad korrigieren, nachdem die Quelle entfernt wurde.

     Betroffen ist die Ebene, auf der die Quelle lag: liegt sie im selben Ast und davor,
     rutscht dort alles um eins nach vorn — auch wenn das Ziel tiefer sitzt.
     Beispiel: Quelle "0" entfernt → aus Ziel "1.0" wird "0.0". Ohne das greift slotIn()
     ins Leere ("Cannot read properties of undefined"). */
  function adjust(target, source) {
    var t = String(target).split(".").map(Number);
    var s = String(source).split(".").map(Number);
    var level = s.length - 1;
    if (t.length > level
        && s.slice(0, level).join() === t.slice(0, level).join()
        && s[level] < t[level]) {
      t[level] -= 1;
    }
    return t.join(".");
  }

  /** Knoten herausnehmen; ein leer gewordenes children-Feld verschwindet mit. */
  function takeOut(root, path) {
    var slot = slotIn(root, path);
    var node = slot.list.splice(slot.index, 1)[0];
    var parts = String(path).split(".");
    if (parts.length > 1 && slot.list.length === 0) {
      delete nodeIn(root, parts.slice(0, -1).join(".")).children;
    }
    return node;
  }

  // ---------------------------------------------------------------- Modus

  function setEditing(scope, active) {
    // Bewusst keine gemeinsame "editing"-Klasse: sie hatte im Lesezeichen-Modus auch
    // den Inhalt gesperrt (Titel klappten nicht mehr).
    body.classList.toggle("edit-" + scope, active);

    pencils.forEach(function (btn) {
      if (btn.dataset.editScope !== scope) return;
      // Der Knopf trägt ein SVG — nur Zustand und Beschriftung ändern, nicht den Inhalt.
      btn.setAttribute("aria-pressed", String(active));
      btn.title = active ? "Fertig" : (scope === "marks" ? "Lesezeichen bearbeiten" : "Inhalt bearbeiten");
      btn.setAttribute("aria-label", btn.title);
    });

    // Texte werden NICHT dauerhaft freigeschaltet: sonst fängt der Browser über ihnen
    // eine Textauswahl an und der Zug beginnt nie. Ein einfacher Klick schaltet sie frei.
    if (!active) {
      document.querySelectorAll("[data-edit]").forEach(function (el) {
        if (scopeOf(el) === scope) el.contentEditable = "false";
      });
    }

    document.querySelectorAll(".sec, .grp, .tile-wrap, .bm-wrap, .bm-folder").forEach(function (el) {
      if (scopeOf(el) !== scope) return;
      el.draggable = active;
    });

    // Links sind von Haus aus ziehbar — sonst zöge der Browser die Adresse statt der Kachel.
    document.querySelectorAll("a.tile, a.bm").forEach(function (a) {
      if (scopeOf(a) === scope) a.draggable = !active;
    });

  }

  /** Meldung, die einen Neuaufbau überleben soll (mutate lädt die Seite neu). */
  var TOAST_KEY = "dmb-toast";

  function toastAfterReload(message) {
    try { sessionStorage.setItem(TOAST_KEY, message); } catch (e) {}
  }

  try {
    var pending = sessionStorage.getItem(TOAST_KEY);
    sessionStorage.removeItem(TOAST_KEY);
    if (pending) toast(pending);
  } catch (e) {}

  /** Kann der Dienst überhaupt eingebettet werden? Sonst bliebe der Reiter leer. */
  async function warnIfNotEmbeddable(url) {
    if (window.GO_PAGE_TYPE !== "frames" || !url) return;
    try {
      var r = await fetch("/api/embeddable?url=" + encodeURIComponent(url), { credentials: "same-origin" });
      if (!r.ok) return;
      var verdict = await r.json();
      if (verdict.embeddable === false) {
        toastAfterReload(verdict.reason + " — dieser Reiter bleibt leer. Der Knopf rechts in der "
                         + "Leiste öffnet ihn in einem neuen Tab.");
      }
    } catch (e) {}   // Prüfung ist Komfort, kein Tor
  }

  /** Vor einem selbst ausgelösten Neuaufbau die offenen Bereiche merken. */
  function rememberScopes() {
    try { sessionStorage.setItem(EDIT_KEY, SCOPES.filter(on).join(",")); } catch (e) {}
  }

  pencils.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var scope = btn.dataset.editScope;
      setEditing(scope, !on(scope));
    });
  });

  /* Nur ein Neuaufbau durch eine eigene Änderung stellt die Modi wieder her — ein
     normales Neuladen oder ein Seitenwechsel beginnt sauber im Lesemodus. Sonst blieb
     ein einmal geöffneter Inhalts-Modus dauerhaft an. */
  try {
    var saved = sessionStorage.getItem(EDIT_KEY);
    sessionStorage.removeItem(EDIT_KEY);
    (saved || "").split(",").forEach(function (scope) {
      if (SCOPES.indexOf(scope) >= 0) setEditing(scope, true);
    });
  } catch (e) {}

  // Im Bearbeiten-Modus darf ein Klick auf eine Kachel nicht navigieren — er öffnet
  // stattdessen den Dialog (das übernimmt der [data-act]-Handler weiter unten).
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest("a.tile, a.bm");
    if (a && on(scopeOf(a))) ev.preventDefault();
  }, true);

  // ---------------------------------------------------------------- Texte inline

  // Titel und Untertitel der Anwendung stehen in der Schublade, nicht auf der Seite.
  var FIELDS = {
    "sec-title": function (m, c, v) { sections(m)[c.s].title = v; },
    "sec-subtitle": function (m, c, v) { put(sections(m)[c.s], "subtitle", v); },
    "grp-label": function (m, c, v) { put(sections(m)[c.s].groups[c.g], "label", v); },
    "link-name": function (m, c, v) { nodeIn(linkRoot(m, c), c.lpath).name = v; },
    "link-desc": function (m, c, v) { put(nodeIn(linkRoot(m, c), c.lpath), "desc", v); },
    "link-url": function (m, c, v) { put(nodeIn(linkRoot(m, c), c.lpath), "url", v); },
    "bm-name": function (m, c, v) { nodeIn(bmRoot(m), c.path).name = v; },
  };

  /* Ein Klick (ohne Ziehen) schaltet das Feld frei und setzt den Cursor an die Klickstelle.
     Beim Verlassen wird es wieder gesperrt, damit die Zeile weiter ziehbar bleibt. */
  var pendingField = null, downX = 0, downY = 0;

  document.addEventListener("mousedown", function (ev) {
    var f = ev.target.closest("[data-edit]");
    pendingField = (f && on(scopeOf(f)) && !f.isContentEditable) ? f : null;
    downX = ev.clientX; downY = ev.clientY;
  });

  document.addEventListener("mouseup", function (ev) {
    var f = pendingField;
    pendingField = null;
    if (!f) return;
    if (Math.abs(ev.clientX - downX) > 4 || Math.abs(ev.clientY - downY) > 4) return;  // gezogen

    f.contentEditable = "plaintext-only";
    f.focus();
    var range = document.caretRangeFromPoint && document.caretRangeFromPoint(ev.clientX, ev.clientY);
    if (range) {
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    }
  });

  document.querySelectorAll("[data-edit]").forEach(function (el) {
    var before = el.textContent.trim();

    el.addEventListener("focus", function () { before = el.textContent.trim(); });

    el.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") { ev.preventDefault(); el.blur(); }
      if (ev.key === "Escape") { el.textContent = before; el.blur(); }
    });

    el.addEventListener("blur", function () {
      var value = el.textContent.trim();
      if (value === before || !on(scopeOf(el))) return;
      var field = el.dataset.edit;
      if (!value && /title$|name$/.test(field)) { el.textContent = before; return; } // Pflichtfeld
      if (field === "link-url" && value) {
        var fixed = normalizeUrl(value);
        if (!fixed) {
          toast("Diese Adresse ist nicht erlaubt — nur http:// und https://.");
          el.textContent = before;
          return;
        }
        value = fixed;
        el.textContent = value;   // ergänztes Schema sofort zeigen
      }
      var c = ctx(el);
      // Die Adresse entscheidet, ob die Kachel ein Link ist — dann muss neu gerendert werden.
      var rebuild = field === "link-url" && (!value || !before);
      (rebuild ? mutate : patch)(function (m) { FIELDS[field](m, c, value); });
      before = value;
    });

    el.addEventListener("blur", function () { el.contentEditable = "false"; });
  });

  // ---------------------------------------------------------------- Ziehen & Ablegen

  var dragged = null;

  function describe(el) {
    if (el.classList.contains("sec")) return { kind: "sec", s: +el.dataset.sec };
    if (el.classList.contains("grp")) {
      var c = ctx(el);
      return { kind: "grp", s: c.s, g: c.g };
    }
    if (el.classList.contains("tile-wrap")) {
      var c2 = ctx(el);
      return { kind: "link", s: c2.s, g: c2.g, lpath: c2.lpath };
    }
    return { kind: "bm", path: el.dataset.path };
  }

  /* Der Server nimmt Einträge nur bis GO_MAX_DEPTH Ebenen an. Wir bieten tiefere
     Ablagen gar nicht erst an: Wer einen Ast mit Untereinträgen zieht, braucht so
     viele Ebenen, wie der Ast hoch ist. */
  var MAX_DEPTH = window.GO_MAX_DEPTH || 4;

  function subtreeHeight(el) {
    var box = el.querySelector(":scope > .sublinks");
    if (!box) return 1;
    var height = 1;
    box.querySelectorAll(":scope > .tile-wrap").forEach(function (kid) {
      height = Math.max(height, 1 + subtreeHeight(kid));
    });
    return height;
  }

  function depthOf(path) { return String(path).split(".").length; }

  /** Passt der gezogene Ast, wenn seine Wurzel auf dieser Ebene landet? */
  function fits(depth) {
    return dragged.kind !== "link" || depth + (dragged.height || 1) - 1 <= MAX_DEPTH;
  }

  document.addEventListener("dragstart", function (ev) {
    var el = ev.target.closest(".sec, .grp, .tile-wrap, .bm-wrap, .bm-folder");
    if (!el || !on(scopeOf(el))) return;
    ev.stopPropagation();
    dragged = describe(el);
    dragged.el = el;
    dragged.height = el.classList.contains("tile-wrap") ? subtreeHeight(el) : 1;
    el.classList.add("dragging");
    ev.dataTransfer.effectAllowed = "move";
    ev.dataTransfer.setData("text/plain", dragged.kind);
  });

  document.addEventListener("dragend", function () {
    if (dragged && dragged.el) dragged.el.classList.remove("dragging");
    clearMarks();
    dragged = null;
  });

  function clearMarks() {
    document.querySelectorAll(".drop-before, .drop-after, .drop-into, .drop-x").forEach(function (el) {
      el.classList.remove("drop-before", "drop-after", "drop-into", "drop-x");
    });
  }

  /** Passendes Ziel unter dem Cursor. "into" = hineinlegen (Untereintrag/Ordner). */
  function targetFor(ev) {
    if (!dragged) return null;
    var sel = { sec: ".sec", grp: ".grp", link: ".tile-wrap", bm: ".bm-wrap, .bm-folder" }[dragged.kind];
    var over = ev.target.closest(sel);

    if (over && over !== dragged.el && !dragged.el.contains(over)) {
      // Bei Einträgen misst nur die Zeile — die Untereinträge gehören nicht zum Ziel.
      var ref = over.querySelector(":scope > .tile-row") || over;
      var box = ref.getBoundingClientRect();
      // Lesezeichen in der Leiste liegen nebeneinander, alles andere untereinander.
      var horizontal = dragged.kind === "bm" && !over.closest(".bm-menu");
      var size = horizontal ? box.width : box.height;
      var offset = horizontal ? ev.clientX - box.left : ev.clientY - box.top;

      // Drittel: oben davor · Mitte untergeordnet · unten danach.
      // Zu tief wird nicht angeboten — dann bleibt nur davor/danach auf gleicher Ebene.
      var nestable = dragged.kind === "bm"
        ? over.classList.contains("bm-folder")
        : fits(depthOf(over.dataset.lpath) + 1);
      if (nestable && offset > size / 3 && offset < size * 2 / 3) {
        return { el: over, pos: "into", horizontal: horizontal };
      }
      if (dragged.kind === "link" && !fits(depthOf(over.dataset.lpath))) return null;
      var pos = offset < size / 2 ? "before" : "after";

      // Zwischen zwei Nachbarn gibt es nur EINEN Spalt — also auch nur eine Linie:
      // "davor" wird zum "danach" des Vorgängers (außer beim ersten Element).
      if (pos === "before") {
        var prev = over.previousElementSibling;
        if (prev && prev.matches(sel) && prev !== dragged.el) {
          return { el: prev, pos: "after", horizontal: horizontal };
        }
      }
      return { el: over, pos: pos, horizontal: horizontal };
    }

    // Leere Container: ans Ende anhängen
    var empty = { link: ".links", grp: ".sec-body", bm: ".bm-menu, #bookmarks" }[dragged.kind];
    if (empty) {
      var cont = ev.target.closest(empty);
      if (cont && !dragged.el.contains(cont)) return { el: cont, pos: "append" };
    }
    return null;
  }

  document.addEventListener("dragover", function (ev) {
    if (!dragged) return;
    var t = targetFor(ev);
    clearMarks();
    if (!t) return;
    ev.preventDefault();
    ev.dataTransfer.dropEffect = "move";
    if (t.pos === "append") return;
    t.el.classList.add("drop-" + t.pos);
    if (t.horizontal) t.el.classList.add("drop-x");
  });

  document.addEventListener("drop", function (ev) {
    if (!dragged) return;
    var t = targetFor(ev);
    if (!t) return;
    ev.preventDefault();
    var src = dragged, dstEl = t.el, pos = t.pos;
    clearMarks();

    // Erst das Modell ändern und speichern, dann das DOM nachziehen — kein Neuladen.
    patch(function (m) {
      if (src.kind === "sec") {
        var secs = sections(m);
        var node = secs.splice(src.s, 1)[0];
        var to = +dstEl.dataset.sec;
        if (src.s < to) to--;
        secs.splice(pos === "after" ? to + 1 : to, 0, node);
        return;
      }

      if (src.kind === "grp") {
        var secs2 = sections(m);
        var g = secs2[src.s].groups.splice(src.g, 1)[0];
        if (pos === "append") {
          secs2[+dstEl.closest("[data-sec]").dataset.sec].groups.push(g);
          return;
        }
        var ds = +dstEl.closest("[data-sec]").dataset.sec;
        var dg = +dstEl.dataset.grp;
        if (ds === src.s && src.g < dg) dg--;
        secs2[ds].groups.splice(pos === "after" ? dg + 1 : dg, 0, g);
        return;
      }

      if (src.kind === "link") {
        var link = takeOut(linkRoot(m, src), src.lpath);

        if (pos === "append") {
          var gEl = dstEl.closest("[data-grp]");
          linkRoot(m, { s: +gEl.closest("[data-sec]").dataset.sec, g: +gEl.dataset.grp }).push(link);
          return;
        }

        var tc = { s: +dstEl.closest("[data-sec]").dataset.sec, g: +dstEl.closest("[data-grp]").dataset.grp };
        var dstRoot = linkRoot(m, tc);
        var sameList = tc.s === src.s && tc.g === src.g;
        var tpath = sameList ? adjust(dstEl.dataset.lpath, src.lpath) : dstEl.dataset.lpath;

        if (pos === "into") {
          var parent = nodeIn(dstRoot, tpath);
          (parent.children || (parent.children = [])).push(link);
          return;
        }
        var slot = slotIn(dstRoot, tpath);
        slot.list.splice(pos === "after" ? slot.index + 1 : slot.index, 0, link);
        return;
      }

      // Lesezeichen
      var root = bmRoot(m);
      var node2 = takeOut(root, src.path);

      if (pos === "append") {
        var folderEl = dstEl.closest(".bm-folder");
        // Auch hier kann sich der Ordner-Pfad durch das Entfernen verschoben haben.
        (folderEl ? nodeIn(root, adjust(folderEl.dataset.path, src.path)).children : root).push(node2);
        return;
      }
      var bpath = adjust(dstEl.dataset.path, src.path);
      if (pos === "into") {
        var target = nodeIn(root, bpath);
        (target.children || (target.children = [])).push(node2);
        return;
      }
      var bslot = slotIn(root, bpath);
      bslot.list.splice(pos === "after" ? bslot.index + 1 : bslot.index, 0, node2);
    }).then(function (ok) {
      // Nur wenn gespeichert wurde — sonst zeigte die Seite etwas, das nicht in der Datei steht.
      if (ok) moveInDom(src.el, dstEl, pos, src.kind);
      else { rememberScopes(); location.reload(); }
    });
  });

  // ---------------------------------------------------------------- DOM nachziehen

  /* Nach einem Zug wird das Element im DOM umgehängt und alle Pfade neu vergeben —
     dann muss die Seite nicht neu laden. Modell und Ansicht folgen denselben Regeln:
     die Reihenfolge im DOM ist die Reihenfolge im JSON. */

  function ensureSublinks(tileWrap) {
    var box = tileWrap.querySelector(":scope > .sublinks");
    if (!box) {
      box = document.createElement("div");
      box.className = "sublinks";
      tileWrap.appendChild(box);
    }
    if (!tileWrap.querySelector(":scope > .tile-row > .caret-btn")) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "caret-btn";
      btn.dataset.act = "toggle";
      btn.setAttribute("aria-expanded", "true");
      btn.title = "Auf-/zuklappen";
      btn.innerHTML = '<span class="caret" aria-hidden="true">▾</span>';
      tileWrap.querySelector(":scope > .tile-row").appendChild(btn);
    }
    return box;
  }

  /** Ein Eintrag ohne Kinder braucht weder Klappbox noch Pfeil. */
  function tidySublinks(tileWrap) {
    if (!tileWrap) return;
    var box = tileWrap.querySelector(":scope > .sublinks");
    if (box && !box.querySelector(":scope > .tile-wrap")) {
      box.remove();
      var caret = tileWrap.querySelector(":scope > .tile-row > .caret-btn");
      if (caret) caret.remove();
      tileWrap.classList.remove("collapsed");
    }
  }

  function ensureMenu(folder) {
    return folder.querySelector(":scope > .bm-menu");
  }

  /** Pfade und Klapp-Schlüssel neu vergeben (Reihenfolge = Wahrheit). */
  function reindex() {
    var tree = document.getElementById("tree");
    if (tree) {
      tree.querySelectorAll(":scope > .sec").forEach(function (sec, si) {
        sec.dataset.sec = si;
        var seckey = "sec-" + (sec.dataset.id || si);
        sec.dataset.key = seckey;

        sec.querySelectorAll(":scope > .sec-body > .grp").forEach(function (grp, gi) {
          grp.dataset.grp = gi;
          var grpkey = seckey + "-grp-" + gi;
          grp.dataset.key = grpkey;

          (function walk(container, prefix) {
            container.querySelectorAll(":scope > .tile-wrap").forEach(function (tile, li) {
              var path = prefix ? prefix + "." + li : String(li);
              tile.dataset.lpath = path;
              tile.dataset.key = grpkey + "-l" + path;
              var sub = tile.querySelector(":scope > .sublinks");
              if (sub) walk(sub, path);
            });
          })(grp.querySelector(":scope > .grp-body > .links"), "");
        });
      });
    }

    var marks = document.getElementById("bookmarks");
    if (marks) {
      (function walk(container, prefix) {
        container.querySelectorAll(":scope > .bm-wrap, :scope > .bm-folder").forEach(function (el, i) {
          var path = prefix ? prefix + "." + i : String(i);
          el.dataset.path = path;
          var menu = el.querySelector(":scope > .bm-menu");
          if (menu) walk(menu, path);
        });
      })(marks, "");
    }
  }

  /** Das gezogene Element an seinen neuen Platz im DOM setzen. */
  function moveInDom(srcEl, dstEl, pos, kind) {
    var oldParentTile = srcEl.closest(".sublinks") ? srcEl.parentElement.closest(".tile-wrap") : null;

    if (pos === "before") dstEl.before(srcEl);
    else if (pos === "after") dstEl.after(srcEl);
    else if (pos === "into") {
      if (kind === "link") ensureSublinks(dstEl).appendChild(srcEl);
      else {
        var menu = ensureMenu(dstEl);
        var add = menu.querySelector(":scope > .add");
        add ? menu.insertBefore(srcEl, add) : menu.appendChild(srcEl);
      }
    } else if (pos === "append") {
      if (kind === "link") dstEl.appendChild(srcEl);
      else if (kind === "grp") dstEl.insertBefore(srcEl, dstEl.querySelector(":scope > .add"));
      else {
        var end = dstEl.querySelector(":scope > .add");
        end ? dstEl.insertBefore(srcEl, end) : dstEl.appendChild(srcEl);
      }
    }

    if (kind === "link") {
      tidySublinks(oldParentTile);
      if (pos === "into") ensureSublinks(dstEl);
    }
    reindex();
  }

  // ---------------------------------------------------------------- Dialog

  function dialog(title, fields, onSubmit, onDelete) {
    var back = document.createElement("div");
    back.className = "modal-back";
    var box = document.createElement("form");
    box.className = "modal";
    box.innerHTML = "<h3></h3>";
    box.querySelector("h3").textContent = title;

    var inputs = {};
    fields.forEach(function (f) {
      var row = document.createElement("label");
      row.className = "field";
      var cap = document.createElement("span");
      cap.textContent = f.label;
      row.appendChild(cap);

      var el;
      if (f.type === "select") {
        el = document.createElement("select");
        f.options.forEach(function (o) {
          var opt = document.createElement("option");
          opt.value = o.value; opt.textContent = o.label;
          if (o.value === (f.value || "")) opt.selected = true;
          el.appendChild(opt);
        });
      } else if (f.type === "checkbox") {
        el = document.createElement("input");
        el.type = "checkbox"; el.checked = !!f.value;
        row.classList.add("field-check");
      } else if (f.type === "icon") {
        el = iconField(f.value || "");
        row.classList.add("field-icon");
      } else if (f.type === "info") {
        el = document.createElement("p");
        el.className = "field-info";
        el.textContent = f.value || "";
      } else {
        el = document.createElement("input");
        el.type = f.type || "text";
        el.value = f.value == null ? "" : f.value;
        if (f.placeholder) el.placeholder = f.placeholder;
      }
      inputs[f.key] = el;
      row.appendChild(el);
      box.appendChild(row);
    });

    var actions = document.createElement("div");
    actions.className = "modal-actions";
    actions.innerHTML = (onDelete ? '<button type="button" class="danger" data-del>Löschen</button>' : "") +
                        '<span class="spacer"></span>' +
                        '<button type="button" class="ghost" data-cancel>Abbrechen</button>' +
                        '<button type="submit" class="primary">Speichern</button>';
    box.appendChild(actions);

    function close() { back.remove(); }
    actions.querySelector("[data-cancel]").addEventListener("click", close);
    if (onDelete) {
      actions.querySelector("[data-del]").addEventListener("click", function () {
        close();
        onDelete();
      });
    }
    back.addEventListener("mousedown", function (e) { if (e.target === back) close(); });

    box.addEventListener("submit", function (e) {
      e.preventDefault();
      var values = {};
      fields.forEach(function (f) {
        var el = inputs[f.key];
        if (f.type === "info") return;
        if (f.type === "checkbox") values[f.key] = el.checked;
        else if (f.type === "icon") values[f.key] = el.dataset.value || "";
        else values[f.key] = el.value.trim();
      });
      close();
      onSubmit(values);
    });

    back.appendChild(box);
    document.body.appendChild(back);
    var first = box.querySelector("input, select");
    if (first) first.focus();
    return back;
  }

  // ---------------------------------------------------------------- Logo-Auswahl

  var ICON_EXT = {};
  var iconIndex = null;

  /** Endungen aller Logos einmal holen — sonst rät die Vorschau ".svg"
      und zeigt für PNG-Logos nichts an. */
  function ensureIconIndex() {
    if (!iconIndex) {
      iconIndex = fetch("/api/icons", { credentials: "same-origin" })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          data.icons.forEach(function (i) { ICON_EXT[i.name] = i.url.slice(i.url.lastIndexOf(".")); });
          return data;
        });
    }
    return iconIndex;
  }

  function iconField(value) {
    var wrap = document.createElement("div");
    wrap.className = "iconpick";
    wrap.dataset.value = value;

    var preview = document.createElement("span");
    preview.className = "iconpick-prev";
    var label = document.createElement("span");
    label.className = "iconpick-name";
    var pick = document.createElement("button");
    pick.type = "button"; pick.className = "ghost"; pick.textContent = "Wählen…";

    function render() {
      var v = wrap.dataset.value;
      preview.innerHTML = "";
      if (v) {
        var img = document.createElement("img");
        img.width = 22; img.height = 22; img.alt = "";
        img.src = "/icons/" + v + (ICON_EXT[v] || ".svg");
        // Falls die Endung noch unbekannt war: die anderen durchprobieren.
        var rest = [".png", ".webp", ".svg"].filter(function (e) { return !img.src.endsWith(e); });
        img.addEventListener("error", function () {
          var next = rest.shift();
          if (next) img.src = "/icons/" + v + next;
        });
        preview.appendChild(img);
      }
      label.textContent = v || "kein Logo";
    }

    pick.addEventListener("click", function () {
      openIconGallery(function (name) { wrap.dataset.value = name; render(); });
    });

    wrap.append(preview, label, pick);
    render();
    ensureIconIndex().then(render);   // mit den echten Endungen noch einmal zeichnen
    return wrap;
  }

  async function openIconGallery(onPick) {
    var data = await ensureIconIndex();

    var back = document.createElement("div");
    back.className = "modal-back";
    var box = document.createElement("div");
    box.className = "modal modal-wide";
    box.innerHTML = "<h3>Logo wählen</h3>";

    var grid = document.createElement("div");
    grid.className = "icongrid";

    var none = document.createElement("button");
    none.type = "button"; none.className = "iconcell";
    none.innerHTML = "<span class='iconcell-none'>—</span><span>kein Logo</span>";
    none.addEventListener("click", function () { onPick(""); back.remove(); });
    grid.appendChild(none);

    data.icons.forEach(function (ic) {
      var cell = document.createElement("button");
      cell.type = "button"; cell.className = "iconcell";
      cell.innerHTML = '<img src="' + ic.url + '" alt="" width="28" height="28">' +
                       "<span>" + ic.name + "</span>" +
                       '<span class="iconcell-del" title="Logo löschen">✕</span>';
      cell.addEventListener("click", function (e) {
        if (e.target.classList.contains("iconcell-del")) {
          e.stopPropagation();
          askConfirm('Logo „' + ic.name + '“ endgültig löschen?').then(function (ok) {
            if (!ok) return;
            fetch("/api/icons/" + ic.name, {
              method: "DELETE", credentials: "same-origin", headers: { "X-CSRF-Token": csrf() },
            }).then(async function (r) {
              if (r.ok) cell.remove();
              else toast(await problem(r, "Löschen fehlgeschlagen"));
            });
          });
          return;
        }
        onPick(ic.name);
        back.remove();
      });
      grid.appendChild(cell);
    });
    box.appendChild(grid);

    var up = document.createElement("div");
    up.className = "iconupload";
    up.innerHTML = "<label class='ghost'>Logo hochladen<input type='file' accept='.svg,.png,.webp' hidden></label>" +
                   "<span class='hint'>Farbiges SVG, Dateiname = Logo-Name. Für den einfarbigen Modus färbt die " +
                   "Seite Umrisse selbst um; Logos mit voller Fläche brauchen zusätzlich <code>name-light</code> " +
                   "und <code>name-dark</code>.</span>";
    up.querySelector("input").addEventListener("change", async function () {
      var file = this.files[0];
      if (!file) return;
      var fd = new FormData();
      fd.append("file", file);
      var res = await fetch("/api/icons", {
        method: "POST", credentials: "same-origin", headers: { "X-CSRF-Token": csrf() }, body: fd,
      });
      if (!res.ok) { toast(await problem(res, "Upload fehlgeschlagen")); return; }
      var out = await res.json();
      ICON_EXT[out.name] = out.url.slice(out.url.lastIndexOf("."));
      onPick(out.name);
      back.remove();
    });
    box.appendChild(up);

    var actions = document.createElement("div");
    actions.className = "modal-actions";
    actions.innerHTML = '<button type="button" class="ghost">Schließen</button>';
    actions.querySelector("button").addEventListener("click", function () { back.remove(); });
    box.appendChild(actions);

    back.addEventListener("mousedown", function (e) { if (e.target === back) back.remove(); });
    back.appendChild(box);
    document.body.appendChild(back);
  }

  // ---------------------------------------------------------------- Design (Schublade)

  var THEME_NAMES = { hell: "Hell", ambient: "Ambient", dunkel: "Dunkel" };

  // Reihenfolge von oben nach unten, wie man die Seite liest.
  var LAYERS = [
    { key: "bar", label: "Titelleiste" },
    { key: "marks", label: "Lesezeichenleiste" },
    { key: "card", label: "Container" },
    { key: "veil", label: "Maske über dem Bild" },
  ];

  // Größen: Gruppe → Regler. Die Grenzen kommen vom Server (GO_LAYOUT_RANGE).
  var SIZES = [
    { group: "bar", label: "Titelleiste", keys: [
      ["height", "Höhe"], ["title", "Titel"], ["link", "Seitenlinks"], ["logo", "Bild"]] },
    { group: "marks", label: "Lesezeichenleiste", keys: [
      ["height", "Höhe"], ["icon", "Logos"], ["text", "Text"]] },
    { group: "content", label: "Inhalt", keys: [
      ["title", "Container-Titel"], ["name", "Eintragstitel"], ["desc", "Beschreibung"], ["logo", "Logos"]] },
  ];

  var CSS_VAR = {
    bar: { height: "--bar-h", title: "--bar-title", link: "--bar-link", logo: "--bar-logo" },
    marks: { height: "--marks-h", icon: "--marks-icon", text: "--marks-text" },
    content: { title: "--c-title", name: "--c-name", desc: "--c-desc", logo: "--c-logo" },
  };

  function hexToRgb(hex) {
    var h = hex.replace("#", "");
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)].join(", ");
  }

  var drawer = null;

  /* Drei Reiter:
       Allgemein     — Titel, Untertitel, Logo, Größen. Gilt für ALLE Seiten (site).
       Hintergrund   — Bilder und Diashow dieser Seite.
       Transparenz   — Flächen je Design, dieser Seite. Nur das lässt sich kopieren. */
  async function openDesign() {
    if (drawer) { closeDrawer(); return; }

    var model = await loadModel();
    var cfg = pageCfg(model);
    var site = model.site || {};
    var theme = document.documentElement.dataset.theme || "ambient";
    var layoutDefaults = window.GO_LAYOUT_DEFAULTS || {};
    var range = window.GO_LAYOUT_RANGE || {};
    var root = document.documentElement;

    var colorsByTheme = JSON.parse(JSON.stringify(cfg.theme || {}));
    var sizes = JSON.parse(JSON.stringify(site.layout || {}));

    drawer = document.createElement("aside");
    drawer.className = "drawer";
    drawer.innerHTML = "<header><h3>Einstellungen</h3>" +
                       '<button type="button" class="iconbtn" data-close title="Schließen">✕</button></header>';

    var TABS = [
      { key: "allgemein", label: "Allgemein" },
      { key: "seiten", label: "Seiten" },
      { key: "hintergrund", label: "Hintergrund" },
      { key: "transparenz", label: "Transparenz" },
    ];
    var tabbar = document.createElement("nav");
    tabbar.className = "tabs";
    var panels = {};

    var scroll = document.createElement("div");
    scroll.className = "drawer-body";

    TABS.forEach(function (tab, i) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = tab.label;
      b.dataset.tab = tab.key;
      b.setAttribute("aria-selected", String(i === 0));
      b.addEventListener("click", function () { showTab(tab.key); });
      tabbar.appendChild(b);

      var panel = document.createElement("div");
      panel.className = "panel";
      panel.hidden = i > 0;
      panels[tab.key] = panel;
      scroll.appendChild(panel);
    });

    function showTab(key) {
      TABS.forEach(function (tab) {
        panels[tab.key].hidden = tab.key !== key;
        tabbar.querySelector('[data-tab="' + tab.key + '"]').setAttribute("aria-selected", String(tab.key === key));
      });
    }

    drawer.append(tabbar, scroll);

    /** Überschrift samt Erklärung in einen Reiter setzen. */
    function section(panel, title, note) {
      var h = document.createElement("h4");
      h.textContent = title;
      panel.appendChild(h);
      if (note) {
        var p = document.createElement("p");
        p.className = "hint";
        p.textContent = note;
        panel.appendChild(p);
      }
    }

    function textRow(panel, label, value, placeholder) {
      var row = document.createElement("label");
      row.className = "field";
      var cap = document.createElement("span");
      cap.textContent = label;
      var input = document.createElement("input");
      input.type = "text";
      input.value = value || "";
      if (placeholder) input.placeholder = placeholder;
      row.append(cap, input);
      panel.appendChild(row);
      return input;
    }

    // ================================================================ Allgemein
    var general = panels.allgemein;
    section(general, "Beschriftung", "Titel und Untertitel stehen in der Titelleiste jeder Seite.");
    var titleInput = textRow(general, "Titel", site.title || "DashMyBoard");
    var subInput = textRow(general, "Untertitel", site.subtitle || "", "z. B. Intranet");

    section(general, "Bild der Seite", "Erscheint links in der Titelleiste und als Symbol im Browser-Reiter.");
    var picker = iconField(site.logo || DEFAULT_LOGO);
    general.appendChild(picker);

    section(general, "Größen", "Gelten für alle Seiten.");
    var sizeBox = document.createElement("div");
    general.appendChild(sizeBox);

    function renderSizes() {
      sizeBox.innerHTML = "";
      SIZES.forEach(function (grp) {
        var block = document.createElement("div");
        block.className = "layer";
        var head = document.createElement("div");
        head.className = "layer-head";
        var name = document.createElement("span");
        name.textContent = grp.label;
        var reset = document.createElement("button");
        reset.type = "button"; reset.className = "ghost"; reset.textContent = "Neutral";
        head.append(name, reset);
        block.appendChild(head);

        grp.keys.forEach(function (pair) {
          var key = pair[0];
          var current = (sizes[grp.group] || {})[key];
          var value = current == null ? layoutDefaults[grp.group][key] : current;
          var bounds = range[grp.group][key];

          var row = document.createElement("div");
          row.className = "size-row";
          var cap = document.createElement("span");
          cap.textContent = pair[1];
          var input = document.createElement("input");
          input.type = "range";
          input.min = String(bounds[0]); input.max = String(bounds[1]); input.step = "1";
          input.value = String(value);
          var out = document.createElement("b");
          out.textContent = value + " px";

          input.addEventListener("input", function () {
            var v = parseInt(input.value, 10);
            (sizes[grp.group] || (sizes[grp.group] = {}))[key] = v;
            out.textContent = v + " px";
            root.style.setProperty(CSS_VAR[grp.group][key], v + "px");
          });

          reset.addEventListener("click", function () {
            var d = layoutDefaults[grp.group][key];
            input.value = String(d);
            out.textContent = d + " px";
            if (sizes[grp.group]) delete sizes[grp.group][key];
            root.style.setProperty(CSS_VAR[grp.group][key], d + "px");
          });

          row.append(cap, input, out);
          block.appendChild(row);
        });

        sizeBox.appendChild(block);
      });
    }

    renderSizes();

    // ================================================================ Seiten
    /* Seiten sind Daten, kein Code: anlegen, umbenennen, sortieren, löschen. Die Art
       entscheidet, was die Seite kann — nur „links“ hat einen Inhalt zum Bearbeiten. */
    var pagesPanel = panels.seiten;
    var pageList = JSON.parse(JSON.stringify(model.pages || []));

    section(pagesPanel, "Seiten", "Reihenfolge = Reihenfolge in der Titelleiste. Ziehen zum Sortieren.");
    var listBox = document.createElement("div");
    listBox.className = "pagelist";
    pagesPanel.appendChild(listBox);

    var addPage = document.createElement("button");
    addPage.type = "button";
    addPage.className = "add";
    addPage.textContent = "+ Seite";
    addPage.addEventListener("click", function () { pageDialog(null); });
    pagesPanel.appendChild(addPage);

    function typeLabel(page) {
      if (page.type === "builtin") return "Eingebaut";
      if (page.type === "frames") return "Reiter";
      return "Linktree";
    }

    /* Die Startseite und die eingebauten Ansichten kommen aus der Anwendung: ihre
       Adresse, Art und Ansicht stecken im Code. Sie lassen sich nur umsortieren —
       ändern oder löschen ginge nur, bis der Server sie beim Speichern zurückweist. */
    function locked(page) {
      return page.type === "builtin" || (page.slug || "") === "";
    }

    function renderPages() {
      listBox.innerHTML = "";
      pageList.forEach(function (page, index) {
        var row = document.createElement("div");
        row.className = "pagerow";
        row.draggable = true;
        row.dataset.index = String(index);

        var grip = document.createElement("span");
        grip.className = "pagegrip";
        grip.textContent = "⠿";

        var name = document.createElement("span");
        name.className = "pagename";
        name.textContent = page.title || "(ohne Titel)";

        var meta = document.createElement("span");
        meta.className = "pagemeta";
        meta.textContent = typeLabel(page) + (page.role ? " · " + page.role : "");

        var slug = document.createElement("code");
        slug.className = "pageslug";
        slug.textContent = "/" + (page.slug || "");

        var tail;
        if (locked(page)) {
          tail = document.createElement("span");
          tail.className = "pagelock";
          tail.textContent = "🔒";
          tail.title = "Von der Anwendung geliefert — nur die Reihenfolge ist änderbar";
        } else {
          tail = document.createElement("button");
          tail.type = "button";
          tail.className = "pageedit";
          tail.title = "Seite bearbeiten";
          tail.textContent = "✎";
          tail.addEventListener("click", function () { pageDialog(index); });
        }

        row.append(grip, name, slug, meta, tail);
        listBox.appendChild(row);
      });
    }

    // Sortieren per Ziehen — dieselbe Regel wie im Inhalt: Reihenfolge ist Wahrheit.
    var dragRow = null;
    listBox.addEventListener("dragstart", function (ev) {
      dragRow = ev.target.closest(".pagerow");
      if (dragRow) dragRow.classList.add("dragging");
    });
    listBox.addEventListener("dragend", function () {
      if (dragRow) dragRow.classList.remove("dragging");
      dragRow = null;
    });
    listBox.addEventListener("dragover", function (ev) {
      if (!dragRow) return;
      var over = ev.target.closest(".pagerow");
      if (!over || over === dragRow) return;
      ev.preventDefault();
      var box = over.getBoundingClientRect();
      var after = ev.clientY > box.top + box.height / 2;
      var from = +dragRow.dataset.index;
      var to = +over.dataset.index + (after ? 1 : 0);
      if (to > from) to -= 1;
      if (to === from) return;
      pageList.splice(to, 0, pageList.splice(from, 1)[0]);
      renderPages();
      dragRow = listBox.querySelector('.pagerow[data-index="' + to + '"]');
      if (dragRow) dragRow.classList.add("dragging");
    });

    /** Dialog für eine Seite. `index === null` legt eine neue an. */
    function pageDialog(index) {
      var page = index == null ? { type: "links" } : pageList[index];
      if (index != null && locked(page)) return;   // gelieferte Seiten sind unveränderlich

      var fields = [
        { key: "title", label: "Titel", value: page.title || "" },
        { key: "slug", label: "Adresse", value: page.slug || "",
          placeholder: "z. B. team  →  /team" },
        { key: "type", label: "Art", type: "select", value: page.type || "links",
          options: [{ value: "links", label: "Linktree (Container und Einträge)" },
                    { value: "frames", label: "Reiter (Inhalt eingebettet)" }] },
        Object.assign({}, ROLE_FIELD, { value: page.role || "" }),
      ];

      // Startreiter nur bei Reiter-Seiten und nur, wenn es schon Reiter gibt.
      var marks = flatMarks(page.bookmarks || []);
      if (page.type === "frames" && marks.length) {
        fields.push({ key: "start", label: "Beim Aufruf zeigen", type: "select",
                      value: page.start || "",
                      options: [{ value: "", label: "erster Reiter" }].concat(marks) });
      }


      dialog(index == null ? "Neue Seite" : "Seite: " + (page.title || ""), fields, function (v) {
        var slug = slugify(v.slug);
        if (!slug) return toast("Die Seite braucht eine Adresse.");
        if (!v.title) return toast("Die Seite braucht einen Titel.");

        var clash = pageList.some(function (other, i) {
          return i !== index && (other.slug || "") === slug;
        });
        if (clash) return toast("Diese Adresse ist schon vergeben.");

        var target = index == null ? {} : pageList[index];
        target.title = v.title;
        target.slug = slug;
        target.type = v.type || "links";
        put(target, "role", v.role);
        if (target.type === "frames") put(target, "start", v.start || "");
        else delete target.start;
        if (target.type !== "links") delete target.sections;
        else if (!target.sections) target.sections = [];

        if (index == null) pageList.push(target);
        renderPages();
      }, index == null ? null : function () {
        askConfirm("Seite „" + (page.title || "") + "“ mit allen Inhalten löschen?").then(function (ok) {
          if (!ok) return;
          pageList.splice(index, 1);
          renderPages();
        });
      });
    }

    /** Lesezeichen einer Seite flach als Auswahlliste (Pfad → Beschriftung). */
    function flatMarks(items, prefix, out) {
      out = out || [];
      items.forEach(function (bm, i) {
        var path = prefix ? prefix + "." + i : String(i);
        if (bm.children) flatMarks(bm.children, path, out);
        else out.push({ value: path, label: bm.name });
      });
      return out;
    }

    function slugify(text) {
      return (text || "").trim().toLowerCase()
        .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss")
        .replace(/[^a-z0-9-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 32);
    }

    renderPages();

    // ================================================================ Hintergrund
    var bgPanel = panels.hintergrund;
    var chosen = (cfg.backgrounds || []).slice();
    var interval = document.createElement("input");

    section(bgPanel, "Hintergrundbild dieser Seite",
            "Mehrere Bilder ergeben eine Diashow. Die Zahl zeigt die Reihenfolge.");

    var bgGrid = document.createElement("div");
    bgGrid.className = "bggrid";
    bgPanel.appendChild(bgGrid);

    function paintBg() {
      bgGrid.querySelectorAll(".bgcell").forEach(function (cell) {
        var i = chosen.indexOf(cell.dataset.name);
        cell.classList.toggle("picked", i >= 0);
        cell.querySelector(".bgnum").textContent = i >= 0 ? String(i + 1) : "";
      });
    }

    function addBgCell(bg) {
      var cell = document.createElement("button");
      cell.type = "button"; cell.className = "bgcell"; cell.dataset.name = bg.name;
      cell.innerHTML = '<img src="' + bg.url + '" alt="" loading="lazy">' +
                       '<span class="bgnum"></span>' +
                       '<span class="iconcell-del" title="Bild löschen">✕</span>';
      cell.addEventListener("click", function (e) {
        if (e.target.classList.contains("iconcell-del")) {
          e.stopPropagation();
          askConfirm('Bild „' + bg.name + '“ endgültig löschen?').then(function (ok) {
            if (!ok) return;
            fetch("/api/backgrounds/" + bg.name, {
              method: "DELETE", credentials: "same-origin", headers: { "X-CSRF-Token": csrf() },
            }).then(async function (r) {
              if (!r.ok) return toast(await problem(r, "Löschen fehlgeschlagen"));
              chosen = chosen.filter(function (n) { return n !== bg.name; });
              cell.remove();
            });
          });
          return;
        }
        var i = chosen.indexOf(bg.name);
        if (i >= 0) chosen.splice(i, 1); else chosen.push(bg.name);
        paintBg();
      });
      bgGrid.appendChild(cell);
    }

    (await (await fetch("/api/backgrounds", { credentials: "same-origin" })).json())
      .backgrounds.forEach(addBgCell);
    paintBg();

    var bgRow = document.createElement("div");
    bgRow.className = "size-row";
    var bgCap = document.createElement("span");
    bgCap.textContent = "Wechsel (Sek.)";
    interval.type = "text";
    interval.className = "num";
    interval.value = String(cfg.interval || 12);
    bgRow.append(bgCap, interval);
    bgPanel.appendChild(bgRow);

    var bgUp = document.createElement("div");
    bgUp.className = "iconupload";
    bgUp.innerHTML = "<label class='ghost'>Bild hochladen<input type='file' accept='.jpg,.jpeg,.png,.webp' hidden></label>" +
                     "<span class='hint'>JPG, PNG oder WebP, höchstens 8 MB.</span>";
    bgUp.querySelector("input").addEventListener("change", async function () {
      var file = this.files[0];
      if (!file) return;
      var fd = new FormData(); fd.append("file", file);
      var res = await fetch("/api/backgrounds", {
        method: "POST", credentials: "same-origin", headers: { "X-CSRF-Token": csrf() }, body: fd,
      });
      if (!res.ok) { toast(await problem(res, "Upload fehlgeschlagen")); return; }
      var out = await res.json();
      addBgCell(out);
      chosen.push(out.name);
      paintBg();
    });
    bgPanel.appendChild(bgUp);

    // ================================================================ Transparenz
    var tPanel = panels.transparenz;
    section(tPanel, "Flächen je Design",
            "Farbe und Deckkraft. 0 % ist durchsichtig, 100 % deckt vollständig. " +
            "Der Wechsler stellt zugleich die Seite um — so siehst du, was du änderst.");

    var switcher = document.createElement("div");
    switcher.className = "themepick";
    Object.keys(THEME_NAMES).forEach(function (name) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = THEME_NAMES[name];
      b.dataset.theme = name;
      b.setAttribute("aria-pressed", String(name === theme));
      b.addEventListener("click", function () { switchTheme(name); });
      switcher.appendChild(b);
    });
    tPanel.appendChild(switcher);

    var colorBox = document.createElement("div");
    tPanel.appendChild(colorBox);

    /** Design umschalten: Seite mit umstellen, Regler des neuen Designs zeigen. */
    function switchTheme(name) {
      if (name === theme) return;
      clearColorPreview();          // Vorschau des alten Designs lösen
      theme = name;
      root.dataset.theme = name;
      try { localStorage.setItem("dmb-theme", name); } catch (e) {}
      document.querySelectorAll(".switch-3").forEach(function (sl) {
        sl.style.setProperty("--i", ["hell", "ambient", "dunkel"].indexOf(name));
        sl.querySelectorAll("button").forEach(function (b) {
          b.setAttribute("aria-checked", String(b.dataset.theme === name));
        });
      });
      switcher.querySelectorAll("button").forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.dataset.theme === name));
      });
      renderColors();
    }

    function renderColors() {
      colorBox.innerHTML = "";
      var defs = (window.GO_THEME_DEFAULTS || {})[theme] || {};
      var own = colorsByTheme[theme] || (colorsByTheme[theme] = {});

      LAYERS.forEach(function (layer) {
        var v = Object.assign({}, defs[layer.key], own[layer.key] || {});
        var block = document.createElement("div");
        block.className = "layer";

        var head = document.createElement("div");
        head.className = "layer-head";
        var name = document.createElement("span");
        name.textContent = layer.label;
        var reset = document.createElement("button");
        reset.type = "button"; reset.className = "ghost"; reset.textContent = "Neutral";
        head.append(name, reset);
        block.appendChild(head);

        var row = document.createElement("div");
        row.className = "layer-row";
        var color = document.createElement("input");
        color.type = "color"; color.value = v.color;
        var alpha = document.createElement("input");
        alpha.type = "range"; alpha.min = "0"; alpha.max = "100"; alpha.step = "1";
        alpha.value = String(Math.round(v.alpha * 100));
        var out = document.createElement("b");
        out.textContent = alpha.value + " %";
        row.append(color, alpha, out);
        block.appendChild(row);

        function preview(hex, a) {
          root.style.setProperty("--" + layer.key + "-rgb", hexToRgb(hex));
          root.style.setProperty("--" + layer.key + "-a", String(a));
        }
        function apply() {
          var a = +alpha.value / 100;
          own[layer.key] = { color: color.value, alpha: a };
          out.textContent = alpha.value + " %";
          preview(color.value, a);
        }
        color.addEventListener("input", apply);
        alpha.addEventListener("input", apply);
        reset.addEventListener("click", function () {
          var d = defs[layer.key];
          color.value = d.color;
          alpha.value = String(Math.round(d.alpha * 100));
          out.textContent = alpha.value + " %";
          delete own[layer.key];
          preview(d.color, d.alpha);
        });

        // Bereits geänderte Werte sofort zeigen
        if (own[layer.key]) preview(v.color, v.alpha);
        colorBox.appendChild(block);
      });
    }

    renderColors();

    // Kopiert werden nur die Flächen — Größen und Beschriftung gelten ohnehin überall.
    var others = (window.GO_PAGES || []).filter(function (pg) { return pg.slug !== PAGE; });
    if (others.length) {
      section(tPanel, "Transparenz kopieren");
      var copyRow = document.createElement("div");
      copyRow.className = "layer-row copyrow";
      var from = document.createElement("span");
      from.textContent = "von Seite";
      var pick2 = document.createElement("select");
      others.forEach(function (pg) {
        var o = document.createElement("option");
        o.value = pg.slug;
        o.textContent = pg.title;
        pick2.appendChild(o);
      });
      var take = document.createElement("button");
      take.type = "button"; take.className = "ghost"; take.textContent = "Übernehmen";
      take.addEventListener("click", async function () {
        var fresh = await loadModel();
        var src = (fresh.pages || []).filter(function (pg) { return (pg.slug || "") === pick2.value; })[0] || {};
        colorsByTheme = JSON.parse(JSON.stringify(src.theme || {}));
        clearColorPreview();
        renderColors();
        applyColorPreview();
      });
      copyRow.append(from, pick2, take);
      tPanel.appendChild(copyRow);
    }

    // ================================================================ Fuß
    var actions = document.createElement("footer");
    actions.className = "drawer-actions";
    actions.innerHTML = '<button type="button" class="ghost" data-cancel>Verwerfen</button>' +
                        '<button type="button" class="primary" data-save>Speichern</button>';
    drawer.appendChild(actions);

    function applyColorPreview() {
      var own = colorsByTheme[theme] || {};
      Object.keys(own).forEach(function (layer) {
        root.style.setProperty("--" + layer + "-rgb", hexToRgb(own[layer].color));
        root.style.setProperty("--" + layer + "-a", String(own[layer].alpha));
      });
    }

    function clearColorPreview() {
      LAYERS.forEach(function (l) {
        root.style.removeProperty("--" + l.key + "-rgb");
        root.style.removeProperty("--" + l.key + "-a");
      });
    }

    function clearPreview() {
      clearColorPreview();
      Object.keys(CSS_VAR).forEach(function (g) {
        Object.keys(CSS_VAR[g]).forEach(function (k) { root.style.removeProperty(CSS_VAR[g][k]); });
      });
    }

    function closeDrawer() {
      clearPreview();
      if (drawer) drawer.remove();
      drawer = null;
      body.classList.remove("drawer-open");
    }

    drawer.querySelector("[data-close]").addEventListener("click", closeDrawer);
    actions.querySelector("[data-cancel]").addEventListener("click", closeDrawer);
    actions.querySelector("[data-save]").addEventListener("click", function () {
      var logo = picker.dataset.value || "";
      var title = titleInput.value.trim();
      var subtitle = subInput.value.trim();
      if (!title) { toast("Die Seite braucht einen Titel."); showTab("allgemein"); return; }
      closeDrawer();

      mutate(function (m) {
        // Zuerst die Seitenliste — sonst zeigte pageCfg() auf eine Seite, die es
        // nach dem Speichern gar nicht mehr gibt.
        m.pages = pageList;

        // Wurde die Seite, auf der wir stehen, gerade gelöscht, gibt es nichts mehr
        // zu gestalten — gespeichert wird trotzdem, und der Neuaufbau landet auf /.
        var c = null;
        try { c = pageCfg(m); } catch (e) { c = null; }

        if (c) {
          // Nur diese Seite: Flächen, Bilder, Diashow.
          var t = {};
          Object.keys(colorsByTheme).forEach(function (name) {
            if (Object.keys(colorsByTheme[name]).length) t[name] = colorsByTheme[name];
          });
          if (Object.keys(t).length) c.theme = t;
          else delete c.theme;

          var secs = parseInt(interval.value, 10);
          c.backgrounds = chosen;
          c.interval = isNaN(secs) ? 12 : Math.max(4, Math.min(600, secs));
        }

        // Alle Seiten: Beschriftung, Logo, Größen.
        m.site = m.site || {};
        m.site.title = title;
        put(m.site, "subtitle", subtitle);
        put(m.site, "logo", logo === DEFAULT_LOGO ? "" : logo);

        Object.keys(sizes).forEach(function (g) {
          if (!Object.keys(sizes[g]).length) delete sizes[g];
        });
        if (Object.keys(sizes).length) m.site.layout = sizes;
        else delete m.site.layout;
      });
    });

    document.body.appendChild(drawer);
    body.classList.add("drawer-open");
    window.__goCloseDrawer = closeDrawer;
  }

  function closeDrawer() {
    if (window.__goCloseDrawer) window.__goCloseDrawer();
  }

  // ---------------------------------------------------------------- Formulare

  var ROLE_FIELD = {
    key: "role", label: "Sichtbar für", type: "select",
    options: [{ value: "", label: "alle Angemeldeten" }, { value: "hoheit", label: "nur Rolle „hoheit“" }],
  };

  function linkFields(l) {
    l = l || {};
    return [
      { key: "name", label: "Titel", value: l.name },
      { key: "desc", label: "Untertitel", value: l.desc, placeholder: "kurze Beschreibung" },
      { key: "url", label: "Adresse", value: l.url, placeholder: "leer = nicht anklickbar" },
      { key: "icon", label: "Logo", type: "icon", value: l.icon },
      { key: "badge", label: "Abzeichen", value: l.badge, placeholder: "z. B. LAN" },
      { key: "vpn", label: "Nur über NetBird (VPN)", type: "checkbox", value: l.vpn },
      { key: "collapsed", label: "Untereinträge beim Laden zugeklappt", type: "checkbox", value: l.collapsed },
    ];
  }

  function applyLink(target, v) {
    target.name = v.name;
    var url = normalizeUrl(v.url === "https://" ? "" : v.url);
    if (url === null) throw new Error("Diese Adresse ist nicht erlaubt — nur http:// und https://.");
    put(target, "url", url);   // ohne Adresse: Eintrag bleibt, ist aber nicht anklickbar
    put(target, "desc", v.desc);
    put(target, "icon", v.icon);
    put(target, "vpn", v.vpn);
    put(target, "badge", v.vpn ? "" : v.badge); // VPN gewinnt, zwei Abzeichen wären sinnlos
    put(target, "collapsed", v.collapsed);
  }

  // ---------------------------------------------------------------- Aktionen

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest("[data-act]");
    if (!btn || btn.dataset.act === "toggle") return;

    var act = btn.dataset.act;

    // Die Design-Schublade hängt an keinem Bearbeiten-Modus.
    if (act === "page-design") { ev.preventDefault(); return void openDesign(); }

    if (!on(scopeOf(btn))) return;
    // Beim Tippen im Titel oder am Ziehgriff soll sich kein Dialog öffnen.
    if (ev.target.closest("[data-edit], .drag-handle")) return;
    ev.preventDefault();
    ev.stopPropagation();

    var c = ctx(btn);

    if (act === "page-marks") return void openBookmarkFiles();

    // ---- Container
    if (act === "sec-add") {
      dialog("Neuer Container", [
        { key: "title", label: "Titel", value: "" },
        { key: "accent", label: "Akzentfarbe", type: "color", value: "#b0566f" },
        ROLE_FIELD,
        { key: "collapsed", label: "Beim Laden zugeklappt", type: "checkbox", value: false },
      ], function (v) {
        mutate(function (m) {
          var sec = { title: v.title, accent: v.accent, groups: [{ links: [] }] };
          put(sec, "role", v.role);
          put(sec, "collapsed", v.collapsed);
          sections(m).push(sec);
        });
      });
      return;
    }

    if (act === "sec-edit") {
      withModel(function (m) {
        var sec = sections(m)[c.s];
        dialog("Container: " + sec.title, [
          { key: "accent", label: "Akzentfarbe", type: "color", value: sec.accent || "#b0566f" },
          Object.assign({}, ROLE_FIELD, { value: sec.role || "" }),
          { key: "collapsed", label: "Beim Laden zugeklappt", type: "checkbox", value: !!sec.collapsed },
        ], function (v) {
          mutate(function (m2) {
            var t = sections(m2)[c.s];
            t.accent = v.accent;
            put(t, "role", v.role);
            put(t, "collapsed", v.collapsed);
          });
        }, function () {
          askConfirm("Container samt Einträgen löschen?").then(function (ok) {
            if (ok) mutate(function (m2) { sections(m2).splice(c.s, 1); });
          });
        });
      });
      return;
    }

    // ---- Gruppen
    if (act === "grp-add") {
      mutate(function (m) { sections(m)[c.s].groups.push({ links: [] }); });
      return;
    }

    if (act === "grp-edit") {
      withModel(function (m) {
        var grp = sections(m)[c.s].groups[c.g];
        dialog("Gruppe", [
          { key: "collapsed", label: "Beim Laden zugeklappt", type: "checkbox", value: !!grp.collapsed },
        ], function (v) {
          mutate(function (m2) { put(sections(m2)[c.s].groups[c.g], "collapsed", v.collapsed); });
        }, function () {
          askConfirm("Gruppe samt Einträgen löschen?").then(function (ok) {
            if (ok) mutate(function (m2) { sections(m2)[c.s].groups.splice(c.g, 1); });
          });
        });
      });
      return;
    }

    // ---- Einträge
    if (act === "link-add") {
      dialog("Neuer Eintrag", linkFields({ url: "https://" }), function (v) {
        mutate(function (m) {
          var link = {};
          applyLink(link, v);
          linkRoot(m, c).push(link);
        });
      });
      return;
    }

    if (act === "link-edit") {
      withModel(function (m) {
        var link = nodeIn(linkRoot(m, c), c.lpath);
        dialog("Eintrag: " + link.name, linkFields(link), function (v) {
          mutate(function (m2) { applyLink(nodeIn(linkRoot(m2, c), c.lpath), v); });
        }, function () {
          askConfirm("Eintrag entfernen? Untereinträge verschwinden mit.", "Entfernen").then(function (ok) {
            if (ok) mutate(function (m2) { takeOut(linkRoot(m2, c), c.lpath); });
          });
        });
      });
      return;
    }

    // ---- Lesezeichen (dieser Seite)
    if (act === "bm-add" || act === "bm-add-child") {
      dialog("Neues Lesezeichen", [
        { key: "name", label: "Name", value: "" },
        { key: "url", label: "Adresse", value: "", placeholder: "https://…" },
        { key: "icon", label: "Logo", type: "icon", value: "" },
        ROLE_FIELD,
      ], function (v) {
        warnIfNotEmbeddable(normalizeUrl(v.url));
        mutate(function (m) {
          var url = normalizeUrl(v.url);
          if (!url) throw new Error("Ein Lesezeichen braucht eine gültige Adresse.");
          var bm = { name: v.name, url: url };
          put(bm, "icon", v.icon);
          put(bm, "role", v.role);
          var list = bmRoot(m);
          if (act === "bm-add-child" && c.path) {
            var folder = nodeIn(list, c.path);
            list = folder.children || (folder.children = []);
          }
          list.push(bm);
        });
      });
      return;
    }

    if (act === "bm-add-folder") {
      dialog("Neuer Ordner", [
        { key: "name", label: "Name", value: "" },
        ROLE_FIELD,
      ], function (v) {
        mutate(function (m) {
          var folder = { name: v.name, children: [] };
          put(folder, "role", v.role);
          bmRoot(m).push(folder);
        });
      });
      return;
    }

    if (act === "bm-edit") {
      withModel(function (m) {
        var bm = nodeIn(bmRoot(m), c.path);
        var isFolder = "children" in bm;
        var fields = isFolder
          ? [Object.assign({}, ROLE_FIELD, { value: bm.role || "" })]
          : [
              { key: "url", label: "Adresse", value: bm.url },
              { key: "icon", label: "Logo", type: "icon", value: bm.icon },
              Object.assign({}, ROLE_FIELD, { value: bm.role || "" }),
            ];
        dialog(isFolder ? "Ordner: " + bm.name : "Lesezeichen: " + bm.name, fields, function (v) {
          if (!isFolder) warnIfNotEmbeddable(normalizeUrl(v.url));
          mutate(function (m2) {
            var t = nodeIn(bmRoot(m2), c.path);
            if (!isFolder) {
              var url = normalizeUrl(v.url);
              if (!url) throw new Error("Ein Lesezeichen braucht eine gültige Adresse.");
              t.url = url;
              put(t, "icon", v.icon);
            }
            put(t, "role", v.role);
          });
        }, function () {
          askConfirm(isFolder ? "Ordner samt Inhalt löschen?" : "Lesezeichen entfernen?").then(function (ok) {
            if (ok) mutate(function (m2) { takeOut(bmRoot(m2), c.path); });
          });
        });
      });
    }
  });
})();
