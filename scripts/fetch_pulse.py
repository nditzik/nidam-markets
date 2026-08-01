#!/usr/bin/env python3
"""
fetch_pulse.py — "בזק מהרשת": כותרות-בזק מחשבונות X פיננסיים אל data/pulse.json.

צינורות (נבדקו 01/08/2026):
  • שיקופי טלגרם רשמיים (t.me/s/<slug> — HTML ציבורי, בלי API):
      The Kobeissi Letter, Walter Bloomberg, FinancialJuice
  • Nitter RSS (nitter.net, גיבוי xcancel.com) לחשבונות בלי שיקוף:
      @wallstengine, @LiveSquawk

סינון: בלי ריטוויטים/תגובות, בלי הודעות-מדיה ריקות, בלי כפילויות, חלון 48 שעות.
עמידות: מקור שנפל משתמש בפריטים האחרונים שנתפסו ממנו (מ-pulse.json הקודם).
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
    ("@wallstengine", "nitter", "wallstengine"),
    ("@LiveSquawk", "nitter", "LiveSquawk"),
]
NITTER_HOSTS = ["nitter.net", "xcancel.com"]

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


def keep(text):
    if not text or len(text) < 25:
        return False
    if text.startswith(("RT by", "R to")):       # ריטוויטים/תגובות (Nitter)
        return False
    if re.match(r"^(Live stream|Pinned|Forwarded)", text, re.I):
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
        key = re.sub(r"\W+", "", it["text"].lower())[:80]
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
