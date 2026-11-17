'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// Run with an in-memory filesystem and stubbed Telegram API; no network or secrets.
async function run({ sent = '[]', failures = 0, news, args = [], env }) {
  const newsPath = path.join('/repo', 'data', 'news.json');
  const sentPath = path.join('/repo', 'data', 'sent_news.json');
  const files = new Map([[newsPath, JSON.stringify(news || [
    { link: 'https://example.com/1', title: 'Склад One' },
    { link: 'https://example.com/2', title: 'Склад Two' }
  ])]]);
  if (sent !== null) files.set(sentPath, sent);
  let calls = 0, exit = 0, payloads = [], logs = [], writes = 0;
  const fakeFs = {
    existsSync: name => name === path.join('/repo', 'data') || files.has(name),
    mkdirSync() {}, readFileSync: name => files.get(name),
    writeFileSync: (name, value, options) => { if (options && options.flag === 'wx' && files.has(name)) throw Error('exists'); writes++; files.set(name, value); }
  };
  let source = fs.readFileSync('scripts/telegram-news.js', 'utf8');
  source = source.replace(/main\(\)\.catch\(err => \{[\s\S]*?\}\);\s*$/, 'globalThis.result = main();');
  const context = { __dirname: '/repo/scripts', URL, URLSearchParams, Set, Date, JSON,
    console: { log: (...values) => logs.push(values.join(" ")), error() {} },
    process: { argv: ['node', 'script', ...args], env: env || { TELEGRAM_BOT_TOKEN: 'test', TELEGRAM_CHAT_ID: 'test' }, exit: code => { exit = code; } },
    setTimeout: callback => callback(),
    require: name => name === 'fs' ? fakeFs : name === 'path' ? path : { post: async (url, payload) => { payloads.push(payload); calls++; if (calls <= failures) throw new Error('failed'); } }
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  let error;
  try { await context.result; } catch (e) { error = e; }
  return { calls, files, sentPath, exit, error, payloads, logs, writes };
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

test('Telegram links point to the matching news in the feed and preserve source link', async () => {
  const link = 'https://example.com/path?a=1&b=two';
  const result = await run({ news: [{link, title:'Склад: новость'}] });
  const buttons = JSON.parse(result.payloads[0].reply_markup).inline_keyboard[0];
  const site = new URL(buttons[0].url);
  assert.equal(buttons[0].text, '🔗 Найти в ленте');
  assert.equal(new URLSearchParams(site.hash.slice(1)).get('news'), link);
  assert.equal(site.searchParams.get('utm_source'), 'telegram');
  assert.equal(new URL(buttons[1].url).origin, 'https://example.com');
});

test('unusually long news URL falls back to the general feed', async () => {
  const result = await run({ news: [{link:'https://example.com/' + 'a'.repeat(1800), title:'Склад: новость'}] });
  const button = JSON.parse(result.payloads[0].reply_markup).inline_keyboard[0][0];
  assert.equal(button.text, '🔗 Все новости');
  assert.equal(new URL(button.url).hash, '');
});

test('topic filter skips generic alerts and unrelated articles, preserving them in the feed', async () => {
  const news = [
    {link:'https://example.com/sea', source:'Google Alert', title:'Оповещение Google – цифровой двойник', description:'Прогнозирование процессов в акватории моря'},
    {link:'https://example.com/empty', source:'Google Alert', title:'Оповещение Google – WMS', description:'Google Alert по теме: WMS'},
    {link:'https://example.com/road', source:'АТИ (новости)', title:'Открыта дорога для путешественников', description:'Логистика, грузы: Открыта дорога для путешественников'},
    {link:'https://example.com/good', source:'Google Alert', title:'Оповещение Google – WMS', description:'На складском комплексе внедрили систему управления складом'},
  ];
  const result = await run({news});
  assert.equal(result.calls, 1);
  assert.match(result.payloads[0].text, /Google Alerts · тема: WMS/);
  assert.deepEqual(JSON.parse(result.files.get(result.sentPath)), ['https://example.com/good']);
  assert.deepEqual(JSON.parse(result.files.get(path.join('/repo','data','news.json'))), news);
});

test('a topical alert keyword alone does not substitute for an actual description', async () => {
  const result = await run({news:[{link:'https://example.com/', title:'Оповещение Google – склад', description:''}]});
  assert.equal(result.calls, 0);
});

test('invalid and undated items do not crash sorting or block valid entries', async () => {
  const result = await run({news:[null, {link:'https://example.com/bad', title:'склад', pubDate:'broken'},
    {link:'https://example.com/good', title:'склад', pubDate:'Sun, 15 Nov 2026 09:00:00 +0000'}]});
  assert.equal(result.error, undefined);
  assert.equal(result.calls, 2);
  assert.equal(JSON.parse(result.files.get(result.sentPath))[0], 'https://example.com/good');
});

test('preview uses normal selection without credentials, delivery or state changes', async () => {
  const sent = JSON.stringify(['https://example.com/1']);
  const result = await run({args:['--preview'], env:{}, sent});
  assert.equal(result.error, undefined);
  assert.equal(result.calls, 0); assert.equal(result.writes, 0);
  assert.equal(result.files.get(result.sentPath), sent);
  const line = result.logs.find(line => line.startsWith('ПРЕДПРОСМОТР {'));
  assert.equal(JSON.parse(line.slice('ПРЕДПРОСМОТР '.length)).source_url, 'https://example.com/2');
  assert.equal(result.logs.filter(line => line.startsWith('ПРЕДПРОСМОТР {')).length, 1);
});

test('preview warns if sent state is missing and rejects corrupt state', async () => {
  const missing = await run({args:['--preview'], env:{}, sent:null});
  assert.match(missing.logs.join(' '), /Журнал отправок не найден/);
  assert.equal(missing.calls, 0); assert.equal(missing.writes, 0);
  const invalid = await run({args:['--preview'], env:{}, sent:'{'});
  assert.match(invalid.error.message, /состояние отправок/);
  assert.equal(invalid.calls, 0); assert.equal(invalid.writes, 0);
});

test('unknown command line arguments never cause a send', async () => {
  const result = await run({args:['--preveiw']});
  assert.match(result.error.message, /Неизвестный аргумент/);
  assert.equal(result.calls, 0); assert.equal(result.writes, 0);
});

test('missing sent journal stops scheduled sending before any message or write', async () => {
  const result = await run({sent:null});
  assert.match(result.error.message, /Журнал отправок отсутствует/);
  assert.equal(result.calls, 0); assert.equal(result.writes, 0);
});

test('initialization excludes all current links but never sends or overwrites a journal', async () => {
  const news = [{link:'https://example.com/a', title:'Склад'}, {link:'https://example.com/a'},
    {link:'https://example.com/b', dead:true}, {link:'javascript:alert(1)'}, null];
  const result = await run({sent:null, args:['--initialize-journal'], env:{}, news});
  assert.equal(result.error, undefined); assert.equal(result.calls, 0);
  assert.deepEqual(JSON.parse(result.files.get(result.sentPath)), ['https://example.com/a', 'https://example.com/b']);
  const again = await run({sent:'["https://example.com/already"]', args:['--initialize-journal'], env:{}, news});
  assert.match(again.error.message, /Журнал уже существует/);
  assert.equal(again.writes, 0); assert.equal(again.calls, 0);
  const empty = await run({sent:null, args:['--initialize-journal'], env:{}, news:[]});
  assert.match(empty.error.message, /нет ссылок/); assert.equal(empty.writes, 0);
});

test('workflows cannot mistake the tracked checkout journal for restored state', () => {
  for (const path of ['.github/workflows/send_telegram.yml', '.github/workflows/preview_telegram.yml']) {
    const workflow = fs.readFileSync(path, 'utf8');
    const remove = workflow.indexOf('run: rm -f data/sent_news.json');
    const restore = workflow.search(/uses: actions\/cache\/restore@[0-9a-f]{40}/);
    assert.ok(remove > -1 && remove < restore, path);
  }
});
