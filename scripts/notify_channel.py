#!/usr/bin/env python3
r"""
notify_channel.py — ארבע הודעות תוכן לערוץ הטלגרם (חבילה ראשונה, 11.9.2026):

  1. preopen  — "5 דקות לפתיחה": חוזים, VIX, אג"ח 10Y, המאקרו של היום (צפי, או
                בפועל אם כבר פורסם ב-15:30), מדווחות לפני הפתיחה ואחרי הסגירה.
                חלון: ב'–ו' 16:05–16:29 שעון ישראל, פעם ביום.
  2. close    — "סיכום סגירה": SPY/QQQ/IWM, VIX, 10Y, 3 העולות ו-3 היורדות של
                יום המסחר (סריקת TradingView עם שינוי *יומי* — לא movers.json,
                שאחרי 23:00 מחזיק שינויי אפטר-מרקט), ומי מדווחת הערב.
                חלון: ב'–ו' 23:05–23:59, פעם ביום.
  3. macro    — "נתון מאקרו": ברגע ש-econ.json מקבל 'בפועל' לאירוע — צפי מול
                בפועל עם כיוון ההפתעה. מקובץ לפי מועד פרסום (CPI חודשי+ליבה+שנתי
                בהודעה אחת). כל אירוע פעם אחת (state), רק אירועים מ-36 השעות
                האחרונות (בלי backfill של היסטוריה).
  4. analysis — "הניתוח היומי": כשה-date של claude_analysis.json מתחלף —
                כותרת, משפט-מהות ושורה תחתונה, עם קישור לטאב מדדים.

בהרצה הראשונה (בלי state) — macro ו-analysis רק קובעים בסיס בלי לשלוח, כדי לא
להציף את הערוץ בנתונים ישנים. state: data/_channel_state.json.

סודות: TELEGRAM_BOT_TOKEN + TELEGRAM_CHANNEL.
בדיקה: python notify_channel.py --dry-run             → מדפיס את כל הארבע, בלי לשלוח
       python notify_channel.py --test preopen|close|macro|analysis → שולח אחת לערוץ, עוקף שערים
"""
import html
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify_telegram import send, load

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
STATE = os.path.join(DATA, "_channel_state.json")
SITE = "https://nditzik.github.io/nidam-markets/"
SCAN = "https://scanner.tradingview.com/america/scan"
UA = {"User-Agent": "Mozilla/5.0 (compatible; nidam-markets-bot)", "Content-Type": "application/json"}

DOW_HE = ["ב'", "ג'", "ד'", "ה'", "ו'", "שבת", "א'"]   # weekday() של פייתון
PREOPEN_WIN = (16 * 60 + 5, 16 * 60 + 29)
CLOSE_WIN = (23 * 60 + 5, 23 * 60 + 59)
MACRO_MAX_AGE_H = 36
MAX_TICKERS = 5


def il_now():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return now + timedelta(hours=off)


def esc(s):
    return html.escape(str(s or ""))


def pct(v, digits=1):
    if v is None:
        return "—"
    return ("+" if v > 0 else "") + f"{v:.{digits}f}%"


def arrow(v):
    return "🟢" if (v or 0) > 0 else "🔴" if (v or 0) < 0 else "⚪"


def item(md, key):
    for it in (md or {}).get("items", []):
        if it.get("key") == key:
            return it
    return None


def day_label(now):
    return "%s %d.%d" % (DOW_HE[now.weekday()], now.day, now.month)


def tickers_line(rows, when):
    syms = [r["ticker"] for r in rows if r.get("when") == when and r.get("ticker")]
    if not syms:
        return None
    more = len(syms) - MAX_TICKERS
    s = ", ".join(syms[:MAX_TICKERS]) + (f" ועוד {more}" if more > 0 else "")
    return s


# ── 1. לפני הפתיחה ─────────────────────────────────────────────────────────
def compose_preopen(now):
    md = load(os.path.join(DATA, "market.json")) or {}
    econ = load(os.path.join(DATA, "econ.json")) or {}
    earn = load(os.path.join(DATA, "earnings.json")) or {}
    es, nq, vix, tnx = item(md, "es"), item(md, "nq"), item(md, "vix"), item(md, "tnx")
    if not es or es.get("chg") is None:
        return None
    lines = ["🔔 <b>5 דקות לפתיחה</b> · " + day_label(now), ""]
    lines.append("%s חוזה S&P <b>%s</b> · חוזה Nasdaq <b>%s</b>" % (arrow(es["chg"]), pct(es["chg"], 2), pct((nq or {}).get("chg"), 2)))
    bits = []
    if vix and vix.get("price") is not None:
        bits.append("VIX %.1f (%s)" % (vix["price"], pct(vix.get("chg"))))
    if tnx and tnx.get("price") is not None:
        bits.append("אג\"ח 10Y %.2f%%" % tnx["price"])
    if bits:
        lines.append("📉 " + " · ".join(bits))
    # המאקרו של היום — אם כבר פורסם (15:30) מציגים בפועל מול צפי, אחרת רק צפי
    today_il = "%d.%d" % (now.day, now.month)
    evs = [e for e in econ.get("events", []) if e.get("ilDate") == today_il]
    for e in evs[:4]:
        nm = esc(e.get("he")) + (" (%s)" % esc(e["period"]) if e.get("period") else "")
        if e.get("actual"):
            lines.append("📅 %s %s: <b>%s</b> מול צפי %s %s" % (esc(e.get("ilTime", "")), nm, esc(e["actual"]), esc(e.get("forecast") or "—"), surprise_word(e.get("surprise"))))
        else:
            lines.append("📅 %s %s — צפי %s · קודם %s" % (esc(e.get("ilTime", "")), nm, esc(e.get("forecast") or "—"), esc(e.get("previous") or "—")))
    rep = earn.get("reporting") or []
    if earn.get("today") == now.date().isoformat():
        b = tickers_line(rep, "before")
        a = tickers_line(rep, "after")
        if b:
            lines.append("🏢 מדווחות לפני הפתיחה: <code>%s</code>" % esc(b))
        if a:
            lines.append("🌙 אחרי הסגירה הערב: <code>%s</code>" % esc(a))
    lines += ["", "🔗 <a href=\"%s\">The Daily Edge</a>" % SITE]
    return "\n".join(lines)


# ── 2. סיכום סגירה ─────────────────────────────────────────────────────────
def tv_day_movers(n=3):
    """3 העולות ו-3 היורדות של יום המסחר (שינוי יומי, נפח ≥1M, מחיר ≥$5)."""
    def scan(asc):
        body = {
            "filter": [
                {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]},
                {"left": "type", "operation": "equal", "right": "stock"},
                {"left": "volume", "operation": "greater", "right": 1_000_000},
                {"left": "close", "operation": "greater", "right": 5},
            ],
            "columns": ["name", "change", "close"],
            "sort": {"sortBy": "change", "sortOrder": "asc" if asc else "desc"},
            "range": [0, n],
        }
        req = urllib.request.Request(SCAN, data=json.dumps(body).encode(), headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read().decode("utf-8"))
        return [(row["d"][0], row["d"][1]) for row in d.get("data", []) if row["d"][1] is not None]
    return scan(False), scan(True)


def compose_close(now):
    md = load(os.path.join(DATA, "market.json")) or {}
    earn = load(os.path.join(DATA, "earnings.json")) or {}
    spy, qqq, iwm, vix, tnx = (item(md, k) for k in ("spy", "qqq", "iwm", "vix", "tnx"))
    if not spy or spy.get("chg") is None:
        return None
    lines = ["🔔 <b>סיכום סגירה</b> · " + day_label(now), ""]
    lines.append("%s S&P 500 <b>%s</b> · Nasdaq <b>%s</b> · Russell <b>%s</b>" % (
        arrow(spy["chg"]), pct(spy["chg"], 2), pct((qqq or {}).get("chg"), 2), pct((iwm or {}).get("chg"), 2)))
    bits = []
    if vix and vix.get("price") is not None:
        bits.append("VIX %.1f (%s)" % (vix["price"], pct(vix.get("chg"))))
    if tnx and tnx.get("price") is not None:
        bits.append("אג\"ח 10Y %.2f%%" % tnx["price"])
    if bits:
        lines.append("📉 " + " · ".join(bits))
    try:
        ups, downs = tv_day_movers()
        if ups:
            lines.append("🟢 בולטות: " + " · ".join("<code>%s</code> %s" % (esc(s), pct(c)) for s, c in ups))
        if downs:
            lines.append("🔴 יורדות: " + " · ".join("<code>%s</code> %s" % (esc(s), pct(c)) for s, c in downs))
    except Exception as e:
        print(f"[warn] movers scan: {e}")
    if earn.get("today") == now.date().isoformat():
        a = tickers_line(earn.get("reporting") or [], "after")
        if a:
            lines.append("🌙 מדווחות הערב אחרי הסגירה: <code>%s</code>" % esc(a))
    lines += ["", "🔗 <a href=\"%s\">The Daily Edge</a>" % SITE]
    return "\n".join(lines)


# ── 3. נתון מאקרו ──────────────────────────────────────────────────────────
def surprise_word(s):
    return {"good": "✅ טוב מהצפוי", "bad": "❌ גרוע מהצפוי", "inline": "➖ בהתאם לצפי"}.get(s or "", "")


def ev_key(e):
    return "%s|%s" % (e.get("date"), e.get("he"))


def fresh_macro(econ, now):
    """אירועים עם 'בפועל' מ-36 השעות האחרונות."""
    out = []
    for e in econ.get("events", []):
        if not e.get("actual"):
            continue
        try:
            t = datetime.strptime(e["date"], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        age_h = (datetime.now(timezone.utc) - t).total_seconds() / 3600
        if 0 <= age_h <= MACRO_MAX_AGE_H:
            out.append(e)
    return out


def compose_macro(evs):
    if not evs:
        return None
    first = evs[0]
    lines = ["📣 <b>נתון מאקרו</b> · %s %s" % (esc(first.get("ilDate", "")), esc(first.get("ilTime", ""))), ""]
    for e in evs:
        nm = esc(e.get("he")) + (" (%s)" % esc(e["period"]) if e.get("period") else "")
        lines.append("• %s: <b>%s</b> מול צפי %s · קודם %s  %s" % (
            nm, esc(e["actual"]), esc(e.get("forecast") or "—"), esc(e.get("previous") or "—"), surprise_word(e.get("surprise"))))
    lines += ["", "🔗 <a href=\"%s\">The Daily Edge</a>" % SITE]
    return "\n".join(lines)


# ── 4. הניתוח היומי ────────────────────────────────────────────────────────
def fmt_d(iso):
    p = (iso or "").split("-")
    return f"{int(p[2])}.{int(p[1])}" if len(p) == 3 else iso


def compose_analysis(ca):
    if not ca or not ca.get("headline"):
        return None
    lines = ["🧭 <b>הניתוח היומי</b> · סיכום המסחר של %s" % esc(fmt_d(ca.get("date"))), ""]
    lines.append("<b>%s</b>" % esc(ca["headline"]))
    if ca.get("tldr"):
        lines += ["", esc(ca["tldr"])]
    if ca.get("bottomline"):
        lines += ["", "💡 " + esc(ca["bottomline"])]
    lines += ["", "🔗 <a href=\"%s#indices\">הניתוח המלא בטאב מדדים</a>" % SITE]
    return "\n".join(lines)


# ── ריצה ───────────────────────────────────────────────────────────────────
def main():
    dry = "--dry-run" in sys.argv
    test = sys.argv[sys.argv.index("--test") + 1] if "--test" in sys.argv and len(sys.argv) > sys.argv.index("--test") + 1 else None
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHANNEL")
    now = il_now()
    today = now.date().isoformat()
    econ = load(os.path.join(DATA, "econ.json")) or {}
    ca = load(os.path.join(DATA, "claude_analysis.json")) or {}

    if dry or test:
        msgs = {
            "preopen": compose_preopen(now),
            "close": compose_close(now),
            "macro": compose_macro(fresh_macro(econ, now) or [e for e in econ.get("events", []) if e.get("actual")][-3:]),
            "analysis": compose_analysis(ca),
        }
        for k, m in msgs.items():
            if test and k != test:
                continue
            print("─" * 30, k, "─" * 30)
            print(m or "(אין נתונים)")
        if test:
            if not (token and chat):
                print("[skip] חסרים סודות טלגרם — לא נשלח.")
                return 0
            if msgs.get(test):
                send(token, chat, msgs[test])
                print(f"[ok] {test} נשלח לערוץ (בדיקה).")
        return 0

    if not (token and chat):
        print("[skip] חסרים סודות טלגרם.")
        return 0

    state = load(STATE) or {}
    first_run = not state
    changed = False
    t = now.hour * 60 + now.minute
    weekday = now.weekday() <= 4

    # 1. לפני הפתיחה
    if weekday and PREOPEN_WIN[0] <= t <= PREOPEN_WIN[1] and state.get("preopen") != today:
        m = compose_preopen(now)
        if m:
            send(token, chat, m); print("[sent] preopen")
        state["preopen"] = today; changed = True

    # 2. סיכום סגירה
    if weekday and CLOSE_WIN[0] <= t <= CLOSE_WIN[1] and state.get("close") != today:
        m = compose_close(now)
        if m:
            send(token, chat, m); print("[sent] close")
        state["close"] = today; changed = True

    # 3. מאקרו — כל אירוע פעם אחת; בריצה הראשונה רק בסיס
    sent_keys = set(state.get("macro") or [])
    fresh = [e for e in fresh_macro(econ, now) if ev_key(e) not in sent_keys]
    if fresh:
        if not first_run:
            groups = {}
            for e in fresh:
                groups.setdefault(e.get("date"), []).append(e)
            for k in sorted(groups):
                send(token, chat, compose_macro(groups[k])); print(f"[sent] macro {k} ({len(groups[k])})")
        sent_keys.update(ev_key(e) for e in fresh)
        state["macro"] = sorted(sent_keys)[-60:]; changed = True

    # 4. הניתוח היומי — כשה-date מתחלף; בריצה הראשונה רק בסיס
    if ca.get("date") and state.get("analysis") != ca["date"]:
        if not first_run:
            m = compose_analysis(ca)
            if m:
                send(token, chat, m); print("[sent] analysis", ca["date"])
        state["analysis"] = ca["date"]; changed = True

    if changed or first_run:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        if first_run:
            print("[init] state נקבע בלי לשלוח (macro/analysis).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
