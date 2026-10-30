const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const errs=[];
 for (const [w,sc] of [[1280,'light'],[375,'dark']]) {
  const p = await b.newPage({ viewport: { width: w, height: 1300 }, colorScheme: sc });
  p.on('pageerror', e => errs.push(e.message));
  await p.goto('https://francescodimichele666.github.io/bussola-mercati/calendario.html'); await p.waitForTimeout(1500);
  console.log(w, await p.textContent('#updated'), '|', await p.textContent('#cal-count'));
  for (const sel of ['#c-vista button[data-v=pubblicati]','#c-imp button[data-v=alta]','#c-paese button[data-v=IT]']) { await p.click(sel); console.log(sel, await p.textContent('#cal-count')); }
  await p.click('#c-vista button[data-v=prossimi]'); await p.click('#c-imp button[data-v=""]'); await p.click('#c-paese button[data-v=""]');

  }
 console.log('errors',errs); await b.close(); })();
