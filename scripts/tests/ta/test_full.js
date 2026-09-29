// השוואה מלאה של analyze(VLO) מול vlo_full.json (path→value)
const E = require('../../../assets/ta_engine.js'); const bars = require('./vlo_bars.json'); const full = require('./vlo_full.json');
const r = E.analyze(bars, { symbol: 'VLO' });
const SKIP = /^(config_hash|data_hash)$/;
function flat(o, p, out) {
  if (Array.isArray(o)) { if (!o.length) out[p] = '[]'; else o.forEach((v, i) => flat(v, p + '[' + i + ']', out)); }
  else if (o && typeof o === 'object') { for (const k of Object.keys(o)) flat(o[k], p ? p + '.' + k : k, out); }
  else out[p] = o;
  return out;
}
const mine = flat(r, '', {});
let bad = 0, missing = 0, extra = 0; const badList = [], missList = [];
for (const k of Object.keys(full)) {
  if (SKIP.test(k)) continue;
  const e = full[k]; if (!(k in mine)) { missing++; missList.push(k + ' = ' + e); continue; }
  const g = mine[k]; let ok;
  if (e === 'null') ok = g == null; else if (e === 'true' || e === 'false') ok = String(g) === e; else if (e === '[]') ok = Array.isArray(g) ? g.length === 0 : g === '[]';
  else if (/^-?\d+(\.\d+)?(e-?\d+)?$/.test(e) && typeof g === 'number') ok = Math.abs(g - parseFloat(e)) <= 1e-10 * Math.max(1, Math.abs(parseFloat(e)));
  else ok = String(g) === String(e);
  if (!ok) { bad++; badList.push(k + '\n   exp: ' + e + '\n   got: ' + g); }
}
console.log('mismatches', bad, 'missing', missing);
badList.slice(0, 80).forEach(x => console.log('✗ ' + x));
missList.slice(0, 40).forEach(x => console.log('? ' + x));
