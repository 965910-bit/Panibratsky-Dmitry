'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');
test('published improvement subjects replace planned entries with worked examples',()=>{
 const page=fs.readFileSync('scm-improvement-practice.html','utf8'),wiki=fs.readFileSync('wiki.html','utf8');
 assert(page.includes('rel="canonical" href="https://scm-news.ru/scm-improvement-practice.html"'));
 assert(fs.readFileSync('sitemap.xml','utf8').includes('https://scm-news.ru/scm-improvement-practice.html'));
 const planned=wiki.split('<details class="wiki-planned">')[1].split('</details>')[0];
 for(const name of ['Разработка KPI систем','Lean Six Sigma','Управление изменениями','Оптимизация процессов']) assert(!planned.includes(`<h3>${name}</h3>`),name);
 for(const id of ['kpi','lean','change','process']){const m=page.match(new RegExp(`<article id="${id}"[\\s\\S]*?</article>`));assert(m&&m[0].length>1500,id);assert(m[0].includes('href="https://'),id);assert(wiki.includes(`href="scm-improvement-practice.html#${id}"`),id);}
 assert.equal(8/200*100,4);assert.equal(18/20*100,90);assert.equal(30/10,3);
});
