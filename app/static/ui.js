/* Auf- und Zuklappen von Containern/Gruppen und die Lesezeichen-Ordner.
   Gilt für alle Angemeldeten — nicht nur Administratoren.
   Der Startzustand kommt aus links.json ("collapsed"); was der Nutzer klickt,
   überschreibt ihn lokal im Browser. */
(function () {
  "use strict";

  var KEY = "dmb-collapsed";

  /* Einblendung unten rechts statt eines Browser-Kastens. Auch der Bearbeiten-Modus
     meldet darüber (window.goToast) — er wird nur für Administratoren geladen. */
  function toast(message, kind) {
    var box = document.getElementById("toasts");
    if (!box) {
      box = document.createElement("div");
      box.id = "toasts";
      box.setAttribute("aria-live", "polite");
      document.body.appendChild(box);
    }
    var el = document.createElement("div");
    el.className = "toast toast-" + (kind || "error");
    var text = document.createElement("span");
    text.textContent = message;
    var close = document.createElement("button");
    close.type = "button";
    close.className = "toast-x";
    close.title = "Schließen";
    close.textContent = "✕";
    close.addEventListener("click", function () { el.remove(); });
    el.append(text, close);
    box.appendChild(el);
    // Fehler bleiben stehen, bis man sie wegklickt; Erfolgsmeldungen gehen von selbst.
    if (kind === "ok") setTimeout(function () { el.remove(); }, 2400);
    return el;
  }

  window.goToast = toast;

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; }
  }

  function store(state) {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  }

  var state = load();

  // Gemerkten Zustand anwenden (der Server hat den Standard schon gesetzt).
  document.querySelectorAll("[data-key]").forEach(function (el) {
    var v = state[el.dataset.key];
    if (v === true) el.classList.add("collapsed");
    else if (v === false) el.classList.remove("collapsed");
    var caret = el.querySelector(".caret-btn");
    if (caret) caret.setAttribute("aria-expanded", String(!el.classList.contains("collapsed")));
  });

  function toggleBox(box) {
    var collapsed = box.classList.toggle("collapsed");
    var caret = box.querySelector(".caret-btn");
    if (caret) caret.setAttribute("aria-expanded", String(!collapsed));
    state[box.dataset.key] = collapsed;
    store(state);
  }

  document.addEventListener("click", function (ev) {
    // Der Pfeil klappt immer; die Überschrift nur, solange der Inhalt nicht bearbeitet
    // wird (dort wird sie getippt). Der Lesezeichen-Modus ändert daran nichts.
    var btn = ev.target.closest(".caret-btn");
    if (!btn && !document.body.classList.contains("edit-content")) {
      btn = ev.target.closest(".clicky");
    }
    if (!btn) return;
    var box = btn.closest("[data-key]");
    if (!box) return;
    ev.preventDefault();
    toggleBox(box);
  });

  // ---- Lesezeichen-Ordner (Klapp-Menüs, beliebig tief)
  function closeAll(except) {
    document.querySelectorAll(".bm-folder.open").forEach(function (f) {
      if (!except || !f.contains(except)) {
        f.classList.remove("open");
        var t = f.querySelector(":scope > .bm-toggle");
        if (t) t.setAttribute("aria-expanded", "false");
      }
    });
  }

  document.addEventListener("click", function (ev) {
    var toggle = ev.target.closest(".bm-toggle");
    if (toggle) {
      ev.preventDefault();
      var folder = toggle.closest(".bm-folder");
      var open = folder.classList.contains("open");
      closeAll(open ? null : folder);
      folder.classList.toggle("open", !open);
      toggle.setAttribute("aria-expanded", String(!open));
      return;
    }
    if (!ev.target.closest(".bm-menu")) closeAll(null);
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") closeAll(null);
  });

  // ---- Ordner in der Seiten-Navigation (Auswahlmenü)
  function closePageFolders(except) {
    document.querySelectorAll(".pagefolder.open").forEach(function (f) {
      if (f === except) return;
      f.classList.remove("open");
      var t = f.querySelector(":scope > .pf-toggle");
      if (t) t.setAttribute("aria-expanded", "false");
    });
  }

  document.addEventListener("click", function (ev) {
    var toggle = ev.target.closest(".pf-toggle");
    if (toggle) {
      // Im Bearbeiten-Modus gehört der Klick dem Dialog, nicht dem Menü.
      if (document.body.classList.contains("edit-content")) return;
      ev.preventDefault();
      var folder = toggle.closest(".pagefolder");
      var offen = folder.classList.contains("open");
      closePageFolders(offen ? null : folder);
      folder.classList.toggle("open", !offen);
      toggle.setAttribute("aria-expanded", String(!offen));
      return;
    }
    if (!ev.target.closest(".pf-menu")) closePageFolders(null);
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") closePageFolders(null);
  });

  // ---- Klappmenüs der Kopfzeile (Darstellung, Konto)
  function closeMenus(except) {
    document.querySelectorAll("[data-menu].open").forEach(function (m) {
      if (m === except) return;
      m.classList.remove("open");
      m.querySelector("[data-menu-btn]").setAttribute("aria-expanded", "false");
    });
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest("[data-menu-btn]");
    if (btn) {
      var menu = btn.closest("[data-menu]");
      var open = menu.classList.contains("open");
      closeMenus(menu);
      menu.classList.toggle("open", !open);
      btn.setAttribute("aria-expanded", String(!open));
      return;
    }
    // Ein Befehl im Menü (Design anpassen, Profil, Abmelden) schließt es; die Regler
    // darin nicht — sonst verschwände das Menü beim ersten Schieben.
    if (ev.target.closest(".menu-action, .menu-list a")) return void closeMenus(null);
    if (!ev.target.closest(".menu-panel")) closeMenus(null);
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") closeMenus(null);
  });

  // ---- Adresse eines Eintrags in die Zwischenablage
  function toClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    // Rückfall für http (z.B. lokale Vorschau): unsichtbares Feld, Auswahl, Kopierbefehl.
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.cssText = "position:fixed;opacity:0";
      document.body.appendChild(ta);
      ta.select();
      var ok = document.execCommand("copy");
      ta.remove();
      ok ? resolve() : reject(new Error("Kopieren nicht möglich"));
    });
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest(".copy");
    if (!btn) return;
    ev.preventDefault();
    ev.stopPropagation();
    toClipboard(btn.dataset.copy).then(function () {
      btn.classList.add("copied");
      btn.title = "Kopiert";
      setTimeout(function () {
        btn.classList.remove("copied");
        btn.title = "Adresse kopieren";
      }, 1200);
    }, function () { toast("Kopieren nicht möglich"); });
  });
})();
