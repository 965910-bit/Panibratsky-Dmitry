'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const SCMDimensionalWeight=require('../js/dimensional-weight.js');
function extract(page,name) {
  const m=page.match(new RegExp(`^    function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n    \\}`,'m'));
  assert.ok(m,name); return m[0];
}
test('compares unrounded dimensional and actual mass, rejecting invalid inputs',()=>{
  const calc=SCMDimensionalWeight.compare;
  assert.equal(calc(['36','25','16','2','5000']),2.88);
  assert.equal(calc(['36','25','16','4','5000']),4);
  assert.equal(calc(['10','10','10','0.1','5000']),0.2);
  for (const values of [[],['0','1','1','1','5000'],['1','1','1','0','5000'],['1','1','1','1','0'],['','1','1','1','1'],['1','2','3','4','-1'],['1','2','3','4','foo'],['1x','2','3','4','5'],['1','2','3','4','Infinity'],['1e308','1e308','2','1','1'],['1e-300','1e-300','1','1','1'],[1,'1','1','1','1']]) assert.equal(calc(values),null,JSON.stringify(values));
});
test('platform rejects invalid entries, preserves legacy and never sends estimate to KPI',()=>{
  const page=fs.readFileSync('scm-platform/calculators.html','utf8');
  const def=page.match(/        \{ id: "dim_weight",[\s\S]*?kpiId: null \},/); assert.ok(def);
  const old='[{"result":null}]', map=new Map([['calc_dim_weight_default',old]]), nodes=new Map(), alerts=[], sends=[];
  const document={getElementById:id=>{if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:''});return nodes.get(id)}};
  const localStorage={getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,v)};
  const ctx={SCMDimensionalWeight,document,localStorage,alert:a=>alerts.push(a),sendToKPI:(...a)=>sends.push(a)};
  vm.createContext(ctx);
  vm.runInContext(`let currentBranchId='default'; const calculators=[${def[0]}];\n`+['saveCalculation','handleSave','handleSendToKPI','updateAllCalculators'].map(x=>extract(page,x)).join('\n'),ctx);
  const event={currentTarget:{getAttribute:k=>k==='data-id'?'dim_weight':'otif'}};
  ctx.updateAllCalculators();ctx.handleSave(event);ctx.handleSendToKPI(event);
  assert.match(nodes.get('result_dim_weight').innerHTML,/Введите положительные/);
  assert.equal(map.get('calc_dim_weight_v1_default'),undefined);assert.deepEqual(sends,[]);
  for(const [id,value] of Object.entries({dim_l:'36',dim_w:'25',dim_h:'16',dim_actual:'2',dim_coef:'5000'})) document.getElementById(id).value=value;
  ctx.updateAllCalculators();ctx.handleSave(event);
  assert.match(nodes.get('result_dim_weight').innerHTML,/<strong>2\.88<\/strong> кг/);
  const saved=JSON.parse(map.get('calc_dim_weight_v1_default'));
  assert.equal(saved[0].result,2.88);assert.equal(saved[0].method,'unrounded-package-comparison-v1');assert.equal(map.get('calc_dim_weight_default'),old);
  document.getElementById('dim_coef').value='0';ctx.handleSave(event);assert.equal(JSON.parse(map.get('calc_dim_weight_v1_default')).length,1);
  document.getElementById('dim_coef').value='1'; document.getElementById('dim_l').value='1e30'; ctx.updateAllCalculators();
  assert.match(nodes.get('result_dim_weight').innerHTML,/e\+32/);
  assert.match(page,/src="\.\.\/js\/dimensional-weight.js"/);
  assert.doesNotMatch(def[0],/5000 для авиа|6000 для авто/);
});
