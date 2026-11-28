'use strict';
// Synthetic markers only. All collection and outbound navigation are blocked.
const marker='scmtestprivateqzy751309';
function markerPresent(url, body) {
  let text=url+'\n'+(body||'');
  for(let i=0;i<3;i++){try{text=decodeURIComponent(text.replace(/\+/g,'%20'));}catch(_){break;}}
  return text.includes(marker);
}
async function main(){
  if(process.env.GITHUB_EVENT_NAME!=='workflow_dispatch'||process.env.GITHUB_REF!=='refs/heads/main'||process.env.GITHUB_REPOSITORY_ID!=='1102759388')throw Error('blocked');
  const {chromium}=require('playwright-core');
  const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
  try {
    for(const kind of ['site_search_query','outbound_link_query']){
      const ctx=await browser.newContext({serviceWorkers:'block'}),page=await ctx.newPage();
      let collection=false,markerSeen=false,tagLoaded=false;
      await ctx.addInitScript(()=>localStorage.setItem('scm_analytics_choice_v1','yes'));
      page.on('response',r=>{const u=new URL(r.url());if(u.hostname==='www.googletagmanager.com'&&u.pathname==='/gtag/js'&&r.status()===200)tagLoaded=true;});
      await page.route('**/*',route=>{
        const req=route.request(),u=new URL(req.url());
        if(u.pathname==='/g/collect'||u.pathname==='/ccm/collect'){
          collection=true;markerSeen ||= markerPresent(req.url(),req.postData());return route.abort();
        }
        if(req.method()==='GET'&&u.protocol==='https:'&&(u.hostname==='scm-news.ru'||(u.hostname==='www.googletagmanager.com'&&u.pathname==='/gtag/js')))return route.continue();
        return route.abort();
      });
      const url='https://scm-news.ru/career.html'+(kind==='site_search_query'?'?q='+marker:'');
      const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000});
      if(!response||response.status()!==200)throw Error('page');
      await page.waitForFunction(()=>!!window.google_tag_data,{timeout:20000});
      if(kind==='outbound_link_query') await page.evaluate(m=>{
        const a=document.createElement('a');a.href='https://example.com/?query='+m;a.textContent='probe';document.body.appendChild(a);
        document.addEventListener('click',event=>event.preventDefault());
        a.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,button:0}));
      },marker);
      await page.waitForTimeout(15000);
      console.log(`::notice title=GA4 automatic privacy probe::case=${kind}; tag_loaded=${tagLoaded}; collection_blocked=${collection}; marker_in_blocked_collection=${markerSeen}; no_collection_sent; limited_test_not_privacy_guarantee`);
      await ctx.close();
    }
  }finally{await browser.close();}
}
if(require.main===module)main().catch(()=>{console.error('::error title=GA4 automatic privacy probe::incomplete; no_collection_sent');process.exitCode=1;});
module.exports={marker,markerPresent};
