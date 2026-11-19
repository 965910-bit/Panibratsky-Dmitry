// Bounded queue producer for already human-checked gallery items; no scheduling.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {buildPayload, buildCandidatePayload, attachCard, endpoint, submit, submitCandidate} from './drafts.mjs';

async function responseJson(response) {
  const reader = response.body?.getReader();
  if (!reader) throw Error('Некорректный ответ очереди');
  let size = 0; const parts = [];
  for (;;) {
    const {done, value} = await reader.read();
    if (done) break;
    size += value.length;
    if (size > 8192) { await reader.cancel(); throw Error('Некорректный ответ очереди'); }
    parts.push(value);
  }
  try { return JSON.parse(Buffer.concat(parts.map(part=>Buffer.from(part))).toString('utf8')); }
  catch { throw Error('Некорректный ответ очереди'); }
}

async function inspect(directory, options, candidateMode = false) {
  if (typeof directory !== 'string' || !directory) throw Error('Нужен каталог галереи');
  const names = await fs.readdir(directory);
  const drafts = names.filter(name=>/^draft-(?:0[1-9]|1[0-9]|20)\.json$/.test(name)).sort();
  if (drafts.length > 20) throw Error('Слишком много записей');
  const ready = [];
  for (const name of drafts) {
    const file = path.join(directory,name), stat = await fs.stat(file);
    if (!stat.isFile() || stat.size > 16000) throw Error('Неверный файл');
    const draft = JSON.parse(await fs.readFile(file,'utf8'));
    if (candidateMode ? draft?.ready_for_review !== false : draft?.ready_for_review !== true) continue;
    const payload = candidateMode ? buildCandidatePayload(draft) : buildPayload(draft);
    const image = path.join(directory, name.replace(/^draft-/, 'card-').replace(/\.json$/, '.png'));
    const cardStat = await fs.stat(image);
    if (!cardStat.isFile() || cardStat.size > 180000) throw Error('Неверная карточка');
    const card = await fs.readFile(image);
    attachCard(payload, card, draft);
    ready.push({number:Number(name.slice(6,8)),draft,card,source_url:payload.source_url});
  }
  if (!ready.length) return {ready,report:{status:'none-ready',items:[],pending:null,uncertain:null,next:null}};
  const url = endpoint(options.url), secret = options.secret;
  if (typeof secret !== 'string' || !/^[A-Za-z0-9_-]{32,256}$/.test(secret)) throw Error('Неверный секрет');
  const check = new URL(url); check.pathname = '/availability';
  const fetcher = options.fetcher || fetch;
  const response = await fetcher(check.href, {method:'POST', headers:{'content-type':'application/json',authorization:`Bearer ${secret}`}, body:JSON.stringify({source_urls:ready.map(item=>item.source_url)}), redirect:'error',signal:AbortSignal.timeout(15000)});
  if (response.status !== 200) throw Error('Проверка очереди недоступна');
  const state = await responseJson(response);
  if (!state || !Array.isArray(state.known) || state.known.length !== ready.length || !state.known.every(x=>typeof x === 'boolean') || !Number.isSafeInteger(state.pending) || state.pending < 0 || !Number.isSafeInteger(state.uncertain) || state.uncertain < 0) throw Error('Некорректный ответ очереди');
  const index = state.known.indexOf(false);
  const status = state.uncertain ? 'uncertain' : state.pending ? 'pending' : index === -1 ? 'all-known' : 'candidate';
  const report = {status,items:ready.map((item,i)=>({number:item.number,known:state.known[i]})),pending:state.pending,uncertain:state.uncertain,next:status==='candidate'?ready[index].number:null};
  return {ready, report, url, secret, fetcher, index};
}

// One read-only preflight; returns numbers and flags, never text, URLs, or credentials.
export async function checkQueue(directory, options = {}) {
  return (await inspect(directory, options)).report;
}

// Read-only preflight for unreviewed candidates; does not submit or notify.
export async function checkAutomaticQueue(directory, options = {}) {
  return (await inspect(directory, options, true)).report;
}

export async function queueOne(directory, options = {}) {
  if (options.send !== true) throw Error('Явное разрешение на отправку в очередь обязательно');
  const check = await inspect(directory,options);
  if (check.report.status !== 'candidate') return {status:check.report.status};
  // The distinct guarded endpoint performs an atomic check-and-insert. No retries.
  await submit(check.ready[check.index].draft, {url:check.url,secret:check.secret,card:check.ready[check.index].card,fetcher:check.fetcher,guarded:true});
  return {status:'queued'};
}
// A separate entry point for unverified daily candidates; never changes the
// semantics of the existing manually checked producer.
export async function queueAutomaticCandidate(directory, options = {}) {
  if (options.send !== true) throw Error('Явное разрешение на отправку в очередь обязательно');
  const check = await inspect(directory,options,true);
  if (check.report.status !== 'candidate') return {status:check.report.status};
  await submitCandidate(check.ready[check.index].draft, {url:check.url,secret:check.secret,card:check.ready[check.index].card,fetcher:check.fetcher,send:true});
  return {status:'queued'};
}
// GitHub annotations expose only bounded status/counts, not URLs or message content.
// A successful job can still mean no send because the queue is blocked or known.
export function queueNotice(report) {
  const labels = {queued:'candidate accepted by queue; delivery must be verified',
    candidate:'candidate available', pending:'waiting for reviewer', uncertain:'delivery state uncertain; do not retry blindly',
    'all-known':'all candidates already known', 'none-ready':'no ready candidates; queue was not checked'};
  if (!report || !Object.hasOwn(labels, report.status)) throw Error('Неизвестное состояние очереди');
  return `Telegram review: ${labels[report.status]}`;
}
async function main(args) {
  if (args.length !== 2 || !['--check','--check-candidate','--send-one','--send-candidate'].includes(args[1])) throw Error('Нужен каталог и режим --check, --check-candidate, --send-one или --send-candidate');
  const options = {url:process.env.REVIEW_INTAKE_URL,secret:process.env.REVIEW_INTAKE_SECRET};
  let report;
  if (args[1] === '--check') report = await checkQueue(args[0],options);
  else if (args[1] === '--check-candidate') report = await checkAutomaticQueue(args[0],options);
  else if (args[1] === '--send-one') report = await queueOne(args[0],{...options,send:true});
  else report = await queueAutomaticCandidate(args[0],{...options,send:true});
  if (args[1] === '--check' || args[1] === '--check-candidate') console.log(JSON.stringify(report,null,2));
  else console.log('Состояние очереди: '+report.status);
  if (process.env.GITHUB_ACTIONS === 'true') console.log('::notice::'+queueNotice(report));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).catch(()=>{console.error('Операция не подтверждена: проверьте настройки и /status; после попытки отправки не повторяйте вслепую.');process.exitCode=1;});
}
