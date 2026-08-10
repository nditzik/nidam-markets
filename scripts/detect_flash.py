#!/usr/bin/env python3
"""
detect_flash.py — מבזק שוק: זיהוי תנועה מהירה תוך-יומית (ספייק) ב-S&P.

שונה מהתראת התנודה היומית של notify_alerts (סולם 1.5/2.5/3.5% על השינוי היומי,
שנשארת כמו שהיא): כאן נמדדת *מהירות* — שינוי באחוזים בחלון של 30 הדקות
האחרונות, מנתוני דקה של Yahoo. פרה-מרקט (11:00–16:30 שעון ישראל) נמדד על
חוזה ES=F; שעות המסחר (16:30–23:00) על SPY.

בעת טריגר: אוסף "ראיות" ממקורות שכבר נמשכו בריצה הזו — פרסומי מאקרו בחלון
הזמן (econ.json, הייחוס האמין ביותר), ציוצים אחרונים (pulse.json) וכותרות
טריות (news.json) — כותב data/flash.json (פס מבזק באתר, כל הטאבים) ושולח
לערוץ הטלגרם. לא נטען קשר סיבתי — מוצג "מה התפרסם באותן דקות".

הגנות ספאם: מדרגות [0.75, 1.25, 2.0] לכל כיוון פעם ביום, תקרה 4 מבזקים/יום.
state: data/_flash_state.json.
בדיקה: python detect_flash.py --test  → כותב flash.json מדומה (בלי טלגרם).
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify_telegram import send, load

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
STATE = os.path.join(DATA, "_flash_state.json")
OUT = os.path.join(DATA, "flash.json")
SITE = "https://nditzik.github.io/nidam-markets/"
UA = {"User-Agent": "Mozilla/5.0 (compatible; nidam-markets-bot)"}

WINDOW_MIN = 30                 # חלון המדידה בדקות
LADDER = [0.5, 1.25, 2.0]       # % תנועה בתוך החלון (0.75→0.5 לניסיון, 10.8)
MAX_PER_DAY = 4
ECON_WIN_MIN = 75               # מאקרו שפורסם עד 75 דק' לפני הזיהוי
PULSE_WIN_MIN = 100
NEWS_WIN_MIN = 150


def il_offset():
    now = datetime.now(timezone.utc)
    return 3 if 4 <= now.month <= 10 else 2


def il_now():
    return datetime.now(timezone.utc) + timedelta(hours=il_offset())


def session():
    """(סימבול, תווית) לפי שעון ישראל, או None מחוץ לשעות הרלוונטיות."""
    now = il_now()
    if now.weekday() > 4:           # שבת/ראשון (weekday: שני=0)
        return None
    m = now.hour * 60 + now.minute
    if 11 * 60 <= m < 16 * 60 + 30:
        return ("ES=F", "חוזה S&P", "פרה-מרקט")
    if 16 * 60 + 30 <= m < 23 * 60:
        return ("SPY", "S&P 500", "מסחר")
    return None


def yahoo_1m(sym):
    """(timestamps[], closes[]) — נתוני דקה של היום."""
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(sym) + "?range=1d&interval=1m")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    res = d["chart"]["result"][0]
    ts = res.get("timestamp") or []
    closes = (res.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    pairs = [(t, c) for t, c in zip(ts, closes) if c is not None]
    return pairs


def measure(pairs):
    """שינוי-% בחלון 30 הדקות האחרונות. None אם הפיד מיושן/דל."""
    if len(pairs) < 5:
        return None
    now_utc = datetime.now(timezone.utc).timestamp()
    t_now, p_now = pairs[-1]
    if now_utc - t_now > 10 * 60:   # ציטוט אחרון בן 10+ דקות — פיד מיושן
        return None
    cutoff = t_now - WINDOW_MIN * 60
    prev = None
    for t, p in pairs:
        if t <= cutoff:
            prev = (t, p)
        else:
            break
    if not prev or t_now - prev[0] > (WINDOW_MIN + 20) * 60:
        return None
    pct = (p_now / prev[1] - 1) * 100
    return {"pct": round(pct, 2), "price": round(p_now, 2)}


def parse_iso(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def gather_evidence():
    now = datetime.now(timezone.utc)
    ev = {"econ": [], "pulse": [], "news": []}
    econ = load(os.path.join(DATA, "econ.json")) or {}
    for e in econ.get("events", []):
        if e.get("actual") is None:
            continue
        dt = parse_iso(e.get("date"))
        if not dt:
            continue
        dt = dt.replace(tzinfo=timezone.utc)   # econ.date נכתב כ-UTC נאיבי
        if timedelta(0) <= now - dt <= timedelta(minutes=ECON_WIN_MIN):
            ev["econ"].append({
                "he": e.get("he"), "ilTime": e.get("ilTime"),
                "actual": e.get("actual"), "forecast": e.get("forecast"),
                "surprise": e.get("surprise"),
            })
    pulse = load(os.path.join(DATA, "pulse.json")) or {}
    for it in pulse.get("items", []):
        dt = parse_iso(it.get("dt"))
        if dt and now - dt <= timedelta(minutes=PULSE_WIN_MIN):
            ev["pulse"].append({"text": it.get("text", "")[:180],
                                "source": it.get("source"), "time": it.get("time"),
                                "link": it.get("link")})
        if len(ev["pulse"]) >= 4:
            break
    news = load(os.path.join(DATA, "news.json")) or {}
    for it in news.get("news", []):
        dt = parse_iso(it.get("dt"))
        if dt and now - dt <= timedelta(minutes=NEWS_WIN_MIN):
            ev["news"].append({"title": it.get("titleEn") or it.get("title"),
                               "source": it.get("source"), "time": it.get("time"),
                               "link": it.get("link")})
        if len(ev["news"]) >= 3:
            break
    return ev


def compose_tg(flash):
    arrow = "📉 ירידה" if flash["pct"] < 0 else "📈 עלייה"
    lines = [f"⚡ <b>תנועה חדה בשוק</b> — {arrow} של {abs(flash['pct']):.1f}% "
             f"ב-{WINDOW_MIN} דקות ({flash['label']}, {flash['session']})"]
    ev = flash.get("evidence", {})
    if ev.get("econ"):
        lines.append("")
        lines.append("📊 <b>פרסומי מאקרו בחלון הזמן</b> (הגורם הסביר):")
        for e in ev["econ"]:
            lines.append(f"▸ {e['he']}: בפועל {e['actual']} מול צפי {e['forecast']} ({e['ilTime']})")
    if ev.get("pulse"):
        lines.append("")
        lines.append("💬 <b>מהרשת בדקות האחרונות</b>:")
        for p in ev["pulse"][:3]:
            lines.append(f"▸ {p['text'][:120]} ({p['source']} · {p['time']})")
    if not ev.get("econ") and not ev.get("pulse"):
        lines.append("לא אותר פרסום בולט בחלון הזמן — ייתכן מהלך טכני.")
    lines.append("")
    lines.append(f'🔗 <a href="{SITE}">The Daily Edge</a>')
    return "\n".join(lines)


def write_flash(flash):
    flash["_meta"] = {"updatedAt": il_now().strftime("%d/%m/%Y %H:%M"), "source": "detect_flash"}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(flash, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT}")


def main():
    test = "--test" in sys.argv
    ses = session()
    if test and not ses:
        ses = ("SPY", "S&P 500", "מסחר")
    if not ses:
        print("[skip] מחוץ לשעות פרה-מרקט/מסחר.")
        return 0
    sym, label, ses_name = ses

    if test:
        m = {"pct": -1.12, "price": 775.31}
    else:
        try:
            m = measure(yahoo_1m(sym))
        except Exception as e:
            print(f"[warn] משיכת נתוני דקה נכשלה: {e}")
            return 0
        if not m:
            print("[skip] אין מדידה טרייה.")
            return 0

    pct = m["pct"]
    iln = il_now()
    day = iln.strftime("%Y-%m-%d")
    st = load(STATE) or {}
    if st.get("day") != day:
        st = {"day": day, "fired": {"up": [], "down": []}, "count": 0}
    dirn = "down" if pct < 0 else "up"

    hit = None
    for step in LADDER:
        if abs(pct) >= step and step not in st["fired"][dirn]:
            hit = step
    if test:
        hit = hit or LADDER[0]
    if not hit:
        print(f"[ok] {label}: {pct:+.2f}% ב-{WINDOW_MIN} דק' — מתחת לסף/כבר דווח.")
        return 0
    if st["count"] >= MAX_PER_DAY and not test:
        print("[skip] תקרת מבזקים יומית.")
        return 0

    flash = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "date": iln.strftime("%d/%m/%Y"), "time": iln.strftime("%H:%M"),
        "dir": dirn, "pct": pct, "windowMin": WINDOW_MIN, "level": hit,
        "symbol": sym, "label": label, "session": ses_name, "price": m["price"],
        "evidence": gather_evidence(),
    }
    write_flash(flash)

    if not test:
        st["fired"][dirn].append(hit)
        st["count"] += 1
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False)
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat = os.environ.get("TELEGRAM_CHANNEL")
        if token and chat:
            try:
                send(token, chat, compose_tg(flash))
                print("[ok] נשלח מבזק לערוץ.")
            except Exception as e:
                print(f"[warn] שליחת טלגרם נכשלה: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
