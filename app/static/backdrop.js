/* Hintergrund-Diashow: zwei Ebenen blenden ineinander über.
   Bei einem Bild passiert nichts — das steht schon als CSS-Hintergrund in der Ebene. */
(function () {
  "use strict";

  var el = document.querySelector(".backdrop");
  if (!el) return;

  var images;
  try { images = JSON.parse(el.dataset.images || "[]"); } catch (e) { images = []; }
  if (images.length < 2) return;

  var interval = Math.max(4, parseInt(el.dataset.interval, 10) || 12) * 1000;

  // Zwei Ebenen unter dem Schleier (::after bleibt darüber liegen).
  var layers = images.slice(0, 2).map(function (src, i) {
    var d = document.createElement("div");
    d.className = "bg-layer";
    d.style.backgroundImage = "url('" + src + "')";
    d.style.opacity = i === 0 ? "1" : "0";
    el.appendChild(d);
    return d;
  });

  el.style.backgroundImage = "none";
  images.forEach(function (src) { new Image().src = src; }); // vorladen

  var index = 0, front = 0;

  setInterval(function () {
    if (document.hidden) return;
    index = (index + 1) % images.length;
    var back = 1 - front;
    layers[back].style.backgroundImage = "url('" + images[index] + "')";
    layers[back].style.opacity = "1";
    layers[front].style.opacity = "0";
    front = back;
  }, interval);
})();
