#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_weekend.py — "השוק סגור, כך נסחר סוף השבוע" (13.9.2026, רעיון של איציק).

כשהבורסות בארה"ב סגורות וגם החוזים של שיקגו (שישי 17:00 עד ראשון 18:00 שעון ניו יורק,
כלומר שישי 23:00/00:00 עד שני 01:00 שעון ישראל) המקום היחיד עם מחיר חי לשוק האמריקאי הוא
החוזים התמידיים של xyz על Hyperliquid (app.trade.xyz): S&P 500 ומניות בודדות. הקריפטו
נסחר 24/7 ומשמש מדחום לתיאבון הסיכון בכל שעה.

פלט: data/weekend.json
  mode      "weekend" (חוזי שיקגו סגורים) / "weekday"
  items     [{key, label, kind: index|stock|crypto, price, ref, refLabel, chg (מול ref, %),
              chg24 (מול 24 שעות קודם, %), vol24 (USDC), thin (מחזור דק), source}]
  ref = הסגירה הרשמית האחרונה מ-Yahoo (נר יומי אחרון); לקריפטו — המחיר בשישי 21:00 UTC
  (סגירת וול-סטריט), מנרות 60 דק' של Yahoo, כדי שהפער "מסגירת שישי" יהיה על אותו ציר.

מקורות: Hyperliquid info API (ציבורי, בלי מפתח): metaAndAssetCtxs עם dex="xyz" למניות
ולמדד, ובלי dex לביטקוין/את'ריום. Yahoo v8 chart לסגירות. כשל בכל מקור → הפריט מדולג;
כשל כולל → הקובץ הקיים נשאר.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "weekend.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
HL = "https://api.hyperliquid.xyz/info"

# (מפתח, תווית, סימבול xyz, סימבול Yahoo לסגירה)
XYZ = [
    ("sp500", "S&P 500", "SP500", "^GSPC"),
    ("nvda", "Nvidia", "NVDA", "NVDA"),
    ("msft", "Microsoft", "MSFT", "MSFT"),
    ("avgo", "Broadcom", "AVGO", "AVGO"),
    ("sndk", "SanDisk", "SNDK", "SNDK"),
    ("googl", "Alphabet", "GOOGL", "GOOGL"),
    ("meta", "Meta", "META", "META"),
    ("amzn", "Amazon", "AMZN", "AMZN"),
    ("pltr", "Palantir", "PLTR", "PLTR"),   # 13.9.2026 ערב — "כדי שיהיה סימטרי" (9 אריחים, 3×3)
]
CRYPTO = [("btc", "ביטקוין", "BTC", "BTC-USD"), ("eth", "את'ריום", "ETH", "ETH-USD")]
THIN_USDC = 1_000_000          # מתחת לזה האריח מסומן "מחזור דק"


def num(v):
    try:
        return float(v)
    except Exception:
        return None


def israel_stamp():
    off = 3 if 4 <= datetime.now(timezone.utc).month <= 10 else 2
    return (datetime.now(timezone.utc) + timedelta(hours=off)).strftime("%d/%m/%Y %H:%M")


def mode_now():
    """weekend = חוזי שיקגו סגורים: שישי 17:00 עד ראשון 18:00 שעון ניו יורק."""
    ny = datetime.now(ZoneInfo("America/New_York"))
    wd, h = ny.weekday(), ny.hour
    if wd == 4 and h >= 17 or wd == 5 or wd == 6 and h < 18:
        return "weekend"
    return "weekday"


def hl_ctxs(dex=None):
    body = {"type": "metaAndAssetCtxs"}
    if dex:
        body["dex"] = dex
    req = urllib.request.Request(HL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        meta, ctxs = json.loads(r.read().decode("utf-8"))
    out = {}
    for a, c in zip(meta.get("universe") or [], ctxs or []):
        name = (a.get("name") or "").split(":")[-1]
        out[name] = {"mark": num(c.get("markPx")), "prev": num(c.get("prevDayPx")), "vol": num(c.get("dayNtlVlm")), "oi": num(c.get("openInterest"))}
    return out


def yahoo_chart(sym, interval, rng):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(sym)
           + f"?interval={interval}&range={rng}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        res = json.loads(r.read().decode("utf-8"))["chart"]["result"][0]
    ts = res.get("timestamp") or []
    cl = ((res.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    return [(datetime.fromtimestamp(t, timezone.utc), float(c)) for t, c in zip(ts, cl) if c is not None]


def last_close(sym):
    """הסגירה הרשמית האחרונה (נר יומי אחרון שאינו של יום מסחר פתוח עכשיו)."""
    bars = yahoo_chart(sym, "1d", "5d")
    if not bars:
        return None, None
    ny = datetime.now(ZoneInfo("America/New_York"))
    t, c = bars[-1]
    # אם הנר האחרון הוא של היום ווול-סטריט עדיין פתוחה — הוא חלקי; קח את הקודם
    if t.astimezone(ZoneInfo("America/New_York")).date() == ny.date() and ny.weekday() < 5 and 9 <= ny.hour < 16 and len(bars) >= 2:
        t, c = bars[-2]
    return c, t.astimezone(ZoneInfo("America/New_York")).strftime("%d.%m")


def crypto_ref(sym):
    """המחיר בסגירת וול-סטריט האחרונה (שישי 20:00 UTC בנר 60 דק' = 21:00 סגירה)."""
    bars = yahoo_chart(sym, "60m", "5d")
    ny = ZoneInfo("America/New_York")
    cands = [(t, c) for t, c in bars if t.astimezone(ny).weekday() < 5 and t.astimezone(ny).hour == 15]
    if not cands:
        return None, None
    t, c = cands[-1]
    return c, t.astimezone(ny).strftime("%d.%m")


def pct(a, b):
    return round((a / b - 1) * 100, 2) if a and b else None


def main():
    mode = mode_now()
    items = []
    try:
        xyz = hl_ctxs("xyz")
    except Exception as e:
        print(f"[warn] Hyperliquid xyz נכשל: {e}")
        xyz = {}
    try:
        main_dex = hl_ctxs()
    except Exception as e:
        print(f"[warn] Hyperliquid main נכשל: {e}")
        main_dex = {}

    for key, label, hsym, ysym in XYZ:
        c = xyz.get(hsym)
        if not c or c["mark"] is None:
            continue
        try:
            ref, ref_lbl = last_close(ysym)
        except Exception as e:
            print(f"[warn] {ysym}: {e}")
            ref, ref_lbl = None, None
        items.append({
            "key": key, "label": label, "kind": "index" if key == "sp500" else "stock",
            "price": c["mark"], "ref": ref, "refLabel": ("סגירת " + ref_lbl) if ref_lbl else None,
            "chg": pct(c["mark"], ref), "chg24": pct(c["mark"], c["prev"]),
            "vol24": round(c["vol"] or 0), "thin": (c["vol"] or 0) < THIN_USDC, "source": "xyz",
        })
    for key, label, hsym, ysym in CRYPTO:
        c = main_dex.get(hsym)
        if not c or c["mark"] is None:
            continue
        try:
            ref, ref_lbl = crypto_ref(ysym)
        except Exception as e:
            print(f"[warn] {ysym}: {e}")
            ref, ref_lbl = None, None
        items.append({
            "key": key, "label": label, "kind": "crypto",
            "price": c["mark"], "ref": ref, "refLabel": ("סגירת וול-סטריט " + ref_lbl) if ref_lbl else None,
            "chg": pct(c["mark"], ref), "chg24": pct(c["mark"], c["prev"]),
            "vol24": round(c["vol"] or 0), "thin": False, "source": "hyperliquid",
        })

    if not items:
        print("[keep] אין נתונים — הקובץ הקיים נשאר.")
        return 0 if os.path.exists(OUT) else 1
    payload = {"mode": mode, "items": items,
               "_meta": {"updatedAt": israel_stamp(), "source": "hyperliquid+yahoo"}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"[done] {mode} · {len(items)} פריטים: " + " · ".join(
        f"{i['label']} {i['chg']:+.2f}%" if i["chg"] is not None else f"{i['label']} —" for i in items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
