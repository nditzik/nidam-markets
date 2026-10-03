"""probe_surprise.py — בדיקה חד-פעמית (3.10.2026) לשלב 2 של עונת הדוחות: האם סורק TradingView נותן
"בפועל מול צפי" (רווח והכנסות) לכל חברות המדד בקריאה אחת. כל עמודה נבדקת לבד (עמודה לא מוכרת
מפילה את כל הבקשה), ואז קריאה אחת עם העמודות שעבדו על חברות שדיווחו בשבועיים האחרונים.
פלט: data/_probe_surprise.txt (נמחק אחרי הבדיקה).
"""
import json
import urllib.request

TV = "https://scanner.tradingview.com/america/scan"
CANDIDATES = [
    "earnings_per_share_fq", "earnings_per_share_diluted_fq", "earnings_per_share_forecast_fq",
    "eps_surprise_fq", "eps_surprise_percent_fq",
    "revenue_fq", "total_revenue_fq", "revenue_forecast_fq", "revenue_surprise_fq", "revenue_surprise_percent_fq",
    "earnings_release_date", "earnings_release_next_date", "sector",
]
SAMPLE = ["NASDAQ:MU", "NYSE:NKE", "NYSE:ACN", "NASDAQ:COST", "NYSE:FDX", "NYSE:GIS", "NASDAQ:TSLA", "NYSE:CCL", "NASDAQ:PAYX", "NYSE:KMX"]


def scan(cols, tickers=None, extra=None):
    body = {"columns": cols, "range": [0, 20]}
    if tickers:
        body["symbols"] = {"tickers": tickers}
    else:
        body["filter"] = extra or []
    req = urllib.request.Request(TV, data=json.dumps(body).encode(), headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


out = []
ok = []
for c in CANDIDATES:
    try:
        d = scan(["name", c], SAMPLE[:2])
        out.append("OK   %-34s %s" % (c, [row["d"] for row in d.get("data", [])]))
        ok.append(c)
    except Exception as e:
        out.append("FAIL %-34s %s" % (c, str(e)[:120]))
out.append("")
try:
    d = scan(["name"] + ok, SAMPLE)
    for row in d.get("data", []):
        out.append(json.dumps(dict(zip(["name"] + ok, row["d"])), ensure_ascii=False))
except Exception as e:
    out.append("SAMPLE FAIL " + str(e)[:200])
with open("data/_probe_surprise.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
print("\n".join(out))
