#!/usr/bin/env python3
"""
archive_focus.py — "המוקד במבחן": ארכוב מניות-במוקד היומיות ומדידת הביצוע שלהן
בסשן המסחר שאחרי, מול ה-S&P — אל data/focus_history.json.

מנגנון:
  • צילום (פעם ביום, לפני פתיחת המסחר): משחזר את חישוב-המפגשים של הדף (מומנטום
    2+ סיגנלים אחרי פילטר בסיס ∩ מועמדים ∩ בולטות, ≥2 מתוך 3) ושומר את הרשימה
    עם מחיר-ייחוס (סגירת יום הבסיס, מהסורק של TradingView).
  • הקפאה: כשמזוהה שיום מסחר חדש הסתיים (indices.date התקדם), נמדד לכל מניה
    השינוי מסגירת הבסיס לסגירה הבאה + S&P מ-history.json — והתוצאה ננעלת.

עמידות: כל כשל משאיר את הקובץ הקיים.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "focus_history.json")
SCAN = "https://scanner.tradingview.com/america/scan"
UA = {"User-Agent": "Mozilla/5.0 (compatible; nidam-markets-bot)",
      "Content-Type": "application/json"}
MIN_VOL = 750000
MAX_KEEP = 60


def il_now():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return now + timedelta(hours=off)


def israel_stamp():
    return il_now().strftime("%d/%m/%Y %H:%M")


def before_open():
    """לפני פתיחת המסחר בארה\"ב (או סופ\"ש) — אז 'סגירה' בסורק = סגירת הסשן שהושלם."""
    now = il_now()
    return now.weekday() >= 5 or (now.hour * 60 + now.minute) < 16 * 60 + 30


def load(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def fnum(v):
    try:
        x = float(v)
        return x
    except (TypeError, ValueError):
        return 0.0


def passes_base(s):
    """פורט נאמן של passesBase מ-app.js — לשמירת זהות בין הדף לארכיון."""
    vol, px = fnum(s.get("vol")), fnum(s.get("price"))
    a = fnum(s.get("wtd_alpha")) if s.get("wtd_alpha") is not None else None
    ma20, rsi = fnum(s.get("ma20")), fnum(s.get("rel_str"))
    if vol <= 0 or px <= 0 or a is None or a <= 0 or ma20 <= 0 or rsi <= 0:
        return False
    if vol < MIN_VOL:
        return False
    if s.get("w52_chg"):
        w = fnum(s.get("w52_chg"))
        if a < w:
            st = (s.get("strength") or "").lower()
            if not any(k in st for k in ("top", "max", "strong")):
                return False
    stoch, ma50, ma100 = fnum(s.get("stoch")), fnum(s.get("ma50")), fnum(s.get("ma100"))
    if rsi > 72 and stoch > 82:
        return False
    if px > 0 and ma50 > 0 and ma100 > 0 and px < ma50 and px < ma100:
        return False
    if s.get("strength") and re.search(r"weak", s["strength"], re.I):
        return False
    if s.get("opinion") and re.search(r"\bsell\b", s["opinion"], re.I):
        return False
    return True


def compute_focus():
    """שחזור חישוב-המפגשים של הדף: מומנטום ∩ מועמדים (הבולטות הוצאו — מתחלפות
    כל רבע שעה וגרמו לרשימה להשתנות במהלך היום). חייב להישאר זהה ל-app.js!"""
    mom = load(os.path.join(DATA, "momentum.json")) or {}
    cand = load(os.path.join(DATA, "candidates.json")) or {}
    hits = {}

    def H(sym):
        sym = (sym or "").upper()
        if not sym:
            return None
        return hits.setdefault(sym, {"sym": sym})

    for s in mom.get("stocks") or []:
        if (s.get("signal_count") or 0) >= 2 and passes_base(s):
            h = H(s.get("symbol"))
            if h is not None:
                h["mom"] = s["signal_count"]
    for c in cand.get("candidates") or []:
        h = H(c.get("symbol"))
        if h is not None:
            h["cand"] = c.get("rank")

    focus = [h for h in hits.values() if "mom" in h and "cand" in h]
    focus.sort(key=lambda h: (-(h.get("mom") or 0), h.get("cand") or 99, h["sym"]))
    return [h["sym"] for h in focus[:6]]


def tv_closes(symbols):
    """סגירה אחרונה לכל סימבול (בבוקר = סגירת הסשן שהושלם)."""
    body = {
        "filter": [
            {"left": "name", "operation": "in_range", "right": symbols},
            {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]},
        ],
        "columns": ["name", "close"],
        "range": [0, len(symbols) + 8],
    }
    req = urllib.request.Request(SCAN, data=json.dumps(body).encode(), headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode("utf-8"))
    out = {}
    for row in d.get("data", []):
        v = row["d"]
        if v[0] in symbols and v[1] is not None and v[0] not in out:
            out[v[0]] = float(v[1])
    return out


def main():
    ind = load(os.path.join(DATA, "indices.json")) or {}
    basis = ind.get("date")
    if not basis:
        print("[skip] אין indices.date")
        return 0

    hist = load(OUT) or {"entries": []}
    entries = {e["date"]: e for e in hist.get("entries", [])}

    if not before_open():
        print("[skip] בזמן מסחר — צילום/הקפאה נעשים לפני הפתיחה.")
        return 0

    changed = False

    # --- הקפאת תוצאות לרשומות שיום מסחר חדש הסתיים אחריהן ---
    days = (load(os.path.join(DATA, "history.json")) or {}).get("days", [])
    day_dates = [d["date"] for d in days]
    spx_by = {d["date"]: d.get("spx") for d in days}
    for e in entries.values():
        if e.get("result") or e["date"] >= basis:
            continue
        # יום המסחר הבא אחרי תאריך הבסיס של הרשומה
        later = [d for d in day_dates if d > e["date"]]
        if not later:
            continue
        nxt = later[0]
        syms = [s["sym"] for s in e.get("symbols", [])]
        if not syms:
            continue
        try:
            closes = tv_closes(syms)
        except Exception as ex:
            print(f"[warn] הקפאה נדחתה ({e['date']}): {ex}")
            continue
        per, vals = [], []
        for s in e["symbols"]:
            c = closes.get(s["sym"])
            if c and s.get("ref"):
                pct = (c / s["ref"] - 1) * 100
                per.append({"sym": s["sym"], "pct": round(pct, 2)})
                vals.append(pct)
        if not vals:
            continue
        spx_pct = None
        if spx_by.get(e["date"]) and spx_by.get(nxt):
            spx_pct = round((spx_by[nxt] / spx_by[e["date"]] - 1) * 100, 2)
        e["result"] = {"date_next": nxt, "per": per,
                       "avg": round(sum(vals) / len(vals), 2), "spx": spx_pct}
        changed = True
        print(f"[freeze] {e['date']} → {nxt}: ממוצע {e['result']['avg']:+.2f}% · S&P {spx_pct}")

    # --- צילום יומי (פעם אחת לכל יום בסיס) ---
    if basis not in entries:
        syms = compute_focus()
        if syms:
            try:
                closes = tv_closes(syms)
            except Exception as ex:
                print(f"[warn] צילום נדחה: {ex}")
                closes = {}
            entry = {"date": basis,
                     "symbols": [{"sym": s, "ref": round(closes[s], 2)} for s in syms if s in closes]}
            if entry["symbols"]:
                entries[basis] = entry
                changed = True
                print(f"[snapshot] {basis}: {', '.join(s['sym'] for s in entry['symbols'])}")
        else:
            print("[info] אין מניות במוקד היום.")

    if changed:
        ordered = sorted(entries.values(), key=lambda e: e["date"])[-MAX_KEEP:]
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({"entries": ordered,
                       "_meta": {"updatedAt": israel_stamp(), "source": "focus archive"}},
                      f, ensure_ascii=False, indent=1)
        print(f"[done] {len(ordered)} רשומות בארכיון")
    else:
        print("[nochange]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
