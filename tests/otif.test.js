'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const SCMOTIF = require('../js/otif.js');

function extract(page, name) {
  const match = page.match(new RegExp(`^    function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n    \\}`, 'm'));
  assert.ok(match, `missing ${name}`);
  return match[0];
}
function storage(initial = {}) {
  const data = new Map(Object.entries(initial));
  return {data, getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value)};
}
function elements() {
  const nodes = new Map();
  return id => {
    if (!nodes.has(id)) nodes.set(id, {value:'', textContent:'', innerHTML:''});
    return nodes.get(id);
  };
}

test('OTIF is a joint order count, validates all inputs and handles zero', () => {
  assert.equal(SCMOTIF.calculate('176', '200'), 88);
  assert.equal(SCMOTIF.calculate('0', '200'), 0);
  assert.equal(SCMOTIF.calculate('200', '200'), 100);
  for (const [a,b] of [['','100'], ['1',''], ['1','0'], ['101','100'], ['-1','10'], ['1.5','10'], ['1e1','100'], ['Infinity','100'], [null,'100'], ['9007199254740992','9007199254740992']]) {
    assert.equal(SCMOTIF.calculate(a,b), null, `${a} / ${b}`);
  }
  // Same marginal rates, different joint counts; multiplication cannot determine OTIF.
  assert.notEqual(SCMOTIF.calculate(90,100), SCMOTIF.calculate(80,100));
});

test('root KPI saves only valid new measurements, never reinterprets legacy data', () => {
  const page = fs.readFileSync('kpi-center.html','utf8');
  const legacy = JSON.stringify({on_time:'90', in_full:'90', result:81});
  const localStorage = storage({kpi_otif: legacy});
  const getElementById = elements();
  const ctx = {SCMOTIF, localStorage, document:{getElementById}, alert:()=>{}};
  vm.createContext(ctx);
  vm.runInContext(['calcOTIF','saveKPI','loadSavedKPIs'].map(n=>extract(page,n)).join('\n'),ctx);
  ctx.loadSavedKPIs();
  assert.equal(getElementById('otif_completed').value, '');
  assert.equal(localStorage.getItem('kpi_otif'), legacy);
  ctx.saveKPI('otif');
  assert.equal(localStorage.getItem('kpi_otif_joint_v1'), null);
  getElementById('otif_completed').value = '0'; getElementById('otif_total').value = '100';
  ctx.saveKPI('otif');
  assert.equal(getElementById('otif_result').textContent, '0.0%');
  assert.equal(JSON.parse(localStorage.getItem('kpi_otif_joint_v1')).method, 'joint-orders-v1');
  getElementById('otif_completed').value = '';
  ctx.loadSavedKPIs();
  assert.equal(getElementById('otif_completed').value, '0');
  assert.equal(localStorage.getItem('kpi_otif'), legacy);
  getElementById('otif_completed').value = '101'; ctx.saveKPI('otif');
  assert.equal(JSON.parse(localStorage.getItem('kpi_otif_joint_v1')).result, 0);
  assert.match(page, /src="js\/otif.js"/);
});

test('platform calculator validates, displays and stores new results separately from old data', () => {
  const page = fs.readFileSync('scm-platform/calculators.html','utf8');
  const definition = page.match(/        \{ id: "otif",[\s\S]*?kpiId: null \},/);
  assert.ok(definition);
  const legacy = JSON.stringify([{values:[90,90],result:81}]);
  const localStorage = storage({calc_otif_default:legacy});
  const getElementById = elements();
  const alerts = [];
  const ctx = {SCMOTIF, localStorage, document:{getElementById}, alert:s=>alerts.push(s)};
  vm.createContext(ctx);
  vm.runInContext(`let currentBranchId = 'default'; const calculators = [${definition[0]}];\n` + ['saveCalculation','handleSave','updateAllCalculators'].map(n=>extract(page,n)).join('\n'),ctx);
  const event = {currentTarget:{getAttribute:()=> 'otif'}};
  ctx.updateAllCalculators(); ctx.handleSave(event);
  assert.match(getElementById('result_otif').innerHTML, /Введите корректные/);
  assert.equal(localStorage.getItem('calc_otif_joint_v1_default'), null);
  getElementById('otif_completed').value = '176'; getElementById('otif_total').value = '200';
  ctx.updateAllCalculators(); ctx.handleSave(event);
  assert.match(getElementById('result_otif').innerHTML, /<strong>88<\/strong>/);
  const saved = JSON.parse(localStorage.getItem('calc_otif_joint_v1_default'));
  assert.equal(saved[0].result, 88); assert.equal(saved[0].method, 'joint-orders-v1');
  assert.equal(localStorage.getItem('calc_otif_default'), legacy);
  getElementById('otif_completed').value = '201'; ctx.handleSave(event);
  assert.equal(JSON.parse(localStorage.getItem('calc_otif_joint_v1_default')).length, 1);
  assert.match(page, /src="\.\.\/js\/otif.js"/);
});
