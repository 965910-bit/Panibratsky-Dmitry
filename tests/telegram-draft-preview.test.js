'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const {buildPreview, clean, validLink} = require('../tools/telegram-draft-preview');
test('preview escapes untrusted fields and never renders dangerous links', () => {
  const html = buildPreview([{title:'<img src=x onerror=alert(1)> Склад & груз',description:'Текст <script>alert(1)</script>',source:'" onmouseover="evil',link:'https://example.com/?x=1&y=2'}, {title:'Опасно',link:'javascript:alert(1)'}]);
  assert(!html.includes('<img src=x'));
  assert(!html.includes('<script>'));
  assert(!html.includes('javascript:alert'));
  assert.match(html, /Склад &amp; груз/);
  assert.match(html, /x=1&amp;y=2/);
  assert.match(html, /не отправлены/);
});
test('invalid and duplicate records ignored, input not mutated', () => {
  const items = [{title:'Склад',link:'https://example.com'}, {title:'Дубль',link:'https://example.com/'},null,{title:'bad',link:'https://user:pass@example.com'}];
  const snapshot = JSON.stringify(items);
  const html = buildPreview(items);
  assert.equal((html.match(/<article>/g) || []).length,1);
  assert.equal(JSON.stringify(items),snapshot);
  assert.equal(validLink('javascript:alert(1)'), '');
  assert.equal(clean('one\u202etwo', 100), 'one two');
  assert.throws(() => buildPreview({}));
});
