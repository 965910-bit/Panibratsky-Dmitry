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
});
