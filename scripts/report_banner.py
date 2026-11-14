#!/usr/bin/env python3
"""
report_banner.py — הבהרה אחידה בראש כל דוח HTML עצמאי שהאתר מפרסם (14.11.2026).

דוח נפתח גם בקישור ישיר (data/trades/…, data/sectors/…, data/reports/…), מחוץ למעטפת האתר, ולכן ההבהרה
חייבת לשבת בתוך הקובץ עצמו: מידע כללי, אין רישיון ייעוץ, לא מותאם אישית, סיכון, קישור לתנאים המלאים,
והמועד שאליו הדוח מתייחס. הסגנון inline כדי שיעבוד בכל דוח (גם ידני, גם בהדפסה, בהיר וכהה).

inject(html, iso, legacy=False) — אידמפוטנטי: בלוק קיים מוחלף, כך שעדכון נוסח מתפשט לכל הקבצים.
legacy=True לדוח שנוסח לפני מעבר האתר לשפת "מערכת מידע" (מוסיף שורת "נוסח ארכיוני").
הרצה ישירה: מעדכן את כל הקבצים הקיימים ב-data/trades, data/sectors, data/reports.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGAL = "https://nditzik.github.io/nidam-markets/legal.html"
CUT = {"trades": "2026-11-13", "sectors": "2026-11-14"}   # מהתאריך הזה הדוח כבר בנוסח החדש (כמו REP_CUT ב-app.js)
BLOCK_RE = re.compile(r"<!--np-disc-->.*?<!--/np-disc-->\s*", re.S)
BODY_RE = re.compile(r"<body\b[^>]*>", re.I)
STYLE = ("direction:rtl;text-align:right;font:13px/1.55 'IBM Plex Sans Hebrew',Arial,sans-serif;color:inherit;"
         "background:rgba(127,127,127,.12);border:1px solid rgba(127,127,127,.4);border-radius:6px;"
         "padding:10px 14px;margin:8px 8px 14px")


def dmy(iso):
    try:
        y, m, d = iso.split("-")
        return "%d.%d.%s" % (int(d), int(m), y)
    except Exception:
        return ""


def banner(iso=None, legacy=False):
    d = dmy(iso or "")
    lines = ['<div style="margin:0"><b>הבהרה.</b> דוח זה מציג מידע וניתוחים כלליים לצורכי מחקר ולימוד. מפעיל האתר אינו בעל רישיון ייעוץ השקעות. '
             'התוכן אינו מותאם לנתוניך ולצרכיך ואינו תחליף לייעוץ השקעות אישי. הנתונים והניתוחים עשויים להיות מעוכבים או שגויים. '
             'השקעה כרוכה בסיכון להפסד. <a href="%s" target="_top" style="color:inherit;text-decoration:underline">הבהרות, סיכונים וגילוי עניין אישי</a></div>' % LEGAL,
             '<div style="margin:4px 0 0">הנתונים והניתוח מתייחסים למועד הפרסום%s ואינם תמונת מצב עדכנית.</div>'
             % ((' (<span dir="ltr">%s</span>)' % d) if d else " המצוין בדוח")]
    if legacy:
        lines.append('<div style="margin:4px 0 0"><b>נוסח ארכיוני.</b> הדוח נכתב לפני 14.11.2026 ומוצג בנוסחו המקורי. ניסוחי מסחר שבו '
                     '(כניסה, סטופ, יעד, החזקה) אינם הוראה או המלצה של האתר.</div>')
    return '<!--np-disc--><div id="np-disc" role="note" style="%s">%s</div><!--/np-disc-->\n' % (STYLE, "".join(lines))


def inject(html, iso=None, legacy=False):
    html = BLOCK_RE.sub("", html)
    b = banner(iso, legacy)
    m = BODY_RE.search(html)
    if m:
        return html[:m.end()] + "\n" + b + html[m.end():]
    return b + html


def is_legacy(kind, iso):
    return bool(iso) and kind in CUT and iso < CUT[kind]


def main():
    n = 0
    for kind in ("trades", "sectors", "reports"):
        d = os.path.join(ROOT, "data", kind)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".html"):
                continue
            m = re.search(r"(\d{4}-\d{2}-\d{2})", name)
            iso = m.group(1) if m else None
            p = os.path.join(d, name)
            with open(p, encoding="utf-8") as f:
                old = f.read()
            new = inject(old, iso, is_legacy(kind, iso))
            if new != old:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(new)
                n += 1
    print("[banner] עודכנו %d קבצים" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
