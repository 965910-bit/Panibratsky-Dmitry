'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const SCMOperationsEstimates=require('../js/operations-estimates.js');
const SCMInventory=require('../js/inventory-models.js');
const cases=[
  ['staff_driver',['200000','45','130','1.15','1.1'],19,['0','45','130','1','1'],0],
  ['gmroi',['2500000','2000000'],1.25,['-50','100'],-0.5],
  ['ccc',['45','30','20'],55,['0','0','20'],-20],
  ['roi_automation',['5000000','1000000'],400,['0','100'],-100],
  ['space_util',['800','1000'],80,['0','100'],0],
  ['pallet_needs',['5000','50','1.2'],120,['0','50','1'],0],
  ['productivity',['12000','150'],80,['0','1'],0],
  ['courier_cost',['2','150','500'],500,['2','0','0'],0],
  ['order_cycle',['4','24','2'],30,['0','0','0'],0],
  ['bep_warehouse',['2000000','50','120'],28572,['0','1','2'],0],
];
test('scenario estimates validate every field and preserve meaningful zero and negative results',()=>{
  const c=SCMOperationsEstimates.calculate;
  for(const [id,valid,expected,zero,z] of cases){
    assert.equal(c(id,valid),expected,id);assert.equal(c(id,zero),z,id);
    for(let i=0;i<valid.length;i++) for(const invalid of ['', '1x', 'Infinity', '1e309','1e-400']) {
      const v=[...valid];v[i]=invalid;assert.equal(c(id,v),null,`${id} field ${i}: ${invalid}`);
    }
    assert.equal(c(id,[]),null);assert.equal(c(id,valid.map(Number)),null);
  }
  const bad=[['staff_driver',['1.2','1','1','1','1']],['staff_driver',['2.00000000000000001','1','1','1','1']],['space_util',['1.00000000000000001','2']],['pallet_needs',['2','1.00000000000000001','1']],['productivity',['2.00000000000000001','1']],['staff_driver',['1','1','0','1','1']],['staff_driver',['1','1','1','1','0.9']],['gmroi',['1','0']],['ccc',['-1','1','1']],['roi_automation',['1','0']],['space_util',['11','10']],['space_util',['1.5','2']],['pallet_needs',['1','0','1']],['pallet_needs',['1','1','0.9']],['productivity',['1','0']],['courier_cost',['0','1','1']],['courier_cost',['1','-1','1']],['order_cycle',['1','-1','1']],['bep_warehouse',['1','2','2']],['bep_warehouse',['1','3','2']],['bep_warehouse',['1e308','0','1']],['gmroi',['1e308','1e-308']],['order_cycle',['1e308','1e308','0']],['courier_cost',['1e-300','1e-300','0']]];
  for(const [id,v] of bad) assert.equal(c(id,v),null,`${id}: ${v}`);
  assert.equal(c('unknown',['1']),null);
});
test('whole-unit ceilings use exact bounded decimal arithmetic',()=>{
  const c=SCMOperationsEstimates.calculate;
  assert.equal(c('bep_warehouse',['0.3','0.3','0.4']),3);
  assert.equal(c('bep_warehouse',['0.30000000000001','0.3','0.4']),4);
  assert.equal(c('pallet_needs',['10','3','1.2']),4);
  assert.equal(c('pallet_needs',['10','3','1.200000000001']),5);
  assert.equal(c('staff_driver',['3','360','1','1','1']),1);
  assert.equal(c('bep_warehouse',['1e-101','0','1']),null);
  assert.equal(c('pallet_needs',['9007199254740991','1','2']),null);
});
function extract(page,name){const m=page.match(new RegExp(`^    function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n    \\}`,'m'));assert.ok(m,name);return m[0];}
test('platform saves only valid versioned estimates, preserves legacy and rejects KPI route',()=>{
  const page=fs.readFileSync('scm-platform/calculators.html','utf8');
  const defs=cases.map(([id])=>{const m=page.match(new RegExp(`        \\{ id: "${id}",[\\s\\S]*?kpiId: null \\}`));assert.ok(m,id);return m[0]});
  const nodes=new Map(),store=new Map(),sent=[];
  const document={getElementById:id=>{if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:''});return nodes.get(id)}};
  const localStorage={getItem:k=>store.get(k)??null,setItem:(k,v)=>store.set(k,v)};
  const ctx={SCMOperationsEstimates,SCMInventory,document,localStorage,alert(){},sendToKPI:(...x)=>sent.push(x)};vm.createContext(ctx);
  vm.runInContext(`let currentBranchId='default';const calculators=[${defs.join(',')}];`+['saveCalculation','handleSave','handleSendToKPI','updateAllCalculators'].map(x=>extract(page,x)).join('\n'),ctx);
  const fields=[['staff_volume','staff_norm','staff_fond','staff_kv','staff_kn'],['gmroi_profit','gmroi_avg'],['ccc_dio','ccc_dso','ccc_dpo'],['roi_saving','roi_cost'],['space_used','space_total'],['pallet_stock','pallet_per','pallet_coef'],['prod_lines','prod_hours'],['courier_weight','courier_rate','courier_min'],['cycle_order','cycle_transit','cycle_last'],['bep_fixed','bep_var','bep_rev']];
  cases.forEach(([id,values,expected],i)=>{
    const old=`calc_${id}_default`,key=`calc_${id}_estimate_v1_default`,event={currentTarget:{getAttribute:k=>k==='data-id'?id:'ccc'}};
    store.set(old,'[{"result":123}]');ctx.handleSave(event);assert.equal(store.has(key),false);
    fields[i].forEach((f,j)=>document.getElementById(f).value=values[j]);
    ctx.updateAllCalculators();ctx.handleSave(event);ctx.handleSendToKPI(event);
    const saved=JSON.parse(store.get(key));assert.equal(saved[0].result,expected);assert.equal(saved[0].method,`scenario-${id}-v1`);assert.equal(store.get(old),'[{"result":123}]');
    document.getElementById(fields[i][0]).value='';ctx.updateAllCalculators();ctx.handleSave(event);assert.match(nodes.get(`result_${id}`).innerHTML,/Проверьте ввод/);assert.equal(JSON.parse(store.get(key)).length,1);
  });
  assert.deepEqual(sent,[]);assert.match(page,/src="\.\.\/js\/operations-estimates.js"/);
});
test('legacy KPI value is assigned as text rather than HTML',()=>{
  const page=fs.readFileSync('scm-platform/calculators.html','utf8'),result={innerHTML:'',children:[],appendChild(child){this.children.push(child)}};
  const document={getElementById:id=>id==='result_example'?result:{value:'1'},createElement:()=>({textContent:''})};
  const ctx={document,SCMData:{loadKPI:()=>({result:'<img src=x onerror=alert(1)>'})}};vm.createContext(ctx);
  vm.runInContext(`let currentBranchId='default';const calculators=[{id:'example',fields:[{id:'x'}],calc:()=>1,unit:'%',kpiId:'x'}];\n${extract(page,'updateAllCalculators')}`,ctx);
  ctx.updateAllCalculators();assert.doesNotMatch(result.innerHTML,/<img/);assert.match(result.children[0].textContent,/<img/);
});
