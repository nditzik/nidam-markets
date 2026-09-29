#!/usr/bin/env python3
"""
fetch_bars.py — נרות יומיים (OHLCV) ליקום המניות של האתר → data/bars/SYM.json (29.9.2026).

למה: מנוע הניתוח הטכני (assets/ta_engine.js, פורט של ANALYSIS_SPEC.md) רץ בדפדפן על
500 נרות יומיים. לדפדפן אין גישה ל-Yahoo (CORS), אז הבוט אוסף ושומר בריפו.

יקום: מומנטום + מועמדים + לוח הדיווחים (היום/השבוע/הקרובים) + "הכסף הגדול" + Insider
+ הצעות לטרייד (6 דוחות אחרונים) + ניתוח דוחות
+ 11 תעודות הסקטורים + SPY/QQQ/IWM + data/ta_watchlist.txt (רשימה חופשית של איציק,
טיקר בכל שורה, # = הערה). סמל שלא נראה ביקום 45 יום נמחק (למעט watchlist).

קצב: פעם ביום מסחר, אחרי 16:20 ניו יורק (רק נרות סגורים נשמרים — הנר של היום
בזמן המסחר מגיע לדפדפן מסורק TradingView כ-is_partial). סמל חדש נמשך בריצה הראשונה
שמוצאת אותו (עד NEW_PER_RUN לריצה). כשל משיכה משאיר את הקובץ הקיים.

פורמט הקובץ (קומפקטי, ~18KB לסמל): {"symbol","updated","last","n","bars":[[date,o,h,l,c,v],…]}
אינדקס: data/bars/index.json → {"updated","symbols":{SYM:{"last","n","seen"}}} — הדפדפן
קורא אותו כדי לדעת לאילו טיקרים יש ניתוח.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iltime import NY  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(DATA, "bars")
INDEX = os.path.join(OUT_DIR, "index.json")   # לא "_index": Jekyll של GitHub Pages משמיט קבצים שמתחילים בקו תחתון
WATCHLIST = os.path.join(DATA, "ta_watchlist.txt")
UA = "nidam-markets-bot"
KEEP_BARS = 520          # ≥500 למנוע + מרווח
NEW_PER_RUN = 60         # תקרת סמלים חדשים בריצה אחת (עומס על Yahoo)
MAX_REQ_PER_RUN = 220
PRUNE_DAYS = 45
RETRY_HOURS = 2          # אחרי ניסיון שלא הביא נר חדש (חג/עיכוב) — לנסות שוב בעוד שעתיים
SECTOR_ETFS = ["XLK", "XLF", "XLV", "XLY", "XLC", "XLI", "XLP", "XLE", "XLB", "XLU", "XLRE"]
INDEX_ETFS = ["SPY", "QQQ", "IWM"]
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,6}$")


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def norm(sym):
    s = str(sym or "").strip().upper()
    if s.startswith("NASDAQ:") or s.startswith("NYSE:") or s.startswith("AMEX:"):
        s = s.split(":", 1)[1]
    return s if TICKER_RE.match(s) else None


def universe():
    """כל הטיקרים שהאתר מציג כרגע + watchlist. מחזיר (set, watch_set)."""
    syms = set(SECTOR_ETFS + INDEX_ETFS)

    def add(x):
        s = norm(x)
        if s:
            syms.add(s)

    for st in (load(os.path.join(DATA, "momentum.json"), {}).get("stocks") or []):
        add(st.get("symbol"))
    for c in (load(os.path.join(DATA, "candidates.json"), {}).get("candidates") or []):
        add(c.get("symbol"))
    earn = load(os.path.join(DATA, "earnings.json"), {})
    for r in (earn.get("reporting") or []):
        add(r.get("ticker"))
    for d in (earn.get("week") or []):
        for c in (d.get("companies") or []):
            add(c.get("ticker"))
    for d in (earn.get("upcoming") or []):
        for t in (d.get("tickers") or []):
            add(t)
    for r in (earn.get("reactions") or []):
        add(r.get("ticker") if isinstance(r, dict) else None)
    ind = load(os.path.join(DATA, "indices.json"), {})
    for it in ((ind.get("bigTrades") or {}).get("items") or []):
        add(it.get("ticker"))
    for r in (load(os.path.join(DATA, "insider.json"), {}).get("reports") or []):
        for t in (r.get("tickers") or []):
            add(t)
    # הצעות לטרייד: הטיקרים מטבלאות 6 הדוחות האחרונים; ניתוח דוחות: הטיקר של כל דוח
    for r in (load(os.path.join(DATA, "trades.json"), {}).get("reports") or [])[:6]:
        for p in (r.get("picks") or []):
            add(p.get("ticker"))
    for r in (load(os.path.join(DATA, "reports.json"), {}).get("reports") or []):
        add(r.get("ticker"))
    watch = set()
    try:
        with open(WATCHLIST, encoding="utf-8") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                for tok in re.split(r"[,\s]+", line):
                    s = norm(tok)
                    if s:
                        watch.add(s)
    except OSError:
        pass
    syms |= watch
    return syms, watch


def yahoo_bars(sym, rng, fetch=None):
    """נרות יומיים סגורים בלבד: [[date,o,h,l,c,v],…]. הנר האחרון נשמט אם הסשן שלו עוד פתוח."""
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(sym) + "?interval=1d&range=" + rng)
    if fetch is None:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode("utf-8"))
    else:
        d = fetch(url)
    res = d["chart"]["result"][0]
    m = res.get("meta") or {}
    off = m.get("gmtoffset") or 0
    ts = res.get("timestamp") or []
    q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    o, h, l, c, v = (q.get(k) or [] for k in ("open", "high", "low", "close", "volume"))
    bars = []
    for i, t in enumerate(ts):
        try:
            oo, hh, ll, cc = o[i], h[i], l[i], c[i]
        except IndexError:
            continue
        if None in (oo, hh, ll, cc):
            continue
        vol = v[i] if i < len(v) and v[i] is not None else 0
        date = datetime.fromtimestamp(t + off, timezone.utc).date().isoformat()
        # תיקון עקביות (Yahoo לפעמים מחזיר high/low שלא מכסים את הפתיחה/סגירה בכמה סנט)
        hi = max(hh, oo, cc)
        lo = min(ll, oo, cc)
        bars.append([date, round(oo, 4), round(hi, 4), round(lo, 4), round(cc, 4), int(vol)])
    if not bars:
        return []
    reg = ((m.get("currentTradingPeriod") or {}).get("regular") or {})
    reg_end = reg.get("end") or 0
    reg_day = datetime.fromtimestamp(reg_end + off, timezone.utc).date().isoformat() if reg_end else ""
    mkt_t = m.get("regularMarketTime") or 0
    last_final = (bars[-1][0] < reg_day) or bool(reg_end and mkt_t >= reg_end)
    if not last_final:
        bars.pop()
    # תאריכים ייחודיים ועולים
    out, seen = [], set()
    for b in bars:
        if b[0] in seen:
            continue
        seen.add(b[0])
        out.append(b)
    return out


def merge(old, new):
    by = {b[0]: b for b in old}
    for b in new:
        by[b[0]] = b
    bars = [by[k] for k in sorted(by)]
    return bars[-KEEP_BARS:]


def last_trading_day(now_ny):
    """היום שהנר הסגור האחרון שלו אמור להיות זמין: היום אם יום חול ואחרי 16:20, אחרת יום החול הקודם.
    חגים לא מטופלים כאן — הניסיון פשוט לא ימצא נר חדש ויחזור בעוד RETRY_HOURS."""
    d = now_ny.date()
    if now_ny.weekday() >= 5 or now_ny.hour * 60 + now_ny.minute < 16 * 60 + 20:
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()


def main(fetch=None, now=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    now_utc = now or datetime.now(timezone.utc)
    now_ny = now_utc.astimezone(NY)
    today_ny = now_ny.date().isoformat()
    target = last_trading_day(now_ny)
    idx = load(INDEX, {"symbols": {}})
    symbols = idx.get("symbols") or {}
    attempts = idx.get("attempts") or {}
    syms, watch = universe()

    for s in syms:
        symbols.setdefault(s, {})
        symbols[s]["seen"] = today_ny

    todo_new, todo_upd = [], []
    for s in sorted(syms):
        info = symbols[s]
        path = os.path.join(OUT_DIR, s + ".json")
        exists = os.path.exists(path) and info.get("last")
        if not exists:
            todo_new.append(s)
            continue
        if info["last"] < target:
            att = attempts.get(s)
            if att and att.get("for") == target:
                try:
                    at = datetime.fromisoformat(att["at"])
                except ValueError:
                    at = now_utc - timedelta(days=1)
                if now_utc - at < timedelta(hours=RETRY_HOURS):
                    continue
            todo_upd.append(s)

    # סמלים חדשים: קודם watchlist ותעודות המדד/הסקטורים, אחר כך לפי א"ב
    pri = set(watch) | set(SECTOR_ETFS) | set(INDEX_ETFS)
    todo_new.sort(key=lambda s: (0 if s in pri else 1, s))
    todo = [(s, "2y") for s in todo_new[:NEW_PER_RUN]] + [(s, "1mo") for s in todo_upd]
    todo = todo[:MAX_REQ_PER_RUN]
    ok = fail = 0
    for s, rng in todo:
        path = os.path.join(OUT_DIR, s + ".json")
        old = load(path, {}).get("bars") or []
        try:
            new = yahoo_bars(s, rng, fetch)
        except Exception as e:  # noqa: BLE001 — כשל משיכה משאיר את הקיים
            print("fetch_bars: %s failed: %s" % (s, e), file=sys.stderr)
            fail += 1
            attempts[s] = {"for": target, "at": now_utc.isoformat()}
            continue
        if rng == "1mo" and len(old) < 400:
            # קובץ קצר מדי (נפגע/חדש) — נמשוך היסטוריה מלאה בריצה הבאה
            try:
                new = yahoo_bars(s, "2y", fetch)
            except Exception:  # noqa: BLE001
                pass
        bars = merge(old, new) if new else old
        if not bars:
            fail += 1
            attempts[s] = {"for": target, "at": now_utc.isoformat()}
            continue
        if not new or bars[-1][0] < target:
            attempts[s] = {"for": target, "at": now_utc.isoformat()}
        else:
            attempts.pop(s, None)
        doc = {"symbol": s, "updated": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), "last": bars[-1][0], "n": len(bars), "bars": bars}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
        symbols[s].update({"last": bars[-1][0], "n": len(bars)})
        ok += 1
        if fetch is None:
            time.sleep(0.15)

    # ניקוי: סמלים שלא נראו ביקום PRUNE_DAYS יום (ולא ב-watchlist)
    cutoff = (now_ny.date() - timedelta(days=PRUNE_DAYS)).isoformat()
    for s in list(symbols):
        seen = symbols[s].get("seen") or "1970-01-01"
        if s in watch or s in syms or seen >= cutoff:
            continue
        symbols.pop(s, None)
        attempts.pop(s, None)
        try:
            os.remove(os.path.join(OUT_DIR, s + ".json"))
        except OSError:
            pass
    # סמלים באינדקס בלי קובץ (למשל כשל ראשון) — לא לסמן להם last
    for s in list(symbols):
        if not os.path.exists(os.path.join(OUT_DIR, s + ".json")):
            symbols[s].pop("last", None)
            symbols[s].pop("n", None)

    idx = {"updated": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), "target": target, "count": sum(1 for s in symbols if symbols[s].get("last")),
           "universe": len(syms), "watchlist": sorted(watch), "symbols": dict(sorted(symbols.items())), "attempts": attempts,
           "_meta": {"source": "Yahoo v8 chart, interval=1d", "note": "נרות סגורים בלבד; הנר של היום מגיע לדפדפן מסורק TradingView כ-is_partial"}}
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    print("fetch_bars: universe=%d files=%d fetched=%d failed=%d pending_new=%d target=%s"
          % (len(syms), idx["count"], ok, fail, max(0, len(todo_new) - NEW_PER_RUN), target))


if __name__ == "__main__":
    main()
