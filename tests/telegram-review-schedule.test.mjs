// Guardrails for the review-only scheduled workflow; no credentials or delivery step.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {mkdtemp, rm, readdir} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
const exec=promisify(execFile);

test('scheduled gallery workflow has read-only permissions and no publishing credentials',async()=>{
 const w=await readFile('.github/workflows/prepare_telegram_gallery.yml','utf8');
 assert.match(w,/schedule:\s*\n\s*#.*\n\s*- cron: '17 6 \* \* \*'/);
 assert.match(w,/workflow_dispatch:/); assert.match(w,/permissions:\s*\n\s*contents: read/);
 assert.match(w,/persist-credentials: false/);assert.match(w,/retention-days: 3/);
 assert.match(w,/telegram-review\/candidates\.mjs/);assert.match(w,/telegram-review\/cards_batch\.py/);
 assert.doesNotMatch(w,/\$\{\{\s*secrets\.|REVIEW_INTAKE|BOT_TOKEN|queue-producer|gallery-submit|send_telegram|wrangler|contents: write/);
});
test('regular shortlist contains only unapproved material and does not mutate the feed',async(t)=>{
 const dir=await mkdtemp(join(tmpdir(),'scheduled-gallery-'));t.after(()=>rm(dir,{recursive:true,force:true}));
 const before=await readFile('data/news.json');const output=join(dir,'candidates.json');
 await exec(process.execPath,['telegram-review/candidates.mjs',output]);
 const batch=JSON.parse(await readFile(output,'utf8'));assert.equal(batch.version,1);assert(batch.drafts.length<=8);
 assert(batch.drafts.every(d=>d.ready_for_review===false && d.comment===''));
 assert.deepEqual(await readFile('data/news.json'),before);assert.deepEqual(await readdir(dir),['candidates.json']);
 await assert.rejects(()=>exec(process.execPath,['telegram-review/candidates.mjs',output]));
});
