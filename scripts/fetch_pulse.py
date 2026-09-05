#!/usr/bin/env python3
"""
fetch_pulse.py — "בזק מהרשת": כותרות-בזק מחשבונות X פיננסיים אל data/pulse.json.

שני צינורות בלתי-תלויים (נבדק 05/09/2026), שמתמזגים לאותה רצועה:
  1. שיקופי טלגרם רשמיים (t.me/s/<slug> — HTML ציבורי, בלי API, בחינם):
     @KobeissiLetter, Walter Bloomberg, FinancialJuice, @Barchart
  2. דיג'סט X במייל (IMAP, אותם סודות GMAIL_* של שאר צינורות המייל בריפו):
     בוט של איציק סורק כל 15 דק' 8 חשבונות ושולח מייל בפורמט קבוע.

החפיפה בין השניים **מכוונת**: 3 מ-8 חשבונות הדיג'סט כבר מגיעים בטלגרם, כך
שנפילה של אחד הצינורות לא מרוקנת את הרצועה — הבוט נופל, הטלגרם מחזיק; הטלגרם
נופל, הבוט מכסה הכל. זה בדיוק הלקח מ-05/09/2026, כשכל 7 מקורות ה-Nitter מתו
בבת אחת מפני שחלקו מנגנון יחיד (ראו למטה).

סינון: בלי ריטוויטים/תגובות, בלי הודעות-מדיה ריקות, בלי כפילויות, חלון 48 שעות.
עמידות: מקור שנפל משתמש בפריטים האחרונים שנתפסו ממנו (מ-pulse.json הקודם).

═══ Nitter מת — 7 מקורות הוסרו (05/09/2026) ═══
עד לתאריך הזה היו כאן עוד 7 חשבונות דרך Nitter (@wallstengine, @LiveSquawk,
@StockMKTNewz, @AIStockSavvy, @MikeZaccardi, @LizAnnSonders, @Kalshi).
בבדיקה התברר ש**שני מופעי ה-Nitter מתו**:
  • nitter.net  → HTTP 410 Gone (הושבת לצמיתות)
  • xcancel.com → עונה, אבל מחזיר פיד-דמה: כותרת ופריט יחיד בנוסח
    "RSS reader not yet whitelisted!" עם בקשה לשלוח מייל ל-rss@xcancel.com
    כדי לקבל whitelist.
זה היה גרוע יותר מ"מקור מת" בשקט: המחרוזת "RSS reader not yet whitelisted!"
היא באורך 31 תווים, כלומר **עברה את סף `keep()` של 25 תווים והתקבלה כפריט
חדשות תקין**. היא לא הופיעה באתר רק במקרה — 4 ערוצי הטלגרם מציפים את
10 המקומות בפיד. בשעה שקטה (סופ"ש/לילה) היא הייתה מתפרסמת באתר ככותרת שוק.
לכן נוסף גם `BAD_PATTERNS` למטה — הגנה כללית, לא רק לתקלה הזו.

חיפוש תחליפים נכשל (נבדק בפועל, 05/09/2026): לאף אחד מ-7 החשבונות אין ערוץ
טלגרם רשמי פעיל. `LizAnnSonders` ו-`KalshiNews` קיימים אבל נטושים (1098 ו-53
ימים) ומכילים ספאם/תוכן לא-קשור — אין להשתמש בהם. גם ערוצי-חלופה כלליים
נבדקו: DeItaone/FirstSquawk/zerohedge/unusual_whales — אין להם שיקוף ציבורי;
spectatorindex נטוש; markettwits פעיל אך ברוסית; disclotv גיאופוליטי ואיטי.
המסקנה: 4 ערוצי הטלגרם שנשארו הם מה שזמין בחינם, והם מכסים היטב (FinancialJuice
לבדו הוא שירות squawk מלא). `fetch_nitter()` נשמרה בקוד — אם יקום מופע Nitter
עובד, מספיק להחזיר שורות ל-SOURCES ולהוסיף את המארח ל-NITTER_HOSTS.
"""
import email
import email.header
import email.utils
import html as htmllib
import imaplib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(ROOT, "data", "pulse.json")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# (מזהה-תצוגה, סוג, פרטים)
SOURCES = [
    ("@KobeissiLetter", "tg", "thekobeissiletter"),
    ("Walter Bloomberg", "tg", "walter_bloomberg"),
    ("FinancialJuice", "tg", "financialjuice"),
    ("@Barchart", "tg", "barchartx"),          # טלגרם רשמי (התגלה בציוץ שלהם)
    # 7 מקורות Nitter הוסרו 05/09/2026 — ראו הסבר מלא ב-docstring למעלה.
]
NITTER_HOSTS = []   # אין מופע Nitter עובד; להוסיף כאן אם יקום אחד

# ── דיג'סט X במייל (05/09/2026) ──────────────────────────────────────────────
# בוט של איציק סורק חשבונות X כל 15 דק' ושולח מייל בפורמט קבוע:
#   YYYY-MM-DD ||| HH:MM ||| @handle ||| טקסט ||| קישור
# (או שורה אחת "NO-ITEMS" כשאין חדש — כך אפשר להבדיל בין שקט לבין בוט מת.)
# העוגן בנושא הוא באנגלית **בכוונה**: הנושא המקורי היה "דיג׳סט X" עם גרש עברי
# (U+05F3), תו שנראה כמו אפוסטרוף אבל שונה ממנו — בדיוק סוג ההתאמה-בשקט
# שהפילה כאן פעמיים את briefing.json ואת fetch_barchart.py.
XD_SUBJECT_MARK = "X-PULSE"
XD_SENDER = "nditzik@gmail.com"
XD_NO_ITEMS = "NO-ITEMS"
XD_SINCE_DAYS = 2          # חלון חיפוש IMAP; סינון 48ש' נעשה ממילא בהמשך
XD_SEP = "|||"

# אותו חשבון, שם אחר בכל ערוץ: @DeItaone הוא Walter Bloomberg (אומת 05/09/2026
# מול 3 התאמות מדויקות בהפרש דקה). בלי המיפוי, MAX_PER_SOURCE היה נותן לו
# 3 מקומות מהטלגרם + 3 מהדיג'סט = 6, והוא היה משתלט על הרצועה.
# ‎@FinancialJuice בדיג'סט מול "FinancialJuice" (בלי @) בטלגרם — בלי המיפוי
# הם נספרים כשני מקורות נפרדים ותקרת MAX_PER_SOURCE נפתחת ל-6 במקום 3.
# ‎@KobeissiLetter ו-@Barchart תואמים כבר ככתבם ולא נדרש להם מיפוי.
XD_ALIASES = {
    "@deitaone": "Walter Bloomberg",
    "@financialjuice": "FinancialJuice",
}

WINDOW_H = 48       # חלון תצוגה (שעות)
MAX_ITEMS = 10      # תקרת פריטים בפלט
MAX_PER_SOURCE = 3  # איזון: שאף ערוץ (במיוחד FinancialJuice) לא יציף את הרצועה
MAX_LEN = 170       # קיצור טקסט


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def il_time(dt):
    off = 3 if 4 <= datetime.now(timezone.utc).month <= 10 else 2
    return dt.astimezone(timezone(timedelta(hours=off))).strftime("%H:%M")


def _get(url, timeout=18):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def clean_text(s):
    s = re.sub(r"<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    s = htmllib.unescape(s)
    s = re.sub(r"https?://\S+", "", s)          # לינקים גולמיים החוצה מהטקסט
    s = re.sub(r"\|FJ\s*$", "", s.strip())      # חתימת FinancialJuice
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > MAX_LEN:
        s = s[:MAX_LEN].rsplit(" ", 1)[0] + "…"
    return s


# הודעות-שירות של הצינור עצמו שהתחזו לפריט חדשות (05/09/2026 — xcancel החזיר
# "RSS reader not yet whitelisted!", 31 תווים, שעבר את סף האורך והתקבל ככותרת).
# כל דפוס כאן נבדק מול טקסט הפריט; ההגנה כללית ולא קשורה למקור ספציפי, כי
# אותה תקלה יכולה לחזור מכל שירות-מראה עתידי בנוסח אחר.
BAD_PATTERNS = re.compile(
    r"(not\s+yet\s+whitelist|whitelist(ed)?\s*!|rss\s+reader|rate.?limit"
    r"|instance\s+(is\s+)?(down|blocked)|tweets?\s+are\s+not\s+available"
    r"|please\s+send\s+an\s+email|try\s+again\s+later|service\s+unavailable"
    r"|error\s*\d{3}|^\s*(error|forbidden|not\s+found)\s*$)",
    re.I,
)


def keep(text):
    if not text or len(text) < 25:
        return False
    if text.startswith(("RT by", "R to")):       # ריטוויטים/תגובות (Nitter)
        return False
    if re.match(r"^(Live stream|Pinned|Forwarded)", text, re.I):
        return False
    if BAD_PATTERNS.search(text):                # הודעת-שירות, לא חדשות
        return False
    return True


def fetch_tg(label, slug):
    """הודעות מדף התצוגה הציבורי של ערוץ טלגרם."""
    h = _get("https://t.me/s/" + slug)
    out = []
    for chunk in h.split('tgme_widget_message_wrap')[1:]:
        post = re.search(r'data-post="([^"]+)"', chunk)
        tm = re.search(r'<time datetime="([^"]+)"', chunk)
        tx = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', chunk, re.S)
        if not (post and tm and tx):
            continue
        text = clean_text(tx.group(1))
        if not keep(text):
            continue
        try:
            dt = datetime.fromisoformat(tm.group(1))
        except ValueError:
            continue
        out.append({"source": label, "text": text, "dt": dt.astimezone(timezone.utc).isoformat(),
                    "link": "https://t.me/" + post.group(1)})
    return out


def fetch_nitter(label, handle):
    """ציוצים דרך Nitter RSS, עם נפילה בין מופעים; לינק משוכתב ל-x.com."""
    last_err = None
    for host in NITTER_HOSTS:
        try:
            h = _get(f"https://{host}/{handle}/rss")
            items = re.findall(r"<item>(.*?)</item>", h, re.S)
            out = []
            for it in items:
                t = re.search(r"<title>(.*?)</title>", it, re.S)
                d = re.search(r"<pubDate>(.*?)</pubDate>", it)
                l = re.search(r"<link>(.*?)</link>", it)
                if not (t and d):
                    continue
                text = clean_text(t.group(1))
                if not keep(text):
                    continue
                try:
                    dt = parsedate_to_datetime(d.group(1))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                link = (l.group(1) if l else "").strip()
                link = re.sub(r"https?://[^/]+/", "https://x.com/", link).split("#")[0]
                out.append({"source": label, "text": text,
                            "dt": dt.astimezone(timezone.utc).isoformat(), "link": link})
            if out:
                return out
        except Exception as e:
            last_err = e
    raise RuntimeError(f"כל מופעי Nitter נכשלו: {last_err}")


def _unwrap_link(url):
    """Gmail עוטף לינקים ב-google.com/url?q=... — מחזיר את היעד האמיתי."""
    url = (url or "").strip()
    if "google.com/url" not in url:
        return url
    try:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("q")
        return urllib.parse.unquote(q[0]) if q else url
    except Exception:
        return url


def _mail_body(msg):
    """גוף המייל כטקסט — מעדיף text/plain, ונופל ל-HTML מנוקה."""
    plain = html = ""
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.get_content_maintype() == "multipart":
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8", "ignore")
        if part.get_content_type() == "text/plain" and not plain:
            plain = text
        elif part.get_content_type() == "text/html" and not html:
            html = text
    if plain:
        return plain
    # HTML → טקסט: <br>/<p> לשורות, ואז הסרת תגיות (בלי clean_text — הוא
    # מקצר וחותך לינקים, וכאן צריך את השורה השלמה לפיצול)
    h = re.sub(r"<br\s*/?>|</p>|</div>|</tr>", "\n", html, flags=re.I)
    h = re.sub(r"<[^>]+>", "", h)
    return htmllib.unescape(h)


def parse_xdigest(body, il_off):
    """שורות הדיג'סט → פריטים. שורה פגומה מדולגת ולא מפילה את השאר."""
    out = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or XD_SEP not in line:
            continue
        # שלושת השדות הראשונים קבועים, והקישור — אם קיים — תמיד אחרון. כל מה
        # שביניהם הוא הטקסט, גם אם המפריד מופיע בתוך הציוץ עצמו (קרה בבדיקה).
        # השדה האחרון נחשב קישור רק אם הוא באמת נראה כמו URL; אחרת הוא טקסט,
        # כדי שציוץ עם ||| ובלי לינק לא יאבד את סופו.
        parts = [p.strip() for p in line.split(XD_SEP)]
        if len(parts) < 4:
            continue
        d, t, handle = parts[0], parts[1], parts[2]
        rest = parts[3:]
        if re.match(r"^https?://", rest[-1]):
            link = _unwrap_link(rest[-1])
            rest = rest[:-1]
        else:
            link = ""
        if not rest:
            continue
        # שני פורמטים נתמכים במקביל, כדי שהחלפת הפקודה בבוט לא תיצור חלון שבור:
        #   5 שדות (ישן): ... ||| טקסט ||| קישור
        #   6 שדות (חדש): ... ||| אנגלית ||| עברית ||| קישור
        # ההבחנה לפי תוכן ולא לפי ספירה בלבד — שדה עברית ריק הוא תקין (כך
        # ביקשנו מהבוט כשאין תרגום טוב), ומצד שני המפריד ||| יכול להופיע בתוך
        # הציוץ עצמו. לכן: השדה האחרון נחשב "עברית" רק אם הוא ריק או מכיל
        # אותיות עבריות; אחרת הוא המשך של הטקסט האנגלי.
        if len(rest) >= 2 and (not rest[-1] or re.search(r"[֐-׿]", rest[-1])):
            text = (" " + XD_SEP + " ").join(rest[:-1])
            he = rest[-1]
        else:
            text = (" " + XD_SEP + " ").join(rest)
            he = ""
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d) or not re.match(r"^\d{1,2}:\d{2}$", t):
            continue
        if not handle.startswith("@"):
            continue
        try:
            naive = datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        dt = naive.replace(tzinfo=timezone(timedelta(hours=il_off)))
        text = clean_text(re.sub(r"^\*+\s*", "", text))   # DeItaone מקדים * לכותרות
        # הסינון תמיד על האנגלית — היא המקור, והיא שנבדקת מול BAD_PATTERNS
        if not keep(text):
            continue
        he = clean_text(re.sub(r"^\*+\s*", "", he))   # הכוכבית עוברת גם לתרגום
        label = XD_ALIASES.get(handle.lower(), handle)
        # מוצג עברית כשיש, ונופל לאנגלית כשאין (שדה ריק = הבוט לא היה בטוח).
        # `_key` נושא תמיד את האנגלית, כי עליה נעשית השוואת-הכפילויות מול
        # הטלגרם — בלי זה תרגום היה שובר את הדה-דופ ואותה ידיעה הייתה מופיעה
        # פעמיים. `_key` נשאר פנימי ולא נכתב לפלט.
        out.append({"source": label, "text": he or text, "_key": text,
                    "dt": dt.astimezone(timezone.utc).isoformat(), "link": link})
    return out


def fetch_xdigest():
    """הדיג'סט האחרון מהמייל. כל כשל → רשימה ריקה (הטלגרם ממשיך לבדו)."""
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not pw:
        print("[skip] דיג'סט X: חסר GMAIL_APP_PASSWORD.")
        return []
    user = os.environ.get("GMAIL_USER") or XD_SENDER
    il_off = 3 if 4 <= datetime.now(timezone.utc).month <= 10 else 2
    imap = None
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(user, pw)
        imap.select('"[Gmail]/All Mail"', readonly=True)
        since = datetime.now(timezone.utc) - timedelta(days=XD_SINCE_DAYS)
        mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][since.month - 1]
        typ, data = imap.search(None, "FROM", XD_SENDER,
                                "SINCE", f"{since.day:02d}-{mon}-{since.year}")
        ids = data[0].split() if typ == "OK" and data and data[0] else []
        items, scanned = [], 0
        for mid in reversed(ids):            # מהחדש לישן
            if scanned >= 40:                # תקרת בטיחות
                break
            typ, md = imap.fetch(mid, "(RFC822)")
            if typ != "OK" or not md or not md[0]:
                continue
            msg = email.message_from_bytes(md[0][1])
            subject = str(email.header.make_header(
                email.header.decode_header(msg.get("Subject") or "")))
            if XD_SUBJECT_MARK not in subject:
                continue
            scanned += 1
            body = _mail_body(msg)
            if XD_NO_ITEMS in body and XD_SEP not in body:
                print(f"[ok] דיג'סט X: {subject[:40]} — NO-ITEMS")
                continue
            got = parse_xdigest(body, il_off)
            items += got
            print(f"[ok] דיג'סט X: {subject[:40]} — {len(got)} פריטים")
            if len(items) >= MAX_ITEMS * 4:
                break
        if not scanned:
            print(f"[warn] דיג'סט X: לא נמצא מייל עם '{XD_SUBJECT_MARK}' ב-"
                  f"{XD_SINCE_DAYS} הימים האחרונים.")
        return items
    except Exception as e:
        print(f"[warn] דיג'סט X נכשל: {e}")
        return []
    finally:
        try:
            if imap:
                imap.logout()
        except Exception:
            pass


def main():
    # פריטים קודמים — גיבוי לכל מקור שנופל הפעם
    prev = {}
    if os.path.exists(OUT_JSON):
        try:
            with open(OUT_JSON, "r", encoding="utf-8") as f:
                for it in json.load(f).get("items", []):
                    prev.setdefault(it["source"], []).append(it)
        except Exception:
            prev = {}

    collected, ok = [], 0
    for label, kind, ref in SOURCES:
        try:
            items = fetch_tg(label, ref) if kind == "tg" else fetch_nitter(label, ref)
            collected += items
            ok += 1
            print(f"[ok] {label}: {len(items)} פריטים")
        except Exception as e:
            old = prev.get(label, [])
            collected += old
            print(f"[fallback] {label}: {e} — משתמש ב-{len(old)} פריטים קודמים")

    # דיג'סט X מהמייל — מצטרף לאותו מאגר, כך שהמיון/הדה-דופ/תקרת-המקור
    # פועלים עליו בדיוק כמו על הטלגרם. חפיפה מכוונת: אם הבוט נופל, 4 ערוצי
    # הטלגרם ממשיכים להחזיק את הרצועה, ולהפך.
    xd = fetch_xdigest()
    if xd:
        collected += xd
        ok += 1

    if not ok and not collected:
        print("[warn] אף מקור לא נמשך.")
        return 0 if os.path.exists(OUT_JSON) else 1

    # חלון זמן + מיון + דה-דופ (לפי תחילת הטקסט מנורמלת)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=WINDOW_H)
    fresh = []
    for it in collected:
        try:
            dt = datetime.fromisoformat(it["dt"])
        except ValueError:
            continue
        if dt >= cutoff:
            it["_dt"] = dt
            fresh.append(it)
    fresh.sort(key=lambda x: x["_dt"], reverse=True)

    # מעבר-מקדים: מבין שתי גרסאות של אותה ידיעה — לבחור את המתורגמת.
    # בלי זה התרגום היה בלתי-נראה לגמרי (נמדד: 0/10 פריטים בעברית): הטלגרם
    # מתייג לפי שעת הפרסום במראה, והדיג'סט לפי שעת הציוץ המקורי — כלומר
    # הגרסה האנגלית תמיד ממוינת ראשונה, תופסת את המקום, והעברית נחסמת
    # ככפילות. כאן נשמר המיקום/הזמן של הראשון (המיון לא זז), ורק הטקסט
    # והקישור מוחלפים בגרסה העברית + הקישור הישיר ל-x.com.
    def _dkey(it):
        return re.sub(r"\W+", "", (it.get("_key") or it["text"]).lower())[:40]

    def _translated(it):
        return bool(it.get("_key")) and it["text"] != it["_key"]

    upgraded = 0
    first_of = {}
    for it in fresh:
        k = _dkey(it)
        keep_it = first_of.get(k)
        if keep_it is None:
            first_of[k] = it
        elif _translated(it) and not _translated(keep_it):
            keep_it["text"] = it["text"]
            keep_it["link"] = it["link"] or keep_it["link"]
            keep_it["_key"] = it["_key"]
            upgraded += 1
    if upgraded:
        print(f"[tr] {upgraded} פריטים הוחלפו בגרסה העברית מהדיג'סט")

    seen, items, per_src = set(), [], {}
    for it in fresh:
        # 40 ולא 80 (05/09/2026): אותה ידיעה מגיעה משני ערוצים בנוסח מעט שונה —
        # חתימות/סיומות בזנב ("- STATE MEDIA", "@Barchart • Sep", אימוג'י פותח)
        # דחפו את המפתחות ל-80 להיראות שונים, ורק 2 מתוך 6 כפילויות אמיתיות
        # נתפסו. נמדד מול נתונים אמיתיים: ב-40 נתפסות 6/6, עם 0 חסימות-שווא
        # (נבדק גם מול 6 פריטים חדשים-באמת וגם מול כל 78 הפריטים החיים בפיד —
        # הפלט נשאר זהה). קריטי לקראת חיבור הדיג'סט של X, שחופף במכוון
        # ל-4 ערוצי הטלגרם כשכבת גיבוי.
        # `_key` (האנגלית המקורית) כשקיים — כך פריט מתורגם מהדיג'סט עדיין
        # מזוהה ככפילות של אותה ידיעה שהגיעה באנגלית מהטלגרם.
        key = re.sub(r"\W+", "", (it.get("_key") or it["text"]).lower())[:40]
        if key in seen:
            continue
        if per_src.get(it["source"], 0) >= MAX_PER_SOURCE:
            continue
        seen.add(key)
        per_src[it["source"]] = per_src.get(it["source"], 0) + 1
        items.append({"source": it["source"], "text": it["text"], "dt": it["dt"],
                      "time": il_time(it["_dt"]), "link": it["link"]})
        if len(items) >= MAX_ITEMS:
            break

    payload = {"items": items,
               "_meta": {"updatedAt": israel_stamp(), "source": "X via Telegram/Nitter"}}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] {len(items)} פריטים ({ok}/{len(SOURCES)} מקורות חיים)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
