const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  for (const f of process.argv.slice(2)) {
    const w = f.includes('Phone') ? 390 : 1280;
    const p = await b.newPage({ viewport: { width: w, height: 900 } });
    await p.goto('file://' + process.cwd() + '/out/prev/' + f);
    await p.waitForTimeout(2500);
    const h = await p.evaluate(() => document.body.firstElementChild.scrollHeight);
    const sw = await p.evaluate(() => document.documentElement.scrollWidth);
    const info = await p.evaluate(() => {
      const fs = {}; const small=[];
      document.querySelectorAll('*').forEach(e => { if(e.children.length===0 && e.textContent.trim()){ const f=parseFloat(getComputedStyle(e).fontSize); fs[f]=(fs[f]||0)+1; } });
      document.querySelectorAll('a,button').forEach(e=>{const r=e.getBoundingClientRect(); if(r.width&&(r.height<24||r.width<24)) small.push(e.textContent.trim().slice(0,16)+' '+Math.round(r.width)+'x'+Math.round(r.height));});
      return {fs, small: small.slice(0,12), nsmall: small.length};
    });
    console.log(f, 'height', h, 'scrollW', sw, JSON.stringify(info));
    await p.screenshot({ path: 'out/prev/' + f.replace('.html', '.png'), fullPage: true });
  }
  await b.close();
})();
