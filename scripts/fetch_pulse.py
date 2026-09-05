#!/usr/bin/env python3
"""
fetch_pulse.py — "בזק מהרשת": כותרות-בזק מחשבונות X פיננסיים אל data/pulse.json.

צינור פעיל (נבדק 05/09/2026): שיקופי טלגרם רשמיים בלבד
(t.me/s/<slug> — HTML ציבורי, בלי API):
    @KobeissiLetter, Walter Bloomberg, FinancialJuice, @Barchart

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
import html as htmllib
import json
import os
import re
import sys
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

    seen, items, per_src = set(), [], {}
    for it in fresh:
        # 40 ולא 80 (05/09/2026): אותה ידיעה מגיעה משני ערוצים בנוסח מעט שונה —
        # חתימות/סיומות בזנב ("- STATE MEDIA", "@Barchart • Sep", אימוג'י פותח)
        # דחפו את המפתחות ל-80 להיראות שונים, ורק 2 מתוך 6 כפילויות אמיתיות
        # נתפסו. נמדד מול נתונים אמיתיים: ב-40 נתפסות 6/6, עם 0 חסימות-שווא
        # (נבדק גם מול 6 פריטים חדשים-באמת וגם מול כל 78 הפריטים החיים בפיד —
        # הפלט נשאר זהה). קריטי לקראת חיבור הדיג'סט של X, שחופף במכוון
        # ל-4 ערוצי הטלגרם כשכבת גיבוי.
        key = re.sub(r"\W+", "", it["text"].lower())[:40]
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
