"""build_earnings_season.py — ציר "עונת הדוחות" בבית (3.10.2026, איציק).

פלט: data/earnings_season.json — שמונה שבועות של עונת דוחות, כמה חברות מה-S&P 500 מדווחות
בכל שבוע, כמה כבר דיווחו, ו-6 "תחנות" (בנקים, נטפליקס·טסלה, הענקיות, אפל·אמזון, אנבידיה,
וולמארט). האתר מציג את הציר מתחת לכותרת הראשית רק בזמן העונה (renderSeason ב-app.js).

העונה מעוגנת לג'יי-פי מורגן: מי שפותחת כל עונה. אם JPM דיווחה ב-70 הימים האחרונים — העונה
היא סביב הדוח האחרון; אחרת סביב הדוח הבא. תחילת העונה = יום שני של השבוע שלפני שבוע הדוח.

מקורות:
- רשימת חברות המדד: קובץ ה-watchlist היומי של S&P 500 ב-indexes-status (אותו קובץ שמזין את
  מד השוק), נשמר ב-data/sp500.json ומתרענן פעם ביום; כשל = הרשימה הקודמת נשארת.
- מועדי הדוחות: סורק TradingView (כמו fetch_earnings.py) — earnings_release_date (האחרון) ו-
  earnings_release_next_date (הבא). חברה שדיווחה בעונה = התאריך האחרון שלה בתוך העונה.

כשל משיכה = הקובץ הקיים נשאר. בדיקה בלי רשת: main(fetch=..., now=...).
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gh_api import gh_headers  # noqa: E402
from iltime import IL, NY  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "earnings_season.json")
SP_CACHE = os.path.join(DATA, "sp500.json")
HOLDINGS = os.path.join(DATA, "holdings.txt")
# הטיקרים בתוך עמודות הציר (np112, אושר במוקאפ 2): עד 5 לשבוע — חברות התחנות (חוץ מהבנקים, שהם
# כותרת) ואחריהן הגדולות במדד מעל $300B, לפי שווי; ובנוסף מניות המעקב מ-data/holdings.txt, בלי הבלטה.
TOP_PER_WEEK = 5
BIG_CAP_B = 300
TV_SCAN = "https://scanner.tradingview.com/america/scan"
IS_LIST = "https://api.github.com/repos/nditzik/indexes-status/contents/data"
IS_RAW = "https://raw.githubusercontent.com/nditzik/indexes-status/main/data/"
ANCHOR = "JPM"
WEEKS = 8
MILESTONES = [
    ("banks", "הבנקים", ["JPM", "WFC", "C", "BAC", "GS", "MS"]),
    ("tsla", None, ["TSLA"]),            # 3.10.2026: טסלה דיווחה ב-2.10, לפני תחילת העונה — תחנה משלה
    ("nflx", None, ["NFLX"]),
    ("mega", None, ["MSFT", "GOOGL", "META"]),
    ("aapl", None, ["AAPL", "AMZN"]),
    ("nvda", None, ["NVDA"]),
    ("wmt", None, ["WMT"]),
]
# תווית התחנה = השמות של מי שבאמת מדווחת בעונה (3.10: טסלה עוד בלי מועד בסורק — "נטפליקס" לבד)
HE = {"NFLX": "נטפליקס", "TSLA": "טסלה", "MSFT": "מיקרוסופט", "GOOGL": "גוגל", "META": "מטא",
      "AAPL": "אפל", "AMZN": "אמזון", "NVDA": "אנבידיה", "WMT": "וולמארט"}


def _get(url, data=None, headers=None):
    h = {"User-Agent": "Mozilla/5.0"}
    h.update(headers or {})
    if data is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def sp500(fetch, today):
    """רשימת חברות המדד — מהמטמון, ומתרעננת פעם ביום מקובץ ה-watchlist האחרון."""
    cache = load(SP_CACHE) or {}
    if cache.get("checked") == today and cache.get("symbols"):
        return [x for x in cache["symbols"] if not x.startswith("$")]
    try:
        files = json.loads(fetch(IS_LIST, None, gh_headers(IS_LIST)))
        names = [f["name"] for f in files if f.get("name", "").startswith("watchlist-sp-500") and f["name"].endswith(".csv")]

        def key(n):   # watchlist-sp-500-intraday-MM-DD-YYYY.csv
            p = n[:-4].split("-")
            return (p[-1], p[-3], p[-2])
        if names:
            name = max(names, key=key)
            import csv
            import io
            rows = list(csv.DictReader(io.StringIO(fetch(IS_RAW + name, None, None))))
            syms = sorted({(r.get("Symbol") or "").strip() for r in rows})
            syms = [s for s in syms if s and not s.startswith("$") and " " not in s and len(s) <= 6]
            if len(syms) >= 400:          # קובץ חלקי/שבור לא דורס רשימה תקינה
                cache = {"symbols": syms, "source": name}
    except Exception as e:
        print(f"[warn] רשימת S&P 500 לא רועננה ({e}) — משתמש במטמון")
    if not cache.get("symbols"):
        return []
    cache["symbols"] = [x for x in cache["symbols"] if not x.startswith("$")]
    cache["checked"] = today
    with open(SP_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, separators=(",", ":"))
    return cache["symbols"]


def tv_dates(fetch):
    """{סמל: (תאריך-אחרון, תאריך-הבא)} בשעון ניו יורק, לכל מניה אמריקאית מעל $2B."""
    body = {
        "filter": [
            {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]},
            {"left": "type", "operation": "in_range", "right": ["stock", "dr"]},
            {"left": "market_cap_basic", "operation": "greater", "right": 2e9},
        ],
        # שלב 2 (3.10.2026): בפועל מול צפי של הרבעון האחרון — נבדק ב-probe_surprise.py על ה-runner
        "columns": ["name", "earnings_release_date", "earnings_release_next_date", "earnings_release_time",
                    "eps_surprise_percent_fq", "revenue_surprise_percent_fq", "sector", "market_cap_basic"],
        "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
        "range": [0, 2500],
    }
    data = json.loads(fetch(TV_SCAN, json.dumps(body).encode(), None)).get("data") or []

    def day(ts):
        return datetime.fromtimestamp(ts, timezone.utc).astimezone(NY).date() if ts else None
    out, extra = {}, {}
    for row in data:
        sym, last_ts, next_ts, t_flag, eps_s, rev_s, sector, cap = row["d"]
        if sym and sym not in out:
            out[sym] = (day(last_ts), day(next_ts), last_ts)
            extra[sym] = {"when": {1: "after", -1: "before"}.get(t_flag), "eps": eps_s, "rev": rev_s, "sector": sector,
                          "capB": round(cap / 1e9) if cap else None}
    tv_dates.extra = extra
    return out


# ---------- שלב 2: לוח התוצאות (3.10.2026) ----------
# סקטורי TradingView → 11 הסקטורים שבשאר האתר (גוגל ומטא יושבות אצל TV ב-Technology Services)
SECTOR_HE = {
    "Technology Services": "טכנולוגיה", "Electronic Technology": "טכנולוגיה", "Finance": "פיננסים",
    "Health Technology": "בריאות", "Health Services": "בריאות", "Retail Trade": "צריכה מחזורית",
    "Consumer Durables": "צריכה מחזורית", "Consumer Services": "צריכה מחזורית",
    "Consumer Non-Durables": "צריכה בסיסית", "Energy Minerals": "אנרגיה", "Utilities": "תשתיות",
    "Producer Manufacturing": "תעשייה", "Industrial Services": "תעשייה", "Transportation": "תעשייה",
    "Commercial Services": "תעשייה", "Distribution Services": "תעשייה", "Process Industries": "חומרים",
    "Non-Energy Minerals": "חומרים", "Communications": "תקשורת", "Miscellaneous": "אחר",
}
REACT_CACHE = os.path.join(DATA, "_season_react.json")
MAX_BARS_PER_RUN = 60


def reaction(fetch, sym, d, when, now):
    """תגובת המניה לדוח: לפני הפתיחה = סגירת יום הדוח מול היום שלפניו; אחרי הסגירה = סגירת
    יום המסחר הבא מול יום הדוח (כמו reactions() ב-fetch_earnings). None = עוד לא נסגר / חסר."""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + sym.replace(".", "-") + "?interval=1d&range=1mo"
    res = json.loads(fetch(url, None, None))["chart"]["result"][0]
    days = [datetime.fromtimestamp(t, timezone.utc).astimezone(NY).date() for t in res["timestamp"]]
    closes = res["indicators"]["quote"][0]["close"]
    bars = [(dd, c) for dd, c in zip(days, closes) if c]
    idx = next((i for i, (dd, _) in enumerate(bars) if dd >= d), None)
    if idx is None:
        return None
    if when == "after":
        idx += 1
    if idx <= 0 or idx >= len(bars):
        return None
    rday = bars[idx][0]
    ny = now.astimezone(NY)
    if rday > ny.date() or (rday == ny.date() and (ny.hour, ny.minute) < (16, 20)):
        return None                                   # סשן התגובה עוד פתוח
    return round((bars[idx][1] / bars[idx - 1][1] - 1) * 100, 2)


def scoreboard(fetch, now, start, end, syms, tv, extra, season_day):
    """כמה דיווחו, כמה עקפו את צפי הרווח/ההכנסות, לפי סקטור, ו"פרס מול עונש" — התגובה
    הממוצעת ביום הדוח אחרי עקיפה ואחרי החטאה. התגובות נשמרות במטמון ומחושבות פעם אחת למניה."""
    cache = load(REACT_CACHE) or {}
    key = start.isoformat()
    if cache.get("season") != key:
        cache = {"season": key, "react": {}}
    rows, fetched = [], 0
    for s in syms:
        d, done = season_day(s)
        if not (d and done):
            continue
        x = extra.get(s) or {}
        r = cache["react"].get(s)
        if (r is None or r.get("d") != d.isoformat() or r.get("v") is None) and x.get("when") and fetched < MAX_BARS_PER_RUN:
            fetched += 1
            try:
                cache["react"][s] = {"d": d.isoformat(), "v": reaction(fetch, s, d, x["when"], now)}
            except Exception as e:
                print(f"[warn] תגובה {s}: {e}")
        r = cache["react"].get(s) or {}
        rows.append({"sym": s, "eps": x.get("eps"), "rev": x.get("rev"),
                     "sector": SECTOR_HE.get(x.get("sector") or "", "אחר"),
                     "react": r.get("v") if r.get("d") == d.isoformat() else None})
    with open(REACT_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, separators=(",", ":"))

    def pct(a, b):
        return round(a / b * 100) if b else None

    def avg(v):
        return round(sum(v) / len(v), 2) if v else None
    eps = [r for r in rows if r["eps"] is not None]
    rev = [r for r in rows if r["rev"] is not None]
    beat = [r for r in eps if r["eps"] > 0]
    miss = [r for r in eps if r["eps"] < 0]
    sect = {}
    for r in eps:
        g = sect.setdefault(r["sector"], [0, 0])
        g[0] += 1
        g[1] += 1 if r["eps"] > 0 else 0
    sectors = sorted(({"name": k, "n": v[0], "beat": v[1]} for k, v in sect.items() if k != "אחר"),
                     key=lambda z: (-z["n"], z["name"]))
    rb = [r["react"] for r in beat if r["react"] is not None]
    rm = [r["react"] for r in miss if r["react"] is not None]
    top = sorted((r for r in eps if r["react"] is not None), key=lambda r: -abs(r["react"]))[:6]
    return {"reported": len(rows), "epsN": len(eps), "epsBeat": len(beat), "epsBeatPct": pct(len(beat), len(eps)),
            "revN": len(rev), "revBeat": sum(1 for r in rev if r["rev"] > 0),
            "revBeatPct": pct(sum(1 for r in rev if r["rev"] > 0), len(rev)),
            "reactBeat": avg(rb), "reactBeatN": len(rb), "reactMiss": avg(rm), "reactMissN": len(rm),
            "sectors": sectors,
            "movers": [{"sym": r["sym"], "react": r["react"], "eps": round(r["eps"], 1)} for r in top]}



def main(fetch=None, now=None):
    fetch = fetch or (lambda url, data, headers: _get(url, data, headers))
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(NY).date()
    syms = sp500(fetch, today.isoformat())
    if len(syms) < 400:
        print(f"[skip] רשימת S&P 500 חסרה ({len(syms)}) — משאיר את הקובץ הקיים")
        return 0
    try:
        tv = tv_dates(fetch)
    except Exception as e:
        print(f"[skip] סורק TradingView נכשל ({e}) — משאיר את הקובץ הקיים")
        return 0
    if ANCHOR not in tv:
        print("[skip] אין מועד ל-JPM בסורק — משאיר את הקובץ הקיים")
        return 0
    last, nxt, _ = tv[ANCHOR]
    anchor = last if (last and 0 <= (today - last).days <= 70) else nxt
    if not anchor:
        print("[skip] אין עוגן לעונה")
        return 0
    start = anchor - timedelta(days=anchor.weekday() + 7)          # שני של השבוע שלפני הבנקים
    end = start + timedelta(days=WEEKS * 7 - 1)

    def season_day(sym):
        """תאריך הדוח של החברה בתוך העונה (+ האם כבר פורסם), או None."""
        if sym not in tv:
            return None, False
        l, n, l_ts = tv[sym]
        if l and start <= l <= end:
            return l, l_ts <= now.timestamp()
        if n and start <= n <= end:
            return n, False
        return None, False

    weeks = [{"mon": (start + timedelta(days=7 * i)).isoformat(),
              "label": "%d.%d" % ((start + timedelta(days=7 * i)).day, (start + timedelta(days=7 * i)).month),
              "n": 0, "tickers": []} for i in range(WEEKS)]
    total = reported = 0
    for s in syms:
        d, done = season_day(s)
        if not d:
            continue
        total += 1
        reported += 1 if done else 0
        weeks[min(WEEKS - 1, (d - start).days // 7)]["n"] += 1

    mine = set()
    rep = load(os.path.join(DATA, "reports.json")) or {}
    for r in rep.get("reports") or rep.get("items") or []:
        if isinstance(r, dict) and r.get("ticker"):
            mine.add(str(r["ticker"]).upper())

    # מי מדווחת בכל שבוע (3.10.2026, איציק: "הטיקרים בתוך העמודות") → weeks[].tickers
    held = set()
    try:
        with open(HOLDINGS, encoding="utf-8") as f:
            for line in f:
                held.update(x.strip().upper() for x in line.split("#")[0].replace(",", " ").split() if x.strip())
    except OSError:
        pass
    members = set(syms)
    xtra = getattr(tv_dates, "extra", {})
    ms_syms = {x for key, _, group in MILESTONES if key != "banks" for x in group}
    cand = [[] for _ in range(WEEKS)]
    extra_held = [[] for _ in range(WEEKS)]
    for sym in tv:                       # סדר הסורק = שווי יורד
        if sym == "GOOG":                # אותה חברה כמו GOOGL
            continue
        d, _ = season_day(sym)
        if not d:
            continue
        i = min(WEEKS - 1, (d - start).days // 7)
        cap = (xtra.get(sym) or {}).get("capB") or 0
        if sym in held:
            extra_held[i].append(sym)
        elif sym in members and (sym in ms_syms or cap >= BIG_CAP_B):
            cand[i].append((0 if sym in ms_syms else 1, -cap, sym))
    for i, w in enumerate(weeks):
        top = sorted(cand[i])[:TOP_PER_WEEK]
        caps = {s_: -c for _, c, s_ in top}
        w["tickers"] = sorted(caps, key=lambda s_: -caps[s_]) + extra_held[i]
    def mile_day(sym):
        """כמו season_day, אבל לתחנות מתקבל גם דוח מהשבועיים שלפני תחילת העונה (טסלה 2.10) —
        הוא מצויר בקצה הימני של הציר כתחנה שכבר עברה."""
        if sym not in tv:
            return None
        l, n, _ = tv[sym]
        for d in (l, n):
            if d and start - timedelta(days=14) <= d <= end:
                return d
        return None

    miles = []
    for key, label, group in MILESTONES:
        ds = sorted((mile_day(s), s) for s in group if mile_day(s))
        if not ds:
            continue
        present = {x for _, x in ds}
        label = label or " · ".join(HE[x] for x in group if x in present)
        miles.append({"key": key, "label": label, "date": ds[0][0].isoformat(),
                      "syms": [s for _, s in ds], "mine": sorted(set(group) & mine)})
    miles.sort(key=lambda m: m["date"])

    board = scoreboard(fetch, now, start, end, syms, tv, getattr(tv_dates, "extra", {}), season_day)

    q = (anchor.month - 1) // 3          # הבנקים של אוקטובר מדווחים על רבעון 3
    q, year = (4, anchor.year - 1) if q == 0 else (q, anchor.year)
    out = {"season": "רבעון %d" % q, "year": year, "start": start.isoformat(), "end": end.isoformat(),
           "anchor": {"sym": ANCHOR, "date": anchor.isoformat()}, "weeks": weeks, "milestones": miles,
           "total": total, "reported": reported, "members": len(syms), "board": board,
           "_meta": {"updatedAt": now.astimezone(IL).strftime("%d/%m/%Y %H:%M"), "source": "TradingView + S&P 500 watchlist"}}
    prev = load(OUT) or {}
    if {k: v for k, v in prev.items() if k != "_meta"} == {k: v for k, v in out.items() if k != "_meta"}:
        print("[same] עונת הדוחות לא השתנתה")
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"[done] {out['season']} {start}–{end}: {reported}/{total} דיווחו · " +
          " · ".join("%s %d" % (w["label"], w["n"]) for w in weeks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
