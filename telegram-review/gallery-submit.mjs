// One explicit gallery draft to private review; publication still requires Telegram approval.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {buildPayload, attachCard, submit} from './drafts.mjs';

export async function sendGalleryItem(directory, number, options = {}) {
  if (typeof directory !== 'string' || !directory || !Number.isInteger(number) || number < 1 || number > 20) throw Error('Укажите каталог и номер от 1 до 20');
  const prefix = String(number).padStart(2, '0');
  const draftPath = path.join(directory, `draft-${prefix}.json`);
  const cardPath = path.join(directory, `card-${prefix}.png`);
  const [draftStat, cardStat] = await Promise.all([fs.stat(draftPath), fs.stat(cardPath)]);
  if (!draftStat.isFile() || draftStat.size > 16000 || !cardStat.isFile() || cardStat.size > 180000) throw Error('Недопустимый размер черновика или карточки');
  const draft = JSON.parse(await fs.readFile(draftPath, 'utf8'));
  const card = await fs.readFile(cardPath);
  // Reuse every check in the original client, even for offline previews.
  const payload = buildPayload(draft);
  attachCard(payload, card, draft);
  if (options.send !== true) return {sent:false, text:payload.text, source_url:payload.source_url};
  await submit(draft, {url:options.url, secret:options.secret, card, fetcher:options.fetcher});
  return {sent:true};
}
async function main(args) {
  if ((args.length !== 2 && args.length !== 3) || !/^\d{1,2}$/.test(args[1]) || (args.length === 3 && args[2] !== '--send')) throw Error('Используйте <каталог> <номер> [--send]');
  const output = await sendGalleryItem(args[0], Number(args[1]), {send:args[2] === '--send', url:process.env.REVIEW_INTAKE_URL, secret:process.env.REVIEW_INTAKE_SECRET});
  if (output.sent) console.log('Отправлено в личную очередь на согласование; в канал без кнопки не публикуется.');
  else console.log(JSON.stringify({preview:true, ...output}, null, 2));
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).catch(error => {
    // Do not print network failures, paths or request details which could contain sensitive data.
    if (error?.name === 'AbortError' || error?.name === 'TimeoutError' || error instanceof TypeError) console.error('Результат неизвестен. Проверьте чат и /status, не отправляйте повторно вслепую.');
    else if (/сервис ответил/i.test(error?.message || '')) console.error('Результат отправки не подтверждён. Проверьте чат и /status, не отправляйте повторно вслепую.');
    else console.error('Не выполнено: проверьте черновик, карточку, настройки и /status.');
    process.exitCode = 1;
  });
}
