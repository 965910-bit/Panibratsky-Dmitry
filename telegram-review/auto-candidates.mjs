// Offline candidate selection. Explicit source allowlist and recent dates are mandatory.
// No network, writes to the journal, or Telegram calls.
import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {shortlist} from './candidates.mjs';

export function selectAutomatic(news, hosts, now = Date.now()) {
  if (!Array.isArray(news) || !Array.isArray(hosts) || !hosts.length || hosts.length > 50 || !Number.isFinite(now)) throw Error('Нужен явный список проверенных источников');
  if (!hosts.every(h => typeof h === 'string' && /^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(h))) throw Error('Неверный список доменов');
  const allowed = new Set(hosts);
  const eligible = news.filter(item => {
    if (typeof item?.pubDate !== 'string' || !item.pubDate.trim() || typeof item.link !== 'string') return false;
    const date = Date.parse(item.pubDate);
    if (!Number.isFinite(date) || date > now || now - date > 14 * 24 * 60 * 60 * 1000) return false;
    try { const u = new URL(item.link); return u.protocol === 'https:' && !u.username && !u.password && !u.port && allowed.has(u.hostname); }
    catch { return false; }
  });
  // Existing source restrictions and generic Google Alert title guard still apply.
  // Sort by source publication time, not feed order; shortlist deduplicates URLs.
  eligible.sort((a,b)=>Date.parse(b.pubDate)-Date.parse(a.pubDate));
  return shortlist(eligible, 8).filter(d=>d.source_name);
}
async function main(args) {
  if (args.length !== 1 || !args[0]) throw Error('Нужен путь к новому файлу');
  const fromEnv = (process.env.SCM_REVIEW_ALLOWED_HOSTS || '').split(',').map(s=>s.trim()).filter(Boolean);
  const fromFile = (await fs.readFile(new URL('./allowed-hosts.txt', import.meta.url), 'utf8')).split(/\s+/).map(s=>s.trim()).filter(Boolean);
  const hosts = [...new Set([...fromEnv, ...fromFile])];
  const feed = JSON.parse(await fs.readFile(new URL('../data/news.json', import.meta.url), 'utf8'));
  const seed = JSON.parse(await fs.readFile(new URL('./seed-news.json', import.meta.url), 'utf8'));
  const stamp = new Date(Date.now() - 3600 * 1000).toISOString();
  const news = [...(Array.isArray(seed) ? seed.map(item => ({...item, pubDate: stamp})) : []), ...(Array.isArray(feed) ? feed : [])];
  const drafts = selectAutomatic(news, hosts);
  if (!drafts.length) throw Error('Нет свежих кандидатов с реальным заголовком на разрешённых доменах');
  await fs.writeFile(args[0], JSON.stringify({version:1,note:'Автоматический отбор без проверки фактов и прав; не опубликовано.',drafts},null,2)+'\n', {flag:'wx',mode:0o600});
  console.log(`Свежих кандидатов: ${drafts.length}. Ничего не отправлено.`);
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main(process.argv.slice(2)).catch(()=>{console.error('Отбор не выполнен: проверьте список разрешённых источников и ленту.');process.exitCode=1;});
