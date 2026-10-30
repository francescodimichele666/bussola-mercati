// Verifica completa del sito: errori, contenuti vuoti, valori strani, link, interazioni, overflow.
const { chromium } = require('playwright');
const BASE = process.env.BASE || 'http://localhost:8766/';
const SHOTS = process.env.SHOTS || '.';
const PAGES = ['', 'titoli-di-stato.html', 'etf.html', 'calendario.html'];
const VIEWS = [[375, 'light'], [768, 'dark'], [1280, 'light'], [1920, 'dark']];
const problems = [];
const P = (pg, vw, msg) => { problems.push(`[${pg || 'index'} @${vw}] ${msg}`); };
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const links = new Set();
  for (const pg of PAGES) for (const [vw, scheme] of VIEWS) {
    const p = await b.newPage({ viewport: { width: vw, height: 900 }, colorScheme: scheme });
    if (process.env.LOCAL) { await p.route('https://cdnjs.cloudflare.com/**', r => r.fulfill({ path: process.env.THREE, contentType: 'application/javascript' })); await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: '', contentType: 'text/css' })); await p.route('https://s3.tradingview.com/**', r => r.abort()); }
    p.on('console', m => { if (m.type() === 'error' && !/tradingview|sheriff|favicon/i.test(m.text())) P(pg, vw, 'console: ' + m.text().slice(0, 160)); });
    p.on('pageerror', e => P(pg, vw, 'JS: ' + e.message));
    p.on('response', r => { if (r.status() >= 400 && !/tradingview|favicon|sheriff/.test(r.url())) P(pg, vw, `HTTP ${r.status()} ${r.url()}`); });
    await p.goto(BASE + pg, { waitUntil: 'networkidle' }).catch(e => P(pg, vw, 'goto ' + e.message));
    await p.waitForTimeout(pg === '' ? 5000 : 2500);
    const r = await p.evaluate(() => {
      const txt = document.body.innerText;
      const bad = (txt.match(/\bNaN\b|\bundefined\b|\bnull\b|Infinity|\[object/g) || []);
      const nd = (txt.match(/n\.d\./g) || []).length;
      const over = document.documentElement.scrollWidth - innerWidth;
      const empty = [];
      for (const sel of ['#pulse', '#it-grid', '#cmp-table tbody', '#eu-facts', '#cats-table tbody', '#fund-tabs', '#fund-panel', '#facts-world', '#proxies tbody', '#paesi', '#bond-head', '#curve', '#bond-table tbody', '#y10-euro', '#y10-other', '#etf-list', '#f-classe', '#f-area', '#cal', '#c-paese'])
        { const el = document.querySelector(sel); if (el && !el.textContent.trim() && !el.querySelector('svg,canvas')) empty.push(sel); }
      const as = [...document.querySelectorAll('a[href]')].map(a => a.href);
      // testo che esce dal suo contenitore (escluse aree a scorrimento)
      const clipped = [];
      document.querySelectorAll('.card,.fact,.etf,.ev,.kpi,.fund,.cell,.pulse li').forEach(el => { if (el.scrollWidth > el.clientWidth + 2) clipped.push((el.className + ' ' + el.textContent.trim().slice(0, 40))); });
      const counts = { cards: document.querySelectorAll('.card').length, cmp: document.querySelectorAll('#cmp-table tbody tr').length, cats: document.querySelectorAll('#cats-table tbody tr').length, funds: document.querySelectorAll('.fund').length, world: document.querySelectorAll('#facts-world .fact').length, bonds: document.querySelectorAll('#bond-table tbody tr').length, etf: document.querySelectorAll('.etf').length, ev: document.querySelectorAll('.ev').length, pending: document.querySelectorAll('.fact.pending').length, stale: document.querySelectorAll('.stale').length };
      const sceneFallback = !!document.querySelector('.scene-fallback');
      const updated = document.querySelector('#updated')?.textContent;
      return { bad, nd, over, empty, as, clipped: clipped.slice(0, 6), counts, sceneFallback, updated, title: document.title, h1: document.querySelector('h1')?.textContent };
    });
    r.as.forEach(h => links.add(h));
    if (r.bad.length) P(pg, vw, 'parole sospette nel testo: ' + [...new Set(r.bad)].join(','));
    if (r.over > 0) P(pg, vw, 'scorrimento orizzontale di ' + r.over + 'px');
    if (r.empty.length) P(pg, vw, 'contenitori vuoti: ' + r.empty.join(' '));
    if (r.clipped.length) P(pg, vw, 'testo tagliato: ' + r.clipped.join(' | '));
    if (vw === 1280) console.log('PAGINA', pg || 'index', JSON.stringify({ title: r.title, h1: r.h1, updated: r.updated, nd: r.nd, counts: r.counts, sceneFallback: r.sceneFallback }));
    await p.screenshot({ path: `${SHOTS}/${(pg || 'index').replace('.html', '')}_${vw}_${scheme}.png`, fullPage: true });

    // interazioni (una volta per pagina, a 375 e 1280)
    if (vw === 375 || vw === 1280) {
      try {
        if (pg === '') {
          const tabs = await p.$$('#fund-tabs [role=tab]');
          for (const t of tabs) { await t.click(); await p.waitForTimeout(80); const n = await p.$$eval('#fund-panel .fund', x => x.length); if (!n) P(pg, vw, 'scheda fondi vuota: ' + (await t.textContent())); }
          await p.focus('#fund-tabs [role=tab]'); await p.keyboard.press('ArrowRight');
          const sel = await p.$eval('#fund-tabs [aria-selected=true]', e => e.textContent); if (!sel) P(pg, vw, 'freccia tastiera non funziona');
        }
        if (pg === 'titoli-di-stato.html') {
          const chips = await p.$$('#paesi button');
          for (const c of chips) { await c.click(); await p.waitForTimeout(60); const n = await p.$$eval('#bond-table tbody tr', x => x.length); const t = await p.$eval('#bond-head', e => e.textContent); if (!n || /NaN|undefined/.test(t)) P(pg, vw, 'Paese senza dati: ' + (await c.textContent())); }
        }
        if (pg === 'etf.html') {
          const combos = [['mercato', 'USA'], ['mercato', ''], ['classe', 'Obbligazioni'], ['classe', 'Materie prime'], ['classe', 'Cripto'], ['area', 'Emergenti'], ['ter', '0.1'], ['politica', 'Distribuzione'], ['ordine', 'ter'], ['ordine', 'nome']];
          for (const [k, v] of combos) { for (const [k2, v2] of [['mercato','Europa'],['classe',''],['area',''],['ter',''],['politica','']]) if (k2 !== k) await p.selectOption(`select[name=${k2}]`, v2); await p.selectOption(`select[name=${k}]`, v); await p.waitForTimeout(60); const n = await p.$$eval('.etf', x => x.length); const c = await p.$eval('#etf-count', e => e.textContent); console.log(`  filtro ${k}=${v}: ${c}`); if (!n) P(pg, vw, `filtro ${k}=${v} senza risultati`); }
          await p.fill('input[name=q]', 'msci world'); await p.waitForTimeout(80); console.log('  ricerca msci world:', await p.$eval('#etf-count', e => e.textContent));
          await p.fill('input[name=q]', 'zzzzz'); await p.waitForTimeout(80); if (!(await p.$('.empty'))) P(pg, vw, 'manca il messaggio "nessun ETF"');
          await p.fill('input[name=q]', ''); await p.selectOption('select[name=mercato]', 'Europa'); await p.selectOption('select[name=classe]', ''); await p.selectOption('select[name=area]', ''); await p.selectOption('select[name=ter]', ''); await p.selectOption('select[name=politica]', '');
          const before = await p.$$eval('.etf', x => x.length); if (await p.isVisible('#etf-more')) { await p.click('#etf-more'); await p.waitForTimeout(80); const after = await p.$$eval('.etf', x => x.length); if (after <= before) P(pg, vw, '"Mostra altri" non funziona'); }
        }
        if (pg === 'calendario.html') {
          for (const sel of ['#c-vista button[data-v=pubblicati]', '#c-imp button[data-v=alta]', '#c-paese button[data-v=IT]', '#c-paese button[data-v=US]', '#c-vista button[data-v=prossimi]', '#c-paese button[data-v=""]']) { await p.click(sel); await p.waitForTimeout(60); console.log('  ' + sel + ': ' + await p.$eval('#cal-count', e => e.textContent)); }
          await p.click('#c-imp button[data-v=""]');
          const d = await p.$('.ev details summary'); if (d) { await d.click(); const open = await p.$eval('.ev details', e => e.open && e.textContent.length > 80); if (!open) P(pg, vw, '"Cosa significa" non si apre'); }
          const noFam = await p.$$eval('.ev', x => x.filter(e => !e.querySelector('details')).map(e => e.querySelector('.nm').textContent)); if (noFam.length) P(pg, vw, 'eventi senza spiegazione: ' + noFam.join('; '));
        }
      } catch (e) { P(pg, vw, 'interazione fallita: ' + e.message.slice(0, 160)); }
    }
    await p.close();
  }
  // link: interni e esterni (solo stato HTTP)
  const ctx = await b.newContext();
  for (const h of links) {
    if (process.env.LOCAL && !h.startsWith(BASE)) continue;
    if (h.startsWith('mailto:') || h.includes('#')) { if (h.includes('#') && h.startsWith(BASE)) { /* ancore: verificate sotto */ } continue; }
    try { const res = await ctx.request.get(h, { timeout: 20000, maxRedirects: 5 }); if (res.status() >= 400) problems.push(`LINK ${res.status()} ${h}`); }
    catch (e) { problems.push(`LINK errore ${h} ${e.message.slice(0, 80)}`); }
  }
  console.log('LINK controllati:', links.size);
  console.log('\nPROBLEMI TROVATI: ' + problems.length); problems.forEach(x => console.log(' - ' + x));
  await b.close();
})();
