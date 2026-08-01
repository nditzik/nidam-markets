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
import urllib.request
from datetime import datetime, timezone, timedelta

API = "https://api.github.com/repos/nditzik/nidam-reports/contents/sectors"
RAW = "https://raw.githubusercontent.com/nditzik/nidam-reports/main/sectors/"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "sectors")
OUT_JSON = os.path.join(ROOT, "data", "sectors.json")

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


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
        m = DATE_RE.search(name)
        if not m:
            print(f"[skip] {name}: אין תאריך בשם הקובץ")
            continue
        try:
            content = _get(RAW + name)
        except Exception as e:
            print(f"[skip] {name}: {e}")
            continue
        path = os.path.join(OUT_DIR, name)
        old = None
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                old = f.read()
        if content != old:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        t = TITLE_RE.search(content)
        title = (t.group(1).strip() if t else "") or ("דוח סקטורים · " + m.group(1))
        reports.append({"file": "data/sectors/" + name, "date": m.group(1), "title": title})
        print(f"[ok] {m.group(1)} — {title[:50]}")

    reports.sort(key=lambda r: r["date"], reverse=True)
    payload = {"reports": reports,
               "_meta": {"updatedAt": israel_stamp(), "source": "nidam-reports/sectors"}}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] {len(reports)} דוחות סקטורים")
    return 0


if __name__ == "__main__":
    sys.exit(main())
