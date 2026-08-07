#!/usr/bin/env python3
"""
briefing_archive.py — ארכיון יומי לתדריכים ולסקירות הבוקר (משותף ל-fetch_gmail
ו-fetch_barchart).

כל מייל נשמר גם כקובץ מתוארך:
    data/briefings/archive/YYYY-MM-DD-<kind>.html    (kind: morning/afternoon/review)
והאינדקס data/briefing_archive.json מחזיק לכל יום את מה שקיים:
    {"days": {"2026-08-07": {"morning": {"file","subject","time"}, ...}}}

שמירה ל-30 הימים האחרונים; קבצים של ימים שנחתכו נמחקים.
"""
import json
import os
from datetime import timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH_DIR = os.path.join(ROOT, "data", "briefings", "archive")
ARCH_REL = "data/briefings/archive/"
INDEX = os.path.join(ROOT, "data", "briefing_archive.json")
KEEP_DAYS = 30


def load_index():
    if os.path.exists(INDEX):
        try:
            with open(INDEX, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"days": {}}


def has_kind(idx, kind):
    return any(kind in v for v in (idx.get("days") or {}).values())


def il_parts(date_dt):
    """(iso-date, 'HH:MM') בשעון ישראל עבור תאריך המייל."""
    if not date_dt:
        return None, ""
    off = 3 if 4 <= date_dt.astimezone(timezone.utc).month <= 10 else 2
    il = date_dt.astimezone(timezone(timedelta(hours=off)))
    return il.strftime("%Y-%m-%d"), il.strftime("%H:%M")


def archive_email(idx, kind, subject, date_dt, html_body):
    """שומר עותק מתוארך + רושם באינדקס. מחזיר True אם משהו השתנה."""
    iso, hhmm = il_parts(date_dt)
    if not iso or not html_body:
        return False
    fname = "%s-%s.html" % (iso, kind)
    path = os.path.join(ARCH_DIR, fname)
    changed = False
    if not os.path.exists(path):
        os.makedirs(ARCH_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_body)
        changed = True
    entry = {"file": ARCH_REL + fname, "subject": subject, "time": hhmm}
    day = idx.setdefault("days", {}).setdefault(iso, {})
    if day.get(kind) != entry:
        day[kind] = entry
        changed = True
    return changed


def prune_and_save(idx, stamp):
    """חיתוך ל-KEEP_DAYS הימים האחרונים + מחיקת קבצים שנחתכו + שמירת האינדקס."""
    days = idx.get("days") or {}
    keep = sorted(days.keys(), reverse=True)[:KEEP_DAYS]
    dropped = [d for d in days if d not in keep]
    for d in dropped:
        for entry in days[d].values():
            p = os.path.join(ROOT, entry.get("file", "").replace("/", os.sep))
            if p.startswith(ARCH_DIR) and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        del days[d]
    idx["_meta"] = {"updatedAt": stamp, "source": "gmail archive", "keepDays": KEEP_DAYS}
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    if dropped:
        print("[archive] נחתכו %d ימים ישנים" % len(dropped))
