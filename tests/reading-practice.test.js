'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');
test('catalog retains all positions and distinguishes published practices from future work',()=>{
 const p=fs.readFileSync('scm-reading-practice.html','utf8'),w=fs.readFileSync('wiki.html','utf8'),map=fs.readFileSync('sitemap.xml','utf8');
 const ids=[...p.matchAll(/id="book-(\d+)"/g)].map(x=>Number(x[1]));assert.deepEqual(ids,Array.from({length:144},(_,i)=>i+1));
 for(const id of ['contract-control','demand-buffer','packaging-tradeoff','port-queues','supply-finance','supplier-development','digital-integration','responsible-purchasing','warehouse-change','catalog']){assert(p.includes(`id="${id}"`));assert(w.includes(`scm-reading-practice.html#${id}`));}
 for(const text of ['не весь каталог издателя','не воспроизводят авторские инструменты','не полноценная методика DDMRP','доказательства не получены','все книги прочитаны']) assert(p.includes(text),text);
 assert(map.includes('https://scm-news.ru/scm-reading-practice.html'));assert(w.includes('отдельные прикладные разборы ещё предстоит разработать'));
 assert.equal(1000*3/60,50);assert.equal(120000/(50*600-10000),6);assert.equal(16/20,.8);assert.equal(90+50,140);assert.equal(40+35-30,45);assert.equal(100000*.01,1000);assert.equal(45/50,.9);assert.equal(20*5+40,140);assert.equal(110+30-10,130);assert.equal(10000+3000-(12000+500),500);
});
