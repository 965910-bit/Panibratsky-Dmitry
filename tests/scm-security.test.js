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

for (const name of ['admin.html', 'js/analytics.js']) {
  test(`${name}: stored analytics fields and map popups are escaped`, () => {
    const html = fs.readFileSync(name, 'utf8');
    const fn = name => {
      const match = html.match(new RegExp(`        function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n        \\}`));
      assert.ok(match, `missing ${name}`);
      return match[0];
    };
    const tables = Object.fromEntries(['sessions', 'downloads', 'pageViews', 'cities'].map(x => [`#${x}Table tbody`, {innerHTML: ''}]));
    let popup = '';
    const data = {
      sessions: [{city: '<svg>', country: '<img>', region: '<script>', lat: 55, lon: 37, referrer: 'ok', userAgent: 'browser'}],
      downloads: [{sessionId: '<img/x>', fileName: 'file', timestamp: '2026-01-01'}],
      pageViews: [{sessionId: '<svg/x>', page: '/', timestamp: '2026-01-01'}]
    };
    const context = {
      document: {querySelector: selector => tables[selector]},
      getData: key => data[key] || [], filterByDate: rows => rows,
      L: {
        map: () => ({setView() {return this;}, addLayer() {}}),
        tileLayer: () => ({addTo() {}}),
        markerClusterGroup: () => ({addLayer() {}}),
        marker: () => ({bindPopup(html) {popup = html;}})
      },
      russiaMap: undefined, markerCluster: undefined
    };
    vm.createContext(context);
    vm.runInContext(['escapeHtml', 'renderSessions', 'renderDownloads', 'renderPageViews', 'renderRussiaMap'].map(fn).join('\n') +
      '\nrenderSessions(); renderDownloads(); renderPageViews(); renderRussiaMap();', context);
    for (const value of [...Object.values(tables).map(t => t.innerHTML), popup]) {
      assert.doesNotMatch(value, /<svg|<img|<script>/i);
    }
    assert.match(tables['#sessionsTable tbody'].innerHTML, /&lt;svg&gt;/);
    assert.match(tables['#sessionsTable tbody'].innerHTML, /&lt;img&gt;/);
    assert.match(tables['#downloadsTable tbody'].innerHTML, /&lt;img\/x&gt;/);
    assert.match(tables['#pageViewsTable tbody'].innerHTML, /&lt;svg\/x&gt;/);
    assert.match(popup, /&lt;svg&gt;/);
    assert.match(popup, /&lt;script&gt;/);
  });
}

test('library search highlights text without parsing markup and removes only its own highlights', () => {
  const html = fs.readFileSync('library.html', 'utf8');
  const code = html.match(/        function removeHighlights\(container\) \{[\s\S]*?(?=        function performSearch\(\))/)[0];
  class FakeNode {
    constructor(type, tag = '') {this.nodeType = type; this.tagName = tag.toUpperCase(); this.childNodes = []; this.parentNode = null; this.attributes = {}; this.value = '';}
    appendChild(node) { node.parentNode = this; this.childNodes.push(node); return node; }
    setAttribute(name, value) {this.attributes[name] = value;}
    get textContent() {return this.nodeType === 3 ? this.value : this.childNodes.map(node => node.textContent).join('');}
    set textContent(value) {this.childNodes = []; if (this.nodeType === 3) this.value = String(value); else this.appendChild(text(value));}
    replaceChild(replacement, old) {
      const index = this.childNodes.indexOf(old);
      assert.notEqual(index, -1);
      const nodes = replacement.nodeType === 11 ? replacement.childNodes : [replacement];
      nodes.forEach(node => {node.parentNode = this;});
      this.childNodes.splice(index, 1, ...nodes);
      old.parentNode = null;
    }
    normalize() {
      const merged = [];
      for (const node of this.childNodes) {
        if (node.nodeType === 3 && merged.at(-1)?.nodeType === 3) merged.at(-1).value += node.value;
        else merged.push(node);
      }
      this.childNodes = merged;
    }
    querySelectorAll(selector) {
      assert.equal(selector, 'mark[data-search-highlight]');
      const found = [];
      const visit = node => {if (node.tagName === 'MARK' && Object.hasOwn(node.attributes, 'data-search-highlight')) found.push(node); node.childNodes.forEach(visit);};
      visit(this); return found;
    }
  }
  function text(value) {const node = new FakeNode(3); node.value = value; return node;}
  const document = {createTextNode: text, createDocumentFragment: () => new FakeNode(11), createElement: tag => new FakeNode(1, tag)};
  const context = {document, Node: {TEXT_NODE: 3, ELEMENT_NODE: 1}};
  vm.createContext(context);
  vm.runInContext(code, context);
  const root = new FakeNode(1, 'div');
  const authored = new FakeNode(1, 'mark'); authored.textContent = 'сохранить'; root.appendChild(authored);
  const source = '<img src=x onerror=alert(1)> склад [склад] СКЛАД'; root.appendChild(text(source));
  context.highlightText(root, 'склад');
  assert.equal(root.textContent, 'сохранить' + source);
  assert.equal(root.querySelectorAll('mark[data-search-highlight]').length, 3);
  assert.deepEqual(root.childNodes.filter(node => node.nodeType === 1).map(node => node.tagName), ['MARK', 'MARK', 'MARK', 'MARK']);
  context.removeHighlights(root);
  assert.equal(root.textContent, 'сохранить' + source);
  assert.equal(root.childNodes[0], authored);
  context.highlightText(root, '[склад]');
  assert.equal(root.querySelectorAll('mark[data-search-highlight]').length, 1);
  assert.equal(root.querySelectorAll('mark[data-search-highlight]')[0].textContent, '[склад]');
  context.removeHighlights(root);
  assert.equal(root.textContent, 'сохранить' + source);
});
