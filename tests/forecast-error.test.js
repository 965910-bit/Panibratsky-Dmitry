'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const SCMForecast = require('../js/forecast-error.js');
function extract(page, name) {
  const match = page.match(new RegExp(`^    function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n    \\}`, 'm'));
  assert.ok(match, name); return match[0];
}
function storage(initial = {}) {
  const data = new Map(Object.entries(initial));
  return {data, getItem:key=>data.get(key) ?? null, setItem:(key,value)=>data.set(key,value)};
}
function elements() {
  const nodes = new Map();
  return id => {if (!nodes.has(id)) nodes.set(id,{value:'',textContent:'',innerHTML:''}); return nodes.get(id);};
}

test('one-observation APE handles zero, invalid and extreme values', () => {
  assert.equal(SCMForecast.ape('1000','850'), 15);
  assert.equal(SCMForecast.ape('100','300'), 200);
  assert.equal(SCMForecast.ape('100','0'), 100);
  assert.equal(SCMForecast.ape('1e2','100'), 0);
  assert.equal(SCMForecast.ape('0.0001','0.001'), 900);
  for (const [a,b] of [['','100'],['100',''],['0','0'],['-1','5'],['1','-1'],['1','Infinity'],['1e999','0'],['abc','1'],['1x','2'],['0x10','1'],['1e-320','1'],[null,'1'],['1',undefined]]) {
    assert.equal(SCMForecast.ape(a,b),null,`${a}/${b}`);
  }
});

test('root KPI preserves legacy accuracy and saves only valid single-observation APE', () => {
  const page = fs.readFileSync('kpi-center.html','utf8');
  const legacy = JSON.stringify({actual:'0', predicted:'10', result:'0.0'});
  const localStorage = storage({kpi_forecast:legacy});
  const getElementById = elements();
  const ctx = {SCMForecast, localStorage, document:{getElementById}, alert:()=>{}};
  vm.createContext(ctx);
  vm.runInContext(['calcForecast','saveKPI','loadSavedKPIs'].map(extract.bind(null,page)).join('\n'),ctx);
  ctx.loadSavedKPIs();
  assert.equal(getElementById('forecast_actual').value, '');
  getElementById('forecast_actual').value='0'; getElementById('forecast_predicted').value='10';
  ctx.saveKPI('forecast'); assert.equal(localStorage.getItem('kpi_forecast_ape_v1'),null);
  assert.equal(getElementById('forecast_result').textContent,'—');
  getElementById('forecast_actual').value='100'; getElementById('forecast_predicted').value='300';
  ctx.saveKPI('forecast'); assert.equal(getElementById('forecast_result').textContent,'200.0%');
  const saved = JSON.parse(localStorage.getItem('kpi_forecast_ape_v1'));
  assert.equal(saved.method,'single-ape-v1'); assert.equal(saved.result,200);
  assert.equal(localStorage.getItem('kpi_forecast'),legacy);
  getElementById('forecast_predicted').value='0'; ctx.saveKPI('forecast');
  getElementById('forecast_predicted').value=''; ctx.loadSavedKPIs();
  assert.equal(getElementById('forecast_predicted').value,'0');
  assert.equal(getElementById('forecast_result').textContent,'100.0%');
  assert.match(page,/src="js\/forecast-error.js"/);
});

test('platform calculator validates and saves APE separately, never routes it to KPI', () => {
  const page=fs.readFileSync('scm-platform/calculators.html','utf8');
  const definition=page.match(/        \{ id: "mape",[\s\S]*?kpiId: null \},/);
  assert.ok(definition);
  const legacy=JSON.stringify([{values:[0,1],result:null}]);
  const localStorage=storage({calc_mape_default:legacy});
  const getElementById=elements(), alerts=[], sends=[];
  const ctx={SCMForecast,localStorage,document:{getElementById},alert:s=>alerts.push(s),sendToKPI:(...args)=>sends.push(args)};
  vm.createContext(ctx);
  vm.runInContext(`let currentBranchId = 'default'; const calculators = [${definition[0]}];\n` + ['saveCalculation','handleSave','handleSendToKPI','updateAllCalculators'].map(extract.bind(null,page)).join('\n'),ctx);
  const event={currentTarget:{getAttribute:attr=>attr==='data-id'?'mape':'otif'}};
  ctx.updateAllCalculators(); ctx.handleSave(event); ctx.handleSendToKPI(event);
  assert.match(getElementById('result_mape').innerHTML,/Введите конечные/);
  assert.equal(localStorage.getItem('calc_ape_v1_default'),null);
  assert.deepEqual(sends,[]);
  getElementById('mape_actual').value='100'; getElementById('mape_forecast').value='300';
  ctx.updateAllCalculators(); ctx.handleSave(event);
  assert.match(getElementById('result_mape').innerHTML,/<strong>200<\/strong>/);
  const saved=JSON.parse(localStorage.getItem('calc_ape_v1_default'));
  assert.equal(saved[0].method,'single-ape-v1'); assert.equal(saved[0].result,200);
  assert.equal(localStorage.getItem('calc_mape_default'),legacy);
  getElementById('mape_actual').value='0'; ctx.handleSave(event);
  assert.equal(JSON.parse(localStorage.getItem('calc_ape_v1_default')).length,1);
  getElementById('mape_actual').value='100'; getElementById('mape_forecast').value='99.996'; ctx.handleSave(event);
  assert.ok(JSON.parse(localStorage.getItem('calc_ape_v1_default'))[1].result > 0);
  getElementById('mape_forecast').value='1e30'; ctx.updateAllCalculators();
  assert.match(getElementById('result_mape').innerHTML, /<strong>1e\+30<\/strong>/);
  getElementById('mape_forecast').value='1e308'; ctx.handleSave(event);
  assert.ok(Number.isFinite(JSON.parse(localStorage.getItem('calc_ape_v1_default'))[2].result));
  assert.match(page,/src="\.\.\/js\/forecast-error.js"/);
});

test('audit and checklist identify MAPE as an error and disclose unverified scoring', () => {
  const checklists=fs.readFileSync('scm-platform/checklists.html','utf8');
  const auditor=fs.readFileSync('scm-platform/auditor.html','utf8');
  assert.match(checklists,/Средняя абсолютная процентная ошибка прогноза спроса \(MAPE\)/);
  for (const page of [checklists,auditor]) assert.match(page,/пороги не подтверждены как отраслевые нормы/);
});
