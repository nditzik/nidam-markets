/* ta_ui.js — חלונית "ניתוח טכני" לכל טיקר (29.9.2026).
   נטען בעצלתיים (יחד עם ta_engine.js) בלחיצה הראשונה על טיקר. קורא data/bars/SYM.json
   (500 נרות סגורים שהבוט שומר), מוסיף את הנר של היום מסורק TradingView (is_partial בזמן
   המסחר), מריץ TAEngine.analyze ומרנדר: 4 אריחים · סיכום · גרף נרות עם 6 ממוצעים ואזורי
   תמיכה/התנגדות/פריצה · 7 ציונים · מאזן הראיות · פירוט. הכל טקסט מהמנוע — אין LLM.
   ממשק: window.__taRender(sym, containerEl), window.__taHas(sym, cb).
   np156: טיקר בלי נרות שמורים → quickRender (ניתוח מקוצר + יסודות מהסורק, לכל טיקר אמריקאי). */
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
  // np153 (26.10.2026, איציק): "יסודות החברה" — data/fundamentals.json (build_fundamentals.py), נטען פעם אחת ל-10 דק'
  var FUND = null, FUND_AT = 0;
  function loadFund(cb) {
    var now = Date.now();
    if (FUND && now - FUND_AT < 10 * 60 * 1000) { cb(FUND); return; }
    fetch("data/fundamentals.json?v=" + Math.floor(now / 600000)).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { FUND = d || { symbols: {} }; FUND_AT = now; cb(FUND); })
      .catch(function () { cb(FUND || { symbols: {} }); });
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
  var HE_DOW = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"];
  function money(v) {
    if (v == null) return "—";
    var a = Math.abs(v), s = v < 0 ? "−" : "";
    if (a >= 1e12) return s + "$" + (a / 1e12).toFixed(2) + "T";
    if (a >= 1e9) return s + "$" + (a / 1e9).toFixed(a >= 1e10 ? 0 : 1) + "B";
    if (a >= 1e6) return s + "$" + (a / 1e6).toFixed(0) + "M";
    return s + "$" + Math.round(a);
  }
  function pctS(v, sign) { return v == null ? "—" : ((sign && v > 0) ? "+" : "") + (Math.abs(v) >= 100 ? Math.round(v) : v.toFixed(Math.abs(v) < 10 ? 1 : 0)) + "%"; }
  function ftile(l, v, s, cls) { return '<div class="ta-ft"><div class="ta-ft-l">' + l + '</div><div class="ta-ft-v num' + (cls ? " " + cls : "") + '" dir="ltr">' + v + '</div>' + (s ? '<div class="ta-ft-s">' + s + "</div>" : "") + "</div>"; }
  function fundHtml(sym, f, lastClose) {
    if (!f || f.cap == null) return "";
    var q = f.quality || {}, price = lastClose || f.price;
    var capS = f.cap >= 2e11 ? "ענקית" : f.cap >= 1e10 ? "גדולה" : f.cap >= 2e9 ? "בינונית" : f.cap >= 3e8 ? "קטנה" : "זעירה";
    var pe = f.fwdPe || f.pe, peLbl = f.fwdPe ? "מכפיל רווח קדימה" : "מכפיל רווח";
    var peS = pe == null || pe <= 0 ? "—" : (pe >= 100 ? Math.round(pe) : pe.toFixed(pe >= 20 ? 0 : 1));
    var peSub = pe == null || pe <= 0 ? "אין רווח" : pe > 35 ? "יקרה" : pe >= 15 ? "סבירה" : "זולה";
    var prof = (f.eps != null && f.eps > 0) || (f.netMargin != null && f.netMargin > 0);
    var tiles = ftile("שווי שוק", money(f.cap), capS) + ftile(peLbl, peS, peSub) +
      ftile("צמיחת הכנסות", pctS(f.revGrowth, true), "שנה מול שנה", f.revGrowth == null ? "" : f.revGrowth >= 0 ? "up" : "down") +
      ftile("רווח תפעולי", pctS(f.opMargin), prof ? "מההכנסות · רווחית" : "מההכנסות · מפסידה", f.opMargin == null ? "" : f.opMargin >= 0 ? "up" : "down") +
      ftile("תזרים חופשי", pctS(f.fcfMargin), "מההכנסות", f.fcfMargin == null ? "" : f.fcfMargin >= 0 ? "up" : "down") +
      ftile("מזומן נטו", money(f.netCash), f.netCash == null ? "" : f.netCash >= 0 ? "יותר מזומן מחוב" : "יותר חוב ממזומן", f.netCash == null ? "" : f.netCash >= 0 ? "" : "down");
    var rows = "";
    var ne = f.nextEarn;
    if (ne && ne.date) {
      var dt = new Date(ne.date + "T12:00:00"), days = Math.round((dt - new Date(new Date().toDateString())) / 864e5);
      var whenS = ne.when === "after" ? "אחרי הסגירה" : ne.when === "before" ? "לפני הפתיחה" : "";
      var inS = days < 0 ? "לפני " + (-days) + " ימים" : days === 0 ? "היום" : days === 1 ? "מחר" : "בעוד " + days + " ימים";
      rows += '<div class="ta-fr' + (days >= 0 && days <= 7 ? " ta-fr-earn" : "") + '"><span class="ta-fr-k">📅 הדוח הבא</span><span class="ta-fr-v"><b>יום ' + HE_DOW[dt.getDay()] + " " + dt.getDate() + "." + (dt.getMonth() + 1) + (whenS ? ", " + whenS : "") + "</b> · " + inS +
        (f.epsEst != null ? ' · צפי רווח למניה <b class="num" dir="ltr">$' + Number(f.epsEst).toFixed(2) + "</b>" : "") + (f.revEst != null ? ' · הכנסות <b class="num" dir="ltr">' + money(f.revEst) + "</b>" : "") +
        (f.move != null ? ' · האופציות מתמחרות תזוזה של <b class="num" dir="ltr">±' + Number(f.move).toFixed(1) + "%</b>" : "") + "</span></div>";
    }
    if (f.target != null && price) {
      var up = (f.target / price - 1) * 100, r = f.recs || {}, buy = (r.strongBuy || 0) + (r.buy || 0), tot = buy + (r.hold || 0) + (r.sell || 0) + (r.strongSell || 0);
      rows += '<div class="ta-fr"><span class="ta-fr-k">אנליסטים</span><span class="ta-fr-v">מחיר יעד ממוצע <b class="num" dir="ltr">$' + (f.target >= 100 ? Math.round(f.target) : f.target.toFixed(2)) + '</b> (<b class="num ' + (up >= 0 ? "up" : "down") + '" dir="ltr">' + (up >= 0 ? "+" : "") + up.toFixed(0) + "%</b> מהמחיר)" +
        (tot ? ' · <b class="num" dir="ltr">' + buy + "</b> מתוך <b class=\"num\" dir=\"ltr\">" + tot + "</b> ממליצים קנייה" : (f.targetN ? ' · <b class="num" dir="ltr">' + f.targetN + "</b> אנליסטים" : "")) + "</span></div>";
    }
    if (f.divYield != null && f.divYield > 0) rows += '<div class="ta-fr"><span class="ta-fr-k">דיבידנד</span><span class="ta-fr-v">תשואה שנתית <b class="num" dir="ltr">' + f.divYield.toFixed(1) + "%</b></span></div>";
    var readS = f.read || "";
    if (ne && ne.date) { var dd = Math.round((new Date(ne.date + "T12:00:00") - new Date(new Date().toDateString())) / 864e5); if (dd >= 0 && dd <= 7) readS += " הדוח " + (dd === 0 ? "היום" : dd === 1 ? "מחר" : "בעוד " + dd + " ימים") + ": כניסה טכנית עכשיו היא גם הימור על הדוח."; }
    if (readS) rows += '<div class="ta-fr"><span class="ta-fr-k">קריאה</span><span class="ta-fr-v">' + esc(readS) + "</span></div>";
    return '<section class="ta-fund" aria-label="יסודות החברה"><div class="ta-fund-h"><h4>יסודות החברה</h4>' + (q.label ? '<span class="ta-fq ' + esc(q.q || "mid") + '">' + esc(q.label) + "</span>" : "") +
      '<span class="ta-fund-src">' + esc([f.name, f.industry].filter(Boolean).join(" · ")) + (f.at ? " · עודכן " + esc(f.at.slice(8, 10)) + "." + esc(f.at.slice(5, 7)) : "") + "</span></div>" +
      (f.about ? '<p class="ta-fund-about">' + esc(f.about) + "</p>" : "") +
      '<div class="ta-fund-grid">' + tiles + "</div>" + (rows ? '<div class="ta-fund-rows">' + rows + "</div>" : "") + "</section>";
  }


  /* ───── np156 (27.10.2026, איציק): ניתוח מקוצר לכל טיקר — גם כזה שלא במעקב באתר ─────
     בלי נרות שמורים אין מנוע מלא, אז הכל מגיע עכשיו מהסורק של TradingView (שתי בקשות פשוטות:
     יסודות = אותן 31 עמודות של build_fundamentals.py, טכני = ממוצעים/מד חום/ביצועים/טווח שנתי).
     כשל של אחת מהן לא מפיל את השנייה. */
  var SCAN = "https://scanner.tradingview.com/america/scan";
  var FCOLS = ["name", "description", "sector", "industry", "market_cap_basic", "close",
    "price_earnings_ttm", "price_earnings_fwd", "earnings_per_share_diluted_ttm", "earnings_per_share_forecast_next_fy",
    "total_revenue_yoy_growth_ttm", "earnings_per_share_diluted_yoy_growth_ttm",
    "gross_margin_ttm", "operating_margin_ttm", "net_margin_ttm", "free_cash_flow_margin_ttm",
    "cash_n_short_term_invest_fq", "total_debt_fq", "dividends_yield_current",
    "price_target_average", "recommendation_mark", "recommendation_total",
    "recommendation_buy", "recommendation_over", "recommendation_hold", "recommendation_under", "recommendation_sell",
    "earnings_per_share_forecast_next_fq", "revenue_forecast_next_fq",
    "earnings_release_next_date", "earnings_release_next_time", "exchange"];
  var TCOLS = ["name", "close", "change", "SMA20", "SMA50", "SMA200", "RSI", "Perf.W", "Perf.1M", "Perf.3M",
    "price_52_week_high", "price_52_week_low", "ATR"];
  function scanRow(tvSym, cols, cb) {
    fetch(SCAN, { method: "POST", body: JSON.stringify({
      filter: [{ left: "name", operation: "equal", right: tvSym }, { left: "exchange", operation: "in_range", right: ["NASDAQ", "NYSE", "AMEX"] }],
      columns: cols, range: [0, 3] }) })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        var row = d && (d.data || []).filter(function (x) { return x.d && x.d[0] === tvSym; })[0];
        if (!row) { cb(null); return; }
        var o = {}; cols.forEach(function (c, i) { o[c] = row.d[i]; }); cb(o);
      }).catch(function () { cb(null); });
  }
  function num(v) { return typeof v === "number" && isFinite(v) ? v : null; }
  function rnd(v, d) { return v == null ? null : Math.round(v * Math.pow(10, d)) / Math.pow(10, d); }
  function nyDate(ts) {
    try { return new Intl.DateTimeFormat("en-CA", { timeZone: NY, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(ts * 1000)); }
    catch (e) { return new Date(ts * 1000).toISOString().slice(0, 10); }
  }
  // פורט של build_fundamentals.parse / quality / read_sentence — אותם שדות ואותם משפטים
  function parseFund(d) {
    var close = num(d.close), fwdEps = num(d.earnings_per_share_forecast_next_fy), fwdPe = num(d.price_earnings_fwd);
    if (fwdPe == null && close && fwdEps && fwdEps > 0) fwdPe = close / fwdEps;
    var cash = num(d.cash_n_short_term_invest_fq), debt = num(d.total_debt_fq), ts = num(d.earnings_release_next_date);
    var f = {
      name: d.description, sector: d.sector, industry: d.industry, exchange: d.exchange,
      cap: num(d.market_cap_basic), price: close,
      pe: rnd(num(d.price_earnings_ttm), 2), fwdPe: rnd(fwdPe, 2),
      eps: num(d.earnings_per_share_diluted_ttm), fwdEps: fwdEps,
      revGrowth: rnd(num(d.total_revenue_yoy_growth_ttm), 1), opMargin: rnd(num(d.operating_margin_ttm), 1),
      netMargin: rnd(num(d.net_margin_ttm), 1), fcfMargin: rnd(num(d.free_cash_flow_margin_ttm), 1),
      netCash: (cash != null && debt != null) ? cash - debt : null,
      divYield: rnd(num(d.dividends_yield_current), 2), target: rnd(num(d.price_target_average), 2), targetN: num(d.recommendation_total),
      recs: { strongBuy: num(d.recommendation_buy), buy: num(d.recommendation_over), hold: num(d.recommendation_hold), sell: num(d.recommendation_under), strongSell: num(d.recommendation_sell) },
      epsEst: num(d.earnings_per_share_forecast_next_fq), revEst: num(d.revenue_forecast_next_fq),
      nextEarn: ts ? { date: nyDate(ts), when: d.earnings_release_next_time === 1 ? "after" : d.earnings_release_next_time === -1 ? "before" : "" } : null
    };
    var q = quality(f); f.quality = q; f.read = readSentence(f, q);
    return f;
  }
  function profitable(f) { return (f.eps != null && f.eps > 0) || (f.netMargin != null && f.netMargin > 0); }
  function quality(f) {
    var cap = f.cap, g = f.revGrowth, prof = profitable(f);
    if (cap == null) return { q: "mid", label: "חסר מידע" };
    if (cap < 3e8 || (!prof && g != null && g < 0)) return { q: "bad", label: "ספקולטיבית" };
    if (cap >= 2e9 && prof && (g == null || g >= 0)) return { q: "ok", label: "מבוססת" };
    if (!prof) return { q: "mid", label: (g || 0) > 0 ? "צומחת, לא רווחית" : "לא רווחית" };
    if (cap < 2e9) return { q: "mid", label: "קטנה" };
    return { q: "mid", label: (g != null && g < 0) ? "רווחית, ההכנסות יורדות" : "מעורבת" };
  }
  function readSentence(f, q) {
    var prof = profitable(f), g = f.revGrowth, s;
    if (prof && g != null && g > 0) s = "חברה רווחית וצומחת";
    else if (prof && g != null) s = "חברה רווחית, אבל ההכנסות יורדות";
    else if (prof) s = "חברה רווחית";
    else if (g != null && g > 0) s = "צומחת אבל עדיין לא רווחית";
    else if (g != null) s = "לא רווחית וההכנסות יורדות";
    else s = "נתוני הרווחיות חסרים";
    var pe = f.fwdPe || f.pe;
    if (pe && pe > 0) s += " במכפיל " + (pe > 35 ? "גבוה" : pe >= 15 ? "סביר" : "נמוך");
    if (f.netCash != null && f.cap) { if (f.netCash > 0) s += ", עם יותר מזומן מחוב"; else if (-f.netCash > 0.3 * f.cap) s += ", ממונפת (החוב נטו מעל 30% מהשווי)"; }
    if (q.q === "bad") s += ". שווי קטן או חברה מפסידה: תנודתית, לא לפוזיציה מלאה";
    return s + ".";
  }
  function sgn(v, d) { return v == null ? "—" : (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d == null ? 1 : d) + "%"; }
  function upDn(v) { return v == null ? "" : v > 0 ? "up" : v < 0 ? "down" : ""; }
  function techHtml(t) {
    var c = num(t.close); if (!c) return "";
    var m20 = num(t.SMA20), m50 = num(t.SMA50), m200 = num(t.SMA200), rsi = num(t.RSI);
    var hi = num(t.price_52_week_high), lo = num(t.price_52_week_low), atr = num(t.ATR);
    var a20 = m20 != null ? c > m20 : null, a50 = m50 != null ? c > m50 : null, a200 = m200 != null ? c > m200 : null;
    var trend = a200 == null || a50 == null ? null :
      (a200 && a50 && a20) ? ["מגמה עולה", "ok"] : (a200 && a50) ? ["עולה, בתיקון קצר", "ok"] :
      a200 ? ["תיקון בתוך מגמה עולה", "mid"] : a50 ? ["ניסיון התאוששות", "mid"] : ["מגמה יורדת", "bad"];
    var offHi = hi ? (c / hi - 1) * 100 : null, fromLo = lo ? (c / lo - 1) * 100 : null;
    var rsiW = rsi == null ? "" : rsi > 70 ? "חם מדי" : rsi >= 65 ? "מתחמם" : rsi >= 45 ? "נוח" : rsi >= 30 ? "חלש" : "מכירת יתר";
    var h = '<section class="ta-qsec" aria-label="תמונה טכנית"><div class="ta-fund-h"><h4>תמונה טכנית</h4>' +
      (trend ? '<span class="ta-fq ' + trend[1] + '">' + trend[0] + "</span>" : "") + '<span class="ta-fund-src">מהסורק של TradingView · עכשיו</span></div>';
    if (hi && lo && hi > lo) {
      var pos = Math.max(0, Math.min(100, (c - lo) / (hi - lo) * 100));
      h += '<div class="ta-range"><div class="ta-range-l" dir="ltr"><span>שפל שנתי <b class="num">$' + f2(lo) + '</b></span><span>שיא שנתי <b class="num">$' + f2(hi) + "</b></span></div>" +
        '<div class="ta-range-t" dir="ltr" role="img" aria-label="המחיר ב-' + Math.round(pos) + '% מהטווח השנתי"><i style="width:' + pos.toFixed(1) + '%"></i><b style="left:' + pos.toFixed(1) + '%"></b></div>' +
        '<div class="ta-range-s">המחיר <b class="num" dir="ltr">' + sgn(offHi) + '</b> מהשיא השנתי, <b class="num" dir="ltr">' + sgn(fromLo, 0) + "</b> מעל השפל</div></div>";
    }
    function maChip(n, v, a) { return v == null ? "" : '<div class="ta-ma ' + (a ? "ok" : "bad") + '"><i aria-hidden="true">' + (a ? "✓" : "✗") + "</i>" + (a ? "מעל " : "מתחת ל") + "ממוצע " + n + ' <span class="num" dir="ltr">' + f2(v) + "</span></div>"; }
    h += '<div class="ta-mas">' + maChip(20, m20, a20) + maChip(50, m50, a50) + maChip(200, m200, a200) + "</div>";
    h += '<div class="ta-fund-grid ta-qtiles">' + ftile("מד חום", rsi == null ? "—" : Math.round(rsi), rsiW) +
      ftile("שבוע", sgn(num(t["Perf.W"])), "", upDn(num(t["Perf.W"]))) + ftile("חודש", sgn(num(t["Perf.1M"])), "", upDn(num(t["Perf.1M"]))) +
      ftile("3 חודשים", sgn(num(t["Perf.3M"])), "", upDn(num(t["Perf.3M"]))) +
      ftile("תנודה יומית", atr ? (atr / c * 100).toFixed(1) + "%" : "—", "ממוצע 14 יום") + "</div>";
    // קריאה — כללים קבועים, תיאור ולא תחזית
    var parts = [];
    if (a20 != null && a50 != null && a200 != null) {
      var up = [], dn = []; [[20, a20], [50, a50], [200, a200]].forEach(function (x) { (x[1] ? up : dn).push(x[0]); });
      parts.push(!dn.length ? "מעל שלושת הממוצעים" : !up.length ? "מתחת לשלושת הממוצעים" : "מעל ממוצע " + up.join(" ו-") + ", מתחת ל-" + dn.join(" ו-"));
    }
    if (offHi != null) parts.push(offHi >= -3 ? "ליד השיא השנתי" : offHi >= -10 ? "קרוב לשיא השנתי" : offHi >= -25 ? Math.round(-offHi) + "% מתחת לשיא השנתי" : "רחוק מאוד מהשיא השנתי (" + Math.round(-offHi) + "%)");
    if (rsi != null) parts.push("מד חום " + rsiW + " (" + Math.round(rsi) + ")");
    var read = parts.length ? parts.join(", ") + "." : "";
    var p3 = num(t["Perf.3M"]);
    if (p3 != null) read += Math.abs(p3) < 3 ? " בשלושה חודשים כמעט לא זזה." : " בשלושה חודשים " + (p3 > 0 ? "עלתה " : "ירדה ") + Math.abs(p3).toFixed(0) + "%.";
    if (a200 === false && a50 === false) read += " חזרה מעל ממוצע 50 היא הסימן הראשון לשינוי.";
    else if (offHi != null && offHi >= -3 && a50) read += " פריצה מעל השיא השנתי היא מה שיאשר המשך.";
    if (read) h += '<div class="ta-fund-rows"><div class="ta-fr"><span class="ta-fr-k">קריאה</span><span class="ta-fr-v">' + esc(read.trim()) + "</span></div></div>";
    return h + "</section>";
  }
  function quickRender(sym, el, fund) {
    var tvSym = sym.replace(/-/g, "."), got = 0, F = null, T = null;
    function done() {
      if (++got < 2) return;
      var stored = fund && fund.symbols && fund.symbols[sym];
      var f = (stored && stored.cap != null) ? stored : F;
      if (!f && !T) { el.innerHTML = '<div class="ta-msg">לא נמצא טיקר <b dir="ltr">' + esc(sym) + "</b> בבורסות האמריקאיות (NASDAQ / NYSE / AMEX).<br>אפשר לבדוק את האיות, או לפתוח את הלשונית \"גרף TradingView\".</div>"; return; }
      var close = (T && num(T.close)) || (f && f.price), chg = T ? num(T.change) : null;
      var h = ['<div class="ta ta-quick">'];
      h.push('<div class="ta-qhd"><b>' + esc((f && f.name) || sym) + "</b>" + (F && F.exchange ? '<span class="mute">' + esc(F.exchange) + "</span>" : "") +
        (close ? '<span class="num" dir="ltr">$' + f2(close) + "</span>" : "") + (chg != null ? '<span class="num ' + upDn(chg) + '" dir="ltr">' + sgn(chg, 2) + "</span>" : "") + "</div>");
      h.push('<div class="ta-qbanner"><b>ניתוח מקוצר.</b> המניה לא במעקב באתר, ולכן אין לנו את ההיסטוריה שהמנוע המלא צריך. מה שמוצג כאן מגיע עכשיו מהסורק של TradingView.</div>');
      if (T) h.push(techHtml(T)); else h.push('<div class="ta-msg">הנתונים הטכניים לא נטענו כרגע. אפשר לפתוח את הלשונית "גרף TradingView".</div>');
      if (f) {
        if (!f.about && f.sector) f = Object.assign({}, f, { about: "ענף: " + f.sector + (f.industry ? " · תעשייה: " + f.industry : "") });
        h.push(fundHtml(sym, f, close));
      }
      h.push('<div class="ta-qnext"><b>הניתוח המלא</b> — אריחי המגמה, תמיכות והתנגדויות על הגרף, מכונת הפריצה ו"אישור מחיר" — זמין למניות שבמעקב באתר. חיבור שמביא היסטוריה לכל טיקר יאפשר אותו גם כאן.</div>');
      h.push('<div class="ta-foot">נתונים: סורק TradingView, נכון לרגע הפתיחה · תיאור טכני ופונדמנטלי בלבד, לא ייעוץ השקעות.</div></div>');
      el.innerHTML = h.join("");
    }
    scanRow(tvSym, FCOLS, function (d) { F = d && num(d.market_cap_basic) != null ? parseFund(d) : null; if (F) F.exchange = d.exchange; done(); });
    scanRow(tvSym, TCOLS, function (d) { T = d; done(); });
  }

  /* ───── "שכבה 2": נרות לכל טיקר דרך Cloudflare Worker (docs/cloudflare/bars-worker.js) ─────
     הכתובת ב-window.__barsProxy (app.js). ריקה = לא מוגדר → ניתוח מקוצר כמו קודם. */
  var PROXY_BARS = {};
  function proxyBars(sym, cb) {
    var base = window.__barsProxy || "";
    if (!base) { cb(null); return; }
    if (PROXY_BARS[sym] && Date.now() - PROXY_BARS[sym].at < 30 * 60 * 1000) { cb(PROXY_BARS[sym]); return; }
    var done = false, t = setTimeout(function () { if (!done) { done = true; cb(null); } }, 8000);
    fetch(base.replace(/\/$/, "") + "/bars?s=" + encodeURIComponent(sym)).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (done) return; done = true; clearTimeout(t);
        if (!d || !d.bars || d.bars.length < 60) { cb(null); return; }
        var bars = d.bars.map(function (b) { return { date: b[0], open: b[1], high: b[2], low: b[3], close: b[4], volume: b[5] }; });
        // נר של היום בזמן המסחר = חלקי; liveBar יוסיף אותו מהסורק כ-is_partial
        var ses = session();
        if (bars.length && bars[bars.length - 1].date === nyToday() && (ses === "regular" || ses === "pre")) bars.pop();
        PROXY_BARS[sym] = { bars: bars, last: bars[bars.length - 1].date, at: Date.now(), proxy: true };
        cb(PROXY_BARS[sym]);
      }).catch(function () { if (!done) { done = true; clearTimeout(t); cb(null); } });
  }
  // יסודות למניה שלא במעקב — מהסורק, באותו מבנה של fundamentals.json
  function scanFund(sym, fund, cb) {
    var stored = fund && fund.symbols && fund.symbols[sym];
    if (stored && stored.cap != null) { cb(fund); return; }
    scanRow(sym.replace(/-/g, "."), FCOLS, function (d) {
      var f = d && num(d.market_cap_basic) != null ? parseFund(d) : null;
      if (f && !f.about && f.sector) f.about = "ענף: " + f.sector + (f.industry ? " · תעשייה: " + f.industry : "");
      var o = { symbols: {} }; if (f) o.symbols[sym] = f; cb(o);
    });
  }

  function render(sym, el, bars, meta, fund, note) {
    var r;
    try { r = window.TAEngine.analyze(bars, { symbol: sym }); }
    catch (e) { el.innerHTML = '<div class="ta-msg">הניתוח נכשל: ' + esc(e.message) + "</div>"; return; }
    if (r.status !== "ANALYZED") { el.innerHTML = '<div class="ta-msg">אין די נתונים לניתוח (' + r.available_bars + " נרות, נדרשים " + r.required_bars + ")</div>"; return; }
    var p = r.presentation, lastBar = bars[bars.length - 1], h = [];
    h.push('<div class="ta">');
    if (note) h.push('<div class="ta-banner">⚠️ ' + esc(note) + "</div>");
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
    // np153: יסודות החברה — מעל "אינדיקטורים וממוצעים"
    h.push(fundHtml(sym, fund && fund.symbols && fund.symbols[sym], lastBar.close));
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
    h.push('<div class="ta-foot">נתונים: Yahoo Finance (נרות) · TradingView (יסודות החברה), ' + bars.length + " נרות יומיים, נר אחרון " + esc(lastBar.date) + (lastBar.is_partial ? " (מתהווה, מסורק TradingView)" : "") + " · מנוע: chart-price-action-v3 (כללים קבועים, ללא בינה מלאכותית) · תיאור טכני בלבד, לא ייעוץ השקעות.</div>");
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
        // np173 (31.10.2026, איציק: OII "לא מראה את הימים האחרונים ואין ניתוח פונדמנטלי"): מניה שיצאה מהיקום של
        // fetch_bars נשארת ב-data/bars עד 45 יום עם נרות קפואים, ובלי רשומה ב-fundamentals.json. נרות שמפגרים אחרי
        // הנר האחרון של SPY = ישנים → נרות טריים מהמתווך (שכבה 2); נכשל → הישנים, עם הערה. יסודות חסרים → מהסורק.
        var ref = IDX && IDX.symbols && IDX.symbols.SPY && IDX.symbols.SPY.last;
        var stale = !!(d && ref && d.last < ref);
        function useProxy(pd) {
          var pb = pd.bars.slice();
          liveBar(sym, function (lb) {
            if (lb && lb.date > pb[pb.length - 1].date) pb.push(lb);
            loadFund(function (fund) { scanFund(sym, fund, function (fo) { render(sym, el, pb, pd, fo); }); });
          });
        }
        function useLocal(note) {
          var bars = d.bars.slice();
          // נר חי מעל נרות ישנים היה יוצר קפיצה של ימים — רק כשהנרות עדכניים
          var go = function (lb) {
            if (lb && lb.date > bars[bars.length - 1].date) bars.push(lb);
            loadFund(function (fund) { scanFund(sym, fund, function (fo) { render(sym, el, bars, d, fo, note); }); });
          };
          if (stale) go(null); else liveBar(sym, go);
        }
        if (!d) {
          // np157: יש מתווך נרות (שכבה 2)? → המנוע המלא; אחרת ניתוח מקוצר מהסורק (np156)
          proxyBars(sym, function (pd) {
            if (!pd) { loadFund(function (fund) { quickRender(sym, el, fund); }); return; }
            useProxy(pd);
          });
          return;
        }
        if (stale) {
          proxyBars(sym, function (pd) {
            if (pd && pd.last > d.last) useProxy(pd);
            else useLocal("המניה כבר לא במעקב היומי של האתר — הנרות עד " + d.last + ", ונרות עדכניים לא נטענו כרגע.");
          });
          return;
        }
        useLocal();
      });
    });
  };
})();
