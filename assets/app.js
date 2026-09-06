/* ==== שוק ההון של איציק נידם — לוגיקת אפליקציה ==== */
(function () {
  "use strict";

  document.getElementById("year").textContent = "2026";

  /* ---------- theme ---------- */
  var themeBtn = document.getElementById("theme-toggle");
  var saved = localStorage.getItem("nidam-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
  syncThemeIcon();
  themeBtn.addEventListener("click", function () {
    var cur = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    var next = cur === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("nidam-theme", next);
    syncThemeIcon();
  });
  function syncThemeIcon() {
    var dark = document.documentElement.getAttribute("data-theme") === "dark";
    themeBtn.innerHTML = dark
      ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/><path d="M12 2v2.6M12 19.4V22M4.2 4.2l1.9 1.9M17.9 17.9l1.9 1.9M2 12h2.6M19.4 12H22M4.2 19.8l1.9-1.9M17.9 6.1l1.9-1.9"/></svg>'
      : '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20.5 14.2a8.3 8.3 0 0 1-10.7-10.7 1 1 0 0 0-1.3-1.2 9.7 9.7 0 1 0 13.2 13.2 1 1 0 0 0-1.2-1.3z"/></svg>';
  }

  /* ---------- tabs ---------- */
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tab"));
  tabs.forEach(function (btn) {
    btn.addEventListener("click", function () { activate(btn.dataset.tab); });
  });
  function activate(name) {
    tabs.forEach(function (b) { b.classList.toggle("is-active", b.dataset.tab === name); });
    document.querySelectorAll(".panel").forEach(function (p) {
      p.classList.toggle("is-active", p.id === "panel-" + name);
    });
    markSeen(name);
    updateTodayBarVis();
    // דוח שנטען כשהפאנל היה מוסתר לא הותאם (המדידה נעצרת על clientWidth=0 וה-retries
    // מתפוגגים) — מריצים fit מחדש ברגע שהטאב נפתח והמידות אמיתיות
    requestAnimationFrame(function () {
      document.querySelectorAll("#panel-" + name + " iframe.trd-frame").forEach(function (f) {
        if (window.__fitFrame) window.__fitFrame(f);
      });
    });
    var tw = document.getElementById("ticker-wrap");
    if (tw) tw.style.display = name === "home" ? "block" : "none";
    if (location.hash.slice(1) !== name) {
      history.replaceState(null, "", "#" + name);
      // GoatCounter: ספירת מעבר-טאב כצפיית-עמוד (הכניסה הראשונית נספרת אוטומטית)
      if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: "/" + name });
    }
  }

  /* ---- live market ticker (our own strip, from data/market.json via Yahoo) ---- */
  function fmtQuote(v) {
    if (v == null || isNaN(v)) return "—";
    var d = Math.abs(v) < 10 ? 3 : 2;
    return Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: d });
  }
  var PIN_KEYS = { es: 1, nq: 1, usdils: 1 };   // בשורה הקבועה, לא ברצועה הנעה
  function mtItem(it) {
    var c = it.chg, cls = c > 0 ? "up" : (c < 0 ? "down" : ""), arr = c > 0 ? "▲" : (c < 0 ? "▼" : "");
    var chg = (c == null) ? "" :
      ' <span class="mt-chg ' + cls + '">' + arr + " " + (c > 0 ? "+" : "") + Number(c).toFixed(2) + "%</span>";
    return '<span class="mt-item"><span class="mt-label">' + esc(it.label) + "</span>" +
      '<span class="mt-price num">' + fmtQuote(it.price) + "</span>" + chg + "</span>";
  }
  function tickSpark(sp, up) {
    if (!sp || sp.length < 2) return "";
    var min = Math.min.apply(null, sp), max = Math.max.apply(null, sp);
    if (max === min) max = min + 1;
    var W = 64, Hh = 26;
    var pts = sp.map(function (v, i) {
      return (i * (W / (sp.length - 1))).toFixed(1) + "," + (Hh - 3 - ((v - min) / (max - min)) * (Hh - 6)).toFixed(1);
    });
    var col = up ? "var(--up)" : "var(--down)";
    return '<svg class="np-blk-spark" viewBox="0 0 64 26" preserveAspectRatio="none">' +
      '<polygon points="0,' + Hh + " " + pts.join(" ") + " " + W + "," + Hh + '" fill="' + col + '" opacity=".12"/>' +
      '<polyline points="' + pts.join(" ") + '" fill="none" stroke="' + col + '" stroke-width="1.6"/></svg>';
  }
  function renderMarketTicker(el, data) {
    if (!el || !data || !data.items || !data.items.length) return;
    // שתי שורות רזות: עליונה = המדדים (SPY→DXY מימין), תחתונה = חוזים + דולר/שקל
    function tick(it) {
      var c = it.chg, cls = c > 0 ? "up" : (c < 0 ? "down" : ""), arr = c > 0 ? "▲" : (c < 0 ? "▼" : "");
      return '<span class="np-tick"><b>' + esc(it.label) + "</b> " +
        '<span class="v num">' + fmtQuote(it.price) + "</span>" +
        (c == null ? "" : ' <span class="c num ' + cls + '" dir="ltr">' + arr + (c > 0 ? "+" : "") + Number(c).toFixed(2) + "%</span>") +
        "</span>";
    }
    var idx = [], futs = [];
    data.items.forEach(function (it) { (PIN_KEYS[it.key] ? futs : idx).push(it); });
    var sep = '<span class="np-sep">·</span>';
    el.innerHTML =
      '<div class="np-line">' + idx.map(tick).join(sep) + "</div>" +
      '<div class="np-line">' + futs.map(tick).join(sep) + "</div>";
  }
  var TICKD = null;
  function loadTicker() {
    var el = document.getElementById("ticker");
    if (!el) return;
    fetchJSON("data/market.json")
      .then(function (d) { TICKD = d; renderMarketTicker(el, d); refreshTickerLive(); })
      .catch(function () {});
  }
  /* עדכון חי מהסורק של TradingView (CORS פתוח כ-simple request) — מחירים כל דקה;
     הגרפים-המיניים נשארים מהשרת (15 דק'). tnx לא זמין בסורק ונשאר בקצב השרת. */
  function refreshTickerLive() {
    if (!TICKD) return;
    var reqs = [
      ["https://scanner.tradingview.com/america/scan",
       { symbols: { tickers: ["AMEX:SPY", "NASDAQ:QQQ", "AMEX:IWM", "TVC:VIX", "TVC:DXY"] },
         columns: ["name", "close", "change", "premarket_close", "premarket_change", "postmarket_close", "postmarket_change"] },
       { SPY: "spy", QQQ: "qqq", IWM: "iwm", VIX: "vix", DXY: "dxy" }],
      ["https://scanner.tradingview.com/futures/scan",
       { symbols: { tickers: ["CME_MINI:ES1!", "CME_MINI:NQ1!"] }, columns: ["name", "close", "change"] },
       { "ES1!": "es", "NQ1!": "nq" }],
      ["https://scanner.tradingview.com/forex/scan",
       { symbols: { tickers: ["FX_IDC:USDILS"] }, columns: ["name", "close", "change"] },
       { USDILS: "usdils" }]
    ];
    var byKey = {};
    TICKD.items.forEach(function (it) { byKey[it.key] = it; });
    var ses = jsSession();
    reqs.forEach(function (r) {
      fetch(r[0], { method: "POST", body: JSON.stringify(r[1]) })
        .then(function (x) { return x.json(); })
        .then(function (d) {
          (d.data || []).forEach(function (row) {
            var v = row.d, key = r[2][v[0]], it = key && byKey[key];
            if (!it) return;
            var px = v[1], chg = v[2];
            // מניות/קרנות מחוץ לשעות המסחר — מחיר פרה/אפטר אם קיים
            if (v.length > 3) {
              if (ses === "pre" && v[4] != null) { px = v[3] != null ? v[3] : px; chg = v[4]; }
              else if (ses === "post" && v[6] != null) { px = v[5] != null ? v[5] : px; chg = v[6]; }
            }
            if (px != null) it.price = px;
            if (chg != null) it.chg = Math.round(chg * 100) / 100;
          });
          renderMarketTicker(document.getElementById("ticker"), TICKD);
        })
        .catch(function () {});
    });
  }

  /* מפת חום סקטוריאלית חיה — 11 תעודות סקטור SPDR, ברייל מתחת למד (עדכון כל דקה) */
  var SECTOR_ETFS = [
    ["XLK", "טכנולוגיה"], ["XLF", "פיננסים"], ["XLV", "בריאות"], ["XLY", "צריכה מחזורית"],
    ["XLC", "תקשורת"], ["XLI", "תעשייה"], ["XLP", "צריכה בסיסית"], ["XLE", "אנרגיה"],
    ["XLB", "חומרים"], ["XLU", "תשתיות"], ["XLRE", "נדל\"ן"]
  ];
  var HEAT = {};
  function refreshHeat() {
    if (!document.getElementById("np-heat")) return;
    var ses = jsSession();
    fetch("https://scanner.tradingview.com/america/scan", {
      method: "POST",
      body: JSON.stringify({
        symbols: { tickers: SECTOR_ETFS.map(function (s) { return "AMEX:" + s[0]; }) },
        columns: ["name", "close", "change", "premarket_close", "premarket_change", "postmarket_close", "postmarket_change"]
      })
    })
      .then(function (x) { return x.json(); })
      .then(function (d) {
        (d.data || []).forEach(function (row) {
          var v = row.d, chg = v[2];
          if (ses === "pre" && v[4] != null) chg = v[4];
          else if (ses === "post" && v[6] != null) chg = v[6];
          if (chg != null) HEAT[v[0]] = Math.round(chg * 100) / 100;
        });
        renderHeat();
      })
      .catch(function () {});
  }
  function renderHeat() {
    var el = document.getElementById("np-heat");
    if (!el) return;
    var ses = jsSession();
    var rows = SECTOR_ETFS
      .filter(function (s) { return HEAT[s[0]] != null; })
      .sort(function (a, b) { return HEAT[b[0]] - HEAT[a[0]]; });
    if (!rows.length) { el.innerHTML = ""; return; }
    var tiles = rows.map(function (s) {
      var c = HEAT[s[0]];
      var mag = Math.min(Math.abs(c) / 2, 1);   // רוויה מלאה בתנועה של 2%
      var base = c >= 0 ? "var(--up)" : "var(--down)";
      var mix = Math.round(8 + mag * 26);
      return '<button class="ht-tile" style="background:color-mix(in srgb, ' + base + " " + mix + '%, var(--bg))" ' +
        "onclick=\"__goTab('indices')\" title=\"" + s[0] + '">' +
        '<span class="ht-name">' + esc(s[1]) + "</span>" +
        '<b class="ht-chg num ' + (c >= 0 ? "up" : "down") + '" dir="ltr">' + (c > 0 ? "+" : "") + c.toFixed(2) + "%</b></button>";
    }).join("");
    var lbl = ses === "regular" ? "עדכון חי" : ses === "pre" ? "פרה-מרקט" : ses === "post" ? "אפטר-מרקט" : "סגירה אחרונה";
    el.innerHTML = '<span class="np-k">מפת הסקטורים<br><span class="ht-ses">' + lbl + "</span></span>" +
      '<div class="ht-grid">' + tiles + "</div>";
  }

  /* "מה השווקים מהמרים" — כרטיסי מגמה אחידים (data/bets.json + history) */
  function betSpark(h, dir) {
    var W = 160, H = 56;
    var min = Math.min.apply(null, h), max = Math.max.apply(null, h);
    if (max - min < 4) { var mid = (max + min) / 2; min = mid - 2; max = mid + 2; }
    var pts = h.map(function (v, i) {
      return [(i * (W / (h.length - 1))).toFixed(1), ((H - 8) - ((v - min) / (max - min)) * (H - 20)).toFixed(1)];
    });
    var line = pts.map(function (p) { return p[0] + "," + p[1]; }).join(" ");
    var col = dir === "up" ? "var(--up)" : dir === "down" ? "var(--down)" : "var(--accent)";
    var last = pts[pts.length - 1];
    return '<div class="bt2-chart"><svg viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="none">' +
      '<polygon points="0,' + H + " " + line + " " + W + "," + H + '" fill="' + col + '" fill-opacity=".13"/>' +
      '<polyline points="' + line + '" fill="none" stroke="' + col + '" stroke-width="2"/>' +
      '<circle cx="' + last[0] + '" cy="' + last[1] + '" r="3" fill="' + col + '"/></svg></div>';
  }
  function renderBets(d) {
    var el = document.getElementById("home-bets");
    if (!el) return;
    if (!d || !(d.rows || []).length) { el.innerHTML = ""; return; }
    var hist = d.history || {};
    // "המהלך של היום" — התזוזה היומית הגדולה ביותר (5 נק'+ לפחות)
    var hotKey = null, hotAbs = 5;
    d.rows.forEach(function (r) {
      if (r.chg != null && Math.abs(r.chg) >= hotAbs) { hotAbs = Math.abs(r.chg); hotKey = r.key; }
    });
    var cards = d.rows.map(function (r) {
      var chg;
      if (r.chg == null || Math.abs(r.chg) < 0.5) {
        chg = '<span class="bt2-chg flat">0 היום</span>';
      } else {
        chg = '<span class="bt2-chg ' + (r.chg > 0 ? "up" : "down") + '"><span class="num" dir="ltr">' +
          (r.chg > 0 ? "▲+" : "▼−") + Math.abs(r.chg).toFixed(0) + "</span> היום</span>";
      }
      var sub = esc(r.sub);
      var journey = "", chart = "";
      var h = (hist[r.key] || []).map(function (e) { return e.pct; });
      if (h.length >= 2) {
        var diff = h[h.length - 1] - h[0];
        var dir = diff > 1.5 ? "up" : diff < -1.5 ? "down" : "flat";
        var arr = { up: "↗", down: "↘", flat: "→" }[dir];
        journey = '<span class="bt2-journey">' + h.length + ' ימים: <span class="num" dir="ltr">' + h[0] +
          '%</span> <span class="arr ' + dir + '">' + arr + '</span> <span class="num" dir="ltr">' + h[h.length - 1] + "%</span></span>";
        chart = betSpark(h, dir);
      }
      var hot = r.key === hotKey;
      // כרטיס לחיץ כשיש קישור למקור (Polymarket/Kalshi) — אחרת div רגיל (עמידות
      // לנתוני bets.json ישנים שנוצרו לפני שהוספנו את השדה)
      var tag = r.url ? "a" : "div";
      var open = r.url
        ? '<a class="bt2-card' + (hot ? " hot" : "") + '" href="' + esc(r.url) + '" target="_blank" rel="noopener" title="פתיחה ב' + esc(r.src || "מקור ההימור") + '">'
        : '<div class="bt2-card' + (hot ? " hot" : "") + '">';
      return open +
        (hot ? '<span class="bt2-hot">🔥 המהלך של היום</span>' : "") +
        '<span class="bt2-label">' + esc(r.label) + "</span>" +
        '<div class="bt2-now"><b class="num">' + r.pct + "%</b>" + chg + "</div>" +
        '<span class="bt2-sub">' + sub + "</span>" +
        journey + chart +
        "</" + tag + ">";
    }).join("");
    el.innerHTML =
      '<div class="card"><span class="np-k" style="margin-bottom:10px">🎲 מה השווקים מהמרים</span>' +
      '<div class="bt2-grid">' + cards + "</div>" +
      '<p class="stamp" style="margin:12px 0 0">מחירי שוקי חיזוי (Polymarket / Kalshi) = ההסתברות שהשוק מתמחר · מתעדכן כל רבע שעה · הגרף: הימים האחרונים</p></div>';
  }

  /* ---- חיפוש כלל-אתרי: סורק את כל הנתונים שכבר בזיכרון הדפדפן (בלי שרת) ---- */
  function tickerCard(sym) {
    var hits = [];
    var st = null;
    ((MOMD && MOMD.stocks) || []).forEach(function (s) { if (s.symbol === sym) st = s; });
    if (st) hits.push(["momentum", "מומנטום · " + st.signal_count + " סיגנלים · " + (st.change_pct > 0 ? "+" : "") + st.change_pct + "%"]);
    ((CANDD && CANDD.candidates) || []).forEach(function (c) {
      if (c.symbol === sym) hits.push(["candidates", "מועמדת #" + c.rank + " · כניסה " + c.entry + " · יעד " + Math.round(c.target * 100) / 100]);
    });
    var MVL = { gainers: "עולות", losers: "יורדות", active: "פעילות" };
    Object.keys(MVL).forEach(function (g) {
      ((MOVERS && MOVERS[g]) || []).forEach(function (x) {
        if (x.symbol === sym) hits.push(["home", "בולטת היום (" + MVL[g] + ") · " + (x.chg > 0 ? "+" : "") + x.chg + "%"]);
      });
    });
    var w = EARN && EARN.window && EARN.window[sym];
    if (w) hits.push(["weekcal", "📅 מדווחת ב-" + fmtTradeDate(w)]);
    else ((EARN && EARN.week) || []).forEach(function (d) {
      (d.companies || []).forEach(function (c) { if (c.ticker === sym) hits.push(["weekcal", "📅 בלוח הדיווחים · " + d.label]); });
    });
    ((REPD && REPD.reports) || []).forEach(function (r) { if (r.ticker === sym) hits.push(["reports", "📑 " + r.title]); });
    var mentions = 0;
    ((PULSE_X && PULSE_X.items) || []).forEach(function (it) {
      if (new RegExp("(^|[^A-Za-z])\\$?" + sym + "([^A-Za-z]|$)").test(it.text || "")) mentions++;
    });
    if (mentions) hits.push(["home", "💬 מוזכרת ב-" + mentions + " ציוצים בבזק מהרשת"]);
    return hits;
  }
  function searchSite(q) {
    var rows = [];
    var ql = q.toLowerCase();
    function push(group, tab, text) {
      if (text && String(text).toLowerCase().indexOf(ql) >= 0 && rows.length < 22) {
        var cnt = 0;
        rows.forEach(function (r) { if (r[0] === group) cnt++; });
        if (cnt < 4) rows.push([group, tab, String(text).slice(0, 105)]);
      }
    }
    ((MOMD && MOMD.stocks) || []).forEach(function (s) { push("מומנטום", "momentum", s.name + " (" + s.symbol + ")"); });
    ["gainers", "losers", "active"].forEach(function (g) {
      ((MOVERS && MOVERS[g]) || []).forEach(function (x) { push("בולטות", "home", x.name + " (" + x.symbol + ")"); });
    });
    ((EARN && EARN.week) || []).forEach(function (d) {
      (d.companies || []).forEach(function (c) { push("דיווחים", "weekcal", c.name + " (" + c.ticker + ") · " + d.label); });
    });
    ((REPD && REPD.reports) || []).forEach(function (r) { push("דוחות", "reports", r.title + " (" + r.ticker + ")"); });
    ((TRAD && TRAD.reports) || []).forEach(function (r) { push("הצעות לטרייד", "trades", r.title); });
    if (BRIEF) ["morning", "afternoon"].forEach(function (k) {
      var s = BRIEF[k] || {};
      (s.headlines || []).forEach(function (h) { push("תדרוך", "briefing", h); });
      (s.schedule || []).forEach(function (it) { if (it.text) push("תדרוך", "briefing", (it.time ? it.time + " · " : "") + it.text); });
    });
    ((NEWS && NEWS.news) || []).forEach(function (n) { push("חדשות", "home", n.titleEn || n.title); });
    ((PULSE_X && PULSE_X.items) || []).forEach(function (it) { push("בזק מהרשת", "home", it.text + " · " + it.source); });
    ((ECON && ECON.events) || []).forEach(function (e) {
      push("מאקרו", "home", e.he + " (" + e.ilDate + ") · צפי " + (e.forecast || "—") + (e.actual ? " · בפועל " + e.actual : ""));
    });
    if (CA) {
      push("הניתוח היומי", "indices", CA.headline);
      (CA.paragraphs || []).forEach(function (p) { push("הניתוח היומי", "indices", p); });
    }
    return rows;
  }
  function srQuote(sym) {
    fetch("https://scanner.tradingview.com/america/scan", {
      method: "POST",
      body: JSON.stringify({
        filter: [{ left: "name", operation: "in_range", right: [sym] },
                 { left: "exchange", operation: "in_range", right: ["NASDAQ", "NYSE", "AMEX"] }],
        columns: ["name", "close", "change"], range: [0, 3]
      })
    }).then(function (x) { return x.json(); }).then(function (d) {
      var row = (d.data || [])[0];
      var el = document.getElementById("sr-quote");
      if (!row || !el) return;
      var px = row.d[1], chg = row.d[2];
      el.innerHTML = '<b class="num">' + fmtQuote(px) + "</b> " +
        '<span class="num ' + (chg >= 0 ? "up" : "down") + '" dir="ltr">' + (chg > 0 ? "+" : "") + Number(chg).toFixed(2) + "%</span>";
    }).catch(function () {});
  }
  function renderSearch(q) {
    var panel = document.getElementById("search-results");
    if (!panel) return;
    q = (q || "").trim();
    if (q.length < 2) { panel.hidden = true; return; }
    var html = "";
    var isTicker = /^[A-Za-z][A-Za-z.\-]{0,5}$/.test(q);
    if (isTicker) {
      var sym = q.toUpperCase();
      var hits = tickerCard(sym);
      html += '<div class="sr-tick"><div class="sr-tick-h"><b dir="ltr">' + esc(sym) + '</b><span id="sr-quote" class="sr-q"></span>' +
        '<a href="https://www.tradingview.com/symbols/' + encodeURIComponent(sym) + '/" target="_blank" rel="noopener">גרף ↗</a></div>' +
        (hits.length
          ? hits.map(function (h) {
              return '<button class="sr-item" data-tab="' + h[0] + '">' + esc(h[1]) + "</button>";
            }).join("")
          : '<div class="sr-none">לא נמצאת כרגע באף לוח באתר</div>') +
        "</div>";
    }
    var rows = searchSite(q);
    var lastG = "";
    rows.forEach(function (r) {
      if (r[0] !== lastG) { html += '<div class="sr-group">' + esc(r[0]) + "</div>"; lastG = r[0]; }
      html += '<button class="sr-item" data-tab="' + r[1] + '">' + esc(r[2]) + "</button>";
    });
    if (!html) html = '<div class="sr-none">לא נמצאו תוצאות ל-"' + esc(q) + '"</div>';
    panel.innerHTML = html;
    panel.hidden = false;
    if (isTicker) srQuote(q.toUpperCase());
    panel.querySelectorAll(".sr-item").forEach(function (b) {
      b.addEventListener("click", function () {
        panel.hidden = true;
        var inp = document.getElementById("site-search");
        if (inp) inp.blur();
        activate(b.dataset.tab);
      });
    });
  }
  function initSearch() {
    var inp = document.getElementById("site-search");
    var panel = document.getElementById("search-results");
    if (!inp || !panel) return;
    var deb = null;
    inp.addEventListener("input", function () {
      clearTimeout(deb);
      deb = setTimeout(function () { renderSearch(inp.value); }, 180);
    });
    inp.addEventListener("focus", function () { if (inp.value.trim().length >= 2) renderSearch(inp.value); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "/" && document.activeElement !== inp &&
          !/INPUT|TEXTAREA/.test((document.activeElement || {}).tagName || "")) {
        e.preventDefault(); inp.focus();
      }
      if (e.key === "Escape") { panel.hidden = true; inp.blur(); }
    });
    document.addEventListener("click", function (e) {
      if (!e.target.closest(".np-search")) panel.hidden = true;
    });
  }

  /* ---- tab badge: green dot only when a category's CONTENT actually changed since you viewed it ---- */
  var SIGS = {};
  function contentSig(d) {
    if (d == null) return "";
    var s;
    // hash the real content, skipping volatile _meta (updatedAt changes on every fetch → false "new")
    try { s = JSON.stringify(d, function (k, v) { return k === "_meta" ? undefined : v; }); }
    catch (e) { s = String((d && d.date) || ""); }
    var h = 5381, i = s.length;
    while (i) { h = (h * 33) ^ s.charCodeAt(--i); }
    return (h >>> 0).toString(36);
  }
  function noteSig(tab, d) {
    var sig = contentSig(d);
    if (!sig) return;
    SIGS[tab] = sig;
    var key = "cseen-" + tab;   // content-seen (fresh baseline; ignores old timestamp-based keys)
    var seen = localStorage.getItem(key);
    if (seen === null) { localStorage.setItem(key, sig); return; } // first visit = baseline, no dot
    if (seen !== sig) {
      var btn = document.querySelector('.tab[data-tab="' + tab + '"]');
      var active = btn && btn.classList.contains("is-active");
      if (btn && !btn.querySelector(".tab-badge") && !active) {
        var dot = document.createElement("span");
        dot.className = "tab-badge";
        btn.appendChild(dot);
      }
    }
  }
  function markSeen(tab) {
    if (SIGS[tab]) localStorage.setItem("cseen-" + tab, SIGS[tab]);
    var btn = document.querySelector('.tab[data-tab="' + tab + '"]');
    var b = btn && btn.querySelector(".tab-badge");
    if (b) b.remove();
  }

  /* ---- "what's new today" bar (home only) ---- */
  function renderTodayBar(el, health) {
    if (!el) return;
    var items = (health && health.today) || [];
    if (!items.length) { el.dataset.has = "0"; updateTodayBarVis(); return; }
    var parts = items.map(function (it) {
      if (it.arrived && it.time) {
        return '<button class="tu-item" onclick="__goTab(\'' + it.tab + '\')">' +
          '<span class="tu-time">' + esc(it.time) + "</span>" + esc(it.label) + "</button>";
      }
      return '<span class="tu-item tu-wait">' + esc(it.label) + " · ממתין</span>";
    }).join("");
    el.innerHTML = '<span class="tu-lead">🆕 היום</span>' + parts;
    el.dataset.has = "1";
    updateTodayBarVis();
  }
  function updateTodayBarVis() {
    var el = document.getElementById("today-bar");
    if (!el) return;
    var act = document.querySelector(".tab.is-active");
    var onHome = act && act.dataset.tab === "home";
    el.style.display = (onHome && el.dataset.has === "1") ? "flex" : "none";
  }
  // expose for CTA buttons
  window.__goTab = activate;

  /* ---- גרף בלחיצה: מודאל TradingView (SMA 20/50/200 + ווליום) לכל טיקר באתר ----
     כל טיקר באתר כבר מקושר ל-tradingview.com/symbols/SYM — מיירטים את הקליק
     ופותחים חלונית במקום לנווט החוצה. tv.js נטען פעם אחת, רק בלחיצה הראשונה. */
  var TV_SYM_RE = /tradingview\.com\/symbols\/([^/?#]+)/;
  function ensureTvLib(cb) {
    if (window.TradingView && window.TradingView.widget) { cb(); return; }
    var s = document.createElement("script");
    s.src = "https://s3.tradingview.com/tv.js";
    s.onload = cb;
    s.onerror = function () {
      var b = document.querySelector("#tvm-wrap .tvm-body");
      if (b) b.innerHTML = '<div class="tvm-err">טעינת הגרף נכשלה — בדקו חיבור לאינטרנט</div>';
    };
    document.head.appendChild(s);
  }
  function closeChart() {
    var w = document.getElementById("tvm-wrap");
    if (w) w.remove();
    document.body.style.overflow = "";
    document.removeEventListener("keydown", escChart);
  }
  function escChart(e) { if (e.key === "Escape") closeChart(); }
  function openChart(sym) {
    closeChart();
    var wrap = document.createElement("div");
    wrap.id = "tvm-wrap";
    wrap.innerHTML =
      '<div class="tvm-box" role="dialog" aria-modal="true" aria-label="גרף ' + esc(sym) + '">' +
        '<div class="tvm-head">' +
          '<b class="tvm-sym" dir="ltr">' + esc(sym) + "</b>" +
          '<span class="tvm-note">ממוצעים <b style="color:#43a047">20</b> · <b style="color:#1e88e5">50</b> · <b style="color:#e53935">200</b> + ווליום</span>' +
          '<a class="tvm-full" href="https://www.tradingview.com/symbols/' + encodeURIComponent(sym) +
            '/" target="_blank" rel="noopener">פתיחה מלאה ↗</a>' +
          '<button class="tvm-x" type="button" aria-label="סגירה">✕</button>' +
        "</div>" +
        '<div class="tvm-body"><div class="tvm-load">טוען גרף…</div><div id="tvm-chart"></div></div>' +
      "</div>";
    document.body.appendChild(wrap);
    document.body.style.overflow = "hidden";
    wrap.addEventListener("click", function (e) { if (e.target === wrap) closeChart(); });
    wrap.querySelector(".tvm-x").addEventListener("click", closeChart);
    document.addEventListener("keydown", escChart);
    ensureTvLib(function () {
      if (!document.getElementById("tvm-chart")) return; // המודאל נסגר בזמן הטעינה
      new window.TradingView.widget({
        container_id: "tvm-chart",
        symbol: sym,
        interval: "D",
        autosize: true,
        timezone: "Asia/Jerusalem",
        theme: document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light",
        style: "1",
        locale: "en",
        hide_side_toolbar: true,
        allow_symbol_change: false,
        withdateranges: true,
        // שלושה סוגי-ממוצע שונים בכוונה: צביעת overrides היא פר-סוג אינדיקטור
        // (כל מופעי אותו סוג חולקים צבע), אז צבע נפרד לכל קו מחייב EMA/WMA/SMA.
        // שם ה-plot של הממוצעים הוא "ma" — "plot" לא נתפס (נבדק אמפירית).
        studies: [
          { id: "MAExp@tv-basicstudies", inputs: { length: 20 } },
          { id: "MAWeighted@tv-basicstudies", inputs: { length: 50 } },
          { id: "MASimple@tv-basicstudies", inputs: { length: 200 } },
        ],
        studies_overrides: {
          "moving average exponential.ma.color": "#43a047",
          "moving average exponential.ma.linewidth": 2,
          "moving average weighted.ma.color": "#1e88e5",
          "moving average weighted.ma.linewidth": 2,
          "moving average.ma.color": "#e53935",
          "moving average.ma.linewidth": 2,
        },
      });
    });
  }
  document.addEventListener("click", function (e) {
    var t = e.target;
    var a = t && t.closest ? t.closest('a[href*="tradingview.com/symbols/"]') : null;
    if (!a || a.classList.contains("tvm-full")) return;
    var m = TV_SYM_RE.exec(a.getAttribute("href") || "");
    if (!m) return;
    e.preventDefault();
    openChart(decodeURIComponent(m[1]));
  });

  /* טיקרים בתוך דוחות ה-iframe (הצעות לטרייד / סקטורים): הדוחות מגיעים כ-HTML
     חיצוני בלי לינקים — סורקים את הטקסט אחרי טעינה (same-origin), עוטפים טיקרים
     ב-span לחיץ שפותח את מודאל הגרף. יקום מוכר → לחיץ תמיד; אחרת היוריסטיקה:
     2-5 אותיות גדולות שאינן מונח מסחר/מאקרו מוכר. כשל בסריקה משאיר את הדוח כרגיל. */
  var TK_STOP = {};
  ("RSI EMA SMA ATR MACD VWAP ADX OBV CCI MFI HOD LOD EOD ATH ATL PT TP SL RR BUY SELL HOLD STOP ENTRY EXIT SETUP SWING RISK GAP AVG MAX MIN MID VOL PE EPS PEG ROE ROI YOY QOQ YTD TTM GDP CPI PPI PCE NFP PMI ISM FED FOMC ECB BOJ USD EUR ILS GBP JPY CEO CFO CTO IPO ETF ETN ADR AI IT US USA UK EU NY NYSE AMEX OTC LLC INC CORP LTD PLC AM PM ET EST EDT GMT UTC OK NA TBD HTML CSS URL API PDF CSV JSON HTTP WWW II III IV DATE TIME NAME PRICE LONG SHORT NEW ALL LOW HIGH OPEN BRIEF DAILY WATCH CHART TREND NOTE NOTES PLAN")
    .split(" ").forEach(function (w) { TK_STOP[w] = 1; });
  function tickerUniverse() {
    var set = {};
    function add(s) { if (s) set[String(s).toUpperCase()] = 1; }
    ((MOMD && MOMD.stocks) || []).forEach(function (s) { add(s.symbol); });
    ((CANDD && CANDD.candidates) || []).forEach(function (c) { add(c.symbol); });
    if (MOVERS) ["gainers", "losers", "active"].forEach(function (g) {
      (MOVERS[g] || []).forEach(function (x) { add(x.symbol); });
    });
    Object.keys(EARNW || {}).forEach(add);
    Object.keys(FOCUSQ || {}).forEach(add);
    (typeof SECTOR_ETFS !== "undefined" ? SECTOR_ETFS : []).forEach(function (s) { add(s[0]); });
    return set;
  }
  var TK_RE = /\b[A-Z]{2,5}(?:\.[A-Z])?\b/g;
  window.__linkTickers = function (f) {
    try {
      var doc = f.contentWindow.document;
      if (!doc || !doc.body || doc.getElementById("np-tk-style")) return;
      var st = doc.createElement("style");
      st.id = "np-tk-style";
      st.textContent = ".np-tk{cursor:pointer;text-decoration:underline dotted;text-underline-offset:2px}" +
        ".np-tk:hover{opacity:.72}";
      (doc.head || doc.body).appendChild(st);
      var known = tickerUniverse();
      var walker = doc.createTreeWalker(doc.body, 4 /* SHOW_TEXT */, null);
      var nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      nodes.forEach(function (n) {
        var p = n.parentNode;
        if (!p || !p.nodeName) return;
        var tag = p.nodeName.toLowerCase();
        if (tag === "script" || tag === "style" || tag === "a" || tag === "title") return;
        if (p.className && String(p.className).indexOf("np-tk") >= 0) return;
        var txt = n.nodeValue;
        if (!txt || !/[A-Z]/.test(txt)) return;
        var frag = null, last = 0, m;
        TK_RE.lastIndex = 0;
        while ((m = TK_RE.exec(txt))) {
          var w = m[0], core = w.replace(/\.[A-Z]$/, "");
          if (!(known[w] || known[core] || !TK_STOP[core])) continue;
          if (!frag) frag = doc.createDocumentFragment();
          if (m.index > last) frag.appendChild(doc.createTextNode(txt.slice(last, m.index)));
          var s = doc.createElement("span");
          s.className = "np-tk";
          s.setAttribute("data-sym", w);
          s.textContent = w;
          frag.appendChild(s);
          last = m.index + w.length;
        }
        if (frag) {
          if (last < txt.length) frag.appendChild(doc.createTextNode(txt.slice(last)));
          p.replaceChild(frag, n);
        }
      });
      doc.body.addEventListener("click", function (e) {
        var t = e.target;
        while (t && t !== doc.body && !(t.getAttribute && t.getAttribute("data-sym"))) t = t.parentNode;
        var sym = t && t.getAttribute && t.getAttribute("data-sym");
        if (sym) { e.preventDefault(); openChart(sym); }
      });
    } catch (err) { /* דוח בפורמט חריג — נשאר בלי לינקים */ }
  };
  // התאמת iframe של דוחות רחבים: אם התוכן רחב מהמסך (טבלאות/גרפים) — מכווצים
  // כך שהדוח כולו נכנס ברוחב המסך (ומשם פינץ'-זום מגדיל).
  // הכיווץ הוא transform:scale על מעטפת בתוך המסמך, לא zoom: ב-WebKit ה-zoom משנה
  // layout (פונטים זעירים מעוגלים כלפי מעלה) כך שהמסמך המכווץ נשאר רחב ~30% מהמדידה
  // — ב-iOS ה-iframe התנפח לרוחב הזה, חתך את צד ימין וריצד בגלילה. transform לא
  // נוגע ב-layout, אז המדידה נכונה תמיד; קיבוע html/body לגודל הוויזואלי מונע
  // מ-iOS לנפח את ה-iframe לגודל התוכן (הניפוח נגזר מגודל הגלילה של המסמך).
  window.__fitFrame = function (f) {
    window.__linkTickers(f);
    function fit() {
      try {
        var doc = f.contentWindow.document;
        var wrap = f.parentElement;
        if (!doc || !doc.body || !wrap) return;
        var root = doc.documentElement;
        // iOS מנפח פונטים בדפים רחבים ("עזרה" של WebKit) — ביטול מפורש בתוך המסמך:
        if (!doc.getElementById("np-fit-style") && doc.head) {
          var st = doc.createElement("style");
          st.id = "np-fit-style";
          st.textContent = "html,body{-webkit-text-size-adjust:100%!important;text-size-adjust:100%!important}";
          doc.head.appendChild(st);
        }
        // פאנל מוסתר (מעבר טאב באמצע ה-retries) — מדידה על clientWidth=0 מקולקלת
        if (!wrap.clientWidth) return;
        // עטיפה חד-פעמית של תוכן המסמך במיכל שה-scale מוחל עליו
        var sc = doc.getElementById("np-fit-scaler");
        if (!sc) {
          sc = doc.createElement("div");
          sc.id = "np-fit-scaler";
          while (doc.body.firstChild) sc.appendChild(doc.body.firstChild);
          doc.body.appendChild(sc);
        }
        var avail = wrap.clientWidth;
        var prevScale = f.__scale || 1;
        // רוחב התוכן: scrollWidth לא מושפע מ-transform; מידות rect כן — מנרמלים בסקייל.
        // מעטפות שממרכזות קופסה ברוחב קבוע (Bundled Page) מסתירות גלישה מ-scrollWidth,
        // לכן נמדדים גם ילדים ונכדים. natural רק גדל (פונטים מאוחרים) — לעולם לא מתכווץ.
        var natural = f.__nat || 0;
        if (!sc.style.width) natural = Math.max(natural, sc.scrollWidth);
        var kids = sc.children;
        for (var i = 0; i < kids.length && i < 20; i++) {
          natural = Math.max(natural, kids[i].scrollWidth, kids[i].getBoundingClientRect().width / prevScale);
          var g = kids[i].children;
          for (var j = 0; j < g.length && j < 30; j++)
            natural = Math.max(natural, g[j].scrollWidth, g[j].getBoundingClientRect().width / prevScale);
        }
        natural = Math.ceil(natural);
        f.__nat = natural;
        var s = natural > avail + 12 ? avail / natural : 1;
        f.__scale = s;
        var h;
        if (s < 1) {
          sc.style.width = natural + "px";
          // העוגן לפי כיוון המסמך: דוח RTL צמוד ימינה (מקבעים את הקצה הימני),
          // דוח LTR צמוד שמאלה — origin שגוי מזיז את כל התוכן אל מחוץ למסך
          var dir = f.contentWindow.getComputedStyle(doc.body).direction;
          sc.style.transformOrigin = "top " + (dir === "ltr" ? "left" : "right");
          sc.style.transform = "scale(" + s + ")";
          h = Math.ceil(sc.getBoundingClientRect().height); // גובה ויזואלי (אחרי scale)
          root.style.width = doc.body.style.width = avail + "px";
          root.style.height = doc.body.style.height = h + "px";
          root.style.overflow = doc.body.style.overflow = "hidden";
        } else {
          sc.style.transform = sc.style.width = "";
          root.style.width = doc.body.style.width = "";
          root.style.height = doc.body.style.height = "";
          root.style.overflow = doc.body.style.overflow = "";
          h = Math.ceil(sc.getBoundingClientRect().height);
        }
        f.style.width = "100%";
        f.style.height = (h + 24) + "px";
      } catch (e) {}
    }
    fit();
    [400, 1200, 2500, 5000].forEach(function (ms) { setTimeout(fit, ms); });
    if (!f.__fitBound) {
      f.__fitBound = true;
      // ספארי iOS יורה resize על כיווץ שורת הכתובת תוך כדי גלילה; ה-fit היה
      // מאפס את ה-zoom באמצע גלילה והדוח נשאר רחב וחתוך — מגיבים רק לשינוי רוחב אמיתי
      var lastW = window.innerWidth, deb = null;
      window.addEventListener("resize", function () {
        if (window.innerWidth === lastW) return;
        lastW = window.innerWidth;
        clearTimeout(deb);
        deb = setTimeout(fit, 150);
      });
    }
  };

  /* ---------- helpers ---------- */
  function h(html) { return String(html == null ? "" : html); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function scoreBand(v) { return v >= 66 ? "score-hi" : v >= 45 ? "score-mid" : "score-lo"; }
  function fmtNum(v, d) {
    if (v == null || isNaN(v)) return "—";
    return Number(v).toLocaleString("en-US", { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 });
  }
  function fmtTradeDate(iso) {
    // "2026-07-29" → "29.7.26"  (no leading zeros, 2-digit year)
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
    return m ? (+m[3]) + "." + (+m[2]) + "." + m[1].slice(2) : "";
  }
  function prevTradingDate(iso) {
    // יום המסחר שלפני התאריך (מדלג על סופ"ש) — סריקת בוקר מבוססת על סגירת אתמול
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
    if (!m) return "";
    var dt = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
    do { dt.setUTCDate(dt.getUTCDate() - 1); } while (dt.getUTCDay() === 0 || dt.getUTCDay() === 6);
    return dt.toISOString().slice(0, 10);
  }
  function fetchJSON(url) {
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(url + " → " + r.status);
      return r.json();
    });
  }
  function stamp(meta) {
    if (!meta || !meta.updatedAt) return "";
    return '<p class="stamp"><span class="dot-live"></span> עודכן לאחרונה: ' + esc(meta.updatedAt) + "</p>";
  }
  // append a version query so browsers/CDN always fetch the freshest iframe HTML
  function bust(url, meta) {
    var v = (meta && (meta.updatedAt || meta.fetchedAt)) || "";
    return esc(url) + "?v=" + encodeURIComponent(v);
  }
  /* per-tab explanation text (uniform style via .tab-intro) */
  var TAB_INTROS = {
    candidates: "כל בוקר אנחנו סורקים מאות מניות מומנטום ומחפשים מניות שעשו תיקון קטן חזרה לממוצע ועכשיו חוזרות לעלות — קונים את התיקון, לא את השיא. המערכת מדרגת ומציגה את הטובות ביותר, עם מחיר כניסה, סטופ ויעד. לצורכי לימוד בלבד, לא המלצה.",
    momentum: "בכל בוקר אנחנו סורקים את שוק המניות האמריקאי ומאתרים את המניות עם המומנטום הכי חזק — אלה שמופיעות במקביל בכמה סורקים טכניים (חוזק מגמה, שיא 6 חודשים, TTM Squeeze, MACD Buy). ככל שיש יותר סיגנלים למניה — הסיכוי להמשך תנועה חזקה גבוה יותר. הרשימה היא כלי סינון בלבד ולא המלצת השקעה."
  };
  function tabIntro(key) {
    var t = TAB_INTROS[key];
    return t ? '<p class="tab-intro">' + esc(t) + "</p>" : "";
  }
  /* הסבר מורחב לטאב מדדים (מוצג מתחת לתמונת המצב) */
  var INDICES_EXPLAINER =
    '<div class="tab-intro intro-rich">' +
      "<h3>איך זה עובד</h3>" +
      "<p>כל בוקר המערכת אוספת את נתוני היום — מחירים, רוחב השוק, מדד הפחד (VIX) וזרימת האופציות — ומנתחת אותם אוטומטית. במקום ערימת מספרים, היא מפיקה שלושה דברים:<br>" +
      "<b>ניתוח</b> (מה קרה) · <b>מסקנה</b> (מה זה אומר) · <b>המלצה</b> (מה לעשות).</p>" +
      "<h3>מה חשוב לדעת על השוק</h3>" +
      '<p>השוק לא נע בקו ישר. מעל פני השטח יש "עלה או ירד" — אבל מתחת מסתתרת הבריאות האמיתית: האם העלייה רחבה (הרבה מניות עולות) או צרה (רק מעטות), האם הכסף הגדול קונה או נערך להגנה, וכמה פחד יש בשוק. המערכת מסתכלת על כל אלה יחד — ונותנת תמונה כנה, כולל רמת הביטחון שלה.</p>' +
      '<p class="intro-disc">⚠️ <b>הסתייגות:</b> המידע כאן הוא לצורך מידע והתרשמות בלבד, ואינו ייעוץ השקעות או המלצה לפעולה. השקעה בשוק ההון כרוכה בסיכון. כל החלטה — באחריותך.</p>' +
    "</div>";
  function emptyPanel(el, emoji, title, note) {
    el.innerHTML =
      '<div class="panel-empty"><span class="emoji">' + emoji + "</span>" +
      "<strong>" + esc(title) + "</strong>" +
      (note ? '<p style="margin:8px 0 0">' + esc(note) + "</p>" : "") + "</div>";
  }

  var SECTOR_HE = {
    FIN: "פיננסים", IND: "תעשייה", HC: "בריאות", CS: "צריכה בסיסית", CD: "צריכה מחזורית",
    IT: "טכנולוגיה", ENE: "אנרגיה", UTL: "תשתיות", RE: "נדל\"ן", MAT: "חומרים", COM: "תקשורת"
  };

  /* ---------- home pulse: Edge Meter (right) + live market clock (left) ---------- */
  function mPolar(cx, cy, r, deg) {   // deg מ"12:00": ‎-90=שמאל, ‎+90=ימין
    var a = deg * Math.PI / 180;
    return [cx + r * Math.sin(a), cy - r * Math.cos(a)];
  }
  function mArc(cx, cy, r, a1, a2) {
    var p1 = mPolar(cx, cy, r, a1), p2 = mPolar(cx, cy, r, a2);
    return "M" + p1[0].toFixed(1) + "," + p1[1].toFixed(1) +
      " A" + r + "," + r + " 0 0 1 " + p2[0].toFixed(1) + "," + p2[1].toFixed(1);
  }
  function mDeg(score) { return -90 + score * 1.8; }
  function meterWord(v) { return v >= 66 ? ["חיובי", "var(--up)"] : v >= 45 ? ["זהיר", "var(--warn)"] : ["הגנתי", "var(--down)"]; }

  function initHomePulse() {
    var el = document.getElementById("home-pulse");
    if (!el) return;
    el.innerHTML =
      '<section class="card pulse-card">' +
        '<div class="pulse-title">🎯 The Edge Meter · מד השוק היומי</div>' +
        '<svg class="meter-svg" viewBox="0 0 200 118" aria-label="מד ציון משולב">' +
          '<g id="meter-arcs" fill="none" stroke-linecap="round"></g>' +
          '<g id="meter-ticks" stroke="var(--text-3)" stroke-width="1" opacity=".55"></g>' +
          '<g class="meter-needle" id="meter-needle" style="transform:rotate(-90deg)">' +
            '<line x1="100" y1="100" x2="100" y2="36" stroke="var(--text)" stroke-width="3.2" stroke-linecap="round"/>' +
            '<circle cx="100" cy="100" r="6.5" fill="var(--text)"/>' +
            '<circle cx="100" cy="100" r="2.4" fill="var(--card-bg)"/>' +
          "</g></svg>" +
        '<div class="meter-score num" id="meter-score">—</div>' +
        '<div class="meter-word" id="meter-word"></div>' +
        '<div class="meter-sub" id="meter-sub"></div>' +
        '<svg class="meter-spark" id="meter-spark" viewBox="0 0 120 30" preserveAspectRatio="none"></svg>' +
        '<div class="spark-label" id="spark-label"></div>' +
      "</section>" +
      '<section class="card pulse-card pulse-news">' +
        '<div class="pulse-title pn-title">📰 חדשות השוק</div>' +
        '<ul class="pn-list" id="pn-list"></ul>' +
      "</section>" +
      '<section class="card pulse-card clock-card">' +
        '<span class="clock-badge closed" id="clock-badge">…</span>' +
        '<div class="clock-time num" id="clock-time" dir="ltr">--:--:--</div>' +
        '<div class="clock-label" id="clock-label"></div>' +
        '<div class="clock-next" id="clock-next" style="display:none"></div>' +
      "</section>";

    // קשתות אזורי הצבע + שנתות
    var arcs = document.getElementById("meter-arcs");
    [[0, 44, "var(--down)"], [45, 65, "var(--warn)"], [66, 100, "var(--up)"]].forEach(function (z) {
      var p = document.createElementNS("http://www.w3.org/2000/svg", "path");
      p.setAttribute("d", mArc(100, 100, 78, mDeg(z[0]) + 1, mDeg(z[1]) - 1));
      p.setAttribute("stroke", z[2]); p.setAttribute("stroke-width", "13"); p.setAttribute("opacity", ".92");
      arcs.appendChild(p);
    });
    var ticks = document.getElementById("meter-ticks");
    [0, 25, 50, 75, 100].forEach(function (v) {
      var a = mDeg(v), o = mPolar(100, 100, 66, a), i2 = mPolar(100, 100, 60, a);
      var l = document.createElementNS("http://www.w3.org/2000/svg", "line");
      l.setAttribute("x1", o[0]); l.setAttribute("y1", o[1]);
      l.setAttribute("x2", i2[0]); l.setAttribute("y2", i2[1]);
      ticks.appendChild(l);
    });
    startClock();
  }

  function renderMeter(d) {
    var v = (d.scores || {}).combined;
    var score = document.getElementById("meter-score");
    if (!score || v == null) return;
    var w = meterWord(v);
    score.textContent = v; score.style.color = w[1];
    var word = document.getElementById("meter-word");
    word.textContent = w[0]; word.style.color = w[1];
    document.getElementById("meter-sub").textContent =
      "טכני " + (d.scores.tech != null ? d.scores.tech : "—") +
      " · רוחב " + (d.scores.breadth != null ? d.scores.breadth : "—") +
      " · אופציות " + (d.scores.flow != null ? d.scores.flow : "—");
    requestAnimationFrame(function () { setTimeout(function () {
      var n = document.getElementById("meter-needle");
      if (n) n.style.transform = "rotate(" + mDeg(v) + "deg)";
    }, 150); });
  }

  /* שעון המסחר — שעון ישראל מקומי; פתיחה 16:30, סגירה 23:00, ב'-ו' */
  var OPEN_T = { h: 16, m: 30 }, CLOSE_T = { h: 23, m: 0 };
  /* לוח חופשות NYSE — סטטי (מתפרסם שנים מראש); לרענן בתחילת כל שנה.
     שים לב: לוח הבורסה ≠ חגים פדרליים (Good Friday סגור, Columbus/Veterans פתוח) */
  var NYSE_HOLIDAYS = {
    "2026-01-01": "השנה החדשה", "2026-01-19": "יום מרטין לותר קינג",
    "2026-02-16": "יום הנשיאים", "2026-04-03": "יום שישי הטוב",
    "2026-05-25": "יום הזיכרון האמריקאי", "2026-06-19": "Juneteenth",
    "2026-07-03": "יום העצמאות האמריקאי", "2026-09-07": "יום העבודה",
    "2026-11-26": "חג ההודיה", "2026-12-25": "חג המולד",
    "2027-01-01": "השנה החדשה", "2027-01-18": "יום מרטין לותר קינג",
    "2027-02-15": "יום הנשיאים", "2027-03-26": "יום שישי הטוב",
    "2027-05-31": "יום הזיכרון האמריקאי", "2027-06-18": "Juneteenth",
    "2027-07-05": "יום העצמאות האמריקאי", "2027-09-06": "יום העבודה",
    "2027-11-25": "חג ההודיה", "2027-12-24": "חג המולד"
  };
  var NYSE_HALF_DAYS = { "2026-11-27": 1, "2026-12-24": 1, "2027-11-26": 1 };   // סגירה מוקדמת 20:00 IL
  function dayKey(d) {
    return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
  }
  function closeT(d) { return NYSE_HALF_DAYS[dayKey(d)] ? { h: 20, m: 0 } : CLOSE_T; }
  function atTime(base, t) { var d = new Date(base); d.setHours(t.h, t.m, 0, 0); return d; }
  function tradingDay(d) { var w = d.getDay(); return w >= 1 && w <= 5 && !NYSE_HOLIDAYS[dayKey(d)]; }
  function clockTarget() {
    var now = new Date();
    if (tradingDay(now) && now < atTime(now, OPEN_T)) return { t: atTime(now, OPEN_T), label: "לפתיחת המסחר בוול-סטריט", open: false };
    if (tradingDay(now) && now < atTime(now, closeT(now))) return { t: atTime(now, closeT(now)), label: "לסגירת המסחר", open: true };
    var d = new Date(now); d.setDate(d.getDate() + 1);
    while (!tradingDay(d)) d.setDate(d.getDate() + 1);
    return { t: atTime(d, OPEN_T), label: "לפתיחת המסחר הבאה", open: false };
  }
  /* היום בלוח: "יום חמישי · 13.8.2026" — מוצג מעל קיקר יום-המסחר בכתבה הראשית */
  function todayLine() {
    var now = new Date();
    var days = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"];
    return "יום " + days[now.getDay()] + ' · <b class="num" dir="ltr">' +
      now.getDate() + "." + (now.getMonth() + 1) + "." + now.getFullYear() + "</b>";
  }
  /* יום ללא מסחר הקרוב בבורסה — משמאל לשעון (במובייל: מתחת לחיפוש).
     "חג" הוחלף ל"יום ללא מסחר" (2026-08-24, בקשת המשתמש) — חלק מהימים
     (Presidents' Day וכד') לא נחווים כ"חג" לקורא ישראלי, וזה מטעה. */
  function renderDayMeta() {
    var el = document.getElementById("np-daymeta");
    if (!el) return;
    var now = new Date();
    var k = dayKey(now), txt = "";
    if (NYSE_HOLIDAYS[k]) {
      txt = "🏖 הבורסה סגורה היום — " + NYSE_HOLIDAYS[k];
    } else if (NYSE_HALF_DAYS[k]) {
      txt = "🕐 מסחר מקוצר היום · סגירה 20:00";
    } else {
      var d = new Date(now), best = null;
      for (var i = 1; i <= 400 && !best; i++) {
        d.setDate(d.getDate() + 1);
        if (NYSE_HOLIDAYS[dayKey(d)]) best = { name: NYSE_HOLIDAYS[dayKey(d)], d: new Date(d), n: i };
      }
      if (best) {
        var when = best.n === 1 ? "מחר" : "בעוד " + best.n + " ימים";
        txt = "🗓 יום ללא מסחר הבא: " + best.name + ' · <span class="num" dir="ltr">' +
          best.d.getDate() + "." + (best.d.getMonth() + 1) + "</span> · " + when;
      }
    }
    el.innerHTML = txt ? '<span class="dm-hol">' + txt + "</span>" : "";
  }
  function startClock() {
    var timeEl = document.getElementById("clock-time");
    if (!timeEl) return;
    function pad(n) { return (n < 10 ? "0" : "") + n; }
    function tick() {
      var g = clockTarget(), s = Math.max(0, Math.floor((g.t - new Date()) / 1000));
      timeEl.textContent = pad(Math.floor(s / 3600)) + ":" + pad(Math.floor((s % 3600) / 60)) + ":" + pad(s % 60);
      document.getElementById("clock-label").textContent = g.label;
      var b = document.getElementById("clock-badge");
      b.textContent = g.open ? "● המסחר פתוח" : "המסחר סגור";
      b.className = "clock-badge " + (g.open ? "open" : "closed");
    }
    tick(); setInterval(tick, 1000);
  }
  function renderClockNext() {
    var el = document.getElementById("clock-next");
    if (!el || !BRIEF) return;
    var slot = (BRIEF.afternoon && BRIEF.afternoon.schedule && BRIEF.afternoon) ||
               (BRIEF.morning && BRIEF.morning.schedule && BRIEF.morning) || null;
    if (!slot) return;
    // "האירוע הבא היום" רק כשבאמת יש יום מסחר היום, והתדריך הוא מהיום
    var now = new Date();
    if (!tradingDay(now)) { el.style.display = "none"; return; }
    var todayLabel = ("0" + now.getDate()).slice(-2) + "/" + ("0" + (now.getMonth() + 1)).slice(-2) + "/" + now.getFullYear();
    if (slot.dateLabel !== todayLabel) { el.style.display = "none"; return; }
    var sched = slot.schedule || [];
    for (var i = 0; i < sched.length; i++) {
      var m = /^(\d{1,2}):(\d{2})$/.exec(sched[i].time || "");
      if (!m) continue;
      var t = new Date(now); t.setHours(+m[1], +m[2], 0, 0);
      if (t > now) {
        el.innerHTML = 'האירוע הבא היום: <b dir="ltr">' + esc(sched[i].time) + "</b> · " + esc(sched[i].text);
        el.style.display = "block";
        return;
      }
    }
    el.style.display = "none";
  }

  /* יום המסחר שהנתונים החיים מתייחסים אליו: היום אם הסשן כבר נפתח, אחרת יום המסחר הקודם */
  function lastSessionDate() {
    var d = new Date();
    if (!(tradingDay(d) && d >= atTime(d, OPEN_T))) {
      do { d.setDate(d.getDate() - 1); } while (!tradingDay(d));
    }
    return d.getDate() + "." + (d.getMonth() + 1) + "." + String(d.getFullYear()).slice(2);
  }

  /* "בזק מהרשת" — כותרות-בזק מחשבונות X (דרך שיקופי טלגרם/Nitter), רצועה ברוחב מלא */
  var PULSE_X = null;
  /* פס מבזק שוק — תנועה חדה תוך-יומית (data/flash.json), מוצג עד 3 שעות מהאירוע */
  var FLASH_TTL_MS = 3 * 60 * 60 * 1000;
  function renderFlash(d) {
    var wrap = document.getElementById("flash-wrap");
    var el = document.getElementById("flash-bar");
    if (!wrap || !el) return;
    var ts = d && d.ts ? Date.parse(d.ts) : NaN;
    if (!d || isNaN(ts) || Date.now() - ts > FLASH_TTL_MS) { wrap.hidden = true; return; }
    var down = d.pct < 0;
    wrap.className = down ? "fl-down" : "fl-up";
    var ev = d.evidence || {};
    var bits = [];
    (ev.econ || []).forEach(function (e) {
      bits.push('<span class="fl-ev">📊 ' + esc(e.he) + ": בפועל " + esc(e.actual) +
        " מול צפי " + esc(e.forecast) + " (" + esc(e.ilTime) + ")</span>");
    });
    (ev.pulse || []).slice(0, 3).forEach(function (p) {
      bits.push('<span class="fl-ev" dir="auto">💬 ' + esc(String(p.text).slice(0, 110)) +
        " · " + esc(p.source) + "</span>");
    });
    if (!bits.length) (ev.news || []).slice(0, 2).forEach(function (n) {
      bits.push('<span class="fl-ev" dir="ltr">📰 ' + esc(n.title) + " · " + esc(n.source) + "</span>");
    });
    var detail = bits.length
      ? '<div class="fl-detail" id="fl-detail" hidden>' + bits.join("") +
        '<span class="fl-note">מה שהתפרסם סביב אותן דקות — לא בהכרח הסיבה.</span></div>'
      : "";
    el.innerHTML =
      '<span class="fl-head">⚡ <b>תנועה חדה:</b> ' + (down ? "ירידה" : "עלייה") + " של " +
      Math.abs(d.pct).toFixed(1) + "% ב-" + (d.windowMin || 30) + " דק' (" + esc(d.label || "") +
      ') · <span class="num" dir="ltr">' + esc(d.time || "") + "</span>" +
      (bits.length ? ' · <button class="fl-toggle" id="fl-toggle" type="button">מה קרה? ⌄</button>' : "") +
      "</span>" + detail;
    wrap.hidden = false;
    var t = document.getElementById("fl-toggle");
    if (t) t.addEventListener("click", function () {
      var dt = document.getElementById("fl-detail");
      if (dt) dt.hidden = !dt.hidden;
      t.textContent = dt && dt.hidden ? "מה קרה? ⌄" : "סגור ⌃";
    });
  }

  var PULSE_X_ALL = false;   // "כל העדכונים" — הרחבה במקום (4 ↔ כל הרשימה)
  function renderPulseX() {
    var el = document.getElementById("tri-x");
    if (!el) return;
    if (!PULSE_X || !(PULSE_X.items || []).length) { el.innerHTML = ""; return; }
    var items = PULSE_X.items;
    var shown = PULSE_X_ALL ? items : items.slice(0, 4);
    var moreLbl = PULSE_X_ALL ? "צמצם ⌃" : "כל העדכונים (" + items.length + ") ⌄";
    el.innerHTML =
      '<h3 class="np-k">בזק מהרשת · X</h3>' +
      shown.map(function (it) {
        return '<a class="np-xit" href="' + esc(it.link) + '" target="_blank" rel="noopener">' +
          '<span class="m">' + esc(it.source) + " · " + esc(it.time) + "</span>" +
          // dir="auto": הפריטים מעורבים — עברית מהדיג'סט ואנגלית מהטלגרם —
          // והדפדפן קובע כיוון לכל פריט לפי התו החזק הראשון שבו (6.9.2026)
          '<p dir="auto">' + esc(it.text) + "</p></a>";
      }).join("") +
      (items.length > 4 ? '<a class="np-more" href="#" id="pulse-more">' + moreLbl + "</a> · " : "") +
      '<a class="np-more" href="#" id="news-toggle">📰 חדשות השוק ⌄</a>';
    var pm = document.getElementById("pulse-more");
    if (pm) pm.addEventListener("click", function (ev) {
      ev.preventDefault();
      PULSE_X_ALL = !PULSE_X_ALL;
      renderPulseX();
    });
    var nt = document.getElementById("news-toggle");
    if (nt) nt.addEventListener("click", function (ev) {
      ev.preventDefault();
      var n = document.getElementById("tri-news");
      if (n) n.style.display = n.style.display === "none" ? "block" : "none";
    });
  }

  /* ציטוטים חיים למניות במוקד — ישירות מהסורק של TradingView (CORS פתוח; body כ-text/plain) */
  var FOCUSQ = {}, FOCUS_SYMS = "", FHIST = null;
  function jsSession() {
    var now = new Date();
    if (!tradingDay(now)) return "closed";
    if (now < atTime(now, OPEN_T)) return (now.getHours() * 60 + now.getMinutes()) >= 660 ? "pre" : "closed";
    if (now < atTime(now, closeT(now))) return "regular";
    return "post";
  }
  function refreshFocusQuotes(syms, force) {
    var key = syms.join(",");
    if (!force && key === FOCUS_SYMS) return;
    FOCUS_SYMS = key;
    if (!syms.length) return;
    fetch("https://scanner.tradingview.com/america/scan", {
      method: "POST",
      body: JSON.stringify({
        filter: [
          { left: "name", operation: "in_range", right: syms },
          { left: "exchange", operation: "in_range", right: ["NASDAQ", "NYSE", "AMEX"] }
        ],
        columns: ["name", "close", "change", "premarket_close", "premarket_change", "postmarket_close", "postmarket_change"],
        range: [0, 20]
      })
    }).then(function (r) { return r.json(); }).then(function (d) {
      var ses = jsSession();
      (d.data || []).forEach(function (row) {
        var v = row.d, px = v[1], chg = v[2];
        if (ses === "pre" && v[4] != null) { px = (v[3] != null ? v[3] : px); chg = v[4]; }
        else if (ses === "post" && v[6] != null) { px = (v[5] != null ? v[5] : px); chg = v[6]; }
        FOCUSQ[v[0]] = { px: px, chg: chg };
      });
      renderFocus();
    }).catch(function () {});
  }

  /* "מניות במוקד" — גלאי מפגשים: מניה שמופיעה ב-2+ מקורות פעילים (מומנטום/מועמדים/בולטות) */
  function renderFocus() {
    var el = document.getElementById("home-focus");
    if (!el) return;
    var hits = {};
    function H(sym) { sym = (sym || "").toUpperCase(); if (!sym) return null; return (hits[sym] = hits[sym] || { sym: sym }); }

    if (MOMD && MOMD.stocks) {
      MOMD.stocks.forEach(function (s) {
        if ((s.signal_count || 0) >= 2 && passesBase(s)) {
          var h = H(s.symbol); if (h) h.mom = s.signal_count;
        }
      });
    }
    if (CANDD && CANDD.candidates) {
      CANDD.candidates.forEach(function (c) { var h = H(c.symbol); if (h) h.cand = c.rank; });
    }
    // הבולטות הוצאו מהחישוב (מתחלפות כל רבע שעה וגרמו לרשימה "לנשום" במהלך היום);
    // המוקד = חיתוך יציב של מומנטום ∩ מועמדים בלבד
    var focus = Object.keys(hits).map(function (k) { return hits[k]; }).filter(function (h) {
      return h.mom != null && h.cand != null;
    });
    if (!focus.length) { el.innerHTML = ""; return; }
    focus.sort(function (a, b) {
      return ((b.mom || 0) - (a.mom || 0)) || ((a.cand || 99) - (b.cand || 99));
    });
    focus = focus.slice(0, 6);
    refreshFocusQuotes(focus.map(function (h) { return h.sym; }));

    var repSet = {};
    if (REPD && REPD.reports) REPD.reports.forEach(function (r) { repSet[(r.ticker || "").toUpperCase()] = 1; });

    // שם/מחיר/שינוי — מהמומנטום או מהבולטות (מה שזמין)
    var info = {};
    if (MOMD && MOMD.stocks) MOMD.stocks.forEach(function (s) {
      info[(s.symbol || "").toUpperCase()] = { name: s.name, px: s.price, chg: s.change_pct };
    });
    if (MOVERS) ["gainers", "losers", "active"].forEach(function (g) {
      (MOVERS[g] || []).forEach(function (x) {
        var k = (x.symbol || "").toUpperCase();
        if (!info[k]) info[k] = { name: x.name, px: x.price, chg: x.chg };
      });
    });

    el.innerHTML =
      '<section class="card focus-card">' +
        '<div class="split-head"><span class="split-title">🎯 מניות במוקד</span>' +
          '<span class="split-sub">מחירים חיים · מומנטום ומועמדות במקביל' +
            (INDD && INDD.date ? ' · נכון ליום המסחר <span dir="ltr">' + fmtTradeDate(INDD.date) + "</span>" : "") +
          "</span></div>" +
        '<div class="fc-grid">' +
        focus.map(function (h) {
          var inf = info[h.sym] || {};
          var live = FOCUSQ[h.sym];
          var pxv = (live && live.px != null) ? live.px : inf.px;
          var chg = (live && live.chg != null) ? live.chg : inf.chg;
          var pxHtml = (pxv != null && !isNaN(pxv))
            ? '<span class="fc-px num" dir="ltr">' + Number(pxv).toLocaleString("en-US", { maximumFractionDigits: 2 }) +
              (chg != null && !isNaN(chg)
                ? ' <b class="' + (chg >= 0 ? "up" : "down") + '">' + (chg > 0 ? "+" : "") + Number(chg).toFixed(2) + "%</b>" : "") +
              "</span>"
            : "";
          var tags = [];
          if (h.mom != null) tags.push('<span class="fc-t">מומנטום · <b>' + h.mom + " סיגנלים</b></span>");
          if (h.cand != null) tags.push('<span class="fc-t">מועמדת <b>#' + h.cand + "</b></span>");
          var iso = EARNW[h.sym];
          if (iso) { var m = /-(\d{2})-(\d{2})$/.exec(iso); if (m) tags.push('<span class="fc-t fc-warn">📅 מדווחת ' + (+m[2]) + "." + (+m[1]) + "</span>"); }
          if (repSet[h.sym]) tags.push('<button class="fc-t fc-rep" onclick="__goTab(\'reports\')">📑 ניתוח</button>');
          return '<div class="fc-item">' +
            '<div class="fc-head">' +
              '<span class="fc-id">' +
                '<img class="fc-logo" src="https://financialmodelingprep.com/image-stock/' + encodeURIComponent(h.sym) +
                  '.png" alt="" loading="lazy" onerror="this.remove()">' +
                '<a class="fc-sym" dir="ltr" href="https://www.tradingview.com/symbols/' + encodeURIComponent(h.sym) +
                  '/" target="_blank" rel="noopener">' + esc(h.sym) + "</a>" +
              "</span>" + pxHtml +
            "</div>" +
            (inf.name ? '<div class="fc-name" dir="ltr">' + esc(inf.name) + "</div>" : "") +
            '<div class="fc-tags">' + tags.join('<span class="fc-sep">·</span>') + "</div></div>";
        }).join("") + "</div>" + focusStatsHtml() + "</section>";
    renderTriIndex();
  }

  /* 📊 נתוני מאקרו — צפי מול בפועל (data/econ.json, ליבה בלבד) */
  var ECON = null;
  function renderEcon() {
    var el = document.getElementById("home-econ");
    if (!el || !ECON || !(ECON.events || []).length) return;
    var released = ECON.events.filter(function (e) { return e.actual != null; }).slice(-5).reverse();
    var upcoming = ECON.events.filter(function (e) { return e.actual == null; }).slice(0, 5);
    function row(e, isUp) {
      var cls = e.surprise === "good" ? "up" : e.surprise === "bad" ? "down" : "";
      var val = isUp
        ? (e.forecast ? 'צפי <b class="num" dir="ltr">' + esc(e.forecast) + "</b>" : "צפי —") +
          (e.previous ? ' · קודם <span class="num" dir="ltr">' + esc(e.previous) + "</span>" : "")
        : 'בפועל <b class="num ' + cls + '" dir="ltr">' + esc(e.actual) + "</b>" +
          (e.forecast ? ' מול צפי <span class="num" dir="ltr">' + esc(e.forecast) + "</span>" : "") +
          (e.surprise === "good" ? " ✓" : e.surprise === "bad" ? " ✗" : "");
      // התאריך מימין והשעה משמאל (סדר RTL טבעי) — כל מספר LTR בפני עצמו
      return '<div class="ec-row' + (isUp ? "" : " " + cls) + '">' +
        '<span class="ec-when num"><span dir="ltr">' + esc(e.ilDate) + "</span>" +
          (isUp && e.ilTime ? ' · <span dir="ltr">' + esc(e.ilTime) + "</span>" : "") + "</span>" +
        '<span class="ec-name">' + esc(e.he) + "</span>" +
        '<span class="ec-val">' + val + "</span></div>";
    }
    el.innerHTML =
      '<section class="card econ-card">' +
        '<div class="split-head"><span class="split-title">📊 נתוני מאקרו — צפי מול בפועל</span>' +
          '<span class="split-sub">מתעדכן אוטומטית עם הפרסום</span></div>' +
        '<div class="ec-cols">' +
          '<div class="ec-col"><div class="ec-t">🔔 פורסמו לאחרונה</div>' +
            (released.map(function (e) { return row(e, false); }).join("") || '<div class="ec-row">אין פרסומים אחרונים</div>') + "</div>" +
          '<div class="ec-col"><div class="ec-t">🗓️ הבאים בתור</div>' +
            (upcoming.map(function (e) { return row(e, true); }).join("") || '<div class="ec-row">אין אירועים קרובים</div>') + "</div>" +
        "</div></section>";
    renderTriIndex();
  }

  /* "המוקד במבחן" — סטטיסטיקת ביצוע בתוך כרטיס המוקד */
  function fmtPct(v) {
    if (v == null || isNaN(v)) return "—";
    return '<b class="' + (v >= 0 ? "up" : "down") + '" dir="ltr">' + (v > 0 ? "+" : "") + Number(v).toFixed(2) + "%</b>";
  }
  function focusStatsHtml() {
    if (!FHIST || !(FHIST.entries || []).length) return "";
    var entries = FHIST.entries;
    var frozen = entries.filter(function (e) { return e.result; });
    var html = '<div class="fc-stats"><span class="fc-stats-t">📊 המוקד במבחן</span>';
    if (frozen.length) {
      var last = frozen[frozen.length - 1], r = last.result;
      var beat = (r.spx != null && r.avg > r.spx);
      html += '<div class="fc-stats-line">המוקד של <span dir="ltr">' + esc(fmtTradeDate(last.date)) + "</span> (" + r.per.length + " מניות): ממוצע " +
        fmtPct(r.avg) + (r.spx != null ? " מול S&P " + fmtPct(r.spx) + (beat ? " ✓" : "") : "") +
        (r.date_next ? ' — ביום המסחר <span dir="ltr">' + esc(fmtTradeDate(r.date_next)) + "</span>" : "") + "</div>";
      html += '<div class="fc-stats-per">' + r.per.map(function (p) {
        return '<span dir="ltr">' + esc(p.sym) + " " + (p.pct > 0 ? "+" : "") + p.pct.toFixed(1) + "%</span>";
      }).join('<span class="fc-sep">·</span>') + "</div>";
      if (frozen.length >= 5) {
        var allPer = [], avgs = [], spxs = [];
        frozen.forEach(function (e) {
          e.result.per.forEach(function (p) { allPer.push(p.pct); });
          avgs.push(e.result.avg);
          if (e.result.spx != null) spxs.push(e.result.spx);
        });
        var winRate = Math.round(100 * allPer.filter(function (v) { return v > 0; }).length / allPer.length);
        var cAvg = avgs.reduce(function (a, b) { return a + b; }, 0) / avgs.length;
        var cSpx = spxs.length ? spxs.reduce(function (a, b) { return a + b; }, 0) / spxs.length : null;
        html += '<div class="fc-stats-line fc-stats-cum">מצטבר (' + frozen.length + " ימים): " + winRate + "% מהמניות עלו · ממוצע " +
          fmtPct(cAvg) + (cSpx != null ? " מול S&P " + fmtPct(cSpx) : "") + "</div>";
      }
    } else {
      html += '<div class="fc-stats-line">🧪 המדידה החלה — תוצאת המוקד של <span dir="ltr">' +
        esc(fmtTradeDate(entries[entries.length - 1].date)) + "</span> תוצג לאחר סגירת סשן המסחר הבא.</div>";
    }
    return html + "</div>";
  }

  /* חדשות השוק — רשימה נפתחת מתוך שורת "מפתח" (אנגלית מקורית) */
  function renderPulseNews() {
    var el = document.getElementById("tri-news");
    if (!el || !NEWS || !NEWS.news) return;
    var items = NEWS.news.slice().sort(function (a, b) {
      return (b.dt || "") < (a.dt || "") ? -1 : 1;
    });
    el.innerHTML = '<h3 class="np-k">חדשות השוק</h3>' +
      items.slice(0, 5).map(function (n) {
        return '<a class="np-xit" href="' + esc(n.link) + '" target="_blank" rel="noopener">' +
          '<p dir="auto">' + esc(n.titleEn || n.title) + "</p>" +
          '<span class="m">' + esc(n.source || "") + " · " + esc(n.time) + "</span></a>";
      }).join("");
    renderTriIndex();
  }

  /* ---------- home split: top movers (right) + today's earnings (left) ---------- */
  var NEWS = null, EARN = null, MOVERS = null, MV_CUR = "gainers";
  var MOMD = null, CANDD = null, REPD = null;   // מאגרי-על לחישוב "מניות במוקד"
  var HIST = null, DIFFS = null, INDD = null;   // היסטוריית ציונים + שינוי-יומי

  /* גרף מגמה קטן מתחת למד — הציון המשולב לאורך הימים האחרונים */
  function renderSpark() {
    var svg = document.getElementById("meter-spark");
    if (!svg || !HIST || !(HIST.days || []).length) return;
    var days = HIST.days.slice(-30);
    var vals = days.map(function (d) { return d.combined; }).filter(function (v) { return v != null; });
    if (vals.length < 2) return;
    var min = Math.min.apply(null, vals), max = Math.max.apply(null, vals);
    var pad = Math.max(2, (max - min) * 0.12); min -= pad; max += pad;
    var W = 120, Hh = 30;
    var pts = vals.map(function (v, i) {
      var x = i * (W / (vals.length - 1));
      var y = Hh - ((v - min) / (max - min)) * Hh;
      return x.toFixed(1) + "," + y.toFixed(1);
    });
    var last = vals[vals.length - 1];
    var lastPt = pts[pts.length - 1].split(",");
    svg.innerHTML =
      '<polyline points="' + pts.join(" ") + '" fill="none" stroke="var(--accent)" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round" opacity=".85"/>' +
      '<circle cx="' + lastPt[0] + '" cy="' + lastPt[1] + '" r="2.6" fill="' + meterWord(last)[1] + '"/>';
    var lbl = document.getElementById("spark-label");
    if (lbl) lbl.textContent = vals.length + " ימי מסחר אחרונים";
  }

  /* שינוי-יומי לציונים (מול יום המסחר הקודם) */
  function computeDiffs() {
    DIFFS = null;
    if (!HIST || (HIST.days || []).length < 2) return;
    var a = HIST.days[HIST.days.length - 2], b = HIST.days[HIST.days.length - 1];
    DIFFS = {};
    ["combined", "tech", "breadth", "flow"].forEach(function (k) {
      if (a[k] != null && b[k] != null) DIFFS[k] = b[k] - a[k];
    });
  }
  function diffTag(key) {
    if (!DIFFS || DIFFS[key] == null || DIFFS[key] === 0) return "";
    var v = DIFFS[key];
    return '<span class="diff ' + (v > 0 ? "up" : "down") + '" dir="ltr">' + (v > 0 ? "▲" : "▼") + Math.abs(v) + "</span>";
  }
  function renderHomeSplit() {
    var el = document.getElementById("home-split");
    if (!el) return;
    var html = "";

    // ---- הבולטות של היום (עמודה ימנית ב-RTL = ראשונה ב-DOM) ----
    // הכרטיס מוצג תמיד כשהקובץ נטען — גם כשרשימה רגעית ריקה (שלא ייעלם המלבן)
    if (MOVERS) {
      // מניה בולטת שמופיעה גם במערכות שלנו מקבלת תג בין שם החברה למחיר
      var momSet = {}, candSet = {};
      if (MOMD && MOMD.stocks) MOMD.stocks.forEach(function (s) { momSet[(s.symbol || "").toUpperCase()] = 1; });
      if (CANDD && CANDD.candidates) CANDD.candidates.forEach(function (c) { candSet[(c.symbol || "").toUpperCase()] = 1; });
      var tabs = [["gainers", "📈 עולות"], ["losers", "📉 יורדות"], ["active", "🔄 הכי נסחרות"]];
      var rows = (MOVERS[MV_CUR] || []).map(function (x) {
        var c = x.chg > 0 ? "up" : x.chg < 0 ? "down" : "";
        var sym = (x.symbol || "").toUpperCase(), sys = [];
        if (momSet[sym]) sys.push("מומנטום");
        if (candSet[sym]) sys.push("מועמדת");
        var sysTag = sys.length ? '<span class="mv-in">' + sys.join(" · ") + "</span>" : "";
        return '<li><a class="mv-sym" target="_blank" rel="noopener" href="https://www.tradingview.com/symbols/' +
          encodeURIComponent(x.symbol) + '/" title="פתח ב-TradingView">' + esc(x.symbol) + "</a>" +
          '<span class="mv-name">' + esc(x.name) + "</span>" + sysTag +
          '<span class="mv-px num" dir="ltr">' + (x.price == null ? "—" : Number(x.price).toLocaleString("en-US", { maximumFractionDigits: 2 })) + "</span>" +
          '<span class="mv-chg ' + c + '" dir="ltr">' + (x.chg > 0 ? "+" : "") + Number(x.chg).toFixed(2) + "%</span></li>";
      }).join("");
      html += '<section class="card split-card">' +
        '<div class="split-head"><span class="split-title">🔥 הבולטות של היום</span>' +
          '<span class="split-sub">' + esc((MOVERS._meta || {}).live || ("נכון ליום המסחר " + lastSessionDate())) + "</span></div>" +
        '<div class="mv-tabs">' + tabs.map(function (t) {
          return '<button class="mv-tab' + (t[0] === MV_CUR ? " on" : "") + '" data-g="' + t[0] + '">' + t[1] + "</button>";
        }).join("") + "</div>" +
        '<ul class="mv-list">' + (rows || '<li style="color:var(--text-3)">אין נתונים כרגע.</li>') + "</ul></section>";
    }

    // מדווחות היום עברו לעמודת ה-tri (renderTriIndex) — כאן נשארו רק הבולטות
    el.innerHTML = html;
    renderTriIndex();
  }

  /* ---------- home briefing card (latest edition: sentiment + 4 headlines + schedule) ---------- */
  var BRIEF = null;
  function briefKey(s) {
    if (!s) return -1;
    var m = /(\d{2})\/(\d{2})\/(\d{4})/.exec(s.dateLabel || "");
    var t = /(\d{1,2}):(\d{2})/.exec(s.time || "");
    if (!m) return 0;
    return (+m[3]) * 1e6 + (+m[2]) * 1e4 + (+m[1]) * 1e2 + (t ? (+t[1]) + (+t[2]) / 100 : 0);
  }
  function renderHomeBriefing() {
    var el = document.getElementById("tri-brief");
    if (!el || !BRIEF) return;
    var m = BRIEF.morning, a = BRIEF.afternoon, edition, s;
    if (m && a) { if (briefKey(a) >= briefKey(m)) { edition = "afternoon"; s = a; } else { edition = "morning"; s = m; } }
    else if (a) { edition = "afternoon"; s = a; }
    else if (m) { edition = "morning"; s = m; }
    else { el.innerHTML = ""; return; }

    var label = edition === "afternoon" ? "אחר הצהריים" : "בוקר";
    var sent = s.sentiment || {};
    var news = (s.headlines || []).slice(0, 4);
    var sched = (s.schedule || []).slice(0, 6);

    var sentHtml = sent.text
      ? '<span class="brief-sent">' + h(sent.emoji || "") + " " + esc(sent.text) + "</span>" : "";
    var newsHtml = news.length
      ? '<ol class="brief-news">' + news.map(function (t) { return "<li>" + esc(t) + "</li>"; }).join("") + "</ol>" : "";
    // במייל של סופ"ש "מה נשאר ביומן" מתייחס ליום המסחר הבא — מציגים כותרת כנה
    var lozTitle = tradingDay(new Date()) ? "🕐 לוז יומי צפוי" : "🕐 לוז ליום המסחר הבא";
    var schedHtml = sched.length
      ? '<div class="brief-sched"><div class="bs-title">' + lozTitle + "</div><ul>" +
        sched.map(function (x) {
          if (x.day) return '<li class="bs-day">' + esc(x.day) + "</li>";   // מפריד-יום (כחול)
          return '<li><span class="bs-time num" dir="ltr">' + esc(x.time) + "</span>" +
            '<span class="bs-ev">' + esc(x.text) + "</span></li>";
        }).join("") + "</ul></div>" : "";

    var asOf = edition === "afternoon" ? "15:00" : "06:00";   // שעת המהדורה (משתנה בין בוקר/צהריים)

    el.innerHTML =
      '<h3 class="np-k">תדרוך משקיעים · ' + esc(label) + ' <span dir="ltr">' + asOf + "</span></h3>" +
      (sentHtml ? '<div class="np-sent">' + sentHtml + "</div>" : "") +
      newsHtml + schedHtml +
      '<a class="np-more" href="#briefing" onclick="__goTab(\'briefing\');return false">התדרוך המלא ←</a>';
  }

  /* ---------- הידיעה המובילה + רייל המד (מהדורת עיתון) ---------- */
  var CA = null;   // data/claude_analysis.json — הניתוח היומי (נכתב ע"י המשימה המתוזמנת)
  function renderLead() {
    var el = document.getElementById("lead-main");
    if (!el || !INDD) return;
    var d = INDD, c = d.conclusion || {}, v = d.verdict || {};
    var ai = (d.aiSummary && d.aiSummary.date === d.date) ? d.aiSummary : null;
    var ca = (CA && CA.date === d.date) ? CA : null;   // ניתוח Claude היומי — עדיפות ראשונה

    // חותמת העדכון עברה לפוטר
    var hs = document.getElementById("head-stamp");
    if (hs) hs.innerHTML = stamp(d._meta);

    var lightsMap = { trend: "מגמה", breadth: "רוחב", volatility: "תנודתיות", rotation: "רוטציה" };
    var lights = v.lights ? Object.keys(lightsMap).map(function (k) {
      var st = v.lights[k] || "";
      return '<span class="np-lt ' + esc(st) + '"><span class="np-dot"></span>' + lightsMap[k] + "</span>";
    }).join("") : "";
    // צ'יפי הסכמת התחומים (מהבלוק המשולב של מנוע-הכללים) — קבוצה נפרדת לפני הנוריות
    var domChips = "";
    if (ai && ai.domains) {
      var domHe = { bull: "חיובי", bear: "שלילי", mixed: "מעורב" };
      var domCls = { bull: "good", bear: "bad", mixed: "warn" };
      domChips = '<span class="np-doms">' +
        [["stocks", "מניות"], ["sectors", "סקטורים"], ["options", "אופציות"]].map(function (p) {
          var sig = ai.domains[p[0]];
          if (!domHe[sig]) return "";
          return '<span class="np-lt ' + domCls[sig] + '"><span class="np-dot"></span>' + p[1] + ": " + domHe[sig] + "</span>";
        }).join("") + "</span>";
    }
    var foot = '<div class="np-leadfoot">' + domChips + lights +
      '<a href="#indices" onclick="__goTab(\'indices\');return false">הניתוח המלא ←</a></div>';

    renderLeadRail(d);
    // עדכון-אירוע (CPI/NFP/פד): מחליף את הכותרת עד הניתוח המלא של מחר בבוקר.
    // במכוון על CA הגולמי ולא על ca מוגן-התאריך — לעדכון יש שעון-טריות משלו
    var eu = freshEventUpdate(CA);
    if (eu) {
      // אירוע מאקרו = אדום/דחוף; אמצע-יום/לקראת-מסחר/לקראת-פתיחה = ניטרלי
      var euCalm = eu.kind === "midday" || eu.kind === "preview" || eu.kind === "preopen";
      var euIco = eu.kind === "midday" ? "🕑" : eu.kind === "preview" ? "🗓" : eu.kind === "preopen" ? "🔔" : "🔴";
      // preview/preopen: ה-event הוא כבר כותרת שלמה ("לקראת פתיחת המסחר") — בלי "עדכון"
      var euLbl = (eu.kind === "preview" || eu.kind === "preopen" ? "" : "עדכון ") + esc(eu.event || "אירוע");
      el.innerHTML =
        '<span class="np-today">' + todayLine() + "</span>" +
        '<span class="np-k ' + (euCalm ? "np-evt-mid" : "np-evt") + '">' + euIco +
          " " + euLbl + ' · <b dir="ltr">' + esc(eu.time || "") + "</b></span>" +
        '<h2 class="np-h1">' + esc(eu.headline) + "</h2>" +
        (eu.tldr ? '<p class="np-dek">' + esc(eu.tldr) + "</p>" : "") +
        (eu.action ? '<p class="np-bottom">⚡ <b>מה עושים:</b> ' + esc(eu.action) + "</p>" : "") +
        (eu.odds ? '<p class="np-odds">🎲 ' + esc(eu.odds) + "</p>" : "") +
        foot;
      return;
    }

    if (ca) {
      // מבנה רזה: קיקר עם התאריך + האחוז · כותרת אנליטית · משפט-מהות · שורה תחתונה
      var pm = /([+−-]\d+(?:\.\d+)?%)/.exec(c.headline || "");
      var pmCls = pm ? (pm[1].charAt(0) === "+" ? "up" : "down") : "";
      el.innerHTML =
        '<span class="np-today">' + todayLine() + "</span>" +
        '<span class="np-k">יום המסחר · <b dir="ltr">' + esc(fmtTradeDate(d.date)) + "</b>" +
          (pm ? ' · <b class="num ' + pmCls + '" dir="ltr">' + esc(pm[1]) + "</b>" : "") + "</span>" +
        '<h2 class="np-h1">' + esc(ca.headline) + "</h2>" +
        (ca.tldr ? '<p class="np-dek">' + esc(ca.tldr) + "</p>" : "") +
        (ca.bottomline ? '<p class="np-bottom">💡 ' + esc(ca.bottomline).replace("שורה תחתונה:", "<b>שורה תחתונה:</b>") + "</p>" : "") +
        foot;
      return;
    }

    // נפילה-חזרה: המבנה הקודם (מנוע הכללים / בלי ניתוח)
    var paras = (ai && ai.paragraphs) || [];
    var bottom = null, body = [];
    paras.forEach(function (p) { (p.indexOf("שורה תחתונה") >= 0 ? (bottom = p) : body.push(p)); });
    var dek = body.length ? body.slice(0, 2).join(" ") : (v.subline || "");
    el.innerHTML =
      '<span class="np-today">' + todayLine() + "</span>" +
      '<span class="np-k">יום המסחר · <b dir="ltr">' + esc(fmtTradeDate(d.date)) + "</b></span>" +
      '<h2 class="np-h1">' + esc(c.headline || v.headline || "סקירת שוק") + "</h2>" +
      (ai && ai.headline ? '<p class="np-reg">' + esc(ai.headline) + "</p>" : "") +
      (dek ? '<p class="np-dek">' + esc(dek) + "</p>" : "") +
      (bottom ? '<p class="np-bottom">' + esc(bottom).replace("שורה תחתונה:", "<b>שורה תחתונה:</b>") + "</p>" : "") +
      foot;
  }

  // ההימור נטו של הכסף הגדול (משוקלל-דלתא) — שורה ברייל, נפרדת מציון-העוצמה
  function bigMoneyRow(fl) {
    fl = fl || {};
    if (!fl.deltaLabel) return "";
    var dc = fl.deltaLabel === "דובי" ? "down" : (fl.deltaLabel === "שורי" ? "up" : "");
    var tip = "קניית Calls $" + Math.round((fl.callBuyP || 0) / 1e6) + "M · מכירת Calls $" + Math.round((fl.callSellP || 0) / 1e6) +
      "M · קניית Puts $" + Math.round((fl.putBuyP || 0) / 1e6) + "M · מכירת Puts $" + Math.round((fl.putSellP || 0) / 1e6) + "M" +
      " · מבוסס על עסקאות בולטות/גדולות בלבד — לא כל נפח האופציות של היום (לכן עשוי להיות שונה ממדדי \"דלתא\" של כלים אחרים)";
    // אזהרת מולטי-לג (symmetric — מבוססת % ולא על כיוון ה-label, ולכן
    // מופיעה זהה לשורי/דובי/מאוזן): מדד legTier/legNote בלבד קובע הצגה.
    var legBadge = "";
    if (fl.legNote && (fl.legTier === "low" || fl.legTier === "limited" || fl.legTier === "mid")) {
      var legIcon = fl.legTier === "low" ? "⛔" : "⚠";
      var legPct = fl.legMultiPct != null ? Math.round(fl.legMultiPct) + "% " : "";
      legBadge = '<span class="er-badge" title="' + esc(fl.legNote +
        " — עסקאות מולטי-לג הן רגליים בודדות מתוך אסטרטגיות משולבות (כמו ספרד), לא בהכרח הימור כיווני עצמאי; אין בנתון דרך לשייך אותן לרגליים המשלימות") +
        '">' + legIcon + " " + legPct + "מולטי-לג</span>";
    }
    return '<div class="np-sub" title="' + esc(tip) + '"><span>הכסף הגדול</span><span><b class="' + dc + '">' + esc(fl.deltaLabel) + "</b>" + legBadge + "</span></div>";
  }

  // ─ רייל המד ─ (פונקציה נפרדת: קודם רץ רק בענף-הנפילה, והרייל נעלם אם ניתוח
  // Claude נטען לפני indices — עכשיו מרונדר תמיד, מכל קריאת renderLead)
  function renderLeadRail(d) {
    var rail = document.getElementById("lead-rail");
    if (!rail) return;
    var s = d.scores || {}, e = d.evidence || {};
    var w = s.combined != null ? meterWord(s.combined) : ["", "var(--text)"];
    function sub(label, key, val) {
      return '<div class="np-sub"><span>' + label + "</span><span><b class=\"num\">" +
        (val == null ? "—" : val) + "</b> " + diffTag(key) + "</span></div>";
    }
    rail.innerHTML =
      '<span class="np-k">The Edge Meter · מד השוק היומי</span>' +
      '<div class="np-score"><b class="num" style="color:' + w[1] + '">' + (s.combined != null ? s.combined : "—") + "</b>" +
        '<span style="color:' + w[1] + '">' + w[0] + "</span></div>" +
      '<svg class="meter-spark np-spark" id="meter-spark" viewBox="0 0 120 30" preserveAspectRatio="none"></svg>' +
      '<div class="spark-label" id="spark-label"></div>' +
      sub("טכני", "tech", s.tech) +
      sub("רוחב", "breadth", s.breadth) +
      sub("אופציות", "flow", s.flow) +
      bigMoneyRow(d.flow) +
      (e.nhCount != null ? '<div class="np-sub"><span>שיאים / שפלים 52ש׳</span><b class="num" dir="ltr">' +
        e.nhCount + " / " + e.nlCount + "</b></div>" : "") +
      '<a class="np-more" href="#indices" onclick="__goTab(\'indices\');return false">פירוט ←</a>';
    renderSpark();
  }

  /* עמודת "מדווחות היום והשבוע" — לוגו+טיקר להיום, שורות ימים לשבוע */
  function renderTriIndex() {   // השם נשמר — כל נקודות-הקריאה הקיימות ממשיכות לעבוד
    var el = document.getElementById("tri-earn");
    if (!el || !EARN) return;
    var rep = EARN.reporting || [], up = EARN.upcoming || [];
    var today = rep.length
      ? '<div class="earn-grid">' + rep.slice(0, 8).map(function (r) {
          return '<a class="earn-tile" href="https://www.tradingview.com/symbols/' + encodeURIComponent(r.ticker) +
            '/" target="_blank" rel="noopener" title="' + esc(r.name) + '">' +
            (r.logo ? '<img src="' + esc(r.logo) + '" alt="" loading="lazy" onerror="this.remove()">' : "") +
            '<span dir="ltr">' + esc(r.ticker) + "</span></a>";
        }).join("") + "</div>" +
        (EARN.todayCount > 8 ? '<div class="np-earn-more">ועוד ' + (EARN.todayCount - 8) + " חברות היום</div>" : "")
      : '<div class="np-earn-more">אין דיווחים היום.</div>';
    var week = up.length
      ? '<div class="earn-up"><div class="earn-up-t">מדווחות השבוע</div>' +
        up.map(function (u) {
          return '<div class="earn-up-row"><span class="earn-up-day">' + esc(u.dow) + " " +
            '<span dir="ltr">' + esc(u.label) + "</span></span>" +
            '<span class="earn-up-n">' + u.count + "</span>" +
            '<span class="earn-up-tk" dir="ltr">' + esc((u.tickers || []).slice(0, 4).join(" · ")) + "</span></div>";
        }).join("") + "</div>"
      : "";
    el.innerHTML =
      '<h3 class="np-k">מדווחות היום והשבוע</h3>' + today + week +
      '<a class="np-more" href="#weekcal" onclick="__goTab(\'weekcal\');return false">לוח הדיווחים המלא ←</a>';
  }

  /* ---------- renderers ---------- */
  function renderMarketOverview(el, d, opts) {
    opts = opts || {};
    var v = d.verdict || {};
    var s = d.scores || {};
    var e = d.evidence || {};
    var c = d.conclusion || {};
    var lightsMap = { trend: "מגמה", breadth: "רוחב", volatility: "תנודתיות", rotation: "רוטציה" };

    var lights = "";
    if (v.lights) {
      lights = '<div class="lights">' + Object.keys(lightsMap).map(function (k) {
        var st = v.lights[k] || "";
        return '<span class="light ' + esc(st) + '"><span class="dot"></span>' + lightsMap[k] + "</span>";
      }).join("") + "</div>";
    }

    var tradeDate = fmtTradeDate(d.date);
    // הסיכום היומי החדש (ai_analysis) — מוצג רק כשתאריכו תואם את יום המסחר של הנתונים
    var ai = (d.aiSummary && d.aiSummary.date === d.date) ? d.aiSummary : null;
    var mid;
    if (opts.home && ai) {
      // בבית: הסיכום היומי מחליף את משפטי-הרקע הישנים; הנוריות נשארות
      mid =
        (ai.headline ? '<p class="v-regime">' + esc(ai.headline) + "</p>" : "") +
        '<div class="verdict-narr">' +
          (ai.paragraphs || []).map(function (p) { return "<p>" + esc(p) + "</p>"; }).join("") +
          (ai.watchFor ? "<p><b>לעקוב:</b> " + esc(ai.watchFor) + "</p>" : "") +
        "</div>";
    } else {
      // נפילה חזרה (אין סיכום יומי / טאב מדדים): המבנה הקודם
      var nrt = d.narrative || {};
      var narr = (opts.home && (nrt.today || nrt.week || nrt.watchFor))
        ? '<div class="verdict-narr">' +
            (nrt.today ? "<p><b>היום:</b> " + esc(nrt.today) + "</p>" : "") +
            (nrt.week ? "<p><b>השבוע:</b> " + esc(nrt.week) + "</p>" : "") +
            (nrt.watchFor ? "<p><b>לעקוב:</b> " + esc(nrt.watchFor) + "</p>" : "") +
          "</div>"
        : "";
      mid = (c.headline && v.headline ? '<p class="v-regime">' + esc(v.headline) + "</p>" : "") +
        "<p>" + esc(v.subline || "") + "</p>" + narr;
    }
    var verdictCard =
      '<div class="card verdict tone-' + esc(v.tone || "") + '">' +
        '<div class="v-top">' +
          '<span class="emoji">' + h(v.emoji || "📊") + "</span>" +
          (tradeDate ? '<span class="vday">יום המסחר ' + tradeDate + "</span>" : "") +
        "</div>" +
        // הכותרת הראשית = סיכום היום המתחלף (conclusion.headline, למשל "יום ירידה מתון -0.2%")
        "<h2>" + esc(c.headline || v.headline || "סקירת שוק") + "</h2>" +
        mid + lights +
      "</div>";

    var fl = d.flow || {};
    var scoreCards =
      '<div class="grid grid-4" style="margin-top:16px">' +
      [["combined", "ציון משולב"], ["tech", "טכני"], ["breadth", "רוחב"], ["flow", "אופציות"]]
        .map(function (p) {
          var val = s[p[0]];
          var sub = "", tip = "";
          if (p[0] === "flow" && (fl.deltaLabel || fl.directionLabel)) {
            // ההימור נטו משוקלל-הדלתא (הכסף הגדול) — לא ציון-הכיוון הישן, שסתר את הדלתא
            if (fl.deltaLabel) {
              var dc = fl.deltaLabel === "דובי" ? "down" : (fl.deltaLabel === "שורי" ? "up" : "");
              sub = '<div class="sub">הכסף הגדול: <b class="' + dc + '">' + esc(fl.deltaLabel) + "</b></div>";
              tip = ' title="' + esc("קניית Calls $" + Math.round((fl.callBuyP || 0) / 1e6) + "M · מכירת Calls $" + Math.round((fl.callSellP || 0) / 1e6) +
                "M · קניית Puts $" + Math.round((fl.putBuyP || 0) / 1e6) + "M · מכירת Puts $" + Math.round((fl.putSellP || 0) / 1e6) + "M") + '"';
            } else {
              sub = '<div class="sub">' + esc(fl.directionLabel) + "</div>";
              if (fl.directionReason) tip = ' title="' + esc(fl.directionReason) + '"';
            }
          }
          return '<div class="card stat"' + tip + '><div class="label">' + p[1] + "</div>" +
            '<div class="value num ' + scoreBand(val) + '">' + (val == null ? "—" : val) + diffTag(p[0]) + "</div>" + sub + "</div>";
        }).join("") + "</div>";

    var marketCards =
      '<div class="grid grid-4" style="margin-top:16px">' +
      [
        ['S&P 500', fmtNum(e.spxPrice, 2), (e.pctMa200 != null ? e.pctMa200 + "% מעל MA200" : "")],
        ['VIX', fmtNum(e.vix, 1), (e.vix != null && e.vix < 20 ? "רגוע" : "מוגבר")],
        ['שיאים / שפלים', fmtNum(e.nhCount) + " / " + fmtNum(e.nlCount), "52 שבועות"],
        ['EQ vs SPX 20י', (e.eqSpx20 != null ? (e.eqSpx20 > 0 ? "+" : "") + e.eqSpx20 + "%" : "—"), "רוחב פנימי"]
      ].map(function (p) {
        return '<div class="card stat"><div class="label">' + p[0] + "</div>" +
          '<div class="value num">' + p[1] + "</div>" +
          '<div class="sub">' + esc(p[2]) + "</div></div>";
      }).join("") + "</div>";

    var concl = "";
    if (c.conclusion || c.recommendation) {
      var r = c.recommendation || {};
      concl =
        '<div class="section-title">📌 המסקנה של איציק</div>' +
        '<div class="card"><p style="margin:0 0 12px">' + esc(c.conclusion || "") + "</p>" +
        (r.action ? '<div class="reco"><h3>מה עושים</h3><p class="line">' + esc(r.action) + "</p>" +
          (r.improve ? '<p class="line"><b>ישתפר אם:</b> ' + esc(r.improve) + "</p>" : "") +
          (r.worsen ? '<p class="line"><b>יורע אם:</b> ' + esc(r.worsen) + "</p>" : "") + "</div>" : "") +
        "</div>";
    }

    // חותמת עדכון: בבית מוצגת בשורת הטלגרם (head-stamp); בטאב מדדים — inline בראש הכרטיס
    var stampHtml = "";
    if (opts.home) {
      var hs = document.getElementById("head-stamp");
      if (hs) hs.innerHTML = stamp(d._meta);
    } else {
      stampHtml = stamp(d._meta);
    }

    // בבית: כרטיס תמונת-המצב יושב בעמודה השמאלית (#home-verdict), הנתונים מתחת (קונטיינרים סטטיים)
    if (opts.home) {
      var hv = document.getElementById("home-verdict");
      if (hv) hv.innerHTML = verdictCard;
      el.innerHTML = scoreCards + marketCards;
    } else {
      el.innerHTML =
        stampHtml +
        verdictCard + scoreCards + marketCards +
        (opts.detail ? concl : "");   // "המסקנה של איציק" רק בטאב מדדים
    }
  }

  // טקסט מהמנוע מכיל הדגשות <b> בלבד — משחררים רק אותן אחרי escape
  function escB(s) {
    return esc(s).replace(/&lt;(\/?b)&gt;/g, "<$1>");
  }
  /* 4 הבלוקים של הערת-האנליסט (מנוע הכללים) — טאב מדדים */
  function aiBlocksHtml(d) {
    var ai = (d.aiSummary && d.aiSummary.date === d.date) ? d.aiSummary : null;
    if (!ai || !(ai.blocks || []).length) return "";
    return '<div class="section-title">🔬 ניתוח לפי תחום</div>' +
      '<div class="card ai-blocks">' +
      ai.blocks.map(function (b) {
        var integ = (b.title || "").indexOf("המשולבת") >= 0;
        return '<div class="ai-blk' + (integ ? " integ" : "") + '">' +
          '<div class="ai-blk-t">' + esc(b.title || "") + "</div>" +
          (b.lines || []).map(function (l) { return "<p>" + escB(l) + "</p>"; }).join("") +
        "</div>";
      }).join("") +
      (ai.watchFor ? '<p class="ai-blk-watch"><b>לעקוב:</b> ' + escB(ai.watchFor) + "</p>" : "") +
      "</div>";
  }

  /* ההימור נטו באופציות — 4 הרבעים משוקללי-הדלתא (טאב מדדים) */
  function flowQuadHtml(d) {
    var f = d.flow || {};
    if (f.callBuyP == null && f.putBuyP == null) return "";
    function m(v) { return v == null ? "—" : "$" + Math.round(v / 1e6) + "M"; }
    var tiltCls = f.deltaLabel === "דובי" ? "down" : (f.deltaLabel === "שורי" ? "up" : "");
    var cells = [
      ["קניית Calls", f.callBuyP, "up"], ["מכירת Calls", f.callSellP, "down"],
      ["קניית Puts", f.putBuyP, "down"], ["מכירת Puts", f.putSellP, "up"]
    ];
    return '<div class="section-title">🎯 ההימור נטו באופציות</div>' +
      '<div class="card">' +
      (f.deltaLabel ? '<p style="margin-top:0">הכסף הגדול נטו: <b class="' + tiltCls + '">' + esc(f.deltaLabel) + "</b>" +
        " (משוקלל-דלתא)" +
        (f.openingLean ? ' · פוזיציות חדשות: <b>' + esc(f.openingLean) + "</b>" : "") + "</p>" : "") +
      '<div class="fq-grid">' +
      cells.map(function (q) {
        return '<div class="fq-cell"><span class="fq-l">' + q[0] + '</span><b class="num ' + q[2] + '">' + m(q[1]) + "</b></div>";
      }).join("") + "</div>" +
      '<p class="stamp" style="margin-bottom:0">קנייה אגרסיבית של Calls ומכירת Puts = הימור שורי; קניית Puts ומכירת Calls = דובי. הציון בכרטיס "אופציות" מודד עוצמת זרימה ואינו כיוון. ' +
        'הנתון מבוסס על עסקאות אופציות בולטות/גדולות בלבד (לא כל נפח המסחר היומי) — לכן עשוי להיות שונה ממדדי "דלתא" כוללי-שוק בכלים אחרים (כמו Barchart).</p>' +
      "</div>";
  }

  /* עדכון-אירוע טרי — או null. תוקף: 18ש'; "לקראת המסחר" (preview) מחזיק 26ש'
     כדי לגשר מבוקר ראשון עד כתיבת שני, ומשני עד ניתוח שלישי 06:30 */
  function freshEventUpdate(ca) {
    var eu = ca && ca.eventUpdate;
    if (!eu || !eu.date || !eu.time || !eu.headline) return null;
    // הגנה: רוטינות אמורות לכתוב date בפורמט ISO (YYYY-MM-DD), אבל מדי פעם
    // חומק פורמט "D.M.YYYY" — במקום שהכותרת תיעלם בשקט (Date.parse מחזיר NaN
    // על כך), מנרמלים אותו ל-ISO כאן.
    var isoDate = /^\d{1,2}\.\d{1,2}\.\d{4}$/.test(eu.date)
      ? (function (p) { return p[2] + "-" + p[1].padStart(2, "0") + "-" + p[0].padStart(2, "0"); })(eu.date.split("."))
      : eu.date;
    var ts = Date.parse(isoDate + "T" + eu.time + ":00");
    if (isNaN(ts)) return null;
    var age = Date.now() - ts;
    var ttl = (eu.kind === "preview" ? 26 : 18) * 3600e3;
    return (age > -3600e3 && age < ttl) ? eu : null;
  }

  /* כרטיס "הניתוח היומי" המלא — בראש טאב מדדים */
  function claudeCardHtml(d) {
    var ca = (CA && CA.date === d.date) ? CA : null;
    if (!ca) return "";
    var eu = freshEventUpdate(CA);
    var euCalm2 = eu && (eu.kind === "midday" || eu.kind === "preview" || eu.kind === "preopen");
    var euLine = eu
      ? '<p class="' + (euCalm2 ? "np-evt-mid" : "np-evt") + '" style="margin:0 0 10px">' +
        (eu.kind === "midday" ? "🕑" : eu.kind === "preview" ? "🗓" : eu.kind === "preopen" ? "🔔" : "🔴") +
        " <b>" + (eu.kind === "preview" || eu.kind === "preopen" ? "" : "עדכון ") + esc(eu.event || "") + " · " + esc(eu.time || "") + ":</b> " + esc(eu.headline) + "</p>"
      : "";
    return '<div class="section-title" style="margin-top:0">🧠 הניתוח היומי</div>' +
      '<div class="card np-ca">' +
        euLine +
        '<h3 class="np-ca-h">' + esc(ca.headline) + "</h3>" +
        (ca.paragraphs || []).map(function (p) { return "<p>" + esc(p) + "</p>"; }).join("") +
        (ca.bottomline ? '<p class="np-ca-bottom">💡 ' + esc(ca.bottomline).replace("שורה תחתונה:", "<b>שורה תחתונה:</b>") + "</p>" : "") +
        (ca.watchFor ? "<p><b>לעקוב:</b> " + esc(ca.watchFor) + "</p>" : "") +
        (ca.confidence ? '<p class="np-ca-conf">רמת ביטחון: ' + esc(ca.confidence) + "</p>" : "") +
      "</div>";
  }

  function renderIndicesDetail(el, d) {
    var c = d.conclusion || {};
    var rot = d.rotation || {};
    var ro = d.riskOff || {};

    // ניתוח לפי תחום: 4 הבלוקים של מנוע-הכללים (מניות/סקטורים/אופציות/התמונה המשולבת);
    // הרשימה הישנה של מנוע-המסקנות נשארת רק כנפילה-חזרה כשאין בלוקים (כפילות אחרת)
    var analysis = aiBlocksHtml(d);
    if (!analysis && c.analysis && c.analysis.length) {
      analysis = '<div class="section-title">🔬 ניתוח לפי תחום</div><div class="card"><ul class="analysis">' +
        c.analysis.map(function (a) {
          return '<li class="tone-' + esc(a.tone || "") + '"><span class="tone-dot"></span>' +
            '<span class="domain">' + esc(a.domain) + "</span><span>" + esc(a.text) + "</span></li>";
        }).join("") + "</ul></div>";
    }
    analysis += flowQuadHtml(d);

    var sectors = "";
    if (rot.sectorRs) {
      var lead = rot.leadingSectors || [];
      sectors = '<div class="section-title">🔄 רוטציה סקטוריאלית</div>' +
        '<div class="card"><div class="chips">' +
        Object.keys(rot.sectorRs).sort(function (a, b) {
          return (rot.sectorRs[b].rs20 || 0) - (rot.sectorRs[a].rs20 || 0);
        }).map(function (k) {
          var isLead = lead.indexOf(k) !== -1;
          return '<span class="chip' + (isLead ? " lead" : "") + '">' +
            esc(SECTOR_HE[k] || k) + " " +
            '<span class="num ' + ((rot.sectorRs[k].rs20 || 0) >= 0 ? "up" : "down") + '">' +
            (rot.sectorRs[k].rs20 > 0 ? "+" : "") + rot.sectorRs[k].rs20 + "%</span></span>";
        }).join("") + "</div></div>";
    }

    var selling = "";
    if (ro.sellingDays && ro.sellingDays.length) {
      selling = '<div class="section-title">⚠️ לחץ מכירות מוסדי</div>' +
        '<div class="card"><p style="margin-top:0">' + esc(ro.stateLine || "") + "</p>" +
        '<div class="table-wrap"><table><thead><tr><th>תאריך</th><th class="num">שינוי %</th></tr></thead><tbody>' +
        ro.sellingDays.map(function (day) {
          return "<tr><td>" + esc(day.date) + '</td><td class="num down">' + day.chg + "%</td></tr>";
        }).join("") + "</tbody></table></div>" +
        (ro.actionLine ? '<p class="stamp" style="margin-bottom:0">' + esc(ro.actionLine) + "</p>" : "") +
        "</div>";
    }

    var narr = "";
    if (d.narrative) {
      var n = d.narrative;
      narr = '<div class="section-title">📖 רקע</div><div class="card">' +
        (n.today ? "<p><b>היום:</b> " + esc(n.today) + "</p>" : "") +
        (n.week ? "<p><b>השבוע:</b> " + esc(n.week) + "</p>" : "") +
        (n.watchFor ? '<p style="margin-bottom:0"><b>לעקוב:</b> ' + esc(n.watchFor) + "</p>" : "") +
        "</div>";
    }

    var head = '<div class="section-title" style="margin-top:0">📈 תמונת מצב מדדים</div>';
    var overview = document.createElement("div");
    renderMarketOverview(overview, d, { detail: true });

    el.innerHTML = "";
    el.insertAdjacentHTML("beforeend", head + claudeCardHtml(d) + INDICES_EXPLAINER);   // הניתוח היומי בראש, ואז ההסבר ותמונת המצב
    el.appendChild(overview);
    el.insertAdjacentHTML("beforeend", analysis + sectors + selling + narr);
    var link = document.createElement("p");
    link.className = "stamp";
    link.innerHTML = 'מקור: <a href="https://nditzik.github.io/indexes-status/" target="_blank" rel="noopener">דשבורד המדדים המלא ↗</a>';
    el.appendChild(link);
  }

  function chgClass(v) {
    var s = String(v || "").trim();
    if (s.charAt(0) === "-" || s.indexOf("−") === 0) return "down";
    if (s.charAt(0) === "+" || parseFloat(s) > 0) return "up";
    return "";
  }

  /* ---- momentum classification (ported verbatim from the local dashboard) ---- */
  var MIN_VOL = 750000;
  function passesBase(d) {
    var vol = +d.vol || 0, px = +d.price || 0, a = parseFloat(d.wtd_alpha),
        ma20 = +d.ma20 || 0, rsi = +d.rel_str || 0;
    if (!vol || vol <= 0) return false;
    if (!px || px <= 0) return false;
    if (d.wtd_alpha == null || isNaN(a) || a <= 0) return false;
    if (!ma20 || ma20 <= 0) return false;
    if (!rsi || rsi <= 0) return false;
    if (vol < MIN_VOL) return false;
    if (d.w52_chg) {
      var w = +d.w52_chg;
      if (!isNaN(w) && a < w) {
        var str = (d.strength || "").toLowerCase();
        if (!(str.indexOf("top") >= 0 || str.indexOf("max") >= 0 || str.indexOf("strong") >= 0)) return false;
      }
    }
    var stoch = +d.stoch || 0, ma50 = +d.ma50 || 0, ma100 = +d.ma100 || 0;
    if (rsi > 0 && stoch > 0 && rsi > 72 && stoch > 82) return false;
    if (px > 0 && ma50 > 0 && ma100 > 0 && px < ma50 && px < ma100) return false;
    if (d.strength && /weak/i.test(d.strength)) return false;
    if (d.opinion && /\bsell\b/i.test(d.opinion)) return false;
    return true;
  }
  function calcDipScore(d) {
    var rsi = parseFloat(d.rel_str || 0), stoch = parseFloat(d.stoch || 0),
        px = parseFloat(d.price || 0), ma50 = parseFloat(d.ma50 || 0),
        ma100 = parseFloat(d.ma100 || 0), rvol = parseFloat(d.rvol || 0);
    var score = 0, parts = 0;
    if (rsi > 0) { parts++; if (rsi >= 35 && rsi <= 58) score += 25; else if (rsi < 35) score += 10; else if (rsi <= 65) score += 12; }
    if (stoch > 0) { parts++; if (stoch >= 20 && stoch <= 48) score += 22; else if (stoch < 20) score += 10; else if (stoch <= 65) score += 10; }
    if (px > 0 && ma50 > 0) { parts++; if (px > ma50) score += 18; else score += 2; }
    if (px > 0 && ma100 > 0) { if (px > ma100) score += 10; }
    if (rvol > 0) { parts++; if (rvol < 0.7) score += 14; else if (rvol < 1.0) score += 8; else if (rvol < 1.3) score += 3; }
    if (parts === 0) return 0;
    return Math.min(100, Math.round(score));
  }
  function isDipEntry(d) {
    if ((d.signal_count || 0) < 2) return false;
    if (calcDipScore(d) < 65) return false;
    var px = +d.price || 0, ma20 = +d.ma20 || 0, ma50 = +d.ma50 || 0;
    var n20 = ma20 > 0 && px <= ma20 * 1.05 && px >= ma20 * 0.98;
    var n50 = ma50 > 0 && px <= ma50 * 1.05 && px >= ma50 * 0.98;
    return n20 || n50;
  }
  function isBreakoutEntry(d) {
    if ((d.signal_count || 0) < 2) return false;
    var px = +d.price || 0, ma20 = +d.ma20 || 0;
    if (!(ma20 > 0 && px >= ma20)) return false;
    var chg = +d.change_pct || 0, rv = +d.rvol || 0;
    if (chg >= 1.0 && rv >= 1.3) return true;
    var stoch = +d.stoch || 0, bbp = (d.bb_pct == null ? -1 : +d.bb_pct);
    if (chg >= 0 && rv >= 1.0 && stoch >= 75 && bbp >= 70) return true;
    return false;
  }
  function isReversalEntry(d) {
    if ((d.signal_count || 0) < 2) return false;
    if (calcDipScore(d) < 65) return false;
    var px = +d.price || 0, ma20 = +d.ma20 || 0, ma50 = +d.ma50 || 0;
    var on20 = ma20 > 0 && px >= ma20 && px <= ma20 * 1.05;
    var on50 = ma50 > 0 && px >= ma50 && px <= ma50 * 1.05;
    if (!(on20 || on50)) return false;
    if ((+d.change_pct || 0) < 0.3) return false;
    if ((+d.rvol || 0) <= 1.0) return false;
    return true;
  }

  /* תג "מדווחת בקרוב" — אזהרת דוחות לסוחרי סווינג (מהמפה שב-earnings.json) */
  var EARNW = {};
  function erBadge(sym) {
    var iso = EARNW[(sym || "").toUpperCase()];
    if (!iso) return "";
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
    if (!m) return "";
    var today = new Date();
    var isToday = today.getFullYear() === +m[1] && (today.getMonth() + 1) === +m[2] && today.getDate() === +m[3];
    var label = isToday ? "היום" : (+m[3]) + "." + (+m[2]);
    return '<span class="er-badge" title="מדווחת דוחות ב-' + (+m[3]) + "." + (+m[2]) + "." + m[1].slice(2) + '">📅 ' + label + "</span>";
  }

  var SIG_LABEL = { strength: "Strength", hot_prospects: "Hot", "6m_high": "6M-High", ttm_squeeze: "TTM", macd_buy: "MACD" };
  function tvLink(sym) {
    return '<a class="tv" href="https://www.tradingview.com/symbols/' + encodeURIComponent(sym) +
      '/" target="_blank" rel="noopener" title="פתח ב-TradingView">' + esc(sym) + " ↗</a>";
  }
  function fmt(v, d) { return (v == null || isNaN(v)) ? "—" : Number(v).toFixed(d == null ? 2 : d); }
  function pct(v) {
    if (v == null || isNaN(v)) return '<span class="num">—</span>';
    var cls = v > 0 ? "up" : (v < 0 ? "down" : "");
    return '<span class="num ' + cls + '">' + (v > 0 ? "+" : "") + Number(v).toFixed(2) + "%</span>";
  }

  function renderMomentum(el, d) {
    if (!d || !d.stocks || !d.stocks.length) {
      emptyPanel(el, "🚀", "מומנטום — בקרוב", "");
      return;
    }
    var base = d.stocks.filter(passesBase);
    var byAlpha = function (a, b) { return (b.wtd_alpha || 0) - (a.wtd_alpha || 0); };
    var cats = [
      { key: "s4", emoji: "🔥", title: "4 סיגנלים", rows: base.filter(function (x) { return x.signal_count >= 4; }).sort(byAlpha) },
      { key: "s3", emoji: "⚡", title: "3 סיגנלים", rows: base.filter(function (x) { return x.signal_count === 3; }).sort(byAlpha) },
      { key: "s2", emoji: "✨", title: "2 סיגנלים", rows: base.filter(function (x) { return x.signal_count === 2; }).sort(byAlpha) },
      { key: "dip", emoji: "📉", title: "כניסת דיפ", rows: base.filter(isDipEntry).sort(byAlpha) },
      { key: "brk", emoji: "🚀", title: "כניסת פריצה", rows: base.filter(isBreakoutEntry).sort(byAlpha) },
      { key: "rev", emoji: "🔄", title: "מניות בהיפוך", rows: base.filter(isReversalEntry).sort(byAlpha) }
    ];
    var firstNon = 0;
    for (var i = 0; i < cats.length; i++) { if (cats[i].rows.length) { firstNon = i; break; } }

    var nav = '<div class="chips" style="margin-bottom:14px">' + cats.map(function (c, i) {
      return '<button class="chip mom-tab' + (i === firstNon ? " lead" : "") + '" data-mom="' + i + '">' +
        c.emoji + " " + esc(c.title) + ' <span class="num">' + c.rows.length + "</span></button>";
    }).join("") + "</div>";

    var panels = cats.map(function (c, i) {
      var body;
      if (!c.rows.length) {
        body = '<div class="panel-empty" style="padding:34px">אין מניות בקטגוריה זו היום.</div>';
      } else {
        var rows = c.rows.map(function (r) {
          var sigs = (r.signals || []).map(function (s) {
            return '<span class="sig-badge" title="' + esc(SIG_LABEL[s] || s) + '">' + esc(SIG_LABEL[s] || s) + "</span>";
          }).join("");
          return "<tr>" +
            '<td class="num"><b>' + r.signal_count + "</b></td>" +
            "<td>" + tvLink(r.symbol) + erBadge(r.symbol) + "</td>" +
            '<td class="mom-name">' + esc(r.name) + "</td>" +
            '<td class="num">' + fmt(r.price) + "</td>" +
            "<td>" + pct(r.change_pct) + "</td>" +
            '<td class="num">' + fmt(r.rel_str, 0) + "</td>" +
            '<td class="num">' + fmt(r.stoch, 0) + "</td>" +
            '<td class="num">' + fmt(r.rvol) + "</td>" +
            '<td class="sig-cell">' + sigs + "</td></tr>";
        }).join("");
        body = '<div class="table-wrap"><table><thead><tr>' +
          '<th class="num">#</th><th>סימבול</th><th>שם</th><th class="num">מחיר</th>' +
          '<th class="num">שינוי</th><th class="num">RSI</th><th class="num">Stoch</th>' +
          '<th class="num">RVOL</th><th>סיגנלים</th>' +
          "</tr></thead><tbody>" + rows + "</tbody></table></div>";
      }
      return '<div class="mom-list" data-mom="' + i + '" style="display:' + (i === firstNon ? "block" : "none") + '">' + body + "</div>";
    }).join("");

    el.innerHTML = stamp(d._meta) +
      '<div class="section-title" style="margin-top:0">🚀 סורק מומנטום</div>' +
      tabIntro("momentum") +
      '<p class="stamp" style="margin-top:-6px">' + base.length + ' מניות איכות (2+ סיגנלים, אחרי פילטר בסיס) · לחיצה על טיקר פותחת ב-TradingView</p>' +
      nav + panels +
      '<p class="stamp"><a href="https://nditzik.github.io/stocks-momentum/" target="_blank" rel="noopener">דשבורד המומנטום המלא ↗</a></p>';

    el.querySelectorAll(".mom-tab").forEach(function (b) {
      b.addEventListener("click", function () {
        var idx = b.dataset.mom;
        el.querySelectorAll(".mom-tab").forEach(function (x) { x.classList.toggle("lead", x.dataset.mom === idx); });
        el.querySelectorAll(".mom-list").forEach(function (x) { x.style.display = x.dataset.mom === idx ? "block" : "none"; });
      });
    });
  }

  /* ארכיון תדריכים/סקירות — data/briefing_archive.json (30 יום אחורה) */
  var BARCHIVE = null, BRIEF_DAY = null, MORN_DAY = null, MORND = null;
  function archDays(kinds, excludeIso) {
    if (!BARCHIVE || !BARCHIVE.days) return [];
    return Object.keys(BARCHIVE.days).filter(function (k) {
      if (k === excludeIso) return false;
      var e = BARCHIVE.days[k];
      return kinds.some(function (kd) { return e[kd]; });
    }).sort().reverse();
  }
  function archNavHtml(cls, days, sel, latestLabel) {
    if (!days.length) return "";
    return '<div class="chips arch-chips" style="margin-bottom:12px">' +
      '<button class="chip ' + cls + (sel ? "" : " lead") + '" data-day="">' + esc(latestLabel) + "</button>" +
      days.map(function (k) {
        return '<button class="chip ' + cls + (sel === k ? " lead" : "") + '" data-day="' + k +
          '"><span dir="ltr">' + esc(fmtTradeDate(k)) + "</span></button>";
      }).join("") + "</div>";
  }

  function renderBriefing(el, d) {
    var slots = [];
    if (d && d.morning) slots.push(["morning", "בוקר", d.morning]);
    if (d && d.afternoon) slots.push(["afternoon", "אחר הצהריים", d.afternoon]);
    if (!slots.length) {
      emptyPanel(el, "📣", "תדרוך משקיעים — בקרוב", "הטאב יתמלא ברגע שצינור הג'ימייל יופעל.");
      return;
    }
    // המהדורה החדשה ביותר → iso (כדי לא להציג אותה פעמיים בצ'יפים);
    // בבוקר briefing.json מחזיק בוקר-של-היום + אחה"צ-של-אתמול — לוקחים את המאוחר
    function isoOf(s) { var m = /^(\d{2})\/(\d{2})\/(\d{4})/.exec(s || ""); return m ? m[3] + "-" + m[2] + "-" + m[1] : ""; }
    var aIso = isoOf(d.morning && d.morning.dateLabel), bIso = isoOf(d.afternoon && d.afternoon.dateLabel);
    var latestIso = aIso > bIso ? aIso : bIso;
    var days = archDays(["morning", "afternoon"], latestIso);
    var sel = (BRIEF_DAY && days.indexOf(BRIEF_DAY) >= 0) ? BRIEF_DAY : null;
    var archNav = archNavHtml("brief-day", days, sel, latestIso ? fmtTradeDate(latestIso) : "אחרון");
    if (sel) {   // יום ארכיון נבחר — הצג את המהדורות השמורות שלו
      var e = BARCHIVE.days[sel];
      slots = [];
      if (e.morning) slots.push(["morning", "בוקר", { subject: e.morning.subject, time: e.morning.time, file: e.morning.file, dateLabel: fmtTradeDate(sel) }]);
      if (e.afternoon) slots.push(["afternoon", "אחר הצהריים", { subject: e.afternoon.subject, time: e.afternoon.time, file: e.afternoon.file, dateLabel: fmtTradeDate(sel) }]);
    }
    var nav = '<div class="chips" style="margin-bottom:12px">' +
      slots.map(function (s, i) {
        var sl = s[2];
        return '<button class="chip brief-tab' + (i === 0 ? " lead" : "") + '" data-brief="' + s[0] + '">' +
          h(sl.sentiment && sl.sentiment.emoji) + " " + esc(s[1]) +
          (sl.time ? ' <span class="num">' + esc(sl.time) + "</span>" : "") + "</button>";
      }).join("") + "</div>";

    var frames = slots.map(function (s, i) {
      var sl = s[2];
      return '<div class="brief-view" data-brief="' + s[0] + '" style="display:' + (i === 0 ? "block" : "none") + '">' +
        '<div class="card" style="padding:14px 18px;margin-bottom:12px">' +
        "<strong>" + esc(sl.subject || "") + "</strong>" +
        (sl.sentiment && sl.sentiment.text ? ' · <span>' + h(sl.sentiment.emoji) + " " + esc(sl.sentiment.text) + "</span>" : "") +
        (sl.dateLabel ? '<div class="stamp" style="margin:4px 0 0">' + esc(sl.dateLabel) + (sl.time ? " · " + esc(sl.time) : "") + "</div>" : "") +
        "</div>" +
        '<iframe class="brief-frame" src="' + bust(sl.file, d._meta) + '" title="' + esc(sl.subject || "") +
        '" style="width:100%;border:1px solid var(--border);border-radius:14px;background:#fff;min-height:640px" ' +
        'onload="try{this.style.height=(this.contentWindow.document.body.scrollHeight+30)+\'px\'}catch(e){}"></iframe></div>';
    }).join("");

    el.innerHTML = stamp(d._meta) +
      '<div class="section-title" style="margin-top:0">📣 תדרוך משקיעים</div>' + archNav + nav + frames;

    el.querySelectorAll(".brief-tab").forEach(function (b) {
      b.addEventListener("click", function () {
        var k = b.dataset.brief;
        el.querySelectorAll(".brief-tab").forEach(function (x) { x.classList.toggle("lead", x.dataset.brief === k); });
        el.querySelectorAll(".brief-view").forEach(function (x) { x.style.display = x.dataset.brief === k ? "block" : "none"; });
      });
    });
    el.querySelectorAll(".brief-day").forEach(function (b) {
      b.addEventListener("click", function () { BRIEF_DAY = b.dataset.day || null; renderBriefing(el, d); });
    });
  }

  /* טאב "דיווחים" — לוח דוחות שבועי (ב'–ו') בסגנון Earnings Whispers */
  function renderWeekCal(el, d) {
    var week = (d && d.week) || [];
    if (!week.length) {
      emptyPanel(el, "📅", "לוח דיווחים — בקרוב", "");
      return;
    }
    var first = week[0], last = week[week.length - 1];
    var year = (first.date || "").slice(0, 4);
    var todayIso = (function () {
      var n = new Date();
      return n.getFullYear() + "-" + ("0" + (n.getMonth() + 1)).slice(-2) + "-" + ("0" + n.getDate()).slice(-2);
    })();
    var cols = week.map(function (day) {
      var tiles = day.companies.map(function (c) {
        return '<a class="wk-tile" href="https://www.tradingview.com/symbols/' + encodeURIComponent(c.ticker) +
          '/" target="_blank" rel="noopener" title="' + esc(c.name) + '">' +
          '<img src="https://financialmodelingprep.com/image-stock/' + encodeURIComponent(c.ticker) +
            '.png" alt="" loading="lazy" onerror="this.remove()">' +
          '<span dir="ltr">' + esc(c.ticker) + "</span></a>";
      }).join("");
      var more = day.total > day.companies.length
        ? '<div class="wk-more">+' + (day.total - day.companies.length) + " נוספות</div>" : "";
      var empty = !day.total ? '<div class="wk-more">אין דיווחים</div>' : "";
      return '<div class="wk-day' + (day.date === todayIso ? " today" : "") + '">' +
        '<div class="wk-head"><b>' + esc(day.dow) + '</b><span class="num" dir="ltr">' + esc(day.label) + "</span>" +
          (day.total ? '<span class="wk-n">' + day.total + "</span>" : "") + "</div>" +
        '<div class="wk-list">' + tiles + empty + "</div>" + more + "</div>";
    }).join("");
    el.innerHTML = stamp(d._meta) +
      '<div class="section-title" style="margin-top:0">📅 לוח דיווחים שבועי</div>' +
      '<p class="stamp" style="margin-top:-6px">שבוע המסחר <span dir="ltr">' + esc(first.label) + "–" + esc(last.label) + "." + esc(year) +
      "</span> · מובילות לפי שווי שוק · לחיצה פותחת ב-TradingView · מתעדכן בכל שבת</p>" +
      '<div class="wk-grid">' + cols + "</div>";
  }

  /* טאב סקטורים — הדוח השבועי האחרון + ארכיון שבועות קודמים */
  var SECT = null;
  function secDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
    return m ? (+m[3]) + "." + (+m[2]) + "." + m[1].slice(2) : iso;
  }
  function renderSectors(el, d) {
    SECT = d;
    var reps = (d && d.reports) || [];
    if (!reps.length) {
      emptyPanel(el, "🔄", "דוח סקטורים — בקרוב", "הדוח השבועי הראשון בדרך.");
      return;
    }
    var nav = reps.length > 1
      ? '<div class="chips" style="margin-bottom:12px">' + reps.map(function (r, i) {
          return '<button class="chip sec-tab' + (i === 0 ? " lead" : "") + '" data-sec="' + i + '">' + esc(secDate(r.date)) + "</button>";
        }).join("") + "</div>"
      : "";
    el.innerHTML = stamp(d._meta) +
      '<div class="section-title" style="margin-top:0">🔄 דוח סקטורים שבועי</div>' +
      nav + '<div id="sec-view"></div>';
    showSector(0);
    el.querySelectorAll(".sec-tab").forEach(function (b) {
      b.addEventListener("click", function () {
        el.querySelectorAll(".sec-tab").forEach(function (x) { x.classList.toggle("lead", x === b); });
        showSector(+b.dataset.sec);
      });
    });
  }
  function showSector(i) {
    var view = document.getElementById("sec-view");
    if (!view || !SECT) return;
    var r = (SECT.reports || [])[i];
    if (!r) return;
    view.innerHTML =
      '<div class="card" style="padding:14px 18px;margin-bottom:12px">' +
        "<strong>" + esc(r.title) + "</strong>" +
        '<div class="stamp" style="margin:4px 0 0">שבוע שהסתיים ב-' + esc(secDate(r.date)) + "</div></div>" +
      // תוכן רחב (גרפים/טבלאות) — בנייד גלילה אופקית + מדידת-גובה חוזרת
      '<div class="frame-scroll"><iframe class="brief-frame trd-frame" src="' + bust(r.file, SECT._meta) + '" title="' + esc(r.title) +
      '" style="width:100%;border:1px solid var(--border);border-radius:14px;background:#fff;min-height:640px" ' +
      'onload="__fitFrame(this)"></iframe></div>';
  }

  /* טאב "הצעות לטרייד" — דוחות Four Pillars וכד', כמו סקטורים (יומי במקום שבועי) */
  var TRAD = null;
  function renderTrades(el, d) {
    TRAD = d;
    var reps = (d && d.reports) || [];
    if (!reps.length) {
      emptyPanel(el, "💡", "הצעות לטרייד — בקרוב", "הדוח הראשון בדרך.");
      return;
    }
    var nav = reps.length > 1
      ? '<div class="chips arch-chips" style="margin-bottom:12px">' + reps.map(function (r, i) {
          return '<button class="chip trd-tab' + (i === 0 ? " lead" : "") + '" data-trd="' + i +
            '"><span dir="ltr">' + esc(fmtTradeDate(r.date) || r.date) + "</span></button>";
        }).join("") + "</div>"
      : "";
    // קטגוריית-משנה קבועה: מצגת הלימוד של השיטה (PDF, נפתח בכרטיסייה חדשה)
    var method = d.method
      ? '<a class="card trd-method" href="' + esc(d.method.url) + '" target="_blank" rel="noopener">' +
          '<span class="trd-method-icon">📚</span>' +
          '<span><b>' + esc(d.method.title) + '</b><span class="trd-method-sub">קובץ PDF · מומלץ לקרוא לפני הסריקות · נפתח בחלון חדש</span></span>' +
        "</a>"
      : "";
    el.innerHTML = stamp(d._meta) +
      '<div class="section-title" style="margin-top:0">💡 הצעות לטרייד</div>' +
      tabIntro("trades") + method +
      '<div class="section-title" style="font-size:.95rem">🔎 סריקות יומיות</div>' +
      nav + '<div id="trd-view"></div>';
    showTrade(0);
    el.querySelectorAll(".trd-tab").forEach(function (b) {
      b.addEventListener("click", function () {
        el.querySelectorAll(".trd-tab").forEach(function (x) { x.classList.toggle("lead", x === b); });
        showTrade(+b.dataset.trd);
      });
    });
    renderTriIndex();
  }
  function showTrade(i) {
    var view = document.getElementById("trd-view");
    if (!view || !TRAD) return;
    var r = (TRAD.reports || [])[i];
    if (!r) return;
    view.innerHTML =
      '<div class="card" style="padding:14px 18px;margin-bottom:12px">' +
        "<strong>" + esc(r.title) + "</strong>" +
        '<div class="stamp" style="margin:4px 0 0">נכון ל-<span dir="ltr">' + esc(fmtTradeDate(r.date) || r.date) + "</span></div></div>" +
      // עטיפת גלילה-אופקית: הטבלאות בדוח רחבות — בנייד גוללים אופקית במקום להימחץ
      '<div class="frame-scroll"><iframe class="brief-frame trd-frame" src="' + bust(r.file, TRAD._meta) + '" title="' + esc(r.title) +
      '" style="width:100%;border:1px solid var(--border);border-radius:14px;background:#fff;min-height:640px" ' +
      'onload="__fitFrame(this)"></iframe></div>';
  }

  function renderMorning(el, d) {
    if (!d || d._status === "pending" || !d.file) {
      emptyPanel(el, "🌅", "סקירת בוקר — בקרוב", "תחובר ברגע שצינור ה-Barchart יופעל.");
      return;
    }
    // ארכיון: היום החדש ביותר באינדקס = הסקירה הנוכחית — הצ'יפ הראשון מייצג אותו
    var revDays = archDays(["review"], "");
    var latestRev = revDays.length ? revDays[0] : "";
    var days = revDays.slice(1);
    var sel = (MORN_DAY && days.indexOf(MORN_DAY) >= 0) ? MORN_DAY : null;
    var archNav = archNavHtml("morn-day", days, sel, latestRev ? fmtTradeDate(latestRev) : "אחרון");
    var subject = d.subject, dateLabel = d.dateLabel, time = d.time, file = d.file;
    if (sel) {
      var e = BARCHIVE.days[sel].review;
      subject = e.subject; dateLabel = fmtTradeDate(sel); time = e.time; file = e.file;
    }
    // חיווי סופ"ש/חג: הצינור רץ אבל ל-Barchart לא היו ניוזלטרים — שקיפות שהכול חי
    var noticeBar = (d.notice && !sel)
      ? '<div class="card" style="padding:10px 16px;margin-bottom:12px;font-size:.86rem">🔕 <b><span dir="ltr">' +
        esc(fmtTradeDate(d.notice.date) || d.notice.date) + "</span></b> — אין ניוזלטרים חדשים מ-Barchart" +
        (d.notice.time ? ' (נבדק ב-<span dir="ltr">' + esc(d.notice.time) + "</span>)" : "") +
        " · מוצגת הסקירה האחרונה שהתקבלה</div>"
      : "";
    el.innerHTML = stamp(d._meta) +
      '<div class="section-title" style="margin-top:0">🌅 סקירת בוקר</div>' + archNav + noticeBar +
      '<div class="card" style="padding:14px 18px;margin-bottom:12px">' +
      "<strong>" + esc(subject || "סיכום Barchart יומי") + "</strong>" +
      (dateLabel ? '<div class="stamp" style="margin:4px 0 0">' + esc(dateLabel) +
        (time ? " · " + esc(time) : "") + "</div>" : "") +
      "</div>" +
      '<iframe class="brief-frame" src="' + bust(file, d._meta) + '" title="' + esc(subject || "") +
      '" style="width:100%;border:1px solid var(--border);border-radius:14px;background:#fff;min-height:640px" ' +
      'onload="try{this.style.height=(this.contentWindow.document.body.scrollHeight+30)+\'px\'}catch(e){}"></iframe>';
    el.querySelectorAll(".morn-day").forEach(function (b) {
      b.addEventListener("click", function () { MORN_DAY = b.dataset.day || null; renderMorning(el, d); });
    });
  }

  function renderCandidates(el, d) {
    if (!d || d._status === "pending" || !d.candidates) {
      emptyPanel(el, "🎯", "מועמדים — בקרוב", "יחובר ברגע שצינור ה-IBKR יופעל.");
      return;
    }
    if (!d.candidates.length) {
      el.innerHTML = stamp(d._meta) +
        '<div class="panel-empty"><span class="emoji">🎯</span><strong>אין מועמדים ל-<span dir="ltr">' +
        esc(fmtTradeDate(d.date) || d.date || "") + "</span></strong><p style=\"margin:8px 0 0\">הסריקה לא מצאה איתותים היום.</p></div>";
      return;
    }
    function n(v, dgts) { return (v == null || isNaN(v)) ? "—" : Number(v).toFixed(dgts); }
    var rows = d.candidates.map(function (c) {
      return "<tr><td class=\"num\">" + c.rank + "</td>" +
        "<td>" + tvLink(c.symbol) + erBadge(c.symbol) + "</td>" +
        "<td>" + esc(c.setup || "") + "</td>" +
        '<td class="num">' + n(c.entry, 2) + "</td>" +
        '<td class="num">' + n(c.stop, 2) + "</td>" +
        '<td class="num">' + n(c.target, 2) + "</td>" +
        '<td class="num ' + (c.risk_pct > 5 ? "down" : "") + '">' + n(c.risk_pct, 1) + "%</td>" +
        '<td class="num up">' + n(c.tp_pct, 1) + "%</td>" +
        '<td class="num">' + n(c.rvol, 2) + "</td>" +
        '<td class="num ' + (c.hist_r >= 0 ? "up" : "down") + '">' + n(c.hist_r, 1) + "</td></tr>";
    }).join("");

    el.innerHTML = stamp(d._meta) +
      '<div class="section-title" style="margin-top:0">🎯 מועמדים למסחר (IBKR)</div>' +
      tabIntro("candidates") +
      '<div class="card" style="padding:14px 18px;margin-bottom:12px">' +
      "<strong>הנתונים מיום <span dir=\"ltr\">" + esc(fmtTradeDate(d.date)) + "</span>" +
      (prevTradingDate(d.date) ? " ותקפים ליום המסחר של <span dir=\"ltr\">" + esc(fmtTradeDate(prevTradingDate(d.date))) + "</span>" : "") +
      "</strong> · " + (d.count || 0) + " מועמדים" +
      (d.shown && d.shown < d.count ? " (מוצגים " + d.shown + " מובילים)" : "") +
      '<div class="stamp" style="margin:6px 0 0">Entry/Stop/Target ברמות המערכת · R היסטורי = ביצוע 2 שנים · מסודר לפי דירוג משולב · לחיצה על טיקר פותחת ב-TradingView</div></div>' +
      '<div class="table-wrap"><table><thead><tr>' +
      "<th class=\"num\">#</th><th>סימבול</th><th>Setup</th>" +
      "<th class=\"num\">כניסה</th><th class=\"num\">סטופ</th><th class=\"num\">מטרה</th>" +
      "<th class=\"num\">סיכון</th><th class=\"num\">TP</th><th class=\"num\">RVOL</th><th class=\"num\">R היסט'</th>" +
      "</tr></thead><tbody>" + rows + "</tbody></table></div>";
  }

  function renderReports(el, d) {
    var reports = (d && d.reports) || [];
    if (!reports.length) {
      emptyPanel(el, "📑", "ניתוח דוחות חברות — בקרוב",
        "כאן יופיעו ניתוחי דוחות רבעוניים של חברות. הדוח הראשון בדרך.");
      return;
    }
    var cards = reports.map(function (r, i) {
      var head = '<div class="rep-head">' +
        (r.logo ? '<img class="rep-logo" src="' + esc(r.logo) + '" alt="' + esc(r.ticker || "") + '" onerror="this.remove()">' : "") +
        (r.ticker ? '<span class="rep-ticker">' + esc(r.ticker) + "</span>" : "") + "</div>";
      return '<button class="rep-card" data-rep="' + i + '">' + head +
        '<span class="rep-title">' + esc(r.title || r.file) + "</span>" +
        (r.date ? '<span class="rep-date">' + esc(r.date) + "</span>" : "") + "</button>";
    }).join("");
    el.innerHTML = stamp(d._meta) +
      '<div class="section-title" style="margin-top:0">📑 ניתוח דוחות חברות</div>' +
      '<div id="rep-list" class="rep-grid">' + cards + "</div>" +
      '<div id="rep-view"></div>';

    var list = el.querySelector("#rep-list");
    var view = el.querySelector("#rep-view");
    function back() { view.style.display = "none"; view.innerHTML = ""; list.style.display = ""; }
    el.querySelectorAll(".rep-card").forEach(function (b) {
      b.addEventListener("click", function () {
        var r = reports[+b.dataset.rep];
        list.style.display = "none";
        view.style.display = "block";
        view.innerHTML =
          '<div class="rep-bar"><button class="cta rep-back">← חזרה לרשימה</button>' +
          '<a class="cta" href="' + esc(r.file) + '" target="_blank" rel="noopener">פתח במסך מלא ↗</a></div>' +
          '<iframe class="brief-frame" src="' + bust(r.file, d._meta) + '" title="' + esc(r.title || "") +
          '" style="width:100%;border:1px solid var(--border);border-radius:14px;background:#fff;min-height:640px;margin-top:12px" ' +
          'onload="try{this.style.height=(this.contentWindow.document.body.scrollHeight+30)+\'px\'}catch(e){}"></iframe>';
        view.querySelector(".rep-back").addEventListener("click", back);
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  /* ---------- boot ---------- */
  function boot() {
    loadTicker();
    initSearch();
    renderDayMeta();
    setInterval(renderDayMeta, 3600000);   // מתרענן שעה-שעה (חוצה-חצות)
    setInterval(loadTicker, 180000);        // הקובץ מהשרת (ספארקים + tnx) כל 3 דק'
    setInterval(refreshTickerLive, 60000);  // מחירים חיים מהסורק כל דקה
    refreshHeat();
    setInterval(refreshHeat, 60000);        // מפת החום הסקטוריאלית (רצועה מתחת לטיקר)
    setInterval(function () {         // ציטוטים חיים למניות במוקד
      if (FOCUS_SYMS) refreshFocusQuotes(FOCUS_SYMS.split(","), true);
    }, 180000);
    startClock();                    // שעון המסחר בשורת הכותרת

    // היסטוריית ציונים — גרף המגמה + חצי שינוי-יומי
    // שומרי-שינוי לרענון התקופתי: מרנדרים מחדש רק כשהתוכן באמת השתנה,
    // כדי לא להפריע לקורא (גלילה/iframe פתוח) על כל מחזור
    var DAILY_SIGS = {};
    function freshD(key, d) {
      var sig = contentSig(d);
      if (DAILY_SIGS[key] === sig) return false;
      DAILY_SIGS[key] = sig;
      return true;
    }

    // home content — news (pulse middle), movers + earnings (split row); each renders as it lands.
    // חדשות + בולטות מתרעננות לבד כל 5 דק' כשהדף פתוח (כמו סרט המדדים)
    function loadLiveContent() {
      fetchJSON("data/news.json")
        .then(function (d) { NEWS = d; renderPulseNews(); })
        .catch(function () {});
      fetchJSON("data/movers.json")
        .then(function (d) { MOVERS = d; renderHomeSplit(); renderFocus(); })
        .catch(function () {});
      fetchJSON("data/focus_history.json")
        .then(function (d) { FHIST = d; renderFocus(); })
        .catch(function () {});
      fetchJSON("data/pulse.json")
        .then(function (d) { PULSE_X = d; renderPulseX(); })
        .catch(function () {});
      // תדריך חדש (בוקר/צהריים) נכנס לבד לדף הבית ולטאב — רק כשבאמת השתנה
      fetchJSON("data/briefing.json")
        .then(function (d) {
          var stampNow = (d._meta || {}).updatedAt || "";
          if (stampNow && stampNow === lastBriefStamp) return;
          lastBriefStamp = stampNow;
          BRIEF = d;
          renderHomeBriefing();
          renderClockNext();
          renderBriefing(document.getElementById("panel-briefing"), d);
          noteSig("briefing", d);
        })
        .catch(function () {
          if (!BRIEF) emptyPanel(document.getElementById("panel-briefing"), "📣", "תדרוך משקיעים — בקרוב", "");
        });
    }
    var lastBriefStamp = "";

    // תוכן "יומי" (מדדים/מומנטום/מועמדים/דוחות/סקטורים/…): נטען בכניסה
    // ומתרענן כל 5 דק' — כך עדכון של אחד הדשבורדים נכנס לדף הפתוח בלי F5
    function loadDaily() {
      fetchJSON("data/history.json")
        .then(function (d) {
          if (!freshD("history", d)) return;
          HIST = d; computeDiffs();
          renderLead();   // חצי השינוי-היומי ברייל + הספארקליין
          if (INDD) renderIndicesDetail(document.getElementById("panel-indices"), INDD);
        })
        .catch(function () {});
      fetchJSON("data/earnings.json")
        .then(function (d) {
          if (!freshD("earnings", d)) return;
          EARN = d; EARNW = d.window || {};
          renderHomeSplit();
          renderWeekCal(document.getElementById("panel-weekcal"), d);
          // תגי "מדווחת בקרוב" על טבלאות שכבר רונדרו לפני שהמפה הגיעה
          if (MOMD) renderMomentum(document.getElementById("panel-momentum"), MOMD);
          if (CANDD) renderCandidates(document.getElementById("panel-candidates"), CANDD);
          renderFocus();
        })
        .catch(function () { if (!EARN) emptyPanel(document.getElementById("panel-weekcal"), "📅", "לוח דיווחים — בקרוב", ""); });
      // Home + indices share the indices dataset
      fetchJSON("data/indices.json").then(function (d) {
        if (!freshD("indices", d)) return;
        INDD = d;
        renderLead();
        renderIndicesDetail(document.getElementById("panel-indices"), d);
        renderFocus();   // התאריך בכותרת "מניות במוקד" תלוי ב-INDD
        noteSig("indices", d);
      }).catch(function (err) {
        // כשל מדדים מפיל רק את הידיעה המובילה — שאר הבית ממשיך לעבוד
        if (INDD) return;
        emptyPanel(document.getElementById("lead-main"), "📡", "נתוני השוק לא נטענו", String(err.message || err));
        emptyPanel(document.getElementById("panel-indices"), "📡", "נתוני המדדים לא נטענו", "");
      });
      fetchJSON("data/momentum.json")
        .then(function (d) { if (!freshD("momentum", d)) return; MOMD = d; renderMomentum(document.getElementById("panel-momentum"), d); renderFocus(); renderHomeSplit(); noteSig("momentum", d); })
        .catch(function () { if (!MOMD) emptyPanel(document.getElementById("panel-momentum"), "🚀", "מומנטום — בקרוב", ""); });
      fetchJSON("data/sectors.json")
        .then(function (d) { if (!freshD("sectors", d)) return; renderSectors(document.getElementById("panel-sectors"), d); noteSig("sectors", d); })
        .catch(function () { if (!("sectors" in DAILY_SIGS)) emptyPanel(document.getElementById("panel-sectors"), "🔄", "דוח סקטורים — בקרוב", ""); });
      fetchJSON("data/morning.json")
        .then(function (d) { if (!freshD("morning", d)) return; MORND = d; renderMorning(document.getElementById("panel-morning"), d); noteSig("morning", d); })
        .catch(function () { if (!("morning" in DAILY_SIGS)) emptyPanel(document.getElementById("panel-morning"), "🌅", "סקירת בוקר — בקרוב", ""); });
      fetchJSON("data/econ.json")
        .then(function (d) { if (!freshD("econ", d)) return; ECON = d; renderEcon(); })
        .catch(function () {});
      // הניתוח היומי של Claude — מוצג בבית (תקציר) ובטאב מדדים (מלא)
      fetchJSON("data/claude_analysis.json")
        .then(function (d) {
          if (!freshD("claude", d)) return;
          CA = d;
          renderLead();
          if (INDD) renderIndicesDetail(document.getElementById("panel-indices"), INDD);
        })
        .catch(function () {});
      // אינדקס הארכיון (תדריכים + סקירות, 30 יום) — מרענן את הצ'יפים בשני הטאבים
      fetchJSON("data/briefing_archive.json")
        .then(function (d) {
          if (!freshD("barchive", d)) return;
          BARCHIVE = d;
          if (BRIEF) renderBriefing(document.getElementById("panel-briefing"), BRIEF);
          if (MORND) renderMorning(document.getElementById("panel-morning"), MORND);
        })
        .catch(function () {});
      fetchJSON("data/candidates.json")
        .then(function (d) { if (!freshD("candidates", d)) return; CANDD = d; renderCandidates(document.getElementById("panel-candidates"), d); renderFocus(); renderHomeSplit(); noteSig("candidates", d); })
        .catch(function () { if (!CANDD) emptyPanel(document.getElementById("panel-candidates"), "🎯", "מועמדים — בקרוב", ""); });
      fetchJSON("data/trades.json")
        .then(function (d) { if (!freshD("trades", d)) return; renderTrades(document.getElementById("panel-trades"), d); noteSig("trades", d); })
        .catch(function () { if (!("trades" in DAILY_SIGS)) emptyPanel(document.getElementById("panel-trades"), "💡", "הצעות לטרייד — בקרוב", ""); });
      fetchJSON("data/reports.json")
        .then(function (d) { if (!freshD("reports", d)) return; REPD = d; renderReports(document.getElementById("panel-reports"), d); renderFocus(); noteSig("reports", d); })
        .catch(function () { if (!REPD) emptyPanel(document.getElementById("panel-reports"), "📑", "ניתוח דוחות — בקרוב", ""); });
      fetchJSON("data/_health.json")
        .then(function (d) {
          if (!freshD("health", d)) return;
          renderHealth(document.getElementById("health"), d);
          renderTodayBar(document.getElementById("today-bar"), d);
        })
        .catch(function () {});
      // מבזק שוק — תנועה חדה תוך-יומית (מוצג בכל הטאבים, רק כשהמבזק טרי)
      fetchJSON("data/flash.json")
        .then(renderFlash)
        .catch(function () {});
      // הסתברויות שוקי חיזוי
      fetchJSON("data/bets.json")
        .then(function (d) { if (!freshD("bets", d)) return; renderBets(d); })
        .catch(function () {});
    }

    loadLiveContent();
    setInterval(loadLiveContent, 300000);
    loadDaily();
    setInterval(loadDaily, 300000);

    // סלולר/טאב ברקע: דפדפנים מקפיאים טיימרים — כשחוזרים לדף, רענון מיידי
    var lastWake = Date.now();
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState !== "visible") return;
      if (Date.now() - lastWake < 120000) return;
      lastWake = Date.now();
      loadTicker(); loadLiveContent(); loadDaily();
    });

    // החלפת קבוצות בבולטות (delegation — שורד רינדור מחדש)
    var splitEl = document.getElementById("home-split");
    if (splitEl) splitEl.addEventListener("click", function (e) {
      var b = e.target.closest(".mv-tab");
      if (!b) return;
      MV_CUR = b.dataset.g;
      renderHomeSplit();
    });

    // deep-link
    var start = location.hash.slice(1);
    if (start && document.getElementById("panel-" + start)) activate(start);
  }

  function renderHealth(el, d) {
    if (!el || !d || !d.sources) return;
    var STAT = {
      ok: ["ok", "מעודכן"], stale: ["stale", "מיושן"],
      down: ["down", "לא זמין"], pending: ["pending", "טרם חובר"]
    };
    var chips = d.sources.map(function (s) {
      var st = STAT[s.status] || STAT.down;
      var when = s.updatedAt ? "עודכן " + s.updatedAt : (s.detail || st[1]);
      return '<span class="hchip ' + st[0] + '" title="' + esc(s.label + " — " + when) + '">' +
        '<span class="hdot"></span>' + esc(s.label) + "</span>";
    }).join("");
    el.innerHTML =
      '<span class="hlabel">מצב מקורות:</span>' + chips +
      (d.generatedAt ? '<span class="hgen">נבדק ' + esc(d.generatedAt) + "</span>" : "");
  }

  function loadPlaceholder(name, emoji, title) {
    var el = document.getElementById("panel-" + name);
    fetchJSON("data/" + name + ".json").then(function (d) {
      if (!d || d._status === "pending") {
        emptyPanel(el, emoji, title + " — בקרוב", (d && d._note) || "הטאב הזה יחובר בשלב הבא של הבנייה.");
      } else {
        // future: real renderer per tab; for now show note if provided
        emptyPanel(el, emoji, title, (d && d._note) || "");
      }
    }).catch(function () {
      emptyPanel(el, emoji, title + " — בקרוב", "הטאב הזה יחובר בשלב הבא של הבנייה.");
    });
  }

  boot();
})();
