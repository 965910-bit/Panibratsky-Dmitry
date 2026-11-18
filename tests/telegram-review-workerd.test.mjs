// Optional local runtime check. Telegram is intercepted inside the worker; no network sends.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

let Miniflare;
try { ({Miniflare} = await import('miniflare')); } catch (error) {
  if (error?.code !== 'ERR_MODULE_NOT_FOUND') throw error;
}

test('workerd runtime and D1 binding with fully simulated Telegram', {skip:!Miniflare && 'Optional miniflare package is not installed'}, async(t)=>{
  const source = await readFile('telegram-review/worker.mjs','utf8');
  const original = 'export default {fetch(request, env) { return handle(request, env); }};';
  assert(source.includes(original));
  // Replace only the entry point for the test: every Telegram call is intercepted.
  const script = source.replace(original, `
const fakeTelegram = async (url, init) => {
  const method = new URL(url).pathname.split('/').at(-1);
  if (!['sendMessage','sendPhoto','answerCallbackQuery'].includes(method)) throw Error('unexpected call');
  const data = typeof init.body === 'string' ? JSON.parse(init.body) : Object.fromEntries((await new Request('http://test', {method:'POST',body:init.body}).formData()).entries());
  await envForTest.DB.prepare('INSERT INTO calls (method, chat_id) VALUES (?, ?)').bind(method, String(data.chat_id || '')).run();
  return Response.json({ok:true,result:{message_id:String(data.chat_id)==='123' ? 37:48,photo:[{file_id:'test-photo'}]}});
};
let envForTest;
export default {fetch(request, env) { envForTest=env; return handle(request, env, fakeTelegram); }};
`);
  const mf = new Miniflare({modules:true,script,compatibilityDate:'2026-07-01',d1Databases:['DB'],bindings:{REVIEWER_ID:'123',CHANNEL_ID:'-100123',BOT_TOKEN:'123456:'+ 'a'.repeat(32),WEBHOOK_SECRET:'w'.repeat(40),INTAKE_SECRET:'i'.repeat(40)}});
  t.after(()=>mf.dispose());
  const db=await mf.getD1Database('DB');
  const schema=await readFile('telegram-review/schema.sql','utf8');
  await db.prepare(schema.replace(/^--.*$/gm,'').trim()).run();
  await db.exec('CREATE TABLE calls (method TEXT, chat_id TEXT);');
  const headers={'content-type':'application/json','authorization':'Bearer '+ 'i'.repeat(40)};
  const res=await mf.dispatchFetch('http://worker.test/intake',{method:'POST',headers,body:JSON.stringify({text:'Тестовый черновик',source_url:'https://example.org/workerd'})});
  assert.equal(res.status,201);
  const row=await db.prepare('SELECT * FROM drafts').first(); assert.equal(row.state,'ready');
  assert.equal((await db.prepare("SELECT COUNT(*) AS n FROM calls WHERE chat_id = '-100123'").first()).n,0);
  const payload={callback_query:{id:'test',from:{id:123},message:{message_id:37,chat:{id:123,type:'private'}},data:`approve:${row.id}`}};
  const send=()=>mf.dispatchFetch('http://worker.test/telegram',{method:'POST',headers:{'content-type':'application/json','x-telegram-bot-api-secret-token':'w'.repeat(40)},body:JSON.stringify(payload)});
  assert.equal((await send()).status,200); assert.equal((await send()).status,200);
  assert.equal((await db.prepare('SELECT state FROM drafts WHERE id = ?').bind(row.id).first()).state,'sent');
  assert.equal((await db.prepare("SELECT COUNT(*) AS n FROM calls WHERE chat_id = '-100123'").first()).n,1);
  const png=Buffer.alloc(33); Buffer.from([137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82]).copy(png); png.writeUInt32BE(1080,16); png.writeUInt32BE(1080,20);
  const photo=await mf.dispatchFetch('http://worker.test/intake',{method:'POST',headers,body:JSON.stringify({text:'Фото черновик',source_url:'https://example.org/card',card_base64:png.toString('base64')})});
  assert.equal(photo.status,201);
  const card=await db.prepare('SELECT * FROM drafts WHERE source_url = ?').bind('https://example.org/card').first();
  assert.equal(card.state,'ready'); assert.equal(card.photo_file_id,'test-photo');
  const cardPayload={callback_query:{id:'photo',from:{id:123},message:{message_id:37,chat:{id:123,type:'private'}},data:`approve:${card.id}`}};
  const approved=await mf.dispatchFetch('http://worker.test/telegram',{method:'POST',headers:{'content-type':'application/json','x-telegram-bot-api-secret-token':'w'.repeat(40)},body:JSON.stringify(cardPayload)});
  assert.equal(approved.status,200); assert.equal((await db.prepare('SELECT state FROM drafts WHERE id = ?').bind(card.id).first()).state,'sent');
  assert.equal((await db.prepare("SELECT COUNT(*) AS n FROM calls WHERE chat_id = '-100123' AND method = 'sendPhoto'").first()).n,1);

  // No real Telegram access: exercise the guarded producer protocol in workerd + local D1.
  const sources=['https://example.org/guard-a','https://example.org/guard-b'];
  const preflight=(auth=headers)=>mf.dispatchFetch('http://worker.test/availability',{method:'POST',headers:auth,body:JSON.stringify({source_urls:sources})});
  assert.equal((await preflight({...headers,authorization:'Bearer wrong'})).status,403);
  let state=await (await preflight()).json();
  assert.deepEqual(state,{known:[false,false],pending:0,uncertain:0});
  const guarded=url=>mf.dispatchFetch('http://worker.test/intake-one',{method:'POST',headers,body:JSON.stringify({text:'Проверенный вывод',source_url:url,card_base64:png.toString('base64')})});
  assert.equal((await guarded(sources[0].replace('guard-a','original-check'))).status,201);
  // Once the record is ready, a different source must not enter or notify.
  assert.equal((await guarded(sources[0])).status,409);
  state=await (await preflight()).json(); assert.equal(state.pending,1);
  const originalRow=await db.prepare('SELECT * FROM drafts WHERE source_url = ?').bind('https://example.org/original-check').first();
  const rejectPayload={callback_query:{id:'reject',from:{id:123},message:{message_id:37,chat:{id:123,type:'private'}},data:`reject:${originalRow.id}`}};
  assert.equal((await mf.dispatchFetch('http://worker.test/telegram',{method:'POST',headers:{'content-type':'application/json','x-telegram-bot-api-secret-token':'w'.repeat(40)},body:JSON.stringify(rejectPayload)})).status,200);
  const results=await Promise.all(sources.map(guarded));
  assert.deepEqual(results.map(r=>r.status).sort((a,b)=>a-b),[201,409]);
  const rows=(await db.prepare("SELECT source_url, state FROM drafts WHERE source_url IN (?, ?)").bind(...sources).all()).results;
  assert.equal(rows.length,1);assert.equal(rows[0].state,'ready');
  const manual=await mf.dispatchFetch('http://worker.test/intake',{method:'POST',headers,body:JSON.stringify({text:'Ручной черновик',source_url:'https://example.org/manual-blocked'})});
  assert.equal(manual.status,409);
  const phone={message:{text:'/draft https://example.org/phone-blocked\nПроверенный текст',from:{id:123},chat:{id:123,type:'private'}}};
  assert.equal((await mf.dispatchFetch('http://worker.test/telegram',{method:'POST',headers:{'content-type':'application/json','x-telegram-bot-api-secret-token':'w'.repeat(40)},body:JSON.stringify(phone)})).status,200);
  assert.equal((await db.prepare("SELECT COUNT(*) AS n FROM drafts WHERE source_url IN ('https://example.org/manual-blocked','https://example.org/phone-blocked')").first()).n,0);
  for (const status of ['notifying','sending']) {
    await db.prepare('UPDATE drafts SET state = ? WHERE source_url = ?').bind(status,rows[0].source_url).run();
    assert.equal((await guarded('https://example.org/blocked-'+status)).status,409);
    const snapshot=await (await preflight()).json();assert.equal(snapshot.uncertain,1);
  }
  await db.prepare("UPDATE drafts SET state = 'ready' WHERE source_url = ?").bind(rows[0].source_url).run();
  state=await (await preflight()).json();assert.deepEqual(state.known,sources.map(url=>url===rows[0].source_url));assert.equal(state.pending,1);assert.equal(state.uncertain,0);
  assert.equal((await db.prepare("SELECT COUNT(*) AS n FROM calls WHERE chat_id = '-100123'").first()).n,2);
});

test('workerd: rejection, unauthorized callbacks and ambiguous Telegram outcomes stop safely', {skip:!Miniflare && 'Optional miniflare package is not installed'}, async(t)=>{
  const source=await readFile('telegram-review/worker.mjs','utf8');
  const entry='export default {fetch(request, env) { return handle(request, env); }};';
  assert(source.includes(entry));
  // Every Telegram request is intercepted; the failure happens after recording an
  // attempted send, modelling an outcome where delivery might have succeeded.
  const script=source.replace(entry, `
let testEnv;
async function fakeTelegram(url, init) {
  const method = new URL(url).pathname.split('/').at(-1);
  if (method !== 'sendMessage' && method !== 'answerCallbackQuery') throw Error('unexpected call');
  const data = JSON.parse(init.body);
  const chat = String(data.chat_id || '');
  await testEnv.DB.prepare('INSERT INTO calls (method, chat_id) VALUES (?, ?)').bind(method, chat).run();
  if (method === 'sendMessage' && ((chat === '123' && data.text.includes('LOSS_REVIEW')) || (chat === '-100123' && data.text.includes('LOSS_CHANNEL')))) throw Error('simulated lost response');
  return Response.json({ok:true,result:{message_id:chat === '123' ? 37 : 48}});
}
export default {fetch(request, env) {testEnv=env; return handle(request, env, fakeTelegram);}};
`);
  const mf=new Miniflare({modules:true,script,compatibilityDate:'2026-07-01',d1Databases:['DB'],bindings:{REVIEWER_ID:'123',CHANNEL_ID:'-100123',BOT_TOKEN:'123456:'+'a'.repeat(32),WEBHOOK_SECRET:'w'.repeat(40),INTAKE_SECRET:'i'.repeat(40)}});
  t.after(()=>mf.dispose());
  const db=await mf.getD1Database('DB');
  await db.prepare((await readFile('telegram-review/schema.sql','utf8')).replace(/^--.*$/gm,'').trim()).run();
  await db.exec('CREATE TABLE calls (method TEXT, chat_id TEXT);');
  const intakeHeaders={'content-type':'application/json',authorization:'Bearer '+'i'.repeat(40)};
  const telegramHeaders={'content-type':'application/json','x-telegram-bot-api-secret-token':'w'.repeat(40)};
  const dispatch=(path,headers,payload)=>mf.dispatchFetch('http://worker.test/'+path,{method:'POST',headers,body:JSON.stringify(payload)});
  const intake=(text,url)=>dispatch('intake-one',intakeHeaders,{text,source_url:'https://example.invalid/'+url});
  const row=async url=>db.prepare('SELECT * FROM drafts WHERE source_url = ?').bind('https://example.invalid/'+url).first();
  const channelCalls=async()=> (await db.prepare("SELECT COUNT(*) AS n FROM calls WHERE chat_id = '-100123'").first()).n;
  const callback=(id,action,from=123,messageId=37)=>({callback_query:{id:'callback',from:{id:from},message:{message_id:messageId,chat:{id:123,type:'private'}},data:action+':'+id}});
  const command=text=>({message:{text,from:{id:123},chat:{id:123,type:'private'}}});

  assert.equal((await intake('Test rejection','reject')).status,201);
  const rejected=await row('reject');
  assert.equal(await channelCalls(),0);
  assert.equal((await dispatch('telegram',{'content-type':'application/json'},callback(rejected.id,'approve'))).status,403);
  await dispatch('telegram',telegramHeaders,callback(rejected.id,'approve',999));
  await dispatch('telegram',telegramHeaders,callback(rejected.id,'approve',123,999));
  assert.equal((await row('reject')).state,'ready');assert.equal(await channelCalls(),0);
  await dispatch('telegram',telegramHeaders,callback(rejected.id,'reject'));
  await dispatch('telegram',telegramHeaders,callback(rejected.id,'approve'));
  assert.equal((await row('reject')).state,'rejected');assert.equal(await channelCalls(),0);

  assert.equal((await intake('LOSS_CHANNEL','ambiguous-channel')).status,201);
  const ambiguous=await row('ambiguous-channel');
  await dispatch('telegram',telegramHeaders,callback(ambiguous.id,'approve'));
  assert.equal((await row('ambiguous-channel')).state,'sending');assert.equal(await channelCalls(),1);
  await dispatch('telegram',telegramHeaders,callback(ambiguous.id,'approve'));
  assert.equal((await intake('Blocked','blocked-channel')).status,409);assert.equal(await channelCalls(),1);
  // A human would first independently verify the channel; this is only a simulation.
  await dispatch('telegram',telegramHeaders,command(`/reconcile ${ambiguous.id} published 48 CONFIRM`));
  assert.equal((await row('ambiguous-channel')).state,'sent');assert.equal(await channelCalls(),1);

  assert.equal((await intake('LOSS_REVIEW','ambiguous-review')).status,503);
  const uncertain=await row('ambiguous-review');assert.equal(uncertain.state,'notifying');
  assert.equal((await intake('Blocked','blocked-review')).status,409);
  await dispatch('telegram',telegramHeaders,command(`/reconcile ${uncertain.id} discard-review CONFIRM`));
  assert.equal((await row('ambiguous-review')).state,'rejected');
  assert.equal((await intake('Duplicate','ambiguous-review')).status,409);
  assert.equal(await channelCalls(),1);
});
