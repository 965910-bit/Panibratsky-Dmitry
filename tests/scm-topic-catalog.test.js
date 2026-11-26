const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');

test('catalog exposes all 80 unique topics and links to seventy prepared articles', () => {
  const page = read('scm-topic-catalog.html');
  const wiki = read('wiki.html');
  const guide = read('scm-network-operations.html');
  assert.match(wiki, /href="scm-topic-catalog\.html"/);
  assert.match(page, /rel="canonical" href="https:\/\/scm-news\.ru\/scm-topic-catalog\.html"/);
  const ids = [...page.matchAll(/\bid="(topic-\d+)"/g)].map(m => m[1]);
  assert.equal(ids.length, 80);
  assert.equal(new Set(ids).size, 80);
  for (let n = 1; n <= 80; n++) assert.ok(ids.includes(`topic-${n}`));
  const ready = [...page.matchAll(/href="scm-network-operations\.html#([^"]+)"/g)].map(m => m[1]);
  assert.equal(ready.length, 70);
  for (const id of ready) assert.ok(guide.includes(`id="${id}"`), id);
  const newTopics = {6: 'process-raci', 62: 'control-tower', 75: 'investment-business-case', 76: 'sla-kpi-data-quality', 77: 'measurement-improvement', 78: 'shift-skills-matrix', 79: 'shift-handover', 80: 'change-implementation-project'};
  Object.assign(newTopics, {2: 'service-segmentation', 3: 'inventory-centralization', 4: 'make-or-buy-3pl', 5: 'logistics-operator-contract', 19: 'indirect-procurement', 22: 'procurement-commercial-terms', 23: 'contract-obligations', 39: 'third-party-inventory'});
  Object.assign(newTopics, {8: 'promotion-new-product-forecast', 9: 'multi-echelon-inventory', 36: 'warehouse-automation', 42: 'vehicle-route-planning', 61: 'epcis-traceability', 64: 'supply-chain-access', 65: 'ai-forecast-documents', 67: 'subtier-supplier-risk'});
  for (const [number, anchor] of Object.entries(newTopics)) {
    const card = page.match(new RegExp(`<article class="catalog-card" id="topic-${number}"[\\s\\S]*?</article>`));
    assert.ok(card && card[0].includes(`scm-network-operations.html#${anchor}`), number);
    assert.ok(guide.includes(`href="#${anchor}"`), anchor);
  }
  assert.equal((page.match(/class="catalog-status">В плане/g) || []).length, 10);
});

test('search handles ё, multiple words, empty results and reset', () => {
  const cards = [{textContent: 'Планирование ворот склада', hidden: false}, {textContent: 'Поток и надёжность', hidden: false}];
  const group = { hidden: false, querySelectorAll: () => cards };
  let handler;
  const input = { value: '', addEventListener: (_, fn) => { handler = fn; } };
  const box = {hidden: true}, status = {textContent: ''};
  const document = {getElementById: id => ({'catalog-search-box': box, 'catalog-search': input, 'catalog-search-status': status})[id], querySelectorAll: () => [group]};
  vm.runInNewContext(read('js/scm-topic-catalog.js'), {document});
  assert.equal(box.hidden, false);
  input.value = 'ворот склад'; handler(); assert.equal(cards[0].hidden, false); assert.equal(cards[1].hidden, true);
  input.value = 'надежность'; handler(); assert.equal(cards[1].hidden, false);
  input.value = 'несуществующее'; handler(); assert.equal(group.hidden, true); assert.match(status.textContent, /0/);
  input.value = ''; handler(); assert.equal(group.hidden, false); assert.ok(cards.every(card => !card.hidden));
});
