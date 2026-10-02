#!/usr/bin/env python3
"""
probe_options.py — בדיקה חד-פעמית (2.10.2026): האם אפשר למשוך שרשרת אופציות מה-runner
ולחשב את "התזוזה שהאופציות מתמחרות" (סטראדל ATM / מחיר).
שני מקורות: Yahoo v7 (עם cookie+crumb) ו-CBOE delayed quotes (JSON ציבורי).
לא כותב שום קובץ — רק מדפיס ליומן. מורץ מ-.github/workflows/probe-options.yml.
"""
import http.cookiejar
import json
import sys
import urllib.request
from datetime import date, datetime

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
SYMS = sys.argv[1:] or ["MSFT", "NKE", "JPM"]


def opener():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA), ("Accept", "*/*")]
    return op


def get(op, url, timeout=20):
    with op.open(url, timeout=timeout) as r:
        return r.status, r.read()


def straddle(price, rows_c, rows_p):
    """rows = [(strike, bid, ask, last)]; ATM = strike הקרוב למחיר. מחזיר (strike, call, put, move%)."""
    def mid(b, a, l):
        return (b + a) / 2 if b and a and a >= b else l
    pc = {s: mid(b, a, l) for s, b, a, l in rows_c}
    pp = {s: mid(b, a, l) for s, b, a, l in rows_p}
    common = [s for s in pc if s in pp and pc[s] and pp[s]]
    if not common or not price:
        return None
    k = min(common, key=lambda s: abs(s - price))
    tot = pc[k] + pp[k]
    return k, round(pc[k], 2), round(pp[k], 2), round(tot / price * 100, 2)


def yahoo(sym):
    op = opener()
    try:
        try:
            get(op, "https://fc.yahoo.com", 10)
        except Exception as e:      # מחזיר 404 אבל שותל cookie
            print(f"  fc.yahoo.com: {e}")
        st, crumb = get(op, "https://query2.finance.yahoo.com/v1/test/getcrumb")
        crumb = crumb.decode().strip()
        print(f"  crumb: status {st}, len {len(crumb)}")
        st, body = get(op, f"https://query2.finance.yahoo.com/v7/finance/options/{sym}?crumb={crumb}")
        d = json.loads(body)["optionChain"]["result"][0]
        q = d.get("quote", {})
        price = q.get("regularMarketPrice")
        exps = d.get("expirationDates", [])
        print(f"  price {price} · {len(exps)} expiries · earnings {q.get('earningsTimestamp')}")
        # הפקיעה הראשונה שאחרי מועד הדוח (אם ידוע), אחרת השנייה ברשימה
        et = q.get("earningsTimestamp") or 0
        exp = next((e for e in exps if e > et), exps[0]) if exps else None
        if exp is None:
            return
        st, body = get(op, f"https://query2.finance.yahoo.com/v7/finance/options/{sym}?date={exp}&crumb={crumb}")
        o = json.loads(body)["optionChain"]["result"][0]["options"][0]
        rc = [(x["strike"], x.get("bid") or 0, x.get("ask") or 0, x.get("lastPrice") or 0) for x in o.get("calls", [])]
        rp = [(x["strike"], x.get("bid") or 0, x.get("ask") or 0, x.get("lastPrice") or 0) for x in o.get("puts", [])]
        s = straddle(price, rc, rp)
        print(f"  expiry {datetime.utcfromtimestamp(exp).date()} · {len(rc)} calls/{len(rp)} puts · ATM {s}")
    except Exception as e:
        print(f"  YAHOO FAIL: {type(e).__name__}: {e}")


def cboe(sym):
    op = opener()
    try:
        st, body = get(op, f"https://cdn.cboe.com/api/global/delayed_quotes/options/{sym}.json")
        d = json.loads(body)["data"]
        price = d.get("current_price") or d.get("close")
        opts = d.get("options", [])
        print(f"  status {st} · price {price} · {len(opts)} contracts · ts {json.loads(body).get('timestamp')}")
        # סמל OCC: MSFT261016C00512500 → פקיעה YYMMDD, C/P, strike*1000
        by = {}
        for x in opts:
            s = x["option"][len(sym):]
            exp, cp, k = s[:6], s[6], int(s[7:]) / 1000
            by.setdefault(exp, {"C": [], "P": []})[cp].append((k, x.get("bid") or 0, x.get("ask") or 0, x.get("last_trade_price") or 0))
        today = date.today().strftime("%y%m%d")
        exps = sorted(e for e in by if e >= today)
        for exp in exps[:4]:
            print(f"  expiry 20{exp[:2]}-{exp[2:4]}-{exp[4:]} · ATM {straddle(price, by[exp]['C'], by[exp]['P'])}")
    except Exception as e:
        print(f"  CBOE FAIL: {type(e).__name__}: {e}")


for sym in SYMS:
    print(f"== {sym} — Yahoo")
    yahoo(sym)
    print(f"== {sym} — CBOE")
    cboe(sym)
