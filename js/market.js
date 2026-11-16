'use strict';

// The source marker prevents historical example files from being presented as collected data.
function validateMarketData(data, now = Date.now()) {
  if (!data || data.schema_version !== 1 || data.source !== 'hh.ru API' ||
      !Array.isArray(data.queries) || !data.queries.every(q => typeof q === 'string') || !data.queries.length ||
      typeof data.date_from !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(data.date_from) ||
      !Number.isInteger(data.total_vacancies) || data.total_vacancies < 1 ||
      !Number.isInteger(data.salary_sample_size) || data.salary_sample_size < 0 || data.salary_sample_size > data.total_vacancies ||
      !data.salary_stats || !Array.isArray(data.top_skills) || !data.avg_salary_by_region ||
      typeof data.avg_salary_by_region !== 'object' || Array.isArray(data.avg_salary_by_region)) return null;
  const updated = Date.parse(data.updated_at);
  if (!Number.isFinite(updated) || updated > now + 300000) return null;
  const average = data.salary_stats.avg;
  if (data.salary_sample_size === 0 ? average !== null : !(typeof average === 'number' && Number.isFinite(average) && average > 0)) return null;
  return { data, updated, stale: now - updated > 72 * 3600000 };
}

function hiringWeeks(count, weeklyRate) {
  if (!Number.isInteger(count) || count < 1 || count > 100000 || !Number.isFinite(weeklyRate) || weeklyRate < 0.01 || weeklyRate > 100000) return null;
  return Math.ceil(count / weeklyRate);
}

async function loadMarketCard(id, path, fetcher = fetch) {
  const target = document.getElementById(id);
  const element = (tag, text, className) => {
    const el = document.createElement(tag);
    el.textContent = text;
    if (className) el.className = className;
    return el;
  };
  try {
    const response = await fetcher(path, { cache: 'no-store' });
    if (!response.ok) throw new Error('unavailable');
    const result = validateMarketData(await response.json());
    if (!result) throw new Error('unverified');
    const { data, updated, stale } = result;
    const number = value => new Intl.NumberFormat('ru-RU').format(value);
    const nodes = [
      element('p', `Обновлено: ${new Date(updated).toLocaleString('ru-RU')} · запросы: ${data.queries.join(', ')}`, 'market-updated'),
      element('p', stale ? 'Данные старше 72 часов — используйте с осторожностью.' : 'Дата обновления указана выше; проверяйте актуальность перед использованием.', stale ? 'market-warning' : 'market-updated'),
      element('p', number(data.total_vacancies), 'market-value'),
      element('p', `уникальных вакансий в выборке с ${data.date_from}`, 'market-label'),
      element('p', data.salary_sample_size ? `${number(data.salary_stats.avg)} ₽` : 'Нет данных', 'market-value'),
      element('p', `средняя нижняя граница зарплаты · наблюдений: ${number(data.salary_sample_size)}`, 'market-label')
    ];
    const regions = Object.entries(data.avg_salary_by_region)
      .filter(([name, value]) => name && typeof value === 'number' && Number.isFinite(value) && value > 0)
      .sort((a, b) => b[1] - a[1]).slice(0, 5);
    if (regions.length) {
      nodes.push(element('h3', 'Регионы · средняя нижняя граница'));
      const list = document.createElement('ul'); list.className = 'market-list';
      for (const [name, value] of regions) {
        const row = document.createElement('li');
        row.append(element('span', name), element('strong', `${number(value)} ₽`));
        list.appendChild(row);
      }
      nodes.push(list);
    }
    if (data.top_skills.length === 0) nodes.push(element('p', 'Навыки в доступной выборке не указаны.', 'market-updated'));
    target.replaceChildren(...nodes);
    return true;
  } catch (_) {
    target.replaceChildren(element('p', 'Проверенная выборка пока недоступна. Исторический пример не используется как актуальная статистика.', 'market-warning'));
    return false;
  }
}

if (typeof module !== 'undefined' && module.exports) module.exports = { validateMarketData, hiringWeeks, loadMarketCard };
if (typeof document !== 'undefined') {
  const status = document.getElementById('market-status');
  Promise.all([
    loadMarketCard('warehouse-data', 'data/hh_warehouse.json'),
    loadMarketCard('transport-data', 'data/hh_transport.json')
  ]).then(results => {
    status.textContent = results.every(Boolean) ? 'Доступные выборки загружены. Источник и ограничения — ниже.' :
      results.some(Boolean) ? 'Доступна только часть выборок. Проверьте статус каждого раздела.' :
      'Проверенные данные ещё не опубликованы или временно недоступны. Методология приведена ниже.';
  });
  const form = document.getElementById('hiring-form');
  form.addEventListener('submit', event => {
    event.preventDefault();
    const weeks = hiringWeeks(Number(document.getElementById('hiring-count').value), Number(document.getElementById('hiring-rate').value));
    document.getElementById('hiring-result').textContent = weeks === null ? 'Введите целое количество людей и положительную скорость найма.' :
      `Оценка сценария (недель): ${new Intl.NumberFormat('ru-RU').format(weeks)} при сохранении указанной скорости. Реальный срок может отличаться.`;
  });
}
