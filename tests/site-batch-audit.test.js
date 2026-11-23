'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const SCMTransportEstimate=require('../js/transport-estimate.js');
const SCMInventory=require('../js/inventory-models.js');
const Chart=require('../js/vendor/chart.umd-4.6.1.js');
function extract(page,name,spaces=4){
  const match=page.match(new RegExp(`^${' '.repeat(spaces)}function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n${' '.repeat(spaces)}\\}`,'m'));
  assert.ok(match,name);return match[0];
}
test('transport estimates require finite and valid values, never conflate trip with tonne-km',()=>{
  const {publicEstimate,ftlEstimate}=SCMTransportEstimate;
  assert.equal(publicEstimate(['500','15','2000']),9500);
  assert.equal(publicEstimate(['500','15','']),7500);
  assert.equal(ftlEstimate(['100','10','1.2']),1200);
  assert.equal(ftlEstimate(['100','0','1']),0);
  for(const vals of [['','1','1'],['1x','1','1'],['0','1','1'],['-1','1','1'],['1','-1','1'],['1e308','1e308','1'],['1e-300','1e-300','1']]){
    assert.equal(publicEstimate(vals),null,JSON.stringify(vals));assert.equal(ftlEstimate(vals),null,JSON.stringify(vals));
  }
  assert.equal(ftlEstimate(['1','1','0']),null);
  assert.equal(publicEstimate(['1','1','-1']),null);
  assert.equal(publicEstimate(['1e308','1','1e308']),null);
});
test('SCM FTL save validates, versions records and cannot overwrite transport KPI',()=>{
  const page=fs.readFileSync('scm-platform/calculators.html','utf8');
  const def=page.match(/        \{ id: "ftl_cost",[\s\S]*?kpiId: null \}/);assert.ok(def);
  const nodes=new Map(),map=new Map([['calc_ftl_cost_default','[{"result":111}]'],['kpi_transportCost_default','{"result":33}']]),sent=[];
  const document={getElementById:id=>{if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:''});return nodes.get(id)}};
  const localStorage={getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,v)};
  const ctx={document,localStorage,SCMTransportEstimate,SCMInventory,alert(){},sendToKPI:(...args)=>sent.push(args)};vm.createContext(ctx);
  vm.runInContext(`let currentBranchId='default';const calculators=[${def[0]}];\n`+['saveCalculation','handleSave','handleSendToKPI','updateAllCalculators'].map(x=>extract(page,x)).join('\n'),ctx);
  const e={currentTarget:{getAttribute:k=>k==='data-id'?'ftl_cost':'transportCost'}};
  ctx.updateAllCalculators();ctx.handleSave(e);ctx.handleSendToKPI(e);assert.equal(map.has('calc_ftl_cost_trip_v1_default'),false);
  for(const [k,v] of Object.entries({ftl_km:'100',ftl_rate:'10',ftl_coef:'1.2'}))document.getElementById(k).value=v;
  ctx.updateAllCalculators();ctx.handleSave(e);ctx.handleSendToKPI(e);
  assert.equal(JSON.parse(map.get('calc_ftl_cost_trip_v1_default'))[0].result,1200);
  assert.equal(JSON.parse(map.get('calc_ftl_cost_trip_v1_default'))[0].method,'trip-estimate-v1');
  assert.equal(map.get('calc_ftl_cost_default'),'[{"result":111}]');assert.equal(map.get('kpi_transportCost_default'),'{"result":33}');assert.deepEqual(sent,[]);
  document.getElementById('ftl_coef').value='';ctx.updateAllCalculators();ctx.handleSave(e);
  assert.match(nodes.get('result_ftl_cost').innerHTML,/Проверьте ввод/);assert.equal(JSON.parse(map.get('calc_ftl_cost_trip_v1_default')).length,1);
  assert.match(fs.readFileSync('scm-platform/kpi-center.html','utf8'),/рубли вместо руб\.\/т-км/);
});
test('public trip estimate hides stale result on edit and invalid input',()=>{
  const page=fs.readFileSync('calculators.html','utf8'),nodes=new Map();let count=0;
  const document={getElementById:id=>{if(!nodes.has(id))nodes.set(id,{value:'',style:{},textContent:''});return nodes.get(id)}};
  const ctx={document,SCMTransportEstimate,SCMInventory,alert:()=>count++};vm.createContext(ctx);
  vm.runInContext(['showResult','formatInventoryValue','hideInventoryResult','calculateTransportCost'].map(x=>extract(page,x,8)).join('\n'),ctx);
  for(const [k,v] of Object.entries({'transp-distance':'500','transp-rate':'15','transp-additional':'2000'}))document.getElementById(k).value=v;
  ctx.calculateTransportCost();assert.equal(document.getElementById('transport-cost-result').style.display,'block');
  document.getElementById('transp-rate').value='1e309';ctx.calculateTransportCost();assert.equal(document.getElementById('transport-cost-result').style.display,'none');assert.equal(count,1);
  assert.match(page,/\[\['transp-distance', 'transp-rate', 'transp-additional'\], 'transport-cost-result'\]/);
});
test('promotion escapes untrusted keyword history and traffic aggregates',()=>{
  const page=fs.readFileSync('promotion.html','utf8');const table={innerHTML:''},stats={innerHTML:''};
  const malicious='"><img src=x onerror=alert(1)>';
  const data={keys:JSON.stringify([{word:'test',positions:[malicious,malicious],dates:['a','b']}]),traffic:JSON.stringify([{visits:malicious,views:1}])};
  const ctx={localStorage:{getItem:k=>data[k]},STORAGE:{keywords:'keys',trafficData:'traffic'},document:{querySelector:()=>table,querySelectorAll:()=>[],getElementById:()=>stats},updateKeywordChart(){}};vm.createContext(ctx);
  vm.runInContext(page.match(/^    function escapeHtml[^\n]+/m)[0]+'\n'+extract(page,'renderKeywords')+'\n'+extract(page,'updateTrafficStats'),ctx);
  ctx.renderKeywords();assert.doesNotMatch(table.innerHTML,/<img/);assert.match(table.innerHTML,/&lt;img/);
  ctx.updateTrafficStats();assert.doesNotMatch(stats.innerHTML,/<img/);assert.match(stats.innerHTML,/&lt;img/);
});
test('keyword chart handles redraw, selection and empty data with one handler',()=>{
  const page=fs.readFileSync('promotion.html','utf8');let keywords=[{word:'one',dates:['a'],positions:[1]},{word:'two',dates:['a'],positions:[2]}],count=0,destroyed=0;
  const select={value:'1',innerHTML:'',onchange:null},canvas={getContext:()=>({})};
  const ctx={localStorage:{getItem:()=>JSON.stringify(keywords)},STORAGE:{keywords:'keywords'},document:{getElementById:id=>id==='keywordSelect'?select:canvas},Chart:function(_ctx,config){count++;this.config=config;this.destroy=()=>destroyed++;}};vm.createContext(ctx);
  vm.runInContext('let keywordChart=null;\n'+page.match(/^    function escapeHtml[^\n]+/m)[0]+'\n'+extract(page,'updateKeywordChart'),ctx);
  ctx.updateKeywordChart();assert.equal(count,1);assert.equal(select.value,'1');const handler=select.onchange;
  handler();assert.equal(count,2);assert.equal(destroyed,1);assert.equal(select.onchange,handler);
  keywords=[];ctx.updateKeywordChart();assert.equal(destroyed,2);
});
test('cabinet can replace a real locally vendored chart on the same canvas',()=>{
  const page=fs.readFileSync('cabinet.html','utf8');
  const canvas={width:400,height:200,style:{},getAttribute:()=>null,setAttribute(){},removeAttribute(){},addEventListener(){},removeEventListener(){}};
  const context=new Proxy({canvas,length:undefined,measureText:t=>({width:String(t).length*8}),setLineDash(){},getLineDash:()=>[]},{get:(o,k)=>k in o?o[k]:()=>{},set:(o,k,v)=>(o[k]=v,true)});canvas.getContext=()=>context;
  const ctx={Chart,document:{getElementById:()=>canvas}};vm.createContext(ctx);vm.runInContext(extract(page,'drawMarketChart'),ctx);
  const config={type:'bar',data:{labels:['a'],datasets:[{data:[1]}]},options:{responsive:false,animation:false}};
  const first=ctx.drawMarketChart('x',config);const second=ctx.drawMarketChart('x',config);assert.equal(first.canvas,null);assert.equal(second.canvas,canvas);second.destroy();
  for(const f of ['cabinet.html','promotion.html']){const text=fs.readFileSync(f,'utf8');assert.match(text,/src="js\/vendor\/chart\.umd-4\.6\.1\.js"/);assert.doesNotMatch(text,/chart\.js@4\.4\.0/);}
});
test('noindex pages remain outside sitemap and accessible to robots for noindex discovery',()=>{
  const robots=fs.readFileSync('robots.txt','utf8'),sitemap=fs.readFileSync('sitemap.xml','utf8');
  for(const file of ['checklist.html','promotion.html']){
    assert.doesNotMatch(robots,new RegExp(`Disallow:\\s*/${file.replace('.', '\\.')}`,'i'));
    assert.match(fs.readFileSync(file,'utf8'),/<meta name="robots" content="noindex/i);
    assert.ok(!sitemap.includes(file));
  }
  for(const bot of ['GPTBot','OAI-SearchBot','ClaudeBot','PerplexityBot'])assert.match(robots,new RegExp(`User-agent: ${bot}\\nAllow: /`));
});

test('promotion import is paused without reading files or touching existing data',()=>{
  const page=fs.readFileSync('promotion.html','utf8'),map=new Map([['keywords','old']]),status={textContent:''};
  const ctx={document:{getElementById:()=>status},localStorage:{setItem:(k,v)=>map.set(k,v)}};vm.createContext(ctx);
  vm.runInContext(extract(page,'importData'),ctx);
  ctx.importData('{"keywords":[1]}');assert.equal(map.get('keywords'),'old');assert.match(status.textContent,/приостановлен/);
  assert.match(page,/id="importAllBtn"[^>]*disabled/);assert.match(page,/id="importLeadsBtn"[^>]*disabled/);
});
test('promotion CSV quotes cells and prefixes spreadsheet text without claiming universal protection',()=>{
  const page=fs.readFileSync('promotion.html','utf8'),ctx={};vm.createContext(ctx);vm.runInContext(extract(page,'csvTextCell'),ctx);
  assert.equal(ctx.csvTextCell('=2+2'),`"'=2+2"`);
  assert.equal(ctx.csvTextCell('x",=1'),`"'x"",=1"`);
  assert.equal(ctx.csvTextCell('a\nb'),`"'a\nb"`);
  assert.match(page,/не гарантирует безопасность во всех табличных программах/);
});
test('promotion initialises empty analytics for new users without replacing existing records',()=>{
  const page=fs.readFileSync('promotion.html','utf8'),map=new Map([['traffic','[{"visits":42}]']]);
  const ctx={STORAGE:{seoPages:'seo',trafficData:'traffic',keywords:'keywords',leads:'leads',authority:'authority',quizzes:'quizzes'},localStorage:{getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,v)}};
  vm.createContext(ctx);vm.runInContext(extract(page,'initData'),ctx);ctx.initData();
  assert.equal(map.get('traffic'),'[{"visits":42}]');assert.deepEqual(JSON.parse(map.get('keywords')),[]);
  assert.match(page,/Старые записи могли быть демонстрационными/);
});
