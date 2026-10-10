#!/usr/bin/env python3
"""
fetch_market.py — מושך מחירי שוק חיים מ-Yahoo Finance (צד שרת, בלי CORS)
ומייצר data/market.json לסרט המחירים בדף הבית.

רץ בכל הרצת Action (כל 15 דק'). עמידות: כשל בסמל בודד → מדלג; כשל מלא → משאיר קיים.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from iltime import il_off, NY   # שעון ישראל/ניו יורק אמיתי (zoneinfo), ראו iltime.py

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "market.json")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# key, תווית, סמל Yahoo, מספר ספרות אחרי הנקודה
# es/nq/usdils מוצגים בשורה הקבועה מתחת לרצועה (לא בגלילה) — ראה renderMarketTicker
SYMBOLS = [
    ("es", "חוזה S&P", "ES=F", 2),
    ("nq", "חוזה Nasdaq", "NQ=F", 2),
    ("usdils", "דולר/שקל", "ILS=X", 3),
    ("spy", "SPY", "SPY", 2),
    ("qqq", "QQQ", "QQQ", 2),
    ("iwm", "IWM", "IWM", 2),
    ("vix", "VIX", "^VIX", 2),
    ("tnx", "אג\"ח 10Y", "^TNX", 3),
    ("dxy", "DXY", "DX-Y.NYB", 2),
    ("brent", "ברנט", "BZ=F", 2),     # 10.10.2026: לכותרת סוף השבוע בבית (לא ברצועה — order ב-renderMarketTicker)
]


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = il_off(now)
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def quote(sym):
    # interval=15m נותן גם סדרה תוך-יומית לגרף-המיני שבכותרת
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(sym) + "?interval=15m&range=1d")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read().decode("utf-8"))
    res = d["chart"]["result"][0]
    m = res["meta"]
    price = m.get("regularMarketPrice")
    prev = m.get("chartPreviousClose") or m.get("previousClose")
    chg = (price / prev - 1) * 100 if price and prev else None
    closes = []
    try:
        closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
    except (KeyError, IndexError, TypeError):
        pass
    if len(closes) > 26:   # דילול ל-26 נקודות לכל היותר
        step = len(closes) / 26.0
        closes = [closes[int(i * step)] for i in range(26)]
    spark = [round(c, 4) for c in closes]
    return price, chg, prev, spark, m.get("regularMarketTime")


def _daily(sym, rng):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(sym) + "?interval=1d&range=" + rng)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        res = json.loads(r.read().decode("utf-8"))["chart"]["result"][0]
    return [c for c in res["indicators"]["quote"][0]["close"] if c is not None]


def vix_light(prev):
    """רמזור VIX (27.9.2026, איציק). מחקר 2005–2026 (scratchpad/research_vix.py, נשמר בזיכרון):
    הסימן היחיד שעבד בכל תקופה = VIX שעולה ביחס לממוצע 50 שלו כשהמדד ליד השיא (10%+ מעל: 18% מהמקרים →
    תיקון 5% תוך 20 יום, מול 11% בסיס). VIX נמוך = *פחות* תיקונים. לכן:
      green  — VIX מתחת לממוצע 50            (או בין 0% ל-10% מעל, אם לא היה צהוב לפני — היסטרזיס)
      yellow — VIX ≥10% מעל ממוצע 50; נכבה רק כשה-VIX חוזר מתחת לממוצע
      red    — S&P 500 ≥3% מתחת לשיא 52 השבועות (הירידה בפועל)
    spike  — דיברגנס: S&P +1% ו-VIX +10% ב-10 ימים (נדיר: 37% → תיקון; מוצג כ-"!" על הצהוב)."""
    v = _daily("^VIX", "4mo"); c = _daily("^GSPC", "1y")
    if len(v) < 51 or len(c) < 30:
        raise ValueError("not enough history")
    vix, ma50 = v[-1], sum(v[-50:]) / 50.0
    ratio = vix / ma50
    hi = max(c); off = (c[-1] / hi - 1) * 100
    spx10 = (c[-1] / c[-11] - 1) * 100; vix10 = (v[-1] / v[-11] - 1) * 100
    spike = spx10 >= 1.0 and vix10 >= 10.0
    was_yellow = (prev or {}).get("state") == "yellow"
    if off <= -3.0:
        state = "red"
    elif ratio >= 1.10 or (was_yellow and ratio >= 1.0):
        state = "yellow"
    else:
        state = "green"
    out = {"state": state, "spike": bool(spike), "vix": round(vix, 2), "ma50": round(ma50, 2),
           "ratio": round(ratio, 3), "spxOffHigh": round(off, 2), "spx10d": round(spx10, 2), "vix10d": round(vix10, 1)}
    out["note"] = vix_note(out)
    return out


def vix_note(l):
    """28.9.2026 (איציק, חלק 3 של 'הרמזור לתוך הרוטינות'): משפט מוכן בעברית לניתוח היומי. הרוטינה קוראת את
    market.json אבל את הפרומפט שלה אי-אפשר לערוך מכאן (מפתח) — לכן ההנחיה יושבת בנתונים, כמו es.note.
    לפי *מצב* ולא לפי שינוי: כל עוד צהוב/אדום — מוזכר; ירוק — שקט."""
    v, m = l["vix"], l["ma50"]
    sp = (" בנוסף דיברגנס: המדד עלה %+.1f%% ב-10 ימים בזמן שה-VIX עלה %+.0f%% — הסימן הנדיר והחד ביותר בבדיקה "
          "(37%% מהמקרים הדומים → תיקון של 5%% תוך 20 ימי מסחר)." % (l["spx10d"], l["vix10d"])) if l["spike"] else ""
    if l["state"] == "yellow":
        return ("לניתוח: רמזור ה-VIX צהוב — VIX %.1f, %.0f%% מעל הממוצע ל-50 יום (%.1f). ציין זאת במשפט אחד: "
                "פחד מזדחל בזמן שהמדד ליד השיא; בבדיקה על 2005–2026 ב-18%% מהמקרים הדומים הגיע תיקון של 5%% תוך 20 ימי מסחר, "
                "מול 11%% בימים רגילים — כלומר תשומת לב מוגברת, לא תחזית (4 מתוך 5 אזעקות הן שווא).%s"
                % (v, (l["ratio"] - 1) * 100, m, sp))
    if l["state"] == "red":
        return ("לניתוח: רמזור ה-VIX אדום — S&P 500 %.1f%% מתחת לשיא 52 השבועות, VIX %.1f מול ממוצע 50 של %.1f. "
                "ציין שהתיקון כבר בפועל; זה מצב, לא תחזית להמשך.%s" % (abs(l["spxOffHigh"]), v, m, sp))
    return ("רמזור ה-VIX ירוק (VIX %.1f מתחת/סביב הממוצע ל-50 יום %.1f) — אין צורך להזכיר בניתוח.%s" % (v, m, sp))


def main():
    items = []
    for key, label, sym, digits in SYMBOLS:
        try:
            price, chg, prev, spark, ts = quote(sym)
            if price is None:
                raise ValueError("no price")
            items.append({
                "key": key, "label": label,
                "price": round(price, digits),
                "chg": round(chg, 2) if chg is not None else None,
                "prev": round(prev, digits) if prev else None,
                "spark": spark,
                "ts": ts,
            })
            print(f"[ok] {label}: {price} ({chg:+.2f}%)")
        except Exception as e:
            print(f"[skip] {label} ({sym}): {e}")

    if not items:
        if os.path.exists(OUT):
            print("[keep] אין נתונים — משאיר market.json קיים.")
            return 0
        return 1

    # 25.9.2026: הרוטינה היומית השוותה את מחיר חוזה דצמבר (7,764) לסגירת המדד (7,704) וכתבה
    # "החוזים +0.7%" ביום שבו chg היה -0.04%. ההפרש הוא בסיס החוזה (עלות נשיאה עד הפקיעה), לא
    # תנועה. מכיוון שאת פרומפט הרוטינה אי-אפשר לערוך מכאן (מפתח), ההגנה יושבת בנתונים שהיא קוראת:
    # לחוזה S&P נוסף indexEquiv = רמת המדד שהחוזה מגלם (סגירה אחרונה × (1+chg)), וההערה למטה.
    try:
        hist = json.load(open(os.path.join(os.path.dirname(OUT), "history.json"), encoding="utf-8"))
        last = [d for d in hist.get("days", []) if d.get("spx")][-1]
        for it in items:
            # 3.10.2026: בשבת בבוקר הרוטינה כתבה "חוזה S&P מוסיף עוד 0.7% הבוקר" — אבל chg של החוזה
            # הוא מול הסטלמנט של *היום הקודם*, ואחרי סגירת המסחר (ובכל סוף השבוע) הוא תנועת אותו יום
            # מסחר עצמו, שכבר כלולה בסגירת המדד. יום המסחר של החוזה = התאריך בניו יורק, ומ-18:00
            # (פתיחת הסשן הבא) — היום שאחריו. אם הוא לא אחרי יום הסגירה של המדד — אין תנועת לילה.
            if it["key"] in ("es", "nq") and it.get("chg") is not None and it.get("ts"):
                t = datetime.fromtimestamp(it["ts"], NY)
                tday = (t + timedelta(days=1)).date() if t.hour >= 18 else t.date()
                it["sameSession"] = tday.isoformat() <= last["date"]
            if it["key"] == "es" and it.get("chg") is not None:
                it["indexClose"] = last["spx"]
                it["indexCloseDate"] = last["date"]
                if it.get("sameSession"):
                    it["overnight"] = 0.0
                    it["indexEquiv"] = last["spx"]
                    it["note"] = ("אין תנועת לילה: chg (%+.2f%%) הוא שינוי החוזה ביום המסחר של %s — אותו יום שסגירת המדד כבר משקפת. "
                                  "אל תכתוב שהחוזה 'מוסיף' או 'ממשיך לטפס' הבוקר; כשהחוזים סגורים (סוף שבוע/אחרי 17:00 ניו יורק) "
                                  "אין מה לדווח עליהם." % (it["chg"], last["date"]))
                else:
                    it["overnight"] = it["chg"]
                    it["indexEquiv"] = round(last["spx"] * (1 + it["chg"] / 100), 2)
                    it["note"] = ("מחיר החוזה כולל בסיס מעל המדד (עלות נשיאה) — אל תשווה אותו לסגירת המדד. "
                                  "תנועת הלילה = overnight (מול הסטלמנט הקודם); רמת המדד שהחוזה מגלם = indexEquiv.")
                it["basis"] = round(it["price"] - it["indexEquiv"], 2)
            if it["key"] == "nq":
                it["note"] = ("אין תנועת לילה — chg הוא יום המסחר שכבר נסגר." if it.get("sameSession") else
                              "מחיר החוזה כולל בסיס מעל המדד — השינוי לפני הפתיחה = chg בלבד, לא השוואה לסגירה.")
    except Exception as e:
        print(f"[warn] indexEquiv: {e}")

    prev_light = None
    try:
        with open(OUT, "r", encoding="utf-8") as f:
            prev_light = json.load(f).get("vixLight")
    except Exception:
        pass
    try:
        light = vix_light(prev_light)
        print(f"[ok] רמזור VIX: {light['state']} (VIX {light['vix']} / ממוצע50 {light['ma50']} · S&P {light['spxOffHigh']:+.2f}% מהשיא)")
    except Exception as e:
        light = prev_light
        print(f"[warn] רמזור VIX נכשל — נשאר הקודם: {e}")

    payload = {"items": items, "vixLight": light, "_meta": {"updatedAt": israel_stamp(), "source": "yahoo",
               "note": "es/nq הם חוזים (ES=F/NQ=F, דצמבר) — מחירם גבוה מהמדד בבסיס של עשרות נקודות. תנועת הלילה = es.overnight (0 כש-sameSession: chg הוא יום המסחר שכבר בסגירה); רמת המדד המגולמת = es.indexEquiv."}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT} ({len(items)} מכשירים)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
