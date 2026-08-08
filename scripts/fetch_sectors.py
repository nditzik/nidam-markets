#!/usr/bin/env python3
r"""
fetch_sectors.py — דוח הרוטציה הסקטוריאלית השבועי אל טאב "סקטורים".

מקור: תת-התיקייה sectors/ בריפו nidam-reports (איציק שומר את הדוח השבועי
ל-C:\challenge\reports\sectors — המשימה המתוזמנת דוחפת לבד).

שמות קבצים סלחניים: כל ‎.html עם תאריך YYYY-MM-DD איפשהו בשם. הכותרת נקראת
מ-<title>. הפלט: data/sectors.json (מהחדש לישן) + העתקי HTML ב-data/sectors/.

עמידות: כשל משיכה → משאיר את הקיים.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

API = "https://api.github.com/repos/nditzik/nidam-reports/contents/sectors"
RAW = "https://raw.githubusercontent.com/nditzik/nidam-reports/main/sectors/"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "sectors")
OUT_JSON = os.path.join(ROOT, "data", "sectors.json")

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
DATE_RE2 = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")   # גם "8.8.2026" (איציק שומר כך)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def date_of(name):
    """תאריך ISO משם הקובץ — תומך גם YYYY-MM-DD וגם D.M.YYYY (שם עברי חופשי)."""
    m = DATE_RE.search(name)
    if m:
        return m.group(1)
    m = DATE_RE2.search(name)
    if m:
        return "%s-%02d-%02d" % (m.group(3), int(m.group(2)), int(m.group(1)))
    return None


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
        print(f"[warn] רשימת דוחות סקטורים נכשלה: {e}")
        return 0 if os.path.exists(OUT_JSON) else 1

    os.makedirs(OUT_DIR, exist_ok=True)
    reports = []
    for name in files:
        iso = date_of(name)
        if not iso:
            print(f"[skip] {name}: אין תאריך בשם הקובץ (YYYY-MM-DD או D.M.YYYY)")
            continue
        try:
            content = _get(RAW + urllib.parse.quote(name))
        except Exception as e:
            print(f"[skip] {name}: {e}")
            continue
        # שם מאוחסן בטוח-ל-URL: תאריך + סיומת (שם עברי בקישור נשבר בחלק מהדפדפנים)
        stored = "sectors-" + iso + ".html"
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
        # כותרת גנרית של כלי-ייצוא ("Bundled Page" וכד' — בלי עברית) → כותרת ברירת-מחדל
        if not title or not re.search(r"[֐-׿]", title):
            d_parts = iso.split("-")
            title = "דוח רוטציה סקטוריאלית · %d.%d.%s" % (int(d_parts[2]), int(d_parts[1]), d_parts[0])
        reports.append({"file": "data/sectors/" + stored, "date": iso, "title": title})
        print(f"[ok] {iso} — {title[:50]}")

    reports.sort(key=lambda r: r["date"], reverse=True)
    payload = {"reports": reports,
               "_meta": {"updatedAt": israel_stamp(), "source": "nidam-reports/sectors"}}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] {len(reports)} דוחות סקטורים")
    return 0


if __name__ == "__main__":
    sys.exit(main())
