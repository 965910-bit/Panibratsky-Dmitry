// A single bounded Telegram API call. Not connected to a worker or scheduler.
// Never log a URL, token, response body, recipient ID or text. The caller must
// enforce cross-instance rate limits and handle errors as uncertain delivery.
const MAX_REPLY = 8192;
async function readJson(response) {
  const reader = response.body?.getReader();
  if (!reader) throw Error('invalid reply');
  let size = 0; const parts = [];
  for (;;) {
    const {done,value} = await reader.read();
    if (done) break;
    size += value.length;
    if (size > MAX_REPLY) { await reader.cancel(); throw Error('reply too large'); }
    parts.push(value);
  }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const part of parts) { bytes.set(part, offset); offset += part.length; }
  return JSON.parse(new TextDecoder().decode(bytes));
}

export function createAudienceTransport(token, fetcher = fetch) {
  if (typeof token !== 'string' || !/^\d{1,20}:[A-Za-z0-9_-]{20,256}$/.test(token) || typeof fetcher !== 'function') throw Error('Invalid transport configuration');
  return async ({chatId,text,photoFileId} = {}) => {
    if (typeof chatId !== 'string' || !/^-?[1-9]\d{0,19}$/.test(chatId) || typeof text !== 'string' || !text.trim() || text.length > (photoFileId ? 1024 : 4096) || !(photoFileId == null || (typeof photoFileId === 'string' && photoFileId.length > 0 && photoFileId.length <= 512))) throw Error('Invalid delivery payload');
    const isPhoto = photoFileId != null;
    const data = isPhoto ? {chat_id:chatId,photo:photoFileId,caption:text} : {chat_id:chatId,text,disable_web_page_preview:true};
    try {
      const response = await fetcher(`https://api.telegram.org/bot${token}/${isPhoto ? 'sendPhoto' : 'sendMessage'}`, {
        method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify(data), redirect:'error', signal:AbortSignal.timeout(15000)
      });
      // Do not retry 429, other HTTP errors, malformed responses or timeouts.
      // The caller marks the result uncertain; no raw Telegram errors are exposed.
      if (!response.ok) throw Error('http error');
      const value = await readJson(response);
      if (value?.ok !== true || !Number.isSafeInteger(value.result?.message_id) || value.result.message_id <= 0) throw Error('invalid reply');
      return {message_id:value.result.message_id};
    } catch { throw Error('Telegram delivery not confirmed'); }
  };
}
