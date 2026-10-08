"""בדיקת scan_candidates מול ה-golden של הסריקה המקורית (8.10.2026).

שימוש: python3 scripts/tests/test_scan_golden.py <נתיב לתיקיית golden>
(התיקייה: nidam-candidates/scanner/golden — universe.csv, bars/, bars_2y/, candidates.json)
עובר = candidates.json זהה (בלי _meta) + אותה תוצאה (עבר/נכשל) לכל מניה שיש לה נרות.
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from scripts import scan_candidates as sc  # noqa: E402


def read_bars(path):
    if not os.path.exists(path):
        return None
    out = []
    with open(path) as f:
        for r in csv.DictReader(f):
            out.append([r["date"], float(r["open"]), float(r["high"]), float(r["low"]),
                        float(r["close"]), float(r["volume"] or 0)])
    return out


def main(golden):
    rows = list(csv.DictReader(open(os.path.join(golden, "universe.csv"), encoding="utf-8")))
    universe = [(r["symbol"], float(r["rvol_file"]) if r["rvol_file"] != "" else None) for r in rows]
    have = set(f[:-4] for f in os.listdir(os.path.join(golden, "bars")))
    universe = [u for u in universe if u[0] in have]
    cands, results = sc.scan(universe,
                             lambda s: read_bars(os.path.join(golden, "bars", s + ".csv")),
                             lambda s: read_bars(os.path.join(golden, "bars_2y", s + ".csv")))
    gold = json.load(open(os.path.join(golden, "candidates.json"), encoding="utf-8"))
    out = sc.payload(cands, gold["date"], "")
    strip = lambda p: {k: v for k, v in p.items() if k != "_meta"}
    same = strip(out) == strip(gold)
    if not same:
        for g, n in zip(gold["candidates"], out["candidates"]):
            if g != n:
                print("DIFF", g["symbol"], n["symbol"], {k: (g[k], n.get(k)) for k in g if g[k] != n.get(k)})
                break
    exp = {r["symbol"]: r for r in rows}
    wrong = []
    for s, (stage, reason) in results.items():
        e = exp[s]
        if (e["result"] == "PASS") != (stage == "PASS") or (stage != "PASS" and e["fail_stage"] != stage):
            wrong.append((s, e["fail_stage"], stage, e["reason"], reason))
    print("candidates.json identical:", same, "(%d/%d)" % (out["shown"], out["count"]))
    print("pass/fail+stage match: %d/%d" % (len(results) - len(wrong), len(results)), wrong[:5])
    return 0 if same and not wrong else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
