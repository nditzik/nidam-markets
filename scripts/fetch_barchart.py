#!/usr/bin/env python3
"""
fetch_barchart.py — מושך את "Pre-Market Bulletin" של Barchart מג'ימייל (IMAP)
ומייצר תקציר מעובד נקי ל-data/morning.json (טאב "סקירת בוקר").

הניוזלטר של Barchart כבד מאוד (HTML שיווקי ~130KB); כאן מחלצים רק את גוף
הכתבה — כותרת + פסקאות הליבה — וזורקים פרסומות ("Sponsored"), טבלת Movers ופוטר.

דורש סודות (זהים ל-fetch_gmail): GMAIL_USER + GMAIL_APP_PASSWORD.
מצב בדיקה מקומי:  python fetch_barchart.py --file <saved_message.json>
עמידות: כשל/היעדר מקור → משאיר morning.json קיים.
"""
import email
import email.header
import email.utils
import html
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "morning.json")

MAILBOX = '"[Gmail]/All Mail"'
SENDER = "newsletters@barchart.com"
BULLETIN_MARK = "Pre-Market Bulletin"


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def imap_since(days=3):
    d = datetime.now(timezone.utc) - timedelta(days=days)
    m = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{d.day:02d}-{m[d.month - 1]}-{d.year}"


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


def extract_digest(html_body):
    """HTML גולמי → רשימת פסקאות ליבה נקיות."""
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", html_body)
    h = re.sub(r"(?is)<br\s*/?>", "\n", h)
    h = re.sub(r"(?is)</(p|div|td|tr|h[1-6]|li)>", "\n", h)
    h = re.sub(r"(?s)<[^>]+>", "", h)
    text = html.unescape(h)
    text = re.sub(r"[ \t ]+", " ", text)

    paras = []
    for line in text.splitlines():
        line = line.strip()
        if not line or (paras and paras[-1] == line):
            continue
        paras.append(line)

    # התחלה: אחרי השורה "...Pre-Market Bulletin for <date>"
    start = 0
    for i, l in enumerate(paras):
        if re.search(r"Pre-?Market Bulletin for", l, re.I):
            start = i + 1
            break
    # סוף: הראשון מבין Movers / Unsubscribe / פוטר
    end = len(paras)
    for i in range(start, len(paras)):
        if re.search(r"Pre-?Market Movers|Unsubscribe|©\s*20|Manage your|View this email|All Rights Reserved", paras[i], re.I):
            end = i
            break
    body = paras[start:end]

    # הסרת בלוק ממומן: מ-"Sponsored"/"Advertisement" עד משפט ה-disclaimer
    cleaned, skip = [], False
    for l in body:
        if re.search(r"Sponsored Message|^Advertisement$", l, re.I):
            skip = True
        if skip:
            if re.search(r"investing advice|paid advertisement", l, re.I):
                skip = False
            continue
        cleaned.append(l)

    # שורות פרסום/CTA לזריקה
    DROP = re.compile(
        r"Like what you are reading|stay connected|Check out the full family|"
        r"pre-?market stock movers here|follow (us|Barchart)|social media|"
        r"Barchart Newsletters|Sign up|Subscribe|View this|click here",
        re.I,
    )
    digest = [l for l in cleaned
              if not DROP.search(l)
              and (len(l) >= 45 or re.match(r"^(Economic Data|Asian|European|In the bond|Today’s|Today's)", l))]
    return digest


def build_payload(subject, date_dt, html_body):
    digest = extract_digest(html_body)
    if not digest:
        return None
    ist = timezone(timedelta(hours=3))
    return {
        "title": subject,
        "dateLabel": date_dt.strftime("%d/%m/%Y") if date_dt else "",
        "time": date_dt.astimezone(ist).strftime("%H:%M") if date_dt else "",
        "source": "Barchart · Pre-Market Bulletin",
        "lang": "en",
        "paragraphs": digest,
    }


def write_if_changed(payload):
    existing = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}
    same = {k: v for k, v in existing.items() if k != "_meta"}
    if same == payload:
        print("[nochange] אין בולטין חדש — morning.json נשאר כפי שהוא.")
        return
    payload = dict(payload)
    payload["_meta"] = {"updatedAt": israel_stamp(), "source": "barchart"}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT} ({len(payload['paragraphs'])} פסקאות)")


def run_offline(path):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    # קובץ ה-MCP השמור נותן תאריך ISO; IMAP נותן RFC822
    try:
        date_dt = datetime.fromisoformat(d["date"].replace("Z", "+00:00"))
    except ValueError:
        date_dt = email.utils.parsedate_to_datetime(d["date"])
    payload = build_payload(d["subject"], date_dt, d["htmlBody"])
    if not payload:
        print("[fail] לא חולץ תקציר.")
        return 1
    write_if_changed(payload)
    return 0


def run_imap():
    user, pw = os.environ.get("GMAIL_USER"), os.environ.get("GMAIL_APP_PASSWORD")
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
        typ, data = imap.search(None, "FROM", SENDER, "SINCE", imap_since())
        ids = data[0].split() if typ == "OK" and data and data[0] else []
        for mid in reversed(ids):  # מהחדש לישן
            typ, md = imap.fetch(mid, "(RFC822)")
            if typ != "OK" or not md or not md[0]:
                continue
            msg = email.message_from_bytes(md[0][1])
            body = html_of(msg)
            if BULLETIN_MARK not in body:
                continue
            subject = str(email.header.make_header(email.header.decode_header(msg.get("Subject") or "")))
            date_dt = email.utils.parsedate_to_datetime(msg.get("Date"))
            payload = build_payload(subject, date_dt, body)
            if payload:
                write_if_changed(payload)
                print(f"[ok] {subject}")
            return 0
        print("[warn] לא נמצא Pre-Market Bulletin.")
        return 0 if os.path.exists(OUT) else 1
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
