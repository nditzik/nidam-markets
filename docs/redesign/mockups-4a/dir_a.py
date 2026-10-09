# Direction A — "המהדורה": a refined broadsheet. Serif display, hairlines, paper and ink.
from common import *

FONTS = 'family=Frank+Ruhl+Libre:wght@500;700;900&amp;family=Heebo:wght@400;500;700'

CSS = '''
.a{--paper:#FAF8F3;--card:#FFFFFF;--ink:#1A1915;--ink2:#47443D;--mute:#6E6A61;--rule:#D9D4C8;--rule2:#1A1915;--up:#1D7348;--dn:#B42318;--acc:#9E2A1B;--gold:#86650F;--zone:#EFEBE2;
 background:var(--paper);color:var(--ink);font-family:Heebo,sans-serif;box-sizing:border-box}
.a.dark{--paper:#14130F;--card:#1B1A15;--ink:#EEEAE0;--ink2:#C9C3B6;--mute:#9C968A;--rule:#36332B;--rule2:#EEEAE0;--up:#58C98F;--dn:#F2836F;--acc:#EE8E78;--gold:#DDB65A;--zone:#24221C}
.a *{box-sizing:border-box}
.a a{color:inherit}
.a .serif{font-family:'Frank Ruhl Libre',serif}
.a .up{color:var(--up)} .a .dn{color:var(--dn)} .a .flat{color:var(--mute)}
.a .kick{font-size:12px;font-weight:700;letter-spacing:.06em;color:var(--acc)}
.a .mute{color:var(--mute)}
.a .more{font-size:14px;font-weight:500;color:var(--ink);text-decoration:none;border-bottom:1px solid var(--rule2);padding-bottom:1px}
.a .mast{padding:14px 48px 0}
.a .mtop{display:flex;justify-content:space-between;font-size:13px;color:var(--ink2);padding-bottom:10px;border-bottom:1px solid var(--rule)}
.a .logo{font-family:'Frank Ruhl Libre',serif;font-weight:900;font-size:46px;text-align:center;letter-spacing:-.01em;padding:10px 0 8px;line-height:1}
.a .logo small{display:block;font-family:Heebo,sans-serif;font-weight:500;font-size:12px;letter-spacing:.18em;color:var(--mute);margin-top:6px}
.a .dbl{border-top:3px double var(--rule2)}
.a .nav{display:flex;align-items:center;gap:30px;padding:0 48px;height:50px;border-bottom:1px solid var(--rule2)}
.a .nav a{text-decoration:none;font-size:16px;font-weight:500;color:var(--ink2);padding:14px 0;border-bottom:3px solid transparent}
.a .nav a.on{color:var(--ink);font-weight:700;border-bottom-color:var(--acc)}
.a .srch{margin-inline-start:auto;display:flex;align-items:center;gap:8px;width:250px;height:34px;border:1px solid var(--rule);background:var(--card);padding:0 12px;font-size:14px;color:var(--mute)}
.a .srch kbd{margin-inline-start:auto;font:12px Heebo;border:1px solid var(--rule);padding:0 5px;color:var(--mute)}
.a .tick{display:flex;overflow:hidden;padding:0 48px;border-bottom:1px solid var(--rule);font-size:14px}
.a .tick > div{padding:9px 13px;border-inline-start:1px solid var(--rule);display:flex;gap:8px;align-items:baseline;white-space:nowrap}
.a .tick > div:first-child{border-inline-start:0;padding-inline-start:0}
.a .tick b{font-weight:500;color:var(--ink2)}
.a .wrap{padding:30px 48px 48px;display:flex;flex-direction:column;gap:34px}
.a .lead{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:0}
.a .lead > .main{padding-inline-end:36px;display:flex;flex-direction:column;gap:14px}
.a .lead > .rail{padding-inline-start:30px;border-inline-start:1px solid var(--rule);display:flex;flex-direction:column;gap:12px}
.a h1{font-family:'Frank Ruhl Libre',serif;font-weight:700;font-size:44px;line-height:1.12;margin:0;letter-spacing:-.005em}
.a .dek{font-size:19px;line-height:1.6;color:var(--ink2);margin:0;max-width:720px}
.a .stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);margin-top:4px}
.a .stats > div{padding:12px 16px;border-inline-start:1px solid var(--rule)}
.a .stats > div:first-child{border-inline-start:0;padding-inline-start:0}
.a .stats .l{font-size:13px;color:var(--mute)}
.a .stats .v{font-family:'Frank Ruhl Libre',serif;font-size:34px;font-weight:700;line-height:1.15}
.a .stats .s{font-size:13px;color:var(--ink2)}
.a .big{font-family:'Frank Ruhl Libre',serif;font-size:76px;font-weight:900;line-height:.9}
.a .scale{position:relative;height:8px;background:linear-gradient(90deg,var(--zone) 0 45%,var(--zone) 45% 66%,var(--zone) 66%);border:1px solid var(--rule)}
.a .scale i{position:absolute;top:-1px;bottom:-1px;width:1px;background:var(--rule2);opacity:.35}
.a .scale b{position:absolute;top:-5px;width:3px;height:16px;background:var(--ink)}
.a .sclab{display:flex;justify-content:space-between;font-size:12px;color:var(--mute)}
.a .comp{display:grid;grid-template-columns:70px minmax(0,1fr) 30px;gap:10px;align-items:center;font-size:14px}
.a .comp .bar{height:4px;background:var(--zone)}
.a .comp .bar i{display:block;height:4px;background:var(--ink2)}
.a .msp{width:100%;height:46px;display:block}
.a .msp .zg{fill:var(--up);opacity:.08}.a .msp .zr{fill:var(--dn);opacity:.08}
.a .msp .ln{fill:none;stroke:var(--ink);stroke-width:1.5}.a .msp .dot{fill:var(--acc)}
.a .railrow{font-size:14px;color:var(--ink2);display:flex;align-items:center;gap:8px;border-top:1px solid var(--rule);padding-top:10px}
.a .lamp{width:9px;height:9px;border-radius:50%;background:var(--up);display:inline-block}
.a .agenda{display:flex;align-items:stretch;border-top:1px solid var(--rule2);border-bottom:1px solid var(--rule2)}
.a .agenda > div{padding:14px 20px;border-inline-start:1px solid var(--rule);display:flex;flex-direction:column;gap:3px;justify-content:center}
.a .agenda > div:first-child{border-inline-start:0;padding-inline-start:0}
.a .agenda .t{font-size:12px;color:var(--mute);font-weight:500}
.a .agenda .v{font-size:15px}
.a .sec{border-top:4px solid var(--rule2);padding-top:12px;display:flex;flex-direction:column;gap:18px}
.a .sech{display:flex;align-items:baseline;gap:16px}
.a .sech h2{font-family:'Frank Ruhl Libre',serif;font-size:30px;font-weight:700;margin:0}
.a .gate{font-size:14px;color:var(--ink2)}
.a .gate b{color:var(--gold)}
.a .cards{display:grid;grid-template-columns:repeat(5,minmax(0,1fr))}
.a .card{padding:0 18px;border-inline-start:1px solid var(--rule);display:flex;flex-direction:column;gap:8px}
.a .card:first-child{border-inline-start:0;padding-inline-start:0}
.a .card .sym{font-family:'Frank Ruhl Libre',serif;font-size:28px;font-weight:900;line-height:1;display:flex;align-items:baseline;gap:8px}
.a .card .sym .n{font-family:Heebo;font-size:14px;font-weight:500}
.a .card .nm{font-size:13px;color:var(--mute);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.a .sp{width:100%;height:64px;display:block}
.a .sp .ar{fill:var(--ink);opacity:.05}.a .sp .ln{fill:none;stroke:var(--ink);stroke-width:1.5}
.a .sp .lv{stroke-width:1;stroke-dasharray:3 3}.a .sp .lo{stroke:var(--dn)}.a .sp .hi{stroke:var(--up)}
.a .lv3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));font-size:12px;color:var(--mute);border-top:1px solid var(--rule);padding-top:6px}
.a .lv3 .n{display:block;font-size:15px;color:var(--ink);font-weight:500}
.a .src{font-size:13px;color:var(--ink2)}
.a .rd{display:inline-block;width:8px;height:8px;margin-inline-end:3px;border:1px solid var(--ink2)}
.a .rd.w{background:var(--ink2)}
.a .rec{font-size:12px;color:var(--mute);display:flex;align-items:center;gap:6px}
.a .ledger{display:flex;align-items:center;gap:18px;font-size:14px;color:var(--ink2);border-top:1px solid var(--rule);padding-top:12px}
.a .two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0}
.a .two > div{padding-inline-end:30px}
.a .two > div + div{padding-inline-end:0;padding-inline-start:30px;border-inline-start:1px solid var(--rule)}
.a h3{font-family:'Frank Ruhl Libre',serif;font-size:22px;font-weight:700;margin:0 0 4px}
.a ol{margin:0;padding:0;list-style:none;counter-reset:b}
.a ol li{counter-increment:b;display:grid;grid-template-columns:28px minmax(0,1fr);gap:6px;padding:9px 0;border-top:1px solid var(--rule);font-size:16px;line-height:1.5}
.a ol li::before{content:counter(b);font-family:'Frank Ruhl Libre',serif;font-weight:900;font-size:20px;color:var(--acc);line-height:1.2}
.a .fl{display:grid;grid-template-columns:52px minmax(0,1fr);gap:8px;padding:9px 0;border-top:1px solid var(--rule);font-size:14px;line-height:1.45}
.a .fl .en{direction:ltr;text-align:left;unicode-bidi:isolate}
.a .fl .who{font-size:12px;color:var(--mute);display:block}
.a .three{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))}
.a .three > div{padding:0 26px;border-inline-start:1px solid var(--rule)}
.a .three > div:first-child{border-inline-start:0;padding-inline-start:0}
.a .row{display:flex;justify-content:space-between;padding:6px 0;border-top:1px solid var(--rule);font-size:15px}
.a .row:first-of-type{border-top:0}
.a.ph .lv3 .n{font-size:13px}
.a .sub{font-size:12px;color:var(--mute);font-weight:500;margin:8px 0 2px}
'''

def ticker():
    out = ''
    for lab, val, c in TICKER[:7]:
        out += f'<div><b>{lab}</b>{n(val) if val else ""}{pct(c)}</div>'
    return f'<div class="tick">{out}</div>'

def nav():
    tabs = ''.join(f'<a href="#" class="{"on" if i == 0 else ""}">{t}</a>' for i, t in enumerate(TABS))
    return f'<nav class="nav">{tabs}<div class="srch">{SEARCH_ICON}<span>חיפוש טיקר או נושא</span><kbd>/</kbd></div></nav>'

def comp(label, v):
    return f'<div class="comp"><span>{label}</span><div class="bar"><i style="width:{v}%"></i></div>{n(v)}</div>'

def card(p):
    return f'''<article class="card">
<div class="sym"><a href="#" style="text-decoration:none">{p['sym']}</a>{pct(p['chg'])}</div>
<div class="nm">{p['name'] or '&nbsp;'}</div>
{pick_spark(p, h=40)}
<div class="lv3"><div>{p['lo_l']}{n(fmt_price(p['lo']))}</div><div>מחיר{n(fmt_price(p['price']))}</div><div>{p['hi_l']}{n(fmt_price(p['hi']))}</div></div>
<div class="src">{p['srcsub']}</div>
<div class="rec">{dots(p['rec'])}<span>{rec_text(p['rec'])}</span></div>
</article>'''

def desktop():
    s = SCORES
    body = f'''<div class="a" dir="rtl" style="width:1280px;min-height:2020px">
<header class="mast">
<div class="mtop"><span>יום שישי · 9 באוקטובר 2026</span><span>טרום מסחר · וול סטריט נפתחת בעוד 3:32 · 12:58 שעון ישראל</span></div>
<div class="logo">The Daily Edge<small>מאת איציק נידם · השוק האמריקאי בעברית</small></div>
</header>
<div class="dbl"></div>
{nav()}
{ticker()}
<main class="wrap">
<section class="lead">
<div class="main">
<div class="kick">יום המסחר של חמישי · 8.10</div>
<h1>{HEADLINE}</h1>
<p class="dek">{DEK}</p>
<div class="stats">
<div><div class="l">S&amp;P 500</div><div class="v">{pct(SPX['chg'])}</div><div class="s">נסגר ב-{n('7,765')}</div></div>
<div><div class="l">המניה הממוצעת (שוויוני)</div><div class="v">{pct(0.60)}</div><div class="s">רוב המניות עלו</div></div>
<div><div class="l">עלו מול ירדו</div><div class="v">{n('345 / 156')}</div><div class="s">יום רוחב חיובי</div></div>
</div>
<div><a href="#" class="more">הניתוח המלא בטאב השוק ←</a></div>
</div>
<aside class="rail">
<div class="kick">The Edge Meter</div>
<div class="mute" style="font-size:13px">נכון לסגירת יום חמישי · 8.10.26</div>
<div style="display:flex;align-items:baseline;gap:14px"><span class="big n">{s['combined']}</span><span class="serif" style="font-size:28px;font-weight:700">זהיר</span></div>
<div class="scale"><i style="right:45%"></i><i style="right:66%"></i><b style="right:calc({s['combined']}% - 1px)"></b></div>
<div class="sclab"><span>הגנתי</span><span>זהיר</span><span>חיובי</span></div>
{comp('טכני', s['tech'])}{comp('רוחב', s['breadth'])}{comp('אופציות', s['flow'])}
<div><div class="mute" style="font-size:12px;margin-bottom:2px">30 ימים</div>{meter_spark()}</div>
<div class="railrow"><span class="lamp"></span><span>רמזור VIX ירוק · {n('15.2')} מתחת לממוצע 50 ({n('15.5')})</span></div>
<div class="railrow" style="padding-top:8px">4 ימי מכירה בחודש האחרון</div>
</aside>
</section>

<section class="agenda" aria-label="היום ביומן">
<div><span class="serif" style="font-size:22px;font-weight:700">היום ביומן</span></div>
<div><span class="t">מאקרו</span><span class="v">אין נתונים היום</span></div>
<div><span class="t">מדווחות היום</span><span class="v"><b class="ltr">DAL</b> לפני הפתיחה · <b class="ltr">PGR</b></span></div>
<div><span class="t">שני 13.10</span><span class="v">הבנקים פותחים את עונת הדוחות</span></div>
<div><span class="t">שלישי 14.10 · 15:30</span><span class="v">CPI ליבה · צפי {n('0.2%')} (קודם {n('0.3%')})</span></div>
<div style="margin-inline-start:auto"><a href="#" class="more">היומן המלא ←</a></div>
</section>

<section class="sec">
<div class="sech"><span class="kick" style="color:var(--gold)">הנבחרות</span><h2>מניות שקיבלו אישור מחיר לקנייה</h2>
<span class="gate">השוק <b>זהיר</b> · עד 4 פוזיציות, בשני שליש גודל</span>
<span style="margin-inline-start:auto"><a href="#" class="more">כל {len(PICKS)} הנבחרות והיומן ←</a></span></div>
<div class="cards">{''.join(card(p) for p in TOP5)}</div>
<div class="ledger"><b>היומן:</b><span>3 מתוך 3 מהדורות שסיימו 5 ימים — מעל השוק</span><span class="mute">{LEDGER_TXT}</span><span>מהדורת 7.10 אחרי יום: {pct(LAST_ED['cur']['excess'])} מעל השוק</span></div>
</section>

<section class="two">
<div><div class="kick">התדרוך · 06:01</div><h3>ארבעה דברים לדעת הבוקר</h3>
<ol>{''.join(f'<li>{h}</li>' for h in BRIEF)}</ol>
<div style="margin-top:10px"><a href="#" class="more">התדרוך המלא ←</a></div></div>
<div><div class="kick">בזק מהרשת</div><h3>מה כותבים עכשיו</h3>
{''.join(f'<div class="fl"><span class="n mute">{t}</span><div><span class="who ltr">{s_}</span><div class="en">{x}</div></div></div>' for s_, t, x in PULSE)}
<div style="margin-top:10px"><a href="#" class="more">עוד בטאב חדשות ←</a></div></div>
</section>

<section class="three" style="border-top:1px solid var(--rule2);padding-top:14px">
<div><div class="kick">סקטורים · 5 ימים מול S&amp;P</div>
<div class="sub">החזקים</div>{''.join(f'<div class="row"><span>{a}</span>{pct(b)}</div>' for a, b in SECT_TOP)}
<div class="sub">החלשים</div>{''.join(f'<div class="row"><span>{a}</span>{pct(b)}</div>' for a, b in SECT_BOT)}</div>
<div><div class="kick">העולם · היום</div>
{''.join(f'<div class="row"><span>{a} <span class="mute" style="font-size:12px">{st}</span></span>{pct(c)}</div>' for a, c, st in WORLD)}</div>
<div><div class="kick">מה השווקים מהמרים</div>
{''.join(f'<div class="row" style="flex-direction:column;gap:2px"><span class="mute" style="font-size:13px">{a}</span><span style="display:flex;justify-content:space-between"><b>{b}</b><span>{n(str(c) + "%")} <span class="mute" style="font-size:12px">({sgn(d, 1)})</span></span></span></div>' for a, b, c, d in BETS)}</div>
</section>
</main>
</div>'''
    return page('המהדורה · בית · מחשב', FONTS, CSS, body, 1280, 2020)

def phone():
    s = SCORES
    t5 = TOP5
    body = f'''<div class="a dark ph" dir="rtl" style="width:390px;min-height:2000px">
<header style="padding:10px 16px 0">
<div class="mtop" style="font-size:12px"><span>שישי · 9.10.2026</span><span>נפתחת בעוד 3:32</span></div>
<div style="display:flex;align-items:center;gap:10px;padding:10px 0">
<div class="serif" style="font-weight:900;font-size:28px;flex-grow:1;line-height:1">The Daily Edge</div>
<button aria-label="חיפוש" style="width:44px;height:44px;border:1px solid var(--rule);background:transparent;color:var(--ink);display:flex;align-items:center;justify-content:center">{SEARCH_ICON}</button>
</div></header>
<div class="dbl"></div>
<nav class="nav" style="padding:0 16px;gap:20px;overflow:hidden;height:46px">{''.join(f'<a href="#" class="{"on" if i == 0 else ""}" style="font-size:15px;white-space:nowrap">{t}</a>' for i, t in enumerate(TABS))}</nav>
<div class="tick" style="padding:0 16px;overflow:hidden;font-size:13px">{''.join(f'<div style="padding:8px 10px"><b>{l}</b>{pct(c)}</div>' for l, v, c in TICKER[:4])}</div>
<main class="wrap" style="padding:18px 16px 32px;gap:26px">
<section style="display:flex;flex-direction:column;gap:10px">
<div class="kick">יום המסחר של חמישי · 8.10</div>
<h1 style="font-size:29px">{HEADLINE}</h1>
<p class="dek" style="font-size:16px">{DEK}</p>
<div class="stats" style="grid-template-columns:repeat(3,minmax(0,1fr))">
<div style="padding:8px 8px 8px 0"><div class="l">S&amp;P 500</div><div class="v" style="font-size:22px">{pct(SPX['chg'])}</div></div>
<div style="padding:8px"><div class="l">הממוצעת</div><div class="v" style="font-size:22px">{pct(0.60)}</div></div>
<div style="padding:8px"><div class="l">עלו/ירדו</div><div class="v" style="font-size:22px">{n('345/156')}</div></div>
</div>
<div style="display:grid;grid-template-columns:auto minmax(0,1fr);gap:14px;align-items:center;border-bottom:1px solid var(--rule);padding:4px 0 12px">
<div><div class="kick" style="font-size:11px">The Edge Meter</div><div style="display:flex;align-items:baseline;gap:8px"><span class="big n" style="font-size:52px">{s['combined']}</span><span class="serif" style="font-size:20px;font-weight:700">זהיר</span></div></div>
<div style="display:flex;flex-direction:column;gap:6px">{comp('טכני', s['tech'])}{comp('רוחב', s['breadth'])}{comp('אופציות', s['flow'])}</div>
</div>
<div class="mute" style="font-size:13px"><span class="lamp"></span> VIX ירוק · 4 ימי מכירה בחודש · סגירת 8.10</div>
</section>
<section class="agenda" style="flex-direction:column">
<div style="padding:10px 0;border:0"><span class="serif" style="font-size:20px;font-weight:700">היום ביומן</span></div>
<div style="padding:8px 0;border-inline-start:0;border-top:1px solid var(--rule)"><span class="v"><b class="ltr">DAL</b> לפני הפתיחה · <b class="ltr">PGR</b> · אין מאקרו</span></div>
<div style="padding:8px 0 12px;border-inline-start:0;border-top:1px solid var(--rule)"><span class="t">בשבוע הבא</span><span class="v">13.10 הבנקים · 14.10 CPI (צפי {n('0.2%')})</span></div>
</section>
<section class="sec">
<div><span class="kick" style="color:var(--gold)">הנבחרות</span><h2 style="font-size:26px;font-family:'Frank Ruhl Libre',serif;margin:2px 0 0">אישור מחיר לקנייה</h2>
<div class="gate" style="margin-top:4px">השוק <b>זהיר</b> · עד 4, בשני שליש גודל</div></div>
<div style="display:flex;gap:0;overflow:hidden;margin-inline-end:-16px">{''.join(f'<div class="card" style="flex:0 0 184px;padding:0 14px">' + card(p)[len('<article class="card">'):-len('</article>')] + '</div>' for p in t5[:3])}</div>
<div class="ledger" style="flex-direction:column;align-items:flex-start;gap:4px"><span><b>היומן:</b> 3 מתוך 3 מהדורות מעל השוק אחרי 5 ימים</span><a href="#" class="more">כל {len(PICKS)} הנבחרות ←</a></div>
</section>
<section><div class="kick">התדרוך · 06:01</div>
<ol style="margin-top:6px">{''.join(f'<li style="font-size:15px">{h}</li>' for h in BRIEF[:3])}</ol>
<div class="kick" style="margin-top:16px">בזק מהרשת</div>
{''.join(f'<div class="fl"><span class="n mute">{t}</span><div><span class="who ltr">{s_}</span><div class="en">{x}</div></div></div>' for s_, t, x in PULSE[:2])}
<div style="margin-top:8px"><a href="#" class="more">חדשות ←</a></div></section>
<section class="three" style="grid-template-columns:repeat(3,minmax(0,1fr));border-top:1px solid var(--rule2);padding-top:10px">
<div style="padding:0 8px 0 0;border:0"><div class="kick" style="font-size:11px">סקטורים</div><div style="font-size:13px;margin-top:4px">{SECT_TOP[0][0]} {pct(SECT_TOP[0][1], 1)}</div><div style="font-size:13px">{SECT_BOT[0][0]} {pct(SECT_BOT[0][1], 1)}</div></div>
<div style="padding:0 8px"><div class="kick" style="font-size:11px">העולם</div><div style="font-size:13px;margin-top:4px">ת"א {pct(WORLD[0][1])}</div><div style="font-size:13px">DAX {pct(WORLD[1][1])}</div></div>
<div style="padding:0 8px"><div class="kick" style="font-size:11px">הימורים</div><div style="font-size:13px;margin-top:4px">הפד: ללא שינוי</div><div style="font-size:13px">{n('84%')}</div></div>
</section>
</main></div>'''
    return page('המהדורה · בית · טלפון', FONTS, CSS, body, 390, 2000)
