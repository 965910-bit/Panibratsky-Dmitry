import {test} from 'node:test';
import assert from 'node:assert/strict';
import {configuration} from '../telegram-review/build-config.mjs';

test('build configuration targets existing D1 without including secrets', () => {
  const config = configuration('12345678-1234-1234-1234-123456789abc');
  assert.deepEqual(config.d1_databases, [{binding:'DB', database_name:'scm-review', database_id:'12345678-1234-1234-1234-123456789abc'}]);
  assert.equal(config.name,'scm-telegram-review');
  assert.equal(config.main,'worker.mjs');
  assert.equal(config.keep_vars,true);
  assert.deepEqual(config.secrets.required,['BOT_TOKEN','CHANNEL_ID','INTAKE_SECRET','REVIEWER_ID','WEBHOOK_SECRET']);
  assert.equal('vars' in config,false);
});
test('missing, malformed or injectable database identifiers fail closed', () => {
  for (const value of [undefined, '', 'REPLACE_LOCALLY', '12345678-1234-1234-1234-123456789abc\n"vars":{}', 'not-a-uuid']) {
    assert.throws(() => configuration(value));
  }
});
