import {test} from 'node:test';
import assert from 'node:assert/strict';
import {selectAutomatic} from '../telegram-review/auto-candidates.mjs';
import {buildCandidatePayload, buildPayload} from '../telegram-review/drafts.mjs';

const now=Date.parse('2026-11-17T12:00:00Z');
const item=(link,date,title='Склад и логистика')=>({title,link,source:'Источник',description:'Текст',pubDate:date});
test('automatic selection requires explicit exact HTTPS sources and fresh publication dates',()=>{
 const list=[item('https://example.org/recent','2026-11-17T11:00:00Z'),item('https://example.org/older','2026-11-16T12:00:00Z'),
 item('https://example.org/stale','2026-10-20T11:59:59Z'),item('https://example.org/future','2026-11-17T12:01:00Z'),item('https://example.org/bad','no date'),
 item('https://sub.example.org/1','2026-11-17T11:30:00Z'),item('http://example.org/http','2026-11-17T11:30:00Z'),item('https://logistics360.ru/a','2026-11-17T11:30:00Z'),
 item('https://example.org/alert','2026-11-17T11:30:00Z','Оповещение Google — логистика')];
 const selected=selectAutomatic(list,['example.org','logistics360.ru'],now);
 assert.deepEqual(selected.map(d=>d.source_url),['https://logistics360.ru/a','https://example.org/recent','https://example.org/older']);
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
 assert.ok(workflow.includes('workflow_dispatch:'));
 assert.ok(!workflow.includes('schedule:'));
 assert.ok(workflow.includes("inputs.confirmation == 'STAGING'"));
 assert.ok(workflow.includes('environment: telegram-review-staging'));
 assert.ok(workflow.includes('REVIEW_INTAKE_URL: https://scm-telegram-review-staging.965910.workers.dev/intake'));
 assert.ok(workflow.includes('secrets.SCM_STAGING_INTAKE_SECRET'));
 assert.ok(workflow.includes('vars.SCM_STAGING_ALLOWED_HOSTS'));
 assert.ok(workflow.includes('persist-credentials: false'));
 assert.ok(!/BOT_TOKEN|CHANNEL_ID|contents: write|send_telegram|wrangler/.test(workflow));
});
test('production workflow is confirmed or scheduled and fixed to the live Worker',async()=>{
 const {readFile}=await import('node:fs/promises');
 const workflow=await readFile('.github/workflows/telegram_review_production.yml','utf8');
 assert.ok(workflow.includes('workflow_dispatch:'));
 assert.ok(workflow.includes('schedule:'));
 assert.ok(workflow.includes("github.event_name == 'schedule' || inputs.confirmation == 'PRODUCTION'"));
 assert.ok(workflow.includes('environment: telegram-review'));
 assert.ok(workflow.includes('REVIEW_INTAKE_URL: https://scm-telegram-review.965910.workers.dev/intake'));
 assert.ok(workflow.includes('secrets.SCM_INTAKE_SECRET'));
 assert.ok(workflow.includes('vars.SCM_REVIEW_ALLOWED_HOSTS'));
 assert.ok(!workflow.includes('scm-telegram-review-staging'));
 assert.ok(!workflow.includes('SCM_STAGING'));
 assert.ok(workflow.includes('persist-credentials: false'));
 assert.ok(!/BOT_TOKEN|CHANNEL_ID|contents: write|send_telegram|wrangler/.test(workflow));
});
