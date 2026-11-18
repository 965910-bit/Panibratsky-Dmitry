'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('SCM guide is discoverable and its local links and references are valid', () => {
 const html=fs.readFileSync('scm-knowledge.html','utf8');
 assert.match(html, /<html lang="ru">/);
 assert.match(html, /rel="canonical" href="https:\/\/scm-news\.ru\/scm-knowledge\.html"/);
 assert(fs.readFileSync('sitemap.xml','utf8').includes('https://scm-news.ru/scm-knowledge.html'));
 for(const page of ['wiki.html','calculators.html']) assert(fs.readFileSync(page,'utf8').includes('href="scm-knowledge.html"'));
 assert.equal((html.match(/data-knowledge-card data-keywords=/g)||[]).length,8);
 assert.match(html,/id="inventory-guide"/);assert.match(html,/840/);
 assert.match(html,/не гарантирует уровень обслуживания/);
 for(const [,href] of html.matchAll(/href="([^"#]+\.html)(?:#[^"]*)?"/g)) {
   if (!/^https?:/.test(href)) assert(fs.existsSync(href),`Missing ${href}`);
 }
 for(const [,url] of html.matchAll(/href="(https:\/\/www\.supplychaintoday\.com\/[^\"]+)"/g)) assert(url.startsWith('https://www.supplychaintoday.com/'));
});

test('directory search is local, supports ё and multiple words, and restores all cards', () => {
 const events={};const area={hidden:true},input={value:'',addEventListener:(type,fn)=>events[type]=fn},status={},empty={};
 const cards=[{dataset:{keywords:'запасы склад'},textContent:'Пополнение',hidden:false},{dataset:{keywords:'поставщик'},textContent:'Закупки',hidden:false}];
 const document={getElementById:id=>({'knowledge-search':area,'topic-search':input,'topic-count':status,'topic-empty':empty})[id],querySelectorAll:()=>cards};
 vm.runInNewContext(fs.readFileSync('js/scm-knowledge.js','utf8'),{document});
 assert.equal(area.hidden,false);assert.match(status.textContent,/2 из 2/);
 input.value='СКЛАД пополнЁние';events.input();assert.equal(cards[0].hidden,false);assert.equal(cards[1].hidden,true);
 input.value='несуществующий';events.input();assert.equal(empty.hidden,false);assert.match(status.textContent,/0 из 2/);
 input.value='';events.input();assert.equal(empty.hidden,true);assert(cards.every(c=>!c.hidden));
});
