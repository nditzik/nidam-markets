#!/usr/bin/env python3
"""
notify_digest.py — תקציר בוקר יומי לערוץ הטלגרם: סיכום יום המסחר הקודם + צפי קדימה.

שער טריות (לפי הגדרת איציק): נשלח רק אחרי שכל הארבעה עודכנו **היום** —
מדדים · מומנטום · מועמדים · תדרוך בוקר. פעם אחת ביום (state), לא בימי ראשון.

סודות: TELEGRAM_BOT_TOKEN + TELEGRAM_CHANNEL (אותם סודות של תזכורות התדריך).
בדיקה: python notify_digest.py --test  (עוקף שערים ושולח מיד)
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify_telegram import send, load  # שימוש חוזר

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
STATE = os.path.join(DATA, "_digest_state.json")
SITE = "https://nditzik.github.io/nidam-markets/"

DOW_HE = ["ב'", "ג'", "ד'", "ה'", "ו'", "שבת", "א'"]  # לפי weekday() של פייתון


def il_now():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return now + timedelta(hours=off)


def updated_today(meta, today_str):
    st = (meta or {}).get("updatedAt") or ""
    return st.startswith(today_str)


def word(v):
    return "חיובי" if v >= 66 else ("זהיר" if v >= 45 else "הגנתי")


def fmt_d(iso):
    p = (iso or "").split("-")
    return f"{int(p[2])}.{int(p[1])}" if len(p) == 3 else iso


def compose(today_str):
    ind = load(os.path.join(DATA, "indices.json")) or {}
    hist = load(os.path.join(DATA, "history.json")) or {}
    mom = load(os.path.join(DATA, "momentum.json")) or {}
    cand = load(os.path.join(DATA, "candidates.json")) or {}
    mov = load(os.path.join(DATA, "movers.json")) or {}
    earn = load(os.path.join(DATA, "earnings.json")) or {}
    brief = load(os.path.join(DATA, "briefing.json")) or {}

    s = ind.get("scores") or {}
    e = ind.get("evidence") or {}
    v = ind.get("verdict") or {}

    lines = []
    now = il_now()
    lines.append("🌅 <b>The Daily Edge — תקציר בוקר</b> · יום %s %d.%d" % (DOW_HE[now.weekday()], now.day, now.month))
    lines.append("")

    # סיכום יום המסחר הקודם
    prev = fmt_d(ind.get("date") or "")
    combined = s.get("combined")
    if combined is not None:
        diff = ""
        days = (hist.get("days") or [])
        if len(days) >= 2 and days[-1].get("combined") is not None and days[-2].get("combined") is not None:
            dv = days[-1]["combined"] - days[-2]["combined"]
            if dv:
                diff = " (%s%d)" % ("▲" if dv > 0 else "▼", abs(dv))
        lines.append("📊 <b>סיכום %s:</b> מד השוק %s · %s%s" % (prev, combined, word(combined), diff))
    # הכותרת הראשית = סיכום-היום המתחלף (כמו באתר); משפט-המשטר הקבוע כגיבוי
    c = ind.get("conclusion") or {}
    if c.get("headline"):
        lines.append("«%s»" % c["headline"])
    elif v.get("headline"):
        lines.append("«%s»" % v["headline"])
    # הסיכום היומי (ai_analysis) — כותרת אנליטית, רק כשתאריכו תואם את יום המסחר
    ai = ind.get("aiSummary") or {}
    ai_ok = ai.get("date") == ind.get("date")
    if ai_ok and ai.get("headline"):
        lines.append(ai["headline"])
    bits = []
    if e.get("spxPrice") is not None:
        bits.append("S&P %s" % format(int(round(e["spxPrice"])), ","))
    if e.get("vix") is not None:
        bits.append("VIX %.1f" % e["vix"])
    if bits:
        lines.append(" · ".join(bits))

    # בלטו אתמול
    g = (mov.get("gainers") or [])[:1]
    l = (mov.get("losers") or [])[:1]
    if g or l:
        parts = []
        if g:
            parts.append("%s %+.0f%%" % (g[0]["symbol"], g[0]["chg"]))
        if l:
            parts.append("%s %+.0f%%" % (l[0]["symbol"], l[0]["chg"]))
        lines.append("🔥 בלטו: " + " · ".join(parts))
    # השורה התחתונה האופרטיבית מהסיכום היומי ("שורה תחתונה: להחזיק קיים · ...")
    if ai_ok:
        bottom = next((p for p in (ai.get("paragraphs") or []) if "שורה תחתונה" in p), None)
        if bottom:
            lines.append("")
            lines.append("💡 " + bottom.replace("שורה תחתונה:", "<b>שורה תחתונה:</b>", 1))
    lines.append("")

    # צפי קדימה
    mom_n = len(mom.get("stocks") or [])
    cand_n = cand.get("count") or len(cand.get("candidates") or [])
    sysbits = []
    if mom_n:
        sysbits.append("מומנטום %d" % mom_n)
    if cand_n:
        sysbits.append("מועמדים %d" % cand_n)
    if sysbits:
        lines.append("🎯 המערכות הבוקר: " + " · ".join(sysbits))

    reps = (earn.get("reporting") or [])[:5]
    if reps:
        lines.append("📅 מדווחות היום: " + ", ".join(r["ticker"] for r in reps) +
                     (" ועוד" if (earn.get("todayCount") or 0) > 5 else ""))
    sched = ((brief.get("morning") or {}).get("schedule") or [])[:3]
    for x in sched:
        lines.append("🕐 %s — %s" % (x.get("time", ""), x.get("text", "")[:60]))

    lines.append("")
    lines.append('🔗 <a href="%s">כל הפרטים באתר</a>' % SITE)
    return "\n".join(lines)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHANNEL")
    if not token or not chat:
        print("[skip] אין סודות טלגרם.")
        return 0

    now = il_now()
    today_str = now.strftime("%d/%m/%Y")
    today_iso = now.strftime("%Y-%m-%d")

    if "--test" in sys.argv:
        send(token, chat, compose(today_str))
        print("[ok] תקציר בדיקה נשלח.")
        return 0

    # נשלח ג'–שבת בלבד: הראשון בשבוע ביום ג' (מסכם את שני), האחרון בשבת (מסכם את שישי)
    if now.weekday() in (6, 0):   # ראשון, שני — דילוג
        print("[skip] אין תקציר בימי ראשון/שני.")
        return 0

    state = load(STATE) or {}
    if state.get("lastSent") == today_iso:
        print("[nochange] תקציר היום כבר נשלח.")
        return 0

    # שער הטריות: ארבעת המקורות עודכנו היום
    ind = load(os.path.join(DATA, "indices.json")) or {}
    mom = load(os.path.join(DATA, "momentum.json")) or {}
    cand = load(os.path.join(DATA, "candidates.json")) or {}
    brief = load(os.path.join(DATA, "briefing.json")) or {}
    gates = {
        "מדדים": updated_today(ind.get("_meta"), today_str),
        "מומנטום": updated_today(mom.get("_meta"), today_str),
        "מועמדים": updated_today(cand.get("_meta"), today_str),
        "תדרוך בוקר": ((brief.get("morning") or {}).get("dateLabel") == today_str),
    }
    missing = [k for k, ok in gates.items() if not ok]
    if missing:
        print("[wait] ממתין לעדכון: " + ", ".join(missing))
        return 0

    try:
        send(token, chat, compose(today_str))
        state["lastSent"] = today_iso
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print("[ok] תקציר הבוקר נשלח לערוץ.")
    except Exception as e:
        print("[warn] שליחה נכשלה: %s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
