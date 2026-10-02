#!/usr/bin/env python3
"""
build_earnings_prep.py — "לקראת הדוח" (2.10.2026, איציק): לכל חברה שיש לה ניתוח דוח קודם באתר
ומדווחת בשבועיים הקרובים, אוסף את המספרים להכנה → data/earnings_prep.json.

החלק המילולי (המשפט המוביל, מה ההנהלה הבטיחה, מה לבדוק, חולשות, תרחישים) נכתב ע"י הרוטינה היומית
לפי scripts/prompts/earnings_prep.md ל-data/earnings_prep_notes.json — הקובץ הזה לא נוגע בו.

מקורות (כולם ציבוריים, בלי מפתח; נבדקו מה-runner ב-2.10.2026 — scripts/tools/probe_*.py):
- מי ומתי: סורק TradingView (earnings_release_next_date/_time) רק לטיקרים שיש להם ניתוח.
- אנליסטים: Yahoo quoteSummary (צפי רווח/הכנסות, 4 הפתעות אחרונות, מחירי יעד, דירוגים, עדכונים).
- אופציות: Yahoo v7 (cookie+crumb) — סטראדל ATM לפקיעה הראשונה אחרי הדוח; התזוזה "ליום הדוח"
  = בניכוי התנודה הרגילה לפי הפקיעה שלפני הדוח. מתעדכן רק בשעות המסחר (מחוץ להן הציטוטים לא עקביים).
- תגובות קודמות: תאריכי הפרסום של 4 הדוחות האחרונים מ-Nasdaq (earnings-surprise, ציבורי) + נרות יומיים —
  יום התגובה = יום הפרסום או המחרת, לפי המחזור. בלי Nasdaq: יום המחזור הגבוה אחרי סוף הרבעון (פחות מדויק).
עמידות: כשל במקור משאיר את הערכים הקודמים של אותה חברה; כשל כללי משאיר את הקובץ.
בדיקה מקומית: main(fetch=..., now=...) עם נתונים מדומים (אין רשת בסנדבוקס).
"""
import http.cookiejar
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iltime import IL, NY  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "earnings_prep.json")
REPORTS = os.path.join(DATA, "reports.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TV_SCAN = "https://scanner.tradingview.com/america/scan"
AHEAD_DAYS = 14          # חברה נכנסת כשהדוח בתוך שבועיים
ANALYST_EVERY_H = 6      # רענון אנליסטים/נרות לכל חברה
VER = 3                  # שינוי מבנה → הרענון של 6 השעות מתאפס (v2: תאריכי Nasdaq; v3: יום תגובה לפי שעת הדוח)
# חברות שנשמרות בשם ולא בטיקר (כמו LOGO_ALIAS ב-fetch_reports.py)
ALIAS = {"ALPHABET": "GOOGL", "GOOGLE": "GOOGL", "FACEBOOK": "META", "BERKSHIRE": "BRK-B"}


# ---------------------------------------------------------------- רשת
class Net:
    """HTTP אמיתי: cookie+crumb של Yahoo נוצרים בבקשה הראשונה."""
    def __init__(self):
        cj = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        self.op.addheaders = [("User-Agent", UA), ("Accept", "*/*")]
        self.crumb = None

    def _get(self, url, timeout=20):
        with self.op.open(url, timeout=timeout) as r:
            return r.read()

    def _crumb(self):
        if self.crumb is None:
            try:
                self._get("https://fc.yahoo.com", 10)
            except Exception:
                pass                      # מחזיר 404 אבל שותל cookie
            self.crumb = self._get("https://query2.finance.yahoo.com/v1/test/getcrumb").decode().strip()
        return self.crumb

    def tv(self, tickers):
        body = json.dumps({
            "filter": [{"left": "name", "operation": "in_range", "right": tickers},
                       {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]}],
            "columns": ["name", "description", "earnings_release_next_date", "earnings_release_next_time",
                        "earnings_per_share_forecast_next_fq", "revenue_forecast_next_fq"],
            "range": [0, 200]}).encode()
        req = urllib.request.Request(TV_SCAN, data=body, headers={"User-Agent": UA})   # simple request
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read()).get("data") or []

    def summary(self, sym):
        mods = "earningsTrend,earningsHistory,financialData,calendarEvents,recommendationTrend,upgradeDowngradeHistory"
        u = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{urllib.parse.quote(sym)}?modules={mods}&crumb={self._crumb()}"
        return json.loads(self._get(u))["quoteSummary"]["result"][0]

    def chain(self, sym, exp=None):
        u = f"https://query2.finance.yahoo.com/v7/finance/options/{urllib.parse.quote(sym)}?crumb={self._crumb()}"
        if exp:
            u += f"&date={exp}"
        return json.loads(self._get(u))["optionChain"]["result"][0]

    def nasdaq(self, sym):
        """4 הדוחות האחרונים עם תאריך פרסום אמיתי (Yahoo לא נותן תאריכים; נבדק 2.10.2026)."""
        req = urllib.request.Request(f"https://api.nasdaq.com/api/company/{urllib.parse.quote(sym)}/earnings-surprise",
                                     headers={"User-Agent": UA, "Accept": "application/json, text/plain, */*",
                                              "Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return (((json.loads(r.read()) or {}).get("data") or {}).get("earningsSurpriseTable") or {}).get("rows") or []

    def bars(self, sym):
        u = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?interval=1d&range=2y"
        res = json.loads(self._get(u))["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        out = []
        for t, c, v in zip(res["timestamp"], q["close"], q["volume"]):
            if c is None:
                continue
            out.append([datetime.fromtimestamp(t, NY).date().isoformat(), round(c, 2), v or 0])
        return out


# ---------------------------------------------------------------- עזר
def raw(v):
    return v.get("raw") if isinstance(v, dict) else v


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def bdays(a, b):
    """ימי מסחר (שני–שישי) מ-a (לא כולל) עד b (כולל). חגים לא נספרים — קירוב מספיק."""
    n, d = 0, a
    while d < b:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def market_open(now):
    ny = now.astimezone(NY)
    if ny.weekday() >= 5:
        return False
    m = ny.hour * 60 + ny.minute
    return 9 * 60 + 45 <= m <= 16 * 60


def straddle(price, opts):
    """opts = {"calls":[...], "puts":[...]} של Yahoo. מחזיר (strike, call, put, pct) ל-ATM."""
    def mid(x):
        b, a, l = x.get("bid") or 0, x.get("ask") or 0, x.get("lastPrice") or 0
        return (b + a) / 2 if b and a and a >= b else l
    pc = {x["strike"]: mid(x) for x in opts.get("calls", [])}
    pp = {x["strike"]: mid(x) for x in opts.get("puts", [])}
    common = [k for k in pc if k in pp and pc[k] and pp[k]]
    if not common or not price:
        return None
    k = min(common, key=lambda s: abs(s - price))
    return k, round(pc[k], 2), round(pp[k], 2), round((pc[k] + pp[k]) / price * 100, 2)


# ---------------------------------------------------------------- חלקים
def parse_summary(r):
    trend = (r.get("earningsTrend") or {}).get("trend") or []
    t0 = next((t for t in trend if t.get("period") == "0q"), trend[0] if trend else {})
    eps = {k: raw(v) for k, v in (t0.get("earningsEstimate") or {}).items()}
    rev = {k: raw(v) for k, v in (t0.get("revenueEstimate") or {}).items()}
    revs = {k: raw(v) for k, v in (t0.get("epsRevisions") or {}).items()}
    fd = r.get("financialData") or {}
    rt = ((r.get("recommendationTrend") or {}).get("trend") or [{}])[0]
    hist = []
    for h in (r.get("earningsHistory") or {}).get("history") or []:
        q = raw(h.get("quarter"))
        if not q:
            continue
        hist.append({"q": datetime.fromtimestamp(q, timezone.utc).date().isoformat(),
                     "actual": raw(h.get("epsActual")), "est": raw(h.get("epsEstimate")),
                     "surprise": round(raw(h.get("surprisePercent")) * 100, 1) if raw(h.get("surprisePercent")) is not None else None})
    acts = []
    for a in ((r.get("upgradeDowngradeHistory") or {}).get("history") or [])[:6]:
        acts.append({"date": datetime.fromtimestamp(a["epochGradeDate"], timezone.utc).date().isoformat(),
                     "firm": a.get("firm"), "action": a.get("action"), "grade": a.get("toGrade"),
                     "from": a.get("fromGrade"), "pt": a.get("currentPriceTarget"), "ptPrev": a.get("priorPriceTarget")})
    ce = (r.get("calendarEvents") or {}).get("earnings") or {}
    edates = [raw(x) for x in (ce.get("earningsDate") or []) if raw(x)]
    return {
        "consensus": {"eps": eps.get("avg"), "epsLow": eps.get("low"), "epsHigh": eps.get("high"),
                      "epsN": eps.get("numberOfAnalysts"), "epsYearAgo": eps.get("yearAgoEps"),
                      "rev": rev.get("avg"), "revLow": rev.get("low"), "revHigh": rev.get("high"),
                      "revN": rev.get("numberOfAnalysts"), "revYearAgo": rev.get("yearAgoRevenue"),
                      "quarterEnd": t0.get("endDate")},
        "revisions": {"up30": revs.get("upLast30days"), "down30": revs.get("downLast30days")},
        "targets": {"mean": raw(fd.get("targetMeanPrice")), "high": raw(fd.get("targetHighPrice")),
                    "low": raw(fd.get("targetLowPrice")), "n": raw(fd.get("numberOfAnalystOpinions"))},
        "recs": {k: rt.get(k) for k in ("strongBuy", "buy", "hold", "sell", "strongSell")},
        "history": sorted(hist, key=lambda h: h["q"])[-4:],
        "actions": acts,
        "yahooDate": datetime.fromtimestamp(edates[0], NY).date().isoformat() if edates else None,
    }


MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def _num(v):
    try:
        return float(str(v).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def nasdaq_history(rows):
    """שורות Nasdaq → [{q, reported, actual, est, surprise}] מהישן לחדש."""
    out = []
    for r in rows:
        try:
            mon, yr = (r.get("fiscalQtrEnd") or "").split()
            m, y = MONTHS[mon[:3]], int(yr)
            q = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).isoformat()   # סוף החודש
            mm, dd, yy = (r.get("dateReported") or "").split("/")
            rep = date(int(yy), int(mm), int(dd)).isoformat()
        except (ValueError, KeyError):
            continue
        a, e = _num(r.get("eps")), _num(r.get("consensusForecast"))
        out.append({"q": q, "reported": rep, "actual": a, "est": e,
                    "surprise": round((a / e - 1) * 100, 1) if a is not None and e else None})
    return sorted(out, key=lambda h: h["q"])[-4:]


def reactions(bars, history, when=None):
    """יום התגובה לכל רבעון. עם תאריך פרסום אמיתי (Nasdaq): יום הפרסום או יום המסחר שאחריו — מי שהמחזור
    שלו גבוה יותר (לפני הפתיחה = אותו יום, אחרי הסגירה = למחרת). בלי תאריך: יום המחזור הגבוה 5–50 יום
    אחרי סוף הרבעון (פחות מדויק — ל-JPM נתן 8.7 במקום 14.7)."""
    idx = {b[0]: i for i, b in enumerate(bars)}
    out = []
    for h in history:
        if h.get("reported"):
            i = next((k for k, b in enumerate(bars) if b[0] >= h["reported"]), None)
            if i is not None and i > 0:
                # חברות שומרות על אותה שעה בכל רבעון → לפי השעה של הדוח הבא (TradingView):
                # לפני הפתיחה = יום הדוח, אחרי הסגירה = המחרת. שעה לא ידועה — לפי המחזור הגבוה מבין השניים
                # (לבד המחזור טועה: JPM 13.1 נמכרה גם למחרת, והמחזור של 14.1 היה גבוה יותר).
                if bars[i][0] == h["reported"] and i + 1 < len(bars):
                    if when == "after" or (when is None and bars[i + 1][2] > bars[i][2]):
                        i += 1
                out.append(dict(h, day=bars[i][0], move=round((bars[i][1] / bars[i - 1][1] - 1) * 100, 2)))
                continue
        q = date.fromisoformat(h["q"])
        lo, hi = (q + timedelta(days=5)).isoformat(), (q + timedelta(days=50)).isoformat()
        cand = [i for i, b in enumerate(bars) if lo <= b[0] <= hi and i > 0]
        if not cand:
            out.append(dict(h, day=None, move=None))
            continue
        i = max(cand, key=lambda j: bars[j][2])
        out.append(dict(h, day=bars[i][0], move=round((bars[i][1] / bars[i - 1][1] - 1) * 100, 2)))
    return out, idx


def options_move(net, sym, rdate, when, now):
    """סטראדל ATM לפקיעה הראשונה שאחרי הדוח, ובניכוי התנודה הרגילה (פקיעה שלפני הדוח)."""
    base = net.chain(sym)
    price = (base.get("quote") or {}).get("regularMarketPrice")
    exps = base.get("expirationDates") or []
    rd = date.fromisoformat(rdate)
    first_after = rd + timedelta(days=1) if when == "after" else rd   # אחרי הסגירה → התגובה למחרת
    post = next((e for e in exps if datetime.fromtimestamp(e, timezone.utc).date() >= first_after), None)
    pre = max((e for e in exps if datetime.fromtimestamp(e, timezone.utc).date() < rd), default=None)
    if not post or not price:
        return None
    s_post = straddle(price, net.chain(sym, post)["options"][0])
    if not s_post:
        return None
    today = now.astimezone(NY).date()
    post_d = datetime.fromtimestamp(post, timezone.utc).date()
    res = {"asOf": now.astimezone(IL).strftime("%d/%m %H:%M"), "price": price,
           "exp": post_d.isoformat(), "strike": s_post[0], "pct": s_post[3], "earn": None,
           "preExp": None, "prePct": None}
    t_post = max(bdays(today, post_d), 1)
    if pre:
        s_pre = straddle(price, net.chain(sym, pre)["options"][0])
        pre_d = datetime.fromtimestamp(pre, timezone.utc).date()
        t_pre = max(bdays(today, pre_d), 1)
        if s_pre:
            res["preExp"], res["prePct"] = pre_d.isoformat(), s_pre[3]
            var = s_post[3] ** 2 - s_pre[3] ** 2 * (t_post - 1) / t_pre
            res["earn"] = round(math.sqrt(var), 2) if var > 0 else None
    if res["earn"] is None and t_post <= 2:
        res["earn"] = s_post[3]          # הפקיעה מיד אחרי הדוח — הסטראדל כולו הוא הדוח
    return res


def price_block(bars, spy, since_day):
    """מחיר אחרון, שינוי מאז ערב הדוח הקודם (מול S&P), שיא 52 שבועות, ממוצע 50, 80 סגירות לגרף."""
    if not bars:
        return None
    closes = [b[1] for b in bars]
    last = bars[-1]
    out = {"close": last[1], "date": last[0], "high52": max(closes[-252:]),
           "ma50": round(sum(closes[-50:]) / min(50, len(closes)), 2),
           "series": [[b[0], b[1]] for b in bars[-80:]]}
    out["off52"] = round((last[1] / out["high52"] - 1) * 100, 1)
    if since_day:
        i = next((k for k, b in enumerate(bars) if b[0] == since_day), None)
        if i and i > 0:
            base = bars[i - 1]
            out["since"] = {"from": base[0], "chg": round((last[1] / base[1] - 1) * 100, 1)}
            sb = {b[0]: b[4] for b in spy} if spy and len(spy[0]) > 4 else {}
            if base[0] in sb and last[0] in sb:
                out["since"]["spy"] = round((sb[last[0]] / sb[base[0]] - 1) * 100, 1)
    return out


# ---------------------------------------------------------------- ראשי
def main(fetch=None, now=None):
    now = now or datetime.now(timezone.utc)
    net = fetch or Net()
    reports = load(REPORTS, {}).get("reports") or []
    prev = load(OUT, {})
    prev_items = {it["sym"]: it for it in prev.get("items", [])}
    stale_ver = (prev.get("_meta") or {}).get("ver") != VER
    notes = load(os.path.join(DATA, "earnings_prep_notes.json"), {})

    # הניתוח האחרון לכל חברה
    latest = {}
    for r in reports:
        t = (r.get("ticker") or "").upper()
        if t and (t not in latest or (r.get("date") or "") > (latest[t].get("date") or "")):
            latest[t] = r
    sym_of = {t: ALIAS.get(t, t) for t in latest}
    if not latest:
        print("[skip] אין ניתוחי דוחות")
        return 0

    try:
        rows = net.tv(sorted(set(sym_of.values())))
    except Exception as e:
        print(f"[warn] TradingView נכשל ({e}) — הקובץ נשאר")
        return 0

    today = now.astimezone(NY).date()
    items, later = [], []
    for row in rows:
        sym, name, nts, ntime, tv_eps, tv_rev = row["d"]
        if not nts:
            continue
        rdate = datetime.fromtimestamp(nts, timezone.utc).astimezone(NY).date()
        when = {1: "after", -1: "before"}.get(ntime)
        last_day = rdate + timedelta(days=1 if when == "after" else 0)
        if today > last_day:
            continue
        if (rdate - today).days > AHEAD_DAYS:
            later.append({"sym": sym, "date": rdate.isoformat(), "when": when})
            continue
        rep_t = next((t for t, s in sym_of.items() if s == sym), sym)
        rep = latest[rep_t]
        old = prev_items.get(sym) or {}
        it = {"sym": sym, "name": name, "date": rdate.isoformat(), "when": when,
              "daysTo": (rdate - today).days,
              "report": {"file": rep.get("file"), "date": rep.get("date"), "title": rep.get("title"), "logo": rep.get("logo"),
                         "logoBg": rep.get("logoBg")},
              "tvConsensus": {"eps": tv_eps, "rev": tv_rev}}
        # אנליסטים + נרות: פעם ב-6 שעות לחברה
        fresh = not stale_ver and old.get("analystsAt") and \
            (now - datetime.fromisoformat(old["analystsAt"])).total_seconds() < ANALYST_EVERY_H * 3600 and \
            old.get("date") == it["date"]
        if fresh:
            for k in ("consensus", "revisions", "targets", "recs", "history", "actions", "price", "analystsAt", "yahooDate"):
                if k in old:
                    it[k] = old[k]
        else:
            try:
                it.update(parse_summary(net.summary(sym)))
                it["analystsAt"] = now.isoformat(timespec="minutes")
            except Exception as e:
                print(f"[warn] {sym}: אנליסטים נכשלו ({e})")
                for k in ("consensus", "revisions", "targets", "recs", "history", "actions", "analystsAt"):
                    if k in old:
                        it[k] = old[k]
            try:
                nh = nasdaq_history(net.nasdaq(sym))
                if len(nh) >= 2:
                    it["history"] = nh      # תאריכים אמיתיים; ה-EPS מ-Nasdaq (מתואם, כמו הצפי שלו)
            except Exception as e:
                print(f"[warn] {sym}: Nasdaq נכשל ({e}) — תאריכי התגובה יוערכו לפי מחזור")
            try:
                bars = net.bars(sym)
                spy = load(os.path.join(DATA, "bars", "SPY.json"), {}).get("bars") or []
                hist, _ = reactions(bars, it.get("history") or [], when)
                it["history"] = hist
                last_react = next((h["day"] for h in reversed(hist) if h.get("day")), None)
                it["price"] = price_block(bars, spy, last_react)
            except Exception as e:
                print(f"[warn] {sym}: נרות נכשלו ({e})")
                if "price" in old:
                    it["price"] = old["price"]
        # אופציות: רק בשעות המסחר; מחוץ להן — הערך האחרון
        it["options"] = old.get("options") if old.get("date") == it["date"] else None
        if market_open(now) or (fetch is not None and not it["options"]):
            try:
                o = options_move(net, sym, it["date"], when, now)
                if o:
                    it["options"] = o
            except Exception as e:
                print(f"[warn] {sym}: אופציות נכשלו ({e})")
        moves = [abs(h["move"]) for h in it.get("history") or [] if h.get("move") is not None]
        it["avgMove"] = round(sum(moves) / len(moves), 1) if moves else None
        n = notes.get(sym) or {}
        it["hasNote"] = n.get("forDate") == it["date"]
        items.append(it)
        print(f"[ok] {sym} {it['date']} ({when or '?'}) · צפי {((it.get('consensus') or {}).get('eps'))} · "
              f"אופציות {((it.get('options') or {}).get('earn'))} · הערות {'✓' if it['hasNote'] else '—'}")

    items.sort(key=lambda x: (x["date"], x["sym"]))
    out = {"_meta": {"updatedAt": now.astimezone(IL).strftime("%d/%m/%Y %H:%M"), "aheadDays": AHEAD_DAYS, "ver": VER,
                     "source": "TradingView (מועדים) · Yahoo Finance (אנליסטים, אופציות, נרות)"},
           "items": items, "later": sorted(later, key=lambda x: x["date"])[:12]}
    if not stale_ver and json.dumps([items, out["later"]], sort_keys=True) == json.dumps([prev.get("items", []), prev.get("later", [])], sort_keys=True):
        print("[nochange]")
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"[done] {len(items)} חברות לקראת דוח")
    return 0


if __name__ == "__main__":
    sys.exit(main())
