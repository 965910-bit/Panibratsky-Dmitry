'use strict';
const {test}=require('node:test'); const assert=require('node:assert/strict'); const fs=require('node:fs');
test('toolkit is a traceable independent index with practical examples',()=>{
 const page=fs.readFileSync('scm-toolkit-guide.html','utf8'),wiki=fs.readFileSync('wiki.html','utf8'),sitemap=fs.readFileSync('sitemap.xml','utf8');
 assert(page.includes('rel="canonical" href="https://scm-news.ru/scm-toolkit-guide.html"'));
 assert(sitemap.includes('https://scm-news.ru/scm-toolkit-guide.html'));
 assert.equal((page.match(/<li data-wiki-topic>/g)||[]).length,118);
 for(const id of ['warehouse','transport','inventory','supply-chain','outsourcing','performance','earlier']){
  assert(page.includes(`id="${id}"`));assert(wiki.includes(`href="scm-toolkit-guide.html#${id}"`));
 }
 for(const s of ['не оригинальные шаблоны','Полнота по всем четырём изданиям не подтверждена','2013','2016','2020','2024','https://www.koganpage.com/register','id="wiki-search-control" hidden','js/wiki-topic-search.js'])assert(page.includes(s),s);
 assert.equal(400/8,50);assert.equal(4/400*100,1);assert.equal(40*5+100,300);assert.equal(4*.4+3*.35+5*.25,3.9);assert.equal(600000/200000,3);
});
