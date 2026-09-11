#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_world.py — מדדי בורסה בינלאומיים ל-data/world.json (טאב "שווקים בינלאומיים").

רץ בכל הרצת Action (כל 15 דק'), אותו מקור ואותה שיטה כמו fetch_market.py.
עמידות: כשל בסמל בודד → מדלג ומשאיר את השאר; כשל מלא → משאיר world.json קיים.

⚠️ מצב מסחר, ולא רק מחיר (9.9.2026): הבורסות כאן פרוסות על פני אסיה, אירופה,
ישראל וארה"ב, ולכן **ברוב שעות היממה רובן סגורות**. מספר בלי הקשר מטעה —
"DAX 0.00%" בשמונה בבוקר הוא נעילת אתמול, לא שוק שלא זז. לכן לכל מדד מחושב
`state` (live/pre/closed) מתוך חותמת הזמן של הציטוט עצמו ומלוח השעות של
הבורסה, ומוצג לצד המחיר. אם ה-API יחזיר חותמת חסרה — נופלים ל-"closed"
בשמרנות, כי עדיף לסמן סגור בטעות מאשר להציג נתון ישן כאילו הוא חי.

⚠️ סמלים שלא ניתן לנחש — כולם אותרו דרך endpoint החיפוש של Yahoo, ולא לפי
הדפוס הצפוי. לא לשנות אותם "להיגיון" בלי לבדוק בפועל מול ה-API:
    תל אביב 125   ^TA125.TA     גרש **וגם** סיומת; TA125.TA מחזיר 404
    ת"א בנקים-5   TA-BANKS.TA   מקף באמצע
    ת"א ביטחוניות 207.TA        מספר סידורי בלבד, בלי שום רמז לשם
    שנגחאי         000001.SS     מספר, לא ראשי-תיבות
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "world.json")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# key, שם תצוגה, דגל, סמל Yahoo, אזור, (פתיחה, נעילה) בשעון ישראל, ימי מסחר
# ימים: 0=שני … 6=ראשון (כמו datetime.weekday)
IL_WEEK = (6, 0, 1, 2, 3)          # ראשון–חמישי (TASE)
WEST_WEEK = (0, 1, 2, 3, 4)        # שני–שישי

# ישראל מפוצלת לשתי קבוצות: 11 שורות ברצף הן קיר טקסט, והפרדה בין "כמה השוק
# זז" לבין "מי הזיז אותו" היא גם ההיגיון שבו קוראים את הדף בפועל.
TA_MAIN = "ישראל — מדדים ראשיים"
TA_SECT = "ישראל — סקטורים"
MARKETS = [
    ("ta35",   "תל אביב 35",    "🇮🇱", "TA35.TA",     TA_MAIN, (9.9, 17.25), IL_WEEK),
    ("ta90",   "תל אביב 90",    "🇮🇱", "TA90.TA",     TA_MAIN, (9.9, 17.25), IL_WEEK),
    ("ta125",  "תל אביב 125",   "🇮🇱", "^TA125.TA",   TA_MAIN, (9.9, 17.25), IL_WEEK),
    # ת"א SME60 (MIDCAP50.TA) הוסר 11.9.2026 לבקשת איציק — "מיותר"; שלושה ראשיים בשורה אחת.
    ("tabank", "ת\"א בנקים-5",  "🇮🇱", "TA-BANKS.TA", TA_SECT, (9.9, 17.25), IL_WEEK),
    ("tains",  "ת\"א ביטוח",    "🇮🇱", "330.TA",      TA_SECT, (9.9, 17.25), IL_WEEK),
    ("tatech", "ת\"א טכנולוגיה", "🇮🇱", "209.TA",     TA_SECT, (9.9, 17.25), IL_WEEK),
    ("tabio",  "ת\"א ביומד",    "🇮🇱", "TASEBM.TA",   TA_SECT, (9.9, 17.25), IL_WEEK),
    ("tadef",  "ת\"א ביטחוניות", "🇮🇱", "207.TA",     TA_SECT, (9.9, 17.25), IL_WEEK),
    ("tare",   "ת\"א נדל\"ן מניב", "🇮🇱", "56.TA",    TA_SECT, (9.9, 17.25), IL_WEEK),
    ("tabld",  "ת\"א בנייה",    "🇮🇱", "55.TA",       TA_SECT, (9.9, 17.25), IL_WEEK),
    ("taind",  "ת\"א תעשייה",   "🇮🇱", "51.TA",       TA_SECT, (9.9, 17.25), IL_WEEK),
    ("taeng",  "ת\"א אנרגיה",   "🇮🇱", "54.TA",       TA_SECT, (9.9, 17.25), IL_WEEK),
    ("taret",  "ת\"א קמעונאות", "🇮🇱", "188.TA",      TA_SECT, (9.9, 17.25), IL_WEEK),
    ("tadual", "ת\"א דואליות",  "🇮🇱", "187.TA",      TA_SECT, (9.9, 17.25), IL_WEEK),
    # ת"א-קנאביס (186.TA) לא נכלל במכוון — ראו הערת STALE_DAYS: Yahoo מחזיר
    # לו מחיר תקין-למראה מ-4.8.2022 עם אפס נתוני מסחר מאז. אם המדד יחזור
    # להיסחר, הוספתו כאן תעבוד מיד; מצב "נתון מיושן" יגן עליה בינתיים.
    ("n225",   "ניקיי 225",     "🇯🇵", "^N225",      "אסיה",   (3.0, 9.0),   WEST_WEEK),
    ("ks11",   "קוספי",          "🇰🇷", "^KS11",      "אסיה",   (3.0, 9.5),   WEST_WEEK),
    ("twii",   "טאיוון",         "🇹🇼", "^TWII",      "אסיה",   (4.0, 8.5),   WEST_WEEK),
    ("sse",    "שנגחאי",         "🇨🇳", "000001.SS",  "אסיה",   (4.5, 10.0),  WEST_WEEK),
    ("hsi",    "האנג סנג",      "🇭🇰", "^HSI",       "אסיה",   (4.5, 11.0),  WEST_WEEK),
    ("nsei",   "ניפטי 50",       "🇮🇳", "^NSEI",      "אסיה",   (6.75, 13.0), WEST_WEEK),
    ("ftse",   "פוטסי 100",     "🇬🇧", "^FTSE",      "אירופה", (10.0, 18.5), WEST_WEEK),
    ("dax",    "דאקס",           "🇩🇪", "^GDAXI",     "אירופה", (10.0, 18.5), WEST_WEEK),
    ("spx",    "S&P 500",       "🇺🇸", "^GSPC",      "ארה\"ב", (16.5, 23.0), WEST_WEEK),
    ("ixic",   "נאסדק",          "🇺🇸", "^IXIC",      "ארה\"ב", (16.5, 23.0), WEST_WEEK),
    ("tsx",    "טורונטו TSX",   "🇨🇦", "^GSPTSE",    "ארה\"ב", (16.5, 23.0), WEST_WEEK),
]

FRESH_MIN = 45      # ציטוט עדכני עד כדי כך → נחשב מסחר חי
PRE_MIN = 90        # עד שעה וחצי לפני הפתיחה → "לפני פתיחה"
STALE_DAYS = 5      # מעבר לכך המדד כנראה מוקפא/נמחק, ולא "סגור"

# ⚠️ למה יש בכלל מצב "מיושן" (9.9.2026): בבדיקת ת"א-קנאביס (186.TA) התברר
# ש-Yahoo מחזיר לו מחיר שנראה תקין לחלוטין — אבל חותמת הזמן היא 4.8.2022,
# לפני ארבע שנים, עם אפס נקודות מסחר. מדד מוקפא נראה בדיוק כמו מדד סגור.
# בנוסף, תצוגת התאריך שלנו הייתה "DD/MM HH:MM" בלי שנה — כך שציטוט בן
# ארבע שנים היה מוצג כ-"04/08 17:31" ונקרא כאילו הוא מהחודש שעבר. שתי
# התקלות יחד היו שמות על האתר מספר בן ארבע שנים בלי שום סימן. מכאן:
# מצב נפרד + שנה בתצוגה בכל פעם שהציטוט אינו מהשנה הנוכחית.


def il_offset():
    return 3 if 4 <= datetime.now(timezone.utc).month <= 10 else 2


def il_now():
    return datetime.now(timezone.utc) + timedelta(hours=il_offset())


def israel_stamp():
    return il_now().strftime("%d/%m/%Y %H:%M")


def session_state(quote_ts, hours, days):
    """(state, תווית) — live / pre / closed, לפי טריות הציטוט ולוח השעות."""
    now = il_now()
    age_min = None
    if quote_ts:
        age_min = (datetime.now(timezone.utc).timestamp() - quote_ts) / 60.0
    open_h, close_h = hours
    cur_h = now.hour + now.minute / 60.0
    trading_day = now.weekday() in days
    # ציטוט טרי בתוך חלון המסחר = נסחר עכשיו. זהו האות האמין ביותר, כי הוא
    # מגיע מהבורסה עצמה ולא מהנחה שלנו על לוח שעות/חגים.
    # מוקפא/נמחק — נבדק ראשון, לפני כל השאר: מדד כזה נראה כמו "סגור" רגיל
    if age_min is not None and age_min > STALE_DAYS * 24 * 60:
        return "stale", "נתון מיושן"
    if trading_day and open_h <= cur_h <= close_h and age_min is not None and age_min <= FRESH_MIN:
        return "live", "נסחר"
    if trading_day and 0 < (open_h - cur_h) * 60 <= PRE_MIN:
        return "pre", "לפני פתיחה"
    return "closed", "סגור"


def quote(sym):
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
    if len(closes) > 26:
        step = len(closes) / 26.0
        closes = [closes[int(i * step)] for i in range(26)]
    return price, chg, prev, [round(c, 2) for c in closes], m.get("regularMarketTime"), (m.get("gmtoffset") or 0)


def daily(sym):
    """נרות יומיים מתחילת השנה: ([(date_iso, close)...], סגירת סוף השנה הקודמת).
    range=ytd — meta.chartPreviousClose הוא בדיוק הסגירה האחרונה של השנה הקודמת."""
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(sym) + "?interval=1d&range=ytd")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        res = json.loads(r.read().decode("utf-8"))["chart"]["result"][0]
    m = res.get("meta") or {}
    off = m.get("gmtoffset") or 0
    bars = []
    for t, c in zip(res.get("timestamp") or [], ((res.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []):
        if c is not None:
            bars.append((datetime.fromtimestamp(t + off, timezone.utc).date().isoformat(), float(c)))
    if len(bars) < 3:
        # סקטורי ת"א (TA-BANKS.TA, 209.TA…): Yahoo לא מחזיק להם היסטוריה יומית בכלל —
        # רק נרות 15 דק' עד חודש אחורה. בונים מהם "סגירות יומיות" (הנר האחרון של כל
        # תאריך). אין YTD (prev_year=None); 5 ימים כן.
        url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
               + urllib.parse.quote(sym) + "?interval=15m&range=1mo")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read().decode("utf-8"))["chart"]["result"][0]
        off = (res.get("meta") or {}).get("gmtoffset") or 0
        by_day = {}
        for t, c in zip(res.get("timestamp") or [], ((res.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []):
            if c is not None:
                by_day[datetime.fromtimestamp(t + off, timezone.utc).date().isoformat()] = float(c)
        bars = sorted(by_day.items())
        return bars, None
    return bars, m.get("chartPreviousClose")


def changes(price, chg_1d, state, qdate, bars, prev_year):
    """(chg, chg5d, chgYtd) — ראו הערת "0.00% ביום ללא מסחר" למטה."""
    i = None
    for k, (d, _) in enumerate(bars):
        if d == qdate:
            i = k
    if state in ("live", "pre") or i is None:
        chg = chg_1d
        ref = price
        j = len(bars) if (i is None or bars[i][0] != qdate) else i
        if i is not None and state in ("live", "pre"):
            j = i          # הנר של היום הוא חלקי — הבסיס ל-5 ימים הוא 5 נרות לפניו
    else:
        # שוק סגור: השינוי של סשן המסחר האחרון (הנר של תאריך הציטוט מול הנר שלפניו)
        chg = (bars[i][1] / bars[i - 1][1] - 1) * 100 if i >= 1 and bars[i - 1][1] else chg_1d
        ref = bars[i][1]
        j = i
    chg5 = (ref / bars[j - 5][1] - 1) * 100 if j >= 5 and bars[j - 5][1] else None
    ytd = (ref / prev_year - 1) * 100 if prev_year else None
    return chg, chg5, ytd


# ⚠️ "0.00% ביום ללא מסחר" (11.9.2026): ביום שישי כל מדדי ת"א הראו 0.00% — הבורסה
# סגורה, ו-range=1d של Yahoo מחזיר יום ריק שבו "הסגירה הקודמת" שווה למחיר. לכן
# כשהשוק סגור השינוי נלקח מהנרות היומיים: הנר של תאריך הציטוט מול הנר שלפניו
# (= השינוי של יום המסחר האחרון, וזה מה שהתאריך שליד המדד ממילא אומר).


def main():
    items = []
    for key, label, flag, sym, region, hours, days in MARKETS:
        try:
            price, chg, prev, spark, ts, goff = quote(sym)
            if price is None:
                raise ValueError("no price")
            state, state_he = session_state(ts, hours, days)
            chg5 = ytd = None
            try:
                bars, prev_year = daily(sym)
                qdate = datetime.fromtimestamp((ts or 0) + goff, timezone.utc).date().isoformat() if ts else ""
                chg, chg5, ytd = changes(price, chg, state, qdate, bars, prev_year)
            except Exception as e:
                print(f"[warn] {label}: נרות יומיים נכשלו — {e}")
            at = ""
            if ts:
                qt = datetime.fromtimestamp(ts, timezone.utc) + timedelta(hours=il_offset())
                # השנה מוצגת רק כשהציטוט אינו מהשנה הנוכחית — אחרת התאריך
                # קצר וקריא, אבל ציטוט ישן לא יכול להתחזות לטרי (ראו למעלה)
                at = qt.strftime("%d/%m %H:%M" if qt.year == il_now().year else "%d/%m/%Y")
            items.append({
                "key": key, "label": label, "flag": flag, "region": region,
                "price": round(price, 2),
                "chg": round(chg, 2) if chg is not None else None,
                "prev": round(prev, 2) if prev else None,
                "chg5d": round(chg5, 2) if chg5 is not None else None,
                "chgYtd": round(ytd, 2) if ytd is not None else None,
                "hours": list(hours), "days": list(days),
                "spark": spark, "state": state, "stateHe": state_he, "at": at,
            })
            print(f"[ok] {label}: {price:,.2f} ({(chg or 0):+.2f}%) · 5d {chg5} · ytd {ytd} · {state_he} · {at}")
        except Exception as e:
            print(f"[skip] {label} ({sym}): {e}")

    if not items:
        if os.path.exists(OUT):
            print("[keep] אין נתונים — משאיר world.json קיים.")
            return 0
        return 1

    payload = {"items": items, "_meta": {"updatedAt": israel_stamp(), "source": "yahoo"}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT} ({len(items)}/{len(MARKETS)} מדדים)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
