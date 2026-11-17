import {test} from 'node:test';
import assert from 'node:assert/strict';
import {smoke} from '../telegram-review/staging-smoke.mjs';

const secret = 's'.repeat(40);
const success = () => Response.json({known:[false],pending:2,uncertain:1});
test('staging probe sends only read-only authenticated availability requests to fixed host', async()=>{
  const calls=[];
  const result=await smoke({secret,confirm:true,fetcher:async(url,init)=>{calls.push({url,init});return calls.length===1?new Response('',{status:403}):success();}});
  assert.deepEqual(result,{pending:2,uncertain:1});assert.equal(calls.length,2);
  assert.equal(calls[0].url,'https://scm-telegram-review-staging.965910.workers.dev/availability');
  assert.equal(calls[1].url,calls[0].url);assert.equal(calls[0].init.method,'POST');
  assert.equal(calls[0].init.headers.authorization,undefined);assert.equal(calls[1].init.headers.authorization,`Bearer ${secret}`);
  assert.equal(calls[1].init.redirect,'error');assert(calls[1].init.signal instanceof AbortSignal);
  const first=JSON.parse(calls[0].init.body), second=JSON.parse(calls[1].init.body);assert.deepEqual(first,second);
  assert.match(first.source_urls[0],/^https:\/\/example\.invalid\/staging-smoke\/[0-9a-f-]{36}$/);
});
test('requires explicit confirmation and valid secret before networking',async()=>{
  let n=0;const fetcher=()=>{n++;};
  for(const opts of [{secret,fetcher},{confirm:true,secret:'bad',fetcher}]) await assert.rejects(()=>smoke(opts));
  assert.equal(n,0);
});
test('stops before sending secret when endpoint is missing, open or unavailable',async()=>{
  for(const status of [200,404,503]) {let n=0;await assert.rejects(()=>smoke({secret,confirm:true,fetcher:async()=>{n++;return new Response('',{status});}}));assert.equal(n,1);}
});
test('rejects auth failures, malformed, oversized and misleading responses without retry',async()=>{
  const responses=[new Response('',{status:403}),Response.json({known:[true],pending:0,uncertain:0}),Response.json({known:[false],pending:-1,uncertain:0}),Response.json({known:[false],pending:0,uncertain:'0'}),new Response('x'.repeat(4097))];
  for(const response of responses){let n=0;await assert.rejects(()=>smoke({secret,confirm:true,fetcher:async()=>++n===1?new Response('',{status:403}):response}));assert.equal(n,2);}
  let n=0;await assert.rejects(()=>smoke({secret,confirm:true,fetcher:async()=>{n++;throw Error('network');}}));assert.equal(n,1);
});
