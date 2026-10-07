"""probe_breadth_history.py — בדיקה חד-פעמית (7.10.2026, איציק: "סוף 2021 — השוק עלה, הרוחב צר, ואז 2022").

רץ על ה-runner (לסנדבוקס אין רשת ל-Yahoo). מושך נרות יומיים מ-2005 לכל חברות ה-S&P 500 של היום
(data/sp500.json) + SPY/RSP/IWM/QQQ/^VIX, ומחשב לכל יום מסחר את מדדי הרוחב כמו במד השוק:
  pct50 / pct200 — אחוז המניות שסגרו מעל ממוצע 50 / 200 (מתוך מי שיש לו מספיק היסטוריה)
  nh / nl       — כמה מניות נגעו בשיא / שפל של 52 שבועות (גבוה/נמוך תוך-יומי מול 252 הימים הקודמים)
  eq20          — תשואת 20 יום של RSP (שוויוני) פחות SPY — "המניה הממוצעת מול המדד"
⚠️ הטיית שורדים: רק מי שבמדד היום; חברות שנפלו ויצאו חסרות — הרוחב בעבר נראה טוב מהמציאות.
פלט: scripts/tools/out/breadth_history.json (עמודות, לא שורות — קטן).
"""
import json
import os
import time
from collections import deque
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "scripts", "tools", "out", "breadth_history.json")
START = int(datetime(2004, 1, 1, tzinfo=timezone.utc).timestamp())
ETFS = ["SPY", "RSP", "IWM", "QQQ", "^VIX", "^GSPC"]


def bars(sym):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/" + sym.replace(".", "-") +
           "?period1=%d&period2=%d&interval=1d" % (START, int(time.time())))
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read().decode())["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            out = {}
            for t, h, l, c in zip(res.get("timestamp") or [], q["high"], q["low"], q["close"]):
                if c is None:
                    continue
                d = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
                out[d] = (h if h is not None else c, l if l is not None else c, c)
            return sym, out
        except Exception as e:
            err = e
            time.sleep(2 + attempt * 3)
    print("FAIL", sym, err)
    return sym, None


def main():
    members = [s for s in json.load(open(os.path.join(ROOT, "data", "sp500.json")))["symbols"] if not s.startswith("$")]
    with ThreadPoolExecutor(8) as ex:
        got = dict(ex.map(bars, members + ETFS))
    spy = got.get("SPY") or {}
    dates = sorted(d for d in spy if d >= "2005-01-01")
    print("dates", len(dates), dates[0], dates[-1], "members ok", sum(1 for s in members if got.get(s)))

    cols = {k: [] for k in ("pct50", "pct200", "nh", "nl", "n50", "n200", "n52")}
    # לכל מניה — סדרות מיושרות לתאריכי SPY (חסר = None)
    acc = [[0] * 7 for _ in dates]   # above50, n50, above200, n200, nh, nl, n52
    for s in members:
        b = got.get(s)
        if not b:
            continue
        ds = sorted(b)
        H = [b[d][0] for d in ds]
        L = [b[d][1] for d in ds]
        C = [b[d][2] for d in ds]
        pos = {d: i for i, d in enumerate(ds)}
        pre = [0.0]
        for c in C:
            pre.append(pre[-1] + c)
        # שיא/שפל מתגלגל של 252 הימים הקודמים (בלי היום) — תור מונוטוני, O(n)
        hmax, lmin = [None] * len(ds), [None] * len(ds)
        qh, ql = deque(), deque()
        for i in range(len(ds)):
            while qh and qh[0] < i - 252:
                qh.popleft()
            while ql and ql[0] < i - 252:
                ql.popleft()
            if i >= 252:
                hmax[i], lmin[i] = H[qh[0]], L[ql[0]]
            while qh and H[qh[-1]] <= H[i]:
                qh.pop()
            qh.append(i)
            while ql and L[ql[-1]] >= L[i]:
                ql.pop()
            ql.append(i)
        for k, d in enumerate(dates):
            i = pos.get(d)
            if i is None:
                continue
            a = acc[k]
            if i >= 49:
                a[1] += 1
                a[0] += C[i] > (pre[i + 1] - pre[i - 49]) / 50
            if i >= 199:
                a[3] += 1
                a[2] += C[i] > (pre[i + 1] - pre[i - 199]) / 200
            if hmax[i] is not None:
                a[6] += 1
                a[4] += H[i] >= hmax[i]
                a[5] += L[i] <= lmin[i]
    for a in acc:
        cols["pct50"].append(round(100 * a[0] / a[1], 1) if a[1] else None)
        cols["pct200"].append(round(100 * a[2] / a[3], 1) if a[3] else None)
        cols["nh"].append(a[4])
        cols["nl"].append(a[5])
        cols["n50"].append(a[1])
        cols["n200"].append(a[3])
        cols["n52"].append(a[6])

    def series(sym):
        b = got.get(sym) or {}
        return [round(b[d][2], 2) if d in b else None for d in dates]
    out = {"dates": dates, **cols, "spx": series("^GSPC"), "spy": series("SPY"), "rsp": series("RSP"),
           "iwm": series("IWM"), "qqq": series("QQQ"), "vix": series("^VIX"),
           "_meta": {"built": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                     "members": len(members), "membersOk": sum(1 for s in members if got.get(s)),
                     "failed": [s for s in members + ETFS if not got.get(s)],
                     "note": "S&P 500 של היום בלבד (הטיית שורדים). שיא/שפל = גבוה/נמוך תוך-יומי מול 252 הימים הקודמים."}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("wrote", OUT, os.path.getsize(OUT), "bytes; last:",
          dates[-1], cols["pct50"][-1], cols["pct200"][-1], cols["nh"][-1], cols["nl"][-1])


if __name__ == "__main__":
    main()
