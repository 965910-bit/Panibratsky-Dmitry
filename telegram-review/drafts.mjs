// Local preparation and explicit submission. Never publishes to the channel directly.
import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

const scrub = (v, max) => (typeof v === 'string' ? v : '').replace(/<[^>]*>/g, ' ').replace(/[\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, max);
function link(value) {
  try { const u = new URL(value); return ['http:', 'https:'].includes(u.protocol) && !!u.hostname && !u.username && !u.password && u.href.length <= 2048 ? u.href : ''; } catch { return ''; }
}
export function prepareDraft(item) {
  if (!item || item.dead || !link(item.link)) throw Error('Новость недоступна или ссылка некорректна');
  const title = scrub(item.title, 240), description = scrub(item.description, 450), source = scrub(item.source, 100);
  if (!title || /^оповещение google\s*[–—-]/iu.test(title)) throw Error('Нужен реальный заголовок материала, а не тема оповещения');
  return {
    version: 1,
    // Must be deliberately set after reviewing and editing the file.
    ready_for_review: false,
    title,
    description,
    source_name: source,
    source_url: link(item.link),
    comment: '',
  };
}
export function buildPayload(draft) {
  if (!draft || draft.version !== 1 || draft.ready_for_review !== true) throw Error('Подтвердите готовность черновика к проверке в Telegram');
  const source = link(draft.source_url);
  const title = scrub(draft.title, 240), description = scrub(draft.description, 450), sourceName = scrub(draft.source_name, 100), comment = scrub(draft.comment, 1000);
  if (!source || !title || !comment || /^оповещение google\s*[–—-]/iu.test(title)) throw Error('Нужны заголовок, источник и собственный комментарий');
  const text = [`📦 ${title}`, description && `📰 ${description}`, `💬 Вывод\n${comment}`, sourceName && `Источник: ${sourceName}`].filter(Boolean).join('\n\n');
  if (text.length > 3000 || text.length + source.length > 3800) throw Error('Черновик превышает допустимую длину');
  return {text, source_url: source};
}
export function endpoint(value) {
  let url; try { url = new URL(value); } catch { throw Error('Некорректный адрес Worker'); }
  if (url.protocol !== 'https:' || !url.hostname.endsWith('.workers.dev') || url.hostname === '.workers.dev' || url.username || url.password || url.port || url.search || url.hash || url.pathname !== '/intake') throw Error('Ожидается HTTPS-адрес workers.dev с путём /intake без параметров');
  return url.href;
}
export function attachCard(payload, bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.length < 33 || bytes.length > 180000) throw Error('PNG должен быть не больше 180000 байт');
  const png = Buffer.from(bytes);
  const signature = Buffer.from([137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82]);
  if (!png.subarray(0, 16).equals(signature) || png.readUInt32BE(16) !== 1080 || png.readUInt32BE(20) !== 1080) throw Error('Ожидается карточка PNG 1080×1080');
  if ((`ЧЕРНОВИК · проверьте источник и текст\n\n${payload.text}\n\nИсточник: ${payload.source_url}`).length > 1024) throw Error('Текст вместе со ссылкой слишком длинный для подписи к изображению; сократите его вручную');
  return {...payload, card_base64:png.toString('base64')};
}
export async function submit(draft, options = {}) {
  const url = endpoint(options.url), secret = options.secret;
  if (typeof secret !== 'string' || !/^[A-Za-z0-9_-]{32,256}$/.test(secret)) throw Error('Не задан корректный секрет приёма');
  const plain = buildPayload(draft);
  const payload = options.card ? attachCard(plain, options.card) : plain;
  // No retries: a timeout or error may occur after the Worker received the draft.
  const response = await (options.fetcher || fetch)(url, {
    method:'POST', headers:{'content-type':'application/json', 'authorization':`Bearer ${secret}`},
    body:JSON.stringify(payload), redirect:'error', signal:AbortSignal.timeout(15000),
  });
  if (response.status !== 201) throw Error(`Сервис ответил ${response.status}; не повторяйте без проверки очереди и личного чата`);
  return true;
}
async function main(args) {
  if (args[0] === 'list' && args.length === 1) {
    const news = JSON.parse(await fs.readFile(new URL('../data/news.json', import.meta.url), 'utf8'));
    if (!Array.isArray(news)) throw Error('Лента повреждена');
    // Indexes refer to the current snapshot; the journal is deliberately not assumed available.
    for (const [index, item] of news.entries()) {
      try { const d = prepareDraft(item); console.log(`${index} · ${d.title} · ${d.source_name || 'источник не указан'}`); } catch {}
    }
    console.log('Это не журнал отправок: записи могут уже быть опубликованы.'); return;
  }
  if (args[0] === 'prepare' && args.length === 3 && /^\d+$/.test(args[1])) {
    const news = JSON.parse(await fs.readFile(new URL('../data/news.json', import.meta.url), 'utf8'));
    if (!Array.isArray(news)) throw Error('Лента повреждена');
    const draft = prepareDraft(news[Number(args[1])]);
    await fs.writeFile(args[2], JSON.stringify(draft, null, 2) + '\n', {encoding:'utf8', flag:'wx', mode:0o600});
    console.log('Черновик создан локально. Проверьте источник, исправьте текст и добавьте комментарий.'); return;
  }
  if (args[0] === 'submit' && (args.length === 2 || (args.length === 4 && args[2] === '--card'))) {
    const draft = JSON.parse(await fs.readFile(args[1], 'utf8'));
    let card;
    if (args.length === 4) {
      const stat = await fs.stat(args[3]);
      if (!stat.isFile() || stat.size > 180000) throw Error('PNG должен быть обычным файлом до 180000 байт');
      card = await fs.readFile(args[3]);
    }
    try { await submit(draft, {url:process.env.REVIEW_INTAKE_URL, secret:process.env.REVIEW_INTAKE_SECRET, card}); }
    catch (e) {
      // Do not display raw network errors, which can include request information.
      if (e?.name === 'AbortError' || e?.name === 'TimeoutError' || e instanceof TypeError) throw Error('Сетевой результат неизвестен; проверьте очередь и личный чат, не отправляйте повторно');
      throw e;
    }
    console.log('Черновик передан в очередь. Публикация в канал требует отдельного подтверждения в Telegram.'); return;
  }
  throw Error('Используйте list, prepare <номер в ленте с нуля> <новый файл> или submit <файл> [--card <png>]');
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).catch(e => { console.error(`Не выполнено: ${e.message}`); process.exitCode = 1; });
}
