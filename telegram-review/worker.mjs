// Cloudflare Worker: editorial approval only; no scheduled publishing.
const MAX_BODY = 16384;
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
  const id = crypto.randomUUID();
  // Unique source URL deliberately blocks duplicate intake, including failed/uncertain attempts.
  try {
    const inserted = await env.DB.prepare("INSERT INTO drafts (id, source_url, text, state, created_at) VALUES (?, ?, ?, 'notifying', ?)").bind(id, draft.source_url, draft.text.trim(), new Date().toISOString()).run();
    if (!inserted.success) throw Error('insert');
  } catch { return result(409, 'Draft not created; check source and storage'); }
  try {
    const sent = await api(env, 'sendMessage', {chat_id: env.REVIEWER_ID, text: `ЧЕРНОВИК · проверьте источник и текст\n\n${draft.text.trim()}\n\nИсточник: ${draft.source_url}`, reply_markup:{inline_keyboard:[[{text:'✅ Одобрить', callback_data:`approve:${id}`},{text:'✖️ Отклонить', callback_data:`reject:${id}`}]]}}, fetcher);
    if (!Number.isSafeInteger(sent?.message_id)) throw Error('invalid message id');
    const update = await env.DB.prepare("UPDATE drafts SET state = 'ready', review_message_id = ? WHERE id = ? AND state = 'notifying'").bind(sent.message_id,id).run();
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
    const row = await env.DB.prepare("SELECT text, source_url FROM drafts WHERE id = ? AND state = 'sending'").bind(id).first();
    if (!validDraft(row)) throw Error('invalid stored draft');
    const posted = await api(env, 'sendMessage', {chat_id: env.CHANNEL_ID, text:`${row.text}\n\nИсточник: ${row.source_url}`}, fetcher);
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
