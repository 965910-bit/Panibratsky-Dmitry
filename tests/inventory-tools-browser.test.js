'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const {chromium} = require('playwright-core');
const chrome = process.env.CHROME_PATH;
if (!chrome) throw new Error('Set CHROME_PATH to an installed Chrome/Chromium');
const args = ['--no-sandbox','--disable-dev-shm-usage',...JSON.parse(process.env.BROWSER_ARGS || '[]')];
async function checkAccessibility(page) {
  await page.addScriptTag({path:require.resolve('axe-core/axe.min.js')});
  for (let i=0;i<2;i++) {
    const violations = await page.evaluate(async()=> (await window.axe.run(document,{runOnly:['color-contrast','label','aria-allowed-attr']})).violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)})));
    assert.deepEqual(violations, []);
    await page.locator('.executive-theme').click();
  }
}
const files = new Set(['inventory-turnover-calculator.html','safety-stock-calculator.html','reorder-point-calculator.html','scm-diagnostic.html','css/inventory-tools.css','css/executive-pages.css','js/executive-theme.js','js/executive-pages.js','js/inventory-models.js','js/inventory-metrics.js','js/inventory-tools.js','js/scm-diagnostic.js']);

test('SCM tools work at desktop and mobile sizes without sending user data',async()=>{
 const requests=[];
 const server=http.createServer((req,res)=>{
   const file=new URL(req.url,'http://example.test').pathname.slice(1);
   requests.push({method:req.method,file});
   if(!files.has(file)){res.writeHead(404);res.end();return;}
   res.setHeader('Content-Type',file.endsWith('.html')?'text/html; charset=utf-8':file.endsWith('.js')?'text/javascript':'text/css');
   res.end(fs.readFileSync(file));
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const base=`http://127.0.0.1:${server.address().port}`;let browser;
 try {
  browser=await chromium.launch({executablePath:chrome,headless:true,args});
  for(const width of [390,1280]) {
   const context=await browser.newContext({viewport:{width,height:844}});const page=await context.newPage();
   await page.route('**/*',route=>route.request().url().startsWith(base+'/')?route.continue():route.abort());
   for(const [filename,expected] of [['inventory-turnover-calculator.html','10 раз за период'],['safety-stock-calculator.html','140 единиц'],['reorder-point-calculator.html','550 единиц']]) {
    await page.goto(`${base}/${filename}`);await page.getByRole('button',{name:'Рассчитать'}).click();
    assert((await page.locator('#tool-result').innerText()).includes(expected));
    await page.locator('input').first().fill('-1');await page.getByRole('button',{name:'Рассчитать'}).click();
    assert.match(await page.locator('#tool-result').innerText(),/Проверьте/);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),true);
    await checkAccessibility(page);
   }
   await page.goto(`${base}/scm-diagnostic.html`);
   await page.locator('#stock').selectOption('yes');await page.locator('#supply').selectOption('unknown');await page.locator('#safety').selectOption('review');await page.locator('#service').selectOption('yes');
   await page.getByRole('button',{name:'Показать вопросы для проверки'}).click();
   assert.equal(await page.locator('#checklist-result li').count(),2);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),true);
   await checkAccessibility(page);
   await context.close();
  }
  const noJs=await browser.newContext({javaScriptEnabled:false});const page=await noJs.newPage();
  await page.goto(`${base}/inventory-turnover-calculator.html`);assert.equal(await page.getByRole('button',{name:'Рассчитать'}).isDisabled(),true);
  await noJs.close();
  assert(requests.every(r=>r.method==='GET'));
 } finally {if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
});
