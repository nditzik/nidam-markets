#!/usr/bin/env python3
"""
fetch_dashboards.py — מושך את נתוני המדדים מריפו indexes-status
ומייצר data/indices.json לצריכת האתר.

מקור ראשי: raw.githubusercontent (הריפו הציבורי).
נפילת גיבוי: קובץ מקומי של הריפו השכן (לפיתוח מקומי).
עמידות: אם המשיכה נכשלת אבל כבר יש indices.json — משאיר אותו כמו שהוא (לא מפיל את ה-Action).
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

RAW_URL = "https://raw.githubusercontent.com/nditzik/indexes-status/main/data/daily_state.json"
AI_URL = "https://raw.githubusercontent.com/nditzik/indexes-status/main/data/ai_analysis.json"
LOCAL_FALLBACK = os.path.join("..", "indexes status", "data", "daily_state.json")
AI_LOCAL = os.path.join("..", "indexes status", "data", "ai_analysis.json")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "indices.json")


def israel_now_str():
    """שעון ישראל (IST/IDT) — קירוב: קיץ +3, חורף +2 לפי חודש."""
    now_utc = datetime.now(timezone.utc)
    # אפריל–אוקטובר ≈ שעון קיץ (+3), אחרת (+2). קירוב מספק לחותמת תצוגה.
    offset = 3 if 4 <= now_utc.month <= 10 else 2
    local = now_utc + timedelta(hours=offset)
    return local.strftime("%d/%m/%Y %H:%M")


def load_source():
    # 1) URL
    try:
        req = urllib.request.Request(RAW_URL, headers={"User-Agent": "nidam-markets-bot"})
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"[ok] נמשך מ-{RAW_URL}")
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"[warn] משיכת URL נכשלה: {e}")
    # 2) local sibling repo (dev)
    local = os.path.normpath(os.path.join(ROOT, LOCAL_FALLBACK))
    if os.path.exists(local):
        try:
            with open(local, "r", encoding="utf-8") as f:
                print(f"[ok] נטען מקומית מ-{local}")
                return json.load(f)
        except Exception as e:
            print(f"[warn] קריאה מקומית נכשלה: {e}")
    return None


def load_ai_summary():
    """הסיכום היומי (ai_analysis.json) — אופציונלי; כשל לא מפיל את המשיכה."""
    try:
        req = urllib.request.Request(AI_URL, headers={"User-Agent": "nidam-markets-bot"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"[info] אין סיכום יומי מה-URL ({e})")
    local = os.path.normpath(os.path.join(ROOT, AI_LOCAL))
    if os.path.exists(local):
        try:
            with open(local, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def main():
    data = load_source()
    if data is None:
        if os.path.exists(OUT):
            print("[keep] מקור לא זמין — משאיר את indices.json הקיים.")
            return 0
        print("[fail] אין מקור ואין קובץ קיים.")
        return 1

    ai = load_ai_summary()
    if ai and ai.get("headline"):
        data["aiSummary"] = ai
        print(f"[ok] סיכום יומי צורף ({ai.get('date')})")

    data["_meta"] = {
        "updatedAt": israel_now_str(),
        "source": "indexes-status",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
