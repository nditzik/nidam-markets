# Direction B — "לוח המסחר": a dense trading board. Panels, grid, mono numbers, dark-first.
from common import *

FONTS = 'family=IBM+Plex+Sans+Hebrew:wght@400;500;600;700&amp;family=IBM+Plex+Mono:wght@400;500;600'

CSS = '''
.b{--bg:#F3F4F6;--pan:#FFFFFF;--pan2:#F7F8FA;--line:#DDE1E6;--tx:#14181F;--tx2:#3D4653;--mute:#5F6B7A;--up:#11845B;--dn:#C4321F;--acc:#B26B00;--accbg:#FFF3DC;--bar:#C9D0D9;--zg:#11845B;--zr:#C4321F;
 background:var(--bg);color:var(--tx);font-family:'IBM Plex Sans Hebrew',sans-serif;box-sizing:border-box;font-size:14px}
.b.dark{--bg:#0B0E13;--pan:#121821;--pan2:#171E29;--line:#232C38;--tx:#E3E8EF;--tx2:#B4BECB;--mute:#8592A3;--up:#3CCB7F;--dn:#FF6B5A;--acc:#F5B03E;--accbg:#2A2110;--bar:#2C3746;--zg:#3CCB7F;--zr:#FF6B5A}
.b *{box-sizing:border-box}
.b a{color:inherit}
.b .n{font-family:'IBM Plex Mono',monospace}
.b .up{color:var(--up)} .b .dn{color:var(--dn)} .b .flat{color:var(--mute)}
.b .mute{color:var(--mute)}
.b .top{display:flex;align-items:center;gap:22px;height:52px;padding:0 24px;background:var(--pan);border-bottom:1px solid var(--line)}
.b .logo{font-weight:700;font-size:17px;display:flex;align-items:center;gap:8px;white-space:nowrap}
.b .logo i{width:10px;height:10px;background:var(--acc);display:inline-block}
.b .tabs{display:flex;height:52px}
.b .tabs a{display:flex;align-items:center;padding:0 16px;text-decoration:none;color:var(--tx2);font-weight:500;border-bottom:2px solid transparent}
.b .tabs a.on{color:var(--tx);border-bottom-color:var(--acc);background:var(--pan2)}
.b .srch{margin-inline-start:auto;display:flex;align-items:center;gap:8px;width:280px;height:32px;border:1px solid var(--line);background:var(--bg);padding:0 10px;color:var(--mute);border-radius:4px}
.b kbd{margin-inline-start:auto;font:12px 'IBM Plex Mono';border:1px solid var(--line);padding:0 5px;border-radius:3px}
.b .sess{display:flex;align-items:center;gap:8px;font-size:13px;white-space:nowrap;color:var(--tx2)}
.b .pill{font-size:12px;font-weight:600;padding:2px 8px;border-radius:3px;background:var(--accbg);color:var(--acc)}
.b .quotes{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));background:var(--pan);border-bottom:1px solid var(--line)}
.b .quotes > div{padding:8px 14px;border-inline-start:1px solid var(--line);display:flex;flex-direction:column;gap:1px}
.b .quotes > div:first-child{border-inline-start:0}
.b .quotes .l{font-size:12px;color:var(--mute)}
.b .quotes .v{display:flex;gap:8px;align-items:baseline;font-size:15px}
.b .grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:12px;padding:16px 24px 32px}
.b .pan{background:var(--pan);border:1px solid var(--line);border-radius:6px;display:flex;flex-direction:column;min-width:0}
.b .ph{display:flex;align-items:center;gap:10px;padding:9px 14px;border-bottom:1px solid var(--line);font-size:13px;font-weight:600;color:var(--tx2)}
.b .ph .go{margin-inline-start:auto;font-weight:500;color:var(--acc);text-decoration:none;font-size:13px}
.b .pb{padding:14px;display:flex;flex-direction:column;gap:12px}
.b h1{font-size:28px;line-height:1.3;font-weight:700;margin:0}
.b .dek{font-size:16px;line-height:1.6;color:var(--tx2);margin:0}
.b .kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border:1px solid var(--line);border-radius:4px}
.b .kpis > div{padding:10px 12px;border-inline-start:1px solid var(--line)}
.b .kpis > div:first-child{border-inline-start:0}
.b .kpis .l{font-size:12px;color:var(--mute)}
.b .kpis .v{font-size:24px;font-weight:600;font-family:'IBM Plex Mono',monospace;direction:ltr;text-align:right;unicode-bidi:isolate}
.b .kpis .s{font-size:12px;color:var(--tx2)}
.b .ad{display:flex;height:6px;border-radius:2px;overflow:hidden;margin-top:6px}
.b .ad i{display:block;height:6px}
.b .score{display:flex;align-items:baseline;gap:12px}
.b .score .n{font-size:56px;font-weight:600;line-height:1}
.b .seg{display:grid;grid-template-columns:45fr 21fr 34fr;gap:2px;height:8px;position:relative}
.b .seg i{display:block;height:8px;opacity:.85}
.b .seg b{position:absolute;top:-4px;width:2px;height:16px;background:var(--tx)}
.b .segl{display:grid;grid-template-columns:45fr 21fr 34fr;font-size:11px;color:var(--mute)}
.b .cm{display:grid;grid-template-columns:62px minmax(0,1fr) 32px;gap:10px;align-items:center}
.b .cm .bar{height:6px;background:var(--bar);border-radius:1px}
.b .cm .bar i{display:block;height:6px;border-radius:1px;background:var(--tx2)}
.b .msp{width:100%;height:56px;display:block;border:1px solid var(--line);border-radius:3px;background:var(--pan2)}
.b .msp .zg{fill:var(--zg);opacity:.1}.b .msp .zr{fill:var(--zr);opacity:.1}
.b .msp .ln{fill:none;stroke:var(--acc);stroke-width:1.6}.b .msp .dot{fill:var(--acc)}
.b .kv{display:flex;justify-content:space-between;align-items:center;font-size:13px;color:var(--tx2);border-top:1px solid var(--line);padding-top:8px}
.b .lamp{width:8px;height:8px;border-radius:50%;background:var(--up);display:inline-block;margin-inline-end:6px}
.b table{width:100%;border-collapse:collapse}
.b th{font-size:12px;font-weight:500;color:var(--mute);text-align:right;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
.b td{padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap;vertical-align:middle}
.b tr:last-child td{border-bottom:0}
.b .tsym{font-weight:700;font-family:'IBM Plex Mono',monospace;font-size:15px;text-decoration:none}
.b .tag{font-size:11px;padding:1px 6px;border-radius:3px;border:1px solid var(--line);color:var(--tx2);white-space:nowrap}
.b .sp{width:130px;height:30px;display:block}
.b .sp .ar{fill:var(--acc);opacity:.08}.b .sp .ln{fill:none;stroke:var(--tx);stroke-width:1.3}
.b .sp .lv{stroke-width:1;stroke-dasharray:2 3}.b .sp .lo{stroke:var(--dn)}.b .sp .hi{stroke:var(--up)}
.b .rng{position:relative;width:110px;height:6px;background:var(--bar);border-radius:3px}
.b .rng b{position:absolute;top:-3px;width:3px;height:12px;background:var(--tx);border-radius:1px}
.b .rd{display:inline-block;width:7px;height:7px;margin-inline-end:2px;background:var(--bar)}
.b .rd.w{background:var(--up)}
.b .cal{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))}
.b .cal > div{padding:12px 14px;border-inline-start:1px solid var(--line);display:flex;flex-direction:column;gap:4px}
.b .cal > div:first-child{border-inline-start:0}
.b .cal .d{font-size:12px;color:var(--mute);display:flex;gap:6px;align-items:center}
.b .cal .now{color:var(--acc);font-weight:600}
.b .cal .e{font-size:15px;font-weight:500}
.b .led{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:1px solid var(--line)}
.b .led > div{padding:9px 14px;border-inline-start:1px solid var(--line);font-size:13px;display:flex;justify-content:space-between}
.b .led > div:first-child{border-inline-start:0}
.b .li{display:grid;grid-template-columns:24px minmax(0,1fr);gap:8px;padding:9px 14px;border-top:1px solid var(--line);line-height:1.5;font-size:15px}
.b .li:first-child{border-top:0}
.b .fl{display:grid;grid-template-columns:48px 110px minmax(0,1fr);gap:10px;padding:8px 14px;border-top:1px solid var(--line);font-size:13px;line-height:1.45}
.b .fl:first-child{border-top:0}
.b .en{direction:ltr;text-align:left;unicode-bidi:isolate}
.b .db{display:grid;grid-template-columns:96px minmax(0,1fr) 52px;gap:8px;align-items:center;padding:4px 0;font-size:13px}
.b .db .t{position:relative;height:10px}
.b .db .t::before{content:"";position:absolute;top:-3px;bottom:-3px;right:50%;width:1px;background:var(--line)}
.b .db .t i{position:absolute;top:0;height:10px;border-radius:1px}
.b .wr{display:flex;justify-content:space-between;padding:6px 0;border-top:1px solid var(--line);font-size:13px}
.b .wr:first-child{border-top:0}
.b .st{width:7px;height:7px;border-radius:50%;display:inline-block;margin-inline-end:6px;background:var(--bar)}
.b .st.on{background:var(--up)}
.b .bt{display:flex;flex-direction:column;gap:4px;padding:6px 0;border-top:1px solid var(--line)}
.b .bt:first-child{border-top:0}
.b .bt .bar{height:6px;background:var(--bar);border-radius:1px}
.b .bt .bar i{display:block;height:6px;background:var(--acc);border-radius:1px}
'''

def quotes():
    out = ''
    for lab, val, c in TICKER:
        out += f'<div><span class="l">{lab}</span><span class="v">{n(val) if val else ""}{pct(c)}</span></div>'
    return f'<div class="quotes">{out}</div>'

def cm(label, v):
    return f'<div class="cm"><span class="mute">{label}</span><div class="bar"><i style="width:{v}%"></i></div>{n(v)}</div>'

def rng(p):
    lo, hi, pr = p['lo'], p['hi'], p['price']
    pos = max(0, min(100, (pr - lo) / (hi - lo) * 100))
    return f'<div class="rng" title="{p["lo_l"]} → {p["hi_l"]}"><b style="right:calc({pos:.0f}% - 1px)"></b></div>'

def row(i, p):
    return f'''<tr><td class="mute n">{i}</td><td><a href="#" class="tsym">{p['sym']}</a><div class="mute" style="font-size:12px;max-width:150px;overflow:hidden;text-overflow:ellipsis">{p['name'] or '&nbsp;'}</div></td>
<td>{n(fmt_price(p['price']))}</td><td>{pct(p['chg'])}</td><td>{pick_spark(p, h=30)}</td>
<td><span class="dn">{n(fmt_price(p['lo']))}</span><div class="mute" style="font-size:11px">{p['lo_l']}</div></td>
<td>{rng(p)}</td>
<td><span class="up">{n(fmt_price(p['hi']))}</span><div class="mute" style="font-size:11px">{p['hi_l']}</div></td>
<td>{''.join(f'<span class="tag" style="margin-inline-end:4px">{t}</span>' for t in p['src'].split(' + '))}</td>
<td>{dots(p['rec'])}<div class="mute" style="font-size:11px">{sum(p['rec'].get('dots', []))}/{p['rec'].get('n', 0)} עלו</div></td></tr>'''

def dbar(name, v, mx=3):
    w = min(abs(v) / mx * 50, 50)
    side = f'left:50%' if v > 0 else 'right:50%'
    # RTL page, but bar chart reads LTR: positive to the left of zero? keep finance convention: positive grows toward reading-end (left in RTL)
    col = 'var(--up)' if v > 0 else 'var(--dn)'
    pos = f'right:calc(50% - {w:.1f}%)' if v > 0 else f'right:50%'
    return f'<div class="db"><span>{name}</span><div class="t"><i style="{pos};width:{w:.1f}%;background:{col}"></i></div>{pct(v)}</div>'

def desktop(dark=False):
    s = SCORES
    body = f'''<div class="b{' dark' if dark else ''}" dir="rtl" style="width:1280px;min-height:1560px">
<header class="top"><div class="logo"><i></i>The Daily Edge</div>
<nav class="tabs">{''.join(f'<a href="#" class="{"on" if i == 0 else ""}">{t}</a>' for i, t in enumerate(TABS))}</nav>
<div class="srch">{SEARCH_ICON}<span>טיקר או נושא</span><kbd>/</kbd></div>
<div class="sess"><span class="pill">טרום מסחר</span><span>פתיחה בעוד {n('3:32')}</span><span class="mute">IL {n('12:58')} · NY {n('05:58')}</span></div>
</header>
{quotes()}
<main class="grid">
<section class="pan" style="grid-column:span 8">
<div class="ph">מצב השוק · יום המסחר של חמישי 8.10<a href="#" class="go">הניתוח המלא ←</a></div>
<div class="pb">
<h1>{HEADLINE}</h1>
<p class="dek">{DEK}</p>
<div class="kpis">
<div><div class="l">S&amp;P 500</div><div class="v dn">{sgn(SPX['chg'])}%</div><div class="s">{n('7,765.36')}</div></div>
<div><div class="l">שוויוני (המניה הממוצעת)</div><div class="v up">+0.60%</div><div class="s">מול S&amp;P: {pct(1.07)}</div></div>
<div><div class="l">עלו / ירדו</div><div class="v">345/156</div><div class="ad"><i style="width:69%;background:var(--up)"></i><i style="width:31%;background:var(--dn)"></i></div></div>
<div><div class="l">VIX</div><div class="v">15.18</div><div class="s"><span class="lamp"></span>רמזור ירוק</div></div>
</div>
</div></section>

<section class="pan" style="grid-column:span 4">
<div class="ph">The Edge Meter<span class="mute" style="font-weight:400">סגירת חמישי · 8.10.26</span></div>
<div class="pb">
<div class="score">{n(s['combined'])}<span style="font-size:20px;font-weight:700;color:var(--acc)">זהיר</span><span class="mute" style="margin-inline-start:auto;font-size:13px">אתמול 55</span></div>
<div class="seg"><i style="background:var(--dn)"></i><i style="background:var(--acc)"></i><i style="background:var(--up)"></i><b style="right:calc({s['combined']}% - 1px)"></b></div>
<div class="segl"><span>הגנתי · 0–44</span><span>זהיר</span><span>חיובי · 66+</span></div>
{cm('טכני', s['tech'])}{cm('רוחב', s['breadth'])}{cm('אופציות', s['flow'])}
{meter_spark()}
<div class="kv"><span>ימי מכירה (30 יום)</span>{n(4)}</div>
</div></section>

<section class="pan" style="grid-column:span 12">
<div class="ph">היומן<span class="mute" style="font-weight:400">שעון ישראל</span><a href="#" class="go">היומן המלא ←</a></div>
<div class="cal">
<div><span class="d"><span class="now">היום · שישי 9.10</span></span><span class="e"><b class="ltr">DAL</b> לפני הפתיחה · <b class="ltr">PGR</b></span><span class="mute" style="font-size:13px">אין נתוני מאקרו</span></div>
<div><span class="d">שני 13.10</span><span class="e">הבנקים פותחים את העונה</span><span class="mute ltr" style="font-size:13px;text-align:right">JPM · WFC · C · GS</span></div>
<div><span class="d">שלישי 14.10 · {n('15:30')}</span><span class="e">CPI ליבה חודשי</span><span class="mute" style="font-size:13px">צפי {n('0.2%')} · קודם {n('0.3%')}</span></div>
<div><span class="d">רביעי 15.10 · {n('15:30')}</span><span class="e">PPI חודשי</span><span class="mute" style="font-size:13px">קודם {n('0.4%')}</span></div>
</div></section>

<section class="pan" style="grid-column:span 12">
<div class="ph"><span style="color:var(--acc)">✦</span> הנבחרות · אישור מחיר לקנייה · מהדורת 8.10<span class="pill">השוק זהיר · עד 4 פוזיציות · שני שליש גודל</span><a href="#" class="go">כל {len(PICKS)} והיומן ←</a></div>
<table><thead><tr><th>#</th><th>מניה</th><th>מחיר</th><th>יום</th><th>60 יום</th><th>סטופ / תמיכה</th><th>מיקום בטווח</th><th>יעד / התנגדות</th><th>מקור</th><th>רקורד</th></tr></thead>
<tbody>{''.join(row(i + 1, p) for i, p in enumerate(TOP5))}</tbody></table>
<div class="led">
{''.join(f'<div><span class="mute">מהדורת {ddmm(d)} · 5 ימים</span>{pct(x)}</div>' for d, x in LEDGER)}
<div><span class="mute">מהדורת 7.10 · יום 1</span>{pct(LAST_ED['cur']['excess'])}</div>
</div></section>

<section class="pan" style="grid-column:span 6">
<div class="ph">התדרוך · {n('06:01')}<a href="#" class="go">המלא ←</a></div>
<div>{''.join(f'<div class="li"><span class="n" style="color:var(--acc)">{i + 1}</span><span>{h}</span></div>' for i, h in enumerate(BRIEF))}</div></section>

<section class="pan" style="grid-column:span 6">
<div class="ph">בזק מהרשת<a href="#" class="go">עוד ←</a></div>
<div>{''.join(f'<div class="fl"><span class="n mute">{t}</span><span class="ltr mute" style="text-align:right">{s_}</span><span class="en">{x}</span></div>' for s_, t, x in PULSE)}</div></section>

<section class="pan" style="grid-column:span 4">
<div class="ph">סקטורים · 5 ימים מול S&amp;P<a href="#" class="go">השוק ←</a></div>
<div class="pb" style="gap:2px">{''.join(dbar(a, v) for a, v in SECT_TOP + SECT_BOT[::-1])}</div></section>
<section class="pan" style="grid-column:span 4">
<div class="ph">העולם<a href="#" class="go">העולם ←</a></div>
<div class="pb" style="gap:0">{''.join(f'<div class="wr"><span><i class="st{" on" if st == "נסחר" else ""}"></i>{a}</span>{pct(c)}</div>' for a, c, st in WORLD)}</div></section>
<section class="pan" style="grid-column:span 4">
<div class="ph">מה השווקים מהמרים</div>
<div class="pb" style="gap:0">{''.join(f'<div class="bt"><div style="display:flex;justify-content:space-between"><span>{a}: <b>{b}</b></span>{n(str(c) + "%")}</div><div class="bar"><i style="width:{c}%"></i></div></div>' for a, b, c, d in BETS)}</div></section>
</main></div>'''
    return page('לוח המסחר · בית · מחשב', FONTS, CSS, body, 1280, 1560)

def phone():
    s = SCORES
    cards = ''
    for p in TOP5[:4]:
        cards += f'''<div style="display:grid;grid-template-columns:72px minmax(0,1fr) auto;gap:10px;align-items:center;padding:10px 14px;border-top:1px solid var(--line)">
<div><a href="#" class="tsym">{p['sym']}</a><div>{pct(p['chg'])}</div></div>
{pick_spark(p, h=30).replace('class="sp"', 'class="sp" style="width:100%"')}
<div style="text-align:left;font-size:12px"><div class="dn">{n(fmt_price(p['lo']))}</div><div class="up">{n(fmt_price(p['hi']))}</div></div></div>'''
    body = f'''<div class="b" dir="rtl" style="width:390px;min-height:1420px">
<header class="top" style="padding:0 14px;gap:10px"><div class="logo" style="flex-grow:1"><i></i>The Daily Edge</div><span class="pill">טרום מסחר {n('3:32')}</span>
<button aria-label="חיפוש" style="width:44px;height:44px;border:1px solid var(--line);background:var(--bg);color:var(--tx);border-radius:4px;display:flex;align-items:center;justify-content:center">{SEARCH_ICON}</button></header>
<nav class="tabs" style="background:var(--pan);border-bottom:1px solid var(--line);height:44px;overflow:hidden">{''.join(f'<a href="#" class="{"on" if i == 0 else ""}" style="padding:0 12px;white-space:nowrap">{t}</a>' for i, t in enumerate(TABS))}</nav>
<div class="quotes" style="grid-template-columns:repeat(3,minmax(0,1fr))">{''.join(f'<div style="padding:6px 10px"><span class="l">{l}</span><span class="v" style="font-size:13px">{pct(c)}</span></div>' for l, v, c in TICKER[:3])}</div>
<main style="padding:12px;display:flex;flex-direction:column;gap:10px">
<section class="pan"><div class="ph">מצב השוק · 8.10</div><div class="pb">
<h1 style="font-size:22px">{HEADLINE}</h1>
<div class="kpis" style="grid-template-columns:repeat(3,minmax(0,1fr))">
<div style="padding:8px"><div class="l">S&amp;P 500</div><div class="v dn" style="font-size:17px">{sgn(SPX['chg'])}%</div></div>
<div style="padding:8px"><div class="l">שוויוני</div><div class="v up" style="font-size:17px">+0.60%</div></div>
<div style="padding:8px"><div class="l">VIX</div><div class="v" style="font-size:17px">15.18</div></div></div>
<div style="display:grid;grid-template-columns:auto minmax(0,1fr);gap:14px;align-items:center;border-top:1px solid var(--line);padding-top:10px">
<div class="score">{n(s['combined']).replace('class="n ', 'style="font-size:44px" class="n ')}<span style="font-size:17px;font-weight:700;color:var(--acc)">זהיר</span></div>
<div style="display:flex;flex-direction:column;gap:4px">{cm('טכני', s['tech'])}{cm('רוחב', s['breadth'])}{cm('אופציות', s['flow'])}</div></div>
</div></section>
<section class="pan"><div class="ph">היומן<a href="#" class="go">המלא ←</a></div>
<div class="pb" style="gap:6px;font-size:14px"><div><span class="now" style="color:var(--acc);font-weight:600">היום</span> · <b class="ltr">DAL</b> לפני הפתיחה · <b class="ltr">PGR</b></div>
<div class="mute">13.10 הבנקים · 14.10 {n('15:30')} CPI (צפי {n('0.2%')})</div></div></section>
<section class="pan"><div class="ph"><span style="color:var(--acc)">✦</span> הנבחרות<span class="pill">זהיר · עד 4</span><a href="#" class="go">כל {len(PICKS)} ←</a></div>
{cards}
<div class="led" style="grid-template-columns:repeat(2,minmax(0,1fr))">{''.join(f'<div style="padding:7px 12px"><span class="mute">{ddmm(d)} · 5 ימים</span>{pct(x)}</div>' for d, x in LEDGER[:2])}</div></section>
<section class="pan"><div class="ph">התדרוך · {n('06:01')}</div>
<div>{''.join(f'<div class="li" style="font-size:14px"><span class="n" style="color:var(--acc)">{i + 1}</span><span>{h}</span></div>' for i, h in enumerate(BRIEF[:3]))}</div></section>
<section class="pan"><div class="ph">בזק מהרשת</div>
<div>{''.join(f'<div class="fl" style="grid-template-columns:44px minmax(0,1fr)"><span class="n mute">{t}</span><span class="en">{x}</span></div>' for s_, t, x in PULSE[:2])}</div></section>
<section style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px">
<div class="pan" style="padding:10px;font-size:12px"><b>סקטורים</b><div>{SECT_TOP[0][0]}</div>{pct(SECT_TOP[0][1], 1)}</div>
<div class="pan" style="padding:10px;font-size:12px"><b>העולם</b><div>DAX</div>{pct(WORLD[1][1])}</div>
<div class="pan" style="padding:10px;font-size:12px"><b>הימורים</b><div>הפד ללא שינוי</div>{n('84%')}</div>
</section></main></div>'''
    return page('לוח המסחר · בית · טלפון', FONTS, CSS, body, 390, 1420)
