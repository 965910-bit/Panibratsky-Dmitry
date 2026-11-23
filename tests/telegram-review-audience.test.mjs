import {test} from 'node:test';
import assert from 'node:assert/strict';
import {subscriptionIntent, eligibleDeliveries} from '../telegram-review/audience-policy.mjs';

const message = (text, chat=123, from=123, type='private') => ({message:{text,chat:{id:chat,type},from:{id:from,is_bot:false}}});
test('subscription is explicit and revocable, /start alone never subscribes',()=>{
 assert.deepEqual(subscriptionIntent(message('/start')), {action:'info',chatId:'123'});
 assert.deepEqual(subscriptionIntent(message('/subscribe')), {action:'subscribe',chatId:'123'});
 for (const cmd of ['/stop','/unsubscribe']) assert.equal(subscriptionIntent(message(cmd)).action,'unsubscribe');
 for (const input of [message('/subscribe',123,124),message('/subscribe',-123,123,'group'),message('/subscribe',123,123,'channel'),message('/subscribe anything'),message('/START'),{message:{text:'/subscribe',chat:{id:123,type:'private'},from:{id:123,is_bot:true}}},{}]) assert.equal(subscriptionIntent(input),null);
});
test('only an already published approved draft and explicit active recipients are eligible',()=>{
 const draft={id:'00000000-0000-4000-8000-000000000001',state:'sent'};
 const subscribers=[{chat_id:'1',active:1},{chat_id:'2',active:0},{chat_id:'1',active:1},{chat_id:'-3',active:1}];
 const targets=[{chat_id:'-100',enabled:1,kind:'channel'},{chat_id:'-101',enabled:0,kind:'group'},{chat_id:'1',enabled:1,kind:'channel'},{chat_id:'-100',enabled:1,kind:'channel'}];
 assert.deepEqual(eligibleDeliveries(draft,subscribers,targets),[{type:'subscriber',id:'1'},{type:'destination',id:'-100'}]);
 for (const state of ['ready','sending','rejected','notifying']) assert.throws(()=>eligibleDeliveries({...draft,state},subscribers,targets));
 assert.throws(()=>eligibleDeliveries({...draft,id:'bad'},subscribers,targets));
});
