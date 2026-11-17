// Create a separate, explicitly human-reviewed gallery item offline. Never sends anything.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {buildPayload, attachCard} from './drafts.mjs';

async function readLimited(file, limit) {
  const stat = await fs.stat(file);
  if (!stat.isFile() || stat.size > limit) throw Error('Файл отсутствует или слишком велик');
  const data = await fs.readFile(file);
  if (data.length > limit) throw Error('Файл слишком велик');
  return data;
}
const utf8 = bytes => new TextDecoder('utf-8', {fatal:true}).decode(bytes);

export async function prepareReviewed(source, number, commentFile, destination, options = {}) {
  if (options.confirmChecked !== true) throw Error('Нужно явно подтвердить проверку источника, текста, прав и карточки');
  if (typeof source !== 'string' || !source || typeof commentFile !== 'string' || !commentFile || typeof destination !== 'string' || !destination || !Number.isInteger(number) || number < 1 || number > 20) throw Error('Некорректные параметры');
  const index = String(number).padStart(2, '0');
  const [json, card, commentary] = await Promise.all([
    readLimited(path.join(source, `draft-${index}.json`), 16000),
    readLimited(path.join(source, `card-${index}.png`), 180000),
    readLimited(commentFile, 8000),
  ]);
  const original = JSON.parse(utf8(json));
  if (!original || original.version !== 1 || original.ready_for_review !== false || original.comment !== '') throw Error('Ожидается неподтверждённый исходный черновик без комментария');
  const comment = utf8(commentary).trim();
  if (!comment || comment.length > 1000) throw Error('Нужен непустой авторский вывод длиной до 1000 символов');
  const reviewed = {...original, comment, ready_for_review:true};
  // Validate the exact payload and PNG before creating anything; this does not verify facts or rights.
  const payload = buildPayload(reviewed);
  attachCard(payload, card, reviewed);
  const encoded = Buffer.from(JSON.stringify(reviewed, null, 2) + '\n', 'utf8');
  if (encoded.length > 16000) throw Error('Черновик слишком велик');
  // Only a new directory is accepted. A failure during writes may leave a partial directory.
  await fs.mkdir(destination, {mode:0o700});
  await fs.writeFile(path.join(destination, 'card-01.png'), card, {flag:'wx',mode:0o600});
  await fs.writeFile(path.join(destination, 'draft-01.json'), encoded, {flag:'wx',mode:0o600});
  return {number:1};
}
async function main(args) {
  if (args.length !== 5 || !/^\d{1,2}$/.test(args[1]) || args[4] !== '--confirm-checked') throw Error('Нужны исходная галерея, номер, файл вывода, новый каталог и --confirm-checked');
  await prepareReviewed(args[0], Number(args[1]), args[2], args[3], {confirmChecked:true});
  console.log('Создана отдельная проверенная заготовка №1. В Telegram ничего не отправлено.');
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).catch(error=>{console.error(`Не выполнено: ${error.message}. Если новый каталог появился, проверьте его вручную.`);process.exitCode=1;});
}
