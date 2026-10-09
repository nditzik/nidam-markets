import os, re, sys, importlib
os.makedirs('out/project', exist_ok=True); os.makedirs('prev', exist_ok=True)
mods = sys.argv[1:] or ['dir_a','dir_b','dir_c']
for m in mods:
    mod = importlib.import_module(m)
    for kind in ('desktop','phone'):
        html = getattr(mod, kind)()
        name = f"{m[-1].upper()}_{'Desktop' if kind=='desktop' else 'Phone'}.dc.html"
        open('out/project/'+name,'w').write(html)
        # preview: helmet->head, drop x-dc + support.js
        hel = re.search(r'<helmet>(.*?)</helmet>', html, re.S).group(1)
        body = re.search(r'</helmet>(.*?)</x-dc>', html, re.S).group(1)
        open('prev/'+name.replace('.dc',''),'w').write(f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">{hel}</head><body>{body}</body></html>')
        print(name, len(html))
