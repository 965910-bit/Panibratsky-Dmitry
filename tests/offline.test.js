'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

function setup() {
  const listeners = {};
  const cache = { add: async url => { cache.added = url; }, match: async url => ({ offline: url }) };
  const removed = [];
  const context = {
    URL, Set,
    self: { location: { origin: 'https://example.com' }, clients: { claim: async () => {} }, addEventListener: (event, handler) => { listeners[event] = handler; } },
    caches: { open: async () => cache, keys: async () => ['scm-news-v2', 'unrelated', 'scm-news-v3'], delete: async key => { removed.push(key); } },
    fetch: async () => { throw new Error('offline'); }
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('sw.js', 'utf8'), context);
  return { listeners, cache, removed };
}
test('installation caches only standalone offline page and removes old app caches', async () => {
  const { listeners, cache, removed } = setup();
  let work;
  listeners.install({ waitUntil: promise => { work = promise; } }); await work;
  assert.equal(cache.added, './offline.html');
  listeners.activate({ waitUntil: promise => { work = promise; } }); await work;
  assert.deepEqual(removed, ['scm-news-v2']);
});
test('offline fallback is limited to public navigations and never handles forms, API or workspaces', async () => {
  const { listeners } = setup();
  function request(url, method = 'GET', mode = 'navigate') {
    let response;
    listeners.fetch({ request: { url, method, mode }, respondWith: promise => { response = promise; } });
    return response;
  }
  assert.equal((await request('https://example.com/trends.html?tag=warehouse')).offline, './offline.html');
  for (const args of [
    ['https://example.com/cabinet.html'], ['https://example.com/scm-platform/planner.html'],
    ['https://example.com/api/chat', 'POST'], ['https://example.com/data/news.json', 'GET', 'cors'],
    ['https://other.example/trends.html']
  ]) assert.equal(request(...args), undefined);
});
