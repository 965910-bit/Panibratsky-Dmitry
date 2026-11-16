'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync('trends.html', 'utf8');
const load = html.match(/        async function loadNews\(\) \{[\s\S]*?\n        \}\n\n        function applyFilters/)[0].replace(/\n\n        function applyFilters$/, '');
function setup(fetch, applyFilters) {
  const list = { childNodes: [{ text: 'static snapshot' }], replaceChildren(...nodes) { this.childNodes = nodes; } };
  const pagination = { childNodes: [], replaceChildren(...nodes) { this.childNodes = nodes; } };
  const status = { textContent: '' };
  const context = { fetch, URL, Date, console: { error() {} }, document: { getElementById(id) { return { 'news-list': list, pagination, 'news-status': status }[id]; } }, applyFilters: () => applyFilters(list) };
  vm.createContext(context);
  vm.runInContext('let allNews = [], filteredNews = [], currentPage = 1;\n' + load, context);
  return { context, list, status };
}
test('news retains static snapshot on fetch error, empty data, or render failure', async () => {
  for (const [fetch, render] of [
    [async () => { throw Error('offline'); }, () => {}],
    [async () => ({ ok: true, json: async () => [] }), () => {}],
    [async () => ({ ok: true, json: async () => [{ link: 'https://example.com/' }] }), list => { list.childNodes = [{ text: 'partial' }]; throw Error('render'); }]
  ]) {
    const { context, list, status } = setup(fetch, render);
    assert.equal(await context.loadNews(), false);
    assert.equal(list.childNodes[0].text, 'static snapshot');
    assert.match(status.textContent, /Не удалось обновить/);
  }
});
test('news success clears warning', async () => {
  const { context, status } = setup(async () => ({ ok: true, json: async () => [{ link: 'https://example.com/' }] }), () => {});
  status.textContent = 'old warning';
  assert.equal(await context.loadNews(), true);
  assert.equal(status.textContent, '');
});
test('checklist defaults to an honest unavailable state', () => {
  const page = fs.readFileSync('checklist.html', 'utf8');
  assert.match(page, /Чек-лист временно недоступен/);
  assert.match(page, /id="saveBtn" disabled/);
  assert.match(page, /await import\('\.\/firebase-config\.js'\)/);
});
test('news displays an honest placeholder for missing or invalid publication dates', () => {
  const render = html.match(/        function renderNews\(\) \{[\s\S]*?\n        \}\n\n        function shareHandler/)[0].replace(/\n\n        function shareHandler$/, '');
  const escape = html.match(/        function escapeHtml\(str\) \{[\s\S]*?\n        \}/)[0];
  const list = { innerHTML: '' }, pagination = { innerHTML: '' };
  const context = { Date, Number, Math, parseInt, filteredNews: [
    { link: 'https://example.com/a', title: 'A', pubDate: '', tags: [] },
    { link: 'https://example.com/b', title: 'B', pubDate: 'bad date', tags: [] }
  ], currentPage: 1, perPage: 10, localStorage: { getItem: () => null },
    document: { getElementById: id => id === 'news-list' ? list : pagination, querySelectorAll: () => [] },
    renderPagination() {}, shareHandler() {}, likeHandler() {} };
  vm.createContext(context); vm.runInContext(escape + '\n' + render + '\nrenderNews();', context);
  assert.equal((list.innerHTML.match(/Дата не указана/g) || []).length, 2);
  assert.doesNotMatch(list.innerHTML, /Invalid Date/);
});
