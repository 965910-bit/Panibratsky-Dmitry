// Bounded queue producer for already human-checked gallery items; no scheduling.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {buildPayload, attachCard, endpoint, submit} from './drafts.mjs';

export async function queueOne(directory, options = {}) {
  if (options.send !== true) throw Error('Явное разрешение на отправку в очередь обязательно');
  if (typeof directory !== 'string' || !directory) throw Error('Нужен каталог галереи');
  const names = await fs.readdir(directory);
  const drafts = names.filter(name=>/^draft-(?:0[1-9]|1[0-9]|20)\.json$/.test(name)).sort();
  if (drafts.length > 20) throw Error('Слишком много записей');
  const ready = [];
  for (const name of drafts) {
    const file = path.join(directory,name), stat = await fs.stat(file);
    if (!stat.isFile() || stat.size > 16000) throw Error('Неверный файл');
    const draft = JSON.parse(await fs.readFile(file,'utf8'));
    if (draft?.ready_for_review !== true) continue;
    const payload = buildPayload(draft);
    const image = path.join(directory, name.replace(/^draft-/, 'card-').replace(/\.json$/, '.png'));
    const cardStat = await fs.stat(image);
    if (!cardStat.isFile() || cardStat.size > 180000) throw Error('Неверная карточка');
    const card = await fs.readFile(image);
    attachCard(payload, card, draft);
    ready.push({draft,card,source_url:payload.source_url});
  }
  if (!ready.length) return {status:'none-ready'};
  const url = endpoint(options.url), secret = options.secret;
  if (typeof secret !== 'string' || !/^[A-Za-z0-9_-]{32,256}$/.test(secret)) throw Error('Неверный секрет');
  const check = new URL(url); check.pathname = '/availability';
  const fetcher = options.fetcher || fetch;
  const response = await fetcher(check.href, {method:'POST', headers:{'content-type':'application/json',authorization:`Bearer ${secret}`}, body:JSON.stringify({source_urls:ready.map(item=>item.source_url)}), redirect:'error',signal:AbortSignal.timeout(15000)});
  if (response.status !== 200) throw Error('Проверка очереди недоступна');
  let state; try { state = await response.json(); } catch { throw Error('Некорректный ответ очереди'); }
  if (!state || !Array.isArray(state.known) || state.known.length !== ready.length || !state.known.every(x=>typeof x === 'boolean') || !Number.isSafeInteger(state.pending) || state.pending < 0 || !Number.isSafeInteger(state.uncertain) || state.uncertain < 0) throw Error('Некорректный ответ очереди');
  if (state.uncertain) return {status:'uncertain'};
  if (state.pending) return {status:'pending'};
  const index = state.known.indexOf(false);
  if (index === -1) return {status:'all-known'};
  // The distinct guarded endpoint performs an atomic check-and-insert. No retries.
  await submit(ready[index].draft, {url,secret,card:ready[index].card,fetcher,guarded:true});
  return {status:'queued'};
}
async function main(args) {
  if (args.length !== 2 || args[1] !== '--send-one') throw Error('Нужен каталог и явный --send-one');
  const result = await queueOne(args[0],{send:true,url:process.env.REVIEW_INTAKE_URL,secret:process.env.REVIEW_INTAKE_SECRET});
  console.log('Состояние очереди: '+result.status);
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).catch(()=>{console.error('Операция не подтверждена: проверьте личный чат и /status, не повторяйте вслепую.');process.exitCode=1;});
}
