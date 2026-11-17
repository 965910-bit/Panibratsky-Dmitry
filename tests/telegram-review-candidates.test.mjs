import {test} from 'node:test';
import assert from 'node:assert/strict';
import {shortlist} from '../telegram-review/candidates.mjs';
import {buildPayload} from '../telegram-review/drafts.mjs';

const item = (title, link) => ({title, link, source:'Источник', description:'Описание'});
test('offline shortlist filters, deduplicates and keeps every candidate unapproved', () => {
  const news = [item('Общее событие', 'https://example.org/1'), item('WMS на складе', 'https://example.org/2'), item('Склад повтор', 'https://example.org/2'), item('Логистика', 'javascript:alert(1)'), {...item('Склад', 'https://example.org/3'),dead:true}, item('Оповещение Google — логистика', 'https://example.org/4'), item('Управление запасами', 'https://example.org/5')];
  const drafts = shortlist(news);
  assert.deepEqual(drafts.map(d=>d.source_url), ['https://example.org/2','https://example.org/5']);
  for (const draft of drafts) { assert.equal(draft.ready_for_review,false); assert.equal(draft.comment,''); assert.throws(()=>buildPayload(draft)); }
});
test('limits and malformed feed fail closed', () => {
  assert.throws(()=>shortlist({})); assert.throws(()=>shortlist([],0)); assert.throws(()=>shortlist([],21));
  assert.equal(shortlist([item('Склад', 'https://example.org/1'), item('WMS', 'https://example.org/2')],1).length,1);
});
