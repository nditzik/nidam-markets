#!/usr/bin/env python3
"""
relay_barchart_mail.py — קובצי Barchart מהמייל → ריפו הדשבורד (indexes-status), בלי המחשב של איציק (29.9.2026).

הזרימה: בוט (גרוק) מוריד ב-05:00 שעון ישראל את קובצי ה-CSV מ-Barchart ושולח מייל אחד עם
צרופות בנושא "Options Flow SPY + SPX – DD.MM.YYYY" (מ-nditzik@gmail.com לעצמו). הצעד הזה
רץ ב-update.yml (כל 15 דק'), מוצא מיילים חדשים בנושא הזה, שומר את הצרופות בשמות הקנוניים
של הדשבורד (כמו scripts/normalize_incoming.py שם) ודוחף ל-indexes-status עם PAT ייעודי.
ה-Action של הדשבורד (push על data/*.csv) מעבד משם כרגיל.

כללים:
  • תאריך המסחר מהתוכן, לא משם הקובץ (Barchart/הבוט שמים את תאריך ההורדה): קובצי flow —
    Exp Date − DTE (רוב); UOA — עמודת Time; watchlist — יום המסחר האחרון שנסגר לפני שליחת המייל.
  • מייל שנשלח לפני סגירת המסחר של אותו יום (יום חלקי, כמו הרצות הניסיון) — מדולג ומסומן.
  • לא דורסים קובץ קיים בריפו (הדחיפה הידנית של איציק קודמת); קובץ זהה = דילוג שקט.
  • כל מייל מטופל פעם אחת (Message-ID ב-data/_barchart_relay_state.json).
  • בלי GMAIL_APP_PASSWORD / INDEXES_STATUS_PAT — יציאה שקטה. כשל = לא מפיל את ה-Action.

Secrets: GMAIL_USER, GMAIL_APP_PASSWORD (קיימים), INDEXES_STATUS_PAT (Fine-grained, Contents
read/write לריפו nditzik/indexes-status בלבד).
בדיקה: --dry-run (בלי דחיפה), או main(messages=[...], repo_dir=..., now=...) מהבדיקות.
"""
import csv
import email
import email.utils
import imaplib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iltime import NY  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "_barchart_relay_state.json")
SUBJECT_MARKS = ("options flow spy + spx", "watchlist s&p 500")   # המייל הרגיל + מייל נפרד של ה-watchlist (29.9)
SENDER = "nditzik@gmail.com"
REPO = "nditzik/indexes-status"
CLOSE_MIN = 16 * 60 + 15      # 16:15 ניו יורק — אחרי זה יום המסחר נחשב סגור
KEEP_IDS = 200


def classify(name):
    """אותם כללים כמו normalize_incoming.classify בריפו הדשבורד."""
    c = re.sub(r"[^a-z0-9]", "", name.lower())
    if "unusual" in c or "uoa" in c:
        return "uoa"
    if "watchlist" in c and "500" in c and ("sp" in c or "sandp" in c):
        return "watchlist"
    if "spx" in c and "option" in c and "flow" in c:
        return "flow"
    if "spy" in c and "option" in c and "flow" in c:
        return "spyflow"
    if "option" in c and "flow" in c:
        return "allflow"
    return None


CANON = {"watchlist": "watchlist-sp-500-intraday-{d}.csv", "flow": "spx-options-flow-{d}.csv", "spyflow": "spy-options-flow-{d}.csv",
         "allflow": "options-flow-{d}.csv", "uoa": "uoa-stocks-{d}.csv"}
HE = {"watchlist": "רשימת S&P 500", "flow": "אופציות SPX", "spyflow": "אופציות SPY", "allflow": "Options Flow כל השוק", "uoa": "אופציות חריגות"}


def rows_of(data):
    text = data.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


def flow_trade_date(rows):
    votes = Counter()
    for r in rows:
        try:
            votes[datetime.strptime(r["Exp Date"], "%Y-%m-%d").date() - timedelta(days=int(float(r["DTE"])))] += 1
        except (KeyError, ValueError, TypeError):
            continue
    return votes.most_common(1)[0][0] if votes else None


def uoa_trade_date(rows):
    votes = Counter()
    for r in rows:
        t = (r.get("Time") or "")[:10]
        try:
            votes[datetime.strptime(t, "%Y-%m-%d").date()] += 1
        except ValueError:
            continue
    return votes.most_common(1)[0][0] if votes else None


def last_closed_day(sent_utc):
    """יום המסחר האחרון שכבר נסגר ברגע שליחת המייל (שעון ניו יורק). חגים לא מטופלים."""
    ny = sent_utc.astimezone(NY)
    d = ny.date()
    if ny.weekday() >= 5 or ny.hour * 60 + ny.minute < CLOSE_MIN:
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def uoa_is_spx_only(rows):
    syms = {(r.get("Symbol") or "").strip() for r in rows}
    syms.discard("")
    return len(syms) <= 5


def extract(msg):
    """מייל → רשימת {kind, name, date, data, note} + רשימת דילוגים."""
    sent = email.utils.parsedate_to_datetime(msg.get("Date") or "") if msg.get("Date") else datetime.now(timezone.utc)
    if sent.tzinfo is None:
        sent = sent.replace(tzinfo=timezone.utc)
    closed = last_closed_day(sent)
    ny = sent.astimezone(NY)
    in_session = ny.weekday() < 5 and 9 * 60 + 30 <= ny.hour * 60 + ny.minute < CLOSE_MIN
    files, skipped = [], []
    for part in msg.walk():
        fn = part.get_filename()
        if not fn or part.get_content_maintype() == "multipart":
            continue
        if not fn.lower().endswith(".csv"):
            skipped.append("%s: לא CSV" % fn)
            continue
        data = part.get_payload(decode=True) or b""
        kind = classify(fn)
        if not kind:
            skipped.append("%s: סוג לא מזוהה" % fn)
            continue
        rows = rows_of(data)
        if len(rows) < 5:
            skipped.append("%s: קובץ ריק/קצר" % fn)
            continue
        if kind == "uoa" and uoa_is_spx_only(rows):
            skipped.append("%s: UOA של SPX בלבד (לא הקובץ הרחב)" % fn)
            continue
        td = flow_trade_date(rows) if kind in ("flow", "spyflow", "allflow") else uoa_trade_date(rows) if kind == "uoa" else None
        if td is None:
            if in_session:
                # קובץ בלי תאריך בתוכן (watchlist) שנשלח בזמן המסחר = תמונת ביניים של היום — לא נר סגור
                skipped.append("%s: נשלח בזמן המסחר (יום חלקי)" % fn)
                continue
            td = closed
        if td > closed:
            # הקובץ מכיל עסקאות של יום שעוד לא נסגר בזמן השליחה — יום חלקי
            skipped.append("%s: יום חלקי (עסקאות %s, המסחר טרם נסגר בזמן השליחה)" % (fn, td.isoformat()))
            continue
        files.append({"kind": kind, "src": fn, "name": CANON[kind].format(d=td.strftime("%m-%d-%Y")), "date": td.isoformat(), "data": data, "rows": len(rows)})
    return files, skipped, sent


def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"done": [], "log": []}


def save_state(st):
    st["done"] = st["done"][-KEEP_IDS:]
    st["log"] = st["log"][-40:]
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def fetch_messages(days=3):
    user = os.environ.get("GMAIL_USER") or SENDER
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not pw:
        print("relay_barchart: אין GMAIL_APP_PASSWORD — דילוג")
        return None
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user, pw)
    imap.select('"[Gmail]/All Mail"', readonly=True)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
    # "S&P" בחיפוש IMAP לא נמצא (29.9) — מחפשים מילה אחת ומסננים לפי הנושא המלא בפייתון
    typ, data = imap.search(None, "OR", "SUBJECT", "Options", "SUBJECT", "Watchlist", "SINCE", since)
    out = []
    for mid in (data[0].split() if typ == "OK" and data and data[0] else []):
        typ, md = imap.fetch(mid, "(RFC822)")
        if typ == "OK" and md and md[0]:
            out.append(email.message_from_bytes(md[0][1]))
    imap.logout()
    return out


def git(args, cwd, check=True):
    return subprocess.run(["git"] + args, cwd=cwd, check=check, capture_output=True, text=True)


def clone_repo(pat, dest):
    url = "https://x-access-token:%s@github.com/%s.git" % (pat, REPO)
    subprocess.run(["git", "clone", "-q", "--depth", "1", url, dest], check=True, capture_output=True, text=True)
    return dest


def push_files(repo_dir, files, label, dry_run=False):
    """שומר קבצים חדשים ב-data/ של הדשבורד ודוחף. מחזיר (נכתבו, דולגו-קיימים)."""
    written, existing = [], []
    for f in files:
        path = os.path.join(repo_dir, "data", f["name"])
        if os.path.exists(path):
            existing.append(f["name"])
            continue
        with open(path, "wb") as fh:
            fh.write(f["data"])
        written.append(f["name"])
    if not written or dry_run:
        return written, existing
    git(["config", "user.name", "nidam-markets-bot"], repo_dir)
    git(["config", "user.email", "actions@github.com"], repo_dir)
    git(["add"] + ["data/" + n for n in written], repo_dir)
    git(["commit", "-q", "-m", "data: קובצי Barchart מהמייל (%s): %s" % (label, ", ".join(written))], repo_dir)
    for i in range(5):
        r = git(["push", "-q"], repo_dir, check=False)
        if r.returncode == 0:
            return written, existing
        git(["pull", "--rebase", "-q"], repo_dir, check=False)
    raise RuntimeError("push failed: " + (r.stderr or "")[-300:])


def main(messages=None, repo_dir=None, now=None, dry_run=False):
    st = load_state()
    msgs = messages if messages is not None else fetch_messages()
    if msgs is None:
        return 0
    todo = []
    for m in msgs:
        subj = str(email.header.make_header(email.header.decode_header(m.get("Subject") or "")))
        mid = (m.get("Message-ID") or subj + (m.get("Date") or "")).strip()
        if not any(k in subj.lower() for k in SUBJECT_MARKS) or mid in st["done"]:
            continue
        todo.append((mid, subj, m))
    if not todo:
        print("relay_barchart: אין מיילים חדשים")
        return 0
    pat = os.environ.get("INDEXES_STATUS_PAT")
    if repo_dir is None:
        if not pat:
            print("relay_barchart: יש %d מיילים חדשים אבל אין INDEXES_STATUS_PAT — ממתין" % len(todo))
            return 0
        repo_dir = clone_repo(pat, tempfile.mkdtemp(prefix="idxst-"))
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for mid, subj, m in todo:
        files, skipped, sent = extract(m)
        entry = {"at": stamp, "subject": subj, "sent": sent.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "skipped": skipped, "written": [], "existing": []}
        try:
            written, existing = push_files(repo_dir, files, subj.split("–")[-1].strip() if "–" in subj else subj, dry_run=dry_run)
            entry["written"], entry["existing"] = written, existing
            entry["ok"] = True
        except Exception as e:  # noqa: BLE001
            entry["ok"] = False
            entry["error"] = str(e)[-300:]
            print("relay_barchart: %s נכשל: %s" % (subj, e), file=sys.stderr)
        if entry.get("ok"):
            st["done"].append(mid)
        st["log"].append(entry)
        print("relay_barchart: %s → נכתבו %s · קיימים %s · דולגו %s" % (subj, entry["written"], entry["existing"], skipped))
    if not dry_run:
        save_state(st)
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
