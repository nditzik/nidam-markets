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

מעקב (13.11.2026, איציק: "לבצע בדיקה נוספת אחרי חצי שעה לראות אם יש מידע נוסף"):
בכל ריצה, אם המבזק האחרון בן 30–120 דקות ועוד אין לו followup — נמדד המחיר מאז
המבזק (המשיך / התאושש / כמעט לא זז, שפל ושיא בדרך), VIX ואג"ח 10 שנים מ-market.json,
ומה שהתפרסם מאז רגע המבזק (מאקרו, בזק, חדשות — רק פריטים חדשים) → flash.json.followup.
פעם אחת למבזק. רץ גם מחוץ לשעות המסחר (מבזק של 22:50 מקבל מעקב ב-23:20).
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from iltime import il_off   # שעון ישראל אמיתי (zoneinfo), ראו iltime.py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify_telegram import send, load
from macro_he import translate, line_he, topics_he, is_hebrew

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
FOLLOW_MIN, FOLLOW_MAX = 30, 120   # המעקב: מ-30 דק' אחרי המבזק, עד שעתיים (אחר כך כבר לא רלוונטי)


def il_offset():
    now = datetime.now(timezone.utc)
    return il_off(now)


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


def gather_evidence(since=None):
    """since (datetime UTC) = רק פריטים שפורסמו אחרי הרגע הזה — למעקב אחרי המבזק."""
    now = datetime.now(timezone.utc)
    ev = {"econ": [], "pulse": [], "news": []}
    def fresh(dt, win):
        if since is not None:
            return dt > since and dt <= now
        return now - dt <= timedelta(minutes=win)
    econ = load(os.path.join(DATA, "econ.json")) or {}
    for e in econ.get("events", []):
        if e.get("actual") is None:
            continue
        dt = parse_iso(e.get("date"))
        if not dt:
            continue
        dt = dt.replace(tzinfo=timezone.utc)   # econ.date נכתב כ-UTC נאיבי
        if (dt > since and dt <= now) if since is not None else (timedelta(0) <= now - dt <= timedelta(minutes=ECON_WIN_MIN)):
            ev["econ"].append({
                "he": e.get("he"), "ilTime": e.get("ilTime"),
                "actual": e.get("actual"), "forecast": e.get("forecast"),
                "surprise": e.get("surprise"),
            })
    pulse = load(os.path.join(DATA, "pulse.json")) or {}
    for it in pulse.get("items", []):
        dt = parse_iso(it.get("dt"))
        if dt and fresh(dt, PULSE_WIN_MIN):
            ev["pulse"].append({"text": it.get("text", "")[:180],
                                "source": it.get("source"), "time": it.get("time"),
                                "link": it.get("link")})
        if len(ev["pulse"]) >= 4:
            break
    news = load(os.path.join(DATA, "news.json")) or {}
    for it in news.get("news", []):
        dt = parse_iso(it.get("dt"))
        if dt and fresh(dt, NEWS_WIN_MIN):
            ev["news"].append({"title": it.get("titleEn") or it.get("title"),
                               "source": it.get("source"), "time": it.get("time"),
                               "link": it.get("link")})
        if len(ev["news"]) >= 3:
            break
    return ev


# 4.11.2026 (איציק: "ההתראה באנגלית ללא הסבר"): נתוני מאקרו מהבזק מתורגמים לעברית
# (macro_he.py), שאר הפריטים מסומנים he/en, ונבנה משפט "why" לשורה הראשית בעברית.
ECON_FAM = {"nfp": ("תעסוקה", "אבטלה"), "cpi": ("CPI",), "ppi": ("PPI",), "pce": ("PCE",),
            "gdp": ('תמ"ג',), "rate": ("ריבית",)}


def enrich(flash):
    ev = flash.setdefault("evidence", {})
    econ = ev.get("econ") or []
    if "macro" in ev:   # כבר תורגם — רק לבנות מחדש את המשפט (אידמפוטנטי)
        flash["why"] = why_he(econ, ev["macro"], ev.get("topics") or [])
        return flash
    econ_he = " ".join(str(e.get("he") or "") for e in econ)
    macro, rest, seen = [], [], set()
    for p in ev.get("pulse") or []:
        t = translate(p.get("text"))
        if t:
            if t["src"] in seen:
                continue
            seen.add(t["src"])
            if econ and any(k in econ_he for k in ECON_FAM.get(t["fam"], ())):
                continue
            t.update({"time": p.get("time"), "source": p.get("source")})
            macro.append(t)
        else:
            q = dict(p)
            q["lang"] = "he" if is_hebrew(p.get("text")) else "en"
            rest.append(q)
    macro.sort(key=lambda t: 0 if t["us"] else 1)
    ev["macro"] = macro
    ev["pulse"] = rest
    ev["topics"] = topics_he([p.get("text") for p in rest if p.get("lang") == "en"] +
                             [n.get("title") for n in ev.get("news") or []])
    flash["why"] = why_he(econ, macro, ev["topics"])
    return flash


def why_he(econ, macro, topics):
    if econ:
        e = econ[0]
        return f"באותן דקות פורסם {e.get('he')}: {e.get('actual')} מול צפי {e.get('forecast')}"
    us = [t for t in macro if t["us"] and t["known"]]
    if us:
        head = next((t for t in us if not t["he"].startswith("רכיב")), us[0])
        s = f"באותן דקות פורסם {head['he']}: {head['actual']}"
        if head.get("forecast"):
            s += f" מול צפי {head['forecast']}"
        if head.get("verdict"):
            s += f" ({head['verdict']})"
        comp = next((t for t in us if t is not head and t["fam"] == head["fam"] and t["kind"] == "infl" and t.get("verdict")), None)
        if comp:
            s += f"; רכיב המחירים {comp['verdict']}"
        return s
    if topics:
        return "באותן דקות דיווחים על: " + " · ".join(topics)
    return "לא אותר פרסום בולט באותן דקות — ייתכן מהלך טכני"


def followup(now=None, fetch=None):
    """מעקב 30 דק' אחרי המבזק — פעם אחת. True כשנכתב."""
    f = load(OUT)
    if not f or f.get("followup") or not f.get("ts") or f.get("price") in (None, 0):
        return False
    ts = parse_iso(f["ts"])
    now = now or datetime.now(timezone.utc)
    if not ts or not (timedelta(minutes=FOLLOW_MIN) <= now - ts <= timedelta(minutes=FOLLOW_MAX)):
        return False
    try:
        pairs = (fetch or yahoo_1m)(f.get("symbol") or "SPY")
    except Exception as e:
        print(f"[warn] מעקב מבזק: משיכת נתוני דקה נכשלה: {e}")
        return False
    after = [(t, p) for t, p in pairs if t >= ts.timestamp() - 60]
    if len(after) < 3:
        return False
    last = after[-1][1]
    lo, hi = min(p for _, p in after), max(p for _, p in after)
    base = float(f["price"])
    since_pct = round((last / base - 1) * 100, 2)
    mins = int((now - ts).total_seconds() // 60)
    down = f.get("pct", 0) < 0
    if abs(since_pct) < 0.15:
        move = "כמעט לא זז מאז"
    elif (since_pct < 0) == down:
        move = ("המשיך לרדת" if down else "המשיך לעלות") + f" עוד {abs(since_pct):.2f}%"
    else:
        move = ("התאושש" if down else "החזיר") + f" {abs(since_pct):.2f}%"
    ev = gather_evidence(since=ts)
    tmp = enrich({"evidence": ev})
    # במעקב החדשות קודמות לבזק (כותרת כמו "מחירי הסיטונאות עלו 6.5%" חשובה מ"הפד סיים לדבר")
    tmp["evidence"]["topics"] = topics_he([n.get("title") for n in tmp["evidence"].get("news") or []] +
                                          [p.get("text") for p in tmp["evidence"].get("pulse") or [] if p.get("lang") == "en"])
    tmp["why"] = why_he(tmp["evidence"].get("econ") or [], tmp["evidence"].get("macro") or [], tmp["evidence"]["topics"])
    fu = {"at": now.isoformat(timespec="seconds"),
          "time": (now + timedelta(hours=il_off(now))).strftime("%H:%M"),
          "minutes": mins, "price": round(last, 2), "pctSince": since_pct,
          "lo": round(lo, 2), "hi": round(hi, 2),
          "move": f"{f.get('label') or 'S&P 500'} {move}",
          "evidence": tmp["evidence"]}
    has_new = bool(ev.get("econ") or tmp["evidence"].get("macro") or tmp["evidence"].get("topics"))
    fu["why"] = (tmp.get("why") or "").replace("באותן דקות", "מאז", 1) if has_new else "לא התפרסם מאז מידע בולט חדש"
    mk = load(os.path.join(DATA, "market.json")) or {}
    for it in mk.get("items") or []:
        if it.get("key") in ("vix", "tnx") and it.get("price") is not None:
            fu[it["key"]] = {"price": it["price"], "chg": it.get("chg")}
    f["followup"] = fu
    write_flash(f)
    print(f"[ok] מעקב מבזק אחרי {mins} דק': {fu['move']} · {fu['why']}")
    return True


def compose_tg(flash):
    enrich(flash) if "why" not in flash else None
    arrow = "📉 ירידה" if flash["pct"] < 0 else "📈 עלייה"
    lines = [f"⚡ <b>תנועה חדה בשוק</b> — {arrow} של {abs(flash['pct']):.1f}% "
             f"ב-{WINDOW_MIN} דקות ({flash['label']}, {flash['session']})"]
    if flash.get("why"):
        lines.append(flash["why"])
    ev = flash.get("evidence", {})
    if ev.get("econ"):
        lines.append("")
        lines.append("📊 <b>פרסומי מאקרו בחלון הזמן</b> (הגורם הסביר):")
        for e in ev["econ"]:
            lines.append(f"▸ {e['he']}: בפועל {e['actual']} מול צפי {e['forecast']} ({e['ilTime']})")
    mac = [t for t in ev.get("macro") or [] if t["us"]][:4]
    if mac:
        lines.append("")
        lines.append("📊 <b>נתונים שפורסמו באותן דקות</b>:")
        for t in mac:
            lines.append("▸ " + line_he(t))
    heb = [p for p in ev.get("pulse") or [] if p.get("lang") == "he"][:3]
    if heb:
        lines.append("")
        lines.append("💬 <b>מהרשת</b>:")
        for p in heb:
            lines.append(f"▸ {p['text'][:140]} ({p['source']} · {p['time']})")
    lines.append("")
    lines.append("מה שהתפרסם באותן דקות — לא בהכרח הסיבה.")
    lines.append(f'🔗 <a href="{SITE}">The Daily Edge</a>')
    return "\n".join(lines)


def write_flash(flash):
    flash["_meta"] = {"updatedAt": il_now().strftime("%d/%m/%Y %H:%M"), "source": "detect_flash"}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(flash, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT}")


def main():
    if "--enrich" in sys.argv:   # תרגום flash.json קיים (בלי מדידה ובלי טלגרם)
        f = load(OUT)
        if f and f.get("evidence"):
            write_flash(enrich(f))
        return 0
    test = "--test" in sys.argv
    if not test:
        try:
            followup()
        except Exception as e:   # המעקב לעולם לא מפיל את הזיהוי
            print(f"[warn] מעקב מבזק נכשל: {e}")
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
    enrich(flash)
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
