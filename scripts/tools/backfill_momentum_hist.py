#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill_momentum_hist.py — כלי חד-פעמי (12.9.2026): משחזר את "היסטוריית הסנאפשוטים"
של דשבורד המומנטום מתוך היסטוריית ה-git של הריפו stocks-momentum, ל-data/_momentum_hist.json.

למה: ציון ה-Readiness בדשבורד כולל רכיב "מגמת היסטוריה" (עד 10 נק') שמחושב
מסנאפשוט שהדשבורד שומר ב-localStorage של הדפדפן בכל העלאת CSV. לשרת אין את זה —
ולכן 12 המועמדות באתר לא תאמו במלואן לדשבורד. הפתרון: אותם סנאפשוטים, מאותם
קבצי CSV, מתוך git (כל העלאה של איציק היא קומיט). מכאן והלאה fetch_momentum.py
מוסיף סנאפשוט לכל תאריך CSV חדש (עד 60 ימים, כמו HISTORY_MAX_DAYS בדשבורד).

שימוש:
    git clone --filter=blob:none https://github.com/nditzik/stocks-momentum <dir>
    python scripts/tools/backfill_momentum_hist.py <dir>
"""
import csv
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from fetch_momentum import SCANNERS, DATE_RE, row_fields, passes_base, snapshot_of, HIST_OUT, HIST_MAX  # noqa: E402


def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def main(repo):
    log = git(repo, "log", "--format=%H %ad %s", "--date=short", "--", "data")
    shas = []
    for line in log.splitlines():
        sha, date, msg = line.split(" ", 2)
        if "refresh delayed quotes" in msg or msg.startswith("Merge"):
            continue
        shas.append((date, sha))
    snaps = {}
    for date, sha in shas:
        files = git(repo, "ls-tree", "--name-only", sha, "data/").splitlines()
        names = [os.path.basename(f) for f in files if f.endswith(".csv")]
        merged, csv_date = {}, None
        for prefix, key in SCANNERS:
            cands = [n for n in names if n.startswith(prefix)]
            if not cands:
                continue
            fname = max(cands, key=lambda f: (lambda m: (int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else (0, 0, 0))(DATE_RE.search(f)))
            m = DATE_RE.search(fname)
            if m:
                csv_date = f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
            text = git(repo, "show", f"{sha}:data/{fname}")
            for r in csv.DictReader(io.StringIO(text)):
                sym = (r.get("Symbol") or "").strip()
                if not sym or " " in sym:
                    continue
                if sym not in merged:
                    merged[sym] = row_fields(r)
                    merged[sym]["symbol"] = sym
                    merged[sym]["signals"] = []
                if key not in merged[sym]["signals"]:
                    merged[sym]["signals"].append(key)
        if not merged or not csv_date or csv_date in snaps:
            continue
        for s in merged.values():
            s["signal_count"] = len(s["signals"])
        snaps[csv_date] = snapshot_of(csv_date, merged.values())
        print(f"[ok] {csv_date} ← {sha[:7]} ({len(snaps[csv_date]['stocks'])} מניות בבסיס)")
    hist = [snaps[k] for k in sorted(snaps)][-HIST_MAX:]
    with open(HIST_OUT, "w", encoding="utf-8") as f:
        json.dump({"days": hist}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"[done] {HIST_OUT}: {len(hist)} סנאפשוטים ({hist[0]['date']} → {hist[-1]['date']})")


if __name__ == "__main__":
    main(sys.argv[1])
