'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('inventory-methodology.html', 'utf8');
function calculator() {
  const nodes = new Map();
  const document = {getElementById(id) {
    if (!nodes.has(id)) nodes.set(id, {value:'', innerHTML:'', textContent:'', addEventListener(type, fn) { this[type] = fn; }});
    return nodes.get(id);
  }};
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
  vm.runInNewContext(scripts.at(-1)[1], { document, Number, parseFloat, isNaN });
  return {nodes, get:id=>document.getElementById(id)};
}
test('inventory audit removes unsupported universal thresholds and mixed-base KSH', () => {
  assert.doesNotMatch(html, /Нормативы \(примерные\)|GMROI &lt; 2|КСХ = \(Р/);
  assert.match(html, /формула и калькулятор удалены/);
  assert.match(html, /при нулевом расходе дни не определены/);
  assert.match(html, /универсального порога «хорошо» нет/);
  assert.ok(Math.abs(29 / (17 / 181) - 308.7647) < 0.001);
});
test('inventory calculators do not classify thresholds and reject invalid inputs', () => {
  const {get} = calculator();
  get('gmroi_profit').value='500000'; get('gmroi_avg_stock').value='250000'; get('calc_gmroi').click();
  assert.match(get('gmroi_result').innerHTML, /GMROI = 2\.00/);
  assert.doesNotMatch(get('gmroi_result').innerHTML, /отлично|норма|плохо/);
  get('gmroi_avg_stock').value='-1'; get('calc_gmroi').click(); assert.match(get('gmroi_result').innerHTML, /корректные/);
  get('depth_stock').value='100'; get('depth_sales_per_day').value='1'; get('calc_depth').click();
  assert.match(get('depth_result').innerHTML, /100\.0 дней/);
  assert.doesNotMatch(get('depth_result').innerHTML, /норм|неликвид/);
  get('depth_stock').value='-1'; get('calc_depth').click(); assert.match(get('depth_result').innerHTML, /корректные/);
  get('mot_bonus').value='70000'; get('mot_obn').value=''; get('mot_mert').value='0.1'; get('mot_cost').value='1'; get('calc_motivation').click();
  assert.match(get('mot_result').textContent, /Введите/);
  get('mot_obn').value='0.2'; get('calc_motivation').click(); assert.match(get('mot_result').innerHTML, /Учебный результат/);
});

test('KPI center rejects missing and invalid values, never saves them, and permits negative cash cycle', () => {
  const page = fs.readFileSync('kpi-center.html','utf8');
  const script = [...page.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
  const nodes = new Map(), stored = new Map();
  const get = id => { if (!nodes.has(id)) nodes.set(id, {value:'',textContent:'',innerHTML:'',addEventListener(){}}); return nodes.get(id); };
  const document = {getElementById:get, querySelectorAll:()=>[]};
  const localStorage = {getItem:()=>null,setItem:(k,v)=>stored.set(k,v)};
  const context = {document,localStorage,alert:()=>{},SCMOTIF:{calculate:()=>null},SCMForecast:{ape:()=>null},Number,Date};
  vm.createContext(context); vm.runInContext(script,context);
  assert.equal(context.calcTurnover(),null);
  get('turnover_cogs').value='100';get('turnover_avg_inv').value='0';assert.equal(context.calcTurnover(),null);
  context.saveKPI('turnover');assert.equal(stored.size,0);
  get('turnover_avg_inv').value='25';assert.equal(context.calcTurnover(),4);
  get('turnover_cogs').value='0';assert.equal(context.calcTurnover(),0);
  get('scm_cost_value').value='10';get('scm_sales').value='0';assert.equal(context.calcSCMCost(),null);
  context.saveKPI('scm_cost');assert.equal(stored.size,0);
  get('scm_sales').value='100';assert.equal(context.calcSCMCost(),10);
  get('scm_cost_value').value='-1';assert.equal(context.calcSCMCost(),null);
  get('c2c_dio').value='10';get('c2c_dso').value='20';get('c2c_dpo').value='40';assert.equal(context.calcC2C(),-10);
  get('c2c_dso').value='';assert.equal(context.calcC2C(),null);context.saveKPI('c2c');assert.equal(stored.size,0);
  get('c2c_dso').value='Infinity';assert.equal(context.calcC2C(),null);
  get('turnover_cogs').value='1e-300'; get('turnover_avg_inv').value='1';context.calcTurnover();assert.match(get('turnover_result').textContent,/e-300/);
  assert.doesNotMatch(page, /условный пример цели|Отличный цикл|запасы замораживают капитал/i);
});

test('platform inventory guide distinguishes SCOR versions and stock classification axes', () => {
  const page=fs.readFileSync('scm-platform/inventory-methodology.html','utf8');
  assert.match(page,/SCOR DS 14\.0/);
  assert.match(page,/В более ранних версиях/);
  assert.match(page,/не являются взаимно исключающей классификацией/);
  assert.match(page,/При нулевых продажах отношение не определено/);
});


test('library versions SCOR accurately and avoids prescriptive 5PL technology claims', () => {
  for (const file of ['library.html','scm-platform/library.html']) {
    const page = fs.readFileSync(file,'utf8');
    assert.match(page,/SCOR DS 14\.0/);
    assert.match(page,/Orchestrate/);
  }
  assert.doesNotMatch(fs.readFileSync('library.html','utf8'),/Экосистема, AI, Big Data, автономизация/);
});
