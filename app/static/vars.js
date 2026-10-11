/* Dynamische Werte, die früher als style= im Markup standen (Akzentfarbe einer Sektion,
   Füllstand eines Balkens). Die Content-Security-Policy lässt style-Attribute nicht zu,
   Zuweisungen über das CSSOM (el.style.…) dagegen schon — deshalb tragen die Elemente
   den Wert als data-Attribut, und dieses Skript setzt ihn. Läuft am Ende des <body>
   synchron (vor dem ersten Zeichnen) und nach jedem htmx-Austausch erneut. */
(function () {
  "use strict";

  function apply(root) {
    root.querySelectorAll("[data-accent]").forEach(function (el) {
      el.style.setProperty("--accent", el.dataset.accent);
    });
    root.querySelectorAll("[data-w]").forEach(function (el) {
      var w = Math.max(0, Math.min(100, parseFloat(el.dataset.w) || 0));
      el.style.width = w + "%";
    });
  }

  apply(document);
  document.addEventListener("htmx:afterSettle", function (ev) { apply(ev.target); });
})();
