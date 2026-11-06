#!/usr/bin/env python3
"""
relay_history_mail.py — היסטוריה ארוכה מ-Barchart מהמייל → data/history/barchart/ (6.11.2026).

לפיצ'ר "ימים חריגים — מה קרה בעבר" (איציק). גרוק מוריד פעם אחת (או לפי בקשה) היסטוריה יומית
מ-Barchart ושולח מייל לעצמו, נושא שמתחיל ב-"History" (הראשון: "History – Breadth 2000"), עם
צרופות hist_<SYM>.csv באותו פורמט כמו קובצי הרוטציה: Time,Open,High,Low,Latest,Change,%Change,Volume.
  $S5TH/$S5FI/$S5TW — אחוז מניות ה-S&P 500 מעל ממוצע 200/50/20 (מ-2007; אין לפני כן ב-Barchart)
  $SPX, $VIX — מ-2000.

כללים:
  • כל צרופה hist_*.csv נבדקת: כותרת עם Time ו-Latest, לפחות 250 שורות נתונים, תאריכים YYYY-MM-DD.
    שורת "Downloaded from Barchart" בסוף נשמטת. השורות נשמרות ממוינות מהישן לחדש, בלי כפילויות.
  • נשמר ל-data/history/barchart/<שם>. קובץ קיים מוחלף רק כשהחדש מגיע לתאריך מאוחר יותר או ארוך יותר
    (מייל מתוקן/מעודכן גובר; מייל ישן לא דורס).
  • כל מייל מטופל פעם אחת (data/_history_relay_state.json). בלי GMAIL_APP_PASSWORD — יציאה שקטה.

Secrets: GMAIL_USER, GMAIL_APP_PASSWORD. בדיקה: --dry-run, או main(messages=[...], root=...).
"""
import csv
import email
import email.header
import imaplib
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imap_util  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENDER = "nditzik@gmail.com"
SUBJ_RE = re.compile(r"^\s*history\b", re.I)
NAME_RE = re.compile(r"hist_[A-Za-z0-9]+\.csv")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MIN_ROWS = 250
KEEP_IDS = 100


def state_path(root):
    return os.path.join(root, "data", "_history_relay_state.json")


def load_state(root):
    try:
        with open(state_path(root), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"done": [], "log": []}


def save_state(root, st):
    st["done"] = st["done"][-KEEP_IDS:]
    st["log"] = st["log"][-40:]
    p = state_path(root)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def subject_of(m):
    return str(email.header.make_header(email.header.decode_header(m.get("Subject") or "")))


def is_ours(m):
    return SENDER in (m.get("From") or "").lower() and SUBJ_RE.match(subject_of(m)) is not None


def clean_csv(data):
    """bytes → (טקסט CSV נקי, מספר שורות, תאריך ראשון, אחרון) או (None, סיבה)."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, "קידוד"
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return None, "ריק"
    head = [h.strip() for h in rows[0]]
    if "Time" not in head or "Latest" not in head:
        return None, "כותרת לא צפויה: %s" % ",".join(head[:8])
    ti = head.index("Time")
    by = {}
    for r in rows[1:]:
        if len(r) < len(head):
            continue
        d = r[ti].strip()
        if not DATE_RE.match(d):
            continue
        by[d] = r
    if len(by) < MIN_ROWS:
        return None, "רק %d שורות" % len(by)
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(head)
    for d in sorted(by):
        w.writerow(by[d])
    days = sorted(by)
    return (out.getvalue(), len(by), days[0], days[-1]), None


def existing_span(path):
    try:
        with open(path, encoding="utf-8") as f:
            rows = list(csv.reader(f))
        ds = [r[0] for r in rows[1:] if r and DATE_RE.match(r[0])]
        return (len(ds), ds[-1]) if ds else (0, "")
    except OSError:
        return None


def extract(msg):
    files, skipped = {}, []
    for part in msg.walk():
        fn = part.get_filename()
        if not fn or part.get_content_maintype() == "multipart":
            continue
        fn = os.path.basename(str(email.header.make_header(email.header.decode_header(fn))).strip())
        if not NAME_RE.fullmatch(fn):
            skipped.append("%s: שם לא צפוי" % fn)
            continue
        files[fn] = part.get_payload(decode=True) or b""
    return files, skipped


def fetch_messages(days=14, skip=()):
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not pw:
        print("relay_history: אין GMAIL_APP_PASSWORD — דילוג")
        return None
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(os.environ.get("GMAIL_USER") or SENDER, pw)
    imap.select('"[Gmail]/All Mail"', readonly=True)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
    typ, data = imap.search(None, "SUBJECT", "History", "FROM", SENDER, "SINCE", since)
    out, skip = [], set(skip)
    for h in imap_util.headers(imap, data[0].split() if typ == "OK" and data and data[0] else []):
        if h["message_id"] in skip or not SUBJ_RE.match(h["subject"]):
            continue
        m = imap_util.full(imap, h["id"])
        if m is not None:
            out.append(m)
    imap.logout()
    return out


def main(messages=None, root=ROOT, now=None, dry_run=False):
    st = load_state(root)
    msgs = messages if messages is not None else fetch_messages(skip=st["done"])
    if msgs is None:
        return 0
    todo = []
    for m in msgs:
        subj = subject_of(m)
        mid = (m.get("Message-ID") or subj + (m.get("Date") or "")).strip()
        if is_ours(m) and mid not in st["done"]:
            todo.append((mid, subj, m))
    if not todo:
        print("relay_history: אין מיילים חדשים")
        return 0
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    folder = os.path.join(root, "data", "history", "barchart")
    for mid, subj, m in todo:
        files, skipped = extract(m)
        entry = {"at": stamp, "subject": subj, "files": [], "skipped": skipped}
        for fn, data in sorted(files.items()):
            res, why = clean_csv(data)
            if res is None:
                entry["files"].append([fn, "rejected: " + why])
                continue
            text, n, first, last = res
            path = os.path.join(folder, fn)
            old = existing_span(path)
            if old and (old[1] > last or (old[1] == last and old[0] >= n)):
                entry["files"].append([fn, "kept existing (%d rows → %s)" % old])
                continue
            if not dry_run:
                os.makedirs(folder, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            entry["files"].append([fn, "written %d rows %s → %s" % (n, first, last)])
        st["done"].append(mid)
        st["log"].append(entry)
        print("relay_history: %s → %s" % (subj, entry["files"]))
    if not dry_run:
        save_state(root, st)
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
