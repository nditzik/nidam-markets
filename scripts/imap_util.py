"""
imap_util.py — קריאת תיבת הדואר בזול: כותרות קודם, גוף מלא רק למייל שעבר סינון (1.10.2026).

הבעיה: fetch_gmail / fetch_barchart / fetch_pulse מחפשים "כל מה שמ-nditzik@gmail.com בימים
האחרונים" ומורידים כל מייל במלואו (RFC822) כדי לבדוק את הנושא. מאז 29.9 מגיעים לאותו שולח
גם מיילי CSV של גרוק (אופציות ~500KB, מומנטום ~300KB, כמה ביום), ו-Gmail האט את ההורדות:
ב-1.10 בבוקר "Fetch gmail briefings" לקח 13 דקות במקום שניות, והריצות של ה-Action נערמו.

הפתרון: בקשה אחת שמביאה רק כותרות (Subject/Date/Message-ID/From) לכל המזהים, סינון לפי
הנושא בפייתון, ורק אז הורדה מלאה של המיילים הרלוונטיים.
"""
import email
import email.header
import email.utils
from datetime import datetime, timezone

_HDR = "(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE MESSAGE-ID FROM)])"
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _dec(s):
    if not s:
        return ""
    try:
        return str(email.header.make_header(email.header.decode_header(s)))
    except Exception:
        return str(s)


def headers(imap, ids, chunk=200):
    """מזהי IMAP → רשימת dict {id, subject, date, message_id, from}, מהחדש לישן.
    בקשת FETCH אחת לכל 200 מזהים, בלי גוף ובלי צרופות. BODY.PEEK לא מסמן כנקרא."""
    out = []
    ids = [i if isinstance(i, bytes) else str(i).encode() for i in ids]
    for k in range(0, len(ids), chunk):
        part = ids[k:k + chunk]
        typ, data = imap.fetch(b",".join(part), _HDR)
        if typ != "OK" or not data:
            continue
        for item in data:
            if not isinstance(item, tuple) or len(item) < 2:
                continue
            mid = item[0].split()[0]
            msg = email.message_from_bytes(item[1])
            try:
                dt = email.utils.parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else None
                if dt is not None and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                dt = None
            out.append({"id": mid, "subject": _dec(msg.get("Subject")), "date": dt,
                        "message_id": (msg.get("Message-ID") or "").strip(), "from": _dec(msg.get("From"))})
    out.sort(key=lambda h: h["date"] or _EPOCH, reverse=True)
    return out


def full(imap, mid):
    """הורדה מלאה של מייל אחד (RFC822) → email.message.Message, או None."""
    typ, md = imap.fetch(mid, "(RFC822)")
    if typ != "OK" or not md or not isinstance(md[0], tuple):
        return None
    return email.message_from_bytes(md[0][1])
