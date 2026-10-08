#!/usr/bin/env python3
"""backfill_scan_universe.py — כלי חד-פעמי (8.10.2026): בונה את data/_scan_universe.json
(היקום של סריקת המועמדים בענן) מהיסטוריית ה-git של stocks-momentum.

היקום של הסריקה המקורית (ibkr-swing-system) = כל המניות שהופיעו אי-פעם בקובצי
momentum_D.M.YYYY.csv של איציק — שהם בדיוק המניות שעברו את פילטר הבסיס בדשבורד המומנטום
באותו יום (נבדק על 7.10: 151/151), עם ה-RVOL של אותו יום. מכאן והלאה fetch_momentum.py
מוסיף יום בכל תאריך CSV חדש.

שימוש:
    git clone --filter=blob:none https://github.com/nditzik/stocks-momentum <dir>
    python scripts/tools/backfill_scan_universe.py <dir> [--since 2026-06-25]
"""
import csv
import io
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from fetch_momentum import SCANNERS, DATE_RE, row_fields, passes_base, UNIVERSE_OUT, universe_day  # noqa: E402


def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def main(repo, since):
    log = git(repo, "log", "--format=%H %ad %s", "--date=short", "--", "data")
    days = {}
    for line in log.splitlines():
        sha, date, msg = line.split(" ", 2)
        if "refresh delayed quotes" in msg or msg.startswith("Merge"):
            continue
        names = [os.path.basename(f) for f in git(repo, "ls-tree", "--name-only", sha, "data/").splitlines()
                 if f.endswith(".csv")]
        merged, csv_date = {}, None
        for prefix, key in SCANNERS:
            cands = [n for n in names if n.startswith(prefix)]
            if not cands:
                continue
            fname = max(cands, key=lambda f: (lambda m: (int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else (0, 0, 0))(DATE_RE.search(f)))
            m = DATE_RE.search(fname)
            if m:
                csv_date = f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
            for r in csv.DictReader(io.StringIO(git(repo, "show", f"{sha}:data/{fname}"))):
                sym = (r.get("Symbol") or "").strip()
                if not sym or " " in sym:
                    continue
                if sym not in merged:
                    merged[sym] = row_fields(r)
                    merged[sym]["symbol"] = sym
                    merged[sym]["signals"] = []
                if key not in merged[sym]["signals"]:
                    merged[sym]["signals"].append(key)
        if not merged or not csv_date or csv_date in days or csv_date < since:
            continue
        days[csv_date] = universe_day(csv_date, merged.values())
        print(f"[ok] {csv_date} ← {sha[:7]} ({len(days[csv_date]['stocks'])})")
    out = [days[k] for k in sorted(days)]
    with open(UNIVERSE_OUT, "w", encoding="utf-8") as f:
        json.dump({"since": since, "days": out}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"[done] {UNIVERSE_OUT}: {len(out)} ימים, {len({s[0] for d in out for s in d['stocks']})} מניות")


if __name__ == "__main__":
    a = sys.argv[1:]
    since = a[a.index("--since") + 1] if "--since" in a else "2026-06-25"
    main(a[0], since)
