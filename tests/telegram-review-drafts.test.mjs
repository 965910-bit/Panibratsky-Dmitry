import {test} from 'node:test';
import assert from 'node:assert/strict';
import {prepareDraft,buildPayload,endpoint,submit} from '../telegram-review/drafts.mjs';
const item={title:'Склад <script>опасно</script> & логистика',description:'Текст новости',source:'Источник',link:'https://example.com/news'};
const prepared=()=>({...prepareDraft(item),comment:'Проверил материал: мой вывод.',ready_for_review:true});
test('preparation requires a valid story and never marks it ready',()=>{
 const d=prepareDraft(item); assert.equal(d.ready_for_review,false); assert.equal(d.comment,''); assert(!d.title.includes('<script>'));
 assert.throws(()=>prepareDraft({...item,title:'Оповещение Google — склад'}));
 assert.throws(()=>prepareDraft({...item,link:'javascript:alert(1)'}));
 assert.throws(()=>prepareDraft({...item,dead:true}));
 assert.throws(()=>buildPayload(d));
});
test('payload requires explicit review, human comment, and valid URL',()=>{
 const d=prepared(); assert.throws(()=>buildPayload({...d,ready_for_review:false})); assert.throws(()=>buildPayload({...d,comment:'  '}));
 assert.throws(()=>buildPayload({...d,source_url:'https://user:pass@example.com'}));
 const payload=buildPayload(d); assert.match(payload.text,/Проверил материал/); assert.equal(payload.source_url,'https://example.com/news');
});
test('submission uses explicit destination and makes exactly one request',async()=>{
 const calls=[]; const result=await submit(prepared(),{url:'https://test.example.workers.dev/intake',secret:'a'.repeat(32),fetcher:async (...args)=>{calls.push(args); return new Response('',{status:201});}});
 assert.equal(result,true); assert.equal(calls.length,1); assert.equal(calls[0][1].redirect,'error'); assert.equal(JSON.parse(calls[0][1].body).source_url,'https://example.com/news');
});
test('rejects unsafe targets and never retries failed or uncertain submission',async()=>{
 for(const url of ['http://x.workers.dev/intake','https://evil.example/intake','https://x.workers.dev/intake?x=1','https://user:pass@x.workers.dev/intake','https://x.workers.dev/other']) assert.throws(()=>endpoint(url));
 let count=0; await assert.rejects(()=>submit(prepared(),{url:'https://x.workers.dev/intake',secret:'a'.repeat(32),fetcher:async()=>{count++; return new Response('',{status:503});}}),/не повторяйте/); assert.equal(count,1);
});
