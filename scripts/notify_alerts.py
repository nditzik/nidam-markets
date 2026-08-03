#!/usr/bin/env python3
"""
notify_alerts.py — התראות חריגים לערוץ הטלגרם (רץ בכל הרצת Action, ~15 דק').

קטגוריות:
  1. שוק רחב — תנודת מדד חריגה (מדרגות 1.5/2.5/3.5%), זינוק VIX (15/25/40%
     או חציית רמה 25/30), תשואת 10Y חוצה 4.8%/5.0% כלפי מעלה.
  3. מד השוק — חציית רף (66 לחיובי / 45 להגנתי) או קפיצה יומית ±10 נק'.
  5. סיכום דוחות-הלילה — הודעה מרוכזת אחת ב-23:30: תגובת האפטר-מרקט של
     המדווחות הגדולות של היום ($20B+, מתוך earnings.json.todayBig).

הגנות ספאם: מדרגות הסלמה (state), תקרה 5 התראות/יום, שעות פעילות ב'–ו'
11:00–23:59, כל טריגר פעם אחת ביום. state: data/_alerts_state.json.
בדיקה: python notify_alerts.py --test  → סיכום-לילה מיידי (עוקף שערים).
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify_telegram import send, load

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
STATE = os.path.join(DATA, "_alerts_state.json")
SITE = "https://nditzik.github.io/nidam-markets/"
SCAN = "https://scanner.tradingview.com/america/scan"
UA = {"User-Agent": "Mozilla/5.0 (compatible; nidam-markets-bot)",
      "Content-Type": "application/json"}

MAX_PER_DAY = 5
IDX_LADDER = [1.5, 2.5, 3.5]        # % תנודת מדד
VIX_LADDER = [15, 25, 40]           # % זינוק VIX יומי
VIX_LEVELS = [25, 30]               # רמות VIX
TNX_LEVELS = [4.8, 5.0]             # תשואת 10Y
METER_JUMP = 10
EARN_DIGEST_MIN = 23 * 60 + 30      # 23:30


def il_now():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return now + timedelta(hours=off)


def market_item(md, key):
    for it in (md or {}).get("items", []):
        if it.get("key") == key:
            return it
    return None


def ladder_hit(value, ladder, fired):
    """המדרגה הגבוהה ביותר שהושגה ועדיין לא נורתה. fired = רשימת מדרגות שנורו."""
    hit = None
    for step in ladder:
        if abs(value) >= step and step not in fired:
            hit = step
    return hit


def tv_post_changes(symbols):
    """שינוי אפטר-מרקט (ונפילה ל-change יומי) לכל סימבול."""
    body = {
        "filter": [
            {"left": "name", "operation": "in_range", "right": symbols},
            {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]},
        ],
        "columns": ["name", "postmarket_change", "change"],
        "range": [0, len(symbols) + 8],
    }
    req = urllib.request.Request(SCAN, data=json.dumps(body).encode(), headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode("utf-8"))
    out = {}
    for row in d.get("data", []):
        v = row["d"]
        if v[0] in symbols and v[0] not in out:
            out[v[0]] = {"post": v[1], "day": v[2]}
    return out


def compose_earn_digest(big):
    syms = [b["ticker"] for b in big]
    try:
        q = tv_post_changes(syms)
    except Exception as e:
        print(f"[warn] ציטוטי אפטר נכשלו: {e}")
        return None
    lines = ["🌙 <b>תגובות השוק לדוחות הערב</b>"]
    shown = 0
    for b in big:
        d = q.get(b["ticker"])
        if not d:
            continue
        post, day = d.get("post"), d.get("day")
        val = post if post is not None else day
        if val is None:
            continue
        tag = "אפטר" if post is not None else "יום"
        emoji = "🟢" if val >= 0 else "🔴"
        lines.append(f"{emoji} <b>{b['ticker']}</b> ({b['name'][:22]}): {val:+.1f}% ({tag})")
        shown += 1
    if not shown:
        return None
    lines.append("")
    lines.append(f'🔗 <a href="{SITE}">The Daily Edge</a>')
    return "\n".join(lines)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHANNEL")
    if not token or not chat:
        print("[skip] אין סודות טלגרם.")
        return 0

    earn = load(os.path.join(DATA, "earnings.json")) or {}
    big = earn.get("todayBig") or []

    if "--test" in sys.argv:
        msg = compose_earn_digest(big) or "🌙 (אין נתוני אפטר-מרקט כרגע למדווחות הגדולות)"
        send(token, chat, msg)
        print("[ok] סיכום-לילה לניסיון נשלח.")
        return 0

    now = il_now()
    today = now.strftime("%Y-%m-%d")
    minutes = now.hour * 60 + now.minute

    # שעות פעילות: ב'-ו', 11:00 עד חצות
    if now.weekday() >= 5 or minutes < 11 * 60:
        print("[skip] מחוץ לשעות הפעילות.")
        return 0

    state = load(STATE) or {}
    if state.get("date") != today:
        state = {"date": today, "fired": {}, "count": 0}

    def fired(key):
        return state["fired"].get(key, [])

    def mark(key, val=True):
        state["fired"].setdefault(key, [])
        if val is not True:
            state["fired"][key].append(val)
        else:
            state["fired"][key] = [True]

    alerts = []
    md = load(os.path.join(DATA, "market.json"))

    # --- 1. תנודת מדד (SPY בזמן מסחר, אחרת חוזה S&P) ---
    in_session = 16 * 60 + 30 <= minutes < 23 * 60
    idx = market_item(md, "spy" if in_session else "es")
    if idx and idx.get("chg") is not None:
        step = ladder_hit(idx["chg"], IDX_LADDER, fired("idx"))
        if step is not None:
            emoji = "🔴" if idx["chg"] < 0 else "🟢"
            name = "S&P 500" if in_session else "חוזה S&P"
            alerts.append((f"idx:{step}", f"{emoji} <b>תנודה חריגה:</b> {name} {idx['chg']:+.1f}%",
                           lambda s=step: mark("idx", s)))

    # --- 1ב. VIX ---
    vix = market_item(md, "vix")
    if vix and vix.get("chg") is not None:
        step = ladder_hit(vix["chg"], VIX_LADDER, fired("vix")) if vix["chg"] > 0 else None
        if step is not None:
            alerts.append((f"vix:{step}", f"⚠️ <b>VIX מזנק {vix['chg']:+.0f}%</b> לרמת {vix.get('price')}",
                           lambda s=step: mark("vix", s)))
        for lvl in VIX_LEVELS:
            key = f"vixlvl:{lvl}"
            if vix.get("price") and vix["price"] >= lvl and lvl not in fired("vixlvl"):
                alerts.append((key, f"⚠️ <b>VIX חצה את רמת {lvl}</b> ({vix['price']})",
                               lambda l=lvl: mark("vixlvl", l)))
                break

    # --- 1ג. תשואת 10Y ---
    tnx = market_item(md, "tnx")
    if tnx and tnx.get("price"):
        for lvl in TNX_LEVELS:
            if tnx["price"] >= lvl and lvl not in fired("tnx"):
                alerts.append((f"tnx:{lvl}", f"📈 <b>תשואת האג\"ח ל-10 שנים חצתה {lvl}%</b> ({tnx['price']})",
                               lambda l=lvl: mark("tnx", l)))
                break

    # --- 3. מד השוק: חציית רף / קפיצה ---
    days = (load(os.path.join(DATA, "history.json")) or {}).get("days", [])
    if len(days) >= 2 and not fired("meter"):
        a, b = days[-2].get("combined"), days[-1].get("combined")
        if a is not None and b is not None:
            msg = None
            if a < 66 <= b:
                msg = f"🟢 <b>מד השוק עלה לחיובי</b> ({a} → {b})"
            elif a >= 45 > b:
                msg = f"🔴 <b>מד השוק ירד להגנתי</b> ({a} → {b})"
            elif abs(b - a) >= METER_JUMP:
                arrow = "⬆️" if b > a else "⬇️"
                msg = f"{arrow} <b>קפיצה במד השוק:</b> {a} → {b}"
            if msg:
                alerts.append(("meter", msg, lambda: mark("meter")))

    # --- 5. סיכום דוחות-הלילה (23:30, פעם ביום) ---
    if minutes >= EARN_DIGEST_MIN and big and not fired("earnnight"):
        msg = compose_earn_digest(big)
        if msg:
            alerts.append(("earnnight", msg, lambda: mark("earnnight")))

    sent = 0
    for key, msg, marker in alerts:
        if state["count"] >= MAX_PER_DAY:
            print(f"[cap] תקרת ההתראות היומית הושגה — {key} לא נשלח.")
            break
        try:
            if "🔗" not in msg:
                msg += f'\n🔗 <a href="{SITE}">The Daily Edge</a>'
            send(token, chat, msg)
            marker()
            state["count"] += 1
            sent += 1
            print(f"[alert] {key}")
        except Exception as e:
            print(f"[warn] {key}: {e}")

    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"[done] {sent} התראות נשלחו · {state['count']}/{MAX_PER_DAY} היום")
    return 0


if __name__ == "__main__":
    sys.exit(main())
