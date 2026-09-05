#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
write_daily_analysis.py — כותב אוטומטית את data/claude_analysis.json ברגע
שיש בפועל סגירה חדשה ב-data/indices.json שעוד לא נותחה.

למה זה קיים (5.9.2026): הרוטינה שהייתה כותבת את זה (nidam-daily-market-analysis
+ retry, ב-claude.ai/code/routines) רצה בשעון UTC קבוע (03:30 + גיבוי 05:00) —
אבל איציק דוחף את ה-CSV של indexes-status בשעות משתנות (לפעמים אחרי 10:00
שעון ישראל, במיוחד אחרי טיסות/חופשות), אז הרוטינה כמעט תמיד רצה *לפני* שהנתונים
היו זמינים ופספסה, מה שדרש עדכון ידני כמעט כל בוקר במשך שבוע שלם.

הפתרון: סקריפט הזה רץ כאן כמו כל שאר ה-fetch_*.py — בתוך אותה ריצת 15-דקות
של update.yml, אחרי ש-fetch_dashboards.py/fetch_market.py/fetch_earnings.py/
fetch_econ.py כבר עדכנו את data/*.json — ובודק אם indices.json["date"] מתקדם
על claude_analysis.json["date"]. אם כן: אוסף את כל ההקשר (ציונים, רוחב,
סקטורים, בולטות, אופציות+מולטי-לג, חוזים, דוחות/מאקרו של היום) ומבקש מ-Claude
לכתוב ניתוח מלא (structured output). אם לא — no-op שקט. כך זה תמיד "יתפוס"
תוך 15 דקות ממתי שהנתונים בפועל מוכנים, לא משנה באיזו שעה הם נדחפו.

עמידות: כל כשל (אין מפתח API, שגיאת רשת, JSON/תשובה לא תקינה) משאיר את
claude_analysis.json הקיים ולא מפיל את ה-Action — בדיוק כמו שאר סקריפטי ה-fetch
כאן. דורש ANTHROPIC_API_KEY ב-Secrets; בלעדיו מדלג בשקט (ממשיכים לעדכן ידנית
עד שהוא יוגדר).
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify_telegram import load, send  # loader/שולח גנריים, כבר קיימים בריפו

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "claude_analysis.json")
MODEL = "claude-opus-5"


def israel_now():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return now + timedelta(hours=off)


def il_stamp():
    return israel_now().strftime("%d/%m/%Y %H:%M")


def dm(date_iso):
    """"2026-09-04" -> "4.9" (בלי אפס מוביל, כמו הסגנון הקיים בכתבות)."""
    try:
        y, m, d = date_iso.split("-")
        return f"{int(d)}.{int(m)}"
    except Exception:
        return date_iso


SYSTEM_PROMPT = """אתה כותב את הניתוח היומי (לאחר סגירת המסחר) עבור "The Daily
Edge by NIDAM" — אתר עברי לסקירת שוק ה-S&P 500 היומית. תפקידך לתרגם את נתוני
היום שסופקו לך (JSON) לניתוח כתוב בעברית, באורך ובסגנון של אנליסט מקצועי,
בדיוק לפי הכללים הבאים — הם קריטיים ולא רשות:

1. איסור ז'רגון: אסור להשתמש במילה "קצה היצרן". אסור להשתמש במילים "דלתא"/
   Delta או "Flow" כפי שהן — יש לתרגם: את ה"דלתא"/ההימור נטו ל"הכסף הגדול
   הפך שורי/דובי/מאוזן", ואת "Flow" ל"עוצמת הפעילות באופציות". כל מונח טכני
   הכרחי אחר (כמו P/C, MA200, VIX) יוסבר בקצרה בפעם הראשונה שהוא מופיע.
2. מדד ייחוס אחד בלבד: לפני פתיחת המסחר (חוזים) — "חוזה S&P". אחרי הפתיחה —
   "S&P 500". לעולם לא "SPY", גם אם זה מקור הנתון בפועל.
3. מספרים בקבוצות ספרות (למשל "7,747.71" ולא "7747.71").
4. אזהרת מולטי-לג — חובה: אם flow.legTier הוא low/limited/mid, יש לשלב
   בפסקת האופציות את התוכן של flow.legNote בניסוח טבעי (לא להעתיק מילולית) —
   שרוב עסקאות האופציות הבולטות הן חלק מאסטרטגיות מרובות-רגליים (כמו ספרדים)
   ולא הימורים כיווניים ישירים, ושזה מקטין את הביטחון בקריאת הכיוון. אם
   legTier הוא high — אפשר לדלג על ההסתייגות הזו.
5. בדיקת חוזים ודוחות-לילה — חובה: לפני כתיבת הכותרת, יש להביא בחשבון את
   נתוני החוזים (market futures) ואת דוחות/אירועי המאקרו של היום (today's
   earnings/econ) שסופקו. אם יש בהם תזוזה משמעותית או הפתעה — זה צריך להשפיע
   על הכותרת/פסקה הראשונה. אם החוזים שטוחים ואין אירוע גדול — מספיק משפט קצר
   שאין הפתעה לילית, בלי להמציא סיפור.
6. דיוק נתונים מוחלט: להשתמש רק במספרים שסופקו בהקשר. אסור להמציא, לעגל
   בצורה מטעה, או להעריך נתון שלא ניתן. אם נתון חסר — פשוט לא להזכיר אותו.
7. מבנה: headline (משפט אחד, ~80-130 תווים, הכי חשוב+מספר מרכזי), tldr
   (פסקת סיכום קצרה, 2-4 משפטים), bottomline (משפט אחד שמתחיל ב"שורה
   תחתונה:" עם המלצה מעשית), paragraphs (מערך של 4 פסקאות עבריות מלאות, בסדר
   הזה: [1] תנועת המחיר+שינוי הציון+בדיקת חוזים/לילה, [2] רוחב+סקטורים+מניות
   בולטות, [3] ניתוח אופציות (עם אזהרת מולטי-לג כשצריך), [4] מבט קדימה —
   אירועי מאקרו/דוחות קרובים), watchFor (משפט אחד: "שיפור: ... · הרעה: ..."),
   confidence (משפט אחד שמתחיל ברמת ביטחון ומסביר למה).
8. סגנון: מקצועי, ענייני, לא סנסציוני. להתייחס לסגירה כ"אתמול" ולציין את
   התאריך בפורמט יום.חודש (למשל "4.9") בפעם הראשונה שמוזכר. אם קיים הקשר
   מהניתוח הקודם (יום המסחר שלפני) — אפשר להמשיך חוט עלילה (כמו רצף ימי
   מולטי-לג, או נושא מאקרו נמשך) כשזה רלוונטי, לא לחזור עליו כברירת מחדל.

פלט: אך ורק שדות ה-JSON המבוקשים, בעברית מלאה, ללא הערות נוספות."""


def build_context(idx, mkt, earn, econ, prev):
    date_iso = idx.get("date")
    s = idx.get("scores") or {}
    prev_scores = (prev.get("_scores_for_context") or {})

    futures = []
    for it in (mkt or {}).get("items", []):
        if it.get("key") in ("es", "nq"):
            futures.append({"symbol": it.get("label"), "chgPct": it.get("chg")})

    econ_today = [
        {"time": e.get("ilTime"), "he": e.get("he"), "actual": e.get("actual"), "forecast": e.get("forecast")}
        for e in (econ or {}).get("events", [])[:8]
    ]

    ctx = {
        "date_being_analyzed": date_iso,
        "date_he_short": dm(date_iso),
        "scores": s,
        "riskOff": idx.get("riskOff"),
        "evidence": idx.get("evidence"),
        "flow": idx.get("flow"),
        "flowWeight": idx.get("flowWeight"),
        "rotation": idx.get("rotation"),
        "conclusion": idx.get("conclusion"),
        "aiSummary_blocks": ((idx.get("aiSummary") or {}).get("blocks")),
        "futures_this_morning": futures,
        "todays_earnings": {
            "count": (earn or {}).get("todayCount"),
            "big_names": (earn or {}).get("todayBig"),
        },
        "todays_econ_calendar": econ_today,
        "previous_daily_analysis": {
            "date": prev.get("date"),
            "headline": prev.get("headline"),
            "tldr": prev.get("tldr"),
            "watchFor": prev.get("watchFor"),
        } if prev.get("date") else None,
    }
    return ("הנה נתוני הסגירה של " + dm(date_iso) + " (ותמונת החוזים/דוחות של "
            "הבוקר) ל-The Daily Edge. כתוב את הניתוח היומי לפי ההנחיות:\n\n"
            + json.dumps(ctx, ensure_ascii=False, indent=1, default=str))


def main():
    idx = load(os.path.join(DATA, "indices.json"))
    if not idx or not idx.get("date") or not (idx.get("scores") or {}).get("combined"):
        print("[skip] אין indices.json תקין.")
        return 0

    prev = load(OUT) or {}
    if prev.get("date") and prev["date"] >= idx["date"]:
        print(f"[skip] כבר נותח {prev.get('date')} (indices: {idx['date']}).")
        return 0

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[skip] אין ANTHROPIC_API_KEY — עדכון ידני עד שיוגדר ב-Secrets.")
        return 0

    try:
        import anthropic
        from pydantic import BaseModel
    except Exception as e:
        print(f"[warn] anthropic/pydantic לא מותקנים: {e}")
        return 0

    class DailyAnalysis(BaseModel):
        headline: str
        tldr: str
        bottomline: str
        paragraphs: list[str]
        watchFor: str
        confidence: str

    mkt = load(os.path.join(DATA, "market.json")) or {}
    earn = load(os.path.join(DATA, "earnings.json")) or {}
    econ = load(os.path.join(DATA, "econ.json")) or {}
    context = build_context(idx, mkt, earn, econ, prev)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.parse(
            model=MODEL,
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": context}],
            output_format=DailyAnalysis,
        )
    except anthropic.RateLimitError as e:
        print(f"[warn] Claude API rate-limited: {e}")
        return 0
    except anthropic.APIStatusError as e:
        print(f"[warn] Claude API status error ({e.status_code}): {e.message}")
        return 0
    except anthropic.APIConnectionError as e:
        print(f"[warn] Claude API connection error: {e}")
        return 0
    except Exception as e:
        print(f"[warn] כשל לא צפוי בקריאת Claude API: {e}")
        return 0

    if getattr(response, "stop_reason", None) == "refusal":
        print("[warn] הבקשה נדחתה ע\"י Claude (refusal) — מדלג.")
        return 0

    result = response.parsed_output
    if not result or not result.headline or len(result.paragraphs or []) < 3:
        print("[warn] תשובה חסרה/לא תקינה (כותרת/פסקאות) — מדלג בלי לכתוב.")
        return 0

    out = {
        "date": idx["date"],
        "headline": result.headline,
        "tldr": result.tldr,
        "bottomline": result.bottomline,
        "paragraphs": result.paragraphs,
        "watchFor": result.watchFor,
        "confidence": result.confidence,
        "source": "claude",
        "_meta": {"updatedAt": il_stamp(), "source": "claude-daily-analysis-auto"},
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"[done] {idx['date']} נותח אוטומטית ונכתב ל-{OUT}")

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHANNEL")
    if token and chat:
        try:
            msg = (f"🤖 כותרת יומית נכתבה אוטומטית לסגירת {dm(idx['date'])}:\n"
                   f"<b>{result.headline}</b>\n\n{result.tldr}")
            send(token, chat, msg)
        except Exception as e:
            print(f"[warn] שליחת טלגרם נכשלה (לא קריטי): {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
