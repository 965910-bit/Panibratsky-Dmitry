// Generate a Cloudflare Builds configuration locally. This never deploys or changes D1.
import {writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

export function configuration(databaseId) {
  if (typeof databaseId !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(databaseId)) {
    throw new Error('SCM_D1_DATABASE_ID must be a D1 database UUID');
  }
  return {
    name: 'scm-telegram-review',
    main: 'worker.mjs',
    compatibility_date: '2026-11-01',
    keep_vars: true,
    secrets: {required:['BOT_TOKEN', 'CHANNEL_ID', 'INTAKE_SECRET', 'REVIEWER_ID', 'WEBHOOK_SECRET']},
    d1_databases: [{binding:'DB', database_name:'scm-review', database_id:databaseId}],
  };
}

async function main() {
  const config = configuration(process.env.SCM_D1_DATABASE_ID);
  const target = fileURLToPath(new URL('./.wrangler-build.json', import.meta.url));
  await writeFile(target, JSON.stringify(config, null, 2) + '\n', {flag:'wx', mode:0o600});
  console.log('Temporary Wrangler configuration created; no deployment performed.');
}
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch(error => { console.error(`Configuration not created: ${error.message}`); process.exitCode = 1; });
}
