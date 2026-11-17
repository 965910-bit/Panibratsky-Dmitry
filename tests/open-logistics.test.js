'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { validOpenLogistics, loadOpenLogistics } = require('../js/open-logistics');
const sample = () => ({ schema_version: 1, saved_on: '2026-11-17', indicators: {
  world_bank: { period: '2022', value: 2.6 },
  eurostat: { period: '2025', value: 2804335, status: null }
} });

test('snapshot validation checks periods, types and ranges', () => {
  assert.equal(validOpenLogistics(sample()), true);
  const bad = sample(); bad.indicators.world_bank.value = 6;
  assert.equal(validOpenLogistics(bad), false);
  bad.indicators.world_bank.value = 2.6; bad.indicators.eurostat.value = '<svg>';
  assert.equal(validOpenLogistics(bad), false);
  assert.equal(validOpenLogistics(null), false);
});

test('only displays data as text and handles unavailable data', async () => {
  const nodes = Object.fromEntries(['open-data-status', 'open-data-bank', 'open-data-eurostat'].map(id => [id, { textContent: '' }]));
  global.document = { getElementById: id => nodes[id] };
  try {
    const flagged = sample(); flagged.indicators.eurostat.status = '<test>';
    await loadOpenLogistics(async () => ({ ok: true, json: async () => flagged }));
    assert.match(nodes['open-data-bank'].textContent, /2022/);
    assert.match(nodes['open-data-eurostat'].textContent, /<test>/);
    assert.match(nodes['open-data-status'].textContent, /2026-11-17/);
    await loadOpenLogistics(async () => { throw Error('offline'); });
    assert.match(nodes['open-data-status'].textContent, /Не удалось/);
  } finally { delete global.document; }
});
