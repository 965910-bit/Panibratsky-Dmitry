import {test} from 'node:test';
import assert from 'node:assert/strict';
import {handle} from '../telegram-review/worker.mjs';

class DB {
  rows = new Map();
  prepare(sql) { const db = this; return {bind(...v) { return {
    async run() {
      if (sql.startsWith('INSERT')) {
        if ([...db.rows.values()].some(r => r.source_url === v[1])) throw Error('duplicate');
        db.rows.set(v[0], {id:v[0], source_url:v[1], text:v[2], state:'notifying'}); return {success:true,meta:{changes:1}};
      }
      if (sql.includes("SET state = 'ready'")) { const r=db.rows.get(v[2]); if (!r || r.state !== 'notifying') return {meta:{changes:0}}; r.state='ready'; r.review_message_id=v[0]; r.photo_file_id=v[1]; return {meta:{changes:1}}; }
      if (sql.includes('SET state = ?')) { const r=db.rows.get(v[1]); if (!r || r.state !== 'ready' || r.review_message_id !== v[2]) return {meta:{changes:0}}; r.state=v[0]; return {meta:{changes:1}}; }
      if (sql.includes("SET state = 'sent'")) { const r=db.rows.get(v[1]); if (!r || r.state !== 'sending') return {meta:{changes:0}}; r.state='sent'; r.channel_message_id=v[0]; return {meta:{changes:1}}; }
      throw Error('unknown query');
    },
    async first() { const r=db.rows.get(v[0]); return r?.state === 'sending' ? r : null; }
  }; }}; }
}
function setup(failChannel=false) {
 const db=new DB(); const env={DB:db,REVIEWER_ID:'123',CHANNEL_ID:'-100123',BOT_TOKEN:'123456:'+ 'a'.repeat(32),WEBHOOK_SECRET:'w'.repeat(40),INTAKE_SECRET:'i'.repeat(40)}; const calls=[];
 const api=async (url,init) => {const method=url.split('/').at(-1), data=init.body instanceof FormData ? Object.fromEntries(init.body.entries()) : JSON.parse(init.body); calls.push({method,data}); if(failChannel && ['sendMessage','sendPhoto'].includes(method) && data.chat_id===env.CHANNEL_ID) throw Error('network'); return new Response(JSON.stringify({ok:true,result:{message_id:data.chat_id===env.REVIEWER_ID ? 11:22,photo:[{file_id:'photo-token'}]}}),{status:200});};
 const request=(path,data,headers={})=> new Request('https://example.com'+path,{method:'POST',headers:{'content-type':'application/json',...headers},body:JSON.stringify(data)});
 const add=(data={text:'Склад: проверенный текст',source_url:'https://example.org/news'})=>handle(request('/intake',data,{authorization:'Bearer '+env.INTAKE_SECRET}),env,api);
 const click=(id,action='approve',overrides={})=>handle(request('/telegram',{callback_query:{id:'callback',from:{id:123},message:{message_id:11,chat:{id:123,type:'private'}},data:`${action}:${id}`,...overrides}},{'x-telegram-bot-api-secret-token':env.WEBHOOK_SECRET}),env,api);
 return {db,env,calls,api,request,add,click};
}
test('approval publishes only once, rejects duplicate intake and duplicate clicks',async()=>{
 const x=setup(); assert.equal((await x.add()).status,201); assert.equal((await x.add()).status,409);
 const id=[...x.db.rows.keys()][0]; await Promise.all([x.click(id), x.click(id)]);
 assert.equal(x.db.rows.get(id).state,'sent'); assert.equal(x.calls.filter(c=>c.method==='sendMessage' && c.data.chat_id===x.env.CHANNEL_ID).length,1);
});
test('unauthorised access and other reviewers cannot publish',async()=>{
 const x=setup(); const bad=await handle(x.request('/intake',{text:'x',source_url:'https://example.org'},{authorization:'Bearer wrong'}),x.env,x.api); assert.equal(bad.status,403);
 await x.add(); const id=[...x.db.rows.keys()][0]; await x.click(id,'approve',{from:{id:124}}); await x.click(id,'approve',{message:{message_id:99,chat:{id:123,type:'private'}}});
 const noSecret=await handle(x.request('/telegram',{}),x.env,x.api); assert.equal(noSecret.status,403);
 assert.equal(x.db.rows.get(id).state,'ready'); assert.equal(x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length,0);
});
test('rejected drafts do not publish and network uncertainty is never retried',async()=>{
 const x=setup(true); await x.add(); const id=[...x.db.rows.keys()][0]; await x.click(id); await x.click(id);
 assert.equal(x.db.rows.get(id).state,'sending'); assert.equal(x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length,1);
 const y=setup(); await y.add(); const id2=[...y.db.rows.keys()][0]; await y.click(id2,'reject'); await y.click(id2); assert.equal(y.db.rows.get(id2).state,'rejected'); assert.equal(y.calls.filter(c=>c.data.chat_id===y.env.CHANNEL_ID).length,0);
});
test('bad drafts, unsafe urls, missing config and oversize payload fail closed',async()=>{
 const x=setup(); assert.equal((await x.add({text:'a',source_url:'javascript:alert(1)'})).status,400);
 assert.equal((await x.add({text:'a'.repeat(3001),source_url:'https://example.org'})).status,400);
 assert.equal((await x.add({text:'a',source_url:'https://user:pass@example.org'})).status,400);
 assert.equal((await handle(x.request('/telegram',{}),{},x.api)).status,503);
 assert.equal((await x.add({text:'x'.repeat(20000),source_url:'https://example.org'})).status,400);
 assert.equal(x.calls.length,0);
});

const fakePng = () => { const bytes=Buffer.alloc(33); Buffer.from([137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82]).copy(bytes); bytes.writeUInt32BE(1080,16); bytes.writeUInt32BE(1080,20); return bytes.toString('base64'); };
test('card and text are reviewed together and identical approved photo is sent once',async()=>{
 const x=setup(); assert.equal((await x.add({text:'Проверенная новость',source_url:'https://example.org/news',card_base64:fakePng()})).status,201);
 const id=[...x.db.rows.keys()][0]; const review=x.calls.find(c=>c.method==='sendPhoto');
 assert.equal(review.data.chat_id,x.env.REVIEWER_ID); assert.match(review.data.caption,/Проверенная новость/); assert(review.data.photo instanceof Blob);
 assert.equal(x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length,0);
 await Promise.all([x.click(id),x.click(id)]); const channel=x.calls.filter(c=>c.method==='sendPhoto' && c.data.chat_id===x.env.CHANNEL_ID);
 assert.equal(channel.length,1); assert.equal(channel[0].data.photo,'photo-token'); assert.equal(channel[0].data.caption,'Проверенная новость\n\nИсточник: https://example.org/news');
 assert.equal(x.db.rows.get(id).state,'sent');
});
test('invalid card or long caption fail before storing or notifying',async()=>{
 const x=setup(); assert.equal((await x.add({text:'a',source_url:'https://example.org/news',card_base64:'abcd'})).status,400);
 assert.equal((await x.add({text:'a'.repeat(1000),source_url:'https://example.org/news',card_base64:fakePng()})).status,400);
 assert.equal(x.db.rows.size,0); assert.equal(x.calls.length,0);
});
test('uncertain photo delivery does not retry',async()=>{
 const x=setup(true); await x.add({text:'Новость',source_url:'https://example.org/news',card_base64:fakePng()});
 const id=[...x.db.rows.keys()][0]; await x.click(id); await x.click(id);
 assert.equal(x.db.rows.get(id).state,'sending'); assert.equal(x.calls.filter(c=>c.method==='sendPhoto' && c.data.chat_id===x.env.CHANNEL_ID).length,1);
});
