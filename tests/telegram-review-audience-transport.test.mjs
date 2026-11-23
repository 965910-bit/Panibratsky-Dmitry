import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createAudienceTransport} from '../telegram-review/audience-transport.mjs';
const token='123456:'+ 'a'.repeat(32);
test('single request delivers text or photo without markup or secret in result',async()=>{
 const calls=[];const send=createAudienceTransport(token,async(url,init)=>{calls.push({url,init});return Response.json({ok:true,result:{message_id:7,private:'ignore'}})});
 assert.deepEqual(await send({chatId:'123',text:'Текст и ссылка',photoFileId:null}),{message_id:7});
 assert.deepEqual(await send({chatId:'-100123',text:'Подпись',photoFileId:'photo-id'}),{message_id:7});
 assert.equal(calls.length,2);assert.match(calls[0].url,/\/sendMessage$/);assert.match(calls[1].url,/\/sendPhoto$/);
 assert.deepEqual(JSON.parse(calls[0].init.body),{chat_id:'123',text:'Текст и ссылка',disable_web_page_preview:true});
 assert.deepEqual(JSON.parse(calls[1].init.body),{chat_id:'-100123',photo:'photo-id',caption:'Подпись'});
 assert.equal(calls[0].init.redirect,'error');assert(calls[0].init.signal);assert(!('parse_mode' in JSON.parse(calls[1].init.body)));
});
test('invalid inputs never call transport',async()=>{
 let n=0;const fake=async()=>{n++;};assert.throws(()=>createAudienceTransport('invalid',fake));const send=createAudienceTransport(token,fake);
 for (const payload of [{chatId:'@channel',text:'x'}, {chatId:'1',text:''}, {chatId:'1',text:'a'.repeat(1025),photoFileId:'p'}, {chatId:'1',text:'a'.repeat(4097)}, {chatId:'1',text:'x',photoFileId:''}]) await assert.rejects(()=>send(payload),/Invalid delivery payload/);
 assert.equal(n,0);
});
test('rate limits, failures, invalid bodies and timeouts fail without retries or leaking token',async()=>{
 for (const fake of [async()=>new Response('secret',{status:429}),async()=>new Response('x'.repeat(8193)),async()=>new Response('invalid'),async()=>Response.json({ok:false,description:'secret'}),async()=>Response.json({ok:true,result:{message_id:0}}),async()=>{throw Error(`URL ${token}`)}]){
  let n=0;const send=createAudienceTransport(token,async(...args)=>{n++;return fake(...args)});
  await assert.rejects(()=>send({chatId:'1',text:'x'}),e=>e.message==='Telegram delivery not confirmed' && !e.message.includes(token));assert.equal(n,1);
 }
});
