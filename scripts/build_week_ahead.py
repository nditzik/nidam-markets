#!/usr/bin/env python3
"""
build_week_ahead.py — חבילת הראיות לצפי השבועי (20.9.2026) → data/week_ahead.json

הרוטינה של יום ראשון ("לקראת שבוע המסחר") קוראת את הקובץ הזה וכותבת ממנו את
eventUpdate.forecast. הסקריפט דטרמיניסטי: הוא אוסף ומחשב, לא מסיק.

מה בפנים:
  seasonality — מה עשה S&P 500 באותו שבוע בדיוק בכל שנה מאז 1990. "אותו שבוע" =
                אותו מרחק בשבועות מהפקיעה החודשית (יום שישי השלישי) של אותו חודש,
                כך ששבוע-אחרי-הפקיעה-המשולשת של ספטמבר מושווה לעצמו ולא לתאריך קלנדרי.
  state       — המד, רוחב, אופציות (SPY), אזהרת SPX, ימי מכירה, VIX, סקטורים (מהאתר).
  knn         — תחזית מודל הדמיון ל-20 יום + הרקורד שלו (מדשבורד המדדים).
  calendar    — מאקרו ומדווחות של השבוע הקרוב.
  weekend     — כותרות סוף השבוע שהאתר אסף (pulse/news/briefing) + web: סריקת Google News לפי נושא
                (טראמפ, AI, פד, סין, גיאופוליטיקה, נפט, ענקיות, "week ahead", אנשים משפיעים). לרוטינה אין רשת.
  record      — המאזן של הצפיות הקודמות (data/forecasts.json).

רץ בכל מחזור של הבוט אבל עובד רק בשבת/ראשון (או כשהקובץ חסר / --force). כשל רשת → משאיר את הקיים.
"""
import json
import os
import statistics
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "week_ahead.json")
KNN_URL = "https://raw.githubusercontent.com/nditzik/indexes-status/main/data/knn_forecast.json"
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?period1=631152000&period2=4102444800&interval=1d"
MONTH_HE = ["", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]


def il_now():
    now = datetime.now(timezone.utc)
    return now + timedelta(hours=3 if 4 <= now.month <= 10 else 2)


def load(name, default=None):
    try:
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 nidam-markets-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


# סריקת הרשת של סוף השבוע (20.9.2026): לרוטינה אין גישה לרשת, אז הבוט סורק בשבילה — Google News RSS,
# שלושה ימים אחורה. הנושאים = מה שמזיז שוק בסוף שבוע: טראמפ, הפד, סין, גיאופוליטיקה, נפט, AI, "week ahead".
WEB_QUERIES = [
    ("trump", "Trump markets OR tariffs OR economy"), ("trumpAI", "Trump AI"), ("fed", "Federal Reserve rate OR Powell OR Fed speakers"),
    ("china", "US China trade talks OR Xi"), ("geopolitics", "Middle East OR Iran OR Houthi OR Ukraine oil markets"),
    ("oil", "oil prices Brent"), ("bigtech", "Nvidia OR Apple OR Microsoft OR Tesla stock"),
    ("weekAhead", "stock market week ahead Wall Street"), ("influencers", "Musk OR Bessent OR Dimon OR Buffett markets"),
]


def web_scan():
    import re
    import urllib.parse
    from email.utils import parsedate_to_datetime
    out, seen = {}, set()
    for key, q in WEB_QUERIES:
        try:
            u = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:3d") + "&hl=en-US&gl=US&ceid=US:en"
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                x = r.read().decode("utf-8", "ignore")
            rows = []
            for t, d in re.findall(r"<item><title>(.*?)</title>.*?<pubDate>(.*?)</pubDate>", x, re.S):
                t = t.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
                k = t.lower()[:60]
                if k in seen:
                    continue
                seen.add(k)
                try:
                    ts = parsedate_to_datetime(d)
                except Exception:
                    continue
                rows.append((ts, t))
            rows.sort(reverse=True)
            out[key] = [{"t": ts.strftime("%m-%d %H:%M"), "title": t} for ts, t in rows[:12]]
        except Exception as e:
            print(f"[warn] web scan {key}: {e}")
    return out


def third_friday(y, m):
    d = date(y, m, 1)
    fridays = [d + timedelta(n) for n in range(31) if (d + timedelta(n)).month == m and (d + timedelta(n)).weekday() == 4]
    return fridays[2]


def stats(a):
    if not a:
        return None
    return {"n": len(a), "avg": round(statistics.mean(a), 2), "median": round(statistics.median(a), 2),
            "upPct": round(100 * sum(x > 0 for x in a) / len(a)), "up": sum(x > 0 for x in a)}


def seasonality(monday):
    r = get_json(YAHOO)["chart"]["result"][0]
    rows = [(datetime.fromtimestamp(t, timezone.utc).date(), c)
            for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c]
    dates = [d for d, _ in rows]

    def close_on_or_before(d):
        import bisect
        i = bisect.bisect_right(dates, d) - 1
        return rows[i][1] if i >= 0 else None

    fri = monday + timedelta(4)
    k = round((fri - third_friday(fri.year, fri.month)).days / 7)   # 0 = שבוע הפקיעה, +1 = השבוע שאחריה
    per_year, mondays = [], []
    for y in range(1990, fri.year):
        f = third_friday(y, fri.month) + timedelta(7 * k)
        a, b = close_on_or_before(f - timedelta(7)), close_on_or_before(f)
        m1 = close_on_or_before(f - timedelta(4))
        if a and b:
            per_year.append({"year": y, "pct": round((b / a - 1) * 100, 2)})
            if m1:
                mondays.append((m1 / a - 1) * 100)
    allw = [(rows[i + 5][1] / rows[i][1] - 1) * 100 for i in range(0, len(rows) - 5, 5)]
    quad = fri.month in (3, 6, 9, 12)
    rel = {0: "שבוע הפקיעה החודשית", 1: "השבוע שאחרי הפקיעה החודשית", -1: "השבוע שלפני הפקיעה החודשית"}.get(
        k, "שבוע %+d ביחס לפקיעה החודשית" % k)
    return {"label": "%s של %s%s" % (rel, MONTH_HE[fri.month], " (פקיעה רבעונית משולשת)" if quad else ""),
            "weeksFromOpex": k, "since": 1990,
            "all": stats([p["pct"] for p in per_year]),
            "last15": stats([p["pct"] for p in per_year[-15:]]),
            "last10": per_year[-10:],
            "mondayOnly": stats(mondays),
            "baselineAnyWeek": stats(allw),
            "lastClose": {"date": str(rows[-1][0]), "close": round(rows[-1][1], 2)}}


def main():
    now = il_now()
    force = "--force" in sys.argv
    if not force and now.weekday() not in (5, 6) and os.path.exists(OUT):   # 5=שבת, 6=ראשון
        print("[skip] לא סוף שבוע")
        return 0
    today = now.date()
    monday = today + timedelta((7 - today.weekday()) % 7 or 7) if today.weekday() != 0 else today
    prev = load("week_ahead.json") or {}
    # בנייה אחת ביום, ועוד אחת אחרי 14:00 — כדי שהרוטינה של ראשון 14:45 תקבל כותרות טריות
    pm = prev.get("_meta", {})
    if not force and prev.get("weekOf") == str(monday) and pm.get("builtDay") == str(today) and (now.hour < 14 or pm.get("builtHour", 0) >= 14):
        print("[skip] כבר נבנה היום")
        return 0

    out = {"weekOf": str(monday), "weekLabel": "%d–%d.%d" % (monday.day, (monday + timedelta(4)).day, (monday + timedelta(4)).month)}
    try:
        out["seasonality"] = seasonality(monday)
    except Exception as e:
        print(f"[warn] עונתיות נכשלה: {e}")
        out["seasonality"] = prev.get("seasonality") if prev.get("weekOf") == str(monday) else None

    ind = load("indices.json") or {}
    wk = load("weekly.json") or {}
    fl = ind.get("flow") or {}
    out["state"] = {
        "date": ind.get("date"), "scores": ind.get("scores"), "evidence": ind.get("evidence"),
        "sellDays": (ind.get("riskOff") or {}).get("count") or (ind.get("conclusion") or {}).get("subline"),
        "options": {"dailyScore": (ind.get("scores") or {}).get("flow"), "meterScore": fl.get("meterScore"),
                    "bigMoney": fl.get("deltaLabel"), "newMoney": fl.get("openLabel"), "spxWarning": fl.get("spxWarning")},
        "rotation": ind.get("rotation"),
        "lastWeek": {"label": wk.get("label"), "summary": wk.get("summary"), "sectors": wk.get("sectors")},
    }
    try:
        k = get_json(KNN_URL)
        m = [s for s in k.get("series", []) if s.get("actual") is not None]
        out["knn"] = {"horizonDays": k.get("horizon"), "latest": (k.get("series") or [None])[-1],
                      "record": {"matured": len(m),
                                 "directionHitPct": round(100 * sum((s["fcMedian"] > 0) == (s["actual"] > 0) for s in m) / len(m)) if m else None,
                                 "avgForecast": round(statistics.mean(s["fcMedian"] for s in m), 2) if m else None,
                                 "avgActual": round(statistics.mean(s["actual"] for s in m), 2) if m else None}}
    except Exception as e:
        print(f"[warn] KNN נכשל: {e}")
        out["knn"] = prev.get("knn")

    end = str(monday + timedelta(6))
    econ = [e for e in (load("econ.json") or {}).get("events", []) if e.get("actual") is None and str(monday) <= str(e.get("date", ""))[:10] <= end]
    earn = load("earnings.json") or {}
    out["calendar"] = {"macro": econ, "earnings": [u for u in earn.get("upcoming", []) if str(monday) <= u.get("date", "") <= end],
                       "note": "יומן המאקרו כאן חלקי (אירועים מרכזיים בלבד) — להשלים בחיפוש: נאומי פד, נתונים משניים, פגישות מדיניות"}
    br = load("briefing.json") or {}
    out["weekend"] = {
        "pulse": [{"t": p.get("dt", "")[:16], "src": p.get("source"), "text": p.get("text")} for p in (load("pulse.json") or {}).get("items", [])[:40]],
        "news": [n.get("title") for n in (load("news.json") or {}).get("news", [])[:20]],
        "briefings": {k: {"sentiment": (br.get(k) or {}).get("sentiment"), "headlines": (br.get(k) or {}).get("headlines")} for k in ("morning", "afternoon")},
    }
    web = web_scan()
    out["weekend"]["web"] = web if web else (prev.get("weekend") or {}).get("web")
    out["weekend"]["webNote"] = "כותרות Google News מ-3 הימים האחרונים לפי נושא (שעות UTC). כותרת בלבד — אל תמציא פרטים שלא כתובים בה."
    fc = load("forecasts.json") or {}
    out["record"] = {"record": fc.get("record"), "last": fc.get("last"), "history": (fc.get("items") or [])[-8:]}
    out["_meta"] = {"updatedAt": now.strftime("%d/%m/%Y %H:%M"), "builtDay": str(today), "builtHour": now.hour, "source": "build_week_ahead"}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    s = (out.get("seasonality") or {}).get("all") or {}
    print(f"[done] week_ahead {out['weekOf']} · עונתיות: עלה ב-{s.get('up')}/{s.get('n')} ({s.get('avg')}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
