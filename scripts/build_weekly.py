#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_weekly.py — סיכום השבוע → data/weekly.json + הודעה לערוץ הטלגרם.

נבנה מנתונים שכבר קיימים בריפו: history.json (ציונים יומיים, S&P, VIX, והכותרת
של כל יום — נשמרת שם מאז 11.9.2026), ו-indices.json (ימי מכירה רחבה). בלי LLM,
בלי מקור חדש: רשימת חמש הכותרות + מסלול המד + השינוי השבועי — עובדות, לא פרוזה.

מתי: אירוע, לא שעון. הסקריפט רץ בכל ריצת Action ובודק אם היום האחרון ב-history
הוא יום שישי שעוד לא סוכם. סגירת שישי נקלטת רק כשאיציק דוחף את הדשבורד (בד"כ
שבת/ראשון בבוקר) — ואז, תוך 15 דקות, הסיכום נבנה ונשלח. שעון קבוע היה מפספס
בדיוק כמו שהרוטינה של הכותרת פספסה שבוע שלם (ראו CLAUDE.md).

באתר: כרטיס בבית מרגע הבנייה ועד יום שני בבוקר (renderWeekly ב-app.js מסתיר
אותו לבד אחר-כך; הקובץ נשאר לארכיון).

    python build_weekly.py --force   → בונה את השבוע השלם האחרון גם אם כבר סוכם
                                       (ולא שולח לטלגרם בלי סודות)
עמידות: כל כשל משאיר את weekly.json הקיים ויוצא 0.
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify_telegram import load, send

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "weekly.json")
STATE = os.path.join(DATA, "_weekly_state.json")
SITE = "https://nditzik.github.io/nidam-markets/"
DOW = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]   # datetime.weekday


def il_stamp():
    now = datetime.now(timezone.utc)
    return (now + timedelta(hours=3 if 4 <= now.month <= 10 else 2)).strftime("%d/%m/%Y %H:%M")


def word(v):
    return "חיובי" if v >= 66 else "זהיר" if v >= 45 else "הגנתי"


def build(days, sell_dates, friday):
    """שבוע המסחר שמסתיים ביום שישי הנתון (ISO) — מתוך רשומות history."""
    fri = datetime.strptime(friday, "%Y-%m-%d").date()
    mon = fri - timedelta(days=4)
    week = [d for d in days if mon.isoformat() <= d["date"] <= friday]
    before = [d for d in days if d["date"] < mon.isoformat()]
    if not week:
        return None
    prev = before[-1] if before else None
    out_days, last_spx = [], (prev or {}).get("spx")
    for d in week:
        chg = None
        if d.get("spx") is not None and last_spx:
            chg = round((d["spx"] / last_spx - 1) * 100, 2)
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        out_days.append({
            "date": d["date"], "dow": DOW[dt.weekday()], "label": f"{dt.day}.{dt.month}",
            "combined": d.get("combined"), "spx": d.get("spx"), "chg": chg,
            "headline": d.get("headline") or "", "sell": d["date"] in sell_dates,
        })
        if d.get("spx") is not None:
            last_spx = d["spx"]
    first, last = week[0], week[-1]
    spx_pct = None
    base = (prev or {}).get("spx") or first.get("spx")
    if base and last.get("spx"):
        spx_pct = round((last["spx"] / base - 1) * 100, 2)
    summary = {
        "combStart": (prev or first).get("combined"), "combEnd": last.get("combined"),
        "spxPct": spx_pct, "vixStart": (prev or first).get("vix"), "vixEnd": last.get("vix"),
        "sellDays": sum(1 for d in out_days if d["sell"]),
    }
    return {
        "weekOf": friday, "from": mon.isoformat(), "to": friday,
        "label": f"{mon.day}–{fri.day}.{fri.month}" if mon.month == fri.month else f"{mon.day}.{mon.month}–{fri.day}.{fri.month}",
        "days": out_days, "summary": summary,
        "_meta": {"updatedAt": il_stamp(), "source": "build_weekly"},
    }


def compose_tg(w):
    s = w["summary"]
    pct = lambda v: "—" if v is None else f"{v:+.2f}%"
    lines = [f"🗓 <b>סיכום השבוע · {w['label']}</b>",
             f"S&amp;P 500 {pct(s['spxPct'])} · מד השוק {s['combStart']}→{s['combEnd']} ({word(s['combEnd'] or 0)})"
             + (" · יום מכירה רחבה אחד" if s["sellDays"] == 1 else f" · {s['sellDays']} ימי מכירה רחבה" if s["sellDays"] else ""), ""]
    for d in w["days"]:
        head = f"<b>{d['dow']}</b> {d['label']} · {pct(d['chg'])} · מד {d['combined']}" + (" ▲" if d["sell"] else "")
        lines.append(head)
        if d["headline"]:
            lines.append(f"   {d['headline']}")
    lines += ["", f'🔗 <a href="{SITE}">The Daily Edge</a>']
    return "\n".join(lines)


def main():
    force = "--force" in sys.argv
    hist = load(os.path.join(DATA, "history.json")) or {}
    days = sorted(hist.get("days", []), key=lambda d: d["date"])
    if not days:
        print("[skip] אין history.json.")
        return 0
    # השבוע השלם האחרון: היום האחרון במאגר חייב להיות יום שישי
    last = days[-1]["date"]
    last_dt = datetime.strptime(last, "%Y-%m-%d")
    if last_dt.weekday() != 4:
        if not force:
            print(f"[skip] היום האחרון במאגר ({last}) אינו יום שישי — השבוע עוד לא הסתיים.")
            return 0
        fridays = [d["date"] for d in days if datetime.strptime(d["date"], "%Y-%m-%d").weekday() == 4]
        if not fridays:
            print("[skip] אין אף יום שישי במאגר.")
            return 0
        last = fridays[-1]
    st = load(STATE) or {}
    if st.get("weekOf") == last and not force:
        print(f"[ok] השבוע שמסתיים ב-{last} כבר סוכם.")
        return 0

    idx = load(os.path.join(DATA, "indices.json")) or {}
    sell = {s["date"] for s in ((idx.get("riskOff") or {}).get("sellDaysMap") or []) if s.get("isSell")}
    w = build(days, sell, last)
    if not w:
        print("[skip] אין רשומות לשבוע הזה.")
        return 0
    # הסיכום המילולי נכתב אחר-כך ע"י רוטינת nidam-weekly-narrative ישירות לתוך
    # weekly.json — בנייה מחדש של אותו שבוע (למשל --force) לא תמחק אותו
    prev_w = load(OUT) or {}
    if prev_w.get("weekOf") == w["weekOf"] and prev_w.get("narrative"):
        w["narrative"] = prev_w["narrative"]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(w, f, ensure_ascii=False, indent=1)
    print(f"[done] סיכום השבוע {w['label']} נכתב · S&P {w['summary']['spxPct']}% · מד {w['summary']['combStart']}→{w['summary']['combEnd']}")

    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHANNEL")
    if token and chat:
        try:
            send(token, chat, compose_tg(w))
            print("[ok] נשלח לערוץ.")
        except Exception as e:
            print(f"[warn] שליחת טלגרם נכשלה: {e}")
    else:
        print("[info] אין סודות טלגרם — לא נשלח.")
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump({"weekOf": last, "at": il_stamp()}, f, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
