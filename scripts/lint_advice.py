#!/usr/bin/env python3
"""
lint_advice.py — בדיקה לפני פרסום: מסמן לביקורת ניסוחים שעלולים להיקרא כהמלצת השקעה (14.11.2026).

האתר הוא מערכת מידע, מחקר ולימוד (ראו scripts/prompts/_language.md). הטקסטים נכתבים ברובם על ידי
רוטינות; הסקריפט הזה עובר על מה שמוצג כרגע באתר ומסמן:
  · הוראות קנייה / מכירה / החזקה מטעם האתר
  · הקצאת הון וגודל פוזיציה
  · תוכנית עסקה (כניסה / סטופ / יעד)
  · הבטחות וניסוחים ודאיים על העתיד
  · החלטות מסחר אישיות ("יצאנו", "נכנסנו")

הבדיקה מתחשבת בהקשר ואינה מחליפה מילים: דיווח על קנייה של מנהל, דירוג אנליסט מיוחס, "הכסף הגדול קנה
הגנות" או "המשקיעים מכרו" הם תיאור ולא המלצה, ולכן רק דפוסים של הנחיה מסומנים. היא לא חוסמת פרסום —
התוצאה נכתבת ל-data/advice_lint.json ומוצגת כצ'יפ "בדיקת ניסוח" במחוון הבריאות שבתחתית האתר.

הרצה: python scripts/lint_advice.py            (תמיד קוד יציאה 0)
       python scripts/lint_advice.py --strict   (קוד יציאה 1 כשיש ממצאים — לבדיקה ידנית)
"""
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

from iltime import il_off

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "advice_lint.json")

VERB = r"(?:לקנות|למכור|להיכנס|לצאת|להחזיק|להוסיף|להגדיל|לצמצם|לרכוש|לממש)(?![א-ת])"
# (שם הכלל, ביטוי) — כל כלל מתאר הנחיה, לא דיווח
RULES = [
    ("הוראת פעולה", r"(?<![א-ת])(?:כדאי|מומלץ|עדיף|צריך|חובה|זמן טוב|הזמן|אפשר|לא)\s+(?:\S+\s+)?" + VERB),
    ("הוראת פעולה", r"להחזיק קיים|להוסיף חשיפה|חשיפה חדשה|להדק\s+סטופ|להדק את|לא לרדוף|לחכות לנשימה|לא לפתוח"),
    ("הוראת פעולה", r"(?:^|[.:;—–]\s*)(?:קנה|קנו|מכור|מכרו|החזק|החזיקו)\s+(?:את|ב|עכשיו)"),
    ("גודל פוזיציה", r"פוזיציה קטנה|גודל (?:ה)?פוזיציה|עד\s+\d+\s+פוזיציות|להגדיל פוזיציה|חצי גודל|גודל מלא|שני שליש גודל"),
    ("גודל פוזיציה", r"בשלישים|שליש ראשון|שליש שני נכנס|מוסיפים שליש|מחזיקים (?:שני )?שליש|מחזיקים את ה|לא מגדילים|מגדילים (?:את ה)?(?:פוזיצי|חשיפה|אחזק)"),
    ("תוכנית עסקה", r"סטופ|טריגר כניסה|נקודת (?:ה)?כניסה|מחיר (?:ה)?כניסה|כניסה (?:מעל|אפשרית|איכותית|רק ב)|יציאה בסגירה|נקודת (?:ה)?יציאה|סיכון/סיכוי|אישור מחיר לקנייה"),
    ("תוכנית עסקה", r"(?<![א-ת])[כהלו]?אות (?:ל)?(?:יציאה|כניסה|קנייה|מכירה)|סטופ (?:צמוד|נדרש|אישי)|יוצאים מ|נשארים בחוץ|להתרחק"),
    ("הבטחה / ודאות", r"מקום לרוץ|פוטנציאל (?:עלייה|התאוששות) של"),
    ("הבטחה / ודאות", r"רווח מובטח|בוודאות|בטוח ש(?:ת|י)על|מוכנה לזינוק|כניסה בטוחה|אסור לפספס|הזדמנות (?:קנייה|שאסור)|אין מה להפסיד"),
    ("החלטה אישית", r"יצאנו|נכנסנו|מכרנו|קנינו|הפוזיציה שלנו|אנחנו מחזיקים|התיק שלנו"),
]
RULES = [(n, re.compile(p)) for n, p in RULES]
# הקשרים שבהם התאמה היא דיווח/ייחוס ולא הנחיה — אם הקטע סביב ההתאמה מתאים, מדלגים
ALLOW = re.compile(
    r"לא הוראת|לא המלצ|אינ[הםו] המלצ|ולא הנחיה|אינ[םה] הנחיה|בלי (?:יציאה ב)?סטופ|ללא סטופ|"       # הבהרות ושלילות
    r"דירוג|חוות דעת|אנליסט|Barchart|Buy|Sell|ממליצי|"                                           # ייחוס לצד שלישי
    r"מנהל|מנכ\"ל|דירקטור|בעל מניות|הקרן|המשקיעים|הכסף הגדול|המוסדיים|הפד|הממשל|החברה|ההנהלה|"   # מישהו אחר עשה
    r"קניית הגנות|רכישה עצמית|באיבק"
)


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def walk(x, path, skip=None):
    """מחזיר (path, text) לכל מחרוזת; skip(path) = True → מדלגים."""
    if isinstance(x, str):
        if not (skip and skip(path)):
            yield path, x
    elif isinstance(x, list):
        for i, y in enumerate(x):
            yield from walk(y, "%s[%d]" % (path, i), skip)
    elif isinstance(x, dict):
        for k, y in x.items():
            if str(k).startswith("_") or k in ("correction", "correctedAt"):
                continue
            yield from walk(y, path + "." + str(k), skip)


def latest_dir(base):
    try:
        ds = sorted(d for d in os.listdir(base) if re.match(r"\d{4}-\d{2}-\d{2}$", d))
    except OSError:
        return None
    return ds[-1] if ds else None


def targets():
    """(תווית, אובייקט, פונקציית דילוג) — מה שמוצג כרגע באתר."""
    out = []
    ca = load(os.path.join(DATA, "claude_analysis.json"))
    if ca:
        out.append(("הניתוח היומי", {k: ca.get(k) for k in ("headline", "tldr", "bottomline", "paragraphs", "watchFor", "eventUpdate")}, None))
    wk = load(os.path.join(DATA, "weekly.json"))
    if wk and wk.get("narrative"):
        out.append(("סיכום השבוע", wk["narrative"], None))
    fc = load(os.path.join(DATA, "forecasts.json"))
    if fc and fc.get("current"):
        out.append(("הצפי השבועי", fc["current"], None))
    d = latest_dir(os.path.join(DATA, "rotation"))
    if d:
        nar = load(os.path.join(DATA, "rotation", d, "narrative.json"))
        if nar:   # מ-14.11.2026 גם העמודה הראשונה במאזן נבדקת (תמצית בשפת המודל, לא ציטוט)
            out.append(("דוח הסקטורים %s" % d, nar, None))
    d = latest_dir(os.path.join(DATA, "fourpillars"))
    if d:
        n = load(os.path.join(DATA, "fourpillars", d, "notes.json"))
        if n:
            out.append(("ארבעת העמודים %s" % d, n, None))
    cs = load(os.path.join(DATA, "consensus.json"))
    if cs:
        out.append(("סיכום", {"why": [r.get("why") for r in cs.get("rows", [])]}, None))
    hb = load(os.path.join(DATA, "stock_hub.json"))
    if hb:   # "תמונה מלאה" בחלון המניה (np202): הטקסטים שהסקריפט מרכיב + כותרות "אחרי הדוח"
        out.append(("חלון המניה", {"t": sorted({a.get("t") or "" for o in (hb.get("syms") or {}).values() for a in o.get("app") or []} |
                                               {r.get("review") or "" for o in (hb.get("syms") or {}).values() for r in o.get("rep") or []})}, None))
    st = load(os.path.join(DATA, "story.json"))
    if st and st.get("active"):
        out.append(("הכתבה בבית", {k: st.get(k) for k in ("title", "dek", "paras", "next", "questions")}, None))
    for f, lab in (("earnings_prep_notes.json", "לקראת הדוח"), ("earnings_review_notes.json", "אחרי הדוח")):
        x = load(os.path.join(DATA, f))
        if x:
            out.append((lab, x, None))
    return out


TAG_DROP = re.compile(r"<(script|style)\b.*?</\1>|<!--np-disc-->.*?<!--/np-disc-->|<!--.*?-->", re.S | re.I)
TAG_BLOCK = re.compile(r"</?(?:p|div|li|tr|td|th|h[1-6]|section|header|footer|br|ul|ol|table|summary|details|blockquote)\b[^>]*>", re.I)
HEB = re.compile(r"[\u0590-\u05ff]")


def html_blocks(html):
    """טקסט של דוח HTML מוגמר, מפוצל לבלוקים (פסקה / תא / פריט). בלי סקריפטים, סגנונות וההבהרה שהוזרקה."""
    import html as _h
    t = TAG_BLOCK.sub("\n", TAG_DROP.sub(" ", html))
    t = _h.unescape(re.sub(r"<[^>]+>", "", t))
    out = []
    for line in t.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) >= 8 and HEB.search(line) and not re.match(r"תיקון\s+\d", line):   # שורת תיעוד התיקון מצטטת את מה שהוסר
            out.append(line)
    return out


def html_files():
    """(current, archive) — הדוחות העצמאיים שהאתר מפרסם. current = האחרון בכל סוג (מה שמוצג כברירת מחדל),
    archive = כל השאר + ניתוחי הדוחות הרבעוניים (נגישים בקישור ישיר)."""
    cur, arch = [], []
    for kind, lab in (("trades", "ארבעת העמודים"), ("sectors", "דוח הסקטורים")):
        d = os.path.join(DATA, kind)
        try:
            names = sorted(n for n in os.listdir(d) if n.endswith(".html"))
        except OSError:
            names = []
        for n in names[:-1]:
            arch.append((lab, os.path.join(d, n)))
        if names:
            cur.append((lab + " (HTML) " + names[-1][-15:-5], os.path.join(d, names[-1])))
    d = os.path.join(DATA, "reports")
    try:
        for n in sorted(os.listdir(d)):
            if n.endswith(".html"):
                arch.append(("ניתוח דוחות", os.path.join(d, n)))
    except OSError:
        pass
    return cur, arch


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def scan(text):
    hits = []
    for name, rx in RULES:
        for m in rx.finditer(text):
            ctx = text[max(0, m.start() - 45): m.end() + 30]
            if ALLOW.search(ctx):
                continue
            hits.append((name, m.group(0).strip(), text[max(0, m.start() - 60): m.end() + 60].strip()))
    return hits


def main(argv=None):
    argv = argv or sys.argv
    items, checked = [], 0
    for label, obj, skip in targets():
        for path, text in walk(obj, "", skip):
            checked += 1
            seen = set()
            for name, term, snip in scan(re.sub(r"<[^>]+>", "", text)):
                if (name, term) in seen:
                    continue
                seen.add((name, term))
                items.append({"where": label, "path": path, "rule": name, "term": term, "text": snip})
    # הדוחות המוגמרים (HTML) כפי שהם מתפרסמים — כולל טקסט התבנית של הסקריפט שבונה אותם
    cur, arch = html_files()
    for label, path in cur:
        seen = set()
        for blk in html_blocks(read(path)):
            checked += 1
            for name, term, snip in scan(blk):
                if (name, term) in seen:
                    continue
                seen.add((name, term))
                items.append({"where": label, "path": os.path.relpath(path, ROOT), "rule": name, "term": term, "text": snip})
    # הארכיון הציבורי: סופרים, לא מפרטים (דוחות בנוסח ישן מסומנים "נוסח ארכיוני" בתוך הקובץ)
    a_files, a_flag, a_hits, a_blocks, a_by = 0, 0, 0, 0, {}
    for label, path in arch:
        a_files += 1
        h = 0
        for blk in html_blocks(read(path)):
            a_blocks += 1
            h += len(scan(blk))
        if h:
            a_flag += 1
            a_hits += h
            a_by[label] = a_by.get(label, 0) + 1
    now = datetime.now(timezone.utc)
    il = now + timedelta(hours=il_off(now))
    scope = {"checked": checked, "archiveFiles": a_files, "archiveBlocks": a_blocks,
             "includes": ["הניתוח היומי והעדכונים", "סיכום השבוע והצפי", "הערות ארבעת העמודים ודוח הסקטורים", "סיכום הסריקות",
                          "לקראת הדוח / אחרי הדוח", "הכתבה בבית", "קובצי ה-HTML של הדוח העדכני בכל סוג", "ארכיון הדוחות הציבורי (ספירה)"],
             "excludes": ["חלון הניתוח הטכני (נבנה בדפדפן)", "תדרוכי הבוקר ו-Barchart (תוכן צד שלישי)", "הודעות הטלגרם", "טקסטים קבועים של האתר"],
             "note": "בדיקת ניסוח אוטומטית לפי דפוסים — אינה בדיקה משפטית."}
    out = {"n": len(items), "items": items[:60],
           "archive": {"files": a_files, "flagged": a_flag, "hits": a_hits, "byKind": a_by},
           "scope": scope,
           "_meta": {"updatedAt": il.strftime("%d/%m/%Y %H:%M"), "source": "lint_advice", "rules": "scripts/prompts/_language.md"}}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("[lint] נבדקו %d פריטים · %d ניסוחים לביקורת · ארכיון: %d מתוך %d קבצים עם ניסוחי מסחר (%d התאמות) %s"
          % (checked, len(items), a_flag, a_files, a_hits, a_by))
    for it in items[:30]:
        print("  · %s %s — %s: «%s» ← %s" % (it["where"], it["path"], it["rule"], it["term"], it["text"][:110]))
    return 1 if (items and "--strict" in argv) else 0


if __name__ == "__main__":
    sys.exit(main())
