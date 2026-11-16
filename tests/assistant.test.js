'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createServer } = require('../server/assistant');

async function withServer(options, run) {
  const server = createServer(options);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try { await run(`http://127.0.0.1:${server.address().port}`); }
  finally { await new Promise(resolve => server.close(resolve)); }
}
function post(base, body, headers = {}) {
  return fetch(base + '/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body) });
}
test('missing server key returns safe unavailable error', async () => {
  await withServer({ apiKey: '' }, async base => {
    const res = await post(base, {question:'Опыт?'});
    assert.equal(res.status, 503);
    assert.match((await res.json()).error, /не настроен/);
  });
});
test('valid request sends curated facts only and returns safe source links', async () => {
  let called;
  const fetchImpl = async (url, options) => {
    called = {url, options};
    return {ok:true, json:async () => ({choices:[{message:{content:'Опыт указан в портфолио.'}}]})};
  };
  await withServer({ apiKey:'server-secret', fetchImpl }, async base => {
    const res = await post(base, {question:'Какой опыт?'});
    const data = await res.json();
    assert.equal(res.status, 200); assert.equal(data.answer, 'Опыт указан в портфолио.');
    assert(!JSON.stringify(data).includes('server-secret'));
    assert.deepEqual(data.sources.map(x => x.href), ['#cases','#experience','#expertise','#contact']);
    assert.equal(called.url, 'https://api.openai.com/v1/chat/completions');
    const payload = JSON.parse(called.options.body);
    assert.match(payload.messages[0].content, /Герасимов/);
    assert.equal(payload.messages[1].content, 'Какой опыт?');
  });
});
test('rejects cross-origin, invalid and oversized inputs', async () => {
  await withServer({ apiKey:'key', fetchImpl: async () => { throw Error('must not call'); } }, async base => {
    assert.equal((await post(base, {question:'a'}, {Origin:'https://attacker.example'})).status, 403);
    assert.equal((await post(base, {question:''})).status, 400);
    assert.equal((await post(base, {question:'x'.repeat(601)})).status, 400);
    assert.equal((await post(base, {question:'a', extra:'x'.repeat(5000)})).status, 413);
    assert.equal((await fetch(base + '/api/chat')).status, 405);
  });
});
test('handles provider failures without leaking details', async () => {
  await withServer({ apiKey:'server-secret', fetchImpl: async () => ({ok:false}) }, async base => {
    const res = await post(base, {question:'Опыт?'}); const body = await res.text();
    assert.equal(res.status, 502); assert(!body.includes('server-secret'));
  });
});
test('enforces request limit', async () => {
  await withServer({apiKey:'key', fetchImpl:async () => ({ok:true,json:async () => ({choices:[{message:{content:'Да'}}]})})}, async base => {
    for (let i=0; i<15; i++) assert.equal((await post(base, {question:'Опыт?'})).status, 200);
    assert.equal((await post(base, {question:'Опыт?'})).status, 429);
  });
});
test('local preview serves home and blocks sensitive paths', async () => {
  await withServer({}, async base => {
    assert.equal((await fetch(base + '/')).status, 200);
    assert.equal((await fetch(base + '/css/executive.css')).status, 200);
    assert.equal((await fetch(base + '/server/assistant.js')).status, 404);
    const resumeDir = path.join(__dirname, '..', 'resume');
    fs.mkdirSync(resumeDir, { recursive: true });
    const privateFile = path.join(resumeDir, `privacy-test-${process.pid}.pdf`);
    fs.writeFileSync(privateFile, 'private');
    try { assert.equal((await fetch(base + '/resume/' + path.basename(privateFile))).status, 404); }
    finally { fs.unlinkSync(privateFile); }
    assert.equal((await fetch(base + '/.git/config')).status, 404);
  });
});
