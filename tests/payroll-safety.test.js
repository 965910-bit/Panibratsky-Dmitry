'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const page = name => fs.readFileSync(`scm-platform/${name}.html`,'utf8');
test('unsupported payroll calculator and staff-derived totals are suspended',()=>{
  const calc=page('calculators'), branches=page('branches'), dashboard=page('dashboard');
  assert.doesNotMatch(calc, /id: "salary_north"/);
  assert.match(calc,/прежняя формула начисляла коэффициент и надбавку друг на друга/);
  assert.match(branches,/row\.insertCell\(6\)\.textContent = 'Приостановлен'/);
  assert.doesNotMatch(branches,/const total = \(pos\.salary_base/);
  assert.doesNotMatch(dashboard,/totalPayrollPlan/);
  for (const content of [calc,branches,page('standards')]) assert.match(content,/xn--80akibcicpdbetz7e2g\.xn--p1ai\/questions\/viewFaq\/1159/);
});
test('dashboard displays explicit input budget, not calculated staff salary',()=>{
  const html=page('dashboard');
  const match=html.match(/^    function renderBudgetStaff\(\) \{[\s\S]*?\n    \}/m); assert.ok(match);
  const node={innerHTML:''};
  const context={document:{getElementById:()=>node},getBranchBudget:()=>Object.fromEntries(['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'].map(m=>[m,{opex:1,payroll:1234,transport:2,capex:3}])),getBranchStaff:()=>[{salary_base:50000,region_coef:1.5,north_bonus:80,count:1}],currentBranchId:'default',Date,escapeHtml: value=>String(value??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))};
  vm.createContext(context);vm.runInContext(match[0],context);context.renderBudgetStaff();
  assert.match(node.innerHTML,/ФОТ \(введённый бюджет\)/);
  assert.match(node.innerHTML,/автоматический расчёт ФОТ приостановлен/);
  assert.doesNotMatch(node.innerHTML,/135.?000|115.?000/);
});
