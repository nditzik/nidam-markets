/* ta_ui.js — חלונית "ניתוח טכני" לכל טיקר (29.9.2026).
   נטען בעצלתיים (יחד עם ta_engine.js) בלחיצה הראשונה על טיקר. קורא data/bars/SYM.json
   (500 נרות סגורים שהבוט שומר), מוסיף את הנר של היום מסורק TradingView (is_partial בזמן
   המסחר), מריץ TAEngine.analyze ומרנדר: 4 אריחים · סיכום · גרף נרות עם 6 ממוצעים ואזורי
   תמיכה/התנגדות/פריצה · 7 ציונים · מאזן הראיות · פירוט. הכל טקסט מהמנוע — אין LLM.
   ממשק: window.__taRender(sym, containerEl), window.__taHas(sym, cb). */
(function () {
  "use strict";
  var IDX = null, IDX_AT = 0, BARS = {}, NY = "America/New_York";
  var MA_COLOR = { EMA20: "#43a047", EMA40: "#8e8e93", SMA50: "#1e88e5", SMA100: "#e0a800", SMA150: "#26c6da", SMA200: "#e53935" };
  var MA_DASH = { EMA20: "6 4", EMA40: "6 4" };
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function f2(x) { return (x == null || !isFinite(x)) ? "—" : Number(x).toFixed(2); }
  function f1(x) { return (x == null || !isFinite(x)) ? "—" : Number(x).toFixed(1); }
  function nyToday() {
    try { return new Intl.DateTimeFormat("en-CA", { timeZone: NY, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date()); }
    catch (e) { return new Date().toISOString().slice(0, 10); }
  }
  function session() { return typeof window.__jsSession === "function" ? window.__jsSession() : "closed"; }

  /* ───── נתונים ───── */
  function loadIndex(cb) {
    var now = Date.now();
    // אינדקס טרי לכל דקה (ולא 10 דק'): הבוט מוסיף סמלים בכל ריצה, ו-404 של CDN לא יישמר
    if (IDX && now - IDX_AT < 60 * 1000) { cb(IDX); return; }
    fetch("data/bars/index.json?v=" + Math.floor(now / 60000), { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { IDX = d || { symbols: {} }; IDX_AT = now; cb(IDX); })
      .catch(function () { cb(IDX || { symbols: {} }); });
  }
  function hasBars(sym, cb) { loadIndex(function (ix) { var s = ix && ix.symbols && ix.symbols[sym]; cb(!!(s && s.last)); }); }
  function loadBars(sym, cb) {
    loadIndex(function (ix) {
      var info = ix && ix.symbols && ix.symbols[sym];
      if (!info || !info.last) { cb(null); return; }
      if (BARS[sym] && BARS[sym].last === info.last) { cb(BARS[sym]); return; }
      fetch("data/bars/" + encodeURIComponent(sym) + ".json?v=" + info.last).then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
          if (!d || !d.bars) { cb(null); return; }
          var bars = d.bars.map(function (b) { return { date: b[0], open: b[1], high: b[2], low: b[3], close: b[4], volume: b[5] }; });
          BARS[sym] = { last: d.last, bars: bars, updated: d.updated }; cb(BARS[sym]);
        }).catch(function () { cb(null); });
    });
  }
  // הנר של היום מסורק TradingView: בזמן המסחר — נר מתהווה; אחרי הסגירה ולפני עדכון הבוט — נר סגור
  function liveBar(sym, cb) {
    var ses = session(), today = nyToday();
    if (ses === "closed" || ses === "pre") { cb(null); return; }
    fetch("https://scanner.tradingview.com/america/scan", {
      method: "POST",
      body: JSON.stringify({ filter: [{ left: "name", operation: "equal", right: sym }, { left: "exchange", operation: "in_range", right: ["NASDAQ", "NYSE", "AMEX"] }],
        columns: ["name", "open", "high", "low", "close", "volume"], range: [0, 3] })
    }).then(function (r) { return r.json(); }).then(function (d) {
      var row = (d.data || []).filter(function (r) { return r.d && r.d[0] === sym; })[0];
      if (!row) { cb(null); return; }
      var v = row.d;
      if ([1, 2, 3, 4].some(function (i) { return v[i] == null || !(v[i] > 0); })) { cb(null); return; }
      cb({ date: today, open: v[1], high: Math.max(v[2], v[1], v[4]), low: Math.min(v[3], v[1], v[4]), close: v[4], volume: v[5] || 0, is_partial: ses === "regular" });
    }).catch(function () { cb(null); });
  }

  /* ───── גרף נרות ───── */
  function chartSvg(bars, r, width) {
    // רוחב הקנבס = רוחב המכל בפיקסלים (1:1), כדי שהטקסט יישאר קריא גם בטלפון; פחות נרות במסך צר
    var W = Math.max(320, Math.min(1400, Math.round(width || 1000))), narrow = W < 640;
    var n = Math.min(bars.length, narrow ? 60 : 120), start = bars.length - n, win = bars.slice(start);
    var H = narrow ? 320 : 420, PH = narrow ? 215 : 300, VH = narrow ? 45 : 60, padR = 54, padL = 6, top = 14, gap = 10;
    var lo = Infinity, hi = -Infinity;
    win.forEach(function (b) { if (b.low < lo) lo = b.low; if (b.high > hi) hi = b.high; });
    var series = r.series, mas = ["EMA20", "EMA40", "SMA50", "SMA100", "SMA150", "SMA200"];
    mas.forEach(function (k) { var s = series.ma[k]; for (var i = start; i < bars.length; i++) if (s[i] != null) { if (s[i] < lo) lo = s[i]; if (s[i] > hi) hi = s[i]; } });
    (r.levels.chart_supports || []).forEach(function (z) { if (z.low < lo) lo = z.low; });
    if (r.levels.resistance && r.levels.resistance.high > hi) hi = r.levels.resistance.high;
    var span = hi - lo || 1; lo -= span * 0.03; hi += span * 0.03; span = hi - lo;
    var xw = (W - padL - padR) / n;
    function X(i) { return padL + (i - start) * xw + xw / 2; }
    function Y(p) { return top + (hi - p) / span * PH; }
    var out = [], labs = [];
    // שלב 7 (10.10.2026): תוויות עברית לא בתוך ה-SVG (WebKit הופך אותן) — שכבת HTML מעל הגרף, ראו ovHtml למטה
    function lbl(y, cls, name, nums) { labs.push({ y: y, cls: cls, name: name, nums: nums }); }
    // אזורים
    (r.levels.chart_supports || []).forEach(function (z, k) {
      out.push('<rect x="' + padL + '" y="' + Y(z.high) + '" width="' + (W - padL - padR) + '" height="' + Math.max(1, Y(z.low) - Y(z.high)) + '" class="ta-zs" opacity="' + (k ? 0.10 : 0.16) + '"/>');
      lbl((Y(z.high) + Y(z.low)) / 2, "ta-l-sup", "תמיכה", f2(z.low) + "–" + f2(z.high));
    });
    if (r.levels.resistance) {
      var rz = r.levels.resistance;
      out.push('<rect x="' + padL + '" y="' + Y(rz.high) + '" width="' + (W - padL - padR) + '" height="' + Math.max(1, Y(rz.low) - Y(rz.high)) + '" class="ta-zr" opacity="0.13"/>');
      lbl((Y(rz.high) + Y(rz.low)) / 2, "ta-l-res", "התנגדות", f2(rz.low) + "–" + f2(rz.high));
    }
    if (r.breakout && r.breakout.event && r.breakout.event.index >= start - 20) {
      var bz = r.breakout.zone, x0 = Math.max(padL, X(r.breakout.event.index) - xw);
      out.push('<rect x="' + x0 + '" y="' + Y(bz.high) + '" width="' + (W - padR - x0) + '" height="' + Math.max(1, Y(bz.low) - Y(bz.high)) + '" class="ta-zb" fill="none" stroke-dasharray="5 4" stroke-width="1.2"/>');
      lbl((Y(bz.high) + Y(bz.low)) / 2, "ta-l-bo", /פריצ/.test(r.breakout.label) ? r.breakout.label : "אזור הפריצה · " + r.breakout.label, f2(bz.low) + "–" + f2(bz.high));
    }
    if (r.market_structure.protected_low && r.market_structure.protected_low.price > lo) {
      var pl = r.market_structure.protected_low;
      out.push('<line x1="' + padL + '" x2="' + (W - padR) + '" y1="' + Y(pl.price) + '" y2="' + Y(pl.price) + '" class="ta-pl" stroke-dasharray="2 4" stroke-width="1"/>');
      lbl(Y(pl.price), "ta-l-pl", "שפל מוגן", f2(pl.price));
    }
    // ממוצעים
    mas.forEach(function (k) {
      var s = series.ma[k], d = "", pen = false;
      for (var i = start; i < bars.length; i++) { if (s[i] == null) { pen = false; continue; } d += (pen ? "L" : "M") + X(i).toFixed(1) + " " + Y(s[i]).toFixed(1); pen = true; }
      if (d) out.push('<path d="' + d + '" fill="none" stroke="' + MA_COLOR[k] + '" stroke-width="1.4"' + (MA_DASH[k] ? ' stroke-dasharray="' + MA_DASH[k] + '"' : "") + ' opacity=".9"/>');
    });
    // נרות
    var maxV = 0; win.forEach(function (b) { if (b.volume > maxV) maxV = b.volume; });
    var vTop = top + PH + gap;
    win.forEach(function (b, j) {
      var i = start + j, x = X(i), up = b.close >= b.open, col = up ? "ta-up" : "ta-dn", bw = Math.max(1.5, xw * 0.62);
      out.push('<line x1="' + x + '" x2="' + x + '" y1="' + Y(b.high) + '" y2="' + Y(b.low) + '" class="' + col + '" stroke-width="1"/>');
      var y1 = Y(Math.max(b.open, b.close)), y2 = Y(Math.min(b.open, b.close));
      out.push('<rect x="' + (x - bw / 2) + '" y="' + y1 + '" width="' + bw + '" height="' + Math.max(1, y2 - y1) + '" class="' + col + '"' + (b.is_partial ? ' opacity=".55" stroke-dasharray="2 2"' : "") + '/>');
      if (maxV) { var vh = b.volume / maxV * VH; out.push('<rect x="' + (x - bw / 2) + '" y="' + (vTop + VH - vh) + '" width="' + bw + '" height="' + vh + '" class="' + col + '" opacity=".35"/>'); }
    });
    // תוויות שיאים/שפלים ראשיים
    r.market_structure.swings.forEach(function (p) {
      if (p.index < start) return;
      var isH = p.kind === "HIGH";
      out.push('<text x="' + X(p.index) + '" y="' + (isH ? Y(p.price) - 6 : Y(p.price) + 14) + '" class="ta-sw ' + (isH ? "ta-dn-t" : "ta-up-t") + '" text-anchor="middle">' + p.label + "</text>");
    });
    // ציר מחיר
    for (var k = 0; k <= 5; k++) { var p = lo + span * k / 5, y = Y(p); out.push('<line x1="' + padL + '" x2="' + (W - padR) + '" y1="' + y + '" y2="' + y + '" class="ta-grid"/><text x="' + (W - padR + 6) + '" y="' + (y + 4) + '" class="ta-ax">' + f2(p) + "</text>"); }
    // ציר זמן
    var step = Math.max(1, Math.round(n / 6));
    for (var j = 0; j < n; j += step) { var d = win[j].date; out.push('<text x="' + X(start + j) + '" y="' + (vTop + VH + 14) + '" class="ta-ax" text-anchor="middle">' + d.slice(8, 10) + "." + d.slice(5, 7) + "</text>"); }
    var legend = mas.map(function (k) { return '<span><i style="background:' + MA_COLOR[k] + '"></i>' + k + "</span>"; }).join("");
    // שכבת התוויות: מרווח מינימלי של 17 יחידות בין תוויות (ממוינות לפי גובה), בתוך גבולות אזור המחיר
    labs.sort(function (a, b) { return a.y - b.y; });
    for (var q = 1; q < labs.length; q++) if (labs[q].y - labs[q - 1].y < 17) labs[q].y = labs[q - 1].y + 17;
    for (var q2 = labs.length - 1; q2 >= 0; q2--) { var mx = top + PH - 8 - (labs.length - 1 - q2) * 17; if (labs[q2].y > mx) labs[q2].y = mx; }
    var ov = labs.map(function (l) {
      return '<span class="ta-lab ' + l.cls + '" style="top:' + (l.y / H * 100).toFixed(2) + '%;left:' + ((padL + 6) / W * 100).toFixed(2) + '%"><i></i>' + esc(l.name) +
        (l.nums ? ' <b class="num" dir="ltr">' + esc(l.nums) + "</b>" : "") + "</span>";
    }).join("");
    // בטלפון התוויות מכסות את הנרות — שם הן יורדות לשורת "רמות" מתחת לגרף (מהגבוהה לנמוכה)
    var lv = narrow && labs.length ? '<div class="ta-levels" dir="rtl">' + labs.map(function (l) {
      return '<span class="ta-lab ' + l.cls + '"><i></i>' + esc(l.name) + (l.nums ? ' <b class="num" dir="ltr">' + esc(l.nums) + "</b>" : "") + "</span>";
    }).join("") + "</div>" : "";
    return '<div class="ta-cw"><svg class="ta-svg" viewBox="0 0 ' + W + " " + H + '" width="' + W + '" height="' + H + '" preserveAspectRatio="xMidYMid meet" direction="ltr" role="img" aria-label="גרף נרות יומי עם ממוצעים, תמיכה והתנגדות">' + out.join("") +
      "</svg>" + (narrow ? "" : '<div class="ta-ov" dir="rtl">' + ov + "</div>") + "</div>" + lv + '<div class="ta-legend" dir="ltr">' + legend + "</div>";
  }

  /* ───── רכיבי תצוגה ───── */
  function tile(title, text, cls, sub) { return '<div class="ta-tile ' + cls + '"><div class="ta-tile-h"><i class="ta-tdot" aria-hidden="true"></i>' + title + '</div><div class="ta-tile-v">' + esc(text) + "</div>" + (sub ? '<div class="ta-tile-s">' + esc(sub) + "</div>" : "") + "</div>"; }
  function tone(state) {
    if (/STRONG_UP|PRESERVED|PRICE_CONFIRMED|QUALITY_ENTRY|POSSIBLE_BUY|CONFIRMED|HEALTHY|RECOVERING|ORDERLY/.test(state)) return "ta-good";
    if (/DAMAGED|AT_RISK|DOWN|FAILED|STRUCTURE_BREAK|WEAKNESS|DEEP|DO_NOT_CHASE|NO_TRADE|UNRESOLVED/.test(state)) return "ta-bad";
    return "ta-mid";
  }
  function scoreBar(label, v, invert) {
    var val = v == null ? null : v, cls = val == null ? "" : invert ? (val > 60 ? "ta-bad" : val > 30 ? "ta-mid" : "ta-good") : (val >= 66 ? "ta-good" : val >= 45 ? "ta-mid" : "ta-bad");
    return '<div class="ta-score"><span class="ta-score-l">' + label + '</span><span class="ta-score-bar"><i class="' + cls + '" style="width:' + (val == null ? 0 : val) + '%"></i></span><b class="ta-score-v">' + (val == null ? "—" : val) + "</b></div>";
  }
  function list(items, cls) { return items && items.length ? '<ul class="ta-list ' + (cls || "") + '">' + items.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>" : '<div class="ta-none">—</div>'; }
  function render(sym, el, bars, meta) {
    var r;
    try { r = window.TAEngine.analyze(bars, { symbol: sym }); }
    catch (e) { el.innerHTML = '<div class="ta-msg">הניתוח נכשל: ' + esc(e.message) + "</div>"; return; }
    if (r.status !== "ANALYZED") { el.innerHTML = '<div class="ta-msg">אין די נתונים לניתוח (' + r.available_bars + " נרות, נדרשים " + r.required_bars + ")</div>"; return; }
    var p = r.presentation, lastBar = bars[bars.length - 1], h = [];
    h.push('<div class="ta">');
    if (r.is_provisional) h.push('<div class="ta-banner">⏳ ' + esc(r.message) + "</div>");
    h.push('<div class="ta-tiles">' + tile("מגמה ראשית", p.hierarchy.primary, tone(r.trend.state), "ציון " + r.scores.trend) + tile("מצב בינוני", p.hierarchy.intermediate, tone(r.trend_hierarchy.intermediate.state)) +
      tile("מצב קצר", p.hierarchy.short, tone(r.trend_hierarchy.short.state)) + tile("סטטוס", p.action, tone(r.decision.action), r.entry.entry != null ? "כניסה מעל " + f2(r.entry.entry) + " · ביטול " + f2(r.entry.invalidation) : "") + "</div>");
    h.push('<p class="ta-sum">' + esc(r.technical_opinion) + "</p>");
    h.push('<div class="ta-chart">' + chartSvg(bars, r, (el.clientWidth || 1000) - 44) + "</div>");
    h.push('<div class="ta-two"><section class="ta-sec"><h4>שבעת הציונים</h4>' +
      scoreBar("איכות המגמה", r.scores.trend) + scoreBar("עוצמת המומנטום", r.scores.momentum) + scoreBar("איכות התיקון", r.scores.pullback) + scoreBar("איכות אזור התמיכה", r.scores.support) +
      scoreBar("איכות נקודת הכניסה", r.scores.entry) + scoreBar("מתיחות המחיר", r.scores.extension, true) + scoreBar("איכות המחזורים", r.scores.volume) +
      '<div class="ta-fn">מתיחות: ציון גבוה = המחיר רחוק מהממוצעים (פחות טוב לכניסה).</div></section>');
    h.push('<section class="ta-sec"><h4>מאזן הראיות</h4><div class="ta-ev"><div><b class="ta-good">מה תומך</b>' + list(r.confluence.supports) + '</div><div><b class="ta-bad">מה סותר או מגביל</b>' + list(r.confluence.contradicts) + '</div><div><b class="ta-mid">מה חסר או מעורב</b>' + list(r.confluence.missing) + "</div></div></section></div>");
    // פירוט
    var maRows = r.moving_averages.map(function (m) { return "<tr><td dir=\"ltr\"><i class=\"ta-dot\" style=\"background:" + MA_COLOR[m.name] + "\"></i>" + m.name + "</td><td dir=\"ltr\">" + f2(m.value) + "</td><td dir=\"ltr\">" + (m.distance_pct >= 0 ? "+" : "") + f1(m.distance_pct) + "%</td><td>" + esc(m.slope) + "</td><td>" + esc(m.role) + "</td></tr>"; }).join("");
    var indRows = p.indicators.map(function (i) { return "<tr><td dir=\"ltr\">" + esc(i.name) + "</td><td dir=\"ltr\">" + esc(i.value) + "</td><td>" + esc(i.text) + "</td></tr>"; }).join("") +
      "<tr><td dir=\"ltr\">RSI(14)</td><td dir=\"ltr\">" + f2(r.indicators.rsi) + "</td><td>לתצוגה בלבד — אינו משתתף בציונים</td></tr><tr><td dir=\"ltr\">RVOL(20)</td><td dir=\"ltr\">" + f2(r.indicators.rvol) + "</td><td>" + (r.volume.heavy ? "מחזור מוגבר בירידות" : r.volume.quiet ? "מחזור שקט בתיקון" : r.volume.returning ? "המחזור חוזר בעלייה" : "ללא חיזוק מיוחד") + "</td></tr>";
    h.push('<details class="ta-det"><summary>אינדיקטורים וממוצעים</summary><table class="ta-tbl"><tr><th>אינדיקטור</th><th>ערך</th><th>קריאה</th></tr>' + indRows + '</table><table class="ta-tbl"><tr><th>ממוצע</th><th>ערך</th><th>מרחק</th><th>שיפוע</th><th>תפקיד</th></tr>' + maRows + "</table>" +
      '<div class="ta-fn">' + esc(p.structure.ma_order) + " · " + esc(r.extension.label) + " (ציון " + r.scores.extension + ")</div></details>");
    var sup = r.levels.support, res = r.levels.resistance;
    h.push('<details class="ta-det"><summary>תמיכה, התנגדות ופריצה</summary>' +
      "<p><b>תמיכה:</b> " + esc(p.support) + (sup ? " · " + esc(sup.sources.join(", ")) + " · " + esc(sup.context.quality) : "") + "</p>" + (sup ? list(sup.context.details) : "") +
      "<p><b>התנגדות:</b> " + esc(p.resistance) + (res ? " · " + esc(res.sources.join(", ")) : "") + "</p>" +
      "<p><b>אירוע פריצה:</b> " + esc(r.breakout.label) + (r.breakout.zone ? " · אזור " + f2(r.breakout.zone.low) + "–" + f2(r.breakout.zone.high) : "") + "</p>" + (r.breakout.reasons.length ? list(r.breakout.reasons) : "") +
      (r.role_changes.length ? "<p><b>החלפת תפקידי רמות:</b></p>" + list(r.role_changes.map(function (x) { return x.explanation; })) : "") + "</details>");
    h.push('<details class="ta-det"><summary>מבנה המחיר (שיאים ושפלים)</summary><p>' + esc(p.structure.sequence) + "</p>" + list(r.market_structure.reasons) + "<p><b>בינוני:</b> " + esc(p.hierarchy.intermediate) + "</p>" + list(r.trend_hierarchy.intermediate.reasons) + "</details>");
    h.push('<details class="ta-det"><summary>הנרות והתבניות</summary><p>' + esc(r.price_action.explanation) + "</p>" + list(r.price_action.sequence.reasons) +
      (r.price_action.tracking.length ? "<p><b>מעקב תבניות (10 נרות אחרונים):</b></p>" + list(r.price_action.tracking.map(function (t) { return t.explanation; })) : "") + "</details>");
    h.push('<details class="ta-det"><summary>מה יאשר כניסה</summary><div class="ta-ev"><div><b class="ta-good">מתקיים</b>' + list(p.confirmation.positive) + '</div><div><b class="ta-mid">חסר</b>' + list(p.confirmation.missing) + '</div><div><b>אפשרויות למעקב</b>' + list(p.confirmation.alternatives) + "</div></div><div class=\"ta-fn\">" + esc(p.confirmation.note) + "</div>" +
      "<p><b>הצעד הבא:</b> " + esc(p.next_step) + "</p><p><b>סיכון:</b> " + esc(p.risk) + "</p></details>");
    h.push('<div class="ta-foot">נתונים: Yahoo Finance, ' + bars.length + " נרות יומיים, נר אחרון " + esc(lastBar.date) + (lastBar.is_partial ? " (מתהווה, מסורק TradingView)" : "") + " · מנוע: chart-price-action-v3 (כללים קבועים, ללא בינה מלאכותית) · תיאור טכני בלבד, לא ייעוץ השקעות.</div>");
    h.push("</div>");
    el.innerHTML = h.join("");
  }

  function ensureEngine(cb) {
    if (window.TAEngine) { cb(); return; }
    var s = document.createElement("script"); s.src = "assets/ta_engine.js?v=" + (window.__npVer || "1"); s.onload = function () { cb(); };
    s.onerror = function () { cb(new Error("load")); };
    document.head.appendChild(s);
  }
  window.__taHas = hasBars;
  window.__taRender = function (sym, el) {
    el.innerHTML = '<div class="ta-msg">טוען נתונים…</div>';
    ensureEngine(function (err) {
      if (err || !window.TAEngine) { el.innerHTML = '<div class="ta-msg">טעינת מנוע הניתוח נכשלה</div>'; return; }
      loadBars(sym, function (d) {
        if (!d) { el.innerHTML = '<div class="ta-msg">אין עדיין נתוני נרות ל־<b dir="ltr">' + esc(sym) + '</b>.<br>הבוט שומר 500 נרות יומיים למניות שמופיעות באתר ולרשימת המעקב (data/ta_watchlist.txt); מניה חדשה מתווספת בעדכון הבא (עד ~15 דקות, אחרי סגירת המסחר).</div>'; return; }
        var bars = d.bars.slice();
        liveBar(sym, function (lb) {
          if (lb && lb.date > bars[bars.length - 1].date) bars.push(lb);
          render(sym, el, bars, d);
        });
      });
    });
  };
})();
