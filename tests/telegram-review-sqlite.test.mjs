// End-to-end local harness: real SQLite schema and SQL, stubbed Telegram HTTP.
// This does not test Cloudflare D1 or Telegram delivery.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {handle} from '../telegram-review/worker.mjs';
import {prepareDraft, submit, draftFingerprint} from '../telegram-review/drafts.mjs';

const bridge = `
import json, sqlite3, sys
p = json.load(sys.stdin)
try:
  con = sqlite3.connect(p['database'])
  con.row_factory = sqlite3.Row
  if p['mode'] == 'init':
    con.executescript(open('telegram-review/schema.sql', encoding='utf-8').read())
    out = {'success': True}
  else:
    cur = con.execute(p['sql'], p['args'])
    if p['mode'] == 'run':
      con.commit()
      out = {'success': True, 'meta': {'changes': cur.rowcount}}
    elif p['mode'] == 'all':
      out = {'success': True, 'results': [dict(row) for row in cur.fetchall()]}
    else:
      row = cur.fetchone()
      out = dict(row) if row else None
  con.close()
  print(json.dumps(out))
except Exception as exc:
  print(str(exc), file=sys.stderr)
  sys.exit(1)
`;
function sqliteAdapter(database) {
  function execute(mode, sql = '', args = []) {
    const proc = spawnSync('python3', ['-c', bridge], {input:JSON.stringify({database, mode, sql, args}), encoding:'utf8'});
    if (proc.status !== 0) throw Error(`SQLite adapter error: ${proc.stderr}`);
    return JSON.parse(proc.stdout);
  }
  execute('init');
  return {prepare(sql) { return {all:async()=>execute('all',sql), bind(...args) { return {
    run:async()=>execute('run',sql,args), first:async()=>execute('first',sql,args), all:async()=>execute('all',sql,args)
  }; }}; }};
}
function fixture(t, {failChannel=false} = {}) {
  const dir=mkdtempSync(join(tmpdir(),'telegram-review-sqlite-')); t.after(()=>rmSync(dir,{recursive:true,force:true}));
  const DB=sqliteAdapter(join(dir,'queue.db'));
  const env={DB,REVIEWER_ID:'123',CHANNEL_ID:'-100123',BOT_TOKEN:'123456:'+ 'a'.repeat(32),WEBHOOK_SECRET:'w'.repeat(40),INTAKE_SECRET:'i'.repeat(40)};
  const calls=[];
  const telegram=async (url,init)=>{
    const method=url.split('/').at(-1), body=init.body instanceof FormData ? Object.fromEntries(init.body.entries()) : JSON.parse(init.body);
    calls.push({method,body});
    if (failChannel && body.chat_id===env.CHANNEL_ID && ['sendPhoto','sendMessage'].includes(method)) throw Error('simulated network timeout');
    return new Response(JSON.stringify({ok:true,result:{message_id:body.chat_id===env.REVIEWER_ID ? 37:48,photo:[{file_id:'telegram-photo-id'}]}}),{status:200});
  };
  const localIntake=(url,init)=>handle(new Request(url,init),env,telegram);
  const webhook=payload=>handle(new Request('https://worker.example/telegram',{method:'POST',headers:{'content-type':'application/json','x-telegram-bot-api-secret-token':env.WEBHOOK_SECRET},body:JSON.stringify(payload)}),env,telegram);
  const command=(text)=>webhook({message:{text,from:{id:123},chat:{id:123,type:'private'}}});
  const approve=id=>webhook({callback_query:{id:'callback',from:{id:123},message:{message_id:37,chat:{id:123,type:'private'}},data:`approve:${id}`}});
  const getRow=()=>DB.prepare('SELECT * FROM drafts').all();
  return {env,calls,localIntake,command,approve,getRow};
}
const png = d => { const x=Buffer.alloc(33); Buffer.from([137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82]).copy(x); x.writeUInt32BE(1080,16); x.writeUInt32BE(1080,20); const info=Buffer.from('SCM-Draft-SHA256\0'+draftFingerprint(d)); const chunk=Buffer.alloc(info.length+12); chunk.writeUInt32BE(info.length); chunk.write('tEXt',4); info.copy(chunk,8); const end=Buffer.alloc(12); end.write('IEND',4); return Buffer.concat([x,chunk,end]); };
const draft = () => ({...prepareDraft({title:'Склад и логистика',description:'Описание',source:'Пример',link:'https://example.org/news'}),ready_for_review:true,comment:'Проверенный вывод.'});
const options = f => ({url:'https://test.example.workers.dev/intake',secret:f.env.INTAKE_SECRET,fetcher:f.localIntake,card:png(draft())});

test('manual submit → private review → approval → SQLite journal; no implicit publication',async(t)=>{
  const f=fixture(t); await submit(draft(),options(f));
  const row=(await f.getRow()).results[0]; assert.equal(row.state,'ready'); assert.equal(row.photo_file_id,'telegram-photo-id');
  assert.equal(f.calls.filter(c=>c.body.chat_id===f.env.CHANNEL_ID).length,0);
  await Promise.all([f.approve(row.id),f.approve(row.id)]);
  const after=(await f.getRow()).results[0]; assert.equal(after.state,'sent'); assert.equal(after.channel_message_id,48);
  const channel=f.calls.filter(c=>c.body.chat_id===f.env.CHANNEL_ID); assert.equal(channel.length,1); assert.equal(channel[0].method,'sendPhoto'); assert.equal(channel[0].body.photo,'telegram-photo-id');
  await f.command('/status'); assert.match(f.calls.at(-1).body.text,/Отправлено по журналу: 1/);
  await f.command(`/inspect ${row.id}`); assert.match(f.calls.at(-1).body.text,/Состояние в журнале: sent/);
  await assert.rejects(()=>submit(draft(),options(f)),/409/);
});
test('uncertain channel outcome persists in SQLite and cannot be resent with another click',async(t)=>{
  const f=fixture(t,{failChannel:true}); await submit(draft(),options(f)); const id=(await f.getRow()).results[0].id;
  await f.approve(id); await f.approve(id); assert.equal((await f.getRow()).results[0].state,'sending');
  assert.equal(f.calls.filter(c=>c.body.chat_id===f.env.CHANNEL_ID).length,1);
  await f.command('/status'); assert.match(f.calls.at(-1).body.text,/Публикуются или требуют сверки: 1/); assert(f.calls.at(-1).body.text.includes(id));
});
test('private draft command uses the real journal and still requires explicit approval',async(t)=>{
  const f=fixture(t); await f.command('/draft https://example.org/mobile\nПроверенный текст с телефона');
  const row=(await f.getRow()).results[0]; assert.equal(row.state,'ready'); assert.equal(row.text,'Проверенный текст с телефона');
  assert.equal(f.calls.filter(c=>c.body.chat_id===f.env.CHANNEL_ID).length,0);
  await f.command('/draft https://example.org/mobile\nПовтор'); assert.equal((await f.getRow()).results.length,1);
  await f.approve(row.id); assert.equal((await f.getRow()).results[0].state,'sent');
  const channel=f.calls.filter(c=>c.body.chat_id===f.env.CHANNEL_ID); assert.equal(channel.length,1); assert.equal(channel[0].method,'sendMessage');
});
