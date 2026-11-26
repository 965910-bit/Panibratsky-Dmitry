'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const install=require('../js/scm-metrics-search.js');
test('search filters published indicators locally, handles ё and resets',()=>{
 const events={},control={hidden:true},input={value:'',addEventListener:(type,fn)=>events[type]=fn},status={},empty={};
 const cards=[{textContent:'Затраты на перевозку ёмкость',hidden:false},{textContent:'Случаи DART OSHA',hidden:false}];
 const doc={getElementById:id=>({'metric-search-control':control,'metric-search-input':input,'metric-search-status':status,'metric-search-empty':empty})[id],querySelectorAll:s=>s==='.metric-entry'?cards:[]};
 install(doc);assert.equal(control.hidden,false);assert.match(status.textContent,/2 из 2/);
 input.value='ПЕРЕВОЗКУ емкость';events.input();assert.equal(cards[0].hidden,false);assert.equal(cards[1].hidden,true);
 input.value='<img src=x>';events.input();assert.equal(empty.hidden,false);assert.match(status.textContent,/0 из 2/);
 input.value='';events.input();assert(cards.every(x=>!x.hidden));assert.equal(empty.hidden,true);
 const code=fs.readFileSync('js/scm-metrics-search.js','utf8');assert.doesNotMatch(code,/fetch\(|localStorage|sessionStorage|XMLHttpRequest|innerHTML|\.gtag\(|\.ym\(/);
});
