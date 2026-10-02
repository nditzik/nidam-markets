#!/usr/bin/env python3
"""
probe_analysts.py — בדיקה חד-פעמית (2.10.2026) לפיצ'ר "לקראת הדוח":
נתוני אנליסטים (Yahoo quoteSummary + שדות בסורק TradingView), נרות יומיים, ותזוזה מתומחרת באופציות.
לא כותב קבצים — מדפיס JSON ליומן. מורץ מ-.github/workflows/probe-analysts.yml.
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, "scripts/tools")
from probe_options import UA, get, opener, straddle  # noqa: E402

SYM = (sys.argv[1:] or ["JPM"])[0]
op = opener()
try:
    get(op, "https://fc.yahoo.com", 10)
except Exception:
    pass
crumb = get(op, "https://query2.finance.yahoo.com/v1/test/getcrumb")[1].decode().strip()
out = {}


def raw(v):
    return v.get("raw") if isinstance(v, dict) else v


# 1) Yahoo quoteSummary
mods = "earningsTrend,earningsHistory,financialData,calendarEvents,recommendationTrend,upgradeDowngradeHistory"
try:
    d = json.loads(get(op, f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{SYM}?modules={mods}&crumb={crumb}")[1])
    r = d["quoteSummary"]["result"][0]
    out["trend"] = [{k: raw(t.get(k)) for k in ("period", "endDate")} |
                    {"eps": {k: raw(v) for k, v in (t.get("earningsEstimate") or {}).items()},
                     "rev": {k: raw(v) for k, v in (t.get("revenueEstimate") or {}).items()},
                     "epsRev": {k: raw(v) for k, v in (t.get("epsRevisions") or {}).items()}}
                    for t in r.get("earningsTrend", {}).get("trend", [])[:2]]
    out["history"] = [{k: raw(h.get(k)) for k in ("quarter", "epsActual", "epsEstimate", "surprisePercent")}
                      for h in r.get("earningsHistory", {}).get("history", [])]
    fd = r.get("financialData", {})
    out["fin"] = {k: raw(fd.get(k)) for k in ("currentPrice", "targetMeanPrice", "targetHighPrice", "targetLowPrice",
                                              "recommendationMean", "recommendationKey", "numberOfAnalystOpinions")}
    ce = r.get("calendarEvents", {}).get("earnings", {})
    out["cal"] = {k: [raw(x) for x in v] if isinstance(v, list) else raw(v) for k, v in ce.items()}
    out["recTrend"] = r.get("recommendationTrend", {}).get("trend", [])[:2]
    out["actions"] = [{"date": datetime.fromtimestamp(a["epochGradeDate"], timezone.utc).date().isoformat(),
                       "firm": a.get("firm"), "action": a.get("action"), "from": a.get("fromGrade"),
                       "to": a.get("toGrade"), "pt": a.get("currentPriceTarget"), "ptPrev": a.get("priorPriceTarget")}
                      for a in r.get("upgradeDowngradeHistory", {}).get("history", [])[:12]]
except Exception as e:
    out["yahooErr"] = f"{type(e).__name__}: {e}"

# 2) TradingView — כל עמודה בנפרד (עמודה לא קיימת מפילה את כל הבקשה)
cols = ["earnings_release_next_date", "earnings_release_next_time", "earnings_per_share_forecast_next_fq",
        "revenue_forecast_next_fq", "earnings_per_share_fq", "earnings_per_share_forecast_fq", "revenue_fq",
        "recommendation_mark", "price_target_average", "price_target_high", "price_target_low"]
tv = {}
for c in cols:
    try:
        body = json.dumps({"filter": [{"left": "name", "operation": "equal", "right": SYM}],
                           "columns": [c], "range": [0, 1]}).encode()
        req = urllib.request.Request("https://scanner.tradingview.com/america/scan", data=body,
                                     headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            rows = json.loads(resp.read()).get("data") or []
        tv[c] = rows[0]["d"][0] if rows else None
    except Exception as e:
        tv[c] = f"ERR {getattr(e, 'code', '')}"
out["tv"] = tv

# 3) נרות יומיים (שנתיים) — לתגובות לדוחות קודמים
try:
    d = json.loads(get(op, f"https://query1.finance.yahoo.com/v8/finance/chart/{SYM}?interval=1d&range=2y")[1])
    res = d["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    out["bars"] = [[datetime.fromtimestamp(t, timezone.utc).date().isoformat(), round(c, 2)]
                   for t, c in zip(res["timestamp"], q["close"]) if c]
except Exception as e:
    out["barsErr"] = str(e)

# 4) אופציות: כל הפקיעות עד ~3 שבועות קדימה
try:
    d = json.loads(get(op, f"https://query2.finance.yahoo.com/v7/finance/options/{SYM}?crumb={crumb}")[1])["optionChain"]["result"][0]
    price = d["quote"].get("regularMarketPrice")
    opt = []
    for exp in d.get("expirationDates", [])[:5]:
        o = json.loads(get(op, f"https://query2.finance.yahoo.com/v7/finance/options/{SYM}?date={exp}&crumb={crumb}")[1])["optionChain"]["result"][0]["options"][0]
        rc = [(x["strike"], x.get("bid") or 0, x.get("ask") or 0, x.get("lastPrice") or 0) for x in o.get("calls", [])]
        rp = [(x["strike"], x.get("bid") or 0, x.get("ask") or 0, x.get("lastPrice") or 0) for x in o.get("puts", [])]
        opt.append([datetime.fromtimestamp(exp, timezone.utc).date().isoformat(), straddle(price, rc, rp)])
    out["opt"] = {"price": price, "asOf": datetime.now(timezone.utc).isoformat(timespec="minutes"), "byExpiry": opt}
except Exception as e:
    out["optErr"] = str(e)

print("PROBE_JSON_BEGIN")
print(json.dumps(out, ensure_ascii=False))
print("PROBE_JSON_END")
