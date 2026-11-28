'use strict';
// Read-only browser diagnosis. All collection requests are blocked, including page views.
const {chromium}=require('playwright-core');
(async()=>{
 if(process.env.GITHUB_EVENT_NAME!=='workflow_dispatch'||process.env.GITHUB_REF!=='refs/heads/main'||process.env.GITHUB_REPOSITORY_ID!=='1102759388')throw Error('blocked');
 const b=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const facts={tag_requested:false,tag_response:'none',tag_request_failed:false,analytics_collection_blocked:false,other_google_request_blocked:false,other_vendor_blocked:false, google_com:false, google_ru:false, google_doubleclick:false, google_ads:false, gtm_other:false, google_other:false, blocked_collect_path:false};
 try{
  const ctx=await b.newContext({serviceWorkers:'block'});const page=await ctx.newPage();
  page.on('requestfailed',req=>{const u=new URL(req.url());if(u.hostname==='www.googletagmanager.com'&&u.pathname==='/gtag/js')facts.tag_request_failed=true;});
  page.on('response',response=>{const u=new URL(response.url());if(u.hostname==='www.googletagmanager.com'&&u.pathname==='/gtag/js')facts.tag_response=response.status()===200?'ok':'non_200';});
  await page.route('**/*',route=>{
   const req=route.request(),u=new URL(req.url());
   if(u.protocol==='https:'&&u.hostname==='scm-news.ru'&&req.method()==='GET')return route.continue();
   if(u.protocol==='https:'&&u.hostname==='www.googletagmanager.com'&&u.pathname==='/gtag/js'&&req.method()==='GET'){facts.tag_requested=true;return route.continue();}
   if(u.hostname==='google-analytics.com'||u.hostname.endsWith('.google-analytics.com'))facts.analytics_collection_blocked=true;
   else if(u.hostname==='google.com'||u.hostname.endsWith('.google.com')||u.hostname.endsWith('.googletagmanager.com')||u.hostname.endsWith('.doubleclick.net')||u.hostname.endsWith('.googleadservices.com')){
    facts.other_google_request_blocked=true;
    if(u.hostname==='www.google.com')facts.google_com=true;
    else if(u.hostname==='www.google.ru')facts.google_ru=true;
    else if(u.hostname.endsWith('.doubleclick.net'))facts.google_doubleclick=true;
    else if(u.hostname.endsWith('.googleadservices.com'))facts.google_ads=true;
    else if(u.hostname.endsWith('.googletagmanager.com'))facts.gtm_other=true;
    else facts.google_other=true;
    if(u.pathname==='/g/collect'||u.pathname==='/ccm/collect')facts.blocked_collect_path=true;
   }
   else facts.other_vendor_blocked=true;
   return route.abort();
  });
  await page.goto('https://scm-news.ru/',{waitUntil:'domcontentloaded',timeout:45000});
  await page.locator('[data-choice="yes"]').click();
  await page.waitForTimeout(18000);
  const state=await page.evaluate(()=>({gtag:typeof window.gtag==='function',tag_data:!!window.google_tag_data,queued:Array.isArray(window.dataLayer),choice:localStorage.getItem('scm_analytics_choice_v1')==='yes'}));
  const result={...facts,...state};
  console.log('::notice title=GA4 tag diagnosis::'+Object.entries(result).map(([k,v])=>k+'='+v).join('; ')+'; no_collection_sent; no_event_tested');
 }finally{await b.close();}
})().catch(()=>{console.error('::error title=GA4 tag diagnosis::browser_or_network_failed; no_collection_sent');process.exitCode=1;});
