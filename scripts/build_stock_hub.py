#!/usr/bin/env python3
"""
build_stock_hub.py — "תמונה מלאה" בחלון המניה (15.11.2026, np202; מוקאפ https://claude.ai/artifact/K4fWbmDqfLGStiz22dsGCD).

לכל מניה שיש עליה משהו באתר מרכז במקום אחד את מה שכבר קיים בקבצים: באילו סריקות הופיעה ומתי, ניתוחי
הדוחות שלה, ורכישות מנהלים שדווחו. דטרמיניסטי, בלי רשת, רץ בכל מחזור של ה-Action → data/stock_hub.json.

שש בדיקות (אותן מערכות כמו build_consensus, אבל כאן מוצגת כל הופעה, לא רק 3 ומעלה):
  nb   — עומדות בתנאים: המהדורה האחרונה ב-20 ימי המסחר האחרונים שבה המניה נרשמה (picks_ledger.json)
  cand — סריקת תיקון: ברשימה הנוכחית (candidates.json)
  mom  — מומנטום: 2 סיגנלים ומעלה או מוכנות 50+ (momentum.json)
  fp   — ארבעת העמודים: בדוח האחרון, בכל סטטוס (fourpillars/<יום>/report.json)
  ins  — רכישות מנהלים: רכישה שדווחה ב-120 הימים האחרונים (insider_daily.json.track)
  sec  — הסקטור: "מאושר" או "מתחמם" בדוח הסקטורים האחרון (גרסה 2)

הטקסטים מתארים נתון + סיווג של המודל, בלי הוראת פעולה (scripts/prompts/_language.md); lint_advice בודק אותם.
קטע לטיני/מספרי בתוך משפט עברי עטוף ב-[[…]] — הדפדפן הופך אותו ל-<bdi dir=ltr> (וצובע מספר חתום).
"""
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

from build_consensus import SECTOR_HE, FP_CAT, load, dm, bars_of

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICK_DAYS = 20     # ימי מסחר — חלון המעקב של היומן
ALIAS = {"ALPHABET": "GOOGL", "GOOGLE": "GOOGL", "FACEBOOK": "META", "BERKSHIRE": "BRK-B"}   # כמו build_earnings_prep
SIG_HE = {"strength": "Strength & Direction", "hot_prospects": "Hot Prospects", "6m_high": "קרוב לשיא 6 חודשים",
          "ttm_squeeze": "TTM Squeeze", "macd_buy": "MACD"}
FP_STATUS = {"ok": "עומדת בקריטריונים", "warn": "גבולית", "fail": "לא עומדת בקריטריונים"}
CHECKS = [("nb", "עומדות בתנאים", "picks"), ("cand", "סריקת תיקון", "candidates"), ("mom", "מומנטום", "momentum"),
          ("fp", "ארבעת העמודים", "trades"), ("ins", "רכישות מנהלים", "insider"), ("sec", "הסקטור", "sectors")]


def L(x):
    return "[[%s]]" % x


def pct(v):
    return L(("+" if v > 0 else "−" if v < 0 else "") + ("%.2f%%" % abs(v)))


def usd(v):
    v = v or 0
    return L("$%.2fM" % (v / 1e6) if v >= 1e6 else "$%dK" % round(v / 1e3))


def main(root=ROOT, now=None):
    now = now or datetime.now(timezone.utc)
    data = os.path.join(root, "data")
    spy = bars_of(root, "SPY")
    if not spy:
        print("build_stock_hub: אין נרות SPY — דילוג")
        return 0
    as_of = spy[-1][0]
    since = [b[0] for b in spy][-PICK_DAYS:][0]
    hub, src = {}, {}

    def ent(sym):
        sym = (sym or "").strip().upper()
        return hub.setdefault(sym, {"app": {}, "rep": [], "ins": []}) if sym else None

    # --- עומדות בתנאים: המהדורה האחרונה בחלון ---
    led = load(os.path.join(data, "picks_ledger.json"), {}) or {}
    for e in sorted(led.get("editions") or [], key=lambda e: e["date"]):
        if not (since <= e["date"] <= as_of):
            continue
        for s in e.get("symbols") or []:
            h = ent(s.get("sym"))
            if h is None:
                continue
            r = (e.get("results") or {}).get(s["sym"]) or {}
            cur = r.get("20") or r.get("cur") or {}
            t = "התקיימו תנאי אישור המחיר."
            if s.get("entry"):
                t += " מחיר ייחוס %s" % L("%.2f" % s["entry"])
                if cur.get("ret") is not None and cur.get("spy") is not None:
                    day = 20 if r.get("20") else cur.get("day")
                    t += "; מאז %s, S&P 500 באותם ימים %s" % (pct(cur["ret"]), pct(cur["spy"]))
                    t += " (יום %d מתוך 20)." % day if day else "."
                else:
                    t += "."
            h["app"]["nb"] = {"d": e["date"], "t": t}
    src["nb"] = {"from": since, "to": as_of}

    # --- סריקת תיקון ---
    cand = load(os.path.join(data, "candidates.json"), {}) or {}
    cday = (cand.get("_meta") or {}).get("basedOn") or cand.get("date")
    for c in cand.get("candidates") or []:
        h = ent(c.get("symbol"))
        if h is None:
            continue
        p = []
        if c.get("rank"):
            p.append("מקום %d בדירוג" % c["rank"])
        if c.get("setup"):
            p.append("תבנית %s" % L(c["setup"]))
        if c.get("ext_atr") is not None:
            p.append("מתיחות %s" % L("%.2f ATR" % c["ext_atr"]))
        if c.get("rvol") is not None:
            p.append("מחזור יחסי %s" % L("%.2f" % c["rvol"]))
        h["app"]["cand"] = {"d": cday, "t": " · ".join(p)}
    src["cand"] = {"d": cday}

    # --- מומנטום ---
    mom = load(os.path.join(data, "momentum.json"), {}) or {}
    mday = None
    for fn in ((mom.get("_meta") or {}).get("files") or {}).values():
        m = re.search(r"(\d{2})-(\d{2})-(\d{4})", fn or "")
        if m:
            d = "%s-%s-%s" % (m.group(3), m.group(1), m.group(2))
            mday = max(mday or d, d)
    for s in mom.get("stocks") or []:
        sigs = s.get("signals") or []
        if not (len(sigs) >= 2 or (s.get("readiness") or 0) >= 50):
            continue
        h = ent(s.get("symbol"))
        if h is None:
            continue
        names = ", ".join(SIG_HE.get(x, x) for x in sigs)
        p = [("סיגנל אחד (%s)" % names) if len(sigs) == 1 else ("%d סיגנלים (%s)" % (len(sigs), names)) if sigs else "בלי סיגנל פעיל"]
        if s.get("readiness") is not None:
            p.append("מוכנות %s" % L(int(s["readiness"])))
        if s.get("opinion"):
            p.append("דירוג Barchart %s (דירוג טכני של צד שלישי)" % L(s["opinion"]))
        h["app"]["mom"] = {"d": mday, "t": " · ".join(p)}
    src["mom"] = {"d": mday}

    # --- ארבעת העמודים: הדוח האחרון ---
    fp_files = sorted(glob.glob(os.path.join(data, "fourpillars", "20*", "report.json")))
    fday = None
    if fp_files:
        rep = load(fp_files[-1], {}) or {}
        fday = rep.get("tradeDay")
        for cat, rows in (rep.get("cats") or {}).items():
            for x in rows:
                h = ent(x.get("sym"))
                if h is None:
                    continue
                p = ['בקטגוריה "%s"' % FP_CAT.get(cat, cat)]
                if x.get("score") is not None:
                    p.append("ציון %s" % L(int(x["score"])))
                p.append(FP_STATUS.get(x.get("status"), ""))
                h["app"]["fp"] = {"d": fday, "t": " · ".join(q for q in p if q)}
    src["fp"] = {"d": fday}

    # --- רכישות מנהלים: כל מה שבמעקב (120 יום); תאריך העסקה והקישור לטופס מהשורות המלאות ---
    ins = load(os.path.join(data, "insider_daily.json"), {}) or {}
    full = {}
    rows = list(ins.get("rows") or [])
    for v in (ins.get("views") or {}).values():
        rows += v.get("rows") or []
    for r in rows:
        full.setdefault((r.get("t"), r.get("who"), r.get("filed")), r)
    for b in sorted(ins.get("track") or [], key=lambda b: (b.get("filed") or "", b.get("value") or 0), reverse=True):
        if b.get("excluded"):
            continue
        h = ent(b.get("t"))
        if h is None:
            continue
        r = full.get((b.get("t"), b.get("who"), b.get("filed"))) or {}
        if len(h["ins"]) < 6:
            h["ins"].append({"who": b.get("who") or "", "role": b.get("role") or "", "value": b.get("value"),
                             "filed": b.get("filed"), "trade": r.get("trade"), "url": r.get("url")})
        if "ins" not in h["app"]:
            who = 'המנכ"ל' if b.get("ceo") else ("בעל מניות גדול" if "10%" in (b.get("role") or "") else (b.get("role") or "איש פנים"))
            h["app"]["ins"] = {"d": b.get("filed"), "t": "%s דיווח על רכישה בסך %s." % (who, usd(b.get("value")))}
    src["ins"] = {"from": ins.get("firstDay"), "to": ins.get("day")}

    # --- ניתוחי דוחות + "אחרי הדוח" + "לקראת הדוח" ---
    reps = (load(os.path.join(data, "reports.json"), {}) or {}).get("reports") or []
    review = load(os.path.join(data, "earnings_review_notes.json"), {}) or {}
    prep = load(os.path.join(data, "earnings_prep.json"), {}) or {}
    prep_notes = load(os.path.join(data, "earnings_prep_notes.json"), {}) or {}
    for r in sorted(reps, key=lambda r: r.get("date") or "", reverse=True):
        sym = ALIAS.get((r.get("ticker") or "").upper(), (r.get("ticker") or "").upper())
        h = ent(sym)
        if h is None or len(h["rep"]) >= 4:
            continue
        item = {"title": r.get("title") or "", "date": r.get("date"), "file": r.get("file")}
        rv = review.get(sym) or {}
        if rv.get("headline") and rv.get("forDate") and r.get("date") and abs((datetime.fromisoformat(rv["forDate"]) - datetime.fromisoformat(r["date"])).days) <= 4:
            item["review"] = re.sub(r"<[^>]+>", "", rv["headline"])
        h["rep"].append(item)
    for it in prep.get("items") or []:
        h = hub.get((it.get("sym") or "").upper())
        if h is not None:
            h["prep"] = {"date": it.get("date"), "when": it.get("when"), "notes": bool((prep_notes.get(it["sym"]) or {}).get("forDate") == it.get("date"))}

    # --- הסקטור: דוח הסקטורים האחרון בגרסה 2 ---
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

    out = {}
    for sym, h in hub.items():
        if not (h["app"] or h["rep"]):
            continue
        sec = SECTOR_HE.get((fund.get(sym) or {}).get("sector") or "", "")
        v = ver.get(sec)
        if v and v.get("cls") in ("ok", "warm"):
            h["app"]["sec"] = {"d": rday, "l": "הסקטור: " + sec,
                               "t": ("מסווג מתחמם (בבחינה) בדוח הסקטורים השבועי." if v["cls"] == "warm" else "מאושר במודל בדוח הסקטורים השבועי.")}
        app = []
        for k, lab, go in CHECKS:      # התווית, היעד ורשימת "לא הופיעה ב…" נבנים בדפדפן (ta_ui.js: HUB_CHECKS) — הקובץ נשאר קטן
            x = h["app"].get(k)
            if x:
                a = {"k": k, "d": x.get("d"), "t": x.get("t") or ""}
                if x.get("l"):
                    a["l"] = x["l"]
                app.append(a)
        o = {"n": len(app), "app": app}
        if "sec" not in h["app"] and sec and v:
            o["secOff"] = sec          # לסקטור יש סיווג בדוח, אבל לא מאושר/מתחמם
        if h["rep"]:
            o["rep"] = h["rep"]
        if h.get("prep"):
            o["prep"] = h["prep"]
        if h["ins"]:
            o["ins"] = h["ins"]
        out[sym] = o

    body = {"asOf": as_of, "checks": len(CHECKS), "src": src, "syms": dict(sorted(out.items()))}
    path = os.path.join(data, "stock_hub.json")
    old = load(path, {}) or {}
    if {k: old.get(k) for k in body} == body:      # בלי שינוי בתוכן — לא כותבים (חוסך קומיט רק בגלל החותמת)
        print("build_stock_hub: asOf=%s syms=%d (בלי שינוי)" % (as_of, len(out)))
        return 0
    body["_meta"] = {"updatedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "ver": 1}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, separators=(",", ":"))
    print("build_stock_hub: asOf=%s syms=%d · עם 3+ הופעות: %d" % (as_of, len(out), sum(1 for o in out.values() if o["n"] >= 3)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
