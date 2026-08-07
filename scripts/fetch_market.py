#!/usr/bin/env python3
"""
fetch_market.py — מושך מחירי שוק חיים מ-Yahoo Finance (צד שרת, בלי CORS)
ומייצר data/market.json לסרט המחירים בדף הבית.

רץ בכל הרצת Action (כל 15 דק'). עמידות: כשל בסמל בודד → מדלג; כשל מלא → משאיר קיים.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "market.json")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# key, תווית, סמל Yahoo, מספר ספרות אחרי הנקודה
# es/nq/usdils מוצגים בשורה הקבועה מתחת לרצועה (לא בגלילה) — ראה renderMarketTicker
SYMBOLS = [
    ("es", "חוזה S&P", "ES=F", 2),
    ("nq", "חוזה Nasdaq", "NQ=F", 2),
    ("usdils", "דולר/שקל", "ILS=X", 3),
    ("spy", "SPY", "SPY", 2),
    ("qqq", "QQQ", "QQQ", 2),
    ("iwm", "IWM", "IWM", 2),
    ("vix", "VIX", "^VIX", 2),
    ("tnx", "אג\"ח 10Y", "^TNX", 3),
    ("dxy", "DXY", "DX-Y.NYB", 2),
]


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def quote(sym):
    # interval=15m נותן גם סדרה תוך-יומית לגרף-המיני שבכותרת
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
    if len(closes) > 26:   # דילול ל-26 נקודות לכל היותר
        step = len(closes) / 26.0
        closes = [closes[int(i * step)] for i in range(26)]
    spark = [round(c, 4) for c in closes]
    return price, chg, prev, spark


def main():
    items = []
    for key, label, sym, digits in SYMBOLS:
        try:
            price, chg, prev, spark = quote(sym)
            if price is None:
                raise ValueError("no price")
            items.append({
                "key": key, "label": label,
                "price": round(price, digits),
                "chg": round(chg, 2) if chg is not None else None,
                "prev": round(prev, digits) if prev else None,
                "spark": spark,
            })
            print(f"[ok] {label}: {price} ({chg:+.2f}%)")
        except Exception as e:
            print(f"[skip] {label} ({sym}): {e}")

    if not items:
        if os.path.exists(OUT):
            print("[keep] אין נתונים — משאיר market.json קיים.")
            return 0
        return 1

    payload = {"items": items, "_meta": {"updatedAt": israel_stamp(), "source": "yahoo"}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT} ({len(items)} מכשירים)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
