#!/usr/bin/env python3
"""
fetch_momentum.py — מושך את רשימות המומנטום מריפו stocks-momentum
ומייצר data/momentum.json.

מזהה אוטומטית את קובץ ה-CSV העדכני לכל רשימה (השם כולל תאריך MM-DD-YYYY)
דרך GitHub Contents API. נופל לקובץ מקומי אם ה-API לא זמין.
עמידות: אם המשיכה נכשלת אבל כבר יש momentum.json — משאיר אותו.
"""
import csv
import io
import json
import os
import re
import sys
import urllib.request

API = "https://api.github.com/repos/nditzik/stocks-momentum/contents/data"
RAW = "https://raw.githubusercontent.com/nditzik/stocks-momentum/main/data/"
LOCAL_DIR = os.path.join("..", "..", "מסמכים אישיים", "market-sentiment", "stocks-momentum", "data")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "momentum.json")
MAX_ROWS = 30

# prefix → כותרת בעברית
LISTS = [
    ("stocks-screener-hot-prospects", "מועמדים חמים"),
    ("stocks-screener-strength-and-direction", "חוזק וכיוון"),
    ("stocks-screener-nearing-6-month-highs", "מתקרבות לשיא 6 חודשים"),
    ("emacd-new-buy-signals-stocks", "איתותי קנייה חדשים (EMACD)"),
    ("ttm-squeeze-triggered", "TTM Squeeze"),
]

DATE_RE = re.compile(r"(\d{2})-(\d{2})-(\d{4})\.csv$")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "nidam-markets-bot"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def list_remote_files():
    try:
        data = json.loads(_get(API).decode("utf-8"))
        return [item["name"] for item in data if item.get("type") == "file"]
    except Exception as e:
        print(f"[warn] GitHub API נכשל: {e}")
        return None


def list_local_files():
    d = os.path.normpath(os.path.join(ROOT, LOCAL_DIR))
    return os.listdir(d) if os.path.isdir(d) else None, d


def latest_for(prefix, files):
    cands = [f for f in files if f.startswith(prefix) and f.endswith(".csv")]
    def key(f):
        m = DATE_RE.search(f)
        return (int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else (0, 0, 0)
    return max(cands, key=key) if cands else None


def parse_csv(text):
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    for r in reader:
        rows.append({
            "sym": r.get("Symbol", ""),
            "name": r.get("Name", ""),
            "industry": r.get("Industry", ""),
            "last": r.get("Latest", ""),
            "chg": r.get("%Change", ""),
            "trend": r.get("Trend", ""),
            "opinion": r.get("Opinion", ""),
            "alpha": r.get("Wtd Alpha", ""),
            "chg52w": r.get("52W %Chg", ""),
            "rsi": r.get("14D RSI", ""),
            "direction": r.get("Direction", ""),
            "strength": r.get("Strength", ""),
        })
        if len(rows) >= MAX_ROWS:
            break
    return rows


def load_text(fname, remote_ok, local_dir):
    if remote_ok:
        try:
            return _get(RAW + fname).decode("utf-8-sig")
        except Exception as e:
            print(f"[warn] משיכת {fname} נכשלה: {e}")
    if local_dir:
        p = os.path.join(local_dir, fname)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8-sig") as f:
                return f.read()
    return None


def main():
    files = list_remote_files()
    remote_ok = files is not None
    local_files, local_dir = (None, None)
    if not remote_ok:
        local_files, local_dir = list_local_files()
        files = local_files
    if not files:
        if os.path.exists(OUT):
            print("[keep] אין מקור — משאיר momentum.json קיים.")
            return 0
        print("[fail] אין מקור ואין קובץ קיים.")
        return 1

    out_lists = []
    for prefix, title in LISTS:
        fname = latest_for(prefix, files)
        if not fname:
            print(f"[skip] לא נמצא קובץ ל-{prefix}")
            continue
        text = load_text(fname, remote_ok, local_dir)
        if not text:
            continue
        rows = parse_csv(text)
        out_lists.append({"key": prefix, "title": title, "file": fname, "count": len(rows), "rows": rows})
        print(f"[ok] {title}: {len(rows)} שורות מ-{fname}")

    if not out_lists:
        if os.path.exists(OUT):
            print("[keep] לא נמשכו רשימות — משאיר קיים.")
            return 0
        return 1

    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    stamp = (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")

    payload = {"lists": out_lists, "_meta": {"updatedAt": stamp, "source": "stocks-momentum"}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
