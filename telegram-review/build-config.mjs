// Generate a Cloudflare Builds configuration locally. This never deploys or changes D1.
import {writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

export function configuration(databaseId, target) {
  const targets = {production: ['scm-telegram-review', 'scm-review'], staging: ['scm-telegram-review-staging', 'scm-review-staging']};
  if (!Object.hasOwn(targets, target)) throw new Error('SCM_BUILD_TARGET must be staging or production');
  const [workerName, databaseName] = targets[target];
  if (typeof databaseId !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(databaseId)) {
    throw new Error('SCM_D1_DATABASE_ID must be a D1 database UUID');
  }
  return {
    name: workerName,
    main: 'worker.mjs',
    compatibility_date: target === 'staging' ? '2026-11-17' : '2026-11-01',
    keep_vars: true,
    // Explicitly match the isolated test Worker's intended settings.
    ...(target === 'staging' ? {preview_urls:false, observability:{enabled:true, logs:{enabled:true}}} : {}),
    secrets: {required:['BOT_TOKEN', 'CHANNEL_ID', 'INTAKE_SECRET', 'REVIEWER_ID', 'WEBHOOK_SECRET']},
    d1_databases: [{binding:'DB', database_name:databaseName, database_id:databaseId}],
  };
}

async function main() {
  const config = configuration(process.env.SCM_D1_DATABASE_ID, process.env.SCM_BUILD_TARGET);
  const target = fileURLToPath(new URL('./.wrangler-build.json', import.meta.url));
  await writeFile(target, JSON.stringify(config, null, 2) + '\n', {flag:'wx', mode:0o600});
  console.log('Temporary Wrangler configuration created; no deployment performed.');
}
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch(error => { console.error(`Configuration not created: ${error.message}`); process.exitCode = 1; });
}
