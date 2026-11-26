const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');

test('network operations guide is discoverable and its local fragments resolve', () => {
  const wiki = fs.readFileSync(path.join(root, 'wiki.html'), 'utf8');
  const page = fs.readFileSync(path.join(root, 'scm-network-operations.html'), 'utf8');
  const ids = [...page.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
  assert.equal(new Set(ids).size, ids.length);
  const links = [...wiki.matchAll(/href="scm-network-operations\.html#([^"]+)"/g)].map(m => m[1]);
  assert.equal(links.length, 6);
  for (const id of links) assert.ok(ids.includes(id), id);
  assert.match(page, /rel="canonical" href="https:\/\/scm-news\.ru\/scm-network-operations\.html"/);
  assert.match(page, /Все числовые примеры условные/);
  for (const [, href] of page.matchAll(/href="([^"#/:]+\.html)(?:#([^"]+))?"/g)) {
    assert.ok(fs.existsSync(path.join(root, href)), href);
  }
  for (const [, fragment] of page.matchAll(/href="scm-network-operations\.html#([^"]+)"/g)) assert.ok(ids.includes(fragment));
});

test('planning topics include detailed formulas, assumptions and worked examples', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'scm-network-operations.html'), 'utf8');
  for (const id of ['network-design', 'capacity-planning', 'kanban', 'inventory-review-policies', 'demand-lead-variability', 'forecast-hierarchy', 'work-in-process', 'maintenance-reliability', 'first-pass-yield', 'multi-echelon-inventory']) {
    const section = html.match(new RegExp(`<section class="encyclopedia-start" id="${id}">([\\s\\S]*?)</section>`));
    assert.ok(section, id);
    assert.match(section[1], /<h3>Углубление:/, id);
  }
  assert.ok(Math.abs((-1 + 2/1.1 + 2/1.1**2) - 2.47107438) < 0.0001);
  assert.equal(Math.ceil((30*3+11)/25), 5);
  assert.ok(Math.abs(Math.sqrt(2*10000*200/5)-894.4272)<0.001);
  assert.equal(4*25 + 20**2, 500);
  assert.equal(120/30, 4);
  assert.ok(Math.abs(81/100 - .9*.9) < 1e-12);
});
