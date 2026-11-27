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
