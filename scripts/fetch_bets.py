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


def kalshi_markets(series):
    req = urllib.request.Request(KALSHI + series + "&status=open&limit=100", headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8")).get("markets", [])


def kalshi_ob_prob(ticker):
    """הסתברות YES מספר-הפקודות הציבורי: אמצע בין הצעת ה-YES הטובה למשלים של
    הצעת ה-NO. (מ-08/2026 ה-API הציבורי כבר לא חושף last_price/bid/ask ישירות.)"""
    url = "https://api.elections.kalshi.com/trade-api/v2/markets/" + ticker + "/orderbook"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        ob = json.loads(r.read().decode("utf-8")).get("orderbook_fp") or {}

    def best(side):
        ps = [float(p) for p, _ in (ob.get(side) or [])]
        return max(ps) if ps else None

    yb, nb = best("yes_dollars"), best("no_dollars")
    if yb is not None and nb is not None:
        return (yb + (1 - nb)) / 2
    if yb is not None:
        return yb
    if nb is not None:
        return 1 - nb
    return None


def cpi_row():
    """אינפלציה שנתית (Kalshi KXCPIYOY): הרף הגבוה ביותר שהשוק נותן לו 50%+.
    בלי נזילות → אין שורה."""
    markets = kalshi_markets("KXCPIYOY")
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
        if not mt:
            continue
        p = kalshi_ob_prob(m.get("ticker"))
        if p is None:
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
            "sub": f"ההימור המוביל: תישאר מעל {best[0]}%", "pct": round(best[1] * 100), "chg": None,
            "src": "Kalshi"}


def spx_row():
    """יעד S&P 500 לסוף השנה (Kalshi KXINXY, סולם טווחי סגירה): הרצפה הגבוהה
    ביותר שהשוק נותן לה 50%+ לסגירה מעליה (הסתברות מצטברת מנורמלת על הסולם)."""
    markets = kalshi_markets("KXINXY")
    if not markets:
        return None
    events = {}
    for m in markets:
        events.setdefault(m.get("event_ticker") or "", []).append(m)
    # אירוע הסגירה הקרוב = סוף השנה הנוכחית (בדצמבר עשויה להיפתח גם שנה קדימה)
    ev = min(events.values(), key=lambda ms: min(m.get("close_time") or "9999" for m in ms))
    year = ""
    ym = re.search(r"-(\d{2})DEC", ev[0].get("ticker") or "")
    if ym:
        year = " 20" + ym.group(1)
    buckets = []   # (רצפת הטווח בנקודות, הסתברות)
    for m in ev:
        sub = m.get("subtitle") or ""
        nums = re.findall(r"[\d,]+(?:\.\d+)?", sub)
        if not nums:
            continue
        p = kalshi_ob_prob(m.get("ticker"))
        if p is None:
            continue
        floor = 0 if "below" in sub else int(round(float(nums[0].replace(",", ""))))
        buckets.append((floor, p))
    total = sum(p for _, p in buckets)
    if total < 0.5:   # ספר דליל מדי בשביל מספר אמין
        return None
    best = None
    for floor, _ in buckets:
        if floor <= 0:
            continue
        cum = sum(p for f2, p in buckets if f2 >= floor) / total
        if cum >= 0.5 and (best is None or floor > best[0]):
            best = (floor, cum)
    if not best:
        return None
    return {"key": "spx_eoy", "label": "יעד S&P 500 לסוף" + (year or " השנה"),
            "sub": f"ההימור המוביל: ייסגר מעל {best[0]:,}", "pct": round(best[1] * 100),
            "chg": None, "src": "Kalshi"}


def yesno_row(key, label, yes_he, no_he, p, chg):
    """שוק כן/לא: מציגים תמיד את הצד המוביל — האחוז, הכיוון והשינוי היומי שלו."""
    if p >= 0.5:
        return {"key": key, "label": label, "sub": "ההימור המוביל: " + yes_he,
                "pct": round(p * 100), "chg": chg}
    return {"key": key, "label": label, "sub": "ההימור המוביל: " + no_he,
            "pct": round((1 - p) * 100), "chg": (-chg if chg is not None else None)}


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
            rows.append(yesno_row("hike_2026", "העלאת ריבית עד סוף 2026",
                                  "תהיה העלאה", "לא תהיה העלאה", p, chg_pp(m)))
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
            rows.append(yesno_row("recession", "מיתון בארה\"ב עד סוף 2026",
                                  "יהיה מיתון", "לא יהיה מיתון", p, chg_pp(m)))
    except Exception as e:
        print(f"[warn] recession: {e}")
    try:
        r = spx_row()
        if r:
            rows.append(r)
    except Exception as e:
        print(f"[warn] spx: {e}")

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
    # מפתחות של שורות שהוסרו (למשל spy_hit הישן) לא נגררים לנצח
    hist = {r["key"]: hist[r["key"]] for r in rows}
    out["history"] = hist
    # לשורות Kalshi אין שינוי-יומי מה-API — נגזר מההיסטוריה שלנו (אתמול מול היום)
    for r in rows:
        if r.get("chg") is None and len(hist.get(r["key"]) or []) >= 2:
            r["chg"] = round(r["pct"] - hist[r["key"]][-2]["pct"], 1)
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
