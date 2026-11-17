import {test} from 'node:test';
import assert from 'node:assert/strict';
import {selectAutomatic} from '../telegram-review/auto-candidates.mjs';
import {buildCandidatePayload, buildPayload} from '../telegram-review/drafts.mjs';

const now=Date.parse('2026-11-17T12:00:00Z');
const item=(link,date,title='Склад и логистика')=>({title,link,source:'Источник',description:'Текст',pubDate:date});
test('automatic selection requires explicit exact HTTPS sources and fresh publication dates',()=>{
 const list=[item('https://example.org/recent','2026-11-17T11:00:00Z'),item('https://example.org/older','2026-11-16T12:00:00Z'),
 item('https://example.org/stale','2026-11-15T11:59:59Z'),item('https://example.org/future','2026-11-17T12:01:00Z'),item('https://example.org/bad','no date'),
 item('https://sub.example.org/1','2026-11-17T11:30:00Z'),item('http://example.org/http','2026-11-17T11:30:00Z'),item('https://logistics360.ru/a','2026-11-17T11:30:00Z'),
 item('https://example.org/alert','2026-11-17T11:30:00Z','Оповещение Google — логистика')];
 const selected=selectAutomatic(list,['example.org','logistics360.ru'],now);
 assert.deepEqual(selected.map(d=>d.source_url),['https://example.org/recent','https://example.org/older']);
 assert(selected.every(d=>!d.ready_for_review && d.comment===''));
 assert.throws(()=>selectAutomatic(list,[],now));assert.throws(()=>selectAutomatic(list,['https://example.org'],now));
});
test('unreviewed payload never pretends to include a human conclusion or changes reviewed-mode checks',()=>{
 const [d]=selectAutomatic([item('https://example.org/a','2026-11-17T11:00:00Z')],['example.org'],now);
 const payload=buildCandidatePayload(d); assert.match(payload.text,/Склад и логистика/);assert.doesNotMatch(payload.text,/Вывод/);
 assert.throws(()=>buildPayload(d)); assert.throws(()=>buildCandidatePayload({...d,ready_for_review:true}));assert.throws(()=>buildCandidatePayload({...d,comment:'edited'}));
});

test('staging workflow is manual, explicitly confirmed and fixed to isolated Worker',async()=>{
 const {readFile}=await import('node:fs/promises');
 const workflow=await readFile('.github/workflows/telegram_review_staging.yml','utf8');
 assert.match(workflow,/workflow_dispatch:/);assert.doesNotMatch(workflow,/schedule:|cron:/);
 assert.match(workflow,/inputs\.confirmation == 'STAGING'/);assert.match(workflow,/environment: telegram-review-staging/);
 assert.match(workflow,/REVIEW_INTAKE_URL: https:\/\/scm-telegram-review-staging\.965910\.workers\.dev\/intake/);
 assert.match(workflow,/secrets\.SCM_STAGING_INTAKE_SECRET/);assert.match(workflow,/vars\.SCM_STAGING_ALLOWED_HOSTS/);
 assert.match(workflow,/persist-credentials: false/);assert.doesNotMatch(workflow,/BOT_TOKEN|CHANNEL_ID|contents: write|send_telegram|wrangler/);
});
