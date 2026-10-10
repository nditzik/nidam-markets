# Stage 5 — the five remaining tab pages (השוק · היומן · מניות · חדשות · העולם), desktop 1280 light,
# built from the style book (same classes as mockups-4b/gen.py + bundle.css) on data/ of 9–10.10.2026.
import json, os, re, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import *  # CSS, header, quotes, n, pct, pick_spark, meter_panel, dots, price, ddmm, data…

R = '/home/user/nidam-markets/data/'
def J(f): return json.load(open(R + f))
wk = J('weekly.json'); fc = J('forecasts.json'); es = J('earnings_season.json'); rep = J('reports.json')['reports']
mom = J('momentum.json'); cand = J('candidates.json'); tr = J('trades.json')['reports']; ins = J('insider.json')['reports'][0]
mo = J('morning.json'); fls = J('flash.json'); news = J('news.json')['news']; wd = J('world.json')['items']; bt = J('bets.json')
ea = J('earnings.json'); ecn = J('econ.json')['events']; brf = J('briefing.json'); sec = J('sectors.json')['reports']
ro = ind['riskOff']; fl = ind['flow']; big = ind['bigTrades']; rs = ind['rotation']['sectorRs']; ev = ind['evidence']

CSS5 = CSS + '''
.b .subtabs{display:flex;gap:8px;padding:12px 24px 0}
.b .subtabs a{padding:0 12px;min-height:36px;display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:4px;color:var(--tx2);font-weight:500;font-size:13px}
.b .subtabs a[aria-current]{background:var(--lkbg);color:var(--lk);border-color:transparent;font-weight:600}
.b .tl{position:relative;height:150px;direction:ltr;border:1px solid var(--line);border-radius:3px;background:var(--pan2)}
.b .tl svg{width:100%;height:100%;display:block}
.b .tl .ln{fill:none;stroke:var(--tx2);stroke-width:1.6}.b .tl .sp2{fill:none;stroke:var(--lk);stroke-width:1.2;opacity:.8}
.b .tl .zg{fill:var(--up);opacity:.08}.b .tl .zr{fill:var(--dn);opacity:.08}.b .tl .sd{fill:var(--dn)}
.b .tlx{display:flex;justify-content:space-between;font-size:12px;color:var(--mute);direction:ltr}
.b .leg{display:flex;gap:16px;font-size:12px;color:var(--mute);flex-wrap:wrap}
.b .leg i{display:inline-block;width:14px;height:3px;vertical-align:middle;margin-inline-end:5px;border-radius:1px}
.b .tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.b .tile{border:1px solid var(--line);border-radius:4px;padding:8px 10px}
.b .tile .l{font-size:12px;color:var(--mute)}.b .tile .v{font-size:20px;font-weight:600;font-family:'IBM Plex Mono',monospace;direction:ltr;text-align:right}
.b .sent{display:grid;grid-template-columns:72px minmax(0,1fr);gap:10px;padding:8px 0;border-top:1px solid var(--line);font-size:13px;line-height:1.5;color:var(--tx2)}
.b .sent:first-child{border-top:0}
.b .sent b{font-size:13px;display:flex;align-items:center;gap:6px}
.b .dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex:none}
.b .bp{display:grid;grid-template-columns:110px minmax(0,1fr) 44px 90px 90px;gap:10px;align-items:center;font-size:13px;padding:5px 0;border-top:1px solid var(--line)}
.b .bp:first-child{border-top:0;color:var(--mute);font-size:12px}
.b .bp .bar{height:10px;background:var(--bar);border-radius:1px;direction:ltr}.b .bp .bar i{display:block;height:10px;background:var(--tx2);border-radius:1px}
.b .bp.today .bar i{background:var(--lk)}
.b .ss{position:relative;height:170px;direction:ltr;padding:0 8px}
.b .ss svg{width:100%;height:100%;display:block}
.b .ss .col{fill:var(--bar)}.b .ss .col.past{fill:var(--tx2)}.b .ss .col.peak{stroke:var(--st);stroke-width:1.5}
.b .ss .tk{font:600 12px 'IBM Plex Mono',monospace;fill:var(--tx2)}.b .ss .cnt{font:12px 'IBM Plex Mono',monospace;fill:var(--mute)}
.b .ssl{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));font-size:12px;color:var(--mute);direction:ltr;text-align:center;padding:0 8px}
.b .wk{display:grid;grid-template-columns:repeat(5,minmax(0,1fr))}
.b .wk>div{padding:10px 12px;border-inline-start:1px solid var(--line);display:flex;flex-direction:column;gap:6px;min-height:130px}
.b .wk>div:first-child{border-inline-start:0}
.b .wk .d{font-size:12px;color:var(--mute)}.b .wk .d b{color:var(--tx)}
.b .wk .tk{display:flex;flex-wrap:wrap;gap:4px}
.b .rx{display:grid;grid-template-columns:60px minmax(0,1fr) 80px 70px;gap:8px;padding:7px 0;border-top:1px solid var(--line);font-size:13px;align-items:center}
.b .rx:first-child{border-top:0}
.b .hm{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px}
.b .hm div{padding:8px;border-radius:3px;font-size:12px;display:flex;flex-direction:column;gap:2px;color:#fff}
.b .wc{border:1px solid var(--line);border-radius:4px;padding:8px 10px;display:flex;flex-direction:column;gap:4px}
.b .wc .t{display:flex;justify-content:space-between;font-size:13px;font-weight:500}
.b .wc .m{display:flex;justify-content:space-between;font-size:12px;color:var(--mute)}
.b .wgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.b .clock{display:flex;gap:6px;flex-wrap:wrap}
.b .clock span{font-size:12px;padding:3px 8px;border:1px solid var(--line);border-radius:3px;color:var(--mute)}
.b .clock span.on{border-color:var(--up);color:var(--up);font-weight:600}
.b .bet{display:grid;grid-template-columns:minmax(0,1fr) 120px 56px 70px;gap:10px;align-items:center;padding:8px 0;border-top:1px solid var(--line);font-size:13px}
.b .bet:first-child{border-top:0}
.b .bet .bar{height:6px;background:var(--bar);border-radius:1px;direction:ltr}.b .bet .bar i{display:block;height:6px;background:var(--tx2);border-radius:1px}
.b .arch{display:flex;gap:6px;flex-wrap:wrap}
.b .arch a{font-size:12px;padding:3px 8px;border:1px solid var(--line);border-radius:3px;color:var(--tx2)}
.b .arch a[aria-current]{background:var(--lkbg);color:var(--lk);border-color:transparent}
.b .hl{display:grid;grid-template-columns:52px minmax(0,1fr);gap:10px;padding:8px 14px;border-top:1px solid var(--line);font-size:14px;line-height:1.5}
.b .hl:first-child{border-top:0}
.b .flash{display:grid;grid-template-columns:auto minmax(0,1fr);gap:16px;align-items:center;padding:14px}
.b .flash .big{font-size:28px;font-weight:600;font-family:'IBM Plex Mono',monospace;direction:ltr}
'''

def page5(title, body, w, h):
    return page(title, body, w, h).replace(f'<style>{CSS}</style>', f'<style>{CSS5}</style>')

def shell(tab, subs, cur, content, h, session='<span class="pill">טרום מסחר</span><span>פתיחה בעוד 3:32</span><span class="mute">IL 12:58 · NY 05:58</span>'):
    hdr = header(session).replace('<a href="#" aria-current="page">בית</a>', '<a href="#">בית</a>').replace(f'<a href="#">{tab}</a>', f'<a href="#" aria-current="page">{tab}</a>')
    st = ''.join(f'<a href="#"{" aria-current=\"page\"" if s == cur else ""}>{s}</a>' for s in subs) if subs else ''
    return f'''<div class="b" dir="rtl" style="width:1280px;min-height:{h}px">{hdr}{quotes()}
{f'<nav class="subtabs" aria-label="לשוניות">{st}</nav>' if st else ''}
<main class="grid">{content}</main></div>'''

# ===================== השוק =====================
def meter_timeline():
    days = hist['days'][-45:]
    w, h = 100, 40
    X = lambda i: i * w / (len(days) - 1)
    Y = lambda v: h * (1 - v / 100)
    pts = ' '.join(f'{X(i):.1f},{Y(d["combined"]):.1f}' for i, d in enumerate(days))
    spx = [d['spx'] for d in days]; lo, hi = min(spx), max(spx)
    sp = ' '.join(f'{X(i):.1f},{(h - 2) - (h - 6) * (v - lo) / (hi - lo):.1f}' for i, v in enumerate(spx))
    sells = {s['date'] for s in ro['sellingDays']}
    marks = ''.join(f'<polygon class="sd" points="{X(i) - 1.2:.1f},{h - 1} {X(i) + 1.2:.1f},{h - 1} {X(i):.1f},{h - 3.5}"></polygon>' for i, d in enumerate(days) if d['date'] in sells)
    return f'''<div class="tl"><svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" role="img" aria-label="ציון המד ב-45 ימי המסחר האחרונים, מ-{days[0]['combined']} ל-{days[-1]['combined']}">
<rect class="zg" x="0" y="0" width="{w}" height="{Y(66):.1f}"></rect><rect class="zr" x="0" y="{Y(45):.1f}" width="{w}" height="{h - Y(45):.1f}"></rect>
<polyline class="sp2" points="{sp}" vector-effect="non-scaling-stroke"></polyline>
<polyline class="ln" points="{pts}" vector-effect="non-scaling-stroke"></polyline>{marks}</svg></div>
<div class="tlx"><span>{ddmm(days[0]['date'])}</span><span>{ddmm(days[len(days)//2]['date'])}</span><span>{ddmm(days[-1]['date'])}</span></div>
<div class="leg"><span><i style="background:var(--tx2)"></i>ציון המד</span><span><i style="background:var(--lk)"></i>S&amp;P 500 (מנורמל)</span><span><i style="background:var(--dn);height:6px;width:6px"></i>יום מכירה רחבה</span><span>רצועות: חיובי מעל 66 · הגנתי מתחת ל-45</span></div>'''

BP_ROWS = [('היום', ev['pctMa200'], '?', '?', True), ('ינואר 2022', 76, -25.4, -19.7, False), ('דצמבר 2024', 60, -17.5, 14.3, False), ('יולי 2015', 59, -13.7, 2.5, False), ('יוני 2023', 52, -3.9, 23.6, False), ('יוני 2025', 48, 0, 20.8, False)]
def bp_rows():
    out = '<div class="bp"><span>שיא</span><span>% מניות מעל ממוצע 200</span><span></span><span>התחתית בשנה שאחרי</span><span>שנה אחרי</span></div>'
    for lab, p, low, yr, today in BP_ROWS:
        f = lambda v: '<span class="n mute">?</span>' if v == '?' else (pct(v, 1) if v else '<span class="mute">לא ירד</span>')
        out += f'<div class="bp{" today" if today else ""}"><span{" style=color:var(--lk);font-weight:600" if today else ""}>{lab}</span><div class="bar"><i style="width:{p}%"></i></div>{n(f"{p:.0f}%")}{f(low)}{f(yr)}</div>'
    return out

def market_page():
    cur = fc['current']; rec = fc['record']; s = wk['summary']; nar = wk['narrative']
    lines = fl['research']['lines']
    tone = {'up': 'var(--up)', 'down': 'var(--dn)', 'warn': 'var(--st)'}
    sent = ''.join(f'<div class="sent"><b><i class="dot" style="background:{tone.get(l["tone"], "var(--mute)")}"></i>{l["label"]}</b><span>{l["text"]}</span></div>' for l in lines)
    bigs = ''.join(f'<div class="sent"><b><span class="n" style="font-weight:700;color:var(--tx)">{i["ticker"]}</span></b><span>{i["text"]}</span></div>' for i in big['items'][:5])
    content = f'''
{meter_panel(4)}
<section class="pan" style="grid-column:span 8"><div class="ph"><h2>ציר הזמן של The Edge Meter · 45 ימי מסחר</h2><span class="mute" style="font-weight:400">30 · 60 · 90 יום</span></div>
<div class="pb">{meter_timeline()}
<div class="tiles"><div class="tile"><div class="l">ימי מכירה ב-25 הימים</div><div class="v">4</div></div><div class="tile"><div class="l">S&amp;P מעל ממוצע 200</div><div class="v">117 <span style="font-size:12px;font-weight:400">ימים</span></div></div><div class="tile"><div class="l">מניות מעל ממוצע 200</div><div class="v">{ev['pctMa200']:.0f}%</div></div><div class="tile"><div class="l">שיאים / שפלים</div><div class="v">{ev['nhCount']}/{ev['nlCount']}</div></div></div>
</div></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>סיכום השבוע · {wk['label']}</h2><a href="#" class="go">הסיכום המלא</a></div>
<div class="pb"><div class="tiles"><div class="tile"><div class="l">S&amp;P 500</div><div class="v {ud(s['spxPct'])}">{sgn(s['spxPct'])}%</div></div><div class="tile"><div class="l">המד</div><div class="v">{s['combStart']}→{s['combEnd']}</div></div><div class="tile"><div class="l">VIX</div><div class="v">{s['vixStart']:.1f}→{s['vixEnd']:.1f}</div></div><div class="tile"><div class="l">ימי מכירה</div><div class="v">{s['sellDays']}</div></div></div>
<p style="font-size:14px;line-height:1.6;color:var(--tx2)">{nar['lead']}</p>
<div class="kv"><span>💸 לאן זרם הכסף</span><span>{' · '.join(f'{o["name"]} {n(o["from"])}%→{n(o["to"])}%' for o in wk['sectors']['out'][:2])} · רוחב השוק {n(wk['sectors']['marketBreadth'])}%</span></div></div></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>הצפי לשבוע · {wk['label'] if False else '5–9.10'}</h2><span class="mute" style="font-weight:400">מאזן: {n(rec['hits'])} מתוך {n(rec['scored'])} פגיעות · {n(rec['inRange'])} בטווח</span><a href="#" class="go">כל הצפיים</a></div>
<div class="pb"><div style="display:flex;align-items:baseline;gap:12px"><span class="n" style="font-size:32px;font-weight:600">{cur['prob']}%</span><span style="font-size:16px;font-weight:600">{cur['label']}</span></div>
<p style="font-size:14px;color:var(--tx2)">{cur['claim']} · טווח {pct(cur['rangeLow'], 1)} עד {pct(cur['rangeHigh'], 1)}</p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:13px;line-height:1.5"><div><b class="dn">נגד</b><ul style="margin:4px 0 0;padding-inline-start:16px">{''.join(f'<li>{x}</li>' for x in cur['bear'][:2])}</ul></div><div><b class="up">בעד</b><ul style="margin:4px 0 0;padding-inline-start:16px">{''.join(f'<li>{x}</li>' for x in cur['bull'][:2])}</ul></div></div>
<div class="kv"><span>המעקב השבוע</span><span>סגירה ○ ○ ○ ○ ○ · יום מכירה ✓ · רוחב ✓</span></div></div></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>ההימור נטו · אופציות · {big['label']}</h2><span class="pill state">ציון {n(SCORES['flow'])} · אזהרת SPX</span><a href="#" class="go">המחקר</a></div>
<div class="pb" style="gap:0">{sent}<div class="kv" style="margin-top:8px"><span>במד נכנס ממוצע יומיים</span><span>{n(fl['meterScore'])} (היום {n(97)}, אתמול {n(87)})</span></div></div></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>הכסף הגדול היום במניות</h2><span class="mute" style="font-weight:400">{n(big['prints'])} העסקאות הגדולות · {n(big['symbols'])} מניות</span></div>
<div class="pb" style="gap:0">{bigs}</div></section>

<section class="pan" style="grid-column:span 7"><div class="ph"><h2>כמה מניות משתתפות בשיא?</h2><span class="mute" style="font-weight:400">המדד {n(f"{abs(vl['spxOffHigh']):.1f}%")} מתחת לשיא · הרוחב צר מבכל שיא קודם</span></div>
<div class="pb" style="gap:0">{bp_rows()}<p class="mute" style="font-size:12px;margin-top:8px">מה שהכריע בעבר: אם תוך כחודש האחוז קפץ מעל 65%. הטיית שורדים — חברות המדד של היום.</p></div></section>

<section class="pan" style="grid-column:span 5"><div class="ph"><h2>מנוע המסקנות</h2><span class="mute" style="font-weight:400">{ind['conclusion']['headline']}</span></div>
<div class="pb" style="gap:0">{''.join(f'<div class="sent"><b><i class="dot" style="background:{dict(pos="var(--up)", neg="var(--dn)", warn="var(--st)").get(a["tone"], "var(--mute)")}"></i>{a["domain"]}</b><span>{a["text"]}</span></div>' for a in ind['conclusion']['analysis'])}</div></section>
'''
    return page5('השוק · מדדים', shell('השוק', ['מדדים', 'סקטורים'], 'מדדים', content, 1720), 1280, 1720)

# ===================== היומן =====================
def season_chart():
    weeks = es['weeks']; mx = max(w['n'] for w in weeks); W, H = 800, 150
    cols = ''
    for i, w in enumerate(weeks):
        x = i * 100 + 12; hh = max(6, w['n'] / mx * 110); y = 128 - hh
        past = w['mon'] < '2026-10-12'; peak = w['n'] == mx
        cols += f'<rect class="col{" past" if past else ""}{" peak" if peak else ""}" x="{x}" y="{y:.0f}" width="76" height="{hh:.0f}" rx="2"></rect>'
        cols += f'<text class="cnt" x="{x + 38}" y="{y - 4:.0f}" text-anchor="middle">{w["n"]}</text>'
        for j, t in enumerate((w.get('tickers') or [])[:4]):
            ty = y + 14 + j * 13
            if ty < 124: cols += f'<text class="tk" x="{x + 38}" y="{ty:.0f}" text-anchor="middle" fill="{"var(--pan)" if past else "var(--tx2)"}">{t}</text>'
    cols += '<line x1="112" y1="0" x2="112" y2="134" stroke="var(--lk)" stroke-width="1.5" stroke-dasharray="3 3"></line>'
    return f'''<div class="ss"><svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" aria-label="מספר המדווחות בכל שבוע של העונה, שיא בשבוע 26.10">{cols}</svg>
<span style="position:absolute;left:calc(14% + 8px);top:0;font-size:12px;color:var(--lk);direction:rtl">אנחנו כאן</span></div>
<div class="ssl">{''.join(f'<span>{w["label"]}</span>' for w in weeks)}</div>'''

def calendar_page():
    b = es['board']; wkd = [('שני', '13.10'), ('שלישי', '14.10'), ('רביעי', '15.10'), ('חמישי', '16.10'), ('שישי', '17.10')]
    syms = {d: [k for k, v in ea['window'].items() if v == f'2026-10-{d[-2:]}' and '/' not in k] for d in ['2026-10-13', '2026-10-14', '2026-10-15', '2026-10-16', '2026-10-17']}
    macro = {'14.10': [e for e in ecn if e['ilDate'] == '14.10'], '15.10': [e for e in ecn if e['ilDate'] == '15.10']}
    cells = ''
    for (dn, dd), key in zip(wkd, syms):
        tk = ''.join(f'<span class="tag">{s}</span>' for s in syms[key][:8])
        mc = ''.join(f'<div style="font-size:13px"><span class="tag macro">מאקרו {n(e["ilTime"])}</span> {e["he"]} <span class="mute">צפי {n(e["forecast"])}</span></div>' for e in macro.get(dd, [])[:2])
        cells += f'<div><span class="d">{dn} <b>{n(dd)}</b> · {n(len(syms[key]))} מדווחות</span>{mc}<div class="tk">{tk}</div></div>'
    react = ''.join(f'<div class="rx"><span class="n" style="font-weight:700">{i["ticker"]}</span><span class="mute">{i["name"][:28]} · {"לפני הפתיחה" if i["when"] == "before" else "אחרי הסגירה"}</span><span class="mute">{d["label"]}</span>{pct(i["chg"])}</div>' for d in ea['reactions']['days'] for i in d['items'])
    econ_rows = ''.join(f'<tr><td>{n(e["ilDate"])} · {n(e["ilTime"])}</td><td>{e["he"]}</td><td>{n(e["forecast"] or "—")}</td><td>{n(e["previous"] or "—")}</td><td>{n(e["actual"]) if e["actual"] else "<span class=mute>—</span>"}</td></tr>' for e in ecn[:12])
    reps = ''.join(f'<a href="#" class="tag" style="min-height:28px;display:inline-flex;align-items:center;gap:6px"><b class="n">{r["ticker"]}</b> {ddmm(r["date"])}</a>' for r in rep[:10])
    content = f'''
<section class="pan" style="grid-column:span 12"><div class="ph"><h2>עונת הדוחות · {es['season']} {es['year']}</h2><span class="mute" style="font-weight:400">שבוע 1 מתוך 8 · דיווחו {n(es['reported'])} מתוך {n(es['total'])} · {n(f"{b['epsBeatPct']}%")} עקפו את צפי הרווח, {n(f"{b['revBeatPct']}%")} בהכנסות</span><a href="#" class="go">לוח התוצאות</a></div>
<div class="pb">{season_chart()}</div></section>

<section class="pan" style="grid-column:span 12"><div class="ph"><h2>השבוע הקרוב · {n('13–17.10')}</h2><span class="mute" style="font-weight:400">דוחות ומאקרו ביחד · שעון ישראל</span></div>
<div class="wk">{cells}</div></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>לקראת הדוח</h2><span class="tag earn">JPM · שני {n('13.10')} · לפני הפתיחה</span><a href="#" class="go">כל ההכנות</a></div>
<div class="pb"><p style="font-size:15px;line-height:1.5">{pn['thesis']}</p><p style="font-size:13px;color:var(--tx2);line-height:1.5">{pn['dek']}</p>
<div class="tiles" style="grid-template-columns:repeat(3,minmax(0,1fr))"><div class="tile"><div class="l">צפי רווח למניה</div><div class="v">$5.93</div></div><div class="tile"><div class="l">האופציות מתמחרות</div><div class="v">±3.5%</div></div><div class="tile"><div class="l">מחיר יעד ממוצע</div><div class="v">$373</div></div></div></div></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>איך הגיבו המדווחות</h2><span class="mute" style="font-weight:400">סגירה מול סגירה, נרות יומיים</span></div>
<div class="pb" style="gap:0">{react}<div class="kv" style="margin-top:8px"><span>העונה עד כה</span><span>עקיפה → {pct(b['reactBeat'])} בממוצע ({n(b['reactBeatN'])} דוחות) · החטאה → אין עדיין</span></div></div></section>

<section class="pan" style="grid-column:span 7"><div class="ph"><h2>מאקרו · צפי מול בפועל</h2><a href="#" class="go">היומן המלא</a></div>
<table><thead><tr><th scope="col">מועד</th><th scope="col">נתון</th><th scope="col">צפי</th><th scope="col">קודם</th><th scope="col">בפועל</th></tr></thead><tbody>{econ_rows}</tbody></table></section>

<section class="pan" style="grid-column:span 5"><div class="ph"><h2>ניתוח דוחות</h2><span class="mute" style="font-weight:400">{n(len(rep))} דוחות באתר</span><a href="#" class="go">כל הניתוחים</a></div>
<div class="pb"><div style="display:flex;gap:6px;flex-wrap:wrap">{reps}</div>
<div class="prep"><div class="h"><b class="ltr n" style="font-size:15px;color:var(--tx)">PEP</b><span>אחרי הדוח · {n('8.10')} · ההכנה מול מה שקרה</span></div><p>3 בדיקות עמדו, אחת חלקית, אחת נכשלה · {pct(3.73)} מול {n('±3.4%')} מתומחר · התחזית הורדה.</p><a href="#" style="font-size:13px;display:inline-flex;align-items:center;min-height:28px">הניתוח החדש</a></div></div></section>
'''
    return page5('היומן · לוח הדיווחים', shell('היומן', ['לוח הדיווחים', 'לקראת הדוח', 'ניתוח דוחות', 'מאקרו'], 'לוח הדיווחים', content, 1700), 1280, 1700)

# ===================== מניות =====================
def stocks_page():
    g = GATE; led = J('picks_ledger.json')['editions']
    rows = ''.join(row(i + 1, p) for i, p in enumerate(PICKS))
    gw = {'neutral': 'זהיר', 'defense': 'הגנתי', 'positive': 'חיובי'}
    ledrows = ''
    for e in led[::-1][:7]:
        a5 = e.get('avg', {}).get('5'); c = e.get('cur')
        ledrows += f'<tr><td>{n(ddmm(e["date"]))}</td><td>{n(len(e["symbols"]))}</td><td>{gw.get(e.get("gate"), "")}</td><td>{pct(a5["excess"]) if a5 else "<span class=mute>—</span>"}</td><td>{(pct(c["excess"]) + f" <span class=mute>יום {c['day']}</span>") if c else "<span class=mute>נבנתה היום</span>"}</td><td>{n(c["win"]) + "%" if c else "—"}</td></tr>'
    cr = ''.join(f'<tr><td>{n(c["rank"])}</td><td><a href="#" class="tsym">{c["symbol"]}</a></td><td><span class="tag">{c["setup"]}</span></td><td>{n(f"{float(c['entry']):.2f}")}</td><td><span class="dn">{n(f"{float(c['stop']):.2f}")}</span></td><td><span class="up">{n(f"{float(c['target']):.2f}")}</span></td><td>{n(f"{float(c['risk_pct']):.1f}%")}</td><td>{n(c["rvol"])}</td></tr>' for c in cand['candidates'][:6])
    mtop = sorted(mom['stocks'], key=lambda s: -int(s['readiness']))[:6]
    SIG = {'strength': 'עוצמה', '6m_high': 'שיא 6ח', 'ttm_squeeze': 'סקוויז', 'macd_buy': 'MACD', 'hot_prospects': 'הוט'}
    mr = ''.join(f'<tr><td><a href="#" class="tsym">{s["symbol"]}</a><div class="mute" style="font-size:12px">{s["industry"][:26]}</div></td><td>{n(s["readiness"])}</td><td>{"".join(f"<span class=tag style=margin-inline-end:4px>{SIG.get(x, x)}</span>" for x in (eval(s["signals"]) if isinstance(s["signals"], str) else s["signals"]))}</td><td>{pct(float(s["change_pct"]))}</td></tr>' for s in mtop)
    from collections import Counter
    cnt = Counter(int(s['signal_count']) for s in mom['stocks'])
    content = f'''
<section class="pan" style="grid-column:span 12"><div class="ph"><h2>הנבחרות · אישור מחיר לקנייה · מהדורת {ddmm(pk['date'])}</h2><span class="pill state">השוק {g['label']} · עד {n(g['maxPos'])} פוזיציות · {g['sizing']} גודל</span><span class="mute" style="font-weight:400">{g['verdict']}</span></div>
<table><caption style="position:absolute;clip:rect(0 0 0 0)">הנבחרות</caption><thead><tr><th scope="col">מניה</th><th scope="col">מחיר</th><th scope="col">יום</th><th scope="col">60 יום</th><th scope="col">סטופ / תמיכה</th><th scope="col">מיקום בטווח</th><th scope="col">יעד / התנגדות</th><th scope="col">מקור</th><th scope="col">רקורד</th></tr></thead><tbody>{rows}</tbody></table>
<div class="led"><div><span class="mute">נפסלו</span><span>OXY — שלושת האישורים הקודמים נכשלו</span></div><div><span class="mute">אופק</span><span>10–20 יום · כניסה בשלישים · סטופ לא צמוד</span></div><div><span class="mute">המאגר</span><span>מועמדים ∪ מומנטום, {n(99)} + {n(27)} מניות</span></div><div><span class="mute">מקור</span><span>סריקה בענן על {n(1164)} מניות</span></div></div></section>

<section class="pan" style="grid-column:span 7"><div class="ph"><h2>יומן ההכנות</h2><span class="mute" style="font-weight:400">כל המספרים מצטברים מהכניסה, מול S&amp;P</span><a href="#" class="go">כל המהדורות</a></div>
<table><thead><tr><th scope="col">מהדורה</th><th scope="col">מניות</th><th scope="col">השער</th><th scope="col">5 ימים</th><th scope="col">עכשיו</th><th scope="col">עלו</th></tr></thead><tbody>{ledrows}</tbody></table></section>

<section class="pan" style="grid-column:span 5"><div class="ph"><h2>הרקורד</h2><span class="mute" style="font-weight:400">מבחן לאחור · {n(REC['n'])} אישורים ב-{n(REC['symbols'])} מניות</span></div>
<div class="pb"><div class="tiles" style="grid-template-columns:repeat(2,minmax(0,1fr))">
<div class="tile"><div class="l">עלו תוך 10 ימים</div><div class="v">{REC['win10']}%</div></div><div class="tile"><div class="l">ממוצע 10 ימים</div><div class="v up">+{REC['avg10']}%</div></div>
<div class="tile"><div class="l">ממוצע 20 יום</div><div class="v up">+{REC['avg20']}%</div></div><div class="tile"><div class="l">ירידה ממוצעת בדרך</div><div class="v dn">{REC['mae']}%</div></div></div>
<p class="mute" style="font-size:12px">הדגימה מוטה לטובה: מניות שנבחרו כשהן במגמת עלייה. השבוע הראשון תנודתי — מחצית נוגעות ב-1.5 ATR.</p></div></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>מועמדים למסחר · סגירת {ddmm(cand['_meta']['basedOn'])}</h2><span class="mute" style="font-weight:400">{n(cand['count'])} מועמדים · נסרקו {n(cand['_meta']['universe'])} מניות בענן</span><a href="#" class="go">כל {n(cand['shown'])}</a></div>
<table><thead><tr><th scope="col">#</th><th scope="col">מניה</th><th scope="col">סטאפ</th><th scope="col">כניסה</th><th scope="col">סטופ</th><th scope="col">יעד</th><th scope="col">סיכון</th><th scope="col">RVOL</th></tr></thead><tbody>{cr}</tbody></table></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>מומנטום · סורקי {ddmm('2026-10-08')}</h2><span class="mute" style="font-weight:400">{n(cnt[3])} עם 3 סיגנלים · {n(cnt[2])} עם 2 · {n(12)} מועמדות לטרייד</span><a href="#" class="go">כל {n(mom['count'])}</a></div>
<table><thead><tr><th scope="col">מניה</th><th scope="col">מוכנות</th><th scope="col">סיגנלים</th><th scope="col">יום</th></tr></thead><tbody>{mr}</tbody></table></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>הצעות לטרייד · ארבעת העמודים</h2><span class="mute" style="font-weight:400">{ddmm(tr[0]['date'])}</span><a href="#" class="go">הדוח</a></div>
<div class="pb" style="gap:6px">{''.join(f'<div class="sent"><b><span class="n" style="font-weight:700;color:var(--tx)">{p["ticker"]}</span></b><span><b>{p["cat"]}</b> · {p["action"]} — {p["note"][:70]}</span></div>' for p in (eval(tr[0]['picks']) if isinstance(tr[0]['picks'], str) else tr[0]['picks'])[:4])}</div></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>Insider · {ins['title']}</h2><a href="#" class="go">הדוח</a></div>
<div class="pb"><p style="font-size:13px;color:var(--tx2)">{ins['range']}</p><div style="display:flex;gap:6px;flex-wrap:wrap">{''.join(f'<a href="#" class="tag" style="min-height:28px;display:inline-flex;align-items:center"><b class="n">{t}</b></a>' for t in (eval(ins['tickers']) if isinstance(ins['tickers'], str) else ins['tickers']))}</div></div></section>
'''
    return page5('מניות · הנבחרות', shell('מניות', ['הנבחרות', 'מועמדים', 'מומנטום', 'הצעות לטרייד', 'Insider'], 'הנבחרות', content, 2240), 1280, 2240)

# ===================== חדשות =====================
def news_page():
    bm = brf['morning']; ba = brf['afternoon']
    heads = ''.join(f'<div class="hl"><span class="n mute">{i + 1}</span><span>{h}</span></div>' for i, h in enumerate(BRIEF))
    aft = eval(ba['headlines']) if isinstance(ba['headlines'], str) else ba['headlines']
    sched = eval(ba['schedule']) if isinstance(ba['schedule'], str) else ba['schedule']
    pulse = ''.join(f'<div class="fl"><span class="n mute">{t}</span><span class="ltr mute" style="text-align:right">{s_}</span><span class="en">{x.replace(" $MACRO", "")}</span></div>' for s_, t, x in [(i['source'], i['time'], i['text'].split(' @​')[0].replace('🚨', '').strip()) for i in pu['items'][:8]])
    nw = ''.join(f'<div class="hl" style="grid-template-columns:52px minmax(0,1fr)"><span class="n mute">{x["time"]}</span><span>{x["title"]}<span class="mute" style="font-size:12px"> · {x["source"]}</span></span></div>' for x in news[:6])
    ev_ = fls['evidence']
    content = f'''
<section class="pan" style="grid-column:span 8"><div class="ph"><h2>התדרוך · בוקר · {n(bm['time'][-5:] if ' ' in bm['time'] else bm['time'])}</h2><span class="mute" style="font-weight:400">{bm['dateLabel']}</span><a href="#" class="go">התדרוך המלא</a></div>
<div>{heads}</div>
<div class="ph" style="border-top:1px solid var(--line);border-bottom:0"><h2>אחר הצהריים · {n(ba['time'])}</h2><span class="pill state">{eval(ba['sentiment'])['text'] if isinstance(ba['sentiment'], str) else ba['sentiment']['text']}</span></div>
<div>{''.join(f'<div class="hl"><span class="n mute">{i + 1}</span><span>{h}</span></div>' for i, h in enumerate(aft[:3]))}</div>
<div class="led" style="grid-template-columns:repeat(3,minmax(0,1fr))">{''.join(f'<div><span class="n mute">{s["time"]}</span><span style="font-size:13px">{s["text"][:46]}</span></div>' for s in sched[:3])}</div></section>

<section class="pan" style="grid-column:span 4"><div class="ph"><h2>בזק מהרשת</h2><span class="mute" style="font-weight:400">4 ערוצים + X Scan</span><a href="#" class="go">כל הבזקים</a></div>
<div>{pulse}</div></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>Barchart</h2><a href="#" class="go">הארכיון</a></div>
<div class="pb"><a href="#" class="prep" style="color:inherit"><div class="h"><span class="tag">סקירת בוקר · {n(mo['time'][-5:])}</span></div><p>{mo['subject'].split('|')[0].strip()} · {mo['subject'].split('|')[1].strip()}</p></a>
<a href="#" class="prep" style="color:inherit"><div class="h"><span class="tag earn">טרום מסחר · {n(mo['premkt']['time'])}</span></div><p>{mo['premkt']['subject'].split('|')[1].split('(')[0].strip()}</p></a>
<div class="arch"><a href="#" aria-current="page">היום</a>{''.join(f'<a href="#">{d}</a>' for d in ['8.10', '7.10', '6.10', '5.10', '2.10', '1.10'])}</div></div></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>חדשות</h2><span class="mute" style="font-weight:400">RSS, מתורגם</span></div>
<div>{nw}</div></section>

<section class="pan" style="grid-column:span 12"><div class="ph"><h2>מבזק ⚡ · המבזק האחרון</h2><span class="mute" style="font-weight:400">ספייק של {n('0.5%+')} ב-{n(30)} דקות · מציג מה התפרסם באותן דקות, לא סיבתיות</span></div>
<div class="flash"><div><div class="big dn">{fls['pct']}%</div><div class="mute" style="font-size:12px">{fls['label']} · {n(fls['date'])} {n(fls['time'])} · {fls['session']}</div></div>
<div style="font-size:13px;color:var(--tx2);line-height:1.5">{''.join(f'<div class="en">{p.get("time", "")} {p.get("source", "")}: {str(p.get("text", ""))[:80]}</div>' for p in ev_['pulse'][:2])}{''.join(f'<div class="en">{str(x.get("title", ""))[:70]}</div>' for x in ev_['news'][:2])}</div></div></section>
'''
    return page5('חדשות · תדרוך', shell('חדשות', ['תדרוך', 'Barchart', 'בזק'], 'תדרוך', content, 1500), 1280, 1500)

# ===================== העולם =====================
def world_page():
    W_ = {x['key']: x for x in wd}
    def card(k):
        x = W_[k]; st = 'נסחר' if x.get('status') in ('open', 'live') else 'נסגר'
        return f'<div class="wc"><div class="t"><span>{x["label"]}</span>{pct(x["chg"])}</div><div class="m"><span class="n">{x["price"]:,.0f}</span><span>שבוע {pct(x["chg5d"], 1) if x.get("chg5d") is not None else "—"}</span><span>השנה {pct(x["chgYtd"], 1) if x.get("chgYtd") is not None else "—"}</span></div></div>'
    il = ''.join(card(k) for k in ['ta125', 'ta35', 'ta90', 'tabank'])
    secs = sorted([x for x in wd if x.get('region') == 'ישראל — סקטורים'], key=lambda x: -x['chg'])
    def hcol(c):
        a = min(abs(c) / 2, 1); return f'rgba({"13,122,82" if c >= 0 else "190,46,28"},{0.25 + 0.75 * a:.2f})'
    def short(l): return l.replace('ת"א ', '')
    heat = ''.join(f'<div style="background:{hcol(x["chg"])}"><span>{short(x["label"])}</span><span class="n" style="font-weight:600">{sgn(x["chg"])}%</span></div>' for x in secs[:12])
    asia = ''.join(card(k) for k in ['n225', 'ks11', 'twii', 'hsi', 'nsei'])
    eu = ''.join(card(k) for k in ['ftse', 'dax'])
    us = ''.join(card(k) for k in ['spx', 'ixic', 'tsx'])
    cr = ''.join(card(k) for k in ['btc', 'eth', 'xrp'])
    bets = ''.join(f'<div class="bet"><span>{r["label"]}<div class="mute" style="font-size:12px">{r["sub"]}</div></span><div class="bar" role="img" aria-label="{r["pct"]}%"><i style="width:{r["pct"]}%"></i></div>{n(str(r["pct"]) + "%")}<span class="mute" style="font-size:12px">{("יומי " + pct(r["chg"], 0).replace("%", " נק׳")) if r.get("chg") else "ללא שינוי"}</span></div>' for r in bt['rows'])
    content = f'''
<section class="pan" style="grid-column:span 12"><div class="ph"><h2>העולם · שישי {n('9.10')} · {n('12:58')} שעון ישראל</h2><span class="mute" style="font-weight:400">אסיה {pct(-0.4, 1)} ממוצע · אירופה {pct(1.1, 1)} · ארה"ב מהחוזים {pct(0.44)}</span></div>
<div class="pb"><div class="clock"><span>טוקיו 03:00–09:00 · סגור</span><span>סיאול 03:00–09:30 · סגור</span><span>הונג קונג 04:30–11:00 · סגור</span><span class="on">תל אביב 09:59–17:25 · פתוח</span><span class="on">פרנקפורט 10:00–18:30 · פתוח</span><span class="on">לונדון 10:00–18:30 · פתוח</span><span>ניו יורק 16:30–23:00 · בעוד 3:32</span></div></div></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>ישראל</h2><span class="mute" style="font-weight:400">בורסת תל אביב · נסחר</span></div>
<div class="pb"><div class="wgrid" style="grid-template-columns:repeat(2,minmax(0,1fr))">{il}</div>
<div class="mute" style="font-size:12px">מפת חום · {n(len(secs))} סקטורים</div><div class="hm">{heat}</div></div></section>

<section class="pan" style="grid-column:span 6"><div class="ph"><h2>העולם</h2><span class="mute" style="font-weight:400">לפי אזור · מצב מסחר מחותמת הציטוט</span></div>
<div class="pb"><div class="mute" style="font-size:12px">אסיה · נסגר</div><div class="wgrid">{asia}</div><div class="mute" style="font-size:12px">אירופה · נסחר</div><div class="wgrid">{eu}</div><div class="mute" style="font-size:12px">אמריקה · סגירת אתמול</div><div class="wgrid">{us}</div></div></section>

<section class="pan" style="grid-column:span 4"><div class="ph"><h2>קריפטו</h2><span class="mute" style="font-weight:400">24/7</span></div>
<div class="pb"><div class="wgrid" style="grid-template-columns:1fr">{cr}</div></div></section>

<section class="pan" style="grid-column:span 8"><div class="ph"><h2>מה השווקים מהמרים</h2><span class="mute" style="font-weight:400">Polymarket + Kalshi · הסתברות + שינוי יומי</span></div>
<div class="pb" style="gap:0">{bets}</div></section>
'''
    return page5('העולם', shell('העולם', [], '', content, 1400), 1280, 1400)

BOARDS5 = [
    ('Market.dc.html', 'השוק · מדדים (לשונית ברירת המחדל)', market_page, 1720),
    ('Calendar.dc.html', 'היומן · לוח הדיווחים', calendar_page, 1700),
    ('Stocks.dc.html', 'מניות · הנבחרות', stocks_page, 2240),
    ('News.dc.html', 'חדשות · תדרוך', news_page, 1500),
    ('World.dc.html', 'העולם', world_page, 1400),
]

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'out5'
    os.makedirs(out + '/project', exist_ok=True); os.makedirs(out + '/prev', exist_ok=True)
    idx = {"v": 3, "createdOnFiles": {"v": 1, "at": datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},
           "title": "The Daily Edge · שלב 5 · חמשת הטאבים", "launch": {"view": "canvas"}, "pages": [], "boards": {}, "order": [], "designSystems": [],
           "notes": {"r1": {"x": 0, "y": -240, "text": "חמשת הטאבים · מחשב 1280 · בהיר · לשונית ברירת המחדל של כל טאב", "kind": "title1", "maxW": 6700}}}
    x = 0
    for i, (name, title, fn, h) in enumerate(BOARDS5):
        html = fn()
        fname = 'Main.dc.html' if i == 0 else name
        idx['boards'][fname] = {"x": x, "y": 0, "w": 1280, "h": h, "title": title}; idx['order'].append(fname); x += 1360
        open(f'{out}/project/{fname}', 'w').write(html)
        hel = re.search(r'<helmet>(.*?)</helmet>', html, re.S).group(1); body = re.search(r'</helmet>(.*?)</x-dc>', html, re.S).group(1)
        open(f'{out}/prev/{fname.replace(".dc.html", ".html")}', 'w').write(f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">{hel}</head><body>{body}</body></html>')
        print(fname, len(html))
    json.dump(idx, open(f'{out}/project/canvas.json', 'w'), ensure_ascii=False, indent=1)
