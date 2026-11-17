import {test} from 'node:test';
import assert from 'node:assert/strict';
import {configuration} from '../telegram-review/build-config.mjs';

test('build configuration targets existing D1 without including secrets', () => {
  const config = configuration('12345678-1234-1234-1234-123456789abc', 'production');
  assert.deepEqual(config.d1_databases, [{binding:'DB', database_name:'scm-review', database_id:'12345678-1234-1234-1234-123456789abc'}]);
  assert.equal(config.name,'scm-telegram-review');
  assert.equal(config.main,'worker.mjs');
  assert.equal(config.compatibility_date,'2026-11-01');
  assert.equal(config.keep_vars,true);
  assert.deepEqual(config.secrets.required,['BOT_TOKEN','CHANNEL_ID','INTAKE_SECRET','REVIEWER_ID','WEBHOOK_SECRET']);
  assert.equal('vars' in config,false);
  assert.equal('preview_urls' in config,false);
  assert.equal('observability' in config,false);
});
test('missing, malformed or injectable database identifiers fail closed', () => {
  for (const value of [undefined, '', 'REPLACE_LOCALLY', '12345678-1234-1234-1234-123456789abc\n"vars":{}', 'not-a-uuid']) {
    assert.throws(() => configuration(value, 'production'));
  }
});

test('target must be explicit and selects matching staging Worker and database', () => {
  const id = '12345678-1234-1234-1234-123456789abc';
  for (const target of [undefined, '', 'Production', '__proto__', 'other']) assert.throws(() => configuration(id, target));
  const config = configuration(id, 'staging');
  assert.equal(config.name, 'scm-telegram-review-staging');
  assert.equal(config.compatibility_date,'2026-11-17');
  assert.equal(config.preview_urls, false);
  assert.deepEqual(config.observability, {enabled:true, logs:{enabled:true}});
  assert.deepEqual(config.d1_databases, [{binding:'DB', database_name:'scm-review-staging', database_id:id}]);
});
