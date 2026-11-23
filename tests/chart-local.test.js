'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const Chart = require('../js/vendor/chart.umd-4.6.1.js');

// Exercise the actual vendored Chart.js in Node with an in-memory canvas.
// This does not test browser rendering, fonts, responsive layout, or accessibility.
function createCanvas() {
  const canvas = {width: 400, height: 200, style: {}, getAttribute: () => null,
    setAttribute() {}, removeAttribute() {}, addEventListener() {}, removeEventListener() {}};
  const context = new Proxy({canvas, length: undefined, measureText: text => ({width: String(text).length * 8}),
    setLineDash() {}, getLineDash: () => []}, {
    get(target, property) {return property in target ? target[property] : () => {};},
    set(target, property, value) {target[property] = value; return true;}
  });
  canvas.getContext = () => context;
  return canvas;
}
function extract(page, name, indent) {
  const match = page.match(new RegExp(`^${' '.repeat(indent)}function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n${' '.repeat(indent)}\\}`, 'm'));
  assert.ok(match, `missing ${name}`);
  return match[0];
}
function chartConstructor(created) {
  return function ChartForTest(target, configuration) {
    const options = {...configuration.options, responsive: false, animation: false};
    const chart = new Chart(target, {...configuration, options});
    created.push(chart);
    return chart;
  };
}
function testRedraw(ctx, method, created) {
  ctx[method]();
  const first = created.at(-1);
  assert.ok(first && first.canvas);
  assert.equal(first.config.type, 'line');
  ctx[method]();
  assert.equal(first.canvas, null, 'previous chart must be destroyed');
  const second = created.at(-1);
  assert.notEqual(second, first);
  assert.ok(second.canvas);
  return second;
}

test('admin chart and forecast work with the local Chart.js build', () => {
  const page = fs.readFileSync('admin.html', 'utf8');
  const canvas = createCanvas();
  const created = [];
  const ctx = {Chart: chartConstructor(created), document: {getElementById: () => canvas},
    getData: () => [{timestamp:'2026-11-01T10:00:00Z'}, {timestamp:'2026-11-02T10:00:00Z'}],
    filterByDate: data => data, currentDateFrom: new Date('2026-11-01T00:00:00Z'), currentDateTo: new Date('2026-11-08T00:00:00Z')};
  vm.createContext(ctx);
  vm.runInContext('let viewsChart = null;\n' + extract(page, 'linearRegression', 8) + '\n' + extract(page, 'renderChartWithForecast', 8), ctx);
  const chart = testRedraw(ctx, 'renderChartWithForecast', created);
  assert.equal(chart.data.labels.length, 15);
  assert.equal(chart.data.datasets.length, 2);
  assert.equal(chart.data.datasets[0].data[0], 1);
  chart.destroy();
});

test('SCM KPI history chart works with the local Chart.js build', () => {
  const page = fs.readFileSync('scm-platform/kpi-center.html', 'utf8');
  const canvas = createCanvas(), created = [];
  const ctx = {Chart: chartConstructor(created), window: {},
    document: {getElementById: id => id === 'kpiSelect' ? {value: 'otif'} : canvas},
    getHistory: () => [{date:'2026-11-01', value:92}, {date:'2026-11-02', value:95}],
    kpiDefinitions: {otif: {name:'OTIF'}}};
  vm.createContext(ctx); vm.runInContext(extract(page, 'updateChart', 4), ctx);
  const chart = testRedraw(ctx, 'updateChart', created);
  assert.equal(chart.data.datasets[0].label, 'OTIF');
  assert.deepEqual(Array.from(chart.data.datasets[0].data), [92, 95]);
  chart.destroy();
});

test('SCM dashboard multi-KPI chart works with the local Chart.js build', () => {
  const page = fs.readFileSync('scm-platform/dashboard.html', 'utf8');
  const canvas = createCanvas(), created = [];
  const nodes = {kpiMultiSelect: {selectedOptions: [{value:'otif'}, {value:'fill'}]}, periodSelect: {value:'30'}, multiKpiChart: canvas};
  const date = new Date().toISOString();
  const ctx = {Chart: chartConstructor(created), document: {getElementById: id => nodes[id]},
    getKPIHistory: kpi => [{date, value: kpi === 'otif' ? 92 : 85}]};
  vm.createContext(ctx); vm.runInContext('let multiChart = null;\n' + extract(page, 'updateMultiChart', 4), ctx);
  const chart = testRedraw(ctx, 'updateMultiChart', created);
  assert.equal(chart.data.datasets.length, 2);
  assert.deepEqual(Array.from(chart.data.datasets, dataset => dataset.data[0]), [92, 85]);
  chart.destroy();
});
