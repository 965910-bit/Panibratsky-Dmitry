'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('js/contact-goals.js', 'utf8');
function setupContact(enabled, ym) {
  const listeners = {};
  const window = {ym};
  const document = {addEventListener: (type, fn) => {listeners[type] = fn;}};
  let script = source;
  if (enabled) {
    assert.equal((script.match(/const CONTACT_GOALS_ENABLED = false;/g) || []).length, 1);
    script = script.replace('const CONTACT_GOALS_ENABLED = false;', 'const CONTACT_GOALS_ENABLED = true;');
  }
  vm.runInNewContext(script, {window, document});
  return listeners;
}
function contactClick(handler, key) {
  let prevented = false;
  const link = {getAttribute: name => {assert.equal(name, 'data-contact-goal'); return key;},
    get href() {throw Error('URL must not be read');}, get textContent() {throw Error('text must not be read');}};
  handler({target:{closest:selector => {assert.equal(selector, 'a[data-contact-goal]'); return link;}},
    preventDefault() { prevented = true; }});
  assert.equal(prevented, false);
}
test('contact goals are disabled by default and do not register click handlers or send data', () => {
  let calls = 0;
  assert.deepEqual(setupContact(false, () => {calls++;}), {});
  assert.equal(calls, 0);
});
test('prepared goals, when explicitly enabled for testing, send only fixed identifiers without reading link data', () => {
  const sent = [];
  const {click} = setupContact(true, (...args) => sent.push(args));
  for (const key of ['phone', 'email', 'profile', '__proto__', 'constructor', 'private@example.test']) contactClick(click, key);
  assert.deepEqual(sent, [
    [108401876, 'reachGoal', 'contact_phone_click'],
    [108401876, 'reachGoal', 'contact_email_click'],
    [108401876, 'reachGoal', 'contact_profile_click']
  ]);
  assert.doesNotMatch(JSON.stringify(sent), /private@example|mailto:|tel:/);
  click({target:null}); click({target:{closest:()=>null}});
  click({defaultPrevented:true, target:{closest:()=>{throw Error('cancelled click');}}});
  click({button:2, target:{closest:()=>{throw Error('non-primary click');}}});
  assert.equal(sent.length, 3);
  for (const ym of [undefined, () => {throw Error('blocked');}]) contactClick(setupContact(true, ym).click, 'phone');
});
test('prepared script is not loaded and only intended public pages mark contact links', () => {
  for (const page of ['index.html','career.html','contact.html']) {
    const html = fs.readFileSync(page, 'utf8');
    assert.doesNotMatch(html, /src="js\/contact-goals\.js"/, page);
    const links = [...html.matchAll(/<a\b[^>]*data-contact-goal="([^"]+)"[^>]*>/g)];
    for (const [tag, href] of html.matchAll(/<a\b[^>]*href="((?:tel|mailto):[^"]+)"[^>]*>/g)) {
      assert.ok(tag.includes(`data-contact-goal="${href.startsWith('tel:') ? 'phone' : 'email'}"`), page);
    }
    assert.ok(links.length, page);
    for (const [, key] of links) assert.ok(['phone','email','profile'].includes(key));
    for (const [tag, key] of links) {
      const href = tag.match(/href="([^"]+)"/)[1];
      assert.ok(key === 'phone' ? href.startsWith('tel:') : key === 'email' ? href.startsWith('mailto:') : href === 'https://set.ki/EYUBwz5', page);
    }
  }
  const sitemap = fs.readFileSync('sitemap.xml', 'utf8');
  for (const [, url] of sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)) {
    const path = new URL(url).pathname.slice(1) || 'index.html';
    assert.doesNotMatch(fs.readFileSync(path, 'utf8'), /src="js\/contact-goals\.js"/, path);
  }
});

const trends = fs.readFileSync('trends.html','utf8');
const legacy = trends.match(/        function trackLegacyNavigation\(goal, eventName, category, label\) \{[\s\S]*?\n        \}/)[0];
const listeners = trends.match(/        document\.querySelectorAll\('#nav-menu a'\)\.forEach[\s\S]*?(?=\n        window\.addEventListener\('scroll')/)[0];
function setupLegacy(ym, gtag) {
  const nav={getAttribute:()=> 'about.html',addEventListener:(_type, fn)=>{nav.click=fn;}};
  const footer={href:'mailto:private@example.test?subject=secret',closest:()=>true,addEventListener:(_type,fn)=>{footer.click=fn;}};
  const rss={addEventListener:(_type,fn)=>{rss.click=fn;}};
  const document={querySelectorAll:s=>s==='#nav-menu a'?[nav]:[footer],querySelector:()=>rss};
  vm.runInNewContext(legacy+'\n'+listeners, {document,window:{ym,gtag}});
  return {nav,footer,rss};
}
test('legacy navigation keeps fixed existing event names and isolates counter failures', () => {
  const a=[], b=[]; const links=setupLegacy((...x)=>a.push(x),(...x)=>b.push(x));
  links.nav.click(); links.footer.click(); links.rss.click();
  assert.deepEqual(a.map(x=>x[2]),['nav_click_about','footer_link_click_email','footer_rss_click']);
  assert.deepEqual(b.map(x=>x[1]),['nav_click','footer_link_click','footer_rss_click']);
  assert.doesNotMatch(JSON.stringify([a,b]), /private@example|secret|mailto:/);
  let ga=0, metrika=0;
  const noYm=setupLegacy(()=>{throw Error('blocked')},()=>ga++); noYm.nav.click();noYm.footer.click();noYm.rss.click(); assert.equal(ga,3);
  const noGa=setupLegacy(()=>metrika++,()=>{throw Error('blocked')}); noGa.nav.click();noGa.footer.click();noGa.rss.click(); assert.equal(metrika,3);
  const absent=setupLegacy(undefined,undefined); assert.doesNotThrow(()=>{absent.nav.click();absent.footer.click();absent.rss.click();});
});
