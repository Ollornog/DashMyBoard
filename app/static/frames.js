/* Reiter-Seiten: ein Klick in der Leiste lädt die Adresse in den Rahmen statt in einen
   neuen Tab. Der offene Reiter steht im Adress-Fragment (#r=<pfad>), damit ein Neuladen
   ihn behält; ohne Fragment entscheidet der in den Einstellungen gewählte Startreiter.

   Die Lesezeichen behalten ihr href — Mittelklick, Strg-Klick und „in neuem Tab öffnen“
   funktionieren dadurch weiter, und ohne JavaScript bleibt die Seite benutzbar. */
(function () {
  "use strict";

  var frame = document.getElementById("frame");
  var empty = document.getElementById("frame-empty");
  var external = document.getElementById("frame-external");
  if (!frame) return;

  function markOf(path) {
    return document.querySelector('.bm-wrap[data-path="' + path + '"] > a.bm');
  }

  /** Reiter öffnen. `path` adressiert das Lesezeichen ("2" oder "1.0" in einem Ordner). */
  function open(path, link) {
    var a = link || markOf(path);
    if (!a || !a.getAttribute("href")) return false;

    document.querySelectorAll("#bookmarks .bm.current").forEach(function (el) {
      el.classList.remove("current");
    });
    a.classList.add("current");
    // Ordner, in dem der Reiter liegt, ebenfalls hervorheben.
    var folder = a.closest(".bm-folder");
    if (folder) {
      var toggle = folder.querySelector(":scope > .bm-toggle");
      if (toggle) toggle.classList.add("current");
    }

    frame.src = a.href;
    frame.hidden = false;
    empty.hidden = true;
    if (external) {
      external.href = a.href;
      external.hidden = false;
    }
    // Nur die Beschriftung, nicht der ganze Knoten — der trägt auch das Logo
    // bzw. dessen Monogramm-Buchstaben.
    var label = a.querySelector(".bm-label");
    document.title = (label ? label.textContent : a.textContent).trim()
                     + " — " + document.title.split(" — ").pop();
    return true;
  }

  document.addEventListener("click", function (ev) {
    // Im Bearbeiten-Modus gehört der Klick dem Dialog, nicht dem Rahmen.
    if (document.body.classList.contains("edit-marks")) return;
    var a = ev.target.closest("#bookmarks a.bm");
    if (!a || ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.button === 1) return;

    var wrap = a.closest(".bm-wrap");
    if (!wrap) return;
    ev.preventDefault();
    if (open(wrap.dataset.path, a)) {
      history.replaceState(null, "", "#r=" + wrap.dataset.path);
      // Untermenü schließen, damit der Blick frei auf den Inhalt fällt.
      document.querySelectorAll(".bm-folder.open").forEach(function (f) {
        f.classList.remove("open");
        var t = f.querySelector(":scope > .bm-toggle");
        if (t) t.setAttribute("aria-expanded", "false");
      });
    }
  });

  // Beim Laden: Fragment schlägt den Startreiter, der Startreiter das erste Lesezeichen.
  var fromHash = (location.hash.match(/^#r=([\d.]+)$/) || [])[1];
  var start = fromHash || window.GO_START_MARK || "";
  if (!start || !open(start)) {
    var first = document.querySelector("#bookmarks .bm-wrap");
    if (start && first) open(first.dataset.path);   // gemerkter Reiter existiert nicht mehr
  }
})();
