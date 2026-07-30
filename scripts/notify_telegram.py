#!/usr/bin/env python3
"""
notify_telegram.py — מפרסם תזכורת בערוץ טלגרם כשמתפרסם תדרוך משקיעים חדש
(בוקר / אחר הצהריים), עם הכותרת, הסנטימנט ולינק לאתר.

רץ בכל הרצת Action. שולח פעם אחת לכל תדרוך חדש (מצב שמור ב-data/_telegram_state.json).
בהרצה הראשונה (בלי state) — רק קובע בסיס בלי לשלוח, כדי לא לשלוח תדרוכים ישנים.

סודות: TELEGRAM_BOT_TOKEN (מ-@BotFather) + TELEGRAM_CHANNEL (למשל @nidam_markets).
בדיקה: python notify_telegram.py --test  → שולח הודעת בדיקה לערוץ.
"""
import html
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIEF = os.path.join(ROOT, "data", "briefing.json")
STATE = os.path.join(ROOT, "data", "_telegram_state.json")
SITE = "https://nditzik.github.io/nidam-markets/#briefing"


def load(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def send(token, chat, text):
    url = "https://api.telegram.org/bot%s/sendMessage" % token
    data = json.dumps({
        "chat_id": chat, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": False,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def compose(slot):
    sent = slot.get("sentiment") or {}
    subj = html.escape(slot.get("subject", ""))
    emoji = sent.get("emoji", "")
    stext = html.escape(sent.get("text", ""))
    line2 = (emoji + " " + stext).strip()
    return ("<b>%s</b>\n%s\n\n🔗 <a href=\"%s\">לתדרוך המלא באתר</a>"
            % (subj, line2, SITE))


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHANNEL")
    if not token or not chat:
        print("[skip] אין TELEGRAM_BOT_TOKEN / TELEGRAM_CHANNEL — דילוג.")
        return 0

    if "--test" in sys.argv:
        try:
            send(token, chat, "✅ <b>בדיקת חיבור</b>\nהבוט של שוק ההון מחובר לערוץ בהצלחה.")
            print("[ok] הודעת בדיקה נשלחה.")
            return 0
        except Exception as e:
            print("[fail] בדיקה נכשלה: %s" % e)
            return 1

    b = load(BRIEF)
    if not isinstance(b, dict):
        print("[skip] אין briefing.json.")
        return 0

    state = load(STATE)
    first_run = state is None
    if state is None:
        state = {}

    changed = False
    for slot_key, label in (("morning", "בוקר"), ("afternoon", "אחר הצהריים")):
        s = b.get(slot_key)
        if not isinstance(s, dict):
            continue
        sig = "|".join([s.get("subject", ""), s.get("dateLabel", ""), s.get("time", "")])
        if state.get(slot_key) == sig:
            continue
        if first_run:
            state[slot_key] = sig  # baseline only — don't send old briefings
            changed = True
            continue
        try:
            send(token, chat, compose(s))
            state[slot_key] = sig
            changed = True
            print("[ok] תזכורת %s נשלחה לערוץ." % label)
        except Exception as e:
            print("[warn] שליחת %s נכשלה: %s" % (label, e))

    if first_run:
        print("[baseline] הרצה ראשונה — נקבע בסיס, לא נשלחו תדרוכים ישנים.")
    if changed:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    else:
        print("[nochange] אין תדרוך חדש לשליחה.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
