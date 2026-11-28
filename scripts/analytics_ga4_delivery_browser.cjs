'use strict';
// A single explicitly named synthetic non-key event; no real goal clicks or form data.
const {chromium}=require('playwright-core');
(async()=>{
 if(process.env.GITHUB_EVENT_NAME!=='workflow_dispatch'||process.env.GITHUB_REF!=='refs/heads/main'||process.env.GITHUB_REPOSITORY_ID!=='1102759388')throw Error('blocked');
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 let collect=false;
 try{
  const ctx=await browser.newContext({serviceWorkers:'block'});
  const page=await ctx.newPage();
  await page.route('**/*',route=>{
   const u=new URL(route.request().url());
   if (u.protocol==='https:' && (['scm-news.ru','www.googletagmanager.com','www.google-analytics.com','region1.google-analytics.com'].includes(u.hostname) || (['www.google.com','region1.google.com'].includes(u.hostname) && ['/g/collect','/ccm/collect'].includes(u.pathname))))return route.continue();
   return route.abort();
  });
  page.on('response',response=>{
   const u=new URL(response.url());
   if ((['www.google-analytics.com','region1.google-analytics.com','www.google.com','region1.google.com'].includes(u.hostname)) && u.pathname==='/g/collect' && response.status()>=200 && response.status()<300)collect=true;
  });
  await page.goto('https://scm-news.ru/',{waitUntil:'domcontentloaded',timeout:45000});
  await page.locator('[data-choice="yes"]').click();
  await page.waitForFunction(()=>typeof window.gtag==='function',{timeout:20000});
  // Debug marker is fixed; the event is not configured as a GA key event.
  await page.evaluate(()=>window.gtag('event','scm_delivery_test',{debug_mode:true}));
  await page.waitForTimeout(12000);
  console.log('::notice title=GA4 browser::test_queued=true; collect_http_success_observed='+collect+'; yandex_blocked=true; no_goal_clicked');
 } finally {await browser.close();}
})().catch(()=>{console.error('::error title=GA4 browser::browser_test_failed_or_uncertain; do_not_retry_blindly');process.exitCode=1;});
