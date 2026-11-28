'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const install=require('../js/wiki-topic-search.js');

test('local search normalises text, filters all words, resets and never interprets input as HTML',()=>{
 const listeners={};const control={hidden:true},input={value:'',addEventListener:(type,fn)=>listeners[type]=fn},status={},empty={};
 const topics=[{dataset:{keywords:'склад часы трудозатраты'},textContent:'Рабочее время',hidden:false}, {dataset:{keywords:'поставщик ёмкость'},textContent:'Оценка',hidden:false}];
 const document={getElementById:id=>({'wiki-search-control':control,'wiki-search-input':input,'wiki-search-status':status,'wiki-search-empty':empty})[id],querySelectorAll:()=>topics};
 install(document);assert.equal(control.hidden,false);assert.match(status.textContent,/2 из 2/);
 input.value='СКЛАД ЧАСЫ';listeners.input();assert.equal(topics[0].hidden,false);assert.equal(topics[1].hidden,true);
 input.value='емкость';listeners.input();assert.equal(topics[0].hidden,true);assert.equal(topics[1].hidden,false);
 input.value='<img src=x onerror=alert(1)>';listeners.input();assert.equal(empty.hidden,false);assert.match(status.textContent,/0 из 2/);
 input.value='';listeners.input();assert.equal(empty.hidden,true);assert(topics.every(x=>!x.hidden));
 const source=fs.readFileSync('js/wiki-topic-search.js','utf8');assert.doesNotMatch(source,/innerHTML|fetch\(|localStorage|sessionStorage|XMLHttpRequest|\.ym\(|\.gtag\(/);
});
test('every curated index target is an existing canonical sitemap page with a valid anchor',()=>{
 const wiki=fs.readFileSync('wiki.html','utf8'); const sitemap=fs.readFileSync('sitemap.xml','utf8');
 const items=[...wiki.matchAll(/<li data-wiki-topic data-keywords="[^"]*"><a href="([^"]+)">/g)];assert.equal(items.length,115);
 assert.equal(new Set(items.map(x=>x[1])).size,items.length);
 for(const [,url] of items){const [file,anchor]=url.split('#');assert(fs.existsSync(file),url);assert(sitemap.includes(`https://scm-news.ru/${file}`),url);
 if(anchor) assert.match(fs.readFileSync(file,'utf8'),new RegExp(`(?:id|name)=["']${anchor}["']`),url);}
});
