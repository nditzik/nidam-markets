#!/usr/bin/env python3
r"""
notify_telegram_broadcast.py — שידור אוטומטי לערוץ: כל תמונה חדשה שאיציק שומר
תחת C:\challenge\reports\ (בכל תת-תיקייה) נשלחת אוטומטית לערוץ הטלגרם, כולל
שורת ה-footer הסטנדרטית (קישור לאתר).

מקור: עץ הקבצים המלא של הריפו הציבורי nidam-reports (המשימה המתוזמנת המקומית
נדים-reports-sync דוחפת את C:\challenge\reports לשם כל 5 דק' — לא נוגעים בה,
רק קוראים ממנה). סורק רק קבצי תמונה (png/jpg/jpeg/webp/gif) — קבצי HTML/CSV
כבר זורמים לאתר דרך fetch_reports/fetch_sectors/fetch_trades/fetch_earnings
ולא משודרים כאן (sendPhoto ממילא לא היה מקבל אותם).

דה-דופ: data/_telegram_broadcast_state.json {sent: {path: sha}} — sha משתנה
כשהתוכן משתנה (למשל תיקון קובץ עם אותו שם), כך שגרסה מתוקנת נשלחת מחדש בכוונה.
הרצה ראשונה (בלי state) קובעת בסיס בלי לשלוח — לא משדר תמונות ישנות.

סודות: TELEGRAM_BOT_TOKEN + TELEGRAM_CHANNEL.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "_telegram_broadcast_state.json")
TREE_API = "https://api.github.com/repos/nditzik/nidam-reports/git/trees/main?recursive=1"
RAW_BASE = "https://raw.githubusercontent.com/nditzik/nidam-reports/main/"
SITE = "https://nditzik.github.io/nidam-markets/"
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")
MAX_PER_RUN = 4   # רשת בטיחות מפני הצפה אם נוספו הרבה תמונות בבת אחת


def load(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def label_of(path):
    name = os.path.splitext(path.rsplit("/", 1)[-1])[0]
    return name.replace("_", " ").replace("-", " ").strip()


def send_photo(token, chat, image_url, caption):
    url = "https://api.telegram.org/bot%s/sendPhoto" % token
    data = json.dumps({
        "chat_id": chat, "photo": image_url, "caption": caption,
        "parse_mode": "HTML",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHANNEL")
    if not token or not chat:
        print("[skip] אין TELEGRAM_BOT_TOKEN / TELEGRAM_CHANNEL — דילוג.")
        return 0

    try:
        req = urllib.request.Request(TREE_API, headers={
            "User-Agent": "nidam-markets-bot", "Accept": "application/vnd.github+json",
        })
        with urllib.request.urlopen(req, timeout=25) as r:
            tree = json.loads(r.read().decode("utf-8")).get("tree", [])
    except Exception as e:
        print(f"[warn] קריאת עץ nidam-reports נכשלה: {e}")
        return 0

    images = [t for t in tree if t.get("type") == "blob"
              and t.get("path", "").lower().endswith(IMAGE_EXT)]

    state = load(STATE)
    first_run = state is None
    if state is None:
        state = {"sent": {}}
    sent = state.setdefault("sent", {})

    changed = False
    sent_count = 0
    pending = []
    for t in sorted(images, key=lambda t: t.get("path", "")):
        path, sha = t["path"], t.get("sha", "")
        if sent.get(path) == sha:
            continue
        if first_run:
            sent[path] = sha
            changed = True
            continue
        if sent_count >= MAX_PER_RUN:
            pending.append(path)
            continue
        image_url = RAW_BASE + urllib.parse.quote(path, safe="/")
        caption = ("🖼 <b>%s</b>\n\n🔗 <a href=\"%s\">האתר המלא</a>"
                   % (label_of(path), SITE))
        try:
            send_photo(token, chat, image_url, caption)
            sent[path] = sha
            changed = True
            sent_count += 1
            print(f"[ok] נשלח: {path}")
        except Exception as e:
            print(f"[warn] שליחת {path} נכשלה: {e}")

    if first_run:
        print(f"[baseline] הרצה ראשונה — {len(sent)} תמונות קיימות נקבעו כבסיס, לא נשלחו.")
    if pending:
        print(f"[queued] {len(pending)} תמונות נוספות ימתינו לריצה הבאה (תקרה {MAX_PER_RUN}/ריצה).")
    if changed:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    elif not first_run:
        print("[nochange] אין תמונות חדשות.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
