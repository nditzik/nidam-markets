const E = require('../../../assets/ta_engine.js'); const bars = require('./vlo_bars.json'); const full = require('./vlo_full.json'); const steps = require('./vlo_steps.json');
const ind = E.computeIndicators(bars);
function pts(kv, n) { const out = []; for (let i = 0; i < n; i++) { const p = {}; for (const f of ['index','date','price','kind','atr','confirmed_index','confirmed_at']) p[f] = kv[`points[${i}].${f}`]; out.push(p); } return out; }
function cmpPoint(a, e, tag) { const bad = []; for (const f of Object.keys(e)) { let g = a[f]; let x = e[f]; if (x === 'null') x = null; if (typeof g === 'number') { if (Math.abs(g - parseFloat(x)) > 1e-9 * Math.max(1, Math.abs(g))) bad.push(f + ':' + g + '≠' + x); } else if (String(g) !== String(x)) bad.push(f + ':' + g + '≠' + x); } if (bad.length) console.log(tag, bad.join(' ')); return !bad.length; }
for (const [si, rev, mb, lb, prefix] of [[0, 3, 6, 252, 'market_structure'], [1, 1.75, 4, 90, 'trend_hierarchy.intermediate.structure']]) {
  const kv = steps[si].kv; const n = Object.keys(kv).filter(k => /^points\[\d+\]\.index$/.test(k)).length;
  const exp = pts(kv, n); const st = E.classifyStructure(bars, ind, rev, mb, lb);
  let ok = st.all_points.length === n; if (!ok) console.log(prefix, 'point count', st.all_points.length, 'vs', n);
  exp.forEach((e, i) => { if (st.all_points[i]) ok = cmpPoint(st.all_points[i], e, prefix + ' pt' + i) && ok; });
  const g = (k) => full[prefix + '.' + k];
  const checks = { state: st.state, breach_closes: st.breach_closes, at_risk: st.at_risk, damaged_sequence: st.damaged_sequence, break_level: st.break_level, 'protected_low.index': st.protected_low && st.protected_low.index, 'protected_low.protected_at': st.protected_low && st.protected_low.protected_at, 'counts.HH': st.counts.HH, 'counts.HL': st.counts.HL, 'counts.LH': st.counts.LH, 'counts.LL': st.counts.LL, higher_high: st.higher_high, higher_low: st.higher_low };
  for (const k in checks) { const e = g(k), a = checks[k]; const same = typeof a === 'number' ? Math.abs(a - parseFloat(e)) < 1e-9 : String(a) === String(e); if (!same) { ok = false; console.log(prefix, k, 'got', a, 'exp', e); } }
  const nsw = Object.keys(full).filter(k => new RegExp('^' + prefix.replace(/\./g, '\\.') + '\\.swings\\[\\d+\\]\\.index$').test(k)).length;
  if (st.swings.length !== nsw) { ok = false; console.log(prefix, 'swings in window', st.swings.length, 'vs', nsw); }
  st.swings.forEach((p, i) => { const e = {}; for (const f of ['index','date','price','kind','atr','confirmed_index','confirmed_at','reversal_atr','label','previous_price']) e[f] = full[prefix + '.swings[' + i + '].' + f]; ok = cmpPoint(p, e, prefix + ' swing' + i) && ok; });
  console.log(prefix, ok ? 'OK' : 'FAIL', 'points', st.all_points.length, 'window', st.swings.length, 'seq', st.sequence.join(' '));
}
