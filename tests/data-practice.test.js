'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');
test('published data and automation subjects replace planned cards with worked practices',()=>{
 const page=fs.readFileSync('scm-data-practice.html','utf8'),wiki=fs.readFileSync('wiki.html','utf8');
 assert(page.includes('rel="canonical" href="https://scm-news.ru/scm-data-practice.html"'));
 assert(fs.readFileSync('sitemap.xml','utf8').includes('https://scm-news.ru/scm-data-practice.html'));
 const planned=wiki.split('<details class="wiki-planned">')[1].split('</details>')[0];
 for(const name of ['Аналитика данных в SCM','BI системы и дашборды','RPA автоматизация','Python для SCM'])assert(!planned.includes(`<h3>${name}</h3>`),name);
 for(const id of ['analytics','bi','rpa','python']){const m=page.match(new RegExp(`<article id="${id}"[\\s\\S]*?</article>`));assert(m&&m[0].length>1500,id);assert(m[0].includes('href="https://'),id);assert(wiki.includes(`href="scm-data-practice.html#${id}"`),id);}
 assert.equal(180/200*100,90);assert.equal((9+10)/(10+90)*100,19);assert.equal((30+40+50)/3,40);
});
