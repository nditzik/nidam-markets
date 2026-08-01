#!/usr/bin/env python3
"""
archive_scores.py — ארכיון ציוני השוק היומיים אל data/history.json
(מזין את גרף המגמה של The Edge Meter ואת חצי השינוי-היומי).

מצב רגיל: קורא את data/indices.json ומעדכן/מוסיף את הרשומה של יום המסחר הנוכחי.
מצב --backfill: משחזר היסטוריה מלאה מקומיטים של data/daily_state.json בריפו
indexes-status (חד-פעמי; רץ מקומית).

עמידות: כל כשל משאיר את history.json הקיים.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IND = os.path.join(ROOT, "data", "indices.json")
OUT = os.path.join(ROOT, "data", "history.json")

API_COMMITS = ("https://api.github.com/repos/nditzik/indexes-status/commits"
               "?path=data/daily_state.json&per_page=100")
RAW_AT = "https://raw.githubusercontent.com/nditzik/indexes-status/{}/data/daily_state.json"
UA = {"User-Agent": "nidam-markets-bot"}
MAX_DAYS = 120


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def _get(url, token=None):
    headers = dict(UA)
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")


def entry_from(d):
    """רשומת יום מתוך מבנה daily_state/indices."""
    s = d.get("scores") or {}
    e = d.get("evidence") or {}
    if not d.get("date") or s.get("combined") is None:
        return None
    return {
        "date": d["date"],
        "combined": s.get("combined"),
        "tech": s.get("tech"),
        "breadth": s.get("breadth"),
        "flow": s.get("flow"),
        "spx": e.get("spxPrice"),
        "vix": e.get("vix"),
    }


def load_history():
    if os.path.exists(OUT):
        try:
            with open(OUT, "r", encoding="utf-8") as f:
                return {d["date"]: d for d in json.load(f).get("days", [])}
        except Exception:
            pass
    return {}


def save_history(by_date):
    days = sorted(by_date.values(), key=lambda x: x["date"])[-MAX_DAYS:]
    payload = {"days": days, "_meta": {"updatedAt": israel_stamp(), "source": "indexes-status"}}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return len(days)


def backfill():
    token = os.environ.get("GITHUB_TOKEN")
    commits = json.loads(_get(API_COMMITS, token))
    print(f"[backfill] {len(commits)} קומיטים")
    by_date = load_history()
    for c in reversed(commits):          # מהישן לחדש — המאוחר באותו יום גובר
        sha = c["sha"]
        try:
            d = json.loads(_get(RAW_AT.format(sha)))
            e = entry_from(d)
            if e:
                by_date[e["date"]] = e
        except Exception as ex:
            print(f"[skip] {sha[:8]}: {ex}")
    n = save_history(by_date)
    print(f"[done] היסטוריה: {n} ימי מסחר")
    return 0


def main():
    if "--backfill" in sys.argv:
        return backfill()
    try:
        with open(IND, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        print(f"[warn] אין indices.json: {e}")
        return 0
    e = entry_from(d)
    if not e:
        print("[warn] אין נתונים לרישום.")
        return 0
    by_date = load_history()
    by_date[e["date"]] = e
    n = save_history(by_date)
    print(f"[done] {e['date']} נרשם · {n} ימים בארכיון")
    return 0


if __name__ == "__main__":
    sys.exit(main())
