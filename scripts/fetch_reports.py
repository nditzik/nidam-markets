#!/usr/bin/env python3
"""
fetch_reports.py — מושך ניתוחי דוחות (HTML) מהריפו הציבורי nidam-reports,
מעתיק אותם ל-data/reports/ ובונה את data/reports.json לטאב "דוחות".

קונבנציית שם קובץ: TICKER__YYYY-MM-DD.html  (למשל META__2026-07-30.html).
טיקר + תאריך נחלצים מהשם; הכותרת נקראת מתוך <title> שבקובץ.

עמידות: כשל משיכה → משאיר את reports.json והקבצים הקיימים.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import struct
import zlib
from gh_api import gh_headers
from datetime import datetime, timezone, timedelta
from iltime import il_off   # שעון ישראל אמיתי (zoneinfo), ראו iltime.py

API = "https://api.github.com/repos/nditzik/nidam-reports/contents"
RAW = "https://raw.githubusercontent.com/nditzik/nidam-reports/main/"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "reports")
LOGO_DIR = os.path.join(OUT_DIR, "logos")
OUT_JSON = os.path.join(ROOT, "data", "reports.json")

FMP_LOGO = "https://financialmodelingprep.com/image-stock/{}.png"

# חברות שנשמרות לפי שם ולא לפי טיקר — מיפוי לסמל ש-FMP מכיר (הכרטיס עדיין מציג את השם המקורי)
LOGO_ALIAS = {
    "ALPHABET": "GOOGL", "GOOGLE": "GOOGL", "FACEBOOK": "META", "BERKSHIRE": "BRK-B",
}

# סלחן: קו-תחתון אחד או שניים בין הטיקר לתאריך (CVX_2026-07-31 וגם CVX__2026-07-31)
NAME_RE = re.compile(r"^([A-Za-z0-9.\-]+?)_+(\d{4}-\d{2}-\d{2})")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = il_off(now)
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def _get(url, binary=False):
    req = urllib.request.Request(url, headers=gh_headers(url))
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read() if binary else r.read().decode("utf-8", "ignore")


def list_html():
    data = json.loads(_get(API))
    return [f["name"] for f in data
            if f.get("type") == "file" and f["name"].lower().endswith(".html")]


def fetch_logo(ticker):
    """מוריד לוגו חברה לפי טיקר (FMP) ל-data/reports/logos/. מחזיר נתיב יחסי או None."""
    rel = "data/reports/logos/" + ticker + ".png"
    path = os.path.join(LOGO_DIR, ticker + ".png")
    if os.path.exists(path) and os.path.getsize(path) > 300:
        return rel
    sym = LOGO_ALIAS.get(ticker.upper(), ticker)
    try:
        data = _get(FMP_LOGO.format(urllib.parse.quote(sym)), binary=True)
        # bad tickers return a 404/HTML page, so the PNG magic is the real guard
        if data and len(data) > 300 and data[:4] == b"\x89PNG":
            os.makedirs(LOGO_DIR, exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
            return rel
    except Exception as e:
        print(f"[logo skip] {ticker}: {e}")
    return None


def logo_is_light(path):
    """לוגו לבן על רקע שקוף (NKE, 2.10.2026) נעלם על הריבוע הלבן של הכרטיס.
    מפענח PNG ‏8-ביט RGB/RGBA בלי interlace (stdlib בלבד) ובודק אם הפיקסלים הנראים כמעט לבנים.
    כל פורמט אחר / שגיאה → False (ברירת המחדל: ריבוע לבן כמו תמיד)."""
    try:
        d = open(path, "rb").read()
        i, idat, hdr = 8, b"", None
        while i < len(d):
            ln = struct.unpack(">I", d[i:i + 4])[0]
            t, c = d[i + 4:i + 8], d[i + 8:i + 8 + ln]
            if t == b"IHDR":
                hdr = struct.unpack(">IIBBBBB", c)
            elif t == b"IDAT":
                idat += c
            i += 12 + ln
        w, h, depth, ctype, _, _, inter = hdr
        if depth != 8 or inter or ctype not in (2, 6):
            return False
        bpp = 4 if ctype == 6 else 3
        raw, stride, pos = zlib.decompress(idat), w * bpp, 0
        prev = bytearray(stride)
        n = lum = clear = 0
        for _ in range(h):
            f = raw[pos]; pos += 1
            line = bytearray(raw[pos:pos + stride]); pos += stride
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]
                if f == 1: line[x] = (line[x] + a) & 255
                elif f == 2: line[x] = (line[x] + b) & 255
                elif f == 3: line[x] = (line[x] + (a + b) // 2) & 255
                elif f == 4:
                    cc = prev[x - bpp] if x >= bpp else 0
                    pp = a + b - cc
                    pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - cc)
                    line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else cc)) & 255
            for x in range(0, stride, bpp):
                if bpp == 4 and line[x + 3] < 40:
                    clear += 1
                    continue
                n += 1
                lum += 0.299 * line[x] + 0.587 * line[x + 1] + 0.114 * line[x + 2]
            prev = line
        # רק לוגו על רקע שקוף: לוגו עם רקע לבן אטום (AAPL, LEN) נראה טוב על הריבוע הלבן
        return n > 0 and clear >= 0.2 * w * h and lum / n >= 225
    except Exception:
        return False


def parse_meta(fname, content):
    m = NAME_RE.match(fname)
    ticker = m.group(1).upper() if m else fname.replace(".html", "")
    date = m.group(2) if m else ""
    t = TITLE_RE.search(content)
    title = (t.group(1).strip() if t else "") or (ticker + (" · " + date if date else ""))
    return ticker, date, title


def main():
    try:
        files = list_html()
    except Exception as e:
        print(f"[warn] רשימת דוחות נכשלה: {e}")
        return 0 if os.path.exists(OUT_JSON) else 1

    if not files:
        print("[info] אין דוחות בריפו nidam-reports עדיין.")
        # keep empty manifest
        _write([])
        return 0

    # "מתי הדוח הופיע לראשונה" — נשמר בין ריצות, כדי שחדש שעולה ייכנס לראש הרשימה
    prev_added = {}
    if os.path.exists(OUT_JSON):
        try:
            with open(OUT_JSON, "r", encoding="utf-8") as f:
                for r in json.load(f).get("reports", []):
                    if r.get("added"):
                        prev_added[os.path.basename(r.get("file", ""))] = r["added"]
        except Exception:
            prev_added = {}
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    os.makedirs(OUT_DIR, exist_ok=True)
    reports = []
    for name in files:
        try:
            content = _get(RAW + name)
        except Exception as e:
            print(f"[skip] {name}: {e}")
            continue
        # write file (content-aware)
        path = os.path.join(OUT_DIR, name)
        old = None
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                old = f.read()
        if content != old:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        ticker, date, title = parse_meta(name, content)
        logo = fetch_logo(ticker) if ticker else None
        rec = {"file": "data/reports/" + name, "ticker": ticker,
               "date": date, "title": title, "logo": logo,
               "added": prev_added.get(name, now_iso)}
        if logo and logo_is_light(os.path.join(ROOT, logo)):
            rec["logoBg"] = "dark"   # לוגו לבן → ריבוע כהה בכרטיס
        reports.append(rec)
        print(f"[ok] {ticker} {date} — {title[:40]}" + ("  🖼" if logo else ""))

    # חדש ראשון: תאריך הדוח, ובתוך אותו יום — מי שהועלה אחרון קודם
    reports.sort(key=lambda r: (r.get("date") or "", r.get("added") or ""), reverse=True)
    _write(reports)
    print(f"[done] {len(reports)} דוחות")
    return 0


def _write(reports):
    payload = {"reports": reports, "_meta": {"updatedAt": israel_stamp(), "source": "nidam-reports"}}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    sys.exit(main())
