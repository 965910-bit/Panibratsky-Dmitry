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
