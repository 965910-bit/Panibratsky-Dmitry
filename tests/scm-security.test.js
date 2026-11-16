'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

for (const name of ['auditor', 'checklists']) {
  test(`${name}: custom items and template names render as text`, () => {
    const html = fs.readFileSync(`scm-platform/${name}.html`, 'utf8');
    const escape = html.match(/function escapeHtml\(value\) \{[^\n]+\}/)[0];
    const render = html.match(/    function renderTemplatesList\(\) \{[\s\S]*?\n    \}\n    function applyTemplate/)[0].replace(/\n    function applyTemplate$/, '');
    const elements = [];
    const context = {
      templates: [{ id: '" onmouseover="bad', name: '<img src=x onerror=bad>', itemIds: ['1'] }],
      document: {
        getElementById: () => ({ innerHTML: '', appendChild: child => elements.push(child) }),
        createElement: () => ({ className: '', innerHTML: '' }),
        querySelectorAll: () => []
      }
    };
    vm.createContext(context);
    vm.runInContext(`${escape}\n${render}\nrenderTemplatesList();`, context);
    assert.doesNotMatch(elements[0].innerHTML, /<img|data-id="" onmouseover/);
    assert.match(elements[0].innerHTML, /&lt;img/);
    assert.match(html, /\$\{escapeHtml\(item\.text\)\} \(\$\{escapeHtml\(item\.unit\)\}\)/);
  });
}

test('report escapes KPI values and handles numbers without dropping zero', () => {
  const html = fs.readFileSync('scm-platform/report-generator.html', 'utf8');
  const escape = html.match(/    function escapeHtml\(value\) \{[\s\S]*?\n    \}/)[0];
  const render = html.match(/    function renderKpiReport\(kpiId, kpiData\) \{[\s\S]*?\n    \}/)[0];
  const context = {};
  vm.createContext(context);
  vm.runInContext(`${escape}\n${render}`, context);
  const output = context.renderKpiReport('<img>', { result: '<img onerror=bad>', timestamp: '2026-01-01', values: { amount: 0 } });
  assert.doesNotMatch(output, /<img/);
  assert.match(output, /&lt;IMG&gt;/);
  assert.match(output, />0<\/td>/);
});
