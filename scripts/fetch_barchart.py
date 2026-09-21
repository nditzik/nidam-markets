#!/usr/bin/env python3
"""
fetch_barchart.py — מושך שתי מהדורות Barchart מג'ימייל (IMAP) → data/morning.json
+ data/briefings/morning-review.html + morning-premkt.html (טאב "Barchart").

שתי מהדורות, אותו שולח (nditzik@gmail.com), אותה ריצה:
  • "review"  — "דוח Barchart יומי" ~06:00, נושא "דוח Barchart יומי | ..."
  • "premkt"  — "טרום מסחר בוול סטריט" ~14:00 (21.9.2026, בקשת איציק), נושא
                "טרום מסחר בוול סטריט | <כותרת היום> (DD.MM.YYYY)"
כל אחת נשמרת כקובץ HTML ומוצגת ב-iframe (כמו טאב תדרוך משקיעים) — לא חילוץ טקסט.

צורת morning.json: review בשורש (תאימות-לאחור — routine prompts קוראים ישירות
d.subject/d.file/d.dateLabel), premkt מקונן תחת מפתח "premkt" באותה צורה.

דורש סודות: GMAIL_USER + GMAIL_APP_PASSWORD.
מצב בדיקה מקומי:  python fetch_barchart.py --file <saved_message.json>  (review בלבד)
עמידות: כשל/היעדר מקור → משאיר morning.json קיים; מהדורה אחת חסרה לא מפילה את השנייה.
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
OUT_HTML_PREMKT = os.path.join(OUT_DIR, "morning-premkt.html")
HTML_REL_PREMKT = "data/briefings/morning-premkt.html"

MAILBOX = '"[Gmail]/All Mail"'
SENDER = "nditzik@gmail.com"
# 2026-08-28: הכותרת נסחפה מ"סיכום Barchart יומי" ל"דוח Barchart יומי" (ראה
# הודעה אמיתית בג'ימייל: "דוח Barchart יומי | 28.08.2026 | 33 הודעות") — המייל
# עצמו נשלח כרגיל כל יום, אבל ההתאמה המדויקת נכשלה בשקט (best=None, בלי
# שגיאה) והשאירה את morning.json תקוע ~3 ימים. אותו דפוס בדיוק כמו הסחיפה
# החוזרת בפרסר של briefing.json — לא לסמוך על מילת-הקידומת המדויקת
# ("סיכום"/"דוח"), רק על החלק היציב "Barchart יומי". אם ייסחף שוב עם קידומת
# שלישית — להוסיף עוד וריאנט, לא להחליף.
SUBJECT_MARK = "Barchart יומי"
# בסופ"ש/חג הצינור של איציק שולח "עדכון Barchart יומי | אין הודעות חדשות | DD.MM.YYYY"
# במקום סיכום — נקלט כחיווי סטטוס בלבד (notice), הסקירה המוצגת נשארת האחרונה שהתקבלה
NOTICE_MARK = "אין הודעות חדשות"
# מהדורת טרום-המסחר (21.9.2026): הכותרת דינמית ("טרום מסחר בוול סטריט | <כותרת
# היום>") — אין קידומת קבועה ארוכה, רק המקטע הראשון היציב. עדיין אין תצפית
# מספיקה על ימי סופ"ש/חג — אם יתברר שיש חיווי "אין הודעות" מקביל, להוסיף כאן.
PREMKT_MARK = "טרום מסחר בוול סטריט"


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


def entry_of(subject, date_dt, html_body, out_html_path, html_rel):
    """(entry-dict, html-changed?) עבור מהדורה אחת — בלי לגעת בקובץ אם לא השתנה."""
    old_html = None
    if os.path.exists(out_html_path):
        with open(out_html_path, "r", encoding="utf-8") as f:
            old_html = f.read()
    changed = html_body != old_html
    if changed:
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(out_html_path, "w", encoding="utf-8") as f:
            f.write(html_body)
    ist = timezone(timedelta(hours=3))
    entry = {
        "subject": subject,
        "dateLabel": date_label(subject, date_dt),
        "time": date_dt.astimezone(ist).strftime("%H:%M") if date_dt else "",
        "file": html_rel,
    }
    return entry, changed


def write_if_changed(review=None, premkt=None, notice=None):
    """review/premkt: (subject, date_dt, html_body) או None. review בשורש (תאימות-לאחור),
    premkt מקונן. מהדורה חסרה משאירה את הקיימת (לא נמחקת)."""
    existing = {}
    if os.path.exists(OUT_JSON):
        try:
            with open(OUT_JSON, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}
    out = {k: v for k, v in existing.items() if k not in ("_meta",)}
    changed = False

    if review:
        entry, html_changed = entry_of(*review, OUT_HTML, HTML_REL)
        ist = timezone(timedelta(hours=3))
        if notice and notice[0] and notice[0] > review[1]:
            nd = notice[0].astimezone(ist)
            entry["notice"] = {"date": nd.strftime("%Y-%m-%d"), "time": nd.strftime("%H:%M")}
        prev_review = {k: v for k, v in out.items() if k != "premkt"}
        if html_changed or prev_review != entry:
            changed = True
        for k in list(out.keys()):
            if k != "premkt":
                del out[k]
        out.update(entry)

    if premkt:
        entry, html_changed = entry_of(*premkt, OUT_HTML_PREMKT, HTML_REL_PREMKT)
        if html_changed or out.get("premkt") != entry:
            changed = True
        out["premkt"] = entry

    if not changed:
        print("[nochange] אין סיכום חדש — morning.json נשאר כפי שהוא.")
        return
    out["_meta"] = {"updatedAt": israel_stamp(), "source": "gmail"}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT_JSON}" + (" (review)" if review else "") + (" (premkt)" if premkt else ""))


def run_offline(path):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    try:
        date_dt = datetime.fromisoformat(d["date"].replace("Z", "+00:00"))
    except ValueError:
        date_dt = email.utils.parsedate_to_datetime(d["date"])
    write_if_changed(review=(d["subject"], date_dt, d["htmlBody"]))
    return 0


def run_imap():
    user = os.environ.get("GMAIL_USER") or "nditzik@gmail.com"
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not pw:
        print("[warn] חסר GMAIL_APP_PASSWORD.")
        return 0 if os.path.exists(OUT_JSON) else 1
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(user, pw)
        imap.select(MAILBOX, readonly=True)
    except Exception as e:
        print(f"[warn] חיבור IMAP נכשל: {e}")
        return 0 if os.path.exists(OUT_JSON) else 1
    try:
        import briefing_archive as ba
        idx = ba.load_index()
        # ריצה ראשונה של מהדורה חדשה (אין עדיין ארכיון שלה) → אכלוס-לאחור של 30 יום
        backfill_review = not ba.has_kind(idx, "review")
        backfill_premkt = not ba.has_kind(idx, "premkt")
        since_days = ba.KEEP_DAYS + 2 if (backfill_review or backfill_premkt) else 3
        # חיפוש ASCII-בטוח (FROM + SINCE); סינון הכותרת בעברית ב-Python
        typ, data = imap.search(None, "FROM", SENDER, "SINCE", imap_since(since_days))
        ids = data[0].split() if typ == "OK" and data and data[0] else []
        best_review = best_premkt = None
        notice = None
        arch_changed = False
        for mid in reversed(ids):  # מהחדש לישן
            typ, md = imap.fetch(mid, "(RFC822)")
            if typ != "OK" or not md or not md[0]:
                continue
            msg = email.message_from_bytes(md[0][1])
            subject = dec(msg.get("Subject"))
            if subject.startswith("Fwd:") or subject.startswith("Fw:"):
                continue
            if notice is None and "Barchart" in subject and NOTICE_MARK in subject:
                try:
                    notice = (email.utils.parsedate_to_datetime(msg.get("Date")),)
                except Exception:
                    pass
                continue
            is_review = SUBJECT_MARK in subject
            is_premkt = PREMKT_MARK in subject
            if not (is_review or is_premkt):
                continue
            date_dt = email.utils.parsedate_to_datetime(msg.get("Date"))
            body = html_of(msg)
            kind = "review" if is_review else "premkt"
            if ba.archive_email(idx, kind, subject, date_dt, body):
                arch_changed = True
            if is_review and best_review is None:
                best_review = (subject, date_dt, body)
            if is_premkt and best_premkt is None:
                best_premkt = (subject, date_dt, body)
            done_review = best_review is not None and not backfill_review
            done_premkt = best_premkt is not None and not backfill_premkt
            if done_review and done_premkt:
                break   # בריצה רגילה מספיק המייל האחרון של כל מהדורה
        if arch_changed:
            ba.prune_and_save(idx, israel_stamp())
            print("[archive] אינדקס הסקירות עודכן")
        if not best_review and not best_premkt:
            print("[warn] לא נמצאה אף מהדורת Barchart.")
            return 0 if os.path.exists(OUT_JSON) else 1
        if not best_review:
            print("[warn] לא נמצא 'דוח Barchart יומי' — נשמר premkt בלבד.")
        if not best_premkt:
            print("[warn] לא נמצא 'טרום מסחר בוול סטריט' — נשמר review בלבד.")
        write_if_changed(review=best_review, premkt=best_premkt, notice=notice)
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
