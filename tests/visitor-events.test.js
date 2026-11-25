'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const install = require('../js/visitor-events.js');
function setup() {
  const callbacks = {}; const calls = [];
  const doc = {addEventListener: (type, fn) => callbacks[type] = fn};
  install(doc, {ym: (...x) => calls.push(['ym', ...x]), gtag: (...x) => calls.push(['gtag', ...x])}, {href:'https://scm-news.ru/career.html', hostname:'scm-news.ru'});
  function click(href, options={}) {
    const link = href ? {getAttribute: () => href} : null;
    callbacks.click({button: options.button ?? 0, defaultPrevented: !!options.prevented, target: {closest: selector => selector === '#print-checklist' ? (options.print ? {} : null) : link}});
  }
  return {calls, click};
}
test('fixed allowlisted events are sent without input or url', () => {
  const {click, calls} = setup();
  click('mailto:dmitry@example.com?subject=private');
  assert.deepEqual(calls, [['ym',108401876,'reachGoal','contact_email_click'], ['gtag','event','contact_email_click']]);
  calls.length=0; click('/scm-review-questions.html?secret=hello');
  assert.deepEqual(calls, [['ym',108401876,'reachGoal','interest_checklist'], ['gtag','event','interest_checklist']]);
});
test('classifies approved actions while avoiding existing PDF handler', () => {
  const {click, calls} = setup();
  for (const [href, expected] of [['tel:+79825810787','contact_phone_click'],['https://surgut.hh.ru/resume/33d5f7abff115bad460039ed1f7166544f5263','resume_click_hh'],['https://t.me/LogisticaandSupplyChain','channel_telegram_click'],['/scm-academy.html','interest_academy'],['/#book','interest_book']]) {
    calls.length=0; click(href); assert.equal(calls[0][3], expected);
  }
  calls.length=0; click('/documents/gerasimov-presentation.pdf'); click('https://other.example/'); click('#contact');
  assert.equal(calls.length,0);
  click(null, {print:true}); assert.equal(calls[0][3], 'checklist_print_click');
});
test('ignored events do not block clicks or fire goals', () => {
  const {click, calls} = setup(); click('/career.html',{button:2}); click('/career.html',{prevented:true});
  assert.equal(calls.length,0);
});
test('browser deployment is disabled by default', () => {
  let listeners=0; const window={document:{addEventListener(){listeners++;}},location:{href:'https://scm-news.ru/'}};
  vm.runInNewContext(fs.readFileSync('js/visitor-events.js','utf8'),{window,URL});
  assert.equal(listeners,0);
});

test('invalid, unrelated and deceptive links never become events', () => {
  const {click, calls} = setup();
  for (const href of ['https://surgut.hh.ru.evil.example/resume/33d5f7abff115bad460039ed1f7166544f5263',
    'https://t.me/another_channel', 'https://dzen.ru/id/other', 'javascript:alert(1)',
    '/vizitka.html', '/scm-review-questions.html.evil', 'https://elsewhere.example/career.html']) click(href);
  assert.deepEqual(calls, []);
});
test('counter failure is isolated; event handlers never cancel navigation', () => {
  let handler, calls=[];
  install({addEventListener: (_, fn) => handler=fn}, {ym() {throw new Error('blocked');}, gtag: (...x) => calls.push(x)}, {href:'https://scm-news.ru/',hostname:'scm-news.ru'});
  const link = {getAttribute: () => '/career.html'};
  const event = {button:0,target:{closest: q => q==='a[href]' ? link : null},preventDefault(){throw new Error('must not cancel navigation');}};
  assert.doesNotThrow(() => handler(event));
  assert.deepEqual(calls,[['event','interest_career']]);
});
test('prepared tracker is not included in any current HTML page', () => {
  for (const filename of fs.readdirSync('.').filter(f => f.endsWith('.html'))) {
    assert.doesNotMatch(fs.readFileSync(filename, 'utf8'), /<script\b[^>]*\bsrc\s*=\s*["'][^"']*visitor-events\.js/i, filename);
  }
});
