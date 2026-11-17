'use strict';

function validOpenLogistics(data) {
  const bank = data?.indicators?.world_bank;
  const euro = data?.indicators?.eurostat;
  const year = value => typeof value === 'string' && /^\d{4}$/.test(value);
  const number = value => typeof value === 'number' && Number.isFinite(value);
  return data?.schema_version === 1 && typeof data.saved_on === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(data.saved_on) &&
    year(bank?.period) && number(bank.value) && bank.value >= 1 && bank.value <= 5 &&
    year(euro?.period) && number(euro.value) && euro.value >= 0 &&
    (euro.status === null || (typeof euro.status === 'string' && euro.status.length <= 40));
}

async function loadOpenLogistics(fetcher = fetch) {
  const status = document.getElementById('open-data-status');
  const bank = document.getElementById('open-data-bank');
  const euro = document.getElementById('open-data-eurostat');
  if (!status || !bank || !euro) return;
  try {
    const response = await fetcher('data/open-logistics.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error('Snapshot unavailable');
    const data = await response.json();
    if (!validOpenLogistics(data)) throw new Error('Invalid snapshot');
    const w = data.indicators.world_bank;
    const e = data.indicators.eurostat;
    bank.textContent = `${w.value.toLocaleString('ru-RU')} из 5 — Россия, период ${w.period} г.`;
    euro.textContent = `${e.value.toLocaleString('ru-RU')} тыс. тонн — Германия, период ${e.period} г.${e.status ? ` Статус наблюдения: ${e.status}.` : ''}`;
    status.textContent = `Снимок сохранён ${data.saved_on} (UTC). Периоды показателей указаны отдельно; это не текущие новости.`;
  } catch (_) {
    bank.textContent = 'Данные временно недоступны.';
    euro.textContent = 'Данные временно недоступны.';
    status.textContent = 'Не удалось загрузить проверенный снимок. Откройте первоисточники ниже.';
  }
}

if (typeof module !== 'undefined' && module.exports) module.exports = { validOpenLogistics, loadOpenLogistics };
if (typeof document !== 'undefined') loadOpenLogistics();
