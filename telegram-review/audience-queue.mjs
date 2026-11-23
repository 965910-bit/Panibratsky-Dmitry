// Staged building blocks only: not wired to the live Worker, cron or Telegram.
// Callers must authenticate, limit throughput, validate channel permissions,
// and provide a transport; these functions do not discover or contact recipients.
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const changes = r => r?.success === true && Number.isSafeInteger(r?.meta?.changes) ? r.meta.changes : (()=>{throw Error('Storage unavailable');})();
function validate(draftId, type, recipientId) {
  if (!UUID.test(draftId) || !['subscriber','destination'].includes(type) || typeof recipientId !== 'string' || !(type === 'subscriber' ? /^[1-9]\d{0,19}$/ : /^-[1-9]\d{0,19}$/).test(recipientId)) throw Error('Invalid audience request');
}

// Creates a single immutable campaign boundary for a published draft. Repeated
// calls never move the boundary, so later signups are not backfilled.
export async function startAudienceCampaign(db, draftId) {
  if (typeof draftId !== 'string' || !UUID.test(draftId)) throw Error('Invalid draft');
  const now = new Date().toISOString();
  const r = await db.prepare("INSERT OR IGNORE INTO audience_campaigns (draft_id,created_at) SELECT id,? FROM drafts WHERE id=? AND state='sent' AND channel_message_id IS NOT NULL").bind(now,draftId).run();
  return changes(r) === 1;
}

// Enqueue one existing, explicitly eligible recipient. Batch enumeration, if
// added later, must use bounded pages and not emit chat IDs in logs.
export async function enqueueAudienceRecipient(db, draftId, type, recipientId) {
  validate(draftId,type,recipientId);
  const table = type === 'subscriber' ? 'audience_subscribers' : 'audience_destinations';
  const field = type === 'subscriber' ? 'subscribed_at' : 'created_at';
  const enabled = type === 'subscriber' ? 'active' : 'enabled';
  const now = new Date().toISOString();
  const sql = `INSERT OR IGNORE INTO audience_deliveries (draft_id,recipient_type,recipient_id,state,created_at,updated_at)
    SELECT c.draft_id,?,r.chat_id,'pending',?,? FROM audience_campaigns c
    JOIN drafts d ON d.id=c.draft_id AND d.state='sent' AND d.channel_message_id IS NOT NULL
    JOIN ${table} r ON r.chat_id=? AND r.${enabled}=1 AND r.${field} <= c.created_at
    WHERE c.draft_id=?`;
  return changes(await db.prepare(sql).bind(type,now,now,recipientId,draftId).run()) === 1;
}

// One atomic claim, one transport call. No automatic retry: any error after
// claiming may indicate successful delivery. A hung/crashed call stays sending.
export async function deliverAudienceRecipient(db, draftId, type, recipientId, send) {
  validate(draftId,type,recipientId);
  if (typeof send !== 'function') throw Error('Transport required');
  const table = type === 'subscriber' ? 'audience_subscribers' : 'audience_destinations';
  const enabled = type === 'subscriber' ? 'active' : 'enabled';
  const joinedAt = type === 'subscriber' ? 'subscribed_at' : 'created_at';
  const now = new Date().toISOString();
  const claim = `UPDATE audience_deliveries SET state='sending',updated_at=?
    WHERE draft_id=? AND recipient_type=? AND recipient_id=? AND state='pending'
    AND EXISTS (SELECT 1 FROM ${table} r JOIN audience_campaigns c ON c.draft_id=audience_deliveries.draft_id WHERE r.chat_id=audience_deliveries.recipient_id AND r.${enabled}=1 AND r.${joinedAt} <= c.created_at)
    AND EXISTS (SELECT 1 FROM drafts d WHERE d.id=audience_deliveries.draft_id AND d.state='sent' AND d.channel_message_id IS NOT NULL)`;
  if (changes(await db.prepare(claim).bind(now,draftId,type,recipientId).run()) !== 1) return {status:'not-claimed'};
  try {
    const draft = await db.prepare("SELECT text,source_url,photo_file_id FROM drafts WHERE id=? AND state='sent' AND channel_message_id IS NOT NULL").bind(draftId).first();
    if (!draft || typeof draft.text !== 'string' || !draft.text.trim() || draft.text.length > 3000 || typeof draft.source_url !== 'string' || draft.source_url.length > 2048) throw Error('Invalid draft');
    const url = new URL(draft.source_url);
    if (!['http:','https:'].includes(url.protocol) || !url.hostname || url.username || url.password) throw Error('Invalid source');
    if (draft.photo_file_id != null && (typeof draft.photo_file_id !== 'string' || !draft.photo_file_id || draft.photo_file_id.length > 512)) throw Error('Invalid photo');
    const text = `${draft.text.trim()}\n\nИсточник: ${draft.source_url}`;
    if (text.length > (draft.photo_file_id ? 1024 : 4096)) throw Error('Message too long');
    const posted = await send({chatId:recipientId,text,photoFileId:draft.photo_file_id || null});
    if (!Number.isSafeInteger(posted?.message_id) || posted.message_id <= 0) throw Error('Invalid transport response');
    const updated = await db.prepare("UPDATE audience_deliveries SET state='sent',message_id=?,updated_at=? WHERE draft_id=? AND recipient_type=? AND recipient_id=? AND state='sending'").bind(posted.message_id,new Date().toISOString(),draftId,type,recipientId).run();
    if (changes(updated) !== 1) throw Error('Storage state uncertain');
    return {status:'sent'};
  } catch {
    // Best effort journal update only. Never turn an unknown result back to pending.
    try { await db.prepare("UPDATE audience_deliveries SET state='uncertain',updated_at=? WHERE draft_id=? AND recipient_type=? AND recipient_id=? AND state='sending'").bind(new Date().toISOString(),draftId,type,recipientId).run(); } catch {}
    return {status:'uncertain'};
  }
}
