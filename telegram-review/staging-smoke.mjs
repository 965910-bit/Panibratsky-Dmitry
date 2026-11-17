// Read-only probe of the isolated staging Worker. No Telegram calls or writes.
import {randomUUID} from 'node:crypto';
import {pathToFileURL} from 'node:url';

const STAGING_ORIGIN = 'https://scm-telegram-review-staging.965910.workers.dev';
const MAX_RESPONSE = 4096;

async function readJson(response) {
  const reader = response.body?.getReader();
  if (!reader) throw Error('Invalid response');
  let size = 0, parts = [];
  for (;;) {
    const {done, value} = await reader.read();
    if (done) break;
    size += value.length;
    if (size > MAX_RESPONSE) { await reader.cancel(); throw Error('Invalid response'); }
    parts.push(value);
  }
  return JSON.parse(Buffer.concat(parts.map(part=>Buffer.from(part))).toString('utf8'));
}

export async function smoke(options = {}) {
  // An exact fixed hostname prevents inadvertently sending a secret to production or another host.
  if (typeof options.secret !== 'string' || !/^[A-Za-z0-9_-]{32,256}$/.test(options.secret)) throw Error('Invalid staging secret');
  if (options.confirm !== true) throw Error('Explicit staging confirmation required');
  const fetcher = options.fetcher || fetch;
  const source = `https://example.invalid/staging-smoke/${randomUUID()}`;
  const send = headers => fetcher(`${STAGING_ORIGIN}/availability`, {
    method:'POST', headers:{'content-type':'application/json', ...headers},
    body:JSON.stringify({source_urls:[source]}), redirect:'error', signal:AbortSignal.timeout(15000),
  });
  // A missing/old route must fail before the secret is sent.
  const denied = await send({});
  if (denied.status !== 403) throw Error('Unauthenticated staging check failed');
  const response = await send({authorization:`Bearer ${options.secret}`});
  if (response.status !== 200) throw Error('Authenticated staging check failed');
  let data; try { data = await readJson(response); } catch { throw Error('Invalid staging response'); }
  if (!data || !Array.isArray(data.known) || data.known.length !== 1 || data.known[0] !== false || !Number.isSafeInteger(data.pending) || data.pending < 0 || !Number.isSafeInteger(data.uncertain) || data.uncertain < 0) throw Error('Invalid staging response');
  return {pending:data.pending, uncertain:data.uncertain};
}

async function main(args) {
  if (args.length !== 1 || args[0] !== '--confirm-staging-read-only') throw Error('Explicit staging confirmation required');
  const state = await smoke({confirm:true, secret:process.env.SCM_STAGING_INTAKE_SECRET});
  console.log(`Staging read-only check passed. Pending: ${state.pending}; uncertain: ${state.uncertain}. No messages sent.`);
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  // Never print raw errors: network errors may contain request details.
  main(process.argv.slice(2)).catch(()=>{console.error('Staging check failed or unavailable; no delivery or deployment is confirmed.');process.exitCode=1;});
}
