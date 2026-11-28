'use strict';
// Diagnostic only: exercise existing links, with navigation and all collection blocked.
const {chromium}=require('playwright-core');
const goals=['presentation_download','resume_click_hh','resume_click_zarplata','contact_phone_click','contact_email_click','setka_profile_click','channel_telegram_click','channel_max_click','channel_dzen_click','setka_community_click','setka_channel_click','tenchat_profile_click','interest_book','interest_checklist','checklist_print_click','book_excerpt_click','workbook_excerpt_click','interest_academy','corporate_training_click','interest_guides','interest_articles','interest_projects','interest_experience','interest_expertise','interest_news','interest_calculators','calculator_calculate','interest_diagnostic','diagnostic_start','interest_career'];
const paths=['/','/about.html','/blog.html','/career.html','/contact.html','/experience.html','/expertise.html','/prompts.html','/trends.html'];
async function main(){
 if(process.env.GITHUB_EVENT_NAME!=='workflow_dispatch'||process.env.GITHUB_REF!=='refs/heads/main'||process.env.GITHUB_REPOSITORY_ID!=='1102759388')throw Error('blocked');
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const blocked=new Set(),queued=new Set();let pageCount=0,clicks=0;
 try{
  const ctx=await browser.newContext({serviceWorkers:'block',acceptDownloads:false});
  for(const path of paths){
   const page=await ctx.newPage();
   await page.route('**/*',route=>{
    const req=route.request(),u=new URL(req.url());
    if(u.pathname==='/g/collect'||u.pathname==='/ccm/collect'){
     const payload=(u.searchParams.toString()+'\n'+(req.postData()||''));
     for(const name of goals)if(new RegExp('(?:^|[&\\n])en='+name+'(?:&|\\n|$)').test(payload))blocked.add(name);
     return route.abort();
    }
    if(req.method()==='GET'&&u.protocol==='https:'&&(u.hostname==='scm-news.ru'||(u.hostname==='www.googletagmanager.com'&&u.pathname==='/gtag/js')))return route.continue();
    return route.abort();
   });
   const response=await page.goto('https://scm-news.ru'+path,{waitUntil:'domcontentloaded',timeout:45000});
   if(!response||response.status()!==200)throw Error('page');
   const choice=page.locator('[data-choice="yes"]');
   if(await choice.isVisible())await choice.click();
   await page.waitForFunction(()=>typeof window.gtag==='function'&&Array.isArray(window.dataLayer),{timeout:20000});
   const count=await page.evaluate(()=>{
    const links=Array.from(document.querySelectorAll('a[href]'));
    if(links.length>500)throw Error('too many links');
    // Run after the site's delegated handlers, suppressing all navigation/downloads.
    document.addEventListener('click',e=>e.preventDefault());
    for(const link of links)link.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,button:0}));
    return links.length;
   });
   clicks+=count;
   await page.waitForTimeout(10000);
   const names=await page.evaluate(()=>window.dataLayer.filter(v=>v&&v[0]==='event').map(v=>v[1]));
   for(const name of names)if(goals.includes(name))queued.add(name);
   pageCount++;
   await page.close();
  }
  const list=s=>goals.filter(n=>s.has(n)).join(',')||'none';
  console.log('::notice title=GA4 goal browser coverage::pages='+pageCount+'; link_activations='+clicks+'; queued='+list(queued)+'; blocked_collection='+list(blocked)+'; no_collection_sent; not_proof_of_ingestion');
 }finally{await browser.close();}
}
main().catch(()=>{console.error('::error title=GA4 goal browser coverage::incomplete; no_collection_sent');process.exitCode=1;});
