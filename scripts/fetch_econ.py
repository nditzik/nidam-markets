#!/usr/bin/env python3
"""
fetch_econ.py — נתוני מאקרו "צפי מול בפועל" אל data/econ.json.

מקור: היומן הכלכלי הציבורי של TradingView (economic-calendar.tradingview.com) —
מחזיר forecast/previous/actual; "בפועל" מתעדכן אצלם תוך דקות מהפרסום, וה-Action
שרץ כל רבע שעה מכניס אותו לאתר מיד.

ליבה בלבד (לפי החלטת איציק 2026-08-07): תעסוקה+אבטלה, CPI (+ליבה), PPI (+ליבה),
PCE ליבה, ריבית הפד, תמ"ג. כיוון-ההפתעה קובע צבע: NFP/תמ"ג — גבוה=טוב;
אבטלה/אינפלציה — גבוה=רע; ריבית — ניטרלי.

עמידות: כשל → משאיר econ.json קיים.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "econ.json")
API = "https://economic-calendar.tradingview.com/events?from={}&to={}&countries=US"
UA = {"User-Agent": "Mozilla/5.0 (compatible; nidam-markets-bot)",
      "Origin": "https://www.tradingview.com"}

PAST_DAYS = 10      # כמה אחורה (לשורות "פורסמו")
AHEAD_DAYS = 40     # כמה קדימה (לשורות "בקרוב")

# title מדויק ב-TV → (שם עברי, יחידה, כיוון: +1 גבוה=טוב / -1 גבוה=רע / 0 ניטרלי)
TRACK = {
    "Non Farm Payrolls":            ("תעסוקה NFP",        "K", +1),
    "Unemployment Rate":            ("שיעור אבטלה",       "%", -1),
    "Inflation Rate MoM":           ("CPI חודשי",         "%", -1),
    "Inflation Rate YoY":           ("CPI שנתי",          "%", -1),
    "Core Inflation Rate MoM":      ("CPI ליבה חודשי",    "%", -1),
    "Core Inflation Rate YoY":      ("CPI ליבה שנתי",     "%", -1),
    "PPI MoM":                      ("PPI חודשי",         "%", -1),
    "Core PPI MoM":                 ("PPI ליבה חודשי",    "%", -1),
    "Core PCE Price Index MoM":     ("PCE ליבה חודשי",    "%", -1),
    "Core PCE Price Index YoY":     ("PCE ליבה שנתי",     "%", -1),
    "Fed Interest Rate Decision":   ("ריבית הפד",         "%", 0),
    "GDP Growth Rate QoQ Adv":      ("תמ\"ג רבעוני (ראשוני)", "%", +1),
    "GDP Growth Rate QoQ 2nd Est":  ("תמ\"ג רבעוני (עדכון)",  "%", +1),
    "GDP Growth Rate QoQ Final":    ("תמ\"ג רבעוני (סופי)",   "%", +1),
}


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def il_of(iso_utc):
    """'2026-08-07T12:30:00.000Z' → ('7.8', '15:30') בשעון ישראל."""
    try:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    except ValueError:
        return "", ""
    off = 3 if 4 <= dt.month <= 10 else 2
    il = dt.astimezone(timezone(timedelta(hours=off)))
    return "%d.%d" % (il.day, il.month), il.strftime("%H:%M")


def fmt_val(v, unit):
    """מספר → מחרוזת תצוגה ('80K', '4.2%', '-23K'). None → None."""
    if v is None:
        return None
    s = ("%g" % v)
    return s + unit


def main():
    now = datetime.now(timezone.utc)
    frm = (now - timedelta(days=PAST_DAYS)).strftime("%Y-%m-%dT00:00:00.000Z")
    to = (now + timedelta(days=AHEAD_DAYS)).strftime("%Y-%m-%dT00:00:00.000Z")
    try:
        req = urllib.request.Request(API.format(frm, to), headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read().decode("utf-8"))
        rows = d.get("result") or []
    except Exception as e:
        print(f"[warn] משיכת היומן נכשלה: {e}")
        return 0 if os.path.exists(OUT) else 1

    events = []
    for x in rows:
        t = x.get("title") or ""
        if t not in TRACK:
            continue
        he, unit, direction = TRACK[t]
        il_d, il_t = il_of(x.get("date") or "")
        fc, actual, prev = x.get("forecast"), x.get("actual"), x.get("previous")
        surprise = None   # צבע השורה כשפורסם: good/bad/inline (=בדיוק בצפי או בלי כיוון)
        if actual is not None and fc is not None:
            if direction == 0 or actual == fc:
                surprise = "inline"
            else:
                surprise = "good" if (actual > fc) == (direction > 0) else "bad"
        events.append({
            "date": (x.get("date") or "")[:16],
            "ilDate": il_d, "ilTime": il_t,
            "he": he,
            "period": x.get("period") or "",
            "forecast": fmt_val(fc, unit),
            "previous": fmt_val(prev, unit),
            "actual": fmt_val(actual, unit),
            "surprise": surprise,
        })

    if not events:
        print("[warn] אף אירוע ליבה לא נמצא בחלון.")
        return 0 if os.path.exists(OUT) else 1

    events.sort(key=lambda e: e["date"])
    payload = {"events": events,
               "_meta": {"updatedAt": israel_stamp(), "source": "TradingView econ calendar"}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    released = sum(1 for e in events if e["actual"] is not None)
    print(f"[done] {len(events)} אירועי ליבה ({released} עם 'בפועל')")
    return 0


if __name__ == "__main__":
    sys.exit(main())
