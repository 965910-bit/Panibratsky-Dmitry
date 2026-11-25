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
  for (const [href, expected] of [['tel:+79825810787','contact_phone_click'],['https://surgut.hh.ru/resume/33d5f7abff115bad460039ed1f7166544f5263','resume_click_hh'],['https://t.me/LogisticaandSupplyChain','channel_telegram_click'],['https://set.ki/EYUBwz5','setka_profile_click'],['https://m.tenchat.ru/u/3CguEuQy','tenchat_profile_click'],['https://setka.ru/communities/01a15b2e-dfa8-7b4d-9059-6b74529f0ac3','setka_community_click'],['https://setka.ru/communities/01a19c5c-b9c8-7a87-b08c-60a87d8f6049/','setka_channel_click'],['/scm-academy.html','interest_academy'],['/expertise.html#corporate-training','corporate_training_click'],['/#book','interest_book']]) {
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
test('browser deployment registers one set of handlers', () => {
  const listeners=[]; const window={document:{addEventListener(type){listeners.push(type);}},location:{href:'https://scm-news.ru/'}};
  vm.runInNewContext(fs.readFileSync('js/visitor-events.js','utf8'),{window,URL});
  assert.deepEqual(listeners,['click','submit','change']);
});

test('invalid, unrelated and deceptive links never become events', () => {
  const {click, calls} = setup();
  for (const href of ['https://surgut.hh.ru.evil.example/resume/33d5f7abff115bad460039ed1f7166544f5263',
    'https://m.tenchat.ru/u/3CguEuQy-other', 'https://m.tenchat.ru.evil.example/u/3CguEuQy', 'https://t.me/another_channel', 'https://dzen.ru/id/other', 'javascript:alert(1)',
    '/vizitka.html', '/scm-review-questions.html.evil', 'https://elsewhere.example/career.html']) click(href);
  assert.deepEqual(calls, []);
});
test('counter failure is isolated; event handlers never cancel navigation', () => {
  let handler, calls=[];
  install({addEventListener: (type, fn) => { if (type === 'click') handler=fn; }}, {ym() {throw new Error('blocked');}, gtag: (...x) => calls.push(x)}, {href:'https://scm-news.ru/',hostname:'scm-news.ru'});
  const link = {getAttribute: () => '/career.html'};
  const event = {button:0,target:{closest: q => q==='a[href]' ? link : null},preventDefault(){throw new Error('must not cancel navigation');}};
  assert.doesNotThrow(() => handler(event));
  assert.deepEqual(calls,[['event','interest_career']]);
});
test('tracker loads once only on nine pages with existing counters', () => {
  const pages = new Set(['index.html','about.html','blog.html','career.html','contact.html','experience.html','expertise.html','prompts.html','trends.html']);
  for (const filename of fs.readdirSync('.').filter(f => f.endsWith('.html'))) {
    const html=fs.readFileSync(filename,'utf8');
    const scripts=html.match(/<script\b[^>]*\bsrc\s*=\s*["'][^"']*visitor-events\.js/gi) || [];
    assert.equal(scripts.length, pages.has(filename) ? 1 : 0, filename);
    if (pages.has(filename)) assert.match(html, /mc\.yandex\.ru\/metrika\/tag\.js/);
  }
});

 test('tool attempts and diagnostic start send fixed events without inputs', () => {
  const callbacks={}, calls=[]; const doc={addEventListener:(type,fn)=>callbacks[type]=fn};
  install(doc,{ym:(...args)=>calls.push(args)}, {href:'https://scm-news.ru/inventory-turnover-calculator.html',hostname:'scm-news.ru'});
  callbacks.submit({target:{matches:s=>s==='form[data-inventory-tool]'}});
  assert.deepEqual(calls, [[108401876,'reachGoal','calculator_calculate']]);
  const diagnostic={}, events=[];
  install({addEventListener:(type,fn)=>diagnostic[type]=fn},{ym:(...args)=>events.push(args)}, {href:'https://scm-news.ru/scm-diagnostic.html',hostname:'scm-news.ru'});
  const target={closest:s=>s==='#scm-checklist select' ? {} : null, get value(){throw Error('must not read answer')}};
  diagnostic.change({target}); diagnostic.change({target});
  assert.deepEqual(events, [[108401876,'reachGoal','diagnostic_start']]);
 });
 test('calculator button records only an attempt', () => {
  let handler; const calls=[];
  install({addEventListener:(type,fn)=>{if(type==='click') handler=fn;}},{ym:(...args)=>calls.push(args)}, {href:'https://scm-news.ru/calculators.html',hostname:'scm-news.ru'});
  handler({button:0,target:{closest:s=>s==='button.calculate-btn'?{}:null}});
  assert.deepEqual(calls,[[108401876,'reachGoal','calculator_calculate']]);
 });

test('home provides distinct user channels used by the tracker', () => {
  const html=fs.readFileSync('index.html','utf8');
  for (const url of ['https://m.tenchat.ru/u/3CguEuQy','https://setka.ru/communities/01a15b2e-dfa8-7b4d-9059-6b74529f0ac3','https://setka.ru/communities/01a19c5c-b9c8-7a87-b08c-60a87d8f6049']) {
    assert.equal(html.split('href="'+url+'"').length - 1, 1, url);
  }
});
