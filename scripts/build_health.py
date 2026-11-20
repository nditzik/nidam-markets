#!/usr/bin/env python3
"""
build_health.py — מייצר data/_health.json: מחוון בריאות לכל מקור נתונים.

רץ אחרון בפייפליין (אחרי כל המשיכות). קורא את חותמת _meta.updatedAt מכל קובץ
נתונים, מחשב "גיל" מול עכשיו, וקובע סטטוס: ok / stale / down / pending.
משמש גם כ-heartbeat (generatedAt מתעדכן בכל ריצה).
"""
import json
import re
import os
from datetime import datetime, timezone, timedelta
from iltime import il_off   # שעון ישראל אמיתי (zoneinfo), ראו iltime.py

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_health.json")

# key, קובץ, כותרת בעברית
SOURCES = [
    ("indices", "indices.json", "מדדים"),
    ("momentum", "momentum.json", "מומנטום"),
    ("morning", "morning.json:.", "Barchart בוקר"),          # ":." = החותמת מ-dateLabel+time של המהדורה עצמה (לא _meta, שמתרענן בכל ריצת IMAP)
    ("premkt", "morning.json:premkt", "Barchart טרום מסחר"),   # מקונן: אותו דבר על d.premkt
    ("briefing", "briefing.json", "תדרוך משקיעים"),
    ("candidates", "candidates.json", "סריקת תיקון"),
]

# ספי טריות (שעות) — סובלני לסופ"ש/לילה
OK_H = 30
STALE_H = 96


def israel_now():
    now = datetime.now(timezone.utc)
    off = il_off(now)
    return now + timedelta(hours=off)


def norm_day(label):
    """dateLabel של מהדורה → "DD/MM/YYYY". 20.11.2026: נושא דוח Barchart הוא "דוח Barchart יומי — 32 הודעות — 20.11.2026",
    ו-date_label לוקח את מה שאחרי המקף הראשון → "32 הודעות — 20.11.2026". מאז ~6.11 "Barchart בוקר" הוצג "לא הגיע"/down
    בכל יום למרות שהמייל הגיע (אזעקת שווא)."""
    m = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", str(label or ""))
    return "%02d/%02d/%s" % (int(m.group(1)), int(m.group(2)), m.group(3)) if m else label


def parse_stamp(s):
    try:
        return datetime.strptime(s, "%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return None


def _load(fname):
    path = os.path.join(DATA, fname)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _meta_today(d, today_str):
    """(arrived_today, time_str) מתוך _meta.updatedAt של הקובץ."""
    stamp = (d.get("_meta") or {}).get("updatedAt") if isinstance(d, dict) else None
    if not stamp or " " not in stamp:
        return False, None
    dpart, tpart = stamp.split(" ", 1)
    return dpart == today_str, tpart


def today_updates(today_str):
    """רשימת 'מה חדש היום' לסרגל דף הבית."""
    items = []

    b = _load("briefing.json")
    if isinstance(b, dict):
        for slot, label in (("morning", "תדרוך בוקר"), ("afternoon", "תדרוך אחה\"צ")):
            s = b.get(slot)
            if isinstance(s, dict):
                items.append({"label": label, "tab": "briefing",
                              "time": s.get("time"),
                              "arrived": s.get("dateLabel") == today_str})

    # 28.9.2026: "הגיע" לפי dateLabel של המהדורה (כמו התדרוך), לא לפי _meta.updatedAt —
    # החותמת מתרעננת בכל ריצת IMAP (גם בלי מייל חדש), אז Barchart הוצג תמיד כ"הגיע".
    # premkt ("טרום מסחר", ~14:00–14:50) נוסף כפריט משלו כדי לראות בבית אם הגיע היום.
    m = _load("morning.json")
    if isinstance(m, dict) and m.get("_status") != "pending":
        items.append({"label": "Barchart בוקר", "tab": "morning",
                      "time": m.get("time"), "arrived": norm_day(m.get("dateLabel")) == today_str})
        pk = m.get("premkt")
        if isinstance(pk, dict):
            items.append({"label": "Barchart טרום מסחר", "tab": "morning",
                          "time": pk.get("time"), "arrived": norm_day(pk.get("dateLabel")) == today_str})

    for fname, label, tab in (("indices.json", "מדדים", "indices"),
                              ("momentum.json", "מומנטום", "momentum"),
                              ("candidates.json", "סריקת תיקון", "candidates")):
        d = _load(fname)
        if isinstance(d, dict) and d.get("_status") != "pending":
            arrived, t = _meta_today(d, today_str)
            items.append({"label": label, "tab": tab, "time": t, "arrived": arrived})

    # שהגיעו קודם (לפי שעה), הממתינים בסוף
    items.sort(key=lambda it: (0, it.get("time") or "") if it.get("arrived") else (1, ""))
    return items


def advice_detail(lint, n, first):
    """ניסוח מדויק לצ'יפ "בדיקת ניסוח" (14.11.2026): מה נבדק, מתי, מה נמצא, מה לא נכלל — לא הודעה גורפת."""
    sc = lint.get("scope") or {}
    ar = lint.get("archive") or {}
    when = (lint.get("_meta") or {}).get("updatedAt") or ""
    parts = ["בדיקה אוטומטית של ניסוח (לא בדיקה משפטית)",
             "נבדקו %s פריטים ב-%s" % (sc.get("checked", "?"), when),
             ("נמצאו %d ניסוחים לבדיקה: %s" % (n, first)) if n else "בתוכן המוצג כרגע לא נמצאו ניסוחים לבדיקה"]
    if ar.get("files"):
        parts.append("בארכיון הציבורי %d מתוך %d קבצים כוללים ניסוחי מסחר ישנים (מוצגים בנוסחם המקורי, מסומנים 'נוסח ארכיוני')" % (ar.get("flagged") or 0, ar["files"]) if ar.get("flagged")
                     else "בארכיון הציבורי (%d קבצים) לא נמצאו ניסוחים לבדיקה" % ar["files"])
    if sc.get("excludes"):
        parts.append("לא כולל: " + ", ".join(sc["excludes"]))
    return " · ".join(parts)


def main():
    now = israel_now().replace(tzinfo=None)
    today_str = now.strftime("%d/%m/%Y")
    out = {"generatedAt": now.strftime("%d/%m/%Y %H:%M"),
           "today": today_updates(today_str), "sources": []}

    for key, fname, label in SOURCES:
        fname, _, nested = fname.partition(":")
        path = os.path.join(DATA, fname)
        entry = {"key": key, "label": label, "updatedAt": None,
                 "ageHours": None, "status": "down", "detail": ""}
        if not os.path.exists(path):
            entry["detail"] = "אין קובץ"
            out["sources"].append(entry)
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            entry["detail"] = "קובץ לא תקין"
            out["sources"].append(entry)
            continue

        if isinstance(d, dict) and d.get("_status") == "pending":
            entry["status"] = "pending"
            entry["detail"] = "טרם חובר"
            out["sources"].append(entry)
            continue

        if nested:   # מהדורת Barchart: החותמת היא מועד המייל עצמו, לא ריצת ה-IMAP
            sub = (d if nested == "." else d.get(nested)) if isinstance(d, dict) else None
            stamp = ("%s %s" % (norm_day(sub.get("dateLabel")), sub.get("time"))) if isinstance(sub, dict) and sub.get("dateLabel") else None
        else:
            stamp = (d.get("_meta") or {}).get("updatedAt") if isinstance(d, dict) else None
        entry["updatedAt"] = stamp
        dt = parse_stamp(stamp)
        if dt is None:
            entry["detail"] = "אין חותמת"
            out["sources"].append(entry)
            continue

        age = (now - dt).total_seconds() / 3600.0
        entry["ageHours"] = round(age, 1)
        entry["status"] = "ok" if age <= OK_H else ("stale" if age <= STALE_H else "down")
        out["sources"].append(entry)
        print(f"[health] {label}: {entry['status']} ({stamp}, {age:.1f}h)")

    # בדיקת הניסוח (lint_advice.py, 14.11.2026): צ'יפ במחוון — ירוק כשאין ממצאים, צהוב כשיש ניסוחים לביקורת
    lint = load(os.path.join(DATA, "advice_lint.json")) if "load" in globals() else None
    if lint is None:
        try:
            with open(os.path.join(DATA, "advice_lint.json"), encoding="utf-8") as lf:
                lint = json.load(lf)
        except Exception:
            lint = None
    if lint is not None:
        n = lint.get("n") or 0
        first = "; ".join("%s: «%s»" % (i.get("where", ""), i.get("term", "")) for i in (lint.get("items") or [])[:3])
        out["sources"].append({"key": "advice", "label": "בדיקת ניסוח", "status": "stale" if n else "ok",   # לפי התוכן הנוכחי בלבד; הארכיון נשאר בנוסחו (החלטת איציק 14.11.2026) ומדווח בפירוט
                               "updatedAt": (lint.get("_meta") or {}).get("updatedAt"),
                               "detail": advice_detail(lint, n, first)})
        out["adviceLint"] = {"n": n, "items": (lint.get("items") or [])[:10], "archive": lint.get("archive"), "scope": lint.get("scope")}

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
