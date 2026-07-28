#!/usr/bin/env python3
"""
fetch_barchart.py — מושך את "סיכום Barchart יומי" מג'ימייל (IMAP) → data/morning.json
+ data/briefings/morning-review.html (טאב "סקירת בוקר").

זהו מייל HTML עברי מעוצב שאיציק שולח לעצמו בבוקר (~06:00), נושא:
"📊 סיכום Barchart יומי — DD ביולי YYYY", מ-nditzik@gmail.com. נשמר כקובץ HTML
ומוצג ב-iframe (כמו טאב תדרוך משקיעים) — לא חילוץ טקסט.

דורש סודות: GMAIL_USER + GMAIL_APP_PASSWORD.
מצב בדיקה מקומי:  python fetch_barchart.py --file <saved_message.json>
עמידות: כשל/היעדר מקור → משאיר morning.json קיים.
"""
import email
import email.header
import email.utils
import imaplib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(ROOT, "data", "morning.json")
OUT_DIR = os.path.join(ROOT, "data", "briefings")
OUT_HTML = os.path.join(OUT_DIR, "morning-review.html")
HTML_REL = "data/briefings/morning-review.html"

MAILBOX = '"[Gmail]/All Mail"'
SENDER = "nditzik@gmail.com"
SUBJECT_MARK = "סיכום Barchart יומי"


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def imap_since(days=3):
    d = datetime.now(timezone.utc) - timedelta(days=days)
    m = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{d.day:02d}-{m[d.month - 1]}-{d.year}"


def dec(s):
    if not s:
        return ""
    return str(email.header.make_header(email.header.decode_header(s)))


def html_of(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                p = part.get_payload(decode=True)
                if p:
                    return p.decode(part.get_content_charset() or "utf-8", "ignore")
    else:
        p = msg.get_payload(decode=True)
        if p:
            return p.decode(msg.get_content_charset() or "utf-8", "ignore")
    return ""


def date_label(subject, date_dt):
    # הכותרת מכילה "— DD ביולי YYYY"; אם לא — נופלים לתאריך המייל
    if "—" in subject:
        tail = subject.split("—", 1)[1].strip()
        if tail:
            return tail
    return date_dt.strftime("%d/%m/%Y") if date_dt else ""


def write_if_changed(subject, date_dt, html_body):
    changed = False
    old_html = None
    if os.path.exists(OUT_HTML):
        with open(OUT_HTML, "r", encoding="utf-8") as f:
            old_html = f.read()
    if html_body != old_html:
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(OUT_HTML, "w", encoding="utf-8") as f:
            f.write(html_body)
        changed = True

    ist = timezone(timedelta(hours=3))
    meta = {
        "subject": subject,
        "dateLabel": date_label(subject, date_dt),
        "time": date_dt.astimezone(ist).strftime("%H:%M") if date_dt else "",
        "file": HTML_REL,
    }
    existing = {}
    if os.path.exists(OUT_JSON):
        try:
            with open(OUT_JSON, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}
    if {k: v for k, v in existing.items() if k != "_meta"} != meta:
        changed = True
    if not changed and os.path.exists(OUT_JSON):
        print("[nochange] אין סיכום חדש — morning.json נשאר כפי שהוא.")
        return
    meta["_meta"] = {"updatedAt": israel_stamp(), "source": "gmail"}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT_JSON}")


def run_offline(path):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    try:
        date_dt = datetime.fromisoformat(d["date"].replace("Z", "+00:00"))
    except ValueError:
        date_dt = email.utils.parsedate_to_datetime(d["date"])
    write_if_changed(d["subject"], date_dt, d["htmlBody"])
    return 0


def run_imap():
    user, pw = os.environ.get("GMAIL_USER"), os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not pw:
        print("[warn] חסרים GMAIL_USER / GMAIL_APP_PASSWORD.")
        return 0 if os.path.exists(OUT_JSON) else 1
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(user, pw)
        imap.select(MAILBOX, readonly=True)
    except Exception as e:
        print(f"[warn] חיבור IMAP נכשל: {e}")
        return 0 if os.path.exists(OUT_JSON) else 1
    try:
        # חיפוש ASCII-בטוח (FROM + SINCE); סינון הכותרת בעברית ב-Python
        typ, data = imap.search(None, "FROM", SENDER, "SINCE", imap_since())
        ids = data[0].split() if typ == "OK" and data and data[0] else []
        best = None
        for mid in reversed(ids):  # מהחדש לישן
            typ, md = imap.fetch(mid, "(RFC822)")
            if typ != "OK" or not md or not md[0]:
                continue
            msg = email.message_from_bytes(md[0][1])
            subject = dec(msg.get("Subject"))
            if subject.startswith("Fwd:") or subject.startswith("Fw:"):
                continue
            if SUBJECT_MARK not in subject:
                continue
            date_dt = email.utils.parsedate_to_datetime(msg.get("Date"))
            best = (subject, date_dt, html_of(msg))
            break
        if not best:
            print("[warn] לא נמצא 'סיכום Barchart יומי'.")
            return 0 if os.path.exists(OUT_JSON) else 1
        write_if_changed(*best)
        print(f"[ok] {best[0]}")
        return 0
    finally:
        try:
            imap.logout()
        except Exception:
            pass


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--file":
        return run_offline(sys.argv[2])
    return run_imap()


if __name__ == "__main__":
    sys.exit(main())
