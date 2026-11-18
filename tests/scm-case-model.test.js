'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { simulate } = require('../js/scm-case-model.js');
const sample = () => ({ stock:'200', demand:'40', horizon:'7', mainDay:'8', mainQty:'300', extraDay:'4', extraQty:'100' });

test('case simulator reproduces the worked example and reports both scenarios', () => {
  const {baseline,alternative} = simulate(sample());
  assert.deepEqual([baseline.requested,baseline.filledTotal,baseline.lostTotal,baseline.shortageDays,baseline.closingStock,baseline.receivedTotal], [280,200,80,2,0,0]);
  assert.deepEqual([alternative.requested,alternative.filledTotal,alternative.lostTotal,alternative.shortageDays,alternative.closingStock,alternative.receivedTotal], [280,280,0,0,20,100]);
  assert.deepEqual(alternative.days[3],{day:4,received:100,demand:40,filled:40,lost:0,balance:140});
});

test('arrivals happen before demand, only in their day; past shortages do not backlog', () => {
  const v=sample();v.extraDay='7';v.horizon='8';
  const {baseline,alternative}=simulate(v);
  assert.equal(alternative.days[5].lost,40);
  assert.equal(alternative.days[6].received,100);
  assert.equal(alternative.days[7].received,300);
  assert.equal(alternative.lostTotal,40);assert.equal(alternative.closingStock,320);
  assert.equal(baseline.lostTotal,80);assert.equal(baseline.closingStock,260);
  v.extraDay='8'; v.mainDay='8';
  const together=simulate(v).alternative;
  assert.equal(together.days[7].received,400);assert.equal(together.lostTotal,80);
});

test('zero demand, beyond-horizon deliveries and first-day arrival are handled', () => {
  const v=sample();v.horizon='1';v.stock='0';v.demand='0';v.mainDay='1';v.mainQty='10';v.extraDay='2';
  const r=simulate(v);assert.equal(r.baseline.closingStock,10);assert.equal(r.alternative.closingStock,10);assert.equal(r.baseline.lostTotal,0);
  v.demand='10';v.extraDay='1';v.extraQty='5';
  const after=simulate(v);assert.equal(after.baseline.lostTotal,0);assert.equal(after.baseline.closingStock,0);assert.equal(after.baseline.shortageDays,0);assert.equal(after.alternative.closingStock,5);
});

test('rejects invalid, non-finite, fractional or unbounded input', () => {
 for(const [key,value] of [['stock',''],['stock','-1'],['stock','1.5'],['stock','1e2'],['stock','NaN'],['stock','1000001'],['horizon','0'],['horizon','31'],['extraDay','0'],['mainDay','366'],['demand','Infinity'],['mainQty','9007199254740992'],['extraQty',2]]) {
  const v=sample();v[key]=value;assert.equal(simulate(v),null,`${key}=${value}`);
 }
 assert.equal(simulate(null),null);
});

test('both scenarios conserve units and extra stock never increases lost demand', () => {
 for(let seed=0;seed<80;seed++) {
  const v={stock:String(seed*3),demand:String(seed%17),horizon:String(seed%30+1),mainDay:String(seed%40+1),mainQty:String(seed*2),extraDay:String(seed%32+1),extraQty:String(seed*4)};
  const result=simulate(v);
  for(const r of [result.baseline,result.alternative]) {
   assert.equal(r.requested,r.filledTotal+r.lostTotal);
   assert.equal(Number(v.stock)+r.receivedTotal,r.filledTotal+r.closingStock);
   assert(r.days.every(day=>day.balance>=0 && day.lost>=0 && day.filled+day.lost===day.demand));
  }
  assert(result.alternative.lostTotal<=result.baseline.lostTotal);
 }
});

test('case laboratory is discoverable, linked, and clearly describes privacy and limitations', () => {
 const page='scm-case-lab.html',html=fs.readFileSync(page,'utf8');
 assert(html.includes(`rel="canonical" href="https://scm-news.ru/${page}"`));
 assert(fs.readFileSync('sitemap.xml','utf8').includes(`https://scm-news.ru/${page}`));
 for(const file of ['wiki.html','scm-academy.html','scm-internal-academy.html','scm-navigator.html']) assert(fs.readFileSync(file,'utf8').includes(`href="${page}"`));
 for(const phrase of ['не цифровой двойник и не прогноз','не отправляются и не сохраняются инструментом','не переносится на следующие дни','Поступления после горизонта','не создаёт заказов','не является оценкой финансового эффекта']) assert(html.includes(phrase),phrase);
 for(const [,,href] of html.matchAll(/href="(([^"#]+\.html)(?:#[^"]*)?)"/g)) if(!/^https?:/.test(href)) assert(fs.existsSync(href),href);
 const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]);assert.equal(new Set(ids).size,ids.length);
});
