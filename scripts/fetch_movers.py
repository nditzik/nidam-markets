#!/usr/bin/env python3
"""
fetch_movers.py — המניות הבולטות של היום (עולות/יורדות/הכי נסחרות) מ-Yahoo
אל data/movers.json. אותו מקור כמו סרט המדדים (screener ציבורי, בלי מפתח).

עמידות: כשל → משאיר movers.json קיים.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "movers.json")

API = ("https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
       "?scrIds={}&count={}")
GROUPS = [
    ("gainers", "day_gainers", 6),
    ("losers", "day_losers", 6),
    ("active", "most_actives", 6),
]
UA = {"User-Agent": "Mozilla/5.0 (compatible; nidam-markets-bot)"}


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def fetch(scr, count):
    req = urllib.request.Request(API.format(scr, count), headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    out = []
    for q in d["finance"]["result"][0]["quotes"][:count]:
        out.append({
            "symbol": q.get("symbol"),
            "name": (q.get("shortName") or q.get("longName") or "")[:34],
            "price": q.get("regularMarketPrice"),
            "chg": round(q.get("regularMarketChangePercent") or 0, 2),
            "vol": q.get("regularMarketVolume"),
        })
    return out


def live_quote(sym):
    """מחיר עדכני כולל פרה/פוסט-מרקט + שינוי % מול סגירת הסשן הקודם."""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}"
           "?range=1d&interval=15m&includePrePost=true")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read().decode("utf-8"))["chart"]["result"][0]
    closes = [c for c in d["indicators"]["quote"][0]["close"] if c is not None]
    prev = d["meta"].get("chartPreviousClose")
    if closes and prev:
        return closes[-1], (closes[-1] / prev - 1) * 100
    return None, None


def main():
    payload = {"_meta": {"updatedAt": israel_stamp(), "source": "Yahoo Finance",
                         "live": "מחירים חיים · כולל פרה/פוסט-מרקט"}}
    got = 0
    for key, scr, count in GROUPS:
        try:
            payload[key] = fetch(scr, count)
            got += 1
        except Exception as e:
            print(f"[skip] {key}: {e}")
            payload[key] = []
    if not got:
        print("[warn] אף קבוצה לא נמשכה.")
        return 0 if os.path.exists(OUT) else 1

    # רענון חי: הסקרינרים משקפים רק את הסשן הרשמי האחרון — לפני הפתיחה זה אתמול.
    # מרעננים כל סימבול (כולל פרה-מרקט) וממיינים מחדש בתוך כל קבוצה.
    for key in ("gainers", "losers", "active"):
        for it in payload.get(key, []):
            try:
                px, chg = live_quote(it["symbol"])
                if px is not None:
                    it["price"] = round(px, 2)
                    it["chg"] = round(chg, 2)
            except Exception as e:
                print(f"[live skip] {it['symbol']}: {e}")
    payload["gainers"].sort(key=lambda x: -(x.get("chg") or 0))
    payload["losers"].sort(key=lambda x: (x.get("chg") or 0))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] movers: {got}/3 קבוצות")
    return 0


if __name__ == "__main__":
    sys.exit(main())
