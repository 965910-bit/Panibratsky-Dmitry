'use strict';
// Offline editorial preview only. Never sends, modifies news or marks it as sent.
const fs = require('node:fs');
const path = require('node:path');

const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function clean(value, limit) {
  return String(typeof value === 'string' ? value : '').replace(/<[^>]*>/g, ' ').replace(/[\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, limit);
}
function validLink(value) {
  try { const u = new URL(value); return ['https:', 'http:'].includes(u.protocol) && !u.username && !u.password ? u.href : ''; } catch { return ''; }
}
function buildPreview(items) {
  if (!Array.isArray(items)) throw Error('Ожидался массив новостей');
  const seen = new Set();
  const candidates = items.filter(item => {
    if (!item || item.dead || !clean(item.title, 300)) return false;
    const url = validLink(item.link);
    if (!url || seen.has(url)) return false;
    seen.add(url); return true;
  }).sort((a,b) => (Date.parse(b.pubDate) || 0) - (Date.parse(a.pubDate) || 0)).slice(0, 8);
  const cards = candidates.map((item, i) => {
    const title = clean(item.title, 240);
    const description = clean(item.description, 450);
    const source = clean(item.source, 100) || 'Не указан';
    const date = Number.isFinite(Date.parse(item.pubDate)) ? new Date(item.pubDate).toISOString().slice(0, 10) : 'не указана';
    return `<article><div class="visual"><div class="brand">SCM NEWS <span>•</span> ЛОГИСТИКА</div><div class="visual-title">${escape(title)}</div><div class="visual-footer">ЛЮДИ <span>→</span> ПРОЦЕССЫ <span>→</span> РЕЗУЛЬТАТ</div></div><div class="body"><div class="label">ЧЕРНОВИК ${i + 1} · ${escape(date)}</div><h2>${escape(title)}</h2><div class="section">СУТЬ ИЗ ЛЕНТЫ · ТРЕБУЕТ ПРОВЕРКИ</div><p>${escape(description || 'Описание отсутствует — проверьте первоисточник.')}</p><div class="section">КОММЕНТАРИЙ РУКОВОДИТЕЛЯ</div><p class="placeholder">Добавьте собственный вывод после проверки материала.</p><div class="source">Источник: ${escape(source)} · <a href="${escape(validLink(item.link))}" target="_blank" rel="noopener noreferrer">Открыть первоисточник ↗</a></div></div></article>`;
  }).join('\n');
  return `<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>Предпросмотр постов · SCM News</title><style>
*{box-sizing:border-box}body{margin:0;background:#edf2f6;color:#142c42;font:16px/1.55 system-ui,sans-serif}.wrap{max-width:1080px;margin:auto;padding:28px 18px}h1{margin:0;font-size:clamp(25px,5vw,38px)}.notice{background:#fff8e7;border-left:4px solid #d99a20;padding:14px 16px;margin:20px 0 28px;border-radius:6px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,310px),1fr));gap:20px}article{background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 5px 22px #17334b16}.visual{min-height:235px;background:linear-gradient(140deg,#0b1b31,#103f59);color:white;padding:24px;display:flex;flex-direction:column;justify-content:space-between;overflow-wrap:anywhere}.brand,.visual-footer{font-size:11px;letter-spacing:.13em;font-weight:800;color:#8cd8d7}.visual-footer span,.brand span{color:#45c6c2}.visual-title{font-size:clamp(21px,2.4vw,29px);font-weight:750;line-height:1.2;margin:20px 0}.body{padding:22px}.label,.section{font-size:11px;letter-spacing:.1em;font-weight:800;color:#557385}.label{color:#008d91}.section{margin-top:20px}h2{line-height:1.25;font-size:21px;margin:10px 0}p{margin:7px 0}.placeholder{color:#6a7c89;font-style:italic}.source{margin-top:20px;font-size:13px;color:#496779;overflow-wrap:anywhere}a{color:#006d78}@media print{body{background:white}.notice{border:1px solid #ddd}.grid{display:block}article{break-inside:avoid;box-shadow:none;border:1px solid #ddd;margin:0 0 16px}.visual{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
</style></head><body><main class="wrap"><h1>Черновики для Telegram</h1><div class="notice"><strong>Только визуальный предпросмотр.</strong> Материалы не проверены и не отправлены. Это не очередь одобрения: журнал отправок не учитывается, возможны уже опубликованные новости. Перед публикацией проверьте источник, даты, права на использование и добавьте свой вывод.</div><div class="grid">${cards || '<p>Нет подходящих записей в файле.</p>'}</div></main></body></html>`;
}
if (require.main === module) {
  try {
    const input = process.argv[2] || path.join(__dirname, '..', 'data', 'news.json');
    const items = JSON.parse(fs.readFileSync(input, 'utf8'));
    process.stdout.write(buildPreview(items));
  } catch (error) { console.error('Предпросмотр не создан:', error.message); process.exitCode = 1; }
}
module.exports = { buildPreview, clean, validLink };
