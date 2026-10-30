const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage();
p.on('response',async r=>{if(r.url().includes('eventsJson')){console.log('URL',r.url(),r.status());try{const t=await r.text();console.log('BODY',t.slice(0,1500));require('fs').writeFileSync('cal_raw/eurostat_pw.json',t)}catch(e){console.log(e.message)}}});
p.on('request',r=>{if(r.url().includes('eventsJson'))console.log('REQ',r.method(),JSON.stringify(r.headers()))});
await p.goto('https://ec.europa.eu/eurostat/news/euro-indicators/release-calendar',{waitUntil:'networkidle',timeout:60000});await p.waitForTimeout(3000);await b.close();})();
