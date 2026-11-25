'use strict';
// Local, intercepted browser regression: no production transfer timings are inferred.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('playwright-core');
const root=path.resolve(__dirname,'..');
const chrome=process.env.CHROME_PATH;
if(!chrome) throw new Error('Set CHROME_PATH to installed Chromium');
const args=['--no-sandbox','--disable-dev-shm-usage',...JSON.parse(process.env.BROWSER_ARGS||'[]')];
const pages=['wiki.html','tools.html','calculators.html','projects.html','certificates.html'];
test('five legacy page portraits use appropriate responsive resources',async()=>{
 const server=http.createServer((req,res)=>{
  const p=path.resolve(root,'.'+new URL(req.url,'http://local').pathname);
  if(!p.startsWith(root+path.sep)||!fs.existsSync(p)||!fs.statSync(p).isFile()){res.writeHead(404);return res.end();}
  const type=p.endsWith('.html')?'text/html; charset=utf-8':p.endsWith('.js')?'text/javascript':p.endsWith('.css')?'text/css':p.endsWith('.webp')?'image/webp':'application/octet-stream';
  res.writeHead(200,{'Content-Type':type});fs.createReadStream(p).pipe(res);
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
 const browser=await chromium.launch({executablePath:chrome,headless:true,args});
 try {
  for(const [width,dpr] of [[1200,1],[1200,2],[375,2]]) {
   const ctx=await browser.newContext({viewport:{width,height:850},deviceScaleFactor:dpr});
   const page=await ctx.newPage();const requests=[];page.on('request',req=>requests.push(req.url()));await page.route('**/*',r=>r.request().url().startsWith(base+'/')?r.continue():r.abort());
   for(const name of pages){
    await page.goto(`${base}/${name}`);const images=page.locator('.photo-left-container img, .photo-right-container img');assert.equal(await images.count(),2,name);
    for(const image of await images.all()) assert.equal(await image.isVisible(),false,`${name}: legacy header hidden`);
    assert.equal(requests.filter(url=>/\/images\/photo-(left|right)(?:-\d+)?\.(jpg|webp)/.test(url)).length,0,`${name}: hidden portraits must not download`);

   }
   await ctx.close();
  }
 } finally {await browser.close();await new Promise(r=>server.close(r));}
});

test('news revalidates a stable cached URL and sees changed content',async()=>{
 let version=1;const observed=[];
 const server=http.createServer((req,res)=>{
  const pathname=new URL(req.url,'http://local').pathname;
  if(pathname==='/data/news.json') {
   const etag=`"feed-${version}"`;const matched=req.headers['if-none-match']===etag;
   observed.push({url:req.url,validator:req.headers['if-none-match'],status:matched?304:200});
   res.setHeader('ETag',etag);res.setHeader('Cache-Control','public, max-age=3600');
   if(matched){res.writeHead(304);return res.end();}
   res.writeHead(200,{'Content-Type':'application/json'});return res.end(JSON.stringify([{link:'https://example.com/story',title:`News version ${version}`,description:'test',source:'test',tags:[]} ]));
  }
  const file=path.resolve(root,'.'+pathname);
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);return res.end();}
  const type=file.endsWith('.html')?'text/html; charset=utf-8':file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'application/octet-stream';
  res.writeHead(200,{'Content-Type':type});fs.createReadStream(file).pipe(res);
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
 const browser=await chromium.launch({executablePath:chrome,headless:true,args:[...args,'--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1']});
 try {
  const ctx=await browser.newContext();const page=await ctx.newPage();
  await page.goto(base+'/trends.html');await page.waitForFunction(()=>document.querySelector('#news-list')?.textContent.includes('News version 1'));
  await page.reload();await page.waitForFunction(()=>document.querySelector('#news-list')?.textContent.includes('News version 1'));
  version=2;await page.reload();await page.waitForFunction(()=>document.querySelector('#news-list')?.textContent.includes('News version 2'));
  assert.deepEqual(observed.map(x=>x.status),[200,304,200]);
  assert.ok(observed.every(x=>x.url==='/data/news.json'));
  await ctx.close();
 } finally {await browser.close();await new Promise(r=>server.close(r));}
});
