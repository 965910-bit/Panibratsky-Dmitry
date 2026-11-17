'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const SCMInventory=require('../js/inventory-models.js');
function extract(page,name,indent='    ') {
  const m=page.match(new RegExp(`^${indent}function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n${indent}\\}`,'m'));
  assert.ok(m,name);return m[0];
}
test('inventory models validate inputs and finite intermediate results',()=>{
  const {eoq,safetyNormal,safetyScenario,reorderPoint,format}=SCMInventory;
  assert.equal(eoq(['10000','500','20']),Math.sqrt(500000));
  assert.ok(Math.abs(safetyNormal(['1.645','8','9'])-39.48)<1e-10);
  assert.equal(safetyScenario(['120','100','7']),140);
  assert.equal(reorderPoint(['100','5','50']),550);
  assert.equal(safetyNormal(['0','8','9']),0);
  assert.equal(safetyNormal(['1','0','9']),0);
  assert.equal(safetyScenario(['100','100','7']),0);
  assert.equal(reorderPoint(['0','5','0']),0);
  for (const v of [['','1','1'],['1x','1','1'],['1e-400','1','1'],['1','Infinity','1'],['1','1','0'],['-1','1','1'],['1e308','1e308','1'],['1e-300','1e-300','1']]) assert.equal(eoq(v),null,JSON.stringify(v));
  for (const v of [['','1','1'],['-1','1','1'],['1','-1','1'],['1','1','0'],['1','1','0.5'],['1e308','1e308','1'],['1e-300','1e-300','1']]) assert.equal(safetyNormal(v),null,JSON.stringify(v));
  for (const v of [['','1','1'],['1','2','1'],['-1','0','1'],['1','1','0'],['1e308','0','2'],['1e-300','0','1e-300']]) assert.equal(safetyScenario(v),null,JSON.stringify(v));
  for (const v of [['','1','1'],['-1','1','1'],['1','0','0'],['1','1','-1'],['1e308','2','0'],['1e-300','1e-300','1']]) assert.equal(reorderPoint(v),null,JSON.stringify(v));
  assert.equal(format(0.00001),'1.00e-5'); assert.equal(format(1.234),'1.23'); assert.equal(format(0),'0');
});
test('platform validates display and save, keeps legacy and isolates model versions',()=>{
  const page=fs.readFileSync('scm-platform/calculators.html','utf8');
  const defs=page.match(/        \{ id: "safety_stock",[\s\S]*?(?=        \{ id: "staff_driver",)/); assert.ok(defs);
  const map=new Map(), nodes=new Map(), alerts=[], sends=[];
  const document={getElementById:id=>{if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:''});return nodes.get(id)}};
  const localStorage={getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,v)};
  const ctx={SCMInventory,document,localStorage,alert:a=>alerts.push(a),sendToKPI:(...a)=>sends.push(a)};
  vm.createContext(ctx);
  vm.runInContext(`let currentBranchId='default'; const calculators=[${defs[0]}];\n`+['saveCalculation','handleSave','handleSendToKPI','updateAllCalculators'].map(x=>extract(page,x)).join('\n'),ctx);
  const cases=[['safety_stock',{ss_z:'1.645',ss_sigma:'8',ss_lt:'9'},39.48,'fixed-lead-normal-v1'],['eoq',{eoq_d:'10000',eoq_s:'500',eoq_h:'20'},Math.sqrt(500000),'classical-eoq-v1'],['rop',{rop_d:'100',rop_lt:'5',rop_ss:'50'},550,'continuous-review-rop-v1']];
  for(const [id,values,result,method] of cases){
    const oldKey=`calc_${id}_default`,newKey=`calc_${id}_model_v1_default`,event={currentTarget:{getAttribute:k=>k==='data-id'?id:'otif'}};
    map.set(oldKey,'[{"result":123}]');
    ctx.updateAllCalculators();ctx.handleSave(event);ctx.handleSendToKPI(event);
    assert.equal(map.has(newKey),false);assert.match(nodes.get(`result_${id}`).innerHTML,/Проверьте ввод/);
    for(const [field,value] of Object.entries(values))document.getElementById(field).value=value;
    ctx.updateAllCalculators();ctx.handleSave(event);
    assert.ok(Math.abs(JSON.parse(map.get(newKey))[0].result-result)<1e-10);assert.equal(JSON.parse(map.get(newKey))[0].method,method);
    assert.equal(map.get(oldKey),'[{"result":123}]');
    document.getElementById(Object.keys(values)[0]).value='';ctx.updateAllCalculators();ctx.handleSave(event);
    assert.match(nodes.get(`result_${id}`).innerHTML,/Проверьте ввод/);assert.equal(JSON.parse(map.get(newKey)).length,1);
  }
  assert.deepEqual(sends,[]);assert.match(page,/src="\.\.\/js\/inventory-models.js"/);
});
test('public page clears prior inventory result on invalid input and on edits',()=>{
  const page=fs.readFileSync('calculators.html','utf8'),nodes=new Map(),alerts=[];
  const document={getElementById:id=>{if(!nodes.has(id))nodes.set(id,{value:'',style:{},textContent:''});return nodes.get(id)}};
  const ctx={SCMInventory,document,alert:a=>alerts.push(a)};vm.createContext(ctx);
  vm.runInContext(['showResult','formatInventoryValue','hideInventoryResult','calculateEOQ','calculateSafetyStock','calculateReorderPoint'].map(x=>extract(page,x,'        ')).join('\n'),ctx);
  const cases=[['calculateEOQ','eoq-result',{'eoq-demand':'10000','eoq-order-cost':'500','eoq-holding-cost':'20'}],['calculateSafetyStock','safety-stock-result',{'ss-max-demand':'120','ss-avg-demand':'100','ss-lead-time':'7'}],['calculateReorderPoint','rop-result',{'rop-demand':'100','rop-lead-time':'5','rop-safety-stock':'50'}]];
  for(const [fn,id,values] of cases){
    for(const [field,value] of Object.entries(values))document.getElementById(field).value=value;
    ctx[fn]();assert.equal(document.getElementById(id).style.display,'block');
    document.getElementById(Object.keys(values)[0]).value='';ctx[fn]();assert.equal(document.getElementById(id).style.display,'none');
  }
  assert.match(page,/addEventListener\('input', \(\) => hideInventoryResult\(resultId\)\)/);assert.match(page,/src="js\/inventory-models.js"/);
});
