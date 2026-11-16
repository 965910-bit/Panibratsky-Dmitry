'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('prompts.html', 'utf8');
const script = html.match(/<script>\s*(function escapePrompt[\s\S]*?)<\/script>/)[1];
const prompts = JSON.parse(fs.readFileSync('data/prompts.json', 'utf8'));
function environment(fetch) {
  const els = {};
  for (const id of ['promptSearch', 'filterTier', 'filterRole', 'filterDiff', 'promptStatus', 'promptCount', 'promptMore', 'promptTbody', 'promptModalContent', 'promptModal']) {
    els[id] = { value: '', textContent: '', innerHTML: '', hidden: true, classList: { add() {}, remove() {} }, addEventListener() {} };
  }
  const ctx = { fetch, document: { getElementById: id => els[id], addEventListener() {} }, navigator: {}, console, Number };
  vm.createContext(ctx); vm.runInContext(script, ctx);
  return { ctx, els };
}
test('catalogue data is complete, unique and page keeps a static preview', () => {
  assert.equal(prompts.length, 3035);
  assert.equal(new Set(prompts.map(p => p.id)).size, 3035);
  assert.equal(prompts[0].id, 1); assert.equal(prompts.at(-1).id, 3035);
  assert.ok(Buffer.byteLength(html) < 500000);
  assert.equal((html.match(/onclick="openPrompt\(\d+\)"/g) || []).length, 30);
});
test('load, filter, paginate and open a prompt', async () => {
  const { ctx, els } = environment(async () => ({ ok: true, json: async () => prompts }));
  await ctx.filterPrompts();
  assert.match(els.promptCount.textContent, /30 из 3035/); assert.equal(els.promptMore.hidden, false);
  els.promptSearch.value = prompts[0].name;
  await ctx.filterPrompts(); assert.match(els.promptTbody.innerHTML, /prompt-1/);
  await ctx.openPrompt(3035); assert.match(els.promptModalContent.innerHTML, /3035/);
});
test('failed fetch retains preview, reports error, and can retry', async () => {
  let calls = 0;
  const { ctx, els } = environment(async () => { if (!calls++) throw Error('offline'); return { ok: true, json: async () => prompts }; });
  els.promptTbody.innerHTML = 'static preview';
  await ctx.filterPrompts(); assert.equal(els.promptTbody.innerHTML, 'static preview'); assert.match(els.promptStatus.textContent, /Не удалось/);
  await ctx.filterPrompts(); assert.match(els.promptCount.textContent, /3035/);
});
