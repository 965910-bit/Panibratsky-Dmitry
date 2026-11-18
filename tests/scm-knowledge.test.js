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

test('encyclopedia is a linked, canonical static guide with working chapter anchors', () => {
 const html = fs.readFileSync('scm-encyclopedia.html','utf8');
 const pages = ['wiki.html','scm-knowledge.html'];
 assert.match(html,/rel="canonical" href="https:\/\/scm-news\.ru\/scm-encyclopedia\.html"/);
 assert(fs.readFileSync('sitemap.xml','utf8').includes('https://scm-news.ru/scm-encyclopedia.html'));
 for (const page of pages) assert(fs.readFileSync(page,'utf8').includes('href="scm-encyclopedia.html"'));
 const ids=['basics','planning','procurement','inventory','eoq','production','warehouse','transport','metrics','risk','returns','data','glossary'];
 assert.equal((html.match(/data-chapter-entry data-keywords=/g)||[]).length,ids.length);
 for(const id of ids){assert(html.includes(`id="${id}"`));assert(html.includes(`href="#${id}"`));}
 assert.match(html,/не исчерпывающая энциклопедия/);
 assert.match(html,/без дисконтирования/);assert.match(html,/поздняя поставка может не предотвратить дефицит/);
 assert.equal((Math.abs(90-100)+Math.abs(120-100))/200*100,15);
 const models=require('../js/inventory-models.js');
 assert.equal(models.eoq(['1000','200','10']),200);
 assert.equal(models.reorderPoint(['40','5','60']),260);
 assert.equal(require('../js/otif.js').calculate(80,100),80);
 assert.equal(300*60+3000,21000);
});

test('encyclopedia search filters only the index and restores all topics', () => {
 const events={}, box={hidden:true},input={value:'',addEventListener:(type,fn)=>events[type]=fn},status={},empty={};
 const entries=[{dataset:{keywords:'прогноз спрос'},textContent:'Планирование',hidden:false},{dataset:{keywords:'сервис otif'},textContent:'Показатели',hidden:false}];
 const document={getElementById:id=>({'chapter-search-box':box,'chapter-search':input,'chapter-search-status':status,'chapter-empty':empty})[id],querySelectorAll:()=>entries};
 vm.runInNewContext(fs.readFileSync('js/scm-encyclopedia.js','utf8'),{document});
 assert.equal(box.hidden,false);assert.match(status.textContent,/2 из 2/);
 input.value='спрос планирование';events.input();assert.equal(entries[0].hidden,false);assert.equal(entries[1].hidden,true);
 input.value='отсутствует';events.input();assert.equal(empty.hidden,false);assert.match(status.textContent,/0 из 2/);
 input.value='OTIF';events.input();assert.equal(entries[0].hidden,true);assert.equal(entries[1].hidden,false);
 input.value='';events.input();assert.equal(empty.hidden,true);assert(entries.every(entry=>!entry.hidden));
});

test('practical guides are linked, indexable and preserve the documented model boundaries', () => {
 const html = fs.readFileSync('scm-practical-guides.html','utf8');
 assert.match(html,/rel="canonical" href="https:\/\/scm-news\.ru\/scm-practical-guides\.html"/);
 assert(fs.readFileSync('sitemap.xml','utf8').includes('https://scm-news.ru/scm-practical-guides.html'));
 for(const page of ['wiki.html','scm-encyclopedia.html']) assert(fs.readFileSync(page,'utf8').includes('href="scm-practical-guides.html'));
 const ids=['supplier','tco','incoterms','lot-size','replenishment','traceability','mapping','reverse','statistics'];
 assert.equal((html.match(/data-chapter-entry data-keywords=/g)||[]).length,ids.length);
 for(const id of ids){assert(html.includes(`id="${id}"`));assert(html.includes(`href="#${id}"`));}
 for(const phrase of ['не юридическая консультация','не всегда совпадает','не скрывает тексты','не универсальное разрешение','версия 2.0, 2017','не измерение срока конкретной доставки']) assert(html.includes(phrase),phrase);
 assert(html.includes('2 011 руб./год'));assert(html.includes('2 033 руб./год'));
 const costs=q=>1000/q*200+q/2*10;
 assert.equal(Math.round(costs(180)),2011);assert.equal(Math.round(costs(240)),2033);
 assert.equal(require('../js/inventory-models.js').reorderPoint(['20','4','30']),110);
 assert.equal(require('../js/otif.js').calculate(18,20),90);
 assert.equal(70+50-20,100);assert.equal(90000+12000+8000,110000);assert.equal(100000+5000+2000,107000);
});
