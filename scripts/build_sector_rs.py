#!/usr/bin/env python3
"""
build_sector_rs.py — חוזק יחסי של 11 סקטורי S&P מול המדד, מתעודות הסל (24.10.2026, איציק: "חייבים אחידות").

עד 24.10 גלגל הרוטציה (וגם "סקטורים · 5 ימים מול S&P" בבית) קראו את rs5/rs20 מהדשבורד
(indices.rotation.sectorRs): ממוצע פשוט של מניות ה-S&P בכל סקטור לפי רשימה פנימית — שכללה
5 מניות לא-אנרגיה באנרגיה (NRG/CEG/VST/CF/FSLR) ומניה עם ציטוט קפוא (CTRA, 8 ימים אותו ערך).
ביום שישי 23.10 האנרגיה עלתה 2.6% (XLE) ומפת החום בבית הראתה את זה, אבל הגלגל הראה אותה
יורדת. מכאן: אותו מקור כמו מפת החום — תעודות הסל של הסקטורים (XLE, XLK…) מול SPY, משוקללות
לפי גודל החברות, מהנרות היומיים שכבר בריפו (data/bars, fetch_bars.py).

rs5  = (ETF היום ÷ ETF לפני 5 ימי מסחר − 1) − (SPY היום ÷ SPY לפני 5 ימי מסחר − 1), באחוזים.
rs20 = אותו דבר על 20 ימי מסחר. d1 = השינוי היומי של התעודה והפער היומי מול SPY (לחלונית).
פלט: data/sector_rs.json {source, spy, date, days:[{date, rs:{IT:[rs5,rs20],…}, d1:{IT:[chg,rel],…}}]}
— 60 ימי המסחר האחרונים, בדיוק המבנה ש-history.json.days[].rs נתן לגלגל (קוד הסקטור כמפתח).
"""
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BARS = os.path.join(ROOT, "data", "bars")
OUT = os.path.join(ROOT, "data", "sector_rs.json")
ETF = {"XLK": "IT", "XLF": "FIN", "XLV": "HC", "XLY": "CD", "XLC": "COM", "XLI": "IND",
       "XLP": "CS", "XLE": "ENE", "XLB": "MAT", "XLU": "UTL", "XLRE": "RE"}
SPY = "SPY"
DAYS = 60


def closes(sym):
    try:
        with open(os.path.join(BARS, sym + ".json"), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return {}
    bars = d.get("bars") if isinstance(d, dict) else d
    out = {}
    for b in bars or []:
        if len(b) >= 5 and b[4] is not None:
            out[b[0]] = float(b[4])
    return out


def ret(c, dates, i, n):
    """תשואה באחוזים מ-i−n עד i על רשימת התאריכים dates (None כשאין נר)."""
    if i - n < 0:
        return None
    a, b = c.get(dates[i]), c.get(dates[i - n])
    return (a / b - 1) * 100 if a and b else None


def main():
    spy = closes(SPY)
    if not spy:
        print("build_sector_rs: אין נרות SPY — דילוג")
        return 0
    etfs = {sym: closes(sym) for sym in ETF}
    # ציר הזמן = ימי המסחר של SPY (נרות סגורים בלבד, כמו fetch_bars)
    dates = sorted(spy)
    days = []
    for i in range(max(21, len(dates) - DAYS), len(dates)):
        rs, d1 = {}, {}
        for sym, code in ETF.items():
            c = etfs[sym]
            r5, r20, r1 = ret(c, dates, i, 5), ret(c, dates, i, 20), ret(c, dates, i, 1)
            s5, s20, s1 = ret(spy, dates, i, 5), ret(spy, dates, i, 20), ret(spy, dates, i, 1)
            if None in (r5, r20, s5, s20):
                continue
            rs[code] = [round(r5 - s5, 2), round(r20 - s20, 2)]
            if r1 is not None and s1 is not None:
                d1[code] = [round(r1, 2), round(r1 - s1, 2)]
        if rs:
            days.append({"date": dates[i], "rs": rs, "d1": d1})
    if not days:
        print("build_sector_rs: אין מספיק נרות")
        return 0
    # np143: סגירות מיושרות ל-days — הגלגל מחשב מהן שביל "מעוגן" (מצטבר מול SPY מאז תחילת השביל),
    # כך שהקטע האחרון בשביל = התנועה של היום מול המדד, ולא הפרש בין שני חלונות נעים.
    first = len(dates) - len(days)
    px = {"dates": dates[first:], SPY: [spy.get(d) for d in dates[first:]]}
    for sym, code in ETF.items():
        px[code] = [etfs[sym].get(d) for d in dates[first:]]
    payload = {
        "source": "ETF", "spy": SPY, "etf": ETF, "date": days[-1]["date"], "days": days, "closes": px,
        "note": "תעודות הסל של הסקטורים מול SPY, מנרות יומיים סגורים (Yahoo) — אותו מקור כמו מפת החום בבית. rs5/rs20 = תשואת התעודה פחות תשואת SPY ב-5/20 ימי מסחר; d1 = השינוי היומי והפער היומי.",
        "_meta": {"updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "build_sector_rs"},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    last = days[-1]
    print("build_sector_rs: %s · %d ימים · %s" % (last["date"], len(days),
          " ".join("%s %+.1f/%+.1f" % (k, v[0], v[1]) for k, v in sorted(last["rs"].items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
