import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {queueOne,checkQueue,queueAutomaticCandidate,checkAutomaticQueue} from '../telegram-review/queue-producer.mjs';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {draftFingerprint} from '../telegram-review/drafts.mjs';
const draft=(n)=>({version:1,title:`Склад ${n}`,description:'Описание',source_name:'Источник',source_url:`https://example.org/${n}`,comment:'Проверенный вывод',ready_for_review:true});
const png=d=>{const a=Buffer.alloc(33);Buffer.from([137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82]).copy(a);a.writeUInt32BE(1080,16);a.writeUInt32BE(1080,20);const info=Buffer.from('SCM-Draft-SHA256\0'+draftFingerprint(d)),c=Buffer.alloc(info.length+12),e=Buffer.alloc(12);c.writeUInt32BE(info.length);c.write('tEXt',4);info.copy(c,8);e.write('IEND',4);return Buffer.concat([a,c,e]);};
async function gallery(t){const dir=await mkdtemp(join(tmpdir(),'queue-producer-'));t.after(()=>rm(dir,{recursive:true,force:true}));for(let i=1;i<=2;i++){const d=draft(i);await writeFile(join(dir,`draft-0${i}.json`),JSON.stringify(d));await writeFile(join(dir,`card-0${i}.png`),png(d));}return dir;}
const options=fetcher=>({send:true,url:'https://test.example.workers.dev/intake',secret:'a'.repeat(32),fetcher});
test('chooses first unknown approved candidate and makes exactly two requests',async(t)=>{const dir=await gallery(t),calls=[];const fetcher=async(url,init)=>{calls.push({url,init});return calls.length===1?Response.json({known:[true,false],pending:0,uncertain:0}):new Response('',{status:201});};const r=await queueOne(dir,options(fetcher));assert.equal(r.status,'queued');assert.equal(calls.length,2);assert.match(calls[0].url,/\/availability$/);assert.match(calls[1].url,/\/intake-one$/);assert.equal(JSON.parse(calls[1].init.body).source_url,'https://example.org/2');});
test('pending, uncertain, known, malformed and failures never trigger intake or retries',async(t)=>{const dir=await gallery(t);for(const state of [{known:[false,false],pending:1,uncertain:0},{known:[false,false],pending:0,uncertain:1},{known:[true,true],pending:0,uncertain:0},{known:[false],pending:0,uncertain:0}]){let n=0;const fetcher=async()=>{n++;return Response.json(state);};if(state.known.length===1)await assert.rejects(()=>queueOne(dir,options(fetcher)));else await queueOne(dir,options(fetcher));assert.equal(n,1);}let n=0;await assert.rejects(()=>queueOne(dir,options(async()=>{n++;return new Response('',{status:503});})));assert.equal(n,1);await assert.rejects(()=>queueOne(dir,{}));});
test('no approved candidates causes no network and missing card fails closed',async(t)=>{const dir=await gallery(t);for(let i=1;i<=2;i++)await writeFile(join(dir,`draft-0${i}.json`),JSON.stringify({...draft(i),ready_for_review:false}));let n=0;const fetcher=async()=>{n++;};assert.equal((await queueOne(dir,options(fetcher))).status,'none-ready');assert.equal(n,0);await writeFile(join(dir,'draft-01.json'),JSON.stringify({...draft(1),title:'изменено'}));await assert.rejects(()=>queueOne(dir,options(fetcher)),/не соответствует/);assert.equal(n,0);});

test('an old worker without guarded endpoint fails closed without falling back',async(t)=>{const dir=await gallery(t),urls=[];await assert.rejects(()=>queueOne(dir,options(async url=>{urls.push(url);return urls.length===1?Response.json({known:[false,false],pending:0,uncertain:0}):new Response('',{status:404});})),/404/);assert.equal(urls.length,2);assert.match(urls[1],/\/intake-one$/);});

test('read-only check reports each ready item and never sends a draft',async(t)=>{
 const dir=await gallery(t),calls=[];const fetcher=async(url,init)=>{calls.push({url,init});return Response.json({known:[true,false],pending:0,uncertain:0});};
 const report=await checkQueue(dir,options(fetcher));
 assert.deepEqual(report,{status:'candidate',items:[{number:1,known:true},{number:2,known:false}],pending:0,uncertain:0,next:2});
 assert.equal(calls.length,1);assert.match(calls[0].url,/\/availability$/);
 assert.deepEqual(JSON.parse(calls[0].init.body),{source_urls:['https://example.org/1','https://example.org/2']});
 assert(!JSON.stringify(report).includes('https://'));assert(!JSON.stringify(report).includes('a'.repeat(32)));
});
test('read-only check reports blocked states without recommending a candidate',async(t)=>{
 const dir=await gallery(t);for(const [pending,uncertain,status] of [[1,0,'pending'],[0,2,'uncertain'],[1,2,'uncertain']]){
  let calls=0;const report=await checkQueue(dir,options(async()=>{calls++;return Response.json({known:[false,true],pending,uncertain});}));
  assert.equal(report.status,status);assert.equal(report.next,null);assert.equal(calls,1);
 }
 const report=await checkQueue(dir,options(async()=>Response.json({known:[true,true],pending:0,uncertain:0})));
 assert.equal(report.status,'all-known');assert.equal(report.next,null);
});
test('check without approved material stays offline; malformed, oversized and failed replies fail closed',async(t)=>{
 const dir=await gallery(t);let calls=0;const fetcher=async()=>{calls++;throw Error('must not send');};
 for(let i=1;i<=2;i++)await writeFile(join(dir,`draft-0${i}.json`),JSON.stringify({...draft(i),ready_for_review:false}));
 assert.deepEqual(await checkQueue(dir,{fetcher}),{status:'none-ready',items:[],pending:null,uncertain:null,next:null});assert.equal(calls,0);
 await writeFile(join(dir,'draft-01.json'),JSON.stringify(draft(1)));
 for(const reply of [new Response('x'.repeat(8193)),Response.json({known:[false],pending:'0',uncertain:0}),new Response('',{status:404})]){
  let n=0;await assert.rejects(()=>checkQueue(dir,options(async()=>{n++;return reply;})));assert.equal(n,1);
 }
 await assert.rejects(()=>checkQueue(dir,options(fetcher)));assert.equal(calls,1);
});
test('check CLI without ready material is offline and prints only the report',async(t)=>{
 const dir=await gallery(t);for(let i=1;i<=2;i++)await writeFile(join(dir,`draft-0${i}.json`),JSON.stringify({...draft(i),ready_for_review:false}));
 const {stdout}=await promisify(execFile)(process.execPath,['telegram-review/queue-producer.mjs',dir,'--check']);
 assert.equal(JSON.parse(stdout).status,'none-ready');assert(!stdout.includes('https://'));
});


test('unverified automatic candidate goes only to guarded intake with no invented comment',async(t)=>{
 const dir=await gallery(t);for(let i=1;i<=2;i++)await writeFile(join(dir,`draft-0${i}.json`),JSON.stringify({...draft(i),comment:'',ready_for_review:false}));
 const calls=[];const fetcher=async(url,init)=>{calls.push({url,init});return calls.length===1?Response.json({known:[true,false],pending:0,uncertain:0}):new Response('',{status:201});};
 assert.equal((await queueAutomaticCandidate(dir,options(fetcher))).status,'queued');
 assert.equal(calls.length,2);assert.match(calls[1].url,/\/intake-one$/);
 const payload=JSON.parse(calls[1].init.body);assert.equal(payload.source_url,'https://example.org/2');assert.doesNotMatch(payload.text,/Вывод|Проверенный вывод/);
});
test('automatic candidate pauses for unresolved or pending work and never retries failures',async(t)=>{
 const dir=await gallery(t);for(let i=1;i<=2;i++)await writeFile(join(dir,`draft-0${i}.json`),JSON.stringify({...draft(i),comment:'',ready_for_review:false}));
 for(const state of [{known:[false,false],pending:1,uncertain:0},{known:[false,false],pending:0,uncertain:1},{known:[true,true],pending:0,uncertain:0}]){
  let n=0;await queueAutomaticCandidate(dir,options(async()=>{n++;return Response.json(state);}));assert.equal(n,1);
 }
 let n=0;await assert.rejects(()=>queueAutomaticCandidate(dir,options(async()=>{n++;return n===1?Response.json({known:[false,false],pending:0,uncertain:0}):new Response('',{status:503});})));assert.equal(n,2);
 await assert.rejects(()=>queueAutomaticCandidate(dir,{}));
});

test('automatic candidate diagnostic is read-only and reports queue state',async(t)=>{
 const dir=await gallery(t);for(let i=1;i<=2;i++)await writeFile(join(dir,`draft-0${i}.json`),JSON.stringify({...draft(i),comment:'',ready_for_review:false}));
 const calls=[];const result=await checkAutomaticQueue(dir,options(async(url,init)=>{calls.push({url,init});return Response.json({known:[true,false],pending:1,uncertain:0});}));
 assert.equal(result.status,'pending');assert.equal(result.pending,1);assert.equal(calls.length,1);assert.match(calls[0].url,/\/availability$/);assert(!JSON.stringify(result).includes('https://'));
});
