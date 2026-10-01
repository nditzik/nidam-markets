#!/usr/bin/env node
/* build_picks.js — "הנבחרות" (30.9.2026, אישור איציק אחרי מוקאפ)
 *
 * המשפך: מתוך המאגר שכבר באתר (המועמדים של IBKR + סריקות המומנטום) נבחרות רק
 * המניות שהמנוע הטכני (assets/ta_engine.js, המפרט chart-price-action-v3) נותן
 * להן בסגירה האחרונה "התקבל אישור מחיר לקנייה" (PRICE_CONFIRMED_BUY).
 * "כניסה אפשרית" לא מספיק — נבדק לאחור (30.9.2026, 17 מניות, שנה): נותן את
 * הבסיס בלבד, בעוד "אישור מחיר" נותן פי 2 ב-20 יום (+11.8% מול +6.0%).
 *
 * פסילות: מדווחת תוך 7 ימים · פחות מ-220 נרות · שלושת האישורים הקודמים של
 * המניה נכשלו כולם (10 ימים אחרי) · תעודות סל ומדדים.
 *
 * שער השוק (מד הדשבורד): הגנה = עד 3 פוזיציות וחצי גודל · ניטרלי = עד 4 ·
 * ירוק = עד 5. השער לא מסנן מניות, רק אומר כמה מותר.
 *
 * פלט:
 *   data/picks.json         — המהדורה של היום (תאריך = הנר הסגור האחרון), כולל
 *                             60 סגירות לגרף, רמות, מקורות, והרקורד של כל מניה.
 *   data/picks_ledger.json  — יומן הכנות: כל מהדורה עם מחיר הכניסה (סגירת יום
 *                             המהדורה), ומה קרה 5/10/20 ימי מסחר אחרי — באחוזים
 *                             וגם מול SPY. מניה שחוזרת יום אחרי יום נספרת פעם
 *                             אחת, מהמהדורה הראשונה. גם מטמון הרקורד ההיסטורי
 *                             של כל מניה (hist), מתרענן אחת לשבוע.
 *
 * רץ בכל מחזור של update.yml אחרי fetch_bars: המהדורה נבנית רק כשתאריך הנרות
 * מתקדם; היומן מתעדכן בכל ריצה (זול). כשל = הקבצים הקיימים נשארים.
 * ללא רשת — הכל מקבצי הריפו. בדיקה מקומית: node scripts/build_picks.js
 */
"use strict";
const fs = require("fs");
const path = require("path");
const ROOT = path.join(__dirname, "..");
const T = require(path.join(ROOT, "assets", "ta_engine.js"));

const BARS_DIR = path.join(ROOT, "data", "bars");
const OUT = path.join(ROOT, "data", "picks.json");
const LEDGER = path.join(ROOT, "data", "picks_ledger.json");
const HORIZONS = [5, 10, 20];
const SKIP = new Set(["SPY", "QQQ", "IWM", "XLK", "XLV", "XLF", "XLE", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]);
const HIST_TTL_DAYS = 7;

// פורט של passesBase (app.js) / passes_base (fetch_momentum.py) / passesBaseFilter בדשבורד המומנטום.
// momentum.json מחזיק גם מניות שנכשלו בסינון (2+ סיגנלים נשמרים תמיד), והמאגר של הנבחרות לקח
// את כולן — PUSA (‏Weak, ‏24% Sell, אלפא שלילית) ו-SCSC (מחזור 237K) נכנסו ב-30.9 (1.10.2026, איציק).
function passesBase(d) {
  const num = v => { const x = parseFloat(v); return isNaN(x) ? 0 : x; };
  const vol = num(d.vol), px = num(d.price), ma20 = num(d.ma20), rsi = num(d.rel_str);
  const a = d.wtd_alpha == null ? NaN : parseFloat(d.wtd_alpha);
  if (vol <= 0 || px <= 0 || isNaN(a) || a <= 0 || ma20 <= 0 || rsi <= 0) return false;
  if (vol < 750000) return false;
  if (d.w52_chg != null && d.w52_chg !== "") {
    const w = parseFloat(d.w52_chg), st = (d.strength || "").toLowerCase();
    if (!isNaN(w) && a < w && !(st.includes("top") || st.includes("max") || st.includes("strong"))) return false;
  }
  const stoch = num(d.stoch), ma50 = num(d.ma50), ma100 = num(d.ma100);
  if (rsi > 72 && stoch > 82) return false;
  if (ma50 > 0 && ma100 > 0 && px < ma50 && px < ma100) return false;
  if (/weak/i.test(d.strength || "")) return false;
  if (/\bsell\b/i.test(d.opinion || "")) return false;
  return true;
}

function readJSON(p, dflt) {
  try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch (e) { return dflt; }
}
function loadBars(sym) {
  const d = readJSON(path.join(BARS_DIR, sym + ".json"), null);
  if (!d || !Array.isArray(d.bars)) return null;
  return d.bars.map(b => ({ date: b[0], open: b[1], high: b[2], low: b[3], close: b[4], volume: b[5] }));
}
function ilStamp() {
  const p = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Jerusalem", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false }).formatToParts(new Date());
  const g = t => p.find(x => x.type === t).value;
  return `${g("day")}/${g("month")}/${g("year")} ${g("hour")}:${g("minute")}`;
}
function grpOf(industry) {
  const s = String(industry || "").toLowerCase();
  if (/tech|software|semi|internet|computer|communic|electron|data|cloud|it serv/.test(s)) return "tech";
  if (/medic|pharm|bio|health|drug|hospital|dental/.test(s)) return "health";
  return "other";
}
function addDays(iso, n) { const d = new Date(iso + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }

/* ---- רקורד היסטורי של מניה: המנוע רץ על כל יום בעבר (walk-forward) ---- */
function history(sym, bars, spy) {
  const spyIdx = {}; spy.forEach((b, i) => { spyIdx[b.date] = i; });
  const ev = []; let last = null; const n = bars.length;
  for (let i = 220; i < n - 20; i++) {
    let r; try { r = T.analyze(bars.slice(0, i + 1), { symbol: sym }); } catch (e) { continue; }
    const a = r.decision.action;
    if (a === "PRICE_CONFIRMED_BUY" && a !== last) {
      const c = bars[i].close, si = spyIdx[bars[i].date];
      const f = {}; HORIZONS.forEach(h => { f[h] = +((bars[i + h].close / c - 1) * 100).toFixed(2); });
      const spy10 = (si != null && spy[si + 10]) ? +((spy[si + 10].close / spy[si].close - 1) * 100).toFixed(2) : null;
      let lo = Infinity; for (let k = 1; k <= 10; k++) lo = Math.min(lo, bars[i + k].low);
      ev.push({ date: bars[i].date, r5: f[5], r10: f[10], r20: f[20], spy10, mae: +((lo / c - 1) * 100).toFixed(1) });
    }
    last = a;
  }
  if (!ev.length) return { computedAt: new Date().toISOString().slice(0, 10), n: 0, events: [] };
  const w = ev.filter(e => e.r10 > 0).length;
  const mean = k => +(ev.reduce((s, e) => s + e[k], 0) / ev.length).toFixed(1);
  return { computedAt: new Date().toISOString().slice(0, 10), n: ev.length, win10: Math.round(w / ev.length * 100),
    avg5: mean("r5"), avg10: mean("r10"), avg20: mean("r20"), mae: mean("mae"), events: ev.slice(-12) };
}

function main() {
  const idx = readJSON(path.join(BARS_DIR, "index.json"), null);
  if (!idx || !idx.target) { console.log("[skip] picks: אין data/bars/index.json"); return 0; }
  // תאריך המהדורה = הנר הסגור האחרון של SPY (העוגן לכל היקום)
  const spy = loadBars("SPY");
  if (!spy || spy.length < 250) { console.log("[skip] picks: אין נרות SPY"); return 0; }
  const asOf = spy[spy.length - 1].date;
  const prev = readJSON(OUT, null);
  const ledger = readJSON(LEDGER, { editions: [], hist: {} });
  ledger.hist = ledger.hist || {}; ledger.editions = ledger.editions || [];

  // המהדורה של יום מסחר X נבנית רק כשגם המומנטום וגם המועמדים מבוססים על סגירת X (איציק,
  // 1.10.2026: "צריך את שני הקבצים ביחד"). עד אז נשארת המהדורה הקודמת, ו-picks.json מקבל
  // pending = מה עוד חסר (מוצג באתר). אחרי ששניהם הגיעו — בנייה מחדש כשהמאגר מתחלף (poolSig).
  const momDay = momentumDay(), candDay = candidatesDay();
  const waiting = [];
  if (momDay !== asOf) waiting.push("מומנטום");
  if (candDay !== asOf) waiting.push("מועמדים");
  const poolSig = poolSignature();
  if (waiting.length) {
    console.log(`[wait] picks: מהדורת ${asOf} ממתינה ל-${waiting.join(" + ")} (מומנטום ${momDay || "?"}, מועמדים ${candDay || "?"})`);
    if (prev) {
      const pend = { asOf, waiting };
      if (JSON.stringify(prev.pending || null) !== JSON.stringify(pend)) { prev.pending = pend; fs.writeFileSync(OUT, JSON.stringify(prev), "utf8"); }
    }
  } else if (!prev || prev.date !== asOf || prev.poolSig !== poolSig) {
    buildEdition(asOf, spy, ledger, idx, poolSig);
  } else {
    if (prev.pending) { delete prev.pending; fs.writeFileSync(OUT, JSON.stringify(prev), "utf8"); }
    console.log(`[nochange] picks: המהדורה של ${asOf} כבר קיימת (המאגר לא השתנה)`);
  }
  updateLedger(ledger, spy);
  ledger._meta = { updatedAt: ilStamp(), source: "build_picks" };
  fs.writeFileSync(LEDGER, JSON.stringify(ledger, null, 1), "utf8");
  return 0;
}

/* יום המסחר שעליו מבוססים קבצי המומנטום (התאריך בשם הקובץ, MM-DD-YYYY) — הישן מבין החמישה */
function momentumDay() {
  const mom = readJSON(path.join(ROOT, "data", "momentum.json"), {});
  const ds = Object.values((mom._meta && mom._meta.files) || {}).map(f => {
    const m = /(\d{2})-(\d{2})-(\d{4})\.csv$/.exec(f); return m ? `${m[3]}-${m[1]}-${m[2]}` : null;
  }).filter(Boolean).sort();
  return ds.length ? ds[0] : null;
}

/* יום המסחר שעליו מבוססים המועמדים — מהתוכן, לא מהשדה date (הריצה של הבוקר והריצה של 23:41
   שתיהן נושאות את תאריך היום, אבל מבוססות על סגירות שונות). מחיר הכניסה של מועמד = סגירת היום
   שעליו הוא נסרק → הצבעה: לאיזה תאריך בנרות סגירה זהה למחיר הכניסה של רוב המועמדים. */
function candidatesDay() {
  const cand = readJSON(path.join(ROOT, "data", "candidates.json"), {});
  const votes = {};
  for (const c of (cand.candidates || []).slice(0, 25)) {
    const bars = loadBars(c.symbol);
    if (!bars || c.entry == null) continue;
    for (const b of bars.slice(-6)) if (Math.abs(b.close - c.entry) <= Math.max(0.005, c.entry * 0.0005)) { votes[b.date] = (votes[b.date] || 0) + 1; break; }
  }
  const best = Object.entries(votes).sort((a, b) => b[1] - a[1])[0];
  return best ? best[0] : null;
}

function poolSignature() {
  const mom = readJSON(path.join(ROOT, "data", "momentum.json"), {});
  const cand = readJSON(path.join(ROOT, "data", "candidates.json"), {});
  const files = (mom._meta && mom._meta.files) ? Object.values(mom._meta.files).sort().join(",") : "";
  // גם הטיקרים עצמם: סריקת בוקר שמחליפה את רשימת הערב יכולה לשמור על אותו תאריך ואותו מספר
  const syms = (cand.candidates || []).map(c => c.symbol).join(",");
  return "base1|" + files + "|" + (cand.date || "") + "|" + syms;
}

function buildEdition(asOf, spy, ledger, idx, poolSig) {
  const mom = readJSON(path.join(ROOT, "data", "momentum.json"), { stocks: [] });
  const cand = readJSON(path.join(ROOT, "data", "candidates.json"), { candidates: [] });
  const earn = readJSON(path.join(ROOT, "data", "earnings.json"), {});
  const ind = readJSON(path.join(ROOT, "data", "indices.json"), {});
  const mk = readJSON(path.join(ROOT, "data", "market.json"), {});
  const momBy = {}; (mom.stocks || []).forEach(s => { if (passesBase(s)) momBy[s.symbol] = s; });
  const candBy = {}; (cand.candidates || []).forEach(c => { candBy[c.symbol] = c; });
  const pool = Array.from(new Set(Object.keys(momBy).concat(Object.keys(candBy)))).filter(s => !SKIP.has(s)).sort();
  const earnWin = earn.window || {};
  const earnCut = addDays(asOf, 7);
  const today = new Date().toISOString().slice(0, 10);
  const spyIdx = {}; spy.forEach((b, i) => { spyIdx[b.date] = i; });

  const picks = [], excluded = []; let scanned = 0;
  for (const sym of pool) {
    const bars = loadBars(sym);
    if (!bars || bars.length < 220) continue;
    scanned++;
    let r; try { r = T.analyze(bars, { symbol: sym }); } catch (e) { continue; }
    if (r.decision.action !== "PRICE_CONFIRMED_BUY") continue;
    if (earnWin[sym] && earnWin[sym] <= earnCut) { excluded.push({ sym, reason: "מדווחת ב-" + earnWin[sym] }); continue; }
    // רקורד היסטורי (מטמון שבועי)
    let h = ledger.hist[sym];
    if (!h || !h.computedAt || addDays(h.computedAt, HIST_TTL_DAYS) < today) { h = history(sym, bars, spy); ledger.hist[sym] = h; }
    const last3 = (h.events || []).slice(-3);
    if (last3.length === 3 && last3.every(e => e.r10 <= 0)) { excluded.push({ sym, reason: "שלושת האישורים הקודמים נכשלו" }); continue; }
    const m = momBy[sym], c = candBy[sym];
    const sources = [];
    if (c) sources.push({ k: "cand", t: "מועמד #" + c.rank, sub: c.setup });
    if (m) sources.push({ k: "mom", t: "מומנטום", sub: (m.signals || []).map(sigHe).join(" · ") + (m.readiness != null ? " · מוכנות " + m.readiness : "") });
    const last = bars[bars.length - 1], before = bars[bars.length - 2];
    const vol20 = bars.slice(-21, -1).reduce((a, b) => a + b.volume, 0) / 20;
    picks.push({
      sym, name: (m && m.name) || "", industry: (m && m.industry) || "", grp: grpOf(m && m.industry),
      price: r.price, chg: +((last.close / before.close - 1) * 100).toFixed(2), rvol: vol20 ? +(last.volume / vol20).toFixed(1) : null,
      score: r.score, trend: r.trend.state, trendLabel: r.trend.label,
      bo: r.breakout && r.breakout.state, boLabel: r.breakout && r.breakout.label,
      pb: r.pullback_quality.state, pbLabel: r.pullback_quality.label, ext: r.extension.state,
      sup: r.levels.support && r.levels.support.mid, res: r.levels.resistance && r.levels.resistance.mid, atr: r.atr,
      entry: c ? +c.entry.toFixed(2) : null, stop: c ? +c.stop.toFixed(2) : null, target: c ? +c.target.toFixed(2) : null,
      sources, closes: bars.slice(-60).map(b => b.close),
      rec: h.n ? { n: h.n, win10: h.win10, avg10: h.avg10, avg20: h.avg20, mae: h.mae, dots: h.events.map(e => e.r10 > 0 ? 1 : 0) } : null,
      since: null
    });
  }
  picks.sort((a, b) => (b.sources.length - a.sources.length) || (b.score - a.score));

  // שער השוק
  const ro = ind.riskOff || {}, sc = ind.scores || {}, ev = ind.evidence || {}, vl = mk.vixLight || {};
  const state = ro.active ? "defense" : (sc.combined >= 65 ? "green" : "neutral");
  const gate = {
    state, label: { defense: "הגנה", neutral: "ניטרלי", green: "ירוק" }[state],
    maxPos: { defense: 3, neutral: 4, green: 5 }[state],
    sizing: { defense: "חצי גודל", neutral: "שני שליש", green: "גודל מלא" }[state],
    combined: sc.combined, breadth: ev.pctMa50, sellDays: (ro.sellingDays || []).length, flow: sc.flow,
    vix: vl.vix, vixState: vl.state, verdict: (ind.verdict || {}).headline || "", asOf: ind.date
  };

  // דה-דופ ביומן: מניה שכבר בפוזיציה פתוחה (מהדורה ב-20 ימי המסחר האחרונים) לא נרשמת שוב
  const cutIdx = Math.max(0, spy.length - 1 - 20);
  const open = {};
  ledger.editions.forEach(e => { if (e.date !== asOf && (spyIdx[e.date] != null ? spyIdx[e.date] : -1) >= cutIdx) e.symbols.forEach(s => { open[s.sym] = open[s.sym] || e.date; }); });
  const fresh = [];
  picks.forEach(p => { if (open[p.sym]) p.since = open[p.sym]; else fresh.push({ sym: p.sym, entry: p.price, stop: p.stop, atr: p.atr }); });
  // מהדורה של אותו יום שנבנית מחדש (המאגר התחלף בבוקר) מחליפה את רשימת המניות — עוד לא
  // נמדד עליה כלום, ומחיר הכניסה (סגירת אותו יום) זהה ממילא
  const ex = ledger.editions.find(e => e.date === asOf);
  if (ex) { ex.symbols = fresh; ex.gate = gate.state; ex.gateLabel = gate.label; ex.results = {}; ex.avg = {}; }
  else {
    ledger.editions.push({ date: asOf, gate: gate.state, gateLabel: gate.label, symbols: fresh, results: {}, avg: {} });
    if (ledger.editions.length > 120) ledger.editions = ledger.editions.slice(-120);
  }

  // רקורד מצטבר: כל המניות שאי-פעם נבחרו (מטמון hist), האישורים ההיסטוריים שלהן
  const all = Object.values(ledger.hist).flatMap(h => h.events || []);
  const record = all.length ? {
    n: all.length, symbols: Object.keys(ledger.hist).length,
    win5: Math.round(all.filter(e => e.r5 > 0).length / all.length * 100),
    win10: Math.round(all.filter(e => e.r10 > 0).length / all.length * 100),
    avg10: +(all.reduce((s, e) => s + e.r10, 0) / all.length).toFixed(1),
    avg20: +(all.reduce((s, e) => s + e.r20, 0) / all.length).toFixed(1),
    mae: +(all.reduce((s, e) => s + e.mae, 0) / all.length).toFixed(1),
    excess10: (() => { const v = all.filter(e => e.spy10 != null); return v.length ? +(v.reduce((s, e) => s + e.r10 - e.spy10, 0) / v.length).toFixed(1) : null; })()
  } : null;

  const out = { date: asOf, poolSig, momDay: momentumDay(), candDay: candidatesDay(), gate, record, picks, excluded, poolSize: pool.length, scanned,
    _meta: { updatedAt: ilStamp(), source: "ta_engine · candidates+momentum", note: "אישור מחיר לקנייה מהמנוע הטכני על סגירת " + asOf } };
  fs.writeFileSync(OUT, JSON.stringify(out), "utf8");
  console.log(`[done] picks ${asOf}: ${picks.length} נבחרות מתוך ${scanned} (מאגר ${pool.length}) · שער ${gate.label} · נפסלו ${excluded.length}` +
    (excluded.length ? " — " + excluded.map(x => x.sym + " (" + x.reason + ")").join(", ") : ""));
}

/* ---- יומן הכנות: תוצאות 5/10/20 ימי מסחר אחרי כל מהדורה, באחוזים ומול SPY ---- */
function updateLedger(ledger, spy) {
  const spyIdx = {}; spy.forEach((b, i) => { spyIdx[b.date] = i; });
  let filled = 0;
  ledger.editions.forEach(e => {
    e.results = e.results || {};
    const si = spyIdx[e.date]; if (si == null) return;
    e.symbols.forEach(s => {
      const res = e.results[s.sym] = e.results[s.sym] || {};
      const need = HORIZONS.filter(h => !res[h]);
      if (!need.length && res.path && res.path.length >= 20) return;
      const bars = loadBars(s.sym); if (!bars) return;
      const bi = bars.findIndex(b => b.date === e.date); if (bi < 0) return;
      // מהלך יומי מצטבר (1.10.2026, איציק): לכל יום מסחר 1..20 מאז המהדורה — [תשואה, מול השוק],
      // ו-cur = היום האחרון שנמדד. העמודה הפעילה (5 / 10 / 20) מתעדכנת ממנו כל יום עד שהיא ננעלת.
      const maxD = Math.min(20, bars.length - 1 - bi, spy.length - 1 - si);
      if (maxD >= 1) {
        res.path = [];
        let lo = Infinity;
        for (let d = 1; d <= maxD; d++) {
          lo = Math.min(lo, bars[bi + d].low);
          const r = (bars[bi + d].close / s.entry - 1) * 100, m = (spy[si + d].close / spy[si].close - 1) * 100;
          res.path.push([+r.toFixed(2), +(r - m).toFixed(2)]);
          if (d === maxD) res.cur = { day: d, ret: +r.toFixed(2), spy: +m.toFixed(2), excess: +(r - m).toFixed(2), mae: +((lo / s.entry - 1) * 100).toFixed(1),
            stopped: s.stop != null ? lo < s.stop : (s.atr ? (s.entry - lo) / s.atr >= 1.5 : false), date: bars[bi + d].date };
        }
      }
      need.forEach(h => {
        if (bi + h >= bars.length || si + h >= spy.length) return;
        let lo = Infinity; for (let k = 1; k <= h; k++) lo = Math.min(lo, bars[bi + k].low);
        const ret = +((bars[bi + h].close / s.entry - 1) * 100).toFixed(2);
        const mkt = +((spy[si + h].close / spy[si].close - 1) * 100).toFixed(2);
        res[h] = { ret, spy: mkt, excess: +(ret - mkt).toFixed(2), mae: +((lo / s.entry - 1) * 100).toFixed(1),
          stopped: s.stop != null ? lo < s.stop : (s.atr ? (s.entry - lo) / s.atr >= 1.5 : false), date: bars[bi + h].date };
        filled++;
      });
    });
    // מהלך המהדורה: ממוצע המניות לכל יום שכולן נמדדו בו, ו-cur = היום האחרון כזה
    const paths = e.symbols.map(s => (e.results[s.sym] || {}).path || []);
    const days = paths.length ? Math.min.apply(null, paths.map(p => p.length)) : 0;
    if (days >= 1) {
      e.path = [];
      for (let d = 0; d < days; d++) e.path.push([+(paths.reduce((a, p) => a + p[d][0], 0) / paths.length).toFixed(2), +(paths.reduce((a, p) => a + p[d][1], 0) / paths.length).toFixed(2)]);
      const last = e.path[days - 1];
      e.cur = { day: days, ret: last[0], excess: last[1], win: Math.round(paths.filter(p => p[days - 1][0] > 0).length / paths.length * 100), n: paths.length };
    }
    // ממוצע המהדורה לכל אופק — רק כשכל המניות שלה מדודות
    e.avg = e.avg || {};
    HORIZONS.forEach(h => {
      const rs = e.symbols.map(s => (e.results[s.sym] || {})[h]).filter(Boolean);
      if (rs.length && rs.length === e.symbols.length) e.avg[h] = {
        ret: +(rs.reduce((a, r) => a + r.ret, 0) / rs.length).toFixed(2),
        excess: +(rs.reduce((a, r) => a + r.excess, 0) / rs.length).toFixed(2),
        win: Math.round(rs.filter(r => r.ret > 0).length / rs.length * 100), n: rs.length };
    });
  });
  if (filled) console.log(`[ledger] נמדדו ${filled} תוצאות חדשות`);
}

function sigHe(s) {
  return { strength: "עוצמה", ttm_squeeze: "סקוויז", macd_buy: "MACD", "6m_high": "שיא 6 חודשים", hot_prospects: "פרוספקט חם" }[s] || s;
}

if (require.main === module) {
  try { process.exit(main()); } catch (e) { console.error("[error] picks:", e && e.stack || e); process.exit(0); }
}
module.exports = { main, history, grpOf };
