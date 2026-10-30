#!/usr/bin/env python3
"""
relay_insider_mail.py — רכישות פנים מהמייל של גרוק → data/insider_daily/ (30.10.2026).

בוט גרוק סורק כל בוקר ב-05:00 שעון ישראל את דיווחי Form 4 של אתמול ב-SEC ושולח מייל לעצמו:
  • "Insider Buys – DD.MM.YYYY" — צרופה insider_buys_DD.MM.YYYY.csv (קניות בשוק הפתוח, 19 עמודות:
    Ticker, Company, Buyer, Role, Filing Date, Trade Date, Shares, Price, Value, Holdings Before/After,
    Holdings Change %, Market Cap, Last Close, % From 52W High/Low, Cluster (30d), Cluster Count, Form 4 URL),
    ולפעמים גם insider_history_DD.MM.YYYY.csv — כל הקניות והמכירות של אנשי פנים באותן חברות ב-24 חודשים
    (Ticker, Insider, Role, Trade Date, Filing Date, Type P/S, Shares, Price, Value, Holdings After, 10b5-1, Form 4 URL).
  • "Insider History – …" — היסטוריה בלבד (הבדיקה הראשונה, 30.10).
התאריך בשם הקובץ = יום הדיווח (Filing Date). הצעד הזה (update.yml, כל 15 דק') שומר:
  data/insider_daily/<יום הדיווח>/buys.csv (+ history.csv) + meta.json, והיסטוריה בלבד ל-
  data/insider_daily/history/<יום השליחה>-<n>.csv. build_insider_daily.py בונה מהם את הפאנל.
כללים: קובץ קיים לא נדרס; כל מייל פעם אחת (data/_insider_relay_state.json); בלי GMAIL_APP_PASSWORD — יציאה שקטה.
בדיקה: --dry-run, או main(messages=[...], root=..., dry_run=True).
"""
import email
import email.header
import email.utils
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imap_util  # noqa: E402
from relay_barchart_mail import rows_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENDER = "nditzik@gmail.com"
SUBJ_RE = re.compile(r"^\s*insider\s+(buys|history)\b", re.I)
DATE_RE = re.compile(r"(\d{1,2})[._-](\d{1,2})[._-](\d{4})")
BUYS_COLS = ("Ticker", "Buyer", "Trade Date", "Price", "Value")
HIST_COLS = ("Ticker", "Insider", "Trade Date", "Type", "Price")
KEEP_IDS = 100


def state_path(root):
    return os.path.join(root, "data", "_insider_relay_state.json")


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
    frm = (m.get("From") or "").lower()
    return SENDER in frm and SUBJ_RE.match(subject_of(m)) is not None


def day_of(text):
    """'insider_buys_29.10.2026.csv' / 'Insider Buys – 29.10.2026' → '2026-10-29', או None."""
    m = DATE_RE.search(text or "")
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return datetime(y, mo, d).strftime("%Y-%m-%d")
    except ValueError:
        return None


def extract(msg):
    """מייל → (קבצים, דילוגים). קובץ = {kind: buys|history, src, day, data, rows}."""
    subj = subject_of(msg)
    files, skipped = [], []
    for part in msg.walk():
        fn = part.get_filename()
        if not fn or part.get_content_maintype() == "multipart":
            continue
        fn = os.path.basename(str(email.header.make_header(email.header.decode_header(fn))).strip())
        low = fn.lower()
        if not low.endswith(".csv"):
            skipped.append("%s: לא CSV" % fn)
            continue
        kind = "history" if "history" in low else ("buys" if "buy" in low or "backfill" in low else None)
        if not kind:
            skipped.append("%s: קובץ לא מזוהה" % fn)
            continue
        data = part.get_payload(decode=True) or b""
        rows = rows_of(data)
        need = HIST_COLS if kind == "history" else BUYS_COLS
        if rows and any(c not in rows[0] for c in need):
            skipped.append("%s: חסרות עמודות %s" % (fn, [c for c in need if c not in rows[0]]))
            continue
        files.append({"kind": kind, "src": fn, "day": day_of(fn) or day_of(subj), "data": data, "rows": len(rows)})
    return files, skipped


def write_files(root, files, subj, sent, dry_run=False):
    """כותב את הקבצים; מחזיר רשימת (path, status)."""
    base = os.path.join(root, "data", "insider_daily")
    out = []
    buys = [f for f in files if f["kind"] == "buys" and f["day"]]
    day = buys[0]["day"] if buys else None
    for f in files:
        if f["kind"] == "buys":
            if not f["day"]:
                out.append((f["src"], "no-date"))
                continue
            path = os.path.join(base, f["day"], "buys.csv")
        elif day:
            path = os.path.join(base, day, "history.csv")
        else:
            hdir = os.path.join(base, "history")
            n = 1
            while True:
                path = os.path.join(hdir, "%s-%d.csv" % (sent.strftime("%Y-%m-%d"), n))
                if not os.path.exists(path):
                    break
                n += 1
        rel = os.path.relpath(path, root)
        if os.path.exists(path):
            out.append((rel, "existing"))
            continue
        if dry_run:
            out.append((rel, "would-write"))
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(f["data"])
        out.append((rel, "written"))
    if day and not dry_run:
        meta_p = os.path.join(base, day, "meta.json")
        if not os.path.exists(meta_p):
            meta = {"filingDay": day, "subject": subj, "sentAt": sent.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "files": {f["kind"]: {"src": f["src"], "rows": f["rows"]} for f in files},
                    "relayedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            with open(meta_p, "w", encoding="utf-8") as fh:
                json.dump(meta, fh, ensure_ascii=False, indent=1)
    return out


def fetch_messages(days=10, skip=()):
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not pw:
        print("relay_insider: אין GMAIL_APP_PASSWORD — דילוג")
        return None
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(os.environ.get("GMAIL_USER") or SENDER, pw)
    imap.select('"[Gmail]/All Mail"', readonly=True)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
    typ, data = imap.search(None, "FROM", SENDER, "SINCE", since)
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
        print("relay_insider: אין מיילים חדשים")
        return 0
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # מהישן לחדש, כדי שמספור קובצי ההיסטוריה יישאר יציב
    todo.sort(key=lambda t: email.utils.parsedate_to_datetime(t[2].get("Date")) if t[2].get("Date") else datetime.min.replace(tzinfo=timezone.utc))
    for mid, subj, m in todo:
        sent = email.utils.parsedate_to_datetime(m.get("Date")) if m.get("Date") else datetime.now(timezone.utc)
        if sent.tzinfo is None:
            sent = sent.replace(tzinfo=timezone.utc)
        files, skipped = extract(m)
        res = write_files(root, files, subj, sent, dry_run=dry_run) if files else []
        st["done"].append(mid)
        st["log"].append({"at": stamp, "subject": subj, "files": res, "skipped": skipped})
        print("relay_insider: %s → %s · דולגו %s" % (subj, res, skipped))
    if not dry_run:
        save_state(root, st)
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
