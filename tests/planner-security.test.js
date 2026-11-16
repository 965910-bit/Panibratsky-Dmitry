'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync('scm-platform/planner.html', 'utf8');
const escapeFunction = html.match(/function escapeHtml\(value\) \{[^\n]+\}/)[0];
const renderFunction = html.match(/    function renderEvents\(\) \{[\s\S]*?\n    \}\n    document\.getElementById\('addEventBtn'\)/)[0].replace(/\n    document\.getElementById\('addEventBtn'\)$/, '');

test('planner escapes event input and imported attribute values', () => {
  const container = { innerHTML: '' };
  const context = {
    document: { getElementById: () => container, querySelectorAll: () => [] },
    dayData: { events: [{ time: '<img src=x onerror=alert(1)>', title: '<b>title</b>', id: '" onmouseover="alert(1)' }] }
  };
  vm.createContext(context);
  vm.runInContext(escapeFunction + '\n' + renderFunction + '\nrenderEvents();', context);
  assert.doesNotMatch(container.innerHTML, /<img|<b>title|data-id="" onmouseover/);
  assert.match(container.innerHTML, /&lt;img/);
  assert.match(container.innerHTML, /&quot; onmouseover=&quot;/);
});
