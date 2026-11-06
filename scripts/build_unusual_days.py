#!/usr/bin/env python3
"""
build_unusual_days.py — "ימים חריגים — מה קרה אחר כך" (6.11.2026, איציק; מוקאפ
https://claude.ai/artifact/4ksCBHgTdmRJUb1tUWT9kv).

יום חריג = S&P 500 ירד 3% ומעלה בסגירה. מכל רצף נספר רק היום הראשון (21 ימי מסחר בלי יום כזה לפני),
אחרת 2008 לבדה ממלאת את הרשימה. לכל מקרה: מה קרה אחרי יום / שבוע / חודש / חצי שנה / שנה
(1/5/21/126/252 ימי מסחר מסגירת יום הנפילה) והשפל ב-21 הימים שאחרי. "דומים" (באתר) = נפילה כשהסגירה
הקודמת הייתה עד 5% מתחת לשיא 252 הימים — לא בתוך שוק דובי.

מקורות (בלי רשת):
  • data/history/barchart/hist_SPX.csv, hist_VIX.csv (מ-2000), hist_S5TH.csv (% מניות S&P מעל ממוצע 200,
    מ-2007) — הורדה חד-פעמית של גרוק מ-Barchart (relay_history_mail.py).
  • המשך יומי אחרי הקבצים: data/history.json (spx, vix לכל יום מהדשבורד) ו-indices.json evidence.pctMa200
    (הרוחב של הדשבורד, קרוב ל-S5TH — 59.9 מול 58.6 ב-5.11). הרוחב היומי נצבר ב-data/history/ext.json
    כי history.json לא שומר אותו.
פלט: data/unusual_days.json {asOf, threshold, nearPct, horizons, rows[[d,ch,vix,vch,offPrev,br,r1,r5,r21,r126,r252,mdd21,label]], latest}.
"""
import csv
import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BASE = os.path.join(DATA, "history", "barchart")
EXT = os.path.join(DATA, "history", "ext.json")
OUT = os.path.join(DATA, "unusual_days.json")
THRESH = -2.995          # "3%": ‎-3.00% בעיגול נכנס (5.8.2024)
GAP = 21                 # ימי מסחר בלי יום חריג → מקרה חדש
NEAR = -5.0              # "דומים" = הסגירה הקודמת עד 5% מתחת לשיא השנה
H = [1, 5, 21, 126, 252]

# מה קרה — לפי הידיעות של אותו יום (מקרים חדשים: הכותרת היומית מ-history.json, או data/unusual_labels.json)
LABELS = {
    "2001-03-12": "התפוצצות בועת הדוט-קום", "2001-09-17": "פתיחת המסחר אחרי 11.9",
    "2002-07-10": "שוק דובי, שערוריות חשבונאות", "2003-03-24": "פתיחת המלחמה בעיראק",
    "2007-02-27": "קריסה בבורסת שנגחאי", "2008-02-05": "תחילת המשבר הפיננסי",
    "2008-06-06": "זינוק בנפט, חשש ממיתון", "2008-09-09": "הימים שלפני ליהמן",
    "2009-01-07": "שפל המשבר הפיננסי", "2009-06-22": "תיקון אחרי ראלי השפל",
    "2010-02-04": "משבר החוב ביוון", "2010-05-06": "ה'פלאש קראש'",
    "2011-08-04": "חשש מהורדת דירוג ארה\"ב", "2011-09-22": "משבר החוב באירופה",
    "2011-11-09": "משבר החוב באיטליה", "2015-08-21": "פיחות היואן בסין",
    "2016-06-24": "משאל הברקזיט", "2018-02-05": "קריסת הימורים על VIX נמוך",
    "2018-10-10": "זינוק בתשואות האג\"ח", "2018-12-04": "מלחמת הסחר עם סין",
    "2020-02-24": "התפרצות הקורונה", "2020-06-11": "חשש מגל קורונה שני",
    "2020-09-03": "מימוש בענקיות הטכנולוגיה", "2020-10-28": "גל קורונה לפני הבחירות",
    "2022-04-29": "העלאות הריבית של הפד", "2022-08-26": "נאום פאוול בג'קסון הול",
    "2024-08-05": "פירוק עסקאות הין", "2025-04-03": "המכסים של 'יום השחרור'",
    "2026-11-05": "מכירה בשבבים ובבינה המלאכותית אחרי ראלי הבחירות",
}


def load_csv(name):
    out = {}
    try:
        with open(os.path.join(BASE, name), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    out[r["Time"]] = float(r["Latest"])
                except (KeyError, ValueError, TypeError):
                    pass
    except OSError:
        pass
    return out


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def extend(spx, vix, br, now):
    """ימים אחרי קובצי Barchart: S&P/VIX מ-history.json, רוחב מ-indices.json (נצבר ב-ext.json)."""
    last = max(spx) if spx else ""
    hist = load_json(os.path.join(DATA, "history.json"), {}).get("days") or []
    for d in hist:
        day = d.get("date")
        if not day or day <= last or d.get("spx") is None:
            continue
        spx[day] = float(d["spx"])
        if d.get("vix") is not None:
            vix[day] = float(d["vix"])
    ext = load_json(EXT, {"br": {}})
    ind = load_json(os.path.join(DATA, "indices.json"), {})
    p = (ind.get("evidence") or {}).get("pctMa200")
    if ind.get("date") and p is not None and ind["date"] > (max(br) if br else ""):
        ext["br"][ind["date"]] = round(float(p), 2)
    for day, v in ext["br"].items():
        br.setdefault(day, v)
    ext["at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return ext


def headline_labels():
    out = {}
    for d in load_json(os.path.join(DATA, "history.json"), {}).get("days") or []:
        h = (d.get("headline") or "").strip()
        if d.get("date") and h:
            out[d["date"]] = re.split(r"\s[—–-]\s|:", h)[0].strip()[:70]
    return out


def compute(spx, vix, br):
    D = sorted(spx)
    C = [spx[d] for d in D]
    rows, last_ev = [], -10 ** 9
    for i in range(252, len(D)):
        ch = (C[i] / C[i - 1] - 1) * 100
        if ch > THRESH:
            continue
        first = i - last_ev > GAP
        last_ev = i
        if not first:
            continue
        hi = max(C[i - 252:i])
        v0, v1 = vix.get(D[i - 1]), vix.get(D[i])
        fwd = [round((C[i + h] / C[i] - 1) * 100, 2) if i + h < len(C) else None for h in H]
        mdd = round(min(C[i + 1:i + 22]) / C[i] * 100 - 100, 1) if i + 21 < len(C) else None
        rows.append({
            "d": D[i], "ch": round(ch, 2), "vix": round(v1, 1) if v1 else None,
            "vch": round((v1 / v0 - 1) * 100, 1) if v0 and v1 else None,
            "offPrev": round((C[i - 1] / hi - 1) * 100, 1),
            "br": round(br[D[i]]) if D[i] in br else None,
            "above200": C[i] > sum(C[i - 200:i]) / 200,
            "fwd": fwd, "mdd21": mdd, "idx": i,
        })
    return D, C, rows


def main(now=None):
    now = now or datetime.now(timezone.utc)
    spx, vix, br = load_csv("hist_SPX.csv"), load_csv("hist_VIX.csv"), load_csv("hist_S5TH.csv")
    if len(spx) < 300:
        print("build_unusual_days: אין היסטוריה (data/history/barchart) — דילוג")
        return 0
    ext = extend(spx, vix, br, now)
    D, C, rows = compute(spx, vix, br)
    labels = dict(LABELS)
    hl = headline_labels()
    labels.update(load_json(os.path.join(DATA, "unusual_labels.json"), {}))
    out_rows = []
    for r in rows:
        lab = labels.get(r["d"]) or hl.get(r["d"]) or ""
        out_rows.append([r["d"], r["ch"], r["vix"], r["vch"], r["offPrev"], r["br"]] + r["fwd"] + [r["mdd21"], lab])
    lt = rows[-1]
    after = sum(1 for i in range(lt["idx"] + 1, len(D)) if (C[i] / C[i - 1] - 1) * 100 <= THRESH)
    latest = {"d": lt["d"], "ch": lt["ch"], "vix": lt["vix"], "vch": lt["vch"], "offPrev": lt["offPrev"],
              "br": lt["br"], "above200": lt["above200"], "since": len(D) - 1 - lt["idx"], "laterDrops": after,
              "near": lt["offPrev"] >= NEAR}
    out = {"asOf": D[-1], "threshold": -3, "nearPct": NEAR, "horizons": H, "rows": out_rows, "latest": latest,
           "first": D[0], "brFirst": min(br) if br else None,
           "src": "Barchart ($SPX, $VIX, $S5TH) + דשבורד המדדים לימים האחרונים",
           "_meta": {"updatedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ")}}
    old = load_json(OUT, {})
    if {k: v for k, v in old.items() if k != "_meta"} != {k: v for k, v in out.items() if k != "_meta"}:
        write_json(OUT, out)
        write_json(EXT, ext)
        print("build_unusual_days: asOf=%s episodes=%d latest=%s (%+.2f%%, since %d)" % (D[-1], len(rows), lt["d"], lt["ch"], latest["since"]))
    else:
        print("build_unusual_days: ללא שינוי (asOf=%s)" % D[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
