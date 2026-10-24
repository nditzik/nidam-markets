#!/usr/bin/env python3
"""
relay_fourpillars_mail.py — שלושת סורקי "ארבעת העמודים" מהמייל → data/fourpillars/<יום המסחר>/ (24.10.2026).

אח של relay_momentum_mail.py ו-relay_rotation_mail.py. בוט גרוק מוריד אחרי סגירת וול סטריט (שלישי–שבת
06:00 שעון ישראל) את שלושת הסקרינרים של Barchart בתצוגת Four Pillars — High Momentum ("4 technical
pillars"), Phoenix Rising, Breakout Candidates — ושולח מייל אחד לעצמו, נושא "Screeners – DD.MM.YYYY"
(התאריך בנושא = יום השליחה; יום המסחר נקבע מתוך הקובץ). הצעד הזה (update.yml, כל 15 דק') שומר את
שלושת הקבצים ל-data/fourpillars/<יום המסחר>/{momentum,phoenix,breakout}.csv + meta.json;
build_fourpillars.py בונה מהם את דוח "הצעות לטרייד" (data/trades/trades-<יום>.html).

כללים:
  • יום המסחר = יום המסחר האחרון שנסגר ברגע ההורדה, משורת "Downloaded from Barchart.com as of
    MM-DD-YYYY hh:mmam CDT" בתחתית הקובץ (נפילה: שעת השליחה). הורדה בזמן המסחר = יום חלקי → דילוג.
  • הכל או כלום: שלושת הסורקים, מאותו יום מסחר, עם העמודות Symbol / Wtd Alpha / Opinion / Trend.
  • תיקייה מלאה לא נדרסת; כל מייל פעם אחת (data/_fourpillars_relay_state.json). בלי GMAIL_APP_PASSWORD — יציאה שקטה.
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
from relay_barchart_mail import last_closed_day, rows_of  # noqa: E402
from relay_momentum_mail import downloaded_at, in_session  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENDER = "nditzik@gmail.com"
SUBJ_RE = re.compile(r"^\s*(screeners?|four\s*pillars|4\s*pillars)\b", re.I)
KINDS = ("momentum", "phoenix", "breakout")
HE = {"momentum": "High Momentum", "phoenix": "Phoenix Rising", "breakout": "Breakout Candidates"}
NEED_COLS = ("Symbol", "Wtd Alpha", "Opinion", "Trend")
KEEP_IDS = 100


def classify(name):
    c = re.sub(r"[^a-z0-9]", "", name.lower())
    if "phoenix" in c:
        return "phoenix"
    if "breakout" in c:
        return "breakout"
    if "pillar" in c or "momentum" in c:
        return "momentum"
    return None


def state_path(root):
    return os.path.join(root, "data", "_fourpillars_relay_state.json")


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


def extract(msg):
    """מייל → (קבצים, דילוגים). קובץ = {kind, src, day, data, rows, downloadedAt}."""
    sent = email.utils.parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else datetime.now(timezone.utc)
    if sent.tzinfo is None:
        sent = sent.replace(tzinfo=timezone.utc)
    files, skipped = [], []
    for part in msg.walk():
        fn = part.get_filename()
        if not fn or part.get_content_maintype() == "multipart":
            continue
        fn = os.path.basename(str(email.header.make_header(email.header.decode_header(fn))).strip())
        if not fn.lower().endswith(".csv"):
            skipped.append("%s: לא CSV" % fn)
            continue
        kind = classify(fn)
        if not kind:
            skipped.append("%s: סורק לא מזוהה" % fn)
            continue
        data = part.get_payload(decode=True) or b""
        rows = [r for r in rows_of(data) if not str(r.get("Symbol", "")).startswith("Downloaded")]
        hdr = rows[0] if rows else {}
        if rows and any(c not in hdr for c in NEED_COLS):
            skipped.append("%s: חסרות עמודות %s" % (fn, [c for c in NEED_COLS if c not in hdr]))
            continue
        at = downloaded_at(data) or sent
        if in_session(at):
            skipped.append("%s: הורד בזמן המסחר (יום חלקי)" % fn)
            continue
        files.append({"kind": kind, "src": fn, "day": last_closed_day(at).isoformat(), "data": data,
                      "rows": len(rows), "downloadedAt": at.strftime("%Y-%m-%dT%H:%M:%SZ")})
    return files, skipped


def validate(files):
    by = {}
    for f in files:
        by.setdefault(f["kind"], f)
    missing = [HE[k] for k in KINDS if k not in by]
    if missing:
        return None, "חסרים סורקים: " + ", ".join(missing)
    days = {f["day"] for f in by.values()}
    if len(days) > 1:
        return None, "ימי מסחר שונים בין הקבצים: " + ", ".join(sorted(days))
    return by, None


def write_files(root, by, subj, dry_run=False):
    day = next(iter(by.values()))["day"]
    folder = os.path.join(root, "data", "fourpillars", day)
    if all(os.path.exists(os.path.join(folder, k + ".csv")) for k in KINDS):
        return "existing", day
    if dry_run:
        return "would-write", day
    os.makedirs(folder, exist_ok=True)
    for k in KINDS:
        with open(os.path.join(folder, k + ".csv"), "wb") as f:
            f.write(by[k]["data"])
    meta = {"tradeDay": day, "subject": subj, "downloadedAt": max(f["downloadedAt"] for f in by.values()),
            "files": {k: {"src": by[k]["src"], "rows": by[k]["rows"]} for k in KINDS},
            "relayedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    with open(os.path.join(folder, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    return "written", day


def fetch_messages(days=4, skip=()):
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not pw:
        print("relay_fourpillars: אין GMAIL_APP_PASSWORD — דילוג")
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
        print("relay_fourpillars: אין מיילים חדשים")
        return 0
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for mid, subj, m in todo:
        files, skipped = extract(m)
        by, reason = validate(files)
        entry = {"at": stamp, "subject": subj, "day": None, "skipped": skipped, "rejected": reason, "status": None}
        if by:
            status, day = write_files(root, by, subj, dry_run=dry_run)
            entry["status"], entry["day"] = status, day
        st["done"].append(mid)
        st["log"].append(entry)
        print("relay_fourpillars: %s → %s · %s · נדחה: %s · דולגו %s" % (subj, entry["day"], entry["status"], reason, skipped))
    if not dry_run:
        save_state(root, st)
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
