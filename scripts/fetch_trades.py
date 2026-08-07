#!/usr/bin/env python3
r"""
fetch_trades.py — דוחות "הצעות לטרייד" (Four Pillars וכד') אל טאב "הצעות לטרייד".

מקור: תת-התיקייה trades/ בריפו nidam-reports (איציק שומר את הדוח
ל-C:\challenge\reports\trades — המשימה המתוזמנת דוחפת לבד תוך ~5 דק').

שמות קבצים סלחניים: כל ‎.html עם תאריך YYYY-MM-DD איפשהו בשם. הכותרת נקראת
מ-<title>. הפלט: data/trades.json (מהחדש לישן) + העתקי HTML ב-data/trades/.

עמידות: כשל משיכה → משאיר את הקיים.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

API = "https://api.github.com/repos/nditzik/nidam-reports/contents/trades"
RAW = "https://raw.githubusercontent.com/nditzik/nidam-reports/main/trades/"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "trades")
OUT_JSON = os.path.join(ROOT, "data", "trades.json")

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
MAX_KEEP = 20   # מציגים עד 20 דוחות אחרונים


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
        print(f"[warn] רשימת דוחות טריידים נכשלה: {e}")
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
        title = (t.group(1).strip() if t else "") or ("הצעות לטרייד · " + m.group(1))
        reports.append({"file": "data/trades/" + name, "date": m.group(1), "title": title})
        print(f"[ok] {m.group(1)} — {title[:50]}")

    reports.sort(key=lambda r: r["date"], reverse=True)
    reports = reports[:MAX_KEEP]
    payload = {"reports": reports,
               "_meta": {"updatedAt": israel_stamp(), "source": "nidam-reports/trades"}}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] {len(reports)} דוחות טריידים")
    return 0


if __name__ == "__main__":
    sys.exit(main())
