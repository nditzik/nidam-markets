#!/usr/bin/env python3
"""
flash_he.py — המשפט הראשי של המבזק ⚡ מהידיעות עצמן, בעברית.

17.11.2026, איציק (על המבזק של 17:46, ‎−0.98% בחצי שעה): "בעברית לא נכתב על תקלת התקשורת,
והמשפט סתמי". עד עכשיו השורה הייתה "באותן דקות דיווחים על: גיאופוליטיקה · הפד והריבית · AI ושבבים" —
שמות נושאים בלבד, בלי מה קרה, ונושא "הפד" הגיע מכתבת ניתוח מאתמול. הידיעות עצמן הוצגו רק באנגלית,
בשורה מקופלת.

מה המודול עושה:
1. clean() — מנקה פריט בזק לפני תרגום: אימוג'י, BREAKING, $טיקרים, "@handle | Source", "- IRNA" בסוף
   (נשמר כ-via), ואצל Walter Bloomberg רק הכותרת באותיות גדולות (הגוף נחתך באמצע). מילים ארוכות
   באותיות גדולות → אותיות קטנות (מתרגם מכונה מתבלבל מ-CAPS); ראשי תיבות קצרים (NSA, FAA) נשארים.
2. add_he() — לכל פריט באנגלית שדה he (תרגום) ו-via; פעם אחת (פריט שכבר יש לו he לא מתורגם שוב).
   התרגום = fetch_news.translate (גוגל, גיבוי MyMemory) — אותו מתרגם של כותרות החדשות באתר.
3. lead() — עד 2 ידיעות למשפט: בלי "הד" של התנועה עצמה ("הדאו יורד 1%"), בלי תוכן שיווקי
   ("3 מניות לקנות"), בלי כתבה שהקישור שלה מיום קודם; ניקוד לפי נושא, מקור בזק, קרבה לרגע המבזק;
   ידיעה אחת לכל נושא.
4. why_line() — "באותן דקות: <ידיעה 1> · <ידיעה 2>". בלי תרגום — נפילה לנושאים, אבל רק מהידיעות
   שעברו את הסינון ועם המקום ("גיאופוליטיקה (איראן)").

מה שהתפרסם באותן דקות — לא בהכרח הסיבה. המשפט לא טוען קשר סיבתי.
"""
import re
from datetime import datetime, timedelta, timezone

from macro_he import topic_of, is_hebrew

EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿‼⁉⭐⬆⬇️]")
PREFIX = re.compile(r"^\s*(?:breaking|just in|alert|update|flash)\s*[:\-–]\s*", re.I)
TICKERS = re.compile(r"^(?:\$[A-Z][A-Z.]{0,6}\s*)+[-–:]?\s*")
TICKERS_ANY = re.compile(r"\s*\$[A-Z][A-Z.]{0,6}\b")
HANDLE = re.compile(r"\s*@\w+\s*\|\s*source\s*$", re.I)
VIA = re.compile(r"\s+[-–]\s+([A-Z][A-Za-z.&']{1,14}(?:\s[A-Z][A-Za-z.&']{1,14}){0,2})\.?\s*$")
ECHO = re.compile(r"\b(?:u\.?s\.? stocks?|stocks?|dow(?: jones)?|s&p(?: 500)?|nasdaq|wall street|futures|equities|indexes|indices)\b"
                  r"[^.]{0,40}?\b(?:fall|falls|fell|drop|drops|dropped|slide|slides|extend|extends|down|lower|tumble|tumbles|plunge|"
                  r"plunges|sink|sinks|gain|gains|rise|rises|rose|up|higher|rally|rallies|jump|jumps|surge|surges|slump|slumps)\b", re.I)
JUNK = re.compile(r"\b(?:\d+ stocks? to (?:buy|watch|sell)|stocks? to (?:buy|watch|sell)|should you buy|time to buy|"
                  r"may move \d|best stocks?|top \d+ stocks?|here's why|here is why)\b", re.I)
URL_DATE = re.compile(r"/(20\d\d)[/-](\d\d)[/-](\d\d)(?:/|-)")
WEIGHT = {"גיאופוליטיקה": 3, "הפד והריבית": 3, "אינפלציה": 3, "נתוני מאקרו": 3, "מכסים וסחר": 3,
          "הבחירות בארה\"ב": 3, "תקלות מחשוב וסייבר": 2, "נפט": 2, "אג\"ח ותשואות": 2, "הבית הלבן": 2,
          "סין": 2, "תקציב הממשל": 2, "AI ושבבים": 1, "דוחות חברות": 1, "מטבעות": 1, "קריפטו": 1}
# מילים קצרות רגילות שיורדות לאותיות קטנות; כל השאר באורך עד 4 אותיות נחשב ראשי תיבות (NSA, FAA, CDC, AMD)
SMALL = set("""A AN THE OF TO IN ON AT BY FOR FROM WITH AND OR BUT NOT NO IS ARE WAS WERE BE BEEN HAS HAD HAVE
WILL CAN MAY SAYS SAID SAY NEW OLD UP DOWN OUT OFF OVER INTO AFTER AS IT ITS I I'M I'VE ME MY WE OUR YOU HE
SHE HIS HER THEY THEM THAT THIS THAT'S WHAT WHEN WHO WHY HOW ALL ANY SOME MORE MOST LESS VERY SO TOO ALSO
JUST NOW THAN THEN SEEN SEE OWN DID DO DOES GET GOT CUT CUTS SET SETS HIT HITS TOP LOW HIGH YEAR DAY WEEK
I'D I'LL WE'VE WE'RE IT'S""".split())
MAX_LEAD = 2
MAX_CHARS = 95


def _alpha(w):
    return sum(c.isalpha() for c in w)


def _is_caps(w):
    letters = [c for c in w if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def clean(text):
    """פריט בזק → (טקסט נקי לתרגום, via או None)."""
    t = EMOJI.sub("", str(text or "")).strip()
    t = HANDLE.sub("", t).strip()
    t = PREFIX.sub("", t).strip()
    t = TICKERS.sub("", t).strip()
    t = TICKERS_ANY.sub("", t).strip()
    words = t.split()
    # Walter Bloomberg: "כותרת באותיות גדולות + גוף רגיל שנחתך…" — רק הכותרת
    run = 0
    while run < len(words) and (_is_caps(words[run]) or _alpha(words[run]) == 0):
        run += 1
    if run >= 3 and run < len(words):
        t = " ".join(words[:run])
    t = t.rstrip("…").rstrip(".").strip()
    via = None
    m = VIA.search(t)
    if m:
        via, t = m.group(1).strip(), t[:m.start()].strip()
    t = re.sub(r"^-+\s*", "", t)
    words = t.split()
    if words and sum(_alpha(w) for w in words if _is_caps(w)) > 0.6 * max(1, sum(_alpha(w) for w in words)):
        words = [w.lower() if _alpha(w) > 4 or re.sub(r"[^A-Za-z'’]", "", w).replace("’", "'").upper() in SMALL else w for w in words]
        t = re.sub(r"\bi\b", "I", " ".join(words))
        t = t[:1].upper() + t[1:]
    return t.strip(" -–:\"'"), via


def _default_tr(text):
    try:
        from fetch_news import translate as tr   # גוגל → MyMemory; רשת רק ב-Action
    except Exception:
        return None
    try:
        out, engine = tr(text)
    except Exception:
        return None
    return out if engine and out and out != text else None


def add_he(ev, tr=None, news_he=None):
    """מוסיף he/via לכל פריט באנגלית בראיות (pulse/news). אידמפוטנטי. news_he = {titleEn: כותרת עברית}."""
    tr = tr or _default_tr
    for p in ev.get("pulse") or []:
        if p.get("he"):
            continue
        if p.get("lang") == "he" or is_hebrew(p.get("text")):
            p["he"] = str(p.get("text") or "")
            continue
        if JUNK.search(str(p.get("text") or "")):
            continue   # תוכן שיווקי — נשאר באנגלית בשורה המקופלת, בלי תרגום
        src, via = clean(p.get("text"))
        if via:
            p["via"] = via
        h = tr(src) if src else None
        if h:
            p["he"] = h.strip()
    for n in ev.get("news") or []:
        if n.get("he"):
            continue
        title = n.get("title") or ""
        if JUNK.search(title):
            continue
        h = (news_he or {}).get(title) or (tr(title) if title else None)
        if h:
            n["he"] = h.strip()
    return ev


def _hm(s):
    try:
        h, m = str(s).split(":")[:2]
        return int(h) * 60 + int(m)
    except Exception:
        return None


def _url_day(link):
    m = URL_DATE.search(str(link or ""))
    return "-".join(m.groups()) if m else None


def lead(ev, at_time=None, at_day=None, after=False):
    """עד MAX_LEAD ידיעות למשפט הראשי. at_time = HH:MM של המבזק; after = במעקב (ידיעות שאחרי המבזק)."""
    at = _hm(at_time) if at_time else None
    cand = []
    for kind, items, key in (("pulse", ev.get("pulse") or [], "text"), ("news", ev.get("news") or [], "title")):
        for i, it in enumerate(items):
            en = str(it.get(key) or "")
            topic, base = topic_of(en)
            if JUNK.search(en) or (ECHO.search(en) and not topic):
                continue
            if kind == "news" and at_day and _url_day(it.get("link")) and _url_day(it.get("link")) < at_day:
                continue   # כתבה מיום קודם שפורסמה מחדש בפיד (CNBC 17.11: ניתוח מ-16.11)
            s = WEIGHT.get(base, 0) + (2 if kind == "pulse" else 1)
            t = _hm(it.get("time"))
            if at is not None and t is not None and abs(t - at) <= 10:
                s += 1
            if re.match(r"^\s*(?:🚨|‼|❗|breaking)", en, re.I):
                s += 1
            if s < 2 or not topic and s < 3:
                continue
            gap = abs(t - at) if (at is not None and t is not None) else 999
            cand.append((-s, gap, kind != "pulse", i, kind, it, base or ("?" + str(i))))
    cand.sort(key=lambda c: c[:4])
    out, seen = [], set()
    for c in cand:
        if c[6] in seen:
            continue
        seen.add(c[6])
        out.append({"kind": c[4], "item": c[5], "topic": c[6]})
        if len(out) >= MAX_LEAD:
            break
    return out


def _short(s, n=MAX_CHARS):
    s = re.sub(r"\s+", " ", str(s)).strip().rstrip(".")
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0]
    return cut.rstrip(",;:–-") + "…"


def why_line(leads, prefix="באותן דקות"):
    """משפט מהידיעות המובילות — רק מה שתורגם. None כשאין."""
    parts = []
    for L in leads:
        it = L["item"]
        h = it.get("he")
        if not h:
            continue
        via = it.get("via")
        lab, base = topic_of(it.get("text") or it.get("title") or "")
        place = lab[lab.index("(") + 1:-1] if base == "גיאופוליטיקה" and lab and "(" in lab else None
        tail = [x for x in (place if place and place not in h else None,
                            f"לפי {via}" if via and via not in h else None) if x]
        parts.append(_short(h) + (" (" + ", ".join(tail) + ")" if tail else ""))
    return (prefix + ": " + " · ".join(parts)) if parts else None


def topics_line(leads, prefix="באותן דקות דיווחים על"):
    labels = []
    for L in leads:
        it = L["item"]
        lab, _ = topic_of(it.get("text") or it.get("title") or "")
        if lab and lab not in labels:
            labels.append(lab)
    return (prefix + ": " + " · ".join(labels)) if labels else None


if __name__ == "__main__":
    for s in ["🚨 NSA'S HIGHLY CLASSIFIED COMMUNICATIONS NETWORK REPORTEDLY DOWN The National Security Agency's (NSA) highly classified internal communications network, known as NSA…",
              "Five to six explosions were heard in the city of Qeshm on Tuesday evening - IRNA",
              "🚨 U.S. STOCKS EXTEND FALL, DOW JONES DOWN 1.00% @walter_bloomberg | Source",
              "🚨 $NVDA -JENSEN HUANG: \"I CREATED PROBLEMS FOR THE BOARD THAT I DEEPLY REGRET. I OWN MY MISTAKES COMPLETELY\" JENSEN HUANG: SINCE MY DEPARTURE, I’VE SEEN AN OUTPOURING OF…",
              "AMD CEO Su: AMD is ensuring it's in the room on chip export control talks. $AMD $NVDA",
              "Japan's PM Takaichi and Trump hold talks in the Philippines - Kyodo."]:
        print(clean(s), "|", topic_of(s), "| echo" if ECHO.search(s) else "")
