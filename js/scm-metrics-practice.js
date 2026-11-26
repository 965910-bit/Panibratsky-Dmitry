/* Working examples; calculations stay in the current page. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else api.install(root.document);
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  const MAX = 1e9;
  function number(value) {
    if (typeof value !== 'string' || !/^\s*\d{1,10}(?:[.,]\d{1,6})?\s*$/.test(value)) return null;
    const n = Number(value.trim().replace(',', '.'));
    return Number.isFinite(n) && n <= MAX ? n : null;
  }
  function pairs(value) {
    if (typeof value !== 'string' || value.length > 8000) return null;
    const lines = value.trim().split(/\r?\n/);
    if (!lines.length || lines.length > 100) return null;
    const parsed = [];
    for (const line of lines) {
      const parts = line.split(';');
      if (parts.length !== 2) return null;
      const a = number(parts[0]), b = number(parts[1]);
      if (a === null || b === null) return null;
      parsed.push([a, b]);
    }
    return parsed;
  }
  function forecast(value) {
    const rows = pairs(value);
    if (!rows) return null;
    let actual = 0, absolute = 0, signed = 0, percent = 0, zeros = 0;
    for (const [a, f] of rows) {
      actual += a; absolute += Math.abs(a - f); signed += a - f;
      if (a === 0) zeros++; else percent += Math.abs(a - f) / a;
    }
    return {count: rows.length, actual, wape: actual > 0 ? absolute / actual * 100 : null,
      mae: absolute / rows.length, cfe: signed, mape: zeros ? null : percent / rows.length * 100};
  }
  function freight(value) {
    const rows = pairs(value);
    if (!rows) return null;
    let distance = 0, tonkm = 0;
    for (const [mass, km] of rows) { distance += km; tonkm += mass * km; }
    return {distance, tonkm, load: distance ? tonkm / distance : null};
  }
  function payable(cost, invoices, fte) {
    cost = number(cost); invoices = number(invoices); fte = number(fte);
    if (cost === null || invoices === null || fte === null || !Number.isSafeInteger(invoices)) return null;
    return {costPerInvoice: invoices ? cost / invoices : null, perFte: fte ? invoices / fte : null};
  }
  const format = n => n === null ? 'не определено: знаменатель равен нулю' : (n !== 0 && Math.abs(n) < 0.005 ? n.toExponential(2) : new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 2}).format(n));
  function install(document) {
    for (const [id, calculate] of [
      ['practice-forecast', form => { const x = forecast(form.elements.rows.value); return x && `Наблюдений: ${x.count}. WAPE: ${format(x.wape)}${x.wape === null ? '' : ' %'}. MAE: ${format(x.mae)} ед. Накопленная ошибка (факт − прогноз): ${format(x.cfe)} ед. MAPE: ${x.mape === null ? 'не определена: есть нулевой факт' : format(x.mape) + ' %'}.`; }],
      ['practice-freight', form => { const x = freight(form.elements.rows.value); return x && `Пробег: ${format(x.distance)} км. Грузооборот: ${format(x.tonkm)} т·км. Средняя загрузка на весь пробег: ${format(x.load)}${x.load === null ? '' : ' т'}.`; }],
      ['practice-payable', form => { const x = payable(form.elements.cost.value, form.elements.invoices.value, form.elements.fte.value); return x && `Стоимость на счёт: ${format(x.costPerInvoice)}${x.costPerInvoice === null ? '' : ' руб.'}. Счетов на FTE за период: ${format(x.perFte)}.`; }]
    ]) {
      const form = document.getElementById(id), output = document.getElementById(id + '-output');
      if (!form || !output) continue;
      const button = form.querySelector('button[type="submit"]');
      if (!button) continue;
      form.addEventListener('input', () => { output.textContent = ''; });
      form.addEventListener('submit', event => {
        event.preventDefault();
        output.textContent = calculate(form) || 'Проверьте ввод: нужны неотрицательные числа до 1 млрд, максимум 6 знаков после запятой; число счетов должно быть целым. В таблице используйте две колонки через точку с запятой, не более 100 строк.';
      });
      button.disabled = false;
    }
  }
  return Object.freeze({number, pairs, forecast, freight, payable, install});
});
