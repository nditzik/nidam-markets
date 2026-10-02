#!/usr/bin/env python3
"""
probe_edates.py — בדיקה חד-פעמית (2.10.2026): מאיפה לקחת תאריכי דוחות קודמים אמיתיים
(ההשערה "יום המחזור הגבוה" נתנה ל-JPM את 8.7 במקום 14.7). שלושה מקורות:
Yahoo visualization (כמו yfinance.get_earnings_dates), Nasdaq earnings-surprise, Yahoo chart events=earn.
"""
import json
import sys
import urllib.request

sys.path.insert(0, "scripts/tools")
from probe_options import UA, get, opener  # noqa: E402

for SYM in (sys.argv[1:] or ["JPM", "PEP", "MSFT"]):
    print("==", SYM)
    op = opener()
    try:
        get(op, "https://fc.yahoo.com", 10)
    except Exception:
        pass
    crumb = get(op, "https://query2.finance.yahoo.com/v1/test/getcrumb")[1].decode().strip()
    # 1) Yahoo visualization
    try:
        body = json.dumps({"size": 8, "query": {"operator": "and", "operands": [
            {"operator": "eq", "operands": ["ticker", SYM]}, {"operator": "eq", "operands": ["eventtype", "2"]}]},
            "sortField": "startdatetime", "sortType": "DESC", "entityIdType": "earnings",
            "includeFields": ["startdatetime", "timeZoneShortName", "epsestimate", "epsactual", "epssurprisepct", "eventtype"]}).encode()
        req = urllib.request.Request(f"https://query1.finance.yahoo.com/v1/finance/visualization?lang=en-US&region=US&crumb={crumb}",
                                     data=body, headers={"Content-Type": "application/json"})
        with op.open(req, timeout=20) as r:
            d = json.loads(r.read())
        rows = d["finance"]["result"][0]["documents"][0]["rows"]
        print("  yahoo-viz:", rows[:6])
    except Exception as e:
        print("  yahoo-viz FAIL:", type(e).__name__, e)
    # 2) Nasdaq
    try:
        req = urllib.request.Request(f"https://api.nasdaq.com/api/company/{SYM}/earnings-surprise",
                                     headers={"User-Agent": UA, "Accept": "application/json, text/plain, */*",
                                              "Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read())
        print("  nasdaq:", [(x.get("fiscalQtrEnd"), x.get("dateReported"), x.get("eps"), x.get("consensusForecast"))
                            for x in d["data"]["earningsSurpriseTable"]["rows"]])
    except Exception as e:
        print("  nasdaq FAIL:", type(e).__name__, e)
    # 3) Yahoo chart events=earn
    try:
        d = json.loads(get(op, f"https://query1.finance.yahoo.com/v8/finance/chart/{SYM}?interval=1d&range=2y&events=earn")[1])
        ev = d["chart"]["result"][0].get("events", {})
        print("  chart-events keys:", list(ev.keys()), str(ev.get("earnings"))[:300])
    except Exception as e:
        print("  chart-events FAIL:", type(e).__name__, e)
