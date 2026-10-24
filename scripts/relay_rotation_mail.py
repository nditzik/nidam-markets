#!/usr/bin/env python3
"""
relay_rotation_mail.py — 20 קובצי הרוטציה הסקטוריאלית מהמייל → data/rotation/<D>/ בריפו הזה (24.10.2026).

אח של relay_barchart_mail.py ו-relay_momentum_mail.py. עד 24.10 גרוק העלה את הקבצים לדרייב ורוטינת
הענן הורידה אותם דרך מחבר Google Drive כ-base64 — איטי, והתוכן נקטע פעמיים (17.10, 24.10: ריצה של
26 דקות בלי תוצאה). מאז גרוק שולח בשבת ~06:00 מייל אחד לעצמו, נושא "Rotation – DD.MM.YYYY", עם
20 הצרופות: 16 hist_<SYM>.csv (Barchart, Daily, 2 Years), breadth.csv, industry-group-rankings.csv,
heatmap.csv, manifest.txt. הצעד הזה (update.yml, כל 15 דק') שומר אותם ל-data/rotation/<D>/ — אותה
תיקייה שהרוטינה (scripts/prompts/rotation_weekly.md) והגיבוי (weekly_narrative.md §7) קוראים — וה-commit
של ה-Action בסוף הריצה דוחף אותם. הדרייב נשאר כגיבוי ידני בלבד.

כללים:
  • D מהנושא (DD.MM.YYYY). בלי תאריך בנושא — המייל מדולג ונרשם.
  • הכל או כלום: בדיוק 20 צרופות בשמות הצפויים (16 hist_*.csv + 4 הקבועים); חסר/עודף — דחייה.
  • build_rotation.py check D חייב לעבור (שורה אחרונה = שישי של אותו שבוע, אורך, סבירות). נכשל —
    הקבצים שנכתבו נמחקים, המייל נרשם כנדחה (מייל מתוקן יגיע עם Message-ID חדש).
  • תיקייה שכבר מלאה (20 קבצים) לא נדרסת — העלאה ידנית/קודמת קודמת.
  • כל מייל מטופל פעם אחת (data/_rotation_relay_state.json). בלי GMAIL_APP_PASSWORD — יציאה שקטה.

Secrets: GMAIL_USER, GMAIL_APP_PASSWORD (קיימים בצעדי ה-IMAP האחרים). אין צורך במפתח push — הריפו הזה.
בדיקה: --dry-run, או main(messages=[...], root=..., dry_run=True) מהבדיקות.
"""
import email
import email.header
import email.utils
import imaplib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imap_util  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENDER = "nditzik@gmail.com"
SUBJ_RE = re.compile(r"^\s*rotation\s*[–—-]?\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", re.I)
FIXED = ("breadth.csv", "industry-group-rankings.csv", "heatmap.csv", "manifest.txt")
HIST_N = 16
KEEP_IDS = 100


def state_path(root):
    return os.path.join(root, "data", "_rotation_relay_state.json")


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


def day_of(subj):
    """'Rotation – 24.10.2026' → '2026-10-24'; בלי תאריך — None."""
    m = SUBJ_RE.match(subj)
    if not m:
        return None
    d, mo, y = (int(x) for x in m.groups())
    try:
        return datetime(y, mo, d).strftime("%Y-%m-%d")
    except ValueError:
        return None


def is_ours(m):
    frm = (m.get("From") or "").lower()
    return SENDER in frm and SUBJ_RE.match(subject_of(m)) is not None


def extract(msg):
    """מייל → ({שם: bytes}, דילוגים). שמות הצרופות נשמרים כפי שהם (hist_CLZ26.csv וכו')."""
    files, skipped = {}, []
    for part in msg.walk():
        fn = part.get_filename()
        if not fn or part.get_content_maintype() == "multipart":
            continue
        fn = os.path.basename(str(email.header.make_header(email.header.decode_header(fn))).strip())
        ok = fn in FIXED or (fn.startswith("hist_") and fn.endswith(".csv") and re.fullmatch(r"hist_[A-Za-z0-9]+\.csv", fn))
        if not ok:
            skipped.append("%s: שם לא צפוי" % fn)
            continue
        data = part.get_payload(decode=True) or b""
        if len(data) < 50:
            skipped.append("%s: ריק" % fn)
            continue
        files[fn] = data
    return files, skipped


def validate_set(files):
    """20 בדיוק: 16 hist + 4 קבועים. מחזיר None כשתקין, אחרת סיבת דחייה."""
    hist = [n for n in files if n.startswith("hist_")]
    miss = [n for n in FIXED if n not in files]
    if miss:
        return "חסרים: " + ", ".join(miss)
    if len(hist) != HIST_N:
        return "קובצי hist: %d במקום %d" % (len(hist), HIST_N)
    return None


def run_check(root, day):
    r = subprocess.run([sys.executable, os.path.join(root, "scripts", "build_rotation.py"), "check", day],
                       cwd=root, capture_output=True, text=True, timeout=120)
    return r.returncode == 0, (r.stdout + r.stderr).strip()[-600:]


def write_files(root, day, files, dry_run=False):
    """כותב ל-data/rotation/<D>/. תיקייה שכבר מלאה — לא נוגעים ("existing")."""
    folder = os.path.join(root, "data", "rotation", day)
    have = set(os.listdir(folder)) if os.path.isdir(folder) else set()
    if all(n in have for n in files):
        return "existing", folder, False
    created = not os.path.isdir(folder)
    if dry_run:
        return "would-write", folder, created
    os.makedirs(folder, exist_ok=True)
    for n, data in files.items():
        if n in have:
            continue
        with open(os.path.join(folder, n), "wb") as f:
            f.write(data)
    return "written", folder, created


def rollback(folder, names, created):
    if created:
        shutil.rmtree(folder, ignore_errors=True)
        return
    for n in names:
        try:
            os.remove(os.path.join(folder, n))
        except OSError:
            pass


def fetch_messages(days=4, skip=()):
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not pw:
        print("relay_rotation: אין GMAIL_APP_PASSWORD — דילוג")
        return None
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(os.environ.get("GMAIL_USER") or SENDER, pw)
    imap.select('"[Gmail]/All Mail"', readonly=True)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
    typ, data = imap.search(None, "SUBJECT", "Rotation", "FROM", SENDER, "SINCE", since)
    out, skip = [], set(skip)
    # כותרות קודם (~700KB למייל): מייל שכבר טופל לא יורד שוב
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
        print("relay_rotation: אין מיילים חדשים")
        return 0
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for mid, subj, m in todo:
        day = day_of(subj)
        files, skipped = extract(m)
        reason = None if day else "אין תאריך בנושא"
        reason = reason or validate_set(files)
        entry = {"at": stamp, "subject": subj, "day": day, "n": len(files), "skipped": skipped,
                 "rejected": reason, "status": None, "check": None}
        if not reason:
            status, folder, created = write_files(root, day, files, dry_run=dry_run)
            entry["status"] = status
            if status == "written":
                ok, out = run_check(root, day)
                entry["check"] = "ok" if ok else out
                if not ok:
                    rollback(folder, files.keys(), created)
                    entry["rejected"] = "check נכשל"
                    entry["status"] = "rolled-back"
        st["done"].append(mid)
        st["log"].append(entry)
        print("relay_rotation: %s → %s · %s · נדחה: %s · דולגו %s" % (subj, day, entry["status"], entry["rejected"], skipped))
    if not dry_run:
        save_state(root, st)
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
