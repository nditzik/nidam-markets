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
TV_SCAN = "https://scanner.tradingview.com/america/scan"
IS_LIST = "https://api.github.com/repos/nditzik/indexes-status/contents/data"
IS_RAW = "https://raw.githubusercontent.com/nditzik/indexes-status/main/data/"
ANCHOR = "JPM"
WEEKS = 8
MILESTONES = [
    ("banks", "הבנקים", ["JPM", "WFC", "C", "BAC", "GS", "MS"]),
    ("nflx", None, ["NFLX", "TSLA"]),
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
        "columns": ["name", "earnings_release_date", "earnings_release_next_date"],
        "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
        "range": [0, 2500],
    }
    data = json.loads(fetch(TV_SCAN, json.dumps(body).encode(), None)).get("data") or []

    def day(ts):
        return datetime.fromtimestamp(ts, timezone.utc).astimezone(NY).date() if ts else None
    out = {}
    for row in data:
        sym, last_ts, next_ts = row["d"]
        if sym and sym not in out:
            out[sym] = (day(last_ts), day(next_ts), last_ts)
    return out


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
              "n": 0} for i in range(WEEKS)]
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
    miles = []
    for key, label, group in MILESTONES:
        ds = sorted((season_day(s)[0], s) for s in group if season_day(s)[0])
        if not ds:
            continue
        present = {x for _, x in ds}
        label = label or " · ".join(HE[x] for x in group if x in present)
        miles.append({"key": key, "label": label, "date": ds[0][0].isoformat(),
                      "syms": [s for _, s in ds], "mine": sorted(set(group) & mine)})

    q = (anchor.month - 1) // 3          # הבנקים של אוקטובר מדווחים על רבעון 3
    q, year = (4, anchor.year - 1) if q == 0 else (q, anchor.year)
    out = {"season": "רבעון %d" % q, "year": year, "start": start.isoformat(), "end": end.isoformat(),
           "anchor": {"sym": ANCHOR, "date": anchor.isoformat()}, "weeks": weeks, "milestones": miles,
           "total": total, "reported": reported, "members": len(syms),
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
