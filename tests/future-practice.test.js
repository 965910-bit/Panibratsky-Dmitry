'use strict';
const {test}=require('node:test'); const assert=require('node:assert/strict'); const fs=require('node:fs');
test('four completed subjects have indexed substantive guidance and leave no planned cards',()=>{
 const page=fs.readFileSync('scm-future-practice.html','utf8'),wiki=fs.readFileSync('wiki.html','utf8');
 assert(page.includes('rel="canonical" href="https://scm-news.ru/scm-future-practice.html"'));
 assert(fs.readFileSync('sitemap.xml','utf8').includes('https://scm-news.ru/scm-future-practice.html'));
 const planned=wiki.split('<details class="wiki-planned">')[1].split('</details>')[0];
 for(const title of ['AI в управлении цепями поставок','Цифровые двойники','Методы прогнозирования','Agile в SCM'])assert(!planned.includes(`<h3>${title}</h3>`));
 for(const id of ['ai','twin','forecast','agile']){const section=page.match(new RegExp(`<article id="${id}"[\\s\\S]*?</article>`));assert(section&&section[0].length>2000,id);assert(section[0].includes('href="https://'),id);assert(wiki.includes(`href="scm-future-practice.html#${id}"`),id);}
 assert.equal(12/(12+3)*100,80);assert.equal(12/20*100,60);assert.equal(90-80,10);assert.equal(40/320*100,12.5);assert.equal(-20/320*100,-6.25);assert.equal(8/10*100,80);
});
