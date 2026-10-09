# Direction C — "האפליקציה": calm, card-based, big numbers, one blue accent, app-like on the phone.
import math
from common import *

FONTS = 'family=Rubik:wght@400;500;600;700'

CSS = '''
.c{--bg:#F2F4F7;--card:#FFFFFF;--soft:#F5F7FA;--line:#E4E8EE;--tx:#101828;--tx2:#475467;--mute:#5E6B7E;--acc:#2E5BDB;--accs:#E8EEFC;--up:#067647;--ups:#E3F5EC;--dn:#C01F12;--dns:#FDECEA;--gold:#9A6B00;--golds:#FBF1D9;--zone:#E6EAF0;
 background:var(--bg);color:var(--tx);font-family:Rubik,sans-serif;box-sizing:border-box}
.c.dark{--bg:#0D1117;--card:#161C26;--soft:#1D2531;--line:#273141;--tx:#EEF2F7;--tx2:#B8C2D1;--mute:#8C98AA;--acc:#7EA2FF;--accs:#1C2945;--up:#4AD394;--ups:#13291F;--dn:#FF7B6E;--dns:#331816;--gold:#F0C35A;--golds:#2E2510;--zone:#273141}
.c *{box-sizing:border-box}
.c a{color:var(--acc);text-decoration:none;font-weight:500}
.c .up{color:var(--up)} .c .dn{color:var(--dn)} .c .flat{color:var(--mute)}
.c .mute{color:var(--mute)}
.c .chip{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;font-size:13px;font-weight:500;background:var(--soft);color:var(--tx2);white-space:nowrap}
.c .chip.up{background:var(--ups);color:var(--up)} .c .chip.dn{background:var(--dns);color:var(--dn)}
.c .chip.gold{background:var(--golds);color:var(--gold)} .c .chip.acc{background:var(--accs);color:var(--acc)}
.c .hdr{display:flex;align-items:center;gap:24px;padding:16px 40px}
.c .logo{display:flex;align-items:center;gap:10px;font-weight:700;font-size:19px;white-space:nowrap}
.c .logo i{width:28px;height:28px;border-radius:8px;background:var(--acc);display:inline-block;position:relative}
.c .logo i::after{content:"";position:absolute;inset:8px 7px 7px 8px;border-left:2.5px solid #fff;border-bottom:2.5px solid #fff;transform:skewX(-12deg)}
.c .segc{display:flex;gap:2px;padding:4px;background:var(--zone);border-radius:12px}
.c .segc a{padding:8px 18px;border-radius:9px;color:var(--tx2);font-weight:500;font-size:15px}
.c .segc a.on{background:var(--card);color:var(--tx);box-shadow:0 1px 2px rgba(16,24,40,.08)}
.c .srch{margin-inline-start:auto;display:flex;align-items:center;gap:8px;width:260px;height:40px;border-radius:12px;background:var(--card);border:1px solid var(--line);padding:0 14px;color:var(--mute);font-size:14px}
.c .qrow{display:flex;gap:8px;padding:0 40px 8px;overflow:hidden}
.c .q{display:flex;gap:8px;align-items:baseline;padding:8px 14px;border-radius:12px;background:var(--card);border:1px solid var(--line);font-size:14px;white-space:nowrap}
.c .q b{font-weight:500;color:var(--tx2)}
.c .wrap{padding:16px 40px 40px;display:flex;flex-direction:column;gap:20px}
.c .card{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:24px;display:flex;flex-direction:column;gap:14px;min-width:0}
.c .ch{display:flex;align-items:center;gap:10px}
.c .ch h2{font-size:20px;font-weight:600;margin:0}
.c .ch .go{margin-inline-start:auto;font-size:14px}
.c .eyebrow{font-size:13px;font-weight:500;color:var(--mute)}
.c h1{font-size:34px;line-height:1.25;font-weight:600;margin:0;letter-spacing:-.01em}
.c .dek{font-size:17px;line-height:1.6;color:var(--tx2);margin:0}
.c .stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.c .stat{background:var(--soft);border-radius:14px;padding:14px 16px}
.c .stat .l{font-size:13px;color:var(--mute)}
.c .stat .v{font-size:30px;font-weight:600;line-height:1.2}
.c .stat .s{font-size:13px;color:var(--tx2)}
.c .gauge{position:relative;width:240px;height:140px;margin:0 auto}
.c .gauge svg{position:absolute;inset:0;width:240px;height:140px}
.c .gauge .num{position:absolute;left:0;right:0;top:62px;text-align:center}
.c .gauge .num .n{font-size:52px;font-weight:700;line-height:1}
.c .comps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;text-align:center}
.c .comps > div{background:var(--soft);border-radius:12px;padding:8px}
.c .comps .n{font-size:20px;font-weight:600;display:block}
.c .comps span{font-size:12px;color:var(--mute)}
.c .ev{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.c .evc{display:grid;grid-template-columns:52px minmax(0,1fr);gap:12px;align-items:center;background:var(--soft);border-radius:14px;padding:12px}
.c .date{width:52px;height:56px;border-radius:12px;background:var(--card);border:1px solid var(--line);display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1.1}
.c .date b{font-size:20px} .c .date span{font-size:11px;color:var(--mute)}
.c .date.now{background:var(--acc);border-color:var(--acc);color:#fff} .c .date.now span{color:#fff}
.c .evc .t{font-size:15px;font-weight:500}
.c .evc .s{font-size:13px;color:var(--mute)}
.c .picks{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}
.c .pk{border:1px solid var(--line);border-radius:16px;padding:14px;display:flex;flex-direction:column;gap:10px;background:var(--card)}
.c .pk .top{display:flex;align-items:center;justify-content:space-between}
.c .pk .sym{font-size:20px;font-weight:700}
.c .pk .nm{font-size:12px;color:var(--mute);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:-6px}
.c .pk .pr{font-size:24px;font-weight:600}
.c .sp{width:100%;height:56px;display:block}
.c .sp .ar{fill:var(--acc);opacity:.12}.c .sp .ln{fill:none;stroke:var(--acc);stroke-width:2;stroke-linejoin:round}
.c .sp .lv{stroke-width:1;stroke-dasharray:3 4}.c .sp .lo{stroke:var(--dn)}.c .sp .hi{stroke:var(--up)}
.c .rb{position:relative;height:6px;border-radius:3px;background:linear-gradient(90deg,var(--ups),var(--dns))}
.c .rb b{position:absolute;top:-4px;width:14px;height:14px;border-radius:50%;background:var(--card);border:3px solid var(--acc);margin-right:-7px}
.c .rbl{display:flex;justify-content:space-between;font-size:12px;color:var(--mute)}
.c .rbl .n{color:var(--tx);font-weight:500}
.c .rd{display:inline-block;width:8px;height:8px;border-radius:50%;margin-inline-end:3px;background:var(--zone)}
.c .rd.w{background:var(--up)}
.c .ledg{display:flex;align-items:center;gap:8px;flex-wrap:wrap;background:var(--soft);border-radius:14px;padding:12px 14px;font-size:14px}
.c .two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}
.c .li{display:grid;grid-template-columns:28px minmax(0,1fr);gap:10px;align-items:start;font-size:16px;line-height:1.55}
.c .li i{width:26px;height:26px;border-radius:8px;background:var(--accs);color:var(--acc);font-style:normal;font-weight:600;font-size:14px;display:flex;align-items:center;justify-content:center}
.c .fl{display:flex;flex-direction:column;gap:4px;padding:12px;border-radius:14px;background:var(--soft);font-size:14px;line-height:1.5}
.c .fl .who{font-size:12px;color:var(--mute);display:flex;gap:8px}
.c .en{direction:ltr;text-align:left;unicode-bidi:isolate}
.c .three{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}
.c .r{display:flex;justify-content:space-between;align-items:center;padding:7px 0;font-size:15px}
.c .r + .r{border-top:1px solid var(--line)}
.c .ring{width:46px;height:46px;flex:0 0 46px}
.c .tabbar{position:absolute;left:0;right:0;bottom:0;height:78px;background:var(--card);border-top:1px solid var(--line);display:grid;grid-template-columns:repeat(6,minmax(0,1fr));padding:8px 4px 18px}
.c .tabbar a{display:flex;flex-direction:column;align-items:center;gap:3px;font-size:11px;color:var(--mute);font-weight:500}
.c .tabbar a.on{color:var(--acc)}
.c .tabbar svg{width:22px;height:22px}
'''

def arc(cx, cy, r, a0, a1):
    # angles in degrees, 180 = left, 0 = right (math), drawn along the top half
    p0 = (cx + r * math.cos(math.radians(a0)), cy - r * math.sin(math.radians(a0)))
    p1 = (cx + r * math.cos(math.radians(a1)), cy - r * math.sin(math.radians(a1)))
    return f'M{p0[0]:.1f} {p0[1]:.1f} A{r} {r} 0 0 1 {p1[0]:.1f} {p1[1]:.1f}'

def gauge(v, w=240):
    # RTL reading: 0 sits on the right, 100 on the left (same as the other directions' scales)
    cx, cy, r = 120, 120, 96
    def ang(x): return x * 180 / 100      # 0 → 0° (right), 100 → 180° (left)
    segs = [(0, 44.5, 'var(--dn)'), (45.5, 65.5, 'var(--gold)'), (66.5, 100, 'var(--up)')]
    paths = ''.join(f'<path d="{arc(cx, cy, r, ang(b), ang(a))}" stroke="{c}" stroke-width="14" fill="none" stroke-linecap="butt" opacity=".9"></path>' for a, b, c in segs)
    a = math.radians(ang(v))
    kx, ky = cx + r * math.cos(a), cy - r * math.sin(a)
    knob = f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="11" fill="var(--card)" stroke="var(--tx)" stroke-width="4"></circle>'
    return f'<svg viewBox="0 0 240 140" aria-hidden="true">{paths}{knob}</svg>'

def rb(p):
    lo, hi, pr = p['lo'], p['hi'], p['price']
    pos = max(0, min(100, (pr - lo) / (hi - lo) * 100))
    return (f'<div class="rb"><b style="right:{pos:.0f}%"></b></div>'
            f'<div class="rbl"><span>{p["lo_l"]} {n(fmt_price(lo))}</span><span>{p["hi_l"]} {n(fmt_price(hi))}</span></div>')

def pkcard(p, style=''):
    return f'''<article class="pk" style="{style}">
<div class="top"><a href="#" class="sym ltr" style="color:var(--tx)">{p['sym']}</a><span class="chip {ud(p['chg'])}">{pct(p['chg'])}</span></div>
<div class="nm">{p['name'] or '&nbsp;'}</div>
<div class="pr">{n('$' + fmt_price(p['price']))}</div>
{pick_spark(p, h=44)}
{rb(p)}
<div style="display:flex;gap:6px;flex-wrap:wrap">{''.join(f'<span class="chip" style="font-size:12px;padding:2px 8px">{t}</span>' for t in p['src'].split(' + '))}</div>
<div style="font-size:12px;color:var(--mute);display:flex;align-items:center;gap:6px"><span>{dots(p['rec'])}</span><span>{rec_text(p['rec'])}</span></div>
</article>'''

def ring(pct_):
    r = 18; c = 2 * math.pi * r
    return (f'<svg class="ring" viewBox="0 0 46 46" aria-hidden="true"><circle cx="23" cy="23" r="{r}" fill="none" stroke="var(--zone)" stroke-width="6"></circle>'
            f'<circle cx="23" cy="23" r="{r}" fill="none" stroke="var(--acc)" stroke-width="6" stroke-dasharray="{c * pct_ / 100:.1f} {c:.1f}" transform="rotate(-90 23 23)" stroke-linecap="round"></circle></svg>')

def desktop():
    s = SCORES
    body = f'''<div class="c" dir="rtl" style="width:1280px;min-height:1880px">
<header class="hdr"><div class="logo"><i></i>The Daily Edge</div>
<nav class="segc">{''.join(f'<a href="#" class="{"on" if i == 0 else ""}">{t}</a>' for i, t in enumerate(TABS))}</nav>
<div class="srch">{SEARCH_ICON}<span>חיפוש טיקר או נושא</span></div>
<span class="chip acc">טרום מסחר · נפתח בעוד {n('3:32')}</span></header>
<div class="qrow">{''.join(f'<div class="q"><b>{l}</b>{n(v) if v else ""}{pct(c)}</div>' for l, v, c in TICKER[:6])}</div>
<main class="wrap">
<section style="display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:20px">
<div class="card" style="padding:28px">
<div class="eyebrow">יום המסחר של חמישי · 8 באוקטובר</div>
<h1>{HEADLINE}</h1>
<p class="dek">{DEK}</p>
<div class="stats">
<div class="stat"><div class="l">S&amp;P 500</div><div class="v">{pct(SPX['chg'])}</div><div class="s">{n('7,765')}</div></div>
<div class="stat"><div class="l">המניה הממוצעת</div><div class="v">{pct(0.60)}</div><div class="s">רוב המניות עלו</div></div>
<div class="stat"><div class="l">עלו / ירדו</div><div class="v">{n('345')}<span class="mute" style="font-size:20px"> / {n('156')}</span></div><div class="s">יום רוחב חיובי</div></div>
</div>
<div><a href="#">לניתוח המלא ←</a></div>
</div>
<div class="card" style="align-items:stretch">
<div class="ch"><h2 style="font-size:17px">The Edge Meter</h2><span class="mute" style="font-size:12px;margin-inline-start:auto">סגירת 8.10</span></div>
<div class="gauge">{gauge(s['combined'])}<div class="num">{n(s['combined'])}<div style="margin-top:4px"><span class="chip gold">זהיר</span></div></div></div>
<div class="comps"><div>{n(s['tech'])}<span>טכני</span></div><div>{n(s['breadth'])}<span>רוחב</span></div><div>{n(s['flow'])}<span>אופציות</span></div></div>
<div style="display:flex;gap:6px;flex-wrap:wrap"><span class="chip up">● VIX ירוק · {n('15.2')}</span><span class="chip">4 ימי מכירה בחודש</span></div>
</div>
</section>

<section class="card" style="padding:20px 24px">
<div class="ch"><h2>היומן</h2><span class="chip">אין נתוני מאקרו היום</span><a href="#" class="go">ליומן המלא ←</a></div>
<div class="ev">
<div class="evc"><div class="date now"><b>9</b><span>היום</span></div><div><div class="t"><span class="ltr">DAL</span> מדווחת לפני הפתיחה</div><div class="s">וגם <span class="ltr">PGR</span></div></div></div>
<div class="evc"><div class="date"><b>13</b><span>אוק׳</span></div><div><div class="t">הבנקים פותחים את עונת הדוחות</div><div class="s">בעוד 4 ימים · <span class="ltr">JPM · WFC · C · GS</span></div></div></div>
<div class="evc"><div class="date"><b>14</b><span>אוק׳</span></div><div><div class="t">מדד המחירים לצרכן (CPI)</div><div class="s">{n('15:30')} · צפי ליבה {n('0.2%')} · קודם {n('0.3%')}</div></div></div>
</div></section>

<section class="card">
<div class="ch"><h2>הנבחרות של היום</h2><span class="chip gold">השוק זהיר · עד 4 פוזיציות, בשני שליש גודל</span><a href="#" class="go">כל {len(PICKS)} הנבחרות ←</a></div>
<div class="picks">{''.join(pkcard(p) for p in TOP5)}</div>
<div class="ledg"><b>היומן</b><span class="mute">מהדורות שסיימו 5 ימים, מול השוק:</span>{''.join(f'<span class="chip up">{ddmm(d)} · {pct(x)}</span>' for d, x in LEDGER)}<span class="mute" style="margin-inline-start:auto">3 מתוך 3 מעל השוק</span></div>
</section>

<section class="two">
<div class="card"><div class="ch"><h2>התדרוך</h2><span class="chip">{n('06:01')}</span><a href="#" class="go">המלא ←</a></div>
{''.join(f'<div class="li"><i>{i + 1}</i><span>{h}</span></div>' for i, h in enumerate(BRIEF))}</div>
<div class="card"><div class="ch"><h2>בזק מהרשת</h2><a href="#" class="go">עוד ←</a></div>
{''.join(f'<div class="fl"><div class="who"><span class="n">{t}</span><span class="ltr">{s_}</span></div><div class="en">{x}</div></div>' for s_, t, x in PULSE[:3])}</div>
</section>

<section class="three">
<div class="card"><div class="ch"><h2 style="font-size:17px">סקטורים</h2><span class="mute" style="font-size:12px">5 ימים מול S&amp;P</span></div>
<div>{''.join(f'<div class="r"><span>{a}</span><span class="chip {ud(b)}">{pct(b)}</span></div>' for a, b in SECT_TOP + SECT_BOT[:1])}</div></div>
<div class="card"><div class="ch"><h2 style="font-size:17px">העולם</h2></div>
<div>{''.join(f'<div class="r"><span>{a} <span class="mute" style="font-size:12px">· {st}</span></span><span class="chip {ud(c)}">{pct(c)}</span></div>' for a, c, st in WORLD[:4])}</div></div>
<div class="card"><div class="ch"><h2 style="font-size:17px">מה השווקים מהמרים</h2></div>
{''.join(f'<div style="display:flex;gap:12px;align-items:center">{ring(c)}<div><div style="font-size:13px" class="mute">{a}</div><div style="font-weight:500">{b} · {n(str(c) + "%")}</div></div></div>' for a, b, c, d in BETS)}</div>
</section>
</main></div>'''
    return page('האפליקציה · בית · מחשב', FONTS, CSS, body, 1280, 1880)

ICONS = [
    '<path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z"></path>',
    '<path d="M4 19l5-6 4 3 7-9"></path>',
    '<rect x="4" y="5" width="16" height="15" rx="2"></rect><path d="M4 10h16M9 3v4M15 3v4"></path>',
    '<path d="M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.4 6.7 19.4l1.2-6L3.4 9.3l6-.7z"></path>',
    '<rect x="4" y="4" width="16" height="16" rx="2"></rect><path d="M8 9h8M8 13h8M8 17h5"></path>',
    '<circle cx="12" cy="12" r="8"></circle><path d="M4 12h16M12 4c3 3 3 13 0 16M12 4c-3 3-3 13 0 16"></path>',
]

def phone():
    s = SCORES
    tabbar = ''.join(f'<a href="#" class="{"on" if i == 0 else ""}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round" aria-hidden="true">{ic}</svg>{t}</a>' for i, (t, ic) in enumerate(zip(TABS, ICONS)))
    body = f'''<div class="c dark" dir="rtl" style="width:390px;min-height:1720px;position:relative">
<header class="hdr" style="padding:14px 16px 10px;gap:10px"><div class="logo" style="flex-grow:1;font-size:17px"><i></i>The Daily Edge</div>
<button aria-label="חיפוש" style="width:44px;height:44px;border-radius:12px;border:1px solid var(--line);background:var(--card);color:var(--tx);display:flex;align-items:center;justify-content:center">{SEARCH_ICON}</button></header>
<div class="qrow" style="padding:0 16px 4px">{''.join(f'<div class="q" style="padding:6px 10px;font-size:13px"><b>{l}</b>{pct(c)}</div>' for l, v, c in TICKER[:3])}</div>
<main class="wrap" style="padding:10px 16px 110px;gap:14px">
<section class="card" style="padding:18px;border-radius:18px">
<div class="eyebrow">יום המסחר של חמישי · 8.10</div>
<h1 style="font-size:24px">{HEADLINE}</h1>
<div style="display:grid;grid-template-columns:150px minmax(0,1fr);gap:10px;align-items:center">
<div class="gauge" style="width:150px;height:92px;margin:0">{gauge(s['combined']).replace('<svg ', '<svg style="width:150px;height:88px" ')}<div class="num" style="top:36px">{n(s['combined']).replace('class="n ', 'style="font-size:34px" class="n ')}</div></div>
<div style="display:flex;flex-direction:column;gap:6px"><span class="chip gold" style="align-self:flex-start">זהיר</span><span style="font-size:13px" class="mute">טכני {n(s['tech'])} · רוחב {n(s['breadth'])} · אופציות {n(s['flow'])}</span></div></div>
<div class="stats" style="gap:8px">
<div class="stat" style="padding:10px"><div class="l">S&amp;P 500</div><div class="v" style="font-size:19px">{pct(SPX['chg'])}</div></div>
<div class="stat" style="padding:10px"><div class="l">הממוצעת</div><div class="v" style="font-size:19px">{pct(0.60)}</div></div>
<div class="stat" style="padding:10px"><div class="l">VIX</div><div class="v" style="font-size:19px">{n('15.18')}</div></div></div>
</section>
<section class="card" style="padding:16px;border-radius:18px;gap:10px">
<div class="ch"><h2 style="font-size:17px">היומן</h2><a href="#" class="go">הכל ←</a></div>
<div class="evc"><div class="date now"><b>9</b><span>היום</span></div><div><div class="t"><span class="ltr">DAL</span> לפני הפתיחה</div><div class="s">וגם <span class="ltr">PGR</span> · אין מאקרו</div></div></div>
<div class="evc"><div class="date"><b>13</b><span>אוק׳</span></div><div><div class="t">הבנקים פותחים את העונה</div><div class="s">ולמחרת CPI · {n('15:30')}</div></div></div>
</section>
<section style="display:flex;flex-direction:column;gap:10px">
<div class="ch"><h2 style="font-size:18px">הנבחרות של היום</h2><a href="#" class="go">כל {len(PICKS)} ←</a></div>
<span class="chip gold" style="align-self:flex-start">השוק זהיר · עד 4, בשני שליש גודל</span>
<div style="display:flex;gap:10px;overflow:hidden;margin-inline-end:-16px">{''.join(pkcard(p, 'flex:0 0 220px') for p in TOP5[:3])}</div>
<div class="ledg" style="font-size:13px"><b>היומן</b>{''.join(f'<span class="chip up">{ddmm(d)} {pct(x)}</span>' for d, x in LEDGER)}</div>
</section>
<section class="card" style="padding:16px;border-radius:18px">
<div class="ch"><h2 style="font-size:17px">התדרוך</h2><span class="chip">{n('06:01')}</span></div>
{''.join(f'<div class="li" style="font-size:15px"><i>{i + 1}</i><span>{h}</span></div>' for i, h in enumerate(BRIEF[:3]))}
<div class="fl"><div class="who"><span class="n">{PULSE[0][1]}</span><span class="ltr">{PULSE[0][0]}</span><span>· בזק</span></div><div class="en">{PULSE[0][2]}</div></div>
</section>
<section style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px">
<div class="card" style="padding:12px;border-radius:14px;gap:4px;font-size:13px"><b>סקטורים</b><span class="mute">{SECT_TOP[0][0]}</span>{pct(SECT_TOP[0][1], 1)}</div>
<div class="card" style="padding:12px;border-radius:14px;gap:4px;font-size:13px"><b>העולם</b><span class="mute">DAX</span>{pct(WORLD[1][1])}</div>
<div class="card" style="padding:12px;border-radius:14px;gap:4px;font-size:13px"><b>הימורים</b><span class="mute">הפד ללא שינוי</span>{n('84%')}</div>
</section>
</main>
<nav class="tabbar" aria-label="טאבים">{tabbar}</nav>
</div>'''
    return page('האפליקציה · בית · טלפון', FONTS, CSS, body, 390, 1720)
