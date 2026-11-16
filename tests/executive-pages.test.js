'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const themeSource = fs.readFileSync('js/executive-theme.js', 'utf8');
const shellSource = fs.readFileSync('js/executive-pages.js', 'utf8');
function element() {
  const listeners = {}, attrs = {}, classes = new Set();
  return { listeners, attrs, textContent: '', title: '', classList: {
    add(x) { classes.add(x); }, remove(x) { classes.delete(x); }, contains(x) { return classes.has(x); },
    toggle(x, force) { const enabled = force === undefined ? !classes.has(x) : force; enabled ? classes.add(x) : classes.delete(x); return enabled; }
  }, addEventListener(type, cb) { listeners[type] = cb; }, setAttribute(k, v) { attrs[k] = v; }, getAttribute(k) { return attrs[k]; }, focus() {} };
}
function setup(stored) {
  const root = { dataset: {} }, body = element(), bar = element(), nav = element(), menu = element(), theme = element();
  const document = { documentElement: root, body, querySelector: () => bar, addEventListener() {} };
  const localStorage = { value: stored, getItem() { return this.value; }, setItem(k, v) { this.value = v; } };
  bar.querySelector = s => ({ '.executive-menu': menu, '.executive-nav': nav, '.executive-theme': theme })[s];
  const context = { document, localStorage, window: { addEventListener() {} } };
  vm.createContext(context); vm.runInContext(themeSource, context); vm.runInContext(shellSource, context);
  return { root, body, nav, menu, theme, localStorage };
}
test('theme follows the home preference and persists changes', () => {
  const s = setup('light');
  assert.equal(s.root.dataset.executiveTheme, 'light');
  assert.match(s.theme.attrs['aria-label'], /тёмную/);
  s.theme.listeners.click();
  assert.equal(s.root.dataset.executiveTheme, 'dark'); assert.equal(s.localStorage.value, 'dark');
});
test('mobile navigation opens and closes after navigation', () => {
  const s = setup(null);
  s.menu.listeners.click(); assert.equal(s.menu.attrs['aria-expanded'], 'true'); assert.ok(s.nav.classList.contains('is-open'));
  s.nav.listeners.click({ target: { closest: () => true } });
  assert.equal(s.menu.attrs['aria-expanded'], 'false'); assert.equal(s.nav.classList.contains('is-open'), false);
});
