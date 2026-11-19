// Offline editorial shortlist; never calls Telegram or modifies the news feed.
import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {prepareDraft} from './drafts.mjs';

// A narrow, transparent heuristic; it cannot verify facts or identify duplicates with different URLs.
const OPS = /(?:склад|логистик|цеп(?:ь|и|ей) постав|цепочк[аи] постав|управлени[ея] запас|товарн(?:ые|ых|ого) запас|распределительн(?:ый|ого|ом) центр|снабжени|фулфилмент|\bwms\b|\btms\b|supply chain|warehouse)/iu;
export function shortlist(news, limit = 8) {
  if (!Array.isArray(news)) throw Error('Ожидается массив новостей');
  if (!Number.isInteger(limit) || limit < 1 || limit > 20) throw Error('Недопустимое число кандидатов');
  const seen = new Set(), drafts = [];
  for (const item of news) {
    if (drafts.length >= limit) break;
    let draft;
    try { draft = prepareDraft(item); } catch { continue; }
    // Previously collected content remains in the feed; do not automatically reuse it
    // in new galleries while source access and usage conditions are unresolved.
    if (!OPS.test(`${draft.title} ${draft.description}`) || seen.has(draft.source_url)) continue;
    seen.add(draft.source_url);
    drafts.push(draft);
  }
  return drafts;
}
async function main(args) {
  if (args.length !== 1 || !args[0]) throw Error('Укажите путь к новому JSON-файлу');
  const feed = JSON.parse(await fs.readFile(new URL('../data/news.json', import.meta.url), 'utf8'));
  const drafts = shortlist(feed);
  const batch = {version:1, note:'Автоматический отбор без проверки фактов. Все материалы требуют проверки и собственного вывода. Не отправлено в Telegram.', drafts};
  await fs.writeFile(args[0], JSON.stringify(batch, null, 2) + '\n', {encoding:'utf8', flag:'wx', mode:0o600});
  console.log(`Создано кандидатов: ${drafts.length}. Ничего не отправлено.`);
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).catch(() => { console.error('Не удалось подготовить подборку; проверьте входную ленту и путь к новому файлу.'); process.exitCode = 1; });
}
