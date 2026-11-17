import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, writeFile, rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {sendGalleryItem} from '../telegram-review/gallery-submit.mjs';
import {draftFingerprint} from '../telegram-review/drafts.mjs';
const makePng=d=>{ const head=Buffer.alloc(33); Buffer.from([137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82]).copy(head); head.writeUInt32BE(1080,16); head.writeUInt32BE(1080,20); const info=Buffer.from('SCM-Draft-SHA256\0'+draftFingerprint(d)), chunk=Buffer.alloc(info.length+12), end=Buffer.alloc(12); chunk.writeUInt32BE(info.length); chunk.write('tEXt',4); info.copy(chunk,8); end.write('IEND',4); return Buffer.concat([head,chunk,end]); };
const sample=()=>({version:1,title:'Склад и WMS',description:'Текст',source_name:'Источник',source_url:'https://example.org/test',comment:'Проверенный вывод',ready_for_review:true});
async function gallery(t, draft=sample()) {const dir=await mkdtemp(join(tmpdir(),'gallery-submit-')); t.after(()=>rm(dir,{recursive:true,force:true})); await writeFile(join(dir,'draft-01.json'),JSON.stringify(draft)); await writeFile(join(dir,'card-01.png'),makePng(draft)); return dir;}
const opts=fetcher=>({send:true,url:'https://test.example.workers.dev/intake',secret:'a'.repeat(32),fetcher});
test('preview is offline and submitting sends exactly one verified draft and card',async(t)=>{
 const dir=await gallery(t); let count=0, body; const fetcher=async(_url,init)=>{count++; body=JSON.parse(init.body);return new Response('',{status:201});};
 const preview=await sendGalleryItem(dir,1,{fetcher}); assert.equal(preview.sent,false); assert.match(preview.text,/Проверенный вывод/); assert.equal(count,0);
 const sent=await sendGalleryItem(dir,1,opts(fetcher)); assert.equal(sent.sent,true); assert.equal(count,1); assert.equal(body.source_url,'https://example.org/test'); assert.ok(body.card_base64);
});
test('unready, changed card, invalid index, and failed delivery all fail closed',async(t)=>{
 const dir=await gallery(t); let count=0; const fail=async()=>{count++;return new Response('',{status:503});};
 await assert.rejects(()=>sendGalleryItem(dir,0,opts(fail))); await assert.rejects(()=>sendGalleryItem(dir,1,opts(fail))); assert.equal(count,1);
 await writeFile(join(dir,'draft-01.json'),JSON.stringify({...sample(),ready_for_review:false})); await assert.rejects(()=>sendGalleryItem(dir,1,opts(fail)));
 await writeFile(join(dir,'draft-01.json'),JSON.stringify({...sample(),title:'Изменено'})); await assert.rejects(()=>sendGalleryItem(dir,1,opts(fail)),/не соответствует/); assert.equal(count,1);
});
test('synthetic PNG smoke fixture is previewable offline and clearly not a publication',async()=>{
 const out=await sendGalleryItem('tests/fixtures/telegram-png-smoke',1);
 assert.equal(out.sent,false);
 assert.match(out.text,/техническая проверка/i);
 assert.match(out.source_url,/^https:\/\/example\.org\/scm-test-/);
});
