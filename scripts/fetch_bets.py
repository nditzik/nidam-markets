#!/usr/bin/env python3
"""
fetch_bets.py — "מה השווקים מהמרים": הסתברויות משוקי חיזוי → data/bets.json.

מקור: Polymarket Gamma API (ציבורי, ללא מפתח). מחיר ה-YES של חוזה = ההסתברות
שהשוק מתמחר; oneDayPriceChange = השינוי היומי בנקודות הסתברות.

שלושה שווקים (נבדקו 10/08/2026):
  • fed-decision-in-september-762 — החלטת הפד הקרובה (התוצאה המובילה)
  • how-many-fed-rate-cuts-in-2026 — מספר הורדות עד סוף השנה (ההימור המוביל)
  • fed-rate-hike-in-2026 — הסתברות להעלאת ריבית השנה

עמידות: כשל משיכה → משאיר bets.json קיים. כתיבה מודעת-תוכן.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "bets.json")
API = "https://gamma-api.polymarket.com/events?slug="
KALSHI = "https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker="
UA = {"User-Agent": "Mozilla/5.0 (compatible; nidam-markets-bot)", "Accept": "application/json"}

MONTH_EN = ["january", "february", "march", "april", "may", "june", "july",
            "august", "september", "october", "november", "december"]

OUTCOME_HE = {
    "50+ bps decrease": "הורדה של 50+ נ\"ב",
    "25 bps decrease": "הורדה של 25 נ\"ב",
    "No change": "ללא שינוי",
    "25 bps increase": "העלאה של 25 נ\"ב",
    "50+ bps increase": "העלאה של 50+ נ\"ב",
}


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def get_event(slug):
    req = urllib.request.Request(API + slug, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        evs = json.loads(r.read().decode("utf-8"))
    return evs[0] if evs else None


def yes_price(m):
    try:
        return float(json.loads(m.get("outcomePrices") or "[]")[0])
    except Exception:
        return None


def leading(markets):
    """(שוק, מחיר-YES) של התוצאה עם ההסתברות הגבוהה ביותר בקבוצה."""
    best = None
    for m in markets or []:
        p = yes_price(m)
        if p is not None and (best is None or p > best[1]):
            best = (m, p)
    return best


def chg_pp(m):
    c = m.get("oneDayPriceChange")
    return round(c * 100, 1) if c is not None else None


def kalshi_prob(m):
    """הסתברות YES משוק Kalshi: מחיר אחרון, או אמצע קנייה/מכירה (סנטים→0..1)."""
    lp = m.get("last_price")
    if lp:
        return lp / 100.0
    yb, ya = m.get("yes_bid"), m.get("yes_ask")
    if yb and ya and 0 < yb <= 100 and 0 < ya <= 100:
        return (yb + ya) / 200.0
    return None


def cpi_row():
    """אינפלציה שנתית (Kalshi KXCPIYOY): הרף הגבוה ביותר שהשוק נותן לו 50%+.
    בלי נזילות → אין שורה."""
    req = urllib.request.Request(KALSHI + "KXCPIYOY&status=open&limit=100", headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        markets = json.loads(r.read().decode("utf-8")).get("markets", [])
    events = {}
    for m in markets:
        events.setdefault(m.get("event_ticker") or m.get("ticker", "")[:14], []).append(m)
    if not events:
        return None
    # האירוע הקרוב ביותר לסגירה = ההדפסה הקרובה
    ev = min(events.values(), key=lambda ms: min(m.get("close_time") or "9999" for m in ms))
    best = None
    for m in ev:
        mt = re.search(r"T(\d+(?:\.\d+)?)$", m.get("ticker") or "")
        p = kalshi_prob(m)
        if not mt or p is None:
            continue
        thr = float(mt.group(1))
        if p >= 0.5 and (best is None or thr > best[0]):
            best = (thr, p, m)
    if not best:
        return None
    month = ""
    mm = re.search(r"-26([A-Z]{3})-", best[2].get("ticker") or "")
    heb = {"JAN": "ינואר", "FEB": "פברואר", "MAR": "מרץ", "APR": "אפריל", "MAY": "מאי", "JUN": "יוני",
           "JUL": "יולי", "AUG": "אוגוסט", "SEP": "ספטמבר", "OCT": "אוקטובר", "NOV": "נובמבר", "DEC": "דצמבר"}
    if mm:
        month = heb.get(mm.group(1), "")
    return {"key": "cpi_next", "label": "אינפלציה שנתית — נתון " + (month or "הבא"),
            "sub": f"ההימור: תישאר מעל {best[0]}%", "pct": round(best[1] * 100), "chg": None,
            "src": "Kalshi"}


def spy_row():
    """יעד SPY חודשי (Polymarket): רף ה-'יגע ב-' הגבוה ביותר עם 50%+ (או המוביל)."""
    now = datetime.now(timezone.utc) + timedelta(hours=3)
    slug = f"what-price-will-spy-hit-in-{MONTH_EN[now.month - 1]}-{now.year}"
    ev = get_event(slug)
    if not ev:
        return None
    ups = []
    for m in ev.get("markets") or []:
        t = m.get("groupItemTitle") or ""
        p = yes_price(m)
        mt = re.search(r"[↑⬆]\s*\$?(\d+)", t)
        if mt and p is not None and p < 0.995:   # רפים שכבר נגעו (p=1) לא מעניינים
            ups.append((int(mt.group(1)), p, m))
    if not ups:
        return None
    over = [u for u in ups if u[1] >= 0.5]
    best = max(over, key=lambda u: u[0]) if over else max(ups, key=lambda u: u[1])
    return {"key": "spy_hit", "label": "יעד S&P החודש (SPY)",
            "sub": f"ההימור: יגע ב-${best[0]}", "pct": round(best[1] * 100),
            "chg": chg_pp(best[2])}


def cuts_label(title):
    # "0 (0 bps)" → "0 הורדות" ; "1 (25 bps)" → "הורדה אחת" ; "2 (50 bps)" → "2 הורדות"
    n = str(title).split(" ")[0]
    if n == "0":
        return "0 הורדות"
    if n == "1":
        return "הורדה אחת"
    return f"{n} הורדות"


def main():
    rows = []
    try:
        ev = get_event("fed-decision-in-september-762")
        best = leading(ev.get("markets")) if ev else None
        if best:
            m, p = best
            title = m.get("groupItemTitle") or ""
            # התפלגות מלאה: כל התוצאות עם 1%+ (ממוינות), כדי שרואים על מה ההימור
            dist = []
            for mk in ev.get("markets") or []:
                mp = yes_price(mk)
                if mp is not None and mp >= 0.01:
                    t = mk.get("groupItemTitle") or ""
                    dist.append({"label": OUTCOME_HE.get(t, t), "pct": round(mp * 100), "chg": chg_pp(mk)})
            dist.sort(key=lambda x: -x["pct"])
            rows.append({
                "key": "fed_next", "label": "החלטת הפד בספטמבר",
                "sub": "ההימור המוביל: " + OUTCOME_HE.get(title, title),
                "pct": round(p * 100), "chg": chg_pp(m), "dist": dist,
            })
    except Exception as e:
        print(f"[warn] sept: {e}")
    try:
        ev = get_event("how-many-fed-rate-cuts-in-2026")
        best = leading(ev.get("markets")) if ev else None
        if best:
            m, p = best
            rows.append({
                "key": "cuts_2026", "label": "הורדות ריבית עד סוף 2026",
                "sub": "ההימור המוביל: " + cuts_label(m.get("groupItemTitle") or ""),
                "pct": round(p * 100), "chg": chg_pp(m),
            })
    except Exception as e:
        print(f"[warn] cuts: {e}")
    try:
        ev = get_event("fed-rate-hike-in-2026")
        m = (ev.get("markets") or [None])[0] if ev else None
        p = yes_price(m) if m else None
        if p is not None:
            rows.append({
                "key": "hike_2026", "label": "העלאת ריבית עד סוף 2026",
                "sub": "הסתברות ל-YES",
                "pct": round(p * 100), "chg": chg_pp(m),
            })
    except Exception as e:
        print(f"[warn] hike: {e}")
    try:
        r = cpi_row()
        if r:
            rows.append(r)
    except Exception as e:
        print(f"[warn] cpi: {e}")
    try:
        ev = get_event("us-recession-by-end-of-2026")
        m = (ev.get("markets") or [None])[0] if ev else None
        p = yes_price(m) if m else None
        if p is not None:
            rows.append({"key": "recession", "label": "מיתון בארה\"ב עד סוף 2026",
                         "sub": "הסתברות ל-YES", "pct": round(p * 100), "chg": chg_pp(m)})
    except Exception as e:
        print(f"[warn] recession: {e}")
    try:
        r = spy_row()
        if r:
            rows.append(r)
    except Exception as e:
        print(f"[warn] spy: {e}")

    if not rows:
        print("[keep] אין נתונים — משאיר bets.json קיים." if os.path.exists(OUT) else "[fail] אין נתונים.")
        return 0 if os.path.exists(OUT) else 1

    out = {"rows": rows, "source": "Polymarket"}
    existing = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    # היסטוריה יומית להסתברויות (מזין את גרפי המגמה בכרטיסים): רשומה אחת ליום,
    # מתעדכנת תוך-יומית, נשמרים 8 ימים אחרונים
    now_il = datetime.now(timezone.utc) + timedelta(hours=3)
    today = now_il.strftime("%Y-%m-%d")
    hist = dict((existing or {}).get("history") or {})
    for r in rows:
        h = [e for e in hist.get(r["key"], []) if e.get("d") != today][-7:]
        h.append({"d": today, "pct": r["pct"]})
        hist[r["key"]] = h
    out["history"] = hist
    if {k: v for k, v in existing.items() if k != "_meta"} == out:
        print("[nochange] ההסתברויות לא השתנו.")
        return 0
    out["_meta"] = {"updatedAt": israel_stamp(), "source": "polymarket"}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT} ({len(rows)} שורות)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
