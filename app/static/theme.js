(function () {
  "use strict";

  var THEMES = ["hell", "ambient", "dunkel"]; // Reihenfolge = Position im Slider
  var KEY = "dmb-theme";
  var MONO_KEY = "dmb-mono";
  var root = document.documentElement;

  function current() {
    var t = root.dataset.theme;
    return THEMES.indexOf(t) === -1 ? "ambient" : t;
  }

  function apply(theme, persist) {
    root.dataset.theme = theme;
    if (persist) {
      try { localStorage.setItem(KEY, theme); } catch (e) {}
    }
    document.querySelectorAll(".switch-3").forEach(function (slider) {
      slider.style.setProperty("--i", THEMES.indexOf(theme));
      slider.querySelectorAll("button").forEach(function (b) {
        b.setAttribute("aria-checked", String(b.dataset.theme === theme));
      });
    });
  }

  document.querySelectorAll(".switch-3").forEach(function (slider) {
    slider.addEventListener("click", function (ev) {
      var btn = ev.target.closest("button[data-theme]");
      if (btn) apply(btn.dataset.theme, true);
    });

    // Pfeiltasten wie bei einem echten Schieberegler
    slider.addEventListener("keydown", function (ev) {
      var step = ev.key === "ArrowRight" ? 1 : ev.key === "ArrowLeft" ? -1 : 0;
      if (!step) return;
      ev.preventDefault();
      var next = Math.min(THEMES.length - 1, Math.max(0, THEMES.indexOf(current()) + step));
      apply(THEMES[next], true);
      slider.querySelector('button[aria-checked="true"]').focus();
    });
  });

  apply(current(), false); // Thumb/ARIA an das im <head> gesetzte Theme angleichen

  // ---- Logos bunt oder einfarbig (eigener Zwei-Stufen-Schalter)
  var mono = document.getElementById("mono-switch");
  if (mono) {
    function paintMono() {
      var isMono = root.dataset.mono === "1";
      mono.style.setProperty("--i", isMono ? 1 : 0);
      mono.querySelectorAll("button").forEach(function (b) {
        b.setAttribute("aria-checked", String((b.dataset.mono === "1") === isMono));
      });
    }

    mono.addEventListener("click", function (ev) {
      var btn = ev.target.closest("button[data-mono]");
      if (!btn) return;
      if (btn.dataset.mono === "1") root.dataset.mono = "1";
      else delete root.dataset.mono;
      try { localStorage.setItem(MONO_KEY, btn.dataset.mono); } catch (e) {}
      paintMono();
    });

    paintMono();
  }
})();
