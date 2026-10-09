# Real data from /home/user/nidam-markets/data (snapshot 9.10.2026 ~13:00 IL)
import json, os
R = '/home/user/nidam-markets/data/'
def L(f): return json.load(open(R + f))

ca = L('claude_analysis.json'); ind = L('indices.json'); mk = L('market.json')
pk = L('picks.json'); led = L('picks_ledger.json'); br = L('briefing.json')
pu = L('pulse.json'); hist = L('history.json'); bets = L('bets.json'); world = L('world.json')

M = {it['key']: it for it in mk['items']}
W = {it['key']: it for it in world['items']}

def sgn(x, d=2):
    s = f'{abs(x):,.{d}f}'
    return ('+' if x > 0 else '−' if x < 0 else '') + s

HEADLINE = ca['headline']
DEK = ca['tldr'].split('. ')[0].rstrip('.') + '.'
SCORES = ind['scores']
METER_SERIES = [d.get('combined') for d in hist['days'][-30:]]
SPX = W['spx']; NDX = W['ixic']

TICKER = [  # pre-market Friday: futures + macro
    ('חוזה S&P', f"{M['es']['price']:,.0f}", M['es']['chg']),
    ('חוזה נאסד"ק', f"{M['nq']['price']:,.0f}", M['nq']['chg']),
    ('ראסל (IWM)', f"{M['iwm']['price']:.2f}", M['iwm']['chg']),
    ('VIX', f"{M['vix']['price']:.2f}", M['vix']['chg']),
    ('אג"ח 10Y', f"{M['tnx']['price']:.2f}%", M['tnx']['chg']),
    ('דולר/שקל', f"{M['usdils']['price']:.3f}", M['usdils']['chg']),
    ('DXY', f"{M['dxy']['price']:.1f}", M['dxy']['chg']),
    ('ביטקוין', '', W['btc']['chg']),
]

NAMES = {'STGW': 'Stagwell', 'ECL': 'Ecolab', 'ROKU': 'Roku'}
GRP = {'tech': 'טכנולוגיה', 'health': 'בריאות', 'other': 'אחר'}
PICKS = []
for p in pk['picks']:
    PICKS.append(dict(
        sym=p['sym'], name=(p.get('name') or NAMES.get(p['sym'], '')).replace(' Inc', '').replace(' Corp Cl A', '').replace(' and Company', ''),
        grp=p.get('grp') or 'other', chg=p.get('chg'), price=p['price'],
        lo=p.get('stop') or p.get('sup'), hi=p.get('target') or p.get('res'),
        lo_l='סטופ' if p.get('stop') else 'תמיכה', hi_l='יעד' if p.get('target') else 'התנגדות',
        src=' + '.join(s['t'].split(' #')[0] for s in p['sources']),
        srcsub=' · '.join(s['t'] for s in p['sources']),
        rec=p.get('rec') or {}, closes=p['closes'][-60:], trend=p.get('trendLabel'),
    ))
GATE = pk['gate']
REC = pk['record']
LEDGER = [(e['date'], e['avg']['5']['excess']) for e in led['editions'] if e.get('avg', {}).get('5')]
LAST_ED = [e for e in led['editions'] if e.get('cur')][-1]

BRIEF = json.loads(br['morning']['headlines']) if isinstance(br['morning']['headlines'], str) else br['morning']['headlines']
PULSE = [(i['source'], i['time'], i['text'].split(' @​')[0].replace('🚨', '').replace('👀', '').strip()) for i in pu['items'][:4]]

SECT_HE = {'HC': 'בריאות', 'CS': 'צריכה בסיסית', 'RE': 'נדל"ן', 'IT': 'טכנולוגיה', 'ENE': 'אנרגיה', 'UTL': 'תשתיות',
           'COM': 'תקשורת', 'MAT': 'חומרים', 'CD': 'צריכה מחזורית', 'IND': 'תעשייה', 'FIN': 'פיננסים'}
rs = ind['rotation']['sectorRs']
srt = sorted(rs.items(), key=lambda kv: -kv[1]['rs5'])
SECT_TOP = [(SECT_HE[k], v['rs5']) for k, v in srt[:3]]
SECT_BOT = [(SECT_HE[k], v['rs5']) for k, v in srt[-3:]][::-1]
WORLD = [('ת"א 125', W['ta125']['chg'], 'נסגר'), ('DAX', W['dax']['chg'], 'נסחר'), ('FTSE', W['ftse']['chg'], 'נסחר'),
         ('הנג סנג', W['hsi']['chg'], 'נסגר'), ('קוספי', W['ks11']['chg'], 'נסגר')]
BETS = [(r['label'].split(' · ')[0], r['sub'].replace('ההימור המוביל: ', ''), r['pct'], r.get('chg', 0)) for r in bets['rows'][:3]]

def spark(vals, w=100, h=30, pad=2):
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    pts = []
    for i, v in enumerate(vals):
        x = i * w / (len(vals) - 1)
        y = pad + (h - 2 * pad) * (1 - (v - lo) / rng)
        pts.append(f'{x:.1f},{y:.1f}')
    return ' '.join(pts)

def yof(v, vals, h=30, pad=2):
    lo, hi = min(vals), max(vals)
    return pad + (h - 2 * pad) * (1 - (v - lo) / ((hi - lo) or 1))

if __name__ == '__main__':
    print(HEADLINE, DEK, SCORES, TICKER, GATE, REC, LEDGER, LAST_ED['cur'], SECT_TOP, SECT_BOT, BETS, sep='\n')
    for p in PICKS[:5]: print(p['sym'], p['name'], p['src'], p['lo'], p['hi'])
