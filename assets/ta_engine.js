/* ta_engine.js — מנוע ניתוח טכני (פורט של ANALYSIS_SPEC.md, chart-price-action-v3, 29.9.2026)
   קלט: נרות יומיים [{date,open,high,low,close,volume}], ישן→חדש. פלט: אובייקט ניתוח.
   טהור: בלי רשת, בלי DOM. עובד בדפדפן (window.TAEngine) וב-Node (module.exports).
   כל הכללים והספים כאן הם מהמפרט; אין לשנות בלי לעדכן את בדיקת VLO 2026-09-28. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.TAEngine = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /* ───────── מוסכמות מספריות ───────── */
  function mean(arr) {
    var n = arr.length; if (!n) return null;
    var sum = 0, c = 0;
    for (var i = 0; i < n; i++) { var x = arr[i], t = sum + x; if (Math.abs(sum) >= Math.abs(x)) c += (sum - t) + x; else c += (x - t) + sum; sum = t; }
    return (sum + c) / n;
  }
  function R(x) {
    if (x == null || !isFinite(x)) return null;
    var f = Math.floor(x), d = x - f;
    if (d > 0.5) return f + 1; if (d < 0.5) return f;
    return (f % 2 === 0) ? f : f + 1;
  }
  function S(x) { return x == null ? null : R(Math.max(0, Math.min(100, x))); }
  function W(items) {
    var num = 0, den = 0, any = false;
    for (var i = 0; i < items.length; i++) { var it = items[i]; if (it.v == null || !isFinite(it.v)) continue; num += it.v * it.w; den += it.w; any = true; }
    return any && den > 0 ? S(num / den) : null;
  }
  function fmt2(x) { return (x == null || !isFinite(x)) ? "—" : x.toFixed(2); }
  function fmt1(x) { return (x == null || !isFinite(x)) ? "—" : x.toFixed(1); }
  function pct0(x) { return String(R(x * 100)); }
  function last(a) { return a[a.length - 1]; }
  function maxArr(a) { return Math.max.apply(null, a); }
  function minArr(a) { return Math.min.apply(null, a); }
  function bar(b) { return { date: b.date, volume: b.volume, open: b.open, high: b.high, low: b.low, close: b.close }; }

  var MA_ORDER = ["EMA20", "EMA40", "SMA50", "SMA100", "SMA150", "SMA200"];
  var MA_PERIOD = { EMA20: 20, EMA40: 40, SMA50: 50, SMA100: 100, SMA150: 150, SMA200: 200 };
  var LONG_MAS = ["SMA100", "SMA150", "SMA200"];
  function maName(k) { return (k.slice(0, 3) === "EMA" ? "ממוצע מעריכי " : "ממוצע פשוט ") + MA_PERIOD[k] + " יום"; }

  /* ───────── 2. אינדיקטורים ───────── */
  function smaSeries(vals, p) {
    var out = new Array(vals.length).fill(null);
    for (var i = p - 1; i < vals.length; i++) {
      var ok = true, win = [];
      for (var j = i - p + 1; j <= i; j++) { if (vals[j] == null) { ok = false; break; } win.push(vals[j]); }
      out[i] = ok ? mean(win) : null;
    }
    return out;
  }
  function emaSeries(vals, p) {
    var out = new Array(vals.length).fill(null), k = 2 / (p + 1), e = null, run = [];
    for (var i = 0; i < vals.length; i++) {
      var v = vals[i];
      if (v == null) { e = null; run = []; continue; }
      if (e == null) { run.push(v); if (run.length === p) { e = mean(run); out[i] = e; } continue; }
      e = e + k * (v - e); out[i] = e;
    }
    return out;
  }
  function computeIndicators(bars) {
    var N = bars.length, C = bars.map(function (b) { return b.close; }), H = bars.map(function (b) { return b.high; }), L = bars.map(function (b) { return b.low; }), V = bars.map(function (b) { return b.volume; });
    var ma = { EMA20: emaSeries(C, 20), EMA40: emaSeries(C, 40), SMA50: smaSeries(C, 50), SMA100: smaSeries(C, 100), SMA150: smaSeries(C, 150), SMA200: smaSeries(C, 200) };
    var TR = new Array(N), ATR = new Array(N).fill(null);
    for (var i = 0; i < N; i++) TR[i] = i === 0 ? H[0] - L[0] : Math.max(H[i] - L[i], Math.abs(H[i] - C[i - 1]), Math.abs(L[i] - C[i - 1]));
    if (N >= 14) { ATR[13] = mean(TR.slice(0, 14)); for (i = 14; i < N; i++) ATR[i] = (13 * ATR[i - 1] + TR[i]) / 14; }
    var TP = bars.map(function (b) { return (b.high + b.low + b.close) / 3; }), CCI = new Array(N).fill(null);
    for (i = 4; i < N; i++) { var w = TP.slice(i - 4, i + 1), m = mean(w), d = mean(w.map(function (x) { return Math.abs(x - m); })); CCI[i] = d === 0 ? 0 : (TP[i] - m) / (0.015 * d); }
    var rawK = new Array(N).fill(null);
    for (i = 14; i < N; i++) { var lo = minArr(L.slice(i - 14, i + 1)), hi = maxArr(H.slice(i - 14, i + 1)); rawK[i] = hi - lo === 0 ? 50 : 100 * (C[i] - lo) / (hi - lo); }
    var K = smaSeries(rawK, 5), D = smaSeries(K, 3);
    var e12 = emaSeries(C, 12), e26 = emaSeries(C, 26), MACD = new Array(N).fill(null);
    for (i = 0; i < N; i++) if (e12[i] != null && e26[i] != null) MACD[i] = e12[i] - e26[i];
    var SIG = emaSeries(MACD, 9), HIST = new Array(N).fill(null);
    for (i = 0; i < N; i++) if (MACD[i] != null && SIG[i] != null) HIST[i] = MACD[i] - SIG[i];
    var RSI = new Array(N).fill(null);
    if (N >= 15) {
      var g = 0, l = 0;
      for (i = 1; i <= 14; i++) { var dc = C[i] - C[i - 1]; g += Math.max(dc, 0); l += Math.max(-dc, 0); }
      g /= 14; l /= 14;
      var rsiOf = function (g, l) { return (g === 0 && l === 0) ? 50 : l === 0 ? 100 : 100 - 100 / (1 + g / l); };
      RSI[14] = rsiOf(g, l);
      for (i = 15; i < N; i++) { dc = C[i] - C[i - 1]; g = (13 * g + Math.max(dc, 0)) / 14; l = (13 * l + Math.max(-dc, 0)) / 14; RSI[i] = rsiOf(g, l); }
    }
    var AVGV = new Array(N).fill(null), RVOL = new Array(N).fill(null);
    for (i = 20; i < N; i++) { AVGV[i] = mean(V.slice(i - 20, i)); RVOL[i] = AVGV[i] > 0 ? V[i] / AVGV[i] : null; }
    return { N: N, C: C, H: H, L: L, V: V, O: bars.map(function (b) { return b.open; }), ma: ma, ATR: ATR, TR: TR, CCI: CCI, rawK: rawK, K: K, D: D, MACD: MACD, SIG: SIG, HIST: HIST, RSI: RSI, AVGV: AVGV, RVOL: RVOL, EMA12: e12, EMA26: e26 };
  }

  /* ───────── 3.1 מבנה שיאים ושפלים ───────── */
  function scanSwings(bars, ind, reversal, minBars) {
    var N = bars.length, ATR = ind.ATR, pts = [], dir = 0, hi = null, lo = null, lastHigh = null, lastLow = null, protectedLow = null;
    function cand(i) { return { index: i, date: bars[i].date, price: null, atr: ATR[i] }; }
    function label(pt) {
      var prev = pt.kind === "HIGH" ? lastHigh : lastLow, tol = 0.15 * pt.atr;
      pt.previous_price = prev ? prev.price : null;
      if (!prev) { pt.label = pt.kind === "HIGH" ? "H" : "L"; return; }
      var d = pt.price - prev.price;
      if (pt.kind === "HIGH") pt.label = d > tol ? "HH" : d < -tol ? "LH" : "EH"; else pt.label = d > tol ? "HL" : d < -tol ? "LL" : "EL";
    }
    function confirm(pt, i) {
      pt.confirmed_index = i; pt.confirmed_at = bars[i].date; pt.reversal_atr = reversal;
      label(pt); pts.push(pt);
      if (pt.kind === "LOW") {
        if (pt.label === "HL" && lastHigh && lastHigh.label === "HH") protectedLow = Object.assign({}, pt, { protected_at: pt.confirmed_at });
        lastLow = pt;
      } else {
        if (pt.label === "HH" && lastLow && lastLow.label === "HL" && (!protectedLow || protectedLow.index !== lastLow.index)) protectedLow = Object.assign({}, lastLow, { protected_at: pt.confirmed_at });
        lastHigh = pt;
      }
    }
    var lastPt = null;
    for (var i = 0; i < N; i++) {
      if (ATR[i] == null || !(ATR[i] > 0)) continue;
      var b = bars[i];
      if (hi == null) { hi = cand(i); hi.price = b.high; lo = cand(i); lo.price = b.low; }
      if (dir >= 0 && b.high > hi.price) { hi = cand(i); hi.price = b.high; }
      if (dir <= 0 && b.low < lo.price) { lo = cand(i); lo.price = b.low; }
      var canConfirm = !lastPt || (i - lastPt.index >= minBars);
      if (!canConfirm) continue;
      if (dir <= 0 && i > lo.index && b.close >= lo.price + reversal * lo.atr) {
        var pl = { index: lo.index, date: lo.date, price: lo.price, kind: "LOW", atr: lo.atr };
        confirm(pl, i); lastPt = pl; dir = 1;
        var mi = lo.index + 1; for (var j = lo.index + 1; j <= i; j++) if (bars[j].high > bars[mi].high) mi = j;
        hi = cand(mi); hi.price = bars[mi].high;
      } else if (dir >= 0 && i > hi.index && b.close <= hi.price - reversal * hi.atr) {
        var ph = { index: hi.index, date: hi.date, price: hi.price, kind: "HIGH", atr: hi.atr };
        confirm(ph, i); lastPt = ph; dir = -1;
        var ni = hi.index + 1; for (j = hi.index + 1; j <= i; j++) if (bars[j].low < bars[ni].low) ni = j;
        lo = cand(ni); lo.price = bars[ni].low;
      }
    }
    return { points: pts, protectedLow: protectedLow };
  }
  function classifyStructure(bars, ind, reversal, minBars, lookback) {
    var N = bars.length, scan = scanSwings(bars, ind, reversal, minBars), cut = N - lookback;
    var win = scan.points.filter(function (p) { return p.index >= cut; });
    var highs = win.filter(function (p) { return p.kind === "HIGH"; }), lows = win.filter(function (p) { return p.kind === "LOW"; });
    var prot = scan.protectedLow && scan.protectedLow.index >= cut ? scan.protectedLow : null;
    var lh = highs.length ? last(highs).label : null, ll = lows.length ? last(lows).label : null;
    var f = { higher_high: lh === "HH", lower_high: lh === "LH", higher_low: ll === "HL", lower_low: ll === "LL" };
    var state = (f.higher_high && f.higher_low) ? "UP" : (f.lower_high && f.lower_low) ? "DOWN" : (highs.length && lows.length) ? "MIXED" : "INSUFFICIENT";
    var recent = win.slice(-12), counts = { HH: 0, HL: 0, LH: 0, LL: 0 };
    recent.forEach(function (p) { if (counts[p.label] != null) counts[p.label]++; });
    var breakLevel = prot ? prot.price - 0.5 * prot.atr : null, breach = 0;
    if (prot) for (var i = N - 1; i >= 0; i--) { if (bars[i].date <= prot.protected_at) break; if (bars[i].close < breakLevel) breach++; else break; }
    var lhAfterLL = false;
    if (prot) {
      var lastLL = null; win.forEach(function (p) { if (p.label === "LL" && p.index > prot.index) lastLL = p; });
      if (lastLL) lhAfterLL = win.some(function (p) { return p.label === "LH" && p.index > lastLL.index; });
    }
    var reasons = [
      "ברצף המשמעותי האחרון זוהו " + counts.HH + " שיאים גבוהים יותר ו־" + counts.HL + " שפלים גבוהים יותר",
      "לצדם זוהו " + counts.LH + " שיאים נמוכים יותר ו־" + counts.LL + " שפלים נמוכים יותר"];
    if (prot) {
      reasons.push("השפל העולה המבני האחרון הוא " + fmt2(prot.price) + " מתאריך " + prot.date);
      reasons.push(breach >= 1 ? "המחיר נסגר " + breach + " פעמים מתחת לגבול השפל המוגן (" + fmt2(breakLevel) + ")" : "השפל העולה המבני עדיין נשמר בסגירה");
    } else reasons.push("לא זוהה שפל עולה מוגן בחלון הנבדק");
    return { state: state, swings: win, highs: highs, lows: lows, sequence: recent.map(function (p) { return p.label; }), counts: counts,
      higher_high: f.higher_high, higher_low: f.higher_low, lower_high: f.lower_high, lower_low: f.lower_low,
      protected_low: prot, break_level: breakLevel, breach_closes: breach, at_risk: breach >= 1,
      damaged_sequence: lhAfterLL && breach >= 2, lower_high_after_lower_low: lhAfterLL, reasons: reasons, all_points: scan.points, lookback: lookback };
  }

  /* ───────── 2.1 + 6.3 ממוצעים נעים ───────── */
  function slopeState(s) { return s == null ? null : s > 0.1 ? "UP" : s < -0.1 ? "DOWN" : "FLAT"; }
  var SLOPE_HE = { UP: "עולה", DOWN: "יורד", FLAT: "שטוח" };
  function analyzeMA(bars, ind) {
    var N = ind.N, t = N - 1, C = ind.C[t], ATR = ind.ATR[t], rows = [], slopes = {}, byKey = {};
    var start = Math.max(1, N - 60);
    MA_ORDER.forEach(function (k) {
      var M = ind.ma[k], v = M[t];
      if (v == null) { slopes[k] = null; return; }
      var s5 = M[t - 5] != null ? (v / M[t - 5] - 1) * 100 : null, ss = slopeState(s5);
      slopes[k] = ss;
      var distPct = (C / v - 1) * 100, distAtr = ATR ? (C - v) / ATR : null;
      var position = C > v ? "ABOVE" : C < v ? "BELOW" : "AT";
      var near = ATR != null && Math.abs(C - v) <= 0.75 * ATR;
      var touching = ATR != null && ind.L[t] <= v + 0.35 * ATR && ind.H[t] >= v - 0.35 * ATR;
      // 6.3 חציות ותגובות ב-60 האחרונים
      var crossings = [], sup = [], res = [], lastEvent = null;
      for (var i = start; i < N; i++) {
        if (M[i] == null || M[i - 1] == null) continue;
        var before = ind.C[i - 1] / M[i - 1] - 1, now = ind.C[i] / M[i] - 1;
        if (before * now < 0) crossings.push({ date: bars[i].date, direction: now > 0 ? "up" : "down", index: i });
        if (i + 3 >= N) continue;
        if (lastEvent != null && i - lastEvent < 5) continue;
        var tol = 0.35 * ind.ATR[i] / M[i];
        var touched = ind.L[i] <= M[i] * (1 + tol) && ind.H[i] >= M[i] * (1 - tol);
        if (!touched) continue;
        var fut = [], ok = true; for (var j = i + 1; j <= i + 3; j++) { if (M[j] == null) { ok = false; break; } fut.push(ind.C[j] / M[j] - 1); }
        if (!ok) continue;
        if (before > tol && fut.every(function (f) { return f > tol; })) { sup.push(bars[i].date); lastEvent = i; }
        else if (before < -tol && fut.every(function (f) { return f < -tol; })) { res.push(bars[i].date); lastEvent = i; }
      }
      var thr = ATR ? 0.35 * ATR / v * 100 : 0, role;
      if (distPct > thr) role = sup.length >= 2 ? "תמיכה עם תגובות חוזרות" : "תמיכה אפשרית";
      else if (distPct < -thr) role = res.length >= 2 ? "התנגדות עם תגובות חוזרות" : "התנגדות אפשרית";
      else role = "המחיר סמוך לממוצע";
      var reclaimed = false;
      if (position === "ABOVE" && crossings.length) {
        var recent = crossings.filter(function (c) { return t - c.index < 20; });
        if (recent.length && last(recent).direction === "up" && recent.slice(0, -1).some(function (c) { return c.direction === "down"; })) reclaimed = true;
      }
      var row = { name: k, value: v, distance_pct: distPct, slope_5_pct: s5, slope: ss ? SLOPE_HE[ss] : "—", role: role, support_dates: sup, resistance_dates: res, crossings: crossings.map(function (c) { return { date: c.date, direction: c.direction }; }), historical_bars: 60,
        distance_atr: distAtr, position: position, near: near, touching: touching, reclaimed: reclaimed, horizon: LONG_MAS.indexOf(k) >= 0 ? "PRIMARY" : "SHORT_INTERMEDIATE" };
      rows.push(row); byKey[k] = row;
    });
    // סדר
    var avail = MA_ORDER.filter(function (k) { return byKey[k]; }), pos = 0, neg = 0, pairs = 0;
    for (var p = 0; p + 1 < avail.length; p++) { pairs++; var a = byKey[avail[p]].value, b = byKey[avail[p + 1]].value; if (a > b) pos++; else if (a < b) neg++; }
    var order = { state: pairs === 0 ? "MIXED" : pos === pairs ? "POSITIVE" : neg === pairs ? "NEGATIVE" : "MIXED", positive_pairs: pos, negative_pairs: neg, pair_count: pairs, complete: avail.length === 6, positive_fraction: pairs ? pos / pairs : null, ranked: avail.slice() };
    var longs = LONG_MAS.filter(function (k) { return byKey[k]; }), la = null, lr = null, lb = null, lf = null;
    if (longs.length) {
      var fr = function (fn) { return longs.filter(fn).length / longs.length; };
      la = fr(function (k) { return byKey[k].position === "ABOVE"; }); lr = fr(function (k) { return slopes[k] === "UP"; });
      lb = fr(function (k) { return byKey[k].position === "BELOW"; }); lf = fr(function (k) { return slopes[k] === "DOWN"; });
    }
    var bullish = longs.length > 0 && la >= 2 / 3 && lr >= 2 / 3, bearish = longs.length > 0 && lb >= 2 / 3 && lf >= 2 / 3;
    var comps = [la, lr, order.positive_fraction].filter(function (x) { return x != null; });
    var score = comps.length ? R(100 * mean(comps)) : null;
    // אשכולות
    var sorted = rows.slice().sort(function (a, b) { return a.value - b.value; }), clusters = [], cur = null;
    sorted.forEach(function (r) {
      if (cur && ATR != null && r.value - cur.anchor <= 0.7 * ATR) cur.members.push(r); else { cur = { anchor: r.value, members: [r] }; clusters.push(cur); }
    });
    clusters = clusters.filter(function (c) { return c.members.length >= 2; }).map(function (c) { return { low: c.members[0].value - 0.35 * ATR, high: last(c.members).value + 0.35 * ATR, members: c.members.map(function (m) { return m.name; }) }; });
    var zones = { clusters: clusters, support: rows.filter(function (r) { return r.position === "ABOVE" && (r.near || r.touching); }).map(function (r) { return r.name; }),
      resistance: rows.filter(function (r) { return r.position === "BELOW" && (r.near || r.touching); }).map(function (r) { return r.name; }) };
    var reasons = rows.map(function (r) {
      var posHe = r.position === "ABOVE" ? "מעל " : r.position === "BELOW" ? "מתחת ל" : "על ";
      var sl = slopes[r.name], slHe = sl === "UP" ? "הממוצע עולה" : sl === "DOWN" ? "הממוצע יורד" : sl === "FLAT" ? "הממוצע שטוח" : "אין עדיין שיפוע";
      return "המחיר " + posHe + "ממוצע " + MA_PERIOD[r.name] + " יום; " + slHe;
    });
    if (rows.length) reasons.push(order.state === "POSITIVE" ? "סדר הממוצעים חיובי מהקצר לארוך" : order.state === "NEGATIVE" ? "סדר הממוצעים שלילי מהקצר לארוך" : "סדר הממוצעים מעורב");
    return { rows: rows, byKey: byKey, slopes: slopes, order: order, score: score, bullish: bullish, bearish: bearish, long_available: longs.length,
      long_above_fraction: la, long_rising_fraction: lr, long_below_fraction: lb, long_falling_fraction: lf, zones: zones, reasons: reasons,
      order_text: order.state === "POSITIVE" ? "סדר חיובי: הממוצעים הקצרים מעל הארוכים" : order.state === "NEGATIVE" ? "סדר שלילי: הממוצעים הקצרים מתחת לארוכים" : "סדר מעורב של הממוצעים" };
  }

  /* ───────── 3.1 שילוב, 3.2 ראשית, 3.3 בינונית ───────── */
  function integrate(structure, ma, ind) {
    var t = ind.N - 1, s50 = ma.byKey.SMA50;
    var mediumWeak = !!(s50 && ind.C[t] < s50.value && (ma.slopes.SMA50 === "FLAT" || ma.slopes.SMA50 === "DOWN"));
    var clearBreak = structure.breach_closes >= 3 && mediumWeak && ma.bearish;
    var damaged = structure.damaged_sequence || clearBreak;
    return { medium_weak: mediumWeak, clear_break: clearBreak, damaged: damaged, at_risk: structure.at_risk && !damaged };
  }
  var PRIMARY_HE = { DAMAGED: "המגמה נפגעה", AT_RISK: "מבנה מגמה בסיכון", STRONG_UP: "מגמת עלייה חזקה", WEAKENING_UP: "מגמת עלייה שנחלשת", UP: "מגמת עלייה", DOWN: "מגמת ירידה", STRONG_DOWN: "מגמת ירידה חזקה", REVERSAL_ATTEMPT: "ניסיון היפוך", RANGE: "דשדוש" };
  function primaryTrend(structure, ma, integ) {
    var intactUp = structure.state === "UP" || (!!structure.protected_low && !integ.damaged && structure.state !== "DOWN");
    var state;
    if (integ.damaged) state = "DAMAGED";
    else if (integ.at_risk) state = "AT_RISK";
    else if (intactUp && ma.bullish && ma.order.complete && ma.order.positive_fraction >= 2 / 3 && structure.state === "UP") state = "STRONG_UP";
    else if (intactUp && integ.medium_weak) state = "WEAKENING_UP";
    else if (intactUp) state = "UP";
    else if (structure.state === "DOWN") state = "DOWN";
    else if (structure.higher_low && ma.bullish) state = "REVERSAL_ATTEMPT";
    else if (ma.bullish) state = "UP";
    else if (ma.bearish && structure.lower_low) state = "DOWN";
    else state = "RANGE";
    var sp = structure.state === "UP" ? 100 : structure.state === "DOWN" ? 0 : 50;
    if (intactUp && structure.state === "MIXED") sp = 80;
    var score = W([{ v: sp, w: 65 }, { v: ma.score, w: 35 }]);
    if (state === "AT_RISK") score = Math.min(score, 55); if (state === "DAMAGED") score = Math.min(score, 30);
    return { state: state, label: PRIMARY_HE[state], score: score, intact_up: intactUp, reasons: structure.reasons.concat(ma.reasons), available_averages: ma.long_available, components: { structure: sp, averages: ma.score } };
  }
  var INTER_HE = { AT_RISK: "המבנה הבינוני בסיכון", WEAKNESS: "חולשה בטווח הבינוני", PRESERVED: "מגמת העלייה נשמרת", REVERSAL_ATTEMPT: "ניסיון היפוך", MIXED: "מבנה ביניים מעורב" };
  function intermediateTrend(structure, integ, primary) {
    var state = (integ.damaged || integ.at_risk) ? "AT_RISK" : (structure.state === "DOWN" || integ.medium_weak) ? "WEAKNESS" : (["UP", "STRONG_UP", "WEAKENING_UP"].indexOf(primary.state) >= 0) ? "PRESERVED" : structure.state === "UP" ? "REVERSAL_ATTEMPT" : "MIXED";
    return { state: state, label: INTER_HE[state], reasons: structure.reasons.slice(), structure: structure };
  }

  /* ───────── 6.4 מכונת פריצה ───────── */
  var BREAKOUT_HE = { IN_PROGRESS: "פריצה בתהליך", CONFIRMED: "פריצה מאושרת", RETEST: "בדיקה חוזרת של אזור הפריצה", PULLBACK: "תיקון לאחר פריצה", FAILED: "פריצה שנכשלה", GAP_BREAKOUT: "פריצה בפער מחיר", GAP_PARTIAL_FILL: "מילוי חלקי של פער המחיר ללא כישלון פריצה", UNRESOLVED: "לא ניתן לקבוע עדיין אם הפריצה נכשלה", NONE: "אין אירוע פריצה" };
  function gapAt(bars, i, zone) {
    var O = bars[i].open, Hp = bars[i - 1].high;
    if (O - Hp > 0.1 * zone.atr && O > zone.high) return { present: true, date: bars[i].date, low: Hp, high: O, size: O - Hp, close_above_zone: bars[i].close > zone.high };
    return { present: false };
  }
  function analyzeBreakout(bars, ind, interStructure, interIntegration) {
    var N = ind.N, t = N - 1, event = null;
    function strongCandle(i, unit) { var q = bars[i].high - bars[i].low; return bars[i].close - bars[i].open >= 0.5 * unit && q > 0 && (bars[i].close - bars[i].low) / q >= 0.75; }
    for (var i = 20; i <= t; i++) {
      var unit = ind.ATR[i - 1];
      if (unit == null || !(unit > 0)) continue;
      if (event && i - event.index > 60) event = null;
      if (event && !event.closed_above && bars[i].close > event.zone.high + 0.05 * event.zone.atr) {
        event.closed_above = true; event.confirmed_at = bars[i].date; event.confirmation_index = i;
        event.strong_candle = strongCandle(i, event.zone.atr); event.rvol = ind.RVOL[i]; event.gap = gapAt(bars, i, event.zone);
      }
      // אזור מ-20 הנרות הקודמים
      var lo = i - 20, highest = -Infinity;
      for (var j = lo; j < i; j++) if (bars[j].high > highest) highest = bars[j].high;
      var near = []; for (j = lo; j < i; j++) if (highest - bars[j].high <= 0.5 * unit) near.push(j);
      var spaced = []; near.forEach(function (idx) { if (!spaced.length || idx - last(spaced) >= 3) spaced.push(idx); });
      var zone = null;
      if (spaced.length >= 2) {
        var minNearH = minArr(near.map(function (idx) { return bars[idx].high; }));
        zone = { low: minNearH - 0.2 * unit, high: highest + 0.2 * unit, atr: unit, known_at: bars[i - 1].date, touch_dates: spaced.map(function (idx) { return bars[idx].date; }), touch_count: spaced.length,
          average_candle_range: mean(near.map(function (idx) { return bars[idx].high - bars[idx].low; })),
          reasons: ["האזור מבוסס על " + spaced.length + " ביקורים קודמים ליד ההתנגדות", "גבולות האזור נקבעו מנתונים שקדמו לנר הפריצה ואינם מוזזים בעקבות התיקון"] };
      }
      if (!zone) continue;
      var crossing = bars[i - 1].close <= zone.high, thr = zone.high + 0.05 * unit;
      var above = bars[i].close > thr, attempt = bars[i].high > thr && bars[i].close >= zone.low;
      var replace = !event || (i - event.index >= 10 && zone.low > event.zone.high + unit);
      if (crossing && (above || attempt) && replace) {
        event = { index: i, date: bars[i].date, zone: zone, closed_above: false, strong_candle: strongCandle(i, unit), gap: gapAt(bars, i, zone), rvol: ind.RVOL[i], confirmed_at: null, confirmation_index: null };
        if (above) { event.closed_above = true; event.confirmed_at = bars[i].date; event.confirmation_index = i; }
      }
    }
    if (!event) return { state: "NONE", label: BREAKOUT_HE.NONE, event: null, zone: null, reasons: [], gaps: [], retest: null, failure: null, holding_closes: 0, drawdown_atr: null };
    var z = event.zone, ref = event.confirmation_index != null ? event.confirmation_index : event.index;
    // פערים
    var gaps = [];
    for (i = event.index; i <= t; i++) { if (i === 0) continue; var g = gapAt(bars, i, z); if (!g.present) continue; var minL = minArr(ind.L.slice(i, t + 1)); g.fill_fraction = Math.max(0, Math.min(1, (g.high - minL) / g.size)); g.initial = i === ref; gaps.push(g); }
    var partial = gaps.length > 0 && last(gaps).fill_fraction > 0 && last(gaps).fill_fraction < 1;
    // כישלון
    var boundary = z.low - 0.3 * z.atr, below = 0;
    for (i = t; i > ref; i--) { if (bars[i].close < boundary) below++; else break; }
    var structuralWeak = interIntegration.at_risk || interIntegration.damaged || interStructure.state === "DOWN";
    var lb = bars[t];
    var selling = lb.close < lb.open && Math.abs(lb.close - lb.open) >= 0.6 * z.atr && ind.RVOL[t] != null && ind.RVOL[t] >= 1.5;
    var continuation = t > 0 && bars[t].close < bars[t - 1].close;
    var failed = event.closed_above && below >= 2 && (structuralWeak || selling || (below >= 3 && continuation));
    var failure = { failed: failed, below_closes: below, boundary: boundary, structure_weak: structuralWeak, reasons: [] };
    if (failed) failure.reasons.push("נרשמו " + below + " סגירות רצופות מתחת לגבול הכישלון " + fmt2(boundary));
    // בדיקה חוזרת
    var after = t > ref, touched = lb.low <= z.high + 0.15 * z.atr && lb.high >= z.low - 0.15 * z.atr, holds = lb.close >= boundary, rejected = touched && lb.close > z.high && lb.close > lb.open;
    var retest = { active: after && event.closed_above && touched && holds && !structuralWeak, touched: touched, holds: holds, rejected: rejected, reasons: [] };
    if (retest.active) retest.reasons.push(rejected ? "המחיר נגע באזור הפריצה ונדחה ממנו כלפי מעלה" : "המחיר בודק מחדש את אזור הפריצה ושומר על גבול הכישלון");
    var following = t - ref, holding = 0;
    for (i = ref + 1; i <= t; i++) if (bars[i].close > z.high) holding++;
    var peak = maxArr(ind.H.slice(event.index, t + 1)), drawdown = (peak - lb.close) / z.atr;
    var state;
    if (failed) state = "FAILED";
    else if (below > 0 || (touched && structuralWeak)) state = "UNRESOLVED";
    else if (partial && event.closed_above && lb.close >= boundary) state = "GAP_PARTIAL_FILL";
    else if (retest.active) state = "RETEST";
    else if (event.closed_above && following > 0 && drawdown >= 0.75) state = "PULLBACK";
    else if (event.gap.present && event.closed_above && following === 0) state = "GAP_BREAKOUT";
    else if (event.closed_above && holding >= 2) state = "CONFIRMED";
    else state = "IN_PROGRESS";
    var reasons = z.reasons.slice();
    reasons.push(event.closed_above ? "ניסיון הפריצה החל בתאריך " + event.date + "; סגירה מעל האזור אושרה בתאריך " + event.confirmed_at : "ניסיון הפריצה החל בתאריך " + event.date + "; טרם נרשמה סגירה מעל האזור");
    if (event.strong_candle) reasons.push("נר הפריצה חזק: גוף רחב וסגירה סמוך לגבוה היומי");
    if (event.rvol != null && event.rvol >= 1.2) reasons.push("המחזור בנר הפריצה גבוה מהממוצע ותומך באיכות האירוע");
    if (event.closed_above && following > 0) reasons.push("לאחר האירוע נרשמו " + holding + " סגירות מעל האזור");
    if (event.gap.present) reasons.push("זוהה פער מחיר כלפי מעלה; מילוי הפער נבדק בנפרד מאובדן אזור הפריצה");
    if (state === "PULLBACK") reasons.push("המחיר ירד מהשיא שאחרי הפריצה, אך טרם איבד בבירור את אזור הפריצה");
    else if (state === "FAILED") reasons.push("הפריצה נכשלה: המחיר איבד את אזור הפריצה ונסגר מתחת לגבול הכישלון");
    else if (state === "UNRESOLVED") reasons.push("המחיר נסגר מתחת לגבול הכישלון או נגע באזור בזמן חולשה מבנית; טרם הוכרע אם הפריצה נכשלה");
    else if (state === "GAP_PARTIAL_FILL") reasons.push("פער המחיר מולא חלקית; אזור הפריצה עצמו נשמר");
    else if (state === "RETEST") reasons.push("המחיר חזר לבדוק את אזור הפריצה ושומר עליו");
    else if (state === "GAP_BREAKOUT") reasons.push("הפריצה התרחשה בפער מחיר; טרם נרשמו נרות המשך");
    else if (state === "CONFIRMED") reasons.push("הפריצה מאושרת: לפחות שתי סגירות מעל האזור");
    else reasons.push("הפריצה עדיין בתהליך; ממתינים לסגירות מעל האזור");
    reasons.push.apply(reasons, failure.reasons); reasons.push.apply(reasons, retest.reasons);
    return { state: state, label: BREAKOUT_HE[state], zone: z, event: event, gaps: gaps, retest: retest, failure: failure, holding_closes: holding, drawdown_atr: drawdown, reasons: reasons };
  }

  /* ───────── 2.4 מתנדים, 2.5 MACD ───────── */
  function oscillator(series, t, lv) {
    var now = series[t], prev = series[t - 1], before = series[t - 2];
    if (now == null || prev == null) return { value: now, previous: prev, state: "STABLE", rising: false, falling: false, turned: false, recovered: false, low: false, high: false, score: 50 };
    var rising = now - prev > lv.eps, falling = prev - now > lv.eps, turned = rising && before != null && prev <= before, recovered = prev <= lv.oversold && now > lv.oversold;
    var state, score;
    if (recovered) { state = "RECOVERED"; score = 75; } else if (turned) { state = "TURNING_UP"; score = 65; } else if (falling) { state = "FALLING"; score = 25; }
    else if (now <= lv.veryLow) { state = "VERY_LOW"; score = 15; } else if (now <= lv.oversold) { state = "LOW"; score = 30; }
    else if (now >= lv.veryHigh) { state = "VERY_HIGH"; score = 85; } else if (now >= lv.overbought) { state = "HIGH"; score = 80; }
    else if (rising) { state = "RISING"; score = 70; } else { state = "STABLE"; score = 50; }
    return { value: now, previous: prev, state: state, rising: rising, falling: falling, turned: turned, recovered: recovered, low: now <= lv.oversold, high: now >= lv.overbought, score: score };
  }
  function analyzeMACD(ind, t) {
    var v = ind.MACD[t], sig = ind.SIG[t], h = ind.HIST[t], atr = ind.ATR[t], eps = 0.001 * (atr || 0);
    var hs = [ind.HIST[t - 3], ind.HIST[t - 2], ind.HIST[t - 1], h], improving = false, falling = false;
    if (hs.every(function (x) { return x != null; })) {
      improving = hs[1] - hs[0] > eps && hs[2] - hs[1] > eps && hs[3] - hs[2] > eps;
      falling = hs[0] - hs[1] > eps && hs[1] - hs[2] > eps && hs[2] - hs[3] > eps;
    }
    var state, score;
    if (v == null) { state = "NEUTRAL"; score = 50; }
    else if (improving) { state = "IMPROVING"; score = 65; } else if (falling) { state = "WEAKENING"; score = 30; }
    else if (v > 0 && h > 0) { state = "SUPPORTIVE"; score = 90; } else if (v > 0) { state = "POSITIVE"; score = 70; }
    else if (atr && v / atr < -1) { state = "VERY_NEGATIVE"; score = 5; } else if (v < 0) { state = "NEGATIVE"; score = 20; } else { state = "NEUTRAL"; score = 50; }
    return { state: state, score: score, value: v, signal: sig, histogram: h, improving: improving, falling: falling, above_zero: v != null && v > 0, above_signal: h != null && h > 0 };
  }

  /* ───────── 2.7 נרות ───────── */
  function candleFlags(bars, ind, t) {
    var b = bars[t], p = bars[t - 1], q = b.high - b.low, body = Math.abs(b.close - b.open), atr = ind.ATR[t] || 0;
    var positive = b.close > b.open, strongClose = q > 0 && (b.close - b.low) / q >= 0.75;
    var strongGreen = positive && body >= 0.6 * atr && q > 0 && body / q >= 0.6, strongRed = b.close < b.open && body >= 0.6 * atr && q > 0 && body / q >= 0.6;
    var lowerTail = q > 0 && (Math.min(b.open, b.close) - b.low) / q >= 0.5, doji = q > 0 && body / q <= 0.1;
    var up = 0, down = 0;
    for (var i = t; i >= 1; i--) { if (bars[i].close > bars[i - 1].close) up++; else break; }
    for (i = t; i >= 1; i--) { if (bars[i].close < bars[i - 1].close) down++; else break; }
    return { strong_green: strongGreen, strong_red: strongRed, lower_tail: lowerTail, strong_close: strongClose, doji: doji, above_previous_high: !!p && b.close > p.high, reversal: lowerTail && positive && !!p && p.close < p.open, up_streak: up, down_streak: down, positive: positive, high: b.high, low: b.low };
  }

  /* ───────── 4.6 מתיחות ───────── */
  var EXT_HE = { VERY_EXTENDED: "המחיר מתוח מאוד", EXTENDED: "המחיר מתוח", MODERATE: "מתיחות המחיר סבירה", NORMAL: "המחיר קרוב לממוצעים" };
  function analyzeExtension(ind, ma, cci, stoch, candles, t) {
    var atr = ind.ATR[t], C = ind.C[t], distances = {}, comps = {}, items = [];
    var spec = { EMA20: [3, 25], SMA50: [5, 25], SMA150: [8, 10], SMA200: [10, 10] };
    MA_ORDER.forEach(function (k) {
      var r = ma.byKey[k]; if (!r) return;
      var dAtr = atr ? (C - r.value) / atr : 0; distances[k] = { percent: r.distance_pct, atr: dAtr };
      if (spec[k]) { comps[k] = S(100 * Math.max(0, dAtr) / spec[k][0]); items.push({ v: comps[k], w: spec[k][1] }); }
    });
    comps.oscillators = 50 * ((cci.high ? 1 : 0) + (stoch.high ? 1 : 0)); items.push({ v: comps.oscillators, w: 15 });
    comps.streak = S(candles.up_streak / 6 * 100); items.push({ v: comps.streak, w: 15 });
    var score = W(items), state = score > 80 ? "VERY_EXTENDED" : score > 60 ? "EXTENDED" : score > 30 ? "MODERATE" : "NORMAL";
    return { score: score, state: state, label: EXT_HE[state], distances: distances, components: comps };
  }

  /* ───────── 4.3 תיקון, 4.7 מחזורים ───────── */
  function detectPullback(bars, ind, primaryState, t) {
    var N = ind.N, start = Math.max(0, N - 30), pi = start;
    for (var i = start; i <= t; i++) if (bars[i].high > bars[pi].high) pi = i;
    var peak = bars[pi].high, C = ind.C[t], depth = peak - C, atr = ind.ATR[t], depthAtr = atr ? depth / atr : 0, age = t - pi, down = 0;
    for (i = pi + 1; i <= t; i++) if (bars[i].close < bars[i - 1].close) down++;
    return { active: age >= 2 && depthAtr >= 0.75, in_uptrend: ["UP", "STRONG_UP", "WEAKENING_UP"].indexOf(primaryState) >= 0, peak: peak, peak_date: bars[pi].date, peak_index: pi, days_since_peak: age, percent: 100 * depth / peak, depth_atr: depthAtr, down_days: down, depth: depth };
  }
  function analyzeVolume(bars, ind, pullback, t) {
    var N = ind.N, up = [], down = [];
    for (var i = Math.max(1, N - 20); i <= t; i++) { if (bars[i].close > bars[i - 1].close) up.push(bars[i].volume); else if (bars[i].close < bars[i - 1].close) down.push(bars[i].volume); }
    var ratio = null; if (up.length && down.length) { var md = mean(down); if (md > 0) ratio = mean(up) / md; }
    var falling = []; for (i = pullback.peak_index + 1; i <= t; i++) if (bars[i].close < bars[i - 1].close) falling.push(bars[i].volume);
    var avgV = ind.AVGV[t], priorSlice = bars.slice(Math.max(0, pullback.peak_index - 20), pullback.peak_index).map(function (b) { return b.volume; });
    var priorAvg = priorSlice.length ? mean(priorSlice) : avgV;
    var corr = (falling.length && priorAvg > 0) ? mean(falling) / priorAvg : null;
    var rv = ind.RVOL[t], selling = t > 0 && bars[t].close < bars[t - 1].close && rv != null && rv >= 1.5, returning = t > 0 && bars[t].close > bars[t - 1].close && rv != null && rv >= 1.1;
    var quiet = corr != null && corr < 0.85, heavy = selling || (corr != null && corr >= 1.5), unavailable = avgV == null || avgV === 0;
    var comps = { balance: ratio == null ? null : S(ratio / 1.5 * 100), correction: quiet ? 100 : heavy ? 0 : corr != null ? 50 : null, last: returning ? 100 : selling ? 0 : rv != null ? 50 : null };
    var score = W([{ v: comps.balance, w: 40 }, { v: comps.correction, w: 35 }, { v: comps.last, w: 25 }]);
    return { score: score, up_down_ratio: ratio, correction_ratio: corr, rvol: rv, quiet: quiet, heavy: heavy, returning: returning, selling: selling, unavailable: unavailable, components: comps, average_volume: avgV };
  }

  /* ───────── 6.1 + 6.2 אזורים ───────── */
  function zoneContext(bars, ind, zone, t) {
    var N = ind.N, atr = ind.ATR[t], start = Math.max(1, N - 60), inside = false, lastVisit = null, sup = [], res = [];
    for (var i = start; i < N; i++) {
      var touched = bars[i].low <= zone.high && bars[i].high >= zone.low;
      if (touched && !inside && (lastVisit == null || i - lastVisit >= 5)) {
        lastVisit = i;
        if (i + 3 < N) {
          var c1 = bars[i + 1].close, c2 = bars[i + 2].close, c3 = bars[i + 3].close, pc = bars[i - 1].close;
          if (pc >= zone.high && c1 > zone.high && c2 > zone.high && c3 > zone.high) sup.push({ date: bars[i].date, age_bars: t - i, strength_atr: atr ? (Math.max(c1, c2, c3) - zone.high) / atr : 0 });
          else if (pc <= zone.low && c1 < zone.low && c2 < zone.low && c3 < zone.low) res.push({ date: bars[i].date, age_bars: t - i });
        }
      }
      inside = touched;
    }
    var fading = sup.length >= 3 && sup[sup.length - 1].strength_atr < sup[sup.length - 2].strength_atr && sup[sup.length - 2].strength_atr < sup[sup.length - 3].strength_atr;
    var quality = fading ? "תגובות נחלשות" : sup.length >= 2 ? "תגובות תמיכה חוזרות" : "תמיכה אפשרית";
    var b = bars[t], p = bars[t - 1], C = b.close, touchedNow = b.low <= zone.high && b.high >= zone.low, state;
    if (C < zone.low) state = "BELOW";
    else if (C > zone.high && (b.low < zone.low || (p && p.close < zone.low))) state = "RECLAIMED";
    else if (touchedNow && C > zone.high) state = "BOUNCE";
    else if (touchedNow) state = "TESTING";
    else if (atr != null && C - zone.high <= 0.75 * atr) state = "APPROACHING";
    else state = "ABOVE";
    var STATE_HE = { BELOW: "הסגירה מתחת לאזור; סימן לחולשה שיש לבחון לפי עומק השבירה והמשכיות", RECLAIMED: "המחיר חזר ונסגר מעל האזור לאחר שבירה; יש לבחון את איכות ההחזרה", BOUNCE: "נר המחיר נגע באזור ונסגר מעליו; נראית תגובה לתמיכה", TESTING: "המחיר בוחן את האזור כעת; טרם נרשמה סגירה מעליו", APPROACHING: "המחיר מתקרב לאזור מלמעלה", ABOVE: "המחיר מעל האזור ואינו בוחן אותו כעת" };
    var details = [quality + ": " + sup.length + " תגובות תמיכה שהושלמו בביקורים נפרדים", STATE_HE[state]];
    if (sup.length) { var ls = last(sup); details.push("התגובה האחרונה ב־" + ls.date + ", לפני " + ls.age_bars + " נרות; עוצמת ההתאוששות " + fmt1(ls.strength_atr) + " ATR ביחס לתנודתיות הנוכחית"); }
    if (res.length) details.push("באזור נצפו גם " + res.length + " תגובות התנגדות; הן אינן נספרות כתגובות תמיכה");
    if (fading) details.push("שלוש ההתאוששויות האחרונות מהאזור נחלשות");
    // לחץ על האזור
    if (N >= 23 && state !== "ABOVE") {
      var prior = bars.slice(N - 23, N - 3).map(function (x) { return x.volume; }), pav = mean(prior), reds = bars.slice(N - 3).filter(function (x) { return x.close < x.open; });
      if (atr > 0 && pav > 0 && reds.length) {
        var pressure = reds.some(function (x) { var q = x.high - x.low; return q > 1.2 * atr && x.close <= x.low + 0.25 * q && x.volume > 1.2 * pav; });
        var orderly = reds.length >= 2 && reds.every(function (x) { return (x.high - x.low) < atr && x.volume < pav; });
        if (pressure) details.push("בנרות האחרונים נר אדום רחב עם סגירה נמוכה ומחזור גבוה — לחץ מכירות על האזור");
        else if (orderly) details.push("הנרות האדומים האחרונים צרים ובמחזור נמוך — תיקון מסודר לאזור");
      }
    }
    details.push("התגובות נבדקות סביב האזור הנוכחי; אין בכך הוכחה שהממוצע הנע עצמו שימש תמיכה בתאריכים אלה");
    return { support_reactions: sup, resistance_reactions: res, fading: fading, quality: quality, state: state, details: details };
  }
  function analyzeLevels(bars, ind, ma, primaryStructure, breakout, t) {
    var atr = ind.ATR[t], w = 0.35 * atr, C = ind.C[t], cands = [];
    MA_ORDER.forEach(function (k) { if (ma.byKey[k]) cands.push({ v: ma.byKey[k].value, src: maName(k) }); });
    primaryStructure.lows.slice(-5).forEach(function (p) { cands.push({ v: p.price, src: "שפל קודם" }); });
    primaryStructure.highs.slice(-5).forEach(function (p) { cands.push({ v: p.price, src: "שיא קודם" }); });
    if (breakout.zone) cands.push({ v: (breakout.zone.low + breakout.zone.high) / 2, src: "אזור פריצה קודם" });
    cands.sort(function (a, b) { return a.v - b.v || (a.src < b.src ? -1 : a.src > b.src ? 1 : 0); });
    var zones = [];
    cands.forEach(function (c) {
      var lo = c.v - w, hi = c.v + w, z = last(zones);
      if (z && lo <= z.high && hi - z.low <= 4 * w) { z.high = Math.max(z.high, hi); if (z.sources.indexOf(c.src) < 0) z.sources.push(c.src); }
      else zones.push({ low: lo, high: hi, sources: [c.src] });
    });
    zones.forEach(function (z) {
      z.context = zoneContext(bars, ind, z, t);
      var rc = z.context.support_reactions.length; if (z.context.fading) rc = Math.min(rc, 2);
      z.reactions = rc;
      var nonMa = z.sources.filter(function (s) { return s.indexOf("ממוצע") !== 0; }).length, hasMa = z.sources.length - nonMa > 0;
      z.score = S(20 + 15 * (nonMa + (hasMa ? 1 : 0)) + 10 * rc);
      z.mid = (z.low + z.high) / 2;
    });
    var support = null, resistance = null;
    zones.forEach(function (z) { if (z.mid <= C) { if (!support || z.high > support.high) support = z; } else if (!resistance || z.low < resistance.low) resistance = z; });
    var nearSupport = !!support && C - support.high <= 0.75 * atr;
    var tested = null, p = bars[t - 1];
    zones.slice().sort(function (a, b) { return b.high - a.high; }).some(function (z) { if (z.context.state === "BELOW" && bars[t].high >= z.low && p && p.close >= z.low) { tested = z; return true; } return false; });
    var chart = zones.filter(function (z) { return z.mid <= C; }).sort(function (a, b) { return b.high - a.high; }).slice(0, 2);
    return { support: support, resistance: resistance, near_support: nearSupport, zones: zones, tested_support: tested, chart_supports: chart };
  }

  /* ───────── 4.3 איכות התיקון ───────── */
  var PQ_HE = { NONE: "אין תיקון פעיל", DANGEROUS: "תיקון מסוכן", HEALTHY: "תיקון בריא", DEEP: "תיקון עמוק", UNCONFIRMED: "תיקון שטרם אושר" };
  function pullbackQuality(pullback, structure, volume, levels, cci, stoch, macd, trend, candles) {
    if (!pullback.active) return { score: null, state: "NONE", label: PQ_HE.NONE, reasons: ["אין תיקון פעיל: המחיר קרוב לשיא 30 הנרות האחרונים"], components: {} };
    var comps = { structure: structure.broken ? 0 : structure.higher_low ? 100 : 50, volume: volume.score, support: levels.near_support && levels.support ? levels.support.score : 0,
      cooled: 50 * ((cci.low ? 1 : 0) + (stoch.low ? 1 : 0)), macd: macd.score, trend: trend.score, depth: S(100 * (1 - pullback.depth_atr / 5)) };
    var score = W([{ v: comps.structure, w: 25 }, { v: comps.volume, w: 20 }, { v: comps.support, w: 15 }, { v: comps.cooled, w: 10 }, { v: comps.macd, w: 10 }, { v: comps.trend, w: 10 }, { v: comps.depth, w: 10 }]);
    var damaged = structure.broken || (volume.heavy && candles.strong_red) || pullback.depth_atr >= 5;
    var state = damaged ? "DANGEROUS" : (pullback.in_uptrend && score >= 60) ? "HEALTHY" : pullback.depth_atr >= 3 ? "DEEP" : "UNCONFIRMED";
    var reasons = ["המחיר ירד " + fmt1(pullback.percent) + "% מהשיא, בעומק של " + fmt1(pullback.depth_atr) + " יחידות תנודתיות"];
    if (volume.quiet) reasons.push("המחזור נחלש במהלך התיקון — סימן לתיקון בריא"); else if (volume.heavy) reasons.push("מחזור גבוה בירידות מעיד על לחץ מכירות");
    if (structure.broken) reasons.push("השפל העולה המאושר נשבר"); else if (structure.higher_low) reasons.push("השפל העולה המאושר עדיין נשמר");
    if (levels.near_support) reasons.push("המחיר נמצא באזור תמיכה אפשרי");
    if (state === "DEEP") reasons.push("עומק התיקון גדול מ־3 יחידות תנודתיות");
    if (damaged) reasons.push("התיקון מסוכן: שבירת מבנה, מכירה במחזור גבוה או עומק חריג");
    return { score: score, state: state, label: PQ_HE[state], reasons: reasons, components: comps, damaged: damaged };
  }

  /* ───────── 3.5 אישור, כניסה, סטטוס ───────── */
  function supportRecoveryEvidence(bars, ind, levels, t) {
    var N = ind.N, cci = ind.CCI, rec = false;
    if (cci[t] != null && cci[t - 1] != null && cci[t] > cci[t - 1]) for (var i = Math.max(0, t - 5); i < t; i++) if (cci[i] != null && cci[i] <= -100) { rec = true; break; }
    var piv = [];
    for (i = Math.max(2, N - 30); i <= N - 2; i++) if (bars[i].low < Math.min(bars[i - 1].low, bars[i - 2].low, bars[i + 1].low)) piv.push(i);
    var cur = piv.length ? last(piv) : null, prev = null;
    if (cur != null) for (i = piv.length - 2; i >= 0; i--) if (cur - piv[i] >= 3) { prev = piv[i]; break; }
    var higher = false;
    if (cur != null && prev != null && cur >= N - 3 && bars[cur].low > bars[prev].low) { higher = true; for (i = prev + 1; i <= t; i++) if (bars[i].low < bars[prev].low) { higher = false; break; } }
    var volInc = t > 0 && bars[t - 1].volume > 0 && bars[t].volume > bars[t - 1].volume;
    var sup = levels.support, touched = !!sup && [t, t - 1].some(function (i) { return i >= 0 && bars[i].low <= sup.high && bars[i].high >= sup.low; });
    return { cci_recovery: rec, higher_low: higher, previous_low: prev != null ? bar(bars[prev]) : null, current_low: cur != null ? bar(bars[cur]) : null, volume_increase: volInc, touched: touched, pivots: piv };
  }
  var ACTION_HE = { DAMAGED: "המגמה נפגעה", AT_RISK: "המגמה בסיכון", DO_NOT_CHASE: "המניה מתוחה – לא לרדוף", WAIT_PULLBACK: "להמתין לתיקון", PULLBACK_UNFINISHED: "התיקון עדיין נמשך", PRICE_CONFIRMED_BUY: "התקבל אישור מחיר לקנייה", QUALITY_ENTRY: "כניסה איכותית", POSSIBLE_BUY: "כניסה אפשרית", WEAKENING: "המגמה נחלשת", WAIT_CONFIRMATION: "להמתין לאישור", MOMENTUM_WEAK: "המגמה נשמרת אך המומנטום חלש", WATCH: "מעקב לקראת כניסה", NO_TRADE: "אין כרגע עסקה מעניינת", INTRADAY_PREVIEW: "ניתוח זמני — ממתין לסגירת הנר" };
  function evaluateEntry(bars, ind, trend, quality, levels, candles, cci, stoch, macd, volume, extension, pstruct, pullback, recovery, t) {
    var b = bars[t], atr = ind.ATR[t], C = b.close, upTrend = trend.state === "UP" || trend.state === "STRONG_UP";
    var signs = { cci: cci.rising, stochastic: stoch.rising, macd: macd.improving, volume: volume.returning, candle: candles.positive && candles.strong_close, price: candles.above_previous_high };
    var conf = W([{ v: signs.cci ? 100 : 0, w: 15 }, { v: signs.stochastic ? 100 : 0, w: 15 }, { v: signs.macd ? 100 : 0, w: 15 }, { v: signs.volume ? 100 : 0, w: 15 }, { v: signs.candle ? 100 : 0, w: 20 }, { v: signs.price ? 100 : 0, w: 20 }]);
    var res = levels.resistance, nearRes = !!res && res.low - C < 0.75 * atr;
    var blocked = pstruct.broken || pstruct.failed_breakout || quality.state === "DANGEROUS" || extension.score > 60 || nearRes;
    var sup = levels.support;
    var candidate = upTrend && quality.state === "HEALTHY" && levels.near_support && candles.positive && (candles.strong_close || candles.above_previous_high) && conf >= 50 && !blocked && !volume.unavailable && atr > 0;
    var entry = null, inval = null, ceiling = false;
    if (candidate) { entry = b.high + 0.05 * atr; inval = Math.min(b.low, sup.low) - 0.15 * atr; if (res && entry >= res.low) { candidate = false; entry = null; inval = null; ceiling = true; } }
    var comps = { trend: trend.score, support: levels.near_support && sup ? sup.score : 0, pullback: quality.score, confirmation: conf, location: extension.score == null ? null : 100 - extension.score, volume: volume.score };
    var score = W([{ v: comps.trend, w: 20 }, { v: comps.support, w: 20 }, { v: comps.pullback, w: 20 }, { v: comps.confirmation, w: 20 }, { v: comps.location, w: 10 }, { v: comps.volume, w: 10 }]);
    if (blocked || ceiling) score = Math.min(score, 49);
    var okBase = !pstruct.broken && !pstruct.failed_breakout && extension.score <= 60 && !volume.unavailable && !volume.heavy && atr > 0;
    var strongRoute = upTrend && quality.state === "HEALTHY" && levels.near_support && candles.positive && candles.strong_close && candles.above_previous_high && okBase;
    var altRoute = recovery.cci_recovery && recovery.higher_low && recovery.volume_increase && recovery.touched && !!sup && C >= sup.low && levels.near_support &&
      upTrend && pullback.active && quality.state !== "DANGEROUS" && quality.state !== "DEEP" && candles.positive && candles.above_previous_high && okBase;
    var priceConfirmed = strongRoute || altRoute, route = strongRoute ? "STRONG_CLOSE" : altRoute ? "CCI_SUPPORT_RECOVERY" : null;
    var riskD = entry != null ? entry - inval : null, riskP = entry != null ? 100 * riskD / entry : null;
    return { confirmation_route: route, recovery_evidence: { cci_recovery: recovery.cci_recovery, higher_low: recovery.higher_low, previous_low: recovery.previous_low, current_low: recovery.current_low, volume_increase: recovery.volume_increase },
      price_confirmed: priceConfirmed, score: score, confirmation_score: conf, signs: signs, candidate: candidate, entry: entry, invalidation: inval, risk_distance: riskD, risk_percent: riskP, near_resistance: nearRes, blocked: blocked, components: comps, ceiling: ceiling, strong_route: strongRoute, alt_route: altRoute };
  }
  function decideAction(trend, extension, quality, entry, pullback, candles, macd) {
    if (trend.state === "DAMAGED") return "DAMAGED";
    if (trend.state === "AT_RISK") return "AT_RISK";
    if (extension.score > 80) return "DO_NOT_CHASE";
    if (extension.score > 60) return "WAIT_PULLBACK";
    if (quality.state === "DANGEROUS") return "PULLBACK_UNFINISHED";
    if (entry.price_confirmed) return "PRICE_CONFIRMED_BUY";
    if (entry.candidate && entry.score >= 75) return "QUALITY_ENTRY";
    if (entry.candidate) return "POSSIBLE_BUY";
    if (trend.state === "WEAKENING_UP") return "WEAKENING";
    if (pullback.active && (candles.down_streak >= 2 || macd.falling)) return "PULLBACK_UNFINISHED";
    if (quality.state === "HEALTHY") return "WAIT_CONFIRMATION";
    if ((trend.state === "UP" || trend.state === "STRONG_UP") && macd.falling) return "MOMENTUM_WEAK";
    if (["UP", "STRONG_UP", "REVERSAL_ATTEMPT"].indexOf(trend.state) >= 0) return "WATCH";
    return "NO_TRADE";
  }

  /* ───────── 3.4 מצב קצר ───────── */
  var SHORT_HE = { STRUCTURE_BREAK: "שבירת מבנה", FAILED_BREAKOUT: "פריצה שנכשלה", EXTENDED: "המניה מתוחה", AFTER_BREAKOUT: "אחרי פריצה", RECOVERING: "ניסיון להתאושש מהתיקון", SUPPORT_TEST: "בדיקת תמיכה", HEALTHY_PULLBACK: "תיקון בריא בתוך מגמת עלייה", DEEP_PULLBACK: "תיקון עמוק", PULLBACK: "תיקון", CONSOLIDATION: "התכנסות", ORDERLY_RISE: "עלייה מסודרת", WEAKNESS: "חולשה", DAMAGED: "המגמה נפגעה", AT_RISK: "המבנה בסיכון", REVERSAL_ATTEMPT: "ניסיון היפוך", POSITIVE_MOMENTUM: "מומנטום חיובי" };
  function shortState(primary, pstruct, extension, pullback, candles, macd, ma, levels, quality, breakout) {
    var base;
    if (primary.state === "DAMAGED") base = "STRUCTURE_BREAK";
    else if (pstruct.failed_breakout) base = "FAILED_BREAKOUT";
    else if (extension.score > 60) base = "EXTENDED";
    else if (pstruct.breakout) base = "AFTER_BREAKOUT";
    else if (pullback.active && candles.positive && (macd.improving || candles.above_previous_high)) base = "RECOVERING";
    else if (pullback.active && (ma.zones.support.length > 0 || levels.near_support)) base = "SUPPORT_TEST";
    else if (quality.state === "HEALTHY") base = "HEALTHY_PULLBACK";
    else if (quality.state === "DEEP" || quality.state === "DANGEROUS") base = "DEEP_PULLBACK";
    else if (pullback.active) base = "PULLBACK";
    else if (pstruct.consolidating) base = "CONSOLIDATION";
    else if (primary.state === "UP" || primary.state === "STRONG_UP") base = "ORDERLY_RISE";
    else base = "WEAKNESS";
    var state = base, label = SHORT_HE[base];
    if (breakout.state !== "NONE" && ["DAMAGED", "AT_RISK", "STRUCTURE_BREAK", "EXTENDED"].indexOf(base) < 0) { state = "BREAKOUT_" + breakout.state; label = BREAKOUT_HE[breakout.state]; }
    return { state: state, base: base, label: label };
  }

  /* ───────── 2.8 תבניות נרות ───────── */
  function priorDirection(bars, s) {
    var closes = [], ranges = [];
    for (var i = Math.max(0, s - 3); i < s; i++) { closes.push(bars[i].close); ranges.push(bars[i].high - bars[i].low); }
    if (closes.length < 2) return 0;
    var d = last(closes) - closes[0], tol = 0.1 * mean(ranges);
    return d > tol ? 1 : d < -tol ? -1 : 0;
  }
  var PAT_HE = { DOJI: "דוג׳י — חוסר הכרעה", HAMMER: "פטיש לאחר ירידה", HANGING_MAN: "איש תלוי לאחר עלייה — אזהרה הדורשת אישור", LOWER_WICK: "זנב תחתון ללא מגמה קודמת ברורה", INVERTED_HAMMER: "פטיש הפוך לאחר ירידה", SHOOTING_STAR: "כוכב נופל לאחר עלייה", UPPER_WICK: "זנב עליון ללא מגמה קודמת ברורה", BULLISH_ENGULFING: "בליעה שורית", BEARISH_ENGULFING: "בליעה דובית", INSIDE: "נר פנימי — התכנסות", OUTSIDE: "נר חיצוני — התרחבות", MORNING_STAR: "כוכב בוקר", EVENING_STAR: "כוכב ערב", RISING_THREE_METHODS: "שלוש שיטות עולות — המשך לאחר תיקון", FALLING_THREE_METHODS: "שלוש שיטות יורדות — המשך לאחר תיקון" };
  var PAT_SPAN = { BULLISH_ENGULFING: 2, BEARISH_ENGULFING: 2, MORNING_STAR: 3, EVENING_STAR: 3, RISING_THREE_METHODS: 5, FALLING_THREE_METHODS: 5 };
  var TRACKED = ["HAMMER", "HANGING_MAN", "INVERTED_HAMMER", "SHOOTING_STAR", "BULLISH_ENGULFING", "BEARISH_ENGULFING", "DOJI", "MORNING_STAR", "EVENING_STAR", "RISING_THREE_METHODS", "FALLING_THREE_METHODS"];
  function detectPatterns(bars, t) {
    var b = bars[t], q = b.high - b.low, out = [];
    if (!(q > 0)) return out;
    var body = Math.abs(b.close - b.open) / q, up = (b.high - Math.max(b.open, b.close)) / q, lo = (Math.min(b.open, b.close) - b.low) / q;
    var pd = priorDirection(bars, t), p = t > 0 ? bars[t - 1] : null, green = b.close > b.open, red = b.close < b.open;
    function add(code, dir) { out.push({ code: code, label: PAT_HE[code], direction: dir }); }
    if (body <= 0.1) add("DOJI", 0);
    if (lo >= 0.55 && up <= 0.2 && body > 0.1) { if (pd < 0) add("HAMMER", 1); else if (pd > 0) add("HANGING_MAN", -1); else add("LOWER_WICK", 0); }
    if (up >= 0.55 && lo <= 0.2 && body > 0.1) { if (pd < 0) add("INVERTED_HAMMER", 1); else if (pd > 0) add("SHOOTING_STAR", -1); else add("UPPER_WICK", 0); }
    if (p) {
      if (green && p.close < p.open && b.open <= p.close && b.close >= p.open) add("BULLISH_ENGULFING", 1);
      if (red && p.close > p.open && b.open >= p.close && b.close <= p.open) add("BEARISH_ENGULFING", -1);
      if (b.high <= p.high && b.low >= p.low) add("INSIDE", 0);
      if (b.high > p.high && b.low < p.low) add("OUTSIDE", green ? 1 : red ? -1 : 0);
    }
    if (t >= 4) {
      var F = bars[t - 2], Sb = bars[t - 1], T = b, qf = F.high - F.low, qt = T.high - T.low, bf = Math.abs(F.close - F.open), bt = Math.abs(T.close - T.open), bs = Math.abs(Sb.close - Sb.open);
      if (qf > 0 && qt > 0 && bf >= 0.6 * qf && bt >= 0.6 * qt && bs <= 0.35 * bf) {
        var pdF = priorDirection(bars, t - 2), mid = (F.open + F.close) / 2;
        if (pdF < 0 && F.close < F.open && T.close > T.open && T.close > mid && Math.max(Sb.open, Sb.close) <= F.close) add("MORNING_STAR", 1);
        if (pdF > 0 && F.close > F.open && T.close < T.open && T.close < mid && Math.min(Sb.open, Sb.close) >= F.close) add("EVENING_STAR", -1);
      }
    }
    if (t >= 6) {
      var F5 = bars[t - 4], Ms = [bars[t - 3], bars[t - 2], bars[t - 1]], T5 = b, qf5 = F5.high - F5.low, qt5 = T5.high - T5.low, bf5 = Math.abs(F5.close - F5.open), bt5 = Math.abs(T5.close - T5.open);
      if (qf5 > 0 && qt5 > 0 && bf5 >= 0.6 * qf5 && bt5 >= 0.6 * qt5 && Ms.every(function (m) { return m.high <= F5.high && m.low >= F5.low && Math.abs(m.close - m.open) < 0.5 * bf5; })) {
        var pd5 = priorDirection(bars, t - 4), redM = Ms.filter(function (m) { return m.close < m.open; }).length, greenM = Ms.filter(function (m) { return m.close > m.open; }).length;
        if (redM >= 2 && pd5 > 0 && F5.close > F5.open && T5.close > T5.open && T5.close > F5.high) add("RISING_THREE_METHODS", 1);
        if (greenM >= 2 && pd5 < 0 && F5.close < F5.open && T5.close < T5.open && T5.close < F5.low) add("FALLING_THREE_METHODS", -1);
      }
    }
    return out;
  }
  function candleGeometry(bars, ind, i) {
    var b = bars[i], q = b.high - b.low, body = Math.abs(b.close - b.open), atr = ind.ATR[i];
    var r5 = [], r10 = []; for (var j = i - 1; j >= 0 && r10.length < 10; j--) { var rr = bars[j].high - bars[j].low; if (r5.length < 5) r5.push(rr); r10.push(rr); }
    var m5 = r5.length ? mean(r5) : 0, m10 = r10.length ? mean(r10) : 0;
    return { date: b.date, volume: b.volume, open: b.open, high: b.high, low: b.low, close: b.close, body: body, range: q, upper_wick: b.high - Math.max(b.open, b.close), lower_wick: Math.min(b.open, b.close) - b.low,
      body_fraction: q ? body / q : 0, upper_fraction: q ? (b.high - Math.max(b.open, b.close)) / q : 0, lower_fraction: q ? (Math.min(b.open, b.close) - b.low) / q : 0,
      open_location: q ? (b.open - b.low) / q : 0.5, close_location: q ? (b.close - b.low) / q : 0.5, range_atr: atr ? q / atr : null, body_atr: atr ? body / atr : null, rvol: ind.RVOL[i],
      range_relative_5: m5 ? q / m5 : null, range_relative_10: m10 ? q / m10 : null, patterns: detectPatterns(bars, i) };
  }
  function analyzePriceAction(bars, ind, levels, ma, pullback, trend, extension, candles, t) {
    var atr = ind.ATR[t], b = bars[t], rv = ind.RVOL[t];
    var lastG = candleGeometry(bars, ind, t), recent = []; for (var i = Math.max(0, t - 4); i <= t; i++) recent.push(candleGeometry(bars, ind, i));
    // ניקוד תבניות
    var pats = lastG.patterns.map(function (pt) {
      var score = 20, dir = pt.direction, span = PAT_SPAN[pt.code] || 1, win = bars.slice(t - span + 1, t + 1);
      var zone = dir >= 0 ? levels.support : levels.resistance, ext = dir >= 0 ? minArr(win.map(function (x) { return x.low; })) : maxArr(win.map(function (x) { return x.high; }));
      var near = !!zone && ext >= zone.low - 0.75 * atr && ext <= zone.high + 0.75 * atr;
      var reasons = ["זוהה מבנה נר מתאים; צורת הנר לבדה היא ראיה חלשה", "גוף " + pct0(lastG.body_fraction) + "%, זנב תחתון " + pct0(lastG.lower_fraction) + "% וזנב עליון " + pct0(lastG.upper_fraction) + "% מהטווח"];
      if (dir !== 0 && near) { score += 25; reasons.push("קיצון התבנית סמוך ל" + (dir > 0 ? "אזור התמיכה" : "אזור ההתנגדות")); }
      if (dir !== 0 && ma.rows.some(function (r) { return Math.abs(ext - r.value) <= 0.75 * atr; })) { score += 10; reasons.push("קיצון התבנית סמוך לממוצע נע"); }
      if ((dir > 0 && pullback.active && (trend.state === "UP" || trend.state === "STRONG_UP")) || (dir < 0 && (trend.state === "DOWN" || trend.state === "STRONG_DOWN"))) { score += 10; reasons.push("התבנית מתיישבת עם כיוון המגמה הראשית"); }
      if ((dir > 0 && lastG.close_location >= 0.75) || (dir < 0 && lastG.close_location <= 0.25)) { score += 10; reasons.push("הסגירה בקצה הטווח לכיוון התבנית"); }
      if (dir !== 0 && near && zone && ((dir > 0 && b.close > zone.high) || (dir < 0 && b.close < zone.low))) { score += 10; reasons.push("הסגירה מעבר לאזור לכיוון התבנית"); }
      if (rv != null && rv >= 1.5) { score += 10; reasons.push("המחזור גבוה משמעותית מהממוצע"); }
      if (lastG.range_atr != null && lastG.range_atr >= 0.5 && lastG.range_atr <= 2) { score += 5; reasons.push("טווח הנר משמעותי ביחס לתנודתיות הרגילה"); }
      if (dir !== 0 && !near) score = Math.min(score, 50);
      if (dir > 0 && (extension.state === "EXTENDED" || extension.state === "VERY_EXTENDED")) score = Math.min(score, 45);
      return { code: pt.code, label: pt.label, direction: dir, strength: Math.min(100, score), reasons: reasons, near_level: near };
    });
    var strength = pats.length ? maxArr(pats.map(function (p) { return p.strength; })) : 0;
    // מעקב תבניות (10 נרות אחרונים)
    var tracking = [];
    for (i = Math.max(0, t - 9); i <= t; i++) {
      detectPatterns(bars, i).forEach(function (pt) {
        if (TRACKED.indexOf(pt.code) < 0) return;
        var span = PAT_SPAN[pt.code] || 1, win = bars.slice(Math.max(0, i - span + 1), i + 1);
        var tr = { code: pt.code, label: pt.label, detected_at: bars[i].date, high: maxArr(win.map(function (x) { return x.high; })), low: minArr(win.map(function (x) { return x.low; })), direction: pt.direction, state: "PENDING", confirmed_at: null, invalidated_at: null };
        for (var j = i + 1; j <= t; j++) {
          var c = bars[j].close;
          if (tr.direction === 0) { if (c > tr.high) tr.direction = 1; else if (c < tr.low) tr.direction = -1; else { if (tr.state === "PENDING" && j - i > 5) { tr.state = "EXPIRED"; break; } continue; } }
          var inval = tr.direction > 0 ? c < tr.low : c > tr.high, conf = tr.direction > 0 ? c > tr.high : c < tr.low;
          if (inval) { tr.state = "INVALIDATED"; tr.invalidated_at = bars[j].date; break; }
          if (tr.state === "PENDING" && j - i > 5) { tr.state = "EXPIRED"; break; }
          if (tr.state === "PENDING" && conf) { tr.state = "CONFIRMED"; tr.confirmed_at = bars[j].date; }
        }
        var ex = tr.label + " מ־" + tr.detected_at + ": ";
        if (tr.state === "PENDING") ex += "ממתינה לאישור. " + (tr.direction === 0 ? "ממתינים לסגירה מחוץ לטווח " + fmt2(tr.low) + "–" + fmt2(tr.high) + ", שתגדיר את כיוון האישור" : "נדרשת סגירה " + (tr.direction > 0 ? "מעל " + fmt2(tr.high) : "מתחת ל־" + fmt2(tr.low)) + " לאישור");
        else if (tr.state === "CONFIRMED") ex += "אושרה בסגירה " + (tr.direction > 0 ? "מעל " + fmt2(tr.high) : "מתחת ל־" + fmt2(tr.low)) + " בתאריך " + tr.confirmed_at;
        else if (tr.state === "INVALIDATED") ex += "בוטלה בסגירה בצד הנגדי בתאריך " + tr.invalidated_at;
        else ex += "פג תוקפה — לא התקבל אישור בתוך 5 נרות";
        tr.explanation = ex; tracking.push(tr);
      });
    }
    // רצף 5 נרות
    var seq = { reasons: [], support_rejections: 0 }, w5 = bars.slice(Math.max(0, t - 4), t + 1);
    var downV = []; for (i = 1; i < w5.length; i++) if (w5[i].close < w5[i - 1].close) downV.push(w5[i].volume);
    if (downV.length >= 2 && downV.every(function (v, k) { return k === 0 || v < downV[k - 1]; })) seq.reasons.push("מחזורי ימי הירידה הולכים וקטנים");
    var ranges = w5.map(function (x) { return x.high - x.low; });
    var contracting = false, expanding = false;
    if (ranges.length >= 4) { contracting = mean(ranges.slice(-2)) < 0.8 * mean(ranges.slice(0, -2)); expanding = last(ranges) > mean(ranges.slice(0, -1)) / 0.8; }
    if (contracting) seq.reasons.push("טווחי הנרות מצטמצמים — התכנסות לאחר התנועה");
    if (expanding) seq.reasons.push("טווח הנר האחרון מתרחב ביחס לנרות הקודמים");
    if (w5.length >= 3 && w5[w5.length - 1].low > w5[w5.length - 2].low && w5[w5.length - 2].low > w5[w5.length - 3].low) seq.reasons.push("שלושה שפלים עולים ברצף — הקונים נכנסים גבוה יותר");
    if (levels.support) w5.forEach(function (x) { if (x.low >= levels.support.low - 0.15 * atr && x.low <= levels.support.high && x.close > levels.support.high) seq.support_rejections++; });
    if (seq.support_rejections >= 2) seq.reasons.push("האזור נדחה " + seq.support_rejections + " פעמים מלמטה — תמיכה פעילה");
    if (candles.strong_green && t > 0 && bars[t - 1].close < bars[t - 1].open) seq.reasons.push("נר ירוק חזק אחרי נר אדום — חזרת קונים");
    if (b.close < b.open && Math.abs(b.close - b.open) >= 0.6 * atr && rv != null && rv >= 1.5) seq.reasons.push("נר אדום רחב במחזור גבוה — לחץ מכירות");
    if (candles.above_previous_high) seq.reasons.push("הסגירה מעל שיא הנר הקודם מספקת אישור מחיר קצר טווח");
    // הסבר
    var ex = (b.close > b.open ? "נר ירוק" : b.close < b.open ? "נר אדום" : "נר ללא שינוי") + "; הגוף מהווה " + pct0(lastG.body_fraction) + "% מהטווח והסגירה נמצאת בגובה " + pct0(lastG.close_location) + "% מהשפל היומי.";
    if (pats.length) ex += " זוהתה " + pats.map(function (p) { return p.label; }).join(", ") + ", בעוצמת ראיות " + strength + "/100.";
    if (rv != null) ex += rv >= 1.5 ? " המחזור גבוה משמעותית מהממוצע." : rv > 1 ? " המחזור גבוה מהממוצע." : " המחזור נמוך מהממוצע.";
    if (contracting) ex += " טווחי הנרות מצטמצמים — התכנסות לאחר התנועה."; else if (expanding) ex += " טווח הנר האחרון מתרחב ביחס לנרות הקודמים.";
    ex += " הנר מסייע להערכת התזמון ואינו משנה לבדו את המגמה הראשית.";
    return { last: lastG, recent: recent, patterns: pats, strength: strength, tracking: tracking, sequence: seq, explanation: ex };
  }

  /* ───────── 6.5 החלפת תפקידים ───────── */
  function roleChanges(bars, ind, primaryStructure, t) {
    var events = [];
    primaryStructure.swings.forEach(function (p) {
      var a = 0.35 * p.atr, buf = 0.1 * p.atr, z = { low: p.price - a, high: p.price + a }, isHigh = p.kind === "HIGH";
      var ev = { low: z.low, high: z.high, known_at: p.confirmed_at, broken_at: null, retested_at: null, confirmed_at: null, invalidated_at: null, direction: isHigh ? "RESISTANCE_TO_SUPPORT" : "SUPPORT_TO_RESISTANCE", state: null, broken_index: null, buf: buf };
      var outside = function (c) { return isHigh ? c > z.high + buf : c < z.low - buf; }, invalid = function (c) { return isHigh ? c < z.low - buf : c > z.high + buf; };
      var run = 0, i;
      for (i = p.confirmed_index + 1; i <= t; i++) { if (outside(bars[i].close)) { run++; if (run >= 2) { ev.state = "BROKEN"; ev.broken_at = bars[i].date; ev.broken_index = i; break; } } else run = 0; }
      if (!ev.state) return;
      for (i = ev.broken_index + 1; i <= t; i++) {
        var c = bars[i].close;
        if (invalid(c)) { ev.state = "INVALIDATED"; ev.invalidated_at = bars[i].date; break; }
        var touch = bars[i].low <= z.high && bars[i].high >= z.low;
        if (ev.state === "BROKEN" && touch) { ev.state = "RETESTING"; ev.retested_at = bars[i].date; }
        if (ev.state === "RETESTING" && outside(c)) { ev.state = "CONFIRMED"; ev.confirmed_at = bars[i].date; }
      }
      if (t - ev.broken_index < 60) events.push(ev);
    });
    events.sort(function (a, b) { return b.broken_index - a.broken_index; });
    var chosen = [];
    events.forEach(function (e) { if (!chosen.some(function (c) { return e.low <= c.high && e.high >= c.low; })) chosen.push(e); });
    var C = ind.C[t];
    chosen.sort(function (a, b) { return Math.abs((a.low + a.high) / 2 - C) - Math.abs((b.low + b.high) / 2 - C); });
    return chosen.slice(0, 2).map(function (e) {
      var isHigh = e.direction === "RESISTANCE_TO_SUPPORT", src = isHigh ? "התנגדות" : "תמיכה", dst = isHigh ? "תמיכה" : "התנגדות";
      var DESC = { BROKEN: "הרמה נפרצה בשתי סגירות; ממתינים לבדיקה חוזרת", RETESTING: "התקבלה בדיקה חוזרת; ממתינים לסגירה בצד החדש", CONFIRMED: "הבדיקה החוזרת אישרה תפקיד של " + dst, INVALIDATED: "המחיר נסגר שוב בצד המקורי; החלפת התפקיד בוטלה" };
      var txt = src + " → " + dst + " באזור " + fmt2(e.low) + "–" + fmt2(e.high) + ": " + DESC[e.state] + ". הרמה הייתה ידועה מ־" + e.known_at + "; הפריצה אושרה ב־" + e.broken_at;
      if (e.retested_at) txt += "; בדיקה חוזרת: " + e.retested_at;
      if (e.confirmed_at) txt += "; אישור התפקיד החדש: " + e.confirmed_at;
      if (e.invalidated_at) txt += "; ביטול: " + e.invalidated_at;
      if (e.state === "BROKEN" || e.state === "RETESTING") txt += "; לאחר נגיעה באזור נדרשת סגירה " + (isHigh ? "מעל " + fmt2(e.high + e.buf) : "מתחת " + fmt2(e.low - e.buf)) + " לאישור התפקיד החדש";
      return { low: e.low, high: e.high, known_at: e.known_at, broken_at: e.broken_at, retested_at: e.retested_at, confirmed_at: e.confirmed_at, invalidated_at: e.invalidated_at, direction: e.direction, state: e.state, explanation: txt };
    });
  }

  /* ───────── 5. מאזן הראיות ───────── */
  function confluence(trend, entry, volume, pullback, cci, stoch, macd, levels, extension) {
    var rows = [];
    var up = trend.state === "UP" || trend.state === "STRONG_UP";
    rows.push(up ? { group: "structure", status: "SUPPORTS", text: "המגמה הראשית עולה; מבנה המחיר והממוצעים נשקלים יחד" } : ["DOWN", "STRONG_DOWN", "DAMAGED", "AT_RISK"].indexOf(trend.state) >= 0 ? { group: "structure", status: "CONTRADICTS", text: "המבנה הראשי יורד או בסיכון" } : { group: "structure", status: "MISSING", text: "המגמה הראשית אינה נותנת תמיכה ברורה לכניסה" });
    var loc = [], ext = extension.state === "EXTENDED" || extension.state === "VERY_EXTENDED";
    if (levels.near_support) loc.push("המחיר סמוך לאזור תמיכה");
    if (entry.near_resistance) loc.push("התנגדות " + fmt2(levels.resistance.low) + "–" + fmt2(levels.resistance.high) + " מגבילה את מרווח העלייה");
    if (ext) loc.push("המחיר מתוח ביחס לממוצעים");
    rows.push({ group: "location", status: (entry.near_resistance || ext) ? "CONTRADICTS" : levels.near_support ? "SUPPORTS" : "MISSING", text: loc.length ? loc.join("; ") : "המחיר אינו קרוב לתמיכה מזוהה" });
    rows.push(entry.price_confirmed ? { group: "price", status: "SUPPORTS", text: "התקבל אישור מחיר לקנייה; הנר והתבנית אינם נספרים כאישורים עצמאיים נוספים" } : { group: "price", status: "MISSING", text: "טרם התקבל אישור מחיר לקנייה לפי הכללים הקיימים; זיהוי תבנית לבדו אינו מחליף אותו" });
    rows.push(volume.unavailable ? { group: "volume", status: "MISSING", text: "נתוני המחזור חסרים" } : volume.heavy ? { group: "volume", status: "CONTRADICTS", text: "מחזור מוגבר בירידות מצביע על לחץ מכירות" } : volume.returning ? { group: "volume", status: "SUPPORTS", text: "המחזור מתרחב בעלייה" } : (pullback.active && volume.quiet) ? { group: "volume", status: "SUPPORTS", text: "המחזור נחלש במהלך התיקון" } : { group: "volume", status: "MISSING", text: "המחזור אינו מספק חיזוק נוסף; אין בכך קביעה שהמהלך ייכשל" });
    var flags = [cci.rising, stoch.rising, macd.improving], n = flags.filter(Boolean).length;
    rows.push(n === 3 ? { group: "momentum", status: "SUPPORTS", text: "CCI, סטוקסטיק ו־MACD מצביעים יחד על שיפור במומנטום" } : n === 0 ? { group: "momentum", status: "CONTRADICTS", text: "לא מזוהה שיפור באף אחד משלושת מדדי המומנטום" } : { group: "momentum", status: "MISSING", text: "מדדי המומנטום מעורבים; זהו חיזוק חלקי שאינו מבטל אישור מחיר שהתקבל" });
    var pick = function (s) { return rows.filter(function (r) { return r.status === s; }).map(function (r) { return r.text; }); };
    return { rows: rows, supports: pick("SUPPORTS"), contradicts: pick("CONTRADICTS"), missing: pick("MISSING"), note: "כל משפחת ראיות מופיעה פעם אחת. זהו הסבר, ללא ציון נוסף או הסתברות הצלחה; אין דרישה שכל המשפחות יהיו חיוביות יחד." };
  }

  /* ───────── 7. סיכום ───────── */
  function zoneText(z) { return z ? "סביב " + fmt2(z.low) + "–" + fmt2(z.high) : "לא זוהה אזור ברור"; }
  function buildSummary(action, trend, entry, levels, pstruct, provisional, provisionalConfirmed) {
    var sup = levels.support, res = levels.resistance, s1, s2;
    if (provisional && provisionalConfirmed) s1 = "תנאי המחיר לקנייה מתקיימים זמנית: נר ירוק מעל הגבוה הקודם באזור תמיכה";
    else if (entry.price_confirmed) s1 = "התקבל אישור מחיר לקנייה: נר ירוק מעל הגבוה הקודם באזור תמיכה";
    else s1 = ACTION_HE[action] + "; " + trend.label;
    var confirmed = provisional ? provisionalConfirmed : entry.price_confirmed;
    if (confirmed && res) s2 = "התנגדות " + zoneText(res) + " עלולה להגביל את המשך העלייה";
    else if (confirmed) s2 = "יש לעקוב אחר המשכיות ושמירה על התמיכה";
    else if (trend.state === "DAMAGED" || trend.state === "AT_RISK" || pstruct.broken) s2 = "נדרשת התייצבות ובנייה מחדש של תמיכה לפני בחינת כניסה" + (sup ? "; התמיכה הקרובה " + zoneText(sup) : "");
    else if (action === "DO_NOT_CHASE" || action === "WAIT_PULLBACK") s2 = "ממתינים להתקרבות לתמיכה ולסימני חזרת קונים" + (sup ? " " + zoneText(sup) : "");
    else if (entry.near_resistance && res) s2 = "ממתינים להתבססות מעל ההתנגדות ב־" + fmt2(res.high) + " או לתיקון לתמיכה";
    else if (entry.candidate && entry.entry != null) s2 = "כניסה אפשרית מעל " + fmt2(entry.entry) + ", בתנאי שהמחזור תומך" + (res ? "; התנגדות " + zoneText(res) + " מגבילה את מרווח העלייה" : "");
    else s2 = "נדרשים שמירה על תמיכה ונר חיובי עם סגירה חזקה או מעל הגבוה הקודם" + (sup ? "; התמיכה " + zoneText(sup) : "");
    var out = s1 + ". " + s2 + ".";
    if (provisional) out += " נר מתהווה — האישור זמני עד הסגירה.";
    return out;
  }

  /* ───────── תצוגה ───────── */
  var SWING_HE = { HH: "שיא גבוה יותר", LH: "שיא נמוך יותר", EH: "שיא שווה", HL: "שפל גבוה יותר", LL: "שפל נמוך יותר", EL: "שפל שווה", H: "שיא ראשון", L: "שפל ראשון" };
  var SCORE_HE = [["trend", "איכות המגמה"], ["momentum", "עוצמת המומנטום"], ["pullback", "איכות התיקון"], ["support", "איכות אזור התמיכה"], ["entry", "איכות נקודת הכניסה"], ["extension", "מתיחות המחיר"], ["volume", "איכות המחזורים"]];
  function cciText(c) { return { RECOVERED: "CCI התאושש מאזור מכירת-יתר", TURNING_UP: "CCI מתהפך למעלה", FALLING: "CCI יורד", VERY_LOW: "CCI נמוך מאוד", LOW: "CCI נמוך", VERY_HIGH: "CCI גבוה מאוד", HIGH: "CCI גבוה", RISING: "CCI עולה", STABLE: "CCI יציב" }[c.state]; }
  function stochText(s) { return { RECOVERED: "הסטוקסטיק התאושש מאזור מכירת-יתר", TURNING_UP: "הסטוקסטיק מתהפך למעלה", FALLING: "הסטוקסטיק עדיין יורד", VERY_LOW: "הסטוקסטיק נמוך מאוד", LOW: "הסטוקסטיק נמוך", VERY_HIGH: "הסטוקסטיק גבוה מאוד", HIGH: "הסטוקסטיק גבוה", RISING: "הסטוקסטיק עולה", STABLE: "הסטוקסטיק יציב", CROSS_UP: "הסטוקסטיק חצה את קו האיתות כלפי מעלה" }[s.state]; }
  function macdText(m) { return { IMPROVING: "ה־MACD משתפר שלושה ימים ברצף", WEAKENING: "ה־MACD נחלש שלושה ימים ברצף", SUPPORTIVE: "ה־MACD חיובי ומעל קו האיתות", POSITIVE: "ה־MACD חיובי, אך נמצא מתחת לקו האיתות", VERY_NEGATIVE: "ה־MACD שלילי מאוד ביחס לתנודתיות", NEGATIVE: "ה־MACD שלילי", NEUTRAL: "ה־MACD ניטרלי" }[m.state]; }
  function presentation(r, ctx) {
    var e = r.entry, lv = r.levels, sup = lv.support, res = lv.resistance, c = r.candles, ind = ctx.ind, t = ind.N - 1, rv = ind.RVOL[t];
    var pos = [], miss = [], alts = [];
    if (c.above_previous_high) pos.push("הסגירה כבר עברה את השיא של הנר הקודם");
    if (c.positive && c.strong_close) pos.push("הנר חיובי ונסגר ברבע העליון של הטווח");
    if (r.cci.rising) pos.push("CCI עולה"); else miss.push("CCI אינו עולה; אישור אפשרי הוא עלייה של לפחות 5 נקודות מהיום הקודם");
    if (r.stochastic.rising) pos.push("הסטוקסטיק עולה");
    if (r.volume.returning) pos.push("המחזור חוזר בעלייה"); else if (rv != null) miss.push("מחזור היום האחרון הוא פי " + fmt2(rv) + " מהממוצע. אישור נוסף יהיה יום עלייה במחזור של לפחות פי 1.10 מממוצע 20 הימים הקודמים");
    if (r.macd.improving) pos.push("ה־MACD משתפר שלושה ימים ברצף"); else miss.push("אישור אפשרי נוסף: שיפור ב־MACD במשך 3 ימי מסחר רצופים; אין חובה לחצייה חיובית");
    if (!(c.positive && c.strong_close) && !c.above_previous_high) miss.push("עדיין חסר נר חיובי עם סגירה ב־25% העליונים של הטווח היומי, או סגירה מעל שיא הנר הקודם");
    else if (!(c.positive && c.strong_close)) miss.push("עדיין חסר נר חיובי עם סגירה ב־25% העליונים של הטווח היומי, או סגירה מעל שיא הנר הקודם");
    if (sup) alts.push("אפשרות למעקב: התייצבות באזור התמיכה " + zoneText(sup) + ", בלי סגירה מתחת ל־" + fmt2(sup.low) + ", ולאחריה נר חיובי שנסגר סמוך לגבוה היומי. זו בדיקה של התנהגות המחיר באזור, לא הוראת קנייה במחיר נתון");
    if (r.breakout.zone) alts.push("לבדיקת הפריצה: שמירה על האזור " + fmt2(r.breakout.zone.low) + "–" + fmt2(r.breakout.zone.high) + " וסגירה מעל גבולו העליון יחזקו את ההחזקה; כישלון מחייב ראיות נוספות מעבר לנגיעה באזור");
    alts.push("אישור הנר יתחזק בסגירה מעל השיא האחרון " + fmt2(c.high) + " תוך שמירה על התמיכה; נדרש גם לבחון את יתר תנאי הכניסה");
    var nextStep = e.price_confirmed ? "התקבל אישור מחיר; יש לבחון את גודל הפוזיציה מול רמת הביטול ואת ההתנגדות הקרובה" : e.candidate ? "כניסה אפשרית מעל " + fmt2(e.entry) + " עם ביטול מתחת ל־" + fmt2(e.invalidation) : r.decision.action === "DO_NOT_CHASE" || r.decision.action === "WAIT_PULLBACK" ? "להמתין לתיקון לעבר התמיכה ולסימני חזרת קונים לפני בחינת כניסה" : r.trend.state === "DAMAGED" || r.trend.state === "AT_RISK" ? "להמתין להתייצבות ולבנייה מחדש של תמיכה" : "כדי לשקול כניסה נדרשים שמירה על תמיכה ונר חיובי, לצד שיפור נוסף במחיר או במחזור";
    var risk = e.entry != null ? "כניסה " + fmt2(e.entry) + ", ביטול " + fmt2(e.invalidation) + ", מרחק סיכון " + fmt2(e.risk_distance) + " (" + fmt2(e.risk_percent) + "%)" : "אין כרגע מחיר כניסה ורמת ביטול מבוססים להצגה";
    var supDetails = sup ? ["מקור האזור: " + sup.sources.join(", ")].concat(sup.context.details) : ["לא זוהה אזור תמיכה"];
    var locItems = [r.extension.label];
    if (sup) locItems.push("התמיכה הקרובה " + zoneText(sup) + "; " + sup.context.quality + "; " + sup.context.details[sup.context.support_reactions.length ? 2 : 1]);
    if (res) locItems.push("התנגדות קרובה " + zoneText(res));
    var volItems = [r.volume.unavailable ? "נתוני המחזור חסרים" : r.volume.heavy ? "המחזור גדל בירידות, דבר המעיד על לחץ מכירות" : r.volume.quiet ? "המחזור נחלש בתיקון — סימן בריא" : r.volume.returning ? "המחזור חוזר בעלייה" : "המחזור אינו נותן חיזוק מיוחד לכיוון"];
    var candleItems = [];
    if (c.doji) candleItems.push("נר עם גוף קטן המעיד על חוסר הכרעה");
    if (c.strong_green) candleItems.push("נר ירוק חזק עם גוף רחב"); if (c.strong_red) candleItems.push("נר אדום חזק עם גוף רחב");
    if (c.lower_tail) candleItems.push("זנב תחתון ארוך — דחייה של מחירים נמוכים");
    if (c.above_previous_high) candleItems.push("סגירה מעל השיא של הנר הקודם");
    if (c.reversal) candleItems.push("נר היפוך: זנב תחתון ונר ירוק אחרי אדום");
    candleItems.push("רצף עליות: " + c.up_streak + "; רצף ירידות: " + c.down_streak);
    candleItems.push("משמעות הנרות נשקלת יחד עם המגמה, התמיכה והמחזור");
    var swings = r.market_structure.swings.map(function (p) { return { date: p.date, confirmed_at: p.confirmed_at, price: p.price, type: p.kind === "HIGH" ? "שיא" : "שפל", label: SWING_HE[p.label] || p.label }; });
    return {
      trend: r.trend.label, state: r.trend_hierarchy.short.label, action: ACTION_HE[r.decision.action], summary: r.technical_opinion,
      hierarchy: { primary: r.trend_hierarchy.primary.label, intermediate: r.trend_hierarchy.intermediate.label, short: r.trend_hierarchy.short.label },
      structure: { swings: swings, sequence: swings.map(function (s) { return s.label; }).join(" ← "), ma_order: ctx.ma.order_text, protected_low: r.market_structure.protected_low, ma_clusters: ctx.ma.zones.clusters },
      confirmation: { positive: pos, missing: miss, alternatives: alts, note: "לא כל הסימנים חייבים להתקיים יחד. שיפור במחיר ובמיקום הכניסה נשקל עם המחזור והאינדיקטורים; כל נר יומי סגור מחייב ניתוח מחדש." },
      scores: SCORE_HE.map(function (s) { return { key: s[0], label: s[1], value: r.scores[s[0]] }; }),
      indicators: [{ name: "CCI(5)", value: fmt2(r.cci.value), text: cciText(r.cci) }, { name: "Stochastic (15,5,3)", value: fmt2(r.stochastic.value) + " / " + fmt2(r.stochastic.d), text: stochText(r.stochastic) }, { name: "MACD", value: fmt2(r.macd.value) + " / " + fmt2(r.macd.signal) + " / " + fmt2(r.macd.histogram), text: macdText(r.macd) }],
      support: zoneText(sup), support_sources: sup ? sup.sources.join(", ") + " — " + sup.context.quality : "—", support_details: supDetails, resistance: zoneText(res), next_step: nextStep, risk: risk,
      evidence: [
        { title: "המגמה", items: r.trend.reasons }, { title: "מצב התיקון", items: r.pullback_quality.reasons }, { title: "מיקום המחיר", items: locItems }, { title: "מחזורים", items: volItems },
        { title: "המלצה ואיכות הכניסה", items: [ACTION_HE[r.decision.action], nextStep, risk] }, { title: "אזור התמיכה והתגובה אליו", items: supDetails }, { title: "הנרות בהקשר הגרף", items: candleItems },
        { title: "מבנה המחיר המשמעותי", items: r.market_structure.reasons }, { title: "המצב הבינוני", items: [r.trend_hierarchy.intermediate.label].concat(r.trend_hierarchy.intermediate.reasons) },
        { title: "המצב הקצר", items: r.trend_hierarchy.short.reasons }, { title: "הפריצה והבדיקה החוזרת", items: r.breakout.reasons.length ? r.breakout.reasons : ["לא זוהה אירוע פריצה ב־60 הנרות האחרונים"] },
        { title: "ניתוח הנרות", items: [r.price_action.explanation].concat(r.price_action.sequence.reasons) }]
    };
  }

  /* ───────── ניתוח מלא ───────── */
  var PARTIAL_MSG = "נר יומי מתהווה — טרם נסגר. כל הניתוח לתאריך זה זמני; אישורי מחיר, תבניות ושבירות טעונים בדיקה מחדש לאחר הסגירה. המחזור חלקי ואינו בר השוואה מלאה למחזור של יום שלם.";
  function validate(bars) {
    if (!bars || !bars.length) throw new Error("קלט ריק");
    for (var i = 0; i < bars.length; i++) {
      var b = bars[i];
      if (!(b.low <= Math.min(b.open, b.close) && Math.max(b.open, b.close) <= b.high) || !(b.low > 0) || !isFinite(b.high) || !(b.volume >= 0)) throw new Error("נר לא תקין בתאריך " + b.date);
      if (i && !(b.date > bars[i - 1].date)) throw new Error("תאריכים לא עולים: " + b.date);
    }
  }
  function stripStruct(s) { var o = {}; for (var k in s) if (k !== "all_points" && k !== "lookback") o[k] = s[k]; return o; }
  function stripMA(m) { var o = {}; for (var k in m) if (k !== "byKey" && k !== "order_text") o[k] = m[k]; return o; }
  function analyze(bars, opts) {
    opts = opts || {}; validate(bars);
    var symbol = opts.symbol || "", N = bars.length, t = N - 1, partial = !!(opts.is_partial || bars[t].is_partial);
    if (N < 40) return { symbol: symbol, as_of: bars[t].date, price: bars[t].close, status: "INSUFFICIENT_DATA", score: null, required_bars: 40, available_bars: N, is_provisional: partial, message: partial ? PARTIAL_MSG : null, strategy_version: "chart-price-action-v3" };
    var ind = computeIndicators(bars), C = ind.C[t], atr = ind.ATR[t];
    var ma = analyzeMA(bars, ind);
    var pStruct = classifyStructure(bars, ind, 3, 6, 252), iStruct = classifyStructure(bars, ind, 1.75, 4, 90);
    var pInteg = integrate(pStruct, ma, ind), iInteg = integrate(iStruct, ma, ind);
    var primary = primaryTrend(pStruct, ma, pInteg), intermediate = intermediateTrend(iStruct, iInteg, primary);
    var breakout = analyzeBreakout(bars, ind, iStruct, iInteg);
    var range10 = maxArr(ind.H.slice(Math.max(0, N - 10))) - minArr(ind.L.slice(Math.max(0, N - 10))), rangeAtr = atr ? range10 / atr : 0;
    var pstruct = { higher_high: pStruct.higher_high, higher_low: pStruct.higher_low, lower_high: pStruct.lower_high, lower_low: pStruct.lower_low, broken: pStruct.at_risk, breakout: breakout.state === "CONFIRMED" || breakout.state === "GAP_BREAKOUT", failed_breakout: breakout.state === "FAILED",
      prior_breakout: breakout.zone ? (breakout.zone.low + breakout.zone.high) / 2 : null, consolidating: rangeAtr <= 3, range_atr: rangeAtr, highs: pStruct.highs.slice(-5), lows: pStruct.lows.slice(-5),
      reasons: [pStruct.higher_high ? "השיאים המאושרים עולים" : pStruct.lower_high ? "השיאים המאושרים יורדים" : "השיאים המאושרים אינם עולים בבירור", pStruct.higher_low ? "השפלים המאושרים עולים" : pStruct.lower_low ? "השפלים המאושרים יורדים" : "השפלים המאושרים אינם עולים בבירור"] };
    var cci = oscillator(ind.CCI, t, { eps: 5, oversold: -100, overbought: 100, veryLow: -200, veryHigh: 200 });
    var stoch = oscillator(ind.K, t, { eps: 1, oversold: 20, overbought: 80, veryLow: 10, veryHigh: 90 });
    stoch.d = ind.D[t]; stoch.cross_up = ind.K[t - 1] != null && ind.D[t - 1] != null && ind.K[t] != null && ind.D[t] != null && ind.K[t - 1] <= ind.D[t - 1] && ind.K[t] > ind.D[t];
    if (stoch.cross_up) { stoch.state = "CROSS_UP"; stoch.score = 75; }
    var macd = analyzeMACD(ind, t), candles = candleFlags(bars, ind, t), extension = analyzeExtension(ind, ma, cci, stoch, candles, t);
    var pullback = detectPullback(bars, ind, primary.state, t), volume = analyzeVolume(bars, ind, pullback, t);
    var levels = analyzeLevels(bars, ind, ma, pStruct, breakout, t);
    var quality = pullbackQuality(pullback, pstruct, volume, levels, cci, stoch, macd, primary, candles);
    var recovery = supportRecoveryEvidence(bars, ind, levels, t);
    var entry = evaluateEntry(bars, ind, primary, quality, levels, candles, cci, stoch, macd, volume, extension, pstruct, pullback, recovery, t);
    var action = decideAction(primary, extension, quality, entry, pullback, candles, macd);
    var short = shortState(primary, pstruct, extension, pullback, candles, macd, ma, levels, quality, breakout);
    var pa = analyzePriceAction(bars, ind, levels, ma, pullback, primary, extension, candles, t);
    var scores = { trend: primary.score, momentum: W([{ v: cci.score, w: 30 }, { v: stoch.score, w: 30 }, { v: macd.score, w: 40 }]), pullback: quality.score, support: levels.support ? levels.support.score : null, entry: entry.score, extension: extension.score, volume: volume.score };
    var conf = confluence(primary, entry, volume, pullback, cci, stoch, macd, levels, extension);
    var roles = roleChanges(bars, ind, pStruct, t);
    // סיבות מצב קצר
    var shortReasons = breakout.state !== "NONE" ? breakout.reasons.slice() : [];
    if (short.base === "STRUCTURE_BREAK") shortReasons.push("המבנה הראשי נפגע");
    if (short.base === "EXTENDED") shortReasons.push("ציון המתיחות " + extension.score + " — המחיר רחוק מהממוצעים");
    if (pullback.active) shortReasons.push("המרחק מהשיא האחרון הוא " + fmt1(pullback.percent) + "%");
    if (ma.zones.support.length) shortReasons.push("המחיר בודק תמיכה סביב ממוצעים: " + ma.zones.support.map(function (k) { return MA_PERIOD[k] + " יום"; }).join(", "));
    if (short.base === "CONSOLIDATION") shortReasons.push("טווח 10 הנרות האחרונים הוא " + fmt1(rangeAtr) + " יחידות תנודתיות — התכנסות");
    if (quality.state === "HEALTHY") shortReasons.push("איכות התיקון " + quality.score + " — תיקון בריא");
    shortReasons.push(pa.explanation);
    var provisionalDecision = null, provisionalConfirmed = false;
    if (partial) {
      provisionalDecision = action; provisionalConfirmed = entry.price_confirmed;
      entry.price_confirmed = false; entry.candidate = false; entry.entry = null; entry.invalidation = null; entry.risk_distance = null; entry.risk_percent = null;
      action = "INTRADAY_PREVIEW";
      conf.rows = conf.rows.map(function (r) { return (r.group === "price" || r.group === "volume") ? { group: r.group, status: "MISSING", text: "נר ומחזור חלקיים — נדרשת סגירה לאישור" } : r; });
      conf.supports = conf.rows.filter(function (r) { return r.status === "SUPPORTS"; }).map(function (r) { return r.text; });
      conf.contradicts = conf.rows.filter(function (r) { return r.status === "CONTRADICTS"; }).map(function (r) { return r.text; });
      conf.missing = conf.rows.filter(function (r) { return r.status === "MISSING"; }).map(function (r) { return r.text; });
      conf.note = PARTIAL_MSG + " " + conf.note;
      var today = bars[t].date;
      pa.tracking.forEach(function (tr) { if ([tr.detected_at, tr.confirmed_at, tr.invalidated_at].indexOf(today) >= 0) { tr.is_provisional = true; tr.explanation = "זמני עד הסגירה: " + tr.explanation; } });
      roles.forEach(function (rc) { if ([rc.broken_at, rc.retested_at, rc.confirmed_at, rc.invalidated_at].indexOf(today) >= 0) { rc.is_provisional = true; rc.explanation = "זמני עד הסגירה: " + rc.explanation; } });
      if (breakout.state !== "NONE") { breakout.is_provisional = true; breakout.reasons.unshift(PARTIAL_MSG); }
    }
    var summary = buildSummary(provisionalDecision || action, primary, entry, levels, pstruct, partial, provisionalConfirmed);
    var tHier = { primary: { state: primary.state, label: primary.label, score: primary.score, reasons: primary.reasons, available_averages: primary.available_averages, components: primary.components },
      intermediate: { state: intermediate.state, label: intermediate.label, reasons: intermediate.reasons, structure: stripStruct(iStruct) },
      short: { state: short.state, label: short.label, reasons: shortReasons } };
    var result = {
      symbol: symbol, as_of: bars[t].date, price: C, strategy_version: "chart-price-action-v3", status: "ANALYZED", score: entry.score, scores: scores,
      indicators: { cci: ind.CCI[t], rsi: ind.RSI[t], stoch_k: ind.K[t], stoch_d: ind.D[t], macd: ind.MACD[t], macd_signal: ind.SIG[t], macd_histogram: ind.HIST[t], rvol: ind.RVOL[t], average_volume: ind.AVGV[t] },
      moving_averages: ma.rows, atr: atr,
      trend: { state: primary.state, label: primary.label, score: primary.score, reasons: primary.reasons, available_averages: primary.available_averages, components: primary.components },
      structure: pstruct, extension: extension, pullback: pullback, pullback_quality: quality, levels: levels,
      cci: Object.assign({}, cci, { support_recovery: entry.recovery_evidence }), stochastic: stoch, macd: macd, volume: volume, candles: candles, entry: entry,
      decision: { action: action, state: short.state, label: ACTION_HE[action], provisional_decision: provisionalDecision },
      confirmed_highs: pStruct.highs.slice(-5), confirmed_lows: pStruct.lows.slice(-5), trend_hierarchy: tHier, market_structure: stripStruct(pStruct), ma_structure: stripMA(ma), confluence: conf, role_changes: roles,
      breakout: breakout, price_action: pa, technical_opinion: summary, is_provisional: partial, message: partial ? PARTIAL_MSG : null, bars_used: N
    };
    result.presentation = presentation(result, { ind: ind, ma: ma });
    result.series = { ATR: ind.ATR, CCI: ind.CCI, K: ind.K, D: ind.D, MACD: ind.MACD, SIG: ind.SIG, HIST: ind.HIST, RSI: ind.RSI, RVOL: ind.RVOL, ma: ind.ma };
    return result;
  }

  return { analyze: analyze, computeIndicators: computeIndicators, scanSwings: scanSwings, classifyStructure: classifyStructure, mean: mean, R: R, S: S, W: W, fmt2: fmt2, MA_ORDER: MA_ORDER, labels: { action: ACTION_HE, primary: PRIMARY_HE, intermediate: INTER_HE, short: SHORT_HE, breakout: BREAKOUT_HE, pattern: PAT_HE, extension: EXT_HE, quality: PQ_HE } };
});
