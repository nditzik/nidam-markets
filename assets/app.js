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

  /* ---------- tabs ----------
     28.9.2026 (איציק): 12 → 9 טאבים. שלושה טאבים "מאוחדים" מכילים שני פאנלים קיימים כל אחד,
     עם לחצני-משנה (#subtabs) מעל הפאנל. הפאנלים, פונקציות הרינדור, ה-hash וה-GoatCounter
     נשארו ברמת הפאנל (candidates/morning/reports…) — קישורים ישנים והסטטיסטיקה ממשיכים לעבוד.
     לחיצה על טאב מאוחד פותחת את החלק האחרון שנבחר בו (או ברירת המחדל def); קישור #sub פותח את sub. */
  // np117 (10.10.2026, עיצוב מחדש שלב 6): 9 → 6 טאבים. ארבעה מאוחדים; הפאנלים/hash/GoatCounter
  // נשארו בשמות הישנים (indices, sectors, weekcal, prep, reports, picks, candidates, momentum, trades,
  // insider, briefing, morning, world) — הסטטיסטיקה רציפה. "movers" (הבולטות) חדש — ירד מהבית.
  var GROUPS = {
    market:   { subs: [["indices", "מדדים"], ["sectors", "סקטורים"]], def: "indices" },
    calendar: { subs: [["weekcal", "לוח הדיווחים"], ["prep", "לקראת הדוח"], ["reports", "ניתוח דוחות"]], def: "weekcal" },
    stocks:   { subs: [["picks", "הנבחרות"], ["candidates", "מועמדים"], ["momentum", "מומנטום"], ["trades", "הצעות לטרייד"], ["insider", "Insider"], ["movers", "הבולטות"]], def: "picks" },
    news:     { subs: [["briefing", "תדרוך"], ["morning", "Barchart"]], def: "briefing" }
  };
  var SUB2TOP = {}, LAST_SUB = {};
  Object.keys(GROUPS).forEach(function (g) { GROUPS[g].subs.forEach(function (s) { SUB2TOP[s[0]] = g; }); });
  function topOf(name) { return SUB2TOP[name] || name; }
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tab"));
  tabs.forEach(function (btn) {
    btn.addEventListener("click", function () { activate(btn.dataset.tab, true); });
  });
  function renderSubtabs(top, sub) {
    var bar = document.getElementById("subtabs");
    if (!bar) return;
    var g = GROUPS[top];
    if (!g) { bar.hidden = true; bar.innerHTML = ""; return; }
    bar.innerHTML = g.subs.map(function (s) {
      return '<button class="subtab' + (s[0] === sub ? " is-active" : "") + '" role="tab" data-sub="' + s[0] + '"' +
        (s[0] === sub ? ' aria-selected="true"' : "") + ">" + esc(s[1]) + "</button>";
    }).join("");
    bar.hidden = false;
    bar.querySelectorAll(".subtab").forEach(function (b) {
      b.addEventListener("click", function () { activate(b.dataset.sub); });
    });
  }
  // name = טאב עליון או פאנל-משנה. fromTab = לחיצה על הטאב העליון (פותח את החלק האחרון/ברירת המחדל);
  // בלי fromTab (קישור #, חיפוש, __goTab) — שם של פאנל-משנה פותח בדיוק אותו.
  function activate(name, fromTab) {
    var top = topOf(name), g = GROUPS[top];
    var sub = g ? ((fromTab || !SUB2TOP[name]) ? (LAST_SUB[top] || g.def) : name) : null;
    var panelName = sub || top;
    if (sub) LAST_SUB[top] = sub;
    tabs.forEach(function (b) { b.classList.toggle("is-active", b.dataset.tab === top); });
    document.querySelectorAll(".panel").forEach(function (p) {
      p.classList.toggle("is-active", p.id === "panel-" + panelName);
    });
    renderSubtabs(top, sub);
    markSeen(panelName);
    updateTodayBarVis();
    // דוח שנטען כשהפאנל היה מוסתר לא הותאם (המדידה נעצרת על clientWidth=0 וה-retries
    // מתפוגגים) — מריצים fit מחדש ברגע שהטאב נפתח והמידות אמיתיות
    requestAnimationFrame(function () {
      document.querySelectorAll("#panel-" + panelName + " iframe.trd-frame").forEach(function (f) {
        if (window.__fitFrame) window.__fitFrame(f);
      });
    });
    // np117: רצועת הציטוטים בכל הטאבים; מפת החום רק בבית
    var hw = document.getElementById("np-heat-wrap");
    if (hw) hw.style.display = panelName === "home" ? "block" : "none";
    if (location.hash.slice(1) !== panelName) {
      history.replaceState(null, "", "#" + panelName);
      // GoatCounter: ספירת מעבר-טאב כצפיית-עמוד (הכניסה הראשונית נספרת אוטומטית)
      if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: "/" + panelName });
    }
  }

  /* ---- live market ticker (our own strip, from data/market.json via Yahoo) ---- */
  function fmtQuote(v) {
    if (v == null || isNaN(v)) return "—";
    var d = Math.abs(v) < 10 ? 3 : 2;
    return Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: d });
  }
  var PIN_KEYS = { es: 1, nq: 1, usdils: 1 };   // בשורה הקבועה, לא ברצועה הנעה
  function renderMarketTicker(el, data) {
    if (!el || !data || !data.items || !data.items.length) return;
    // שתי שורות רזות: עליונה = המדדים (SPY→DXY מימין), תחתונה = חוזים + דולר/שקל
    function tick(it) {
      var c = it.chg, cls = c > 0 ? "up" : (c < 0 ? "down" : ""), arr = c > 0 ? "▲" : (c < 0 ? "▼" : "");
      return '<span class="np-tick"><b>' + esc(it.label) + "</b> " + (it.key === "vix" ? vlDot(data && data.vixLight) : "") +
        '<span class="v num">' + fmtQuote(it.price) + "</span>" +
        (c == null ? "" : ' <span class="c num ' + cls + '" dir="ltr">' + arr + (c > 0 ? "+" : "") + Number(c).toFixed(2) + "%</span>") +
        "</span>";
    }
    // np117: רצועת לוח — 8 תאים שווים (ספר הסגנון, רכיב Quotes). לפני הפתיחה החוזים ראשונים.
    var by = {}; data.items.forEach(function (it) { by[it.key] = it; });
    var ses = jsSession();
    var order = (ses === "regular" || ses === "post") ? ["spy", "qqq", "iwm", "vix", "tnx", "es", "nq", "usdils", "dxy"]
                                                     : ["es", "nq", "spy", "iwm", "vix", "tnx", "usdils", "dxy", "qqq"];
    var cells = order.map(function (k) { return by[k]; }).filter(Boolean).slice(0, 8);
    el.innerHTML = cells.map(function (it) {
      var c = it.chg, cls = c > 0 ? "up" : (c < 0 ? "down" : "");
      return '<div class="bd-q"><span class="l">' + esc(it.label) + (it.key === "vix" ? " " + vlDot(data && data.vixLight) : "") + "</span>" +
        '<span class="v"><span class="num p" dir="ltr">' + fmtQuote(it.price) + "</span>" +
        (c == null ? "" : '<span class="num c ' + cls + '" dir="ltr">' + (c > 0 ? "+" : c < 0 ? "−" : "") + Math.abs(Number(c)).toFixed(2) + "%</span>") + "</span></div>";
    }).join("");
  }
  var TICKD = null;
  function loadTicker() {
    var el = document.getElementById("ticker");
    if (!el) return;
    fetchJSON("data/market.json")
      .then(function (d) { TICKD = d; renderMarketTicker(el, d); refreshTickerLive(); if (INDD) { renderLead(); renderBreadthPeaks(); } })
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
        // 28.9.2026: גם SPY — נקודת "עכשיו" בגלגל הרוטציה (חוזק תוך-יומי של סקטור = השינוי שלו פחות השינוי של המדד)
        symbols: { tickers: SECTOR_ETFS.map(function (s) { return "AMEX:" + s[0]; }).concat(["AMEX:SPY"]) },
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
        if (typeof renderRotationWheel === "function" && document.getElementById("rw-svg")) renderRotationWheel();
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

  /* ===== np117 — פאנלי הבית של "לוח המסחר" (עיצוב מחדש שלב 6, ספר הסגנון docs/redesign/styleguide) =====
     כל פאנל = .pan עם .ph (כותרת + קישור אחד) ותוכן. מספרים ב-.num (מונו, LTR). כל גרפיקה LTR. */
  function bdPct(v, d) {
    if (v == null || isNaN(v)) return '<span class="num mute">—</span>';
    var n = Number(v), cls = n > 0 ? "up" : n < 0 ? "down" : "mute";
    return '<span class="num ' + cls + '" dir="ltr">' + (n > 0 ? "+" : n < 0 ? "−" : "") + Math.abs(n).toFixed(d == null ? 2 : d) + "%</span>";
  }
  function bdGo(name, label) { return '<a class="go" href="#' + name + '" onclick="__goTab(\'' + name + '\');return false">' + label + "</a>"; }
  function bdDM(iso) { var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || ""); return m ? (+m[3]) + "." + (+m[2]) : ""; }
  var BD_DOW = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"];

  /* ---- היומן בבית: ארבעה תאים (היום + 3 הבאים), תג לפי סוג האירוע (מאקרו ענבר / דוחות כחול).
     יום אירוע (מאקרו מתוזמן היום, או חברה עם "לקראת הדוח" שמדווחת היום) → הבלוק עולה לראש הבית
     (class "event" → CSS order) עם שתי עמודות: דוחות | מאקרו. ---- */
  function renderHomeCal() {
    var el = document.getElementById("home-cal");
    if (!el) return;
    var t = ilNowParts(), today = t.iso;
    var evs = ((ECON && ECON.events) || []).filter(function (e) { return String(e.date).slice(0, 10) >= today; });
    var byDay = {};
    evs.forEach(function (e) { var k = String(e.date).slice(0, 10); (byDay[k] = byDay[k] || { macro: [], earn: [], count: 0 }).macro.push(e); });
    var rep = (EARN && EARN.reporting) || [], up = (EARN && EARN.upcoming) || [];
    if (rep.length) { var d0 = byDay[today] = byDay[today] || { macro: [], earn: [], count: 0 }; d0.earn = rep.map(function (r) { return { t: r.ticker, w: r.when }; }); d0.count = EARN.todayCount || rep.length; }
    if (!up.length && EARNW) {
      var byD = {};
      Object.keys(EARNW).forEach(function (sym) { var k = EARNW[sym]; if (k > today && sym.indexOf("/") < 0) (byD[k] = byD[k] || []).push(sym); });
      up = Object.keys(byD).sort().slice(0, 5).map(function (k) { return { date: k, tickers: byD[k].slice(0, 8), count: byD[k].length }; });
    }
    up.forEach(function (u) { if (u.date > today) { var dd = byDay[u.date] = byDay[u.date] || { macro: [], earn: [], count: 0 }; dd.earn = (u.tickers || []).map(function (x) { return { t: x, w: "" }; }); dd.count = u.count || dd.earn.length; dd.dow = u.dow; } });
    // חברות עם "לקראת הדוח" (יש להן ניתוח באתר) — תג מודגש
    var prep = {}; ((PREPD && PREPD.items) || []).forEach(function (p) { if (p.date) (prep[p.date] = prep[p.date] || []).push(p); });
    Object.keys(prep).forEach(function (k) { if (k >= today) { var dp = byDay[k] = byDay[k] || { macro: [], earn: [], count: 0 }; dp.prep = prep[k]; } });
    var days = Object.keys(byDay).sort().filter(function (k) { return k >= today; }).slice(0, 4);
    if (!days.length) { el.innerHTML = '<div class="ph"><h2>היומן</h2>' + bdGo("weekcal", "היומן המלא") + '</div><div class="pb mute">אין אירועים מתוזמנים בשבוע הקרוב.</div>'; el.classList.remove("event"); return; }
    var isEvent = !!(byDay[today] && (byDay[today].macro.length || (byDay[today].prep || []).length));
    function dayLbl(k, cell) {
      var dt = new Date(k + "T12:00:00"), dow = k === today ? "היום" : (cell.dow ? cell.dow.replace("׳", "") : BD_DOW[dt.getDay()]);
      return (k === today ? "<b>" : "") + dow + ' · <span class="num" dir="ltr">' + bdDM(k) + "</span>" + (k === today ? "</b>" : "");
    }
    function macroLine(e, full) {
      var cls = e.surprise === "good" ? "up" : e.surprise === "bad" ? "down" : "";
      var val = e.actual != null
        ? 'בפועל <b class="num ' + cls + '" dir="ltr">' + esc(e.actual) + "</b>" + (e.forecast ? ' · צפי <span class="num" dir="ltr">' + esc(e.forecast) + "</span>" : "")
        : (e.forecast ? 'צפי <span class="num" dir="ltr">' + esc(e.forecast) + "</span>" : "") + (e.previous ? ' · קודם <span class="num" dir="ltr">' + esc(e.previous) + "</span>" : "");
      return '<div class="e"><span class="tag macro">מאקרו' + (e.ilTime ? ' <span class="num" dir="ltr">' + esc(e.ilTime) + "</span>" : "") + "</span> " + esc(e.he) + "</div>" +
        (val ? '<div class="mute s">' + val + "</div>" : "");
    }
    function earnLine(cell) {
      var list = (cell.earn || []).slice(), n = cell.count || list.length;
      (cell.prep || []).forEach(function (p) { if (!list.some(function (x) { return x.t === p.sym; })) { list.unshift({ t: p.sym, w: p.when || "" }); n++; } });
      if (!list.length) return "";
      var bef = list.filter(function (x) { return x.w === "before"; }).map(function (x) { return x.t; });
      var aft = list.filter(function (x) { return x.w === "after"; }).map(function (x) { return x.t; });
      var any = list.map(function (x) { return x.t; });
      var pset = {}; (cell.prep || []).forEach(function (p) { pset[p.sym] = 1; });
      var tk = function (arr) { return arr.slice(0, 6).map(function (s) { return '<b class="ltr' + (pset[s] ? " has-prep" : "") + '" dir="ltr">' + esc(s) + "</b>"; }).join(" · "); };
      var body = bef.length || aft.length
        ? (bef.length ? tk(bef) + " לפני הפתיחה" : "") + (bef.length && aft.length ? " · " : "") + (aft.length ? tk(aft) + " אחרי הסגירה" : "")
        : tk(any);
      return '<div class="e"><span class="tag earn">דוחות' + (n > 6 ? ' <span class="num" dir="ltr">' + n + "</span>" : "") + "</span> " + body + (n > 6 && any.length ? ' <span class="mute">ועוד</span>' : "") + "</div>";
    }
    if (isEvent) {
      // ---- יום אירוע: שתי עמודות דוחות | מאקרו, הבלוק עולה לראש ----
      var c0 = byDay[today], p0 = (c0.prep || [])[0], pn = p0 && PREPN && PREPN[p0.sym];
      var cons = p0 && p0.consensus, opt = p0 && p0.options;
      var prepCard = p0 ? '<div class="prep"><div class="h"><b class="num" dir="ltr">' + esc(p0.sym) + "</b><span>לקראת הדוח" +
          (cons && cons.eps != null ? ' · צפי רווח <span class="num" dir="ltr">$' + Number(cons.eps).toFixed(2) + "</span> למניה" : "") +
          (opt && opt.earn != null ? ' · האופציות מתמחרות <span class="num" dir="ltr">±' + Number(opt.earn).toFixed(1) + "%</span>" : "") + "</span></div>" +
          (pn && pn.thesis ? "<p>" + esc(pn.thesis) + "</p>" : "") +
          '<a href="#prep" onclick="__goTab(\'prep\');return false">ההכנה המלאה ל-' + esc(p0.sym) + "</a></div>" : "";
      var nextDays = days.slice(1, 3).map(function (k) { var c = byDay[k]; return '<div class="mute s">' + dayLbl(k, c) + ": " + (c.macro.length ? esc(c.macro[0].he) + (c.macro[0].ilTime ? ' <span class="num" dir="ltr">' + esc(c.macro[0].ilTime) + "</span>" : "") : "") + (c.macro.length && c.earn.length ? " · " : "") + (c.earn.length ? c.earn.slice(0, 4).map(function (x) { return x.t; }).join(", ") : "") + "</div>"; }).join("");
      el.innerHTML = '<div class="ph"><h2>היום · ' + BD_DOW[new Date(today + "T12:00:00").getDay()] + ' <span class="num" dir="ltr">' + bdDM(today) + "</span> · יום אירוע</h2>" +
          (c0.macro.length ? '<span class="tag macro">' + esc(c0.macro[0].he) + (c0.macro[0].ilTime ? ' <span class="num" dir="ltr">' + esc(c0.macro[0].ilTime) + "</span>" : "") + "</span>" : "") +
          ((c0.earn || []).length ? '<span class="tag earn">' + (c0.count || c0.earn.length) + " מדווחות</span>" : "") + bdGo("weekcal", "היומן המלא") + "</div>" +
        '<div class="ev"><div>' + (earnLine(c0) ? '<h3><span class="tag earn">דוחות</span>היום</h3>' + earnLine(c0).replace('<span class="tag earn">דוחות</span> ', "") : "") + prepCard + "</div>" +
        "<div>" + (c0.macro.length ? '<h3><span class="tag macro">מאקרו</span>' + (c0.macro[0].ilTime ? '<span class="num" dir="ltr">' + esc(c0.macro[0].ilTime) + "</span> · " : "") + "שעון ישראל</h3>" +
          '<div class="mrows"><div class="mrow mute"><span>נתון</span><span class="num">צפי</span><span class="num">קודם</span><span class="num">בפועל</span></div>' +
          c0.macro.slice(0, 5).map(function (e) { var cls = e.surprise === "good" ? "up" : e.surprise === "bad" ? "down" : ""; return '<div class="mrow"><span>' + esc(e.he) + '</span><span class="num" dir="ltr">' + esc(e.forecast || "—") + '</span><span class="num" dir="ltr">' + esc(e.previous || "—") + '</span><span class="num ' + cls + '" dir="ltr">' + esc(e.actual != null ? e.actual : "—") + "</span></div>"; }).join("") + "</div>" : "") +
          (nextDays ? '<div class="nx"><b>אחר כך השבוע</b>' + nextDays + "</div>" : "") + "</div></div>";
      el.classList.add("event");
      return;
    }
    el.innerHTML = '<div class="ph"><h2>היומן</h2><span class="mute">שעון ישראל</span>' + bdGo("weekcal", "היומן המלא") + "</div>" +
      '<div class="cal">' + days.map(function (k) {
        var c = byDay[k];
        var inner = c.macro.slice(0, 2).map(function (e) { return macroLine(e); }).join("") + earnLine(c);
        if (!inner) inner = '<div class="mute s">אין אירועים</div>';
        if (k === today && !c.macro.length) inner += '<div class="mute s">אין נתוני מאקרו מתוזמנים</div>';
        return '<div><span class="d">' + dayLbl(k, c) + "</span>" + inner + "</div>";
      }).join("") + "</div>";
    el.classList.remove("event");
  }

  /* ---- הנבחרות בבית: 5 הראשונות כטבלה (מחיר · יום · 60 יום · סטופ · מיקום · יעד · מקור · רקורד) + רצועת היומן ---- */
  function bdPickSpark(p) {
    var c = p.closes || []; if (c.length < 2) return "";
    var lo_ = p.stop || p.sup, hi_ = p.target || p.res, W = 100, H = 34, pad = 2;
    var vals = c.slice(); if (lo_) vals.push(lo_); if (hi_) vals.push(hi_);
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals), rng = (hi - lo) || 1;
    var Y = function (v) { return pad + (H - 2 * pad) * (1 - (v - lo) / rng); };
    var pts = c.map(function (v, i) { return (i * W / (c.length - 1)).toFixed(1) + "," + Y(v).toFixed(1); }).join(" ");
    var lines = "";
    if (lo_) lines += '<line class="lv lo" x1="0" x2="' + W + '" y1="' + Y(lo_).toFixed(1) + '" y2="' + Y(lo_).toFixed(1) + '" vector-effect="non-scaling-stroke"/>';
    if (hi_) lines += '<line class="lv hi" x1="0" x2="' + W + '" y1="' + Y(hi_).toFixed(1) + '" y2="' + Y(hi_).toFixed(1) + '" vector-effect="non-scaling-stroke"/>';
    return '<svg class="sp" viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="none" role="img" aria-label="' + esc(p.sym) + ': 60 ימי מסחר">' +
      '<polygon class="ar" points="0,' + H + " " + pts + " " + W + "," + H + '"/>' + lines + '<polyline class="ln" points="' + pts + '" vector-effect="non-scaling-stroke"/></svg>';
  }
  function renderHomePicks() {
    var el = document.getElementById("home-picks");
    if (!el) return;
    var d = PICKD;
    if (!d || !d.picks) { el.innerHTML = '<div class="ph"><h2>הנבחרות</h2>' + bdGo("picks", "הנבחרות") + '</div><div class="pb mute">המהדורה הראשונה נבנית אחרי הריצה הבאה של הבוט.</div>'; return; }
    var g = d.gate || {}, gw = g.combined != null ? meterWord(g.combined) : ["", ""];
    var gateCls = { defense: "bad", neutral: "warn", green: "good" }[g.state] || "";
    var rows = d.picks.slice(0, 5).map(pickRowHtml).join("");
    var eds = ((PICKL && PICKL.editions) || []).slice(-4), led = eds.map(function (e) {
      var a5 = e.avg && e.avg["5"], c = e.cur;
      var v = a5 ? a5.excess : (c ? c.excess : null), lbl = a5 ? "5 ימים" : (c ? "יום " + c.day : "נבנתה היום");
      return '<div><span class="mute">מהדורת <span class="num" dir="ltr">' + bdDM(e.date) + "</span> · " + lbl + "</span><span>" + bdPct(v) + (v != null ? ' <span class="mute">מול S&amp;P</span>' : "") + "</span></div>";
    }).join("");
    el.innerHTML = '<div class="ph"><h2>הנבחרות · אישור מחיר לקנייה · מהדורת <span class="num" dir="ltr">' + bdDM(d.date) + "</span></h2>" +
        (g.label ? '<span class="pill state ' + gateCls + '">השוק ' + esc(g.label) + (g.maxPos ? ' · עד <span class="num">' + esc(g.maxPos) + "</span> פוזיציות" : "") + (g.sizing ? " · " + esc(g.sizing) + " גודל" : "") + "</span>" : "") +
        bdGo("picks", "כל " + d.picks.length + " הנבחרות והיומן") + "</div>" +
      (d.picks.length ? '<div class="tbl"><table><caption class="sr-only">הנבחרות של מהדורת ' + esc(bdDM(d.date)) + '</caption><thead><tr><th scope="col">מניה</th><th scope="col">מחיר</th><th scope="col">יום</th><th scope="col">60 יום</th><th scope="col">סטופ / תמיכה</th><th scope="col">מיקום בטווח</th><th scope="col">יעד / התנגדות</th><th scope="col">מקור</th><th scope="col">רקורד</th></tr></thead><tbody>' + rows + "</tbody></table></div>"
        : '<div class="pb mute">אף מניה לא קיבלה היום אישור מחיר. זה קורה, ולא מחפשים תחליף.</div>') +
      (led ? '<div class="led">' + led + "</div>" : "");
  }

  /* ---- "מסביב": סקטורים (5 ימים מול S&P) | העולם | מה השווקים מהמרים ---- */
  function renderHomeAround() {
    var es = document.getElementById("home-sect"), ew = document.getElementById("home-world");
    if (es) {
      var rs = (INDD && INDD.rotation && INDD.rotation.sectorRs) || null;
      if (rs) {
        var arr = Object.keys(rs).map(function (k) { return { k: k, v: rs[k].rs5 }; }).filter(function (x) { return x.v != null; }).sort(function (a, b) { return b.v - a.v; });
        var show = arr.slice(0, 3).concat(arr.slice(-3));
        es.innerHTML = '<div class="ph"><h2>סקטורים · 5 ימים מול S&amp;P</h2>' + bdGo("sectors", "השוק") + '</div><div class="pb bd-dbs">' + show.map(function (x) {
          var w = Math.min(Math.abs(x.v) / 3 * 50, 50), pos = x.v > 0 ? "left:50%" : "left:calc(50% - " + w.toFixed(1) + "%)";
          return '<div class="db"><span>' + esc(SECTOR_HE[x.k] || x.k) + '</span><div class="t" role="img" aria-label="' + esc(SECTOR_HE[x.k] || x.k) + " " + x.v + '%"><i style="' + pos + ";width:" + w.toFixed(1) + "%;background:var(--" + (x.v > 0 ? "up" : "down") + ')"></i></div>' + bdPct(x.v) + "</div>";
        }).join("") + "</div>";
      } else es.innerHTML = '<div class="ph"><h2>סקטורים</h2>' + bdGo("sectors", "השוק") + "</div>";
    }
    if (ew) {
      var items = (WORLDD && WORLDD.items) || [], by = {}; items.forEach(function (i) { by[i.key] = i; });
      var keys = ["ta125", "dax", "ftse", "n225", "hsi", "ks11"].filter(function (k) { return by[k] && by[k].chg != null && by[k].state !== "stale"; });
      ew.innerHTML = '<div class="ph"><h2>העולם</h2>' + bdGo("world", "העולם") + "</div>" +
        (keys.length ? '<div class="pb bd-wrs">' + keys.map(function (k) { var i = by[k]; return '<div class="wr"><span><i class="stt' + (i.state === "live" ? " on" : "") + '"></i>' + esc(i.label) + (i.stateHe ? ' <span class="mute s">' + esc(i.stateHe) + "</span>" : "") + "</span>" + bdPct(i.chg) + "</div>"; }).join("") + "</div>" : '<div class="pb mute">טוען…</div>');
    }
  }
  function renderBets(d) {
    var el = document.getElementById("home-bets");
    if (!el) return;
    var rows = (d && d.rows) || [];
    if (!rows.length) { el.innerHTML = ""; return; }
    el.innerHTML = '<div class="ph"><h2>מה השווקים מהמרים</h2><span class="mute">Polymarket · Kalshi</span></div><div class="pb bd-bts">' + rows.slice(0, 4).map(function (r) {
      var lab = String(r.label || "").split(" · ")[0], sub = String(r.sub || "").replace("ההימור המוביל: ", "");
      return '<div class="bt"><div class="r"><span>' + esc(lab) + ": <b>" + esc(sub) + '</b></span><span class="num" dir="ltr">' + esc(r.pct) + "%" + (r.chg ? ' <small class="' + (r.chg > 0 ? "up" : "down") + '">' + (r.chg > 0 ? "+" : "−") + Math.abs(r.chg) + "</small>" : "") + "</span></div>" +
        '<div class="bar" role="img" aria-label="' + esc(r.pct) + '%"><i style="width:' + esc(r.pct) + '%"></i></div></div>';
    }).join("") + "</div>";
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
    ((INSD && INSD.reports) || []).forEach(function (r) { push("Insider", "insider", r.title + " " + (r.tickers || []).join(" ")); });
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
      var btn = document.querySelector('.tab[data-tab="' + topOf(tab) + '"]');
      var active = btn && btn.classList.contains("is-active") && (!SUB2TOP[tab] || LAST_SUB[topOf(tab)] === tab);
      if (btn && !btn.querySelector(".tab-badge") && !active) {
        var dot = document.createElement("span");
        dot.className = "tab-badge";
        btn.appendChild(dot);
      }
    }
  }
  function markSeen(tab) {
    if (SIGS[tab]) localStorage.setItem("cseen-" + tab, SIGS[tab]);
    var btn = document.querySelector('.tab[data-tab="' + topOf(tab) + '"]');
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
      var b = document.getElementById("tvm-chart");
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
  /* 29.9.2026: המודאל מציג שני מבטים — "ניתוח טכני" (המנוע שלנו, assets/ta_engine.js + ta_ui.js,
     על 500 נרות שהבוט שומר ב-data/bars) ו"גרף TradingView". ברירת המחדל: ניתוח כשיש נרות לסמל. */
  var TA_VER = "np129";
  window.__npVer = TA_VER;
  window.__jsSession = function () { return jsSession(); };
  function ensureTaUi(cb) {
    if (window.__taRender) { cb(); return; }
    var s = document.createElement("script");
    s.src = "assets/ta_ui.js?v=" + TA_VER; s.onload = function () { cb(); }; s.onerror = function () { cb(new Error("load")); };
    document.head.appendChild(s);
  }
  function mountTvWidget(sym) {
    ensureTvLib(function () {
      var box = document.getElementById("tvm-chart");
      if (!box || box.dataset.ready) return; // המודאל נסגר בזמן הטעינה / כבר נבנה
      box.dataset.ready = "1";
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
  function showChartView(sym, view) {
    var wrap = document.getElementById("tvm-wrap");
    if (!wrap) return;
    wrap.querySelectorAll(".tvm-tab").forEach(function (b) { b.classList.toggle("is-on", b.dataset.view === view); });
    var ta = wrap.querySelector("#tvm-ta"), tv = wrap.querySelector("#tvm-chart"), note = wrap.querySelector(".tvm-note");
    ta.hidden = view !== "ta"; tv.hidden = view !== "tv"; if (note) note.hidden = view !== "tv";
    if (view === "tv") mountTvWidget(sym);
    else if (!ta.dataset.ready) {
      ta.dataset.ready = "1";
      ensureTaUi(function (err) {
        var box = document.getElementById("tvm-ta");
        if (!box) return;
        if (err || !window.__taRender) { box.innerHTML = '<div class="ta-msg">טעינת הניתוח נכשלה</div>'; return; }
        window.__taRender(sym, box);
      });
    }
  }
  function openChart(sym) {
    closeChart();
    var wrap = document.createElement("div");
    wrap.id = "tvm-wrap";
    wrap.innerHTML =
      '<div class="tvm-box" role="dialog" aria-modal="true" aria-label="גרף ' + esc(sym) + '">' +
        '<div class="tvm-head">' +
          '<b class="tvm-sym" dir="ltr">' + esc(sym) + "</b>" +
          '<div class="tvm-tabs" role="tablist"><button type="button" class="tvm-tab" data-view="ta">ניתוח טכני</button><button type="button" class="tvm-tab" data-view="tv">גרף TradingView</button></div>' +
          '<span class="tvm-note" hidden>ממוצעים <b style="color:#43a047">20</b> · <b style="color:#1e88e5">50</b> · <b style="color:#e53935">200</b> + ווליום</span>' +
          '<a class="tvm-full" href="https://www.tradingview.com/symbols/' + encodeURIComponent(sym) +
            '/" target="_blank" rel="noopener">פתיחה ב-TradingView</a>' +
          '<button class="tvm-x" type="button" aria-label="סגירה">✕</button>' +
        "</div>" +
        '<div class="tvm-body"><div id="tvm-ta" class="tvm-ta" hidden></div><div id="tvm-chart" hidden><div class="tvm-load">טוען גרף…</div></div></div>' +
      "</div>";
    document.body.appendChild(wrap);
    document.body.style.overflow = "hidden";
    wrap.addEventListener("click", function (e) { if (e.target === wrap) closeChart(); });
    wrap.querySelector(".tvm-x").addEventListener("click", closeChart);
    wrap.querySelectorAll(".tvm-tab").forEach(function (b) { b.addEventListener("click", function () { showChartView(sym, b.dataset.view); }); });
    document.addEventListener("keydown", escChart);
    // ברירת מחדל: ניתוח טכני כשיש נרות שמורים לסמל, אחרת גרף TradingView
    var decided = false;
    function decide(has) { if (decided || !document.getElementById("tvm-wrap")) return; decided = true; showChartView(sym, has ? "ta" : "tv"); }
    ensureTaUi(function (err) { if (err || !window.__taHas) { decide(false); return; } window.__taHas(sym, decide); });
    setTimeout(function () { decide(false); }, 4000);
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
  function candTradeDay(d) {
    // על איזו סגירה מבוססת רשימת המועמדים (1.10.2026): ריצת הבוקר נושאת את תאריך היום על
    // סגירת אתמול, אבל ריצת הערב (23:41) נושאת אותו תאריך על סגירת היום עצמו — "תקפים ל-29.9"
    // הוצג על רשימה שמחיריה הם סגירות 30.9. נגזר משעת הריצה בשעון ניו יורק: אחרי 16:00 ביום
    // מסחר = אותו יום, אחרת יום המסחר הקודם.
    if (d && d._meta && d._meta.basedOn) return d._meta.basedOn;   // הסריקה בענן כותבת את יום הסגירה במפורש
    var m = /^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})/.exec((d && d._meta && d._meta.updatedAt) || "");
    if (!m) return prevTradingDate(d && d.date);
    var wall = Date.UTC(+m[3], +m[2] - 1, +m[1], +m[4], +m[5]);
    var parts = function (t, tz) {
      var o = {};
      new Intl.DateTimeFormat("en-GB", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false, weekday: "short" })
        .formatToParts(new Date(t)).forEach(function (x) { o[x.type] = x.value; });
      return o;
    };
    var il = parts(wall, "Asia/Jerusalem");   // היסט ישראל ברגע הזה (DST)
    var t = wall - (Date.UTC(+il.year, +il.month - 1, +il.day, +il.hour % 24, +il.minute) - wall);
    var ny = parts(t, "America/New_York"), day = ny.year + "-" + ny.month + "-" + ny.day;
    var after = (+ny.hour % 24) * 60 + (+ny.minute) >= 16 * 60 && ny.weekday !== "Sat" && ny.weekday !== "Sun";
    return after ? day : prevTradingDate(day);
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
    morning: "שתי מהדורות Barchart שאיציק מקבל: דוח יומי ב-06:00 (סיכום המסחר האחרון וההקשר שמסביבו), ועדכון טרום-מסחר ב-14:00 (חוזי המדדים, מוקדי השוק ותנועות בולטות לפני הפתיחה).",
    insider: "כשמנכ\"ל, סמנכ\"ל כספים או דירקטור קונים את המניה של החברה שלהם בכסף פרטי, זה אחד האיתותים הנקיים בשוק: למכור יש הרבה סיבות, לקנות יש רק אחת. הדוח סורק את כל קניות בעלי העניין בארה\"ב, מסנן את המשמעותיות ובודק כל מועמדת מול ההיסטוריה של אותם קונים ומול הגרף. זה מידע להתרשמות, לא המלצה.",
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

  // 26.9.2026: המסלול בתוך השבוע — "שפל 49" כשהשפל נמוך משתי הקצוות (או "שיא" כשגבוה משתיהן)
  function meterLowHi(s) {
    var a = s.combStart, b = s.combEnd, lo = s.combLow, hi = s.combHigh, out = "";
    if (lo != null && a != null && b != null && lo < Math.min(a, b)) out += ' · שפל <span class="num">' + lo + "</span>";
    if (hi != null && a != null && b != null && hi > Math.max(a, b)) out += ' · שיא <span class="num">' + hi + "</span>";
    return out;
  }
  function meterWord(v) { return v >= 66 ? ["חיובי", "var(--up)"] : v >= 45 ? ["זהיר", "var(--warn)"] : ["הגנתי", "var(--down)"]; }



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
    FLASHD = d || FLASHD;
    renderNewsSiblings();
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
    var moreLbl = PULSE_X_ALL ? "פחות" : "כל " + items.length + " הבזקים";
    el.innerHTML =
      '<div class="ph"><h2>בזק מהרשת</h2>' +
        (items.length > 4 ? '<a class="go" href="#" id="pulse-more">' + moreLbl + "</a>" : "") + "</div>" +
      '<div class="bd-list">' + shown.map(function (it) {
        // dir="auto": הפריטים מעורבים — עברית מהדיג'סט ואנגלית מהטלגרם —
        // והדפדפן קובע כיוון לכל פריט לפי התו החזק הראשון שבו (6.9.2026)
        return '<a class="fl" href="' + esc(it.link) + '" target="_blank" rel="noopener">' +
          '<span class="num mute" dir="ltr">' + esc(it.time) + '</span><span class="mute src" dir="ltr">' + esc(it.source) + "</span>" +
          '<span class="tx" dir="auto">' + esc(it.text) + "</span></a>";
      }).join("") + "</div>" +
      '<a class="np-more" href="#" id="news-toggle" hidden>📰 חדשות השוק ⌄</a>';
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
  /* 2.10.2026 (איציק): הכרטיס ירד מהבית — "הנבחרות" עונה על אותו צורך. אין #home-focus ב-index.html,
     ולכן renderFocus יוצא מיד; archive_focus.py ו-focus_history.json נשארים כמו שהם. */
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
    // np120: טבלה אחת בפאנל "מאקרו · צפי מול בפועל" בטאב היומן — הבאים בתור ואז מה שפורסם
    var released = ECON.events.filter(function (e) { return e.actual != null; }).slice(-6).reverse();
    var upcoming = ECON.events.filter(function (e) { return e.actual == null; }).slice(0, 8);
    function row(e) {
      var cls = e.surprise === "good" ? "up" : e.surprise === "bad" ? "down" : "";
      return "<tr><td class=\"num\" dir=\"ltr\">" + esc(e.ilDate) + (e.ilTime ? " · " + esc(e.ilTime) : "") + "</td><td>" + esc(e.he) + (e.period ? ' <span class="mute s">' + esc(e.period) + "</span>" : "") + "</td>" +
        '<td class="num" dir="ltr">' + esc(e.forecast || "—") + '</td><td class="num mute" dir="ltr">' + esc(e.previous || "—") + '</td><td class="num ' + cls + '" dir="ltr">' +
        (e.actual != null ? "<b>" + esc(e.actual) + "</b>" + (e.surprise === "good" ? " ✓" : e.surprise === "bad" ? " ✗" : "") : '<span class="mute">—</span>') + "</td></tr>";
    }
    el.className = "pan";
    el.innerHTML = panHd("מאקרו · צפי מול בפועל", '<span class="mute">מתעדכן אוטומטית עם הפרסום · שעון ישראל</span>') +
      '<div class="tbl"><table class="bd-tbl"><thead><tr><th>מועד</th><th>נתון</th><th>צפי</th><th>קודם</th><th>בפועל</th></tr></thead><tbody>' +
      (upcoming.length ? '<tr class="sec"><td colspan="5">🗓️ הבאים בתור</td></tr>' + upcoming.map(row).join("") : "") +
      (released.length ? '<tr class="sec"><td colspan="5">🔔 פורסמו לאחרונה</td></tr>' + released.map(row).join("") : "") +
      (!upcoming.length && !released.length ? '<tr><td colspan="5" class="mute">אין אירועים</td></tr>' : "") + "</tbody></table></div>";
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
  function renderSpark(sfx) {
    sfx = sfx || "";
    var svg = document.getElementById("meter-spark" + sfx);
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
    var lbl = document.getElementById("spark-label" + sfx);
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
      '<div class="ph"><h2>התדרוך · ' + esc(label) + ' <span class="num" dir="ltr">' + asOf + "</span></h2>" +
        (sent.text ? '<span class="pill state">' + esc(sent.text.replace(/^סנטימנט:\s*/, "")) + "</span>" : "") +
        '<a class="go" href="#briefing" onclick="__goTab(\'briefing\');return false">התדרוך המלא</a></div>' +
      '<div class="bd-list">' + news.map(function (t, i) { return '<div class="li"><span class="num mute">' + (i + 1) + "</span><span>" + esc(t) + "</span></div>"; }).join("") + "</div>" +
      (sched.length ? '<div class="led bd-sched">' + sched.slice(0, 3).map(function (x) {
          return x.day ? "" : '<div><span class="num mute" dir="ltr">' + esc(x.time) + "</span><span>" + esc(x.text) + "</span></div>";
        }).join("") + "</div>" : "");
  }

  /* ---------- כותרת סוף-השבוע: סיכום שבועי בבית (שבת → ראשון 15:00) ---------- */
  function ilNowParts() {
    // שעון ישראל בלי תלות באזור הזמן של הדפדפן
    var f = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Jerusalem", weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
    var o = {}; f.forEach(function (p) { o[p.type] = p.value; });
    return { dow: o.weekday, hour: parseInt(o.hour, 10) % 24, iso: o.year + "-" + o.month + "-" + o.day };
  }
  // הצד שהחזיק מעמד / שאליו נכנס הכסף (19.9.2026) + הסבר מפורש מה האחוז אומר
  function heldHtml(sc) {
    if (!sc || !sc.held || !sc.held.length) return "";
    return ' · <b>' + (sc.heldIn ? "לכאן נכנס:" : "החזיקו מעמד:") + "</b> " + sc.held.map(function (o) {
      var isBest = sc.best && sc.best.name === o.name;
      var v = o.from != null ? "<bdi>" + o.from + "%</bdi> ← <bdi>" + o.to + "%</bdi>" : "<bdi>" + o.to + "%</bdi>" + (o.stable ? " יציב" : "");
      return esc(o.name) + ' <span class="num ' + (o.from != null && o.to > o.from ? "up" : "") + '">' + v + "</span>" +
        (isBest ? ' <span class="soft">(הסקטור הטוב של השבוע, <bdi>' + (sc.best.pct > 0 ? "+" : "") + sc.best.pct + "%</bdi>)</span>" : "");
    }).join(" · ");
  }
  /* ---------- עיצוב הכותרת 20.9.2026 (איציק: "פחות מילים יותר נתונים") ----------
     שלד אחד לסוף שבוע וליום חול: קיקר · כותרת · 3 נתונים · טקסט קצר · אריחים · נוריות.
     "השבוע הבא"/"היום ביומן" עברו לרייל, מתחת למד (leadAgendaHtml). */
  function leadStats(arr) {
    arr = arr.filter(Boolean);
    if (!arr.length) return "";
    return '<div class="np-stats">' + arr.map(function (x) {
      return '<div class="np-stat"><div class="l">' + x.l + '</div><div class="v num ' + (x.cls || "") + '" dir="ltr">' + x.v +
        '</div><div class="s">' + (x.s || "") + "</div></div>";
    }).join("") + "</div>";
  }
  // שורת נתונים לכותרות העדכון (לקראת שבוע / לקראת פתיחה / אמצע יום) — מהטיקר החי (TICKD)
  function marketStats(keys) {
    var by = {};
    ((TICKD && TICKD.items) || []).forEach(function (it) { by[it.key] = it; });
    var L = { es: "חוזה S&amp;P 500", nq: "חוזה נאסד\"ק", vix: "VIX · מדד הפחד", tnx: "תשואת אג\"ח 10 שנים", spy: "S&amp;P 500 (SPY)" };
    return leadStats(keys.map(function (k) {
      var it = by[k];
      if (!it || it.price == null) return null;
      var chg = it.chg == null ? "" : (it.chg > 0 ? "+" : "") + Number(it.chg).toFixed(2) + "%";
      var cls = it.chg > 0 ? "up" : it.chg < 0 ? "down" : "";
      var px = Number(it.price).toLocaleString("en-US", { maximumFractionDigits: 2 });
      if (k === "vix") return { l: L[k], v: Number(it.price).toFixed(2), cls: it.price >= 20 ? "down" : "", s: '<span class="num" dir="ltr">' + chg + "</span>" };
      if (k === "tnx") return { l: L[k], v: Number(it.price).toFixed(2) + "%", s: Math.abs(it.price - 5) < 0.03 ? "סביב רף ה-5%" : it.price > 5 ? "מעל רף ה-5%" : "מתחת לרף ה-5%" };
      return { l: L[k] || esc(it.label), v: chg || px, cls: cls, s: '<span class="num" dir="ltr">' + px + "</span>" };
    }));
  }
  /* הצפי השבועי (20.9.2026): eventUpdate.forecast שהרוטינה של יום ראשון כותבת מתוך חבילת הראיות
     (data/week_ahead.json). המאזן המצטבר מגיע מ-data/forecasts.json (scripts/score_forecast.py). */
  var FCAST = null;

  /* מעקב הצפי השבועי (24.9.2026, איציק): שלוש טענות — הסגירה מול הקו (הנמדדת), יום מכירה
     רחבה, רוחב — כל אחת ○ פתוח / ✓ / ✗. בבית: שורה אחת בתחתית הכותרת (במקום המכוונים שירדו
     ב-20.9, בלי שינוי גובה). בטאב מדדים: הפס עם נקודה לכל סגירה. שבת–ראשון: התוצאה. */
  var DOW_HE = ["א׳", "ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳"];
  function isoAdd(iso, n) { var d = new Date(iso + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
  function mondayOf(iso) { var wd = new Date(iso + "T00:00:00Z").getUTCDay(); return isoAdd(iso, -(wd === 0 ? 6 : wd - 1)); }
  function fcWeek() {
    if (!FCAST || !(FCAST.items || []).length || !HIST) return null;
    var t = ilNowParts(), mon = mondayOf(t.iso), fri = isoAdd(mon, 4);
    var f = null, fnext = null, monNext = isoAdd(mon, 7);
    (FCAST.items || []).forEach(function (x) { if (x.weekOf === mon) f = x; if (x.weekOf === monNext) fnext = x; });
    // 27.9.2026: מראשון 15:00, כשהצפי לשבוע הבא כבר נכתב והשבוע הנוכחי כבר צוין — עוברים לשבוע הבא
    // (כמו הכותרת). עד אז (שבת–ראשון בבוקר) מוצגת התוצאה של השבוע שנגמר.
    var isNext = false;
    if ((!f || f.result) && fnext) { f = fnext; mon = monNext; fri = isoAdd(mon, 4); isNext = true; }
    if (!f || f.ref == null) return null;
    var closes = (HIST.days || []).filter(function (d) { return d.date >= mon && d.date <= fri && d.spx != null; });
    var lastDate = closes.length ? closes[closes.length - 1].date : "";
    // הסגירה של היום כבר ב-indices אבל עוד לא ב-history → משלימים
    if (INDD && INDD.date > lastDate && INDD.date >= mon && INDD.date <= fri && INDD.evidence && INDD.evidence.spxPrice) {
      closes.push({ date: INDD.date, spx: INDD.evidence.spxPrice }); lastDate = INDD.date;
    }
    var r = f.result || null;
    var pct = closes.length ? (closes[closes.length - 1].spx / f.ref - 1) * 100 : null;
    var below = f.test !== "above";
    var price = r ? { st: r.hit ? "hit" : "miss", pct: r.actual }
                  : { st: "open", pct: pct };
    var claims = [];
    (f.claims || []).forEach(function (c) {
      var rc = r && r.claims && r.claims[c.key];
      if (c.key === "sellDay") {
        var days = r ? (rc && rc.days) || [] : ((INDD && INDD.riskOff && INDD.riskOff.sellingDays) || []).filter(function (d) { return d.date >= mon && d.date <= fri; });
        var st = r ? (rc && rc.hit ? "hit" : "miss") : (days.length ? "hit" : "open");
        claims.push({ key: c.key, text: c.text, prob: c.prob, st: st,
          val: days.length ? days.map(function (d) { return DOW_HE[new Date(d.date + "T00:00:00Z").getUTCDay()] + (d.chg != null ? ' <span class="num" dir="ltr">' + d.chg.toFixed(2) + "%</span>" : ""); }).join(", ") : (r ? "לא היה" : "עוד לא") });
      } else if (c.metric) {
        // 28.9.2026: vixOverMa50 = אחוז ה-VIX מעל הממוצע ל-50 יום, חי מ-market.json.vixLight (רמזור ה-VIX)
        var v = r ? (rc ? rc.value : null)
              : c.metric === "vixOverMa50" ? ((TICKD && TICKD.vixLight && TICKD.vixLight.ratio) ? (TICKD.vixLight.ratio - 1) * 100 : null)
              : ((INDD && INDD.evidence && INDD.evidence[c.metric] != null) ? INDD.evidence[c.metric] : (c.metric === "pctMa50" && WEEKLY && WEEKLY.sectors ? WEEKLY.sectors.marketBreadth : null));
        if (v == null) return;
        var ok = r ? (rc && rc.hit) : (c.op === ">" ? v > c.value : c.op === ">=" ? v >= c.value : c.op === "<=" ? v <= c.value : v < c.value);
        claims.push({ key: c.key, text: c.text, st: ok ? "hit" : (r ? "miss" : "risk"), val: '<span class="num" dir="ltr">' + Math.round(v) + "%</span>" + (r ? "" : " כרגע") });
      }
    });
    var hits = (price.st === "hit" ? 1 : 0) + claims.filter(function (c) { return c.st === "hit"; }).length;
    var total = 1 + claims.length;
    var m = mon.split("-"), fr = fri.split("-");
    var label = (m[1] === fr[1]) ? (+m[2]) + "–" + (+fr[2]) + "." + (+fr[1]) : (+m[2]) + "." + (+m[1]) + "–" + (+fr[2]) + "." + (+fr[1]);
    return { f: f, r: r, mon: mon, fri: fri, label: label, closes: closes, n: closes.length,
             price: price, below: below, claims: claims, hits: hits, total: total, weekend: (t.dow === "Sat" || t.dow === "Sun") && !isNext };
  }
  function fcSym(st) { return st === "hit" ? "✓" : st === "miss" ? "✗" : "○"; }
  function fcPct(v, signed) { return v == null ? "—" : '<span class="num" dir="ltr">' + (signed && v > 0 ? "+" : "") + v.toFixed(1) + "%</span>"; }
  function fcPriceText(w, long) {
    var p = w.price;
    if (p.st !== "open") return (long ? "השבוע " : "") + fcPct(p.pct, true);
    if (p.pct == null) return "ממתין לסגירה ראשונה";
    var above = p.pct >= 0, need = w.below ? -p.pct : -p.pct;
    return fcPct(Math.abs(p.pct), false) + (above ? " מעל הקו" : " מתחת לקו") +
      (long ? ((w.below === above) ? " · צריך " + fcPct(Math.abs(need), false) + (w.below ? " ירידה" : " עלייה") + " עד שישי" : " · בכיוון הצפי") : "");
  }
  // שורת התחתית בבית
  function fcTrackLine() {
    var w = fcWeek();
    if (!w) return "";
    var link = '<a href="#indices" onclick="__goTab(\'indices\');var m=document.getElementById(\'fc-track\');if(m)setTimeout(function(){m.scrollIntoView({behavior:\'smooth\',block:\'start\'})},50);return false">מעקב ←</a>';
    if (w.r) {
      // 26.9.2026 (איציק): שלושת הסימנים במפורש, בלי ספירה מסכמת — הטענה הנמדדת ראשונה
      var res = ['<span class="np-fc-i st-' + w.price.st + '">' + fcSym(w.price.st) + " סגירה " + (w.below ? "מתחת ל-" : "מעל ") +
        '<span class="num" dir="ltr">' + Number(w.f.ref).toLocaleString("en-US", { maximumFractionDigits: 1 }) + "</span> · S&amp;P " + fcPct(w.price.pct, true) + "</span>"];
      w.claims.forEach(function (c) {
        res.push('<span class="np-fc-i st-' + c.st + '">' + fcSym(c.st) + " " + (c.key === "sellDay" ? "יום מכירה" : "רוחב") + " · " + c.val + "</span>");
      });
      return '<span class="np-fc"><span class="np-fc-k">🎯 הצפי לשבוע ' + esc(w.label) + "</span>" + res.join("") + link + "</span>";
    }
    var items = ['<span class="np-fc-i st-' + w.price.st + '">' + fcSym(w.price.st) + " סגירה " + (w.below ? "מתחת ל-" : "מעל ") + '<span class="num" dir="ltr">' + Number(w.f.ref).toLocaleString("en-US", { maximumFractionDigits: 1 }) + "</span> · " + fcPriceText(w, false) + "</span>"];
    w.claims.forEach(function (c) {
      items.push('<span class="np-fc-i st-' + c.st + '">' + fcSym(c.st) + " " + (c.key === "sellDay" ? "יום מכירה" : "רוחב") + " · " + c.val + "</span>");
    });
    return '<span class="np-fc"><span class="np-fc-k">🎯 הצפי · יום ' + '<span class="num" dir="ltr">' + w.n + "/5</span></span>" + items.join("") + link + "</span>";
  }
  // הבלוק בטאב מדדים
  function fcTrackHtml() {
    var w = fcWeek();
    if (!w) return "";
    var f = w.f, X = function (v) { return Math.max(0, Math.min(100, (v + 3) / 6 * 100)); };
    var lo = f.rangeLow, hi = f.rangeHigh, dirCls = f.direction === "up" ? "up" : f.direction === "down" ? "down" : "warn";
    var bar = '<div class="fc-bar fc-bar-track" dir="ltr"><i class="fc-zero"></i>' +
      ((lo != null && hi != null && hi > lo) ? '<i class="fc-rng ' + dirCls + '" style="left:' + X(lo) + "%;width:" + (X(hi) - X(lo)) + '%"></i>' +
        '<span class="fc-t" style="left:' + X(lo) + '%">' + (lo > 0 ? "+" : "") + lo + '%</span><span class="fc-t" style="left:' + X(hi) + '%">' + (hi > 0 ? "+" : "") + hi + "%</span>" : "") +
      '<span class="fc-t fc-ref" style="left:50%">' + Number(f.ref).toLocaleString("en-US", { maximumFractionDigits: 1 }) + "</span>" +
      w.closes.map(function (c, i) {
        var pct = (c.spx / f.ref - 1) * 100, last = i === w.closes.length - 1;
        return '<i class="fc-pt' + (last ? " now" : "") + '" style="left:' + X(pct) + '%" title="' + esc(fmtTradeDate(c.date)) + " · " + (pct > 0 ? "+" : "") + pct.toFixed(2) + '%"></i>' +
          (last ? '<span class="fc-t now" style="left:' + X(pct) + '%">' + (pct > 0 ? "+" : "") + pct.toFixed(1) + "%</span>" : "");
      }).join("") + "</div>";
    var dots = [0, 1, 2, 3, 4].map(function (i) { return i < w.n ? "●" : "○"; }).join(" ");
    function row(st, text, val) { return '<div class="fc-claim st-' + st + '"><span class="st">' + fcSym(st) + '</span><span class="tx">' + text + '</span><span class="val">' + val + "</span></div>"; }
    var rows = row(w.price.st, esc(f.claim || "") + (f.prob ? ' <small>(' + f.prob + "%)</small>" : ""), fcPriceText(w, true)) + bar;
    w.claims.forEach(function (c) { rows += row(c.st, esc(c.text) + (c.prob ? ' <small>(~' + c.prob + "%)</small>" : ""), c.val); });
    var rec = w.r
      ? '<p class="fc-rec">התוצאה: <b>' + w.hits + " מתוך " + w.total + '</b> · S&amp;P בשבוע ' + fcPct(w.price.pct, true) + (w.r.inRange ? " · בתוך הטווח" : " · מחוץ לטווח") + "</p>"
      : '<p class="fc-rec">' + (w.weekend ? "השבוע נסגר — הציון ייכתב עם קליטת סגירת שישי." : "○ פתוח עד סגירת יום שישי · ✓/✗ נקבעים אוטומטית בשבת.") +
        (FCAST.record && FCAST.record.scored ? " המאזן עד כה: " + FCAST.record.hits + " מתוך " + FCAST.record.scored + " שבועות." : "") + "</p>";
    return '<section class="fc-track" id="fc-track"><div class="fc-head"><span class="np-k">🎯 מעקב הצפי השבועי</span>' +
      '<b class="num" dir="ltr">' + esc(w.label) + '</b><span class="fc-days" title="ימי מסחר שנסגרו">' + dots + "</span></div>" +
      '<p class="fc-sum" style="margin-bottom:8px">' + esc(f.label || "") + (f.headline ? " — " + esc(f.headline) : "") + "</p>" + rows + rec + "</section>";
  }

  function forecastHtml(f) {
    if (!f || !f.label) return "";
    function li(arr) { return (arr || []).map(function (x) { return "<li>" + esc(x) + "</li>"; }).join(""); }
    var dirCls = f.direction === "up" ? "up" : f.direction === "down" ? "down" : "warn";
    var lo = f.rangeLow, hi = f.rangeHigh, bar = "";
    if (lo != null && hi != null && hi > lo) {
      // סרגל -3%…+3%: הטווח הצפוי כפס, האפס כקו
      var X = function (v) { return Math.max(0, Math.min(100, (v + 3) / 6 * 100)); };
      bar = '<div class="fc-bar" dir="ltr"><i class="fc-zero"></i><i class="fc-rng ' + dirCls + '" style="left:' + X(lo) + "%;width:" + (X(hi) - X(lo)) + '%"></i>' +
        '<span class="fc-t" style="left:' + X(lo) + '%">' + (lo > 0 ? "+" : "") + lo + '%</span><span class="fc-t" style="left:' + X(hi) + '%">' + (hi > 0 ? "+" : "") + hi + "%</span></div>";
    }
    var rec;
    if (FCAST && FCAST.record && FCAST.record.scored) {
      rec = '<p class="fc-rec">המאזן עד כה: צדקנו ב-<b class="num">' + FCAST.record.hits + '</b> מתוך <b class="num">' + FCAST.record.scored + "</b> שבועות" +
        (FCAST.last ? " · שבוע שעבר: " + (FCAST.last.hit ? "✓ פגענו" : "✗ החטאנו") + ' (<span class="num" dir="ltr">' + (FCAST.last.actual > 0 ? "+" : "") + FCAST.last.actual + "%</span>)" : "") + "</p>";
    } else rec = '<p class="fc-rec">זה הצפי הראשון. בשבת נבדוק אותו מול מה שקרה ונציג כאן מאזן מצטבר.</p>';
    return '<section class="fc"><div class="fc-head"><span class="np-k">🎯 הצפי שלנו לשבוע</span>' +
        '<b class="fc-lbl ' + dirCls + '">' + esc(f.label) + "</b></div>" +
      '<div class="fc-main"><div class="fc-prob"><b class="num ' + dirCls + '">' + esc(String(f.prob)) + "%</b><span>" + esc(f.claim || "") + "</span></div>" +
        (bar ? '<div class="fc-range"><span class="fc-cap">טווח סביר לשבוע (S&amp;P 500)</span>' + bar + "</div>" : "") + "</div>" +
      (f.summary ? '<p class="fc-sum">' + esc(f.summary) + "</p>" : "") +
      // 20.9.2026 (איציק): הנימוקים סגורים כברירת מחדל — מי שרוצה מרחיב
      '<details class="fc-more"><summary><span class="fc-open">הנימוקים המלאים: מה מושך למטה, מה מושך למעלה ומה יכריע</span><span class="fc-close">סגור את הנימוקים</span></summary>' +
      '<div class="fc-cols"><div><h4 class="down">מה מושך למטה</h4><ul>' + li(f.bear) + '</ul></div><div><h4 class="up">מה מושך למעלה</h4><ul>' + li(f.bull) + "</ul></div></div>" +
      (f.pivot ? '<p class="fc-piv"><b>האירוע שיכריע:</b> ' + esc(f.pivot) + "</p>" : "") +
      (f.invalidation ? '<p class="fc-piv"><b>מה יפריך את הצפי:</b> ' + esc(f.invalidation) + "</p>" : "") +
      rec + '<p class="fc-disc">הערכה הסתברותית על סמך נתונים היסטוריים ומצב השוק, לא המלצה ולא הבטחה.</p></details></section>';
  }
  function firstSentence(t) {
    var f = String(t || "").split(/(?<=[^\d])\.\s/)[0];
    return f ? f.replace(/\.$/, "") + "." : "";
  }
  function weekendNow() { var t = ilNowParts(); return t.dow === "Sat" || t.dow === "Sun"; }
  // אריחי הסקטורים: פס אפור = לפני שבוע, פס צבעוני = עכשיו
  function sectorTilesHtml(sec) {
    if (!sec || !sec.out || !sec.out.length) return "";
    function tile(o, cls, tag) {
      var val = o.from != null ? "<bdi>" + o.from + "%</bdi> ← <bdi>" + o.to + "%</bdi>" : "<bdi>" + o.to + "%</bdi>" + (o.stable ? " <small>יציב</small>" : "");
      return '<div class="np-tile ' + cls + '"><div class="n">' + esc(o.name) + (tag ? ' <span class="np-tag">' + tag + "</span>" : "") + "</div>" +
        '<div class="p num">' + val + "</div>" +
        '<div class="np-track">' + (o.from != null ? '<i class="was" style="width:' + o.from + '%"></i>' : "") + '<i class="now" style="width:' + o.to + '%"></i></div></div>';
    }
    var held = (sec.held || []).map(function (o) {
      var best = sec.best && sec.best.name === o.name;
      return tile(o, "in", best ? "★" : "");
    }).join("");
    return '<div class="np-sech"><b>💸 לאן זרם הכסף</b><span>' + SEC_EXPLAIN + "</span>" +
        '<a href="#sectors" onclick="__goTab(\'sectors\');return false">הדוח המלא ←</a></div>' +
      '<div class="np-flow' + (held ? "" : " one") + '"><div><div class="np-grp down">מכאן יצא</div><div class="np-tiles">' +
        sec.out.map(function (o) { return tile(o, "out", ""); }).join("") + "</div></div>" +
      (held ? '<div><div class="np-grp up">' + (sec.heldIn ? "לכאן נכנס" : "החזיקו מעמד") +
        (sec.best ? ' <span class="np-grp-n">★ הטוב בשבוע <bdi>' + (sec.best.pct > 0 ? "+" : "") + sec.best.pct + "%</bdi></span>" : "") + '</div><div class="np-tiles two">' + held + "</div></div>" : "") +
      "</div>";
  }
  // אריחי "הכסף הגדול היום במניות" — חמש הפוזיציות, רק כשהקובץ של אותו יום מסחר
  function bigMoneyTilesHtml(d) {
    var b = d.bigTrades;
    if (!b || !b.items || !b.items.length || b.date !== d.date) return "";
    function money(v) { return v >= 1e9 ? (v / 1e9).toFixed(1) + "B" : Math.round(v / 1e6) + "M"; }
    var KIND = { "new": "פוזיציה חדשה", "roll": "גלגול", "synthetic": "תחליף מניה", "combo": "אסטרטגיה משולבת", "flow": "זרימה" };
    return '<div class="np-sech"><b>💰 הכסף הגדול היום במניות</b><span>הפוזיציות הגדולות באופציות, אחרי ניקוי</span>' +
        '<a href="#indices" onclick="__goTab(\'indices\');return false">הפירוט ←</a></div>' +
      '<div class="np-tiles five">' + b.items.slice(0, 5).map(function (it) {
        var cls = it.direction === "up" ? "in" : it.direction === "down" ? "out" : "flat";
        var tag = it.direction === "up" ? '<span class="np-tag">▲ למעלה</span>' : it.direction === "down" ? '<span class="np-tag dn">▼ למטה</span>' : "";
        return '<div class="np-tile ' + cls + '" title="' + esc(it.text || "") + '"><div class="n"><span class="num" dir="ltr">' + esc(it.ticker) + "</span> " + tag + "</div>" +
          '<div class="p num" dir="ltr">$' + money(it.premium) + "</div>" +
          '<div class="d">' + esc(KIND[it.kind] || it.kindHe || "") + (cls === "flat" ? " · לא כיווני" : "") + "</div></div>";
      }).join("") + "</div>";
  }
  // היומן ברייל, מתחת למד: בסוף שבוע "השבוע הבא", ביום חול "היום ביומן"
  function leadAgendaHtml() {
    var t = ilNowParts(), dm = parseInt(t.iso.slice(8), 10) + "." + parseInt(t.iso.slice(5, 7), 10);
    var up = ((EARN && EARN.upcoming) || []).filter(function (u) { return u.date > t.iso; });
    var evs = ((ECON && ECON.events) || []);
    function row(dw, co, macro) { return '<div class="np-ag' + (macro ? " macro" : "") + '"><span class="dw">' + dw + '</span><span class="co">' + co + "</span></div>"; }
    function tk(list, n) { return '<span dir="ltr">' + esc(list.slice(0, n).join(" · ")) + "</span>"; }
    var rows = "", title;
    if (weekendNow()) {
      title = "🔭 השבוע הבא";
      var lim = new Date(Date.parse(t.iso) + 8 * 864e5).toISOString().slice(0, 10);
      var byDay = {};
      evs.forEach(function (e) { var k = String(e.date).slice(0, 10); if (e.actual == null && k > t.iso && k <= lim) (byDay[k] = byDay[k] || []).push(e); });
      var days = {};
      up.slice(0, 5).forEach(function (u) { days[u.date] = u; });
      Object.keys(byDay).forEach(function (k) { days[k] = days[k] || { date: k }; });
      Object.keys(days).sort().slice(0, 6).forEach(function (k) {
        var u = days[k], lbl = u.dow ? esc(u.dow) + ' <span dir="ltr">' + esc(u.label) + "</span>" : '<span dir="ltr">' + esc(byDay[k][0].ilDate) + "</span>";
        if (u.tickers && u.tickers.length) rows += row(lbl, tk(u.tickers, 3) + (u.count > 3 ? ' <small>+' + (u.count - 3) + "</small>" : ""), false);
        (byDay[k] || []).slice(0, 2).forEach(function (e) { rows += row(lbl + (e.ilTime ? ' · <span dir="ltr">' + esc(e.ilTime) + "</span>" : ""), esc(e.he), true); });
      });
      if (!rows && WEEKLY && WEEKLY.narrative && WEEKLY.narrative.lookahead) rows = '<p class="np-ag-note">' + esc(WEEKLY.narrative.lookahead) + "</p>";
    } else {
      title = "📅 היום ביומן";
      var rep = (EARN && EARN.reporting) || [];
      function names(w) { return rep.filter(function (r) { return (r.when || "") === w; }).map(function (r) { return r.ticker; }); }
      var bef = names("before"), aft = names("after"), unk = names("");
      rows += row("לפני הפתיחה", bef.length ? tk(bef, 4) : "אין דוחות בולטים", false);
      var today = evs.filter(function (e) { return e.ilDate === dm && String(e.date).slice(0, 4) === t.iso.slice(0, 4); });
      if (today.length) today.slice(0, 3).forEach(function (e) {
        var cls = e.surprise === "good" ? "up" : e.surprise === "bad" ? "down" : "";
        rows += row('<span dir="ltr">' + esc(e.ilTime || "") + "</span> · מאקרו", esc(e.he) +
          (e.actual != null ? ' <b class="num ' + cls + '" dir="ltr">' + esc(e.actual) + "</b>" + (e.forecast ? ' <small>צפי <span dir="ltr">' + esc(e.forecast) + "</span></small>" : "")
            : (e.forecast ? ' <small>צפי <span dir="ltr">' + esc(e.forecast) + "</span></small>" : "")), true);
      });
      else rows += row("מאקרו", "אין נתון מרכזי היום", true);
      rows += row("אחרי הסגירה", aft.length ? tk(aft, 4) : "אין דוחות בולטים", false);
      if (unk.length) rows += row("היום", tk(unk, 4), false);
      if (up.length && up[0].tickers && up[0].tickers.length) rows += row("הבא בתור · " + esc(up[0].dow || ""), tk(up[0].tickers, 3), false);
    }
    if (!rows) return "";
    return '<div class="np-agenda"><div class="np-sech"><b>' + title + "</b>" +
      '<a href="#weekcal" onclick="__goTab(\'weekcal\');return false">הלוח המלא ←</a></div>' + rows + "</div>";
  }
  function refreshLeadAgenda() { var a = document.getElementById("lead-agenda"); if (a) a.innerHTML = leadAgendaHtml(); }

  var SEC_EXPLAIN = "האחוז = כמה מהמניות בסקטור נסחרות מעל ממוצע 50 יום שלהן.";
  function weekendLeadHtml(ca, foot) {
    var w = WEEKLY, nar = w && w.narrative;
    if (!w || !w.weekOf) return "";
    var t = ilNowParts();
    var inWindow = t.dow === "Sat" || (t.dow === "Sun" && t.hour < 15);
    if (!inWindow) return "";
    // הסיכום חייב להיות של יום שישי האחרון (עד 3 ימים אחורה)
    var ageDays = (Date.parse(t.iso) - Date.parse(w.weekOf)) / 864e5;
    if (!(ageDays >= 0 && ageDays <= 3)) return "";
    // עדכון-אירוע שאינו preview ושתאריכו אחרי יום שישי (ידני/דחוף) גובר על הסיכום
    var eu = freshEventUpdate(CA);
    if (eu && eu.kind !== "preview" && eu.date > w.weekOf) return "";
    var s = w.summary || {}, sec = w.sectors || null;
    // 3.10.2026 (איציק): "עיוות" בשבת בבוקר — 06:18 כותרת הניתוח של שישי, 07:02 הסיכום השבועי.
    // המספרים של השבוע (build_weekly) קיימים כבר מ-05:31, אז עד שהסיכום המילולי נכתב
    // הכותרת היא כבר שבועית — משפט שנבנה מהמספרים; הניתוח של שישי נשאר בשורה שמתחת.
    if (!nar || !nar.lead) {
      if (s.spxPct == null) return "";
      var mv = Math.abs(s.spxPct) < 0.5 ? "כמעט ללא שינוי"   // המספר המדויק באריח שמתחת — בלי סוגריים שמתהפכים ב-RTL
        : (s.spxPct > 0 ? "בעלייה של " : "בירידה של ") + Math.abs(s.spxPct).toFixed(2) + "%";
      nar = { lead: "S&P 500 סיים את השבוע " + mv + ".", pending: true };
    }
    function pct(v) { return v == null ? "—" : (v > 0 ? "+" : "") + v.toFixed(2) + "%"; }
    function cls(v) { return v > 0 ? "up" : v < 0 ? "down" : ""; }
    // H1 = המשפט הראשון של ה-lead; ארוך מדי → עד הנקודתיים/המקף הראשון
    // התאריכים כבר בקיקר; בסוגריים בתוך הטקסט הם מתהפכים ב-RTL — מסירים לפני החיתוך
    var leadClean = String(nar.lead).replace(/\s*\(\d{1,2}[–-]\d{1,2}\.\d{1,2}\)/, "");
    var first = leadClean.split(/(?<=[^\d])\.\s/)[0].replace(/\.$/, "");
    // 10.10.2026 (איציק: "המשפט צריך להיות ביחד"): לא חותכים יותר את המשפט הראשון — משפט ארוך
    // מקבל כותרת בגופן קטן יותר (np-h1-long) במקום חצי בכותרת וחצי בטקסט שמתחת.
    var longH1 = first.length > 95;
    var rest = leadClean.slice(first.length).replace(/^[\s:—.,;]+/, "");   // גם פסיק — אחרי החיתוך בפסיק (26.9)
    // np128: בגרסה 2 של הסיכום יש כותרת משלו (headline, עד 80 תווים) — היא ה-H1, וה-lead כולו הטקסט שמתחת
    if (nar.headline) { first = String(nar.headline).replace(/\.$/, ""); longH1 = first.length > 60; rest = leadClean; }
    var stats = leadStats([
      { l: "S&amp;P 500 · שבועי", v: pct(s.spxPct), cls: cls(s.spxPct), s: '<span title="מסגירת שישי הקודם ועד סגירת שישי, כמו S&amp;P ו-VIX">מד השוק ' + (s.combStart != null ? s.combStart : "—") + " ← " + (s.combEnd != null ? s.combEnd : "—") + meterLowHi(s) + "</span>" },
      (s.vixStart != null && s.vixEnd != null) ? { l: "VIX · מדד הפחד", v: s.vixStart.toFixed(2) + " → " + s.vixEnd.toFixed(2), s: s.vixEnd < s.vixStart ? "ירד במהלך השבוע" : s.vixEnd > s.vixStart ? "עלה במהלך השבוע" : "ללא שינוי" } : null,
      (sec && sec.marketBreadth != null) ? { l: "מניות במגמת עלייה", v: sec.marketBreadth + "%", cls: sec.marketBreadth < 40 ? "down" : sec.marketBreadth > 60 ? "up" : "", s: "מעל ממוצע 50 יום" } : null
    ]);
    var head = '<span class="np-today">' + todayLine() + "</span>" +
      // 26.9.2026 (איציק): שעת הכתיבה של הסיכום — כדי שיהיה ברור מתי הכותרת התחלפה משישי לשבועי
      '<span class="np-k np-evt-mid">🗓 סיכום השבוע · <b dir="ltr">' + esc(w.label || "") + "</b>" +
        ((nar.writtenAt && /\d{1,2}:\d{2}/.test(nar.writtenAt)) ? ' · <span class="np-upd">נכתב <b dir="ltr">' + esc(/(\d{1,2}:\d{2})/.exec(nar.writtenAt)[1]) + "</b></span>" : "") +
        (nar.pending ? ' · <span class="np-upd">הסיכום המילולי ייכתב בשעה הקרובה</span>' : "") + "</span>" +
      '<h2 class="np-h1' + (longH1 ? " np-h1-long" : "") + '">' + esc(first) + "</h2>";
    // np129 (10.10.2026, איציק: "יותר מידע ופחות נתונים טכניים… קצר תמציתי"): כשהסיכום נושא drivers —
    // שורת שוק אחת (S&P שבועי · ברנט · אג"ח 10 שנים, חי מ-TICKD), פסקת "מה הניע את השוק", ושורת "השבוע הבא".
    // המד/הרוחב/אריחי הסקטורים יורדים מהבית — הם בטאב השוק. בלי drivers (גרסה 1–2) — הפריסה הקודמת.
    if (nar.drivers) {
      var tk = {}; ((TICKD && TICKD.items) || []).forEach(function (it) { tk[it.key] = it; });
      var line = ['<b>S&amp;P 500</b> <span class="num ' + cls(s.spxPct) + '" dir="ltr">' + pct(s.spxPct) + "</span>"];
      if (tk.brent && tk.brent.price != null) line.push('<b>ברנט</b> <span class="num" dir="ltr">' + Math.round(tk.brent.price) + "$</span>");
      if (tk.tnx && tk.tnx.price != null) line.push('<b>אג"ח 10 שנים</b> <span class="num" dir="ltr">' + (+tk.tnx.price).toFixed(2) + "%</span>");
      return head + '<p class="np-wk-mkt">' + line.join(' <span class="mute">·</span> ') + "</p>" +
        '<p class="np-dek">' + esc(nar.drivers) + "</p>" +
        (nar.nextWeek ? '<p class="np-wk-next"><b>השבוע הבא</b> ' + esc(nar.nextWeek) + "</p>" : "") +
        (ca ? '<p class="np-wk-last"><span class="np-k">יום המסחר האחרון · <b dir="ltr">' + esc(fmtTradeDate(ca.date)) + "</b></span> " + esc(ca.headline) + "</p>" : "") +
        foot;
    }
    return head +
      stats +
      // טקסט קצר: משפט אחד מהסיכום + משפט אחד מדוח הסקטורים; המלא בטאב מדדים ובדוח
      '<p class="np-dek">' + (rest ? esc(nar.headline ? rest : firstSentence(rest)) + " " : "") + (sec && sec.lead && !nar.sectors ? esc(firstSentence(sec.lead)) : "") + "</p>" +
      sectorTilesHtml(sec) +
      (ca ? '<p class="np-wk-last"><span class="np-k">יום המסחר האחרון · <b dir="ltr">' + esc(fmtTradeDate(ca.date)) + "</b></span> " + esc(ca.headline) + "</p>" : "") +
      foot;
  }

  /* ---------- עונת הדוחות — ציר בבית (3.10.2026, np107, איציק; אושר במוקאפ 3) ----------
     data/earnings_season.json (build_earnings_season.py): 8 שבועות, כמה מחברות ה-S&P 500 מדווחות בכל
     שבוע, כמה כבר דיווחו, ו-6 תחנות. מוצג מתחת לכותרת רק משבוע לפני תחילת העונה ועד סופה. */
  var SEASON = null;
  function ssAdd(iso, n) { var d = new Date(iso + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
  function ssDiff(a, b) { return Math.round((Date.parse(b + "T12:00:00Z") - Date.parse(a + "T12:00:00Z")) / 864e5); }
  function ssLbl(iso) { var p = iso.split("-"); return +p[2] + "." + +p[1]; }
  function renderSeason() {
    var el = document.getElementById("home-season");
    if (!el) return;
    var s = SEASON, today = ilNowParts().iso;
    if (!s || !s.weeks || !s.weeks.length || today < ssAdd(s.start, -7) || today > s.end) { el.hidden = true; el.innerHTML = ""; refreshSeasonBoard(); return; }
    var nW = s.weeks.length, days = nW * 7;
    // הפתיחה = הבנקים (העוגן), לא התחנה הראשונה — טסלה דיווחה לפני תחילת העונה (3.10)
    var first = (s.milestones || []).filter(function (m) { return m.key === "banks"; })[0] || { label: "הבנקים", date: s.anchor.date };
    var toFirst = ssDiff(today, first.date), title;
    if (toFirst > 0) title = "העונה נפתחת " + (toFirst === 1 ? "מחר" : "בעוד " + toFirst + " ימים") + " — " + first.label + " פותחים ב-" + ssLbl(first.date);
    else if (toFirst === 0 && !s.reported) title = "העונה נפתחת היום — " + first.label + " מדווחים";
    else {
      title = "שבוע " + Math.min(nW, Math.floor(ssDiff(s.start, today) / 7) + 1) + " מתוך " + nW + " · דיווחו " + s.reported + " מתוך " + s.total;
      var bd = s.board || {};
      title += (bd.epsN >= 10 && bd.epsBeatPct != null) ? " · " + bd.epsBeatPct + "% עקפו את צפי הרווח" + (bd.revBeatPct != null ? ", " + bd.revBeatPct + "% בהכנסות" : "")
        : " חברות המדד שמדווחות העונה";
    }
    // הציר — הזמן זורם מימין לשמאל. np112 (איציק, מוקאפ 2): אזור התחנות שמתחת לציר ירד; בתוך כל עמודה
    // הטיקרים של השבוע (weeks[].tickers — הגדולות + מניות המעקב, נבחרים ב-build_earnings_season.py),
    // ובעמודה נמוכה מדי — מעליה. "הבנקים" נשאר ככותרת מעל השבוע של הבנקים.
    var VH = 234, L = 10, R = 1130, base = 206, maxH = 140, LH = 16, colW = (R - L) / nW, h = "", max = 1, ov = "";
    // np110 (איציק: "עדיין הפוך" באייפון): כל טקסט עברי יוצא מה-SVG לשכבת HTML מעליו — WebKit לא
    // מסדר עברית בתוך <text> של SVG גם עם direction:ltr. מיקום באחוזים מה-viewBox, גודל ב-cqw.
    function ovAt(cls, x, y, txt) {
      return '<span class="ss-ov ' + cls + '" style="left:' + (x / 1140 * 100).toFixed(2) + "%;top:" + (y / VH * 100).toFixed(2) + '%">' + txt + "</span>";
    }
    s.weeks.forEach(function (w) { if (w.n > max) max = w.n; });
    var banksMon = first.date ? ssAdd(first.date, -((new Date(first.date + "T12:00:00Z").getUTCDay() + 6) % 7)) : "";
    var nx = Math.max(L + 2, Math.min(R - 2, R - (ssDiff(s.start, today) + 0.5) / days * (R - L)));
    s.weeks.forEach(function (w, i) {
      var x1 = R - (i + 1) * colW + 5, wd = colW - 10, cx = x1 + wd / 2, bh = Math.max(3, w.n / max * maxH);
      var done = ssAdd(w.mon, 7) <= today, top = base - bh;
      var tks = w.tickers || [], need = tks.length * LH + 4, inside = need <= bh;
      var y0 = inside ? top + 3 : top - need + 2;
      h += '<rect x="' + x1.toFixed(1) + '" y="' + top.toFixed(1) + '" width="' + wd.toFixed(1) + '" height="' + bh.toFixed(1) + '" rx="2" class="' + (done ? "ss-done" : "ss-bar") + '"' +
        (w.n === max ? ' stroke="var(--accent)" stroke-width="1.5"' : "") + '><title>' + w.n + " חברות מהמדד מדווחות בשבוע " + w.label + "</title></rect>";
      tks.forEach(function (t, k) {
        h += '<text class="ss-tk' + (done && inside ? " inv" : "") + '" x="' + cx.toFixed(1) + '" y="' + (y0 + k * LH + 13).toFixed(1) + '">' + esc(t) + "</text>";
      });
      var numY = (inside ? top : y0) - 6;
      h += '<text class="ss-num" x="' + cx.toFixed(1) + '" y="' + numY.toFixed(1) + '">' + w.n + "</text>";
      h += '<text class="ss-num" x="' + cx.toFixed(1) + '" y="' + (base + 16) + '">' + w.label + "</text>";
      if (w.n === max) ov += ovAt("ss-ov-peak", cx, numY - 14, "שבוע השיא");
      if (w.mon === banksMon) ov += ovAt("ss-ov-lbl", cx, numY - 14, esc(first.label));
    });
    h += '<line x1="' + L + '" y1="' + base + '" x2="' + R + '" y2="' + base + '" class="ss-base"></line>';
    // "אנחנו כאן" — הקו מאחורי העמודות והטיקרים, התווית מעל הכל
    h = '<line x1="' + nx.toFixed(1) + '" y1="' + (base - maxH - 36) + '" x2="' + nx.toFixed(1) + '" y2="' + (base + 4) + '" class="ss-now"></line>' + h +
      '<rect x="' + (Math.min(R - 68, Math.max(L, nx - 34))).toFixed(1) + '" y="' + (base - maxH - 58) + '" width="68" height="20" rx="10" class="ss-nowbg"></rect>';
    ov += ovAt("ss-ov-now", Math.min(R - 34, Math.max(L + 34, nx)), base - maxH - 44, "אנחנו כאן");
    // np120: הציר הוא פאנל בטאב היומן — הכותרת ב-.ph, הקישור גולל ללוח התוצאות באותו טאב
    el.classList.add("pan");
    el.innerHTML = panHd("🗓 עונת הדוחות · " + esc(s.season), '<span class="mute">' + esc(title) + "</span>",
        '<a class="go" href="#weekcal" onclick="var m=document.getElementById(\'sbd-pan\');if(m)m.scrollIntoView({behavior:\'smooth\',block:\'start\'});return false">' + (s.reported ? "לוח התוצאות" : "לוח התוצאות") + "</a>") +
      '<div class="pb"><div class="ss-scroll"><div class="ss-wrap"><svg class="ss-tl" viewBox="0 0 1140 ' + VH + '" role="img" aria-label="ציר עונת הדוחות: כמה חברות מהמדד מדווחות בכל שבוע">' + h + "</svg>" + ov + "</div></div>" +
      '<p class="ss-cap">העמודות: כמה מחברות ה-S&amp;P 500 מדווחות בכל שבוע · בתוכן: החברות הגדולות שמדווחות באותו שבוע · כהה = שבוע שעבר</p></div>';
    el.hidden = false;
    refreshSeasonBoard();
  }

  /* לוח התוצאות של העונה (3.10.2026, שלב 2) — בראש טאב לוח הדיווחים. מ-earnings_season.json.board:
     בפועל מול צפי מסורק TradingView (הרבעון שדווח), תגובה = סגירה מול סגירה ביום התגובה. */
  function seasonBoardHtml(bare_) {
    var s = SEASON, b = s && s.board;
    if (!s || !b) return "";
    var today = ilNowParts().iso;
    if (today < ssAdd(s.start, -7) || today > ssAdd(s.end, 14)) return "";
    function sgn(v) { return v == null ? "—" : '<bdi dir="ltr">' + (v > 0 ? "+" : "") + v.toFixed(1) + "%</bdi>"; }
    var head = bare_ ? "" : '<div class="sbd-head"><span class="np-k">🗓 לוח התוצאות · עונת הדוחות ' + esc(s.season) + "</span>" +
      '<span class="sbd-sub">חברות ה-S&amp;P 500 · מתעדכן כל רבע שעה</span></div>';
    if (!b.reported) {
      var opens = ((s.milestones || []).filter(function (m) { return m.key === "banks"; })[0] || {}).date || s.anchor.date;
      return '<section class="sbd">' + head + '<p class="sbd-pre">יתמלא מ-' + ssLbl(opens) +
        ", כשהבנקים פותחים את העונה: כמה חברות דיווחו, כמה עקפו את הצפי ברווח ובהכנסות, איך השוק הגיב — ולפי סקטור.</p></section>";
    }
    var p = s.total ? Math.round(b.reported / s.total * 100) : 0;
    function tile(v, l, sub, cls) { return '<div class="sbd-st"><div class="v ' + (cls || "") + '">' + v + '</div><div class="l">' + l + '</div><div class="s">' + sub + "</div></div>"; }
    var stats =
      tile(b.epsBeatPct != null ? b.epsBeatPct + "%" : "—", "עקפו את צפי הרווח", b.epsBeat + " מתוך " + b.epsN) +
      tile(b.revBeatPct != null ? b.revBeatPct + "%" : "—", "עקפו בהכנסות", b.revBeat + " מתוך " + b.revN) +
      tile(b.reactBeatN >= 3 ? sgn(b.reactBeat) : "—", "פרס על עקיפה", b.reactBeatN >= 3 ? "תגובה ממוצעת ביום הדוח (" + b.reactBeatN + ")" : "מתמלא", b.reactBeat > 0 ? "up" : b.reactBeat < 0 ? "down" : "") +
      tile(b.reactMissN >= 3 ? sgn(b.reactMiss) : "—", "עונש על החטאה", b.reactMissN >= 3 ? "תגובה ממוצעת ביום הדוח (" + b.reactMissN + ")" : "מתמלא", b.reactMiss > 0 ? "up" : b.reactMiss < 0 ? "down" : "");
    var secs = (b.sectors || []).filter(function (x) { return x.n >= 2; }).map(function (x) {
      var q = Math.round(x.beat / x.n * 100);
      return '<div class="sbd-row"><span>' + esc(x.name) + '</span><span class="t"><i class="' + (q < 60 ? "lo" : "") + '" style="width:' + q + '%"></i></span><span class="n">' + x.beat + "/" + x.n + "</span></div>";
    }).join("");
    var movers = (b.movers || []).map(function (m) {
      return '<a class="sbd-mv" dir="ltr" href="https://www.tradingview.com/symbols/' + encodeURIComponent(m.sym) + '/" target="_blank" rel="noopener" title="' +
        (m.eps > 0 ? "עקפה" : m.eps < 0 ? "החטיאה" : "בצפי") + " את צפי הרווח ב-" + Math.abs(m.eps) + '%">' + esc(m.sym) +
        ' <b class="' + (m.react > 0 ? "up" : "down") + '">' + (m.react > 0 ? "+" : "") + m.react.toFixed(1) + "%</b></a>";
    }).join("");
    return '<section class="sbd">' + head +
      '<div class="sbd-grid"><div>' +
        '<div class="sbd-prog"><b>' + b.reported + "</b><span>מתוך " + s.total + " דיווחו (" + p + "%)</span></div>" +
        '<div class="sbd-bar" aria-hidden="true"><i style="width:' + p + '%"></i></div>' +
        '<div class="sbd-stats">' + stats + "</div></div>" +
      "<div>" + (secs ? '<p class="sbd-h">עקפו את צפי הרווח, לפי סקטור</p>' + secs : "") +
        (movers ? '<p class="sbd-h">התגובות הבולטות ביום הדוח</p><div class="sbd-mvs">' + movers + "</div>" : "") +
      "</div></div></section>";
  }
  function refreshSeasonBoard() { var el = document.getElementById("season-board"); if (el) el.innerHTML = seasonBoardHtml(true); }

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
    // 20.9.2026 (איציק): שורת המכוונים (מניות/סקטורים/אופציות + 4 הנוריות) ירדה מהבית — נשאר רק הקישור
    var fullLink = '<a href="#indices" onclick="__goTab(\'indices\');return false">הניתוח המלא ←</a>';
    // 24.9.2026: שורת מעקב הצפי במקום המכוונים; בכותרת "לקראת שבוע המסחר" בלוק הצפי כבר מוצג → בלי השורה
    var footPlain = '<div class="np-leadfoot">' + fullLink + "</div>";
    var foot = '<div class="np-leadfoot">' + fcTrackLine() + fullLink + "</div>";

    renderLeadRail(d);
    var ls = document.getElementById("lead-sub");
    if (ls) ls.innerHTML = 'סגירת יום ' + MD_DOW[new Date(d.date + "T12:00:00").getDay()] + ' · <b class="num" dir="ltr">' + esc(fmtTradeDate(d.date)) + "</b>";
    // כותרת סוף-השבוע (19.9.2026, איציק): משבת ועד ראשון 15:00 הכותרת בבית היא סיכום השבוע
    // (משפט-הפתיחה של הסיכום המילולי + "לאן זרם הכסף" מדוח הסקטורים); הניתוח של יום שישי
    // יורד שורה למטה. מראשון 15:00 חוזרת הלוגיקה הרגילה — סקירת "לקראת שבוע המסחר"
    // (eventUpdate preview, נכתבת 14:45). עדכון-אירוע ידני/דחוף שתאריכו אחרי יום שישי גובר.
    var wkHtml = weekendLeadHtml(ca, foot);
    if (wkHtml) { el.innerHTML = wkHtml; return; }
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
        // 20.9.2026: כותרות רגועות באותו שלד של שאר הכותרות — 3 נתונים חיים + משפט אחד;
        // עדכון מאקרו אדום (CPI/פד) נשאר עם הטקסט המלא, שם הפירוט הוא העיקר
        (euCalm ? marketStats(eu.kind === "preview" ? ["es", "tnx", "vix"] : ["es", "nq", "vix"]) : "") +
        (eu.tldr ? '<p class="np-dek">' + esc(euCalm ? firstSentence(eu.tldr) : eu.tldr) + "</p>" : "") +
        // הרוטינה של שני 07:45 דורסת את eventUpdate — הצפי הנעול נשמר ב-forecasts.json (current)
        (eu.kind === "preview" ? forecastHtml(eu.forecast || (FCAST && FCAST.current)) : "") +
        (eu.action ? '<p class="np-bottom">⚡ <b>מה עושים:</b> ' + esc(eu.action) + "</p>" : "") +
        (eu.odds ? '<p class="np-odds">🎲 ' + esc(eu.odds) + "</p>" : "") +
        ((eu.kind === "preview" && (eu.forecast || (FCAST && FCAST.current))) ? footPlain : foot);
      return;
    }

    if (ca) {
      // מבנה רזה: קיקר עם התאריך + האחוז · כותרת אנליטית · משפט-מהות · שורה תחתונה
      var pm = /([+−-]\d+(?:\.\d+)?%)/.exec(c.headline || "");
      var pmCls = pm ? (pm[1].charAt(0) === "+" ? "up" : "down") : "";
      // המניה הממוצעת = המדד השוויוני; הנתון קיים רק בטקסט של מנוע המסקנות
      var ev = d.evidence || {}, eqm = /שוויוני\s*([+−-]\d+(?:\.\d+)?%)/.exec(JSON.stringify(c.analysis || []) + (c.conclusion || ""));
      var spm = /שוויוני\s*[+−-]\d+(?:\.\d+)?%\s*מול(?:\s*מדד)?\s*([+−-]\d+(?:\.\d+)?%)/.exec(JSON.stringify(c.analysis || []) + (c.conclusion || ""));
      if (spm && pm) pm = [pm[0], spm[1]];
      var dayStats = leadStats([
        pm ? { l: "S&amp;P 500 · יומי", v: esc(pm[1]), cls: pmCls, s: ev.spxPrice != null ? '<span class="num" dir="ltr">' + Number(ev.spxPrice).toLocaleString("en-US", { maximumFractionDigits: 2 }) + "</span>" : "" } : null,
        eqm ? { l: "המניה הממוצעת", v: esc(eqm[1]), cls: eqm[1].charAt(0) === "+" ? "up" : "down", s: "המדד במשקל שווה" }
            : (ev.pctMa200 != null ? { l: "מניות מעל ממוצע 200", v: Math.round(ev.pctMa200) + "%", s: "רוחב השוק" } : null),
        ev.vix != null ? { l: "VIX · מדד הפחד", v: Number(ev.vix).toFixed(2), cls: ev.vix >= 20 ? "down" : "", s: ev.vix < 16 ? "רגוע" : ev.vix < 20 ? "מוגבר" : "גבוה" } : null
      ]);
      el.innerHTML =
        '<span class="np-today">' + todayLine() + "</span>" +
        '<span class="np-k">יום המסחר · <b dir="ltr">' + esc(fmtTradeDate(d.date)) + "</b>" +
          (pm ? ' · <b class="num ' + pmCls + '" dir="ltr">' + esc(pm[1]) + "</b>" : "") +
          // 25.9.2026 (איציק): שעת הכתיבה של הניתוח — כדי שיהיה ברור מתי "הבוקר" של הכותרת
          ((ca._meta && ca._meta.updatedAt && /\d{1,2}:\d{2}/.test(ca._meta.updatedAt))
            ? ' · <span class="np-upd">עודכן <b dir="ltr">' + esc(/(\d{1,2}:\d{2})/.exec(ca._meta.updatedAt)[1]) + "</b></span>" : "") + "</span>" +
        '<h2 class="np-h1">' + esc(ca.headline) + "</h2>" +
        dayStats +
        // בבית רק המשפט הראשון של ה-tldr; המלא בטאב מדדים ("הניתוח המלא ←")
        (ca.tldr ? '<p class="np-dek">' + esc(firstSentence(ca.tldr)) + "</p>" : "") +
        (ca.bottomline ? '<p class="np-bottom">💡 ' + esc(ca.bottomline).replace("שורה תחתונה:", "<b>שורה תחתונה:</b>") + "</p>" : "") +
        bigMoneyTilesHtml(d) +
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
    // 12.9.2026: קריאת הכיוון מגיעה עכשיו מייצוא SPY (ב-SPX ~99% מולטי-לג → תמיד "שורי");
    // dirSource/dirNote מ-daily_state. openLabel = ההטיה של פוזיציות חדשות (נפח > OI).
    var src = fl.dirSource ? '<span class="er-badge" title="' + esc(fl.dirNote || "") + '">' + esc(fl.dirSource) + "</span>" : "";
    var opn = fl.openLabel ? ' <span class="np-open" title="כסף חדש = לאן נטו הפוזיציות שנפתחו היום (עסקאות שהנפח בהן גדול מהפוזיציות הפתוחות, כלומר כניסה חדשה ולא סגירה), $' + Math.round((fl.openP || 0) / 1e6) + 'M)">כסף חדש: <b class="' +
      (fl.openLabel === "דובי" ? "down" : fl.openLabel === "שורי" ? "up" : "") + '">' + esc(fl.openLabel) + "</b></span>" : "";
    return '<div class="np-sub" title="' + esc(tip) + '"><span>הכסף הגדול</span><span><b class="' + dc + '">' + esc(fl.deltaLabel) + "</b>" + opn + legBadge + src + "</span></div>";
  }

  /* רמזור VIX (27.9.2026, איציק) — מצב, לא תחזית. המספרים ההיסטוריים בריחוף בלבד. */
  var VL_HE = { green: "ירוק", yellow: "צהוב", red: "אדום" };
  var VL_TIP = {
    green: "ירוק: VIX מתחת לממוצע שלו ל-50 יום — שוק רגוע. בבדיקה על 2005–2026, כשה-VIX נמוך תיקון של 5% תוך 20 יום נדיר יותר מהרגיל.",
    yellow: "צהוב: VIX לפחות 10% מעל הממוצע ל-50 יום — פחד מזדחל. בבדיקה על 2005–2026: ב-18% מהמקרים הדומים הגיע תיקון של 5% תוך 20 ימי מסחר, מול 11% בימים רגילים. 4 מתוך 5 אזעקות הן שווא. נכבה כשה-VIX חוזר מתחת לממוצע.",
    red: "אדום: S&P 500 לפחות 3% מתחת לשיא 52 השבועות — הירידה בפועל התחילה."
  };
  var VL_SPIKE = " ‼ דיברגנס: המדד עלה 1%+ ב-10 ימים בזמן שה-VIX עלה 10%+ — הסימן הנדיר והחד ביותר בבדיקה (37% מהמקרים → תיקון של 5% תוך 20 יום, פעם בשנה בערך).";
  function vlDot(l, big) { return l ? '<span class="vl-dot ' + esc(l.state) + (big ? " big" : "") + '" title="' + esc(VL_TIP[l.state] || "") + (l.spike ? esc(VL_SPIKE) : "") + '"></span>' : ""; }
  function vixLightRow() {
    var l = TICKD && TICKD.vixLight;
    if (!l || !l.state) return "";
    return '<div class="np-sub np-vixl" title="' + esc((VL_TIP[l.state] || "") + (l.spike ? VL_SPIKE : "")) + '"><span>VIX ' + vlDot(l) + (l.spike ? '<b class="vl-spike">!</b>' : "") + "</span>" +
      '<span><b class="num ' + esc(l.state) + '">' + esc(VL_HE[l.state] || "") + "</b> <small>" + '<span class="num" dir="ltr">' + Number(l.vix).toFixed(1) + "</span> · ממוצע 50: " + '<span class="num" dir="ltr">' + Number(l.ma50).toFixed(1) + "</span>" +
      (l.state === "red" ? ' · <span class="num" dir="ltr">' + Number(l.spxOffHigh).toFixed(1) + "%</span> מהשיא" : "") + "</small></span></div>";
  }

  /* np113 (6.10.2026, איציק): יום המסחר שהמד מתייחס אליו — מתחת לכותרת המד, כדי שיהיה ברור
     שהוא מסונכרן עם המדדים. "לא עודכן" רק כשהסגירה האחרונה כבר בת 10 שעות ויותר (הדשבורד
     של סגירת אמש מגיע בבוקר, ~05:15) והמד עדיין על יום קודם. */
  var MD_DOW = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"];
  function meterDayHtml(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
    if (!m) return "";
    var dt = new Date(+m[1], +m[2] - 1, +m[3]);
    var now = new Date(), c = new Date(now);
    if (!(tradingDay(c) && c >= atTime(c, closeT(c)))) { do { c.setDate(c.getDate() - 1); } while (!tradingDay(c)); }
    var lastClose = atTime(c, closeT(c)), stale = dayKey(dt) < dayKey(c) && (now - lastClose) > 10 * 3600e3;
    return '<div class="np-meter-day">נכון לסגירת יום ' + MD_DOW[dt.getDay()] + ' · <b class="num" dir="ltr">' + fmtTradeDate(iso) + "</b>" +
      (stale ? ' <span class="np-meter-stale" title="נתוני הסגירה של ' + c.getDate() + "." + (c.getMonth() + 1) + ' עוד לא הגיעו לדשבורד">· לא עודכן</span>' : "") + "</div>";
  }

  // ─ רייל המד ─ (פונקציה נפרדת: קודם רץ רק בענף-הנפילה, והרייל נעלם אם ניתוח
  // Claude נטען לפני indices — עכשיו מרונדר תמיד, מכל קריאת renderLead)
  function renderLeadRail(d) {
    var rail = document.getElementById("lead-rail");
    if (!rail) return;
    rail.innerHTML = leadRailHtml(d, "");
    renderSpark("");
  }
  /* גוף רייל המד — משותף לבית (sfx="") ולטאב השוק (sfx="-i", np120); ה-id-ים של הספארקליין מקבלים סיומת */
  function leadRailHtml(d, sfx) {
    sfx = sfx || "";
    var s = d.scores || {}, e = d.evidence || {};
    var w = s.combined != null ? meterWord(s.combined) : ["", "var(--text)"];
    function sub(label, key, val) {
      return '<div class="np-sub np-cm"><span>' + label + '</span><span class="bar"><i style="width:' + (val == null ? 0 : Math.max(0, Math.min(100, val))) + '%"></i></span><span><b class="num">' +
        (val == null ? "—" : val) + "</b> " + diffTag(key) + "</span></div>";
    }
    var seg = s.combined != null ? '<div class="seg" role="img" aria-label="ציון ' + s.combined + ' מתוך 100"><i style="background:var(--down)"></i><i style="background:var(--state-fill)"></i><i style="background:var(--up)"></i><b style="left:calc(' + s.combined + '% - 1px)"></b></div>' +
      '<div class="segl"><span>הגנתי · עד 44</span><span>זהיר · 45–65</span><span>חיובי · מ-66</span></div>' : "";
    return '<div class="ph"><h2>The Edge Meter</h2>' + meterDayHtml(d.date) + (sfx ? "" : '<a class="go" href="#indices" onclick="__goTab(\'indices\');return false">המד המלא</a>') + '</div><div class="pb">' +
      '<div class="np-score"><b class="num" style="color:' + w[1] + '">' + (s.combined != null ? s.combined : "—") + "</b>" +
        '<span style="color:' + w[1] + '">' + w[0] + "</span>" + (DIFFS && DIFFS.combined != null && HIST && HIST.days.length > 1 ? '<span class="mute s" style="margin-inline-start:auto">אתמול: <span class="num">' + HIST.days[HIST.days.length - 2].combined + "</span></span>" : "") + "</div>" + seg +
      '<svg class="meter-spark np-spark" id="meter-spark' + sfx + '" viewBox="0 0 120 30" preserveAspectRatio="none" style="cursor:pointer" role="link" aria-label="לגרף המלא בטאב מדדים" onclick="__goTab(\'indices\');var m=document.getElementById(\'meter-timeline\');if(m)m.scrollIntoView({behavior:\'smooth\',block:\'start\'});"></svg>' +
      '<div class="spark-label" id="spark-label' + sfx + '"></div>' +
      sub("טכני", "tech", s.tech) +
      sub("רוחב", "breadth", s.breadth) +
      sub("אופציות", "flow", s.flow) +
      // v6 (19.9.2026): המספר למעלה = הקריאה של היום; במד נכנס ממוצע יומיים (מאחורי הקלעים)
      ((d.flow && d.flow.meterScore != null && d.flow.meterScore !== s.flow) ? '<div class="np-sub-note">במד נכנס ממוצע יומיים: <b class="num">' + d.flow.meterScore + "</b></div>" : "") +
      vixLightRow() +
      bigMoneyRow(d.flow) +
      ((d.flow && d.flow.spxWarning && d.flow.spxWarning.active) ? '<div class="np-sub np-spxw" title="' + esc(d.flow.spxWarning.text || "") + '"><span>⚠ מכירת ביטוח חריגה ב-SPX</span><b class="num">אחוזון ' + esc(String(d.flow.spxWarning.pct)) + "</b></div>" : "") +
      // 18.9.2026 (איציק): "46 / 101" ב-RTL נקרא הפוך — כל מספר צמוד לתווית שלו ובצבע שלו
      (e.nhCount != null ? '<div class="np-sub"><span>שיאים ושפלים 52ש׳</span><b class="np-nhnl">' +
        '<span class="up"><span class="num" dir="ltr">' + e.nhCount + '</span> שיאים</span><span class="np-sep">·</span>' +
        '<span class="down"><span class="num" dir="ltr">' + e.nlCount + '</span> שפלים</span></b></div>' : "") +
      "</div>";
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
            (r.logo ? earnLogoImg(r) : "") +
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
    // תגובות המדווחות עברו לטאב דיווחים (11.9.2026 אחה"צ, בקשת איציק) — הבית: היום והשבוע בלבד
    refreshLeadAgenda();
    el.innerHTML =
      '<h3 class="np-k">מדווחות היום והשבוע</h3>' + today + week +
      '<a class="np-more" href="#weekcal" onclick="__goTab(\'weekcal\');return false">לוח הדיווחים המלא ←</a>';
  }

  /* סיכום השבוע — בטאב מדדים, מתחת לציר הזמן (הועבר מהבית 11.9.2026 לבקשת איציק):
     מציג תמיד את השבוע השלם האחרון, ומתחלף כשהבא נבנה. מתחת לאריחים — הסיכום
     המילולי (`narrative`) שרוטינת nidam-weekly-narrative כותבת בסופ"ש; עד אז הוא חסר. */
  var WEEKLY = null;
  function renderWeekly(d) {
    var el = document.getElementById("weekly-slot");
    if (!el) return;
    var days = (d && d.days) || [], s = (d && d.summary) || {};
    if (!days.length || !d.weekOf) { el.innerHTML = ""; return; }
    var nar = d.narrative || null;
    function pct(v) { return v == null ? "—" : (v > 0 ? "+" : "") + v.toFixed(2) + "%"; }
    function cls(v) { return v > 0 ? "up" : v < 0 ? "down" : ""; }
    var w1 = meterWord(s.combEnd || 0);
    // np120: פאנל "סיכום השבוע" בטאב השוק — 4 אריחים, חמשת הימים, הסיכום המילולי, "לאן זרם הכסף"
    el.innerHTML =
      panHd('סיכום השבוע שעבר · <span class="num" dir="ltr">' + esc(d.label || "") + "</span>", '<span class="mute">מסגירת שישי לסגירת שישי</span>') + '<div class="pb">' +
      '<div class="tiles">' + bdTile("S&amp;P 500", pct(s.spxPct), "", cls(s.spxPct)) +
        bdTile("מד השוק", (s.combStart != null ? s.combStart : "—") + "→" + (s.combEnd != null ? s.combEnd : "—"), '<span style="color:' + w1[1] + '">' + w1[0] + "</span>" + meterLowHi(s)) +
        bdTile("VIX", (s.vixStart != null ? s.vixStart.toFixed(1) : "—") + "→" + (s.vixEnd != null ? s.vixEnd.toFixed(1) : "—")) +
        bdTile("ימי מכירה רחבה", s.sellDays || 0, "", s.sellDays ? "down" : "") + "</div>" +
      '<div class="wk-days">' + days.map(function (x) {
        var w = meterWord(x.combined || 0);
        return '<div class="wk-day' + (x.sell ? " sell" : "") + '"><div class="wk-dow">' + esc(x.dow) + ' <span dir="ltr">' + esc(x.label) + "</span></div>" +
          '<div class="wk-c" style="color:' + w[1] + '">' + (x.combined != null ? x.combined : "—") + "</div>" +
          '<div class="wk-p num ' + cls(x.chg) + '" dir="ltr">' + pct(x.chg) + "</div>" +
          (x.headline ? '<div class="wk-h">' + esc(x.headline) + "</div>" : "") + "</div>";
      }).join("") + "</div>" +
      (nar ? '<div class="wk-nar' + (nar.version >= 2 ? " v2" : "") + '">' +
          // np128 (10.10.2026, איציק: "סיכום שבועי איכותי יותר"): גרסה 2 של הסיכום — כותרת, שורה תחתונה,
          // ופרקים עם כותרות (מה הזיז את השוק / לאן זרם הכסף / הדוחות / מאקרו / הצפי שלנו / הנבחרות / השבוע הבא)
          // + "מה לבדוק" (3 שאלות). המפתחות הישנים (news/earnings/macro/lookahead) נשארו באותם שמות — גרסה 1 מתרנדרת כרגיל.
          (nar.headline ? '<h3 class="wk-head">' + esc(nar.headline) + "</h3>" : "") +
          (nar.lead ? "<p class=\"wk-lead\">" + esc(nar.lead) + "</p>" : "") +
          [["מה הזיז את השוק", nar.news], ["לאן זרם הכסף", nar.sectors], ["הדוחות", nar.earnings], ["מאקרו", nar.macro],
           ["הצפי שלנו מול מה שקרה", nar.forecast], ["הנבחרות", nar.picks], ["השבוע הבא", nar.lookahead]].map(function (p) {
            return p[1] ? '<p class="wk-line"><b>' + p[0] + "</b> " + esc(p[1]) + "</p>" : "";
          }).join("") +
          (nar.version >= 2 && !nar.sectors ? '<p class="wk-line mute"><b>לאן זרם הכסף</b> דוח הסקטורים השבועי טרם הגיע — הסיכום ייכתב מחדש כשיגיע.</p>' : "") +
          ((nar.watch || []).length ? '<div class="wk-watch"><b>מה לבדוק בשבוע הבא</b><ol>' + nar.watch.map(function (q) { return "<li>" + esc(q) + "</li>"; }).join("") + "</ol></div>" : "") +
          "</div>"
        : '<p class="wk-wait mute">הסיכום המילולי של השבוע נכתב בסוף השבוע, אחרי שסגירת שישי נקלטת.</p>') +
      (d.sectors && (d.sectors.lead || (d.sectors.out || []).length) ? '<div class="kv"><span>💸 לאן זרם הכסף</span><span>' +
        (d.sectors.lead ? esc(d.sectors.lead) + " " : "") +
        ((d.sectors.out || []).length ? "הרוחב ירד ב: " + d.sectors.out.map(function (o) { return esc(o.name) + ' <span class="num"><bdi>' + o.from + "%</bdi> ← <bdi>" + o.to + "%</bdi></span>"; }).join(" · ") : "") + heldHtml(d.sectors) + " · " +
        '<a href="#sectors" onclick="__goTab(\'sectors\');return false">הדוח המלא</a></span></div>' + '<p class="np-wk-exp mute s">' + SEC_EXPLAIN + "</p>" : "") +
      (nar ? '<p class="stamp" style="margin:0">סיכום מילולי · נכתב ' + esc(nar.writtenAt || "") + "</p>" : "") +
      "</div>";
  }

  /* ---------- renderers ---------- */

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
    // שלוש שורות סנטימנט תיאוריות (13.9.2026) — research.lines מ-send_report.sentiment_lines:
    // מניות (UOA כלל-שוקי מול ההיסטוריה שלו) · SPY (כיוון + פוזיציות חדשות) · SPX (ביטוח נמכר/נקנה + IV/RV).
    // טקסט בלבד, לא ציון — המד לא נוגע בזה.
    var lines = ((f.research && f.research.lines) || []).filter(function (l) { return l.display !== "bigtrades"; });
    if (f.spxWarning && f.spxWarning.active) lines = lines.map(function (l) { return l.key === "spx" ? { key: "spx", label: "SPX", tone: "warn", text: "⚠ " + f.spxWarning.text } : l; });
    var linesHtml = lines.length ? '<div class="fs-lines">' + lines.map(function (l) {
      return '<div class="fs-line tone-' + esc(l.tone || "neutral") + '"><span class="fs-dot"></span>' +
        '<span class="fs-lbl">' + esc(l.label) + '</span><span class="fs-txt">' + esc(l.text) + "</span></div>";
    }).join("") + "</div>" : "";
    var noteHtml = f.scoreNote ? '<p class="stamp" style="margin:0 0 10px">🧮 ' + esc(f.scoreNote) +
      (f.spxScore != null ? ' לשם השוואה, הציון הישן מ-SPX בלבד (v4): ' + esc(String(f.spxScore)) + '.' : '') + "</p>" : "";
    return '<div class="section-title">🎯 ההימור נטו באופציות</div>' +
      '<div class="card">' +
      linesHtml + noteHtml +
      (f.deltaLabel ? '<p style="margin-top:0">הכסף הגדול נטו: <b class="' + tiltCls + '">' + esc(f.deltaLabel) + "</b>" +
        " (משוקלל-דלתא)" +
        (f.openLabel ? ' · כסף חדש היום (פוזיציות שנפתחו, $' + Math.round((f.openP || 0) / 1e6) + 'M): <b class="' + (f.openLabel === "דובי" ? "down" : f.openLabel === "שורי" ? "up" : "") + '">' + esc(f.openLabel) + "</b>"
          : (f.openingLean ? ' · פוזיציות חדשות: <b>' + esc(f.openingLean) + "</b>" : "")) + "</p>" : "") +
      (f.dirNote ? '<p class="stamp" style="margin:-4px 0 8px">' + esc(f.dirNote) + (f.legNote ? " · " + esc(f.legNote) : "") + "</p>" : "") +
      '<div class="fq-grid">' +
      cells.map(function (q) {
        return '<div class="fq-cell"><span class="fq-l">' + q[0] + '</span><b class="num ' + q[2] + '">' + m(q[1]) + "</b></div>";
      }).join("") + "</div>" +
      '<p class="stamp" style="margin-bottom:0">קנייה אגרסיבית של Calls ומכירת Puts = הימור שורי; קניית Puts ומכירת Calls = דובי. הציון בכרטיס "אופציות" (v6, מ-19.9.2026) נבנה מכיוון הכסף הגדול ב-SPY בלבד, מול ההיסטוריה של עצמו; SPX משמש נורת אזהרה ומניות בודדות מוצגות בנפרד למטה. הריבועים כאן הם קניות ומכירות של הכסף הגדול ב-SPY. ' +
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
    // 20.9.2026: הרוטינה כתבה time="14:46 IL" → Date.parse החזיר NaN והכותרת נפלה בשקט
    // לניתוח של יום שישי. לוקחים רק את ה-HH:MM מתוך השדה, מה שלא יהיה סביבו.
    var hm = /(\d{1,2}):(\d{2})/.exec(String(eu.time));
    if (!hm) return null;
    eu.time = hm[1].padStart(2, "0") + ":" + hm[2];   // גם לתצוגה: "14:46" נקי
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

  /* ציר הזמן של The Edge Meter — בראש טאב מדדים (11.9.2026).
     history.json (עד 120 יום) + ימי-המכירה מ-indices.json. הציון המשולב על רקע
     שלוש רצועות-המצב של המד (66+/45+/מתחת), ▲ בימי מכירה רחבה, ומתחת פס S&P 500
     על אותו ציר זמן *בפאנל משלו* — לא ציר-Y כפול (שני סולמות על גרף אחד מטעים).
     הרכיבים (טכני/רוחב/אופציות) כבויים כברירת מחדל כדי שהגרף לא יהפוך לספגטי.
     המצב (טווח/רכיבים) חי ב-MT כי הטאב נבנה מחדש בכל רענון נתונים. */
  var MT = { range: 30, show: { tech: false, breadth: false, flow: false }, hover: -1 };
  var MT_DOW = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"];
  function mtCss(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
  function mtD(s) { var p = s.split("-"); return (+p[2]) + "/" + (+p[1]); }
  function mtEl(t, a) { var e = document.createElementNS("http://www.w3.org/2000/svg", t); for (var k in a) e.setAttribute(k, a[k]); return e; }
  function meterTimelineHtml(bare_) {
    var seg = '<div class="mt-seg" role="group" aria-label="טווח">' + [30, 60, 90].map(function (r) {
          return '<button type="button" data-r="' + r + '" aria-pressed="' + (MT.range === r) + '">' + r + "</button>";
        }).join("") + "</div>";
    var lg = '<div class="mt-lg" role="group" aria-label="רכיבים"><span class="k">רכיבים:</span>' +
        [["tech", "טכני"], ["breadth", "רוחב"], ["flow", "אופציות"]].map(function (p) {
          return '<button type="button" data-s="' + p[0] + '" aria-pressed="' + MT.show[p[0]] + '" style="--c:var(--mt-' + p[0] + ')"><i></i>' + p[1] + "</button>";
        }).join("") + "</div>";
    // np120: בפאנל של טאב השוק הכותרת יושבת ב-.ph של הפאנל (עם #mt-sub) — כאן רק הכפתורים
    return '<section class="mt" id="meter-timeline">' +
      (bare_ ? '<div class="mt-ctrl">' + seg + lg + "</div>"
        : '<div class="mt-head"><h3 class="section-title" style="margin:0">📈 The Edge Meter <small id="mt-sub"></small></h3>' + seg + "</div>" + lg) +
      '<figure class="mt-fig" id="mt-fig" tabindex="0" aria-label="ציר הזמן של ציון בריאות השוק ו-S&P 500. חצים ימינה ושמאלה לנוע בין ימים.">' +
        '<svg id="mt-svg" aria-hidden="true"></svg><div class="mt-tip" id="mt-tip"></div>' +
        "<figcaption>הציון המשולב (0–100) על רקע שלושת המצבים של המד — חיובי מ-66, זהיר 45–66, הגנתי מתחת. ▲ = יום מכירה רחבה. קו מקווקו = שינוי בנוסחת ציון האופציות (v5 ב-13.9.2026, v6 ב-18.9.2026): ערכים משני צדיו אינם ברי-השוואה ישירה. מתחת: S&amp;P 500 על אותו ציר זמן. ריחוף או חצי מקלדת מציגים את כל הערכים של אותו יום, כולל הכותרת שפורסמה בו.</figcaption>" +
      "</figure>" +
      '<details class="mt-tbl"><summary>הנתונים בטבלה</summary><table id="mt-table"></table></details></section>';
  }
  function renderMeterTimeline() {
    var fig = document.getElementById("mt-fig"), svg = document.getElementById("mt-svg"), tip = document.getElementById("mt-tip");
    if (!fig || !svg || !HIST || !(HIST.days || []).length) return;
    var rows = HIST.days.slice(-MT.range);
    var sell = {};
    (((INDD || {}).riskOff || {}).sellDaysMap || []).forEach(function (s) { if (s.isSell) sell[s.date] = 1; });
    var sub = document.getElementById("mt-sub");
    if (sub) sub.textContent = rows.length < MT.range ? "כל " + rows.length + " ימי המסחר במאגר" : MT.range + " ימי מסחר אחרונים";
    // הטאב עשוי להיות מוסתר בזמן הבנייה (רוחב 0) — ResizeObserver למטה מצייר שוב כשהוא נפתח
    var W = fig.clientWidth || 900, narrow = W < 560;
    var ML = narrow ? 34 : 44, MR = narrow ? 46 : 60, T = 10, HA = narrow ? 190 : 240, GAP = 44, HB = narrow ? 72 : 96, AX = 26;
    var H = T + HA + GAP + HB + AX;
    svg.setAttribute("viewBox", "0 0 " + W + " " + H); svg.setAttribute("width", W); svg.setAttribute("height", H);
    svg.innerHTML = "";
    var n = rows.length;
    function x(i) { return ML + (n < 2 ? 0 : (W - ML - MR) * i / (n - 1)); }
    function yA(v) { return T + HA - HA * v / 100; }
    var spx = rows.map(function (r) { return r.spx; }).filter(function (v) { return v != null; });
    var lo = Math.min.apply(null, spx), hi = Math.max.apply(null, spx), pad = (hi - lo) * 0.12 || 50; lo -= pad; hi += pad;
    function yB(v) { return T + HA + GAP + HB - HB * (v - lo) / (hi - lo); }
    var gb = svg.appendChild(mtEl("g", {}));
    var bands = [[66, 100, "--up", "חיובי"], [45, 66, "--warn", "זהיר"], [0, 45, "--down", "הגנתי"]];
    bands.forEach(function (b) {
      gb.appendChild(mtEl("rect", { x: ML, y: yA(b[1]), width: W - ML - MR, height: yA(b[0]) - yA(b[1]), fill: mtCss(b[2]), opacity: .07 }));
      var t = mtEl("text", { x: ML + 6, y: yA(b[1]) + 13, "font-size": 11, fill: mtCss("--text-3") }); t.textContent = b[3]; gb.appendChild(t);
    });
    [45, 66].forEach(function (v) { gb.appendChild(mtEl("line", { x1: ML, x2: W - MR, y1: yA(v), y2: yA(v), stroke: mtCss("--paper-hair"), "stroke-width": 1 })); });
    [0, 25, 50, 75, 100].forEach(function (v) {
      if (v !== 0 && v !== 100) gb.appendChild(mtEl("line", { x1: ML, x2: W - MR, y1: yA(v), y2: yA(v), stroke: mtCss("--paper-hair"), "stroke-width": 1, opacity: .55 }));
      var t = mtEl("text", { x: ML - 6, y: yA(v) + 4, "font-size": 11, "text-anchor": "end", fill: mtCss("--text-3") }); t.textContent = v; gb.appendChild(t);
    });
    var step = (hi - lo) > 400 ? 200 : 100, first = Math.ceil(lo / step) * step;
    for (var v = first; v < hi; v += step) {
      gb.appendChild(mtEl("line", { x1: ML, x2: W - MR, y1: yB(v), y2: yB(v), stroke: mtCss("--paper-hair"), "stroke-width": 1, opacity: .55 }));
      var tv = mtEl("text", { x: ML - 6, y: yB(v) + 4, "font-size": 11, "text-anchor": "end", fill: mtCss("--text-3") }); tv.textContent = v.toLocaleString("en-US"); gb.appendChild(tv);
    }
    var lb = mtEl("text", { x: ML, y: T + HA + GAP - 8, "font-size": 11, "font-weight": 600, fill: mtCss("--text-3") }); lb.textContent = "S&P 500"; gb.appendChild(lb);
    gb.appendChild(mtEl("line", { x1: ML, x2: W - MR, y1: T + HA + GAP + HB, y2: T + HA + GAP + HB, stroke: mtCss("--paper-hair") }));
    var every = Math.max(1, Math.round(n / (narrow ? 5 : 8)));
    rows.forEach(function (r, i) {
      if (i % every === 0 || i === n - 1) {
        var t = mtEl("text", { x: x(i), y: H - 8, "font-size": 11, "text-anchor": "middle", fill: mtCss("--text-3") }); t.textContent = mtD(r.date); gb.appendChild(t);
      }
      if (sell[r.date]) {
        var cx = x(i), cy = T + HA + 10;
        var p = mtEl("path", { d: "M" + (cx - 5) + "," + (cy + 8) + " L" + (cx + 5) + "," + (cy + 8) + " L" + cx + "," + cy + " Z", fill: mtCss("--down") });
        var tt = mtEl("title", {}); tt.textContent = "יום מכירה רחבה " + mtD(r.date); p.appendChild(tt); gb.appendChild(p);
      }
    });
    // 13.9.2026: קו "שינוי נוסחה" — היום הראשון שבו formulaVersion שונה מהיום שלפניו.
    // ההיסטוריה לא מחושבת מחדש (כלל הדשבורד), אז הקפיצה מסומנת במקום להיות מוסתרת.
    rows.forEach(function (r, i) {
      if (i === 0 || !r.formulaVersion || rows[i - 1].formulaVersion === r.formulaVersion) return;
      var mx = x(i);
      gb.appendChild(mtEl("line", { x1: mx, x2: mx, y1: T, y2: T + HA + GAP + HB, stroke: mtCss("--text-3"), "stroke-width": 1, "stroke-dasharray": "4 3", opacity: .8 }));
      var ml = mtEl("text", { x: mx - 5, y: T + 12, "font-size": 10, "text-anchor": "end", fill: mtCss("--text-3") });
      ml.textContent = "שינוי נוסחה " + r.formulaVersion; gb.appendChild(ml);
      var mt = mtEl("title", {}); mt.textContent = "מ-" + mtD(r.date) + " ציון האופציות מחושב לפי נוסחה " + r.formulaVersion + " (קודם " + (rows[i - 1].formulaVersion || "v4") + "). ערכים משני צדי הקו אינם ברי-השוואה ישירה."; ml.appendChild(mt);
    });
    function line(key, yf, color, w) {
      var d = rows.map(function (r, i) { return r[key] == null ? "" : ((i === 0 || rows[i - 1][key] == null ? "M" : "L") + x(i) + "," + yf(r[key])); }).join(" ");
      svg.appendChild(mtEl("path", { d: d, fill: "none", stroke: color, "stroke-width": w, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    }
    ["tech", "breadth", "flow"].forEach(function (k) { if (MT.show[k]) line(k, yA, mtCss("--mt-" + k), 1.5); });
    line("combined", yA, mtCss("--mt-comb"), 2);
    line("spx", yB, mtCss("--text-soft"), 2);
    var last = rows[n - 1], lx = x(n - 1);
    svg.appendChild(mtEl("circle", { cx: lx, cy: yA(last.combined), r: 4.5, fill: mtCss("--mt-comb"), stroke: mtCss("--bg"), "stroke-width": 2 }));
    var el1 = mtEl("text", { x: lx + 9, y: yA(last.combined) + 5, "font-size": 13, "font-weight": 700, fill: mtCss("--text") }); el1.textContent = last.combined; svg.appendChild(el1);
    if (last.spx != null) {
      svg.appendChild(mtEl("circle", { cx: lx, cy: yB(last.spx), r: 4, fill: mtCss("--text-soft"), stroke: mtCss("--bg"), "stroke-width": 2 }));
      var el2 = mtEl("text", { x: lx + 9, y: yB(last.spx) + 4, "font-size": 11, "font-weight": 600, fill: mtCss("--text") }); el2.textContent = Math.round(last.spx).toLocaleString("en-US"); svg.appendChild(el2);
    }
    var cross = mtEl("line", { x1: 0, x2: 0, y1: T, y2: T + HA + GAP + HB, stroke: mtCss("--text-soft"), "stroke-width": 1, opacity: 0 }); svg.appendChild(cross);
    var dot = mtEl("circle", { r: 5, fill: mtCss("--mt-comb"), stroke: mtCss("--bg"), "stroke-width": 2, opacity: 0 }); svg.appendChild(dot);
    var dot2 = mtEl("circle", { r: 4, fill: mtCss("--text-soft"), stroke: mtCss("--bg"), "stroke-width": 2, opacity: 0 }); svg.appendChild(dot2);
    var hit = mtEl("rect", { x: ML, y: T, width: W - ML - MR, height: HA + GAP + HB, fill: "transparent" }); svg.appendChild(hit);
    function nearest(px) { return Math.max(0, Math.min(n - 1, Math.round((px - ML) / ((W - ML - MR) / Math.max(1, n - 1))))); }
    function paint() {
      if (MT.hover < 0 || MT.hover >= n) { cross.setAttribute("opacity", 0); dot.setAttribute("opacity", 0); dot2.setAttribute("opacity", 0); tip.style.display = "none"; return; }
      var r = rows[MT.hover], cx = x(MT.hover);
      cross.setAttribute("x1", cx); cross.setAttribute("x2", cx); cross.setAttribute("opacity", .6);
      dot.setAttribute("cx", cx); dot.setAttribute("cy", yA(r.combined)); dot.setAttribute("opacity", 1);
      if (r.spx != null) { dot2.setAttribute("cx", cx); dot2.setAttribute("cy", yB(r.spx)); dot2.setAttribute("opacity", 1); } else dot2.setAttribute("opacity", 0);
      var w = meterWord(r.combined), dt = new Date(r.date + "T12:00:00");
      function row(nm, val, cv) { return '<div class="row"><span class="n"><i style="--c:' + cv + '"></i>' + nm + "</span><b>" + esc(val) + "</b></div>"; }
      tip.innerHTML = '<div class="d">יום ' + MT_DOW[dt.getDay()] + " · " + mtD(r.date) + "/" + r.date.slice(0, 4) + "</div>" +
        '<div class="big"><b>' + r.combined + '</b><span style="color:' + w[1] + '">' + w[0] + "</span></div>" +
        row("טכני", r.tech, "var(--mt-tech)") + row("רוחב", r.breadth, "var(--mt-breadth)") + row("אופציות", r.flow, "var(--mt-flow)") +
        (r.spx != null ? '<div class="row"><span class="n">S&amp;P 500</span><b>' + Math.round(r.spx).toLocaleString("en-US") + "</b></div>" : "") +
        (r.vix != null ? '<div class="row"><span class="n">VIX</span><b>' + esc(r.vix) + "</b></div>" : "") +
        (sell[r.date] ? '<div class="sell">▲ יום מכירה רחבה</div>' : "") +
        (r.formulaVersion && i > 0 && rows[i - 1].formulaVersion !== r.formulaVersion ? '<div class="sell" style="color:var(--text-soft)">┊ מכאן נוסחה ' + esc(r.formulaVersion) + "</div>" : "") +
        (r.headline ? '<div class="hl">' + esc(r.headline) + "</div>" : "");
      tip.style.display = "block";
      var fw = fig.clientWidth || W, tw = tip.offsetWidth, sx = cx * (fw / W);
      tip.style.left = Math.max(0, Math.min(fw - tw, sx > fw / 2 ? sx - tw - 16 : sx + 16)) + "px"; tip.style.top = "6px";
    }
    hit.addEventListener("pointermove", function (e) { var b = svg.getBoundingClientRect(); MT.hover = nearest((e.clientX - b.left) * W / b.width); paint(); });
    hit.addEventListener("pointerleave", function () { MT.hover = -1; paint(); });
    fig.onkeydown = function (e) {
      if (e.key === "ArrowLeft") { MT.hover = MT.hover < 0 ? n - 1 : Math.max(0, MT.hover - 1); paint(); e.preventDefault(); }
      else if (e.key === "ArrowRight") { MT.hover = MT.hover < 0 ? n - 1 : Math.min(n - 1, MT.hover + 1); paint(); e.preventDefault(); }
      else if (e.key === "Escape") { MT.hover = -1; paint(); }
    };
    paint();
    var tbl = document.getElementById("mt-table");
    if (tbl) tbl.innerHTML = "<tr><th>תאריך</th><th>משולב</th><th>טכני</th><th>רוחב</th><th>אופציות</th><th>S&amp;P 500</th><th>VIX</th><th>מכירה</th></tr>" +
      rows.slice().reverse().map(function (r) {
        return "<tr><td>" + mtD(r.date) + "/" + r.date.slice(2, 4) + '</td><td class="n">' + r.combined + '</td><td class="n">' + r.tech + '</td><td class="n">' + r.breadth + '</td><td class="n">' + r.flow +
          '</td><td class="n">' + (r.spx != null ? Math.round(r.spx).toLocaleString("en-US") : "—") + '</td><td class="n">' + (r.vix != null ? r.vix : "—") + "</td><td>" + (sell[r.date] ? "▲" : "") + "</td></tr>";
      }).join("");
  }
  function bindMeterTimeline(root) {
    root.querySelectorAll(".mt-seg button").forEach(function (b) {
      b.addEventListener("click", function () { MT.range = +b.dataset.r; MT.hover = -1;
        root.querySelectorAll(".mt-seg button").forEach(function (o) { o.setAttribute("aria-pressed", String(+o.dataset.r === MT.range)); }); renderMeterTimeline(); });
    });
    root.querySelectorAll(".mt-lg button").forEach(function (b) {
      b.addEventListener("click", function () { var k = b.dataset.s; MT.show[k] = !MT.show[k]; b.setAttribute("aria-pressed", String(MT.show[k])); renderMeterTimeline(); });
    });
    var fig = root.querySelector("#mt-fig");
    if (fig && window.ResizeObserver) {
      var lastW = 0;
      new ResizeObserver(function () { var w = fig.clientWidth; if (w && w !== lastW) { lastW = w; renderMeterTimeline(); } }).observe(fig);
    }
  }

  /* ---------- ציון האופציות (v6) מול המחיר (19.9.2026, בקשת איציק: "נראה אם יש הלימה") ----------
     שני פאנלים על ציר זמן משותף (לא ציר-Y כפול): למעלה הציון היומי מ-SPY (0–100, קו 50) והממוצע
     הדו-יומי שנכנס למד; למטה S&P 500. מתחת: סיכום ההלימה — מה עשה S&P ביום שאחרי ציון נמוך/גבוה,
     מחושב מהסדרה עצמה (d.flow.v6Series מ-send_report). ריחוף מציג את היום ואת מה שקרה למחרת. */
  function optVsPriceHtml(d) {
    var ser = ((d.flow || {}).v6Series || []).filter(function (r) { return r.score != null && r.spx != null; });
    if (ser.length < 8) return "";
    var lo = [], hi = [];
    for (var i = 0; i < ser.length - 1; i++) {
      var nx = (ser[i + 1].spx / ser[i].spx - 1) * 100;
      if (ser[i].score <= 33) lo.push(nx); else if (ser[i].score >= 67) hi.push(nx);
    }
    function avg(a) { return a.length ? a.reduce(function (x, y) { return x + y; }, 0) / a.length : null; }
    function ups(a) { return a.length ? Math.round(a.filter(function (v) { return v > 0; }).length / a.length * 100) : null; }
    function pc(v) { return (v > 0 ? "+" : "") + v.toFixed(2) + "%"; }
    var fit = (lo.length >= 3 && hi.length >= 3)
      ? "ביום שאחרי ציון נמוך (עד 33): S&P 500 <b class=\"num " + (avg(lo) < 0 ? "down" : "up") + "\" dir=\"ltr\">" + pc(avg(lo)) + "</b> בממוצע, עלה ב-" + ups(lo) + "% מהימים (" + lo.length + " ימים). " +
        "ביום שאחרי ציון גבוה (67 ומעלה): <b class=\"num " + (avg(hi) < 0 ? "down" : "up") + "\" dir=\"ltr\">" + pc(avg(hi)) + "</b>, עלה ב-" + ups(hi) + "% (" + hi.length + " ימים)."
      : "עדיין מעט מדי ימים בקצוות כדי לסכם הלימה.";
    return '<div class="section-title">📐 ציון האופציות מול המחיר <span class="np-k num" dir="ltr">' + ser.length + " ימים</span></div>" +
      '<div class="card"><figure class="mt-fig ovp-fig" id="ovp-fig"><svg id="ovp-svg" aria-hidden="true"></svg><div class="mt-tip" id="ovp-tip"></div>' +
      "<figcaption>למעלה: ציון האופציות היומי (v6, כיוון הכסף הגדול ב-SPY) והקו הדק = הממוצע הדו-יומי שנכנס למד. למטה: S&amp;P 500 על אותו ציר זמן. " + fit +
      " מדגם קטן — כיוון, לא הבטחה.</figcaption></figure></div>";
  }
  function renderOptVsPrice() {
    var fig = document.getElementById("ovp-fig"), svg = document.getElementById("ovp-svg"), tip = document.getElementById("ovp-tip");
    if (!fig || !svg || !INDD) return;
    var rows = ((INDD.flow || {}).v6Series || []).filter(function (r) { return r.score != null && r.spx != null; });
    if (rows.length < 8) return;
    var W = fig.clientWidth || 900, narrow = W < 560;
    var ML = narrow ? 30 : 40, MR = narrow ? 44 : 58, T = 10, HA = narrow ? 130 : 160, GAP = 40, HB = narrow ? 80 : 100, AX = 24;
    var H = T + HA + GAP + HB + AX, n = rows.length;
    svg.setAttribute("viewBox", "0 0 " + W + " " + H); svg.setAttribute("width", W); svg.setAttribute("height", H); svg.innerHTML = "";
    function x(i) { return ML + (W - ML - MR) * i / (n - 1); }
    function yA(v) { return T + HA - HA * v / 100; }
    var px = rows.map(function (r) { return r.spx; }), lo = Math.min.apply(null, px), hi = Math.max.apply(null, px), pad = (hi - lo) * 0.12 || 40; lo -= pad; hi += pad;
    function yB(v) { return T + HA + GAP + HB - HB * (v - lo) / (hi - lo); }
    var g = svg.appendChild(mtEl("g", {}));
    g.appendChild(mtEl("rect", { x: ML, y: yA(100), width: W - ML - MR, height: yA(67) - yA(100), fill: mtCss("--up"), opacity: .06 }));
    g.appendChild(mtEl("rect", { x: ML, y: yA(33), width: W - ML - MR, height: yA(0) - yA(33), fill: mtCss("--down"), opacity: .06 }));
    [0, 33, 50, 67, 100].forEach(function (v) {
      g.appendChild(mtEl("line", { x1: ML, x2: W - MR, y1: yA(v), y2: yA(v), stroke: mtCss("--paper-hair"), "stroke-width": 1, "stroke-dasharray": v === 50 ? "4 3" : "", opacity: v === 50 ? 1 : .6 }));
      var t = mtEl("text", { x: ML - 6, y: yA(v) + 4, "font-size": 11, "text-anchor": "end", fill: mtCss("--text-3") }); t.textContent = v; g.appendChild(t);
    });
    var la = mtEl("text", { x: ML, y: T + 12, "font-size": 11, "font-weight": 600, fill: mtCss("--text-3") }); la.textContent = "ציון אופציות"; g.appendChild(la);
    var step = (hi - lo) > 400 ? 200 : 100, first = Math.ceil(lo / step) * step;
    for (var v = first; v < hi; v += step) {
      g.appendChild(mtEl("line", { x1: ML, x2: W - MR, y1: yB(v), y2: yB(v), stroke: mtCss("--paper-hair"), "stroke-width": 1, opacity: .6 }));
      var tv = mtEl("text", { x: ML - 6, y: yB(v) + 4, "font-size": 11, "text-anchor": "end", fill: mtCss("--text-3") }); tv.textContent = v.toLocaleString("en-US"); g.appendChild(tv);
    }
    var lb = mtEl("text", { x: ML, y: T + HA + GAP - 8, "font-size": 11, "font-weight": 600, fill: mtCss("--text-3") }); lb.textContent = "S&P 500"; g.appendChild(lb);
    var every = Math.max(1, Math.round(n / (narrow ? 5 : 8)));
    rows.forEach(function (r, i) { if (i % every === 0 || i === n - 1) { var t = mtEl("text", { x: x(i), y: H - 6, "font-size": 11, "text-anchor": "middle", fill: mtCss("--text-3") }); t.textContent = mtD(r.date); g.appendChild(t); } });
    function path(key, yf) { return rows.map(function (r, i) { return (i ? "L" : "M") + x(i) + "," + yf(r[key]); }).join(" "); }
    svg.appendChild(mtEl("path", { d: path("meter", yA), fill: "none", stroke: mtCss("--text-3"), "stroke-width": 1.2, "stroke-linejoin": "round" }));
    svg.appendChild(mtEl("path", { d: path("score", yA), fill: "none", stroke: mtCss("--mt-flow"), "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    rows.forEach(function (r, i) { svg.appendChild(mtEl("circle", { cx: x(i), cy: yA(r.score), r: narrow ? 2 : 2.6, fill: mtCss("--mt-flow"), stroke: mtCss("--bg"), "stroke-width": 1 })); });
    svg.appendChild(mtEl("path", { d: path("spx", yB), fill: "none", stroke: mtCss("--text-soft"), "stroke-width": 2, "stroke-linejoin": "round" }));
    var last = rows[n - 1];
    var e1 = mtEl("text", { x: x(n - 1) + 8, y: yA(last.score) + 4, "font-size": 12, "font-weight": 700, fill: mtCss("--text") }); e1.textContent = last.score; svg.appendChild(e1);
    var e2 = mtEl("text", { x: x(n - 1) + 8, y: yB(last.spx) + 4, "font-size": 11, "font-weight": 600, fill: mtCss("--text") }); e2.textContent = Math.round(last.spx).toLocaleString("en-US"); svg.appendChild(e2);
    var cross = mtEl("line", { y1: T, y2: T + HA + GAP + HB, stroke: mtCss("--text-3"), "stroke-width": 1, opacity: 0 }); svg.appendChild(cross);
    function show(i) {
      var r = rows[i], nx = i < n - 1 ? (rows[i + 1].spx / r.spx - 1) * 100 : null;
      cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.setAttribute("opacity", .7);
      tip.innerHTML = '<div class="d">' + mtD(r.date) + "</div>" +
        '<div>ציון אופציות: <b class="num">' + r.score + "</b>" + (r.meter != null ? ' · במד: <b class="num">' + r.meter + "</b>" : "") + "</div>" +
        '<div>S&amp;P 500: <b class="num" dir="ltr">' + Math.round(r.spx).toLocaleString("en-US") + "</b></div>" +
        (nx != null ? '<div>ביום שאחרי: <b class="num ' + (nx < 0 ? "down" : "up") + '" dir="ltr">' + (nx > 0 ? "+" : "") + nx.toFixed(2) + "%</b></div>" : '<div class="soft">היום שאחרי עוד לא נסחר</div>');
      tip.style.display = "block";
      var tx = x(i) + 12; if (tx + 210 > W) tx = x(i) - 210; tip.style.left = Math.max(4, tx) + "px"; tip.style.top = "14px";
    }
    function hide() { tip.style.display = "none"; cross.setAttribute("opacity", 0); }
    var hit = mtEl("rect", { x: ML, y: T, width: W - ML - MR, height: HA + GAP + HB, fill: "transparent" }); svg.appendChild(hit);
    function at(ev) { var b = svg.getBoundingClientRect(), cx = ((ev.touches ? ev.touches[0].clientX : ev.clientX) - b.left) * (W / b.width); return Math.max(0, Math.min(n - 1, Math.round((cx - ML) / ((W - ML - MR) / (n - 1))))); }
    hit.addEventListener("mousemove", function (ev) { show(at(ev)); }); hit.addEventListener("mouseleave", hide);
    hit.addEventListener("touchstart", function (ev) { show(at(ev)); }, { passive: true }); hit.addEventListener("touchmove", function (ev) { show(at(ev)); }, { passive: true });
    if (window.ResizeObserver && !fig.__ro) { fig.__ro = true; var lw = W; new ResizeObserver(function () { var w = fig.clientWidth; if (w && w !== lw) { lw = w; renderOptVsPrice(); } }).observe(fig); }
  }

  // "הכסף הגדול היום במניות" (13.9.2026) — d.bigTrades מ-indexes-status/data/big_trades.json:
  // 5 הפוזיציות הגדולות במניות בודדות מתוך 500 העסקאות הגדולות של היום, אחרי איחוד
  // הדפסות, השמטת 0DTE וסימון תחליפי-מניה (דלתא ~1) כ"לא כיווני". תיאור, לא ציון.
  function bigTradesHtml(d) {
    var b = d.bigTrades;
    if (!b || !b.items || !b.items.length) return "";
    var KIND_CLS = { "new": "bt-new", "roll": "bt-roll", "synthetic": "bt-syn", "combo": "bt-combo", "flow": "bt-flow" };
    function dirHtml(it) {
      if (it.direction === "up") return '<span class="bt-dir up">▲ למעלה</span>';
      if (it.direction === "down") return '<span class="bt-dir down">▼ למטה</span>';
      if (it.direction === "flat") return '<span class="bt-dir">◆ מאוזן</span>';
      return '<span class="bt-dir soft">◇ לא כיווני</span>';
    }
    function money(v) { return v >= 1e9 ? (v / 1e9).toFixed(1) + "B" : Math.round(v / 1e6) + "M"; }
    return '<div class="section-title">💰 הכסף הגדול היום במניות <span class="np-k num" dir="ltr">' + esc(b.label || "") + "</span></div>" +
      '<div class="card bt-card">' +
      (function () {   // שורת הסנטימנט של המניות (UOA) — תצוגה בלבד, לא נכנסת לציון (v6)
        var sl = (((d.flow || {}).research || {}).lines || []).filter(function (l) { return l.display === "bigtrades"; })[0];
        return sl ? '<p class="bt-sent"><b>סנטימנט במניות:</b> ' + esc(sl.text) + ' <span class="soft">לתצוגה בלבד, לא נכנס לציון האופציות.</span></p>' : "";
      })() +
      '<div class="bt-list">' + b.items.map(function (it) {
        return '<div class="bt-row">' +
          '<div class="bt-head"><b class="bt-tk num" dir="ltr">' + esc(it.ticker) + "</b>" +
          '<span class="bt-pm num" dir="ltr">$' + money(it.premium) + "</span>" +
          '<span class="bt-kind ' + (KIND_CLS[it.kind] || "") + '">' + esc(it.kindHe || "") + "</span>" +
          dirHtml(it) + "</div>" +
          '<div class="bt-txt">' + esc(it.text || "") + "</div>" +
          "</div>";
      }).join("") + "</div>" +
      '<p class="stamp" style="margin-bottom:0">' + esc(b.note || "") + ' · "תחליף מניה" = אופציות עמוקות בכסף (דלתא ~1) שמתנהגות כמו המניה — קרן שמחליפה מניות באופציות, לא הימור. ' +
      'סה"כ ' + esc(String(b.symbols || "")) + ' מניות בקובץ · מקור: Barchart Options Flow.</p>' +
      "</div>";
  }


  /* ---------- כמה מניות משתתפות בשיא? (np114, 7.10.2026, איציק — אושר במוקאפ) ----------
     שורה לכל שיא בעבר: אחוז מניות ה-S&P מעל ממוצע 200 ביום השיא, התחתית בשנה שאחריו ואיפה המדד
     היה שנה אחרי. נתוני העבר קבועים — מחושבים פעם אחת מנרות 2005–2026 (scripts/tools/probe_breadth_history.py,
     חברות המדד של היום). שורת "היום" = evidence.pctMa200 מהדשבורד; המרחק מהשיא = vixLight.spxOffHigh. */
  var BP_ROWS = [
    { when: "ינואר 2022", p: 76, low: -25.4, lowAt: "אוקטובר 2022", y1: -19.7 },
    { when: "דצמבר 2024", p: 60, low: -17.5, lowAt: "אפריל 2025", y1: 14.3 },
    { when: "יולי 2015", p: 59, low: -13.7, lowAt: "פברואר 2016", y1: 2.5 },
    { when: "יוני 2023", p: 52, low: -3.9, lowAt: "אוקטובר 2023", y1: 23.6 },
    { when: "יוני 2025", p: 48, low: 0, lowAt: "", y1: 20.8 }
  ];
  function breadthPeaksHtml(d) {
    var e = (d && d.evidence) || {}, p = e.pctMa200;
    if (p == null) return "";
    p = Math.round(p);
    var off = TICKD && TICKD.vixLight && TICKD.vixLight.spxOffHigh != null ? +TICKD.vixLight.spxOffHigh : null;
    function sg(v) { return (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(1) + "%"; }
    function row(r, today) {
      var low = today ? '<span class="bp-res bp-low bp-q">?</span>' : (r.low <= -1
        ? '<span class="bp-res bp-low ' + (r.low <= -10 ? "dn" : "mild") + '"><i>תחתית </i><b dir="ltr">' + sg(r.low) + "</b><small>" + r.lowAt + "</small></span>"
        : '<span class="bp-res bp-low up"><i>תחתית: </i><b>לא ירד</b></span>');
      var y1 = today ? '<span class="bp-res bp-y1 bp-q">?</span>' : '<span class="bp-res bp-y1 ' + (r.y1 >= 0 ? "up" : "dn") + '"><i>שנה אחרי </i><b dir="ltr">' + sg(r.y1) + "</b></span>";
      return '<div class="bp-row' + (today ? " today" : "") + '"><span class="bp-when">' + r.when + "</span>" +
        '<div class="bp-barw"><div class="bp-bar" style="width:' + r.p + '%"></div><span class="bp-pct" style="right:' + r.p + '%">' + r.p + "%</span></div>" + low + y1 + "</div>";
    }
    var n10 = Math.round(p / 10), minPast = Math.min.apply(null, BP_ROWS.map(function (r) { return r.p; }));
    var where = off == null ? "בשיא" : off > -1 ? "בשיא" : off > -3 ? "ליד השיא" : null;
    var title = !where ? "המדד " + Math.abs(off).toFixed(1) + "% מתחת לשיא, ו-" + n10 + " מכל 10 מניות במגמת עלייה"
      : p >= 65 ? "הרוחב התרחב: " + n10 + " מכל 10 מניות במגמת עלייה, והמדד " + where
      : "המדד " + where + ", אבל רק " + n10 + " מכל 10 מניות במגמת עלייה" + (p < minPast ? ", פחות מבכל שיא קודם" : "");
    return '<section class="bp" id="breadth-peaks"><div class="bp-k">כמה מניות משתתפות בשיא?</div>' +
      '<h3 class="bp-title">' + esc(title) + "</h3>" +
      '<p class="bp-sub">אחוז מניות ה-S&amp;P 500 שמעל ממוצע 200 יום, ביום שבו המדד היה בשיא · כמה המדד ירד מהשיא עד התחתית בשנה שאחרי · ואיפה הוא היה שנה אחרי</p>' +
      '<div class="bp-rows"><div class="bp-row bp-hdr"><span></span><span>מניות במגמת עלייה ביום השיא</span><span>התחתית בשנה שאחרי</span><span>שנה אחרי השיא</span></div>' +
        row({ when: "היום", p: p }, true) + '<div class="bp-sep"></div>' + BP_ROWS.map(function (r) { return row(r); }).join("") + "</div>" +
      '<p class="bp-take"><b>הלקח:</b> גם שיא רחב (ינואר 2022) נגמר בירידה, וגם שיאים צרים (2023, 2025) המשיכו לעלות. מה שהכריע הוא החודש שאחרי: אם תוך כחודש עוד מניות הצטרפו והאחוז קפץ מעל 65%, השוק המשיך לעלות. אם לא, הגיע תיקון.</p>' +
      '<p class="stamp">נכון לסגירת <span dir="ltr">' + esc(fmtTradeDate(d.date)) + "</span> · התחתית = הנקודה הנמוכה ביותר של המדד בשנה שאחרי השיא, באחוזים מהשיא. נתוני העבר: חישוב על חברות המדד של היום מנרות 2005–2026 (חברות שיצאו מהמדד חסרות, ולכן העבר נראה מעט טוב יותר).</p></section>";
  }
  function renderBreadthPeaks() { var el = document.getElementById("bp-slot"); if (el && INDD) el.innerHTML = bpPan(INDD); }

  function renderIndicesDetail(el, d) {
    // np120 (עיצוב מחדש שלב 6 חלק 2): טאב השוק כרשת פאנלים לפי מוקאפ שלב 5 —
    // המד | ציר הזמן → הניתוח היומי → סיכום השבוע | הצפי → ההימור נטו | הכסף הגדול →
    // הרוחב בשיא | מנוע המסקנות → ניתוח לפי תחום | תמונת מצב → ציון האופציות מול המחיר →
    // רוטציה | לחץ מכירות | רקע → "איך זה עובד". שום תוכן לא ירד — רק הלבשה וסדר.
    var c = d.conclusion || {}, rot = d.rotation || {}, ro = d.riskOff || {}, e = d.evidence || {}, s = d.scores || {}, fl = d.flow || {}, v = d.verdict || {}, nrt = d.narrative || {};
    var sd = (ro.sellingDays || []).length, mAbove = null;
    (c.analysis || []).forEach(function (a) { var m = /מעל MA200 כבר (\d+)/.exec(a.text || ""); if (m) mAbove = +m[1]; });
    var tiles = '<div class="tiles">' +
      bdTile("ימי מכירה ב-" + ((ro.sellDaysMap || []).length || 25) + " הימים", sd, ro.active ? "לחץ מכירות פעיל" : "", sd >= 4 ? "down" : "") +
      (mAbove != null ? bdTile("S&amp;P מעל ממוצע 200", mAbove + ' <small>ימים</small>') : bdTile("VIX", fmtNum(e.vix, 1), e.vix != null && e.vix < 20 ? "רגוע" : "מוגבר")) +
      bdTile("מניות מעל ממוצע 200", e.pctMa200 != null ? Math.round(e.pctMa200) + "%" : "—", e.pctMa50 != null ? Math.round(e.pctMa50) + "% מעל ממוצע 50" : "") +
      '<div class="tile"><div class="l">שיאים / שפלים 52ש׳</div><div class="v num" dir="ltr"><span class="up">' + fmtNum(e.nhCount) + '</span>/<span class="down">' + fmtNum(e.nlCount) + "</span></div></div></div>";
    var TONE = { pos: "up", neg: "down", warn: "warn" };
    var conclRows = (c.analysis || []).map(function (a) {
      return '<div class="sent"><b><i class="dot ' + (TONE[a.tone] || "") + '"></i>' + esc(a.domain) + "</b><span>" + esc(a.text) + "</span></div>";
    }).join("");
    var r = c.recommendation || {};
    var concl = (c.conclusion ? '<p class="bd-concl">📌 ' + esc(c.conclusion) + "</p>" : "") +
      (r.action ? '<div class="bd-reco"><p><b>מה עושים:</b> ' + esc(r.action) + "</p>" + (r.improve ? "<p><b>ישתפר אם:</b> " + esc(r.improve) + "</p>" : "") + (r.worsen ? "<p><b>יורע אם:</b> " + esc(r.worsen) + "</p>" : "") + "</div>" : "");
    var lightsMap = { trend: "מגמה", breadth: "רוחב", volatility: "תנודתיות", rotation: "רוטציה" };
    var lights = v.lights ? '<div class="lights">' + Object.keys(lightsMap).map(function (k) { return '<span class="light ' + esc(v.lights[k] || "") + '"><span class="dot"></span>' + lightsMap[k] + "</span>"; }).join("") + "</div>" : "";
    var scoreTiles = [["combined", "ציון משולב"], ["tech", "טכני"], ["breadth", "רוחב"], ["flow", "אופציות"]].map(function (p) {
      return '<div class="tile"><div class="l">' + p[1] + '</div><div class="v num ' + scoreBand(s[p[0]]) + '">' + (s[p[0]] == null ? "—" : s[p[0]]) + diffTag(p[0]) + "</div>" +
        (p[0] === "flow" && fl.deltaLabel ? '<div class="s mute">הכסף הגדול: <b class="' + (fl.deltaLabel === "דובי" ? "down" : fl.deltaLabel === "שורי" ? "up" : "") + '">' + esc(fl.deltaLabel) + "</b>" + (fl.meterScore != null ? ' · במד <span class="num">' + fl.meterScore + "</span>" : "") + "</div>" : "") + "</div>";
    }).join("");
    var mktTiles = bdTile("S&amp;P 500", fmtNum(e.spxPrice, 2), e.pctMa200 != null ? e.pctMa200 + "% מעל MA200" : "") +
      bdTile("VIX", fmtNum(e.vix, 1), e.vix != null && e.vix < 20 ? "רגוע" : "מוגבר") +
      bdTile("מניות מעל ממוצע 50", e.pctMa50 != null ? Math.round(e.pctMa50) + "%" : "—", "רוחב") +
      bdTile("EQ מול SPX 20י", e.eqSpx20 != null ? (e.eqSpx20 > 0 ? "+" : "") + e.eqSpx20 + "%" : "—", "רוחב פנימי");
    var verdict = (v.headline ? '<p class="bd-vh">' + h(v.emoji || "📊") + " " + esc(v.headline) + "</p>" : "") + (v.subline ? '<p class="mute" style="margin:0">' + esc(v.subline) + "</p>" : "") + lights;
    var backg = (nrt.today ? "<p><b>היום:</b> " + esc(nrt.today) + "</p>" : "") + (nrt.week ? "<p><b>השבוע:</b> " + esc(nrt.week) + "</p>" : "") + (nrt.watchFor ? "<p><b>לעקוב:</b> " + esc(nrt.watchFor) + "</p>" : "");
    var sectors = "";
    if (rot.sectorRs) {
      var lead = rot.leadingSectors || [];
      sectors = '<div class="chips">' + Object.keys(rot.sectorRs).sort(function (a, b) { return (rot.sectorRs[b].rs20 || 0) - (rot.sectorRs[a].rs20 || 0); }).map(function (k) {
        return '<span class="chip' + (lead.indexOf(k) !== -1 ? " lead" : "") + '">' + esc(SECTOR_HE[k] || k) + ' <span class="num ' + ((rot.sectorRs[k].rs20 || 0) >= 0 ? "up" : "down") + '">' + (rot.sectorRs[k].rs20 > 0 ? "+" : "") + rot.sectorRs[k].rs20 + "%</span></span>";
      }).join("") + "</div>";
    }
    var selling = "";
    if (ro.sellingDays && ro.sellingDays.length) {
      selling = '<p style="margin:0">' + esc(ro.stateLine || "") + "</p>" +
        '<div class="tbl"><table class="bd-tbl"><thead><tr><th>תאריך</th><th>שינוי %</th></tr></thead><tbody>' +
        ro.sellingDays.map(function (day) { return '<tr><td class="num" dir="ltr">' + esc(day.date) + '</td><td class="num down" dir="ltr">' + day.chg + "%</td></tr>"; }).join("") + "</tbody></table></div>" +
        (ro.actionLine ? '<p class="stamp" style="margin:0">' + esc(ro.actionLine) + "</p>" : "");
    }
    var ai = aiBlocksHtml(d), flowQ = flowQuadHtml(d), ovp = optVsPriceHtml(d), big = bigTradesHtml(d), ca = claudeCardHtml(d), bt = d.bigTrades || {};
    var flowPill = s.flow != null ? '<span class="pill' + (fl.spxWarning && fl.spxWarning.active ? " state" : "") + '">ציון <span class="num">' + s.flow + "</span>" + (fl.spxWarning && fl.spxWarning.active ? " · אזהרת SPX" : "") + "</span>" : "";
    var tradeDate = fmtTradeDate(d.date);
    el.innerHTML = stamp(d._meta) + '<div class="board">' +
      '<section class="pan bd-meter" id="ind-meter"' + bdSpan(4) + ">" + leadRailHtml(d, "-i") + "</section>" +
      '<section class="pan"' + bdSpan(8) + ">" + panHd("ציר הזמן של The Edge Meter", '<span class="mute" id="mt-sub"></span>') + '<div class="pb">' + meterTimelineHtml(true) + tiles + "</div></section>" +
      (ca ? '<section class="pan"' + bdSpan(12) + ">" + panHd("הניתוח היומי", tradeDate ? '<span class="mute">יום המסחר <span class="num" dir="ltr">' + esc(tradeDate) + "</span></span>" : "") + '<div class="pb bd-ca">' + bare(ca) + "</div></section>" : "") +
      '<section class="pan" id="weekly-slot"' + bdSpan(6) + "></section>" +
      '<section class="pan" id="fc-pan"' + bdSpan(6) + "></section>" +
      (flowQ ? '<section class="pan"' + bdSpan(6) + ">" + panHd("ההימור נטו · אופציות" + (bt.label ? ' · <span class="num" dir="ltr">' + esc(bt.label) + "</span>" : ""), flowPill) + '<div class="pb bd-flow">' + bare(flowQ) + "</div></section>" : "") +
      (big ? '<section class="pan"' + bdSpan(6) + ">" + panHd("הכסף הגדול היום במניות", '<span class="mute">' + (bt.prints ? '<span class="num">' + esc(String(bt.prints)) + "</span> העסקאות הגדולות · " : "") + '<span class="num">' + esc(String(bt.symbols || "")) + "</span> מניות</span>") + '<div class="pb">' + bare(big) + "</div></section>" : "") +
      '<section class="pan" id="bp-slot"' + bdSpan(7) + ">" + bpPan(d) + "</section>" +
      (conclRows || concl ? '<section class="pan"' + bdSpan(5) + ">" + panHd("מנוע המסקנות", '<span class="mute">' + esc(c.headline || "") + "</span>") + '<div class="pb bd-sents">' + conclRows + concl + "</div></section>" : "") +
      (ai ? '<section class="pan"' + bdSpan(6) + ">" + panHd("ניתוח לפי תחום", '<span class="mute">מנוע הכללים</span>') + '<div class="pb">' + bare(ai) + "</div></section>" : "") +
      '<section class="pan"' + bdSpan(ai ? 6 : 12) + ">" + panHd("תמונת מצב", tradeDate ? '<span class="mute">יום המסחר <span class="num" dir="ltr">' + esc(tradeDate) + "</span></span>" : "") +
        '<div class="pb">' + verdict + '<div class="tiles">' + scoreTiles + '</div><div class="tiles">' + mktTiles + "</div>" + (backg ? '<div class="bd-backg">' + backg + "</div>" : "") + "</div></section>" +
      (ovp ? '<section class="pan"' + bdSpan(12) + ">" + panHd("ציון האופציות מול המחיר", '<span class="mute num" dir="ltr">' + ((fl.v6Series || []).length) + " ימים</span>") + '<div class="pb">' + bare(ovp) + "</div></section>" : "") +
      (sectors ? '<section class="pan"' + bdSpan(selling ? 6 : 12) + ">" + panHd("רוטציה סקטוריאלית", '<span class="mute">כוח יחסי 20 יום מול S&amp;P</span>', '<a class="go" href="#sectors" onclick="__goTab(\'sectors\');return false">גלגל הרוטציה</a>') + '<div class="pb">' + sectors + "</div></section>" : "") +
      (selling ? '<section class="pan"' + bdSpan(sectors ? 6 : 12) + ">" + panHd("לחץ מכירות מוסדי", '<span class="mute">' + esc(ro.evidenceLine || "") + "</span>") + '<div class="pb">' + selling + "</div></section>" : "") +
      '<section class="pan"' + bdSpan(12) + '><details class="bd-exp"><summary>איך זה עובד</summary>' + INDICES_EXPLAINER + "</details>" +
        '<p class="stamp" style="margin:0 14px 12px">מקור: <a href="https://nditzik.github.io/indexes-status/" target="_blank" rel="noopener">דשבורד המדדים המלא ↗</a></p></section>' +
      "</div>";
    bindMeterTimeline(el); renderMeterTimeline(); renderSpark("-i");
    setTimeout(renderOptVsPrice, 0);   // ה-figure של הגרף נכנס ל-DOM רק בהמשך הפונקציה
    if (WEEKLY) renderWeekly(WEEKLY);
    renderForecastPan();
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
    var pool = d.stocks.filter(function (x) { return x.symbol && !/\s/.test(x.symbol) && passesBase(x); });   // שורת "Downloaded from Barchart" בקובץ אינה מניה
    var base = pool.filter(function (x) { return x.signal_count >= 2; });   // הקטגוריות הקיימות — 2+ סיגנלים; המועמדות — גם סיגנל אחד
    var byAlpha = function (a, b) { return (b.wtd_alpha || 0) - (a.wtd_alpha || 0); };
    var cats = [
      { key: "s4", emoji: "🔥", title: "4 סיגנלים", rows: base.filter(function (x) { return x.signal_count >= 4; }).sort(byAlpha) },
      { key: "s3", emoji: "⚡", title: "3 סיגנלים", rows: base.filter(function (x) { return x.signal_count === 3; }).sort(byAlpha) },
      { key: "s2", emoji: "✨", title: "2 סיגנלים", rows: base.filter(function (x) { return x.signal_count === 2; }).sort(byAlpha) },
      { key: "dip", emoji: "📉", title: "כניסת דיפ", rows: base.filter(isDipEntry).sort(byAlpha) },
      { key: "brk", emoji: "🚀", title: "כניסת פריצה", rows: base.filter(isBreakoutEntry).sort(byAlpha) },
      { key: "rev", emoji: "🔄", title: "מניות בהיפוך", rows: base.filter(isReversalEntry).sort(byAlpha) },
      // "מועמדים" (12.9.2026, בקשת איציק): כמו "מועמדות לטרייד" בדשבורד המומנטום —
      // Readiness ≥ 50 (מחושב ב-fetch_momentum.py, פורט של calcReadiness), עם ציון
      // קבצי ה-CSV שמהם כל מניה הגיעה (d._meta.files).
      { key: "cand", emoji: "🎯", title: "מועמדים", cand: true,
        rows: pool.filter(function (x) { return (x.readiness || 0) >= 50; }).sort(function (a, b) { return (b.readiness - a.readiness) || ((b.wtd_alpha || 0) - (a.wtd_alpha || 0)); }).slice(0, 12) }   // 12 המובילות — כמו בדשבורד
    ];
    var firstNon = 0;
    for (var i = 0; i < cats.length; i++) { if (cats[i].rows.length) { firstNon = i; break; } }

    // שלב 7 (10.10.2026): הקטגוריות כצ'יפים בראש פאנל הטבלה (כמו לשוניות-משנה), בלי אמוג'י
    var nav = '<div class="chips bd-chips mom-nav">' + cats.map(function (c, i) {
      return '<button type="button" class="tag mom-tab' + (i === firstNon ? " on" : "") + '" data-mom="' + i + '" aria-pressed="' + (i === firstNon) + '">' +
        esc(c.title) + ' <b class="num">' + c.rows.length + "</b></button>";
    }).join("") + "</div>";
    var MOM_SUB = {
      s4: "מניות שמופיעות בארבעה סורקים", s3: "מניות שמופיעות בשלושה סורקים", s2: "מניות שמופיעות בשני סורקים",
      dip: "קרובות לממוצע 20 או 50 אחרי תיקון", brk: "מעל ממוצע 20, עלייה עם נפח גבוה", rev: "חזרו אל מעל ממוצע 20 או 50",
      cand: "Readiness 50 ומעלה — 12 המובילות"
    };

    var panels = cats.map(function (c, i) {
      var body;
      if (!c.rows.length) {
        body = '<div class="pb mute">אין מניות בקטגוריה זו היום.</div>';
      } else if (c.cand) {
        var files = (d._meta && d._meta.files) || {};
        function srcChips(sigs) {
          return (sigs || []).map(function (k) {
            var fn = files[k] || "";
            // שם הקובץ בלי התאריך (משותף לכולם — מופיע פעם אחת בכותרת) ובלי הסיומת
            var stem = fn.replace(/-\d{2}-\d{2}-\d{4}\.csv$/, "");
            return '<span class="src-chip" title="' + esc(fn || SIG_LABEL[k] || k) + '">' + esc(SIG_LABEL[k] || k) + (stem ? ' <span class="src-file" dir="ltr">' + esc(stem) + "</span>" : "") + "</span>";
          }).join("");
        }
        var crows = c.rows.map(function (r) {
          var rd = r.readiness || 0, ma50 = +r.ma50 || 0, px = +r.price || 0;
          var dist = (ma50 > 0 && px > 0) ? (px - ma50) / ma50 * 100 : null;
          return "<tr>" +
            '<td class="num"><span class="rdy ' + (rd >= 70 ? "rdy-hi" : "rdy-mid") + '" title="Readiness ' + rd + '/100 — כמו בדשבורד, כולל מגמת היסטוריה מ-' + ((d._meta && d._meta.histDays) || 0) + ' סנאפשוטים">' + (rd >= 70 ? "🟢" : "🟡") + " " + rd + "</span></td>" +
            "<td>" + tvLink(r.symbol) + erBadge(r.symbol) + "</td>" +
            '<td class="mom-name">' + esc(r.name) + "</td>" +
            '<td class="num">' + fmt(r.price) + "</td>" +
            "<td>" + pct(r.change_pct) + "</td>" +
            '<td class="num">' + fmt(r.rel_str, 0) + "</td>" +
            '<td class="num">' + fmt(r.stoch, 0) + "</td>" +
            '<td class="num">' + fmt(r.rvol) + "</td>" +
            '<td class="num">' + (dist == null ? "—" : '<span dir="ltr">' + (dist >= 0 ? "+" : "") + dist.toFixed(1) + "%</span>") + "</td>" +
            '<td class="sig-cell src-cell">' + srcChips(r.signals) + "</td></tr>";
        }).join("");
        body = '<p class="stamp mom-note">כמו "מועמדות לטרייד" בדשבורד המומנטום: 12 המובילות עם Readiness ≥ 50 (RSI/Stoch בריאים, קרבה ל-MA50, נפח יחסי, סיגנלים, נר ירוק) · 🟢 70+ מוכנה · 🟡 50–69 מתקרבת · העמודה האחרונה: הסורקים (קבצי Barchart) שמהם המניה הגיעה</p>' +
          '<div class="tbl"><table class="bd-tbl"><thead><tr>' +
          '<th class="num">Readiness</th><th>סימבול</th><th>שם</th><th class="num">מחיר</th><th class="num">שינוי</th><th class="num">RSI</th><th class="num">Stoch</th><th class="num">RVOL</th><th class="num">מ-MA50</th><th>מקור (קבצים)</th>' +
          "</tr></thead><tbody>" + crows + "</tbody></table></div>";
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
        body = '<div class="tbl"><table class="bd-tbl"><thead><tr>' +
          '<th class="num">#</th><th>סימבול</th><th>שם</th><th class="num">מחיר</th>' +
          '<th class="num">שינוי</th><th class="num">RSI</th><th class="num">Stoch</th>' +
          '<th class="num">RVOL</th><th>סיגנלים</th>' +
          "</tr></thead><tbody>" + rows + "</tbody></table></div>";
      }
      return '<div class="mom-list" data-mom="' + i + '" style="display:' + (i === firstNon ? "block" : "none") + '">' + body + "</div>";
    }).join("");

    // שלב 7 (10.10.2026): פאנל ראשי (תאריך הסורקים + 4 אריחים) · פאנל הטבלה (צ'יפים + טבלה) · "איך זה עובד" מקופל
    var fdate = (function () { var f = (d._meta && d._meta.files) || {}, k = Object.keys(f)[0], m = k && /(\d{2})-(\d{2})-(\d{4})\.csv$/.exec(f[k]); return m ? (+m[2]) + "." + (+m[1]) : ""; })();
    var upd = d._meta && d._meta.updatedAt ? /(\d{1,2}:\d{2})/.exec(d._meta.updatedAt) : null;
    var nCand = cats[6].rows.length, n4 = cats[0].rows.length, n3 = cats[1].rows.length, n2 = cats[2].rows.length;
    function catHd(c) { return panHd(esc(c.title), '<span class="mute"><span class="num">' + c.rows.length + "</span> מניות · " + esc(MOM_SUB[c.key] || "") + "</span>"); }
    el.innerHTML = '<div class="board">' +
      '<section class="pan"' + bdSpan(12) + ">" +
        panHd("סורק מומנטום" + (fdate ? ' · סורקי <span class="num" dir="ltr">' + fdate + "</span>" : ""),
          '<span class="mute"><span class="num">' + base.length + "</span> מניות איכות, 2 סיגנלים ומעלה אחרי פילטר הבסיס" + (upd ? ' · עודכן <span class="num" dir="ltr">' + upd[1] + "</span>" : "") + "</span>",
          '<a class="go" href="https://nditzik.github.io/stocks-momentum/" target="_blank" rel="noopener">דשבורד המומנטום המלא</a>') +
        '<div class="pb"><div class="tiles">' +
          bdTile("4 סיגנלים", String(n4), "בכל הסורקים") +
          bdTile("3 סיגנלים", String(n3), "") +
          bdTile("2 סיגנלים", String(n2), "") +
          bdTile("מועמדות לטרייד", String(nCand), "Readiness 50 ומעלה") +
        "</div></div></section>" +
      '<section class="pan mom-pan"' + bdSpan(12) + '><div class="mom-hd">' + catHd(cats[firstNon]) + "</div>" +
        '<div class="pb mom-navwrap">' + nav + "</div>" + panels + "</section>" +
      '<section class="pan"' + bdSpan(12) + '><details class="bd-exp"><summary>איך זה עובד</summary>' + tabIntro("momentum") +
        '<p class="stamp" style="margin:0 14px 12px">לחיצה על טיקר פותחת את הניתוח הטכני · Readiness = מוכנות לכניסה (0–100), כמו בדשבורד</p></details></section>' +
      "</div>";

    el.querySelectorAll(".mom-tab").forEach(function (b) {
      b.addEventListener("click", function () {
        var idx = b.dataset.mom;
        el.querySelectorAll(".mom-tab").forEach(function (x) { var on = x.dataset.mom === idx; x.classList.toggle("on", on); x.setAttribute("aria-pressed", on); });
        el.querySelectorAll(".mom-list").forEach(function (x) { x.style.display = x.dataset.mom === idx ? "block" : "none"; });
        var hd = el.querySelector(".mom-hd"); if (hd) hd.innerHTML = catHd(cats[+idx]);
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
    // np120: טאב חדשות כרשת פאנלים — תקציר התדרוך | בזק מהרשת → Barchart | חדשות RSS → המבזק האחרון → התדרוך המלא (המייל + ארכיון)
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
        '<div class="mute s" style="margin-bottom:8px"><b>' + esc(sl.subject || "") + "</b>" +
        (sl.sentiment && sl.sentiment.text ? ' · <span>' + h(sl.sentiment.emoji) + " " + esc(sl.sentiment.text) + "</span>" : "") +
        (sl.dateLabel ? " · " + esc(sl.dateLabel) + (sl.time ? " · " + esc(sl.time) : "") : "") + "</div>" +
        '<iframe class="brief-frame" src="' + bust(sl.file, d._meta) + '" title="' + esc(sl.subject || "") +
        '" style="width:100%;border:1px solid var(--border);border-radius:6px;background:#fff;min-height:640px" ' +
        'onload="try{this.style.height=(this.contentWindow.document.body.scrollHeight+30)+\'px\'}catch(e){}"></iframe></div>';
    }).join("");
    // התקציר: המהדורה המאוחרת ראשונה, השנייה מתחתיה
    var m = d.morning, a = d.afternoon, lead;
    if (m && a) lead = briefKey(a) >= briefKey(m) ? [a, "אחר הצהריים", m, "בוקר"] : [m, "בוקר", a, "אחר הצהריים"];
    else lead = m ? [m, "בוקר"] : [a, "אחר הצהריים"];
    function hl(list) { return '<div class="bd-list">' + (list || []).map(function (t, i) { return '<div class="li"><span class="num mute">' + (i + 1) + "</span><span>" + esc(t) + "</span></div>"; }).join("") + "</div>"; }
    function sentPill(s) { return s && s.sentiment && s.sentiment.text ? '<span class="pill state">' + esc(s.sentiment.text.replace(/^סנטימנט:\s*/, "")) + "</span>" : ""; }
    function tm(s) { return s.time ? ' · <span class="num" dir="ltr">' + esc(s.time) + "</span>" : ""; }
    var sched = (lead[0].schedule || []).filter(function (x) { return !x.day; }).slice(0, 3);
    var summary = panHd("התדרוך · " + lead[1] + tm(lead[0]), '<span class="mute">' + esc(lead[0].dateLabel || "") + "</span>" + sentPill(lead[0]),
        '<a class="go" href="#brief-full" onclick="var m=document.getElementById(\'brief-full\');if(m)m.scrollIntoView({behavior:\'smooth\',block:\'start\'});return false">התדרוך המלא</a>') +
      hl(lead[0].headlines) +
      (lead[2] ? '<div class="ph ph2"><h2>' + lead[3] + tm(lead[2]) + "</h2>" + sentPill(lead[2]) + "</div>" + hl((lead[2].headlines || []).slice(0, 4)) : "") +
      (sched.length ? '<div class="led bd-sched">' + sched.map(function (x) { return '<div><span class="num mute" dir="ltr">' + esc(x.time) + "</span><span>" + esc(x.text) + "</span></div>"; }).join("") + "</div>" : "");
    el.innerHTML = stamp(d._meta) + '<div class="board">' +
      '<section class="pan" id="nb-brief"' + bdSpan(8) + ">" + summary + "</section>" +
      '<section class="pan" id="nb-pulse"' + bdSpan(4) + "></section>" +
      '<section class="pan" id="nb-bar"' + bdSpan(6) + '></section><section class="pan" id="nb-rss"' + bdSpan(6) + "></section>" +
      '<section class="pan" id="nb-flash"' + bdSpan(12) + "></section>" +
      '<section class="pan" id="brief-full"' + bdSpan(12) + ">" + panHd("התדרוך המלא", '<span class="mute">המייל כפי שהתקבל · ארכיון 30 יום</span>') + '<div class="pb">' + archNav + nav + frames + "</div></section></div>";
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
    renderNewsSiblings();
  }

  /* טאב "דיווחים" — לוח דוחות שבועי (ב'–ו') בסגנון Earnings Whispers */
  function renderWeekCal(el, d) {
    var week = (d && d.week) || [];
    if (!week.length) {
      emptyPanel(el, "📅", "לוח דיווחים — בקרוב", "");
      return;
    }
    // np120: טאב היומן כרשת פאנלים (display:contents על #weekcal-body — הפאנלים משתתפים ברשת של #panel-weekcal):
    // ציר העונה (#home-season) → "השבוע הקרוב" (דוחות + מאקרו ביחד) → לקראת הדוח | איך הגיבו → מאקרו (#home-econ) | ניתוח דוחות → לוח התוצאות
    var first = week[0], last = week[week.length - 1];
    var year = (first.date || "").slice(0, 4), todayIso = ilNowParts().iso;
    var ecoBy = {}; ((ECON && ECON.events) || []).forEach(function (e) { var k = String(e.date).slice(0, 10); (ecoBy[k] = ecoBy[k] || []).push(e); });
    var cols = week.map(function (day) {
      var mac = (ecoBy[day.date] || []).slice(0, 3).map(function (e) {
        var cls = e.surprise === "good" ? "up" : e.surprise === "bad" ? "down" : "";
        return '<div class="wkm"><span class="tag macro">מאקרו' + (e.ilTime ? ' <span class="num" dir="ltr">' + esc(e.ilTime) + "</span>" : "") + "</span> " + esc(e.he) +
          ' <span class="mute">' + (e.actual != null ? 'בפועל <b class="num ' + cls + '" dir="ltr">' + esc(e.actual) + "</b>" : (e.forecast ? 'צפי <span class="num" dir="ltr">' + esc(e.forecast) + "</span>" : "")) + "</span></div>";
      }).join("");
      var tiles = day.companies.map(function (c) {
        return '<a class="wk-tile" href="https://www.tradingview.com/symbols/' + encodeURIComponent(c.ticker) + '/" target="_blank" rel="noopener" title="' + esc(c.name) + '">' + earnLogoImg(c) + '<span dir="ltr">' + esc(c.ticker) + "</span></a>";
      }).join("");
      var more = day.total > day.companies.length ? '<div class="wk-more">+' + (day.total - day.companies.length) + " נוספות</div>" : "";
      var empty = !day.total && !mac ? '<div class="mute s">אין דיווחים</div>' : "";
      return '<div' + (day.date === todayIso ? ' class="today"' : "") + '><span class="d">' + esc(day.dow) + ' <b class="num" dir="ltr">' + esc(day.label) + "</b>" + (day.total ? ' · <span class="num">' + day.total + "</span> מדווחות" : "") + "</span>" +
        mac + '<div class="tk">' + tiles + empty + "</div>" + more + "</div>";
    }).join("");
    // לקראת הדוח — הקרובה ביותר
    var items = (PREPD && PREPD.items) || [], p0 = items[0], prepPan = "";
    if (p0) {
      var pn = PREPN && PREPN[p0.sym], cons = p0.consensus || {}, opt = p0.options || {}, tg = p0.targets || {};
      prepPan = panHd("לקראת הדוח", '<span class="tag earn"><span dir="ltr">' + esc(p0.sym) + "</span> · " + epDow(p0.date) + ' <span class="num" dir="ltr">' + epDate(p0.date) + "</span> · " + epWhen(p0) + "</span>", bdGo("prep", "כל ההכנות")) +
        '<div class="pb">' + (pn && pn.thesis ? '<p class="bd-lead-p">' + esc(pn.thesis) + "</p>" + (pn.dek ? '<p class="mute" style="margin:0">' + esc(pn.dek) + "</p>" : "") : '<p class="mute" style="margin:0">ההכנה המילולית תיכתב בבוקר שלפני שבוע הדוח. המספרים כבר כאן.</p>') +
        '<div class="tiles t3">' + bdTile("צפי רווח למניה", cons.eps != null ? "$" + Number(cons.eps).toFixed(2) : "—") +
          bdTile("האופציות מתמחרות", opt.earn != null ? "±" + Number(opt.earn).toFixed(1) + "%" : (opt.pct != null ? "±" + Number(opt.pct).toFixed(1) + "%" : "—"), opt.earn != null ? "ליום הדוח" : (p0.avgMove != null ? "ממוצע בדוחות " + Number(p0.avgMove).toFixed(1) + "%" : "")) +
          bdTile("מחיר יעד ממוצע", tg.mean != null ? "$" + Math.round(tg.mean) : "—", tg.n ? '<span class="num">' + tg.n + "</span> אנליסטים" : "") + "</div>" +
        (items.length > 1 ? '<p class="mute s" style="margin:0">אחר כך: ' + items.slice(1, 5).map(function (x) { return '<b class="num" dir="ltr">' + esc(x.sym) + "</b> " + epDate(x.date); }).join(" · ") + "</p>" : "") + "</div>";
    } else if (PREPD) {
      var later = (PREPD.later || []).slice(0, 6);
      prepPan = panHd("לקראת הדוח", "", bdGo("prep", "כל ההכנות")) + '<div class="pb mute">אף חברה עם ניתוח קודם באתר לא מדווחת בשבועיים הקרובים.' +
        (later.length ? "<br>הבאות בתור: " + later.map(function (x) { return '<b class="num" dir="ltr">' + esc(x.sym) + "</b> " + epDate(x.date); }).join(" · ") : "") + "</div>";
    }
    // איך הגיבו המדווחות + "העונה עד כה" מלוח התוצאות
    var rx = reactionsTable(d.reactions, true), b = SEASON && SEASON.board, rxPan = "";
    if (rx) {
      var kv = b && (b.reactBeatN >= 3 || b.reactMissN >= 3) ? '<div class="kv"><span>העונה עד כה</span><span>עקיפה → ' + (b.reactBeatN >= 3 ? bdPct(b.reactBeat) + ' בממוצע (<span class="num">' + b.reactBeatN + "</span> דוחות)" : "מתמלא") +
        " · החטאה → " + (b.reactMissN >= 3 ? bdPct(b.reactMiss) + ' בממוצע (<span class="num">' + b.reactMissN + "</span>)" : "אין עדיין") + "</span></div>" : "";
      rxPan = panHd("איך הגיבו המדווחות", '<span class="mute">סגירה מול סגירה, נרות יומיים · Yahoo Finance</span>') + rx + (kv ? '<div class="pb" style="padding-top:8px">' + kv + "</div>" : "");
    }
    // ניתוח דוחות — צ'יפים + "אחרי הדוח"
    var reps = (REPD && REPD.reports) || [], repPan = "";
    if (reps.length) {
      var chips = reps.slice(0, 12).map(function (r) {
        return '<a class="tag rep-chip" href="#reports" onclick="if(window.__openReport)window.__openReport(\'' + esc(r.file) + '\');return false"><b class="num" dir="ltr">' + esc(r.ticker || "") + "</b> " + (/^\d{4}-/.test(r.date || "") ? '<span class="num" dir="ltr">' + bdDM(r.date) + "</span>" : esc(r.date || "")) + "</a>";
      }).join("");
      var rc = ((PREPD && PREPD.recent) || [])[0], rn = rc && PREPR && PREPR[rc.sym], after = "";
      if (rc) {
        var re = rc.reaction || {}, o = rc.options || {}, marks = { hit: 0, mixed: 0, miss: 0 };
        ((rn && rn.checks) || []).forEach(function (ck) { if (marks[ck.mark] != null) marks[ck.mark]++; });
        after = '<div class="prep"><div class="h"><b class="num" dir="ltr">' + esc(rc.sym) + '</b><span>אחרי הדוח · <span class="num" dir="ltr">' + epDate(rc.date) + "</span> · ההכנה מול מה שקרה</span></div>" +
          "<p>" + (rn ? esc(rn.headline || "") + (rn.checks ? ' · <span class="num">' + marks.hit + "</span> בדיקות עמדו, <span class=\"num\">" + marks.mixed + "</span> חלקית, <span class=\"num\">" + marks.miss + "</span> נכשלו" : "") : "ההשוואה המילולית תיכתב בבוקר הקרוב") +
          (re.chg != null ? " · " + bdPct(re.chg) + (o.pct != null ? ' מול <span class="num" dir="ltr">±' + Number(o.pct).toFixed(1) + "%</span> מתומחר" : "") : "") + "</p>" +
          (rc.newReport && rc.newReport.file ? '<a href="#reports" onclick="if(window.__openReport)window.__openReport(\'' + esc(rc.newReport.file) + '\');return false">הניתוח החדש</a>' : '<a href="#prep" onclick="__goTab(\'prep\');return false">ההכנה המלאה</a>') + "</div>";
      }
      repPan = panHd("ניתוח דוחות", '<span class="mute"><span class="num">' + reps.length + "</span> דוחות באתר</span>", bdGo("reports", "כל הניתוחים")) + '<div class="pb"><div class="chips bd-chips">' + chips + "</div>" + after + "</div>";
    }
    el.innerHTML =
      '<section class="pan bd-wk5" style="order:1;grid-column:span 12">' + panHd('השבוע הקרוב · <span class="num" dir="ltr">' + esc(first.label) + "–" + esc(last.label) + "." + esc(year) + "</span>", '<span class="mute">דוחות ומאקרו ביחד · שעון ישראל · מובילות לפי שווי שוק · מתעדכן בכל שבת</span>') +
        '<div class="wk5">' + cols + "</div></section>" +
      (prepPan ? '<section class="pan" style="order:2;grid-column:span 6">' + prepPan + "</section>" : "") +
      (rxPan ? '<section class="pan bd-rx" style="order:3;grid-column:span ' + (prepPan ? 6 : 12) + '">' + rxPan + "</section>" : "") +
      (repPan ? '<section class="pan" style="order:5;grid-column:span 5">' + repPan + "</section>" : "") +
      '<section class="pan" id="sbd-pan" style="order:6;grid-column:span 12">' + panHd("לוח התוצאות" + (SEASON && SEASON.season ? " · עונת הדוחות " + esc(SEASON.season) : ""), '<span class="mute">חברות ה-S&amp;P 500 · מתעדכן כל רבע שעה</span>') + '<div class="pb" id="season-board">' + seasonBoardHtml(true) + "</div></section>";
  }
  /* לוגו בלוח הדיווחים: העותק שה-Action שמר (FMP ומקורות גיבוי, data/earnings/logos) ואם אין — FMP ישירות.
     (10.10.2026: ל-UNH לא הוצג לוגו כשהדפדפן משך רק מ-FMP) */
  function earnLogo(c) {
    return c.logo || "https://financialmodelingprep.com/image-stock/" + encodeURIComponent(c.ticker) + ".png";
  }
  /* לוגו לבן על רקע שקוף (logoBg:"dark" מ-fetch_earnings, 10.10.2026) → ריבוע כהה */
  function earnLogoImg(c) {
    return '<img' + (c.logoBg === "dark" ? ' class="dk"' : "") + ' src="' + esc(earnLogo(c)) + '" alt="" loading="lazy" onerror="this.remove()">';
  }
  /* "איך הגיבו המדווחות" (11.9.2026) — טבלה בטאב דיווחים. המספרים מ-fetch_earnings.py:
     סגירה-מול-סגירה מנרות יומיים (לא %Change של ה-CSV, שהוא מיום הייצוא). מדווחת
     אחרי-הסגירה נמדדת ביום המסחר הבא; מספר של סשן שעדיין פתוח מסומן "ביניים" ולא
     מוצג כסופי; בלי נר תגובה — "מגיבה במסחר הבא". */
  function reactionsTable(rx, bare_) {
    var days = (rx && rx.days) || [];
    if (!days.length) return "";
    function d2(iso) { var m = /^\d{4}-(\d{2})-(\d{2})/.exec(iso || ""); return m ? (+m[2]) + "." + (+m[1]) : ""; }
    var rows = [];
    days.forEach(function (day) {
      (day.items || []).forEach(function (r, i) {
        var when = r.when === "after" ? "אחרי הסגירה" : "לפני הפתיחה";   // בלי מועד ידוע — fetch_earnings מדלג על החברה
        var val, note;
        if (r.status === "final" || r.status === "live") {
          val = '<b class="num ' + (r.chg > 0 ? "up" : r.chg < 0 ? "down" : "") + (r.status === "live" ? " rx-live" : "") + '" dir="ltr">' + (r.chg > 0 ? "+" : "") + r.chg.toFixed(1) + "%</b>";
          if (r.status === "live") val += '<span class="rx-mob">ביניים</span>';
          note = r.status === "live" ? '<span class="rx-tag rx-tag-live">ביניים · המסחר פתוח</span>'
               : '<span class="rx-tag">סגירת <span dir="ltr">' + d2(r.reactDate) + "</span></span>";
        } else if (r.status === "pending") {
          val = '<span class="rx-wait">—</span><span class="rx-mob">במסחר הבא</span>'; note = '<span class="rx-tag">מגיבה במסחר הבא</span>';
        } else {
          val = '<span class="rx-wait">—</span>'; note = '<span class="rx-tag">אין נתון</span>';
        }
        rows.push('<tr' + (i === 0 ? ' class="rx-first"' : "") + ">" +
          "<td>" + (i === 0 ? '<b>' + esc(day.label) + "</b>" : "") + "</td>" +
          '<td><a class="rx-co" href="https://www.tradingview.com/symbols/' + encodeURIComponent(r.ticker) + '/" target="_blank" rel="noopener">' +
            earnLogoImg(r) +
            '<span class="rx-tk" dir="ltr">' + esc(r.ticker) + '</span><span class="rx-nm">' + esc(r.name || "") + "</span></a></td>" +
          '<td class="rx-when">' + when + "</td>" +
          '<td class="num">' + val + "</td>" +
          '<td class="num">' + (r.price != null ? '<span dir="ltr">' + r.price.toFixed(2) + "</span>" : "") + "</td>" +
          "<td>" + note + "</td></tr>");
      });
    });
    if (bare_) return '<div class="tbl rx-wrap"><table class="bd-tbl"><thead><tr><th>דיווח</th><th>חברה</th><th>מועד</th><th>תגובה</th><th>סגירה</th><th>סטטוס</th></tr></thead><tbody>' + rows.join("") + "</tbody></table></div>";
    return '<div class="section-title" style="margin-top:26px">📈 איך הגיבו המדווחות</div>' +
      '<p class="stamp" style="margin-top:-6px">שינוי סגירה-מול-סגירה ביום התגובה (מדווחת אחרי הסגירה — ביום המסחר הבא) · מקור: Yahoo Finance · הגדולות לפי שווי שוק</p>' +
      '<div class="table-wrap rx-wrap"><table><thead><tr><th>דיווח</th><th>חברה</th><th>מועד</th><th class="num">תגובה</th><th class="num">סגירה</th><th>סטטוס</th></tr></thead><tbody>' +
      rows.join("") + "</tbody></table></div>";
  }

  /* טאב סקטורים — הדוח השבועי האחרון + ארכיון שבועות קודמים */
  var SECT = null;
  function secDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
    return m ? (+m[3]) + "." + (+m[2]) + "." + m[1].slice(2) : iso;
  }
  /* שווקים בינלאומיים — מדדי בורסה מרחבי העולם, מקובצים לפי אזור.
     המספר לבדו מטעה כאן: ברוב שעות היממה רוב הבורסות סגורות, ו"DAX 0.00%"
     בבוקר הוא נעילת אתמול ולא שוק ששקט. לכן כל שורה נושאת חיווי מצב ואת
     שעת העדכון בפועל — שניהם מגיעים מ-fetch_world.py, שמחשב אותם מחותמת
     הזמן של הציטוט עצמו ולא מהנחה על לוח שעות. */
  /* "השוק סגור, כך נסחר סוף השבוע" (13.9.2026) — data/weekend.json מ-fetch_weekend.py:
     בסוף השבוע (חוזי שיקגו סגורים) חוזי xyz על Hyperliquid ל-S&P 500 ולשבע מניות
     שאיציק בחר + ביטקוין/את'ריום; בימי חול רק הקריפטו (24/7) לצד חוזי שיקגו. הפער
     מול הסגירה הרשמית האחרונה; "מחזור דק" מסומן. אינדיקציה לכיוון, לא תחזית לפתיחה. */
  var WKND = null, WORLDD = null;
  function weekendStrip() {
    var w = WKND; if (!w || !w.items || !w.items.length) return "";
    var wk = w.mode === "weekend";
    function pc(v, d2) { return v == null ? "—" : (v > 0 ? "+" : "") + v.toFixed(d2 == null ? 2 : d2) + "%"; }
    function cls(v) { return v > 0 ? "up" : v < 0 ? "down" : ""; }
    // הקריפטו עבר לכרטיסים משלו מתחת למפה (13.9.2026 ערב); הרצועה = חוזי xyz, ורק בסוף השבוע
    if (!wk) return "";
    var rows = w.items.filter(function (i) { return i.kind !== "crypto"; });
    if (!rows.length) return "";
    var tiles = rows.map(function (i) {
      var v = i.chg, a = v == null ? 0 : Math.min(1, Math.abs(v) / 2.5);
      var bg = i.thin ? "var(--surface-2)" : v > 0 ? "rgba(26,157,87," + (0.12 + 0.62 * a).toFixed(2) + ")" : v < 0 ? "rgba(224,52,42," + (0.12 + 0.62 * a).toFixed(2) + ")" : "var(--surface-2)";
      var tip = esc(i.label) + " · " + (i.price != null ? i.price.toLocaleString("en-US", { maximumFractionDigits: 2 }) : "—") +
        (i.refLabel && i.ref != null ? " · " + esc(i.refLabel) + " " + i.ref.toLocaleString("en-US", { maximumFractionDigits: 2 }) : "") +
        (i.chg24 != null ? " · 24 שעות " + pc(i.chg24) : "") +
        (i.vol24 ? " · מחזור 24 שעות $" + Math.round(i.vol24 / 1e6) + "M" : "") + (i.thin ? " · מחזור דק" : "");
      return '<div class="wh wk-t' + (i.thin ? " wk-thin" : "") + '" style="background:' + bg + '" title="' + tip + '">' +
        '<span class="wh-n">' + esc(i.label) + (i.kind === "crypto" ? ' <span class="wk-k">24/7</span>' : i.source === "xyz" ? ' <span class="wk-k">xyz</span>' : "") + "</span>" +
        '<b class="wh-c num ' + cls(v) + '" dir="ltr">' + pc(v) + "</b>" +
        '<span class="wh-5 num" dir="ltr">' + (i.price != null ? i.price.toLocaleString("en-US", { maximumFractionDigits: i.price > 1000 ? 0 : 2 }) : "—") + "</span>" +
        (i.chg24 != null ? '<span class="wh-5 num" dir="ltr">24h ' + pc(i.chg24, 1) + "</span>" : "") + "</div>";
    }).join("");
    var title = "🌙 השוק סגור — כך נסחר סוף השבוע";
    var sub = "חוזים תמידיים של xyz על Hyperliquid · הפער מסגירת שישי · אינדיקציה, מחזור דק";
    return '<section class="wm-grp wk-grp"><h3 class="wm-rg">' + title + ' <span class="wm-rg-s">' + sub + "</span></h3>" +
      '<div class="wm-heat wk-heat">' + tiles + "</div>" +
      (wk ? '<p class="wk-note">המחירים כאן הם חוזים על מחיר, לא מניות, במחזורים של מיליונים בודדים — מספיק לכיוון ולריכוז (מדד מול מניות ה-AI), לא לגודל התנועה. פערי סוף שבוע נסגרים לא פעם עד פתיחת החוזים בשיקגו (שני 01:00). עודכן ' + esc((w._meta || {}).updatedAt || "") + "</p>" : "") +
      "</section>";
  }

  function renderWorld(el, d) {
    if (!el) return;
    var items = (d && d.items) || [];
    if (!items.length) { emptyPanel(el, "🌍", "שווקים בינלאומיים — בקרוב", ""); return; }
    // np120: טאב העולם כרשת פאנלים — סיכום + שעון עולמי → ישראל (כרטיסים + מפת חום) | העולם לפי אזור →
    // מפת העולם → קריפטו | מה השווקים מהמרים. המצב של כל שורה נגזר מחותמת הציטוט (ראו הערות 9–11.9.2026).
    // שנגחאי 10.10.2026: fetch_world החזיר chg של מיליארדים — ערך לא סביר נחשב חסר (באג בצינור, לא כאן)
    items.forEach(function (i) { if (i.chg != null && Math.abs(i.chg) > 50) { i.chg = null; i.chg5d = null; } });
    var byKey = {}; items.forEach(function (i) { byKey[i.key] = i; });
    var IL_MAIN = "ישראל — מדדים ראשיים", IL_SECT = "ישראל — סקטורים";
    var groups = {}; items.forEach(function (i) { (groups[i.region] = groups[i.region] || []).push(i); });
    var dot = { live: "🟢", pre: "🟡", closed: "⚪", stale: "⚠️" };
    function pc(v, d2) { return v == null ? "—" : (v > 0 ? "+" : "") + v.toFixed(d2 == null ? 2 : d2) + "%"; }
    function cls(v) { return v > 0 ? "up" : v < 0 ? "down" : ""; }
    function avg(rows) {
      var xs = rows.filter(function (i) { return i.chg != null && i.state !== "stale"; }).map(function (i) { return i.chg; });
      return xs.length ? xs.reduce(function (a, b) { return a + b; }, 0) / xs.length : null;
    }
    function spark(i) {
      var arr = i.spark || [], c = cls(i.chg);
      if (arr.length < 3) return "";
      var mn = Math.min.apply(null, arr), mx = Math.max.apply(null, arr), rg = (mx - mn) || 1;
      var pts = arr.map(function (v, k) { return (k * (100 / (arr.length - 1))).toFixed(1) + "," + (26 - ((v - mn) / rg) * 22 + 2).toFixed(1); });
      var lp = pts[pts.length - 1].split(",");
      return '<svg class="wc-sp" viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true"><polyline points="' + pts.join(" ") + '" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>' +
        '<circle cx="' + lp[0] + '" cy="' + lp[1] + '" r="2.6" class="' + c + '"/></svg>';
    }
    function card(i) {
      var c = cls(i.chg);
      return '<div class="wc wc-' + esc(i.state) + '" id="wc-' + esc(i.key) + '" title="' + esc(i.stateHe) + (i.at ? " · " + esc(i.at) : "") + '">' +
        '<div class="t"><span class="wc-n"><span class="wm-fl">' + esc(i.flag) + "</span> " + esc(i.label) + '</span><b class="wc-c num ' + c + '" dir="ltr">' + pc(i.chg) + "</b></div>" +
        '<div class="m"><span class="wc-p num" dir="ltr">' + (i.price != null ? i.price.toLocaleString("en-US", { maximumFractionDigits: i.price > 1000 ? 0 : 2 }) : "—") + "</span>" +
          '<span>שבוע <b class="num ' + cls(i.chg5d) + '" dir="ltr">' + pc(i.chg5d, 1) + "</b></span>" +
          (i.chgYtd != null ? '<span>השנה <b class="num ' + cls(i.chgYtd) + '" dir="ltr">' + pc(i.chgYtd, 1) + "</b></span>" : "") + "</div>" +
        spark(i) +
        '<div class="wc-s mute">' + (dot[i.state] || "") + " " + esc(i.stateHe) + (i.at ? ' · <span class="num" dir="ltr">' + esc(i.at) + "</span>" : "") + "</div></div>";
    }
    function cards(rows, g) { return '<div class="wgrid' + (g ? " " + g : "") + '">' + rows.map(card).join("") + "</div>"; }
    function heat(rows) {
      var sorted = rows.slice().sort(function (a, b) { return (b.chg == null ? -99 : b.chg) - (a.chg == null ? -99 : a.chg); });
      return '<div class="wm-heat">' + sorted.map(function (i) {
        var v = i.chg, a = v == null ? 0 : Math.min(1, Math.abs(v) / 2.5);
        var bg = v > 0 ? "rgba(13,122,82," + (0.18 + 0.62 * a).toFixed(2) + ")" : v < 0 ? "rgba(190,46,28," + (0.18 + 0.62 * a).toFixed(2) + ")" : "var(--surface-2)";
        return '<div class="wh wh-' + esc(i.state) + '" style="background:' + bg + '" title="' + esc(i.label) + " · " + (i.price != null ? i.price.toLocaleString("en-US") : "") + " · " + esc(i.stateHe) + (i.at ? " " + esc(i.at) : "") + '">' +
          '<span class="wh-n">' + esc(i.label.replace(/^ת"א /, "")) + "</span>" +
          '<b class="wh-c num" dir="ltr">' + pc(v, 1) + "</b>" +
          (i.chg5d != null ? '<span class="wh-5 num" dir="ltr">5d ' + pc(i.chg5d, 1) + "</span>" : "") + "</div>";
      }).join("") + "</div>";
    }
    function stateWord(rows) {
      if (rows.some(function (i) { return i.state === "live"; })) return "נסחר";
      if (rows.some(function (i) { return i.state === "pre"; })) return "לפני פתיחה";
      return "סגירה אחרונה";
    }
    // 1. שורת סיכום עולמי
    var fut = null;
    if (TICKD) (TICKD.items || []).forEach(function (t) { if (t.key === "es") fut = t; });
    var usLive = (groups["ארה\"ב"] || []).some(function (i) { return i.state === "live"; });
    var segs = [];
    var asia = avg(groups["אסיה"] || []), eu = avg(groups["אירופה"] || []), il = byKey.ta125 || byKey.ta35;
    function segWord(v, live) { return v == null ? "" : (live ? (v > 0 ? "עולה" : v < 0 ? "יורדת" : "ללא שינוי") : (v > 0 ? "נסגרה בעלייה" : v < 0 ? "נסגרה בירידה" : "נסגרה ללא שינוי")); }
    if (asia != null) segs.push("אסיה " + segWord(asia, (groups["אסיה"] || []).some(function (i) { return i.state === "live"; })) + ' <b class="num ' + cls(asia) + '" dir="ltr">' + pc(asia) + "</b>");
    if (eu != null) segs.push("אירופה " + segWord(eu, (groups["אירופה"] || []).some(function (i) { return i.state === "live"; })) + ' <b class="num ' + cls(eu) + '" dir="ltr">' + pc(eu) + "</b>");
    if (il && il.chg != null) segs.push("תל אביב " + segWord(il.chg, il.state === "live") + ' <b class="num ' + cls(il.chg) + '" dir="ltr">' + pc(il.chg) + "</b>");
    if (usLive && byKey.spx) segs.push('ארה"ב ' + segWord(byKey.spx.chg, true) + ' <b class="num ' + cls(byKey.spx.chg) + '" dir="ltr">' + pc(byKey.spx.chg) + "</b>");
    else if (WKND && WKND.mode === "weekend" && (WKND.items || []).some(function (i) { return i.key === "sp500" && i.chg != null; }))
      (WKND.items || []).forEach(function (i) { if (i.key === "sp500") segs.push('ארה"ב בסוף השבוע (xyz) <b class="num ' + cls(i.chg) + '" dir="ltr">' + pc(i.chg) + "</b>"); });
    else if (fut && fut.chg != null) segs.push('ארה"ב מהחוזים <b class="num ' + cls(fut.chg) + '" dir="ltr">' + pc(fut.chg) + "</b>");
    // 2. שעון עולמי — צ'יפים לפי שעת הפתיחה בשעון ישראל; פתוח = ירוק
    var CITIES = [["n225", "טוקיו"], ["ks11", "סיאול"], ["twii", "טאיפיי"], ["sse", "שנגחאי"], ["hsi", "הונג קונג"], ["nsei", "מומבאי"], ["ta125", "תל אביב"], ["ftse", "לונדון"], ["dax", "פרנקפורט"], ["spx", "ניו יורק"], ["tsx", "טורונטו"]];
    function hm(h) { var H = Math.floor(h), M = Math.round((h - H) * 60); return ("0" + H).slice(-2) + ":" + ("0" + M).slice(-2); }
    var SW = { live: "פתוח", pre: "לפני פתיחה", closed: "סגור", stale: "ציטוט ישן" };
    var clock = CITIES.map(function (c) { return byKey[c[0]] ? { i: byKey[c[0]], city: c[1] } : null; }).filter(Boolean)
      .sort(function (a, b) { return (a.i.hours || [0])[0] - (b.i.hours || [0])[0]; })
      .map(function (x) {
        var hh = x.i.hours || [];
        return '<span class="ck ' + esc(x.i.state) + '"><span class="wm-fl">' + esc(x.i.flag) + "</span> " + esc(x.city) +
          (hh.length === 2 ? ' <span class="num" dir="ltr">' + hm(hh[0]) + "–" + hm(hh[1]) + "</span>" : "") + " · " + (SW[x.i.state] || esc(x.i.stateHe)) + "</span>";
      }).join("");
    var t = ilNowParts(), DOW = { Sun: "ראשון", Mon: "שני", Tue: "שלישי", Wed: "רביעי", Thu: "חמישי", Fri: "שישי", Sat: "שבת" };
    var hmNow = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Jerusalem", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date());
    var html = '<div class="board">' +
      '<section class="pan"' + bdSpan(12) + ">" + panHd("העולם · " + (DOW[t.dow] || "") + ' <span class="num" dir="ltr">' + bdDM(t.iso) + '</span> · <span class="num" dir="ltr">' + hmNow + "</span> שעון ישראל", segs.length ? '<span class="mute">' + segs.join(' <span class="wm-sep">·</span> ') + "</span>" : "") +
        '<div class="pb"><div class="clock" aria-label="שעון עולמי">' + clock + '</div><span class="mute s">🟢 נסחר · 🟡 לפני פתיחה · ⚪ סגור (השינוי = יום המסחר האחרון) · ⚠️ ציטוט ישן · שעון ישראל</span></div></section>';
    if (groups[IL_MAIN] || groups[IL_SECT]) {
      html += '<section class="pan"' + bdSpan(6) + ">" + panHd("ישראל", '<span class="mute">בורסת תל אביב · ' + stateWord(groups[IL_MAIN] || []) + "</span>") + '<div class="pb">' +
        (groups[IL_MAIN] ? cards(groups[IL_MAIN], "g2") : "") +
        (groups[IL_SECT] ? '<div class="mute s">מפת חום · <span class="num">' + groups[IL_SECT].length + "</span> סקטורים · ממוין מהעולה החזק ליורד</div>" + heat(groups[IL_SECT]) : "") + "</div></section>";
    }
    html += '<section class="pan"' + bdSpan(6) + ">" + panHd("העולם", '<span class="mute">לפי אזור · מצב המסחר מחותמת הציטוט</span>') + '<div class="pb">';
    ["אסיה", "אירופה", "ארה\"ב"].forEach(function (region) {
      if (groups[region]) html += '<div class="mute s">' + esc(region) + " · " + stateWord(groups[region]) + "</div>" + cards(groups[region]);
      if (region === "ארה\"ב") html += weekendStrip();
    });
    html += "</div></section>";
    html += '<section class="pan"' + bdSpan(12) + ">" + panHd("מפת העולם", '<span class="mute">צבע = השינוי היומי · נקודה פועמת = נסחר עכשיו · האזור המוצלל בלילה · לחיצה גוללת לכרטיס</span>') + '<div class="pb"><div id="wm-map" class="wm-map"></div></div></section>';
    if (groups["קריפטו"]) html += '<section class="pan"' + bdSpan(4) + ">" + panHd("קריפטו", '<span class="mute">24/7 · השינוי היומי מ-00:00 UTC</span>') + '<div class="pb">' + cards(groups["קריפטו"], "g1") + "</div></section>";
    html += '<section class="pan" id="wd-bets"' + bdSpan(groups["קריפטו"] ? 8 : 12) + "></section>";
    html += '<p class="stamp" style="grid-column:span 12;margin:0">נתוני המדדים מ-Yahoo Finance, מושהים בכ-15-20 דקות · 5 ימים ומתחילת השנה מסגירה לסגירה · עודכן ' + esc((d._meta || {}).updatedAt || "") + "</p></div>";
    el.innerHTML = html;
    renderWorldMap(items);
    renderWorldBets();
  }

  /* מפת העולם (11.9.2026) — מתחת לסקטורי ישראל. הגבולות מגיעים מ-assets/worldmap.json
     (נבנה פעם אחת ע"י scripts/tools/build_worldmap.py, היטל שטוח 1000×440); כאן רק
     צובעים מדינות לפי world.json, מציירים נקודת בורסה לכל עיר (פועמת כשנסחר) וקו
     יום/לילה שמחושב מהשעה. בלי ספרייה: המפה סטטית, הצבע הוא כל מה שמשתנה. */
  var WMAP = null, WMAP_LOADING = false;
  var WMAP_COUNTRY = { "392": "n225", "410": "ks11", "158": "twii", "156": "sse", "356": "nsei", "826": "ftse", "276": "dax", "840": "spx", "124": "tsx", "376": "ta125" };
  var WMAP_CITIES = [["n225", "טוקיו", 139.69, 35.69], ["ks11", "סיאול", 126.98, 37.57], ["twii", "טאיפיי", 121.56, 25.03], ["sse", "שנגחאי", 121.47, 31.23],
    ["hsi", "הונג קונג", 114.17, 22.32], ["nsei", "מומבאי", 72.88, 19.08], ["ta125", "תל אביב", 34.78, 32.08], ["ftse", "לונדון", -0.13, 51.51],
    ["dax", "פרנקפורט", 8.68, 50.11], ["spx", "ניו יורק", -74.01, 40.71], ["tsx", "טורונטו", -79.38, 43.65]];
  function renderWorldMap(items) {
    var host = document.getElementById("wm-map");
    if (!host) return;
    if (!WMAP) {
      if (!WMAP_LOADING) {
        WMAP_LOADING = true;
        fetchJSON("assets/worldmap.json").then(function (m) { WMAP = m; renderWorldMap(items); }).catch(function () { host.innerHTML = ""; });
      }
      return;
    }
    var W = WMAP.w, H = WMAP.h, top = WMAP.latTop, bot = WMAP.latBottom;
    function px(lon, lat) { return [(lon + 180) / 360 * W, (top - lat) / (top - bot) * H]; }
    var byKey = {}; items.forEach(function (i) { byKey[i.key] = i; });
    function fill(i) {
      if (!i || i.chg == null || i.state === "stale") return "";
      var a = Math.min(1, Math.abs(i.chg) / 2.5);
      return i.chg > 0 ? "rgba(26,157,87," + (0.25 + 0.6 * a).toFixed(2) + ")" : i.chg < 0 ? "rgba(224,52,42," + (0.25 + 0.6 * a).toFixed(2) + ")" : "";
    }
    var land = Object.keys(WMAP.countries).map(function (id) {
      var i = byKey[WMAP_COUNTRY[id]], f = fill(i);
      var t = i ? i.label + " · " + (i.chg == null ? "—" : (i.chg > 0 ? "+" : "") + i.chg.toFixed(2) + "%") + " · " + i.stateHe : "";
      return '<path class="wmc' + (i ? " wmc-on" : "") + '" d="' + WMAP.countries[id] + '"' + (f ? ' style="fill:' + f + '"' : "") +
        (i ? ' data-k="' + esc(i.key) + '"><title>' + esc(t) + "</title></path>" : "/>");
    }).join("");
    // קו יום/לילה: נקודת השמש מהשעה (נטייה + משוואת הזמן בקירוב), והלילה כפוליגון
    var now = new Date(), doy = Math.floor((now - new Date(now.getUTCFullYear(), 0, 0)) / 864e5);
    var decl = -23.44 * Math.cos(2 * Math.PI / 365 * (doy + 10));
    var b = 2 * Math.PI * (doy - 81) / 365, eot = 9.87 * Math.sin(2 * b) - 7.53 * Math.cos(b) - 1.5 * Math.sin(b);
    var utcH = now.getUTCHours() + now.getUTCMinutes() / 60 + eot / 60;
    var sunLon = (12 - utcH) * 15;
    var d2r = Math.PI / 180, r2d = 180 / Math.PI, pts = [];
    for (var lon = -180; lon <= 180; lon += 3) {
      var lat = Math.atan(-Math.cos((lon - sunLon) * d2r) / Math.tan(decl * d2r)) * r2d;
      pts.push(px(lon, lat));
    }
    var poleY = decl > 0 ? H + 20 : -20;      // הלילה בקוטב הנגדי לנטיית השמש
    var night = "M" + pts.map(function (p) { return p[0].toFixed(0) + "," + p[1].toFixed(0); }).join("L") + "L" + W + "," + poleY + "L0," + poleY + "Z";
    var pins = WMAP_CITIES.map(function (c) {
      var i = byKey[c[0]]; if (!i) return "";
      var p = px(c[2], c[3]), st = i.state;
      return '<g class="wmp wmp-' + esc(st) + '" data-k="' + esc(c[0]) + '" transform="translate(' + p[0].toFixed(1) + "," + p[1].toFixed(1) + ')">' +
        (st === "live" ? '<circle class="wmp-ring" r="5"/>' : "") + '<circle class="wmp-dot" r="' + (c[0] === "ta125" ? 4.2 : 3.4) + '"/>' +
        "<title>" + esc(c[1] + " · " + i.label + " · " + i.stateHe + (i.at ? " " + i.at : "")) + "</title></g>";
    }).join("");
    host.innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="xMidYMid meet" role="img" aria-label="מפת העולם — שינוי יומי לפי מדינה ובורסות פתוחות">' +
      '<g class="wm-land">' + land + "</g>" + '<path class="wm-night" d="' + night + '"/>' + '<g class="wm-pins">' + pins + "</g></svg>";
    host.querySelectorAll("[data-k]").forEach(function (n) {
      n.addEventListener("click", function () {
        var c = document.getElementById("wc-" + n.getAttribute("data-k"));
        if (c) { c.scrollIntoView({ behavior: "smooth", block: "center" }); c.classList.add("wc-flash"); setTimeout(function () { c.classList.remove("wc-flash"); }, 1600); }
      });
    });
  }

  /* ── גלגל הרוטציה (28.9.2026, איציק) ─────────────────────────────────────────
     11 סקטורים על שני צירים מול S&P 500: ימינה = חוזק ב-20 יום (rs20), למעלה = חוזק ב-5 ימים (rs5).
     הנתון היומי מהדשבורד (indices.rotation.sectorRs) נשמר ב-history.json.days[].rs (archive_scores),
     וממנו השביל: "השבוע" = 5 ימי מסחר יום-יום (ברירת מחדל), "החודש" = קפיצות של שבוע.
     צבע אחד לכל הנקודות — הרבע (רקע ירקרק/אדמדם) הוא המידע. ריחוף/נגיעה: השביל של הסקטור מודגש,
     חלונית עם המספרים, מול אתמול, מול לפני שבוע, ומשפט מדוח הסקטורים השבועי כשיש. */
  var RW = { mode: "week", all: false };
  var RW_LAY = { X0: -11, X1: 7, Y0: -9.5, Y1: 4.5 };
  var RW_ETF = { XLK: "IT", XLF: "FIN", XLV: "HC", XLY: "CD", XLC: "COM", XLI: "IND", XLP: "CS", XLE: "ENE", XLB: "MAT", XLU: "UTL", XLRE: "RE" };
  // נקודת "עכשיו" (אומדן תוך-יומי): לכל סקטור, השינוי היומי החי שלו פחות השינוי של SPY (ממפת החום, כל דקה)
  // מתווסף ל-rs5/rs20 של הסגירה האחרונה. אומדן — החלון המתגלגל לא מעודכן, רק היום נוסף. רק כשהבורסה לא סגורה.
  function rwLive() {
    if (typeof HEAT === "undefined" || HEAT.SPY == null || jsSession() === "closed") return null;
    var out = {}, n = 0;
    Object.keys(RW_ETF).forEach(function (etf) { if (HEAT[etf] != null) { out[RW_ETF[etf]] = Math.round((HEAT[etf] - HEAT.SPY) * 100) / 100; n++; } });
    return n ? out : null;
  }
  function rwDays() {
    var days = ((HIST && HIST.days) || []).filter(function (d) { return d.rs && Object.keys(d.rs).length; });
    // היום של indices עשוי להיות טרי יותר מ-history (עד ריצת הארכיון הבאה) — משלימים
    if (INDD && INDD.rotation && INDD.rotation.sectorRs && INDD.date && (!days.length || days[days.length - 1].date < INDD.date)) {
      var rs = {}; Object.keys(INDD.rotation.sectorRs).forEach(function (k) { rs[k] = [INDD.rotation.sectorRs[k].rs5, INDD.rotation.sectorRs[k].rs20]; });
      days.push({ date: INDD.date, rs: rs });
    }
    return days;
  }
  function rwQuad(rs5, rs20) { return rs20 >= 0 ? (rs5 >= 0 ? ["מוביל", "up"] : ["נחלש", "down"]) : (rs5 >= 0 ? ["מתאושש", "up"] : ["מפגר", "down"]); }
  function rwFmt(v) { return v == null ? "—" : (v > 0 ? "+" : "") + Number(v).toFixed(1) + "%"; }
  function rwWeeklyNote(name) {
    var sec = WEEKLY && WEEKLY.sectors; if (!sec) return "";
    var o = (sec.out || []).filter(function (x) { return x.name === name; })[0];
    if (o) return "בדוח השבועי: הרוחב ירד מ-" + o.from + "% ל-" + o.to + "%";
    var h = (sec.held || []).filter(function (x) { return x.name === name; })[0];
    if (h) return "בדוח השבועי: החזיק, " + h.from + "% ← " + h.to + "%";
    return "";
  }
  function rotationWheelHtml() {
    if (!rwDays().length) return "";
    // שלב 7 (10.10.2026): כותרת פאנל במקום כותרת-סעיף + כרטיס
    return panHd("גלגל הרוטציה · לאן הכסף זז", '<span class="mute">11 הסקטורים מול S&amp;P 500</span>') +
      '<div class="pb rw-card">' +
        '<p class="rw-dek">כל סקטור נמדד מול S&P 500: ימינה = חזק יותר מהמדד ב-20 הימים האחרונים, למעלה = חזק יותר ב-5 הימים האחרונים. ' +
        'השביל מראה מאיפה הוא הגיע. סקטור שנע למטה-שמאלה מאבד כסף; למעלה-ימינה מקבל.</p>' +
        '<div class="rw-row"><span class="rw-cap">שביל:</span>' +
          '<button class="chip rw-chip' + (RW.mode === "week" ? " on" : "") + '" data-rw="week">השבוע · יום-יום</button>' +
          '<button class="chip rw-chip' + (RW.mode === "month" ? " on" : "") + '" data-rw="month">החודש · שבוע-שבוע</button>' +
          '<button class="chip rw-chip' + (RW.all ? " on" : "") + '" data-rw="all">כל השבילים</button>' +
          '<span class="rw-legend"><span><i class="d"></i>העיגול: מול המדד בתקופה</span><span><i class="t"></i>הקו: התנועה האחרונה על הגרף</span><span><i class="g"></i>ירוק עלה · <i class="r"></i>אדום ירד</span><span id="rw-lg-now" hidden><i class="n"></i>עכשיו · אומדן חי</span></span></div>' +
        '<div class="rw-wrap"><svg id="rw-svg" role="img" aria-label="גלגל הרוטציה של 11 הסקטורים"></svg><div class="rw-tip" id="rw-tip"></div></div>' +
        '<p class="rw-foot" id="rw-foot"></p>' +
      "</div>";
  }
  function renderRotationWheel() {
    var svg = document.getElementById("rw-svg"), tip = document.getElementById("rw-tip");
    if (!svg) return;
    var days = rwDays(); if (!days.length) return;
    var mobile = window.innerWidth < 600;
    var W = mobile ? 520 : 960, H = mobile ? 560 : 540, P = mobile ? { l: 44, r: 14, t: 30, b: 40 } : { l: 56, r: 24, t: 34, b: 44 };
    var L = RW_LAY;
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.classList.toggle("all", RW.all);
    function sx(v) { return P.l + (v - L.X0) / (L.X1 - L.X0) * (W - P.l - P.r); }
    function sy(v) { return H - P.b - (v - L.Y0) / (L.Y1 - L.Y0) * (H - P.t - P.b); }
    function cl(v, a, b) { return Math.max(a, Math.min(b, v)); }
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    var g = mtEl("g", {}); svg.appendChild(g);
    g.appendChild(mtEl("rect", { x: sx(0), y: P.t, width: sx(L.X1) - sx(0), height: sy(0) - P.t, class: "rw-q up" }));
    g.appendChild(mtEl("rect", { x: sx(L.X0), y: sy(0), width: sx(0) - sx(L.X0), height: sy(L.Y0) - sy(0), class: "rw-q down" }));
    var xs = mobile ? 4 : 2, t;
    for (var x = -8; x <= 6; x += xs) { g.appendChild(mtEl("line", { x1: sx(x), x2: sx(x), y1: P.t, y2: H - P.b, class: "rw-ax" })); t = mtEl("text", { x: sx(x), y: H - P.b + 16, class: "rw-axl", "text-anchor": "middle" }); t.textContent = (x > 0 ? "+" : "") + x + "%"; g.appendChild(t); }
    for (var y = -8; y <= 4; y += 2) { g.appendChild(mtEl("line", { y1: sy(y), y2: sy(y), x1: P.l, x2: W - P.r, class: "rw-ax" })); t = mtEl("text", { x: P.l - 8, y: sy(y) + 4, class: "rw-axl", "text-anchor": "end" }); t.textContent = (y > 0 ? "+" : "") + y + "%"; g.appendChild(t); }
    g.appendChild(mtEl("line", { x1: sx(0), x2: sx(0), y1: P.t, y2: H - P.b, class: "rw-zero" }));
    g.appendChild(mtEl("line", { y1: sy(0), y2: sy(0), x1: P.l, x2: W - P.r, class: "rw-zero" }));
    t = mtEl("text", { x: W - P.r, y: H - 6, class: "rw-axt", "text-anchor": "start", style: "direction:rtl" }); t.textContent = "← חוזק מול S&P 500 ב-20 יום"; g.appendChild(t);
    t = mtEl("text", { x: P.l - 40, y: P.t - 12, class: "rw-axt", "text-anchor": "end", style: "direction:rtl" }); t.textContent = "↑ חוזק מול S&P 500 ב-5 ימים"; g.appendChild(t);
    [[sx(L.X1) - 8, P.t + 16, "end", "מובילים"], [sx(L.X1) - 8, sy(L.Y0) - 10, "end", "נחלשים"], [sx(L.X0) + 8, sy(L.Y0) - 10, "start", "מפגרים"], [sx(L.X0) + 8, P.t + 16, "start", "מתאוששים"]]
      .forEach(function (q) { t = mtEl("text", { x: q[0], y: q[1], class: "rw-qt", "text-anchor": q[2] }); t.textContent = q[3]; g.appendChild(t); });
    var n = days.length, last = days[n - 1], pts = [];
    var step = RW.mode === "week" ? 1 : 5, cnt = RW.mode === "week" ? 4 : 4;
    // 10.10.2026 (איציק, שלושה סבבים): שני צבעים, שתי שאלות. הקו = התנועה האחרונה *על הגרף* — הקטע האחרון של
    // השביל (יום בתצוגת השבוע, שבוע בתצוגת החודש), שני הצירים יחד: "ירדה מהמובילים לנחלשים" = אדום.
    // העיגול = מול המדד לאורך התקופה (סימן rs5 לשבוע, rs20 לחודש). הצבעים קבועים, לא רק בריחוף.
    // (ניסיון קודם באותו יום: הקו לפי המחיר של הסקטור — טכנולוגיה עלתה 5.9% בחודש ויצאה ירוקה למרות שעל הגרף ירדה.)
    var win = RW.mode === "week" ? 5 : 20;
    function sgn(v) { return v == null ? "" : v > 0.05 ? "up" : v < -0.05 ? "down" : ""; }
    Object.keys(last.rs).forEach(function (k) {
      var cur = last.rs[k]; if (cur[0] == null || cur[1] == null) return;
      var tr = [];
      for (var i = cnt; i >= 0; i--) { var j = n - 1 - i * step; if (j >= 0 && days[j].rs[k] && days[j].rs[k][0] != null) tr.push(days[j]); }
      var rsP = RW.mode === "week" ? cur[0] : cur[1], dotDir = sgn(rsP);
      var pv = tr.length > 1 ? tr[tr.length - 2].rs[k] : null, lastMove = pv ? (cur[0] + cur[1]) - (pv[0] + pv[1]) : null, lineDir = sgn(lastMove);
      var tg = mtEl("g", { class: "rw-tg", "data-k": k });
      if (tr.length > 1) {
        tg.appendChild(mtEl("path", { class: "rw-trail " + lineDir, "data-k": k, d: tr.map(function (d, i) { return (i ? "L" : "M") + sx(cl(d.rs[k][1], L.X0, L.X1)) + "," + sy(cl(d.rs[k][0], L.Y0, L.Y1)); }).join(" ") }));
        tr.slice(0, -1).forEach(function (d) { tg.appendChild(mtEl("circle", { class: "rw-tdot " + lineDir, "data-k": k, cx: sx(cl(d.rs[k][1], L.X0, L.X1)), cy: sy(cl(d.rs[k][0], L.Y0, L.Y1)), r: 3.5 })); });
      }
      g.appendChild(tg);
      var prev1 = n >= 2 && days[n - 2].rs[k], prev5 = n >= 6 && days[n - 6].rs[k];
      // כיוון השביל לאורך התקופה (29.9, איציק): תחילת השביל מול סופו על שני הצירים יחד (rs5+rs20) — ירוק השתפר, אדום נחלש
      var first = tr.length > 1 ? tr[0].rs[k] : null, tdf = first ? (cur[0] + cur[1]) - (first[0] + first[1]) : null;
      var dir = tdf == null ? "" : tdf > 0.05 ? "up" : tdf < -0.05 ? "down" : "";   // |שינוי| ≤ 0.05 = ללא שינוי (נשאר כחול)
      pts.push({ k: k, x: sx(cl(cur[1], L.X0, L.X1)), y: sy(cl(cur[0], L.Y0, L.Y1)), rs5: cur[0], rs20: cur[1], dir: dir, lineDir: lineDir, dotDir: dotDir, lastMove: lastMove, rsP: rsP, win: win,
                 tdiff: first ? (cur[0] + cur[1]) - (first[0] + first[1]) : null, tdays: tr.length - 1,
                 d1: prev1 ? [cur[0] - prev1[0], cur[1] - prev1[1]] : null, d5: prev5 ? [cur[0] - prev5[0], cur[1] - prev5[1]] : null });
    });
    // תוויות: מעל הנקודה; בהתנגשות — לצדדים/מתחת
    var placed = []; pts.sort(function (a, b) { return a.x - b.x; });
    pts.forEach(function (p) {
      var name = SECTOR_HE[p.k] || p.k, w = name.length * (mobile ? 6.5 : 7) + 6;
      var cands = [[p.x, p.y - 12, "middle"], [p.x + 10, p.y + 4, "start"], [p.x - 10, p.y + 4, "end"], [p.x, p.y + 18, "middle"], [p.x + 10, p.y - 9, "start"], [p.x - 10, p.y - 9, "end"]];
      for (var c = 0; c < cands.length; c++) {
        var cx = cands[c][0], cy = cands[c][1], an = cands[c][2], x0 = an === "middle" ? cx - w / 2 : an === "start" ? cx : cx - w, x1 = x0 + w, ok = true;
        for (var q = 0; q < placed.length; q++) { var r = placed[q]; if (x0 < r.x1 + 4 && x1 > r.x0 - 4 && Math.abs(cy - r.y) < 13) { ok = false; break; } }
        if (ok) { p.lx = cx; p.ly = cy; p.la = an; placed.push({ x0: x0, x1: x1, y: cy }); break; }
      }
      if (p.lx == null) { p.lx = p.x; p.ly = p.y - 12; p.la = "middle"; }
    });
    var live = rwLive(), lg = document.getElementById("rw-lg-now");
    if (lg) lg.hidden = !live;
    pts.forEach(function (p) {
      if (live && live[p.k] != null) {
        p.now = [p.rs5 + live[p.k], p.rs20 + live[p.k]]; p.dnow = live[p.k];
        var nx = sx(cl(p.now[1], L.X0, L.X1)), ny = sy(cl(p.now[0], L.Y0, L.Y1));
        g.appendChild(mtEl("line", { class: "rw-now-ln", "data-k": p.k, x1: p.x, y1: p.y, x2: nx, y2: ny }));
        g.appendChild(mtEl("circle", { class: "rw-now", "data-k": p.k, cx: nx, cy: ny, r: mobile ? 5 : 5.5 }));
      }
      g.appendChild(mtEl("circle", { class: "rw-dot " + p.dotDir, "data-k": p.k, cx: p.x, cy: p.y, r: mobile ? 5.5 : 6 }));
      t = mtEl("text", { class: "rw-lbl", "data-k": p.k, x: p.lx, y: p.ly, "text-anchor": p.la }); t.textContent = SECTOR_HE[p.k] || p.k; g.appendChild(t);
    });
    function show(p) {
      var q = rwQuad(p.rs5, p.rs20), name = SECTOR_HE[p.k] || p.k;
      tip.innerHTML = "";
      var b = document.createElement("b"); b.textContent = name; tip.appendChild(b);
      var qd = document.createElement("div"); qd.className = "rw-qd " + q[1]; qd.textContent = q[0]; tip.appendChild(qd);
      [["5 ימים מול המדד", p.rs5, p.d1 && p.d1[0], p.d5 && p.d5[0]], ["20 יום מול המדד", p.rs20, p.d1 && p.d1[1], p.d5 && p.d5[1]]].forEach(function (r) {
        var d = document.createElement("div"); d.textContent = r[0] + ": ";
        var nn = document.createElement("span"); nn.className = "num"; nn.textContent = rwFmt(r[1]); d.appendChild(nn); tip.appendChild(d);
        var sub = document.createElement("div"); sub.className = "rw-sub";
        sub.textContent = "מול אתמול " + (r[2] == null ? "—" : rwFmt(r[2])) + " · מול לפני שבוע " + (r[3] == null ? "—" : rwFmt(r[3])); tip.appendChild(sub);
      });
      if (p.now) { var nw = document.createElement("div"); nw.className = "rw-now-t"; nw.textContent = "עכשיו (אומדן חי): " + rwFmt(p.dnow) + " מול המדד היום → " + rwQuad(p.now[0], p.now[1])[0]; tip.appendChild(nw); }
      var wn = rwWeeklyNote(name); if (wn) { var w = document.createElement("div"); w.className = "rw-sub rw-wn"; w.textContent = wn; tip.appendChild(w); }
      var per = p.win === 5 ? "5 ימים" : "20 יום";
      if (p.lastMove != null) { var tl = document.createElement("div"); tl.className = "rw-sub rw-td " + p.lineDir; tl.textContent = "הקו · התנועה האחרונה על הגרף (" + (p.win === 5 ? "מאתמול" : "מלפני שבוע") + "): " + rwFmt(p.lastMove) + (p.lineDir === "up" ? " (עלה)" : p.lineDir === "down" ? " (ירד)" : " (ללא שינוי)") + " · שני הצירים יחד"; tip.appendChild(tl); }
      var td = document.createElement("div"); td.className = "rw-sub rw-td " + p.dotDir; td.textContent = "העיגול · מול המדד ב-" + per + ": " + rwFmt(p.rsP) + (p.dotDir === "up" ? " (הכה את המדד)" : p.dotDir === "down" ? " (פיגר אחרי המדד)" : ""); tip.appendChild(td);
      tip.style.display = "block";
      // 29.9 (איציק): ההסבר בפינה הריקה שממול לסקטור, לא על השביל שלו
      var r = svg.getBoundingClientRect(), sc = r.width / W;
      var plotL = P.l * sc, plotR = (W - P.r) * sc, plotT = P.t * sc, plotB = (H - P.b) * sc, midX = (plotL + plotR) / 2, midY = (plotT + plotB) / 2;
      var tw = Math.min(230, r.width - 20), th = tip.offsetHeight || 150;
      tip.style.left = (p.x * sc < midX ? plotR - tw - 8 : plotL + 8) + "px";
      tip.style.top = (p.y * sc < midY ? plotB - th - 8 : plotT + 8) + "px";
      svg.classList.add("focus");
      svg.querySelectorAll("[data-k]").forEach(function (x) { x.classList.toggle("hl", x.dataset.k === p.k); });
    }
    function hide() { tip.style.display = "none"; svg.classList.remove("focus"); svg.querySelectorAll(".hl").forEach(function (x) { x.classList.remove("hl"); }); }
    pts.forEach(function (p) {
      var h = mtEl("circle", { class: "rw-hit", cx: p.x, cy: p.y, r: 18, tabindex: 0 });
      h.addEventListener("pointerenter", function () { show(p); }); h.addEventListener("pointerleave", hide);
      h.addEventListener("focus", function () { show(p); }); h.addEventListener("blur", hide);
      g.appendChild(h);
    });
    svg.addEventListener("pointerleave", hide);
    var f = document.getElementById("rw-foot"), ld = last.date.split("-");
    if (f) f.textContent = "חוזק יחסי של 11 סקטורי S&P מול המדד, מהדשבורד, עד סגירת " + (+ld[2]) + "." + (+ld[1]) + " · " + n + " ימי מסחר בארכיון. " +
      (RW.mode === "week" ? "השביל: 5 ימי המסחר האחרונים, יום-יום." : "השביל: איפה הסקטור עמד לפני שבוע, שבועיים, שלושה, חודש.") + " צבע הקו = לאן הסקטור זז על הגרף בקטע האחרון של השביל (יום בשבוע, שבוע בחודש): ירוק עלה, אדום ירד; צבע העיגול = האם הכה את המדד או פיגר אחריו לאורך התקופה. ריחוף או נגיעה על סקטור: המספרים, מול אתמול ומול לפני שבוע." + (live ? " הנקודה החלולה = אומדן חי מהמסחר של היום (השינוי היומי של הסקטור פחות של המדד), מתעדכן כל דקה." : "");
    document.querySelectorAll(".rw-chip").forEach(function (c) {
      c.onclick = function () {
        if (c.dataset.rw === "all") { RW.all = !RW.all; c.classList.toggle("on", RW.all); svg.classList.toggle("all", RW.all); return; }
        RW.mode = c.dataset.rw; document.querySelectorAll('.rw-chip[data-rw="week"],.rw-chip[data-rw="month"]').forEach(function (x) { x.classList.toggle("on", x.dataset.rw === RW.mode); });
        renderRotationWheel();
      };
    });
  }
  function refreshRotationWheel() {
    var slot = document.getElementById("rw-slot");
    if (!slot) return;
    if (!document.getElementById("rw-svg")) slot.innerHTML = rotationWheelHtml();
    renderRotationWheel();
  }

  /* שלב 7 (10.10.2026): תבנית אחת לארבע לשוניות הדוחות (סקטורים · הצעות לטרייד · Insider · Barchart):
     פאנל-כותרת (שם הדוח + תאריך + "מסך מלא") עם צ'יפי ארכיון, ומתחתיו פאנל שמחזיק את ה-iframe. */
  function repChips(cls, reps, lab, sel) {
    if (reps.length < 2) return "";
    return '<div class="chips bd-chips rep-arch">' + reps.map(function (r, i) {
      return '<button type="button" class="tag ' + cls + (i === (sel || 0) ? " on" : "") + '" data-i="' + i + '" aria-pressed="' + (i === (sel || 0)) + '"><span class="num" dir="ltr">' + esc(lab(r)) + "</span></button>";
    }).join("") + "</div>";
  }
  function repFrame(file, meta, title) {
    return '<div class="frame-scroll"><iframe class="brief-frame trd-frame rep-frame" src="' + bust(file, meta) + '" title="' + esc(title || "") +
      '" style="width:100%;min-height:640px" onload="__fitFrame(this)"></iframe></div>';
  }
  function repFull(file) { return '<a class="go" href="' + esc(file) + '" target="_blank" rel="noopener">מסך מלא</a>'; }
  function bindRepChips(el, cls, show) {
    el.querySelectorAll("." + cls).forEach(function (b) {
      b.addEventListener("click", function () {
        el.querySelectorAll("." + cls).forEach(function (x) { var on = x === b; x.classList.toggle("on", on); x.setAttribute("aria-pressed", on); });
        show(+b.dataset.i);
      });
    });
  }
  function renderSectors(el, d) {
    SECT = d;
    var reps = (d && d.reports) || [];
    if (!reps.length) {
      emptyPanel(el, "🔄", "דוח סקטורים — בקרוב", "הדוח השבועי הראשון בדרך.");
      return;
    }
    el.innerHTML = '<div class="board">' +
      '<section class="pan" id="rw-slot"' + bdSpan(12) + ">" + rotationWheelHtml() + "</section>" +
      '<section class="pan" id="sec-view"' + bdSpan(12) + "></section></div>";
    renderRotationWheel();
    showSector(0);
  }
  function showSector(i) {
    var view = document.getElementById("sec-view");
    if (!view || !SECT) return;
    var r = (SECT.reports || [])[i];
    if (!r) return;
    var reps = SECT.reports || [];
    view.innerHTML = panHd("דוח הסקטורים השבועי", '<span class="mute">' + esc(r.title) + ' · שבוע שהסתיים ב-<span class="num" dir="ltr">' + esc(secDate(r.date)) + "</span></span>", repFull(r.file)) +
      (reps.length > 1 ? '<div class="pb">' + repChips("sec-tab", reps, function (x) { return secDate(x.date); }, i) + "</div>" : "") +
      repFrame(r.file, SECT._meta, r.title);
    bindRepChips(view, "sec-tab", showSector);
  }

  /* טאב "Insider" (20.9.2026) — דוחות קניות של בעלי עניין מ-nidam-reports/insider.
     כמו סקטורים: הדוח האחרון מוצג, הקודמים נשמרים כצ'יפים (scripts/fetch_insider.py ממזג היסטוריה). */
  /* ---------- לקראת הדוח (2.10.2026, np103, איציק — אושר במוקאפ JPM) ----------
     data/earnings_prep.json = המספרים (scripts/build_earnings_prep.py, כל רבע שעה): חברות שיש להן ניתוח
     דוח קודם באתר ומדווחות בשבועיים הקרובים — צפי אנליסטים, היסטוריית הפתעות + תגובת המניה, מחירי יעד,
     התזוזה שהאופציות מתמחרות, מחיר מאז הדוח הקודם. data/earnings_prep_notes.json = המילים (הרוטינה
     היומית לפי scripts/prompts/earnings_prep.md): משפט מוביל, תחזית ההנהלה, 5 בדיקות, חולשות, תרחישים. */
  var PREPD = null, PREPN = null, PREPR = null;
  var EP_DOW = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"];
  function epDate(iso) { var p = iso.split("-"); return (+p[2]) + "." + (+p[1]); }
  function epDow(iso) { return EP_DOW[new Date(iso + "T12:00:00Z").getUTCDay()]; }
  function epWhen(it) {
    return it.when === "before" ? "לפני הפתיחה" : it.when === "after" ? "אחרי הסגירה" : "שעה לא ידועה";
  }
  function epMoney(v) {
    if (v == null) return "—";
    var a = Math.abs(v);
    return "$" + (a >= 1e12 ? (v / 1e12).toFixed(2) + "T" : a >= 1e9 ? (v / 1e9).toFixed(1) + "B" : a >= 1e6 ? (v / 1e6).toFixed(0) + "M" : Number(v).toFixed(2));
  }
  function epLogo(it, big) {
    var r = it.report || {};
    // הטיקר כטקסט מתחת ללוגו — אם התמונה לא נטענת היא נמחקת והטקסט נשאר
    return '<span class="ep-logo' + (big ? " big" : "") + '">' + esc(it.sym) +
      (r.logo ? '<img class="' + (r.logoBg === "dark" ? "dk" : "") + '" src="' + esc(r.logo) + '" alt="" onerror="this.remove()">' : "") + "</span>";
  }
  function epQuarter(q) { var p = q.split("-"); return ["", "ינו'", "פבר'", "מרץ", "אפר'", "מאי", "יוני", "יולי", "אוג'", "ספט'", "אוק'", "נוב'", "דצמ'"][+p[1]] + " " + p[0].slice(2); }
  function epReactSvg(it) {
    var h = (it.history || []).filter(function (x) { return x.move != null; });
    if (!h.length) return "";
    var band = it.options && it.options.earn, top = Math.max(band || 0, 1);
    h.forEach(function (x) { top = Math.max(top, Math.abs(x.move)); });
    var W = 400, H = 200, mid = 92, k = 70 / top, L = 40, R = 385, w = 56, gap = (R - L - 20 - w) / Math.max(h.length - 1, 1);
    var Y = function (v) { return mid - v * k; };
    var s = '<svg class="ep-chart" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="תגובת המניה בדוחות הקודמים">';
    if (band) {
      s += '<rect x="' + L + '" y="' + Y(band) + '" width="' + (R - L) + '" height="' + (Y(-band) - Y(band)) + '" style="fill:var(--ep-band)"/>' +
        '<text x="' + (L + 2) + '" y="' + (Y(band) - 6) + '" font-size="10.5" text-anchor="start" style="fill:var(--accent)">±' + band.toFixed(1) + "% — מה שהאופציות מתמחרות לדוח הבא</text>";
    }
    s += '<line x1="' + L + '" x2="' + R + '" y1="' + mid + '" y2="' + mid + '" style="stroke:var(--border)"/>';
    h.forEach(function (x, i) {
      var cx = L + 20 + i * gap, v = x.move, col = v >= 0 ? "var(--up)" : "var(--down)";
      s += '<rect x="' + cx + '" y="' + Math.min(Y(v), mid) + '" width="' + w + '" height="' + Math.max(Math.abs(Y(v) - mid), 1) + '" rx="3" style="fill:' + col + '"/>' +
        '<text x="' + (cx + w / 2) + '" y="' + (v >= 0 ? Y(v) - 5 : Y(v) + 13) + '" font-size="11.5" font-weight="700" text-anchor="middle" style="fill:' + col + '">' + (v > 0 ? "+" : "") + v.toFixed(1) + "%</text>" +
        '<text x="' + (cx + w / 2) + '" y="194" font-size="11" text-anchor="middle" style="fill:var(--text-3)">' + esc(epDate(x.day || x.q)) + "</text>";
    });
    return s + "</svg>";
  }
  function epPriceSvg(it) {
    var p = it.price || {}, ser = p.series || [];
    if (ser.length < 2) return "";
    var c = ser.map(function (x) { return x[1]; });
    var lo = Math.min.apply(null, c), hi = Math.max.apply(null, c), padv = (hi - lo) * 0.08 || 1;
    lo -= padv; hi += padv;
    var W = 960, H = 220, L = 52, R = 900, T = 18, B = 190, n = c.length - 1;
    var X = function (i) { return L + i / n * (R - L); }, Y = function (v) { return B - (v - lo) / (hi - lo) * (B - T); };
    var d = c.map(function (v, i) { return (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(v).toFixed(1); }).join("");
    var s = '<svg class="ep-chart" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="מחיר המניה ב-80 ימי המסחר האחרונים">';
    var step = Math.pow(10, Math.floor(Math.log10((hi - lo) / 3))), t0 = Math.ceil(lo / step) * step;
    for (var t = t0; t < hi; t += step * Math.max(1, Math.round((hi - lo) / 3 / step))) {
      s += '<line x1="' + L + '" x2="' + R + '" y1="' + Y(t) + '" y2="' + Y(t) + '" style="stroke:var(--border-soft)"/>' +
        '<text x="' + (L - 8) + '" y="' + (Y(t) + 4) + '" font-size="11" text-anchor="end" style="fill:var(--text-3)">$' + Math.round(t) + "</text>";
    }
    s += '<path d="' + d + "L" + X(n) + " " + B + "L" + X(0) + " " + B + 'Z" style="fill:var(--ep-band)"/>' +
      '<path d="' + d + '" style="fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round"/>';
    var rd = p.since && p.since.from ? ser.findIndex(function (x) { return x[0] > p.since.from; }) : -1;
    if (rd > 0) {
      var lastH = (it.history || []).filter(function (x) { return x.move != null; }).slice(-1)[0];
      s += '<line x1="' + X(rd) + '" x2="' + X(rd) + '" y1="' + T + '" y2="' + B + '" style="stroke:var(--pk-gold,#b7861c);stroke-width:1.5;stroke-dasharray:4 4"/>' +
        '<text x="' + (X(rd) + 6) + '" y="' + (T + 10) + '" font-size="11.5" font-weight="700" text-anchor="start" style="fill:var(--pk-gold,#b7861c)">הדוח הקודם' +
        (lastH ? " · " + (lastH.move > 0 ? "+" : "") + lastH.move.toFixed(1) + "%" : "") + "</text>";
    }
    s += '<circle cx="' + X(n) + '" cy="' + Y(c[n]) + '" r="4.5" style="fill:var(--accent)"/>' +
      '<text x="' + (X(n) - 8) + '" y="' + (Y(c[n]) + 18) + '" font-size="12" font-weight="700" text-anchor="end" style="fill:var(--text)">' + c[n].toFixed(2) + "</text>";
    [0, Math.round(n / 3), Math.round(2 * n / 3), n].forEach(function (i) {
      s += '<text x="' + X(i) + '" y="' + (B + 18) + '" font-size="11" text-anchor="' + (i === 0 ? "start" : i === n ? "end" : "middle") + '" style="fill:var(--text-3)">' + esc(epDate(ser[i][0])) + "</text>";
    });
    return s + "</svg>";
  }
  function epTarget(it) {
    var t = it.targets || {}, px = it.price && it.price.close;
    if (!t.mean || !t.low || !t.high || !px) return "";
    var lo = Math.min(t.low, px) * 0.98, hi = Math.max(t.high, px) * 1.02;
    var X = function (v) { return 12 + (v - lo) / (hi - lo) * 376; };
    return '<svg class="ep-tgt" viewBox="0 0 400 58" role="img" aria-label="מחיר יעד ממוצע ' + t.mean.toFixed(0) + " מול מחיר " + px.toFixed(0) + '">' +
      '<line x1="' + X(t.low) + '" x2="' + X(t.high) + '" y1="26" y2="26" stroke-width="8" stroke-linecap="round" style="stroke:var(--surface-3)"/>' +
      '<line x1="' + X(Math.min(px, t.mean)) + '" x2="' + X(Math.max(px, t.mean)) + '" y1="26" y2="26" stroke-width="8" style="stroke:' + (t.mean >= px ? "var(--up)" : "var(--down)") + ';opacity:.35"/>' +
      '<circle cx="' + X(t.mean) + '" cy="26" r="6" style="fill:' + (t.mean >= px ? "var(--up)" : "var(--down)") + '"/>' +
      '<rect x="' + (X(px) - 1.5) + '" y="14" width="3" height="24" style="fill:var(--text)"/>' +
      '<text x="' + X(t.low) + '" y="52" font-size="11" text-anchor="start" style="fill:var(--text-3)">' + Math.round(t.low) + "</text>" +
      '<text x="' + X(t.high) + '" y="52" font-size="11" text-anchor="end" style="fill:var(--text-3)">' + Math.round(t.high) + "</text>" +
      '<text x="' + X(px) + '" y="10" font-size="11" font-weight="700" text-anchor="middle" style="fill:var(--text)">מחיר ' + Math.round(px) + "</text>" +
      '<text x="' + X(t.mean) + '" y="52" font-size="11" font-weight="700" text-anchor="middle" style="fill:' + (t.mean >= px ? "var(--up)" : "var(--down)") + '">יעד ממוצע ' + Math.round(t.mean) + "</text></svg>";
  }
  function epCard(it) {
    var n = (PREPN && PREPN[it.sym] && PREPN[it.sym].forDate === it.date) ? PREPN[it.sym] : null;
    var c = it.consensus || {}, o = it.options || {}, p = it.price || {}, rec = it.recs || {}, rv = it.revisions || {}, tg = it.targets || {};
    var rep = it.report || {};
    var head = '<header class="ep-head">' + epLogo(it, true) +
      '<div class="ep-who"><div class="ep-name">' + esc(it.name || it.sym) + ' <small dir="ltr">' + esc(it.sym) + "</small></div>" +
      '<div class="ep-when"><span class="ep-pill hot">' + epDow(it.date) + " " + epDate(it.date) + " · " + epWhen(it) + "</span>" +
      '<span class="ep-pill">' + (it.daysTo > 0 ? "עוד " + it.daysTo + " ימים" : it.daysTo === 0 ? "היום" : "התגובה היום") + "</span></div></div>" +
      (rep.file ? '<button class="ep-rep" onclick="__goTab(\'reports\')">הניתוח של הדוח הקודם (' + esc(epDate(rep.date || "")) + ") ←</button>" : "") + "</header>";
    var words = n
      ? '<h3 class="ep-thesis">' + esc(n.thesis) + "</h3>" + (n.dek ? '<p class="ep-dek">' + esc(n.dek) + "</p>" : "")
      : '<p class="ep-wait">ההכנה המילולית (מה ההנהלה הבטיחה, מה לבדוק, חולשות) תיכתב בבוקר שלפני שבוע הדוח. המספרים כבר כאן.</p>';
    var epsG = c.eps != null && c.epsYearAgo ? (c.eps / c.epsYearAgo - 1) * 100 : null;
    var revG = c.rev != null && c.revYearAgo ? (c.rev / c.revYearAgo - 1) * 100 : null;
    var stats = '<div class="ep-stats">' +
      '<div class="ep-stat"><span class="k">צפי רווח למניה</span><span class="v num" dir="ltr">' + (c.eps != null ? "$" + c.eps.toFixed(2) : "—") + "</span>" +
        '<span class="s">' + (epsG != null ? '<span class="num" dir="ltr">' + pkPct(epsG, 0) + "</span> משנה שעברה" : "") + (c.epsN ? " · " + c.epsN + " אנליסטים" : "") + "</span></div>" +
      '<div class="ep-stat"><span class="k">צפי הכנסות</span><span class="v num" dir="ltr">' + epMoney(c.rev) + "</span>" +
        '<span class="s">' + (revG != null ? '<span class="num" dir="ltr">' + pkPct(revG, 1) + "</span> משנה שעברה" : "") + "</span></div>" +
      '<div class="ep-stat"><span class="k">תזוזה שהאופציות מתמחרות</span><span class="v num" dir="ltr">' + (o.earn != null ? "±" + o.earn.toFixed(1) + "%" : "—") + "</span>" +
        '<span class="s">' + (o.pct != null ? 'ליום הדוח · <span class="num" dir="ltr">±' + o.pct.toFixed(1) + "%</span> עד פקיעת " + esc(epDate(o.exp)) : "מתעדכן בשעות המסחר") + "</span></div>" +
      '<div class="ep-stat"><span class="k">תזוזה ממוצעת בדוחות</span><span class="v num" dir="ltr">' + (it.avgMove != null ? it.avgMove.toFixed(1) + "%" : "—") + "</span>" +
        '<span class="s">ממוצע ' + ((it.history || []).filter(function (x) { return x.move != null; }).length) + " הדוחות האחרונים</span></div></div>";
    var sec = [];
    if (n && ((n.guidance || []).length || n.guidanceNote)) {
      sec.push('<section class="ep-sec"><h4>מה ההנהלה הבטיחה <small>מהדוח של ' + esc(epDate(rep.date || "")) + "</small></h4>" +
        ((n.guidance || []).length ? '<table class="ep-tbl"><tr><th>מדד</th><th class="r">התחזית</th><th class="r">לפני כן</th></tr>' +
          n.guidance.map(function (g) { return "<tr><td>" + esc(g.metric) + '</td><td class="r num" dir="ltr">' + esc(g.value) + '</td><td class="r num" dir="ltr">' + esc(g.prev || "—") + "</td></tr>"; }).join("") + "</table>" : "") +
        (n.guidanceNote ? '<p class="ep-cap">' + esc(n.guidanceNote) + "</p>" : "") + "</section>");
    }
    if (n && (n.checks || []).length) {
      sec.push('<section class="ep-sec"><h4>' + (n.checks.length === 5 ? "חמשת המספרים לבדוק" : "המספרים לבדוק") + '</h4><ol class="ep-check">' +
        n.checks.map(function (x) { return "<li><span><b>" + esc(x.title) + '</b><span class="t">' + esc(x.text) + "</span></span></li>"; }).join("") + "</ol></section>");
    }
    var recTot = (rec.strongBuy || 0) + (rec.buy || 0) + (rec.hold || 0) + (rec.sell || 0) + (rec.strongSell || 0);
    if (recTot || tg.mean) {
      var acts = (it.actions || []).slice(0, 4);
      sec.push('<section class="ep-sec"><h4>מה האנליסטים חושבים <small>' + (recTot ? recTot + " אנליסטים · " : "") + "Yahoo Finance</small></h4>" +
        (recTot ? '<div class="ep-rbar" role="img" aria-label="' + (rec.strongBuy || 0) + " קנייה חזקה, " + (rec.buy || 0) + " קנייה, " + (rec.hold || 0) + " החזקה, " + ((rec.sell || 0) + (rec.strongSell || 0)) + ' מכירה">' +
          '<i class="sb" style="flex:' + (rec.strongBuy || 0) + '"></i><i class="b" style="flex:' + (rec.buy || 0) + '"></i><i class="h" style="flex:' + (rec.hold || 0) + '"></i><i class="s" style="flex:' + ((rec.sell || 0) + (rec.strongSell || 0)) + '"></i></div>' +
          '<div class="ep-rlab"><span class="sb">קנייה חזקה ' + (rec.strongBuy || 0) + '</span><span class="b">קנייה ' + (rec.buy || 0) + '</span><span class="h">החזקה ' + (rec.hold || 0) + '</span><span class="s">מכירה ' + ((rec.sell || 0) + (rec.strongSell || 0)) + "</span></div>" : "") +
        epTarget(it) +
        (rv.up30 != null ? '<p class="ep-cap">ב-30 הימים האחרונים ' + (rv.up30 || 0) + " אנליסטים העלו את צפי הרווח לרבעון ו-" + (rv.down30 || 0) + " הורידו.</p>" : "") +
        (acts.length ? '<table class="ep-tbl sm"><tr><th>תאריך</th><th>בית השקעות</th><th class="r">מחיר יעד</th></tr>' + acts.map(function (a) {
          return '<tr><td class="num">' + esc(epDate(a.date)) + "</td><td>" + esc(a.firm || "") + (a.grade ? " · " + esc(a.grade) : "") + '</td><td class="r num" dir="ltr">' +
            (a.ptPrev ? Math.round(a.ptPrev) + " → " : "") + (a.pt ? Math.round(a.pt) : "—") + "</td></tr>";
        }).join("") + "</table>" : "") + "</section>");
    }
    var hist = it.history || [];
    if (hist.length) {
      var beats = hist.filter(function (x) { return x.surprise > 0; }).length, ups = hist.filter(function (x) { return x.move > 0; }).length, nm = hist.filter(function (x) { return x.move != null; }).length;
      sec.push('<section class="ep-sec"><h4>עמידה בציפיות ותגובת המניה <small>יום התגובה, סגירה מול סגירה</small></h4>' + epReactSvg(it) +
        '<table class="ep-tbl"><tr><th>רבעון</th><th class="r">רווח בפועל / צפי</th><th class="r">הפתעה</th><th class="r">המניה</th></tr>' +
        hist.map(function (x) {
          return "<tr><td>" + esc(epQuarter(x.q)) + '</td><td class="r num" dir="ltr">' + (x.actual != null ? x.actual.toFixed(2) : "—") + " / " + (x.est != null ? x.est.toFixed(2) : "—") +
            '</td><td class="r num ' + (x.surprise > 0 ? "up" : x.surprise < 0 ? "down" : "") + '" dir="ltr">' + pkPct(x.surprise, 1) +
            '</td><td class="r num ' + (x.move > 0 ? "up" : x.move < 0 ? "down" : "") + '" dir="ltr">' + pkPct(x.move, 1) + "</td></tr>";
        }).join("") + "</table>" +
        '<p class="ep-cap">עקפה את הצפי ב-' + beats + " מתוך " + hist.length + "; המניה עלתה ב-" + ups + " מתוך " + nm + " ימי התגובה.</p></section>");
    }
    var grid = sec.length ? '<div class="ep-grid">' + sec.join("") + "</div>" : "";
    var price = p.series ? '<section class="ep-sec ep-wide"><h4>איפה המניה עומדת <small>סגירה ' + esc(epDate(p.date)) + "</small></h4>" + epPriceSvg(it) +
      '<p class="ep-cap"><span class="num" dir="ltr">$' + p.close.toFixed(2) + "</span>" +
      (p.since ? ' · מאז ערב הדוח הקודם <span class="num ' + (p.since.chg >= 0 ? "up" : "down") + '" dir="ltr">' + pkPct(p.since.chg, 1) + "</span>" +
        (p.since.spy != null ? ' (S&amp;P 500 <span class="num" dir="ltr">' + pkPct(p.since.spy, 1) + "</span>)" : "") : "") +
      ' · <span class="num" dir="ltr">' + Math.abs(p.off52).toFixed(1) + "%</span> מתחת לשיא 52 שבועות" +
      " · " + (p.close >= p.ma50 ? "מעל" : "מתחת ל") + 'ממוצע 50 יום (<span class="num" dir="ltr">$' + p.ma50.toFixed(1) + "</span>)" +
      (tg.mean ? " · מחיר היעד הממוצע " + (tg.mean >= p.close ? "גבוה" : "נמוך") + ' ב-<span class="num" dir="ltr">' + Math.abs((tg.mean / p.close - 1) * 100).toFixed(1) + "%</span>" : "") + "</p></section>" : "";
    var after = "";
    if (n && ((n.weaknesses || []).length || n.bull || n.bear)) {
      after = '<div class="ep-grid">' +
        ((n.weaknesses || []).length ? '<section class="ep-sec"><h4>נקודות החולשה מהפעם הקודמת</h4><ul class="ep-dots">' + n.weaknesses.map(function (w) { return "<li>" + esc(w) + "</li>"; }).join("") + "</ul></section>" : "") +
        (n.bull || n.bear ? '<section class="ep-sec"><h4>מה לחפש ביום הדוח</h4><div class="ep-scen">' +
          (n.bull ? '<div class="g"><b>מה יחזק</b>' + esc(n.bull) + "</div>" : "") + (n.bear ? '<div class="r"><b>מה יחליש</b>' + esc(n.bear) + "</div>" : "") + "</div></section>" : "") + "</div>";
    }
    var foot = '<div class="ep-foot"><span>מקורות: ניתוח הדוח הקודם (האתר) · צפי ואנליסטים: Yahoo Finance · אופציות: Yahoo' +
      (o.asOf ? ", " + esc(o.asOf) : "") + " · מחירים: נרות יומיים" + (n && n.writtenAt ? " · ההכנה נכתבה " + esc(n.writtenAt) : "") + ".</span>" +
      "<span>התזוזה ליום הדוח = הסטראדל לפקיעה הראשונה אחרי הדוח, בניכוי התנודה הרגילה. תאריכי הדוחות הקודמים והרווח מול הצפי: Nasdaq; יום התגובה = יום הדוח (לפני הפתיחה) או המחרת (אחרי הסגירה). תיאור מבוסס נתונים, לא ייעוץ השקעות.</span></div>";
    return '<article class="ep-card" id="ep-' + esc(it.sym) + '">' + head + words + stats + grid + price + after + foot + "</article>";
  }
  /* "אחרי הדוח" (9.10.2026, איציק): כשהניתוח החדש עולה, הכרטיס של החברה עובר לכאן — ההכנה מול מה שקרה.
     המספרים (צפי ותזוזה מתומחרת לפני הדוח, התגובה בפועל) מ-earnings_prep.json.recent (build_earnings_prep שומר
     תמונת "לפני" ב-_prep_snap.json); המילים מ-earnings_review_notes.json שהרוטינה כותבת (scripts/prompts/earnings_review.md). */
  var EP_MARK = { hit: ["✓", "פגע ברף"], miss: ["✗", "לא עמד ברף"], mixed: ["~", "חלקי"] };
  var EP_SCEN = { bull: "קרוב לתרחיש החיובי", bear: "קרוב לתרחיש השלילי", mixed: "באמצע בין התרחישים" };
  function epReviewCard(rc) {
    var r = (PREPR && PREPR[rc.sym] && PREPR[rc.sym].forDate === rc.date) ? PREPR[rc.sym] : null;
    var pn = (PREPN && PREPN[rc.sym] && PREPN[rc.sym].forDate === rc.date) ? PREPN[rc.sym] : null;
    var o = rc.options || {}, c = rc.consensus || {}, re = rc.reaction || {}, nr = rc.newReport;
    var head = '<header class="ep-head">' + epLogo(rc, true) +
      '<div class="ep-who"><div class="ep-name">' + esc(rc.name || rc.sym) + ' <small dir="ltr">' + esc(rc.sym) + "</small></div>" +
      '<div class="ep-when"><span class="ep-pill done">דיווחה · ' + epDow(rc.date) + " " + epDate(rc.date) + " · " + epWhen(rc) + "</span>" +
      (r ? '<span class="ep-pill sc-' + esc(r.scenario || "mixed") + '">' + esc(EP_SCEN[r.scenario] || EP_SCEN.mixed) + "</span>" : "") + "</div></div>" +
      (nr && nr.file ? '<button class="ep-rep" onclick="__openReport(\'' + esc(nr.file) + '\')">הניתוח החדש (' + esc(epDate(nr.date || "")) + ") ←</button>" : "") + "</header>";
    var words = r ? '<h3 class="ep-thesis">' + esc(r.headline) + "</h3>" + (r.scenarioText ? '<p class="ep-dek">' + esc(r.scenarioText) + "</p>" : "")
      : '<p class="ep-wait">' + (nr ? "ההשוואה המלאה (הבדיקות מול התוצאות, התחזית לפני ואחרי) תיכתב בבוקר הקרוב, מתוך הניתוח החדש." :
        "ההשוואה תיכתב אחרי שהניתוח החדש של הדוח יעלה לאתר. בינתיים: מה תומחר מול מה שקרה.") + "</p>";
    var marks = r ? (r.checks || []) : [];
    var cnt = { hit: 0, miss: 0, mixed: 0 };
    marks.forEach(function (x) { if (cnt[x.mark] != null) cnt[x.mark]++; });
    var mv = re.move, band = o.earn;
    var vsBand = mv != null && band != null ? (Math.abs(mv) > band ? "גדולה מהמתומחר" : "בתוך הטווח המתומחר") : (mv == null ? "מחכה לסגירת יום התגובה" : "");
    var stats = '<div class="ep-stats">' +
      '<div class="ep-stat"><span class="k">האופציות תמחרו</span><span class="v num" dir="ltr">' + (band != null ? "±" + band.toFixed(1) + "%" : "—") + '</span><span class="s">ליום הדוח' + (o.asOf ? " · " + esc(o.asOf) : "") + "</span></div>" +
      '<div class="ep-stat"><span class="k">התגובה בפועל</span><span class="v num ' + (mv > 0 ? "up" : mv < 0 ? "down" : "") + '" dir="ltr">' + (mv != null ? pkPct(mv, 1) : "—") + '</span><span class="s">' + esc(vsBand) + "</span></div>" +
      '<div class="ep-stat"><span class="k">צפי הרווח לפני הדוח</span><span class="v num" dir="ltr">' + (c.eps != null ? "$" + c.eps.toFixed(2) : "—") + '</span><span class="s">' + (c.epsLow != null ? 'טווח <span class="num" dir="ltr">' + c.epsLow.toFixed(2) + "–" + c.epsHigh.toFixed(2) + "</span>" : "") + "</span></div>" +
      '<div class="ep-stat"><span class="k">הבדיקות שקבענו</span><span class="v">' + (marks.length ? '<span class="ep-m hit">' + cnt.hit + '✓</span> <span class="ep-m mixed">' + cnt.mixed + '~</span> <span class="ep-m miss">' + cnt.miss + "✗</span>" : "—") +
        '</span><span class="s">' + (marks.length ? "מתוך " + marks.length : "מחכה להשוואה") + "</span></div></div>";
    var sec = [];
    if (marks.length) {
      var pre = {};
      ((pn && pn.checks) || []).forEach(function (x) { pre[x.title] = x.text; });
      sec.push('<section class="ep-sec ep-wide"><h4>מה בדקנו מול מה שקרה' + (pn && pn.writtenAt ? " <small>ההכנה נכתבה " + esc(pn.writtenAt) + "</small>" : "") + '</h4><ol class="ep-rv">' +
        marks.map(function (x) {
          var m = EP_MARK[x.mark] || EP_MARK.mixed;
          return '<li><span class="ep-m ' + esc(x.mark) + '" title="' + m[1] + '" aria-label="' + m[1] + '">' + m[0] + "</span><span><b>" + esc(x.title) + '</b><span class="t">' + esc(x.actual) + "</span>" +
            (pre[x.title] ? '<span class="was">לפני: ' + esc(pre[x.title]) + "</span>" : "") + "</span></li>";
        }).join("") + "</ol></section>");
    }
    if (r && (r.guidance || []).length) {
      sec.push('<section class="ep-sec"><h4>התחזית לפני ואחרי' + (r.guidanceDir === "down" ? ' <small class="down">הורדה</small>' : r.guidanceDir === "up" ? ' <small class="up">הועלתה</small>' : "") + "</h4>" +
        '<table class="ep-tbl"><tr><th>מדד</th><th class="r">לפני</th><th class="r">אחרי</th></tr>' +
        r.guidance.map(function (g) { return "<tr><td>" + esc(g.metric) + '</td><td class="r">' + esc(g.before || "—") + '</td><td class="r"><b>' + esc(g.after || "—") + "</b></td></tr>"; }).join("") + "</table></section>");
    }
    if (r && (r.nextChecks || []).length) {
      sec.push('<section class="ep-sec"><h4>מה בודקים ברבעון הבא <small>ייכנס להכנה הבאה</small></h4><ul class="ep-dots">' +
        r.nextChecks.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul></section>");
    }
    var grid = sec.length ? '<div class="ep-grid">' + sec.join("") + "</div>" : "";
    var foot = '<div class="ep-foot"><span>ההכנה: ' + (pn && pn.writtenAt ? esc(pn.writtenAt) : "—") + " · ההשוואה: " + (r && r.writtenAt ? esc(r.writtenAt) : "טרם נכתבה") +
      " · התגובה: סגירה מול סגירה ביום התגובה (" + (re.day ? esc(epDate(re.day)) : "—") + ") · האופציות: התמונה האחרונה לפני הדוח.</span>" +
      "<span>תיאור מבוסס נתונים, לא ייעוץ השקעות.</span></div>";
    return '<article class="ep-card ep-after" id="ep-' + esc(rc.sym) + '">' + head + words + stats + grid + foot + "</article>";
  }
  function renderPrep(el) {
    if (!el) return;
    var items = (PREPD && PREPD.items) || [], later = (PREPD && PREPD.later) || [], recent = (PREPD && PREPD.recent) || [];
    // שלב 7 (10.10.2026): פאנל-כותרת עם הצ'יפים במקום הקיקר וה-H2; הכרטיסים עצמם (ep-card) נשארו כמו שהם
    var chips = (items.length || recent.length) ? '<div class="chips bd-chips ep-chips2">' + items.concat(recent).map(function (it) {
        return '<a class="tag ep-chip2" href="#ep-' + esc(it.sym) + '" onclick="document.getElementById(\'ep-' + esc(it.sym) + '\').scrollIntoView({behavior:\'smooth\'});return false">' +
          epLogo(it) + '<b class="num" dir="ltr">' + esc(it.sym) + "</b> <span class=\"mute\">" + (recent.indexOf(it) >= 0 ? "דיווחה " + epDate(it.date) : epDow(it.date) + " " + epDate(it.date) + " · " + epWhen(it)) + "</span></a>";
      }).join("") + "</div>" : "";
    var intro = '<section class="pan"' + bdSpan(12) + ">" +
      panHd("לקראת הדוח · השבועיים הקרובים", '<span class="mute">חברות שיש להן ניתוח דוח קודם באתר · המספרים מתעדכנים כל רבע שעה, ההכנה המילולית נכתבת בבוקר שלפני שבוע הדוח</span>') +
      '<div class="pb">' + (chips || '<span class="mute">אף חברה עם ניתוח קודם באתר לא מדווחת בשבועיים הקרובים.' +
        (later.length ? " הבאות בתור: " + later.slice(0, 6).map(function (x) { return '<b class="num" dir="ltr">' + esc(x.sym) + "</b> " + epDate(x.date); }).join(" · ") : "") + "</span>") + "</div></section>";
    var body = items.map(epCard).join("");
    if (recent.length) {
      body += '<section class="pan"' + bdSpan(12) + ">" + panHd("אחרי הדוח · ההכנה מול מה שקרה", '<span class="mute">הבדיקות שקבענו לפני הדוח, מה יצא בפועל, התחזית לפני ואחרי, וכמה המניה זזה מול מה שהאופציות תמחרו</span>') + "</section>" +
        recent.map(epReviewCard).join("");
    }
    el.innerHTML = '<div class="board ep-board">' + intro + body + "</div>";
  }

  /* ---------- הנבחרות (30.9.2026, np93) ----------
     data/picks.json = המהדורה של היום מ-scripts/build_picks.js: המועמדים+המומנטום
     שקיבלו "אישור מחיר לקנייה" מהמנוע הטכני על הסגירה האחרונה. data/picks_ledger.json =
     יומן הכנות (5/10/20 ימי מסחר אחרי, באחוזים ומול SPY). קלף לכל מניה: פס הענף,
     חותמת האישור, גרף 60 יום עם תמיכה/התנגדות, יציאה/כניסה/יעד, מי באתר מצביע, והרקורד
     ההיסטורי של המניה עצמה (במשפט אחד + ריבועים). הטיקר פותח את מודאל הניתוח הטכני. */
  var PICKD = null, PICKL = null;
  var PK_GRP = { tech: "טכנולוגיה", health: "בריאות", other: "אחר" };
  var PK_BO = { CONFIRMED: "פריצה מאושרת", RETEST: "בדיקה חוזרת של הפריצה", UNRESOLVED: "פריצה לא הוכרעה", PULLBACK: "תיקון אחרי פריצה",
    IN_PROGRESS: "פריצה בתהליך", GAP_PARTIAL_FILL: "מילוי חלקי של פער", GAP_BREAKOUT: "פריצה בפער", FAILED: "פריצה שנכשלה", NONE: "ללא פריצה" };
  function pkPct(v, d) { return v == null ? "—" : (v > 0 ? "+" : "") + Number(v).toFixed(d == null ? 1 : d) + "%"; }
  function pkLedger(bare_) {
    var eds = (PICKL && PICKL.editions) || [];
    if (!eds.length) return "";
    var H = [5, 10, 20], LO = { 5: 0, 10: 5, 20: 10 };
    // עמודה נעולה = התוצאה של יום 5/10/20. העמודה הפעילה מתעדכנת כל יום מ-cur ("יום 3"),
    // עד שהיא ננעלת ומתחילה הבאה (1.10.2026, איציק). הצבע תמיד לפי ההפרש מהשוק.
    // mk = להציג גם את השוק עצמו (שורת המהדורה בלבד; במניות זה אותו מספר בכל שורה)
    var cell = function (r, cur, h, mk) {
      var live = !r && cur && cur.day > LO[h] && cur.day < h;
      var v = r || (live ? cur : null);
      if (!v) return '<td class="pend">—</td>';
      var tone = v.excess > 0 ? "good" : v.excess < 0 ? "bad" : "";
      return '<td class="' + tone + (live ? " live" : "") + '"><b>' + pkPct(v.ret) + "</b><small>" + (live ? '<span class="dd">יום ' + cur.day + " · </span>" : "") + pkPct(v.excess) + '<span class="vm"> מול השוק</span></small>' +
        (mk && v.spy != null ? '<small class="mk">S&amp;P ' + pkPct(v.spy, 2) + "</small>" : "") + "</td>";
    };
    // מהלך יומי: קו התשואה המצטברת יום-יום (עד 20), קו אפס, נקודה בסוף בצבע הכיוון
    // מחיר כניסה → סגירה אחרונה (2.10.2026, איציק); הסגירה מ-cur.close, או נגזרת מהתשואה
    var pxNow = function (s, rs, twoLines) {
      var c = rs && rs.cur ? (rs.cur.close != null ? rs.cur.close : s.entry * (1 + rs.cur.ret / 100)) : null;
      return '<span class="pk-px" dir="ltr">$' + fmtNum(s.entry, 2) + (c != null ? "\u00a0→" + (twoLines ? "<br>" : " ") + '<b class="' + (c > s.entry ? "up" : c < s.entry ? "dn" : "") + '">$' + fmtNum(c, 2) + "</b>" : "") + "</span>";
    };
    // מהלך יומי (2.10.2026, איציק): עמודה לכל יום מסחר 1..20 — גובה = התשואה המצטברת מהכניסה
    // באותו יום (ירוק/אדום), משבצת ריקה לימים שעוד לא הגיעו, קו מקווקו אחרי יום 5 ויום 10
    // (העמודות "אחרי 5"/"אחרי 10"). ציר הזמן משמאל לימין כמו בשאר הגרפים באתר.
    var spark = function (path) {
      if (!path || !path.length) return '<td class="pk-path"></td>';
      var n = 20, W = 200, Hh = 30, slot = W / n, bw = slot * 0.62, pad = 2;
      var ys = path.map(function (p) { return p[0]; });
      var top = Math.max(0.5, Math.max.apply(null, ys)), bot = Math.min(-0.5, Math.min.apply(null, ys));
      var Y = function (v) { return pad + (top - v) / (top - bot) * (Hh - 2 * pad); }, y0 = Y(0);
      var bars = "";
      for (var d = 0; d < n; d++) {
        var x = (d * slot + (slot - bw) / 2).toFixed(1);
        if (d < path.length) {
          var v = path[d][0], yv = Y(v), h = Math.max(1, Math.abs(yv - y0));
          bars += '<rect class="b ' + (v > 0 ? "up" : v < 0 ? "dn" : "") + '" x="' + x + '" y="' + Math.min(yv, y0).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + h.toFixed(1) + '"><title>יום ' + (d + 1) + ": " + pkPct(v) + " (מול השוק " + pkPct(path[d][1]) + ")</title></rect>";
        } else {
          bars += '<rect class="f" x="' + x + '" y="' + (y0 - 1.5).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="3"/>';
        }
      }
      var cut = function (k) { var xx = (k * slot).toFixed(1); return '<line class="m" x1="' + xx + '" x2="' + xx + '" y1="0" y2="' + Hh + '"/>'; };
      return '<td class="pk-path"><svg viewBox="0 0 ' + W + " " + Hh + '" preserveAspectRatio="none" role="img" aria-label="מהלך ' + path.length + ' ימים מתוך 20">' +
        cut(5) + cut(10) + '<line class="z" x1="0" x2="' + (path.length * slot).toFixed(1) + '" y1="' + y0.toFixed(1) + '" y2="' + y0.toFixed(1) + '"/>' + bars + "</svg>" +
        '<small>יום ' + path.length + "/20</small></td>";
    };
    var rows = eds.slice().reverse().map(function (e, i) {
      var syms = (e.symbols || []).map(function (s) { return s.sym; });
      var main = '<tr class="pk-ed" data-ed="' + i + '"><td><span dir="ltr">' + esc(secDate(e.date)) + "</span>" +
        (e.spyEntry ? '<small class="pk-spy" dir="ltr" title="מחיר הכניסה של השוק — סגירת SPY ביום המהדורה">SPY ' + fmtNum(e.spyEntry, 2) + "</small>" : "") + "</td><td>" + syms.length + '<small class="pk-syms" dir="ltr">' + esc(syms.join(" ")) + "</small></td><td>" + esc(e.gateLabel || "") + "</td>" +
        spark(e.path) + H.map(function (h) { return cell(e.avg && e.avg[h], e.cur, h, true); }).join("") + "</tr>";
      var det = (e.symbols || []).map(function (s) {
        var rs = e.results && e.results[s.sym] || {};
        var stopped = H.some(function (h) { return rs[h] && rs[h].stopped; }) || (rs.cur && rs.cur.stopped);
        return '<tr class="pk-det" data-ed="' + i + '" hidden><td></td><td><a dir="ltr" href="https://www.tradingview.com/symbols/' + encodeURIComponent(s.sym) + '/" target="_blank" rel="noopener">' + esc(s.sym) + "</a>" + '<small class="pk-px-m">' + pxNow(s, rs, true) + "</small>" + (stopped ? '<small class="pk-stopped">נגעה בסטופ</small>' : "") + '</td><td>' + pxNow(s, rs) + "</td>" +
          spark(rs.path) + H.map(function (h) { return cell(rs[h], rs.cur, h); }).join("") + "</tr>";
      }).join("");
      return main + det;
    }).join("");
    if (bare_) return '<p class="pk-sub mute s" style="margin:10px 14px 4px">כל מהדורה נרשמת עם מחיר הסגירה של אותו יום ונמדדת כל יום מסחר: התשואה המצטברת באחוזים, ולידה ההפרש מ-S&P 500. ימים 1–5 מתעדכנים בעמודת "5", ביום 5 היא ננעלת, ואז 6–10 בעמודת "10", וכך עד 20. מניה שחוזרת יום אחרי יום נספרת פעם אחת.</p>' +
      '<div class="tbl"><table class="pk-table"><thead><tr><th>מהדורה</th><th>מניות</th><th>מצב השוק</th><th>מהלך יומי</th><th>אחרי 5 ימים</th><th>אחרי 10</th><th>אחרי 20</th></tr></thead><tbody>' + rows + "</tbody></table></div>";
    return '<section class="pk-ledger card"><div class="section-title" style="margin-top:0">📒 יומן הכנות</div>' +
      '<p class="pk-sub">כל מהדורה נרשמת עם מחיר הסגירה של אותו יום ונמדדת כל יום מסחר: התשואה המצטברת באחוזים, ולידה ההפרש מ-S&P 500 באותם ימים. ימים 1–5 מתעדכנים בעמודת "5" ("יום 3"), ביום 5 היא ננעלת, ואז ימים 6–10 בעמודת "10", וכך עד 20. הקו מראה את המהלך היומי. הצבע לפי ההפרש מהשוק. לחיצה על מהדורה פותחת מניה-מניה. מניה שחוזרת יום אחרי יום נספרת פעם אחת, מהמהדורה הראשונה שלה.</p>' +
      '<div class="table-wrap"><table class="pk-table"><thead><tr><th>מהדורה</th><th>מניות</th><th>מצב השוק</th><th>מהלך יומי</th><th>אחרי 5 ימים</th><th>אחרי 10</th><th>אחרי 20</th></tr></thead><tbody>' + rows + "</tbody></table></div></section>";
  }
  function renderPicks(el) {
    if (!el) return;
    // np120: טאב מניות כרשת פאנלים — טבלת הנבחרות המלאה (כמו בבית, כל המניות) + רצועות הערות →
    // יומן ההכנות | הרקורד → מועמדים | מומנטום → הצעות לטרייד | Insider (הפאנלים האחים ב-renderStockSiblings)
    var d = PICKD, main;
    if (!d || !d.picks) main = panHd("הנבחרות") + '<div class="pb mute">המהדורה הראשונה נבנית אחרי הריצה הבאה של הבוט.</div>';
    else {
      var g = d.gate || {}, r = d.record;
      var gateCls = { defense: "bad", neutral: "warn", green: "good" }[g.state] || "";
      var rule = { defense: "עד 3 פוזיציות · חצי גודל · כניסה בשלישים · אופק 10 עד 20 יום", neutral: "עד 4 פוזיציות · שני שליש גודל · כניסה בשלישים · אופק 10 עד 20 יום", green: "עד 5 פוזיציות · גודל מלא · כניסה בשלישים · אופק 10 עד 20 יום" }[g.state] || "";
      var facts = [g.combined != null ? "ציון משולב <b class=\"num\">" + esc(g.combined) + "</b>" : "", g.breadth != null ? "רוחב <b class=\"num\">" + Math.round(g.breadth) + "%</b> מעל ממוצע 50" : "",
        g.sellDays != null ? "<b class=\"num\">" + esc(g.sellDays) + "</b> ימי מכירה בחודש" : "", g.flow != null ? "אופציות <b class=\"num\">" + esc(g.flow) + "</b>" : "",
        g.vix != null ? "VIX <b class=\"num\">" + Math.round(g.vix) + "</b> " + ({ green: "ירוק", yellow: "צהוב", red: "אדום" }[g.vixState] || "") : ""].filter(Boolean);
      var byGrp = {}; d.picks.forEach(function (p) { byGrp[p.grp] = (byGrp[p.grp] || 0) + 1; });
      var mix = Object.keys(byGrp).map(function (k) { return byGrp[k] + " " + (PK_GRP[k] || k); }).join(" · ");
      var notes = (d.momOnly ? '<div class="pb mute s" style="padding-top:0">מהמומנטום בלבד: המועמדים לא הגיעו עד 08:00. כשיגיעו, המהדורה תיבנה מחדש משניהם.</div>' : "") +
        (d.pending && d.pending.asOf > d.date ? '<div class="pb mute s" style="padding-top:0">מהדורת <span class="num" dir="ltr">' + esc(secDate(d.pending.asOf)) + "</span> ממתינה ל" + esc((d.pending.waiting || []).join(" ו")) + ".</div>" : "");
      main = panHd('הנבחרות · אישור מחיר לקנייה · מהדורת <span class="num" dir="ltr">' + bdDM(d.date) + "</span>",
          (g.label ? '<span class="pill state ' + gateCls + '">השוק ' + esc(g.label) + (g.maxPos ? ' · עד <span class="num">' + esc(g.maxPos) + "</span> פוזיציות" : "") + (g.sizing ? " · " + esc(g.sizing) + " גודל" : "") + "</span>" : "") +
          (g.verdict ? '<span class="mute">' + esc(g.verdict) + "</span>" : "")) +
        (d.picks.length ? picksTableHtml(d.picks) : '<div class="pb mute">אף מניה לא קיבלה היום אישור מחיר. זה קורה, ולא מחפשים תחליף.</div>') +
        '<div class="led"><div><span class="mute">נפסלו</span><span>' + ((d.excluded || []).length ? d.excluded.map(function (x) { return '<b class="num" dir="ltr">' + esc(x.sym) + "</b> — " + esc(x.reason); }).join(" · ") : "אין") + "</span></div>" +
          '<div><span class="mute">אופק</span><span>' + esc(rule || "10–20 יום · כניסה בשלישים · סטופ לא צמוד") + "</span></div>" +
          '<div><span class="mute">המאגר</span><span>' + (d.momOnly ? "המומנטום בלבד" : "מועמדים ∪ מומנטום") + (d.poolSize ? ' · <span class="num">' + esc(d.poolSize) + "</span> מניות" : "") + (mix ? " · " + esc(mix) : "") + "</span></div>" +
          '<div><span class="mute">מקור</span><span>' + (d.scanned ? 'נסרקו <span class="num">' + esc(d.scanned) + "</span> מניות" : "המנוע הטכני") + (facts.length ? " · " + facts.join(" · ") : "") + "</span></div></div>" + notes +
        '<div class="led bd-how"><div><b>1. המאגר</b><span>סריקת המועמדים וסריקות המומנטום. רק מה שכבר באתר.</span></div>' +
          '<div><b>2. השופט</b><span>המנוע הטכני רץ על 500 נרות של כל מניה. נכנסות רק מניות עם "אישור מחיר לקנייה". "כניסה אפשרית" לא מספיק (נבדק לאחור: לא מנצח יום רגיל).</span></div>' +
          '<div><b>3. הסינון</b><span>מדווחת בשבוע הקרוב יוצאת. מניה ששלושת האישורים הקודמים שלה נכשלו יוצאת.</span></div>' +
          '<div><b>4. השער</b><span>מד השוק קובע כמה מותר: הגנה = עד 3 וחצי גודל. ירוק = עד 5.</span></div></div>' +
        '<p class="stamp" style="margin:10px 14px">תיאור טכני של מצב המניות על פי נרות יומיים, לא ייעוץ השקעות. המספרים ההיסטוריים מבוססים על שנה אחת ועל מניות שנבחרו כשהן במגמת עלייה, ולכן מוטים לטובה. לחיצה על הטיקר פותחת את הניתוח הטכני המלא.</p>';
    }
    var rec = d && d.record;
    el.innerHTML = (d ? stamp(d._meta) : "") + '<div class="board">' +
      '<section class="pan bd-picks" id="pk-main"' + bdSpan(12) + ">" + main + "</section>" +
      (d && PICKL && (PICKL.editions || []).length ? '<section class="pan"' + bdSpan(rec ? 7 : 12) + ">" + panHd("יומן ההכנות", '<span class="mute">כל המספרים מצטברים מהכניסה, מול S&amp;P · לחיצה על מהדורה פותחת מניה-מניה</span>') + '<div class="pk-ledger-b">' + pkLedger(true) + "</div></section>" : "") +
      (rec ? '<section class="pan"' + bdSpan(5) + ">" + panHd("הרקורד", '<span class="mute">מבחן לאחור · <span class="num">' + esc(rec.n) + '</span> אישורים ב-<span class="num">' + esc(rec.symbols) + "</span> מניות</span>") +
        '<div class="pb"><div class="tiles t2">' + bdTile("עלו תוך 10 ימים", esc(rec.win10) + "%") + bdTile("ממוצע 10 ימים", pkPct(rec.avg10), rec.excess10 != null ? "מול S&amp;P " + pkPct(rec.excess10) : "", rec.avg10 > 0 ? "up" : "down") +
          bdTile("ממוצע 20 יום", pkPct(rec.avg20), "", rec.avg20 > 0 ? "up" : "down") + bdTile("ירידה ממוצעת בדרך", pkPct(rec.mae), "הסטופ לא צמוד", "down") + "</div>" +
        '<p class="mute s" style="margin:0">הדגימה מוטה לטובה: מניות שנבחרו כשהן במגמת עלייה. השבוע הראשון תנודתי — מחצית נוגעות ב-1.5 ATR.</p></div></section>' : "") +
      '<section class="pan" id="pk-cand"' + bdSpan(6) + '></section><section class="pan" id="pk-mom"' + bdSpan(6) + "></section>" +
      '<section class="pan" id="pk-trd"' + bdSpan(6) + '></section><section class="pan" id="pk-ins"' + bdSpan(6) + "></section></div>";
    el.querySelectorAll(".pk-ed").forEach(function (tr) {
      tr.addEventListener("click", function () {
        var open = tr.classList.toggle("open");
        el.querySelectorAll('.pk-det[data-ed="' + tr.dataset.ed + '"]').forEach(function (x) { x.hidden = !open; });
      });
    });
    renderStockSiblings();
  }
  var INSD = null;
  function renderInsider(el, d) {
    INSD = d;
    var reps = (d && d.reports) || [];
    if (!reps.length) {
      emptyPanel(el, "🕵️", "Insider — בקרוב", "הדוח הראשון בדרך.");
      return;
    }
    el.innerHTML = '<div class="board"><section class="pan" id="ins-view"' + bdSpan(12) + "></section>" +
      '<section class="pan"' + bdSpan(12) + '><details class="bd-exp"><summary>איך זה עובד</summary>' + tabIntro("insider") + "</details></section></div>";
    showInsider(0);
  }
  function showInsider(i) {
    var view = document.getElementById("ins-view");
    if (!view || !INSD) return;
    var r = (INSD.reports || [])[i];
    if (!r) return;
    var reps = INSD.reports || [];
    var tks = (r.tickers || []).map(function (t) {
      return '<a class="tag" dir="ltr" href="https://www.tradingview.com/symbols/' + encodeURIComponent(t) + '/" target="_blank" rel="noopener"><b class="num">' + esc(t) + "</b></a>";
    }).join("");
    view.innerHTML = panHd("Insider · " + esc(r.title || "קניות של בעלי עניין"), '<span class="mute">' + (r.range ? esc(r.range) + " · " : "") + 'הופק ב-<span class="num" dir="ltr">' + esc(secDate(r.date)) + "</span></span>", repFull(r.file)) +
      ((reps.length > 1 || tks) ? '<div class="pb">' + repChips("ins-tab", reps, function (x) { return secDate(x.date); }, i) +
        (tks ? '<div class="rep-tks"><span class="mute s">המניות בדוח</span><div class="chips bd-chips">' + tks + "</div></div>" : "") + "</div>" : "") +
      repFrame(r.file, INSD._meta, r.title);
    bindRepChips(view, "ins-tab", showInsider);
  }

  /* טאב "הצעות לטרייד" — דוחות Four Pillars וכד', כמו סקטורים (יומי במקום שבועי) */
  function renderTrades(el, d) {
    TRAD = d;
    var reps = (d && d.reports) || [];
    if (!reps.length) {
      emptyPanel(el, "💡", "הצעות לטרייד — בקרוב", "הדוח הראשון בדרך.");
      return;
    }
    // מצגת הלימוד של השיטה (PDF) — שורה קבועה בראש הפאנל
    el.innerHTML = '<div class="board"><section class="pan" id="trd-view"' + bdSpan(12) + "></section></div>";
    showTrade(0);
    renderTriIndex();
  }
  function showTrade(i) {
    var view = document.getElementById("trd-view");
    if (!view || !TRAD) return;
    var r = (TRAD.reports || [])[i];
    if (!r) return;
    var reps = TRAD.reports || [], m = TRAD.method;
    view.innerHTML = panHd("הצעות לטרייד · " + esc(r.title), '<span class="mute">סריקה יומית · נכון ל-<span class="num" dir="ltr">' + esc(fmtTradeDate(r.date) || r.date) + "</span></span>", repFull(r.file)) +
      '<div class="pb">' + repChips("trd-tab", reps, function (x) { return fmtTradeDate(x.date) || x.date; }, i) +
        (m ? '<a class="trd-method2" href="' + esc(m.url) + '" target="_blank" rel="noopener"><b>' + esc(m.title) + '</b> <span class="mute">· מצגת השיטה (PDF), מומלץ לקרוא לפני הסריקות</span></a>' : "") + "</div>" +
      repFrame(r.file, TRAD._meta, r.title);
    bindRepChips(view, "trd-tab", showTrade);
  }

  /* טאב "Barchart" — שתי מהדורות (21.9.2026, בקשת איציק): "review" ב-06:00
     (בשורש d, תאימות-לאחור) ו-"premkt" (טרום מסחר) ב-14:00, מקונן ב-d.premkt.
     מבנה זהה ל-renderBriefing (בוקר/אחה"צ): צ'יפ-טאב לכל מהדורה + היסטוריה לפי יום. */
  function renderMorning(el, d) {
    var hasReview = d && d.file, hasPremkt = d && d.premkt && d.premkt.file;
    if (!d || d._status === "pending" || (!hasReview && !hasPremkt)) {
      emptyPanel(el, "📊", "Barchart — בקרוב", "יתחבר ברגע שצינור ה-Barchart יופעל.");
      return;
    }
    var slots = [];
    // טרום-מסחר קודם (מאוחר יותר ביום, יותר עדכני) ואז הדוח היומי
    if (hasPremkt) slots.push(["premkt", "טרום מסחר · 14:00", d.premkt]);
    if (hasReview) slots.push(["review", "דוח יומי · 06:00", { subject: d.subject, dateLabel: d.dateLabel, time: d.time, file: d.file }]);

    var revDays = archDays(["review", "premkt"], "");
    var latestRev = revDays.length ? revDays[0] : "";
    var days = revDays.slice(1);
    var sel = (MORN_DAY && days.indexOf(MORN_DAY) >= 0) ? MORN_DAY : null;
    // שלב 7 (10.10.2026): פאנל אחד — כותרת עם המהדורה + "מסך מלא", צ'יפי מהדורה וצ'יפי ארכיון, וה-iframe בתוך הפאנל
    var archNav = days.length ? '<div class="chips bd-chips rep-arch"><span class="mute s">ארכיון</span>' +
      '<button type="button" class="tag morn-day' + (sel ? "" : " on") + '" data-day=""><span class="num" dir="ltr">' + esc(latestRev ? fmtTradeDate(latestRev) : "אחרון") + "</span></button>" +
      days.map(function (k) { return '<button type="button" class="tag morn-day' + (sel === k ? " on" : "") + '" data-day="' + k + '"><span class="num" dir="ltr">' + esc(fmtTradeDate(k)) + "</span></button>"; }).join("") + "</div>" : "";
    if (sel) {   // יום ארכיון נבחר — הצג את המהדורות השמורות שלו בלבד
      var e = BARCHIVE.days[sel];
      slots = [];
      if (e.premkt) slots.push(["premkt", "טרום מסחר · 14:00", { subject: e.premkt.subject, time: e.premkt.time, file: e.premkt.file, dateLabel: fmtTradeDate(sel) }]);
      if (e.review) slots.push(["review", "דוח יומי · 06:00", { subject: e.review.subject, time: e.review.time, file: e.review.file, dateLabel: fmtTradeDate(sel) }]);
    }
    // חיווי סופ"ש/חג: הצינור רץ אבל ל-Barchart לא היו ניוזלטרים — שקיפות שהכול חי
    var noticeBar = (d.notice && !sel)
      ? '<p class="mute s rep-note"><span class="num" dir="ltr">' + esc(fmtTradeDate(d.notice.date) || d.notice.date) + "</span> — אין ניוזלטרים חדשים מ-Barchart" +
        (d.notice.time ? ' (נבדק ב-<span class="num" dir="ltr">' + esc(d.notice.time) + "</span>)" : "") + " · מוצגת הסקירה האחרונה שהתקבלה</p>"
      : "";
    var nav = slots.length > 1
      ? '<div class="chips bd-chips">' + slots.map(function (s, i) {
          return '<button type="button" class="tag morn-tab' + (i === 0 ? " on" : "") + '" data-morn="' + s[0] + '">' + esc(s[1]) + "</button>";
        }).join("") + "</div>"
      : "";
    function mornHd(sl) {
      return panHd("Barchart" + (sl.dateLabel ? ' · <span class="num" dir="ltr">' + esc(sl.dateLabel) + "</span>" : ""),
        '<span class="mute">' + esc(sl.subject || "") + (sl.time ? ' · <span class="num" dir="ltr">' + esc(sl.time) + "</span>" : "") + "</span>", repFull(sl.file));
    }
    var frames = slots.map(function (s, i) {
      var sl = s[2];
      return '<div class="morn-view" data-morn="' + s[0] + '" style="display:' + (i === 0 ? "block" : "none") + '">' +
        '<iframe class="brief-frame rep-frame" src="' + bust(sl.file, d._meta) + '" title="' + esc(sl.subject || "") +
        '" style="width:100%;min-height:640px" ' +
        'onload="try{this.style.height=(this.contentWindow.document.body.scrollHeight+30)+\'px\'}catch(e){}"></iframe></div>';
    }).join("");

    el.innerHTML = '<div class="board"><section class="pan"' + bdSpan(12) + '><div class="morn-hd">' + mornHd(slots[0][2]) + "</div>" +
        '<div class="pb">' + nav + archNav + noticeBar + "</div>" + frames + "</section>" +
      '<section class="pan"' + bdSpan(12) + '><details class="bd-exp"><summary>איך זה עובד</summary>' + tabIntro("morning") + "</details></section></div>";

    el.querySelectorAll(".morn-tab").forEach(function (b) {
      b.addEventListener("click", function () {
        var k = b.dataset.morn;
        el.querySelectorAll(".morn-tab").forEach(function (x) { x.classList.toggle("on", x.dataset.morn === k); });
        el.querySelectorAll(".morn-view").forEach(function (x) { x.style.display = x.dataset.morn === k ? "block" : "none"; });
        var sl = slots.filter(function (x) { return x[0] === k; })[0];
        if (sl) el.querySelector(".morn-hd").innerHTML = mornHd(sl[2]);
      });
    });
    el.querySelectorAll(".morn-day").forEach(function (b) {
      b.addEventListener("click", function () { MORN_DAY = b.dataset.day || null; renderMorning(el, d); });
    });
  }

  function renderCandidates(el, d) {
    if (!d || d._status === "pending" || !d.candidates) {
      emptyPanel(el, "🎯", "מועמדים — בקרוב", "הרשימה תופיע אחרי הסריקה הבאה.");
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
        '<td dir="ltr" class="num">' + n(c.entry, 2) + "</td>" +
        '<td dir="ltr" class="num">' + n(c.stop, 2) + "</td>" +
        '<td dir="ltr" class="num">' + n(c.target, 2) + "</td>" +
        '<td dir="ltr" class="num ' + (c.risk_pct > 5 ? "down" : "") + '">' + n(c.risk_pct, 1) + "%</td>" +
        '<td dir="ltr" class="num up">' + n(c.tp_pct, 1) + "%</td>" +
        '<td dir="ltr" class="num">' + n(c.rvol, 2) + "</td>" +
        '<td dir="ltr" class="num ' + (c.hist_r >= 0 ? "up" : "down") + '">' + n(c.hist_r, 1) + "</td></tr>";
    }).join("");

    // שלב 7 (10.10.2026): פאנל ראשי (סגירה + 4 אריחים) · פאנל הטבלה · "איך זה עובד" מקופל
    var cs = d.candidates, tdy = candTradeDay(d), cloud = d._meta && d._meta.source === "nidam-cloud-scan";
    function med(arr) { arr = arr.filter(function (v) { return v != null && !isNaN(v); }).sort(function (a, b) { return a - b; }); return arr.length ? arr[Math.floor(arr.length / 2)] : null; }
    var mRisk = med(cs.map(function (c) { return c.risk_pct; })), mTp = med(cs.map(function (c) { return c.tp_pct; }));
    var posR = cs.filter(function (c) { return c.hist_r > 0; }).length;
    var runAt = d._meta && d._meta.updatedAt ? /(\d{1,2}\/\d{1,2})\/\d{4} (\d{1,2}:\d{2})/.exec(d._meta.updatedAt) : null;
    el.innerHTML = '<div class="board">' +
      '<section class="pan"' + bdSpan(12) + ">" +
        panHd("מועמדים למסחר" + (tdy ? ' · סגירת <span class="num" dir="ltr">' + esc(fmtTradeDate(tdy)) + "</span>" : ""),
          '<span class="mute">' + (cloud ? "סריקה בענן" : "סריקת IBKR") + (runAt ? ' · רצה ב-<span class="num" dir="ltr">' + runAt[1].replace("/", ".") + '</span> בשעה <span class="num" dir="ltr">' + runAt[2] + "</span>" : "") + "</span>") +
        '<div class="pb"><div class="tiles">' +
          bdTile("מועמדים", String(d.count || cs.length), d.shown && d.shown < d.count ? "מוצגים " + d.shown + " המובילים" : "") +
          bdTile("נסרקו", cloud && d._meta.universe ? Number(d._meta.universe).toLocaleString("en-US") : "—", "מניות מומנטום") +
          bdTile("סיכון חציוני", mRisk != null ? mRisk.toFixed(1) + "%" : "—", "מהכניסה עד הסטופ") +
          bdTile("R היסטורי חיובי", '<span class="num">' + posR + '</span><small> מתוך ' + cs.length + "</small>", "ביצוע הסטאפ בשנתיים") +
        "</div></div></section>" +
      '<section class="pan"' + bdSpan(12) + ">" +
        panHd("הרשימה", '<span class="mute">לפי דירוג משולב · כניסה/סטופ/מטרה ברמות המערכת' + (mTp != null ? ' · יעד חציוני <span class="num" dir="ltr">' + mTp.toFixed(1) + "%</span>" : "") + "</span>") +
        '<div class="tbl"><table class="bd-tbl"><caption class="sr-only">מועמדים למסחר</caption><thead><tr>' +
        '<th scope="col">#</th><th scope="col">מניה</th><th scope="col">סטאפ</th>' +
        '<th scope="col">כניסה</th><th scope="col">סטופ</th><th scope="col">מטרה</th>' +
        '<th scope="col">סיכון</th><th scope="col">יעד</th><th scope="col">RVOL</th><th scope="col">R היסטורי</th>' +
        "</tr></thead><tbody>" + rows + "</tbody></table></div></section>" +
      '<section class="pan"' + bdSpan(12) + '><details class="bd-exp"><summary>איך זה עובד</summary>' + tabIntro("candidates") +
        '<p class="stamp" style="margin:0 14px 12px">' + (cloud ? "הסריקה רצה בענן אוטומטית אחרי שקובצי המומנטום מתעדכנים · " : "") + "R היסטורי = הביצוע של אותו סטאפ על המניה בשנתיים האחרונות, ביחידות של הסיכון (R) · לחיצה על טיקר פותחת את הניתוח הטכני</p></details></section>" +
      "</div>";
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
        (r.logo ? '<img class="rep-logo' + (r.logoBg === "dark" ? " rep-logo-dk" : "") + '" src="' + esc(r.logo) + '" alt="' + esc(r.ticker || "") + '" onerror="this.remove()">' : "") +
        (r.ticker ? '<span class="rep-ticker">' + esc(r.ticker) + "</span>" : "") + "</div>";
      return '<button class="rep-card" data-rep="' + i + '">' + head +
        '<span class="rep-title">' + esc(r.title || r.file) + "</span>" +
        (r.date ? '<span class="rep-date num" dir="ltr">' + esc(fmtTradeDate(r.date) || r.date) + "</span>" : "") + "</button>";
    }).join("");
    // שלב 7 (10.10.2026): הרשת בתוך פאנל; דוח פתוח = פאנל עם "חזרה" ו"מסך מלא"
    el.innerHTML = '<div class="board">' +
      '<section class="pan" id="rep-list-pan"' + bdSpan(12) + ">" + panHd("ניתוח דוחות חברות", '<span class="mute"><span class="num">' + reports.length + "</span> ניתוחים · החדש ראשון</span>") +
        '<div class="pb"><div id="rep-list" class="rep-grid">' + cards + "</div></div></section>" +
      '<section class="pan" id="rep-view"' + bdSpan(12) + ' style="display:none"></section></div>';

    var list = el.querySelector("#rep-list");
    var view = el.querySelector("#rep-view");
    // פתיחת דוח מסוים מבחוץ ("הניתוח החדש" בכרטיס "אחרי הדוח", 9.10.2026)
    window.__openReport = function (file) {
      if (window.__goTab) window.__goTab("reports");
      var i = reports.findIndex(function (x) { return x.file === file; });
      var b = i >= 0 ? el.querySelector('.rep-card[data-rep="' + i + '"]') : null;
      if (b) setTimeout(function () { b.click(); }, 30);
    };
    var listPan = el.querySelector("#rep-list-pan");
    function back() { view.style.display = "none"; view.innerHTML = ""; listPan.style.display = ""; }
    el.querySelectorAll(".rep-card").forEach(function (b) {
      b.addEventListener("click", function () {
        var r = reports[+b.dataset.rep];
        listPan.style.display = "none";
        view.style.display = "";
        view.innerHTML = panHd('<button type="button" class="rep-back">כל הניתוחים</button> · ' + esc(r.title || r.file), r.date ? '<span class="mute num" dir="ltr">' + esc(fmtTradeDate(r.date) || r.date) + "</span>" : "", repFull(r.file)) +
          '<iframe class="brief-frame rep-frame" src="' + bust(r.file, d._meta) + '" title="' + esc(r.title || "") +
          '" style="width:100%;min-height:640px" ' +
          'onload="try{this.style.height=(this.contentWindow.document.body.scrollHeight+30)+\'px\'}catch(e){}"></iframe>';
        view.querySelector(".rep-back").addEventListener("click", back);
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  /* ===================== לוח המסחר — גוף הטאבים (np120, עיצוב מחדש שלב 6 חלק 2) =====================
     עזרים משותפים לחמשת הטאבים + הפאנלים האחים (מניות/חדשות/העולם) שמתמלאים כשהנתונים שלהם מגיעים.
     כל טאב = <div class="board"> (רשת 12) של <section class="pan"> עם כותרת .ph וגוף .pb — כמו הבית. */
  function panHd(h2, extra, go) { return '<div class="ph"><h2>' + h2 + "</h2>" + (extra || "") + (go || "") + "</div>"; }
  function bdSpan(n) { return ' style="grid-column:span ' + n + '"'; }
  function bdTile(l, v, s, cls) {
    return '<div class="tile"><div class="l">' + l + '</div><div class="v num' + (cls ? " " + cls : "") + '" dir="ltr">' + v + "</div>" + (s ? '<div class="s mute">' + s + "</div>" : "") + "</div>";
  }
  // מסיר את כותרת-הסעיף ואת עטיפת הכרטיס של הרנדררים הישנים — הגוף נכנס לפאנל החדש כפי שהוא
  function bare(html) {
    return String(html || "").replace(/^\s*<div class="section-title"[^>]*>[\s\S]*?<\/div>\s*/, "").replace(/^<div class="card[^"]*"[^>]*>/, "").replace(/<\/div>\s*$/, "");
  }
  function bpPan(d) {
    var html = breadthPeaksHtml(d);
    if (!html) return "";
    var m = /<h3 class="bp-title">([\s\S]*?)<\/h3>/.exec(html);
    return panHd("כמה מניות משתתפות בשיא?", m ? '<span class="mute">' + m[1] + "</span>" : "") + '<div class="pb">' + html + "</div>";
  }
  function currentForecast() {
    var eu = CA && CA.eventUpdate;
    return (eu && eu.forecast && eu.forecast.label) ? eu.forecast : (FCAST && FCAST.current && FCAST.current.label ? FCAST.current : null);
  }
  function renderForecastPan() {
    var el = document.getElementById("fc-pan");
    if (!el) return;
    var f = currentForecast(), track = fcTrackHtml(), rec = FCAST && FCAST.record;
    if (!f && !track) { el.innerHTML = ""; return; }
    el.innerHTML = panHd("הצפי לשבוע", rec && rec.scored ? '<span class="mute">מאזן: <span class="num">' + rec.hits + '</span> מתוך <span class="num">' + rec.scored + '</span> פגיעות · <span class="num">' + (rec.inRange || 0) + "</span> בטווח</span>" : "") +
      '<div class="pb">' + (f ? forecastHtml(f) : "") + '<div id="fc-track-slot">' + track + "</div></div>";
  }
  function pickRowHtml(p, i) {
    var lo_ = p.stop || p.sup, hi_ = p.target || p.res, loL = p.stop ? "סטופ" : "תמיכה", hiL = p.target ? "יעד" : "התנגדות";
    var pos = (lo_ && hi_) ? Math.max(0, Math.min(100, (p.price - lo_) / ((hi_ - lo_) || 1) * 100)) : null;
    var rec = p.rec || {}, dots = (rec.dots || []).map(function (x) { return '<i class="rd' + (x ? " w" : "") + '"></i>'; }).join("");
    var src = (p.sources || []).map(function (s) { return '<span class="tag">' + esc(String(s.t || "").split(" #")[0]) + "</span>"; }).join(" ");
    return "<tr><td><a href=\"https://www.tradingview.com/symbols/" + encodeURIComponent(p.sym) + '/" class="tsym" target="_blank" rel="noopener"><span class="rank num">' + (i + 1) + "</span>" + esc(p.sym) + "</a>" +
        '<div class="mute nm">' + esc((p.name || "").replace(/ Inc\.?$| Corp.*$| and Company$|, Inc\.$/, "")) + (p.since ? ' · ברשימה מ-<span class="num" dir="ltr">' + esc(secDate(p.since)) + "</span>" : "") + "</div></td>" +
      '<td><span class="num" dir="ltr">' + fmtNum(p.price, 2) + "</span></td><td>" + bdPct(p.chg) + "</td>" +
      '<td class="sp-cell">' + bdPickSpark(p) + "</td>" +
      '<td><span class="num down" dir="ltr">' + (lo_ != null ? fmtNum(lo_, 2) : "—") + '</span><div class="mute s">' + loL + "</div></td>" +
      "<td>" + (pos != null ? '<div class="rng" role="img" aria-label="המחיר ב-' + pos.toFixed(0) + '% מהדרך בין ' + loL + ' ל' + hiL + '"><b style="left:calc(' + pos.toFixed(0) + '% - 1px)"></b></div>' : "") + "</td>" +
      '<td><span class="num up" dir="ltr">' + (hi_ != null ? fmtNum(hi_, 2) : "—") + '</span><div class="mute s">' + hiL + "</div></td>" +
      "<td>" + src + "</td>" +
      "<td>" + dots + (rec.n ? '<div class="mute s"><span class="num">' + (rec.dots || []).reduce(function (a, b) { return a + b; }, 0) + "</span> מתוך <span class=\"num\">" + rec.n + "</span> עלו</div>" : '<div class="mute s">אישור ראשון</div>') + "</td></tr>";
  }
  function picksTableHtml(picks, cap) {
    return '<div class="tbl"><table><caption class="sr-only">' + (cap || "הנבחרות") + '</caption><thead><tr><th scope="col">מניה</th><th scope="col">מחיר</th><th scope="col">יום</th><th scope="col">60 יום</th><th scope="col">סטופ / תמיכה</th><th scope="col">מיקום בטווח</th><th scope="col">יעד / התנגדות</th><th scope="col">מקור</th><th scope="col">רקורד</th></tr></thead><tbody>' +
      picks.map(pickRowHtml).join("") + "</tbody></table></div>";
  }
  /* הפאנלים האחים בטאב מניות: מועמדים · מומנטום · הצעות לטרייד · Insider — תקצירים עם קישור ללשונית המלאה */
  var TRAD = null;
  function renderStockSiblings() {
    var ec = document.getElementById("pk-cand"), em = document.getElementById("pk-mom"), et = document.getElementById("pk-trd"), ei = document.getElementById("pk-ins");
    if (ec) {
      var c = CANDD, rows = (c && c.candidates) || [], tdy = c && candTradeDay(c);
      ec.innerHTML = !rows.length
        ? panHd("מועמדים למסחר", "", bdGo("candidates", "מועמדים")) + '<div class="pb mute">' + (c ? "אין מועמדים בסריקה האחרונה." : "טוען…") + "</div>"
        : panHd("מועמדים למסחר" + (tdy ? ' · סגירת <span class="num" dir="ltr">' + esc(fmtTradeDate(tdy)) + "</span>" : ""),
            '<span class="mute"><span class="num">' + (c.count || rows.length) + "</span> מועמדים" + (c._meta && c._meta.universe ? ' · נסרקו <span class="num">' + c._meta.universe + "</span> מניות בענן" : "") + "</span>", bdGo("candidates", "כל " + (c.shown || rows.length))) +
          '<div class="tbl"><table class="bd-tbl"><thead><tr><th>#</th><th>מניה</th><th>סטאפ</th><th>כניסה</th><th>סטופ</th><th>יעד</th><th>סיכון</th><th>RVOL</th></tr></thead><tbody>' +
          rows.slice(0, 6).map(function (x) {
            return '<tr><td class="num mute">' + x.rank + "</td><td>" + tvLink(x.symbol) + erBadge(x.symbol) + '</td><td><span class="tag">' + esc(x.setup || "") + '</span></td><td class="num" dir="ltr">' + fmt(x.entry) +
              '</td><td class="num down" dir="ltr">' + fmt(x.stop) + '</td><td class="num up" dir="ltr">' + fmt(x.target) + '</td><td class="num' + (x.risk_pct > 5 ? " down" : "") + '" dir="ltr">' + fmt(x.risk_pct, 1) + '%</td><td class="num" dir="ltr">' + fmt(x.rvol) + "</td></tr>";
          }).join("") + "</tbody></table></div>";
    }
    if (em) {
      var md = MOMD, pool = ((md && md.stocks) || []).filter(function (x) { return x.symbol && !/\s/.test(x.symbol) && passesBase(x); });
      var top = pool.slice().sort(function (a, b) { return (b.readiness || 0) - (a.readiness || 0) || (b.wtd_alpha || 0) - (a.wtd_alpha || 0); }).slice(0, 6);
      var n3 = pool.filter(function (x) { return x.signal_count >= 3; }).length, n2 = pool.filter(function (x) { return x.signal_count === 2; }).length, nc = pool.filter(function (x) { return (x.readiness || 0) >= 50; }).length;
      var fdate = (function () { var f = (md && md._meta && md._meta.files) || {}, k = Object.keys(f)[0], m = k && /(\d{2})-(\d{2})-(\d{4})\.csv$/.exec(f[k]); return m ? (+m[2]) + "." + (+m[1]) : ""; })();
      em.innerHTML = !top.length
        ? panHd("מומנטום", "", bdGo("momentum", "מומנטום")) + '<div class="pb mute">' + (md ? "אין מניות שעברו את פילטר הבסיס." : "טוען…") + "</div>"
        : panHd("מומנטום" + (fdate ? ' · סורקי <span class="num" dir="ltr">' + fdate + "</span>" : ""), '<span class="mute"><span class="num">' + n3 + '</span> עם 3+ סיגנלים · <span class="num">' + n2 + '</span> עם 2 · <span class="num">' + Math.min(12, nc) + "</span> מועמדות לטרייד</span>", bdGo("momentum", "כל " + pool.length)) +
          '<div class="tbl"><table class="bd-tbl"><thead><tr><th>מניה</th><th>מוכנות</th><th>סיגנלים</th><th>יום</th></tr></thead><tbody>' +
          top.map(function (s) {
            return "<tr><td>" + tvLink(s.symbol) + erBadge(s.symbol) + '<div class="mute s">' + esc((s.industry || "").slice(0, 28)) + '</div></td><td class="num" dir="ltr">' + (s.readiness != null ? s.readiness : "—") + "</td><td>" +
              (s.signals || []).map(function (k) { return '<span class="tag">' + esc(SIG_LABEL[k] || k) + "</span>"; }).join(" ") + "</td><td>" + pct(s.change_pct) + "</td></tr>";
          }).join("") + "</tbody></table></div>";
    }
    if (et) {
      var tr = TRAD && (TRAD.reports || [])[0], pk = tr && (typeof tr.picks === "string" ? [] : (tr.picks || []));
      et.innerHTML = !tr
        ? panHd("הצעות לטרייד", "", bdGo("trades", "הדוח")) + '<div class="pb mute">' + (TRAD ? "אין דוח." : "טוען…") + "</div>"
        : panHd("הצעות לטרייד · " + esc(tr.title || "ארבעת העמודים"), '<span class="mute num" dir="ltr">' + esc(fmtTradeDate(tr.date) || tr.date || "") + "</span>", bdGo("trades", "הדוח")) +
          (pk.length ? '<div class="pb bd-sents">' + pk.slice(0, 5).map(function (p) {
            return '<div class="sent"><b><span class="num tk" dir="ltr">' + esc(p.ticker) + "</span></b><span><b>" + esc(p.cat || "") + "</b>" + (p.action ? " · " + esc(p.action) : "") + (p.note ? " — " + esc(p.note) : "") + "</span></div>";
          }).join("") + "</div>" : '<div class="pb mute">' + (TRAD.method ? '<a href="' + esc(TRAD.method.url) + '" target="_blank" rel="noopener">📚 ' + esc(TRAD.method.title) + "</a>" : "הדוח המלא בלשונית הצעות לטרייד.") + "</div>");
    }
    if (ei) {
      var ir = INSD && (INSD.reports || [])[0];
      ei.innerHTML = !ir
        ? panHd("Insider", "", bdGo("insider", "הדוח")) + '<div class="pb mute">' + (INSD ? "אין דוח." : "טוען…") + "</div>"
        : panHd("Insider · " + esc(ir.title || "קניות של בעלי עניין"), '<span class="mute num" dir="ltr">' + esc(secDate(ir.date)) + "</span>", bdGo("insider", "הדוח")) +
          '<div class="pb">' + (ir.range ? '<p class="mute" style="margin:0">' + esc(ir.range) + "</p>" : "") +
          ((ir.tickers || []).length ? '<div class="chips bd-chips">' + ir.tickers.map(function (tk) { return '<a class="tag" dir="ltr" href="https://www.tradingview.com/symbols/' + encodeURIComponent(tk) + '/" target="_blank" rel="noopener"><b class="num">' + esc(tk) + "</b></a>"; }).join("") + "</div>" : "") + "</div>";
    }
  }
  /* הפאנלים האחים בטאב חדשות: בזק מהרשת · Barchart · חדשות RSS · המבזק האחרון */
  var FLASHD = null, NB_PULSE_ALL = false;
  function renderNewsSiblings() {
    var ep = document.getElementById("nb-pulse"), eb = document.getElementById("nb-bar"), er = document.getElementById("nb-rss"), ef = document.getElementById("nb-flash");
    if (ep) {
      var items = (PULSE_X && PULSE_X.items) || [], shown = NB_PULSE_ALL ? items : items.slice(0, 8);
      ep.innerHTML = !items.length ? panHd("בזק מהרשת") + '<div class="pb mute">אין בזקים כרגע.</div>'
        : panHd("בזק מהרשת", '<span class="mute">4 ערוצים + X Scan</span>', items.length > 8 ? '<a class="go" href="#" id="nb-pulse-more">' + (NB_PULSE_ALL ? "פחות" : "כל " + items.length + " הבזקים") + "</a>" : "") +
          '<div class="bd-list">' + shown.map(function (it) {
            return '<a class="fl" href="' + esc(it.link) + '" target="_blank" rel="noopener"><span class="num mute" dir="ltr">' + esc(it.time) + '</span><span class="mute src" dir="ltr">' + esc(it.source) + '</span><span class="tx" dir="auto">' + esc(it.text) + "</span></a>";
          }).join("") + "</div>";
      var pm = document.getElementById("nb-pulse-more");
      if (pm) pm.addEventListener("click", function (ev) { ev.preventDefault(); NB_PULSE_ALL = !NB_PULSE_ALL; renderNewsSiblings(); });
    }
    if (eb) {
      var mo = MORND, cardsB = "";
      if (mo && mo.file) cardsB += '<a class="prep" href="#morning" onclick="__goTab(\'morning\');return false"><div class="h"><span class="tag">סקירת בוקר' + (mo.time ? ' · <span class="num" dir="ltr">' + esc(mo.time) + "</span>" : "") + "</span>" + (mo.dateLabel ? '<span class="mute">' + esc(mo.dateLabel) + "</span>" : "") + "</div><p>" + esc(mo.subject || "דוח Barchart יומי") + "</p></a>";
      if (mo && mo.premkt && mo.premkt.file) cardsB += '<a class="prep" href="#morning" onclick="__goTab(\'morning\');return false"><div class="h"><span class="tag earn">טרום מסחר' + (mo.premkt.time ? ' · <span class="num" dir="ltr">' + esc(mo.premkt.time) + "</span>" : "") + "</span>" + (mo.premkt.dateLabel ? '<span class="mute">' + esc(mo.premkt.dateLabel) + "</span>" : "") + "</div><p>" + esc(mo.premkt.subject || "") + "</p></a>";
      var arch = archDays(["review", "premkt"], "").slice(0, 8);
      eb.innerHTML = panHd("Barchart", '<span class="mute">שתי מהדורות ביום · 06:00 ו-14:00</span>', bdGo("morning", "הארכיון")) +
        '<div class="pb">' + (cardsB || '<span class="mute">' + (mo ? "אין מהדורה היום." : "טוען…") + "</span>") +
        (arch.length ? '<div class="chips bd-chips">' + arch.map(function (k, i) { return '<button type="button" class="tag nb-arch' + (i === 0 ? " on" : "") + '" data-day="' + (i === 0 ? "" : k) + '"><span class="num" dir="ltr">' + esc(fmtTradeDate(k)) + "</span></button>"; }).join("") + "</div>" : "") + "</div>";
      eb.querySelectorAll(".nb-arch").forEach(function (b) {
        b.addEventListener("click", function () { MORN_DAY = b.dataset.day || null; if (MORND) renderMorning(document.getElementById("panel-morning"), MORND); __goTab("morning"); });
      });
    }
    if (er) {
      var nw = ((NEWS && NEWS.news) || []).slice().sort(function (a, b) { return (b.dt || "") < (a.dt || "") ? -1 : 1; }).slice(0, 6);
      er.innerHTML = panHd("חדשות", '<span class="mute">RSS, מתורגם</span>') + (nw.length ? '<div class="bd-list">' + nw.map(function (n) {
        return '<a class="li nb-news" href="' + esc(n.link) + '" target="_blank" rel="noopener"><span class="num mute" dir="ltr">' + esc(n.time || "") + '</span><span dir="auto">' + esc(n.title || n.titleEn || "") + (n.source ? ' <span class="mute s">· ' + esc(n.source) + "</span>" : "") + "</span></a>";
      }).join("") + "</div>" : '<div class="pb mute">' + (NEWS ? "אין חדשות כרגע." : "טוען…") + "</div>");
    }
    if (ef) {
      var f = FLASHD;
      if (!f || f.pct == null) ef.innerHTML = "";
      else {
        var ev = f.evidence || {}, lines = [];
        (ev.econ || []).forEach(function (e) { lines.push("📊 " + esc(e.he) + ": בפועל " + esc(e.actual) + " מול צפי " + esc(e.forecast) + " (" + esc(e.ilTime) + ")"); });
        (ev.pulse || []).slice(0, 3).forEach(function (p) { lines.push('<span dir="auto">💬 ' + esc(String(p.text).slice(0, 120)) + " · " + esc(p.source) + "</span>"); });
        (ev.news || []).slice(0, 2).forEach(function (n) { lines.push('<span dir="auto">📰 ' + esc(n.title) + " · " + esc(n.source) + "</span>"); });
        var fresh = f.ts && Date.now() - Date.parse(f.ts) < FLASH_TTL_MS;
        ef.innerHTML = panHd("מבזק ⚡ · " + (fresh ? "תנועה חדה עכשיו" : "המבזק האחרון"), '<span class="mute">ספייק של 0.5%+ ב-' + (f.windowMin || 30) + " דקות · מציג מה התפרסם באותן דקות, לא סיבתיות</span>") +
          '<div class="flash"><div><div class="big num ' + (f.pct < 0 ? "down" : "up") + '" dir="ltr">' + (f.pct > 0 ? "+" : "") + Number(f.pct).toFixed(2) + '%</div><div class="mute s">' + esc(f.label || f.symbol || "") + ' · <span class="num" dir="ltr">' + esc(f.date || "") + " " + esc(f.time || "") + "</span>" + (f.session ? " · " + esc(f.session) : "") + "</div></div>" +
          '<div class="fx">' + (lines.length ? lines.map(function (l) { return "<div>" + l + "</div>"; }).join("") : '<span class="mute">לא נמצאו פרסומים באותן דקות.</span>') + "</div></div>";
      }
    }
  }
  /* "מה השווקים מהמרים" — כל השורות, בטאב העולם */
  var BETSD = null;
  function renderWorldBets() {
    var el = document.getElementById("wd-bets");
    if (!el) return;
    var rows = (BETSD && BETSD.rows) || [];
    if (!rows.length) { el.innerHTML = ""; return; }
    el.innerHTML = panHd("מה השווקים מהמרים", '<span class="mute">Polymarket + Kalshi · הסתברות + שינוי יומי בנקודות</span>') + '<div class="pb bd-bets">' + rows.map(function (r) {
      var sub = String(r.sub || "").replace("ההימור המוביל: ", "");
      return '<div class="bet"><span>' + (r.url ? '<a href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.label) + "</a>" : esc(r.label)) + '<div class="mute s">ההימור המוביל: ' + esc(sub) + (r.src ? " · " + esc(r.src) : "") + "</div></span>" +
        '<div class="bar" role="img" aria-label="' + esc(r.pct) + '%"><i style="width:' + esc(r.pct) + '%"></i></div><span class="num" dir="ltr">' + esc(r.pct) + "%</span>" +
        '<span class="mute s">' + (r.chg ? '<span class="num ' + (r.chg > 0 ? "up" : "down") + '" dir="ltr">' + (r.chg > 0 ? "+" : "−") + Math.abs(r.chg) + "</span> נק׳ יומי" : "ללא שינוי") + "</span></div>";
    }).join("") + "</div>";
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
        .then(function (d) { NEWS = d; renderPulseNews(); renderNewsSiblings(); })
        .catch(function () {});
      fetchJSON("data/movers.json")
        .then(function (d) { MOVERS = d; renderHomeSplit(); renderFocus(); })
        .catch(function () {});
      fetchJSON("data/pulse.json")
        .then(function (d) { PULSE_X = d; renderPulseX(); renderNewsSiblings(); })
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
          refreshRotationWheel();
        })
        .catch(function () {});
      // סיכום השבוע (11.9.2026): נבנה ע"י build_weekly.py כשסגירת שישי נקלטת,
      // ומוצג בבית מערב שישי עד תחילת השבוע הבא; אחר-כך נעלם מעצמו
      fetchJSON("data/weekly.json")
        .then(function (d) { if (!freshD("weekly", d)) return; WEEKLY = d; renderWeekly(d); renderLead(); refreshRotationWheel(); })
        .catch(function () {});
      // עונת הדוחות (3.10.2026): ציר מתחת לכותרת, רק בזמן העונה
      fetchJSON("data/earnings_season.json")
        .then(function (d) { if (!freshD("season", d)) return; SEASON = d; renderSeason(); if (EARN) renderWeekCal(document.getElementById("weekcal-body"), EARN); })
        .catch(function () {});
      fetchJSON("data/earnings.json")
        .then(function (d) {
          if (!freshD("earnings", d)) return;
          EARN = d; EARNW = d.window || {};
          renderHomeSplit(); renderHomeCal();
          renderWeekCal(document.getElementById("weekcal-body"), d);
          // תגי "מדווחת בקרוב" על טבלאות שכבר רונדרו לפני שהמפה הגיעה
          if (MOMD) renderMomentum(document.getElementById("panel-momentum"), MOMD);
          if (CANDD) renderCandidates(document.getElementById("panel-candidates"), CANDD);
          renderFocus();
        })
        .catch(function () { if (!EARN) emptyPanel(document.getElementById("weekcal-body"), "📅", "לוח דיווחים — בקרוב", ""); });
      // Home + indices share the indices dataset
      fetchJSON("data/indices.json").then(function (d) {
        if (!freshD("indices", d)) return;
        INDD = d;
        renderLead(); renderHomeAround();
        renderIndicesDetail(document.getElementById("panel-indices"), d);
        renderFocus();   // התאריך בכותרת "מניות במוקד" תלוי ב-INDD
        refreshRotationWheel();
        noteSig("indices", d);
      }).catch(function (err) {
        // כשל מדדים מפיל רק את הידיעה המובילה — שאר הבית ממשיך לעבוד
        if (INDD) return;
        emptyPanel(document.getElementById("lead-main"), "📡", "נתוני השוק לא נטענו", String(err.message || err));
        emptyPanel(document.getElementById("panel-indices"), "📡", "נתוני המדדים לא נטענו", "");
      });
      fetchJSON("data/momentum.json")
        .then(function (d) { if (!freshD("momentum", d)) return; MOMD = d; renderMomentum(document.getElementById("panel-momentum"), d); renderFocus(); renderHomeSplit(); renderStockSiblings(); noteSig("momentum", d); })
        .catch(function () { if (!MOMD) emptyPanel(document.getElementById("panel-momentum"), "🚀", "מומנטום — בקרוב", ""); });
      fetchJSON("data/forecasts.json")
        .then(function (d) { if (!freshD("forecasts", d)) return; FCAST = d; if (INDD) renderLead(); renderForecastPan(); })
        .catch(function () {});
      fetchJSON("data/insider.json")
        .then(function (d) { if (!freshD("insider", d)) return; renderInsider(document.getElementById("panel-insider"), d); renderStockSiblings(); noteSig("insider", d); })
        .catch(function () { if (!("insider" in DAILY_SIGS)) emptyPanel(document.getElementById("panel-insider"), "🕵️", "Insider — בקרוב", ""); });
      // הנבחרות (30.9.2026): המהדורה + יומן הכנות; היומן לא חוסם את הקלפים
      Promise.all([fetchJSON("data/earnings_prep.json"), fetchJSON("data/earnings_prep_notes.json").catch(function () { return {}; }),
        fetchJSON("data/earnings_review_notes.json").catch(function () { return {}; })])
        .then(function (r) { if (!freshD("prep", r)) return; PREPD = r[0]; PREPN = r[1]; PREPR = r[2]; renderPrep(document.getElementById("panel-prep")); renderHomeCal(); if (EARN) renderWeekCal(document.getElementById("weekcal-body"), EARN); noteSig("prep", [r[1], r[2]]); })
        .catch(function () { if (!PREPD) renderPrep(document.getElementById("panel-prep")); });
      Promise.all([fetchJSON("data/picks.json"), fetchJSON("data/picks_ledger.json").catch(function () { return null; })])
        .then(function (r) { if (!freshD("picks", r[0])) return; PICKD = r[0]; PICKL = r[1]; renderPicks(document.getElementById("panel-picks")); renderHomePicks(); noteSig("picks", r[0]); })
        .catch(function () { if (!PICKD) emptyPanel(document.getElementById("panel-picks"), "✦", "הנבחרות — בקרוב", "המהדורה הראשונה נבנית אחרי הריצה הבאה של הבוט."); });
      fetchJSON("data/sectors.json")
        .then(function (d) { if (!freshD("sectors", d)) return; renderSectors(document.getElementById("panel-sectors"), d); noteSig("sectors", d); })
        .catch(function () { if (!("sectors" in DAILY_SIGS)) emptyPanel(document.getElementById("panel-sectors"), "🔄", "דוח סקטורים — בקרוב", ""); });
      Promise.all([fetchJSON("data/world.json"), fetchJSON("data/weekend.json").catch(function () { return null; })])
        .then(function (r) { WKND = r[1]; WORLDD = r[0]; renderWorld(document.getElementById("panel-world"), r[0]); renderHomeAround(); })
        .catch(function () { emptyPanel(document.getElementById("panel-world"), "🌍", "שווקים בינלאומיים — בקרוב", ""); });
      fetchJSON("data/morning.json")
        .then(function (d) { if (!freshD("morning", d)) return; MORND = d; renderMorning(document.getElementById("panel-morning"), d); renderNewsSiblings(); noteSig("morning", d); })
        .catch(function () { if (!("morning" in DAILY_SIGS)) emptyPanel(document.getElementById("panel-morning"), "📊", "Barchart — בקרוב", ""); });
      fetchJSON("data/econ.json")
        .then(function (d) { if (!freshD("econ", d)) return; ECON = d; renderEcon(); refreshLeadAgenda(); renderHomeCal(); if (EARN) renderWeekCal(document.getElementById("weekcal-body"), EARN); })
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
        .then(function (d) { if (!freshD("candidates", d)) return; CANDD = d; renderCandidates(document.getElementById("panel-candidates"), d); renderFocus(); renderHomeSplit(); renderStockSiblings(); noteSig("candidates", d); })
        .catch(function () { if (!CANDD) emptyPanel(document.getElementById("panel-candidates"), "🎯", "מועמדים — בקרוב", ""); });
      fetchJSON("data/trades.json")
        .then(function (d) { if (!freshD("trades", d)) return; renderTrades(document.getElementById("panel-trades"), d); renderStockSiblings(); noteSig("trades", d); })
        .catch(function () { if (!("trades" in DAILY_SIGS)) emptyPanel(document.getElementById("panel-trades"), "💡", "הצעות לטרייד — בקרוב", ""); });
      fetchJSON("data/reports.json")
        .then(function (d) { if (!freshD("reports", d)) return; REPD = d; renderReports(document.getElementById("panel-reports"), d); renderFocus(); if (EARN) renderWeekCal(document.getElementById("weekcal-body"), EARN); noteSig("reports", d); })
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
        .then(function (d) { if (!freshD("bets", d)) return; BETSD = d; renderBets(d); renderWorldBets(); })
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


  boot();
})();
