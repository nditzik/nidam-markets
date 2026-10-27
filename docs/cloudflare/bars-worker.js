// bars-worker.js — "שכבה 2" של "נתח מניה" (27.10.2026).
// Cloudflare Worker קטן שמביא נרות יומיים מ-Yahoo לכל טיקר אמריקאי ומחזיר אותם לאתר,
// כדי שהמנוע הטכני המלא ירוץ גם על מניה שאין לה היסטוריה שמורה ב-data/bars.
// הדפדפן לא יכול לפנות ל-Yahoo ישירות (CORS), והשרתים של GitHub חסומים שם — לכן מתווך.
//
// כתובת: GET https://<worker>.workers.dev/bars?s=AAPL
// תשובה:  {"symbol":"AAPL","bars":[["2026-10-26",343.9,347.09,341.03,343.91,42205799],…],"source":"yahoo"}
// מטמון: שעה בקצה של Cloudflare (נרות יומיים לא משתנים מהר), כך שגם הרבה מבקרים = מעט בקשות ל-Yahoo.
// הגבלה: רק סמלים של 1–6 אותיות (עם . או -), ורק לאתר עצמו (ORIGINS). בלי מפתחות, בלי מידע אישי.

const ORIGINS = ["https://nditzik.github.io", "http://localhost:8765", "http://127.0.0.1:8765"];
const SYM_RE = /^[A-Z][A-Z.\-]{0,6}$/;
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";

function cors(origin) {
  const allow = ORIGINS.includes(origin) ? origin : ORIGINS[0];
  return { "Access-Control-Allow-Origin": allow, "Access-Control-Allow-Methods": "GET, OPTIONS", "Vary": "Origin" };
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
