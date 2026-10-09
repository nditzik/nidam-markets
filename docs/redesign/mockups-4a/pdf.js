const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const b = await chromium.launch();
  const items = [['A','גרסה א · המהדורה'],['B','גרסה ב · לוח המסחר'],['C','גרסה ג · האפליקציה']];
  const shots = [];
  for (const [k, t] of items) {
    const p = await b.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1.5 });
    await p.goto('file://' + process.cwd() + '/prev/' + k + '_Desktop.html', { waitUntil: 'networkidle' });
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(800);
    const h = await p.evaluate(() => document.body.firstElementChild.scrollHeight);
    const out = '../share/' + k + '_' + t.split(' · ')[1].replace(/ /g,'_') + '_מחשב.png';
    await p.setViewportSize({ width: 1280, height: h }); await p.waitForTimeout(300); await p.screenshot({ path: out, fullPage: true });
    shots.push({ t, h, data: fs.readFileSync(out).toString('base64') });
    console.log(out, h);
  }
  const html = `<!doctype html><html dir="rtl"><head><meta charset="utf-8"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Heebo:wght@500;700&display=swap"><style>
  @page{margin:0} body{margin:0;font-family:Heebo,sans-serif}
  .pg{width:1280px;page-break-after:always;background:#fff}
  .t{height:70px;display:flex;align-items:center;padding:0 40px;font-size:28px;font-weight:700;background:#111;color:#fff}
  .t span{font-weight:500;font-size:16px;opacity:.75;margin-inline-start:auto}
  img{display:block;width:1280px}</style></head><body>` +
  shots.map(s => `<div class="pg"><div class="t">${s.t}<span>The Daily Edge · הצעה לדף הבית · נתונים אמיתיים מ-9.10.2026</span></div><img src="data:image/png;base64,${s.data}"></div>`).join('') + `</body></html>`;
  const p = await b.newPage();
  await p.setContent(html, { waitUntil: 'networkidle' });
  const maxH = Math.max(...shots.map(s => s.h)) + 70;
  await p.pdf({ path: '../share/The_Daily_Edge_שלוש_גרסאות_מחשב.pdf', width: '1280px', height: maxH + 'px', printBackground: true });
  await b.close();
})();
