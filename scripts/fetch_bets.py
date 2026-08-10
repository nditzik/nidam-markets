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
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "bets.json")
API = "https://gamma-api.polymarket.com/events?slug="
UA = {"User-Agent": "Mozilla/5.0 (compatible; nidam-markets-bot)", "Accept": "application/json"}

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
            rows.append({
                "key": "fed_next", "label": "החלטת הפד בספטמבר",
                "sub": "ההימור המוביל: " + OUTCOME_HE.get(title, title),
                "pct": round(p * 100), "chg": chg_pp(m),
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
