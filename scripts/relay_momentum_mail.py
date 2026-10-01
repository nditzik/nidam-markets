#!/usr/bin/env python3
"""
relay_momentum_mail.py — חמשת סורקי המומנטום מהמייל → ריפו stocks-momentum, בלי המחשב של איציק (30.9.2026).

אח של relay_barchart_mail.py (האופציות). בוט גרוק מוריד אחרי סגירת וול סטריט את חמשת הסורקים
מ-Barchart ושולח מייל אחד לעצמו בנושא שמתחיל ב-"momentum" (למשל "momentum – 01.10.2026").
הצעד הזה (update.yml, כל 15 דק') מזהה כל צרופה לפי מילים בשם, נותן לה את השם הקנוני שהדשבורד
והאתר מחפשים, ודוחף ל-nditzik/stocks-momentum/data. משם fetch_momentum.py באתר ו-autoLoadFromData
בדשבורד לוקחים את התאריך החדש ביותר לכל סורק — לכן רק מוסיפים קבצים, לא מוחקים ישנים.

כללים:
  • התאריך = יום המסחר האחרון שנסגר ברגע ההורדה, לפי שורת "Downloaded from Barchart.com as of
    MM-DD-YYYY hh:mmam CDT" שבתחתית הקובץ (נפילה: שעת שליחת המייל). כך בדיוק איציק קורא לקבצים
    שהוא מוריד בבוקר (הורדה ב-30.9 01:20 CDT → 09-29-2026).
  • הורדה בזמן המסחר (9:30–16:15 ניו יורק) = יום חלקי → כל המייל מדולג.
  • חייבים את כל חמשת הסורקים מאותו תאריך; אחרת לא דוחפים כלום (האתר ממזג את חמשתם, וסט חלקי
    היה מערבב ימים). הדחיפה הידנית נשארת כגיבוי.
  • שפיות לסקוויז: הלשונית הנכונה (Triggered) מחזירה ~900–1,300 שורות; אם הקובץ קטן מ-40% מהקובץ
    האחרון בריפו — כנראה לשונית אחרת (On / Long Squeeze, 30.9) → המייל מדולג ונרשם.
  • לא דורסים קובץ קיים (הדחיפה הידנית קודמת); כל מייל מטופל פעם אחת (data/_momentum_relay_state.json).
  • בלי GMAIL_APP_PASSWORD או מפתח — יציאה שקטה. כשל לא מפיל את ה-Action.

Secrets: GMAIL_USER, GMAIL_APP_PASSWORD (קיימים); MOMENTUM_PAT או INDEXES_STATUS_PAT — Fine-grained,
Contents read/write, וחייב לכלול את הריפו nditzik/stocks-momentum.
בדיקה: --dry-run (בלי דחיפה), או main(messages=[...], repo_dir=..., dry_run=True) מהבדיקות.
"""
import email
import email.header
import email.utils
import imaplib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iltime import NY  # noqa: E402
from relay_barchart_mail import CLOSE_MIN, git, last_closed_day, rows_of  # noqa: E402
import imap_util  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "_momentum_relay_state.json")
SENDER = "nditzik@gmail.com"
REPO = "nditzik/stocks-momentum"
KEEP_IDS = 200
SQUEEZE_MIN_RATIO = 0.4

# מפתח → קידומת השם הקנוני (זהה ל-SCANNERS ב-fetch_momentum.py ול-fileConfigs בדשבורד)
PREFIX = {
    "strength": "stocks-screener-strength-and-direction",
    "hot_prospects": "stocks-screener-hot-prospects",
    "6m_high": "stocks-screener-nearing-6-month-highs",
    "ttm_squeeze": "ttm-squeeze-triggered",
    "macd_buy": "emacd-new-buy-signals-stocks",
}
HE = {"strength": "Strength & Direction", "hot_prospects": "Hot Prospects", "6m_high": "6 Month Highs",
      "ttm_squeeze": "TTM Squeeze", "macd_buy": "eMACD"}
AS_OF_RE = re.compile(r"as of\s+(\d{2})-(\d{2})-(\d{4})\s+(\d{1,2}):(\d{2})\s*([ap]m)\s+(C[DS]T|E[DS]T)", re.I)
TZ = {"CDT": "America/Chicago", "CST": "America/Chicago", "EDT": "America/New_York", "EST": "America/New_York"}


def classify(name):
    """שם הצרופה → מפתח הסורק. גם השמות של הבוט (emac_buy_signal_…) וגם השמות של Barchart."""
    c = re.sub(r"[^a-z0-9]", "", name.lower())
    if "squeeze" in c or "ttm" in c:
        return "ttm_squeeze"
    if "macd" in c or "emac" in c:
        return "macd_buy"
    if "hotprospect" in c:
        return "hot_prospects"
    if "6month" in c or "sixmonth" in c or "6mhigh" in c:
        return "6m_high"
    if "strength" in c:
        return "strength"
    return None


def downloaded_at(data):
    """שורת התחתית של Barchart → רגע ההורדה (UTC), או None."""
    tail = data[-400:].decode("utf-8", errors="replace")
    m = AS_OF_RE.search(tail)
    if not m:
        return None
    mo, dd, yy, hh, mi, ap, tz = m.groups()
    h = int(hh) % 12 + (12 if ap.lower() == "pm" else 0)
    local = datetime(int(yy), int(mo), int(dd), h, int(mi), tzinfo=ZoneInfo(TZ[tz.upper()]))
    return local.astimezone(timezone.utc)


def in_session(t_utc):
    ny = t_utc.astimezone(NY)
    return ny.weekday() < 5 and 9 * 60 + 30 <= ny.hour * 60 + ny.minute < CLOSE_MIN


def extract(msg):
    """מייל → (קבצים תקינים, דילוגים, זמן שליחה). קובץ = {kind, src, name, date, data, rows}."""
    sent = email.utils.parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else datetime.now(timezone.utc)
    if sent.tzinfo is None:
        sent = sent.replace(tzinfo=timezone.utc)
    files, skipped = [], []
    for part in msg.walk():
        fn = part.get_filename()
        if not fn or part.get_content_maintype() == "multipart":
            continue
        if not fn.lower().endswith(".csv"):
            skipped.append("%s: לא CSV" % fn)
            continue
        kind = classify(fn)
        if not kind:
            skipped.append("%s: סורק לא מזוהה" % fn)
            continue
        data = part.get_payload(decode=True) or b""
        rows = [r for r in rows_of(data) if not str(r.get("Symbol", "")).startswith("Downloaded")]
        if not rows or "Symbol" not in rows[0] or "Wtd Alpha" not in rows[0]:
            skipped.append("%s: חסרות עמודות (Symbol / Wtd Alpha)" % fn)
            continue
        at = downloaded_at(data) or sent
        if in_session(at):
            skipped.append("%s: הורד בזמן המסחר (יום חלקי)" % fn)
            continue
        d = last_closed_day(at)
        files.append({"kind": kind, "src": fn, "name": "%s-%s.csv" % (PREFIX[kind], d.strftime("%m-%d-%Y")),
                      "date": d.isoformat(), "data": data, "rows": len(rows)})
    return files, skipped, sent


def latest_rows(repo_dir, kind):
    """מספר השורות בקובץ האחרון של הסורק בריפו (לבדיקת השפיות), או None."""
    ddir = os.path.join(repo_dir, "data")
    pat = re.compile(re.escape(PREFIX[kind]) + r"-(\d{2})-(\d{2})-(\d{4})\.csv$")
    best = None
    for n in os.listdir(ddir) if os.path.isdir(ddir) else []:
        m = pat.match(n)
        if m:
            k = (m.group(3), m.group(1), m.group(2))
            if best is None or k > best[0]:
                best = (k, n)
    if not best:
        return None
    with open(os.path.join(ddir, best[1]), "rb") as f:
        return len([r for r in rows_of(f.read()) if not str(r.get("Symbol", "")).startswith("Downloaded")])


def validate(files, repo_dir):
    """מחזיר (קבצים לדחיפה, סיבת-דחייה או None). כל חמשת הסורקים, תאריך אחד, סקוויז בגודל סביר."""
    by = {}
    for f in files:
        by.setdefault(f["kind"], f)
    missing = [HE[k] for k in PREFIX if k not in by]
    if missing:
        return [], "חסרים סורקים: " + ", ".join(missing)
    dates = {f["date"] for f in by.values()}
    if len(dates) > 1:
        return [], "תאריכים שונים בין הקבצים: " + ", ".join(sorted(dates))
    prev = latest_rows(repo_dir, "ttm_squeeze")
    sq = by["ttm_squeeze"]["rows"]
    if prev and sq < prev * SQUEEZE_MIN_RATIO:
        return [], "TTM Squeeze קטן מדי (%d שורות מול %d בקובץ האחרון) — כנראה לשונית לא נכונה, צריך Triggered" % (sq, prev)
    return [by[k] for k in PREFIX], None


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


def subject_of(m):
    return str(email.header.make_header(email.header.decode_header(m.get("Subject") or "")))


def is_ours(m):
    """"momentum…" מאיציק לעצמו. לא "⚡ Momentum Scanner" (Brevo) — שולח אחר."""
    frm = (m.get("From") or "").lower()
    return SENDER in frm and subject_of(m).strip().lower().startswith("momentum")


def fetch_messages(days=3, skip=()):
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not pw:
        print("relay_momentum: אין GMAIL_APP_PASSWORD — דילוג")
        return None
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(os.environ.get("GMAIL_USER") or SENDER, pw)
    imap.select('"[Gmail]/All Mail"', readonly=True)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
    typ, data = imap.search(None, "SUBJECT", "momentum", "FROM", SENDER, "SINCE", since)
    out = []
    # כותרות קודם: מייל שכבר טופל לא יורד שוב (כל מייל ~300KB, כמה ביום)
    skip = set(skip)
    for h in imap_util.headers(imap, data[0].split() if typ == "OK" and data and data[0] else []):
        if h["message_id"] in skip or not h["subject"].strip().lower().startswith("momentum"):
            continue
        m = imap_util.full(imap, h["id"])
        if m is not None:
            out.append(m)
    imap.logout()
    return out


def clone_repo(pat, dest):
    url = "https://x-access-token:%s@github.com/%s.git" % (pat, REPO)
    r = subprocess.run(["git", "clone", "-q", "--depth", "1", url, dest], capture_output=True, text=True)
    if r.returncode != 0:
        # לא להדפיס את ה-URL (מכיל את המפתח)
        raise RuntimeError("clone נכשל — המפתח כנראה לא כולל את %s" % REPO)
    return dest


def push_files(repo_dir, files, label, dry_run=False):
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
    git(["commit", "-q", "-m", "data: סורקי מומנטום מהמייל (%s)" % label], repo_dir)
    for _ in range(5):
        r = git(["push", "-q"], repo_dir, check=False)
        if r.returncode == 0:
            return written, existing
        git(["pull", "--rebase", "-q"], repo_dir, check=False)
    raise RuntimeError("push נכשל אחרי 5 ניסיונות")


def main(messages=None, repo_dir=None, now=None, dry_run=False):
    st = load_state()
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
        print("relay_momentum: אין מיילים חדשים")
        return 0
    if repo_dir is None:
        pat = os.environ.get("MOMENTUM_PAT") or os.environ.get("INDEXES_STATUS_PAT")
        if not pat:
            print("relay_momentum: %d מיילים חדשים אבל אין מפתח — ממתין" % len(todo))
            return 0
        try:
            repo_dir = clone_repo(pat, tempfile.mkdtemp(prefix="stmom-"))
        except Exception as e:  # noqa: BLE001
            # לא מסמנים כ-done — ינסה שוב בריצה הבאה, אחרי שהמפתח יורחב
            print("relay_momentum: %s" % e, file=sys.stderr)
            st["log"].append({"at": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"), "ok": False, "error": str(e)})
            if not dry_run:
                save_state(st)
            return 0
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for mid, subj, m in todo:
        files, skipped, sent = extract(m)
        good, reason = validate(files, repo_dir)
        entry = {"at": stamp, "subject": subj, "sent": sent.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "files": {f["kind"]: f["rows"] for f in files}, "skipped": skipped, "rejected": reason, "written": [], "existing": []}
        try:
            if good:
                entry["written"], entry["existing"] = push_files(repo_dir, good, good[0]["date"], dry_run=dry_run)
            entry["ok"] = True
        except Exception as e:  # noqa: BLE001
            entry["ok"] = False
            entry["error"] = str(e)[-300:]
            print("relay_momentum: %s נכשל: %s" % (subj, e), file=sys.stderr)
        if entry["ok"]:
            st["done"].append(mid)
        st["log"].append(entry)
        print("relay_momentum: %s → נכתבו %s · קיימים %s · נדחה: %s · דולגו %s" % (subj, entry["written"], entry["existing"], reason, skipped))
    if not dry_run:
        save_state(st)
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
