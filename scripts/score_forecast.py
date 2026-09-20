#!/usr/bin/env python3
"""
score_forecast.py — הזיכרון והציון של הצפי השבועי (20.9.2026) → data/forecasts.json

בכל מחזור של הבוט:
  1. ארכוב: אם ב-claude_analysis.json יש eventUpdate.forecast — נשמר לפי weekOf. אפשר לעדכן אותו
     עד פתיחת המסחר של יום שני (16:30 שעון ישראל); אחר כך הוא נעול — אי אפשר "לתקן" צפי בדיעבד.
     (הרוטינה של שני 07:45 דורסת את eventUpdate; האתר מציג את הצפי מכאן — שדה current.)
  2. ציון: אחרי שהשבוע נסגר (weekly.json של אותו יום שישי), הטענה נבדקת מול סגירת S&P 500:
     test=below → פגיעה אם הסגירה השבועית מתחת ל-ref; above → מעל. נשמרים גם השינוי השבועי בפועל
     והאם נפל בתוך הטווח שניתן (inRange).
  3. record = {scored, hits, inRange} + last — מוצג באתר בתוך בלוק הצפי.
"""
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "forecasts.json")


def il_now():
    now = datetime.now(timezone.utc)
    return now + timedelta(hours=3 if 4 <= now.month <= 10 else 2)


def load(name, default=None):
    try:
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def main():
    now = il_now()
    db = load("forecasts.json") or {"items": []}
    items = {it["weekOf"]: it for it in db.get("items", [])}
    db.pop("_meta", None)
    before = json.dumps(db, ensure_ascii=False, sort_keys=True)

    # 1. ארכוב
    ca = load("claude_analysis.json") or {}
    eu = ca.get("eventUpdate") or {}
    f = eu.get("forecast")
    if isinstance(f, dict) and f.get("weekOf") and f.get("label"):
        wk = f["weekOf"]
        lock = datetime.strptime(wk, "%Y-%m-%d").replace(hour=16, minute=30, tzinfo=now.tzinfo)
        if now < lock or wk not in items:
            keep = items.get(wk, {})
            same = {k: v for k, v in keep.items() if k not in ("headline", "savedAt", "result")} == f
            if (now < lock and not same) or not keep:
                items[wk] = dict(f, headline=eu.get("headline"), savedAt=now.strftime("%d/%m/%Y %H:%M"),
                                 **{k: keep[k] for k in ("result",) if k in keep})

    # 2. ציון
    wkly = load("weekly.json") or {}
    days = wkly.get("days") or []
    if wkly.get("weekOf") and days:
        fri = datetime.strptime(wkly["weekOf"], "%Y-%m-%d").date()
        mon = str(fri - timedelta(fri.weekday()))
        it = items.get(mon)
        close = days[-1].get("spx")
        if it and "result" not in it and close and it.get("ref"):
            ref = float(it["ref"])
            actual = round((close / ref - 1) * 100, 2)
            hit = close < ref if it.get("test") == "below" else close > ref
            lo, hi = it.get("rangeLow"), it.get("rangeHigh")
            it["result"] = {"close": close, "actual": actual, "hit": bool(hit),
                            "inRange": (lo is not None and hi is not None and lo <= actual <= hi),
                            "scoredAt": now.strftime("%d/%m/%Y %H:%M")}

    out_items = sorted(items.values(), key=lambda x: x["weekOf"])
    scored = [x for x in out_items if "result" in x]
    this_mon = str(now.date() - timedelta(now.date().weekday()))
    next_mon = str(now.date() + timedelta(7 - now.date().weekday()))
    cur = next((x for x in reversed(out_items) if x["weekOf"] in (this_mon, next_mon) and "result" not in x), None)
    db = {"items": out_items, "current": cur,
          "record": {"scored": len(scored), "hits": sum(x["result"]["hit"] for x in scored),
                     "inRange": sum(bool(x["result"].get("inRange")) for x in scored)},
          "last": ({"weekOf": scored[-1]["weekOf"], "label": scored[-1].get("label"), "prob": scored[-1].get("prob"),
                    **scored[-1]["result"]} if scored else None)}
    if json.dumps(db, ensure_ascii=False, sort_keys=True) == before:
        print("[skip] אין שינוי")
        return 0
    db["_meta"] = {"updatedAt": now.strftime("%d/%m/%Y %H:%M"), "source": "score_forecast"}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(db, fh, ensure_ascii=False, indent=1)
    print(f"[done] {len(out_items)} צפיות · נבדקו {len(scored)} · פגיעות {db['record']['hits']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
