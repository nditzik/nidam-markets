#!/usr/bin/env python3
"""
build_fundamentals.py — "יסודות החברה" לחלון הניתוח הטכני (26.10.2026, איציק: "לשלב בגרף בלבד ולא לערבב עם הטבלאות").

לכל מניה שמופיעה באתר (אותו יקום כמו fetch_bars, בלי תעודות הסל) נשמרים מספרים בסיסיים מ-Yahoo quoteSummary:
שווי שוק, מכפיל רווח (12 חודשים וקדימה), צמיחת הכנסות, רווח תפעולי, תזרים חופשי, מזומן נטו, דיבידנד, מחיר יעד
ודירוגי אנליסטים, צפי לדוח הבא (רווח למניה והכנסות), ענף ותעשייה. בנוסף: מועד הדוח הבא (קודם מלוח הדיווחים
של האתר — הסורק של TradingView — ואז Yahoo), התזוזה שהאופציות מתמחרות ליום הדוח (מ-earnings_prep.json כשיש),
תג איכות (מבוססת / צומחת, לא רווחית / קטנה / מעורבת / ספקולטיבית) ומשפט "קריאה" בעברית.

קצב: מניה מתרעננת פעם ב-7 ימים (יסודות משתנים פעם ברבעון), עד MAX_PER_RUN מניות לריצה — הריצה הראשונה
מתפרסת על כמה מחזורים; קודם הנבחרות, ארבעת העמודים, מניות המעקב ו-ta_watchlist. מניה שיצאה מהיקום נמחקת
אחרי 45 יום. פלט: data/fundamentals.json {updated, symbols:{SYM:{…}}}; assets/ta_ui.js קורא אותו בפתיחת החלון.
בדיקה בלי רשת: main(fetch=<פונקציה sym→quoteSummary result>, now=<datetime>).
"""
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iltime import NY  # noqa: E402
import fetch_bars  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "fundamentals.json")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MODS = "price,summaryProfile,summaryDetail,defaultKeyStatistics,financialData,calendarEvents,recommendationTrend,earningsTrend"
REFRESH_DAYS = 7
MAX_PER_RUN = 60
DROP_DAYS = 45
VER = 1
PAUSE_S = 0.7          # בין מניות — 60 בקשות רצופות בלי הפסקה קיבלו 429 בריצה הראשונה (26.10.2026)
RETRY_WAIT_S = (4, 8, 15)   # ניסיונות חוזרים על 429, עם cookie+crumb חדשים
ERROR_RETRY_H = 24     # מניה שנכשלה (סמל לא קיים, ADR דק) — ניסיון נוסף אחרי יום, לא כל רבע שעה
LIMIT_ABORT = 3        # שלוש מניות ברצף שנחסמו גם אחרי הניסיונות החוזרים — Yahoo חוסם, ממשיכים בריצה הבאה


class RateLimited(Exception):
    pass


class Net:
    """HTTP אמיתי: cookie+crumb של Yahoo נוצרים בבקשה הראשונה; על 429 — המתנה, cookie חדש וניסיון חוזר."""
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.op.addheaders = [("User-Agent", UA), ("Accept", "*/*")]
        self.crumb = None
        self.strategy = None

    def _get(self, url, timeout=20):
        with self.op.open(url, timeout=timeout) as r:
            return r.read()

    GETCRUMB = "https://query2.finance.yahoo.com/v1/test/getcrumb"

    def _cookie_basic(self):
        """fc.yahoo.com מחזיר 404 אבל שותל cookie — עובד מ-runner אמריקאי."""
        try:
            self._get("https://fc.yahoo.com", 10)
        except urllib.error.HTTPError:
            pass

    def _cookie_csrf(self):
        """runner באירופה מקבל דף הסכמה (GDPR) במקום cookie, ו-getcrumb עונה 429 — עוברים את ההסכמה כמו yfinance."""
        html = self._get("https://guce.yahoo.com/consent").decode("utf-8", "replace")
        m_tok = re.search(r'name="csrfToken"\s+value="([^"]+)"', html) or re.search(r'value="([^"]+)"\s+name="csrfToken"', html)
        m_sid = re.search(r'name="sessionId"\s+value="([^"]+)"', html) or re.search(r'value="([^"]+)"\s+name="sessionId"', html)
        if not (m_tok and m_sid):
            raise RuntimeError("consent page without csrfToken/sessionId")
        sid = m_sid.group(1)
        body = urllib.parse.urlencode([("agree", "agree"), ("agree", "agree"), ("consentUUID", "default"), ("sessionId", sid),
                                       ("csrfToken", m_tok.group(1)), ("originalDoneUrl", "https://finance.yahoo.com/"), ("namespace", "yahoo")]).encode()
        req = urllib.request.Request(f"https://consent.yahoo.com/v2/collectConsent?sessionId={sid}", data=body,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        with self.op.open(req, timeout=20) as r:
            r.read()
        try:
            self._get(f"https://guce.yahoo.com/copyConsent?sessionId={sid}")
        except urllib.error.HTTPError:
            pass

    def _crumb(self):
        if self.crumb is None:
            last = None
            for strat in (self._cookie_basic, self._cookie_csrf):
                try:
                    strat()
                    c = self._get(self.GETCRUMB).decode().strip()
                    if c and "<" not in c:
                        self.crumb, self.strategy = c, strat.__name__[8:]
                        return c
                    last = RuntimeError("empty crumb")
                except Exception as e:  # 429 בלי cookie, דף הסכמה בלי שדות…
                    last = e
                self.cj.clear()
            code = getattr(last, "code", 429)
            raise urllib.error.HTTPError(self.GETCRUMB, code, f"crumb: {last}"[:70], None, None)
        return self.crumb

    def summary(self, sym):
        last = None
        for i in range(len(RETRY_WAIT_S) + 1):
            try:
                u = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{urllib.parse.quote(sym)}?modules={MODS}&crumb={self._crumb()}"
                return json.loads(self._get(u))["quoteSummary"]["result"][0]
            except urllib.error.HTTPError as e:
                if e.code != 429:
                    raise
                last = e
                if i < len(RETRY_WAIT_S):
                    self.crumb = None
                    self.cj.clear()
                    time.sleep(RETRY_WAIT_S[i])
        raise RateLimited(str(last)[:60])


def raw(v):
    if isinstance(v, dict):
        return v.get("raw")
    return v if isinstance(v, (int, float)) else None


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def pct(v, d=1):
    return None if v is None else round(v * 100, d)


# ---------------------------------------------------------------- לוח הדיווחים של האתר (TradingView) — המועד הסמכותי
def site_earnings():
    """{SYM: (date, when)} מלוח הדיווחים (היום/השבוע/הבאים) — מועד מאומת מהסורק."""
    out = {}
    e = load(os.path.join(DATA, "earnings.json"), {})
    today = e.get("today")
    today = today.get("date") if isinstance(today, dict) else today
    for r in (e.get("reporting") or []):
        if r.get("ticker") and today:
            out[r["ticker"]] = (today, r.get("when") or "")
    for d in (e.get("week") or []):
        for c in (d.get("companies") or []):
            if c.get("ticker") and d.get("date"):
                out.setdefault(c["ticker"], (d["date"], c.get("when") or ""))
    for d in (e.get("upcoming") or []):
        for t in (d.get("tickers") or []):
            if d.get("date"):
                out.setdefault(t, (d["date"], ""))
    return out


def prep_moves():
    """{SYM: {move, eps, rev}} מ-earnings_prep.json — התזוזה המתומחרת והצפי כשיש הכנה."""
    out = {}
    p = load(os.path.join(DATA, "earnings_prep.json"), {})
    for it in (p.get("items") or []):
        o = it.get("options") or {}
        c = it.get("consensus") or {}
        out[it.get("sym")] = {"move": o.get("earn") or o.get("pct"), "eps": c.get("eps"), "rev": c.get("rev")}
    return out


# ---------------------------------------------------------------- פענוח
def parse(r):
    pr = r.get("price") or {}
    sp = r.get("summaryProfile") or {}
    sd = r.get("summaryDetail") or {}
    ks = r.get("defaultKeyStatistics") or {}
    fd = r.get("financialData") or {}
    rt = ((r.get("recommendationTrend") or {}).get("trend") or [{}])[0]
    trend = (r.get("earningsTrend") or {}).get("trend") or []
    t0 = next((t for t in trend if t.get("period") == "0q"), {})
    ce = (r.get("calendarEvents") or {}).get("earnings") or {}
    edates = [raw(x) for x in (ce.get("earningsDate") or []) if raw(x)]
    rev = raw(fd.get("totalRevenue"))
    fcf = raw(fd.get("freeCashflow"))
    cash, debt = raw(fd.get("totalCash")), raw(fd.get("totalDebt"))
    eps = raw(ks.get("trailingEps"))
    if eps is None:
        eps = raw(fd.get("epsTrailingTwelveMonths"))
    out = {
        "name": pr.get("longName") or pr.get("shortName"),
        "sector": sp.get("sector"), "industry": sp.get("industry"),
        "cap": raw(pr.get("marketCap")) or raw(sd.get("marketCap")),
        "price": raw(pr.get("regularMarketPrice")),
        "pe": raw(sd.get("trailingPE")) or raw(ks.get("trailingPE")),
        "fwdPe": raw(sd.get("forwardPE")) or raw(ks.get("forwardPE")),
        "eps": eps, "fwdEps": raw(ks.get("forwardEps")),
        "revGrowth": pct(raw(fd.get("revenueGrowth"))),
        "epsGrowth": pct(raw(fd.get("earningsGrowth"))),
        "grossMargin": pct(raw(fd.get("grossMargins"))),
        "opMargin": pct(raw(fd.get("operatingMargins"))),
        "netMargin": pct(raw(fd.get("profitMargins"))),
        "fcfMargin": pct(fcf / rev) if (fcf is not None and rev) else None,
        "cash": cash, "debt": debt,
        "netCash": (cash - debt) if (cash is not None and debt is not None) else None,
        "divYield": pct(raw(sd.get("dividendYield")), 2),
        "target": raw(fd.get("targetMeanPrice")), "targetN": raw(fd.get("numberOfAnalystOpinions")),
        "recKey": fd.get("recommendationKey"), "recMean": raw(fd.get("recommendationMean")),
        "recs": {k: rt.get(k) for k in ("strongBuy", "buy", "hold", "sell", "strongSell")},
        "epsEst": raw(((t0.get("earningsEstimate") or {}).get("avg"))),
        "revEst": raw(((t0.get("revenueEstimate") or {}).get("avg"))),
        "yahooEarn": datetime.fromtimestamp(edates[0], NY).date().isoformat() if edates else None,
    }
    return out


def quality(f):
    cap, growth = f.get("cap"), f.get("revGrowth")
    prof = (f.get("eps") is not None and f["eps"] > 0) or (f.get("netMargin") is not None and f["netMargin"] > 0)
    if cap is None:
        return {"q": "mid", "label": "חסר מידע"}
    if cap < 3e8 or (not prof and growth is not None and growth < 0):
        return {"q": "bad", "label": "ספקולטיבית"}
    if cap >= 2e9 and prof and (growth is None or growth >= 0):
        return {"q": "ok", "label": "מבוססת"}
    if not prof:
        return {"q": "mid", "label": "צומחת, לא רווחית" if (growth or 0) > 0 else "לא רווחית"}
    if cap < 2e9:
        return {"q": "mid", "label": "קטנה"}
    return {"q": "mid", "label": "רווחית, ההכנסות יורדות" if (growth is not None and growth < 0) else "מעורבת"}


def read_sentence(f, q):
    prof = (f.get("eps") is not None and f["eps"] > 0) or (f.get("netMargin") is not None and f["netMargin"] > 0)
    g = f.get("revGrowth")
    if prof and g is not None and g > 0:
        s = "חברה רווחית וצומחת"
    elif prof and g is not None:
        s = "חברה רווחית, אבל ההכנסות יורדות"
    elif prof:
        s = "חברה רווחית"
    elif g is not None and g > 0:
        s = "צומחת אבל עדיין לא רווחית"
    elif g is not None:
        s = "לא רווחית וההכנסות יורדות"
    else:
        s = "נתוני הרווחיות חסרים"
    pe = f.get("fwdPe") or f.get("pe")
    if pe and pe > 0:
        s += " במכפיל " + ("גבוה" if pe > 35 else "סביר" if pe >= 15 else "נמוך")
    nc, cap = f.get("netCash"), f.get("cap")
    if nc is not None and cap:
        if nc > 0:
            s += ", עם יותר מזומן מחוב"
        elif -nc > 0.3 * cap:
            s += ", ממונפת (החוב נטו מעל 30% מהשווי)"
    if q["q"] == "bad":
        s += ". שווי קטן או חברה מפסידה: תנודתית, לא לפוזיציה מלאה"
    return s + "."


# ---------------------------------------------------------------- ריצה
def priority(syms):
    """קודם מה שבולט באתר: הנבחרות, ארבעת העמודים, מניות המעקב, רשימת המעקב הטכנית."""
    first = []
    for p in (load(os.path.join(DATA, "picks.json"), {}).get("picks") or []):
        first.append(p.get("sym") or p.get("symbol"))
    for r in (load(os.path.join(DATA, "trades.json"), {}).get("reports") or [])[:2]:
        for p in (r.get("featured") or r.get("picks") or []):
            first.append(p.get("ticker"))
    for fn in ("holdings.txt", "ta_watchlist.txt"):
        try:
            with open(os.path.join(DATA, fn), encoding="utf-8") as f:
                first += [ln.strip().upper() for ln in f if ln.strip() and not ln.startswith("#")]
        except OSError:
            pass
    seen, out = set(), []
    for s in first + sorted(syms):
        if s and s in syms and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def main(fetch=None, now=None):
    now = now or datetime.now(timezone.utc)
    syms, _ = fetch_bars.universe()
    syms = {s for s in syms if s not in fetch_bars.SECTOR_ETFS + fetch_bars.INDEX_ETFS and "/" not in s}
    prev = load(OUT, {})
    symbols = prev.get("symbols") or {}
    earn, moves = site_earnings(), prep_moves()
    net = None
    if fetch is None:
        net = Net()
        fetch = net.summary
    todo = []
    for s in priority(syms):
        rec = symbols.get(s)
        if not rec or rec.get("ver") != VER:
            todo.append(s)
            continue
        age_h = (now - datetime.fromisoformat(rec["at"].replace("Z", "+00:00"))).total_seconds() / 3600
        if rec.get("error"):
            if "429" in rec["error"] or age_h >= ERROR_RETRY_H:   # 429 של ריצה קודמת = לא כישלון של המניה
                todo.append(s)
        elif age_h >= 24 * REFRESH_DAYS:
            todo.append(s)
    ok = fail = limited = 0
    first_err = None
    for i, s in enumerate(todo[:MAX_PER_RUN]):
        if net is not None and i:
            time.sleep(PAUSE_S)
        try:
            f = parse(fetch(s))
        except RateLimited as e:  # Yahoo חוסם גם אחרי הניסיונות החוזרים — לא רושמים כישלון, ננסה בריצה הבאה
            limited += 1
            first_err = first_err or f"{s}: {e}"
            if limited >= LIMIT_ABORT:
                print(f"[warn] Yahoo חוסם (429) — {limited} מניות ברצף, ממשיכים בריצה הבאה ({first_err})")
                break
            continue
        except Exception as e:  # מניה בלי נתונים (SPAC, ADR דק) — לא עוצרת את הריצה
            fail += 1
            first_err = first_err or f"{s}: {e}"
            symbols.setdefault(s, {})["at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            symbols[s]["ver"] = VER
            symbols[s]["error"] = str(e)[:80]
            continue
        limited = 0
        q = quality(f)
        f["quality"], f["read"] = q, read_sentence(f, q)
        f["at"], f["ver"] = now.strftime("%Y-%m-%dT%H:%M:%SZ"), VER
        f.pop("error", None)
        symbols[s] = f
        ok += 1
    # מועד הדוח הבא + תזוזה מתומחרת — מתרעננים בכל ריצה (זולים, מהקבצים)
    for s, f in symbols.items():
        if "cap" not in f:
            continue
        d = earn.get(s)
        f["nextEarn"] = {"date": d[0], "when": d[1], "src": "tv"} if d else ({"date": f["yahooEarn"], "when": "", "src": "yahoo"} if f.get("yahooEarn") else None)
        m = moves.get(s) or {}
        f["move"] = m.get("move")
        if m.get("eps") is not None:
            f["epsEst"] = m["eps"]
        if m.get("rev") is not None:
            f["revEst"] = m["rev"]
    # ניקוי: מניה מחוץ ליקום 45 יום
    for s in list(symbols):
        if s not in syms:
            at = symbols[s].get("at")
            if not at or (now - datetime.fromisoformat(at.replace("Z", "+00:00"))).days >= DROP_DAYS:
                del symbols[s]
    out = {"updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "ver": VER, "universe": len(syms),
           "count": sum(1 for v in symbols.values() if "cap" in v), "pending": max(0, len(todo) - MAX_PER_RUN),
           "symbols": dict(sorted(symbols.items()))}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print("fundamentals: universe=%d have=%d refreshed=%d failed=%d limited=%d pending=%d%s%s"
          % (len(syms), out["count"], ok, fail, limited, out["pending"],
             f" · cookie via {net.strategy}" if net is not None and net.strategy else "",
             f" · first error {first_err}" if first_err else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
