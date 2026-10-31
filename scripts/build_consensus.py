#!/usr/bin/env python3
"""
build_consensus.py — "סיכום": מניות שכמה מערכות באתר בחרו בהן (31.10.2026, np167, איציק).

מוקאפ שאושר: https://claude.ai/artifact/KU3hNTXbgPJdBtEBcT2r2K (הגרסה הפשוטה).
שש מערכות, כל אחת "כן/לא" למניה, בלי משקלים:
  בנבחרות       — נכנסה למהדורה ב-WINDOW ימי המסחר האחרונים (picks_ledger.json)
  מועמדת        — ברשימת המועמדים הנוכחית (candidates.json)
  מומנטום       — 2 סיגנלים ומעלה או מוכנות 50+ (momentum.json, כמו טאב המומנטום)
  הצעות לטרייד  — בדוח ארבעת העמודים האחרון בסטטוס "עומדת" (fourpillars/<יום>/report.json)
  מנהלים קנו    — קנייה בשוק הפתוח שדווחה ב-WINDOW ימי המסחר האחרונים (insider_daily.json.track)
  הסקטור        — "מאושר" או "מתחמם" בדוח הרוטציה האחרון (גרסה 2; הסקטור מ-fundamentals.json)
מניה שעברה MIN_N ומעלה → data/consensus.json. דטרמיניסטי, בלי רשת; רץ בכל מחזור של ה-Action.
"""
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
WINDOW = 10      # ימי מסחר — "שבועיים אחרונים" לנבחרות ולרכישות המנהלים
MIN_N = 3
MAX_ROWS = 15
SECTOR_HE = {
    "Technology Services": "טכנולוגיה", "Electronic Technology": "טכנולוגיה", "Finance": "פיננסים",
    "Health Technology": "בריאות", "Health Services": "בריאות", "Retail Trade": "צריכה מחזורית",
    "Consumer Durables": "צריכה מחזורית", "Consumer Services": "צריכה מחזורית",
    "Consumer Non-Durables": "צריכה בסיסית", "Energy Minerals": "אנרגיה", "Utilities": "תשתיות",
    "Producer Manufacturing": "תעשייה", "Industrial Services": "תעשייה", "Transportation": "תעשייה",
    "Commercial Services": "תעשייה", "Distribution Services": "תעשייה", "Process Industries": "חומרים",
    "Non-Energy Minerals": "חומרים", "Communications": "תקשורת",
}
FP_CAT = {"momentum": "הרכבות הדוהרות", "breakout": "הקפיצים הנדרכים", "phoenix": "עופות החול"}
ORDER = ("ins", "nb", "cand", "fp", "mom", "sec")


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def dm(iso):
    return "%d.%d" % (int(iso[8:10]), int(iso[5:7])) if iso else ""


def money(v):
    v = v or 0
    return "%.1f מיליון דולר" % (v / 1e6) if v >= 1e6 else "%d אלף דולר" % round(v / 1e3)


def bars_of(root, sym):
    j = load(os.path.join(root, "data", "bars", sym.replace(".", "-") + ".json"), {}) or {}
    return j.get("bars") or []


def main(root=ROOT, now=None):
    now = now or datetime.now(timezone.utc)
    data = os.path.join(root, "data")
    spy = bars_of(root, "SPY")
    if not spy:
        print("build_consensus: אין נרות SPY — דילוג")
        return 0
    as_of = spy[-1][0]
    span = [b[0] for b in spy][-WINDOW:]
    since = span[0]
    sig, src = {}, {}

    def add(sym, k, d):
        sym = (sym or "").strip().upper()
        if sym and k not in sig.setdefault(sym, {}):
            sig[sym][k] = d

    # הנבחרות — המהדורה הראשונה בחלון (מתי נכנסה)
    led = load(os.path.join(data, "picks_ledger.json"), {}) or {}
    for e in sorted(led.get("editions") or [], key=lambda e: e["date"]):
        if since <= e["date"] <= as_of:
            for s in e.get("symbols") or []:
                add(s.get("sym"), "nb", {"d": e["date"]})
    src["nb"] = {"from": since, "to": as_of}

    cand = load(os.path.join(data, "candidates.json"), {}) or {}
    cday = (cand.get("_meta") or {}).get("basedOn") or cand.get("date")
    for c in cand.get("candidates") or []:
        add(c.get("symbol"), "cand", {"d": cday, "rank": c.get("rank")})
    src["cand"] = {"d": cday}

    mom = load(os.path.join(data, "momentum.json"), {}) or {}
    mday = None
    for fn in ((mom.get("_meta") or {}).get("files") or {}).values():
        m = re.search(r"(\d{2})-(\d{2})-(\d{4})", fn or "")
        if m:
            d = "%s-%s-%s" % (m.group(3), m.group(1), m.group(2))
            mday = max(mday or d, d)
    for s in mom.get("stocks") or []:
        n = len(s.get("signals") or [])
        if n >= 2 or (s.get("readiness") or 0) >= 50:
            add(s.get("symbol"), "mom", {"d": mday, "n": n, "ready": s.get("readiness")})
    src["mom"] = {"d": mday}

    fp_files = sorted(glob.glob(os.path.join(data, "fourpillars", "20*", "report.json")))
    fday = None
    if fp_files:
        rep = load(fp_files[-1], {}) or {}
        fday = rep.get("tradeDay")
        for cat, rows in (rep.get("cats") or {}).items():
            for x in rows:
                if x.get("status") == "ok":
                    add(x.get("sym"), "fp", {"d": fday, "cat": FP_CAT.get(cat, cat), "score": x.get("score")})
    src["fp"] = {"d": fday}

    ins = load(os.path.join(data, "insider_daily.json"), {}) or {}
    for b in sorted(ins.get("track") or [], key=lambda b: (b.get("filed") or "", b.get("value") or 0), reverse=True):
        if since <= (b.get("filed") or "") <= as_of and not b.get("excluded"):
            add(b.get("t"), "ins", {"d": b["filed"], "role": b.get("role") or "", "ceo": bool(b.get("ceo")), "value": b.get("value")})
    src["ins"] = {"from": max(since, ins.get("firstDay") or since), "to": as_of}

    # הסקטור — דוח הרוטציה האחרון בגרסה 2 (verdicts)
    ver, rday = {}, None
    for r in (load(os.path.join(data, "rotation", "index.json"), {}) or {}).get("reports") or []:
        nar = load(os.path.join(data, "rotation", r["date"], "narrative.json"), {}) or {}
        wk = load(os.path.join(data, "rotation", r["date"], "week.json"), {}) or {}
        if nar.get("verdicts") and wk.get("sectors"):
            rday = r["date"]
            for k, v in nar["verdicts"].items():
                if k in wk["sectors"]:
                    ver[wk["sectors"][k]["name_he"]] = v
            break
    src["sec"] = {"d": rday}
    fund = (load(os.path.join(data, "fundamentals.json"), {}) or {}).get("symbols") or {}

    rows = []
    for sym, s in sig.items():
        f = fund.get(sym) or {}
        sec = SECTOR_HE.get(f.get("sector") or "", "")
        v = ver.get(sec)
        if v and v.get("cls") in ("ok", "warm"):
            s["sec"] = {"d": rday, "sec": sec, "warm": v["cls"] == "warm"}
        if len(s) < MIN_N:
            continue
        b = bars_of(root, sym)
        close = b[-1][4] if b else None
        w5 = round((b[-1][4] / b[-6][4] - 1) * 100, 1) if len(b) >= 6 and b[-6][4] else None
        who, why = [], []
        for k in ORDER:
            x = s.get(k)
            if not x:
                continue
            if k == "ins":
                lab = 'המנכ"ל קנה' if x["ceo"] else ("בעל מניות גדול קנה" if "10%" in x["role"] else (x["role"] or "איש פנים") + " קנה")
                why.append("%s ב-%s ב-%s." % (lab.replace(" קנה", "") + " קנה", money(x["value"]), dm(x["d"])))
            elif k == "nb":
                lab = "בנבחרות"
                why.append("נכנסה לנבחרות ב-%s." % dm(x["d"]))
            elif k == "cand":
                lab = "מועמדת"
                if x.get("rank"):
                    why.append("מקום %d ברשימת המועמדים." % x["rank"])
            elif k == "fp":
                lab = "הצעות לטרייד"
                why.append('ב"%s" בהצעות לטרייד.' % x["cat"])
            elif k == "mom":
                lab = "מומנטום"
                why.append("%d סיגנלי מומנטום." % x["n"] if x["n"] >= 2 else "מוכנות %d במומנטום." % (x.get("ready") or 0))
            else:
                lab = "סקטור מתחמם" if x["warm"] else "סקטור מאושר"
                why.append("ה%s %s בדוח הסקטורים." % (x["sec"], "מתחמם" if x["warm"] else "מאושר"))
            who.append({"k": k, "l": lab, "d": x["d"]})
        note = []
        if w5 is not None and w5 >= 15:
            note.append("עלתה %d%% בשבוע — רחוקה מנקודת כניסה." % round(w5))
        if f.get("cap") is not None and f["cap"] < 3e8:
            note.append("חברה קטנה — תנודתית.")
        prio = (3 if "ins" in s else 0) + (2 if "nb" in s else 0) + (1 if "fp" in s else 0) - ((s.get("cand") or {}).get("rank") or 99) / 100
        rows.append({"t": sym, "co": f.get("name") or "", "sec": sec, "n": len(s), "who": who,
                     "why": " ".join(why[:2] + note[:1]), "close": close, "w5": w5, "_p": prio})
    rows.sort(key=lambda r: (-r["n"], -r["_p"], r["t"]))
    for r in rows:
        r.pop("_p")
    out = {"asOf": as_of, "minN": MIN_N, "window": WINDOW, "n": len(rows), "rows": rows[:MAX_ROWS], "src": src,
           "_meta": {"updatedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "ver": 1}}
    with open(os.path.join(data, "consensus.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("build_consensus: asOf=%s rows=%d (%s)" % (as_of, len(rows), " ".join(r["t"] for r in rows[:MAX_ROWS])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
