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
