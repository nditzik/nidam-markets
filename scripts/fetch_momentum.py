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
HIST_OUT = os.path.join(ROOT, "data", "_momentum_hist.json")   # סנאפשוטים יומיים (ראו readiness)
HIST_MAX = 60                                                  # כמו HISTORY_MAX_DAYS בדשבורד
SIG_WEIGHT = {"strength": 3, "hot_prospects": 2, "6m_high": 2, "ttm_squeeze": 1, "macd_buy": 1}

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
        "rel_str": num(r.get("14D RSI") if r.get("14D RSI") is not None else r.get("14D Rel Str")),   # עד יולי 2026 העמודה נקראה "14D Rel Str"
        "stoch": num(r.get("14D Stoch %K")),
        "rvol": num(r.get("50D RelVol")),
        "bb_pct": num(r.get("BB%")),
        "strength": r.get("Strength", ""),
        "opinion": r.get("Opinion", ""),
        "direction": r.get("Direction", ""),
        "trend": r.get("Trend", ""),
    }


def _fl(s, k):
    try:
        return float(s.get(k) or 0)
    except (TypeError, ValueError):
        return 0.0


def passes_base(s):
    """פורט מדויק של passesBaseFilter() מדשבורד המומנטום (ואותו passesBase ב-app.js)."""
    vol, px, ma20, rsi = _fl(s, "vol"), _fl(s, "price"), _fl(s, "ma20"), _fl(s, "rel_str")
    a = s.get("wtd_alpha")
    if vol <= 0 or px <= 0 or a is None or float(a) <= 0 or ma20 <= 0 or rsi <= 0:
        return False
    if vol < 750000:
        return False
    w = s.get("w52_chg")
    if w is not None and float(a) < float(w):
        st = (s.get("strength") or "").lower()
        if not ("top" in st or "max" in st or "strong" in st):
            return False
    stoch, ma50, ma100 = _fl(s, "stoch"), _fl(s, "ma50"), _fl(s, "ma100")
    if rsi > 0 and stoch > 0 and rsi > 72 and stoch > 82:
        return False
    if px > 0 and ma50 > 0 and ma100 > 0 and px < ma50 and px < ma100:
        return False
    if re.search(r"weak", s.get("strength") or "", re.I):
        return False
    if re.search(r"\bsell\b", s.get("opinion") or "", re.I):
        return False
    return True


def snapshot_of(date, rows):
    """סנאפשוט כמו saveHistorySnapshot() בדשבורד: כל מניה שעברה בסיס, עם הסיגנלים שלה."""
    return {"date": date, "stocks": [{"s": r["symbol"], "sig": list(r.get("signals") or [])} for r in rows if passes_base(r)]}


def load_hist():
    try:
        with open(HIST_OUT, "r", encoding="utf-8") as f:
            return json.load(f).get("days") or []
    except Exception:
        return []


def hist_trend_points(sym, hist):
    """רכיב "מגמת ההיסטוריה" של calcReadiness (0/5/10): ציון-יום לפי משקלי הסיגנלים,
    חצי ראשון מול חצי אחרון של הסדרה (רק ימים שבהם המניה הייתה בבסיס)."""
    arr = []
    for e in hist:
        for st in e.get("stocks") or []:
            if st.get("s") == sym:
                arr.append(sum(SIG_WEIGHT.get(k, 0) for k in st.get("sig") or []))
                break
    if len(arr) < 2:
        return 0
    half = -(-len(arr) // 2)
    first = sum(arr[:half]) / half
    last = sum(arr[-half:]) / half
    trend = last - first
    return 10 if trend > 1 else 5 if trend > 0 else 0


# ── Readiness 0–100 (12.9.2026) — פורט מדויק של calcReadiness() מדשבורד המומנטום
# (momentum_dashboard.html בריפו stocks-momentum), שם קטגוריית "מועמדות לטרייד" =
# מניות שעברו את פילטר הבסיס עם Readiness ≥ 50. רכיב "מגמת ההיסטוריה" (עד 10 נק')
# מחושב שם מסנאפשוטים ב-localStorage של הדפדפן; כאן — מ-data/_momentum_hist.json,
# אותם סנאפשוטים (כל תאריך CSV = סנאפשוט; שוחזר לאחור מ-git של stocks-momentum ע"י
# scripts/tools/backfill_momentum_hist.py, ומתעדכן כאן בכל תאריך CSV חדש).
def readiness(s, hist=None):
    def f(k):
        try:
            return float(s.get(k) or 0)
        except (TypeError, ValueError):
            return 0.0
    rsi, stoch, price, ma50, rvol, chg = f("rel_str"), f("stoch"), f("price"), f("ma50"), f("rvol"), f("change_pct")
    sc = len(s.get("signals") or [])
    r = 0
    if rsi > 0 and stoch > 0:
        if rsi < 60 and stoch < 65:
            r += 25
        elif rsi < 65 or stoch < 72:
            r += 12
    if price > 0 and ma50 > 0 and price >= ma50:
        dist = (price - ma50) / ma50 * 100
        r += 20 if dist <= 8 else 10 if dist <= 15 else 0
    r += 15 if rvol >= 2.0 else 10 if rvol >= 1.5 else 5 if rvol >= 1.0 else 0
    r += 15 if sc >= 3 else 8 if sc == 2 else 4 if sc == 1 else 0
    r += hist_trend_points(s.get("symbol"), hist or [])
    r += 15 if chg > 1.5 else 8 if chg > 0 else 0
    return max(0, min(100, r))


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
    src_files = {}   # מפתח סיגנל → שם קובץ ה-CSV (המקור, לתצוגה בטאב מומנטום)
    csv_date = None  # תאריך ה-CSV (YYYY-MM-DD) — מפתח הסנאפשוט בהיסטוריה
    for prefix, key in SCANNERS:
        fname = latest_for(prefix, files)
        if not fname:
            continue
        src_files[key] = fname
        dm = DATE_RE.search(fname)
        if dm:
            csv_date = f"{dm.group(3)}-{dm.group(1)}-{dm.group(2)}"
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

    # 2+ סיגנלים (כל הקטגוריות דורשות זאת) — וגם מניות עם סיגנל אחד שהן "מועמדות"
    # (Readiness ≥ 50, כמו בדשבורד שסורק את כל המניות) — אחרת הקטגוריה תחסר אותן
    for s in merged.values():
        s["signal_count"] = len(s["signals"])
    # היסטוריית סנאפשוטים: תאריך CSV חדש → סנאפשוט חדש (כמו העלאה בדשבורד)
    hist = load_hist()
    if csv_date and not any(e.get("date") == csv_date for e in hist):
        hist = sorted(hist + [snapshot_of(csv_date, merged.values())], key=lambda e: e["date"])[-HIST_MAX:]
        try:
            with open(HIST_OUT, "w", encoding="utf-8") as f:
                json.dump({"days": hist}, f, ensure_ascii=False, separators=(",", ":"))
            print(f"[ok] סנאפשוט {csv_date} נוסף להיסטוריה ({len(hist)} ימים)")
        except Exception as e:
            print(f"[warn] כתיבת היסטוריה נכשלה: {e}")
    stocks = []
    for s in merged.values():
        s["readiness"] = readiness(s, hist)
        # מניית סיגנל-אחד נשמרת רק אם היא מועמדת *וגם* עוברת את פילטר הבסיס של הדשבורד
        if s["signal_count"] >= 2 or (s["readiness"] >= 50 and passes_base(s)):
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
               "_meta": {"updatedAt": stamp, "source": "stocks-momentum", "files": src_files,
                         "histDays": len(hist)}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT} ({len(stocks)} מניות: 2+ סיגנלים או Readiness≥50)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
