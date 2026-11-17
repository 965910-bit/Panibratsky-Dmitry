// Cloudflare Worker: editorial approval only; no scheduled publishing.
const MAX_BODY = 270000;
const MAX_PNG = 180000;
const equal = (a, b) => {
  if (typeof a !== 'string' || typeof b !== 'string' || !a || !b) return false;
  const enc = new TextEncoder(), x = enc.encode(a), y = enc.encode(b);
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) diff |= (x[i] || 0) ^ (y[i] || 0);
  return diff === 0;
};
const result = (code, message) => new Response(message, {status: code, headers: {'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff'}});
const changes = r => r?.meta?.changes || 0;
function configured(env) {
  return !!(env.DB && /^\d{1,20}$/.test(env.REVIEWER_ID || '') && /^-?\d{1,20}$/.test(env.CHANNEL_ID || '') && /^\d{1,20}:[A-Za-z0-9_-]{20,}$/.test(env.BOT_TOKEN || '') && /^[A-Za-z0-9_-]{32,256}$/.test(env.WEBHOOK_SECRET || '') && /^[A-Za-z0-9_-]{32,256}$/.test(env.INTAKE_SECRET || '') && env.WEBHOOK_SECRET !== env.INTAKE_SECRET);
}
async function body(req) {
  if (!/^application\/json(?:\s*;|$)/i.test(req.headers.get('content-type') || '')) throw Error('content type');
  const reader = req.body?.getReader(); if (!reader) throw Error('body');
  let size = 0, parts = [];
  for (;;) { const {done, value} = await reader.read(); if (done) break; size += value.length; if (size > MAX_BODY) { await reader.cancel(); throw Error('body too large'); } parts.push(value); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const part of parts) { bytes.set(part, offset); offset += part.length; }
  return JSON.parse(new TextDecoder().decode(bytes));
}
function validDraft(d) {
  if (!d || typeof d !== 'object' || typeof d.text !== 'string' || !d.text.trim() || d.text.length > 3000 || typeof d.source_url !== 'string' || d.source_url.length > 2048 || d.text.trim().length + d.source_url.length > 3800) return false;
  try { const u = new URL(d.source_url); return ['https:', 'http:'].includes(u.protocol) && !!u.hostname && !u.username && !u.password; } catch { return false; }
}
function decodeCard(value) {
  if (typeof value !== 'string' || value.length > Math.ceil(MAX_PNG / 3) * 4 || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value)) throw Error('invalid card');
  let binary; try { binary = atob(value); } catch { throw Error('invalid card'); }
  if (binary.length < 33 || binary.length > MAX_PNG) throw Error('invalid card');
  const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
  const signature = [137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82];
  if (!signature.every((v, i) => bytes[i] === v)) throw Error('invalid card');
  const view = new DataView(bytes.buffer);
  if (view.getUint32(16) !== 1080 || view.getUint32(20) !== 1080) throw Error('invalid size');
  return bytes;
}
const postText = draft => `${draft.text.trim()}\n\nИсточник: ${draft.source_url}`;
const reviewPrefix = 'ЧЕРНОВИК · проверьте источник и текст\n\n';
async function sendPhoto(env, data, bytes, fetcher) {
  const form = new FormData();
  form.set('chat_id', String(data.chat_id));
  form.set('caption', data.caption);
  form.set('reply_markup', JSON.stringify(data.reply_markup));
  form.set('photo', new Blob([bytes], {type:'image/png'}), 'card.png');
  const response = await fetcher(`https://api.telegram.org/bot${env.BOT_TOKEN}/sendPhoto`, {method:'POST', body:form});
  if (!response.ok) throw Error('telegram request failed');
  const json = await response.json();
  if (!json.ok) throw Error('telegram request rejected');
  return json.result;
}
async function api(env, method, data, fetcher) {
  // Never log response bodies or URLs: the token is part of the URL.
  const response = await fetcher(`https://api.telegram.org/bot${env.BOT_TOKEN}/${method}`, {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(data)});
  if (!response.ok) throw Error('telegram request failed');
  const json = await response.json();
  if (!json.ok) throw Error('telegram request rejected');
  return json.result;
}
async function intake(request, env, fetcher) {
  if (!equal(request.headers.get('authorization'), `Bearer ${env.INTAKE_SECRET}`)) return result(403, 'Forbidden');
  let draft; try { draft = await body(request); } catch { return result(400, 'Invalid request'); }
  if (!validDraft(draft)) return result(400, 'Invalid draft');
  let card = null;
  if (draft.card_base64 !== undefined) {
    try { card = decodeCard(draft.card_base64); } catch { return result(400, 'Invalid card'); }
    // Both the review and channel captions must fit Telegram's 1024-character limit.
    if ((reviewPrefix + postText(draft)).length > 1024) return result(400, 'Caption too long');
  }
  const id = crypto.randomUUID();
  // Unique source URL deliberately blocks duplicate intake, including failed/uncertain attempts.
  try {
    const inserted = await env.DB.prepare("INSERT INTO drafts (id, source_url, text, state, created_at) VALUES (?, ?, ?, 'notifying', ?)").bind(id, draft.source_url, draft.text.trim(), new Date().toISOString()).run();
    if (!inserted.success) throw Error('insert');
  } catch { return result(409, 'Draft not created; check source and storage'); }
  try {
    const markup = {inline_keyboard:[[{text:'✅ Одобрить', callback_data:`approve:${id}`},{text:'✖️ Отклонить', callback_data:`reject:${id}`}]]};
    const sent = card
      ? await sendPhoto(env, {chat_id:env.REVIEWER_ID, caption:reviewPrefix + postText(draft), reply_markup:markup}, card, fetcher)
      : await api(env, 'sendMessage', {chat_id:env.REVIEWER_ID, text:reviewPrefix + postText(draft), reply_markup:markup}, fetcher);
    if (!Number.isSafeInteger(sent?.message_id)) throw Error('invalid message id');
    const photoId = card ? sent?.photo?.at(-1)?.file_id : null;
    if (card && (typeof photoId !== 'string' || !photoId || photoId.length > 512)) throw Error('invalid photo id');
    const update = await env.DB.prepare("UPDATE drafts SET state = 'ready', review_message_id = ?, photo_file_id = ? WHERE id = ? AND state = 'notifying'").bind(sent.message_id,photoId,id).run();
    if (!changes(update)) throw Error('state update');
    return result(201, 'Draft queued');
  } catch {
    // Do not retry notification blindly: Telegram may have accepted it.
    return result(503, 'Notification or state uncertain; operator review required');
  }
}
async function webhook(request, env, fetcher) {
  if (!equal(request.headers.get('x-telegram-bot-api-secret-token'), env.WEBHOOK_SECRET)) return result(403, 'Forbidden');
  let update; try { update = await body(request); } catch { return result(400, 'Invalid request'); }
  const cb = update?.callback_query;
  if (!cb || typeof cb.id !== 'string' || cb.id.length > 256 || String(cb.from?.id) !== env.REVIEWER_ID || cb.message?.chat?.type !== 'private' || String(cb.message?.chat?.id) !== env.REVIEWER_ID || !Number.isSafeInteger(cb.message?.message_id) || typeof cb.data !== 'string') return result(200, 'Ignored');
  const match = /^(approve|reject):([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$/i.exec(cb.data);
  if (!match) return result(200, 'Ignored');
  const [, action, id] = match;
  // A single conditional transition prevents duplicate button clicks and stale messages.
  const next = action === 'approve' ? 'sending' : 'rejected';
  let locked;
  try { locked = await env.DB.prepare("UPDATE drafts SET state = ? WHERE id = ? AND state = 'ready' AND review_message_id = ?").bind(next, id, cb.message.message_id).run(); }
  catch { return result(503, 'Storage unavailable'); }
  if (!changes(locked)) {
    try { await api(env, 'answerCallbackQuery', {callback_query_id: cb.id, text:'Уже обработано или недоступно'}, fetcher); } catch {}
    return result(200, 'Already processed');
  }
  if (action === 'reject') {
    try { await api(env, 'answerCallbackQuery', {callback_query_id:cb.id, text:'Черновик отклонён'}, fetcher); } catch {}
    return result(200, 'Rejected');
  }
  try {
    const row = await env.DB.prepare("SELECT text, source_url, photo_file_id FROM drafts WHERE id = ? AND state = 'sending'").bind(id).first();
    if (!validDraft(row)) throw Error('invalid stored draft');
    if (row.photo_file_id !== null && row.photo_file_id !== undefined && (typeof row.photo_file_id !== 'string' || !row.photo_file_id || row.photo_file_id.length > 512 || postText(row).length > 1024)) throw Error('invalid stored photo');
    const posted = row.photo_file_id
      ? await api(env, 'sendPhoto', {chat_id:env.CHANNEL_ID, photo:row.photo_file_id, caption:postText(row)}, fetcher)
      : await api(env, 'sendMessage', {chat_id:env.CHANNEL_ID, text:postText(row)}, fetcher);
    if (!Number.isSafeInteger(posted?.message_id)) throw Error('invalid message id');
    const saved = await env.DB.prepare("UPDATE drafts SET state = 'sent', channel_message_id = ? WHERE id = ? AND state = 'sending'").bind(posted.message_id,id).run();
    if (!changes(saved)) throw Error('state update');
    try { await api(env, 'answerCallbackQuery', {callback_query_id:cb.id, text:'Опубликовано'}, fetcher); } catch {}
    return result(200, 'Sent');
  } catch {
    // Any failure after locking may have delivered. Remain in sending for manual reconciliation.
    try { await api(env, 'answerCallbackQuery', {callback_query_id:cb.id, text:'Результат неизвестен. Проверьте канал.'}, fetcher); } catch {}
    return result(200, 'Needs reconciliation');
  }
}
export async function handle(request, env, fetcher = fetch) {
  if (!configured(env)) return result(503, 'Not configured');
  if (request.method !== 'POST') return result(405, 'Method not allowed');
  const url = new URL(request.url);
  try {
    if (url.pathname === '/intake') return await intake(request, env, fetcher);
    if (url.pathname === '/telegram') return await webhook(request, env, fetcher);
    return result(404, 'Not found');
  } catch { return result(503, 'Service unavailable'); }
}
export default {fetch(request, env) { return handle(request, env); }};
