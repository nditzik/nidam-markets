#!/usr/bin/env python3
"""scan_cloud.py — סריקת המועמדים בענן, כל בוקר אחרי שקובצי המומנטום מגיעים (מ-9.10.2026).

מחליף את הסריקה במחשב של איציק (ibkr-swing-system) — אותה לוגיקה (scan_candidates.py, זהה
ל-golden של 8.10), על נרות Yahoo במקום IBKR. נבדק 8.10: 55/56 מועמדים זהים לסריקת IBKR.

  1. היקום: data/_scan_universe.json — כל מי שעבר בסיס במומנטום מ-25.6 (fetch_momentum מוסיף יום),
     בסדר "היום החדש ביותר קודם"; ה-RVOL = מהיום החדש ביותר שיש בו ערך.
  2. טריגר: יום המומנטום האחרון (D) חדש מ-data/_scan_state.json, ו-SPY ב-Yahoo כבר עם נר סגור של D.
  3. נרות: Yahoo v8, שנתיים, נרות עד D בלבד (נר חלקי/מאוחר נשמט), עיגול ל-4 ספרות (float32 של Yahoo).
     חלון הסריקה = 124 הנרות האחרונים (כמו "6 M" של IBKR); hist_r = 501 הנרות האחרונים.
  4. פלט: data/candidates.json באותו מבנה כמו IBKR (date = יום הריצה בשעון ישראל, כמו המקור),
     _meta.source = nidam-cloud-scan, _meta.basedOn = D. build_picks ממשיך משם באותה ריצה.
  שמירה: פחות מ-85% מהמניות עם נרות → לא כותבים (נראה כמו תקלת רשת), ניסיון חוזר בריצה הבאה.
  fetch_ibkr.py לא דורס את הפלט הזה, אלא אם רשימת IBKR מיום ריצה מאוחר יותר (גיבוי ליום שהענן נכשל).

שימוש: python scripts/scan_cloud.py [--force]
"""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import scan_candidates as sc   # sys.path[0] = scripts/
from iltime import IL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UNIVERSE = os.path.join(DATA, "_scan_universe.json")
STATE = os.path.join(DATA, "_scan_state.json")
OUT = os.path.join(DATA, "candidates.json")
SOURCE = "nidam-cloud-scan"
WIN_SCAN, WIN_HIST = 124, 501
MIN_OK = 0.85


def load(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return d


def universe_list(u):
    """[(sym, rvol)] — היום החדש ביותר קודם, בלי כפילויות (כמו load_watchlists במקור)."""
    order, rv, seen = [], {}, set()
    for d in sorted(u.get("days", []), key=lambda d: d["date"], reverse=True):
        for sym, r in d["stocks"]:
            if sym not in seen:
                seen.add(sym)
                order.append(sym)
            if sym not in rv and r is not None:
                rv[sym] = r
    return [(s, rv.get(s)) for s in order]


def yahoo(sym, day, fetch=None):
    """נרות יומיים עד day (כולל): [[date,o,h,l,c,v],...] או None."""
    p2 = int((datetime.strptime(day, "%Y-%m-%d") + timedelta(days=2)).replace(tzinfo=timezone.utc).timestamp())
    p1 = p2 - 800 * 86400
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/" + sym.replace(".", "-").replace("/", "-") +
           "?period1=%d&period2=%d&interval=1d" % (p1, p2))
    for attempt in range(3):
        try:
            if fetch:
                res = fetch(url)
            else:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=25) as r:
                    res = json.loads(r.read().decode())
            res = res["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            off = (res.get("meta") or {}).get("gmtoffset") or 0
            out = []
            for t, o, h, l, c, v in zip(res.get("timestamp") or [], q["open"], q["high"], q["low"], q["close"], q["volume"]):
                if None in (o, h, l, c):
                    continue
                d = datetime.fromtimestamp(t + off, timezone.utc).strftime("%Y-%m-%d")
                if d <= day:
                    out.append([d, round(o, 4), round(h, 4), round(l, 4), round(c, 4), v or 0])
            return out or None
        except Exception:
            time.sleep(1.5 + attempt * 2)
    return None


def il_stamp(now):
    return now.astimezone(IL).strftime("%d/%m/%Y %H:%M")


def main(force=False, fetch=None, now=None):
    now = now or datetime.now(timezone.utc)
    u = load(UNIVERSE)
    if not u or not u.get("days"):
        print("[skip] אין יקום (data/_scan_universe.json)")
        return 0
    day = max(d["date"] for d in u["days"])
    st = load(STATE, {}) or {}
    if st.get("day") == day and not force:
        print(f"[skip] כבר נסרק על סגירת {day} ({st.get('at')})")
        return 0
    spy = yahoo("SPY", day, fetch)
    if not spy or spy[-1][0] != day:
        print(f"[wait] ל-SPY ב-Yahoo עוד אין נר סגור של {day} (אחרון: {spy[-1][0] if spy else '—'})")
        return 0
    universe = universe_list(u)
    t0 = time.time()
    with ThreadPoolExecutor(8) as ex:
        bars = dict(zip([s for s, _ in universe], ex.map(lambda s: yahoo(s, day, fetch), [s for s, _ in universe])))
    ok = sum(1 for v in bars.values() if v)
    print(f"[bars] {ok}/{len(universe)} מניות, {time.time() - t0:.0f} שנ'")
    if ok < MIN_OK * len(universe):
        print(f"[wait] רק {ok}/{len(universe)} עם נרות — לא כותב, ניסיון חוזר בריצה הבאה")
        return 0
    cands, results = sc.scan(universe,
                             lambda s: (bars.get(s) or [])[-WIN_SCAN:] or None,
                             lambda s: (bars.get(s) or [])[-WIN_HIST:] or None)
    out = sc.payload(cands, now.astimezone(IL).strftime("%Y-%m-%d"), il_stamp(now), SOURCE)
    stages = {}
    for stage, _ in results.values():
        stages[stage] = stages.get(stage, 0) + 1
    out["_meta"].update(basedOn=day, universe=len(universe), barsOk=ok,
                        note="סריקה בענן על נרות Yahoo — אותה לוגיקה כמו הסריקה של IBKR")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump({"day": day, "at": il_stamp(now), "count": out["count"], "universe": len(universe),
                   "barsOk": ok, "stages": stages, "top": [c["symbol"] for c in out["candidates"][:10]]},
                  f, ensure_ascii=False, indent=1)
    print(f"[done] {out['count']} מועמדים על סגירת {day}: {', '.join(c['symbol'] for c in out['candidates'][:10])}…")
    return 0


if __name__ == "__main__":
    sys.exit(main(force="--force" in sys.argv))
