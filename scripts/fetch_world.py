#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_world.py — מדדי בורסה בינלאומיים ל-data/world.json (טאב "שווקים בינלאומיים").

רץ בכל הרצת Action (כל 15 דק'), אותו מקור ואותה שיטה כמו fetch_market.py.
עמידות: כשל בסמל בודד → מדלג ומשאיר את השאר; כשל מלא → משאיר world.json קיים.

⚠️ מצב מסחר, ולא רק מחיר (9.9.2026): הבורסות כאן פרוסות על פני אסיה, אירופה,
ישראל וארה"ב, ולכן **ברוב שעות היממה רובן סגורות**. מספר בלי הקשר מטעה —
"DAX 0.00%" בשמונה בבוקר הוא נעילת אתמול, לא שוק שלא זז. לכן לכל מדד מחושב
`state` (live/pre/closed) מתוך חותמת הזמן של הציטוט עצמו ומלוח השעות של
הבורסה, ומוצג לצד המחיר. אם ה-API יחזיר חותמת חסרה — נופלים ל-"closed"
בשמרנות, כי עדיף לסמן סגור בטעות מאשר להציג נתון ישן כאילו הוא חי.

⚠️ סמל תל אביב 125 הוא `^TA125.TA` — גרש **וגם** סיומת. `TA125.TA` (הצורה
הצפויה, כמו TA35/TA90) מחזיר 404. אותר רק דרך endpoint החיפוש של Yahoo.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "world.json")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# key, שם תצוגה, דגל, סמל Yahoo, אזור, (פתיחה, נעילה) בשעון ישראל, ימי מסחר
# ימים: 0=שני … 6=ראשון (כמו datetime.weekday)
IL_WEEK = (6, 0, 1, 2, 3)          # ראשון–חמישי (TASE)
WEST_WEEK = (0, 1, 2, 3, 4)        # שני–שישי
MARKETS = [
    ("ta35",  "תל אביב 35",  "🇮🇱", "TA35.TA",   "ישראל",  (9.9, 17.25), IL_WEEK),
    ("ta90",  "תל אביב 90",  "🇮🇱", "TA90.TA",   "ישראל",  (9.9, 17.25), IL_WEEK),
    ("ta125", "תל אביב 125", "🇮🇱", "^TA125.TA", "ישראל",  (9.9, 17.25), IL_WEEK),
    ("n225",  "ניקיי 225",   "🇯🇵", "^N225",     "אסיה",   (2.0, 8.0),   WEST_WEEK),
    ("ks11",  "קוספי",        "🇰🇷", "^KS11",     "אסיה",   (3.0, 9.5),   WEST_WEEK),
    ("nsei",  "ניפטי 50",     "🇮🇳", "^NSEI",     "אסיה",   (6.25, 12.5), WEST_WEEK),
    ("ftse",  "פוטסי 100",   "🇬🇧", "^FTSE",     "אירופה", (10.0, 18.5), WEST_WEEK),
    ("dax",   "דאקס",         "🇩🇪", "^GDAXI",    "אירופה", (10.0, 19.5), WEST_WEEK),
    ("spx",   "S&P 500",     "🇺🇸", "^GSPC",     "ארה\"ב", (16.5, 23.0), WEST_WEEK),
    ("ixic",  "נאסדק",        "🇺🇸", "^IXIC",     "ארה\"ב", (16.5, 23.0), WEST_WEEK),
]

FRESH_MIN = 45      # ציטוט עדכני עד כדי כך → נחשב מסחר חי
PRE_MIN = 90        # עד שעה וחצי לפני הפתיחה → "לפני פתיחה"


def il_offset():
    return 3 if 4 <= datetime.now(timezone.utc).month <= 10 else 2


def il_now():
    return datetime.now(timezone.utc) + timedelta(hours=il_offset())


def israel_stamp():
    return il_now().strftime("%d/%m/%Y %H:%M")


def session_state(quote_ts, hours, days):
    """(state, תווית) — live / pre / closed, לפי טריות הציטוט ולוח השעות."""
    now = il_now()
    age_min = None
    if quote_ts:
        age_min = (datetime.now(timezone.utc).timestamp() - quote_ts) / 60.0
    open_h, close_h = hours
    cur_h = now.hour + now.minute / 60.0
    trading_day = now.weekday() in days
    # ציטוט טרי בתוך חלון המסחר = נסחר עכשיו. זהו האות האמין ביותר, כי הוא
    # מגיע מהבורסה עצמה ולא מהנחה שלנו על לוח שעות/חגים.
    if trading_day and open_h <= cur_h <= close_h and age_min is not None and age_min <= FRESH_MIN:
        return "live", "נסחר"
    if trading_day and 0 < (open_h - cur_h) * 60 <= PRE_MIN:
        return "pre", "לפני פתיחה"
    return "closed", "סגור"


def quote(sym):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(sym) + "?interval=15m&range=1d")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read().decode("utf-8"))
    res = d["chart"]["result"][0]
    m = res["meta"]
    price = m.get("regularMarketPrice")
    prev = m.get("chartPreviousClose") or m.get("previousClose")
    chg = (price / prev - 1) * 100 if price and prev else None
    closes = []
    try:
        closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
    except (KeyError, IndexError, TypeError):
        pass
    if len(closes) > 26:
        step = len(closes) / 26.0
        closes = [closes[int(i * step)] for i in range(26)]
    return price, chg, prev, [round(c, 2) for c in closes], m.get("regularMarketTime")


def main():
    items = []
    for key, label, flag, sym, region, hours, days in MARKETS:
        try:
            price, chg, prev, spark, ts = quote(sym)
            if price is None:
                raise ValueError("no price")
            state, state_he = session_state(ts, hours, days)
            at = ""
            if ts:
                at = (datetime.fromtimestamp(ts, timezone.utc)
                      + timedelta(hours=il_offset())).strftime("%d/%m %H:%M")
            items.append({
                "key": key, "label": label, "flag": flag, "region": region,
                "price": round(price, 2),
                "chg": round(chg, 2) if chg is not None else None,
                "prev": round(prev, 2) if prev else None,
                "spark": spark, "state": state, "stateHe": state_he, "at": at,
            })
            print(f"[ok] {label}: {price:,.2f} ({chg:+.2f}%) · {state_he} · {at}")
        except Exception as e:
            print(f"[skip] {label} ({sym}): {e}")

    if not items:
        if os.path.exists(OUT):
            print("[keep] אין נתונים — משאיר world.json קיים.")
            return 0
        return 1

    payload = {"items": items, "_meta": {"updatedAt": israel_stamp(), "source": "yahoo"}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT} ({len(items)}/{len(MARKETS)} מדדים)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
