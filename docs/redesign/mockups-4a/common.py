from data import *

LRM = '‎'

def n(t, cls=''):
    return f'<span class="n {cls}">{t}</span>'

def ud(x):
    return 'up' if x > 0 else 'dn' if x < 0 else 'flat'

def pct(x, d=2):
    return n(sgn(x, d) + '%', ud(x))

def ddmm(iso):
    y, m, d = iso[:10].split('-')
    return f'{int(d)}.{int(m)}'

SEARCH_ICON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="M20 20l-3.5-3.5"></path></svg>'

TABS = ['בית', 'השוק', 'היומן', 'מניות', 'חדשות', 'העולם']

def page(title, fonts, css, body, w, h):
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
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{fonts}&amp;display=swap">
<style>
body{{margin:0}}
.n{{direction:ltr;unicode-bidi:isolate;font-variant-numeric:tabular-nums}}
.ltr{{direction:ltr;unicode-bidi:isolate}}
{css}
</style>
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

def pick_spark(p, w=100, h=34, cls='sp'):
    """60-day line + dashed lo/hi levels, all in one viewBox (data-scaled incl. levels)."""
    vals = list(p['closes'])
    ext = vals + [v for v in (p['lo'], p['hi']) if v]
    lo, hi = min(ext), max(ext)
    rng = (hi - lo) or 1
    pad = 2
    def Y(v): return pad + (h - 2 * pad) * (1 - (v - lo) / rng)
    pts = ' '.join(f'{i * w / (len(vals) - 1):.1f},{Y(v):.1f}' for i, v in enumerate(vals))
    area = f'0,{h} ' + pts + f' {w},{h}'
    lines = ''
    if p['lo']: lines += f'<line class="lv lo" x1="0" x2="{w}" y1="{Y(p["lo"]):.1f}" y2="{Y(p["lo"]):.1f}" vector-effect="non-scaling-stroke"></line>'
    if p['hi']: lines += f'<line class="lv hi" x1="0" x2="{w}" y1="{Y(p["hi"]):.1f}" y2="{Y(p["hi"]):.1f}" vector-effect="non-scaling-stroke"></line>'
    return (f'<svg class="{cls}" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-label="60 ימי מסחר">'
            f'<polygon class="ar" points="{area}"></polygon>{lines}'
            f'<polyline class="ln" points="{pts}" vector-effect="non-scaling-stroke"></polyline></svg>')

def meter_spark(w=100, h=30, cls='msp'):
    vals = METER_SERIES
    def Y(v): return h * (1 - v / 100)
    pts = ' '.join(f'{i * w / (len(vals) - 1):.1f},{Y(v):.1f}' for i, v in enumerate(vals))
    return (f'<svg class="{cls}" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-label="המד ב-30 הימים האחרונים">'
            f'<rect class="zg" x="0" y="0" width="{w}" height="{Y(66):.1f}"></rect>'
            f'<rect class="zr" x="0" y="{Y(45):.1f}" width="{w}" height="{h - Y(45):.1f}"></rect>'
            f'<polyline class="ln" points="{pts}" vector-effect="non-scaling-stroke"></polyline>'
            f'<circle class="dot" cx="{w}" cy="{Y(vals[-1]):.1f}" r="1.6"></circle></svg>')

def dots(rec, cls='rd'):
    return ''.join(f'<i class="{cls} {"w" if d else "l"}"></i>' for d in rec.get('dots', []))

def rec_text(rec):
    k = sum(rec.get('dots', []))
    return f'בעבר: {k} מתוך {rec.get("n", 0)} עלו'

def fmt_price(v):
    return f'{v:,.2f}'

TOP5 = PICKS[:5]
MORE = len(PICKS) - 5
LEDGER_TXT = ' · '.join(f'{ddmm(d)} {sgn(x)}%' for d, x in LEDGER)
