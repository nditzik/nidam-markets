// bars-worker.js — "שכבה 2" של "נתח מניה" (27.10.2026).
// Cloudflare Worker קטן שמביא נרות יומיים מ-Yahoo לכל טיקר אמריקאי ומחזיר אותם לאתר,
// כדי שהמנוע הטכני המלא ירוץ גם על מניה שאין לה היסטוריה שמורה ב-data/bars.
// הדפדפן לא יכול לפנות ל-Yahoo ישירות (CORS), והשרתים של GitHub חסומים שם — לכן מתווך.
//
// כתובת: GET https://<worker>.workers.dev/bars?s=AAPL
// תשובה:  {"symbol":"AAPL","bars":[["2026-10-26",343.9,347.09,341.03,343.91,42205799],…],"source":"yahoo"}
// מטמון: שעה בקצה של Cloudflare (נרות יומיים לא משתנים מהר), כך שגם הרבה מבקרים = מעט בקשות ל-Yahoo.
// הגבלה: רק סמלים של 1–6 אותיות (עם . או -), ורק לאתר עצמו (ORIGINS). בלי מפתחות, בלי מידע אישי.
//
// 10.11.2026 — גם מתווך לסורק של TradingView (נשאר לשימוש עתידי; ב-10.11 הסורק היה קפוא על סגירת אתמול
// למניות ותעודות סל לכל פונה — גם לשרת וגם ל-Worker הזה, לכן המחירים החיים עברו ל-/quotes מ-Yahoo):
//   POST /scan?m=america|futures|forex   (גוף = אותו JSON שהאתר שולח לסורק, text/plain) → התשובה של הסורק כמו שהיא
//   GET  /scan-test?s=SPY                 → {"s":"SPY","close":…,"change":…} — בדיקה בעין מהדפדפן
// מטמון 30 שניות בקצה לכל גוף בקשה (הרבה מבקרים באותה דקה = בקשה אחת לסורק).
//
//   GET /quotes?s=SPY,QQQ,^VIX,XLK…      → {"quotes":{"SPY":{price,chg,prev,t,ext,extChg,et}},"source":"yahoo"}
// מחירים חיים מ-Yahoo (גרף v8, יום אחד, נרות 5 דק' כולל פרה/אפטר) — עד 20 סמלים, מטמון 60 שניות לכל סמל.
// chg = מחיר המסחר הרציף האחרון מול הסגירה הקודמת (כמו fetch_market.py); ext = הנר האחרון אחרי המסחר הרציף
// (פרה-מרקט/אפטר-מרקט), extChg = מולו מחיר המסחר הרציף האחרון.

const ORIGINS = ["https://nditzik.github.io", "http://localhost:8765", "http://127.0.0.1:8765"];
const SYM_RE = /^[A-Z][A-Z.\-]{0,6}$/;
const Q_RE = /^[\^A-Z0-9][A-Z0-9.\-=^]{0,11}$/;
const Q_TTL = 60;
const SCAN_MARKETS = ["america", "futures", "forex"];
const SCAN_TTL = 30;
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";

function cors(origin) {
  const allow = ORIGINS.includes(origin) ? origin : ORIGINS[0];
  return { "Access-Control-Allow-Origin": allow, "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Vary": "Origin" };
}
function json(body, status, origin, maxAge) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=" + (maxAge || 0), ...cors(origin) },
  });
}
function nyDate(sec) {
  return new Date(sec * 1000).toLocaleDateString("en-CA", { timeZone: "America/New_York" });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "";
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
    if (url.pathname === "/quotes") return quotes(url, origin, ctx);
    if (url.pathname === "/scan" || url.pathname === "/scan-test") return scan(request, url, origin, ctx);
    if (url.pathname !== "/bars") return json({ error: "not found" }, 404, origin);
    const sym = (url.searchParams.get("s") || "").trim().toUpperCase().replace(/\./g, "-");
    if (!SYM_RE.test(sym)) return json({ error: "bad symbol" }, 400, origin);

    // מטמון בקצה — אותה תשובה לכל המבקרים במשך שעה
    const cache = caches.default;
    const key = new Request("https://bars.cache/" + sym);
    const hit = await cache.match(key);
    if (hit) {
      const r = new Response(hit.body, hit);
      Object.entries(cors(origin)).forEach(([k, v]) => r.headers.set(k, v));
      return r;
    }

    const yurl = "https://query1.finance.yahoo.com/v8/finance/chart/" + encodeURIComponent(sym) + "?range=2y&interval=1d&includePrePost=false";
    let data;
    try {
      const yr = await fetch(yurl, { headers: { "User-Agent": UA, "Accept": "application/json" } });
      if (!yr.ok) return json({ error: "yahoo " + yr.status }, 502, origin);
      data = await yr.json();
    } catch (e) {
      return json({ error: "yahoo unreachable" }, 502, origin);
    }
    const res = data && data.chart && data.chart.result && data.chart.result[0];
    const q = res && res.indicators && res.indicators.quote && res.indicators.quote[0];
    if (!res || !q || !res.timestamp) return json({ error: "no data" }, 404, origin);
    const bars = [];
    res.timestamp.forEach((t, i) => {
      const o = q.open[i], h = q.high[i], l = q.low[i], c = q.close[i], v = q.volume[i];
      if ([o, h, l, c].some((x) => x == null || !(x > 0))) return;
      const r4 = (x) => Math.round(x * 10000) / 10000;
      bars.push([nyDate(t), r4(o), r4(h), r4(l), r4(c), v || 0]);
    });
    // יום כפול (נר חלקי + נר יומי) — משאירים את האחרון
    const out = [];
    bars.forEach((b) => { if (out.length && out[out.length - 1][0] === b[0]) out[out.length - 1] = b; else out.push(b); });
    const body = { symbol: sym, bars: out, source: "yahoo", exchange: res.meta && res.meta.exchangeName, currency: res.meta && res.meta.currency };
    const resp = json(body, 200, origin, 3600);
    ctx.waitUntil(cache.put(key, resp.clone()));
    return resp;
  },
};

// ---- מתווך לסורק של TradingView (10.11.2026) ----
async function sha(text) {
  const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");
}
async function scan(request, url, origin, ctx) {
  let market, body, test = null;
  if (url.pathname === "/scan-test") {
    test = (url.searchParams.get("s") || "SPY").trim().toUpperCase();
    if (!SYM_RE.test(test)) return json({ error: "bad symbol" }, 400, origin);
    market = "america";
    // כמו כרטיס החיפוש באתר: סינון לפי שם (סמל לא קיים ברשימת tickers מפיל את כל הבקשה)
    body = JSON.stringify({ filter: [{ left: "name", operation: "in_range", right: [test.replace(/-/g, ".")] },
      { left: "exchange", operation: "in_range", right: ["NASDAQ", "NYSE", "AMEX"] }], columns: ["name", "close", "change"], range: [0, 3] });
  } else {
    if (request.method !== "POST") return json({ error: "POST only" }, 405, origin);
    market = url.searchParams.get("m") || "america";
    if (!SCAN_MARKETS.includes(market)) return json({ error: "bad market" }, 400, origin);
    body = await request.text();
    if (!body || body.length > 8000) return json({ error: "bad body" }, 400, origin);
    try { JSON.parse(body); } catch (e) { return json({ error: "bad json" }, 400, origin); }
  }
  const cache = caches.default;
  const key = new Request("https://scan.cache/" + market + "/" + (await sha(body)));
  let text = null;
  const hit = await cache.match(key);
  if (hit) text = await hit.text();
  else {
    try {
      const r = await fetch("https://scanner.tradingview.com/" + market + "/scan", {
        method: "POST",
        headers: { "User-Agent": UA, "Content-Type": "text/plain;charset=UTF-8", "Accept": "application/json" },
        body,
      });
      text = await r.text();
      if (!r.ok) return json({ error: "scanner " + r.status, detail: text.slice(0, 200) }, 502, origin);
    } catch (e) {
      return json({ error: "scanner unreachable" }, 502, origin);
    }
    ctx.waitUntil(cache.put(key, new Response(text, { headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=" + SCAN_TTL } })));
  }
  if (test) {
    let row = null;
    try { row = (JSON.parse(text).data || [])[0]; } catch (e) {}
    if (!row) return json({ error: "not found", s: test }, 404, origin);
    return json({ s: test, close: row.d[1], change: row.d[2], at: new Date().toISOString() }, 200, origin);
  }
  return new Response(text, { status: 200, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...cors(origin) } });
}

// ---- מחירים חיים מ-Yahoo (10.11.2026) ----
async function quoteOne(sym, ctx) {
  const cache = caches.default;
  const key = new Request("https://quote.cache/" + encodeURIComponent(sym));
  const hit = await cache.match(key);
  if (hit) { try { return await hit.json(); } catch (e) {} }
  const u = "https://query1.finance.yahoo.com/v8/finance/chart/" + encodeURIComponent(sym) + "?range=1d&interval=5m&includePrePost=true";
  let d;
  try {
    const r = await fetch(u, { headers: { "User-Agent": UA, "Accept": "application/json" } });
    if (!r.ok) return null;
    d = await r.json();
  } catch (e) { return null; }
  const res = d && d.chart && d.chart.result && d.chart.result[0], m = res && res.meta;
  if (!m || m.regularMarketPrice == null) return null;
  const price = m.regularMarketPrice, prev = m.chartPreviousClose != null ? m.chartPreviousClose : m.previousClose;
  const out = { price, prev, chg: prev ? Math.round((price / prev - 1) * 10000) / 100 : null, t: m.regularMarketTime || null, ext: null, extChg: null, et: null };
  const ts = res.timestamp || [], cl = (res.indicators && res.indicators.quote && res.indicators.quote[0] && res.indicators.quote[0].close) || [];
  for (let i = ts.length - 1; i >= 0; i--) {
    if (cl[i] == null) continue;
    if (out.t && ts[i] > out.t + 60) { out.ext = Math.round(cl[i] * 10000) / 10000; out.et = ts[i]; out.extChg = Math.round((cl[i] / price - 1) * 10000) / 100; }
    break;
  }
  ctx.waitUntil(cache.put(key, new Response(JSON.stringify(out), { headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=" + Q_TTL } })));
  return out;
}
async function quotes(url, origin, ctx) {
  const syms = (url.searchParams.get("s") || "").toUpperCase().split(",").map((x) => x.trim()).filter(Boolean);
  if (!syms.length || syms.length > 20 || syms.some((x) => !Q_RE.test(x))) return json({ error: "bad symbols" }, 400, origin);
  const got = await Promise.all(syms.map((x) => quoteOne(x, ctx)));
  const q = {};
  syms.forEach((x, i) => { if (got[i]) q[x] = got[i]; });
  if (!Object.keys(q).length) return json({ error: "yahoo unavailable" }, 502, origin);
  return json({ quotes: q, source: "yahoo", at: new Date().toISOString() }, 200, origin);
}
