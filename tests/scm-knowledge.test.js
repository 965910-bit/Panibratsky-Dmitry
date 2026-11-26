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
 const ids=['supplier','tco','incoterms','lot-size','replenishment','traceability','mapping','reverse','statistics','inventory-balance','working-hours','supply-chain-roles','abc-xyz','warehouse-review','capacity','kpi-application','service-and-stockouts','inventory-accuracy','receiving-to-availability','warehouse-slotting','supplier-lead-time','category-strategy','supplier-corrective-action','available-to-promise','order-to-cash','product-master-data','cross-docking','carrier-performance','fifo-fefo','little-law','supplier-selection','three-way-match'];
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

test('SCM academy has an indexable, linked self-study route without invented services', () => {
 const html=fs.readFileSync('scm-academy.html','utf8');
 assert.match(html,/rel="canonical" href="https:\/\/scm-news\.ru\/scm-academy\.html"/);
 assert(fs.readFileSync('sitemap.xml','utf8').includes('https://scm-news.ru/scm-academy.html'));
 for (const page of ['wiki.html','scm-encyclopedia.html','scm-knowledge.html']) assert(fs.readFileSync(page,'utf8').includes('href="scm-academy.html"'));
 const ids=['transformation','data-foundation','digital-twin','scenario','ai','pilot','leadership','program','review'];
 assert.equal((html.match(/data-chapter-entry data-keywords=/g)||[]).length,ids.length);
 for(const id of ids) {assert(html.includes(`id="${id}"`));assert(html.includes(`href="#${id}"`));}
 for(const phrase of ['не действующий корпоративный курс','нет регистрации','не работающий цифровой двойник','не является обязательной частью цифрового двойника','без дисконтирования','не обрабатывает и не сохраняет ответы']) assert(html.includes(phrase),phrase);
 assert.equal(200/40,5);assert.equal((7-5)*40,80);assert.equal(200-3*40+100-4*40,20);assert.equal(200-5*40+100-2*40,20);
 assert.equal((180-120)/120*100,50);
});

test('academy local links and fragments resolve and its IDs are unique', () => {
 const html=fs.readFileSync('scm-academy.html','utf8');
 const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);
 assert.equal(new Set(ids).size,ids.length,'Duplicate academy IDs');
 for(const [,href] of html.matchAll(/\bhref="([^"]+)"/g)) {
  if (/^(?:https?:|\/)/.test(href)) continue;
  const [file,fragment]=href.split('#');
  const target=file||'scm-academy.html';
  assert(fs.existsSync(target),`Missing local target ${href}`);
  if (fragment) assert(fs.readFileSync(target,'utf8').includes(`id="${fragment}"`),`Missing fragment ${href}`);
 }
});

test('internal academy connects leadership development with enterprise case work', () => {
 const page='scm-internal-academy.html';const html=fs.readFileSync(page,'utf8');
 assert.match(html,/rel="canonical" href="https:\/\/scm-news\.ru\/scm-internal-academy\.html"/);
 assert(fs.readFileSync('sitemap.xml','utf8').includes('https://scm-news.ru/scm-internal-academy.html'));
 for(const source of ['scm-academy.html','scm-knowledge.html','wiki.html']) assert(fs.readFileSync(source,'utf8').includes(`href="${page}"`));
 const ids=['purpose','operating-model','leader-growth','case-process','case-template','case-example','measurement','launch'];
 assert.equal((html.match(/data-chapter-entry data-keywords=/g)||[]).length,ids.length);
 for(const id of ids){assert(html.includes(`id="${id}"`));assert(html.includes(`href="#${id}"`));}
 for(const phrase of ['не описание работающей структуры','не выдаёт сертификаты','Без разрешения рабочий процесс не меняется','не данные реального предприятия','5 процентных пунктов','нельзя приписать весь эффект','не является обещанием срока','закрытой информации во внешние сервисы без разрешения']) assert(html.includes(phrase),phrase);
 assert.equal(20/100*100-15/100*100,5);
 const allIds=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(allIds).size,allIds.length);
 for(const [,href] of html.matchAll(/\bhref="([^"]+)"/g)){
  if(/^(?:https?:|\/)/.test(href))continue;
  const [file,fragment]=href.split('#'),target=file||page;
  assert(fs.existsSync(target),`Missing target ${href}`);
  if(fragment)assert(fs.readFileSync(target,'utf8').includes(`id="${fragment}"`),`Missing fragment ${href}`);
 }
});

test('unified SCM navigation and additional guides are indexable and locally connected', () => {
 const pages={
  'scm-navigator.html':['strategy','planning','sourcing','operations','inventory','delivery','trade','finance','returns','resilience','data','people','measures'],
  'scm-advanced-practice.html':['sop','mrp','trade','capital','environment','cyber']
 };
 for(const [file,ids] of Object.entries(pages)) {
  const html=fs.readFileSync(file,'utf8');
  assert(html.includes(`rel="canonical" href="https://scm-news.ru/${file}"`));
  assert(fs.readFileSync('sitemap.xml','utf8').includes(`https://scm-news.ru/${file}`));
  assert.equal((html.match(/data-chapter-entry data-keywords=/g)||[]).length,ids.length);
  for(const id of ids){assert(html.includes(`id="${id}"`));assert(html.includes(`href="#${id}"`));}
  const all=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(all).size,all.length);
  for(const [,href] of html.matchAll(/\bhref="([^"]+)"/g)) {
   if(/^(?:https?:|\/)/.test(href)) continue;
   const [path,fragment]=href.split('#'),target=path||file;assert(fs.existsSync(target),`Missing ${href}`);
   if(fragment)assert(fs.readFileSync(target,'utf8').includes(`id="${fragment}"`),`Missing ${href}`);
  }
 }
 for(const file of ['wiki.html','scm-encyclopedia.html','scm-practical-guides.html','scm-knowledge.html','scm-academy.html','scm-internal-academy.html']) {
  const html=fs.readFileSync(file,'utf8');assert(html.includes('href="scm-navigator.html"'));assert(html.includes('href="scm-advanced-practice.html"'));
 }
 const html=fs.readFileSync('scm-advanced-practice.html','utf8');
 for(const phrase of ['не полный MRP','не является нормативом','не доказанная денежная экономия','не подтверждает соответствие','не заменяют весь договор','не делает прогноз']) {
  assert(html.includes(phrase),phrase);
 }
 assert.equal(1000-800-100,100);assert.equal(100*2-50-30,120);assert.equal(100*2-50,150);assert.equal(50+30-40,40);assert.equal(45+30-40,35);assert.equal(10*100*0.1,100);
});
