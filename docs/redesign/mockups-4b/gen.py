# Stage 4b — polished mockup of direction B ("לוח המסחר") on today's real data.
# Fixes from docs/redesign/critique-4b.md: one role per color (amber = market state,
# blue = interactive), AA palette in light, LTR rule for all graphics, calendar by
# importance, one link pattern, 12px floor, phone labels + 44px targets.
import json, os, re, sys, datetime
sys.path.insert(0, '/home/user/nidam-markets/docs/redesign/mockups-4a')
from data import *  # real data: HEADLINE, DEK, SCORES, PICKS, LEDGER, BRIEF, PULSE, SECT_*, WORLD, BETS, M, W, ind, hist, ca, led, pk, bets

R = '/home/user/nidam-markets/data/'
_e = json.load(open(R + 'econ.json')); ec = _e.get('items') or _e.get('events') or _e.get('rows')
ea = json.load(open(R + 'earnings.json'))
ep = json.load(open(R + 'earnings_prep.json'))['items'][0]
pn = json.load(open(R + 'earnings_prep_notes.json'))['JPM']
ev = ind['evidence']; ro = ind['riskOff']; fl = ind['flow']; vl = M and json.load(open(R + 'market.json'))['vixLight']
last = hist['days'][-1]; prev = hist['days'][-2]
TABS = ['בית', 'השוק', 'היומן', 'מניות', 'חדשות', 'העולם']
ICON_SEARCH = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="M20 20l-3.5-3.5"></path></svg>'
ICON_MOON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"></path></svg>'
FONTS = 'family=IBM+Plex+Sans+Hebrew:wght@400;500;600;700&amp;family=IBM+Plex+Mono:wght@400;500;600'

def n(t, cls=''): return f'<span class="n {cls}">{t}</span>'
def ud(x): return 'up' if x > 0 else 'dn' if x < 0 else 'flat'
def pct(x, d=2): return n(sgn(x, d) + '%', ud(x))
def ddmm(iso): y, m, d = iso[:10].split('-'); return f'{int(d)}.{int(m)}'
def price(v): return f'{v:,.2f}'
CHANGES = {'tech': 90, 'breadth': 32, 'flow': 97}
EDITIONS = [e for e in led['editions']]
TOP5 = PICKS[:5]
LASTED = [e for e in EDITIONS if e.get('cur')][-1]

CSS = '''
body{margin:0}
.n{direction:ltr;unicode-bidi:isolate;font-variant-numeric:tabular-nums;font-family:'IBM Plex Mono',monospace}
.ltr{direction:ltr;unicode-bidi:isolate}
.b{--bg:#EEF0F3;--pan:#FFFFFF;--pan2:#F6F7F9;--line:#D8DDE4;--tx:#14181F;--tx2:#3D4653;--mute:#5B6675;--up:#0D7A52;--dn:#BE2E1C;--st:#8A5200;--stfill:#D9961F;--stbg:#FBF1DC;--lk:#1D5BB8;--lkbg:#E7EEFA;--bar:#CBD2DB;--brand:#D9961F;
 background:var(--bg);color:var(--tx);font-family:'IBM Plex Sans Hebrew',sans-serif;font-size:14px;line-height:1.45}
.b.dark{--bg:#0B0E13;--pan:#121821;--pan2:#171E29;--line:#243040;--tx:#E3E8EF;--tx2:#B4BECB;--mute:#8C98A8;--up:#3CCB7F;--dn:#FF6B5A;--st:#F5B03E;--stfill:#D9961F;--stbg:#2A2110;--lk:#7FB2FF;--lkbg:#182A47;--bar:#2C3746;--brand:#F5B03E}
.b *{box-sizing:border-box}
.b a{color:var(--lk);text-decoration:none}.b a:hover{text-decoration:underline}.b a:focus-visible,.b button:focus-visible{outline:2px solid var(--lk);outline-offset:2px}
.b h1,.b h2,.b p{margin:0}
.b .up{color:var(--up)} .b .dn{color:var(--dn)} .b .flat{color:var(--mute)} .b .mute{color:var(--mute)} .b .st{color:var(--st)}
.b .top{display:flex;align-items:center;gap:20px;height:56px;padding:0 24px;background:var(--pan);border-bottom:1px solid var(--line)}
.b .logo{font-weight:700;font-size:17px;display:flex;align-items:center;gap:8px;white-space:nowrap;color:var(--tx)}
.b .logo i{width:10px;height:10px;background:var(--brand);display:inline-block}
.b .tabs{display:flex;height:56px}
.b .tabs a{display:flex;align-items:center;padding:0 16px;color:var(--tx2);font-weight:500;border-bottom:2px solid transparent;min-height:44px}
.b .tabs a:hover{text-decoration:none;color:var(--tx)}
.b .tabs a[aria-current]{color:var(--lk);border-bottom-color:var(--lk);font-weight:600}
.b .srch{margin-inline-start:auto;display:flex;align-items:center;gap:8px;width:260px;height:36px;border:1px solid var(--line);background:var(--bg);padding:0 10px;color:var(--mute);border-radius:4px;font:inherit;cursor:text}
.b .srch kbd{margin-inline-start:auto;font:12px 'IBM Plex Mono',monospace;border:1px solid var(--line);padding:0 5px;border-radius:3px;color:var(--mute)}
.b .ibtn{width:36px;height:36px;border:1px solid var(--line);background:var(--bg);color:var(--tx2);border-radius:4px;display:flex;align-items:center;justify-content:center;cursor:pointer}
.b .sess{display:flex;align-items:center;gap:8px;font-size:13px;white-space:nowrap;color:var(--tx2)}
.b .pill{font-size:12px;font-weight:600;padding:3px 8px;border-radius:3px;border:1px solid var(--line);color:var(--tx2);background:var(--pan)}
.b .pill.state{background:var(--stbg);color:var(--st);border-color:transparent}
.b .tag{font-size:12px;padding:1px 7px;border-radius:3px;border:1px solid var(--line);color:var(--tx2);white-space:nowrap;background:var(--pan)}
.b .tag.macro{background:var(--stbg);color:var(--st);border-color:transparent;font-weight:600}
.b .tag.earn{background:var(--lkbg);color:var(--lk);border-color:transparent;font-weight:600}
.b .quotes{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));background:var(--pan);border-bottom:1px solid var(--line)}
.b .quotes > div{padding:8px 14px;border-inline-start:1px solid var(--line);display:flex;flex-direction:column;gap:1px}
.b .quotes > div:first-child{border-inline-start:0}
.b .quotes .l{font-size:12px;color:var(--mute)}
.b .quotes .v{display:flex;gap:8px;align-items:baseline;font-size:15px}
.b .grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:12px;padding:16px 24px 32px}
.b .pan{background:var(--pan);border:1px solid var(--line);border-radius:6px;display:flex;flex-direction:column;min-width:0}
.b .ph{display:flex;align-items:center;gap:10px;padding:0 14px;min-height:44px;border-bottom:1px solid var(--line);font-size:13px;font-weight:600;color:var(--tx2)}
.b .ph h2{font-size:13px;font-weight:600;color:var(--tx2)}
.b .ph .go{margin-inline-start:auto;font-weight:500;font-size:13px;padding:12px 0;line-height:20px}
.b .pb{padding:14px;display:flex;flex-direction:column;gap:12px}
.b h1{font-size:28px;line-height:1.3;font-weight:700}
.b .dek{font-size:16px;line-height:1.6;color:var(--tx2)}
.b .kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border:1px solid var(--line);border-radius:4px}
.b .kpis > div{padding:10px 12px;border-inline-start:1px solid var(--line)}
.b .kpis > div:first-child{border-inline-start:0}
.b .kpis .l{font-size:12px;color:var(--mute)}
.b .kpis .v{font-size:24px;font-weight:600;font-family:'IBM Plex Mono',monospace;direction:ltr;text-align:right;unicode-bidi:isolate}
.b .kpis .s{font-size:12px;color:var(--tx2)}
.b .ad{display:flex;height:6px;border-radius:2px;overflow:hidden;margin-top:6px;direction:ltr;gap:2px}
.b .ad i{display:block;height:6px}
.b .sig{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:auto}
.b .sig > div{font-size:13px;color:var(--tx2);border-top:1px solid var(--line);padding-top:8px;line-height:1.5}
.b .sig b{display:block;font-size:12px;color:var(--mute);font-weight:500}
.b .score{display:flex;align-items:baseline;gap:12px}
.b .score .big{font-size:56px;font-weight:600;line-height:1;font-family:'IBM Plex Mono',monospace}
.b .seg{display:grid;grid-template-columns:45fr 21fr 34fr;gap:2px;height:8px;position:relative;direction:ltr}
.b .seg i{display:block;height:8px;opacity:.85;border-radius:1px}
.b .seg b{position:absolute;top:-4px;width:2px;height:16px;background:var(--tx)}
.b .segl{display:grid;grid-template-columns:45fr 21fr 34fr;font-size:12px;color:var(--mute);direction:ltr}
.b .segl span{text-align:left}.b .segl span:last-child{text-align:right}.b .segl span:nth-child(2){text-align:center}
.b .cm{display:grid;grid-template-columns:62px minmax(0,1fr) 32px;gap:10px;align-items:center;font-size:13px}
.b .cm .bar{height:6px;background:var(--bar);border-radius:1px;direction:ltr}
.b .cm .bar i{display:block;height:6px;border-radius:1px;background:var(--tx2)}
.b .msp{width:100%;height:56px;display:block;border:1px solid var(--line);border-radius:3px;background:var(--pan2)}
.b .msp .zg{fill:var(--up);opacity:.1}.b .msp .zr{fill:var(--dn);opacity:.1}
.b .msp .ln{fill:none;stroke:var(--tx2);stroke-width:1.6}.b .msp .dot{fill:var(--st)}
.b .kv{display:flex;justify-content:space-between;align-items:center;font-size:13px;color:var(--tx2);border-top:1px solid var(--line);padding-top:8px}
.b .lamp{width:8px;height:8px;border-radius:50%;background:var(--up);display:inline-block;margin-inline-end:6px;vertical-align:middle}
.b table{width:100%;border-collapse:collapse}
.b th{font-size:12px;font-weight:500;color:var(--mute);text-align:right;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
.b td{padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap;vertical-align:middle;font-size:14px}
.b tr:last-child td{border-bottom:0}
.b .tsym{font-weight:700;font-family:'IBM Plex Mono',monospace;font-size:15px;color:var(--tx);display:inline-flex;align-items:center;min-height:24px}
.b .tsym:hover{color:var(--lk)}
.b .rank{font-size:12px;color:var(--mute);font-family:'IBM Plex Mono',monospace;margin-inline-end:8px}
.b .sp{width:130px;height:30px;display:block;direction:ltr}
.b .sp .ar{fill:var(--tx2);opacity:.07}.b .sp .ln{fill:none;stroke:var(--tx);stroke-width:1.3}
.b .sp .lv{stroke-width:1;stroke-dasharray:2 3}.b .sp .lo{stroke:var(--dn)}.b .sp .hi{stroke:var(--up)}
.b .rng{position:relative;width:110px;height:6px;background:var(--bar);border-radius:3px;direction:ltr}
.b .rng b{position:absolute;top:-3px;width:3px;height:12px;background:var(--tx);border-radius:1px}
.b .rd{display:inline-block;width:8px;height:8px;margin-inline-end:3px;border:1.5px solid var(--mute);border-radius:1px;vertical-align:middle}
.b .rd.w{background:var(--up);border-color:var(--up)}
.b .led{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:1px solid var(--line)}
.b .led > div{padding:9px 14px;border-inline-start:1px solid var(--line);font-size:13px;display:flex;justify-content:space-between;gap:8px}
.b .led > div:first-child{border-inline-start:0}
.b .cal{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))}
.b .cal > div{padding:12px 14px;border-inline-start:1px solid var(--line);display:flex;flex-direction:column;gap:5px}
.b .cal > div:first-child{border-inline-start:0}
.b .cal .d{font-size:12px;color:var(--mute);display:flex;gap:8px;align-items:center}
.b .cal .d b{color:var(--tx);font-weight:600}
.b .cal .e{font-size:15px;font-weight:500}
.b .li{display:grid;grid-template-columns:20px minmax(0,1fr);gap:8px;padding:9px 14px;border-top:1px solid var(--line);line-height:1.5;font-size:15px}
.b .li:first-child{border-top:0}
.b .li .n{color:var(--mute);font-size:13px;padding-top:2px}
.b .fl{display:grid;grid-template-columns:44px 110px minmax(0,1fr);gap:10px;padding:8px 14px;border-top:1px solid var(--line);font-size:13px;line-height:1.45}
.b .fl:first-child{border-top:0}
.b .en{direction:ltr;text-align:left;unicode-bidi:isolate}
.b .db{display:grid;grid-template-columns:96px minmax(0,1fr) 56px;gap:8px;align-items:center;padding:4px 0;font-size:13px}
.b .db .t{position:relative;height:10px;direction:ltr}
.b .db .t::before{content:"";position:absolute;top:-3px;bottom:-3px;left:50%;width:1px;background:var(--line)}
.b .db .t i{position:absolute;top:0;height:10px;border-radius:1px}
.b .wr{display:flex;justify-content:space-between;padding:6px 0;border-top:1px solid var(--line);font-size:13px}
.b .wr:first-child{border-top:0}
.b .stt{width:7px;height:7px;border-radius:50%;display:inline-block;margin-inline-end:6px;background:var(--bar);border:1px solid var(--mute)}
.b .stt.on{background:var(--up);border-color:var(--up)}
.b .bt{display:flex;flex-direction:column;gap:4px;padding:6px 0;border-top:1px solid var(--line)}
.b .bt:first-child{border-top:0}
.b .bt .bar{height:6px;background:var(--bar);border-radius:1px;direction:ltr}
.b .bt .bar i{display:block;height:6px;background:var(--tx2);border-radius:1px}
.b .ev{display:grid;grid-template-columns:1fr 1fr;gap:0}
.b .ev > div{padding:14px;border-inline-start:1px solid var(--line);display:flex;flex-direction:column;gap:10px}
.b .ev > div:first-child{border-inline-start:0}
.b .ev h3{margin:0;font-size:15px;font-weight:600;display:flex;align-items:center;gap:8px}
.b .mrow{display:grid;grid-template-columns:minmax(0,1fr) 70px 70px;gap:8px;font-size:13px;padding:5px 0;border-top:1px solid var(--line)}
.b .mrow:first-of-type{border-top:0}
.b .mrow .n{text-align:right}
.b .prep{border:1px solid var(--line);border-radius:4px;padding:10px 12px;display:flex;flex-direction:column;gap:6px;background:var(--pan2)}
.b .prep .h{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--tx2)}
.b .prep p{font-size:14px;line-height:1.5}
.b .chk{font-size:13px;color:var(--tx2);display:grid;grid-template-columns:auto minmax(0,1fr);gap:6px}
.b .chk i{width:6px;height:6px;border-radius:50%;background:var(--mute);margin-top:8px}
.b.phn .top{height:52px;padding:0 12px;gap:10px}
.b.phn .tabs{height:48px;overflow:hidden;background:var(--pan);border-bottom:1px solid var(--line)}
.b.phn .tabs a{padding:0 11px;white-space:nowrap;min-height:48px}
.b.phn h1{font-size:22px}
.b.phn .kpis{grid-template-columns:repeat(3,minmax(0,1fr))}
.b.phn .kpis > div{padding:8px}
.b.phn .kpis .v{font-size:17px}
.b .crow{display:grid;grid-template-columns:76px minmax(0,1fr) 92px;gap:10px;align-items:center;padding:8px 12px;border-top:1px solid var(--line);min-height:56px}
.b .crow .sp{width:100%;height:32px}
.b .crow .lv2{font-size:12px;display:flex;justify-content:space-between;gap:6px;direction:ltr}
.b .crow .lv2 small{font-size:12px;color:var(--mute);display:block;font-family:'IBM Plex Sans Hebrew',sans-serif;direction:rtl}
.b .crl{display:flex;align-items:center;gap:8px;padding:0 12px;min-height:48px;border-top:1px solid var(--line);font-size:14px}
.b .crl .e{flex:1 1 auto;min-width:0}
.b .srow{display:flex;align-items:center;gap:10px;padding:0 12px;min-height:48px;border-top:1px solid var(--line);font-size:14px}
.b .srow:first-child{border-top:0}
.b .srow .l{font-weight:600;width:64px;flex:none}
.b .srow .r{flex:1 1 auto;min-width:0;display:flex;gap:12px;flex-wrap:wrap;color:var(--tx2)}
'''

def page(title, body, w, h):
    return f'''<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{FONTS}&amp;display=swap">
<style>{CSS}</style>
</helmet>
{body}
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":{w},"height":{h}}}}}'>
class Component extends DCLogic {{
  renderVals() {{ return {{}}; }}
}}
</script>
</body>
</html>
'''

# ---------- pieces ----------
def pick_spark(p, w=100, h=34):
    vals = list(p['closes']); ext = vals + [v for v in (p['lo'], p['hi']) if v]
    lo, hi = min(ext), max(ext); rng = (hi - lo) or 1; pad = 2
    Y = lambda v: pad + (h - 2 * pad) * (1 - (v - lo) / rng)
    pts = ' '.join(f'{i * w / (len(vals) - 1):.1f},{Y(v):.1f}' for i, v in enumerate(vals))
    lines = ''
    for k, c in (('lo', 'lo'), ('hi', 'hi')):
        if p[k]: lines += f'<line class="lv {c}" x1="0" x2="{w}" y1="{Y(p[k]):.1f}" y2="{Y(p[k]):.1f}" vector-effect="non-scaling-stroke"></line>'
    return (f'<svg class="sp" viewBox="0 0 {w} {h}" preserveAspectRatio="none" role="img" aria-label="{p["sym"]}: 60 ימי מסחר, {p["lo_l"]} {price(p["lo"])}, {p["hi_l"]} {price(p["hi"])}">'
            f'<polygon class="ar" points="0,{h} {pts} {w},{h}"></polygon>{lines}<polyline class="ln" points="{pts}" vector-effect="non-scaling-stroke"></polyline></svg>')

def meter_spark(w=100, h=30):
    vals = METER_SERIES; Y = lambda v: h * (1 - v / 100)
    pts = ' '.join(f'{i * w / (len(vals) - 1):.1f},{Y(v):.1f}' for i, v in enumerate(vals))
    return (f'<svg class="msp" viewBox="0 0 {w} {h}" preserveAspectRatio="none" role="img" aria-label="המד ב-30 ימי המסחר האחרונים, מ-{vals[0]} ל-{vals[-1]}">'
            f'<rect class="zg" x="0" y="0" width="{w}" height="{Y(66):.1f}"></rect><rect class="zr" x="0" y="{Y(45):.1f}" width="{w}" height="{h - Y(45):.1f}"></rect>'
            f'<polyline class="ln" points="{pts}" vector-effect="non-scaling-stroke"></polyline><circle class="dot" cx="{w}" cy="{Y(vals[-1]):.1f}" r="1.8"></circle></svg>')

def dots(rec): return ''.join(f'<i class="rd{" w" if d else ""}"></i>' for d in rec.get('dots', []))

TICKER = TICKER[:7] + [('ביטקוין', f"{W['btc']['price']:,.0f}", W['btc']['chg'])]
def quotes(items=TICKER):
    return '<div class="quotes">' + ''.join(f'<div><span class="l">{lab}</span><span class="v">{n(val) if val else ""}{pct(c)}</span></div>' for lab, val, c in items) + '</div>'

def cm(label, v):
    return f'<div class="cm"><span class="mute">{label}</span><div class="bar"><i style="width:{v}%"></i></div>{n(v)}</div>'

def rng(p):
    pos = max(0, min(100, (p['price'] - p['lo']) / (p['hi'] - p['lo']) * 100))
    return f'<div class="rng" role="img" aria-label="המחיר ב-{pos:.0f}% מהדרך בין {p["lo_l"]} ל{p["hi_l"]}"><b style="left:calc({pos:.0f}% - 1px)"></b></div>'

def row(i, p):
    return f'''<tr><td><a href="#" class="tsym"><span class="rank">{i}</span>{p['sym']}</a><div class="mute" style="font-size:12px;max-width:160px;overflow:hidden;text-overflow:ellipsis">{p['name'] or '&nbsp;'}</div></td>
<td>{n(price(p['price']))}</td><td>{pct(p['chg'])}</td><td>{pick_spark(p)}</td>
<td><span class="dn">{n(price(p['lo']))}</span><div class="mute" style="font-size:12px">{p['lo_l']}</div></td>
<td>{rng(p)}</td>
<td><span class="up">{n(price(p['hi']))}</span><div class="mute" style="font-size:12px">{p['hi_l']}</div></td>
<td>{''.join(f'<span class="tag" style="margin-inline-end:4px">{t}</span>' for t in p['src'].split(' + '))}</td>
<td>{dots(p['rec'])}<div class="mute" style="font-size:12px">{sum(p['rec'].get('dots', []))} מתוך {p['rec'].get('n', 0)} עלו</div></td></tr>'''

def dbar(name, v, mx=3):
    w = min(abs(v) / mx * 50, 50)
    pos = f'left:50%' if v > 0 else f'left:calc(50% - {w:.1f}%)'
    col = 'var(--up)' if v > 0 else 'var(--dn)'
    return f'<div class="db"><span>{name}</span><div class="t" role="img" aria-label="{name} {sgn(v)}% מול S&P"><i style="{pos};width:{w:.1f}%;background:{col}"></i></div>{pct(v)}</div>'

def header(session, extra='', dark=False):
    tabs = ''.join(f'<a href="#"{" aria-current=\"page\"" if i == 0 else ""}>{t}</a>' for i, t in enumerate(TABS))
    return f'''<header class="top"><div class="logo"><i></i>The Daily Edge</div>
<nav class="tabs" aria-label="ניווט ראשי">{tabs}</nav>
<button class="srch" type="button" aria-label="חיפוש טיקר או נושא">{ICON_SEARCH}<span>טיקר או נושא</span><kbd>/</kbd></button>
<button class="ibtn" type="button" aria-label="{'מצב בהיר' if dark else 'מצב כהה'}">{ICON_MOON}</button>
<div class="sess">{session}{extra}</div>
</header>'''

def market_panel(span=8):
    spx = last['chg'] if 'chg' in last else -0.47
    return f'''<section class="pan" style="grid-column:span {span}">
<div class="ph"><h2>מצב השוק · סגירת חמישי {ddmm(ind['date'])}</h2><a href="#" class="go">הניתוח המלא</a></div>
<div class="pb" style="flex:1">
<h1>{HEADLINE}</h1>
<p class="dek">{DEK}</p>
<div class="kpis">
<div><div class="l">S&amp;P 500</div><div class="v dn">{sgn(-0.47)}%</div><div class="s">{n(f"{ev['spxPrice']:,.2f}")}</div></div>
<div><div class="l">שוויוני (המניה הממוצעת)</div><div class="v up">+0.60%</div><div class="s">מול S&amp;P ב-20 יום: {pct(ev['eqSpx20'])}</div></div>
<div><div class="l">עלו / ירדו</div><div class="v">345/156</div><div class="ad" role="img" aria-label="69% עלו"><i style="width:69%;background:var(--up)"></i><i style="width:31%;background:var(--dn)"></i></div></div>
<div><div class="l">VIX</div><div class="v">{ev['vix']:.2f}</div><div class="s"><span class="lamp"></span>רמזור ירוק · מתחת לממוצע 50</div></div>
</div>
<div class="sig">
<div><b>הכסף הגדול באופציות</b>{fl['deltaLabel']} (ציון {n(SCORES['flow'])}) · יום {n(fl['streak'])} ברצף · פוזיציות חדשות {fl['openLabel']}</div>
<div><b>רוחב השוק</b>{n(ev['nhCount'])} שיאים מול {n(ev['nlCount'])} שפלים · {n(f"{ev['pctMa200']:.0f}%")} מהמניות מעל ממוצע 200</div>
<div><b>לחץ מכירות</b>{ro['evidenceLine']}</div>
</div>
</div></section>'''

def meter_panel(span=4):
    s = SCORES
    return f'''<section class="pan" style="grid-column:span {span}">
<div class="ph"><h2>The Edge Meter</h2><span class="mute" style="font-weight:400">סגירת חמישי · {ddmm(ind['date'])}</span></div>
<div class="pb">
<div class="score"><span class="big">{s['combined']}</span><span class="st" style="font-size:20px;font-weight:700">זהיר</span><span class="mute" style="margin-inline-start:auto;font-size:13px">אתמול: {n(prev['combined'])}</span></div>
<div class="seg" role="img" aria-label="ציון {s['combined']} מתוך 100, אזור זהיר"><i style="background:var(--dn)"></i><i style="background:var(--stfill)"></i><i style="background:var(--up)"></i><b style="left:calc({s['combined']}% - 1px)"></b></div>
<div class="segl"><span>הגנתי · עד 44</span><span>זהיר · 45–65</span><span>חיובי · מ-66</span></div>
{cm('טכני', s['tech'])}{cm('רוחב', s['breadth'])}{cm('אופציות', s['flow'])}
{meter_spark()}
<div class="kv"><span>ימי מכירה רחבה</span><span>{n(4)} מתוך {n(25)} ימים · הסף {n(4)}</span></div>
</div></section>'''

def cal_panel():
    cpi = [e for e in ec if e['ilDate'] == '14.10'][0]; ppi = [e for e in ec if e['ilDate'] == '15.10'][0]
    return f'''<section class="pan" style="grid-column:span 12">
<div class="ph"><h2>היומן</h2><span class="mute" style="font-weight:400">שעון ישראל</span><a href="#" class="go">היומן המלא</a></div>
<div class="cal">
<div><span class="d"><b>היום · שישי {n('9.10')}</b></span><span class="e"><span class="tag earn">דוחות</span> <b class="ltr">DAL</b> לפני הפתיחה · <b class="ltr">PGR</b></span><span class="mute" style="font-size:13px">אין נתוני מאקרו מתוזמנים</span></div>
<div><span class="d">שני {n('13.10')} · לפני הפתיחה</span><span class="e"><span class="tag earn">עונת הדוחות נפתחת</span> הבנקים</span><span class="mute ltr" style="font-size:13px;text-align:right">JPM · WFC · C · GS · UNH · JNJ</span></div>
<div><span class="d">שלישי {n('14.10')} · {n(cpi['ilTime'])}</span><span class="e"><span class="tag macro">מאקרו</span> {cpi['he']}</span><span class="mute" style="font-size:13px">צפי {n(cpi['forecast'])} · קודם {n(cpi['previous'])} · קאלשי: {n('88%')} שהשנתי יישאר מעל {n('3.5%')}</span></div>
<div><span class="d">רביעי {n('15.10')} · {n(ppi['ilTime'])}</span><span class="e"><span class="tag macro">מאקרו</span> {ppi['he']}</span><span class="mute" style="font-size:13px">צפי {n(ppi['forecast'])} · קודם {n(ppi['previous'])}</span></div>
</div></section>'''

def picks_panel():
    g = GATE
    eds = [(e['date'], e['avg']['5']['excess']) for e in EDITIONS if e.get('avg', {}).get('5')][-3:]
    led_cells = ''.join(f'<div><span class="mute">מהדורת {ddmm(d)} · 5 ימים</span><span>{pct(x)} <span class="mute">מול S&amp;P</span></span></div>' for d, x in eds)
    led_cells += f'<div><span class="mute">מהדורת {ddmm(LASTED["date"])} · יום {n(LASTED["cur"]["day"])}</span><span>{pct(LASTED["cur"]["excess"])} <span class="mute">מול S&amp;P</span></span></div>'
    return f'''<section class="pan" style="grid-column:span 12">
<div class="ph"><h2>הנבחרות · אישור מחיר לקנייה · מהדורת {ddmm(pk['date'])}</h2><span class="pill state">השוק {g['label']} · עד {n(g['maxPos'])} פוזיציות · {g['sizing']} גודל</span><a href="#" class="go">כל {n(len(PICKS))} הנבחרות והיומן</a></div>
<table><caption style="position:absolute;clip:rect(0 0 0 0)">הנבחרות של מהדורת {ddmm(pk['date'])}</caption><thead><tr><th scope="col">מניה</th><th scope="col">מחיר</th><th scope="col">יום</th><th scope="col">60 יום</th><th scope="col">סטופ / תמיכה</th><th scope="col">מיקום בטווח</th><th scope="col">יעד / התנגדות</th><th scope="col">מקור</th><th scope="col">רקורד</th></tr></thead>
<tbody>{''.join(row(i + 1, p) for i, p in enumerate(TOP5))}</tbody></table>
<div class="led">{led_cells}</div></section>'''

def brief_panel(span=6, k=4):
    return f'''<section class="pan" style="grid-column:span {span}"><div class="ph"><h2>התדרוך · {n('06:01')}</h2><a href="#" class="go">התדרוך המלא</a></div>
<div>{''.join(f'<div class="li"><span class="n">{i + 1}</span><span>{h}</span></div>' for i, h in enumerate(BRIEF[:k]))}</div></section>'''

def pulse_panel(span=6, k=4):
    return f'''<section class="pan" style="grid-column:span {span}"><div class="ph"><h2>בזק מהרשת</h2><a href="#" class="go">כל הבזקים</a></div>
<div>{''.join(f'<div class="fl"><span class="n mute">{t}</span><span class="ltr mute" style="text-align:right">{s_}</span><span class="en">{x.replace(" $MACRO", "")}</span></div>' for s_, t, x in PULSE[:k])}</div></section>'''

def around_row():
    return f'''<section class="pan" style="grid-column:span 4"><div class="ph"><h2>סקטורים · 5 ימים מול S&amp;P</h2><a href="#" class="go">השוק</a></div>
<div class="pb" style="gap:2px">{''.join(dbar(a, v) for a, v in SECT_TOP + SECT_BOT[::-1])}</div></section>
<section class="pan" style="grid-column:span 4"><div class="ph"><h2>העולם</h2><a href="#" class="go">העולם</a></div>
<div class="pb" style="gap:0">{''.join(f'<div class="wr"><span><i class="stt{" on" if st == "נסחר" else ""}"></i>{a} <span class="mute" style="font-size:12px">{st}</span></span>{pct(c)}</div>' for a, c, st in WORLD)}</div></section>
<section class="pan" style="grid-column:span 4"><div class="ph"><h2>מה השווקים מהמרים</h2><a href="#" class="go">כל ההימורים</a></div>
<div class="pb" style="gap:0">{''.join(f'<div class="bt"><div style="display:flex;justify-content:space-between;gap:8px"><span>{a}: <b>{b}</b></span>{n(str(c) + "%")}</div><div class="bar" role="img" aria-label="{c}%"><i style="width:{c}%"></i></div></div>' for a, b, c, d in BETS)}</div></section>'''

# ---------- desktop ----------
def desktop(dark=False):
    body = f'''<div class="b{' dark' if dark else ''}" dir="rtl" style="width:1280px;min-height:1600px">
{header(f'<span class="pill">טרום מסחר</span><span>פתיחה בעוד {n("3:32")}</span><span class="mute">IL {n("12:58")} · NY {n("05:58")}</span>', dark=dark)}
{quotes()}
<main class="grid">
{market_panel()}{meter_panel()}{cal_panel()}{picks_panel()}{brief_panel()}{pulse_panel()}{around_row()}
</main></div>'''
    return page('לוח המסחר · בית · מחשב' + (' · כהה' if dark else ' · בהיר'), body, 1280, 1600)

# ---------- event day (Mon 13.10: banks before the open; CPI tomorrow) ----------
def event_day(dark=False):
    cpi = [e for e in ec if e['ilDate'] == '14.10']
    cons = eval(ep['consensus']) if isinstance(ep['consensus'], str) else ep['consensus']
    opt = eval(ep['options']) if isinstance(ep['options'], str) else ep['options']
    checks = eval(pn['checks']) if isinstance(pn['checks'], str) else pn['checks']
    hist_ = eval(ep['history']) if isinstance(ep['history'], str) else ep['history']
    beats = sum(1 for h in hist_ if h['surprise'] > 0)
    mrows = ''.join(f'<div class="mrow"><span>{e["he"]}</span>{n(e["forecast"] or "—")}{n(e["previous"] or "—")}</div>' for e in cpi)
    event = f'''<section class="pan" style="grid-column:span 8;border-color:var(--stfill)">
<div class="ph"><h2>היום · שני {n('13.10')} · יום אירוע</h2><span class="tag earn">עונת הדוחות נפתחת</span><span class="tag macro">מחר {n('15:30')} CPI</span><a href="#" class="go">היומן המלא</a></div>
<div class="ev">
<div>
<h3><span class="tag earn">לפני הפתיחה</span>הבנקים פותחים את העונה</h3>
<div style="display:flex;gap:6px;flex-wrap:wrap"><span class="tag">JPM</span><span class="tag">WFC</span><span class="tag">C</span><span class="tag">GS</span><span class="tag">UNH</span><span class="tag">JNJ</span><span class="tag">DPZ</span></div>
<div class="prep">
<div class="h"><b class="ltr" style="font-family:'IBM Plex Mono',monospace;font-size:15px;color:var(--tx)">JPM</b><span>לקראת הדוח · צפי רווח {n(f"${cons['eps']:.2f}")} למניה (לפני שנה {n(f"${cons['epsYearAgo']:.2f}")}) · האופציות מתמחרות {n(f"±{opt['earn']:.1f}%")} · עקפה {n(beats)} מ-{n(len(hist_))} הדוחות האחרונים</span></div>
<p>{pn['thesis']}</p>
{''.join(f'<div class="chk"><i></i><span><b>{c["title"]}</b> — {c["text"]}</span></div>' for c in checks[:2])}
<a href="#" style="font-size:13px;min-height:24px;display:inline-flex;align-items:center">ההכנה המלאה ל-JPM</a>
</div>
</div>
<div>
<h3><span class="tag macro">מחר · {n('15:30')}</span>אינפלציה — ספטמבר</h3>
<div><div class="mrow" style="color:var(--mute);font-size:12px;border-top:0"><span>נתון</span><span class="n">צפי</span><span class="n">קודם</span></div>{mrows}</div>
<div style="font-size:13px;color:var(--tx2);border-top:1px solid var(--line);padding-top:8px">השווקים מהמרים (קאלשי): {n('88%')} שהאינפלציה השנתית תישאר מעל {n('3.5%')} — קפיצה של {n(10)} נקודות מאתמול.</div>
<div style="font-size:13px;color:var(--tx2)">אחר כך השבוע: רביעי {n('15:30')} PPI · חמישי BAC, MS, TSM, ASML.</div>
</div>
</div></section>'''
    body = f'''<div class="b{' dark' if dark else ''}" dir="rtl" style="width:1280px;min-height:1700px">
{header(f'<span class="pill">לפני פתיחה</span><span>פתיחה בעוד {n("8:50")}</span><span class="mute">IL {n("07:40")} · NY {n("00:40")}</span>', dark=dark)}
{quotes()}
<main class="grid">
{event}{meter_panel()}
{market_panel(12).replace('<h1>', '<h1 style="font-size:24px">')}
{picks_panel()}{brief_panel()}{pulse_panel()}{around_row()}
</main></div>'''
    return page('לוח המסחר · בית · יום אירוע', body, 1280, 1700)

# ---------- phone ----------
def phone(dark=False):
    s = SCORES; g = GATE
    cards = ''
    for p in TOP5[:4]:
        cards += f'''<a href="#" class="crow" style="color:inherit;text-decoration:none"><div><span class="tsym">{p['sym']}</span><div>{pct(p['chg'])}</div></div>
{pick_spark(p)}
<div class="lv2"><span><small>{p['lo_l']}</small><span class="n dn">{price(p['lo'])}</span></span><span><small>{p['hi_l']}</small><span class="n up">{price(p['hi'])}</span></span></div></a>'''
    eds = [(e['date'], e['avg']['5']['excess']) for e in EDITIONS if e.get('avg', {}).get('5')][-1]
    cpi = [e for e in ec if e['ilDate'] == '14.10'][0]
    body = f'''<div class="b phn{' dark' if dark else ''}" dir="rtl" style="width:390px;min-height:1640px">
<header class="top"><div class="logo" style="flex-grow:1"><i></i>The Daily Edge</div><span class="pill">טרום מסחר · {n('3:32')}</span>
<button class="ibtn" type="button" aria-label="חיפוש" style="width:44px;height:44px">{ICON_SEARCH}</button></header>
<nav class="tabs" aria-label="ניווט ראשי">{''.join(f'<a href="#"{" aria-current=\"page\"" if i == 0 else ""}>{t}</a>' for i, t in enumerate(TABS))}</nav>
<div class="quotes" style="grid-template-columns:repeat(3,minmax(0,1fr))">{''.join(f'<div style="padding:6px 10px"><span class="l">{l}</span><span class="v" style="font-size:13px">{n(v) if v else ""}{pct(c)}</span></div>' for l, v, c in TICKER[:3])}</div>
<main style="padding:12px;display:flex;flex-direction:column;gap:10px">
<section class="pan"><div class="ph"><h2>מצב השוק · סגירת חמישי {ddmm(ind['date'])}</h2><a href="#" class="go">הניתוח</a></div><div class="pb">
<h1>{HEADLINE}</h1>
<div class="kpis">
<div><div class="l">S&amp;P 500</div><div class="v dn">{sgn(-0.47)}%</div></div>
<div><div class="l">שוויוני</div><div class="v up">+0.60%</div></div>
<div><div class="l">VIX</div><div class="v">{ev['vix']:.2f}</div><div class="s"><span class="lamp"></span>ירוק</div></div></div>
<div style="display:grid;grid-template-columns:auto minmax(0,1fr);gap:14px;align-items:center;border-top:1px solid var(--line);padding-top:10px">
<div class="score"><span class="big" style="font-size:44px">{s['combined']}</span><span class="st" style="font-size:17px;font-weight:700">זהיר</span></div>
<div style="display:flex;flex-direction:column;gap:4px">{cm('טכני', s['tech'])}{cm('רוחב', s['breadth'])}{cm('אופציות', s['flow'])}</div></div>
</div></section>
<section class="pan"><div class="ph"><h2>היומן</h2><a href="#" class="go">היומן המלא</a></div>
<div class="crl" style="border-top:0"><span class="tag earn">היום</span><span class="e"><b class="ltr">DAL</b> לפני הפתיחה · <b class="ltr">PGR</b></span></div>
<div class="crl"><span class="tag earn">שני {n('13.10')}</span><span class="e">הבנקים פותחים את העונה</span></div>
<div class="crl"><span class="tag macro">שלישי {n('14.10')} · {n('15:30')}</span><span class="e">CPI ליבה · צפי {n(cpi['forecast'])}</span></div></section>
<section class="pan"><div class="ph"><h2>הנבחרות · מהדורת {ddmm(pk['date'])}</h2><span class="pill state">{g['label']} · עד {n(g['maxPos'])}</span><a href="#" class="go">כל {n(len(PICKS))}</a></div>
{cards}
<div class="led" style="grid-template-columns:1fr"><div><span class="mute">מהדורת {ddmm(eds[0])} אחרי 5 ימים</span><span>{pct(eds[1])} <span class="mute">מול S&amp;P</span></span></div></div></section>
<section class="pan"><div class="ph"><h2>התדרוך · {n('06:01')}</h2><a href="#" class="go">המלא</a></div>
<div>{''.join(f'<div class="li" style="font-size:14px"><span class="n">{i + 1}</span><span>{h}</span></div>' for i, h in enumerate(BRIEF[:3]))}</div></section>
<section class="pan"><div class="ph"><h2>בזק מהרשת</h2><a href="#" class="go">הכל</a></div>
<div>{''.join(f'<div class="fl" style="grid-template-columns:44px minmax(0,1fr)"><span class="n mute">{t}</span><span class="en">{x.replace(" $MACRO", "")}</span></div>' for s_, t, x in PULSE[:2])}</div></section>
<section class="pan">
<a href="#" class="srow" style="color:inherit"><span class="l">סקטורים</span><span class="r"><span>{SECT_TOP[0][0]} {pct(SECT_TOP[0][1])}</span><span>{SECT_BOT[0][0]} {pct(SECT_BOT[0][1])}</span></span></a>
<a href="#" class="srow" style="color:inherit"><span class="l">העולם</span><span class="r"><span>DAX {pct(WORLD[1][1])}</span><span>FTSE {pct(WORLD[2][1])}</span><span>ת"א {n('125')} {pct(WORLD[0][1])}</span></span></a>
<a href="#" class="srow" style="color:inherit"><span class="l">הימורים</span><span class="r"><span>הפד ללא שינוי {n('84%')}</span><span>CPI מעל {n('3.5%')}: {n('88%')}</span></span></a>
</section></main></div>'''
    return page('לוח המסחר · בית · טלפון' + (' · כהה' if dark else ' · בהיר'), body, 390, 1640)

BOARDS = [
    ('Main.dc.html', 'בית · מחשב · בהיר', desktop(False), 1280, 1600, 0, 0),
    ('Desktop_dark.dc.html', 'בית · מחשב · כהה', desktop(True), 1280, 1600, 1360, 0),
    ('Event_day.dc.html', 'בית ביום אירוע · שני 13.10 · הבנקים (+CPI מחר)', event_day(False), 1280, 1700, 2720, 0),
    ('Phone_light.dc.html', 'בית · טלפון · בהיר', phone(False), 390, 1640, 0, 1920),
    ('Phone_dark.dc.html', 'בית · טלפון · כהה', phone(True), 390, 1640, 470, 1920),
]

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'out'
    os.makedirs(out + '/project', exist_ok=True); os.makedirs(out + '/prev', exist_ok=True)
    idx = {"v": 3, "createdOnFiles": {"v": 1, "at": datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},
           "title": "The Daily Edge · שלב 4ב · לוח המסחר מלוטש", "launch": {"view": "canvas"}, "pages": [],
           "boards": {}, "order": [], "designSystems": [],
           "notes": {"r1": {"x": 0, "y": -240, "text": "מחשב 1280 — יום רגיל (בהיר · כהה) ויום אירוע", "kind": "title1", "maxW": 4000},
                     "r2": {"x": 0, "y": 1680, "text": "טלפון 390 — בהיר · כהה", "kind": "title1", "maxW": 1200}}}
    for name, title, html, w, h, x, y in BOARDS:
        idx['boards'][name] = {"x": x, "y": y, "w": w, "h": h, "title": title}
        idx['order'].append(name)
        open(f'{out}/project/{name}', 'w').write(html)
        hel = re.search(r'<helmet>(.*?)</helmet>', html, re.S).group(1)
        body = re.search(r'</helmet>(.*?)</x-dc>', html, re.S).group(1)
        open(f'{out}/prev/{name.replace(".dc.html", ".html")}', 'w').write(f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">{hel}</head><body>{body}</body></html>')
        print(name, len(html))
    json.dump(idx, open(f'{out}/project/canvas.json', 'w'), ensure_ascii=False, indent=1)
