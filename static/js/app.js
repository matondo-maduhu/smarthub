// Kubadilisha mandhari (nyeusi/nyeupe)
(function () {
  var btn = document.getElementById("theme-toggle");
  if (!btn) return;
  btn.addEventListener("click", function () {
    var root = document.documentElement;
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch (e) {}
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", next === "dark" ? "#0d1117" : "#ffffff");
  });
})();

// Vichujio vya jamvi na market
(function () {
  function setActive(group, chip) {
    group.querySelectorAll(".chip").forEach(function (c) { c.classList.remove("on"); });
    chip.classList.add("on");
  }

  var tipsGroup = document.querySelector('[data-filter-group="tips"]');
  if (tipsGroup) {
    tipsGroup.addEventListener("click", function (e) {
      var chip = e.target.closest(".chip");
      if (!chip) return;
      setActive(tipsGroup, chip);
      var f = chip.dataset.filter;
      document.querySelectorAll("#tips-list > [data-status]").forEach(function (el) {
        el.classList.toggle("hidden", f !== "all" && el.dataset.status !== f);
      });
    });
  }

  var marketGroup = document.querySelector('[data-filter-group="market"]');
  var search = document.getElementById("market-search");
  var empty = document.getElementById("market-empty");
  var current = "zote";

  function applyMarket() {
    var q = search ? search.value.trim().toLowerCase() : "";
    var shown = 0;
    document.querySelectorAll("#market-list > [data-category]").forEach(function (el) {
      var okCat = current === "zote" || el.dataset.category === current;
      var okText = !q || el.dataset.title.indexOf(q) !== -1;
      var show = okCat && okText;
      el.classList.toggle("hidden", !show);
      if (show) shown++;
    });
    if (empty) empty.classList.toggle("hidden", shown !== 0);
  }

  if (marketGroup) {
    marketGroup.addEventListener("click", function (e) {
      var chip = e.target.closest(".chip");
      if (!chip) return;
      setActive(marketGroup, chip);
      current = chip.dataset.filter;
      applyMarket();
    });
  }
  if (search) search.addEventListener("input", applyMarket);
})();

// Makadirio ya shilingi wakati wa kutoa coin
(function () {
  var a = document.getElementById("toa-amount");
  var out = document.getElementById("toa-tsh");
  if (!a || !out) return;
  var rate = parseInt(a.dataset.rate, 10) || 0;
  function update() {
    var n = parseInt(a.value, 10);
    out.textContent = n > 0 ? (n * rate).toLocaleString("en-US") : "0";
  }
  a.addEventListener("input", update);
  update();
})();

// Ujumbe: kuangalia ujumbe mpya kila sekunde 8 (haufanyi kazi ukurasa ukiwa umefichwa)
(function () {
  var box = document.getElementById("chat-box");
  if (!box) return;
  var url = box.dataset.poll;
  var last = parseInt(box.dataset.last || "0", 10);
  box.scrollTop = box.scrollHeight;

  function add(m) {
    var d = document.createElement("div");
    d.className = "bubble " + (m.mine ? "mine" : "theirs");
    d.dataset.id = m.id;
    var b = document.createElement("div");
    b.className = "prewrap";
    b.textContent = m.body;
    var s = document.createElement("small");
    s.textContent = m.time;
    d.appendChild(b); d.appendChild(s);
    box.appendChild(d);
  }

  function poll() {
    if (document.hidden) return;
    fetch(url + "?baada=" + last, { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (rows) {
        if (!rows.length) return;
        var empty = document.getElementById("chat-empty");
        if (empty) empty.hidden = true;
        var atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
        rows.forEach(function (m) { if (m.id > last) { add(m); last = m.id; } });
        if (atBottom) box.scrollTop = box.scrollHeight;
      })
      .catch(function () {});
  }
  setInterval(poll, 8000);
})();

// Tabo: tab iliyochaguliwa ionekane hata kama orodha inasogezwa
(function () {
  var on = document.querySelector(".chips .chip.on");
  if (on && on.scrollIntoView) on.scrollIntoView({ inline: "center", block: "nearest" });
})();

// Matangazo: kuteleza kiotomatiki kila sekunde 5; kugusa/kuburuta kunasimamisha kwa muda
(function () {
  var box = document.querySelector("[data-ads]");
  if (!box) return;
  var track = box.querySelector(".ads-track");
  var slides = track.children, dots = box.querySelectorAll(".ads-dots i");
  var paused = false, timer = null, resume = null;
  function cur() { return Math.round(track.scrollLeft / (slides[0].offsetWidth + 10)); }
  function go(i) { track.scrollTo({ left: i * (slides[0].offsetWidth + 10), behavior: "smooth" }); }
  track.addEventListener("scroll", function () {
    var c = cur();
    for (var i = 0; i < dots.length; i++) dots[i].className = i === c ? "on" : "";
  }, { passive: true });
  if (slides.length < 2) return;
  function hold() {
    paused = true; clearTimeout(resume);
    resume = setTimeout(function () { paused = false; }, 8000);
  }
  ["touchstart", "pointerdown", "wheel", "mouseenter"].forEach(function (e) { track.addEventListener(e, hold, { passive: true }); });
  if (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  timer = setInterval(function () {
    if (paused || document.hidden) return;
    go((cur() + 1) % slides.length);
  }, 5000);
})();

// Kaunta ya kufungwa kwa mkeka: inahesabu kwa sekunde kutoka muda uliobaki wa seva (si saa ya simu)
(function () {
  var els = document.querySelectorAll("[data-left]:not([data-ads])");
  if (!els.length) return;
  var t0 = Date.now(), done = false;
  function fmt(s) { var m = Math.floor(s / 60), r = s % 60; return (m < 10 ? "0" : "") + m + ":" + (r < 10 ? "0" : "") + r; }
  function tick() {
    var gone = Math.floor((Date.now() - t0) / 1000), expired = false;
    for (var i = 0; i < els.length; i++) {
      var left = parseInt(els[i].getAttribute("data-left"), 10) - gone;
      if (isNaN(left)) continue;
      var b = els[i].querySelector("b");
      if (left <= 0) { expired = true; if (b) b.textContent = "00:00"; els[i].classList.add("expired"); }
      else if (b) { b.textContent = fmt(left); els[i].classList.toggle("urgent", left <= 120); }
    }
    if (expired && !done) { done = true; setTimeout(function () { location.reload(); }, 1500); }
  }
  setInterval(tick, 1000);
})();
