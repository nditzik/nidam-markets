#!/usr/bin/env python3
"""
fetch_gmail.py — מושך את "תדרוך משקיעים" (בוקר + אחר הצהריים) מג'ימייל דרך IMAP
ומייצר data/briefing.json + data/briefings/morning.html + afternoon.html.

דורש סודות (GitHub Secrets):
  GMAIL_USER          — כתובת הג'ימייל (nditzik@gmail.com)
  GMAIL_APP_PASSWORD  — App Password (16 תווים) מ- https://myaccount.google.com/apppasswords

עמידות: אם אין סוד/חיבור נכשל אבל כבר יש briefing.json — משאיר אותו (לא מפיל את ה-Action).
"""
import email
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from email.header import decode_header

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(ROOT, "data", "briefing.json")
OUT_DIR = os.path.join(ROOT, "data", "briefings")

MAILBOX = '"[Gmail]/All Mail"'
SENDER = "nditzik@gmail.com"
MORNING_MARK = "בוקר"
AFTERNOON_MARK = "אחר הצהריים"
SENTIMENT_RE = re.compile(r"([🟢🟡🔴])\s*([^;<\n—–]{0,40})")


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def dec(s):
    if not s:
        return ""
    parts = decode_header(s)
    out = ""
    for text, enc in parts:
        out += text.decode(enc or "utf-8", "ignore") if isinstance(text, bytes) else text
    return out


def html_of(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", "ignore")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(msg.get_content_charset() or "utf-8", "ignore")
    return ""


def sentiment_of(html):
    # מחפש את אימוג'י הסנטימנט הראשון + המילה שאחריו (מתוך תגית ה-pill בכותרת)
    m = SENTIMENT_RE.search(html)
    if not m:
        return {"emoji": "", "text": ""}
    word = re.sub(r"[^֐-׿ \-–]", "", m.group(2)).strip()
    return {"emoji": m.group(1), "text": word}


def _clean(s):
    """מנקה טקסט מתוך HTML: מסיר תגיות, ישויות, רווחים כפולים ורווח לפני פיסוק."""
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&#8203;", ""),
                 ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"')):
        s = s.replace(a, b)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,.;:%])", r"\1", s)
    return s.lstrip("◆").strip()


def _section(html, start, ends):
    """מחזיר את קטע ה-HTML מ-start עד ה-marker הבא מבין ends (או עד הסוף)."""
    i = html.find(start)
    if i < 0:
        return ""
    stop = len(html)
    for e in ends:
        j = html.find(e, i + len(start))
        if 0 <= j < stop:
            stop = j
    return html[i:stop]


# מקטעי-קצה אפשריים אחרי מקטע הידיעות / הלוז
_ENDS = ["RISK VECTOR", "MARKET GRID", "VIX PRIMARY", "TIMELINE", "WATCHLIST", "BOTTOM LINE"]


def _after_heading(html, *labels):
    """קטע ה-HTML שאחרי כותרת המכילה אחת מהתוויות, עד הכותרת הבאה (מבנה 2026+)."""
    for lab in labels:
        i = html.find(lab)
        if i < 0:
            continue
        j = html.find("<h2", i + len(lab))
        return html[i: j if j > 0 else len(html)]
    return ""


def headlines_of(html):
    """4 הידיעות הראשיות. המיילים משנים מבנה בין ימים (h2/ul, divים מעוצבים, סמנים
    באנגלית) — לכן החילוץ עמיד-מבנה: כותרת הסעיף בעברית + הרשימה/הכותרות הקרובות."""
    out = []

    # --- "חדש מאז ..." (כל ניסוח) → תבליטי ה-<ul> הראשון שאחרי הכותרת ---
    i = html.find("חדש מאז")
    if i >= 0:
        m = re.search(r"<ul[^>]*>(.*?)</ul>", html[i:], re.S)
        if m:
            for li in re.findall(r"<li[^>]*>(.*?)</li>", m.group(1), re.S):
                t = _clean(li)
                if t:
                    out.append(t)
    # --- "הידיעות המרכזיות" → <h3> או divים מודגשים-ממוספרים ("1. כותרת") ---
    if not out:
        i = html.find("הידיעות המרכזיות")
        if i >= 0:
            tail = html[i:]
            for m in re.finditer(r"<h3[^>]*>(.*?)</h3>", tail, re.S):
                t = _clean(m.group(1))
                if t:
                    out.append(t)
                if len(out) >= 6:
                    break
            if not out:
                for m in re.finditer(r"<div[^>]*font-weight:\s*800[^>]*>\s*(\d+\s*[.):|]\s*.*?)</div>", tail, re.S):
                    t = re.sub(r"^\d+\s*[.):|]\s*", "", _clean(m.group(1)))
                    if t:
                        out.append(t)
                    if len(out) >= 6:
                        break
    if out:
        return out[:4]

    # --- מבנה ישן ---
    delta = _section(html, "DELTA UPDATE", _ENDS)   # מהדורת צהריים ("חדש מאז הבוקר")
    if delta:
        for cell in re.findall(r"<td[^>]*>(.*?)</td>", delta, re.S):
            if "◆" in cell:
                t = _clean(cell)
                if t:
                    out.append(t)
    if not out:                                      # מהדורת בוקר
        keysig = _section(html, "KEY SIGNALS", ["TIMELINE", "WATCHLIST", "BOTTOM LINE"])
        for m in re.finditer(r"SIGNAL\s*\d+\s*</div>\s*<div[^>]*>(.*?)</div>", keysig or html, re.S):
            t = _clean(m.group(1))
            if t:
                out.append(t)
    return out[:4]


def schedule_of(html):
    """הלוז היומי — זוגות (שעה/תווית, אירוע). עמיד-מבנה: הטבלה הראשונה שאחרי כותרת
    היומן; תומך גם בשתי עמודות (שעה|אירוע) וגם בתא בודד (<b>תווית</b><br>טקסט)."""
    out = []
    for lab in ("מה נשאר ביומן", "יומן השוק", "TIMELINE"):
        i = html.find(lab)
        if i < 0:
            continue
        m = re.search(r"<table[^>]*>(.*?)</table>", html[i:], re.S)
        if not m:
            continue
        for tr in re.findall(r"<tr>(.*?)</tr>", m.group(1), re.S):
            tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
            if not tds:
                continue
            if len(tds) >= 2:
                tm = re.search(r"\d{1,2}:\d{2}", _clean(tds[0]))
                ev = _clean(tds[1])
                if tm and ev:
                    out.append({"time": tm.group(0), "text": ev})
            else:
                b = re.search(r"<b[^>]*>(.*?)</b>", tds[0], re.S)
                label = _clean(b.group(1)) if b else ""
                ev = _clean(re.sub(r"<b[^>]*>.*?</b>", "", tds[0], flags=re.S))
                if not ev:
                    continue
                tm = re.search(r"\d{1,2}:\d{2}", label)
                if tm:
                    out.append({"time": tm.group(0), "text": ev})
                elif label:   # שורה בלי שעה ("היום, ראשון") — תווית קצרה במקום שעה
                    out.append({"time": label.split(",")[0].split("—")[0].strip()[:6], "text": ev})
        if out:
            return out
    return out


def imap_since(days=4):
    """מחרוזת IMAP SINCE (DD-Mon-YYYY, אנגלית) לימים האחרונים."""
    d = datetime.now(timezone.utc) - timedelta(days=days)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{d.day:02d}-{months[d.month - 1]}-{d.year}"


def fetch_candidates(imap):
    """
    שולף את כל המיילים מהשולח מהימים האחרונים ומחזיר רשימת (subject, date_dt, msg)
    ממוינת מהחדש לישן. חיפוש ASCII בלבד (FROM+SINCE) — אין עברית בשאילתת IMAP
    (חיפוש כותרת בעברית ב-Gmail IMAP נכשל ללא charset ומחזיר ריק).
    """
    typ, data = imap.search(None, 'FROM', SENDER, 'SINCE', imap_since())
    ids = data[0].split() if typ == "OK" and data and data[0] else []
    out = []
    for mid in ids:
        typ, msg_data = imap.fetch(mid, "(RFC822)")
        if typ != "OK" or not msg_data or not msg_data[0]:
            continue
        msg = email.message_from_bytes(msg_data[0][1])
        subject = dec(msg.get("Subject"))
        date_dt = email.utils.parsedate_to_datetime(msg.get("Date"))
        out.append((subject, date_dt, msg))
    out.sort(key=lambda t: (t[1] or datetime(1970, 1, 1, tzinfo=timezone.utc)), reverse=True)
    return out


def pick_latest(candidates, mark, exclude=None):
    """מחזיר (subject, date_dt, html) עבור הבריף האחרון שכותרתו מכילה 'תדרוך משקיעים' + mark."""
    for subject, date_dt, msg in candidates:
        if subject.startswith("Fwd:") or subject.startswith("Fw:"):
            continue  # דילוג על העברות (Forward) — לא המקור
        if "תדרוך משקיעים" not in subject or mark not in subject:
            continue
        if exclude and exclude in subject:
            continue
        return subject, date_dt, html_of(msg)
    return None


def build_slot(res):
    if not res:
        return None
    subject, date_dt, html = res
    return {"subject": subject, "date_dt": date_dt, "html": html}


def main():
    user = os.environ.get("GMAIL_USER") or "nditzik@gmail.com"
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not pw:
        print("[warn] חסר GMAIL_APP_PASSWORD.")
        if os.path.exists(OUT_JSON):
            print("[keep] משאיר briefing.json קיים.")
            return 0
        return 1

    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(user, pw)
        imap.select(MAILBOX, readonly=True)
    except Exception as e:
        print(f"[warn] חיבור IMAP נכשל: {e}")
        return 0 if os.path.exists(OUT_JSON) else 1

    try:
        candidates = fetch_candidates(imap)
        print(f"[info] נמצאו {len(candidates)} מיילים מהשולח בימים האחרונים.")
        morning = build_slot(pick_latest(candidates, MORNING_MARK))
        afternoon = build_slot(pick_latest(candidates, AFTERNOON_MARK))
    finally:
        try:
            imap.logout()
        except Exception:
            pass

    if not morning and not afternoon:
        print("[warn] לא נמצאו בריפים.")
        return 0 if os.path.exists(OUT_JSON) else 1

    # התחל מהקיים כדי לא לאבד צד שלא נמשך הפעם
    existing = {}
    if os.path.exists(OUT_JSON):
        try:
            with open(OUT_JSON, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    os.makedirs(OUT_DIR, exist_ok=True)
    out = {k: v for k, v in existing.items() if k != "_meta"}
    changed = False

    for key, slot, fname in (("morning", morning, "morning.html"),
                             ("afternoon", afternoon, "afternoon.html")):
        if not slot:
            continue
        path = os.path.join(OUT_DIR, fname)
        old_html = None
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                old_html = f.read()
        if slot["html"] != old_html:
            with open(path, "w", encoding="utf-8") as f:
                f.write(slot["html"])
            changed = True
        d = slot["date_dt"]
        # גם התאריך וגם השעה בשעון ישראל — אחרת מייל שנשלח לפי אזור-זמן זר
        # (למשל -0400) נותן תאריך גולמי של אתמול ומבלבל את בחירת המהדורה בבית.
        off = 3 if 4 <= datetime.now(timezone.utc).month <= 10 else 2
        il = d.astimezone(timezone(timedelta(hours=off))) if d else None
        meta = {
            "subject": slot["subject"],
            "dateLabel": il.strftime("%d/%m/%Y") if il else "",
            "time": il.strftime("%H:%M") if il else "",
            "sentiment": sentiment_of(slot["html"]),
            "headlines": headlines_of(slot["html"]),
            "schedule": schedule_of(slot["html"]),
            "file": f"data/briefings/{fname}",
        }
        if out.get(key) != meta:
            changed = True
        out[key] = meta
        print(f"[ok] {key}: {slot['subject']}")

    # "commit רק אם יש שינוי": אם שום בריף לא השתנה — לא נוגעים בקבצים
    if not changed and os.path.exists(OUT_JSON):
        print("[nochange] אין בריף חדש — briefing.json נשאר כפי שהוא.")
        return 0

    out["_meta"] = {"updatedAt": israel_stamp(), "source": "gmail"}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT_JSON} (שינוי זוהה)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
