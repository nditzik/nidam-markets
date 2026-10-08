"""probe_scan_yahoo.py — בדיקה חד-פעמית (8.10.2026): סריקת המועמדים על נרות Yahoo מול IBKR.

רץ על ה-runner (לסנדבוקס אין רשת ל-Yahoo). לוקח את היקום ואת התוצאה של הסריקה המקורית
מבוקר 8.10 (nidam-candidates/scanner/golden), מושך נרות מ-Yahoo לכל 1,148 המניות,
ומריץ את scripts/scan_candidates.py בשני אופני חלון:
  A — אותו חלון כמו IBKR לכל מניה (first_bar מה-golden עד 7.10) → מבודד את הבדל הספק
  B — 124 הנרות האחרונים (מה שהגרסה בענן תעשה בפועל)
פלט: scripts/tools/out/scan_yahoo_probe.json (סיכום + כל מניה שהתוצאה שלה שונה).
"""
import csv
import io
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from scripts import scan_candidates as sc  # noqa: E402

RAW = "https://raw.githubusercontent.com/nditzik/nidam-candidates/main/scanner/golden/"
OUT = os.path.join(ROOT, "scripts", "tools", "out", "scan_yahoo_probe.json")
LAST = "2026-10-07"
START_2Y = "2024-10-08"
P1 = int(datetime(2024, 9, 1, tzinfo=timezone.utc).timestamp())
P2 = int(datetime(2026, 10, 8, tzinfo=timezone.utc).timestamp())


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def ybars(sym):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/" + sym.replace(".", "-") +
           "?period1=%d&period2=%d&interval=1d" % (P1, P2))
    err = None
    for attempt in range(3):
        try:
            res = json.loads(get(url))["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            off = (res.get("meta") or {}).get("gmtoffset") or 0
            out = []
            for t, o, h, l, c, v in zip(res.get("timestamp") or [], q["open"], q["high"], q["low"], q["close"], q["volume"]):
                if None in (o, h, l, c):
                    continue
                d = datetime.fromtimestamp(t + off, timezone.utc).strftime("%Y-%m-%d")
                if d <= LAST:
                    out.append([d, o, h, l, c, v or 0])
            return sym, out
        except Exception as e:
            err = e
            time.sleep(2 + attempt * 3)
    print("FAIL", sym, err)
    return sym, None


def run(universe, bars6, bars2):
    cands, results = sc.scan(universe, bars6, bars2)
    return cands, results


def main():
    U = list(csv.DictReader(io.StringIO(get(RAW + "universe.csv"))))
    gold = json.loads(get(RAW + "candidates.json"))
    universe = [(r["symbol"], float(r["rvol_file"]) if r["rvol_file"] != "" else None) for r in U]
    first = {r["symbol"]: r["first_bar"] for r in U}
    with ThreadPoolExecutor(8) as ex:
        Y = dict(ex.map(ybars, [u[0] for u in universe]))
    ok = sum(1 for v in Y.values() if v)
    print("yahoo ok", ok, "/", len(Y))

    def w_a(s):
        b = Y.get(s)
        return [x for x in b if x[0] >= first[s]] if b and first.get(s) else None

    def w_b(s):
        b = Y.get(s)
        return b[-124:] if b else None

    def w_2y(s):
        b = Y.get(s)
        return [x for x in b if x[0] >= START_2Y] if b else None

    gres = {r["symbol"]: r for r in U}
    gsyms = [c["symbol"] for c in gold["candidates"]]
    summary = {}
    diffs = {}
    for name, w in (("A_ibkr_window", w_a), ("B_last124", w_b)):
        cands, results = run(universe, w, w_2y)
        ysyms = [c["symbol"] for c in cands]
        gstage = {s: ("PASS" if r["result"] == "PASS" else r["fail_stage"]) for s, r in gres.items()}
        changed = []
        for s, (st, reason) in results.items():
            if gstage[s] != st:
                g = gres[s]
                yb = (w(s) or [None])[-1]
                changed.append({"sym": s, "ibkr": gstage[s], "yahoo": st, "ibkrReason": g["reason"], "yahooReason": reason,
                                "ibkrLast": [g["first_bar"], g["last_bar"], g["n_bars"], g["open"], g["low"], g["close"],
                                             g["ema20"], g["ema40"], g["ema50"], g["atr14"]],
                                "yahooLast": yb, "yahooN": len(w(s) or [])})
        gc = {c["symbol"]: c for c in gold["candidates"]}
        lv = []
        for c in cands:
            if c["symbol"] in gc:
                g = gc[c["symbol"]]
                lv.append({"sym": c["symbol"], "entry": [g["entry"], c["entry"]], "stop": [g["stop"], c["stop"]],
                           "setup": [g["setup"], c["setup"]], "hist_r": [g["hist_r"], c.get("hist_r")],
                           "ext": [g["ext_atr"], c.get("ext_atr")], "rank": [g["rank"], ysyms.index(c["symbol"]) + 1]})
        summary[name] = {"count": len(cands), "both": len(set(ysyms) & set(gsyms)),
                         "onlyIbkr": sorted(set(gsyms) - set(ysyms)), "onlyYahoo": sorted(set(ysyms) - set(gsyms)),
                         "stageChanged": len(changed), "top10ibkr": gsyms[:10], "top10yahoo": ysyms[:10],
                         "noData": sorted(s for s, (st, _) in results.items() if st == "0_no_data")[:60]}
        diffs[name] = {"changed": changed, "levels": lv}
        print(name, json.dumps(summary[name])[:600])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"built": datetime.now(timezone.utc).isoformat(timespec="minutes"), "yahooOk": ok,
               "universe": len(universe), "summary": summary, "diffs": diffs},
              open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("wrote", OUT, os.path.getsize(OUT))


if __name__ == "__main__":
    main()
