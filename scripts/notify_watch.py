#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notify_watch.py — התראות על חברות שאיציק מחזיק, מ-X לערוץ הטלגרם.

בוט ה-Grok סורק חשבונות X סביב הטיקרים שבתיק ושולח מייל בנושא "WATCH-ALERT",
בפורמט שורות זהה לדיג'סט של fetch_pulse, עם שני שדות נוספים בראש:

    NEWS ||| TICKER ||| @handle ||| אנגלית ||| עברית ||| קישור

הסקריפט קורא את המיילים ב-IMAP (אותם סודות GMAIL_* של שאר צינורות המייל),
מסנן מה שכבר נשלח, ומפרסם לערוץ. הודעה אחת לכל פריט — לא מקבץ — כדי שכל
התראה תהיה ניתנת לשיתוף ולקריאה בפני עצמה.

⚠️ שיקול מקורות (7.9.2026): בניגוד ל"בזק מהרשת", שמוזן משירותי חדשות מבוססים
(FinancialJuice/Barchart/Kobeissi/Walter Bloomberg), המקורות כאן הם לרוב
חשבונות X של אנשים פרטיים. לכן ההודעה **תמיד** נושאת ייחוס מפורש לחשבון
המקור ולינק לפוסט — הקורא צריך לדעת שזו ידיעה מ-X ולא ממסוף מקצועי, ולהיות
מסוגל לאמת בעצמו בלחיצה אחת.

מצבי הרצה:
    python notify_watch.py --dry-run   → מדפיס את ההודעות בלי לשלוח ובלי IMAP
    python notify_watch.py --test      → שולח הודעת דוגמה אחת ל-ADMIN (פרטי)
    python notify_watch.py             → ריצה רגילה (IMAP → ערוץ)
עמידות: כל כשל (אין סודות/רשת/פורמט) → יציאה 0 בלי לשלוח ובלי להפיל את ה-Action.
"""
import email
import email.header
import html as htmllib
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify_telegram import load, send
import fetch_pulse as fp          # שימוש חוזר ב-IMAP/פענוח-לינקים/ניקוי-טקסט

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "_watch_state.json")

SUBJECT_MARK = "WATCH-ALERT"      # עוגן ASCII, מאותה סיבה כמו X-PULSE
KIND_MARK = "NEWS"
MAX_PER_RUN = 5                   # תקרה: התפרצות בבוט לא תציף את הערוץ
KEEP_KEYS = 400                   # גודל זיכרון הדה-דופ


def il_now():
    now = datetime.now(timezone.utc)
    return now + timedelta(hours=3 if 4 <= now.month <= 10 else 2)


def parse_watch(body):
    """שורות WATCH-ALERT → פריטים. שורה פגומה מדולגת ולא מפילה את השאר."""
    out = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or fp.XD_SEP not in line:
            continue
        parts = [p.strip() for p in line.split(fp.XD_SEP)]
        if len(parts) < 5 or parts[0].upper() != KIND_MARK:
            continue
        ticker, handle = parts[1].upper().lstrip("$"), parts[2]
        rest = parts[3:]
        link = ""
        if re.match(r"^https?://", rest[-1]):
            link = fp._unwrap_link(rest[-1])
            rest = rest[:-1]
        if not rest or not re.match(r"^[A-Z][A-Z.\-]{0,9}$", ticker) or not handle.startswith("@"):
            continue
        # כמו בדיג'סט: השדה האחרון הוא עברית רק אם ריק או מכיל אותיות עבריות
        if len(rest) >= 2 and (not rest[-1] or re.search(r"[֐-׿]", rest[-1])):
            en, he = (" " + fp.XD_SEP + " ").join(rest[:-1]), rest[-1]
        else:
            en, he = (" " + fp.XD_SEP + " ").join(rest), ""
        en, he = fp.clean_text(en), fp.clean_text(he)
        if not en or len(en) < 20:
            continue
        out.append({"ticker": ticker, "handle": handle, "en": en, "he": he, "link": link})
    return out


def compose(it):
    """הודעת טלגרם אחת. עברית כשיש, ונפילה לאנגלית כשאין."""
    body = it["he"] or it["en"]
    txt = (f"🔔 <b>{htmllib.escape(it['ticker'])}</b> · עדכון על חברה בתיק\n\n"
           f"{htmllib.escape(body)}\n\n"
           f"<i>מקור: {htmllib.escape(it['handle'])} ב-X · "
           f"{il_now().strftime('%d.%m %H:%M')}</i>")
    if it["link"]:
        txt += f'\n🔗 <a href="{htmllib.escape(it["link"], quote=True)}">לפוסט המקורי</a>'
    return txt


def fetch_watch_items():
    """פריטי WATCH-ALERT מהמייל; כל כשל → רשימה ריקה (בלי להפיל את ה-Action)."""
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not pw:
        print("[skip] חסר GMAIL_APP_PASSWORD.")
        return []
    user = os.environ.get("GMAIL_USER") or fp.XD_SENDER
    imap = None
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(user, pw)
        imap.select('"[Gmail]/All Mail"', readonly=True)
        since = datetime.now(timezone.utc) - timedelta(days=2)
        mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][since.month - 1]
        typ, data = imap.search(None, "FROM", fp.XD_SENDER,
                                "SINCE", f"{since.day:02d}-{mon}-{since.year}")
        ids = data[0].split() if typ == "OK" and data and data[0] else []
        items, scanned = [], 0
        for mid in reversed(ids):                 # מהחדש לישן
            if scanned >= 20:
                break
            typ, md = imap.fetch(mid, "(RFC822)")
            if typ != "OK" or not md or not md[0]:
                continue
            msg = email.message_from_bytes(md[0][1])
            subject = str(email.header.make_header(
                email.header.decode_header(msg.get("Subject") or "")))
            if SUBJECT_MARK not in subject:
                continue
            scanned += 1
            got = parse_watch(fp._mail_body(msg))
            items += got
            print(f"[ok] {subject[:44]} — {len(got)} פריטים")
        if not scanned:
            print(f"[warn] לא נמצא מייל '{SUBJECT_MARK}' ביומיים האחרונים.")
        return items
    except Exception as e:
        print(f"[warn] קריאת WATCH-ALERT נכשלה: {e}")
        return []
    finally:
        try:
            if imap:
                imap.logout()
        except Exception:
            pass


def main():
    dry = "--dry-run" in sys.argv
    test = "--test" in sys.argv
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_ADMIN_CHAT") if test else os.environ.get("TELEGRAM_CHANNEL")

    if test or dry:
        sample = ("NEWS ||| NVO ||| @ByLizC ||| Novo Nordisk confirmed it stopped the HERMES "
                  "and ATHENA ziltivekimab heart-drug trials for futility. ||| נובו נורדיסק "
                  "אישרה שהפסיקה את ניסויי HERMES ו־ATHENA בתרופת הלב זילטיבקימאב בשל חוסר "
                  "תועלת. ||| https://x.com/ByLizC/status/2096873396487274824")
        items = parse_watch(sample)
        for it in items:
            print("─" * 58)
            print(compose(it))
            print("─" * 58)
        if dry or not (token and chat):
            if not dry:
                print("[skip] חסר TELEGRAM_BOT_TOKEN/TELEGRAM_ADMIN_CHAT — לא נשלח.")
            return 0
        for it in items:
            send(token, chat, compose(it))
        print(f"[ok] נשלחו {len(items)} הודעות בדיקה ל-ADMIN (פרטי, לא לערוץ).")
        return 0

    if not (token and chat):
        print("[skip] חסרים סודות טלגרם.")
        return 0
    items = fetch_watch_items()
    if not items:
        print("[skip] אין פריטי WATCH-ALERT חדשים.")
        return 0

    st = load(STATE) or {}
    seen = st.get("seen", [])
    seen_set = set(seen)
    fresh = []
    for it in items:
        key = it["link"] or re.sub(r"\W+", "", it["en"].lower())[:60]
        if key in seen_set:
            continue
        seen_set.add(key)
        seen.append(key)
        fresh.append(it)
    if not fresh:
        print("[ok] כל הפריטים כבר נשלחו.")
        return 0

    sent = 0
    for it in fresh[:MAX_PER_RUN]:
        try:
            send(token, chat, compose(it))
            sent += 1
        except Exception as e:
            print(f"[warn] שליחה נכשלה ({it['ticker']}): {e}")
    if len(fresh) > MAX_PER_RUN:
        print(f"[note] {len(fresh) - MAX_PER_RUN} פריטים מעבר לתקרה — יישלחו בריצה הבאה.")
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump({"seen": seen[-KEEP_KEYS:]}, f, ensure_ascii=False)
    print(f"[done] נשלחו {sent} התראות לערוץ.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
