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
    themeBtn.textContent = dark ? "☀️" : "🌙";
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
    if (location.hash.slice(1) !== name) history.replaceState(null, "", "#" + name);
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

    var verdictCard =
      '<div class="card verdict tone-' + esc(v.tone || "") + '">' +
        '<span class="emoji">' + h(v.emoji || "📊") + "</span>" +
        "<div><h2>" + esc(v.headline || "סקירת שוק") + "</h2>" +
        "<p>" + esc(v.subline || "") + "</p>" + lights + "</div>" +
      "</div>";

    var scoreCards =
      '<div class="grid grid-4" style="margin-top:16px">' +
      [["combined", "ציון משולב"], ["tech", "טכני"], ["breadth", "רוחב"], ["flow", "Flow"]]
        .map(function (p) {
          var val = s[p[0]];
          return '<div class="card stat"><div class="label">' + p[1] + "</div>" +
            '<div class="value num ' + scoreBand(val) + '">' + (val == null ? "—" : val) + "</div></div>";
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

    var links = opts.showLinks ?
      '<div class="cta-links">' +
        '<button class="cta" onclick="__goTab(\'indices\')">פירוט מדדים מלא ←</button>' +
        '<button class="cta" onclick="__goTab(\'momentum\')">מומנטום ←</button>' +
        '<button class="cta" onclick="__goTab(\'briefing\')">תדרוך משקיעים ←</button>' +
      "</div>" : "";

    el.innerHTML =
      stamp(d._meta) + verdictCard + scoreCards + marketCards +
      (opts.showLinks ? '<div class="section-title">מבט מהיר</div>' + links : "") +
      concl;
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
    renderMarketOverview(overview, d, { showLinks: false });

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

  function renderMomentum(el, d) {
    if (!d || !d.lists || !d.lists.length) {
      emptyPanel(el, "🚀", "מומנטום — בקרוב", "");
      return;
    }
    var nav = '<div class="chips" style="margin-bottom:14px">' +
      d.lists.map(function (l, i) {
        return '<button class="chip mom-tab' + (i === 0 ? " lead" : "") + '" data-mom="' + i + '">' +
          esc(l.title) + " <span class=\"num\">" + l.count + "</span></button>";
      }).join("") + "</div>";

    var tables = d.lists.map(function (l, i) {
      var rows = l.rows.map(function (r) {
        return "<tr><td><b>" + esc(r.sym) + "</b></td>" +
          "<td>" + esc(r.name) + "</td>" +
          '<td class="num">' + esc(r.last) + "</td>" +
          '<td class="num ' + chgClass(r.chg) + '">' + esc(r.chg) + "</td>" +
          "<td>" + esc(r.trend) + "</td>" +
          "<td>" + esc(r.opinion) + "</td>" +
          "<td>" + esc(r.strength) + "</td>" +
          '<td class="num">' + esc(r.rsi) + "</td></tr>";
      }).join("");
      return '<div class="mom-list" data-mom="' + i + '" style="display:' + (i === 0 ? "block" : "none") + '">' +
        '<div class="table-wrap"><table><thead><tr>' +
        "<th>סימבול</th><th>שם</th><th class=\"num\">מחיר</th><th class=\"num\">שינוי</th>" +
        "<th>מגמה</th><th>המלצה</th><th>חוזק</th><th class=\"num\">RSI</th>" +
        "</tr></thead><tbody>" + rows + "</tbody></table></div>" +
        '<p class="stamp">מקור: ' + esc(l.file) + " · מוצגות עד 30 שורות מובילות</p></div>";
    }).join("");

    el.innerHTML = stamp(d._meta) +
      '<div class="section-title" style="margin-top:0">🚀 סורק מומנטום</div>' + nav + tables +
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
        '<iframe class="brief-frame" src="' + esc(sl.file) + '" title="' + esc(sl.subject || "") +
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
      '<iframe class="brief-frame" src="' + esc(d.file) + '" title="' + esc(d.subject || "") +
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
        "<td><b>" + esc(c.symbol) + "</b></td>" +
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
      '<div class="stamp" style="margin:6px 0 0">Entry/Stop/Target ברמות המערכת · R היסטורי = ביצוע 2 שנים · מסודר לפי דירוג משולב</div></div>' +
      '<div class="table-wrap"><table><thead><tr>' +
      "<th class=\"num\">#</th><th>סימבול</th><th>Setup</th>" +
      "<th class=\"num\">כניסה</th><th class=\"num\">סטופ</th><th class=\"num\">מטרה</th>" +
      "<th class=\"num\">סיכון</th><th class=\"num\">TP</th><th class=\"num\">RVOL</th><th class=\"num\">R היסט'</th>" +
      "</tr></thead><tbody>" + rows + "</tbody></table></div>";
  }

  /* ---------- boot ---------- */
  function boot() {
    // Home + indices share the indices dataset
    fetchJSON("data/indices.json").then(function (d) {
      renderMarketOverview(document.getElementById("panel-home"), d, { showLinks: true });
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
      .then(function (d) { renderBriefing(document.getElementById("panel-briefing"), d); noteSig("briefing", d); })
      .catch(function () { emptyPanel(document.getElementById("panel-briefing"), "📣", "תדרוך משקיעים — בקרוב", ""); });

    fetchJSON("data/morning.json")
      .then(function (d) { renderMorning(document.getElementById("panel-morning"), d); noteSig("morning", d); })
      .catch(function () { emptyPanel(document.getElementById("panel-morning"), "🌅", "סקירת בוקר — בקרוב", ""); });

    fetchJSON("data/candidates.json")
      .then(function (d) { renderCandidates(document.getElementById("panel-candidates"), d); noteSig("candidates", d); })
      .catch(function () { emptyPanel(document.getElementById("panel-candidates"), "🎯", "מועמדים — בקרוב", ""); });

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
