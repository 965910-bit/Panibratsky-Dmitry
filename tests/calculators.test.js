const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const html = fs.readFileSync('calculators.html', 'utf8');
const scripts = [...html.matchAll(/<script(?![^>]*(?:src|application\/ld\+json))[^>]*>([\s\S]*?)<\/script>/gi)];
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, { value: '', textContent: '', style: {} });
  return elements.get(id);
}
let alerts = [];
const context = { document: { getElementById: element, addEventListener() {} }, alert: text => alerts.push(text), console, Number, Math, SCMInventory: require('../js/inventory-models.js'), SCMInventoryMetrics: require('../js/inventory-metrics.js') };
vm.createContext(context);
for (const match of scripts) vm.runInContext(match[1], context);
function set(id, value) { element(id).value = String(value); }
set('ss-max-demand', 120); set('ss-avg-demand', 100); set('ss-lead-time', 7);
context.calculateSafetyStock();
assert.strictEqual(element('safety-stock-value').textContent, '140 единиц');
assert.match(element('safety-stock-explanation').textContent, /не гарантирует/);
set('ss-max-demand', 90); alerts = []; context.calculateSafetyStock(); assert.strictEqual(alerts.length, 1);
set('rop-demand', 100); set('rop-lead-time', 5); set('rop-safety-stock', 0); alerts = [];
context.calculateReorderPoint(); assert.strictEqual(alerts.length, 0); assert.strictEqual(element('rop-value').textContent, '500 единиц');
set('fill-total-demand', 100); set('fill-stockouts', 0); context.calculateFillRate();
assert.strictEqual(element('fill-rate-value').textContent, '100.00%');
set('transp-distance', 500); set('transp-rate', 15); set('transp-additional', 2000); context.calculateTransportCost();
assert.match(element('transport-cost-explanation').textContent, /9500|9,500|9 500/);
set('eoq-demand', -1); set('eoq-order-cost', 500); set('eoq-holding-cost', 20); alerts = [];
context.calculateEOQ(); assert.strictEqual(alerts.length, 1);
console.log('Calculator scenarios passed');
