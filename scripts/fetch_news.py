#!/usr/bin/env python3
"""
fetch_news.py — מושך כותרות שוק ההון מ-RSS, מתרגם לעברית ובונה את data/news.json.

מקורות: CNBC Markets + MarketWatch (RSS ציבורי, בלי מפתח API).
תרגום: MyMemory (ראשי) → Google (גיבוי) → אם שניהם נכשלו, נשארת הכותרת באנגלית.

מטמון (data/_news_cache.json): כל כותרת מתורגמת פעם אחת בלבד. ברוב הריצות
יש 0-2 כותרות חדשות בלבד, כך שאנחנו הרבה מתחת למכסה החינמית וגם מהירים.

עמידות: כל כשל משאיר את news.json הקיים.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(ROOT, "data", "news.json")
CACHE_JSON = os.path.join(ROOT, "data", "_news_cache.json")

# סדר = עדיפות בסבב (הראשונים מקבלים יותר מקומות). Nasdaq הוסר (timeout כרוני),
# WSJ/MarketWatch נבדקו ונמצאו קפואים על 2025. GoogleNews = שער ל-Reuters/NYT/BBC.
FEEDS = [
    ("Bloomberg", "https://feeds.bloomberg.com/markets/news.rss"),
    ("CNBC", "https://www.cnbc.com/id/20910258/device/rss/rss.html"),        # Markets
    ("CNBC", "https://www.cnbc.com/id/10000664/device/rss/rss.html"),        # Economy/Finance
    ("GoogleNews", "https://news.google.com/rss/search?q=stock%20market%20when:1d&hl=en-US&gl=US&ceid=US:en"),
    ("Investing", "https://www.investing.com/rss/news_25.rss"),              # גיבוי — אחרון בסבב
]

# מסננים: טורי ייעוץ אישי + דוחות סגירה של בורסות משניות (דנמרק/טורקיה וכו')
SKIP_RE = re.compile(
    r"\b(I'm|I am|my (wife|husband|son|daughter|mother|father|friend|boss)|"
    r"should I|can I|dear |my \d{2}-year|how much should|is it (ok|fine)|"
    r"suze orman|my portfolio|advice|"
    r"stocks (higher|lower|mixed) at close)\b", re.I)

MAX_ITEMS = 6            # כמה כותרות להציג
MAX_NEW_TRANSLATIONS = 8  # תקרת תרגומים חדשים לריצה (הגנה על המכסה)
UA = {"User-Agent": "Mozilla/5.0 (compatible; nidam-markets-bot)"}


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def il_time(dt):
    off = 3 if 4 <= datetime.now(timezone.utc).month <= 10 else 2
    return dt.astimezone(timezone(timedelta(hours=off))).strftime("%H:%M")


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def clean(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    for a, b in (("&apos;", "'"), ("&amp;", "&"), ("&quot;", '"'),
                 ("&#39;", "'"), ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " ")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def parse_feed(name, url):
    out = []
    try:
        root = ET.fromstring(_get(url))
    except Exception as e:
        print(f"[skip] {name}: {e}")
        return out
    for it in root.findall(".//item"):
        title = clean(it.findtext("title"))
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate") or ""
        src = name
        if name == "GoogleNews":
            # שם המפרסם האמיתי (Reuters/NYT/BBC...) יושב בתגית <source>;
            # מסירים את הסיומת " - Publisher" מהכותרת אם קיימת
            src = clean(it.findtext("source")) or "News"
            suffix = " - " + src
            if title.lower().endswith(suffix.lower()):
                title = title[: -len(suffix)].rstrip()
        if not title or not link or SKIP_RE.search(title):
            continue
        try:
            dt = parsedate_to_datetime(pub)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            dt = datetime.now(timezone.utc)
        out.append({"group": name, "source": src, "title_en": title, "link": link, "dt": dt})
    return out


def tr_mymemory(text):
    # de= (כתובת מייל) מרחיב את המכסה החינמית היומית פי ~10 — בלי הרשמה
    url = "https://api.mymemory.translated.net/get?" + urllib.parse.urlencode(
        {"q": text, "langpair": "en|he", "de": "nditzik@gmail.com"})
    d = json.loads(_get(url, timeout=25))
    if d.get("quotaFinished"):
        raise RuntimeError("quota finished")
    t = (d.get("responseData") or {}).get("translatedText") or ""
    if not t or "MYMEMORY WARNING" in t.upper():
        raise RuntimeError("no translation")
    return t.strip()


def tr_google(text):
    url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(
        {"client": "gtx", "sl": "en", "tl": "iw", "dt": "t", "q": text})
    d = json.loads(_get(url, timeout=25))
    return "".join(seg[0] for seg in d[0]).strip()


def translate(text):
    """מחזיר (טקסט, מנוע|None). גוגל ראשי (איכות טובה יותר), MyMemory גיבוי.
    הערה: GitHub Models נבדק כמועמד LLM ונמצא בתהליך סגירה (HTTP 410 retirement)."""
    for name, fn in (("google", tr_google), ("mymemory", tr_mymemory)):
        try:
            t = fn(text)
            if t and t != text:
                return t, name
        except Exception as e:
            print(f"[tr {name}] {e}")
    return text, None


def main():
    items = []
    for name, url in FEEDS:
        items += parse_feed(name, url)

    if not items:
        print("[warn] לא נמשכו כותרות.")
        return 0 if os.path.exists(OUT_JSON) else 1

    # החדשות ביותר קודם, ללא כפילויות כותרת
    items.sort(key=lambda x: x["dt"], reverse=True)
    seen, uniq = set(), []
    for it in items:
        k = it["title_en"].lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(it)

    # שילוב מקורות (round-robin לפי קבוצת-פיד, בסדר עדיפות קבוע) — שלא ישתלט
    # פיד אחד; כל כותרות GoogleNews נחשבות קבוצה אחת (Reuters/NYT/BBC וכו')
    PRIORITY = ["Bloomberg", "CNBC", "GoogleNews", "Investing"]
    buckets = {}
    for it in uniq:
        buckets.setdefault(it["group"], []).append(it)
    order = [g for g in PRIORITY if g in buckets] + [g for g in buckets if g not in PRIORITY]
    mixed, i = [], 0
    while len(mixed) < MAX_ITEMS and any(buckets.values()):
        for src in order:
            if buckets[src] and len(mixed) < MAX_ITEMS:
                mixed.append(buckets[src].pop(0))
        i += 1
        if i > 20:
            break
    uniq = mixed

    # מטמון v2: {en: {"t": תרגום, "e": מנוע}} — פורמט ישן (מחרוזות) מנוקה ומתורגם מחדש
    cache = {}
    if os.path.exists(CACHE_JSON):
        try:
            with open(CACHE_JSON, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict) and raw.get("_v") == 2:
                cache = raw.get("items", {})
        except Exception:
            cache = {}

    budget = MAX_NEW_TRANSLATIONS
    news = []
    for it in uniq:
        en = it["title_en"]
        hit = cache.get(en)
        he = hit.get("t") if isinstance(hit, dict) else None
        if he is None and budget > 0:
            he, engine = translate(en)
            if engine:
                cache[en] = {"t": he, "e": engine}
                budget -= 1
            else:
                he = None
        news.append({
            "title": he or en,
            "titleEn": en,
            "translated": bool(he) and he != en,
            "source": it["source"],
            "time": il_time(it["dt"]),
            "link": it["link"],
        })

    # שמירת מטמון (מוגבל, שלא יתפח לאורך זמן)
    if len(cache) > 400:
        cache = dict(list(cache.items())[-400:])
    with open(CACHE_JSON, "w", encoding="utf-8") as f:
        json.dump({"_v": 2, "items": cache}, f, ensure_ascii=False, indent=1)

    payload = {"news": news, "_meta": {"updatedAt": israel_stamp(), "source": "Bloomberg · CNBC · Reuters+"}}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    done = sum(1 for n in news if n["translated"])
    print(f"[done] {len(news)} כותרות ({done} בעברית) · מטמון: {len(cache)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
