#!/usr/bin/env python3
"""
strip_advice.py — מסיר מקובצי הנתונים הגולמיים שדות של הוראת פעולה ותוכנית עסקה (14.11.2026, איציק: "מחק").

האתר הוא מערכת מידע (scripts/prompts/_language.md), וגם הקבצים הגולמיים שהוא מפרסם לא אמורים להכיל
המלצה או תוכנית עסקה:
  · indices.json    — conclusion.recommendation.action, riskOff.actionLine, ושורות "המלצה: …" ב-aiSummary
                      (מגיעים מהדשבורד המקומי של איציק; improve/worsen = תנאים, נשארים)
  · candidates.json — stop / target / risk_pct / tp_pct של כל מניה (entry = סגירת יום הסריקה, נשאר כמחיר ייחוס)

נקרא מתוך fetch_dashboards.py, scan_cloud.py ו-fetch_ibkr.py לפני הכתיבה. הרצה ישירה מנקה את הקבצים הקיימים.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
ADVICE_LINE = re.compile(r"^\s*(?:📌\s*)?המלצה\s*[:：]|להחזיק קיים|להוסיף חשיפה|חשיפה חדשה|להדק סטופ")
CAND_DROP = ("stop", "target", "risk_pct", "tp_pct")


def strip_indices(d):
    if not isinstance(d, dict):
        return d
    rec = (d.get("conclusion") or {}).get("recommendation")
    if isinstance(rec, dict):
        rec.pop("action", None)
    if isinstance(d.get("riskOff"), dict):
        d["riskOff"].pop("actionLine", None)
    ai = d.get("aiSummary")
    if isinstance(ai, dict):
        for b in ai.get("blocks") or []:
            if isinstance(b, dict) and isinstance(b.get("lines"), list):
                b["lines"] = [l for l in b["lines"] if not (isinstance(l, str) and ADVICE_LINE.search(l))]
        if isinstance(ai.get("paragraphs"), list):
            ai["paragraphs"] = [p for p in ai["paragraphs"] if not (isinstance(p, str) and ADVICE_LINE.search(p))]
    return d


def strip_candidates(d):
    if isinstance(d, dict):
        for c in d.get("candidates") or []:
            if isinstance(c, dict):
                for k in CAND_DROP:
                    c.pop(k, None)
    return d


def main():
    for name, fn in (("indices.json", strip_indices), ("candidates.json", strip_candidates)):
        p = os.path.join(DATA, name)
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception as e:
            print("[strip] %s: %s" % (name, e))
            continue
        before = json.dumps(d, ensure_ascii=False, sort_keys=True)
        fn(d)
        if json.dumps(d, ensure_ascii=False, sort_keys=True) != before:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
            print("[strip] %s נוקה" % name)
        else:
            print("[strip] %s נקי" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
