'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { validateMarketData, hiringWeeks, loadMarketCard } = require('../js/market');
const now = Date.parse('2026-11-16T12:00:00Z');
function data(overrides = {}) {
  return { schema_version: 1, source: 'hh.ru API', queries: ['склад'], date_from: '2026-10-17',
    total_vacancies: 10, salary_sample_size: 2, salary_stats: { avg: 50000 },
    top_skills: [], avg_salary_by_region: {}, updated_at: '2026-11-16T10:00:00Z', ...overrides };
}
test('rejects old examples, malformed samples and future dates', () => {
  assert.equal(validateMarketData({ current: data() }, now), null);
  assert.equal(validateMarketData(data({ salary_sample_size: 11 }), now), null);
  assert.equal(validateMarketData(data({ updated_at: '2026-11-17T00:00:00Z' }), now), null);
  assert.equal(validateMarketData(data({ salary_sample_size: 0, salary_stats: { avg: 0 } }), now), null);
  assert.ok(validateMarketData(data({ salary_sample_size: 0, salary_stats: { avg: null } }), now));
  assert.equal(validateMarketData(data(), now).stale, false);
  assert.equal(validateMarketData(data({ updated_at: '2026-11-10T10:00:00Z' }), now).stale, true);
});
test('hiring calculator uses user-supplied rate and rejects invalid inputs', () => {
  assert.equal(hiringWeeks(10, 3), 4);
  assert.equal(hiringWeeks(1, 0.5), 2);
  for (const [count, rate] of [[0, 1], [1, 0], [1.5, 1], [1, Infinity], [100001, 1]]) assert.equal(hiringWeeks(count, rate), null);
});
test('failed or historical data displays unavailable status', async () => {
  const target = { replaceChildren(...nodes) { this.nodes = nodes; } };
  global.document = { getElementById: () => target, createElement: tag => ({ tag, textContent: '', className: '' }) };
  try {
    assert.equal(await loadMarketCard('x', 'x', async () => ({ ok: true, json: async () => ({ current: data() }) })), false);
    assert.match(target.nodes[0].textContent, /недоступна/);
    assert.equal(await loadMarketCard('x', 'x', async () => { throw Error('offline'); }), false);
    assert.match(target.nodes[0].textContent, /недоступна/);
  } finally { delete global.document; }
});
