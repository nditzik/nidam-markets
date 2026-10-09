const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  for (const f of process.argv.slice(2)) {
    const w = f.includes('Phone') ? 390 : 1280;
    const p = await b.newPage({ viewport: { width: w, height: 900 } });
    await p.goto('file://' + process.cwd() + '/prev/' + f);
    await p.waitForTimeout(1500);
    const h = await p.evaluate(() => document.body.firstElementChild.scrollHeight);
    const sw = await p.evaluate(() => document.documentElement.scrollWidth);
    console.log(f, 'height', h, 'scrollW', sw);
    await p.screenshot({ path: 'prev/' + f.replace('.html', '.png'), fullPage: true });
  }
  await b.close();
})();
