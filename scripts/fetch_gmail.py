#!/usr/bin/env python3
"""
fetch_gmail.py — מושך את "תדרוך משקיעים" (בוקר + אחר הצהריים) מג'ימייל דרך IMAP
ומייצר data/briefing.json + data/briefings/morning.html + afternoon.html.

דורש סודות (GitHub Secrets):
  GMAIL_USER          — כתובת הג'ימייל (nditzik@gmail.com)
  GMAIL_APP_PASSWORD  — App Password (16 תווים) מ- https://myaccount.google.com/apppasswords

עמידות: אם אין סוד/חיבור נכשל אבל כבר יש briefing.json — משאיר אותו (לא מפיל את ה-Action).
"""
import email
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from email.header import decode_header

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(ROOT, "data", "briefing.json")
OUT_DIR = os.path.join(ROOT, "data", "briefings")

MAILBOX = '"[Gmail]/All Mail"'
SENDER = "nditzik@gmail.com"
MORNING_MARK = "בוקר"
AFTERNOON_MARK = "אחר הצהריים"
SENTIMENT_RE = re.compile(r"([🟢🟡🔴])\s*([^<\n]{0,24})")


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def dec(s):
    if not s:
        return ""
    parts = decode_header(s)
    out = ""
    for text, enc in parts:
        out += text.decode(enc or "utf-8", "ignore") if isinstance(text, bytes) else text
    return out


def html_of(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", "ignore")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(msg.get_content_charset() or "utf-8", "ignore")
    return ""


def sentiment_of(html):
    # מחפש את אימוג'י הסנטימנט הראשון + המילה שאחריו (מתוך תגית ה-pill בכותרת)
    m = SENTIMENT_RE.search(html)
    if not m:
        return {"emoji": "", "text": ""}
    word = re.sub(r"[^֐-׿ \-–]", "", m.group(2)).strip()
    return {"emoji": m.group(1), "text": word}


def pick_latest(imap, mark, exclude=None):
    """מחזיר (subject, date_dt, html) עבור המייל האחרון שכותרתו מכילה 'תדרוך משקיעים' + mark."""
    typ, data = imap.search(None, 'FROM', f'"{SENDER}"', 'SUBJECT', '"תדרוך"')
    ids = data[0].split() if data and data[0] else []
    # מהחדש לישן
    for mid in reversed(ids):
        typ, msg_data = imap.fetch(mid, "(RFC822)")
        if typ != "OK" or not msg_data or not msg_data[0]:
            continue
        msg = email.message_from_bytes(msg_data[0][1])
        subject = dec(msg.get("Subject"))
        if "תדרוך משקיעים" not in subject or mark not in subject:
            continue
        if exclude and exclude in subject:
            continue
        date_dt = email.utils.parsedate_to_datetime(msg.get("Date"))
        return subject, date_dt, html_of(msg)
    return None


def build_slot(res):
    if not res:
        return None
    subject, date_dt, html = res
    return {"subject": subject, "date_dt": date_dt, "html": html}


def main():
    user = os.environ.get("GMAIL_USER")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not pw:
        print("[warn] חסרים GMAIL_USER / GMAIL_APP_PASSWORD.")
        if os.path.exists(OUT_JSON):
            print("[keep] משאיר briefing.json קיים.")
            return 0
        return 1

    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(user, pw)
        imap.select(MAILBOX, readonly=True)
    except Exception as e:
        print(f"[warn] חיבור IMAP נכשל: {e}")
        return 0 if os.path.exists(OUT_JSON) else 1

    try:
        morning = build_slot(pick_latest(imap, MORNING_MARK))
        afternoon = build_slot(pick_latest(imap, AFTERNOON_MARK))
    finally:
        try:
            imap.logout()
        except Exception:
            pass

    if not morning and not afternoon:
        print("[warn] לא נמצאו בריפים.")
        return 0 if os.path.exists(OUT_JSON) else 1

    os.makedirs(OUT_DIR, exist_ok=True)
    out = {"_meta": {"updatedAt": israel_stamp(), "source": "gmail"}}

    for key, slot, fname in (("morning", morning, "morning.html"),
                             ("afternoon", afternoon, "afternoon.html")):
        if not slot:
            continue
        with open(os.path.join(OUT_DIR, fname), "w", encoding="utf-8") as f:
            f.write(slot["html"])
        d = slot["date_dt"]
        out[key] = {
            "subject": slot["subject"],
            "dateLabel": d.strftime("%d/%m/%Y") if d else "",
            "time": d.astimezone(timezone(timedelta(hours=3))).strftime("%H:%M") if d else "",
            "sentiment": sentiment_of(slot["html"]),
            "file": f"data/briefings/{fname}",
        }
        print(f"[ok] {key}: {slot['subject']}")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
