import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtempSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {handle} from '../telegram-review/worker.mjs';
const bridge=`import json,sqlite3,sys
p=json.load(sys.stdin); c=sqlite3.connect(p['path']);c.row_factory=sqlite3.Row
if p['mode']=='init':
 for f in ['telegram-review/schema.sql','telegram-review/migrations/003-audience.sql','telegram-review/migrations/004-audience-order.sql']: c.executescript(open(f).read())
 print('{}')
else:
 cur=c.execute(p['sql'],p['args']);c.commit();print(json.dumps({'success':True,'meta':{'changes':cur.rowcount},'rows':[dict(r) for r in cur.fetchall()]}))
c.close()`;
function fixture(t, enabled=true) {
 const dir=mkdtempSync(join(tmpdir(),'audience-test-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));const file=join(dir,'db');
 function exec(mode,sql='',args=[]) {const p=spawnSync('python3',['-c',bridge],{input:JSON.stringify({path:file,mode,sql,args}),encoding:'utf8'});if(p.status!==0)throw Error(p.stderr);return JSON.parse(p.stdout);}
 exec('init'); const DB={prepare(sql){return {bind(...args){return {run:async()=>exec('query',sql,args)}}}}};
 const env={DB,REVIEWER_ID:'123',CHANNEL_ID:'-100123',BOT_TOKEN:'123456:'+ 'a'.repeat(32),WEBHOOK_SECRET:'w'.repeat(40),INTAKE_SECRET:'i'.repeat(40),AUDIENCE_ENABLED:enabled?'true':'false'};
 const calls=[], api=async(url,init)=>{calls.push(JSON.parse(init.body));return Response.json({ok:true,result:{message_id:1}})};
 const send=(text,update_id,options={})=>handle(new Request('https://example.org/telegram',{method:'POST',headers:{'content-type':'application/json','x-telegram-bot-api-secret-token':options.secret??env.WEBHOOK_SECRET},body:JSON.stringify({update_id,message:{text,chat:{id:44,type:options.type??'private'},from:{id:options.from??44}}})}),env,api);
 const row=()=>exec('query','SELECT * FROM audience_subscribers',[]).rows;
 return {send,row,calls,env,exec};
}
test('explicit subscribe and unsubscribe persist, older Telegram updates cannot undo choice',async t=>{
 const x=fixture(t);assert.equal((await x.send('/start',1)).status,200);assert.equal(x.row().length,0);assert.match(x.calls[0].text,/добровольной подписки/);
 await x.send('/subscribe',2);assert.equal(x.row()[0].active,1);await x.send('/stop',3);assert.equal(x.row()[0].active,0);
 const n=x.calls.length;await x.send('/subscribe',2);await x.send('/stop',3);assert.equal(x.row()[0].active,0);assert.equal(x.calls.length,n);
 await x.send('/subscribe',4);assert.equal(x.row()[0].active,1);assert.equal(x.row()[0].last_update_id,4);
});
test('disabled feature, wrong secret and non-private or mismatched users cannot subscribe',async t=>{
 const x=fixture(t);assert.equal((await x.send('/subscribe',1,{secret:'wrong'})).status,403);
 await x.send('/subscribe',2,{type:'group'});await x.send('/subscribe',3,{from:45});assert.equal(x.row().length,0);assert.equal(x.calls.length,0);
 const y=fixture(t,false);await y.send('/subscribe',4);assert.equal(y.row().length,0);assert.equal(y.calls.length,0);
});
test('storage errors do not report successful subscription',async t=>{
 const x=fixture(t); x.env.DB={prepare(){throw Error('unavailable');}};
 assert.equal((await x.send('/subscribe',5)).status,503);assert.equal(x.calls.length,0);assert.equal(x.row().length,0);
});
test('old watermarks expire so Telegram update id resets do not permanently lock a subscriber',async t=>{
 const x=fixture(t);await x.send('/subscribe',1000);
 x.exec('query',"UPDATE audience_subscribers SET updated_at = '2020-01-01T00:00:00.000Z'",[]);
 await x.send('/stop',4);assert.equal(x.row()[0].active,0);assert.equal(x.row()[0].last_update_id,4);
});
