'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync('trends.html', 'utf8');
const validNewsUrl = html.match(/        function isSafeNewsUrl\(value\) \{[\s\S]*?\n        \}/)[0];
const load = html.match(/        async function loadNews\(\) \{[\s\S]*?\n        \}\n\n        function applyFilters/)[0].replace(/\n\n        function applyFilters$/, '');
function setup(fetch, applyFilters) {
  const list = { childNodes: [{ text: 'static snapshot' }], replaceChildren(...nodes) { this.childNodes = nodes; } };
  const pagination = { childNodes: [], replaceChildren(...nodes) { this.childNodes = nodes; } };
  const status = { textContent: '' };
  const context = { fetch, URL, Date, window: { location: { hash: '' } }, prioritizeLinkedNews: items => ({ items, found: false, message: '' }), console: { error() {} }, document: { getElementById(id) { return { 'news-list': list, pagination, 'news-status': status, 'news-target-status': { textContent: '' } }[id]; } }, applyFilters: () => applyFilters(list) };
  vm.createContext(context);
  vm.runInContext('let allNews = [], filteredNews = [], currentPage = 1, targetHandled = false;\n' + validNewsUrl + '\n' + load, context);
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

test('Telegram news links prioritize only an exact current feed match', () => {
  const fn = html.match(/        function prioritizeLinkedNews\(items, hash\) \{[\s\S]*?\n        \}/)[0];
  const ctx = { URLSearchParams }; vm.createContext(ctx); vm.runInContext(fn, ctx);
  const items = [{link:'https://example.com/one'}, {link:'https://example.com/two?a=1&b=2'}];
  const hash = '#' + new URLSearchParams({news: items[1].link});
  const match = ctx.prioritizeLinkedNews(items, hash);
  assert.equal(match.found, true); assert.equal(match.items[0], items[1]);
  assert.equal(ctx.prioritizeLinkedNews(items, '#news=missing').found, false);
  assert.match(ctx.prioritizeLinkedNews(items, '#news=missing').message, /нет в текущей ленте/);
  assert.equal(ctx.prioritizeLinkedNews([items[0], items[0]], '#news=' + encodeURIComponent(items[0].link)).found, false);
  assert.equal(ctx.prioritizeLinkedNews(items, '').message, '');
});
test('opening a Telegram link clears an old filter and places its matching item first', async () => {
  const targetFunction = html.match(/        function prioritizeLinkedNews\(items, hash\) \{[\s\S]*?\n        \}/)[0];
  const link = 'https://example.com/second?x=1&y=2';
  const nodes = {
    'news-list': { childNodes: [], replaceChildren() {} },
    pagination: { childNodes: [], replaceChildren() {} },
    'news-status': { textContent: '' }, 'news-target-status': { textContent: '' },
    'filter-bar': { style: {display:'block'} }, searchInput: {value:'old search'}
  };
  const ctx = { URL, URLSearchParams, Date, Set, window: {location: { hash: '#' + new URLSearchParams({news: link}) }},
    fetch: async () => ({ok:true, json:async () => [{link:'https://example.com/first'}, {link}]}),
    document: { getElementById: id => nodes[id] }, localStorage: { removeItem() {} }, console,
    applyFilters: () => {} };
  vm.createContext(ctx);
  vm.runInContext('let allNews = [], filteredNews = [], currentPage = 1, currentTagFilter = "old", currentSearch = "old", targetHandled = false;\n' + targetFunction + '\n' + validNewsUrl + '\n' + load, ctx);
  assert.equal(await ctx.loadNews(), true);
  assert.equal(vm.runInContext('allNews[0].link', ctx), link);
  assert.equal(vm.runInContext('currentTagFilter', ctx), null);
  assert.equal(nodes['filter-bar'].style.display, 'none');
  assert.match(nodes['news-target-status'].textContent, /найдена/);
});


test('news URLs reject deceptive credentials, control characters and ambiguous destinations', () => {
  const ctx = {URL}; vm.createContext(ctx); vm.runInContext(validNewsUrl, ctx);
  const cases = JSON.parse(fs.readFileSync('tests/fixtures/news-link-cases.json', 'utf8'));
  for (const item of cases) assert.equal(ctx.isSafeNewsUrl(item.url), item.valid, JSON.stringify(item.url));
});

test('news loading discards unsafe links while preserving valid articles', async () => {
  const data = [{link: 'https://trusted.example@bad.example/', title: 'unsafe'},
    {link: 'https://example.com/legitimate', title: 'safe'},
    {link: 'https://example.com/invalid\\@bad.example/', title: 'unsafe'}];
  const {context} = setup(async () => ({ok:true, json:async () => data}), () => {});
  assert.equal(await context.loadNews(), true);
  assert.equal(vm.runInContext('allNews.length', context), 1);
  assert.equal(vm.runInContext('allNews[0].title', context), 'safe');
});

const tracking = html.match(/        function trackNewsEvent\(key\) \{[\s\S]*?\n        \}/)[0];
test('news tracking accepts only fixed event keys and payloads', () => {
  const sent = [];
  const ctx = {window: {ym: (...args) => sent.push(['ym', ...args]), gtag: (...args) => sent.push(['ga', ...args])}};
  vm.createContext(ctx); vm.runInContext(tracking, ctx);
  const expected = [
    ['read', 'news_click_read_more', 'news_click_read_more', 'news', null],
    ['like', 'news_like', 'news_like', 'engagement', null],
    ['tag', 'tag_click', 'tag_click', 'news', null],
    ['source', 'source_click', 'source_click', 'news', null],
    ['search', 'news_search', 'news_search', 'news', null],
    ['share_tg', 'share_tg', 'share', 'engagement', 'telegram'],
    ['share_vk', 'share_vk', 'share', 'engagement', 'vk'],
    ['share_tw', 'share_tw', 'share', 'engagement', 'twitter']
  ];
  for (const [key, goal, name, category, label] of expected) {
    sent.length = 0;
    ctx.trackNewsEvent(key, 'private@example.test?token=secret');
    assert.equal(sent.length, 2);
    assert.deepEqual(sent[0], ['ym', 108401876, 'reachGoal', goal]);
    assert.deepEqual(JSON.parse(JSON.stringify(sent[1])), ['ga', 'event', name,
      label ? {event_category: category, event_label: label} : {event_category: category}]);
    assert.doesNotMatch(JSON.stringify(sent), /private@example|token|secret/);
  }
  sent.length = 0;
  for (const key of ['__proto__', 'constructor', 'private@example.test', '', null]) ctx.trackNewsEvent(key);
  assert.deepEqual(sent, []);
});

test('news actions do not pass feed data to custom analytics', () => {
  const func = name => html.match(new RegExp(`        function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n        \\}`))[0];
  const sent = [], opened = [], elements = [];
  const privateValue = 'private@example.test?token=secret';
  const btn = {getAttribute: name => ({'data-url': 'https://example.com/?token=secret', 'data-title': privateValue, 'data-share': 'tg', 'data-link': 'https://example.com/?token=secret'})[name],
    querySelector: () => ({textContent: ''}), classList: {add() {}, remove() {}}};
  const sourceNode = {addEventListener: (name, fn) => elements.push(fn), getAttribute: () => privateValue};
  const list = {innerHTML: ''};
  const storage = new Map();
  const ctx = {window: {ym: (...args) => sent.push(args), gtag: (...args) => sent.push(args), open: (...args) => opened.push(args)},
    document: {getElementById: id => id === 'sources-list' ? list : id === 'tagcloud' ? {innerHTML:'', appendChild: node => elements.push(node.onclick)} : {style:{}, textContent:''},
      querySelectorAll: () => [sourceNode], createElement: () => ({style:{}, textContent:'', title:'', onclick:null})},
    localStorage: {getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value)},
    applyFilters() {}, currentTagFilter: null, Math, parseInt};
  vm.createContext(ctx);
  vm.runInContext([tracking, func('escapeHtml'), func('shareHandler'), func('likeHandler'), func('buildTagCloud'), func('buildSourcesRank')].join('\n'), ctx);
  ctx.shareHandler({preventDefault(){}, currentTarget: btn});
  ctx.likeHandler({stopPropagation(){}, currentTarget: btn});
  ctx.buildTagCloud([{tags:[privateValue]}]);
  elements.pop()();
  ctx.buildSourcesRank([{source:privateValue}]);
  elements.pop()();
  assert.equal(sent.length, 8);
  assert.doesNotMatch(JSON.stringify(sent), /private@example|token|secret/);
  // Sharing intentionally passes the selected URL and title to the chosen platform, not to custom event parameters.
  assert.match(opened[0][0], /^https:\/\/t\.me\/share\/url\?/);
  assert.match(opened[0][0], /token%3Dsecret/);
});

test('sharing still opens when analytics is missing or throws', () => {
  const share = html.match(/        function shareHandler\(e\) \{[\s\S]*?\n        \}/)[0];
  for (const analytics of [{}, {ym() {throw Error('blocked');}, gtag() {throw Error('blocked');}}]) {
    const opened = [];
    const ctx = {window: {...analytics, open: (...args) => opened.push(args)}};
    vm.createContext(ctx); vm.runInContext(tracking + '\n' + share, ctx);
    ctx.shareHandler({preventDefault(){}, currentTarget: {getAttribute: name => ({'data-url': 'https://example.com/a', 'data-title': 'News', 'data-share':'vk'})[name]}});
    assert.equal(opened.length, 1);
    assert.match(opened[0][0], /^https:\/\/vk\.com\/share\.php\?/);
  }
});

test('reading and searching record only fixed events, without URL or search text', () => {
  const render = html.match(/        function renderNews\(\) \{[\s\S]*?\n        \}\n\n        function shareHandler/)[0].replace(/\n\n        function shareHandler$/, '');
  const escape = html.match(/        function escapeHtml\(str\) \{[\s\S]*?\n        \}/)[0];
  const search = html.match(/        document\.getElementById\('searchBtn'\)\.addEventListener\('click', \(\) => \{[\s\S]*?\n        \}\);/)[0];
  const sent = [], listeners = {};
  const newsLink = {addEventListener: (event, callback) => {listeners.read = callback;}, getAttribute: () => 'https://example.test/?email=private@example.test'};
  const nodes = {'news-list': {innerHTML: ''}, pagination: {innerHTML: ''},
    searchBtn: {addEventListener: (event, callback) => {listeners.search = callback;}},
    searchInput: {value: 'private@example.test'}, 'filter-bar': {style: {}}};
  const ctx = {window: {ym: (...args) => sent.push(args), gtag: (...args) => sent.push(args)},
    document: {getElementById: id => nodes[id], querySelectorAll: selector => selector === '.news-title-link' ? [newsLink] : []},
    filteredNews: [{link:'https://example.test/?email=private@example.test', title:'title', tags:[]}],
    currentPage: 1, perPage: 10, currentSearch: '', currentTagFilter: null,
    localStorage: {getItem: () => null, removeItem() {}}, applyFilters() {}, renderPagination() {}, shareHandler() {}, likeHandler() {},
    Date, Number, Math, parseInt};
  vm.createContext(ctx); vm.runInContext(tracking + '\n' + escape + '\n' + render + '\n' + search, ctx);
  ctx.renderNews(); listeners.read(); listeners.search();
  assert.equal(sent.length, 4);
  assert.doesNotMatch(JSON.stringify(sent), /private@example|email=/);
  assert.match(JSON.stringify(sent), /news_click_read_more/);
  assert.match(JSON.stringify(sent), /news_search/);
});
