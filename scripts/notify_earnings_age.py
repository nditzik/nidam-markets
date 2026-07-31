#!/usr/bin/env python3
r"""
notify_earnings_age.py — התראה פרטית בטלגרם (רק לאיציק) כשקובץ הדיווחים מתיישן.

מנגנון: שומר hash של earnings.csv + התאריך שבו התוכן הנוכחי נראה לראשונה
(data/_earnings_state.json). כשהתוכן משתנה — השעון מתאפס. אם עברו 21+ ימים
בלי עדכון — נשלחת הודעה פרטית, ותזכורת חוזרת כל 7 ימים כל עוד לא רוענן.

סודות: TELEGRAM_BOT_TOKEN + TELEGRAM_ADMIN_CHAT (ה-chat id הפרטי של איציק —
לא הערוץ!). בלי הסוד — עוקב אחרי הגיל בשקט ולא שולח.
בדיקה: python notify_earnings_age.py --test
"""
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify_telegram import send  # שימוש חוזר בשליחת הטלגרם הקיימת

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "_earnings_state.json")
REMOTE_CSV = "https://raw.githubusercontent.com/nditzik/nidam-reports/main/earnings.csv"
LOCAL_CSV = os.path.join(ROOT, "earnings.csv")

STALE_DAYS = 21   # מכאן הקובץ נחשב מתיישן
REMIND_DAYS = 7   # תדירות תזכורת חוזרת כל עוד לא רוענן


def israel_date():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).date()


def csv_bytes():
    try:
        req = urllib.request.Request(REMOTE_CSV, headers={"User-Agent": "nidam-markets-bot"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read()
    except Exception:
        pass
    try:
        with open(LOCAL_CSV, "rb") as f:
            return f.read()
    except Exception:
        return None


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_ADMIN_CHAT")

    if "--test" in sys.argv:
        if not token or not chat:
            print("[skip] חסר TELEGRAM_BOT_TOKEN / TELEGRAM_ADMIN_CHAT.")
            return 0
        try:
            send(token, chat, "✅ <b>בדיקת התראות פרטיות</b>\nהבוט יודע לשלוח לך הודעות אישיות (לא לערוץ).")
            print("[ok] הודעת בדיקה פרטית נשלחה.")
            return 0
        except Exception as e:
            print("[fail] %s" % e)
            return 1

    data = csv_bytes()
    if data is None:
        print("[skip] אין earnings.csv לבדיקה.")
        return 0

    digest = hashlib.sha1(data).hexdigest()
    today = israel_date()

    state = {}
    if os.path.exists(STATE):
        try:
            with open(STATE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    if state.get("hash") != digest:
        # הקובץ עודכן — איפוס השעון
        state = {"hash": digest, "firstSeen": today.isoformat(), "lastAlert": None}
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print("[fresh] earnings.csv עודכן — שעון ההתיישנות אופס.")
        return 0

    try:
        first = datetime.strptime(state.get("firstSeen", ""), "%Y-%m-%d").date()
    except ValueError:
        first = today
    age = (today - first).days
    print(f"[age] earnings.csv בן {age} ימים (סף: {STALE_DAYS}).")

    if age < STALE_DAYS:
        return 0

    last = state.get("lastAlert")
    if last:
        try:
            if (today - datetime.strptime(last, "%Y-%m-%d").date()).days < REMIND_DAYS:
                print("[quiet] כבר נשלחה תזכורת לאחרונה.")
                return 0
        except ValueError:
            pass

    if not token or not chat:
        print("[skip] הקובץ מתיישן אבל חסר TELEGRAM_ADMIN_CHAT — אין למי לשלוח.")
        return 0

    msg = ("📅 <b>תזכורת: קובץ הדיווחים מתיישן</b>\n"
           f"earnings.csv לא עודכן כבר {age} ימים.\n"
           "שמור קובץ טרי ל-<code>C:\\challenge\\reports</code> — והוא יעלה לאתר לבד.")
    try:
        send(token, chat, msg)
        state["lastAlert"] = today.isoformat()
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print("[ok] תזכורת פרטית נשלחה.")
    except Exception as e:
        print("[warn] שליחה נכשלה: %s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
