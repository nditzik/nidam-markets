#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_rotation.py — דוח הרוטציה הסקטוריאלית השבועי ("לאן זרם הכסף השבוע?") מקובצי ה-CSV
של Barchart שגרוק מעלה לדרייב (Rotation/YYYY-MM-DD). המספרים כאן, המילים ברוטינה.

    python3 scripts/build_rotation.py check   <date>   # בקרת שפיות על התיקייה (יציאה ≠0 = לא מוכן)
    python3 scripts/build_rotation.py decode  <date>   # raw/*.b64 (שה-Drive connector מחזיר) → קבצים
    python3 scripts/build_rotation.py compute <date>   # → data/rotation/<date>/week.json + תקציר למסך
    python3 scripts/build_rotation.py render  <date>   # week.json + narrative.json → data/sectors/sectors-<date>.html
                                                       #   + מיזוג ל-data/sector_history.json + data/rotation/index.json

<date> = תאריך התיקייה (שבת). יום הנתונים = השורה האחרונה בקובצי ההיסטוריה (שישי).
קלט: data/rotation/<date>/{hist_<SYM>.csv ×16, breadth.csv, industry-group-rankings.csv, heatmap.csv, manifest.txt}
המתודולוגיה (ציון רוטציה, רביעים, CRS): docs/rotation/METHOD.md. stdlib בלבד.
"""
import base64
import calendar
import csv
import glob
import html
import json
import os
import re
import sys
from datetime import date, datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
HIST_PATH = os.path.join(DATA, "sector_history.json")
MAX_WEEKS = 26

SECTOR_SYMS = ["SRIT", "SRHC", "SRFI", "SRCD", "SRCS", "SREN", "SRIN", "SRMA", "SRRE", "SRUT", "SRTS"]
MACRO_SYMS = ["TNX", "DXY"]          # + חוזה נפט CL* וזהב GC* (שם החוזה משתנה)
ETF = {"SRIT": "XLK", "SRHC": "XLV", "SRFI": "XLF", "SRCD": "XLY", "SRCS": "XLP", "SREN": "XLE",
       "SRIN": "XLI", "SRMA": "XLB", "SRRE": "XLRE", "SRUT": "XLU", "SRTS": "XLC"}
HE = {"XLK": "טכנולוגיה", "XLV": "בריאות", "XLF": "פיננסים", "XLY": "צריכה מחזורית", "XLP": "צריכה בסיסית",
      "XLE": "אנרגיה", "XLI": "תעשייה", "XLB": "חומרים", "XLRE": "נדל\"ן", "XLU": "תשתיות", "XLC": "תקשורת"}
DESC = {"XLK": "שבבים, תוכנה", "XLC": "גוגל, מטא, טלקום", "XLV": "תרופות, שירותי רפואה", "XLP": "מזון, משקאות",
        "XLY": "אמזון, טסלה, קמעונאות", "XLE": "נפט וגז", "XLF": "בנקים, ביטוח", "XLB": "כימיקלים, מתכות",
        "XLI": "תעשייה, תחבורה", "XLRE": "נדל\"ן מניב", "XLU": "חשמל, גז, מים"}
BREADTH_NAMES = {"S&P 500 Consumer Discretionary": "XLY", "S&P 500 Consumer Staples": "XLP", "S&P 500 Energy": "XLE",
                 "S&P 500 Financials": "XLF", "S&P 500 Health Care": "XLV", "S&P 500 Industrials": "XLI",
                 "S&P 500 Information Technology": "XLK", "S&P 500 Materials": "XLB", "S&P 500 Real Estate": "XLRE",
                 "S&P 500 Comm Services": "XLC", "S&P 500 Utilities": "XLU"}
ORDER = ["XLK", "XLC", "XLV", "XLP", "XLY", "XLE", "XLF", "XLB", "XLI", "XLRE", "XLU"]
QHE = {"leading": "🟢 מוביל", "improving": "🔵 משתפר", "improving_early": "🔵 משתפר מוקדם",
       "weakening": "🟡 נחלש", "lagging": "🔴 מפגר"}
QCOLOR = {"leading": "#2e7d32", "improving": "#0b5394", "improving_early": "#0b5394", "weakening": "#b26a00", "lagging": "#c62828"}
CRS_HE = {"inflecting_up": "חצתה מעלה השבוע", "rising": "מעל הממוצע ועולה", "flat": "על הממוצע",
          "inflecting_down": "מעל הממוצע אך מתגלגלת מטה", "falling": "מתחת לממוצע ויורדת",
          "falling_narrowing": "מתחת לממוצע, הפער מצטמצם"}
CRS_PTS = {"inflecting_up": 15, "rising": 12, "flat": 7, "inflecting_down": 3, "falling": 0, "falling_narrowing": 0}


# ---------------------------------------------------------------- קלט
def folder(d):
    return os.path.join(DATA, "rotation", d)


def load_hist(path):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            t = (r.get("Time") or "").strip()
            if not re.match(r"\d{4}-\d{2}-\d{2}$", t):
                continue      # שורת footer "Downloaded from Barchart..."
            try:
                rows.append((date.fromisoformat(t), float(r["Latest"])))
            except (KeyError, ValueError):
                continue
    rows.sort()
    return rows


def hist_files(d):
    out = {}
    for p in glob.glob(os.path.join(folder(d), "hist_*.csv")):
        out[os.path.basename(p)[5:-4]] = p
    return out


def contract(files, prefix):
    c = sorted(k for k in files if k.startswith(prefix) and len(k) > 2 and k[2].isalpha())
    return c[0] if c else None


def load_breadth(d):
    out = {}
    with open(os.path.join(folder(d), "breadth.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                out[(r.get("Name") or "").strip()] = {k.lower(): int(r[k]) for k in ("MA5", "MA20", "MA50", "MA100", "MA150", "MA200")}
            except (KeyError, ValueError, TypeError):
                continue
    return out


def load_rankings(d):
    rows = []
    with open(os.path.join(folder(d), "industry-group-rankings.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            n = (r.get("Name") or "").strip()
            try:
                rows.append({"name": n, "alpha": float((r.get("Wtd Alpha") or "x").replace("+", "")),
                             "chg": float((r.get("Wtd. Alpha Change") or "x").replace("+", "")), "n": int(r.get("# of Stocks") or "x")})
            except (ValueError, TypeError):
                continue      # שורת footer / שורה ריקה
    return rows


def load_heatmap(d):
    rows = []
    with open(os.path.join(folder(d), "heatmap.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                rows.append({"name": (r.get("Industry") or "").strip(), "perf": float(r.get("Perf_1M") or "x")})
            except (ValueError, TypeError):
                continue
    return rows


def is_group_row(name):
    return name.startswith(("Indices", "ETFS", "Sectors"))


# ---------------------------------------------------------------- חישובים
def minus_months(d, m):
    y, mo = d.year, d.month - m
    while mo <= 0:
        mo += 12
        y -= 1
    return date(y, mo, min(d.day, calendar.monthrange(y, mo)[1]))


def close_on_or_before(rows, d):
    best = None
    for dt, c in rows:
        if dt <= d:
            best = (dt, c)
        else:
            break
    return best


def pct(a, b):
    return round((a / b - 1) * 100, 2)


def sma(vals, n):
    return round(sum(vals[-n:]) / n, 4) if len(vals) >= n else None


def perf_block(rows):
    closes = [c for _, c in rows]
    last = rows[-1][0]
    cur = closes[-1]
    r = {"close": cur, "date": str(last), "1d": pct(cur, closes[-2]), "1w": pct(cur, closes[-6])}
    for k, m in (("1m", 1), ("3m", 3), ("6m", 6), ("1y", 12)):
        ref = close_on_or_before(rows, minus_months(last, m))
        r[k] = pct(cur, ref[1])
    ytd = close_on_or_before(rows, date(last.year - 1, 12, 31))
    r["ytd"] = pct(cur, ytd[1]) if ytd else None
    for n in (20, 50, 100, 200):
        r["ma%d" % n] = sma(closes, n)
    yr = closes[-252:]
    r["hi52"], r["lo52"] = max(yr), min(yr)
    r["off_hi52"] = pct(cur, r["hi52"])
    return r


def crs_block(sec_rows, spx_rows):
    spx = dict(spx_rows)
    crs = [(d, c / spx[d]) for d, c in sec_rows if d in spx]
    vals = [v for _, v in crs]
    ma = [None] * len(vals)
    for i in range(20, len(vals)):
        ma[i] = sum(vals[i - 20:i + 1]) / 21
    cur, curma, prev5, prev5ma = vals[-1], ma[-1], vals[-6], ma[-6]
    gap = (cur / curma - 1) * 100
    gap5 = (prev5 / prev5ma - 1) * 100
    hi10 = max(vals[-10:])
    if prev5 < prev5ma and cur > curma:
        st = "inflecting_up"
    elif abs(gap) < 0.2:
        st = "flat"
    elif cur > curma:
        st = "inflecting_down" if (gap < gap5 and cur < hi10) else "rising"
    else:
        st = "falling_narrowing" if gap > gap5 else "falling"
    return {"val": round(cur, 4), "ma": round(curma, 4), "gap_pct": round(gap, 2), "gap5_pct": round(gap5, 2),
            "val_5d_ago": round(prev5, 4), "ma_5d_ago": round(prev5ma, 4), "state": st,
            "series": [(str(d), round(v, 4), round(m, 4) if m else None) for (d, v), m in zip(crs[-65:], ma[-65:])]}


def gap_pts(g):
    return 18 if g >= 6 else 13 if g >= 3 else 8 if g >= 1 else 5 if g == 0 else 3 if g >= -2 else 1 if g >= -5 else 0


def lvl_pts(p):
    return 15 if p >= 80 else 12 if p >= 65 else 8 if p >= 50 else 4 if p >= 35 else 0


def breadth_dir(delta):
    if delta is None:
        return "unknown", 5
    if delta >= 15:
        return "rising_sharp", 10
    if delta >= 4:
        return "rising", 8
    if delta > -4:
        return "flat", 5
    if delta > -15:
        return "falling", 2
    return "collapsing", 0


def load_history():
    try:
        with open(HIST_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"meta": {"version": 1, "created": str(date.today())}, "weeks": [], "entries_log": []}


def prev_week(hist, d):
    ws = [w for w in hist.get("weeks", []) if w.get("date") and w["date"] < d]
    return ws[-1] if ws else None


def fri_of(d):
    """יום שישי האחרון שלפני/בתאריך d (d = שבת → אתמול)."""
    dd = date.fromisoformat(d)
    while dd.weekday() != 4:
        dd -= timedelta(days=1)
    return dd


def compute(d):
    files = hist_files(d)
    cl, gc = contract(files, "CL"), contract(files, "GC")
    series = {s: load_hist(files[s]) for s in ["SPX"] + SECTOR_SYMS + MACRO_SYMS + [x for x in (cl, gc) if x]}
    last = series["SPX"][-1][0]
    res = {s: perf_block(rows) for s, rows in series.items()}
    for s in SECTOR_SYMS:
        res[s]["crs"] = crs_block(series[s], series["SPX"])
    for k in ("1w", "1m", "3m", "6m", "1y"):
        for i, s in enumerate(sorted(SECTOR_SYMS, key=lambda x: -res[x][k])):
            res[s].setdefault("rank", {})[k] = i + 1

    br = load_breadth(d)
    spx_br = br.get("S&P 500 Index") or {}
    brx = {etf: br[name] for name, etf in BREADTH_NAMES.items() if name in br}
    hist = load_history()
    prev = prev_week(hist, d) or {}
    psec = prev.get("sectors", {})

    week = {"date": d, "data_date": str(last), "source": "csv_drive_rotation_" + d,
            "spx_perf": {k: res["SPX"][k] for k in ("1w", "1m", "3m", "6m", "ytd", "1y")},
            "spx_levels": {k: res["SPX"][k] for k in ("close", "ma20", "ma50", "ma200", "hi52", "off_hi52")},
            "spx_breadth": spx_br, "spx_breadth_prev": prev.get("spx_breadth"), "sectors": {}}
    for sym in SECTOR_SYMS:
        etf = ETF[sym]
        r, p, b = res[sym], psec.get(etf, {}), brx.get(etf, {})
        rk = r["rank"]
        gap = rk["6m"] - rk["1m"]
        prk = (p.get("rank") or {}).get("1m")
        wow = (prk - rk["1m"]) if prk else None
        c1 = gap_pts(gap) + (max(0, min(12, 6 + 3 * wow)) if wow is not None else 6)
        pb = p.get("pct_above_ma50")
        d50 = (b["ma50"] - pb) if (pb is not None and "ma50" in b) else None
        bdir, dpts = breadth_dir(d50)
        c2 = (lvl_pts(b["ma50"]) if "ma50" in b else 0) + dpts
        st = r["crs"]["state"]
        c4 = CRS_PTS[st]
        raw, mx = c1 + c2 + c4, 70
        score = round(raw / mx * 100)
        strong = rk["6m"] <= 5
        quad = ("leading" if score >= 55 else "weakening") if strong else ("improving" if score >= 55 else "lagging")
        flags = []
        if quad == "lagging" and st == "inflecting_up" and (d50 or 0) >= 10:
            quad, flags = "improving_early", ["משתפר מוקדם"]
        if quad == "leading" and st == "inflecting_down":
            flags.append("CRS מתגלגל")
        week["sectors"][etf] = {
            "name_he": HE[etf], "index_sym": sym, "close": r["close"],
            "perf": {k: r[k] for k in ("1d", "1w", "1m", "3m", "6m", "ytd", "1y")},
            "rank": {k: rk[k] for k in ("1w", "1m", "3m", "6m", "1y")}, "rank_gap": gap, "rank_1m_wow": wow,
            "ma": {k: r[k] for k in ("ma20", "ma50", "ma100", "ma200")},
            "above_ma200": r["close"] > r["ma200"], "above_ma50": r["close"] > r["ma50"],
            "hi52": r["hi52"], "off_hi52": r["off_hi52"],
            "pct_above_ma5": b.get("ma5"), "pct_above_ma20": b.get("ma20"), "pct_above_ma50": b.get("ma50"),
            "pct_above_ma100": b.get("ma100"), "pct_above_ma200": b.get("ma200"),
            "pct_above_ma50_prev": pb, "breadth_delta_wow": d50, "breadth_direction": bdir,
            "crs_val": r["crs"]["val"], "crs_ma": r["crs"]["ma"], "crs_gap_pct": r["crs"]["gap_pct"],
            "crs_gap_pct_5d_ago": r["crs"]["gap5_pct"], "crs_state": st, "crs_series": r["crs"]["series"],
            "new_highs_3m": None, "new_lows_3m": None, "bearish_div_count": None, "bullish_div_count": None,
            "squeeze_count": None, "iv_rank": None,
            "score_components": {"rank_momentum": c1, "breadth": c2, "highs_lows": None, "crs": c4, "signals": None,
                                 "raw": raw, "max": mx},
            "rotation_score": score, "rotation_score_prev": p.get("rotation_score"),
            "quadrant": quad, "quadrant_prev": p.get("quadrant"), "flags": flags}

    im = {}
    for key, s in (("us10y", "TNX"), ("dxy", "DXY"), ("oil", cl), ("gold", gc)):
        if s and s in res:
            im[key] = dict({k: res[s][k] for k in ("close", "1d", "1w", "1m", "3m", "ma20", "ma50", "ma200", "hi52", "lo52", "off_hi52")}, sym=s)
    week["intermarket_data"] = im

    rk_rows = load_rankings(d)
    ind = [x for x in rk_rows if not is_group_row(x["name"]) and x["n"] >= 10]
    week["radar"] = {"groups": len(ind), "positive": sum(1 for x in ind if x["chg"] > 0),
                     "inflows": sorted(ind, key=lambda x: -x["chg"])[:14],
                     "outflows": sorted(ind, key=lambda x: x["chg"])[:14],
                     "top_alpha": sorted(ind, key=lambda x: -x["alpha"])[:8],
                     "sector_rows": [x for x in rk_rows if x["name"].startswith("Indices S&P 500")]}
    hm = load_heatmap(d)
    hind = [x for x in hm if not is_group_row(x["name"])]
    week["heatmap"] = {"industries": len(hind), "positive": sum(1 for x in hind if x["perf"] > 0),
                       "top": hind[:15], "bottom": hind[-15:][::-1],
                       "sector_rows": [x for x in hm if x["name"].startswith("Indices S&P 500")],
                       "all": {x["name"]: x["perf"] for x in hind}}
    week["radar"]["all"] = {x["name"]: [x["alpha"], x["chg"], x["n"]] for x in ind}

    # לוח הדוחות לשבוע הבא — מהאתר (TradingView)
    try:
        with open(os.path.join(DATA, "earnings.json"), encoding="utf-8") as f:
            e = json.load(f)
        week["earnings_next_week"] = [{"date": x["date"], "dow": x.get("dow"),
                                       "tickers": [(c["ticker"], c.get("when") or "") for c in x.get("companies", [])]}
                                      for x in e.get("week", []) if x.get("date", "") > str(last)]
    except (OSError, ValueError, KeyError):
        week["earnings_next_week"] = []
    week["prev_week"] = {"date": prev.get("date"), "recommendations": prev.get("recommendations"),
                         "notes": prev.get("notes"), "earnings_season": prev.get("earnings_season"),
                         "spx_perf": prev.get("spx_perf")}
    week["weeks_in_history"] = len(hist.get("weeks", []))
    return week


# ---------------------------------------------------------------- תקציר לרוטינה
def fmt(v, d=2):
    return "—" if v is None else ("%+.*f%%" % (d, v))


def digest(w):
    s = []
    S = w["sectors"]
    s.append(f"== דוח רוטציה {w['date']} · נתונים עד {w['data_date']} · {w['weeks_in_history']} שבועות בהיסטוריה (קודם: {w['prev_week'].get('date')}) ==")
    sp, sb, sbp = w["spx_perf"], w["spx_breadth"], w.get("spx_breadth_prev") or {}
    s.append(f"S&P 500 {w['spx_levels']['close']}: שבוע {fmt(sp['1w'])} · חודש {fmt(sp['1m'])} · 3ח {fmt(sp['3m'])} · 6ח {fmt(sp['6m'])} · שנה {fmt(sp['1y'])} · {fmt(w['spx_levels']['off_hi52'])} מהשיא {w['spx_levels']['hi52']}")
    s.append(f"רוחב השוק (מעל MA50): {sb.get('ma50')}% (לפני שבוע {sbp.get('ma50')}%) · MA20 {sb.get('ma20')}% · MA200 {sb.get('ma200')}%")
    s.append("")
    s.append("etf  סקטור          סגירה    שבוע    חודש    3ח     6ח    שנה | דירוג ש/ח/3/6/ש  פער | רוחב50 Δ   כיוון | CRS מצב (פער%, לפני5י) | ציון(קודם) רביע(קודם) >MA200")
    for etf in sorted(S, key=lambda k: S[k]["rank"]["1m"]):
        x = S[etf]; rk = x["rank"]; p = x["perf"]
        s.append(f"{etf:4} {x['name_he']:13} {x['close']:8.2f} {fmt(p['1w']):>7} {fmt(p['1m']):>7} {fmt(p['3m']):>6} {fmt(p['6m']):>6} {fmt(p['1y']):>6} | "
                 f"{rk['1w']:2}/{rk['1m']:2}/{rk['3m']:2}/{rk['6m']:2}/{rk['1y']:2} {x['rank_gap']:+d} | "
                 f"{str(x['pct_above_ma50']):>3}% {('%+d' % x['breadth_delta_wow']) if x['breadth_delta_wow'] is not None else '—':>4} {x['breadth_direction']:12} | "
                 f"{x['crs_state']:18} ({x['crs_gap_pct']:+.2f}, {x['crs_gap_pct_5d_ago']:+.2f}) | {x['rotation_score']:3} ({x['rotation_score_prev']}) {x['quadrant']} ({x['quadrant_prev']}) {'כן' if x['above_ma200'] else 'לא'} "
                 f"MA20 {x['ma']['ma20']:.0f} MA50 {x['ma']['ma50']:.0f} MA200 {x['ma']['ma200']:.0f}")
    s.append("")
    for k, v in w["intermarket_data"].items():
        s.append(f"{k:6} {v['sym']:6} {v['close']:>9} שבוע {fmt(v['1w'])} חודש {fmt(v['1m'])} 3ח {fmt(v['3m'])} | MA20 {v['ma20']} MA50 {v['ma50']} MA200 {v['ma200']} | שיא52 {v['hi52']} ({fmt(v['off_hi52'])}) שפל {v['lo52']}")
    r = w["radar"]
    s.append(f"\nמכ\"ם: {r['positive']}/{r['groups']} קבוצות עם שינוי אלפא חיובי. נכנס: " + " · ".join(f"{x['name']} {x['chg']:+.2f} (אלפא {x['alpha']:.0f}, n={x['n']})" for x in r["inflows"]))
    s.append("יוצא: " + " · ".join(f"{x['name']} {x['chg']:+.2f} (אלפא {x['alpha']:.0f})" for x in r["outflows"]))
    s.append("מדדי הסקטור במכ\"ם: " + " · ".join(f"{x['name'].replace('Indices S&P 500 ', '')} {x['chg']:+.2f}" for x in r["sector_rows"]))
    h = w["heatmap"]
    s.append(f"\nמפת חום חודשית: {h['positive']}/{h['industries']} תעשיות חיוביות. עליונות: " + " · ".join(f"{x['name']} {x['perf']:+.1f}" for x in h["top"]))
    s.append("תחתונות: " + " · ".join(f"{x['name']} {x['perf']:+.1f}" for x in h["bottom"]))
    s.append("מדדי הסקטור במפה: " + " · ".join(f"{x['name'].replace('Indices S&P 500 ', '')} {x['perf']:+.1f}" for x in h["sector_rows"]))
    s.append("\nדוחות בשבוע הבא: " + " | ".join(f"{x['date']} ({x['dow']}): " + ", ".join(t for t, _ in x["tickers"]) for x in w["earnings_next_week"]))
    pw = w["prev_week"]
    if pw.get("recommendations"):
        s.append("\nהקריאות של שבוע שעבר (לדין וחשבון):")
        for rec in pw["recommendations"]:
            s.append(f"  {rec.get('sector')}: {rec.get('action')} — {rec.get('trigger')} [{rec.get('confidence')}]")
    if pw.get("notes"):
        s.append("הערות שבוע שעבר: " + str(pw["notes"])[:600])
    if pw.get("earnings_season"):
        s.append("מודול הדוחות (מהשבוע שעבר): " + json.dumps(pw["earnings_season"], ensure_ascii=False)[:900])
    return "\n".join(s)


# ---------------------------------------------------------------- HTML
CSS = """
:root{--acc:#0b5394;--g:#2e7d32;--r:#c62828;--amb:#b26a00;--ink:#1f2933;--mut:#5f6b76;--line:#e3e7eb;--soft:#f4f7fa}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);font-family:"Segoe UI","Heebo","Arial Hebrew",Arial,sans-serif;line-height:1.8;font-size:16px}
.wrap{max-width:860px;margin:0 auto;padding:40px 18px 60px}
h1{font-size:34px;margin:0 0 4px;color:var(--acc);line-height:1.3}
.sub{color:var(--mut);font-size:14px;margin-bottom:28px}
h2{font-size:22px;margin:46px 0 6px;color:var(--ink);border-bottom:2px solid var(--acc);padding-bottom:6px;line-height:1.4}
h2 .ch{color:var(--acc);font-weight:600;font-size:15px;display:block}
h3{font-size:17px;margin:26px 0 6px;color:var(--acc)}
p{margin:8px 0}
.box{background:var(--soft);border-right:4px solid var(--acc);padding:16px 20px;margin:18px 0;border-radius:4px}
.box h3{margin-top:0}
.box ol,.box ul{margin:6px 0;padding-right:22px}
.tag{display:inline-block;background:var(--amb);color:#fff;font-size:12px;padding:1px 10px;border-radius:10px;margin-bottom:4px}
table{width:100%;border-collapse:collapse;margin:12px 0;font-size:14.5px}
th{background:var(--soft);text-align:right;padding:8px 10px;border-bottom:2px solid var(--line);font-weight:600;color:var(--mut);font-size:13px}
td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
td.n,th.n{text-align:center;font-variant-numeric:tabular-nums;white-space:nowrap}
.kv b{direction:ltr;unicode-bidi:isolate}
.sw{display:block;font-size:13px;color:var(--mut);margin-top:6px}
.up{color:var(--g)} .dn{color:var(--r)} .mu{color:var(--mut)}
.pill{display:inline-block;padding:0 8px;border-radius:10px;font-size:12.5px;white-space:nowrap}
.frozen{background:#fde9e9;color:var(--r)} .held{background:#e8f3ea;color:var(--g)} .watch{background:#e6eef7;color:var(--acc)} .out{background:#eee;color:var(--mut)}
figure{margin:14px 0;overflow-x:auto}
figure>svg{min-width:600px}
.tw{overflow-x:auto}
figcaption{font-size:13px;color:var(--mut);text-align:center}
svg{max-width:100%;height:auto;display:block;margin:0 auto}
.appendix{border-top:2px dashed var(--line);background:#fafafa;margin-top:60px;padding:20px 22px 30px;border-radius:6px}
.appendix h2{border-bottom-color:#bbb;color:#555;font-size:19px}
.appendix h3{color:#666;font-size:15.5px}
.appendix table{font-size:13px}
.small{font-size:13px;color:var(--mut)}
.disc{font-size:12.5px;color:var(--mut);border-top:1px solid var(--line);margin-top:30px;padding-top:12px}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:12px 0}
.kv div{background:#fff;border:1px solid var(--line);border-radius:6px;padding:10px 12px}
.kv b{display:block;font-size:20px;font-variant-numeric:tabular-nums}
.kv span{font-size:13px;color:var(--mut)}
@media (max-width:600px){table{font-size:12.5px;min-width:640px} td,th{padding:6px 5px} h1{font-size:28px} .tw{margin:0 -18px;padding:0 18px}}
"""


def e(x):
    return html.escape(str(x))


def pc(v, d=1):
    if v is None:
        return "—"
    return '<span dir="ltr" style="unicode-bidi:isolate">' + ("%+.*f%%" % (d, v)).replace("-", "−") + "</span>"


def col(v):
    return "var(--g)" if (v or 0) > 0 else "var(--r)" if (v or 0) < 0 else "var(--mut)"


def dmy(iso):
    y, m, d = iso.split("-")
    return f"{int(d)}.{int(m)}.{y}"


def dm(iso):
    y, m, d = iso.split("-")
    return f"{int(d)}.{int(m)}"


def tbl(head, rows_html):
    return '<div class="tw"><table><thead><tr>' + "".join(head) + "</tr></thead><tbody>" + rows_html + "</table></div>"


def flow_svg(w, nar):
    S = w["sectors"]
    moves = [(S[k]["name_he"], S[k]["pct_above_ma50_prev"], S[k]["pct_above_ma50"], S[k]["breadth_delta_wow"])
             for k in ORDER if S[k]["breadth_delta_wow"] is not None]
    out_pairs = sorted([m for m in moves if m[3] < 0], key=lambda m: m[3])[:6]
    in_pairs = sorted([m for m in moves if m[3] > 0], key=lambda m: -m[3])[:6]
    if not out_pairs:
        out_pairs = sorted(moves, key=lambda m: m[3])[:2]

    def box(x, title, color, pairs, note):
        s = f'<rect x="{x}" y="40" width="330" height="{70 + 30 * len(pairs) + 56}" rx="10" fill="#fff" stroke="{color}" stroke-width="2"/>'
        s += f'<text x="{x + 165}" y="70" text-anchor="middle" font-size="19" font-weight="700" fill="{color}">{title}</text>'
        s += f'<text x="{x + 165}" y="92" text-anchor="middle" font-size="12" fill="#5f6b76">אחוז המניות מעל ממוצע 50 — לפני שבוע ועכשיו</text>'
        y = 122
        for name, a, b, _ in pairs:
            s += f'<text x="{x + 310}" y="{y}" text-anchor="end" font-size="15" fill="#1f2933">{e(name)}</text>'
            s += f'<text x="{x + 20}" y="{y}" text-anchor="start" font-size="15" font-weight="600" fill="{color}">{b}% ← {a}%</text>'
            y += 30
        for k, ln in enumerate((note or "").split("|")):
            s += f'<text x="{x + 165}" y="{y + 8 + k * 17}" text-anchor="middle" font-size="12.5" fill="#5f6b76">{e(ln.strip())}</text>'
        return s
    hgt = 70 + 30 * max(len(out_pairs), len(in_pairs)) + 56 + 60
    svg = f'<svg viewBox="0 0 760 {hgt}" width="760" height="{hgt}" xmlns="http://www.w3.org/2000/svg" style="direction:ltr">'
    svg += box(410, "הכסף יצא", "#c62828", out_pairs, nar.get("flow_out_note", ""))
    svg += box(20, "הכסף נכנס", "#2e7d32", in_pairs, nar.get("flow_in_note", ""))
    svg += '<defs><marker id="ar" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5f6b76"/></marker></defs>'
    svg += '<path d="M405 150 L360 150" stroke="#5f6b76" stroke-width="3" fill="none" marker-end="url(#ar)"/></svg>'
    return svg


def quad_svg(w):
    S = w["sectors"]
    Wd, Hd, L, Rm, T, B = 760, 420, 50, 20, 20, 50

    def X(rank):
        return L + (11 - rank) / 10 * (Wd - L - Rm)

    def Y(score):
        return T + (100 - score) / 100 * (Hd - T - B)
    s = f'<svg viewBox="0 0 {Wd} {Hd}" width="{Wd}" height="{Hd}" xmlns="http://www.w3.org/2000/svg" style="direction:ltr;font-family:Segoe UI,Arial">'
    xm, ym = X(5.5), Y(55)
    s += f'<rect x="{xm}" y="{T}" width="{Wd - Rm - xm}" height="{ym - T}" fill="#e8f3ea"/><rect x="{L}" y="{T}" width="{xm - L}" height="{ym - T}" fill="#e6eef7"/>'
    s += f'<rect x="{xm}" y="{ym}" width="{Wd - Rm - xm}" height="{Hd - B - ym}" fill="#fbf1e3"/><rect x="{L}" y="{ym}" width="{xm - L}" height="{Hd - B - ym}" fill="#f9e6e6"/>'
    for lab, x, y in (("מוביל", Wd - Rm - 8, T + 18), ("משתפר", L + 8, T + 18), ("נחלש", Wd - Rm - 8, Hd - B - 8), ("מפגר", L + 8, Hd - B - 8)):
        s += f'<text x="{x}" y="{y}" text-anchor="{"end" if x > Wd / 2 else "start"}" font-size="14" font-weight="700" fill="#5f6b76">{lab}</text>'
    for sc in (0, 25, 50, 75, 100):
        s += f'<text x="{L - 6}" y="{Y(sc) + 4}" text-anchor="end" font-size="11" fill="#5f6b76">{sc}</text>'
    for rk in range(1, 12):
        s += f'<text x="{X(rk)}" y="{Hd - B + 16}" text-anchor="middle" font-size="11" fill="#5f6b76">{rk}</text>'
    s += f'<text x="{(L + Wd - Rm) / 2}" y="{Hd - 8}" text-anchor="middle" font-size="12" fill="#5f6b76">דירוג 6 חודשים (1 = החזק ביותר, בימין) · ציר אנכי: ציון זרימת כסף 0–100 · קו מקווקו: מהשבוע שעבר</text>'
    hist = load_history()
    prev = prev_week(hist, w["date"]) or {}
    for etf in ORDER:
        d = S[etf]
        p = (prev.get("sectors") or {}).get(etf) or {}
        x, y = X(d["rank"]["6m"]), Y(d["rotation_score"])
        if p.get("rotation_score") is not None and (p.get("rank") or {}).get("6m"):
            px, py = X(p["rank"]["6m"]), Y(p["rotation_score"])
            s += f'<line x1="{px:.0f}" y1="{py:.0f}" x2="{x:.0f}" y2="{y:.0f}" stroke="#9aa5b1" stroke-dasharray="4 3" stroke-width="1.5"/><circle cx="{px:.0f}" cy="{py:.0f}" r="3" fill="#9aa5b1"/>'
        s += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="7" fill="{QCOLOR[d["quadrant"]]}" stroke="#fff" stroke-width="1.5"/>'
        dy = 20 if d["rank"]["6m"] == 11 else -11
        s += f'<text x="{x:.0f}" y="{y + dy:.0f}" text-anchor="middle" font-size="12" font-weight="700" fill="#1f2933">{etf}</text>'
    return s + "</svg>"


def crs_spark(ser, w=220, h=60):
    ser = [t for t in ser if t[2]]
    if len(ser) < 5:
        return ""
    vals = [t[1] for t in ser] + [t[2] for t in ser]
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1

    def pt(i, v):
        return f"{i / (len(ser) - 1) * (w - 4) + 2:.1f},{h - 2 - (v - lo) / rng * (h - 4):.1f}"
    p1 = " ".join(pt(i, t[1]) for i, t in enumerate(ser))
    p2 = " ".join(pt(i, t[2]) for i, t in enumerate(ser))
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" style="direction:ltr;display:inline-block">'
            f'<polyline points="{p2}" fill="none" stroke="#9aa5b1" stroke-width="1.5"/><polyline points="{p1}" fill="none" stroke="#0b5394" stroke-width="2"/></svg>')


def rank_cell(v, extra=""):
    cls = "up" if v <= 3 else "dn" if v >= 9 else ""
    return f'<td class="n {cls}"><strong>{v}</strong>{extra}</td>'


def paras(x):
    if isinstance(x, str):
        x = [x]
    return "".join(f"<p>{t}</p>" for t in (x or []))


def render_html(w, nar):
    S, sp = w["sectors"], w["spx_perf"]
    fri = w["data_date"]
    week_no = nar.get("week_no") or (w["weeks_in_history"] + 1)
    prev_fri = str(date.fromisoformat(fri) - timedelta(days=7))
    season = nar.get("season_tag", "")
    H = []
    H.append(f'<h1>לאן זרם הכסף השבוע?</h1><div class="sub">דוח רוטציה סקטוריאלית שבועי | שבוע המסחר: שישי {dm(prev_fri)} – שישי {dmy(fri)} | שבוע {week_no} למעקב | נתונים: Barchart (קובצי CSV, {dmy(w["date"])}){(" · " + e(season)) if season else ""}</div>')
    H.append('<div class="box"><h3>בחמישה משפטים</h3><ol>' + "".join(f"<li>{t}</li>" for t in nar["five"]) + "</ol></div>")
    H.append('''<div class="box"><h3>ארבעה מושגים בדקה</h3><ul>
<li><strong>סקטור</strong> — ענף כלכלי (טכנולוגיה, בנקים, אנרגיה…). מדד S&amp;P 500 מחולק ל-11 סקטורים.</li>
<li><strong>רוחב</strong> — כמה מהמניות בסקטור נמצאות מעל הממוצע של 50 הימים האחרונים. רוחב גבוה = רוב המניות עולות, לא רק כמה ענקיות.</li>
<li><strong>רוטציה</strong> — מעבר של כסף גדול (קרנות, מוסדיים) מסקטור לסקטור. אנחנו מנסים לזהות אותו מוקדם, ורק אחרי אישור.</li>
<li><strong>נקודת יציאה (סטופ)</strong> — רמת מחיר שנקבעה מראש; אם השוק סוגר מתחתיה — יוצאים, בלי ויכוח.</li>
</ul></div>''')
    # פרק 1
    rows = ""
    for etf in sorted(ORDER, key=lambda k: S[k]["rank"]["1m"]):
        d = S[etf]
        rk = d["rank"]
        rows += (f'<tr><td><strong>{e(d["name_he"])}</strong> <span class="mu">({DESC[etf]})</span></td>' + rank_cell(rk["1y"]) + rank_cell(rk["3m"]) + rank_cell(rk["6m"]) + rank_cell(rk["1m"])
                 + rank_cell(rk["1w"], f'<br><span class="small" style="color:{col(d["perf"]["1w"])}">{pc(d["perf"]["1w"], 2)}</span>') + f'<td>{nar.get("what", {}).get(etf, "")}</td></tr>')
    H.append(f'<h2><span class="ch">פרק 1</span>{nar["ch1_title"]}</h2>'
             f'<p>דירוג 11 הסקטורים (1 = החזק) בחמישה אופקי זמן, מחושב מסגירות המדדים הסקטוריאליים של S&amp;P. מדד S&amp;P 500 עצמו: שבוע {pc(sp["1w"], 2)} · חודש {pc(sp["1m"], 2)} · 3 חודשים {pc(sp["3m"], 2)} · 6 חודשים {pc(sp["6m"], 2)} · שנה {pc(sp["1y"], 2)}.</p>'
             + tbl(["<th>סקטור</th>", '<th class="n">שנה</th>', '<th class="n">3 חודשים</th>', '<th class="n">6 חודשים</th>', '<th class="n">חודש</th>', '<th class="n">שבוע</th>', "<th>מה זה אומר בפשטות</th>"], rows)
             + f'<p class="sw"><strong>איך קוראים את זה:</strong> {nar.get("ch1_sowhat", "חזק בכל העמודות = מגמה מבוססת. חזק בשנה וחלש בחודש = הכסף אולי עוזב. חלש בחצי שנה וחזק בחודש = מועמד לרוטציה — מועמד בלבד עד שיש שבוע אישור שני.")}</p>')
    # פרק 2
    im = w["intermarket_data"]
    sb, sbp = w["spx_breadth"], w.get("spx_breadth_prev") or {}
    kv = ""
    for key, label, fmt_fn in (("us10y", "ריבית השוק (אג\"ח 10 שנים)", lambda v: f"{v:.2f}%"), ("dxy", "מדד הדולר", lambda v: f"{v:.2f}"),
                               ("oil", "נפט (חוזה " + im.get("oil", {}).get("sym", "") + ")", lambda v: f"${v:.2f}"), ("gold", "זהב (חוזה " + im.get("gold", {}).get("sym", "") + ")", lambda v: f"${v:,.0f}")):
        if key in im:
            kv += f'<div><span>{e(label)}</span><b>{fmt_fn(im[key]["close"])}</b><span>{nar.get("intermarket_notes", {}).get(key, "")}</span></div>'
    H.append(f'<h2><span class="ch">פרק 2</span>{nar["ch2_title"]}</h2><figure>{flow_svg(w, nar)}<figcaption>אחוז המניות מעל ממוצע 50 בכל סקטור, לפני שבוע ועכשיו (Barchart, מניות גדולות). רוחב השוק כולו: {sb.get("ma50")}% (לפני שבוע {sbp.get("ma50", "—")}%).</figcaption></figure>'
             f'<h3>ארבעה מספרי רקע</h3><div class="kv">{kv}</div><h3>הסיפור של השבוע במילים פשוטות</h3>{paras(nar.get("story"))}'
             + (f'<p class="small"><strong>שקיפות:</strong> {nar["transparency"]}</p>' if nar.get("transparency") else ""))
    # פרק 3
    rows = "".join(f"<tr><td><strong>{e(a)}</strong></td><td>{b}</td><td class=\"n small\">{c}</td><td>{d}</td></tr>" for a, b, c, d in nar.get("industries", []))
    r, hm = w["radar"], w["heatmap"]
    H.append(f'<h2><span class="ch">פרק 3</span>{nar["ch3_title"]}</h2>'
             f'<p>המכ"ם התעשייתי (דירוג {r["groups"]} קבוצות תעשייה לפי Weighted Alpha ושינויו השבועי) ומפת החום החודשית: {r["positive"]} מ-{r["groups"]} קבוצות עם שינוי אלפא חיובי, ו-{hm["positive"]} מ-{hm["industries"]} חיוביות בחודש האחרון. {nar.get("ch3_intro", "")}</p>'
             + tbl(["<th>סקטור</th>", "<th>התעשיות הבולטות</th>", '<th class="n">שינוי בחודש</th>', "<th>הערה חשובה</th>"], rows)
             + (f'<p class="sw">{nar["ch3_sowhat"]}</p>' if nar.get("ch3_sowhat") else ""))
    # פרק 4
    erows = "".join(f'<tr><td class="n">{e(a)}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>' for a, b, c, d in nar.get("earnings_rows", []))
    ebox = ""
    if erows:
        ebox = (f'<div class="box"><span class="tag">{e(nar.get("earnings_tag", "מודול עונת הדוחות"))}</span><h3>{e(nar.get("earnings_title", "לוח הדוחות לשבוע הבא"))}</h3>'
                + tbl(['<th class="n">יום</th>', "<th>חברות כבדות</th>", "<th>סקטור</th>", "<th>מה זה אומר</th>"], erows)
                + f'<p class="small">{nar.get("earnings_note", "כלל הדוחות: סקטור שהכבדות שלו מדווחות בשבוע הקרוב <strong>מוקפא לכניסות</strong>; פוזיציה קיימת — לא מגדילים לתוך הדוח.")} מקור הלוח: סורק TradingView דרך האתר.</p></div>')
    prows = "".join(f'<tr><td><strong>{e(a)}</strong><br><span class="pill {e(b)}">{c}</span></td><td>{d}</td><td class="small">{ev}</td><td class="small">{f}</td></tr>' for a, b, c, d, ev, f in nar.get("positions", []))
    H.append(f'<h2><span class="ch">פרק 4</span>{nar["ch4_title"]}</h2>{ebox}<p>{nar.get("ch4_intro", "הדוח ממוקד בסקטורים — בלי בחירת מניות בודדות. הטבלה: מצב, פעולה, הרמה החשובה והסיבה.")}</p>'
             + tbl(["<th>סקטור · מצב</th>", "<th>הפעולה השבוע</th>", "<th>הרמה החשובה / הטריגר</th>", "<th>למה</th>"], prows)
             + f'<div class="box"><h3>שורה תחתונה לשבוע הקרוב</h3>{paras(nar.get("bottom_line"))}</div>')
    # נספח
    acc = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in nar.get("accountability", []))
    deep = ""
    for etf in ORDER:
        d = S[etf]
        sc = d["score_components"]
        ds = (d["rotation_score"] - d["rotation_score_prev"]) if d["rotation_score_prev"] is not None else None
        db = d["breadth_delta_wow"]
        deep += (f'<tr><td><strong>{e(d["name_he"])}</strong><br><span class="small">{etf}</span></td>'
                 f'<td class="n">{d["rotation_score"]}<br><span class="small" style="color:{col(ds)}">{("%+d" % ds) if ds is not None else "—"}</span></td>'
                 f'<td class="n">{d["rank"]["6m"]} / {d["rank"]["1m"]}<br><span class="small">פער {d["rank_gap"]:+d}</span></td>'
                 f'<td class="n">{d["pct_above_ma50"]}%<br><span class="small" style="color:{col(db)}">{("%+d" % db) if db is not None else "—"}</span></td>'
                 f'<td class="n">{d["crs_val"]:.4f}<br><span class="small">ממוצע {d["crs_ma"]:.4f} · {d["crs_gap_pct"]:+.2f}%</span></td>'
                 f'<td class="small">{CRS_HE[d["crs_state"]]}</td><td class="n small">{sc["rank_momentum"]} · {sc["breadth"]} · — · {sc["crs"]} · —</td><td>{QHE[d["quadrant"]]}</td></tr>')
    focus = nar.get("crs_focus") or [k for k in ORDER if S[k]["quadrant"] in ("leading", "weakening", "improving", "improving_early")][:6]
    sparks = "".join(f'<div style="display:inline-block;text-align:center;margin:6px 10px"><div class="small"><strong>{e(S[k]["name_he"])}</strong> ({k}) — {CRS_HE[S[k]["crs_state"]]}</div>{crs_spark(S[k]["crs_series"])}</div>' for k in focus if k in S)
    imtxt = " · ".join(f'{ {"us10y": "ריבית 10 שנים", "dxy": "דולר", "oil": "נפט", "gold": "זהב"}[k]} {v["sym"]} {v["close"]} (ממוצעים 20/50/200: {v["ma20"]}/{v["ma50"]}/{v["ma200"]}; שיא 52ש\' {v["hi52"]}, {pc(v["off_hi52"], 1)}; שבוע {pc(v["1w"], 1)}, חודש {pc(v["1m"], 1)})' for k, v in im.items())
    radar_txt = ("נכנס: " + " · ".join(f'{e(x["name"])} {x["chg"]:+.2f}' for x in r["inflows"][:10]) + ". יוצא: " + " · ".join(f'{e(x["name"])} {x["chg"]:+.2f}' for x in r["outflows"][:10])
                 + ". ברמת המדדים: " + " · ".join(f'{e(x["name"].replace("Indices S&P 500 ", ""))} {x["chg"]:+.2f}' for x in r["sector_rows"]))
    exrows = "".join(f'<tr><td>{e(a)}</td><td class="n">{b}</td><td class="n">{c}</td><td>{d}</td></tr>' for a, b, c, d in nar.get("expectations", []))
    extbl = (f'<h3>ציפיות רווח לרבעון מול ביצועי 3 חודשים (מודול עונת הדוחות)</h3>' + tbl(["<th>סקטור</th>", '<th class="n">צמיחת רווח צפויה</th>', '<th class="n">ביצוע 3 חודשים</th>', "<th>קריאה</th>"], exrows)
             + f'<p class="small">{nar.get("expectations_note", "")}</p>') if exrows else ""
    rules = nar.get("rules") or [
        "<strong>כלל השבועיים</strong> — כל כניסה חדשה דורשת שני שבועות רצופים של אישור.",
        "<strong>כלל היציאה המשולשת</strong> — יציאה דורשת רוחב + מחיר (שבירת ממוצע 50) + שיאים/שפל. לא עד בודד.",
        "<strong>כלל הדוחות</strong> — אין כניסה בשבוע שלפני דוח; פוזיציה לתוך דוח — לא מגדילים.",
        "<strong>כלל הפרבולה</strong> — אין הצטרפות לתעשייה שעלתה בקצב קלימקטי; צפייה עד עיכול.",
        "<strong>יומן כניסות</strong> — כל כניסה עם מחיר ביצוע ותאריך (ברמת סקטור, לפי בקשת המשתמש).",
        "<strong>וטו עוצמה יחסית</strong> — ציון גבוה בלי אישור CRS = \"לא מאושר\".",
        "<strong>כלל השבוע השני גם לטריגר</strong> — טריגר שנורה ממתין שבוע אישור; גם ביטול טריגר ממתין שבוע.",
        "<strong>כלל עונת הדוחות</strong> — מוקפא בשבוע שלפני הדוח; כניסה מוקדמת = שבועיים אחרי, אחרי מבחן התגובה."]
    lims = ["<strong>מחושב מקובצי CSV בלבד</strong> (16 קובצי היסטוריה יומית, טבלת הרוחב, המכ\"ם ומפת החום). מצב העוצמה מול השוק (CRS) נקבע לפי כלל מספרי (חצייה/פער מול ממוצע 21), לא מקריאת גרף.",
            "הציון מבוסס 3 מתוך 5 רכיבים (אין שיאים/שפל חדשים ואין סקרינרי דיברגנס/Squeeze בסט הקבצים) — מנורמל ל-100.",
            "מפת החום היא ממוצע שווה-משקל של מניות התעשייה; מדדי הסקטור משוקללי-שווי. הפער ביניהם הוא מידע (עלייה צרה של ענקיות).",
            "תשואת שנה מחושבת מול הסגירה לפני שנה קלנדרית."] + list(nar.get("limitations", []))
    H.append(f'''<div class="appendix"><h2>נספח למתקדמים ולמעקב המערכת</h2>
<h3>א. דין וחשבון — הקריאות של שבוע שעבר ({dmy(w["prev_week"]["date"]) if w["prev_week"].get("date") else "—"}) מול מה שקרה</h3>
{tbl(["<th>הקריאה</th>", "<th>מה קרה</th>", "<th>פסיקה</th>"], acc) if acc else "<p class='small'>שבוע בסיס — אין קריאות קודמות.</p>"}
{('<p class="small">' + nar["acc_summary"] + "</p>") if nar.get("acc_summary") else ""}
<h3>ב. מדדי העומק</h3>
<figure>{quad_svg(w)}<figcaption>מפת הרוטציה: ציון זרימת כסף מול דירוג 6 חודשים. נקודה אפורה = לפני שבוע. {nar.get("quad_caption", "")}</figcaption></figure>
{tbl(["<th>סקטור</th>", '<th class="n">ציון<br>Δ ציון</th>', '<th class="n">דירוג 6ח / 1ח<br>פער</th>', '<th class="n">רוחב MA50<br>Δ רוחב</th>', '<th class="n">עוצמה מול השוק (CRS)<br>ממוצע 21 · פער</th>', "<th>מצב CRS</th>", '<th class="n">רכיבים<br>דירוג·רוחב·שיאים·CRS·איתותים</th>', "<th>רביע</th>"], deep)}
<p class="small">הציון מנורמל מ-3 רכיבים זמינים (70 נק' → 100): מומנטום דירוג (30), רוחב (25), עוצמה מול השוק (15). שיאים/שפל ואיתותי סקרינרים אינם בסט הקבצים — "—". Δ מול רשומת השבוע הקודם. CRS = סגירת הסקטור ÷ סגירת S&amp;P 500; הממוצע = 21 ימים.</p>
<p><strong>לוח העוצמה מול השוק (65 ימי מסחר; כחול = CRS, אפור = ממוצע 21):</strong></p><div style="text-align:center">{sparks}</div>
<p class="small"><strong>בין-שוקי (סגירות {dmy(fri)}):</strong> {imtxt}. {nar.get("intermarket_read", "")}</p>
<p class="small"><strong>מכ"ם — Alpha Change בולטים (קבוצות ≥10 מניות):</strong> {radar_txt}.</p>
{extbl}
<h3>ג. הכללים הקבועים</h3><ol class="small">{"".join(f"<li>{t}</li>" for t in rules)}</ol>
<h3>ד. מגבלות השבוע</h3><ul class="small">{"".join(f"<li>{t}</li>" for t in lims)}</ul>
<h3>ה. מקורות</h3><p class="small">Barchart: hist_*.csv ×16 (Daily, 2 Years, סגירה {dmy(fri)}), breadth.csv (Percentage of Large Cap Stocks Above Their Moving Averages), industry-group-rankings.csv, heatmap.csv (1-Month, ≥10 מניות) — תיקיית Rotation/{w["date"]} בדרייב. לוח הדוחות: TradingView דרך האתר. {nar.get("sources_extra", "")}</p>
<div class="disc">דוח זה הוא ניתוח לצרכים חינוכיים בלבד ואינו ייעוץ השקעות. שבוע {week_no} למעקב · שבוע המסחר {dm(prev_fri)}–{dmy(fri)} · הופק {dmy(w["date"])} מקובצי CSV בלבד.</div></div>''')
    title = f"לאן זרם הכסף השבוע? | שבוע {week_no} | {dmy(w['date'])}"
    return f'<!DOCTYPE html>\n<html lang="he" dir="rtl">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>{e(title)}</title>\n<style>{CSS}</style>\n</head>\n<body><div class="wrap">\n{"".join(H)}\n</div></body></html>', title


# ---------------------------------------------------------------- היסטוריה
def history_record(w, nar):
    rec = {k: w[k] for k in ("date", "data_date", "source", "spx_perf", "spx_levels", "spx_breadth")}
    rec["week_no"] = nar.get("week_no") or (w["weeks_in_history"] + 1)
    rec["sectors"] = {}
    for etf, s in w["sectors"].items():
        x = {k: v for k, v in s.items() if k != "crs_series"}
        x["industries_note"] = nar.get("what", {}).get(etf)
        rec["sectors"][etf] = x
    rec["intermarket"] = {"data": w["intermarket_data"], "read_he": nar.get("intermarket_read")}
    rec["radar"] = {"breadth": f'{w["radar"]["positive"]}/{w["radar"]["groups"]} קבוצות עם שינוי אלפא חיובי; מפת חום {w["heatmap"]["positive"]}/{w["heatmap"]["industries"]} חיוביות בחודש',
                    "inflows": [{"industry": x["name"], "alpha_chg": x["chg"], "alpha": x["alpha"]} for x in w["radar"]["inflows"][:10]],
                    "outflows": [{"industry": x["name"], "alpha_chg": x["chg"], "alpha": x["alpha"]} for x in w["radar"]["outflows"][:10]]}
    for k in ("earnings_season", "recommendations", "signals", "notes", "lessons"):
        if nar.get(k) is not None:
            rec[k] = nar[k]
    rec["earnings_next_week"] = w["earnings_next_week"]
    return rec


def merge_history(rec):
    hist = load_history()
    weeks = [x for x in hist.get("weeks", []) if x.get("date") != rec["date"]]
    weeks.append(rec)
    weeks.sort(key=lambda x: x["date"])
    hist["weeks"] = weeks[-MAX_WEEKS:]
    hist.setdefault("meta", {})["last_updated"] = str(date.today())
    hist["meta"]["weeks_count"] = len(hist["weeks"])
    hist.setdefault("entries_log", [])
    with open(HIST_PATH, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=1)
    return hist


# ---------------------------------------------------------------- פקודות
def cmd_check(d):
    fd = folder(d)
    probs = []
    if not os.path.isdir(fd):
        print(f"[check] אין תיקייה {fd}")
        return 2
    files = hist_files(d)
    exp_fri = fri_of(d)
    need = ["SPX"] + SECTOR_SYMS + MACRO_SYMS
    for s in need:
        if s not in files:
            probs.append(f"חסר hist_{s}.csv")
    if not contract(files, "CL"):
        probs.append("חסר חוזה נפט (hist_CL*.csv)")
    if not contract(files, "GC"):
        probs.append("חסר חוזה זהב (hist_GC*.csv)")
    for s, p in files.items():
        rows = load_hist(p)
        if len(rows) < 260:
            probs.append(f"hist_{s}: רק {len(rows)} שורות")
        elif rows[-1][0] != exp_fri:
            probs.append(f"hist_{s}: שורה אחרונה {rows[-1][0]} ≠ שישי {exp_fri}")
    try:
        if len(load_breadth(d)) < 12:
            probs.append("breadth.csv: פחות מ-12 שורות")
    except OSError:
        probs.append("חסר breadth.csv")
    try:
        if len(load_rankings(d)) < 120:
            probs.append("industry-group-rankings.csv: פחות מ-120 שורות")
    except OSError:
        probs.append("חסר industry-group-rankings.csv")
    try:
        if len(load_heatmap(d)) < 120:
            probs.append("heatmap.csv: פחות מ-120 שורות")
    except OSError:
        probs.append("חסר heatmap.csv")
    if "SPX" in files:
        rows = load_hist(files["SPX"])
        if rows and abs(pct(rows[-1][1], rows[-6][1])) > 10:
            probs.append("SPX: תשואת 5 ימים לא סבירה")
    if probs:
        print("[check] לא מוכן:\n  " + "\n  ".join(probs))
        return 1
    print(f"[check] OK — 16 קבצי היסטוריה עד {exp_fri}, רוחב/מכ\"ם/מפת חום במקום")
    return 0


def cmd_decode(d):
    raw = os.path.join(folder(d), "raw")
    n = 0
    for p in glob.glob(os.path.join(raw, "*.b64")):
        name = os.path.basename(p)[:-4]
        with open(p, "r", encoding="utf-8") as f:
            txt = f.read().strip()
        try:
            data = base64.b64decode(txt)
        except ValueError as ex:
            print(f"[decode] {name}: {ex}")
            continue
        with open(os.path.join(folder(d), name), "wb") as f:
            f.write(data)
        os.remove(p)
        n += 1
        print(f"[decode] {name}: {len(data)} בתים")
    if os.path.isdir(raw) and not os.listdir(raw):
        os.rmdir(raw)
    print(f"[decode] {n} קבצים")
    return 0


def cmd_compute(d):
    w = compute(d)
    with open(os.path.join(folder(d), "week.json"), "w", encoding="utf-8") as f:
        json.dump(w, f, ensure_ascii=False, indent=1)
    print(digest(w))
    print(f"\n[compute] נשמר {folder(d)}/week.json")
    return 0


def cmd_render(d):
    with open(os.path.join(folder(d), "week.json"), encoding="utf-8") as f:
        w = json.load(f)
    with open(os.path.join(folder(d), "narrative.json"), encoding="utf-8") as f:
        nar = json.load(f)
    for k in ("five", "ch1_title", "ch2_title", "ch3_title", "ch4_title", "story", "positions", "bottom_line"):
        if not nar.get(k):
            print(f"[render] narrative.json חסר '{k}'")
            return 1
    page, title = render_html(w, nar)
    out_dir = os.path.join(DATA, "sectors")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "sectors-" + d + ".html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    merge_history(history_record(w, nar))
    idx_path = os.path.join(DATA, "rotation", "index.json")
    try:
        with open(idx_path, encoding="utf-8") as f:
            idx = json.load(f)
    except (OSError, ValueError):
        idx = {"reports": []}
    idx["reports"] = [r for r in idx["reports"] if r.get("date") != d]
    idx["reports"].append({"date": d, "file": "data/sectors/sectors-" + d + ".html", "title": title, "source": "build_rotation"})
    idx["reports"].sort(key=lambda r: r["date"], reverse=True)
    idx["_meta"] = {"updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    print(f"[render] {out} ({len(page)} תווים) · היסטוריה עודכנה · index.json")
    return 0


def main(argv):
    if len(argv) < 3 or argv[1] not in ("check", "decode", "compute", "render"):
        print(__doc__)
        return 2
    return {"check": cmd_check, "decode": cmd_decode, "compute": cmd_compute, "render": cmd_render}[argv[1]](argv[2])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
