#!/usr/bin/env python3
"""
fetch_momentum.py — מושך את 5 סורקי המומנטום מריפו stocks-momentum, ממזג לכל
מניה את מספר הסיגנלים (בכמה סורקים היא מופיעה) + כל האינדיקטורים, ומייצר
data/momentum.json. שומר רק מניות עם 2+ סיגנלים (כל הקטגוריות דורשות 2+).

הסיווג לקטגוריות (דיפ/פריצה/היפוך) נעשה בצד הלקוח, עם אותן נוסחאות בדיוק
כמו בדשבורד המקומי (מועתקות ל-app.js).
"""
import csv
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

API = "https://api.github.com/repos/nditzik/stocks-momentum/contents/data"
RAW = "https://raw.githubusercontent.com/nditzik/stocks-momentum/main/data/"
LOCAL_DIR = os.path.join("..", "..", "מסמכים אישיים", "market-sentiment", "stocks-momentum", "data")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "momentum.json")

# prefix → מפתח סיגנל (חייב להתאים לתוויות ב-app.js)
SCANNERS = [
    ("stocks-screener-strength-and-direction", "strength"),
    ("stocks-screener-hot-prospects", "hot_prospects"),
    ("stocks-screener-nearing-6-month-highs", "6m_high"),
    ("ttm-squeeze-triggered", "ttm_squeeze"),
    ("emacd-new-buy-signals-stocks", "macd_buy"),
]

DATE_RE = re.compile(r"(\d{2})-(\d{2})-(\d{4})\.csv$")


def num(v):
    """מנקה מחרוזת מספרית ('+14.93%', '1,234', 'N/A') → float או None."""
    if v is None:
        return None
    s = str(v).strip().replace(",", "").replace("%", "").replace("$", "")
    s = s.replace("−", "-").replace("+", "").strip('"').strip()
    if not s or s.upper() == "N/A":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "nidam-markets-bot"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def list_remote():
    try:
        data = json.loads(_get(API).decode("utf-8"))
        return [x["name"] for x in data if x.get("type") == "file"]
    except Exception as e:
        print(f"[warn] GitHub API נכשל: {e}")
        return None


def latest_for(prefix, files):
    cands = [f for f in files if f.startswith(prefix) and f.endswith(".csv")]
    def key(f):
        m = DATE_RE.search(f)
        return (int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else (0, 0, 0)
    return max(cands, key=key) if cands else None


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


def row_fields(r):
    return {
        "name": r.get("Name", ""),
        "industry": r.get("Industry", ""),
        "price": num(r.get("Latest")),
        "change_pct": num(r.get("%Change")),
        "vol": num(r.get("200D Avg Vol")),
        "wtd_alpha": num(r.get("Wtd Alpha")),
        "w52_chg": num(r.get("52W %Chg")),
        "ma20": num(r.get("20D MA")),
        "ma50": num(r.get("50D MA")),
        "ma100": num(r.get("100D MA")),
        "rel_str": num(r.get("14D RSI")),
        "stoch": num(r.get("14D Stoch %K")),
        "rvol": num(r.get("50D RelVol")),
        "bb_pct": num(r.get("BB%")),
        "strength": r.get("Strength", ""),
        "opinion": r.get("Opinion", ""),
        "direction": r.get("Direction", ""),
        "trend": r.get("Trend", ""),
    }


def main():
    files = list_remote()
    remote_ok = files is not None
    local_dir = None
    if not remote_ok:
        local_dir = os.path.normpath(os.path.join(ROOT, LOCAL_DIR))
        files = os.listdir(local_dir) if os.path.isdir(local_dir) else None
    if not files:
        if os.path.exists(OUT):
            print("[keep] אין מקור — משאיר momentum.json קיים.")
            return 0
        return 1

    merged = {}  # symbol -> fields + signals[]
    for prefix, key in SCANNERS:
        fname = latest_for(prefix, files)
        if not fname:
            continue
        text = load_text(fname, remote_ok, local_dir)
        if not text:
            continue
        for r in csv.DictReader(io.StringIO(text)):
            sym = (r.get("Symbol") or "").strip()
            if not sym:
                continue
            if sym not in merged:
                merged[sym] = row_fields(r)
                merged[sym]["symbol"] = sym
                merged[sym]["signals"] = []
            if key not in merged[sym]["signals"]:
                merged[sym]["signals"].append(key)
        print(f"[ok] {key}: {fname}")

    # רק 2+ סיגנלים (כל הקטגוריות דורשות זאת) — מקטין מאוד את הקובץ
    stocks = []
    for s in merged.values():
        s["signal_count"] = len(s["signals"])
        if s["signal_count"] >= 2:
            stocks.append(s)
    stocks.sort(key=lambda s: (s["signal_count"], s.get("wtd_alpha") or 0), reverse=True)

    if not stocks:
        if os.path.exists(OUT):
            print("[keep] לא נמצאו מניות 2+ — משאיר קיים.")
            return 0
        return 1

    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    stamp = (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")
    payload = {"stocks": stocks, "count": len(stocks),
               "_meta": {"updatedAt": stamp, "source": "stocks-momentum"}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT} ({len(stocks)} מניות 2+ סיגנלים)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
