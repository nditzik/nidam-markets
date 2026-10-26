#!/usr/bin/env python3
"""
probe_fund_sources.py — בדיקה חד-פעמית על ה-runner (26.10.2026): למה quoteSummary של Yahoo עונה 429 מה-Action,
ואילו שדות פונדמנטליים קיימים בסורק של TradingView (מקור חלופי בלי cookie/crumb). מדפיס ללוג בלבד, לא כותב קבצים.
"""
import http.cookiejar
import json
import re
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [("User-Agent", UA), ("Accept", "*/*"), ("Accept-Language", "en-US,en;q=0.9")]


def get(url, data=None, headers=None, timeout=20):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with op.open(req, timeout=timeout) as r:
            return r.status, r.geturl(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.geturl() if hasattr(e, "geturl") else url, e.read()[:400]
    except Exception as e:
        return None, url, repr(e).encode()


def line(s):
    return re.sub(r"\s+", " ", s)[:400]


print("== Yahoo: fc.yahoo.com")
st, u, b = get("https://fc.yahoo.com", timeout=10)
print("  status", st, "final", u, "cookies", [c.name + "@" + c.domain for c in cj])
st, u, b = get("https://query2.finance.yahoo.com/v1/test/getcrumb")
print("  getcrumb status", st, "body", line(b.decode("utf-8", "replace")))
crumb = b.decode().strip() if st == 200 and b and b"<" not in b else None

print("== Yahoo: guce consent")
st, u, b = get("https://guce.yahoo.com/consent")
html = b.decode("utf-8", "replace")
print("  status", st, "final", u, "len", len(html), "cookies", [c.name + "@" + c.domain for c in cj])
print("  csrfToken?", bool(re.search(r"csrfToken", html)), "sessionId?", bool(re.search(r"sessionId", html)))
print("  inputs:", [line(m) for m in re.findall(r"<input[^>]+>", html)][:8])
print("  head:", line(html[:600]))
sid = (re.search(r'sessionId=([A-Za-z0-9_-]+)', u) or re.search(r'name="sessionId"\s+value="([^"]+)"', html))
tok = re.search(r'name="csrfToken"\s+value="([^"]+)"', html)
if sid and tok:
    sid = sid.group(1)
    body = urllib.parse.urlencode([("agree", "agree"), ("agree", "agree"), ("consentUUID", "default"), ("sessionId", sid),
                                   ("csrfToken", tok.group(1)), ("originalDoneUrl", "https://finance.yahoo.com/"), ("namespace", "yahoo")]).encode()
    st, u2, b2 = get(f"https://consent.yahoo.com/v2/collectConsent?sessionId={sid}", data=body,
                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    print("  collectConsent status", st, "final", u2)
    st, u3, b3 = get(f"https://guce.yahoo.com/copyConsent?sessionId={sid}")
    print("  copyConsent status", st, "final", u3, "cookies", [c.name + "@" + c.domain for c in cj])
    st, u4, b4 = get("https://query2.finance.yahoo.com/v1/test/getcrumb")
    print("  getcrumb after consent", st, line(b4.decode("utf-8", "replace")))
    crumb = crumb or (b4.decode().strip() if st == 200 and b4 and b"<" not in b4 else None)

print("== Yahoo: getcrumb via query1 / finance.yahoo.com homepage cookie")
cj.clear()
st, u, b = get("https://finance.yahoo.com/quote/NOW/", timeout=20)
print("  homepage status", st, "final", u, "cookies", [c.name + "@" + c.domain for c in cj])
st, u, b = get("https://query1.finance.yahoo.com/v1/test/getcrumb")
print("  query1 getcrumb", st, line(b.decode("utf-8", "replace")))
crumb = crumb or (b.decode().strip() if st == 200 and b and b"<" not in b else None)

print("== Yahoo: quoteSummary NOW (crumb=%s)" % ("yes" if crumb else "no"))
mods = "price,summaryProfile,summaryDetail,defaultKeyStatistics,financialData,calendarEvents,recommendationTrend,earningsTrend"
st, u, b = get(f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/NOW?modules={mods}" + (f"&crumb={urllib.parse.quote(crumb)}" if crumb else ""))
print("  status", st, line(b.decode("utf-8", "replace"))[:300])
st, u, b = get("https://query2.finance.yahoo.com/v8/finance/chart/NOW?range=5d&interval=1d")
print("  v8 chart (no crumb) status", st)

print("== TradingView scanner: metainfo")
st, u, b = get("https://scanner.tradingview.com/america/metainfo", headers={"Content-Type": "application/json"})
print("  status", st, "len", len(b))
fields = []
if st == 200:
    try:
        meta = json.loads(b)
        fields = [f.get("n") for f in meta.get("fields", []) if isinstance(f, dict)]
        print("  fields", len(fields))
        keys = ("margin", "price_earnings", "earnings_per_share", "revenue", "debt", "cash", "dividend", "target",
                "recommendation", "growth", "free_cash", "market_cap", "earnings_release", "net_income", "beta", "short")
        hits = sorted(f for f in fields if f and any(k in f for k in keys))
        print("  relevant:", " ".join(hits))
    except Exception as e:
        print("  parse failed", e, line(b.decode("utf-8", "replace")))

print("== TradingView scanner: candidate columns one by one")
cands = ["name", "description", "sector", "industry", "market_cap_basic", "close", "price_earnings_ttm", "price_earnings_forward_fy",
         "earnings_per_share_diluted_ttm", "earnings_per_share_forecast_next_fy", "earnings_per_share_forecast_next_fq",
         "revenue_forecast_next_fq", "total_revenue_yoy_growth_ttm", "total_revenue_ttm", "earnings_per_share_diluted_yoy_growth_ttm",
         "gross_margin_ttm", "operating_margin_ttm", "net_margin_ttm", "free_cash_flow_margin_ttm", "free_cash_flow_ttm",
         "total_debt_fq", "cash_n_short_term_invest_fq", "cash_n_equivalents_fq", "dividends_yield_current", "dividends_yield",
         "price_target_average", "price_target_high", "price_target_low", "recommendation_mark", "recommendation_total",
         "recommendation_buy", "recommendation_over", "recommendation_hold", "recommendation_under", "recommendation_sell",
         "earnings_release_next_date", "earnings_release_next_time", "net_income_ttm", "beta_1_year", "number_of_employees",
         "enterprise_value_fq", "price_sales_ttm", "return_on_equity_fq", "debt_to_equity_fq", "float_shares_outstanding"]
ok, bad = [], []
for c in cands:
    body = json.dumps({"filter": [{"left": "name", "operation": "in_range", "right": ["NOW", "AAPL"]},
                                  {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]}],
                       "columns": ["name", c], "range": [0, 5]}).encode()
    st, u, b = get("https://scanner.tradingview.com/america/scan", data=body, headers={"Content-Type": "text/plain"})
    if st == 200:
        try:
            rows = json.loads(b).get("data") or []
            ok.append(f"{c}={[r['d'][1] for r in rows]}")
        except Exception as e:
            bad.append(f"{c}:parse {e}")
    else:
        bad.append(f"{c}:{st}")
print("  OK:", " | ".join(ok))
print("  BAD:", " | ".join(bad))
print("== done")
