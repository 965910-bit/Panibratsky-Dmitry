import {test} from 'node:test';
import assert from 'node:assert/strict';
import {handle} from '../telegram-review/worker.mjs';

class DB {
  rows = new Map();
  prepare(sql) { const db = this; return {async all() {
    if (sql.startsWith('SELECT state, COUNT')) {
      const counts = {}; for (const row of db.rows.values()) counts[row.state] = (counts[row.state] || 0) + 1;
      return {success:true,results:Object.entries(counts).map(([state,count])=>({state,count}))};
    }
    if (sql.startsWith('SELECT id, state, created_at')) {
      return {success:true,results:[...db.rows.values()].filter(r=>['sending','notifying'].includes(r.state)).slice(0,5).map(r=>({id:r.id,state:r.state,created_at:r.created_at}))};
    }
    throw Error('unknown query');
  },bind(...v) { return {
    async run() {
      if (sql.startsWith('INSERT')) {
        if ([...db.rows.values()].some(r => ['notifying','ready','sending'].includes(r.state))) return {success:true,meta:{changes:0}};
        if ([...db.rows.values()].some(r => r.source_url === v[1])) throw Error('duplicate');
        db.rows.set(v[0], {id:v[0], source_url:v[1], text:v[2], state:'notifying',created_at:v[3]}); return {success:true,meta:{changes:1}};
      }
      if (sql.includes("resolution_kind = 'confirmed_channel_message'")) { const r=db.rows.get(v[2]); if (!r || r.state !== 'sending' || r.channel_message_id != null || r.resolution_kind != null || r.resolved_at != null) return {success:true,meta:{changes:0}}; r.state='sent'; r.channel_message_id=v[0]; r.resolved_at=v[1]; r.resolution_kind='confirmed_channel_message'; return {success:true,meta:{changes:1}}; }
      if (sql.includes("resolution_kind = 'abandoned_review'")) { const r=db.rows.get(v[1]); if (!r || r.state !== 'notifying' || r.resolution_kind != null || r.resolved_at != null) return {success:true,meta:{changes:0}}; r.state='rejected'; r.resolved_at=v[0]; r.resolution_kind='abandoned_review'; return {success:true,meta:{changes:1}}; }
      if (sql.includes("SET state = 'ready'")) { const r=db.rows.get(v[2]); if (!r || r.state !== 'notifying') return {meta:{changes:0}}; r.state='ready'; r.review_message_id=v[0]; r.photo_file_id=v[1]; return {meta:{changes:1}}; }
      if (sql.includes('SET state = ?')) { const r=db.rows.get(v[1]); if (!r || r.state !== 'ready' || r.review_message_id !== v[2]) return {meta:{changes:0}}; r.state=v[0]; return {meta:{changes:1}}; }
      if (sql.includes("SET state = 'sent'")) { const r=db.rows.get(v[1]); if (!r || r.state !== 'sending') return {meta:{changes:0}}; r.state='sent'; r.channel_message_id=v[0]; return {meta:{changes:1}}; }
      throw Error('unknown query');
    },
    async all() { if (sql.startsWith('SELECT source_url FROM drafts WHERE')) return {success:true,results:[...db.rows.values()].filter(r=>v.includes(r.source_url)).map(r=>({source_url:r.source_url}))}; throw Error('unknown query'); },
    async first() { const r=db.rows.get(v[0]); return sql.startsWith('SELECT state, created_at') ? r || null : r?.state === 'sending' ? r : null; }
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

test('status reveals only counts and unresolved IDs to the authorized private chat',async()=>{
 const x=setup(true); await x.add(); const id=[...x.db.rows.keys()][0]; await x.click(id);
 const status=async message=>handle(x.request('/telegram',{message},{'x-telegram-bot-api-secret-token':x.env.WEBHOOK_SECRET}),x.env,x.api);
 const base={text:'/status',from:{id:123},chat:{id:123,type:'private'}};
 const before=x.calls.length; await status({...base,from:{id:124}}); await status({...base,chat:{id:123,type:'group'}});
 assert.equal(x.calls.length,before);
 await status(base); const last=x.calls.at(-1); assert.equal(last.data.chat_id,'123');
 assert.match(last.data.text,/Публикуются или требуют сверки: 1/); assert(last.data.text.includes(id));
 assert(!last.data.text.includes('https://example.org/news')); assert(!last.data.text.includes('Склад: проверенный текст'));
 assert.equal(x.db.rows.get(id).state,'sending');
});
test('status reports unavailable storage without altering state or sending to channel',async()=>{
 const x=setup(); x.env.DB={prepare(){throw new Error('unavailable');}};
 const response=await handle(x.request('/telegram',{message:{text:'/status',from:{id:123},chat:{id:123,type:'private'}}},{'x-telegram-bot-api-secret-token':x.env.WEBHOOK_SECRET}),x.env,x.api);
 assert.equal(response.status,200); assert.match(x.calls.at(-1).data.text,/Не удалось прочитать журнал/);
 assert.equal(x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length,0);
});

test('inspect is read-only, private and displays bounded identifying information',async()=>{
 const x=setup(true); await x.add(); const id=[...x.db.rows.keys()][0]; await x.click(id);
 const inspect=async (msg,secret=x.env.WEBHOOK_SECRET)=>handle(x.request('/telegram',{message:msg},{'x-telegram-bot-api-secret-token':secret}),x.env,x.api);
 const base={text:`/inspect ${id}`,from:{id:123},chat:{id:123,type:'private'}};
 const before=x.calls.length; assert.equal((await inspect(base,'wrong')).status,403);
 await inspect({...base,from:{id:456}}); await inspect({...base,chat:{id:123,type:'group'}}); await inspect({...base,text:'/inspect invalid'});
 assert.equal(x.calls.length,before);
 await inspect(base); const reply=x.calls.at(-1); assert.equal(reply.data.chat_id,'123'); assert.equal(reply.data.disable_web_page_preview,true);
 assert.match(reply.data.text,/Состояние в журнале: sending/); assert.match(reply.data.text,/https:\/\/example.org\/news/);
 assert.equal(x.db.rows.get(id).state,'sending'); assert.equal(x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length,1);
});
test('manual reconciliation is restricted, explicit, one-way and never sends to channel',async()=>{
 const x=setup(true); await x.add(); const id=[...x.db.rows.keys()][0]; await x.click(id);
 assert.equal(x.db.rows.get(id).state,'sending');
 const command=async (message, secret=x.env.WEBHOOK_SECRET)=>handle(x.request('/telegram',{message},{'x-telegram-bot-api-secret-token':secret}),x.env,x.api);
 const base={text:`/reconcile ${id} published 54321 CONFIRM`,from:{id:123},chat:{id:123,type:'private'}};
 const channelCalls=()=>x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length;
 assert.equal(channelCalls(),1);
 assert.equal((await command(base,'bad')).status,403);
 await command({...base,from:{id:124}}); await command({...base,chat:{id:123,type:'group'}});
 await command({...base,text:`/reconcile ${id} published 54321`});
 await command({...base,text:`/reconcile ${id} published 9999999999999999 CONFIRM`});
 assert.equal(x.db.rows.get(id).state,'sending');
 await command(base); let row=x.db.rows.get(id);
 assert.equal(row.state,'sent'); assert.equal(row.channel_message_id,54321); assert.equal(row.resolution_kind,'confirmed_channel_message'); assert.match(row.resolved_at,/^\d{4}-/);
 await command({...base,text:`/reconcile ${id} published 12345 CONFIRM`});
 await x.click(id); assert.equal(row.channel_message_id,54321); assert.equal(channelCalls(),1);
});
test('only uncertain review can be discarded and URL remains blocked',async()=>{
 const x=setup(); await x.add(); const id=[...x.db.rows.keys()][0];
 const command=text=>handle(x.request('/telegram',{message:{text,from:{id:123},chat:{id:123,type:'private'}}},{'x-telegram-bot-api-secret-token':x.env.WEBHOOK_SECRET}),x.env,x.api);
 await command(`/reconcile ${id} discard-review CONFIRM`); assert.equal(x.db.rows.get(id).state,'ready');
 x.db.rows.get(id).state='notifying';
 await command(`/reconcile ${id} discard-review CONFIRM`);
 const row=x.db.rows.get(id); assert.equal(row.state,'rejected'); assert.equal(row.resolution_kind,'abandoned_review'); assert(row.resolved_at);
 await x.click(id); assert.equal(x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length,0);
 assert.equal((await x.add()).status,409);
});
test('reconciliation reports storage failure without claiming success',async()=>{
 const x=setup(); x.env.DB={prepare(){throw Error('missing migration')}};
 const msg={text:'/reconcile 11111111-1111-4111-8111-111111111111 discard-review CONFIRM',from:{id:123},chat:{id:123,type:'private'}};
 await handle(x.request('/telegram',{message:msg},{'x-telegram-bot-api-secret-token':x.env.WEBHOOK_SECRET}),x.env,x.api);
 assert.match(x.calls.at(-1).data.text,/Не удалось подтвердить/);
 assert.equal(x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length,0);
});

test('inspect handles unknown ID and storage failure without channel sends',async()=>{
 const x=setup(); const msg={text:'/inspect 11111111-1111-4111-8111-111111111111',from:{id:123},chat:{id:123,type:'private'}};
 const req=()=>x.request('/telegram',{message:msg},{'x-telegram-bot-api-secret-token':x.env.WEBHOOK_SECRET});
 await handle(req(),x.env,x.api); assert.match(x.calls.at(-1).data.text,/Запись не найдена/);
 x.env.DB={prepare(){throw Error('outage')}}; await handle(req(),x.env,x.api); assert.match(x.calls.at(-1).data.text,/Не удалось прочитать запись/);
 assert.equal(x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length,0);
});

test('owner can propose a draft privately without publishing; approval remains separate',async()=>{
 const x=setup(); const msg={text:'/draft https://example.org/new\nМой проверенный текст и вывод',from:{id:123},chat:{id:123,type:'private'}};
 const req=(m,secret=x.env.WEBHOOK_SECRET)=>x.request('/telegram',{message:m},{'x-telegram-bot-api-secret-token':secret});
 const before=x.calls.length; await handle(req({...msg,from:{id:124}}),x.env,x.api); await handle(req({...msg,chat:{id:123,type:'group'}}),x.env,x.api);
 assert.equal((await handle(req(msg,'wrong'),x.env,x.api)).status,403); assert.equal(x.calls.length,before); assert.equal(x.db.rows.size,0);
 assert.equal((await handle(req(msg),x.env,x.api)).status,200); assert.equal(x.db.rows.size,1);
 const id=[...x.db.rows.keys()][0]; assert.equal(x.db.rows.get(id).state,'ready');
 assert.match(x.calls.at(-1).data.text,/Мой проверенный текст/); assert.equal(x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length,0);
 await x.click(id); assert.equal(x.db.rows.get(id).state,'sent'); assert.equal(x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length,1);
});
test('draft command rejects bad content and duplicate requests without accidental sends',async()=>{
 const x=setup(); const send=text=>handle(x.request('/telegram',{message:{text,from:{id:123},chat:{id:123,type:'private'}}},{'x-telegram-bot-api-secret-token':x.env.WEBHOOK_SECRET}),x.env,x.api);
 await send('/draft'); assert.match(x.calls.at(-1).data.text,/Формат/); assert.equal(x.db.rows.size,0);
 await send('/draft javascript:alert(1)\nтекст'); assert.equal(x.db.rows.size,0);
 const command='/draft https://example.org/news\nпроверенный текст'; await send(command); await send(command);
 assert.equal(x.db.rows.size,1); assert.match(x.calls.at(-1).data.text,/не отправляйте повторно/);
 assert.equal(x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length,0);
});
test('owner can propose one photo with caption, and the reviewed photo is used on approval',async()=>{
 const x=setup(); const msg={caption:'/draft https://example.org/picture\nПроверенный текст',photo:[{file_id:'small'},{file_id:'original-photo'}],from:{id:123},chat:{id:123,type:'private'}};
 const send=(m,secret=x.env.WEBHOOK_SECRET)=>handle(x.request('/telegram',{message:m},{'x-telegram-bot-api-secret-token':secret}),x.env,x.api);
 await send({...msg,from:{id:999}}); assert.equal(x.db.rows.size,0);
 assert.equal((await send(msg,'bad')).status,403); assert.equal(x.db.rows.size,0);
 await send(msg); const id=[...x.db.rows.keys()][0]; assert.equal(x.db.rows.get(id).state,'ready');
 const review=x.calls.find(c=>c.method==='sendPhoto'); assert.equal(review.data.photo,'original-photo'); assert.match(review.data.caption,/Проверенный текст/);
 assert.equal(x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length,0);
 await x.click(id); const delivered=x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID);
 assert.equal(delivered.length,1); assert.equal(delivered[0].method,'sendPhoto'); assert.equal(delivered[0].data.photo,'photo-token'); assert.equal(x.db.rows.get(id).state,'sent');
});
test('photo albums, invalid photo ID and overly long captions cannot enter the queue',async()=>{
 const x=setup(); const base={caption:'/draft https://example.org/picture\nТекст',photo:[{file_id:'photo'}],from:{id:123},chat:{id:123,type:'private'}};
 const send=msg=>handle(x.request('/telegram',{message:msg},{'x-telegram-bot-api-secret-token':x.env.WEBHOOK_SECRET}),x.env,x.api);
 await send({...base,media_group_id:'album'}); await send({...base,photo:[{file_id:''}]}); await send({...base,caption:'/draft https://example.org/picture\n'+'x'.repeat(1000)});
 assert.equal(x.db.rows.size,0); assert.equal(x.calls.filter(c=>c.method==='sendPhoto').length,0); assert.equal(x.calls.filter(c=>c.data.chat_id===x.env.CHANNEL_ID).length,0);
});

test('availability is authenticated, read-only and reports known sources and pending work',async()=>{
 const x=setup(); await x.add(); const check=(data,secret=x.env.INTAKE_SECRET)=>handle(x.request('/availability',data,{authorization:'Bearer '+secret}),x.env,x.api);
 assert.equal((await check({source_urls:['https://example.org/news']},'bad')).status,403);
 for(const v of [[],['javascript:alert(1)'],Array(21).fill('https://example.org/news')]) assert.equal((await check({source_urls:v})).status,400);
 const before=x.calls.length; const res=await check({source_urls:['https://example.org/news','https://example.org/new']});
 assert.equal(res.status,200); assert.deepEqual(await res.json(),{known:[true,false],pending:1,uncertain:0}); assert.equal(x.calls.length,before); assert.equal(x.db.rows.size,1);
 const id=[...x.db.rows.keys()][0]; await x.click(id,'reject'); assert.deepEqual(await (await check({source_urls:['https://example.org/news']})).json(),{known:[true],pending:0,uncertain:0});
});
test('availability fails closed on storage errors and exposes no journal content',async()=>{
 const x=setup(); x.env.DB={prepare(){throw Error('storage');}}; const res=await handle(x.request('/availability',{source_urls:['https://example.org/news']},{authorization:'Bearer '+x.env.INTAKE_SECRET}),x.env,x.api);
 assert.equal(res.status,503); assert.equal(await res.text(),'Storage unavailable'); assert.equal(x.calls.length,0);
});
