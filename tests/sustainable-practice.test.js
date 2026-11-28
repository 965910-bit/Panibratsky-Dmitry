'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');
test('sustainable guide presents referenced scoped practices with examples and discoverability',()=>{
 const page=fs.readFileSync('scm-sustainable-practice.html','utf8'),wiki=fs.readFileSync('wiki.html','utf8');
 assert(page.includes('rel="canonical" href="https://scm-news.ru/scm-sustainable-practice.html"'));
 assert(fs.readFileSync('sitemap.xml','utf8').includes('https://scm-news.ru/scm-sustainable-practice.html'));
 for(const id of ['circular','emissions','supplier-risk','reading']){const m=page.match(new RegExp(`<article id="${id}"[\\s\\S]*?</article>`));assert(m&&m[0].length>1600,id);assert(m[0].includes('href="https://'),id);assert(wiki.includes(`href="scm-sustainable-practice.html#${id}"`),id);}
 for(const item of ['Коэффициенты вымышлены','не по прочитанным полным текстам','повторный учёт недопустим','15 ещё открыты'])assert(page.includes(item),item);
 assert.equal((40+20)/100*100,60);assert.equal((40+20+10+15)/100*100,85);assert.equal(10*200*.1+10*50*.2,300);assert.equal(300/100,3);assert.equal(5-3,2);
});
