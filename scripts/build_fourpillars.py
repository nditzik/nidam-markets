#!/usr/bin/env python3
"""
build_fourpillars.py — דוח "ארבעת העמודים" (הצעות לטרייד) מקובצי הסורקים שהגיעו במייל (24.10.2026).

עד 2.10 איציק כתב את הדוח בשיחת claude.ai (סקיל four-pillars-scanner) מצילומי Barchart ושמר ל-nidam-reports/trades.
מאז: relay_fourpillars_mail.py שומר את שלושת הסקרינרים (High Momentum / Phoenix Rising / Breakout Candidates)
ל-data/fourpillars/<יום המסחר>/, והסקריפט הזה עושה את **המספרים** של הסקיל: אימות הקריטריונים של כל קטגוריה
(✅/⚠️/❌), דירוג, ציון Four Pillars 0–100, דגלים אדומים (RSI חם, דוח קרוב), מצב השוק (SPY מול ממוצע 50 + המד),
ורמות (שיא 52 שבועות = טריגר, ממוצע 100 = קו ההוכחה/יציאה). **המילים** — data/fourpillars/<D>/notes.json
שרוטינת הבוקר כותבת לפי scripts/prompts/fourpillars_notes.md (כותרת, הערה לכל מניה, 3–5 מובילות, שורה תחתונה);
בלי notes הדוח מלא עם משפטי תבנית. פלט: data/fourpillars/<D>/report.json, data/trades/trades-<D>.html,
data/fourpillars/index.json, ושורה ב-data/trades.json (הטאב "הצעות לטרייד" קורא ממנו; fetch_trades ממזג גם).

ציון (לפי הסקיל): עמידה בקריטריונים 40 · RSI 50–65 → 15 (45–50/65–70 → 7) · מרחק מהשיא ≤8% → 15 (8–25% → 7) ·
שיאים חודשיים יחסית לקבוצה → 15 · Trust & Verify 15 (אין רשת — לא מבוצע, הציון מנורמל ל-85 ומסומן).
הרצה: python3 scripts/build_fourpillars.py [D]  (בלי D: כל התיקיות שאין להן דוח או שה-notes שלהן התחדש)
"""
import csv
import glob
import html
import io
import json
import os
import re
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FP = os.path.join(DATA, "fourpillars")
KINDS = ("momentum", "breakout", "phoenix")
CAT = {   # הכותרות מכילות את מילות המפתח של fetch_trades.extract_picks (דוהר/פריצה/עוף)
    "momentum": {"he": "הרכבות הדוהרות", "en": "High Momentum", "what": "עוצמה מעל 50, חוות דעת Barchart קנייה מלאה, קו המגמה בקנייה — המניות שרצות"},
    "breakout": {"he": "הקפיצים הנדרכים", "en": "Breakout Candidates", "what": "עוצמה 5-–50, חוות דעת קנייה 30–80%, קו המגמה בקנייה — מתכוננות לפריצה"},
    "phoenix": {"he": "עופות החול", "en": "Phoenix Rising", "what": "עוצמה מתחת ל-50 וחוות דעת מכירה, אבל קו המגמה כבר בקנייה — תחתית אפשרית; התנאי: כיבוש ממוצע 100"},
}
DOW = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]


def num(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "").replace("%", "").replace("+", "")
    if s in ("", "N/A", "unch"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def opinion(v):
    """'100% Buy' → (100, 'Buy'); '8% Sell' → (8, 'Sell'); 'Hold' → (None, 'Hold')."""
    s = str(v or "").strip()
    m = re.match(r"(\d+)%\s*(Buy|Sell|Hold)", s, re.I)
    if m:
        return int(m.group(1)), m.group(2).title()
    return None, s.title() if s else ""


def load_csv(path):
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.DictReader(io.StringIO(f.read())))
    return [r for r in rows if r.get("Symbol") and not str(r["Symbol"]).startswith("Downloaded")]


def parse_row(r):
    pct, side = opinion(r.get("Opinion"))
    return {"sym": r["Symbol"].strip(), "name": (r.get("Name") or "").strip(), "industry": (r.get("Industry") or "").strip(),
            "last": num(r.get("Latest")), "d5": num(r.get("5D Chg")), "nh": num(r.get("1M #Hi")),
            "trend": (r.get("Trend") or "").strip().title(), "opPct": pct, "opSide": side, "opRaw": (r.get("Opinion") or "").strip(),
            "alpha": num(r.get("Wtd Alpha")), "rsi": num(r.get("14D RSI")), "ma100": num(r.get("100D MA")),
            "offHi": num(r.get("52W %/High")), "m1": num(r.get("1M %Chg")), "m3": num(r.get("3M %Chg")), "y1": num(r.get("52W %Chg"))}


# ---------------------------------------------------------------- אימות וציון
def checks(kind, s):
    """[(תווית, מצב ok/warn/fail, פירוט)] לפי filter-criteria.md. Strength/Direction/Beta אינם בקובץ — לא נבדקים."""
    a, p, side, tr = s["alpha"], s["opPct"], s["opSide"], s["trend"]
    out = []
    if kind == "momentum":
        out.append(("עוצמה > 50", "ok" if a is not None and a > 50 else "fail", "%.0f" % a if a is not None else "—"))
        out.append(("חוות דעת קנייה ≥ 99%", "ok" if side == "Buy" and (p or 0) >= 99 else "fail", s["opRaw"]))
        out.append(("קו המגמה בקנייה", "ok" if tr == "Buy" else "fail", tr or "—"))
    elif kind == "breakout":
        out.append(("עוצמה בין 5- ל-50", "ok" if a is not None and -5 <= a <= 50 else "fail", "%.0f" % a if a is not None else "—"))
        st = "fail" if side != "Buy" or p is None or p < 30 or p > 80 else ("ok" if 40 <= p <= 70 else "warn")
        out.append(("חוות דעת קנייה 30–80% (אידיאלי 40–70)", st, s["opRaw"]))
        out.append(("קו המגמה בקנייה", "ok" if tr == "Buy" else "fail", tr or "—"))
    else:
        out.append(("עוצמה מתחת ל-50", "ok" if a is not None and a < 50 else "fail", "%.0f" % a if a is not None else "—"))
        out.append(("חוות דעת מכירה", "ok" if side == "Sell" else "fail", s["opRaw"]))
        out.append(("קו המגמה בקנייה (המפתח)", "ok" if tr == "Buy" else "fail", tr or "—"))
        above = s["last"] is not None and s["ma100"] and s["last"] > s["ma100"]
        out.append(("מעל ממוצע 100 (תנאי הכניסה)", "ok" if above else "warn", ("%.2f מול %.2f" % (s["last"], s["ma100"])) if s["ma100"] else "—"))
    return out


def score(kind, s, nh_max):
    cs = checks(kind, s)
    crit = sum(1 if c[1] == "ok" else 0.5 if c[1] == "warn" else 0 for c in cs) / len(cs) * 40
    r = s["rsi"]
    rsi = 15 if r is not None and 50 <= r <= 65 else 7 if r is not None and (45 <= r < 50 or 65 < r <= 70) else 0
    off = abs(s["offHi"]) if s["offHi"] is not None else None
    prox = 15 if off is not None and off <= 8 else 7 if off is not None and off <= 25 else 0
    nh = 15 * (s["nh"] / nh_max) if nh_max and s["nh"] is not None else 0
    raw = crit + rsi + prox + nh          # מתוך 85 (בלי Trust & Verify)
    return round(raw / 85 * 100), cs


def status_of(cs):
    sts = [c[1] for c in cs]
    return "fail" if "fail" in sts else "warn" if "warn" in sts else "ok"


def flags(kind, s, earn_win, picks):
    f = []
    if s["rsi"] is not None and s["rsi"] > 70:
        f.append("מד חום %.0f — חם מדי, מהר מדי" % s["rsi"])
    if s["rsi"] is not None and s["rsi"] < 50 and kind != "phoenix":
        f.append("מד חום %.0f — המגמה עוד לא מאושרת" % s["rsi"])
    if s["offHi"] is not None and abs(s["offHi"]) >= 25:
        f.append("%.0f%% מהשיא — מקום לרוץ, פחות אישור" % abs(s["offHi"]))
    if kind == "phoenix" and s["ma100"] and s["last"] is not None and s["last"] <= s["ma100"]:
        f.append("מתחת לממוצע 100 (%.2f) — בלי כיבושו אין כניסה" % s["ma100"])
    if s["sym"] in earn_win:
        f.append("מדווחת ב-%s" % earn_win[s["sym"]])
    if s["last"] is not None and s["last"] < 5:
        f.append("מחיר מתחת ל-$5")
    if s["sym"] in picks:
        f.append("בנבחרות של האתר")
    return f


def levels(kind, s):
    """טריגר = השיא (52 שבועות, נגזר מהמרחק) · קו ההוכחה/היציאה = ממוצע 100."""
    hi = s["last"] / (1 + s["offHi"] / 100) if s["last"] and s["offHi"] is not None and s["offHi"] < 0 else s["last"]
    out = {"hi52": round(hi, 2) if hi else None, "ma100": s["ma100"]}
    if kind == "phoenix":
        out["trigger"] = s["ma100"]
        out["triggerHe"] = "סגירה מעל ממוצע 100 (%s) והחזקה שבוע" % fmtn(s["ma100"])
    else:
        out["trigger"] = out["hi52"]
        out["triggerHe"] = ("פריצת השיא %s בנפח" % fmtn(out["hi52"])) if s["offHi"] is not None and s["offHi"] < 0 else "החזקה מעל השיא שנפרץ"
    out["stopHe"] = ("יציאה בסגירה מתחת לממוצע 100 (%s)" % fmtn(s["ma100"])) if s["ma100"] else "יציאה לפי ממוצע 100"
    return out


def fmtn(v, d=2):
    return "—" if v is None else ("{:,.%df}" % d).format(v)


def market_state():
    """SPY מול ממוצע 50 (מנרות), המד מ-indices.json, ורמזור VIX מ-market.json."""
    st = {}
    try:
        b = json.load(open(os.path.join(DATA, "bars", "SPY.json"), encoding="utf-8"))["bars"]
        c = [x[4] for x in b]
        st.update({"spyDate": b[-1][0], "spy": c[-1], "ma50": round(sum(c[-50:]) / 50, 2), "ma20": round(sum(c[-20:]) / 20, 2)})
        st["aboveMa50"] = c[-1] > st["ma50"]
    except Exception:
        pass
    try:
        i = json.load(open(os.path.join(DATA, "indices.json"), encoding="utf-8"))
        comb = (i.get("scores") or {}).get("combined")
        st.update({"meter": comb, "meterDate": i.get("date"), "verdict": (i.get("verdict") or {}).get("headline") or "",
                   "gate": "חיובי" if comb is not None and comb >= 66 else "זהיר" if comb is not None and comb >= 45 else "הגנתי" if comb is not None else ""})
    except Exception:
        pass
    try:
        m = json.load(open(os.path.join(DATA, "market.json"), encoding="utf-8"))
        vl = m.get("vixLight") or {}
        st.update({"vix": vl.get("vix"), "vixState": vl.get("state"), "spxOffHigh": vl.get("spxOffHigh")})
    except Exception:
        pass
    return st


def compute(day):
    folder = os.path.join(FP, day)
    meta = json.load(open(os.path.join(folder, "meta.json"), encoding="utf-8"))
    try:
        earn_win = (json.load(open(os.path.join(DATA, "earnings.json"), encoding="utf-8")).get("window") or {})
    except Exception:
        earn_win = {}
    try:
        picks = {p["sym"] for p in json.load(open(os.path.join(DATA, "picks.json"), encoding="utf-8")).get("picks", [])}
    except Exception:
        picks = set()
    cats, total, passed = {}, 0, 0
    for k in KINDS:
        rows = [parse_row(r) for r in load_csv(os.path.join(folder, k + ".csv"))]
        nh_max = max([s["nh"] for s in rows if s["nh"] is not None] or [0])
        items = []
        for s in rows:
            sc, cs = score(k, s, nh_max)
            s.update({"score": sc, "checks": [{"label": a, "state": b, "value": c} for a, b, c in cs], "status": status_of(cs),
                      "flags": flags(k, s, earn_win, picks), "levels": levels(k, s)})
            items.append(s)
        items.sort(key=lambda s: (-s["score"], -(s["nh"] or 0)))
        for i, s in enumerate(items):
            s["rank"] = i + 1
        total += len(items)
        passed += sum(1 for s in items if s["status"] != "fail")
        cats[k] = items
    return {"tradeDay": day, "meta": meta, "market": market_state(), "cats": cats, "total": total, "passed": passed,
            "builtAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


# ---------------------------------------------------------------- HTML
CSS = """
:root{--bg:#EEF0F3;--surface:#FFFFFF;--surface-2:#F6F7F9;--border:#D8DDE4;--text:#14181F;--text-soft:#3D4653;--text-3:#5B6675;
--accent:#1D5BB8;--accent-soft:#E7EEFA;--up:#0D7A52;--down:#BE2E1C;--warn:#8A5200;--warn-soft:#FBF1DC;--up-soft:#E3F3EC;--down-soft:#F9E7E4;
--sans:"IBM Plex Sans Hebrew","Heebo",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#0B0E13;--surface:#121821;--surface-2:#171E29;--border:#243040;--text:#E3E8EF;--text-soft:#B4BECB;--text-3:#8C98A8;
--accent:#7FB2FF;--accent-soft:#182A47;--up:#3CCB7F;--down:#FF6B5A;--warn:#F5B03E;--warn-soft:#2A2110;--up-soft:#15302A;--down-soft:#3A1F1C;color-scheme:dark}}
*{box-sizing:border-box} html{direction:rtl}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 var(--sans);padding:20px 16px 48px}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums;direction:ltr;unicode-bidi:isolate}
.wrap{max-width:1080px;margin:0 auto;display:grid;gap:12px}
h1,h2,h3,p{margin:0} h1{font-size:24px;line-height:1.3;font-weight:700} h2{font-size:13px;font-weight:600;color:var(--text-soft);line-height:20px}
a{color:var(--accent)}
.pan{background:var(--surface);border:1px solid var(--border);border-radius:6px;min-width:0}
.ph{display:flex;align-items:center;gap:10px;min-height:44px;padding:0 14px;border-bottom:1px solid var(--border);flex-wrap:wrap}
.ph .sub{margin-inline-start:auto;font-size:12px;color:var(--text-3)}
.pb{padding:14px}
.head{display:grid;gap:8px;padding:16px 14px 14px}
.kick{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:12px;color:var(--text-3)}
.kick .tag{background:var(--accent-soft);color:var(--accent);border-radius:3px;padding:1px 7px;font-weight:600}
.dek{font-size:15px;line-height:1.6;color:var(--text-soft);max-width:75ch}
.mkt{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:1px solid var(--border)}
.mkt>div{padding:10px 14px;border-inline-start:1px solid var(--border);min-width:0}
.mkt>div:first-child{border-inline-start:0}
.mkt .l{font-size:12px;color:var(--text-3)} .mkt .v{font:600 18px/1.3 var(--mono)} .mkt .v.t{font:600 15px/1.4 var(--sans)} .mkt .s{font-size:12px;color:var(--text-soft)}
.gloss{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;padding:14px}
.gloss div{font-size:13px;line-height:1.5;color:var(--text-soft);border:1px solid var(--border);border-radius:4px;padding:10px 12px;background:var(--surface-2)}
.gloss b{color:var(--text);font-weight:600}
.tw{overflow-x:auto} table{width:100%;border-collapse:collapse;min-width:900px}
thead th{font-size:12px;font-weight:500;color:var(--text-3);text-align:start;padding:8px 10px;border-bottom:1px solid var(--border);white-space:nowrap}
tbody td{padding:7px 8px;vertical-align:top;border-bottom:1px solid var(--border);font-size:13px}
tbody tr:last-child td{border-bottom:0}
td.sym{font:700 14px var(--mono);direction:ltr;text-align:right;white-space:nowrap} td.sym small{display:block;font:12px var(--sans);color:var(--text-3);direction:rtl;text-align:right;white-space:normal}
td.sym a{color:var(--text);text-decoration:none} td.sym a:hover{color:var(--accent)}
td.nm{font-size:13px;min-width:110px} td.nm small{display:block;font-size:12px;color:var(--text-3)}
.up{color:var(--up)} .dn{color:var(--down)}
.st{display:inline-block;font-size:12px;font-weight:600;border-radius:3px;padding:1px 8px;white-space:nowrap;cursor:help}
.st-ok{background:var(--up-soft);color:var(--up)} .st-warn{background:var(--warn-soft);color:var(--warn)} .st-fail{background:var(--down-soft);color:var(--down)}
.sc{font:600 15px var(--mono)} .sc small{font:11px var(--sans);color:var(--text-3)}
.chk{font-size:11px;color:var(--text-3);line-height:1.4;margin-top:2px;white-space:nowrap} .chk .ok{color:var(--up)} .chk .fail{color:var(--down)} .chk .warn{color:var(--warn)}
.note{font-size:13px;line-height:1.45;color:var(--text-soft);min-width:200px}
.flag{display:inline-block;font-size:12px;color:var(--down);background:var(--down-soft);border-radius:3px;padding:0 6px;margin:2px 0;white-space:nowrap}
.flag.soft{color:var(--text-soft);background:var(--surface-2)}
.top{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;padding:14px}
.tp{border:1px solid var(--border);border-radius:4px;padding:12px;display:grid;gap:6px;align-content:start}
.tp .who{display:flex;align-items:center;gap:8px} .tp .who b{font:700 15px var(--mono)} .tp .who .st{margin-inline-start:auto}
.tp p{font-size:13px;line-height:1.5;color:var(--text-soft)} .tp .kv{font-size:12px;color:var(--text-3)} .tp .kv b{color:var(--text);font-weight:600}
.cat-what{font-size:12px;color:var(--text-3);padding:8px 14px 0}
.red{padding:0 14px 14px} .red li{font-size:13px;line-height:1.5;color:var(--text-soft);margin:4px 0} .red b{font:700 13px var(--mono)}
.bottom{padding:14px;font-size:14px;line-height:1.6} .bottom b{font-weight:600}
.foot{font-size:12px;color:var(--text-3);text-align:center;padding:4px 0 0}
.empty{padding:14px;font-size:13px;color:var(--text-3)}
@media (max-width:860px){.mkt,.gloss{grid-template-columns:repeat(2,minmax(0,1fr))}.mkt>div:nth-child(3){border-inline-start:0}.mkt>div:nth-child(n+3){border-top:1px solid var(--border)}}
@media (max-width:560px){h1{font-size:20px}.mkt,.gloss{grid-template-columns:1fr}.ph .sub{display:none}body{padding:12px 12px 40px}}
"""
GLOSS = [("ציון עוצמה (Weighted Alpha)", "בכמה המניה הכתה את השוק בשנה האחרונה, עם משקל עודף לחודשים האחרונים. S&P עומד בדרך כלל על 20–25."),
         ("חוות דעת Barchart (Opinion)", "13 אינדיקטורים טכניים — כמה מהם בקנייה. 100% = כולם."),
         ("קו המגמה (Trend Seeker)", "מערכת מגמה של Barchart; קנייה = המחיר מעל הקו העולה."),
         ("מד חום (RSI 14)", "50–65 בריא · מעל 70 חם מדי · מתחת ל-50 המגמה לא מאושרת."),
         ("שיאים בחודש", "כמה שיאים חדשים המניה עשתה החודש. הרבה = עלייה עקבית. המיון הראשי של השיטה."),
         ("ציון ארבעת העמודים", "0–100: קריטריונים 40 · מד חום 15 · קרבה לשיא 15 · שיאים 15 · אימות חדשותי 15 (לא מבוצע כאן — הציון מנורמל)")]


def e(x):
    return html.escape(str(x))


def pc(v, d=1):
    if v is None:
        return "—"
    return '<span class="num %s">%s%%</span>' % ("up" if v > 0 else "dn" if v < 0 else "", ("%+.*f" % (d, v)).replace("-", "−"))


def tv(sym):
    return '<a href="https://www.tradingview.com/symbols/%s/" target="_blank" rel="noopener">%s</a>' % (e(sym), e(sym))


def row_html(k, s, note):
    st = {"ok": "עומדת", "warn": "גבולית", "fail": "לא עומדת"}[s["status"]]
    mark = {"ok": "✓", "warn": "◐", "fail": "✗"}
    tip = " · ".join("%s %s" % (mark[c["state"]], c["label"]) for c in s["checks"])   # כל הבדיקות — בריחוף
    bad = [c for c in s["checks"] if c["state"] != "ok"]                                 # בשורה רק מה שלא עבר
    chk = " · ".join('<span class="%s">%s %s</span>' % (c["state"], mark[c["state"]], e(c["label"])) for c in bad)
    chk = ('<div class="chk">%s</div>' % chk) if chk else ""
    fl = "".join('<span class="flag%s">%s</span> ' % (" soft" if ("בנבחרות" in f or "מקום לרוץ" in f) else "", e(f)) for f in s["flags"])
    lv = s["levels"]
    return ('<tr><td class="num">%d</td><td class="sym">%s</td><td class="nm">%s<small>%s</small></td>'
            '<td><span class="sc">%d<small> /100</small></span></td><td><span class="st st-%s" title="%s">%s</span>%s</td>'
            '<td class="num">%s</td><td>%s</td><td class="num">%s</td><td>%s</td><td class="num">%s</td><td class="num">%s</td><td>%s</td>'
            '<td class="num">%s</td><td class="num">%s</td>'
            '<td class="note">%s%s</td></tr>') % (
        s["rank"], tv(s["sym"]), e(s["name"]), e(s["industry"]), s["score"], s["status"], e(tip), st, chk,
        fmtn(s["last"]), pc(s["d5"]), "%.0f" % s["alpha"] if s["alpha"] is not None else "—", e(s["opRaw"]),
        "%.0f" % s["rsi"] if s["rsi"] is not None else "—", "%.0f" % s["nh"] if s["nh"] is not None else "—", pc(s["offHi"]),
        fmtn(lv["trigger"]), fmtn(lv["ma100"]),
        (fl + "<br>" if fl else ""), e(note) if note else "")


def template_note(k, s):
    lv = s["levels"]
    if s["status"] == "fail":
        bad = [c["label"] for c in s["checks"] if c["state"] == "fail"]
        return "לא עומדת: " + ", ".join(bad) + " — כנראה הסריקה רצה עם הגדרות שונות. לא ברשימת המעקב."
    parts = []
    if s["rsi"] is not None and s["rsi"] > 70:
        parts.append("חמה מדי — לחכות לנשימה")
    elif s["offHi"] is not None and abs(s["offHi"]) <= 8:
        parts.append("קרוב לשיא — מבחן הפריצה קרוב")
    parts.append("טריגר: " + lv["triggerHe"])
    parts.append(lv["stopHe"])
    return " · ".join(parts)


def render(rep, notes):
    day = rep["tradeDay"]
    d = date.fromisoformat(day)
    dow = DOW[d.weekday()]
    mk = rep["market"]
    n = notes or {}
    nn = n.get("notes") or {}
    head = n.get("headline") or ("ארבעת העמודים — סגירת יום %s: %d מניות בשלוש הסריקות, %d עומדות בקריטריונים" % (dow, rep["total"], rep["passed"]))
    dek = n.get("summary") or "הסריקות של Barchart לפי שיטת ארבעת העמודים (Weighted Alpha · Opinion · Trend Seeker · Beta): מי רץ, מי נדרך לפריצה, ומי אולי בתחתית. הטבלאות מאמתות את הקריטריונים ומדרגות; ההערות והשורה התחתונה נכתבות בבוקר."
    mkt_line = ""
    if mk.get("spy"):
        mkt_line = ('<div><div class="l">S&amp;P 500 (SPY) · %s</div><span class="v num">%s</span><div class="s">%s ממוצע 50 (%s) · %s ממוצע 20</div></div>' %
                    (e(dmy(mk.get("spyDate", day))), fmtn(mk["spy"]), "מעל" if mk.get("aboveMa50") else "מתחת ל", fmtn(mk["ma50"]), "מעל" if mk["spy"] > mk["ma20"] else "מתחת ל"))
    mkt_line += ('<div><div class="l">מד השוק</div><span class="v num">%s</span><div class="s">%s · %s</div></div>' % (mk.get("meter", "—"), e(mk.get("gate", "")), e((mk.get("verdict") or "")[:60])) if mk.get("meter") is not None else "")
    mkt_line += ('<div><div class="l">VIX</div><span class="v num">%s</span><div class="s">רמזור %s · S&amp;P %s מהשיא</div></div>' % (fmtn(mk.get("vix"), 1), {"green": "ירוק", "yellow": "צהוב", "red": "אדום"}.get(mk.get("vixState"), "—"), pc(mk.get("spxOffHigh")))) if mk.get("vix") else ""
    mkt_line += '<div><div class="l">הסריקות</div><span class="v t">%d מניות · %d עומדות</span><div class="s">%s</div></div>' % (
        rep["total"], rep["passed"], " · ".join("%s %d" % (CAT[k]["he"], len(rep["cats"][k])) for k in KINDS))
    beta_note = "בשוק %s ממוצע 50 בטא גבוה %s" % ("מעל" if mk.get("aboveMa50") else "מתחת ל", "מקבל בונוס" if mk.get("aboveMa50") else "נענש — עדיפות למניות רגועות") if mk.get("spy") else ""
    H = ['<header class="pan"><div class="head"><div class="kick"><span class="tag">הצעות לטרייד · ארבעת העמודים</span><span>סגירת יום %s · <span class="num">%s</span> · הורדה %s</span>%s</div><h1>%s</h1><p class="dek">%s</p></div><div class="mkt">%s</div></header>' %
         (dow, dmy(day), e(dmy((rep["meta"].get("downloadedAt") or "")[:10]) if rep["meta"].get("downloadedAt") else ""), ('<span class="tag" style="background:var(--warn-soft);color:var(--warn)">%s</span>' % e(beta_note)) if beta_note else "", e(head), e(dek), mkt_line)]
    H.append('<section class="pan"><div class="ph"><h2>שישה מושגים בשורה</h2></div><div class="gloss">' + "".join("<div><b>%s</b> — %s</div>" % (e(a), e(b)) for a, b in GLOSS) + "</div></section>")
    thead = "<thead><tr><th>#</th><th>מניה</th><th>שם</th><th>ציון</th><th>סטטוס</th><th>מחיר</th><th>5 ימים</th><th>עוצמה</th><th>חוות דעת</th><th>מד חום</th><th>שיאים בחודש</th><th>מרחק מהשיא</th><th>טריגר</th><th>ממוצע 100</th><th>הערה</th></tr></thead>"
    for k in KINDS:
        items = rep["cats"][k]
        okn = sum(1 for s in items if s["status"] != "fail")
        body = "".join(row_html(k, s, nn.get(s["sym"]) or template_note(k, s)) for s in items)
        H.append('<section class="pan"><div class="ph"><h2>%s — %s · %d מניות, %d כשירות</h2><span class="sub">%s</span></div>' % (e(CAT[k]["he"]), e(CAT[k]["en"]), len(items), okn, e(CAT[k]["what"])) +
                 (('<div class="tw"><table>%s<tbody>%s</tbody></table></div>' % (thead, body)) if items else '<div class="empty">הסריקה חזרה ריקה היום.</div>') + "</section>")
    # מובילות
    top = n.get("top") or []
    if not top:
        allv = [(k, s) for k in KINDS for s in rep["cats"][k] if s["status"] != "fail"]
        allv.sort(key=lambda t: -t[1]["score"])
        top = [{"sym": s["sym"], "text": template_note(k, s)} for k, s in allv[:4]]
    bysym = {s["sym"]: (k, s) for k in KINDS for s in rep["cats"][k]}
    cards = ""
    for t in top:
        if t.get("sym") not in bysym:
            continue
        k, s = bysym[t["sym"]]
        lv = s["levels"]
        cards += ('<div class="tp"><div class="who"><b>%s</b><span class="num">%s</span><span class="st st-%s">%s · %d</span></div><p>%s</p>'
                  '<div class="kv">טריגר <b>%s</b> · מחיר <b>%s</b> · מד חום <b>%s</b> · שיאים בחודש <b>%s</b> · %s</div></div>') % (
            tv(s["sym"]), e(s["name"]), s["status"], e(CAT[k]["he"]), s["score"], e(t.get("text", "")), fmtn(lv["trigger"]), fmtn(s["last"]),
            "%.0f" % s["rsi"] if s["rsi"] is not None else "—", "%.0f" % s["nh"] if s["nh"] is not None else "—", e(lv["stopHe"]))
    H.append('<section class="pan"><div class="ph"><h2>ניתוח פרטני — המובילות</h2><span class="sub">Watchlist + טריגר כניסה, לא "לקנות עכשיו"</span></div><div class="top">%s</div></section>' % (cards or '<div class="empty">אין מניות כשירות.</div>'))
    # דגלים אדומים
    reds = []
    for k in KINDS:
        for s in rep["cats"][k]:
            hard = [f for f in s["flags"] if "בנבחרות" not in f and "מקום לרוץ" not in f]
            if s["status"] == "fail":
                hard.insert(0, "לא עומדת בקריטריונים של " + CAT[k]["he"])
            if hard:
                reds.append("<li><b>%s</b> — %s</li>" % (e(s["sym"]), e(" · ".join(hard))))
    for r in (n.get("redFlags") or []):
        reds.append("<li>%s</li>" % e(r))
    H.append('<section class="pan"><div class="ph"><h2>דגלים אדומים</h2></div>' + (('<ul class="red">%s</ul>' % "".join(reds)) if reds else '<div class="empty">אין.</div>') + "</section>")
    bottom = n.get("bottom") or ("לרשימת המעקב: " + " · ".join("<b>%s</b> (%s)" % (e(t["sym"]), e(bysym[t["sym"]][1]["levels"]["triggerHe"])) for t in top if t.get("sym") in bysym) + ". כניסה רק בטריגר, בשלישים, עם יציאה מתחת לממוצע 100.")
    H.append('<section class="pan"><div class="ph"><h2>שורה תחתונה</h2></div><div class="bottom">%s</div></section>' % bottom)
    H.append('<p class="foot">ניתוח טכני לצורכי לימוד — אינו המלצת השקעה. מקור: סורקי Barchart (Four Pillars), הורדה %s, נתוני סגירת %s. ציון ללא Trust &amp; Verify (אין רשת לרוטינה). המילים: %s.</p>' %
             (e(rep["meta"].get("downloadedAt", "")), e(dmy(day)), "רוטינת הבוקר (%s)" % e(n.get("writtenAt", "")) if n else "משפטי תבנית — ההערות ייכתבו בבוקר"))
    title = "דוח ארבעת העמודים — %s" % dmy(day)
    page = ('<!DOCTYPE html>\n<html lang="he" dir="rtl">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>%s</title>\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Hebrew:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">\n'
            '<style>%s</style>\n</head>\n<body><div class="wrap">\n%s\n</div></body></html>') % (e(title), CSS, "".join(H))
    return page, title


def dmy(iso):
    try:
        y, m, d = iso.split("-")
        return "%d.%d.%s" % (int(d), int(m), y)
    except Exception:
        return iso


# ---------------------------------------------------------------- רישום
def load_notes(day):
    p = os.path.join(FP, day, "notes.json")
    try:
        n = json.load(open(p, encoding="utf-8"))
        return n if n.get("tradeDay") in (None, day) else None
    except (OSError, ValueError):
        return None


def register(day, title, picks):
    """data/fourpillars/index.json + שורה ב-data/trades.json (הטאב קורא ממנו; fetch_trades ממזג גם)."""
    idx_p = os.path.join(FP, "index.json")
    try:
        idx = json.load(open(idx_p, encoding="utf-8"))
    except (OSError, ValueError):
        idx = {"reports": []}
    rel = "data/trades/trades-%s.html" % day
    idx["reports"] = [r for r in idx["reports"] if r.get("date") != day] + [{"date": day, "file": rel, "title": title, "source": "build_fourpillars"}]
    idx["reports"].sort(key=lambda r: r["date"], reverse=True)
    idx["_meta"] = {"updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    json.dump(idx, open(idx_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tj = os.path.join(DATA, "trades.json")
    try:
        t = json.load(open(tj, encoding="utf-8"))
    except (OSError, ValueError):
        t = {"reports": [], "method": None, "_meta": {}}
    t["reports"] = [r for r in t.get("reports", []) if r.get("date") != day] + [{"file": rel, "date": day, "title": title, "picks": picks, "source": "build_fourpillars"}]
    t["reports"].sort(key=lambda r: r["date"], reverse=True)
    t["reports"] = t["reports"][:20]
    json.dump(t, open(tj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def build(day):
    rep = compute(day)
    notes = load_notes(day)
    page, title = render(rep, notes)
    out = os.path.join(DATA, "trades", "trades-%s.html" % day)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    rep["notesAt"] = (notes or {}).get("writtenAt")
    json.dump(rep, open(os.path.join(FP, day, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    try:
        from fetch_trades import extract_picks
        picks = extract_picks(page)
    except Exception:
        picks = []
    register(day, title, picks)
    print("[fourpillars] %s: %d מניות, %d כשירות · notes=%s · %s" % (day, rep["total"], rep["passed"], "כן" if notes else "לא", out))
    return 0


def pending():
    """תיקיות שאין להן דוח, או שה-notes שלהן חדש יותר מהדוח."""
    out = []
    for folder in sorted(glob.glob(os.path.join(FP, "????-??-??"))):
        day = os.path.basename(folder)
        if not os.path.exists(os.path.join(folder, "meta.json")):
            continue
        rp = os.path.join(folder, "report.json")
        if not os.path.exists(os.path.join(DATA, "trades", "trades-%s.html" % day)) or not os.path.exists(rp):
            out.append(day)
            continue
        try:
            built = json.load(open(rp, encoding="utf-8")).get("notesAt")
        except (OSError, ValueError):
            built = None
        n = load_notes(day)
        if n and n.get("writtenAt") != built:
            out.append(day)
    return out


def main(argv):
    days = argv[1:] or pending()
    if not days:
        print("[fourpillars] אין מה לבנות")
        return 0
    for d in days:
        build(d)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
