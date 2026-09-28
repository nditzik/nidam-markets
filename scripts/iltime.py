#!/usr/bin/env python3
"""
iltime.py — שעון ישראל אמיתי לכל הסקריפטים (28.9.2026).

עד היום כל סקריפט ניחש: "UTC+3 בחודשים אפריל–אוקטובר, אחרת UTC+2". זה שגוי בשבוע
שבין מעבר השעון לסוף החודש (25–31.10.2026, 27–31.3.2027 וכו') — שבוע בשנה שבו כל
חותמות הזמן, חלונות הטלגרם והשערים זזו בשעה. כאן ההיסט נקרא מלוח אזורי הזמן של
המערכת (zoneinfo, stdlib) ולכן נכון תמיד, כולל שנים הבאות, בלי טיפול ידני.

שימוש: `from iltime import il_off, IL, NY` (sys.path[0] הוא scripts/ כשמריצים `python scripts/x.py`).
  il_off(dt=None) → 2 או 3 (שעות מעל UTC) לרגע הנתון (naive = UTC; ברירת מחדל: עכשיו)
  IL / NY        → אובייקטי אזור-זמן להמרות מלאות (dt.astimezone(IL))
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

IL = ZoneInfo("Asia/Jerusalem")
NY = ZoneInfo("America/New_York")


def il_off(dt=None):
    """ההיסט של שעון ישראל מ-UTC בשעות (2 בחורף, 3 בקיץ) לרגע dt (ברירת מחדל: עכשיו)."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.astimezone(IL).utcoffset().total_seconds() // 3600)
