'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
test('published procurement topics replace their planned cards and link to complete sections',()=>{
 const page=fs.readFileSync('scm-procurement-practice.html','utf8');
 const wiki=fs.readFileSync('wiki.html','utf8');
 assert.match(page,/rel="canonical" href="https:\/\/scm-news\.ru\/scm-procurement-practice\.html"/);
 assert(fs.readFileSync('sitemap.xml','utf8').includes('https://scm-news.ru/scm-procurement-practice.html'));
 assert(wiki.includes('href="scm-procurement-practice.html"'));
 const planned=wiki.split('<details class="wiki-planned">')[1].split('</details>')[0];
 for(const name of ['Стратегия закупок','Управление поставщиками','Оптимизация затрат на закупки','Управление контрактами','Аналитика закупок']) assert(!planned.includes(`<h3>${name}</h3>`),name);
 for(const id of ['strategy','suppliers','cost','contracts','analytics']) {
  assert(page.includes(`href="#${id}"`));
  const section=page.match(new RegExp(`<article id="${id}"[\\s\\S]*?</article>`));
  assert(section,id);assert(section[0].includes('href="https://'),id);assert(section[0].length>1600,id);
 }
 assert.equal((1000000+80000+220000)-(1100000+50000+100000),50000);
 assert.equal((12+18+30)/3,20);assert.equal(200000/4000000*100,5);
});
