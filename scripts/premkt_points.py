# -*- coding: utf-8 -*-
"""נקודות לדף הבית מתוך מייל "טרום מסחר" של Barchart (14:00).

points(html) -> עד 3 משפטים קצרים בעברית.
1. מקור מועדף: פרק שכותרתו מכילה "לדף הבית" (HOME_MARK) — תבליטי ה-<ul> הראשון שאחריו.
   זה הפרק שהבוט מתבקש לכתוב (docs/prompts-briefing-home.md).
2. נפילה: תבליטי הכרטיס "מאקרו ופד" (המבנה הקיים מ-11.2026) — בלי רשימות אחוזים של מניות.
בלי תוכן מתאים — רשימה ריקה, והאתר לא מציג את הבלוק.
"""
import html as _html
import re

HOME_MARK = "לדף הבית"
MAX_POINTS = 3
MAX_LEN = 240


def _clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    # Barchart כותב את הסימן אחרי האחוז ("0.5%+"): ירידה — הסימן חוזר לפני המספר,
    # ועלייה בלי סימן ("צפי 0.5%") — פלוס בתוך משפט עברי מתהפך בתצוגה
    s = re.sub(r"(\d[\d.,]*)%\+", r"\1%", s)
    s = re.sub(r"(\d[\d.,]*)%([\-−])", lambda m: "-" + m.group(1) + "%", s)
    s = re.sub(r"-\s*-(?=\d)", "-", s)   # "ירד ב--0.3%" → "ירד ב-0.3%"
    s = re.sub(r"\s+([.,;:])", r"\1", s)
    s = re.sub(r"(?<=[\u05d0-\u05ea])-\s+(?=[+\-−]?\d)", "-", s)   # "ל- +4.3%" → "ל-+4.3%"
    s = re.sub(r"\(\s+", "(", s)
    s = re.sub(r"\s+\)", ")", s)
    return s


def _cut(s):
    if len(s) <= MAX_LEN:
        return s
    head = s[:MAX_LEN]
    for sep in (". ", "; ", " — ", ", "):
        i = head.rfind(sep)
        if i > 90:
            return head[:i].rstrip(" ,;—") + "."
    return head.rsplit(" ", 1)[0] + "…"


def _lis(block):
    m = re.search(r"<ul[^>]*>(.*?)</ul>", block, re.S)
    if not m:
        return []
    out = []
    for li in re.findall(r"<li[^>]*>(.*?)</li>", m.group(1), re.S):
        t = _clean(li)
        if len(t) > 15:
            out.append(_cut(t))
    return out


def points(html):
    if not html:
        return []
    i = html.find(HOME_MARK)
    if i >= 0:
        got = _lis(html[i:i + 6000])
        if got:
            return got[:MAX_POINTS]
    # נפילה: הכרטיס שהתג/הכותרת שלו "מאקרו"
    for m in re.finditer(r"<(span|h2|h3)[^>]*>([^<]*מאקרו[^<]*)</\1>", html):
        got = _lis(html[m.end():m.end() + 6000])
        if got:
            return got[:MAX_POINTS]
    return []


if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else "data/briefings/morning-premkt.html"
    for t in points(open(p, encoding="utf-8").read()):
        print("-", t)
