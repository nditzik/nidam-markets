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
    var tw = document.getElementById("ticker-wrap");
    if (tw) tw.style.display = name === "home" ? "block" : "none";
    if (location.hash.slice(1) !== name) history.replaceState(null, "", "#" + name);
  }

  /* ---- live market ticker (our own strip, from data/market.json via Yahoo) ---- */
  function fmtQuote(v) {
    if (v == null || isNaN(v)) return "—";
    var d = Math.abs(v) < 10 ? 3 : 2;
    return Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: d });
  }
  function renderMarketTicker(el, data) {
    if (!el || !data || !data.items || !data.items.length) return;
    var one = data.items.map(function (it) {
      var c = it.chg, cls = c > 0 ? "up" : (c < 0 ? "down" : ""), arr = c > 0 ? "▲" : (c < 0 ? "▼" : "");
      var chg = (c == null) ? "" :
        ' <span class="mt-chg ' + cls + '">' + arr + " " + (c > 0 ? "+" : "") + Number(c).toFixed(2) + "%</span>";
      return '<span class="mt-item"><span class="mt-label">' + esc(it.label) + "</span>" +
        '<span class="mt-price num">' + fmtQuote(it.price) + "</span>" + chg + "</span>";
    }).join("");
    // duplicate for a seamless scrolling loop
    el.innerHTML = '<div class="mt-track">' + one + one + "</div>";
  }
  function loadTicker() {
    var el = document.getElementById("ticker");
    if (!el) return;
    fetchJSON("data/market.json")
      .then(function (d) { renderMarketTicker(el, d); })
      .catch(function () {});
  }

  /* ---- "new since last visit" tab badges ---- */
  var SIGS = {};
  function noteSig(tab, d) {
    var sig = (d && d._meta && d._meta.updatedAt) || (d && d.date) || "";
    if (!sig) return;
    SIGS[tab] = sig;
    var key = "seen-" + tab;
    var seen = localStorage.getItem(key);
    if (seen === null) { localStorage.setItem(key, sig); return; } // first visit = baseline
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
    if (SIGS[tab]) localStorage.setItem("seen-" + tab, SIGS[tab]);
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
    var el = document.getElementById("home-briefing");
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
    var schedHtml = sched.length
      ? '<div class="brief-sched"><div class="bs-title">🕐 לוז יומי צפוי</div><ul>' +
        sched.map(function (x) {
          return '<li><span class="bs-time num" dir="ltr">' + esc(x.time) + "</span>" +
            '<span class="bs-ev">' + esc(x.text) + "</span></li>";
        }).join("") + "</ul></div>" : "";

    var asOf = edition === "afternoon" ? "15:00" : "06:00";   // שעת המהדורה (משתנה בין בוקר/צהריים)

    el.innerHTML =
      '<div class="section-title brief-top">📋 תדרוך משקיעים אחרון</div>' +
      '<div class="card brief-card">' +
        '<div class="brief-head"><span class="brief-ed">' + esc(label) +
          (s.dateLabel ? ' · <span class="brief-date" dir="ltr">' + esc(s.dateLabel) + "</span>" : "") +
          ' · <span class="brief-asof">נכון לשעה <span dir="ltr">' + asOf + "</span></span>" +
        "</span>" + sentHtml + "</div>" +
        newsHtml + schedHtml +
      "</div>";
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
    var verdictCard =
      '<div class="card verdict tone-' + esc(v.tone || "") + '">' +
        '<div class="v-top">' +
          '<span class="emoji">' + h(v.emoji || "📊") + "</span>" +
          (tradeDate ? '<span class="vday">יום המסחר ' + tradeDate + "</span>" : "") +
        "</div>" +
        "<h2>" + esc(v.headline || "סקירת שוק") + "</h2>" +
        "<p>" + esc(v.subline || "") + "</p>" + lights +
      "</div>";

    var fl = d.flow || {};
    var scoreCards =
      '<div class="grid grid-4" style="margin-top:16px">' +
      [["combined", "ציון משולב"], ["tech", "טכני"], ["breadth", "רוחב"], ["flow", "אופציות"]]
        .map(function (p) {
          var val = s[p[0]];
          var sub = "", tip = "";
          if (p[0] === "flow" && fl.directionLabel) {
            sub = '<div class="sub">' + esc(fl.directionLabel) + "</div>";
            if (fl.directionReason) tip = ' title="' + esc(fl.directionReason) + '"';
          }
          return '<div class="card stat"' + tip + '><div class="label">' + p[1] + "</div>" +
            '<div class="value num ' + scoreBand(val) + '">' + (val == null ? "—" : val) + "</div>" + sub + "</div>";
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

    el.innerHTML =
      stampHtml +
      (opts.home ? '<div id="home-briefing"></div>' : "") +   // תדריך אחרון — מעל תמונת המצב
      verdictCard + scoreCards + marketCards +
      (opts.detail ? concl : "");   // "המסקנה של איציק" רק בטאב מדדים, לא בבית

    if (opts.home) renderHomeBriefing();
  }

  function renderIndicesDetail(el, d) {
    var c = d.conclusion || {};
    var rot = d.rotation || {};
    var ro = d.riskOff || {};

    var analysis = "";
    if (c.analysis && c.analysis.length) {
      analysis = '<div class="section-title">🔬 ניתוח לפי תחום</div><div class="card"><ul class="analysis">' +
        c.analysis.map(function (a) {
          return '<li class="tone-' + esc(a.tone || "") + '"><span class="tone-dot"></span>' +
            '<span class="domain">' + esc(a.domain) + "</span><span>" + esc(a.text) + "</span></li>";
        }).join("") + "</ul></div>";
    }

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
    el.insertAdjacentHTML("beforeend", head);
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
            "<td>" + tvLink(r.symbol) + "</td>" +
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

  function renderBriefing(el, d) {
    var slots = [];
    if (d && d.morning) slots.push(["morning", "בוקר", d.morning]);
    if (d && d.afternoon) slots.push(["afternoon", "אחר הצהריים", d.afternoon]);
    if (!slots.length) {
      emptyPanel(el, "📣", "תדרוך משקיעים — בקרוב", "הטאב יתמלא ברגע שצינור הג'ימייל יופעל.");
      return;
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
      '<div class="section-title" style="margin-top:0">📣 תדרוך משקיעים</div>' + nav + frames;

    el.querySelectorAll(".brief-tab").forEach(function (b) {
      b.addEventListener("click", function () {
        var k = b.dataset.brief;
        el.querySelectorAll(".brief-tab").forEach(function (x) { x.classList.toggle("lead", x.dataset.brief === k); });
        el.querySelectorAll(".brief-view").forEach(function (x) { x.style.display = x.dataset.brief === k ? "block" : "none"; });
      });
    });
  }

  function renderMorning(el, d) {
    if (!d || d._status === "pending" || !d.file) {
      emptyPanel(el, "🌅", "סקירת בוקר — בקרוב", "תחובר ברגע שצינור ה-Barchart יופעל.");
      return;
    }
    el.innerHTML = stamp(d._meta) +
      '<div class="section-title" style="margin-top:0">🌅 סקירת בוקר</div>' +
      '<div class="card" style="padding:14px 18px;margin-bottom:12px">' +
      "<strong>" + esc(d.subject || "סיכום Barchart יומי") + "</strong>" +
      (d.dateLabel ? '<div class="stamp" style="margin:4px 0 0">' + esc(d.dateLabel) +
        (d.time ? " · " + esc(d.time) : "") + "</div>" : "") +
      "</div>" +
      '<iframe class="brief-frame" src="' + bust(d.file, d._meta) + '" title="' + esc(d.subject || "") +
      '" style="width:100%;border:1px solid var(--border);border-radius:14px;background:#fff;min-height:640px" ' +
      'onload="try{this.style.height=(this.contentWindow.document.body.scrollHeight+30)+\'px\'}catch(e){}"></iframe>';
  }

  function renderCandidates(el, d) {
    if (!d || d._status === "pending" || !d.candidates) {
      emptyPanel(el, "🎯", "מועמדים — בקרוב", "יחובר ברגע שצינור ה-IBKR יופעל.");
      return;
    }
    if (!d.candidates.length) {
      el.innerHTML = stamp(d._meta) +
        '<div class="panel-empty"><span class="emoji">🎯</span><strong>אין מועמדים ל-' +
        esc(d.date || "") + "</strong><p style=\"margin:8px 0 0\">הסריקה לא מצאה איתותים היום.</p></div>";
      return;
    }
    function n(v, dgts) { return (v == null || isNaN(v)) ? "—" : Number(v).toFixed(dgts); }
    var rows = d.candidates.map(function (c) {
      return "<tr><td class=\"num\">" + c.rank + "</td>" +
        "<td>" + tvLink(c.symbol) + "</td>" +
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
      '<div class="card" style="padding:14px 18px;margin-bottom:12px">' +
      "<strong>" + esc(d.date || "") + "</strong> · " + (d.count || 0) + " מועמדים" +
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
    setInterval(loadTicker, 180000); // refresh the strip every 3 min
    // Home + indices share the indices dataset
    fetchJSON("data/indices.json").then(function (d) {
      renderMarketOverview(document.getElementById("panel-home"), d, { home: true });
      renderIndicesDetail(document.getElementById("panel-indices"), d);
      noteSig("indices", d);
    }).catch(function (err) {
      emptyPanel(document.getElementById("panel-home"), "📡", "נתוני השוק לא נטענו", String(err.message || err));
      emptyPanel(document.getElementById("panel-indices"), "📡", "נתוני המדדים לא נטענו", "");
    });

    fetchJSON("data/momentum.json")
      .then(function (d) { renderMomentum(document.getElementById("panel-momentum"), d); noteSig("momentum", d); })
      .catch(function () { emptyPanel(document.getElementById("panel-momentum"), "🚀", "מומנטום — בקרוב", ""); });

    fetchJSON("data/briefing.json")
      .then(function (d) { BRIEF = d; renderBriefing(document.getElementById("panel-briefing"), d); renderHomeBriefing(); noteSig("briefing", d); })
      .catch(function () { emptyPanel(document.getElementById("panel-briefing"), "📣", "תדרוך משקיעים — בקרוב", ""); });

    fetchJSON("data/morning.json")
      .then(function (d) { renderMorning(document.getElementById("panel-morning"), d); noteSig("morning", d); })
      .catch(function () { emptyPanel(document.getElementById("panel-morning"), "🌅", "סקירת בוקר — בקרוב", ""); });

    fetchJSON("data/candidates.json")
      .then(function (d) { renderCandidates(document.getElementById("panel-candidates"), d); noteSig("candidates", d); })
      .catch(function () { emptyPanel(document.getElementById("panel-candidates"), "🎯", "מועמדים — בקרוב", ""); });

    fetchJSON("data/reports.json")
      .then(function (d) { renderReports(document.getElementById("panel-reports"), d); noteSig("reports", d); })
      .catch(function () { emptyPanel(document.getElementById("panel-reports"), "📑", "ניתוח דוחות — בקרוב", ""); });

    fetchJSON("data/_health.json")
      .then(function (d) {
        renderHealth(document.getElementById("health"), d);
        renderTodayBar(document.getElementById("today-bar"), d);
      })
      .catch(function () {});

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
