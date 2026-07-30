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
from datetime import datetime, timezone, timedelta

API = "https://api.github.com/repos/nditzik/nidam-reports/contents"
RAW = "https://raw.githubusercontent.com/nditzik/nidam-reports/main/"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "reports")
LOGO_DIR = os.path.join(OUT_DIR, "logos")
OUT_JSON = os.path.join(ROOT, "data", "reports.json")

FMP_LOGO = "https://financialmodelingprep.com/image-stock/{}.png"

NAME_RE = re.compile(r"^([A-Za-z0-9.\-]+)__(\d{4}-\d{2}-\d{2})")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def _get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "nidam-markets-bot"})
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
    try:
        data = _get(FMP_LOGO.format(urllib.parse.quote(ticker)), binary=True)
        # bad tickers return a 404/HTML page, so the PNG magic is the real guard
        if data and len(data) > 300 and data[:4] == b"\x89PNG":
            os.makedirs(LOGO_DIR, exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
            return rel
    except Exception as e:
        print(f"[logo skip] {ticker}: {e}")
    return None


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
        reports.append({"file": "data/reports/" + name, "ticker": ticker,
                        "date": date, "title": title, "logo": logo})
        print(f"[ok] {ticker} {date} — {title[:40]}" + ("  🖼" if logo else ""))

    reports.sort(key=lambda r: r.get("date") or "", reverse=True)
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
