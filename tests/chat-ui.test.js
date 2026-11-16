'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('js/executive.js', 'utf8');

function element() {
  const handlers = {};
  return { handlers, disabled: false, hidden: false, value: '', textContent: '', firstElementChild: {},
    classList: { add() {}, remove() {}, contains() { return false; }, toggle() { return false; } },
    setAttribute() {}, getAttribute() { return ''; }, addEventListener(name, cb) { handlers[name] = cb; },
    appendChild(child) { (this.children ||= []).push(child); }, focus() {} };
}
function setup(fetch) {
  const theme = element(), menu = element(), nav = element(), form = element(), field = element();
  const submit = element(), messages = element(), status = element(), retry = element(), suggestion = element();
  suggestion.dataset = { question: 'Опыт?' }; form.querySelector = () => submit;
  const elements = { 'chat-form': form, 'chat-question': field, 'chat-messages': messages, 'chat-status': status, 'chat-retry': retry };
  const document = { body: element(), querySelector: s => ({'.theme-toggle': theme, '.menu-toggle': menu, '.site-nav': nav})[s],
    querySelectorAll: () => [suggestion], getElementById: id => elements[id], addEventListener() {}, createElement: () => element() };
  const context = { document, window: { addEventListener() {}, innerWidth: 1000 }, localStorage: { getItem() { return null; }, setItem() {} },
    fetch, AbortController, setTimeout, clearTimeout };
  vm.createContext(context); vm.runInContext(source, context);
  return { form, field, submit, status, retry, suggestion, messages };
}
const tick = () => new Promise(resolve => setImmediate(resolve));
test('unconfigured chat is disabled and provides retry without submitting a question', async () => {
  const calls = [];
  const ui = setup(async (url, options) => { calls.push(options); return { ok: true, headers: { get: () => 'application/json' }, json: async () => ({ configured: false }) }; });
  await tick();
  assert.equal(ui.field.disabled, true); assert.equal(ui.submit.disabled, true); assert.equal(ui.suggestion.disabled, true);
  assert.equal(ui.retry.hidden, false); assert.match(ui.status.textContent, /НЕДОСТУПЕН/);
  ui.field.value = 'Опыт?'; ui.form.handlers.submit({ preventDefault() {} });
  assert.equal(calls.length, 1);
});
test('configured chat permits question and renders response', async () => {
  const calls = [];
  const ui = setup(async (url, options) => {
    calls.push(options);
    if (!options.method) return { ok: true, headers: { get: () => 'application/json' }, json: async () => ({ configured: true }) };
    return { ok: true, json: async () => ({ answer: 'Ответ', sources: [] }) };
  });
  await tick();
  assert.equal(ui.field.disabled, false); assert.equal(ui.retry.hidden, true);
  ui.field.value = 'Опыт?'; ui.form.handlers.submit({ preventDefault() {} });
  await tick();
  assert.equal(calls.length, 2); assert.equal(calls[1].method, 'POST');
  assert.equal(ui.messages.children[1].textContent, 'Ответ');
});
