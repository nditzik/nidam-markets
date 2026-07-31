#!/usr/bin/env python3
"""
fetch_earnings.py — קורא את קובץ הדיווחים (earnings.csv) שאיציק מעדכן שבועית
ובונה את data/earnings.json: מי מדווחת היום + מי בהמשך השבוע.

מקור: earnings.csv בשורש הפרויקט (או data/earnings.csv), בפורמט:
    Symbol,Name,Latest,"Earnings Date"
    AAPL,"Apple Inc",333.43,2026-07-30

לוגואים נמשכים לפי טיקר (FMP) ל-data/earnings/logos/ — content-aware, כל טיקר פעם אחת.
עמידות: אם הקובץ חסר/פגום — משאיר earnings.json קיים.
"""
import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(ROOT, "data", "earnings.json")
LOGO_DIR = os.path.join(ROOT, "data", "earnings", "logos")
FMP_LOGO = "https://financialmodelingprep.com/image-stock/{}.png"

# מחפש את ה-CSV בשני המקומות — כך שלא משנה איפה איציק שומר אותו
CSV_CANDIDATES = [
    os.path.join(ROOT, "data", "earnings.csv"),
    os.path.join(ROOT, "earnings.csv"),
]

UPCOMING_DAYS = 7      # כמה ימים קדימה להציג ב"בהמשך"
MAX_TODAY = 12         # תקרת כרטיסים ליום (השאר נספרים ב-more)


def israel_today():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).date()


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def find_csv():
    for p in CSV_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def fetch_logo(ticker):
    """מוריד לוגו לפי טיקר פעם אחת ושומר מקומית. מחזיר נתיב יחסי או None."""
    safe = ticker.replace("/", "-")
    rel = "data/earnings/logos/" + safe + ".png"
    path = os.path.join(LOGO_DIR, safe + ".png")
    if os.path.exists(path):
        return rel if os.path.getsize(path) > 300 else None
    try:
        req = urllib.request.Request(FMP_LOGO.format(urllib.parse.quote(ticker)),
                                     headers={"User-Agent": "nidam-markets-bot"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        if data and len(data) > 300 and data[:4] == b"\x89PNG":
            os.makedirs(LOGO_DIR, exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
            return rel
    except Exception as e:
        print(f"[logo skip] {ticker}: {e}")
    return None


def row_to_item(r, with_logo=False):
    sym = (r.get("Symbol") or "").strip().upper()
    item = {
        "ticker": sym,
        "name": (r.get("Name") or "").strip(),
        "price": (r.get("Latest") or "").strip(),
    }
    if with_logo and sym:
        logo = fetch_logo(sym)
        if logo:
            item["logo"] = logo
    return item


def main():
    path = find_csv()
    if not path:
        print("[warn] לא נמצא earnings.csv")
        return 0 if os.path.exists(OUT_JSON) else 1

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        print(f"[warn] קריאת CSV נכשלה: {e}")
        return 0 if os.path.exists(OUT_JSON) else 1

    if not rows or "Earnings Date" not in rows[0]:
        print("[warn] פורמט CSV לא צפוי — נדרשות עמודות Symbol/Name/Latest/Earnings Date")
        return 0 if os.path.exists(OUT_JSON) else 1

    today = israel_today()
    by_date = {}
    for r in rows:
        d = (r.get("Earnings Date") or "").strip()
        if d:
            by_date.setdefault(d, []).append(r)

    key = today.isoformat()
    today_rows = sorted(by_date.get(key, []), key=lambda r: r.get("Symbol", ""))
    today_items = [row_to_item(r, with_logo=True) for r in today_rows[:MAX_TODAY]]

    upcoming = []
    for i in range(1, UPCOMING_DAYS + 1):
        d = (today + timedelta(days=i))
        k = d.isoformat()
        rs = by_date.get(k)
        if not rs:
            continue
        upcoming.append({
            "date": k,
            "label": "%d/%d" % (d.day, d.month),
            "dow": ["ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳", "א׳"][d.weekday()],
            "count": len(rs),
            "tickers": [(r.get("Symbol") or "").strip().upper() for r in sorted(rs, key=lambda r: r.get("Symbol", ""))][:6],
        })

    payload = {
        "today": key,
        "todayCount": len(today_rows),
        "reporting": today_items,
        "more": max(0, len(today_rows) - len(today_items)),
        "upcoming": upcoming,
        "_meta": {"updatedAt": israel_stamp(), "source": os.path.basename(path)},
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[done] {key}: {len(today_rows)} מדווחות היום · {len(upcoming)} ימים בהמשך")
    return 0


if __name__ == "__main__":
    sys.exit(main())
