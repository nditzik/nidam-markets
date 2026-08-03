#!/usr/bin/env python3
r"""
fetch_earnings.py — קורא את קובץ הדיווחים (earnings.csv) שאיציק מעדכן שבועית
ובונה את data/earnings.json: מי מדווחת היום + מי בהמשך השבוע.

מקור ראשי: earnings.csv בריפו nidam-reports — איציק שומר את הקובץ ל-
C:\challenge\reports (המשימה המתוזמנת דוחפת אותו לבד תוך ~5 דק').
גיבוי: עותק מקומי בריפו הזה (שורש או data/) אם המשיכה נכשלה.

פורמט:
    Symbol,Name,Latest,"Earnings Date","Market Cap"
    AAPL,"Apple Inc",333.43,2026-07-30,4897204800000

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

# מקור ראשי: nidam-reports (מסתנכרן לבד מ-C:\challenge\reports)
REMOTE_CSV = "https://raw.githubusercontent.com/nditzik/nidam-reports/main/earnings.csv"

# גיבוי: עותק מקומי בריפו הזה
CSV_CANDIDATES = [
    os.path.join(ROOT, "data", "earnings.csv"),
    os.path.join(ROOT, "earnings.csv"),
]

UPCOMING_DAYS = 7      # כמה ימים קדימה להציג ב"בהמשך"
MAX_TODAY = 12         # תקרת כרטיסים ליום (השאר נספרים ב-more)

# שמות אפשריים לעמודת שווי שוק — אם קיימת, ממיינים לפיה (הגדולות קודם)
CAP_COLS = ["Market Cap", "MarketCap", "Mkt Cap", "Market Capitalization", "Cap"]

# גיבוי עד שתתווסף עמודת שווי שוק: חברות ענק מוכרות יוצגו ראשונות
MEGA = set("""AAPL MSFT NVDA GOOGL GOOG AMZN META AVGO TSLA BRK.B LLY JPM V XOM UNH MA COST
HD PG WMT NFLX JNJ ABBV CRM BAC ORCL CVX KO AMD PEP MRK TMO LIN ADBE ACN MCD CSCO PM ABT
GE INTU DIS CAT VZ TXN QCOM IBM AMGN NOW BKNG SPGI RTX AXP NEE UBER PFE LOW HON BLK SYK
AMAT PGR TJX ETN BSX C UNP COP ADP MDT VRTX PLTR MU LRCX ANET SBUX GILD MMM CB ADI DE
INTC MDLZ REGN CI SO ISRG PANW KLAC APP MELI CEG DASH ABNB TTWO MAR CVS""".split())


def parse_cap(val):
    """'1.23T' / '456.7B' / '12,345M' / '1234567' -> float (מיליוני דולר). None אם לא ניתן."""
    if not val:
        return None
    s = str(val).strip().upper().replace(",", "").replace("$", "")
    mult = 1.0
    if s.endswith("T"):
        mult, s = 1_000_000.0, s[:-1]
    elif s.endswith("B"):
        mult, s = 1_000.0, s[:-1]
    elif s.endswith("M"):
        mult, s = 1.0, s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


def cap_col(rows):
    """מחזיר את שם עמודת שווי השוק אם קיימת בקובץ."""
    if not rows:
        return None
    keys = {k.strip().lower(): k for k in rows[0].keys() if k}
    for c in CAP_COLS:
        if c.lower() in keys:
            return keys[c.lower()]
    return None


def rank_key(r, capk):
    """מפתח מיון: הגדולות קודם. לפי שווי שוק אם יש, אחרת רשימת חברות הענק."""
    sym = (r.get("Symbol") or "").strip().upper()
    if capk:
        c = parse_cap(r.get(capk))
        if c is not None:
            return (0, -c, sym)
    return (0 if sym in MEGA else 1, 0, sym)


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
    item = {"ticker": sym, "name": (r.get("Name") or "").strip()}
    if with_logo and sym:
        logo = fetch_logo(sym)
        if logo:
            item["logo"] = logo
    return item


def load_rows():
    """שורות ה-CSV: קודם מ-nidam-reports (המקור שאיציק מעדכן), אחרת עותק מקומי."""
    import io
    try:
        req = urllib.request.Request(REMOTE_CSV, headers={"User-Agent": "nidam-markets-bot"})
        with urllib.request.urlopen(req, timeout=20) as r:
            text = r.read().decode("utf-8-sig", "replace")
        rows = list(csv.DictReader(io.StringIO(text)))
        if rows and "Earnings Date" in rows[0]:
            print("[info] earnings.csv נטען מ-nidam-reports")
            return rows
        print("[warn] ה-CSV המרוחק בפורמט לא צפוי — עובר לעותק המקומי")
    except Exception as e:
        print(f"[info] אין earnings.csv ב-nidam-reports ({e}) — עובר לעותק המקומי")

    path = find_csv()
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"[warn] קריאת CSV מקומי נכשלה: {e}")
        return None


def main():
    rows = load_rows()
    if rows is None:
        print("[warn] לא נמצא earnings.csv")
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

    capk = cap_col(rows)
    print("[info] מיון לפי %s" % ("עמודת '%s'" % capk if capk else "רשימת חברות ענק (אין עמודת שווי שוק)"))

    key = today.isoformat()
    today_rows = sorted(by_date.get(key, []), key=lambda r: rank_key(r, capk))
    today_items = [row_to_item(r, with_logo=True) for r in today_rows[:MAX_TODAY]]

    # "מדווחות השבוע" — שבוע המסחר (ב'–ו'): באמצע השבוע רק הימים שנותרו,
    # ובשבת/ראשון — השבוע הקרוב המלא (מתרענן עם ה-CSV שאיציק שומר בשבת)
    wd = today.weekday()          # שני=0 … ראשון=6
    if wd >= 5:                   # שבת/ראשון → שני–שישי הבאים
        start = today + timedelta(days=7 - wd)
        end = start + timedelta(days=4)
    else:                         # באמצע השבוע → ממחר עד שישי הנוכחי
        start = today + timedelta(days=1)
        end = today + timedelta(days=4 - wd)

    upcoming = []
    cur = start
    while cur <= end:
        k = cur.isoformat()
        rs = by_date.get(k)
        day = cur
        cur = cur + timedelta(days=1)
        if not rs:
            continue
        upcoming.append({
            "date": k,
            "label": "%d/%d" % (day.day, day.month),
            "dow": ["ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳", "א׳"][day.weekday()],
            "count": len(rs),
            "tickers": [(r.get("Symbol") or "").strip().upper()
                        for r in sorted(rs, key=lambda r: rank_key(r, capk))][:6],
        })

    # לוח השבוע המלא לטאב "דיווחים": ב'–ו' של השבוע הרלוונטי (שבת/ראשון → הבא),
    # עד 12 מובילות-שווי ליום + מונה כולל
    week_monday = today + timedelta(days=(7 - wd) if wd >= 5 else -wd)
    week = []
    for i in range(5):
        wday = week_monday + timedelta(days=i)
        k = wday.isoformat()
        rs = sorted(by_date.get(k, []), key=lambda r: rank_key(r, capk))
        week.append({
            "date": k,
            "dow": ["שני", "שלישי", "רביעי", "חמישי", "שישי"][i],
            "label": "%d.%d" % (wday.day, wday.month),
            "total": len(rs),
            "companies": [{"ticker": (r.get("Symbol") or "").strip().upper(),
                           "name": (r.get("Name") or "").strip()} for r in rs[:12]],
        })

    # מפת חיפוש מלאה לתגי "מדווחת בקרוב": טיקר → תאריך דיווח (היום עד +7 ימים)
    window = {}
    for i in range(0, UPCOMING_DAYS + 1):
        k = (today + timedelta(days=i)).isoformat()
        for r in by_date.get(k, []):
            sym = (r.get("Symbol") or "").strip().upper()
            if sym:
                window[sym] = k

    # המדווחות הגדולות של היום (שווי שוק $20B+) — לסיכום-הלילה בטלגרם
    today_big = []
    if capk:
        for r in today_rows:
            c = parse_cap(r.get(capk))
            if c is None:
                continue
            dollars = c if c > 1e8 else c * 1e6    # ערך גולמי בדולרים או במיליונים
            if dollars >= 20e9:
                today_big.append({"ticker": (r.get("Symbol") or "").strip().upper(),
                                  "name": (r.get("Name") or "").strip(),
                                  "capB": round(dollars / 1e9, 1)})
    today_big = today_big[:8]

    payload = {
        "today": key,
        "todayCount": len(today_rows),
        "todayBig": today_big,
        "reporting": today_items,
        "more": max(0, len(today_rows) - len(today_items)),
        "upcoming": upcoming,
        "week": week,
        "window": window,
        "_meta": {"updatedAt": israel_stamp(), "source": "earnings.csv"},
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[done] {key}: {len(today_rows)} מדווחות היום · {len(upcoming)} ימים בהמשך")
    return 0


if __name__ == "__main__":
    sys.exit(main())
