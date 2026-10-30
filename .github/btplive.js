const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const errs=[];
  for (const [w,scheme] of [[1280,'light'],[375,'dark']]) {
    const p = await b.newPage({ viewport: { width: w, height: 900 }, colorScheme: scheme });
    p.on('pageerror', e => errs.push(e.message)); p.on('console', m => m.type()==='error' && errs.push(m.text()));
    await p.goto('https://francescodimichele666.github.io/bussola-mercati/titoli-di-stato.html'); await p.waitForTimeout(1200);
    const r = async () => ({count: await p.textContent('#btp-count'), rows: await p.$$eval('#btp-table tbody tr', x=>x.length), more: await p.isVisible('#btp-more')});
    console.log(w, 'start', await r());
    await p.selectOption('select[name=famiglia]', 'CCTeu'); console.log('CCTeu', await r(), await p.textContent('#fam-note'));
    await p.selectOption('select[name=famiglia]', ''); await p.selectOption('select[name=durata]', '15-99'); console.log('>15', await r());
    await p.selectOption('select[name=durata]', ''); await p.fill('input[name=q]', 'IT0005547390'); console.log('isin', await r());
    await p.fill('input[name=q]', '2035'); console.log('2035', await r());
    await p.fill('input[name=q]', ''); await p.selectOption('select[name=ordine]', 'cedola'); console.log('top cedola', await p.textContent('#btp-table tbody tr td:nth-child(3)'));
    await p.selectOption('select[name=ordine]', 'scadenza'); console.log('more', await r());
    const sw = await p.evaluate(()=>document.documentElement.scrollWidth); console.log('scrollWidth', sw);
    const sec = await p.$('section[aria-labelledby=btp-title]'); 
  }
  console.log('errors', errs); await b.close();
})();
