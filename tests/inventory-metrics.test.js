'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const SCMInventoryMetrics=require('../js/inventory-metrics.js');
const SCMInventory=require('../js/inventory-models.js');
function extract(page,name) {
  const m=page.match(new RegExp(`^    function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n    \\}`,'m'));
  assert.ok(m,name);return m[0];
}
test('period turnover and unit fill use strict inputs, finite results and distinguish zero',()=>{
  const m=SCMInventoryMetrics;
  assert.equal(m.turnover(['500','100','90']),5);
  assert.deepEqual(m.turnoverDays(['500','100','90']),{ratio:5,days:18});
  assert.deepEqual(m.turnoverDays(['0','100','90']),{ratio:0,days:null});
  assert.equal(m.fillRate(['100','75'],'fulfilled'),75);
  assert.equal(m.fillRate(['100','25'],'shortage'),75);
  assert.equal(m.fillRate(['100','0'],'fulfilled'),0);
  assert.equal(m.fillRate(['100','0'],'shortage'),100);
  assert.equal(m.fillRate(['100','100'],'shortage'),0);
  for(const a of [[],['','100','90'],['1x','100','90'],['-1','100','90'],['100','0','90'],['100','1','0'],['100','1','1.1'],['100','1','Infinity'],['1e308','1e-308','90'],['1e-300','1e300','90'],['1e-400','1','1']]) assert.equal(m.turnover(a),null,JSON.stringify(a));
  assert.equal(m.turnoverDays(['1e-300','1','1e9']),null);
  for(const a of [[],['0','0'],['','0'],['100',''],['100','-1'],['100','101'],['Infinity','1'],['1e308','1e-300'],['1e-400','0']]) assert.equal(m.fillRate(a,'fulfilled'),null,JSON.stringify(a));
  assert.equal(m.fillRate(['100','25'],'bad'),null);
});
test('SCM rejects invalid values, isolates legacy results and does not send KPI',()=>{
  const page=fs.readFileSync('scm-platform/calculators.html','utf8');
  const definitions=['turnover','fill_rate'].map(id=>{
    const m=page.match(new RegExp(`        \\{ id: "${id}",[\\s\\S]*?kpiId: null \\}`));assert.ok(m,id);return m[0];
  });
  const map=new Map(),nodes=new Map(),alerts=[],sends=[];
  const document={getElementById:id=>{if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:''});return nodes.get(id)}};
  const localStorage={getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,v)};
  const ctx={SCMInventoryMetrics,SCMInventory,document,localStorage,alert:a=>alerts.push(a),sendToKPI:(...a)=>sends.push(a)};vm.createContext(ctx);
  vm.runInContext(`let currentBranchId='default';const calculators=[${definitions.join(',')}];\n`+['saveCalculation','handleSave','handleSendToKPI','updateAllCalculators'].map(x=>extract(page,x)).join('\n'),ctx);
  const cases=[['turnover',{turn_cogs:'500',turn_avg:'100',turn_days:'90'},5,'period-cogs-average-inventory-v1'],['fill_rate',{fill_ordered:'100',fill_shipped:'75'},75,'unit-fill-immediate-v1']];
  for(const [id,values,result,method] of cases){
    const legacy=`calc_${id}_default`,key=`calc_${id}_metric_v1_default`,event={currentTarget:{getAttribute:k=>k==='data-id'?id:id==='turnover'?'turnover':'fillrate'}};
    map.set(legacy,'[{"result":123}]');ctx.updateAllCalculators();ctx.handleSave(event);ctx.handleSendToKPI(event);
    assert.match(nodes.get(`result_${id}`).innerHTML,/Проверьте ввод/);assert.equal(map.has(key),false);
    for(const [field,value] of Object.entries(values))document.getElementById(field).value=value;
    ctx.updateAllCalculators();ctx.handleSave(event);ctx.handleSendToKPI(event);
    const saved=JSON.parse(map.get(key));assert.equal(saved[0].result,result);assert.equal(saved[0].method,method);
    assert.equal(map.get(legacy),'[{"result":123}]');
    document.getElementById(Object.keys(values)[0]).value='';ctx.updateAllCalculators();ctx.handleSave(event);
    assert.match(nodes.get(`result_${id}`).innerHTML,/Проверьте ввод/);assert.equal(JSON.parse(map.get(key)).length,1);
  }
  assert.deepEqual(sends,[]);assert.match(page,/src="\.\.\/js\/inventory-metrics.js"/);
});
test('public page uses period and hides prior results on changes and invalid input',()=>{
  const page=fs.readFileSync('calculators.html','utf8');const nodes=new Map(),alerts=[];let ready;
  function node(id){if(!nodes.has(id))nodes.set(id,{value:'',style:{},textContent:'',listeners:{},addEventListener(k,f){this.listeners[k]=f;}});return nodes.get(id)}
  const document={getElementById:node,addEventListener:(event,fn)=>{if(event==='DOMContentLoaded')ready=fn;},querySelectorAll:()=>[]};
  const ctx={document,alert:a=>alerts.push(a),SCMInventory,SCMInventoryMetrics,window:{},IntersectionObserver:class{observe(){}}};vm.createContext(ctx);
  for(const script of page.matchAll(/<script(?![^>]*(?:src|application\/ld\+json))[^>]*>([\s\S]*?)<\/script>/gi))vm.runInContext(script[1],ctx);
  for(const [id,value] of Object.entries({'eoq-demand':'10000','eoq-order-cost':'500','eoq-holding-cost':'20','ss-max-demand':'120','ss-avg-demand':'100','ss-lead-time':'7','rop-demand':'100','rop-lead-time':'5','rop-safety-stock':'50','turnover-cogs':'500','turnover-avg-inventory':'100','turnover-period-days':'90','fill-total-demand':'100','fill-stockouts':'25','transp-distance':'500','transp-rate':'15','transp-additional':'0'}))node(id).value=value;
  ready();assert.match(node('turnover-value').textContent,/5 раз за период \(оценка 18 дней\)/);assert.equal(node('fill-rate-value').textContent,'75.00%');
  node('turnover-period-days').listeners.input();assert.equal(node('turnover-result').style.display,'none');
  node('turnover-period-days').value='0';ctx.calculateInventoryTurnover();assert.equal(node('turnover-result').style.display,'none');
  node('turnover-period-days').value='90';node('turnover-cogs').value='0';ctx.calculateInventoryTurnover();assert.match(node('turnover-value').textContent,/не определены/);
  node('fill-stockouts').listeners.input();assert.equal(node('fill-rate-result').style.display,'none');
  node('fill-stockouts').value='101';ctx.calculateFillRate();assert.equal(node('fill-rate-result').style.display,'none');
  assert.equal(alerts.length,2);assert.match(page,/src="js\/inventory-metrics.js"/);
});
