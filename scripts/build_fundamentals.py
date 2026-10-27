#!/usr/bin/env python3
"""
build_fundamentals.py — "יסודות החברה" לחלון הניתוח הטכני (26.10.2026, איציק: "לשלב בגרף בלבד ולא לערבב עם הטבלאות").

לכל מניה שמופיעה באתר (אותו יקום כמו fetch_bars, בלי תעודות הסל) נשמרים מספרים בסיסיים מ**סורק TradingView**
(בקשה אחת לכל היקום, בלי cookie/crumb — Yahoo quoteSummary חסם את ה-IP של ה-runner ב-429 לכל בקשה, 26.10.2026):
שווי שוק, מכפיל רווח (12 חודשים וקדימה), צמיחת הכנסות, שולי רווח, תזרים חופשי, מזומן וחוב, דיבידנד, מחיר יעד
ודירוגי אנליסטים, צפי לדוח הבא (רווח למניה והכנסות), ענף ותעשייה ומועד הדוח הבא. בנוסף: מועד הדוח קודם מלוח הדיווחים
של האתר, התזוזה שהאופציות מתמחרות ליום הדוח (מ-earnings_prep.json כשיש), תג איכות (מבוססת / צומחת, לא רווחית /
קטנה / מעורבת / ספקולטיבית) ומשפט "קריאה" בעברית.

קצב: הכל מתרענן פעם ביום (REFRESH_H) בבקשה אחת; מניה חדשה ביקום נמשכת בריצה הבאה. מניה שהסורק לא מכיר (OTC,
סמל ישן) מסומנת error ומנוסה שוב אחרי יום. מניה שיצאה מהיקום נמחקת אחרי 45 יום.
פלט: data/fundamentals.json {updated, symbols:{SYM:{…}}}; assets/ta_ui.js קורא אותו בפתיחת החלון.
בדיקה בלי רשת: main(fetch=<פונקציה rows(symbols)→{SYM:{column:value}}>, now=<datetime>).
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iltime import NY  # noqa: E402
import fetch_bars  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "fundamentals.json")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
TV_SCAN = "https://scanner.tradingview.com/america/scan"
REFRESH_H = 24
ERROR_RETRY_H = 24
DROP_DAYS = 45
VER = 2

# העמודות אומתו על ה-runner ב-26.10.2026 (scripts/tools/probe_fund_sources.py) — כולן קיימות ב-metainfo של הסורק
COLS = ["name", "description", "sector", "industry", "market_cap_basic", "close",
        "price_earnings_ttm", "price_earnings_fwd", "earnings_per_share_diluted_ttm", "earnings_per_share_forecast_next_fy",
        "total_revenue_yoy_growth_ttm", "earnings_per_share_diluted_yoy_growth_ttm",
        "gross_margin_ttm", "operating_margin_ttm", "net_margin_ttm", "free_cash_flow_margin_ttm",
        "cash_n_short_term_invest_fq", "total_debt_fq", "dividends_yield_current",
        "price_target_average", "recommendation_mark", "recommendation_total",
        "recommendation_buy", "recommendation_over", "recommendation_hold", "recommendation_under", "recommendation_sell",
        "earnings_per_share_forecast_next_fq", "revenue_forecast_next_fq",
        "earnings_release_next_date", "earnings_release_next_time"]


def tv_rows(symbols):
    """בקשה אחת לסורק: {SYM (סגנון Yahoo): {column: value}}. BRK-B אצלנו = BRK.B בסורק."""
    tv2y = {s.replace("-", "."): s for s in symbols}
    body = json.dumps({
        "filter": [{"left": "name", "operation": "in_range", "right": sorted(tv2y)},
                   {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]}],
        "columns": COLS, "range": [0, len(tv2y) + 50]}).encode()
    req = urllib.request.Request(TV_SCAN, data=body, headers={"User-Agent": UA, "Content-Type": "text/plain"})
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.loads(r.read().decode("utf-8")).get("data") or []
    out = {}
    for row in data:
        d = dict(zip(COLS, row.get("d") or []))
        sym = tv2y.get(d.get("name"))
        if sym and sym not in out:
            out[sym] = d
    return out


# np156: הניתוח המקוצר באתר (ta_ui.js, quickRender) מבקש מהדפדפן גם את העמודות הטכניות האלה.
# בדיקה פעם ביום מה-runner — כדי לדעת מכאן שהן עדיין קיימות בסורק (שם עמודה שגוי = כל הבקשה נכשלת).
TECH_COLS = ["name", "close", "change", "SMA20", "SMA50", "SMA200", "RSI", "Perf.W", "Perf.1M", "Perf.3M",
             "price_52_week_high", "price_52_week_low", "ATR"]


def probe_tech(sym="AAPL"):
    body = json.dumps({"filter": [{"left": "name", "operation": "equal", "right": sym},
                                  {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]}],
                       "columns": TECH_COLS, "range": [0, 3]}).encode()
    req = urllib.request.Request(TV_SCAN, data=body, headers={"User-Agent": UA, "Content-Type": "text/plain"})
    with urllib.request.urlopen(req, timeout=20) as r:
        rows = json.loads(r.read().decode("utf-8")).get("data") or []
    row = next((x["d"] for x in rows if x.get("d") and x["d"][0] == sym), None)
    if not row:
        raise RuntimeError("no row")
    vals = dict(zip(TECH_COLS, row))
    missing = [c for c in TECH_COLS if vals.get(c) is None]
    return {"ok": not missing, "missing": missing, "sample": {k: vals[k] for k in ("close", "SMA50", "RSI", "Perf.3M")}}


def num(v):
    return v if isinstance(v, (int, float)) and v == v else None


def rnd(v, d=1):
    return None if v is None else round(v, d)


def parse(d):
    """שורת סורק → הרשומה שהאתר קורא (אותם שמות שדות כמו בגרסה 1, Yahoo)."""
    close, fwd_eps = num(d.get("close")), num(d.get("earnings_per_share_forecast_next_fy"))
    fwd_pe = num(d.get("price_earnings_fwd"))
    if fwd_pe is None and close and fwd_eps and fwd_eps > 0:
        fwd_pe = close / fwd_eps
    cash, debt = num(d.get("cash_n_short_term_invest_fq")), num(d.get("total_debt_fq"))
    mark = num(d.get("recommendation_mark"))
    rec_key = None if mark is None else "strong_buy" if mark <= 1.5 else "buy" if mark <= 2.5 else "hold" if mark <= 3.5 else "sell" if mark <= 4.5 else "strong_sell"
    ts, tflag = num(d.get("earnings_release_next_date")), d.get("earnings_release_next_time")
    return {
        "name": d.get("description"), "sector": d.get("sector"), "industry": d.get("industry"),
        "cap": num(d.get("market_cap_basic")), "price": close,
        "pe": rnd(num(d.get("price_earnings_ttm")), 2), "fwdPe": rnd(fwd_pe, 2),
        "eps": rnd(num(d.get("earnings_per_share_diluted_ttm")), 3), "fwdEps": rnd(fwd_eps, 3),
        "revGrowth": rnd(num(d.get("total_revenue_yoy_growth_ttm"))),
        "epsGrowth": rnd(num(d.get("earnings_per_share_diluted_yoy_growth_ttm"))),
        "grossMargin": rnd(num(d.get("gross_margin_ttm"))), "opMargin": rnd(num(d.get("operating_margin_ttm"))),
        "netMargin": rnd(num(d.get("net_margin_ttm"))), "fcfMargin": rnd(num(d.get("free_cash_flow_margin_ttm"))),
        "cash": cash, "debt": debt, "netCash": (cash - debt) if (cash is not None and debt is not None) else None,
        "divYield": rnd(num(d.get("dividends_yield_current")), 2),
        "target": rnd(num(d.get("price_target_average")), 2), "targetN": num(d.get("recommendation_total")),
        "recKey": rec_key, "recMean": rnd(mark, 2),
        "recs": {"strongBuy": num(d.get("recommendation_buy")), "buy": num(d.get("recommendation_over")), "hold": num(d.get("recommendation_hold")),
                 "sell": num(d.get("recommendation_under")), "strongSell": num(d.get("recommendation_sell"))},
        "epsEst": rnd(num(d.get("earnings_per_share_forecast_next_fq")), 3), "revEst": num(d.get("revenue_forecast_next_fq")),
        "scanEarn": {"date": datetime.fromtimestamp(ts, NY).date().isoformat(),
                     "when": {1: "after", -1: "before"}.get(tflag, "")} if ts else None,
    }


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def site_earnings():
    """{SYM: (date, when)} מלוח הדיווחים (היום/השבוע/הבאים) — מועד מאומת מהסורק."""
    out = {}
    e = load(os.path.join(DATA, "earnings.json"), {})
    today = e.get("today")
    today = today.get("date") if isinstance(today, dict) else today
    for r in (e.get("reporting") or []):
        if r.get("ticker") and today:
            out[r["ticker"]] = (today, r.get("when") or "")
    for d in (e.get("week") or []):
        for c in (d.get("companies") or []):
            if c.get("ticker") and d.get("date"):
                out.setdefault(c["ticker"], (d["date"], c.get("when") or ""))
    for d in (e.get("upcoming") or []):
        for t in (d.get("tickers") or []):
            if d.get("date"):
                out.setdefault(t, (d["date"], ""))
    return out


def prep_moves():
    """{SYM: {move, eps, rev}} מ-earnings_prep.json — התזוזה המתומחרת והצפי כשיש הכנה."""
    out = {}
    p = load(os.path.join(DATA, "earnings_prep.json"), {})
    for it in (p.get("items") or []):
        o = it.get("options") or {}
        c = it.get("consensus") or {}
        out[it.get("sym")] = {"move": o.get("earn") or o.get("pct"), "eps": c.get("eps"), "rev": c.get("rev")}
    return out


# ---------------------------------------------------------------- פענוח
def quality(f):
    cap, growth = f.get("cap"), f.get("revGrowth")
    prof = (f.get("eps") is not None and f["eps"] > 0) or (f.get("netMargin") is not None and f["netMargin"] > 0)
    if cap is None:
        return {"q": "mid", "label": "חסר מידע"}
    if cap < 3e8 or (not prof and growth is not None and growth < 0):
        return {"q": "bad", "label": "ספקולטיבית"}
    if cap >= 2e9 and prof and (growth is None or growth >= 0):
        return {"q": "ok", "label": "מבוססת"}
    if not prof:
        return {"q": "mid", "label": "צומחת, לא רווחית" if (growth or 0) > 0 else "לא רווחית"}
    if cap < 2e9:
        return {"q": "mid", "label": "קטנה"}
    return {"q": "mid", "label": "רווחית, ההכנסות יורדות" if (growth is not None and growth < 0) else "מעורבת"}


def read_sentence(f, q):
    prof = (f.get("eps") is not None and f["eps"] > 0) or (f.get("netMargin") is not None and f["netMargin"] > 0)
    g = f.get("revGrowth")
    if prof and g is not None and g > 0:
        s = "חברה רווחית וצומחת"
    elif prof and g is not None:
        s = "חברה רווחית, אבל ההכנסות יורדות"
    elif prof:
        s = "חברה רווחית"
    elif g is not None and g > 0:
        s = "צומחת אבל עדיין לא רווחית"
    elif g is not None:
        s = "לא רווחית וההכנסות יורדות"
    else:
        s = "נתוני הרווחיות חסרים"
    pe = f.get("fwdPe") or f.get("pe")
    if pe and pe > 0:
        s += " במכפיל " + ("גבוה" if pe > 35 else "סביר" if pe >= 15 else "נמוך")
    nc, cap = f.get("netCash"), f.get("cap")
    if nc is not None and cap:
        if nc > 0:
            s += ", עם יותר מזומן מחוב"
        elif -nc > 0.3 * cap:
            s += ", ממונפת (החוב נטו מעל 30% מהשווי)"
    if q["q"] == "bad":
        s += ". שווי קטן או חברה מפסידה: תנודתית, לא לפוזיציה מלאה"
    return s + "."


# ---------------------------------------------------------------- ריצה
def age_h(rec, now):
    try:
        return (now - datetime.fromisoformat(rec["at"].replace("Z", "+00:00"))).total_seconds() / 3600
    except (KeyError, ValueError, TypeError):
        return 1e9


def main(fetch=None, now=None):
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    syms, _ = fetch_bars.universe()
    syms = {s for s in syms if s not in fetch_bars.SECTOR_ETFS + fetch_bars.INDEX_ETFS and "/" not in s}
    prev = load(OUT, {})
    symbols = prev.get("symbols") or {}
    earn, moves = site_earnings(), prep_moves()
    fetch = fetch or tv_rows
    todo = sorted(s for s in syms if (lambda r: not r or r.get("ver") != VER or age_h(r, now) >= (ERROR_RETRY_H if r.get("error") else REFRESH_H))(symbols.get(s)))
    ok = fail = 0
    if todo:
        try:
            rows = fetch(todo)
        except Exception as e:  # הסורק לא ענה (או אין רשת, כמו ברוטינה) — הרשומות הקיימות נשארות, ננסה לרענן בריצה הבאה
            print(f"[warn] fundamentals: הסורק של TradingView נכשל ({e}) — בלי רענון הפעם")
            rows, todo = {}, []
        for s in todo:
            d = rows.get(s)
            if not d or num(d.get("market_cap_basic")) is None:
                fail += 1
                symbols[s] = {"at": stamp, "ver": VER, "error": "לא בסורק" if not d else "בלי שווי שוק"}
                continue
            f = parse(d)
            q = quality(f)
            f["quality"], f["read"] = q, read_sentence(f, q)
            f["at"], f["ver"] = stamp, VER
            symbols[s] = f
            ok += 1
    # מועד הדוח הבא + תזוזה מתומחרת + "מה החברה עושה" — מתרעננים בכל ריצה (זולים, מהקבצים)
    blurbs = (load(os.path.join(DATA, "company_blurbs.json"), {}).get("blurbs") or {})
    for s, f in symbols.items():
        if "cap" not in f:
            continue
        about = (blurbs.get(s) or {}).get("he")
        if about:
            f["about"] = about
        else:
            f.pop("about", None)
        d = earn.get(s)
        f["nextEarn"] = {"date": d[0], "when": d[1], "src": "tv"} if d else ({"date": f["scanEarn"]["date"], "when": f["scanEarn"]["when"], "src": "scan"} if f.get("scanEarn") else None)
        m = moves.get(s) or {}
        f["move"] = m.get("move")
        if m.get("eps") is not None:
            f["epsEst"] = m["eps"]
        if m.get("rev") is not None:
            f["revEst"] = m["rev"]
    # ניקוי: מניה מחוץ ליקום 45 יום
    for s in list(symbols):
        if s not in syms and age_h(symbols[s], now) >= 24 * DROP_DAYS:
            del symbols[s]
    tech = prev.get("techProbe") or {}
    if fetch is tv_rows and tech.get("day") != stamp[:10]:
        try:
            tech = dict(probe_tech(), day=stamp[:10])
        except Exception as e:  # noqa: BLE001 — מידע בלבד, לא עוצר
            tech = {"day": stamp[:10], "ok": False, "error": str(e)[:80]}
        print("fundamentals: tech columns probe %s" % json.dumps(tech, ensure_ascii=False))
    out = {"updated": stamp, "ver": VER, "universe": len(syms), "source": "TradingView scanner", "techProbe": tech,
           "count": sum(1 for v in symbols.values() if "cap" in v), "pending": 0,
           "symbols": dict(sorted(symbols.items()))}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    errs = [k for k, v in symbols.items() if v.get("error")]
    no_blurb = [k for k, v in symbols.items() if "cap" in v and not v.get("about")]
    print("fundamentals: universe=%d have=%d refreshed=%d failed=%d missing=%s · without blurb=%d%s"
          % (len(syms), out["count"], ok, fail, ",".join(errs[:12]) + ("…" if len(errs) > 12 else "") if errs else "0",
             len(no_blurb), (" (" + ",".join(no_blurb[:10]) + ")") if no_blurb else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
