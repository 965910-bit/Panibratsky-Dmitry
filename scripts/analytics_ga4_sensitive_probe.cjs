'use strict';
// Check live consent-based tag on instrument pages while every collection is blocked.
const {chromium}=require('playwright-core');
const cases=[['/scm-review-questions.html','print','checklist_print_click'],['/calculators.html','button','calculator_calculate'],['/inventory-turnover-calculator.html','form','calculator_calculate'],['/safety-stock-calculator.html','safety_form','calculator_calculate'],['/reorder-point-calculator.html','reorder_form','calculator_calculate'],['/scm-diagnostic.html','select','diagnostic_start']];
const markers=['scmprivateqzy751309','987654321.123'];
async function run(){
 if(process.env.GITHUB_EVENT_NAME!=='workflow_dispatch'||process.env.GITHUB_REF!=='refs/heads/main'||process.env.GITHUB_REPOSITORY_ID!=='1102759388')throw Error('blocked');
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 try {
  for(const [path,kind,goal] of cases){
   let collection=false,goalBlocked=false,markerBlocked=false,queryMarker=false,numberMarker=false,tagOk=false; const markerEvents=new Set(),markerFields=new Set();
   const ctx=await browser.newContext({serviceWorkers:'block'}),page=await ctx.newPage();
   await ctx.addInitScript(()=>localStorage.setItem('scm_analytics_choice_v1','yes'));
   page.on('response',r=>{const u=new URL(r.url());if(u.hostname==='www.googletagmanager.com'&&u.pathname==='/gtag/js'&&r.status()===200)tagOk=true;});
   await page.route('**/*',route=>{
    const req=route.request(),u=new URL(req.url());
    if(u.pathname==='/g/collect'||u.pathname==='/ccm/collect'){
     collection=true;let text=req.url()+'\n'+(req.postData()||'');
     for(let i=0;i<3;i++){try{text=decodeURIComponent(text.replace(/\+/g,'%20'));}catch(_){break;}}
     if(markers.some(m=>text.includes(m))){
      markerBlocked=true;queryMarker||=text.includes(markers[0]);numberMarker||=text.includes(markers[1]);
      for(const event of ['page_view','form_start','form_submit','scroll','calculator_calculate','diagnostic_start','checklist_print_click'])if(new RegExp('(?:^|[&\\n])en='+event+'(?:&|\\n|$)').test(text))markerEvents.add(event);
      // Log only a fixed field category, never the value or arbitrary field names.
      for(const part of text.split(/[&\n?]/)){const idx=part.indexOf('=');if(idx<0||!markers.some(m=>part.slice(idx+1).includes(m)))continue;const key=part.slice(0,idx);markerFields.add(['dl','dr','ep.form_destination','ep.form_id'].includes(key)?key:'other');}
     }
     if(new RegExp('(?:^|[&\\n])en='+goal+'(?:&|\\n|$)').test(text))goalBlocked=true;
     return route.abort();
    }
    if(req.method()==='GET'&&u.protocol==='https:'&&(u.hostname==='scm-news.ru'||(u.hostname==='www.googletagmanager.com'&&u.pathname==='/gtag/js')))return route.continue();
    return route.abort();
   });
   const response=await page.goto('https://scm-news.ru'+path+'?scm_probe=scmprivateqzy751309#scmprivateqzy751309',{waitUntil:'domcontentloaded',timeout:45000});
   if(!response||response.status()!==200)throw Error('page');
   await page.waitForFunction(()=>!!window.google_tag_data,{timeout:20000});
   const activated=await page.evaluate(kind=>{
    const field=document.querySelector('input:not([type=hidden])');if(field){field.value='987654321.123';field.dispatchEvent(new Event('input',{bubbles:true}));field.dispatchEvent(new Event('change',{bubbles:true}));}
    window.print=()=>{};
    document.addEventListener('submit',e=>e.preventDefault());
    if(kind==='print'){const e=document.querySelector('#print-checklist');if(!e)return false;e.click();return true;}
    if(kind==='button'){const e=document.querySelector('button.calculate-btn');if(!e)return false;e.click();return true;}
    if(['form','safety_form','reorder_form'].includes(kind)){const e=document.querySelector('form[data-inventory-tool]');if(!e)return false;e.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));return true;}
    const e=document.querySelector('#scm-checklist select');if(!e)return false;const o=document.createElement('option');o.value='scmprivateqzy751309';o.textContent='test';e.appendChild(o);e.value=o.value;e.dispatchEvent(new Event('change',{bubbles:true}));return true;
   },kind);
   await page.waitForTimeout(15000);
   const queued=await page.evaluate(goal=>window.dataLayer.some(v=>v&&v[0]==='event'&&v[1]===goal),goal);
   console.log(`::notice title=Isolated GA4 privacy probe::case=${kind}; action_found=${activated}; tag_loaded=${tagOk}; event_queued=${queued}; goal_in_blocked_collection=${goalBlocked}; collection_blocked=${collection}; test_marker_in_blocked_collection=${markerBlocked}; query_marker=${queryMarker}; number_marker=${numberMarker}; marker_events=${[...markerEvents].sort().join(',')||'none'}; marker_fields=${[...markerFields].sort().join(',')||'none'}; no_collection_sent; limited_test_not_privacy_guarantee`);
   await ctx.close();
  }
 }finally{await browser.close();}
}
run().catch(()=>{console.error('::error title=Isolated GA4 privacy probe::incomplete; no_collection_sent');process.exitCode=1;});
