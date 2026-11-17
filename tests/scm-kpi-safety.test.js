'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const page = fs.readFileSync('scm-platform/kpi-center.html', 'utf8');
function extract(name) {
  const match = page.match(new RegExp(`^    function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n    \\}`, 'm'));
  assert.ok(match, name); return match[0];
}
function harness(initial) {
  const store = new Map(Object.entries(initial));
  let writes = 0, chartUpdates = 0;
  const nodes = new Map();
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, {value:'', textContent:'', innerHTML:''});
    return nodes.get(id);
  };
  node('categoryFilter').value = 'all'; node('kpiSelect').value = 'otd';
  let cards = [];
  const grid = node('kpiGrid');
  Object.defineProperty(grid, 'innerHTML', {set() {cards = [];}, get() {return '';}});
  grid.appendChild = card => {
    cards.push(card);
    for (const match of card.innerHTML.matchAll(/id="([^"]+)"/g)) nodes.set(match[1], {value:'', textContent:'', innerHTML:''});
  };
  function button() {return {addEventListener(type, fn) {this.handler = fn;}, click() {this.handler();}};}
  const document = {
    getElementById: node,
    createElement: () => {
      const buttons = {'.calc-kpi': button(), '.print-kpi-btn': button()};
      return {innerHTML:'', setAttribute() {}, querySelector: name => buttons[name], buttons};
    }
  };
  const get = (key, fallback) => store.has(key) ? JSON.parse(store.get(key)) : fallback;
  const set = (key, value) => {writes++; store.set(key, JSON.stringify(value));};
  const SCMData = {
    loadKPI: (id, branch) => get(`kpi_${id}_${branch}`, branch === 'default' ? get(`kpi_${id}`, null) : null),
    saveKPI: (id, value, branch) => set(`kpi_${id}_${branch}`, value),
    getKPIHistory: (id, branch) => get(`kpi_${id}_${branch}_history`, branch === 'default' ? get(`kpi_${id}_history`, []) : []),
    saveKPIHistory: (id, history, branch) => set(`kpi_${id}_${branch}_history`, history)
  };
  const localStorage = {setItem: (key, value) => {writes++; store.set(key, value);}, getItem: key => store.get(key) ?? null};
  class FileReader {readAsText(file) {this.onload({target:{result:file}});}}
  const context = {document, SCMData, localStorage, FileReader, alert:()=>{}, window:{open(){}}, updateChart:()=>{chartUpdates++;}};
  vm.createContext(context);
  const definitions = page.match(/    const kpiDefinitions = \{[\s\S]*?\n    \};/)[0];
  vm.runInContext(definitions + '\nlet currentBranchId = "default";\n' +
    ['saveHistory','getHistory','createKPICard','renderKPICards','importKPI'].map(extract).join('\n') +
    '\nfunction updateChartOptions() {}', context);
  return {context, node, store, cards:()=>cards, writes:()=>writes, chartUpdates:()=>chartUpdates,
    branch: id => vm.runInContext(`currentBranchId = ${JSON.stringify(id)}`, context),
    click: id => cards.find(card => card.innerHTML.includes(`data-kpi="${id}"`)).buttons['.calc-kpi'].click()};
}

test('render, filters and branch changes never save, rewrite history or create tasks', () => {
  const snapshot = {
    kpi_otd_default: JSON.stringify({result:78, values:{otd_val:'78'}, timestamp:'2020-01-01'}),
    kpi_co2_default: JSON.stringify({result:0.15, values:{calculated:0.15,source:'calculator'}, timestamp:'2020-01-01'}),
    kpi_otd_default_history: JSON.stringify([{value:78,date:'2020-01-01'}]),
    kpi_otd_other: JSON.stringify({result:99, values:{otd_val:'99'}}),
    scm_planner_tasks_v5_default: JSON.stringify({backlog:[{id:'auto_kpi_otd_old',text:'old'}]})
  };
  const h = harness(snapshot);
  h.context.renderKPICards();
  assert.equal(h.node('result_otd').textContent, '78 %');
  assert.equal(h.node('result_co2').textContent, '0.15 кг/(т·км)');
  assert.equal(h.node('co2_val_co2').value, '', 'calculator-derived saved value must not be replaced with zero');
  h.node('categoryFilter').value = 'esg'; h.context.renderKPICards();
  h.node('categoryFilter').value = 'all'; h.context.renderKPICards();
  h.branch('other'); h.context.renderKPICards(); assert.equal(h.node('result_otd').textContent, '99 %');
  h.branch('default'); h.context.renderKPICards();
  assert.equal(h.writes(),0);
  assert.deepEqual(Object.fromEntries(h.store), snapshot);
});

test('explicit save validates input, keeps fractional values and does not create planner tasks', () => {
  const old = JSON.stringify([{value:0.12,date:'2020-01-01'}]);
  const tasks = JSON.stringify({backlog:[{id:'old'}]});
  const h = harness({kpi_co2_history:old, scm_planner_tasks_v5_default:tasks});
  h.context.renderKPICards();
  h.click('co2'); assert.equal(h.writes(),0);
  h.node('co2_val_co2').value = 'Infinity'; h.click('co2'); assert.equal(h.writes(),0);
  h.node('co2_val_co2').value = '0.15'; h.click('co2');
  assert.equal(JSON.parse(h.store.get('kpi_co2_default')).result, 0.15);
  assert.deepEqual(JSON.parse(h.store.get('kpi_co2_default_history')).map(e=>e.value), [0.12,0.15]);
  assert.equal(h.store.get('kpi_co2_history'), old);
  assert.equal(h.store.get('scm_planner_tasks_v5_default'), tasks);
  assert.equal(h.node('result_co2').textContent, '0.15 кг/(т·км)');
  h.node('co2_val_co2').value = '0'; h.click('co2');
  assert.equal(JSON.parse(h.store.get('kpi_co2_default')).result, 0);
  const saved = h.store.get('kpi_co2_default');
  h.node('co2_val_co2').value = ''; h.click('co2');
  assert.equal(h.store.get('kpi_co2_default'), saved);
  h.context.renderKPICards(); assert.equal(h.node('co2_val_co2').value, '0');
});

test('import displays exact saved result without generating history or tasks', () => {
  const tasks = JSON.stringify({backlog:[{id:'old'}]});
  const h = harness({scm_planner_tasks_v5_default:tasks});
  const payload = {otd:{result:77.2, values:{otd_val:'77.2'},timestamp:'2020-01-01'}, otd_history:[{value:75,date:'2020-01-01'}]};
  h.context.importKPI(JSON.stringify(payload));
  assert.deepEqual(JSON.parse(h.store.get('kpi_otd_default_history')),payload.otd_history);
  assert.equal(JSON.parse(h.store.get('kpi_otd_default')).result,77.2);
  assert.equal(h.node('result_otd').textContent,'77.2 %');
  assert.equal(h.store.get('scm_planner_tasks_v5_default'),tasks);
  assert.equal(h.writes(),2);
});

test('existing values are rendered as text and not interpreted as markup', () => {
  const h = harness({kpi_otd_default:JSON.stringify({result:'<img src=x>',values:{}})});
  h.context.renderKPICards();
  assert.equal(h.node('result_otd').textContent,'<img src=x> %');
  assert.equal(h.node('result_otd').innerHTML,'');
  assert.equal(h.writes(),0);
});
