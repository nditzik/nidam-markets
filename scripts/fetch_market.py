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
SYMBOLS = [
    ("es", "חוזה S&P", "ES=F", 2),
    ("nq", "חוזה Nasdaq", "NQ=F", 2),
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
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(sym) + "?interval=1d&range=1d")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read().decode("utf-8"))
    m = d["chart"]["result"][0]["meta"]
    price = m.get("regularMarketPrice")
    prev = m.get("chartPreviousClose") or m.get("previousClose")
    chg = (price / prev - 1) * 100 if price and prev else None
    return price, chg


def main():
    items = []
    for key, label, sym, digits in SYMBOLS:
        try:
            price, chg = quote(sym)
            if price is None:
                raise ValueError("no price")
            items.append({
                "key": key, "label": label,
                "price": round(price, digits),
                "chg": round(chg, 2) if chg is not None else None,
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
