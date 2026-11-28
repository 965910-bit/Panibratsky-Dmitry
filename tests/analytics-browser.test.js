'use strict';
// Vendors are stubbed: verifies our integration, not actual delivery to their servers.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('playwright-core');
const root=path.resolve(__dirname,'..');
const chrome=process.env.CHROME_PATH;
if (!chrome) throw new Error('Set CHROME_PATH to installed Chromium');
const args=['--no-sandbox','--disable-dev-shm-usage',...JSON.parse(process.env.BROWSER_ARGS || '[]')];

test('consent, events and withdrawal in real Chromium with mocked analytics vendors',async()=>{
 const browser=await chromium.launch({executablePath:chrome,headless:true,args});
 const ctx=await browser.newContext(); const page=await ctx.newPage(); const vendors=[];
 try {
  await page.route('**/*',async route=>{
    const u=new URL(route.request().url());
    if (u.hostname==='mc.yandex.ru' || u.hostname==='www.googletagmanager.com') {vendors.push(u.href);return route.fulfill({status:200,contentType:'application/javascript',body:'/* vendor stub */'});}
    if (u.hostname!=='scm-news.ru') return route.abort();
    const file=path.resolve(root,'.'+(u.pathname==='/'?'/index.html':u.pathname));
    if (!file.startsWith(root+path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) return route.fulfill({status:404,body:''});
    const type=file.endsWith('.html')?'text/html; charset=utf-8':file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'application/octet-stream';
    return route.fulfill({status:200,contentType:type,body:fs.readFileSync(file)});
  });
  await page.goto('https://scm-news.ru/career.html?private=do-not-send#secret');
  await page.waitForSelector('.analytics-choice');
  assert.equal(vendors.length,0,'No vendor request before choice');
  await page.locator('[data-choice="no"]').click();
  assert.equal(vendors.length,0);
  await page.reload(); assert.equal(vendors.length,0); assert.equal(await page.locator('.analytics-choice').isVisible(),false);
  await page.locator('.analytics-settings').click(); await page.locator('[data-choice="yes"]').click();
  await page.waitForFunction(()=>window.ym && window.gtag);
  const config=await page.evaluate(()=>({ym:Array.from(window.ym.a[0]),ga:Array.from(window.dataLayer).map(x=>Array.from(x))}));
  assert.equal(config.ym[1],'init'); assert.equal(config.ym[2].webvisor,false); assert.equal(config.ym[2].clickmap,false); assert.equal(config.ym[2].trackLinks,false);
  assert.doesNotMatch(JSON.stringify(config),/private|do-not-send|secret/);
  await page.evaluate(()=>{const a=document.querySelector('a[href^="tel:"]');a.dispatchEvent(new MouseEvent('click',{bubbles:true,button:0}));});
  let events=await page.evaluate(()=>window.ym.a.map(x=>Array.from(x)));
  assert.equal(events.filter(x=>x[2]==='contact_phone_click').length,1);
  await page.evaluate(()=>{const a=document.querySelector('a[data-presentation-download]');a.dispatchEvent(new MouseEvent('click',{bubbles:true,button:0}));});
  events=await page.evaluate(()=>window.ym.a.map(x=>Array.from(x)));
  assert.equal(events.filter(x=>x[2]==='presentation_download').length,1);
  await page.goto('https://scm-news.ru/scm-review-questions.html');
  await page.evaluate(()=>{window.print=()=>{};document.getElementById('print-checklist').click();});
  events=await page.evaluate(()=>window.ym.a.map(x=>Array.from(x)));
  assert.equal(events.filter(x=>x[2]==='checklist_print_click').length,1);
  assert.equal(await page.evaluate(()=>window.dataLayer.filter(x=>x[0]==='event'&&x[1]==='checklist_print_click').length),1,'one GA4 checklist event');
  await page.goto('https://scm-news.ru/inventory-turnover-calculator.html');
  await page.evaluate(()=>document.querySelector('form[data-inventory-tool]').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})));
  events=await page.evaluate(()=>window.ym.a.map(x=>Array.from(x)));
  assert.equal(events.filter(x=>x[2]==='calculator_calculate').length,1);
  assert.equal(await page.evaluate(()=>window.dataLayer.filter(x=>x[0]==='event'&&x[1]==='calculator_calculate').length),1,'one GA4 calculator event');
  await page.goto('https://scm-news.ru/scm-diagnostic.html');
  await page.locator('#stock').selectOption('review'); await page.locator('#supply').selectOption('unknown');
  events=await page.evaluate(()=>window.ym.a.map(x=>Array.from(x)));
  assert.equal(events.filter(x=>x[2]==='diagnostic_start').length,1);
  assert.equal(await page.evaluate(()=>window.dataLayer.filter(x=>x[0]==='event'&&x[1]==='diagnostic_start').length),1,'one GA4 diagnostic event');
  assert.doesNotMatch(JSON.stringify(await page.evaluate(()=>window.dataLayer.map(x=>Array.from(x)))),/review|unknown/);
  assert.doesNotMatch(JSON.stringify(events),/review|unknown/);
  await page.locator('.analytics-settings').click();
  await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded',timeout:45000}), page.locator('[data-choice="no"]').dispatchEvent('click')]);
  assert.equal(await page.evaluate(()=>typeof window.ym),'undefined');
  assert.equal(await page.evaluate(()=>localStorage.getItem('scm_analytics_choice_v1')),'no');
 } finally {await browser.close();}
});
