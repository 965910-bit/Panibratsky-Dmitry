'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
test('published SCM flow topics are complete linked and no longer planned',()=>{
 const page=fs.readFileSync('scm-flow-practice.html','utf8'),wiki=fs.readFileSync('wiki.html','utf8');
 assert(page.includes('rel="canonical" href="https://scm-news.ru/scm-flow-practice.html"'));
 assert(fs.readFileSync('sitemap.xml','utf8').includes('https://scm-news.ru/scm-flow-practice.html'));
 const planned=wiki.split('<details class="wiki-planned">')[1].split('</details>')[0];
 for(const topic of ['Стратегия SCM','Управление запасами','Оптимизация складов','Транспортная логистика'])assert(!planned.includes(`<h3>${topic}</h3>`),topic);
 for(const id of ['strategy','inventory','warehouse','transport']){
  const section=page.match(new RegExp(`<article id="${id}"[\\s\\S]*?</article>`));
  assert(section&&section[0].length>1500,id);assert(section[0].includes('href="https://'),id);
  assert(wiki.includes(`href="scm-flow-practice.html#${id}"`),id);
 }
 assert.equal(70+50-20,100);assert.equal(20*4+30,110);assert.equal(150000/300,500);
});
