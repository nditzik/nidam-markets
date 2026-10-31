#!/usr/bin/env python3
"""
build_insider_daily.py — הפאנל "רכישות פנים · אתמול" בטאב Insider (30.10.2026, אושר במוקאפ
https://claude.ai/artifact/Tfb2A52gWP9oXDeKM43gCd).

קלט: data/insider_daily/<יום הדיווח>/buys.csv (+ history.csv) ו-data/insider_daily/history/*.csv
(relay_insider_mail.py), נרות מ-data/bars (fetch_bars מוריד אותם לכל טיקר כאן — `universe`).
פלט: data/insider_daily.json — הכל נגזר מחדש מהקבצים הגולמיים בכל ריצה; אין מצב שנשמר.

כללים:
  • נספרות רק קניות של חברות: קרן סגורה / ETF / SPAC (שם החברה) → excluded, מוצגות חיוורות.
  • בדיקת מחיר: עסקה שהמחיר שלה מחוץ לטווח הנר של אותו יום (±3%) — לא המניה הרגילה (מניות בכורה,
    HBAN 30.10: 13 עסקאות ב-$19–25 כשהמניה ב-$16–17) → נפסלת ונספרת ב-check. בלי נר = לא נבדקת.
  • מעקב: מסגירת יום הדיווח (היום שבו הקנייה נהייתה ציבורית), 5/20/60 ימי מסחר, מול SPY.
    "עד עכשיו" = הסגירה האחרונה מול המחיר שהמנהל שילם.
  • ההיסטוריה (24 חודשים) מתאחדת מכל קובצי ההיסטוריה + הקניות מהקבצים היומיים, בלי כפילויות.
  • התגים והמשפטים — דטרמיניסטיים, תיאור של מה שהמנהלים עשו, לא המלצה.
בדיקה בלי רשת: main(root=..., now=...).
"""
import csv
import glob
import io
import json
import os
import re
import sys
from bisect import bisect_left
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUND_RE = re.compile(r"\b(FUND|ETF|ETN|ACQUISITION\s+CORP|SPAC|PORTFOLIO|MUNICIPAL|INCOME\s+TRUST)\b", re.I)
HORIZONS = (5, 20, 60)
TRACK_DAYS = 120          # כמה זמן קנייה נשארת במעקב (ימים קלנדריים מיום הדיווח)
HIST_MONTHS = 24
WEEK_DAYS = 5            # "כל השבוע" = ימי הדיווח ב-5 ימי המסחר האחרונים


def num(x):
    try:
        s = str(x).replace(",", "").replace("$", "").replace("%", "").strip()
        return float(s) if s not in ("", "-", "—") else None
    except (TypeError, ValueError):
        return None


def read_csv(path):
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            return list(csv.DictReader(io.StringIO(f.read())))
    except OSError:
        return []


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


class Bars:
    def __init__(self, root):
        self.dir = os.path.join(root, "data", "bars")
        self.cache = {}

    def get(self, sym):
        if sym not in self.cache:
            d = load_json(os.path.join(self.dir, sym.replace(".", "-") + ".json"), {})
            b = d.get("bars") if isinstance(d, dict) else None
            self.cache[sym] = (b or [], [x[0] for x in (b or [])], {x[0]: x for x in (b or [])})
        return self.cache[sym]

    def price_ok(self, sym, day, price):
        """True = תואם, False = מחוץ לטווח היום, None = אין נר לבדוק."""
        bars, _, by = self.get(sym)
        b = by.get(day)
        if not b or price is None:
            return None
        return b[3] * 0.97 <= price <= b[2] * 1.03

    def fwd(self, sym, day, h):
        """תשואה מסגירת היום (או הנר הבא) עד h נרות אחריו; None כשעוד לא הגיע."""
        bars, ds, _ = self.get(sym)
        i = bisect_left(ds, day)
        if i >= len(bars) or i + h >= len(bars):
            return None
        return bars[i + h][4] / bars[i][4] - 1

    def elapsed(self, sym, day):
        bars, ds, _ = self.get(sym)
        i = bisect_left(ds, day)
        return max(0, len(bars) - 1 - i) if i < len(bars) else 0

    def last(self, sym):
        bars = self.get(sym)[0]
        return (bars[-1][0], bars[-1][4]) if bars else (None, None)


def role_he(role):
    r = (role or "").lower()
    parts = []
    if "chief executive" in r or re.search(r"\bceo\b", r):
        parts.append('מנכ"ל')
    elif "president" in r:
        parts.append("נשיא")
    if "chief financial" in r or re.search(r"\bcfo\b", r):
        parts.append('סמנכ"ל כספים')
    if "chair" in r:
        parts.append('יו"ר')
    if "10%" in r:
        parts.append("בעל 10%")
    if not parts and "director" in r:
        parts.append("דירקטור")
    if not parts:
        parts.append("נושא משרה")
    return " · ".join(parts)


def is_ceo(role):
    r = (role or "").lower()
    return "chief executive" in r or re.search(r"\bceo\b", r) is not None


def money(v):
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1e9:
        return "$%.1fB" % (v / 1e9)
    if a >= 1e6:
        return "$%.2fM" % (v / 1e6)
    if a >= 1e3:
        return "$%.0fK" % (v / 1e3)
    return "$%.0f" % v


def dm(day):
    return "%d.%d" % (int(day[8:10]), int(day[5:7])) if day else ""


def nice(s):
    """'MYERS FRANKLIN' → 'Myers Franklin' (SEC כותב שם משפחה ראשון, לפעמים באותיות גדולות)."""
    s = (s or "").strip()
    return s.title() if s.isupper() else s


def name_key(s):
    """בלי תלות בסדר: 'Michael P Lyons' (קובץ 28.10) = 'Lyons Michael P.' (Form 4) — TFC הופיעה פעמיים."""
    return "".join(sorted(re.findall(r"[a-z]+", (s or "").lower())))


def load_days(root):
    out = []
    for path in sorted(glob.glob(os.path.join(root, "data", "insider_daily", "????-??-??", "buys.csv"))):
        day = os.path.basename(os.path.dirname(path))
        out.append((day, read_csv(path), os.path.join(os.path.dirname(path), "history.csv")))
    return out


def load_history(root, days):
    paths = sorted(glob.glob(os.path.join(root, "data", "insider_daily", "history", "*.csv")))
    paths += [h for _, _, h in days if os.path.exists(h)]
    tx = {}
    for p in paths:
        for r in read_csv(p):
            t = (r.get("Ticker") or "").strip().upper()
            if not t:
                continue
            k = (t, name_key(r.get("Insider")), r.get("Trade Date"), (r.get("Type") or "").upper()[:1], num(r.get("Shares")))
            tx[k] = {"t": t, "who": nice(r.get("Insider")), "role": (r.get("Role") or "").strip(),
                     "trade": (r.get("Trade Date") or "").strip(), "filed": (r.get("Filing Date") or "").strip(),
                     "type": k[3], "shares": num(r.get("Shares")), "price": num(r.get("Price")),
                     "value": num(r.get("Value")), "plan": (r.get("10b5-1") or "").strip().lower() == "yes"}
    return list(tx.values())


def main(root=ROOT, now=None):
    now = now or datetime.now(timezone.utc)
    out_path = os.path.join(root, "data", "insider_daily.json")
    days = load_days(root)
    if not days:
        print("build_insider_daily: אין קבצים ב-data/insider_daily — דילוג")
        return 0
    bars = Bars(root)
    spy_days = bars.get("SPY")[1]

    # --- היומן: כל הקניות מכל הימים ---
    buys, seen = [], set()
    # מהחדש לישן: אותה עסקה בשני קבצים (TFC — 28.10 בלי Filing Date, 29.10 עם) נשמרת מהקובץ החדש והמלא
    for day, rows, _ in sorted(days, key=lambda x: x[0], reverse=True):
        for r in rows:
            t = (r.get("Ticker") or "").strip().upper()
            if not t:
                continue
            key = (t, name_key(r.get("Buyer")), r.get("Trade Date"), num(r.get("Shares")))
            if key in seen:
                continue
            seen.add(key)
            co = (r.get("Company") or "").strip()
            b = {"t": t, "co": co, "who": nice(r.get("Buyer")), "roleEn": (r.get("Role") or "").strip(),
                 "role": role_he(r.get("Role")), "ceo": is_ceo(r.get("Role")),
                 "filed": (r.get("Filing Date") or day).strip(), "trade": (r.get("Trade Date") or "").strip(), "day": day,
                 "shares": num(r.get("Shares")), "price": num(r.get("Price")), "value": num(r.get("Value")),
                 "before": num(r.get("Holdings Before")), "after": num(r.get("Holdings After")),
                 "holdPct": num(r.get("Holdings Change %")), "cap": num(r.get("Market Cap")),
                 "lastClose": num(r.get("Last Close")), "offHi": num(r.get("% From 52W High")),
                 "offLo": num(r.get("% From 52W Low")), "cluster": (r.get("Cluster (30d)") or "").lower() == "yes",
                 "clusterN": int(num(r.get("Cluster Count")) or 0), "url": (r.get("Form 4 URL") or "").strip()}
            if FUND_RE.search(co) or (b["cap"] is None and re.search(r"\bFUND\b|\bTRUST\b", co, re.I)):
                b["excluded"] = "fund"
            ok = bars.price_ok(t, b["trade"], b["price"])
            if ok is False:
                bar = bars.get(t)[2].get(b["trade"])
                # מתחת לשפל היום = כנראה הנפקה/הקצאה (RAPP 28.10: $21 כשהמניה נסחרה ב-$22–24)
                b["excluded"] = "offering" if bar and b["price"] < bar[3] else "price"
            b["priceCheck"] = ok
            buys.append(b)

    # אותו קונה, אותה מניה, אותו יום דיווח = שורה אחת (Form 4 אחד עם כמה עסקאות; LYCA 30.10)
    merged, idx = [], {}
    for b in buys:
        k = (b["t"], name_key(b["who"]), b["day"], b.get("excluded"))
        if k not in idx:
            idx[k] = b
            merged.append(b)
            continue
        m = idx[k]
        m["shares"] = (m["shares"] or 0) + (b["shares"] or 0)
        m["value"] = (m["value"] or 0) + (b["value"] or 0)
        m["price"] = round(m["value"] / m["shares"], 4) if m["shares"] else m["price"]
        m["tradeTo"] = max(m.get("tradeTo") or m["trade"], b["trade"])
        m["trade"] = min(m["trade"], b["trade"])
        if b["before"] is not None and (m["before"] is None or b["before"] < m["before"]):
            m["before"] = b["before"]
        if b["after"] is not None and (m["after"] is None or b["after"] > m["after"]):
            m["after"] = b["after"]
        if m["before"] and m["after"] is not None:
            m["holdPct"] = round((m["after"] - m["before"]) / m["before"] * 100, 2)
        m["parts"] = m.get("parts", 1) + 1
    buys = merged

    # --- מעקב: מסגירת יום הדיווח ---
    for b in buys:
        if b.get("excluded"):
            continue
        res = {}
        for h in HORIZONS:
            a, m = bars.fwd(b["t"], b["filed"], h), bars.fwd("SPY", b["filed"], h)
            if a is not None and m is not None:
                res[str(h)] = {"ret": round(a * 100, 2), "spy": round(m * 100, 2), "ex": round((a - m) * 100, 2)}
        b["res"] = res
        b["elapsed"] = bars.elapsed(b["t"], b["filed"])
        ld, lc = bars.last(b["t"])
        if lc and ld and ld >= b["trade"] and b["price"]:
            b["since"] = round((lc / b["price"] - 1) * 100, 2)
            b["sinceAt"] = ld
        elif b["lastClose"] and b["price"]:
            b["since"] = round((b["lastClose"] / b["price"] - 1) * 100, 2)
            b["sinceAt"] = b["day"]

    # יום בלי דיווחים (קובץ ריק בסוף שבוע/חג) לא מחליף את הרשימה האחרונה שיש בה רכישות
    latest = max([d for d, rows, _ in days if rows] or [d for d, _, _ in days])
    # 31.10.2026 (איציק: "הדוח של 29 נעלם"): לא רק היום האחרון — כל יום דיווח ב-5 ימי המסחר
    # האחרונים נשמר כתצוגה משלו, ועוד תצוגת "כל השבוע" שמאחדת אותם
    week_span = [d for d in spy_days if d <= latest][-WEEK_DAYS:]
    if latest not in week_span:
        week_span = (week_span + [latest])[-WEEK_DAYS:]
    view_days = sorted({b["day"] for b in buys if b["day"] in week_span} | {latest}, reverse=True)
    shown = [b for b in buys if b["day"] in view_days]
    today = [b for b in buys if b["day"] == latest]
    counted_all = [b for b in shown if not b.get("excluded")]

    # --- ההיסטוריה ---
    hist = load_history(root, days)
    for b in buys:   # הקניות מהקבצים היומיים הן גם היסטוריה
        if b.get("excluded") == "fund":
            continue
        k = (b["t"], name_key(b["who"]), b["trade"], "P", b["shares"])
        if not any((x["t"], name_key(x["who"]), x["trade"], x["type"], x["shares"]) == k for x in hist):
            hist.append({"t": b["t"], "who": b["who"], "role": b["roleEn"], "trade": b["trade"], "filed": b["filed"],
                         "type": "P", "shares": b["shares"], "price": b["price"], "value": b["value"], "plan": False})
    cut = (now - timedelta(days=HIST_MONTHS * 30.5)).strftime("%Y-%m-%d")
    check = {"received": 0, "valid": 0, "invalid": 0, "unchecked": 0, "invalidBy": {}}
    by_t = {}
    for x in hist:
        if x["trade"] < cut:
            continue
        ok = bars.price_ok(x["t"], x["trade"], x["price"])
        check["received"] += 1
        if ok is False:
            check["invalid"] += 1
            key = "%s · %s" % (x["t"], x["who"])
            check["invalidBy"][key] = check["invalidBy"].get(key, 0) + 1
            continue
        check["valid" if ok else "unchecked"] += 1
        by_t.setdefault(x["t"], []).append(x)

    hist_out = {}
    for b in counted_all:
        tx = sorted(by_t.get(b["t"], []), key=lambda x: x["trade"])
        has_hist = any(x["t"] == b["t"] for x in hist if x["type"] in ("P", "S") and not (x["type"] == "P" and x["trade"] == b["trade"] and name_key(x["who"]) == name_key(b["who"])))
        P = [x for x in tx if x["type"] == "P"]
        S = [x for x in tx if x["type"] == "S"]
        prior = [x for x in P if x["trade"] < b["trade"]]
        same = [x for x in prior if name_key(x["who"]) == name_key(b["who"])]
        past = []
        for x in prior:
            fd = x["filed"] or x["trade"]
            a, m = bars.fwd(x["t"], fd, 20), bars.fwd("SPY", fd, 20)
            a60 = bars.fwd(x["t"], fd, 60)
            past.append({"d": x["trade"], "who": x["who"], "role": role_he(x["role"]), "price": x["price"],
                         "r20": round(a * 100, 1) if a is not None else None,
                         "ex20": round((a - m) * 100, 1) if a is not None and m is not None else None,
                         "r60": round(a60 * 100, 1) if a60 is not None else None})
        done = [p for p in past if p["r20"] is not None and p["ex20"] is not None]
        st = {"buys": len(P), "buyV": sum(x["value"] or 0 for x in P), "sells": len(S), "sellV": sum(x["value"] or 0 for x in S),
              "planV": sum(x["value"] or 0 for x in S if x["plan"]), "sameN": len(same) + 1,
              "pastN": len(done), "pastAvg": round(sum(p["r20"] for p in done) / len(done), 1) if done else None,
              "pastWin": sum(1 for p in done if p["ex20"] > 0)}
        if not has_hist:
            b["hist"] = None
            continue
        # --- תגים מההקשר ---
        ctx = []
        span = (datetime.strptime(b["trade"], "%Y-%m-%d") - datetime.strptime(same[0]["trade"], "%Y-%m-%d")).days if same else 0
        if len(same) >= 2 and span <= 45:
            ctx.append(("big", "צובר · %d קניות ב-%d ימים" % (len(same) + 1, max(span, 1))))
        elif len(same) >= 2:
            ctx.append(("big", "קונה חוזר · %d בשנתיים" % (len(same) + 1)))
        elif same and (datetime.strptime(b["trade"], "%Y-%m-%d") - datetime.strptime(same[-1]["trade"], "%Y-%m-%d")).days <= 60:
            wk = max(1, round((datetime.strptime(b["trade"], "%Y-%m-%d") - datetime.strptime(same[-1]["trade"], "%Y-%m-%d")).days / 7))
            ctx.append(("big", "קנייה שנייה תוך %d שבועות" % wk))
        others = [x for x in prior if name_key(x["who"]) != name_key(b["who"])]
        y1 = (datetime.strptime(b["trade"], "%Y-%m-%d") - timedelta(days=365)).strftime("%Y-%m-%d")
        if not [x for x in prior if x["trade"] >= y1]:
            ctx.append(("big", ("קנייה ראשונה מאז " + dm(prior[-1]["trade"]) + "." + prior[-1]["trade"][2:4]) if prior else "קנייה ראשונה בשנתיים"))
        if b["value"] and P and b["value"] >= max(x["value"] or 0 for x in P) and len(P) >= 2 and not any("ראשונה" in c[1] for c in ctx):
            ctx.append(("big", "הגדולה בשנתיים"))
        nonplan = st["sellV"] - st["planV"]
        if st["buyV"] > 0 and nonplan >= 5 * st["buyV"] and nonplan >= 1e6:
            ctx.append(("low", "מנהלים מוכרים פי %d" % round(nonplan / st["buyV"])))
        big_plan = [x for x in S if x["plan"] and (x["value"] or 0) >= 1e6 and x["trade"] < b["trade"]]
        if big_plan and others and not ctx:
            ctx.append(("clu", "קונים אחרי מכירה מתוכננת"))
        b["ctx"] = [{"k": k, "txt": t} for k, t in ctx[:2]]
        sline = []
        if len(same) >= 1:
            sline.append("%s קנה %d פעמים בשנתיים, האחרונה ב-%s." % (b["who"], len(same) + 1, dm(same[-1]["trade"])))
        if st["sells"]:
            sline.append("בחברה: %d קניות · %s מול %d מכירות · %s%s." % (
                st["buys"], money(st["buyV"]), st["sells"], money(st["sellV"]),
                (" (%s מתוכננות מראש)" % money(st["planV"])) if st["planV"] >= 0.5 * st["sellV"] and st["planV"] else ""))
        else:
            sline.append("בחברה: %d קניות · %s, ואף מכירה בשנתיים." % (st["buys"], money(st["buyV"])))
        hist_out[b["t"]] = {
            "stats": st, "sent": " ".join(sline), "past": past[-8:],
            "tx": [{"d": x["trade"], "ty": x["type"], "p": x["price"], "v": x["value"], "who": x["who"],
                    "r": role_he(x["role"]), "plan": x["plan"]} for x in tx],
        }
        b["hist"] = True

    # --- תגים מהקובץ עצמו + חיתוך עם האתר ---
    picks = {(p.get("sym") or p.get("symbol") or "").upper() for p in (load_json(os.path.join(root, "data", "picks.json"), {}).get("picks") or [])}
    cands = {(c.get("symbol") or "").upper() for c in (load_json(os.path.join(root, "data", "candidates.json"), {}).get("candidates") or [])}
    moms = {(s.get("symbol") or "").upper() for s in (load_json(os.path.join(root, "data", "momentum.json"), {}).get("stocks") or [])}
    for b in shown:
        tags = []
        if b.get("excluded") == "fund":
            tags.append({"k": "dim", "txt": "קרן · לא נספרת"})
        elif b.get("excluded") == "offering":
            tags.append({"k": "dim", "txt": "כנראה בהנפקה · לא נספרת"})
        elif b.get("excluded") == "price":
            tags.append({"k": "dim", "txt": "מחיר לא תואם · לא נספרת"})
        else:
            if b["ceo"]:
                tags.append({"k": "ceo", "txt": 'מנכ"ל'})
            tags += b.get("ctx") or []
            if not b.get("ctx") and b["holdPct"] is not None and b["holdPct"] >= 100:
                tags.append({"k": "big", "txt": "הכפיל אחזקה" if b["holdPct"] < 300 else "פי %d באחזקה" % round(1 + b["holdPct"] / 100)})
            if b["cluster"] and b["clusterN"] >= 2:
                tags.append({"k": "clu", "txt": "אשכול · %d" % b["clusterN"]})
            if b["offLo"] is not None and b["offLo"] <= 5:
                tags.append({"k": "low", "txt": "ליד השפל"})
            if b["cap"] is not None and b["cap"] < 3e8:
                tags.append({"k": "dim", "txt": "חברה קטנה"})
            for s, lab in ((picks, "✦ בנבחרות"), (cands, "מועמדת"), (moms, "מומנטום")):
                if b["t"] in s:
                    tags.append({"k": "site", "txt": lab})
        b["tags"] = tags
    # --- מה בולט: עד 3, לפי עדיפות ---
    def score(b):
        s = (b["value"] or 0) / 1e6
        if b["ceo"]:
            s += 3
        if any("חוזר" in c["txt"] or "שנייה" in c["txt"] for c in b.get("ctx") or []):
            s += 2
        if any("ראשונה" in c["txt"] or "הגדולה" in c["txt"] for c in b.get("ctx") or []):
            s += 1.5
        if b["cluster"]:
            s += 1.5
        if b["offLo"] is not None and b["offLo"] <= 5:
            s += 1
        if b["cap"] is not None and b["cap"] < 3e8:
            s -= 2
        return s

    def hl(b):
        h = hist_out.get(b["t"])
        if b["ceo"]:
            k = 'המנכ"ל קונה'
        elif b["cluster"]:
            k = "אשכול"
        elif b["offLo"] is not None and b["offLo"] <= 5:
            k = "ליד השפל השנתי"
        else:
            k = (b.get("ctx") or [{"txt": b["role"]}])[0]["txt"]
        txt = "%s קנה ב-%s" % (b["role"], money(b["value"]))
        if b["holdPct"] is not None and b["holdPct"] >= 90:
            txt += ", האחזקה שלו %s" % ("הוכפלה" if b["holdPct"] < 150 else "גדלה פי %d" % round(1 + b["holdPct"] / 100))
        txt += "."
        if b["offHi"] is not None and b["offHi"] <= -10:
            txt += " המניה %d%% מתחת לשיא." % round(-b["offHi"])
        if h and h["stats"]["pastN"] >= 3:
            txt += " אחרי %d הקניות הקודמות בחברה: %s%.1f%% בממוצע תוך 20 יום." % (h["stats"]["pastN"], "+" if h["stats"]["pastAvg"] >= 0 else "−", abs(h["stats"]["pastAvg"]))
        return {"t": b["t"], "k": k, "txt": txt}

    def slim(b):
        keys = ("t", "co", "who", "role", "ceo", "filed", "trade", "tradeTo", "parts", "shares", "price", "value", "before", "after", "holdPct",
                "cap", "offHi", "offLo", "cluster", "clusterN", "url", "since", "sinceAt", "res", "elapsed", "excluded", "tags", "hist")
        return {k: b[k] for k in keys if k in b and b[k] is not None}

    def view(sel):
        """תצוגה אחת (יום דיווח או כל השבוע): הסיכום, משפט הפתיחה, השורות, מה בולט, חיתוך עם האתר."""
        counted = [b for b in sel if not b.get("excluded")]
        ranked = sorted(counted, key=score, reverse=True)
        lead = []
        for b in ranked[:2]:
            co = b["co"].title() if b["co"].isupper() else b["co"]
            lead.append("%s (%s): %s קנה ב-%s%s." % (co, b["t"], b["role"], money(b["value"]),
                                                  (" — " + b["ctx"][0]["txt"]) if b.get("ctx") else ""))
        return {
            "summary": {"n": len(counted), "total": round(sum(b["value"] or 0 for b in counted)),
                        "excluded": len(sel) - len(counted), "ceo": sum(1 for b in counted if b["ceo"]),
                        "ceoWho": [b["t"] for b in counted if b["ceo"]][:3],
                        "clusters": sum(1 for b in counted if b["cluster"] and b["clusterN"] >= 2),
                        "clusterWho": [b["t"] for b in counted if b["cluster"] and b["clusterN"] >= 2][:3],
                        "top": {"t": ranked[0]["t"], "v": ranked[0]["value"]} if ranked else None},
            "lead": " ".join(lead),
            "rows": [slim(b) for b in sorted(sel, key=lambda b: (bool(b.get("excluded")), -(b["value"] or 0)))],
            "highlights": [hl(b) for b in ranked[:3]],
            "siteHits": sorted({b["t"] for b in counted if any(t["k"] == "site" for t in b["tags"])}),
        }

    views = {d: dict(view([b for b in shown if b["day"] == d]), day=d) for d in view_days}
    order = list(view_days)
    if len(view_days) > 1:
        views["week"] = dict(view(shown), **{"from": min(week_span), "to": max(week_span), "days": len(view_days)})
        order = ["week"] + order
    cur = views[latest]

    # --- 20 ימי מסחר אחרונים ---
    span = [d for d in spy_days if d <= latest][-19:]
    if latest not in span:
        span.append(latest)
    span = sorted(set(span))[-20:]
    have = {d for d, _, _ in days}
    strip = []
    for d in span:
        bs = [b for b in buys if b["day"] == d and not b.get("excluded")]
        strip.append({"d": d, "n": len(bs), "v": round(sum(b["value"] or 0 for b in bs)), "has": d in have})

    # --- המעקב: כל הקניות שנספרו ב-TRACK_DAYS האחרונים ---
    tcut = (now - timedelta(days=TRACK_DAYS)).strftime("%Y-%m-%d")
    track = sorted([b for b in buys if not b.get("excluded") and b["filed"] >= tcut], key=lambda b: (b["filed"], b["value"] or 0), reverse=True)
    agg = {}
    for h in HORIZONS:
        r = [b["res"][str(h)] for b in track if str(h) in b.get("res", {})]
        if r:
            agg[str(h)] = {"n": len(r), "ret": round(sum(x["ret"] for x in r) / len(r), 2),
                           "ex": round(sum(x["ex"] for x in r) / len(r), 2), "win": sum(1 for x in r if x["ex"] > 0)}

    universe = sorted({b["t"] for b in buys if b["filed"] >= tcut and b.get("excluded") != "fund"})
    out = {
        "day": latest,
        # היום האחרון גם בשורש (החיפוש באתר ותאימות לאחור); התצוגות המלאות ב-views לפי viewOrder
        "summary": cur["summary"], "lead": cur["lead"], "rows": cur["rows"],
        "highlights": cur["highlights"], "siteHits": cur["siteHits"],
        "views": views, "viewOrder": order,
        "history": hist_out, "check": check,
        "days": strip, "firstDay": min(have),
        "track": [slim(b) for b in track[:60]], "trackAgg": agg,
        "universe": universe,
        "_meta": {"updatedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "grok mail → data/insider_daily", "ver": 1},
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("build_insider_daily: day=%s views=%s rows=%d counted=%d history=%d check=%s track=%d"
          % (latest, order, len(today), cur["summary"]["n"], len(hist_out), {k: check[k] for k in ("received", "valid", "invalid", "unchecked")}, len(track)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
