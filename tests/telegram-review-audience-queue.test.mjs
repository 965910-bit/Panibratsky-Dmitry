import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtempSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {startAudienceCampaign,enqueueAudienceRecipient,deliverAudienceRecipient,enqueueSubscriberPage} from '../telegram-review/audience-queue.mjs';
import {createAudienceTransport} from '../telegram-review/audience-transport.mjs';
const draft='00000000-0000-4000-8000-000000000001',old='2020-01-01T00:00:00.000Z',future='2099-01-01T00:00:00.000Z';
const bridge=`import json,sqlite3,sys
p=json.load(sys.stdin); c=sqlite3.connect(p['path']);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
if p['mode']=='init':
 for f in ['telegram-review/schema.sql','telegram-review/migrations/003-audience.sql','telegram-review/migrations/004-audience-order.sql','telegram-review/migrations/005-audience-campaigns.sql']: c.executescript(open(f).read())
 print('{}')
else:
 cur=c.execute(p['sql'],p['args']);rows=[dict(r) for r in cur.fetchall()] if cur.description else [];c.commit();print(json.dumps({'success':True,'meta':{'changes':cur.rowcount},'rows':rows}))
c.close()`;
function fixture(t){
 const dir=mkdtempSync(join(tmpdir(),'audience-queue-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));const path=join(dir,'db');
 const exec=(mode,sql='',args=[])=>{const p=spawnSync('python3',['-c',bridge],{input:JSON.stringify({path,mode,sql,args}),encoding:'utf8'});if(p.status!==0)throw Error(p.stderr);return JSON.parse(p.stdout)};exec('init');
 const DB={prepare(sql){return {bind(...args){return {run:async()=>exec('run',sql,args),first:async()=>exec('run',sql,args).rows[0]??null,all:async()=>{const r=exec('run',sql,args);return {success:true,results:r.rows}}}}}}};
 const sql=(s,a=[])=>exec('run',s,a);sql('INSERT INTO drafts(id,source_url,text,state,created_at,channel_message_id,photo_file_id) VALUES(?,?,?,?,?,?,?)',[draft,'https://example.org/news','Текст','sent',old,42,'photo-id']);
 return {DB,sql};
}
test('approved campaign targets only existing consent and enabled configured destinations; no later backfill',async t=>{
 const {DB,sql}=fixture(t);sql("INSERT INTO audience_subscribers(chat_id,subscribed_at,updated_at,active) VALUES('10',?,?,1)",[old,old]);sql("INSERT INTO audience_subscribers(chat_id,subscribed_at,updated_at,active) VALUES('11',?,?,0)",[old,old]);sql("INSERT INTO audience_destinations(chat_id,kind,enabled,created_at) VALUES('-100','group',1,?)",[old]);sql("INSERT INTO audience_destinations(chat_id,kind,enabled,created_at) VALUES('-101','channel',0,?)",[old]);
 assert.equal(await startAudienceCampaign(DB,draft),true);assert.equal(await startAudienceCampaign(DB,draft),false);
 assert.equal(await enqueueAudienceRecipient(DB,draft,'subscriber','10'),true);assert.equal(await enqueueAudienceRecipient(DB,draft,'subscriber','10'),false);
 assert.equal(await enqueueAudienceRecipient(DB,draft,'subscriber','11'),false);assert.equal(await enqueueAudienceRecipient(DB,draft,'destination','-100'),true);assert.equal(await enqueueAudienceRecipient(DB,draft,'destination','-101'),false);
 sql("INSERT INTO audience_subscribers(chat_id,subscribed_at,updated_at,active) VALUES('12',?,?,1)",[future,future]);assert.equal(await enqueueAudienceRecipient(DB,draft,'subscriber','12'),false);
 const rows=sql('SELECT * FROM audience_deliveries').rows;assert.equal(rows.length,2);
});
test('only sent drafts can start a campaign, invalid identifiers rejected',async t=>{
 const {DB,sql}=fixture(t);sql("UPDATE drafts SET state='ready' WHERE id=?",[draft]);assert.equal(await startAudienceCampaign(DB,draft),false);
 await assert.rejects(()=>enqueueAudienceRecipient(DB,draft,'destination','10'));await assert.rejects(()=>startAudienceCampaign(DB,'not-id'));
});
test('one atomic claim for concurrent send, same approved photo and text, no duplicate delivery',async t=>{
 const {DB,sql}=fixture(t);sql("INSERT INTO audience_subscribers VALUES('10',?,?,1,-1)",[old,old]);await startAudienceCampaign(DB,draft);await enqueueAudienceRecipient(DB,draft,'subscriber','10');
 const calls=[],send=async payload=>{calls.push(payload);return {message_id:7}};
 const results=await Promise.all([deliverAudienceRecipient(DB,draft,'subscriber','10',send),deliverAudienceRecipient(DB,draft,'subscriber','10',send)]);
 assert.deepEqual(results.map(x=>x.status).sort(),['not-claimed','sent']);assert.equal(calls.length,1);assert.equal(calls[0].photoFileId,'photo-id');assert.match(calls[0].text,/Источник: https:\/\/example.org\/news/);
 const row=sql('SELECT state,message_id FROM audience_deliveries').rows[0];assert.equal(row.state,'sent');assert.equal(row.message_id,7);
});
test('unsubscribed, resubscribed after boundary or disabled destination is not sent',async t=>{
 const {DB,sql}=fixture(t);sql("INSERT INTO audience_subscribers VALUES('10',?,?,1,-1)",[old,old]);sql("INSERT INTO audience_destinations VALUES('-100','channel',1,?)",[old]);await startAudienceCampaign(DB,draft);await enqueueAudienceRecipient(DB,draft,'subscriber','10');await enqueueAudienceRecipient(DB,draft,'destination','-100');
 const send=()=>{throw Error('must not send')};sql("UPDATE audience_subscribers SET active=0 WHERE chat_id='10'");assert.equal((await deliverAudienceRecipient(DB,draft,'subscriber','10',send)).status,'not-claimed');
 sql("UPDATE audience_subscribers SET active=1,subscribed_at=? WHERE chat_id='10'",[future]);assert.equal((await deliverAudienceRecipient(DB,draft,'subscriber','10',send)).status,'not-claimed');
 sql("UPDATE audience_destinations SET enabled=0 WHERE chat_id='-100'");assert.equal((await deliverAudienceRecipient(DB,draft,'destination','-100',send)).status,'not-claimed');
});
test('uncertain transport is never automatically retried',async t=>{
 const {DB,sql}=fixture(t);sql("INSERT INTO audience_subscribers VALUES('10',?,?,1,-1)",[old,old]);await startAudienceCampaign(DB,draft);await enqueueAudienceRecipient(DB,draft,'subscriber','10');let calls=0;
 const send=async()=>{calls++;throw Error('timeout after possible delivery')};assert.equal((await deliverAudienceRecipient(DB,draft,'subscriber','10',send)).status,'uncertain');assert.equal((await deliverAudienceRecipient(DB,draft,'subscriber','10',send)).status,'not-claimed');assert.equal(calls,1);assert.equal(sql('SELECT state FROM audience_deliveries').rows[0].state,'uncertain');
});

test('storage failure after transport does not trigger a second send',async t=>{
 const {DB,sql}=fixture(t);sql("INSERT INTO audience_subscribers VALUES('10',?,?,1,-1)",[old,old]);await startAudienceCampaign(DB,draft);await enqueueAudienceRecipient(DB,draft,'subscriber','10');let calls=0;
 const failing={prepare(query){if(query.includes("SET state='sent'"))throw Error('storage outage');return DB.prepare(query)}};
 const result=await deliverAudienceRecipient(failing,draft,'subscriber','10',async()=>{calls++;return {message_id:8}});
 assert.equal(result.status,'uncertain');assert.equal((await deliverAudienceRecipient(DB,draft,'subscriber','10',async()=>{calls++;return {message_id:9}})).status,'not-claimed');assert.equal(calls,1);
});

test('queue and transport send one approved photo and journal a confirmed mock reply',async t=>{
 const {DB,sql}=fixture(t);sql("INSERT INTO audience_subscribers VALUES('10',?,?,1,-1)",[old,old]);await startAudienceCampaign(DB,draft);await enqueueAudienceRecipient(DB,draft,'subscriber','10');
 const calls=[];const send=createAudienceTransport('123456:'+ 'a'.repeat(32),async(url,init)=>{calls.push({url,body:JSON.parse(init.body)});return Response.json({ok:true,result:{message_id:55}})});
 assert.equal((await deliverAudienceRecipient(DB,draft,'subscriber','10',send)).status,'sent');assert.equal(calls.length,1);assert.match(calls[0].url,/\/sendPhoto$/);assert.equal(calls[0].body.chat_id,'10');assert.equal(calls[0].body.photo,'photo-id');assert.equal(sql('SELECT message_id FROM audience_deliveries').rows[0].message_id,55);
});
test('queue and transport stop on mocked Telegram 429 without retry',async t=>{
 const {DB,sql}=fixture(t);sql("INSERT INTO audience_subscribers VALUES('10',?,?,1,-1)",[old,old]);await startAudienceCampaign(DB,draft);await enqueueAudienceRecipient(DB,draft,'subscriber','10');let calls=0;
 const send=createAudienceTransport('123456:'+ 'a'.repeat(32),async()=>{calls++;return new Response('',{status:429})});
 assert.equal((await deliverAudienceRecipient(DB,draft,'subscriber','10',send)).status,'uncertain');assert.equal((await deliverAudienceRecipient(DB,draft,'subscriber','10',send)).status,'not-claimed');assert.equal(calls,1);
});

test('bounded subscriber pages are idempotent, ordered, and exclude inactive or later subscribers',async t=>{
 const {DB,sql}=fixture(t);
 for(const id of ['1','2','10','30','40']) sql('INSERT INTO audience_subscribers VALUES(?,?,?,1,-1)',[id,old,old]);
 sql("INSERT INTO audience_subscribers VALUES('50',?,?,0,-1)",[old,old]);
 await startAudienceCampaign(DB,draft);
 const boundary=sql('SELECT created_at FROM audience_campaigns').rows[0].created_at;
 sql("INSERT INTO audience_subscribers VALUES('60',?,?,1,-1)",[boundary,boundary]);
 const a=await enqueueSubscriberPage(DB,draft,'',2);assert.deepEqual(a,{queued:2,nextCursor:'10'});
 assert.deepEqual(await enqueueSubscriberPage(DB,draft,'',2),{queued:0,nextCursor:'10'});
 const b=await enqueueSubscriberPage(DB,draft,a.nextCursor,2);assert.deepEqual(b,{queued:2,nextCursor:'30'});
 assert.deepEqual(await enqueueSubscriberPage(DB,draft,b.nextCursor,2),{queued:1,nextCursor:null});
 assert.deepEqual(sql('SELECT recipient_id FROM audience_deliveries ORDER BY recipient_id').rows.map(x=>x.recipient_id),['1','10','2','30','40']);
 assert.equal(await enqueueAudienceRecipient(DB,draft,'subscriber','60'),false);
 await assert.rejects(()=>enqueueSubscriberPage(DB,draft,'',21));await assert.rejects(()=>enqueueSubscriberPage(DB,draft,'1 OR 1=1'));
});
test('same-millisecond resubscription cannot receive an old pending campaign',async t=>{
 const {DB,sql}=fixture(t);sql("INSERT INTO audience_subscribers VALUES('10',?,?,1,-1)",[old,old]);await startAudienceCampaign(DB,draft);await enqueueAudienceRecipient(DB,draft,'subscriber','10');
 const boundary=sql('SELECT created_at FROM audience_campaigns').rows[0].created_at;
 sql("UPDATE audience_subscribers SET subscribed_at=? WHERE chat_id='10'",[boundary]);
 const result=await deliverAudienceRecipient(DB,draft,'subscriber','10',async()=>{throw Error('should not send')});assert.equal(result.status,'not-claimed');
});
test('storage page failure does not queue or leak recipient data',async t=>{
 const {DB,sql}=fixture(t);await startAudienceCampaign(DB,draft);
 const broken={prepare(){return {bind(){return {all:async()=>({success:false,results:[]})}}}}};
 await assert.rejects(()=>enqueueSubscriberPage(broken,draft));assert.equal(sql('SELECT * FROM audience_deliveries').rows.length,0);
});
