'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('js/presentation-download.js','utf8');
function setup(ym,gtag) { let click; vm.runInNewContext(source,{window:{ym,gtag},document:{addEventListener(type,fn){assert.equal(type,'click');click=fn;}}});return click; }
function event(link=true,extra={}) {return {target:{closest(selector){assert.equal(selector,'a[data-presentation-download]');return link ? {} : null;}}, ...extra};}
test('download analytics sends fixed events independently and never prevents default',()=>{
 const y=[],g=[];const click=setup((...x)=>y.push(x),(...x)=>g.push(x));
 click(event());assert.deepEqual(y,[[108401876,'reachGoal','presentation_download']]);assert.deepEqual(g,[['event','presentation_download']]);
 click(event(false));click(event(true,{defaultPrevented:true}));click(event(true,{button:2}));click({target:null});assert.equal(y.length,1);assert.equal(g.length,1);
 let calls=0;assert.doesNotThrow(()=>setup(()=>{throw Error('blocked')},()=>calls++)(event()));assert.equal(calls,1);
 assert.doesNotThrow(()=>setup(undefined,undefined)(event()));
});
test('home links a public PDF and loads the event handler',()=>{
 const html=fs.readFileSync('index.html','utf8');assert.match(html,/<a\b[^>]*href="documents\/gerasimov-presentation\.pdf"[^>]*download[^>]*data-presentation-download/);
 assert.match(html,/<script src="js\/presentation-download\.js" defer><\/script>/);
 const pdf=fs.readFileSync('documents/gerasimov-presentation.pdf');assert.equal(pdf.subarray(0,5).toString(),'%PDF-');
});

test('career page provides the presentation and a photographic sharing preview',()=>{
 const html=fs.readFileSync('career.html','utf8');
 assert.match(html,/<a\b[^>]*href="documents\/gerasimov-presentation\.pdf"[^>]*download[^>]*data-presentation-download/);
 assert.match(html,/<script src="js\/presentation-download\.js" defer><\/script>/);
 assert.match(html,/<meta property="og:url" content="https:\/\/scm-news\.ru\/career\.html">/);
 assert.match(html,/<meta property="og:image" content="https:\/\/scm-news\.ru\/images\/gerasimov-career-share\.jpg">/);
 assert.equal(fs.readFileSync('images/gerasimov-career-share.jpg').subarray(0,3).toString('hex'),'ffd8ff');
 assert.doesNotMatch(html,/fonts\.googleapis\.com|fonts\.gstatic\.com/);
});
