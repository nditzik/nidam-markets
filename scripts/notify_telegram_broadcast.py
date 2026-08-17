#!/usr/bin/env python3
r"""
notify_telegram_broadcast.py — שידור אוטומטי לערוץ: כל תמונה שאיציק שומר תחת
C:\challenge\reports\טלגרם\ נשלחת אוטומטית לערוץ הטלגרם — הודעה אחת שנראית כך:
שורת "🔗 לאתר המלא" ומתחתיה כרטיס-אתר מלא (שם האתר + התיאור) שבתוכו התמונה
עצמה בגדול.

איך זה עובד (מגבלת טלגרם ופתרונה): טלגרם בונה כרטיס-תצוגה עשיר רק לקישור
בהודעת *טקסט* — לעולם לא ל-caption של תמונה. לכן לכל תמונה נוצר דף-נחיתה זעיר
באתר (data/tg/tg-<sha>.html) שתגיות ה-OG שלו מצהירות: כותרת/תיאור = מיתוג
האתר, תמונת-שיתוף = התמונה המשודרת. שולחים sendMessage שמצביע לדף — טלגרם
מרנדר את הכרטיס עם התמונה בפנים, והקליק מפנה מיד לדף הבית (meta refresh).
הדף חייב להיות חי ב-Pages לפני השליחה, לכן הסקריפט דוחף אותו בעצמו וממתין
לפרסום (עד ~4 דק'); אם הפרסום מתעכב — נשלחת התמונה בפורמט הפשוט (caption)
כדי שהשידור לא ילך לאיבוד.

מקור: תת-התיקייה "טלגרם" בריפו nidam-reports (המשימה המתוזמנת המקומית דוחפת
את C:\challenge\reports לשם כל 5 דק'). תיקייה ייעודית בכוונה — תמונות שנשמרות
במקומות אחרים לצרכים אחרים לא ישודרו בטעות. רק קבצי תמונה (png/jpg/jpeg/webp/gif).

דה-דופ: data/_telegram_broadcast_state.json {sent: {path: sha}} — sha משתנה
כשהתוכן משתנה (תיקון קובץ באותו שם), כך שגרסה מתוקנת נשלחת מחדש בכוונה.
הרצה ראשונה (בלי state) קובעת בסיס בלי לשלוח — לא משדר תמונות ישנות.

סודות: TELEGRAM_BOT_TOKEN + TELEGRAM_CHANNEL.
"""
import html
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "_telegram_broadcast_state.json")
TREE_API = "https://api.github.com/repos/nditzik/nidam-reports/git/trees/main?recursive=1"
RAW_BASE = "https://raw.githubusercontent.com/nditzik/nidam-reports/main/"
SITE = "https://nditzik.github.io/nidam-markets/"
TG_DIR_REL = "data/tg"                      # דפי-הנחיתה של הכרטיסים
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")
WATCH_DIR = "טלגרם/"   # רק תיקייה ייעודית זו משודרת — לא כל nidam-reports
MAX_PER_RUN = 4   # רשת בטיחות מפני הצפה אם נוספו הרבה תמונות בבת אחת
PAGES_WAIT_SEC = 240   # המתנה מרבית לפרסום דף-הנחיתה ב-Pages לפני fallback

OG_TITLE = "The Daily Edge by NIDAM"
OG_DESC = "השוק, כל יום — בשפה של משקיעים. תדריכים, מדדים, מומנטום, מועמדים וניתוחי דוחות."

PAGE_TMPL = """<!DOCTYPE html>
<html lang="he">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta property="og:type" content="website">
<meta property="og:site_name" content="{title}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{image}">
<meta name="twitter:card" content="summary_large_image">
<meta property="og:url" content="{site}">
<meta http-equiv="refresh" content="0;url={site}">
</head>
<body><a href="{site}">{title}</a></body>
</html>
"""


def load(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def tg_api(token, method, payload):
    url = "https://api.telegram.org/bot%s/%s" % (token, method)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def send_card(token, chat, page_url):
    """הודעת טקסט שהקישור בה מצביע לדף-הנחיתה — טלגרם בונה ממנו את הכרטיס
    (שם+תיאור+התמונה בגדול). הקליק מגיע לאתר דרך ה-redirect של הדף."""
    return tg_api(token, "sendMessage", {
        "chat_id": chat,
        "text": "🔗 <a href=\"%s\">לאתר המלא</a>" % page_url,
        "parse_mode": "HTML",
        "link_preview_options": {"url": page_url, "prefer_large_media": True},
    })


def send_photo_fallback(token, chat, image_url):
    """גיבוי אם Pages לא פרסם בזמן: הפורמט הפשוט — תמונה + שורת הקישור."""
    return tg_api(token, "sendPhoto", {
        "chat_id": chat, "photo": image_url,
        "caption": "🔗 <a href=\"%s\">לאתר המלא</a>" % SITE,
        "parse_mode": "HTML",
    })


def git(*args):
    return subprocess.run(["git", "-C", ROOT] + list(args),
                          capture_output=True, text=True, timeout=120)


def push_pages(paths):
    """דוחף את דפי-הנחיתה מיד (לא מחכים לצעד ה-commit של ה-Action — השליחה
    צריכה את הדף חי עכשיו). retry עם rebase כמו בצעד ה-commit הראשי."""
    git("add", *paths)
    r = git("-c", "user.name=nidam-markets-bot", "-c", "user.email=actions@github.com",
            "commit", "-m", "data: telegram broadcast card pages")
    if r.returncode != 0:
        return "nothing to commit" in (r.stdout + r.stderr)
    for _ in range(4):
        if git("push").returncode == 0:
            return True
        git("pull", "--rebase", "--autostash", "origin", "main")
        time.sleep(3)
    return False


def wait_live(url, timeout_sec):
    """ממתין שהדף יעלה ל-Pages (יחזיר 200). מחזיר True אם חי."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, method="HEAD",
                                         headers={"User-Agent": "nidam-markets-bot"})
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(6)
    return False


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
              and t.get("path", "").startswith(WATCH_DIR)
              and t.get("path", "").lower().endswith(IMAGE_EXT)]

    state = load(STATE)
    first_run = state is None
    if state is None:
        state = {"sent": {}}
    sent = state.setdefault("sent", {})

    # שלב א' — איסוף התמונות החדשות של הריצה (עד התקרה)
    queue = []
    pending = 0
    for t in sorted(images, key=lambda t: t.get("path", "")):
        path, sha = t["path"], t.get("sha", "")
        if sent.get(path) == sha:
            continue
        if first_run:
            sent[path] = sha
            continue
        if len(queue) >= MAX_PER_RUN:
            pending += 1
            continue
        queue.append((path, sha))

    if first_run:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print(f"[baseline] הרצה ראשונה — {len(sent)} תמונות קיימות נקבעו כבסיס, לא נשלחו.")
        return 0
    if not queue:
        print("[nochange] אין תמונות חדשות.")
        return 0

    # שלב ב' — יצירת דפי-הנחיתה של הכרטיסים ודחיפתם ל-Pages
    os.makedirs(os.path.join(ROOT, TG_DIR_REL), exist_ok=True)
    page_files = []
    for path, sha in queue:
        image_url = RAW_BASE + urllib.parse.quote(path, safe="/")
        page_rel = f"{TG_DIR_REL}/tg-{sha[:12]}.html"
        with open(os.path.join(ROOT, page_rel), "w", encoding="utf-8") as f:
            f.write(PAGE_TMPL.format(
                title=html.escape(OG_TITLE), desc=html.escape(OG_DESC),
                image=html.escape(image_url), site=SITE))
        page_files.append(page_rel)
    pushed = push_pages(page_files)
    if not pushed:
        print("[warn] דחיפת דפי-הכרטיס נכשלה — נופלים לפורמט הפשוט.")

    # שלב ג' — שליחה: כרטיס אם הדף חי, אחרת fallback לתמונה+כיתוב
    changed = False
    for (path, sha), page_rel in zip(queue, page_files):
        image_url = RAW_BASE + urllib.parse.quote(path, safe="/")
        page_url = SITE + page_rel
        try:
            if pushed and wait_live(page_url, PAGES_WAIT_SEC):
                send_card(token, chat, page_url)
                print(f"[ok] נשלח ככרטיס: {path}")
            else:
                send_photo_fallback(token, chat, image_url)
                print(f"[ok] נשלח בפורמט פשוט (fallback): {path}")
            sent[path] = sha
            changed = True
        except Exception as e:
            print(f"[warn] שליחת {path} נכשלה: {e}")

    if pending:
        print(f"[queued] {pending} תמונות נוספות ימתינו לריצה הבאה (תקרה {MAX_PER_RUN}/ריצה).")
    if changed:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
