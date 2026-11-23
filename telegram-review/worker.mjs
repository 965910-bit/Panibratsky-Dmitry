import {subscriptionIntent} from './audience-policy.mjs';
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
async function intake(request, env, fetcher, telegramPhoto = null) {
  if (!equal(request.headers.get('authorization'), `Bearer ${env.INTAKE_SECRET}`)) return result(403, 'Forbidden');
  let draft; try { draft = await body(request); } catch { return result(400, 'Invalid request'); }
  if (!validDraft(draft)) return result(400, 'Invalid draft');
  let card = null;
  if (telegramPhoto !== null && (typeof telegramPhoto !== 'string' || !telegramPhoto || telegramPhoto.length > 512)) return result(400, 'Invalid card');
  if (draft.card_base64 !== undefined && telegramPhoto !== null) return result(400, 'Invalid card');
  if (draft.card_base64 !== undefined) {
    try { card = decodeCard(draft.card_base64); } catch { return result(400, 'Invalid card'); }
  }
  // Both the review and channel captions must fit Telegram's 1024-character limit.
  if ((card || telegramPhoto) && (reviewPrefix + postText(draft)).length > 1024) return result(400, 'Caption too long');
  const id = crypto.randomUUID();
  // Unique source URL deliberately blocks duplicate intake, including failed/uncertain attempts.
  try {
    // All intake paths share one atomic gate, including private /draft.
    const sql = "INSERT INTO drafts (id, source_url, text, state, created_at) SELECT ?, ?, ?, 'notifying', ? WHERE NOT EXISTS (SELECT 1 FROM drafts WHERE state IN ('notifying', 'ready', 'sending'))";
    const inserted = await env.DB.prepare(sql).bind(id, draft.source_url, draft.text.trim(), new Date().toISOString()).run();
    if (!inserted.success || changes(inserted) !== 1) throw Error('insert');
  } catch { return result(409, 'Draft not created; check source and storage'); }
  try {
    const markup = {inline_keyboard:[[{text:'✅ Одобрить', callback_data:`approve:${id}`},{text:'✖️ Отклонить', callback_data:`reject:${id}`}]]};
    const sent = card
      ? await sendPhoto(env, {chat_id:env.REVIEWER_ID, caption:reviewPrefix + postText(draft), reply_markup:markup}, card, fetcher)
      : telegramPhoto
        ? await api(env, 'sendPhoto', {chat_id:env.REVIEWER_ID, photo:telegramPhoto, caption:reviewPrefix + postText(draft), reply_markup:markup}, fetcher)
        : await api(env, 'sendMessage', {chat_id:env.REVIEWER_ID, text:reviewPrefix + postText(draft), reply_markup:markup}, fetcher);
    if (!Number.isSafeInteger(sent?.message_id)) throw Error('invalid message id');
    const photoId = (card || telegramPhoto) ? sent?.photo?.at(-1)?.file_id : null;
    if ((card || telegramPhoto) && (typeof photoId !== 'string' || !photoId || photoId.length > 512)) throw Error('invalid photo id');
    const update = await env.DB.prepare("UPDATE drafts SET state = 'ready', review_message_id = ?, photo_file_id = ? WHERE id = ? AND state = 'notifying'").bind(sent.message_id,photoId,id).run();
    if (!changes(update)) throw Error('state update');
    return result(201, 'Draft queued');
  } catch {
    // Do not retry notification blindly: Telegram may have accepted it.
    return result(503, 'Notification or state uncertain; operator review required');
  }
}
// Read-only, authenticated preflight for a future automated producer.
// This is advisory: unique INSERT and uncertain-state handling remain authoritative.
async function availability(request, env) {
  if (!equal(request.headers.get('authorization'), `Bearer ${env.INTAKE_SECRET}`)) return result(403, 'Forbidden');
  let data; try { data = await body(request); } catch { return result(400, 'Invalid request'); }
  const urls = data?.source_urls;
  if (!Array.isArray(urls) || urls.length < 1 || urls.length > 20 || !urls.every(source_url => validDraft({source_url, text:'x'}))) return result(400, 'Invalid sources');
  try {
    const counts = await env.DB.prepare("SELECT state, COUNT(*) AS count FROM drafts GROUP BY state").all();
    const query = `SELECT source_url FROM drafts WHERE source_url IN (${urls.map(() => '?').join(',')})`;
    const matches = await env.DB.prepare(query).bind(...urls).all();
    if (!counts.success || !matches.success || !Array.isArray(counts.results) || !Array.isArray(matches.results)) throw Error('storage');
    const totals = {ready:0, notifying:0, sending:0, sent:0, rejected:0};
    for (const row of counts.results) {
      if (!Object.hasOwn(totals, row.state) || !Number.isSafeInteger(row.count) || row.count < 0) throw Error('storage');
      totals[row.state] = row.count;
    }
    const seen = new Set();
    for (const row of matches.results) {
      if (typeof row.source_url !== 'string' || !urls.includes(row.source_url)) throw Error('storage');
      seen.add(row.source_url);
    }
    return new Response(JSON.stringify({known:urls.map(url=>seen.has(url)), pending:totals.ready, uncertain:totals.notifying + totals.sending}), {status:200,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff'}});
  } catch { return result(503, 'Storage unavailable'); }
}
async function statusReply(message, env, fetcher) {
  if (message?.text !== '/status' || message?.chat?.type !== 'private' || String(message?.from?.id) !== env.REVIEWER_ID || String(message?.chat?.id) !== env.REVIEWER_ID) return false;
  let text;
  try {
    const counts = await env.DB.prepare('SELECT state, COUNT(*) AS count FROM drafts GROUP BY state').all();
    const pending = await env.DB.prepare("SELECT id, state, created_at FROM drafts WHERE state IN ('notifying', 'sending') ORDER BY created_at ASC LIMIT 5").all();
    if (!counts.success || !pending.success || !Array.isArray(counts.results) || !Array.isArray(pending.results)) throw Error('invalid status');
    const totals = {ready:0, notifying:0, sending:0, sent:0, rejected:0};
    for (const row of counts.results) {
      if (!Object.hasOwn(totals, row.state) || !Number.isSafeInteger(row.count) || row.count < 0) throw Error('invalid count');
      totals[row.state] = row.count;
    }
    const items = pending.results.map(row => {
      if (!/^[0-9a-f-]{36}$/i.test(row.id) || !['notifying','sending'].includes(row.state) || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(row.created_at)) throw Error('invalid row');
      return `• ${row.id} · ${row.state} · ${row.created_at}`;
    });
    text = [`Очередь публикаций`, `Ожидают вашего решения: ${totals.ready}`, `Доставляются на проверку или требуют сверки: ${totals.notifying}`, `Публикуются или требуют сверки: ${totals.sending}`, `Отправлено по журналу: ${totals.sent}`, `Отклонено: ${totals.rejected}`, '', 'Notifying / sending могут быть ещё в работе. Если состояние не меняется, проверьте личный чат, канал и журнал; не повторяйте отправку вслепую.', ...(items.length ? ['', 'До 5 старейших записей:', ...items] : []), '', 'Показан только журнал: это не подтверждение доставки в Telegram.'].join('\n');
  } catch {
    text = 'Не удалось прочитать журнал очереди. Не повторяйте отправку вслепую; проверьте состояние сервиса и канал.';
  }
  try { await api(env, 'sendMessage', {chat_id:env.REVIEWER_ID, text}, fetcher); } catch { /* A manual status request is safe to repeat. */ }
  return true;
}
async function inspectReply(message, env, fetcher) {
  if (message?.chat?.type !== 'private' || String(message?.from?.id) !== env.REVIEWER_ID || String(message?.chat?.id) !== env.REVIEWER_ID || typeof message?.text !== 'string') return false;
  const match = /^\/inspect ([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$/i.exec(message.text);
  if (!match) return false;
  let text;
  try {
    const row = await env.DB.prepare('SELECT state, created_at, text, source_url, review_message_id, channel_message_id FROM drafts WHERE id = ?').bind(match[1]).first();
    if (!row) text = 'Запись не найдена. Не повторяйте отправку без проверки журнала и канала.';
    else {
      if (!validDraft(row) || !['notifying','ready','sending','sent','rejected'].includes(row.state) || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(row.created_at) || ![row.review_message_id, row.channel_message_id].every(v => v == null || (Number.isSafeInteger(v) && v > 0))) throw Error('invalid row');
      // Bound response size and strip controls; no parse_mode or preview of links.
      const safe = value => value.replace(/[\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]/g, ' ');
      const excerpt = safe(row.text).slice(0, 1000);
      const source = safe(row.source_url).slice(0, 1800);
      text = [`Запись: ${match[1]}`, `Состояние в журнале: ${row.state}`, `Создана: ${row.created_at}`, `ID сообщения редактору: ${row.review_message_id ?? 'нет в журнале'}`, `ID сообщения канала: ${row.channel_message_id ?? 'нет в журнале'}`, '', `Текст (фрагмент): ${excerpt}${row.text.length > 1000 ? '…' : ''}`, `Источник: ${source}${row.source_url.length > 1800 ? '…' : ''}`, '', 'Это сведения журнала, не подтверждение доставки. Проверьте чат и канал. Запись не изменена.'].join('\n');
    }
  } catch { text = 'Не удалось прочитать запись. Проверьте состояние сервиса; не повторяйте публикацию вслепую.'; }
  try { await api(env, 'sendMessage', {chat_id:env.REVIEWER_ID, text, disable_web_page_preview:true}, fetcher); } catch { /* Read-only command can be requested again. */ }
  return true;
}
// Manual, explicit reconciliation is deliberately one-way. It cannot send to
// a channel, delete records, make a draft ready or retry an ambiguous send.
// The reviewer must verify Telegram independently before attesting delivery.
async function reconcileReply(message, env, fetcher) {
  if (message?.chat?.type !== 'private' || String(message?.from?.id) !== env.REVIEWER_ID || String(message?.chat?.id) !== env.REVIEWER_ID || typeof message?.text !== 'string') return false;
  if (!/^\/reconcile(?:\s|$)/.test(message.text)) return false;
  const pattern = /^\/reconcile ([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}) (?:published ([1-9]\d{0,15})|discard-review) CONFIRM$/i;
  const match = pattern.exec(message.text);
  let text = 'Формат: /reconcile ID published НОМЕР_СООБЩЕНИЯ CONFIRM или /reconcile ID discard-review CONFIRM. Сначала дождитесь завершения операции и проверьте /inspect, личный чат и канал. Ничего не переотправляется.';
  if (match) {
    const id = match[1], confirmedMessage = match[2] === undefined ? null : Number(match[2]);
    if (confirmedMessage !== null && (!Number.isSafeInteger(confirmedMessage) || confirmedMessage < 1)) {
      text = 'Некорректный номер сообщения. Запись не изменена.';
    } else {
      try {
        const at = new Date().toISOString();
        const changed = confirmedMessage !== null
          ? await env.DB.prepare("UPDATE drafts SET state = 'sent', channel_message_id = ?, resolution_kind = 'confirmed_channel_message', resolved_at = ? WHERE id = ? AND state = 'sending' AND channel_message_id IS NULL AND resolution_kind IS NULL AND resolved_at IS NULL").bind(confirmedMessage, at, id).run()
          : await env.DB.prepare("UPDATE drafts SET state = 'rejected', resolution_kind = 'abandoned_review', resolved_at = ? WHERE id = ? AND state = 'notifying' AND resolution_kind IS NULL AND resolved_at IS NULL").bind(at, id).run();
        if (!changed.success) throw Error('storage');
        text = changes(changed) === 1
          ? confirmedMessage !== null
            ? 'Журнал помечен как отправленный по вашему подтверждению. Бот не проверял канал и не отправлял сообщение. Повторная отправка не выполнялась.'
            : 'Неопределённый черновик отклонён в журнале. Повторной отправки не было; тот же URL останется заблокированным.'
          : 'Запись не изменена: состояние уже изменилось, ID не найден или операция недоступна. Проверьте /status и /inspect; не повторяйте отправку.';
      } catch {
        text = 'Не удалось подтвердить изменение журнала. Проверьте /status, /inspect и наличие миграции; не повторяйте отправку.';
      }
    }
  }
  try { await api(env, 'sendMessage', {chat_id:env.REVIEWER_ID, text, disable_web_page_preview:true}, fetcher); } catch { /* The state change may have succeeded; check /status and /inspect. */ }
  return true;
}
async function draftReply(message, env, fetcher) {
  if (message?.chat?.type !== 'private' || String(message?.from?.id) !== env.REVIEWER_ID || String(message?.chat?.id) !== env.REVIEWER_ID) return false;
  const isPhoto = Array.isArray(message?.photo);
  const content = isPhoto ? message.caption : message.text;
  if (typeof content !== 'string' || !/^\/draft(?:\s|$)/.test(content)) return false;
  const match = /^\/draft[ \t]+([^\s]+)\r?\n([\s\S]+)$/.exec(content);
  // Reject albums and invalid image identifiers rather than silently creating a partial post.
  const photoId = isPhoto ? message.photo.at(-1)?.file_id : null;
  const photoValid = !isPhoto || (!message.media_group_id && typeof photoId === 'string' && photoId.length > 0 && photoId.length <= 512);
  let resultCode = 400;
  if (match && photoValid) {
    // Internal call reuses the same validator, journal and duplicate protection as the CLI.
    // Never expose the intake secret or post to the channel here.
    const request = new Request('https://internal.invalid/intake', {
      method:'POST', headers:{'content-type':'application/json', authorization:`Bearer ${env.INTAKE_SECRET}`},
      body:JSON.stringify({source_url:match[1], text:match[2]})
    });
    resultCode = (await intake(request, env, fetcher, photoId)).status;
  }
  if (resultCode !== 201) {
    const text = resultCode === 400
      ? 'Формат: /draft ССЫЛКА на первой строке, затем с новой строки — подготовленный текст. Для изображения отправьте одно фото с этой подписью; проверьте ссылку и длину текста.'
      : 'Не удалось подтвердить создание черновика. Проверьте личный чат и /status; не отправляйте повторно вслепую: запись могла сохраниться.';
    try { await api(env, 'sendMessage', {chat_id:env.REVIEWER_ID, text, disable_web_page_preview:true}, fetcher); } catch {}
  }
  return true;
}
// Disabled unless explicitly configured after migration and isolated testing.
// The webhook secret must already have been verified before entering this function.
async function audienceReply(update, env, fetcher) {
  if (env.AUDIENCE_ENABLED !== 'true') return false;
  const intent = subscriptionIntent(update);
  if (!intent || !Number.isSafeInteger(update.update_id) || update.update_id < 0) return false;
  let text;
  if (intent.action === 'info') {
    text = 'Рассылка Дмитрия Герасимова: материалы о логистике, SCM и управлении. Для добровольной подписки отправьте /subscribe. Остановить рассылку: /stop. Для работы хранится идентификатор чата и статус подписки.';
  } else {
    const active = intent.action === 'subscribe' ? 1 : 0;
    const now = new Date().toISOString();
    // Telegram may randomize update_id after a week without updates. An old
    // per-chat watermark expires after seven days; Telegram does not retain
    // undelivered updates indefinitely.
    const resetBefore = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
    // Atomically ignore duplicates and older updates, including delayed unsubscribe/subscribe retries.
    const sql = `INSERT INTO audience_subscribers (chat_id, subscribed_at, updated_at, active, last_update_id)
      VALUES (?, ?, ?, ?, ?) ON CONFLICT(chat_id) DO UPDATE SET
      subscribed_at = CASE WHEN excluded.active = 1 AND audience_subscribers.active = 0 THEN excluded.subscribed_at ELSE audience_subscribers.subscribed_at END,
      updated_at = excluded.updated_at, active = excluded.active, last_update_id = excluded.last_update_id
      WHERE excluded.last_update_id > audience_subscribers.last_update_id OR audience_subscribers.updated_at < ?`;
    const saved = await env.DB.prepare(sql).bind(intent.chatId,now,now,active,update.update_id,resetBefore).run();
    if (!saved.success) throw Error('subscription storage unavailable');
    if (!changes(saved)) return true;
    text = active ? 'Вы подписались на материалы о логистике и SCM. Остановить рассылку можно командой /stop.' : 'Подписка отключена. Новые рассылки получать не будете. Включить снова: /subscribe.';
  }
  // A failed acknowledgement does not roll back consent or justify a blind retry.
  try { await api(env,'sendMessage',{chat_id:intent.chatId,text,disable_web_page_preview:true},fetcher); } catch {}
  return true;
}
async function webhook(request, env, fetcher) {
  if (!equal(request.headers.get('x-telegram-bot-api-secret-token'), env.WEBHOOK_SECRET)) return result(403, 'Forbidden');
  let update; try { update = await body(request); } catch { return result(400, 'Invalid request'); }
  if (await audienceReply(update, env, fetcher)) return result(200, 'Subscription processed');
  if (await statusReply(update?.message, env, fetcher)) return result(200, 'Status processed');
  if (await inspectReply(update?.message, env, fetcher)) return result(200, 'Inspection processed');
  if (await reconcileReply(update?.message, env, fetcher)) return result(200, 'Reconciliation processed');
  if (await draftReply(update?.message, env, fetcher)) return result(200, 'Draft processed');
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
    if (url.pathname === '/availability') return await availability(request, env);
    if (url.pathname === '/intake') return await intake(request, env, fetcher);
    if (url.pathname === '/intake-one') return await intake(request, env, fetcher);
    if (url.pathname === '/telegram') return await webhook(request, env, fetcher);
    return result(404, 'Not found');
  } catch { return result(503, 'Service unavailable'); }
}
export default {fetch(request, env) { return handle(request, env); }};
