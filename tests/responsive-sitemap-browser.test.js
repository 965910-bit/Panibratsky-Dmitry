'use strict';
// Fixed local sitemap pages only; external services and analytics are blocked.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright-core');
const root=path.resolve(__dirname,'..'),chrome=process.env.CHROME_PATH;
if(!chrome)throw new Error('Set CHROME_PATH');
const pages=[...fs.readFileSync(path.join(root,'sitemap.xml'),'utf8').matchAll(/<loc>https:\/\/scm-news\.ru\/(.*?)<\/loc>/g)].map(m=>m[1]||'index.html');
test('sitemap pages fit mobile, tablet and desktop viewport without document overflow',async()=>{
 const server=http.createServer((req,res)=>{
  const p=path.resolve(root,'.'+new URL(req.url,'http://local').pathname);
  if(!p.startsWith(root+path.sep)||!fs.existsSync(p)||!fs.statSync(p).isFile()){res.writeHead(404);return res.end();}
  const ext=path.extname(p),type={'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml'}[ext]||'application/octet-stream';
  res.writeHead(200,{'Content-Type':type});fs.createReadStream(p).pipe(res);
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const base=`http://127.0.0.1:${server.address().port}`;
 const browser=await chromium.launch({executablePath:chrome,headless:true,args:['--no-sandbox','--disable-dev-shm-usage',...JSON.parse(process.env.BROWSER_ARGS||'[]')]});
 const errors=[];
 try{
  for(const width of [320,375,768,1440]){
   const ctx=await browser.newContext({viewport:{width,height:850},serviceWorkers:'block'}),page=await ctx.newPage();
   await page.route('**/*',r=>r.request().url().startsWith(base+'/')?r.continue():r.abort());
   for(const file of pages){
    try{
     const response=await page.goto(`${base}/${file}`,{waitUntil:'domcontentloaded',timeout:30000});
     if(!response||response.status()!==200){errors.push(`${file}@${width}: unavailable`);continue;}
     await page.evaluate(()=>{for(const d of document.querySelectorAll('details'))d.open=true;});
     const result=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth, offenders:[...document.querySelectorAll('body *')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0 && r.right>innerWidth+1 }).slice(-12).map(e=>e.tagName+'.'+String(e.className).slice(0,80)+' '+Math.round(e.getBoundingClientRect().right)), inner:[...document.querySelectorAll('body *')].filter(e=>e.clientWidth>0 && e.scrollWidth>e.clientWidth+3 && getComputedStyle(e).overflowX==='visible').slice(-12).map(e=>e.tagName+'.'+String(e.className).slice(0,80)+' '+e.clientWidth+'/'+e.scrollWidth)}));
     if(result.scroll>result.width+1)errors.push(`${file}@${width}: ${result.scroll}px ${result.offenders.join(' | ')} inner=${result.inner.join(' | ')}`);
    }catch(e){errors.push(`${file}@${width}: load failed`);}
   }
   await ctx.close();
  }
 }finally{await browser.close();await new Promise(r=>server.close(r));}
 assert.deepEqual(errors,[],errors.join('\n'));
});
