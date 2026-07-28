#!/usr/bin/env python3
"""
fetch_ibkr.py — מושך את מועמדי ה-IBKR מג'ימייל (IMAP) → data/candidates.json.

מאתר את המייל האחרון עם נושא שמתחיל ב-"[IBKR-CANDIDATES]" (נשלח מהמערכת המקומית
דרך export_candidates.py), מחלץ את הקובץ המצורף candidates.json וכותב אותו.
המייל הוא candidate-only מעצם בנייתו — אין בו נתוני חשבון/פוזיציות/יתרות.

דורש סודות (זהים לשאר): GMAIL_USER + GMAIL_APP_PASSWORD.
עמידות: כשל/היעדר מקור → משאיר candidates.json קיים.
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
OUT = os.path.join(ROOT, "data", "candidates.json")

MAILBOX = '"[Gmail]/All Mail"'
SUBJECT_TAG = "[IBKR-CANDIDATES]"


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def imap_since(days=7):
    d = datetime.now(timezone.utc) - timedelta(days=days)
    m = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{d.day:02d}-{m[d.month - 1]}-{d.year}"


def extract_json_attachment(msg):
    for part in msg.walk():
        fn = part.get_filename() or ""
        ctype = part.get_content_type()
        if fn.lower().endswith(".json") or ctype == "application/json":
            payload = part.get_payload(decode=True)
            if payload:
                try:
                    return json.loads(payload.decode("utf-8", "ignore"))
                except Exception as e:
                    print(f"[warn] קובץ מצורף לא תקין: {e}")
    return None


def write_if_changed(payload):
    existing = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}
    if {k: v for k, v in existing.items() if k != "_meta"} == \
       {k: v for k, v in payload.items() if k != "_meta"}:
        print("[nochange] אין מועמדים חדשים — candidates.json נשאר כפי שהוא.")
        return
    payload = dict(payload)
    payload["_meta"] = {"updatedAt": israel_stamp(), "source": "ibkr-swing-system"}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT} ({payload.get('shown', '?')} מועמדים, {payload.get('date')})")


def main():
    user = os.environ.get("GMAIL_USER")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not pw:
        print("[warn] חסרים GMAIL_USER / GMAIL_APP_PASSWORD.")
        return 0 if os.path.exists(OUT) else 1
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(user, pw)
        imap.select(MAILBOX, readonly=True)
    except Exception as e:
        print(f"[warn] חיבור IMAP נכשל: {e}")
        return 0 if os.path.exists(OUT) else 1
    try:
        # חיפוש ASCII-בטוח: נושא + טווח זמן
        typ, data = imap.search(None, "SUBJECT", SUBJECT_TAG, "SINCE", imap_since())
        ids = data[0].split() if typ == "OK" and data and data[0] else []
        for mid in reversed(ids):  # מהחדש לישן
            typ, md = imap.fetch(mid, "(RFC822)")
            if typ != "OK" or not md or not md[0]:
                continue
            msg = email.message_from_bytes(md[0][1])
            subject = str(email.header.make_header(email.header.decode_header(msg.get("Subject") or ""))) \
                if msg.get("Subject") else ""
            if SUBJECT_TAG not in subject:
                continue
            payload = extract_json_attachment(msg)
            if payload and "candidates" in payload:
                write_if_changed(payload)
                print(f"[ok] {subject}")
                return 0
        print("[warn] לא נמצא מייל [IBKR-CANDIDATES] עם קובץ תקין.")
        return 0 if os.path.exists(OUT) else 1
    finally:
        try:
            imap.logout()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
