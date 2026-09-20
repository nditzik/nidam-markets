#!/usr/bin/env python3
r"""
fetch_insider.py — דוחות "קניות של בעלי עניין" אל טאב "Insider".

מקור: תת-התיקייה insider/ בריפו nidam-reports (איציק שומר את הדוח
ל-C:\challenge\reports\insider — המשימה המתוזמנת דוחפת לבד תוך ~5 דק').

תאריך הדוח, לפי סדר עדיפות:
  1. YYYY-MM-DD או D.M.YYYY בשם הקובץ
  2. "הופק ב-D.M.YYYY" בתוך הדוח (השם הנוכחי הוא חודשי: insider-buying-report-2026-09.html)
  3. YYYY-MM בשם הקובץ → ה-1 בחודש

זיכרון: הרשימה הקודמת ב-data/insider.json נשמרת וממוזגת — דוח שנדרס/נמחק במקור
(למשל קובץ חודשי שעודכן באמצע החודש ומקבל תאריך הפקה חדש) נשאר בארכיון של האתר
כל עוד העתק ה-HTML שלו קיים ב-data/insider/.

עמידות: כשל משיכה → משאיר את הקיים.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

API = "https://api.github.com/repos/nditzik/nidam-reports/contents/insider"
RAW = "https://raw.githubusercontent.com/nditzik/nidam-reports/main/insider/"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "insider")
OUT_JSON = os.path.join(ROOT, "data", "insider.json")

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
DATE_RE2 = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
MONTH_RE = re.compile(r"(\d{4})-(\d{2})(?!\d)")
MADE_RE = re.compile(r"הופק ב-?\s*(\d{1,2})\.(\d{1,2})\.(\d{4})")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<(script|style)[\s\S]*?</\1>|<[^>]+>", re.IGNORECASE)
# שורת הטווח שבראש הדוח: "עסקאות מ-1 עד 18 בספטמבר 2026"
RANGE_RE = re.compile(r"(עסקאות מ-[^.]{3,60}?\d{4})")
# המניות שנבדקו לעומק: השורות הממוספרות בטבלת הדירוג ("1 UBER …")
RANK_RE = re.compile(r"(?<![\d.$])([1-9]|1\d)\s+([A-Z]{1,5})\s")


def _iso(y, m, d):
    return "%s-%02d-%02d" % (y, int(m), int(d))


def date_of(name, content):
    m = DATE_RE.search(name)
    if m:
        return m.group(1)
    m = DATE_RE2.search(name)
    if m:
        return _iso(m.group(3), m.group(2), m.group(1))
    m = MADE_RE.search(content)
    if m:
        return _iso(m.group(3), m.group(2), m.group(1))
    m = MONTH_RE.search(name)
    if m:
        return _iso(m.group(1), m.group(2), 1)
    return None


def tickers_of(text):
    """הטיקרים מטבלת הדירוג, לפי הסדר (1,2,3…) — נעצר כשהמספור נשבר."""
    out, want = [], 1
    for m in RANK_RE.finditer(text):
        if int(m.group(1)) == want and m.group(2) not in out:
            out.append(m.group(2))
            want += 1
    return out[:12]


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "nidam-markets-bot"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")


def main():
    try:
        files = [f["name"] for f in json.loads(_get(API))
                 if f.get("type") == "file" and f["name"].lower().endswith(".html")]
    except Exception as e:
        print(f"[warn] רשימת דוחות insider נכשלה: {e}")
        return 0 if os.path.exists(OUT_JSON) else 1

    os.makedirs(OUT_DIR, exist_ok=True)
    reports = {}
    for name in files:
        try:
            content = _get(RAW + urllib.parse.quote(name))
        except Exception as e:
            print(f"[skip] {name}: {e}")
            continue
        iso = date_of(name, content)
        if not iso:
            print(f"[skip] {name}: לא נמצא תאריך (בשם הקובץ או 'הופק ב-' בדוח)")
            continue
        stored = "insider-" + iso + ".html"
        path = os.path.join(OUT_DIR, stored)
        old = None
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                old = f.read()
        if content != old:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        t = TITLE_RE.search(content)
        title = (t.group(1).strip() if t else "")
        if not title or not re.search(r"[֐-׿]", title):
            p = iso.split("-")
            title = "דוח קניות של בעלי עניין · %d.%d.%s" % (int(p[2]), int(p[1]), p[0])
        text = re.sub(r"\s+", " ", TAG_RE.sub(" ", content))
        rng = RANGE_RE.search(text)
        reports[iso] = {"file": "data/insider/" + stored, "date": iso, "title": title,
                        "range": rng.group(1) if rng else "", "tickers": tickers_of(text), "src": name}
        print(f"[ok] {iso} — {title[:50]} · {', '.join(reports[iso]['tickers'])}")

    # זיכרון: דוחות קודמים שכבר לא במקור נשארים, כל עוד העתק ה-HTML קיים
    try:
        with open(OUT_JSON, "r", encoding="utf-8") as f:
            for r in json.load(f).get("reports", []):
                if r.get("date") not in reports and os.path.exists(os.path.join(ROOT, r.get("file", ""))):
                    reports[r["date"]] = r
    except Exception:
        pass

    out = sorted(reports.values(), key=lambda r: r["date"], reverse=True)
    payload = {"reports": out,
               "_meta": {"updatedAt": israel_stamp(), "source": "nidam-reports/insider"}}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] {len(out)} דוחות insider")
    return 0


if __name__ == "__main__":
    sys.exit(main())
