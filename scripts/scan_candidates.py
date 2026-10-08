"""scan_candidates.py — סריקת המועמדים (EMA-bounce) בענן, בלי IBKR.

פורט של ibkr-swing-system (המפרט: nidam-candidates/scanner/SCAN_SPEC.md, 8.10.2026).
פייתון stdlib בלבד. הלוגיקה זהה למקור כולל פרטי הנקודה הצפה של pandas:
  EMA/ATR = ewm(adjust=False) בנוסחה של pandas (alpha = 1/(1+com), חלוקה ב-(old+alpha), דילוג כש-w==x).
הנרות: [date, open, high, low, close, volume], מהישן לחדש, הנר האחרון סגור.

כאן רק החישוב. היקום, הנרות והכתיבה — בשכבה שקוראת לזה.
"""

EMA_FAST, EMA_SLOW, EMA_SLOWEST = 20, 40, 50
ATR_PERIOD = 14
ATR_STOP_MULT = 1.5
RR_TARGET = 1.5
PROX = 0.02            # "מגע" = השפל עד 2% מעל הממוצע
RISING = 5             # הממוצע גבוה מערכו לפני 5 נרות
HOLD = 3               # 3 הנרות שלפני האחרון נסגרו מעל הממוצע
MAX_RISK_PCT = 8.0
VOL_AVG = 20
CCI_PERIOD, CCI_LOOKBACK = 5, 5
CCI_OVERSOLD, CCI_OVERBOUGHT = -100.0, 100.0
W_EXT, W_RVOL, W_CCI, W_HIST = 0.45, 0.20, 0.15, 0.20
BT_MAX_HOLD = 40
MAX_SHOWN = 60
MIN_BARS = max(EMA_SLOWEST, ATR_PERIOD) + 5   # 55


def _ewm(vals, alpha):
    """pandas Series.ewm(alpha=..., adjust=False).mean() — אותה אריתמטיקה בדיוק."""
    out = []
    w = None
    old_f = 1.0 - alpha
    for x in vals:
        if w is None:
            w = x
        elif w != x:
            w = (old_f * w + alpha * x) / (old_f + alpha)
        out.append(w)
    return out


def ema(vals, span):
    com = (span - 1) / 2.0
    return _ewm(vals, 1.0 / (1.0 + com))


def atr(H, L, C, period=ATR_PERIOD):
    tr = [H[0] - L[0]]
    for i in range(1, len(C)):
        pc = C[i - 1]
        tr.append(max(H[i] - L[i], abs(H[i] - pc), abs(L[i] - pc)))
    com = 1.0 / (1.0 / period) - 1.0
    return _ewm(tr, 1.0 / (1.0 + com))


def cci(H, L, C, period=CCI_PERIOD):
    tp = [(h + l + c) / 3 for h, l, c in zip(H, L, C)]
    out = [None] * len(tp)
    for i in range(period - 1, len(tp)):
        x = tp[i - period + 1:i + 1]
        m = sum(x) / period
        mad = sum(abs(v - m) for v in x) / period
        out[i] = (tp[i] - m) / (0.015 * mad) if mad else None
    return out


def analyze(bars):
    """הנר האחרון: dict עם has_signal/reason ושדות. bars = [[d,o,h,l,c,v],...]."""
    if len(bars) < MIN_BARS:
        return {"has_signal": False, "stage": "0_insufficient_history", "reason": "insufficient history"}
    O = [b[1] for b in bars]; H = [b[2] for b in bars]; L = [b[3] for b in bars]
    C = [b[4] for b in bars]; V = [b[5] or 0 for b in bars]
    e20, e40, e50 = ema(C, EMA_FAST), ema(C, EMA_SLOW), ema(C, EMA_SLOWEST)
    A = atr(H, L, C)
    close, open_, low, atr_v = C[-1], O[-1], L[-1], A[-1]
    n = len(C)

    vol_ratio = 0.0
    if n > VOL_AVG:
        prior = V[-(VOL_AVG + 1):-1]
        avg = sum(prior) / VOL_AVG
        vol_ratio = V[-1] / avg if avg > 0 else 0.0

    cc = cci(H, L, C)
    cci_now = cc[-1] if cc[-1] is not None else 0.0
    cci_prev = cc[-2] if (n > 1 and cc[-2] is not None) else cci_now
    recent = [v for v in cc[-CCI_LOOKBACK:] if v is not None]
    cci_score = 0.0
    if recent and cci_now > cci_prev and cci_now < CCI_OVERBOUGHT:
        cci_score = min(2.0, max(0.0, min(recent) / CCI_OVERSOLD))

    base = {"has_signal": False, "close": close, "open": open_, "low": low, "atr": atr_v,
            "ema20": e20[-1], "ema40": e40[-1], "ema50": e50[-1],
            "vol_ratio": vol_ratio, "cci": cci_now, "cci_score": cci_score}

    def held(es):
        return all(C[k] >= es[k] for k in range(n - 1 - HOLD, n - 1)) if n > HOLD else True

    def rising(es):
        return not (n > RISING and es[-1] <= es[-1 - RISING])

    def bounce(fs, ss, fn, sn):
        fv, sv = fs[-1], ss[-1]
        if not fv > sv:
            return False, "not in uptrend (%s <= %s)" % (fn, sn)
        if not rising(fs):
            return False, "%s not rising" % fn
        if close <= open_:
            return False, "latest candle not green"
        if not (low <= fv * (1.0 + PROX) and low <= sv * (1.0 + PROX)):
            return False, "candle did not touch %s & %s" % (fn, sn)
        if close <= fv:
            return False, "close below %s" % fn
        if close <= sv:
            return False, "close below %s" % sn
        if not held(fs):
            return False, "pullback closed below %s (not a shallow pullback)" % fn
        return True, "green candle bounced off %s & %s" % (fn, sn)

    def single(es, en):
        ev = es[-1]
        if not rising(es):
            return False, "%s not rising" % en
        if close <= open_:
            return False, "latest candle not green"
        if not low <= ev * (1.0 + PROX):
            return False, "candle did not touch %s" % en
        if close <= ev:
            return False, "close below %s" % en
        if not held(es):
            return False, "pullback closed below %s (not held)" % en
        return True, "green candle bounced off %s" % en

    if not (e20[-1] > e40[-1] > e50[-1]):
        base.update(stage="1_no_uptrend_stack", reason="not in general uptrend (need EMA20 > EMA40 > EMA50)")
        return base
    ok, reason = bounce(e20, e40, "EMA20", "EMA40")
    setup = "EMA20/40" if ok else None
    for name, fn in (("EMA40/50", lambda: bounce(e40, e50, "EMA40", "EMA50")),
                     ("EMA50", lambda: single(e50, "EMA50")),
                     ("EMA20", lambda: single(e20, "EMA20"))):
        if ok:
            break
        ok2, r2 = fn()
        if ok2:
            ok, reason, setup = True, r2, name
    if not ok:
        base.update(stage="2_no_bounce", reason=reason)
        return base
    if atr_v <= 0:
        base.update(stage="2_no_bounce", reason="invalid ATR")
        return base
    entry = close
    stop = entry - ATR_STOP_MULT * atr_v
    risk = entry - stop
    target = entry + RR_TARGET * risk
    base.update(has_signal=True, stage="", reason=reason, setup=setup, entry=entry, stop=stop,
                target=target, risk_pct=(risk / entry * 100) if entry else 0.0,
                ext_atr=round((close - e50[-1]) / atr_v, 2) if atr_v else None)
    return base


def _signal_mask(O, H, L, C, e20, e40, e50, A):
    n = len(C)
    m = [False] * n

    def held(es, i):
        return i - HOLD >= 0 and all(C[k] >= es[k] for k in range(i - HOLD, i))

    def rising(es, i):
        return i - RISING >= 0 and es[i] > es[i - RISING]

    for i in range(n):
        if not (A[i] > 0 and C[i] > O[i] and e20[i] > e40[i] > e50[i]):
            continue

        def pair(f, s):
            return (f[i] > s[i] and rising(f, i) and L[i] <= f[i] * (1 + PROX) and L[i] <= s[i] * (1 + PROX)
                    and C[i] > f[i] and C[i] > s[i] and held(f, i))

        def one(e):
            return rising(e, i) and L[i] <= e[i] * (1 + PROX) and C[i] > e[i] and held(e, i)
        m[i] = pair(e20, e40) or pair(e40, e50) or one(e50) or one(e20)
    return m


def hist_r(bars):
    """סכום ה-R של backtest על החלון (backtest_symbol במקור). None = אין עסקאות."""
    n = len(bars)
    warmup = max(EMA_SLOWEST, ATR_PERIOD, RISING) + 2
    if n < warmup + 2:
        return None
    O = [b[1] for b in bars]; H = [b[2] for b in bars]; L = [b[3] for b in bars]; C = [b[4] for b in bars]
    e20, e40, e50 = ema(C, EMA_FAST), ema(C, EMA_SLOW), ema(C, EMA_SLOWEST)
    A = atr(H, L, C)
    mask = _signal_mask(O, H, L, C, e20, e40, e50, A)
    rs = []
    i = warmup
    while i < n - 1:
        if not mask[i]:
            i += 1
            continue
        entry = O[i + 1]
        risk = ATR_STOP_MULT * A[i]
        if risk <= 0:
            i += 1
            continue
        stop, target = entry - risk, entry + RR_TARGET * risk
        ex = exj = None
        last = min(i + BT_MAX_HOLD, n - 1)
        for j in range(i + 1, last + 1):
            if O[j] <= stop:
                ex, exj = O[j], j; break
            if L[j] <= stop:
                ex, exj = stop, j; break
            if O[j] >= target:
                ex, exj = O[j], j; break
            if H[j] >= target:
                ex, exj = target, j; break
        if ex is None:
            ex, exj = C[last], last
        rs.append(round((ex - entry) / risk, 4))
        i = exj + 1
    return round(sum(rs), 1) if rs else None


def _pct_rank(vals):
    idx = [i for i, v in enumerate(vals) if v is not None]
    out = [0.5] * len(vals)
    if len(idx) <= 1:
        return out
    for pos, i in enumerate(sorted(idx, key=lambda i: vals[i])):
        out[i] = pos / (len(idx) - 1)
    return out


def rank(rows):
    """rows בסדר היקום; מוסיף rank_score וממיין (מיון יציב — שוויון נשאר בסדר היקום)."""
    if not rows:
        return rows
    ext = _pct_rank([-r["ext_atr"] if r.get("ext_atr") is not None else None for r in rows])
    vol = _pct_rank([r.get("rvol") for r in rows])
    cc = _pct_rank([r.get("cci_score") for r in rows])
    hr = _pct_rank([r.get("hist_r") for r in rows])
    tot = (W_EXT + W_RVOL + W_CCI + W_HIST) or 1.0
    for k, r in enumerate(rows):
        r["rank_score"] = round((W_EXT * ext[k] + W_RVOL * vol[k] + W_CCI * cc[k] + W_HIST * hr[k]) / tot, 4)
    rows.sort(key=lambda r: r["rank_score"] if r.get("rank_score") is not None else -1e9, reverse=True)
    return rows


def scan(universe, bars_6m, bars_2y):
    """universe = [(sym, rvol_from_file_or_None)] בסדר הסריקה.
    bars_6m(sym) / bars_2y(sym) -> רשימת נרות או None.
    מחזיר (מועמדים ממוינים, תוצאה לכל מניה {sym: (stage, reason)})."""
    rows, results = [], {}
    for sym, rv in universe:
        b = bars_6m(sym)
        if not b:
            results[sym] = ("0_no_data", "no bars")
            continue
        a = analyze(b)
        if not a["has_signal"]:
            results[sym] = (a["stage"], a["reason"])
            continue
        if (a.get("risk_pct") or 0) > MAX_RISK_PCT:
            results[sym] = ("3_risk_guard", "risk guard")
            continue
        b2 = bars_2y(sym)
        a["hist_r"] = hist_r(b2) if b2 else None
        a["rvol"] = rv if rv is not None else (a.get("vol_ratio") or 0.0)
        a["symbol"] = sym
        results[sym] = ("PASS", a["reason"])
        rows.append(a)
    return rank(rows), results


FIELDS = ("setup", "entry", "stop", "target", "risk_pct", "rvol", "hist_r", "ext_atr", "rank_score")


def payload(rows, date_iso, stamp, source="nidam-cloud-scan", max_n=MAX_SHOWN):
    cands = []
    for i, r in enumerate(rows[:max_n], 1):
        row = {"rank": i, "symbol": r["symbol"]}
        for f in FIELDS:
            row[f] = r.get(f)
        e, t = r.get("entry"), r.get("target")
        row["tp_pct"] = round((t / e - 1) * 100, 2) if e and t else None
        cands.append(row)
    return {"date": date_iso, "count": len(rows), "shown": len(cands), "candidates": cands,
            "_meta": {"updatedAt": stamp, "source": source}}
