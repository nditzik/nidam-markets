#!/usr/bin/env python3
"""
fetch_movers.py — המניות הבולטות של *עכשיו* אל data/movers.json.

מקור: הסורק הציבורי של TradingView (scanner.tradingview.com) — מדרג לפי הסשן
הנוכחי: פרה-מרקט (11:00–16:30 IL) / מסחר רציף (16:30–23:00) / אחרי הסגירה /
סגור (סופ"ש ולילה → סגירת הסשן האחרון). כך "עולות" הן העולות של היום, לא של אתמול.

סינון איכות: מחיר > $3, שווי שוק > $200M, נפח מינימלי לסשן.
עמידות: כשל → משאיר movers.json קיים.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "movers.json")

SCAN = "https://scanner.tradingview.com/america/scan"
UA = {"User-Agent": "Mozilla/5.0 (compatible; nidam-markets-bot)",
      "Content-Type": "application/json"}
N = 6


def il_now():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return now + timedelta(hours=off)


def israel_stamp():
    return il_now().strftime("%d/%m/%Y %H:%M")


def us_session():
    """הסשן האמריקאי לפי שעון ישראל (קירוב, תואם ליתר הסקריפטים)."""
    now = il_now()
    wd, t = now.weekday(), now.hour * 60 + now.minute
    if wd >= 5:                    # שבת/ראשון
        return "closed"
    if 11 * 60 <= t < 16 * 60 + 30:
        return "pre"
    if 16 * 60 + 30 <= t < 23 * 60:
        return "regular"
    if t >= 23 * 60 or (t < 3 * 60 and wd != 0):
        return "post"
    return "closed"


# session → (עמודת שינוי, עמודת מחיר, עמודת נפח, סף נפח, תווית)
SESSIONS = {
    "pre":     ("premarket_change",  "premarket_close",  "premarket_volume",  100_000,   "פרה-מרקט · חי"),
    "regular": ("change",            "close",            "volume",            1_000_000, "מסחר רציף · חי"),
    "post":    ("postmarket_change", "postmarket_close", "postmarket_volume", 100_000,   "אחרי הסגירה · חי"),
    "closed":  ("change",            "close",            "volume",            1_000_000, "סגירת יום המסחר האחרון"),
}


def scan(chg_col, px_col, vol_col, vol_min, sort_by, ascending):
    body = {
        "filter": [
            {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]},
            {"left": "close", "operation": "greater", "right": 3},
            {"left": "market_cap_basic", "operation": "greater", "right": 200_000_000},
            {"left": vol_col, "operation": "greater", "right": vol_min},
        ],
        "columns": ["name", "description", px_col, chg_col, vol_col],
        "sort": {"sortBy": sort_by, "sortOrder": "asc" if ascending else "desc"},
        "range": [0, N],
    }
    req = urllib.request.Request(SCAN, data=json.dumps(body).encode(), headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode("utf-8"))
    out = []
    for row in d.get("data", []):
        v = row["d"]
        out.append({
            "symbol": v[0],
            "name": (v[1] or "")[:34],
            "price": round(v[2], 2) if v[2] is not None else None,
            "chg": round(v[3], 2) if v[3] is not None else None,
            "vol": v[4],
        })
    return out


def fetch_groups(ses):
    """שלוש הקבוצות לסשן נתון. מחזיר (payload-חלקי, מס' קבוצות שנמשכו)."""
    chg_col, px_col, vol_col, vol_min, label = SESSIONS[ses]
    groups, got = {}, 0
    for key, sort_by, asc in (("gainers", chg_col, False),
                              ("losers", chg_col, True),
                              ("active", vol_col, False)):
        try:
            groups[key] = scan(chg_col, px_col, vol_col, vol_min, sort_by, asc)
            got += 1
        except Exception as e:
            print(f"[skip] {key}: {e}")
            groups[key] = []
    return groups, label, got


def main():
    ses = us_session()
    groups, label, got = fetch_groups(ses)

    # פרה-מרקט/אפטר דלילים מחזירים לעיתים 0 שורות — נפילה לדירוג הסשן האחרון,
    # אחרת המלבן בדף הבית נעלם (רשימה ריקה = הכרטיס מוסתר)
    if ses != "closed" and not (groups.get("gainers") or groups.get("losers")):
        print(f"[info] סריקת {ses} ריקה — נופל לדירוג הסשן האחרון")
        ses = "closed"
        groups, label, got = fetch_groups(ses)

    if not got or not (groups.get("gainers") or groups.get("losers")):
        print("[warn] אין תוצאות — משאיר movers.json קיים.")
        return 0 if os.path.exists(OUT) else 1

    payload = {"_meta": {"updatedAt": israel_stamp(), "source": "TradingView",
                         "session": ses, "live": label}}
    payload.update(groups)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] movers ({ses}): {got}/3 קבוצות")
    return 0


if __name__ == "__main__":
    sys.exit(main())
