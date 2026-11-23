// Pure policy only: this module makes no network or database calls and is not
// connected to the live review bot. Webhook authentication is required upstream.
const id = value => Number.isSafeInteger(value) && value > 0 ? String(value) : null;

export function subscriptionIntent(update) {
  const message = update?.message;
  if (!message || message.chat?.type !== 'private' || message.from?.is_bot || !id(message.chat?.id) || id(message.from?.id) !== id(message.chat?.id) || typeof message.text !== 'string') return null;
  // /start explains the service but is deliberately not a subscription.
  const command = message.text.trim();
  if (command === '/start') return {action:'info', chatId:id(message.chat.id)};
  if (command === '/subscribe') return {action:'subscribe', chatId:id(message.chat.id)};
  if (command === '/stop' || command === '/unsubscribe') return {action:'unsubscribe', chatId:id(message.chat.id)};
  return null;
}

export function eligibleDeliveries(draft, subscribers, destinations) {
  if (!draft || draft.state !== 'sent' || typeof draft.id !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(draft.id)) throw Error('Only a recorded approved and published draft may be distributed');
  if (!Array.isArray(subscribers) || !Array.isArray(destinations)) throw Error('Invalid recipients');
  const result = [], seen = new Set();
  for (const row of subscribers) {
    if (row?.active !== 1 || typeof row.chat_id !== 'string' || !/^[1-9]\d{0,19}$/.test(row.chat_id)) continue;
    const key = `subscriber:${row.chat_id}`;
    if (!seen.has(key)) { seen.add(key); result.push({type:'subscriber',id:row.chat_id}); }
  }
  for (const row of destinations) {
    // Negative chat IDs distinguish groups/channels from private users. A configured
    // destination is not proof of permission or current Telegram admin rights.
    if (row?.enabled !== 1 || !['group','channel'].includes(row.kind) || typeof row.chat_id !== 'string' || !/^-[1-9]\d{0,19}$/.test(row.chat_id)) continue;
    const key = `destination:${row.chat_id}`;
    if (!seen.has(key)) { seen.add(key); result.push({type:'destination',id:row.chat_id}); }
  }
  return result;
}
