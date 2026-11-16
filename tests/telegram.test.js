'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// Run with an in-memory filesystem and stubbed Telegram API; no network or secrets.
async function run({ sent, failures = 0 }) {
  const newsPath = path.join('/repo', 'data', 'news.json');
  const sentPath = path.join('/repo', 'data', 'sent_news.json');
  const files = new Map([[newsPath, JSON.stringify([
    { link: 'https://example.com/1', title: 'One' },
    { link: 'https://example.com/2', title: 'Two' }
  ])]]);
  if (sent !== undefined) files.set(sentPath, sent);
  let calls = 0, exit = 0;
  const fakeFs = {
    existsSync: name => name === path.join('/repo', 'data') || files.has(name),
    mkdirSync() {}, readFileSync: name => files.get(name),
    writeFileSync: (name, value) => files.set(name, value)
  };
  let source = fs.readFileSync('scripts/telegram-news.js', 'utf8');
  source = source.replace(/main\(\)\.catch\(err => \{[\s\S]*?\}\);\s*$/, 'globalThis.result = main();');
  const context = { __dirname: '/repo/scripts', URL, Set, Date, JSON,
    console: { log() {}, error() {} },
    process: { env: { TELEGRAM_BOT_TOKEN: 'test', TELEGRAM_CHAT_ID: 'test' }, exit: code => { exit = code; } },
    setTimeout: callback => callback(),
    require: name => name === 'fs' ? fakeFs : name === 'path' ? path : { post: async () => { calls++; if (calls <= failures) throw new Error('failed'); } }
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  let error;
  try { await context.result; } catch (e) { error = e; }
  return { calls, files, sentPath, exit, error };
}

test('partial Telegram failure fails the job but retains successful sends', async () => {
  const result = await run({ failures: 1 });
  assert.equal(result.calls, 2);
  assert.match(result.error.message, /Не все новости доставлены/);
  assert.deepEqual(JSON.parse(result.files.get(result.sentPath)), ['https://example.com/2']);
});

test('invalid saved state stops before sending to prevent duplicate posts', async () => {
  for (const sent of ['{', '{}']) {
    const result = await run({ sent });
    assert.equal(result.calls, 0);
    assert.match(result.error.message, /состояние отправок/);
  }
});
