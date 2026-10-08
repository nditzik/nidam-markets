#!/usr/bin/env python3
"""
fetch_ibkr.py — מושך את מועמדי ה-IBKR מהריפו הציבורי nidam-candidates → data/candidates.json.

המערכת המקומית דוחפת candidates.json ל-nidam-candidates (דרך export_candidates.py),
והאתר קורא אותו ישירות — בלי מייל ובלי סיסמה. הקובץ הוא candidate-only מעצם בנייתו
(אין נתוני חשבון/פוזיציות/יתרות).

עמידות: כשל משיכה → משאיר candidates.json קיים (לא מפיל את ה-Action).
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from iltime import il_off   # שעון ישראל אמיתי (zoneinfo), ראו iltime.py

RAW_URL = "https://raw.githubusercontent.com/nditzik/nidam-candidates/main/candidates.json"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "candidates.json")


def israel_stamp():
    now = datetime.now(timezone.utc)
    off = il_off(now)
    return (now + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def fetch():
    req = urllib.request.Request(RAW_URL, headers={"User-Agent": "nidam-markets-bot"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    try:
        payload = fetch()
    except Exception as e:
        print(f"[warn] משיכת מועמדים נכשלה: {e}")
        return 0 if os.path.exists(OUT) else 1

    if not isinstance(payload, dict) or "candidates" not in payload:
        print("[warn] פורמט מועמדים לא תקין.")
        return 0 if os.path.exists(OUT) else 1

    # מודע-תוכן: כותב רק אם השתנה (משאיר את _meta של המקור, מרענן חותמת משיכה)
    existing = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}
    # רשימה ריקה לא דורסת רשימה מלאה (1.10.2026): סריקת בוקר שלא קיבלה נתונים מ-IBKR
    # (חיבור כפול לחשבון חסם את המשיכה) ייצאה 0 מועמדים ומחקה את רשימת הערב התקינה.
    # יום אמיתי בלי איתותים נראה אותו דבר — עדיף להשאיר את הרשימה הקודמת עד הסריקה הבאה.
    if not payload.get("candidates") and existing.get("candidates"):
        print(f"[keep] התקבלה רשימה ריקה ({payload.get('date')}, "
              f"{(payload.get('_meta') or {}).get('updatedAt')}) — נשארת הרשימה של "
              f"{existing.get('date')} ({len(existing['candidates'])} מועמדים).")
        return 0

    # מ-9.10.2026 הסריקה רצה בענן (scan_cloud.py) והיא המקור. רשימת IBKR נכנסת רק כגיבוי —
    # כשהיא מיום ריצה מאוחר מזה של הענן (בוקר שבו הסריקה בענן לא רצה/נכשלה).
    if (existing.get("_meta") or {}).get("source") == "nidam-cloud-scan" and \
       str(payload.get("date") or "") <= str(existing.get("date") or ""):
        print(f"[cloud] הסריקה בענן ({existing.get('date')}) עדכנית — רשימת IBKR ({payload.get('date')}) לא נכנסת.")
        return 0

    if {k: v for k, v in existing.items() if k != "_meta"} == \
       {k: v for k, v in payload.items() if k != "_meta"}:
        print("[nochange] אין מועמדים חדשים.")
        return 0

    meta = payload.get("_meta") or {}
    meta["fetchedAt"] = israel_stamp()
    if "updatedAt" not in meta:
        meta["updatedAt"] = meta["fetchedAt"]
    meta["source"] = "ibkr-swing-system"
    payload["_meta"] = meta

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT} ({payload.get('shown', '?')} מועמדים, {payload.get('date')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
