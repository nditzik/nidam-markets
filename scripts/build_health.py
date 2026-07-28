#!/usr/bin/env python3
"""
build_health.py — מייצר data/_health.json: מחוון בריאות לכל מקור נתונים.

רץ אחרון בפייפליין (אחרי כל המשיכות). קורא את חותמת _meta.updatedAt מכל קובץ
נתונים, מחשב "גיל" מול עכשיו, וקובע סטטוס: ok / stale / down / pending.
משמש גם כ-heartbeat (generatedAt מתעדכן בכל ריצה).
"""
import json
import os
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_health.json")

# key, קובץ, כותרת בעברית
SOURCES = [
    ("indices", "indices.json", "מדדים"),
    ("momentum", "momentum.json", "מומנטום"),
    ("morning", "morning.json", "סקירת בוקר"),
    ("briefing", "briefing.json", "תדרוך משקיעים"),
    ("candidates", "candidates.json", "מועמדים"),
]

# ספי טריות (שעות) — סובלני לסופ"ש/לילה
OK_H = 30
STALE_H = 96


def israel_now():
    now = datetime.now(timezone.utc)
    off = 3 if 4 <= now.month <= 10 else 2
    return now + timedelta(hours=off)


def parse_stamp(s):
    try:
        return datetime.strptime(s, "%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return None


def main():
    now = israel_now().replace(tzinfo=None)
    out = {"generatedAt": now.strftime("%d/%m/%Y %H:%M"), "sources": []}

    for key, fname, label in SOURCES:
        path = os.path.join(DATA, fname)
        entry = {"key": key, "label": label, "updatedAt": None,
                 "ageHours": None, "status": "down", "detail": ""}
        if not os.path.exists(path):
            entry["detail"] = "אין קובץ"
            out["sources"].append(entry)
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            entry["detail"] = "קובץ לא תקין"
            out["sources"].append(entry)
            continue

        if isinstance(d, dict) and d.get("_status") == "pending":
            entry["status"] = "pending"
            entry["detail"] = "טרם חובר"
            out["sources"].append(entry)
            continue

        stamp = (d.get("_meta") or {}).get("updatedAt") if isinstance(d, dict) else None
        entry["updatedAt"] = stamp
        dt = parse_stamp(stamp)
        if dt is None:
            entry["detail"] = "אין חותמת"
            out["sources"].append(entry)
            continue

        age = (now - dt).total_seconds() / 3600.0
        entry["ageHours"] = round(age, 1)
        entry["status"] = "ok" if age <= OK_H else ("stale" if age <= STALE_H else "down")
        out["sources"].append(entry)
        print(f"[health] {label}: {entry['status']} ({stamp}, {age:.1f}h)")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[done] נכתב {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
