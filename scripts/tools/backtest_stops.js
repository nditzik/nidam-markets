// backtest_stops.js — כללי סטופ/יעד לנבחרות על האישורים ההיסטוריים (24.10.2026, איציק: "סטופ ויעד בטבלה").
// לכל אירוע "אישור מחיר" ב-picks_ledger.hist (תאריך) מריצים את המנוע על הנרות עד אותו יום, לוקחים
// תמיכה/התנגדות/ATR, ומדמים 20 ימי מסחר קדימה עם כמה כללי סטופ ויעד. פלט: scripts/tools/out/stops_backtest.json
const fs = require("fs"), path = require("path");
const ROOT = path.join(__dirname, "..", "..");
const T = require(path.join(ROOT, "assets", "ta_engine.js"));
const L = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "picks_ledger.json"), "utf8"));
function bars(sym) { const d = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "bars", sym + ".json"), "utf8")); return (d.bars || d).map(b => ({ date: b[0], open: b[1], high: b[2], low: b[3], close: b[4], volume: b[5] })); }
const STOPS = {
  atr15: (p, s, atr) => p - 1.5 * atr, atr20: (p, s, atr) => p - 2 * atr, atr25: (p, s, atr) => p - 2.5 * atr,
  sup: (p, s, atr) => s != null ? Math.max(s - 0.25 * atr, p - 2.5 * atr) : p - 2 * atr,
  sup3: (p, s, atr) => s != null ? Math.max(s - 0.25 * atr, p - 3 * atr) : p - 2 * atr,
};
const TGTS = { none: null, r2: "r2", res: "res", r3: "r3" };
const out = { events: 0, variants: {} };
for (const sk of Object.keys(STOPS)) for (const tk of Object.keys(TGTS)) out.variants[sk + "/" + tk] = { n: 0, stopHit10: 0, stopHit20: 0, tgtHit20: 0, sum20: 0, sumHold20: 0, sumHold10: 0, win20: 0, sumR: 0 };
let evs = 0;
for (const [sym, h] of Object.entries(L.hist)) {
  let B; try { B = bars(sym); } catch (e) { continue; }
  for (const ev of (h.events || [])) {
    const i = B.findIndex(b => b.date === ev.date); if (i < 220 || i + 20 >= B.length) continue;
    let r; try { r = T.analyze(B.slice(0, i + 1), { symbol: sym }); } catch (e) { continue; }
    const p = B[i].close, atr = r.atr, sup = r.levels.support && r.levels.support.low, res = r.levels.resistance && r.levels.resistance.low;
    if (!atr) continue;
    evs++;
    for (const sk of Object.keys(STOPS)) {
      const stop = STOPS[sk](p, sup, atr), risk = p - stop;
      for (const tk of Object.keys(TGTS)) {
        let tgt = null;
        if (tk === "r2") tgt = p + 2 * risk; else if (tk === "r3") tgt = p + 3 * risk;
        else if (tk === "res") tgt = (res != null && res - p >= 1.5 * risk) ? res : p + 2 * risk;
        const v = out.variants[sk + "/" + tk]; v.n++;
        let exit = null, exitDay = null, hitStop = null;
        for (let d = 1; d <= 20; d++) {
          const b = B[i + d];
          if (b.low <= stop) { exit = Math.min(stop, b.open); exitDay = d; hitStop = d; break; }   // פער למטה = מילוי בפתיחה
          if (tgt != null && b.high >= tgt) { exit = Math.max(tgt, b.open); exitDay = d; v.tgtHit20++; break; }
        }
        if (hitStop != null) { if (hitStop <= 10) v.stopHit10++; v.stopHit20++; }
        const ret = ((exit != null ? exit : B[i + 20].close) / p - 1) * 100;
        v.sum20 += ret; v.sumR += (exit != null ? exit - p : B[i + 20].close - p) / risk; if (ret > 0) v.win20++;
        v.sumHold20 += (B[i + 20].close / p - 1) * 100; v.sumHold10 += (B[i + 10].close / p - 1) * 100;
      }
    }
  }
}
out.events = evs;
for (const [k, v] of Object.entries(out.variants)) {
  v.avg20 = +(v.sum20 / v.n).toFixed(2); v.avgR = +(v.sumR / v.n).toFixed(2); v.hold20 = +(v.sumHold20 / v.n).toFixed(2); v.hold10 = +(v.sumHold10 / v.n).toFixed(2);
  v.stopHit10 = Math.round(v.stopHit10 / v.n * 100); v.stopHit20 = Math.round(v.stopHit20 / v.n * 100); v.tgtHit20 = Math.round(v.tgtHit20 / v.n * 100); v.win20 = Math.round(v.win20 / v.n * 100);
  delete v.sum20; delete v.sumR; delete v.sumHold20; delete v.sumHold10;
}
fs.writeFileSync(path.join(__dirname, "out", "stops_backtest.json"), JSON.stringify(out, null, 1));
console.log("events", evs);
for (const [k, v] of Object.entries(out.variants)) console.log(k.padEnd(12), JSON.stringify(v));
