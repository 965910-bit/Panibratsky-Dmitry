'use strict';
// Calculations run locally; no case data are transmitted or stored by this tool.
(function () {
  const form = document.getElementById('case-simulation');
  const output = document.getElementById('case-result');
  const error = document.getElementById('case-error');
  if (!form || !output || !error || !window.SCMCaseModel) return;
  const fmt = value => new Intl.NumberFormat('ru-RU').format(value);
  function clear() {
    output.hidden = true;
    error.textContent = '';
    document.getElementById('case-summary').textContent = '';
    document.getElementById('case-rows').replaceChildren();
  }
  form.addEventListener('input', clear);
  form.addEventListener('submit', event => {
    event.preventDefault();
    clear();
    const values = Object.fromEntries(['stock', 'demand', 'horizon', 'mainDay', 'mainQty', 'extraDay', 'extraQty'].map(name => [name, form.elements.namedItem(name).value]));
    const result = window.SCMCaseModel.simulate(values);
    if (!result) {
      error.textContent = 'Проверьте поля: нужны целые числа в указанных диапазонах; дни поступлений — от 1 до 365, горизонт — от 1 до 30.';
      return;
    }
    const { baseline, alternative } = result;
    document.getElementById('case-summary').textContent = `За ${fmt(baseline.days.length)} дн.: спрос ${fmt(baseline.requested)} ед. Без дополнительной поставки: неудовлетворённый спрос ${fmt(baseline.lostTotal)} ед., дней с дефицитом ${fmt(baseline.shortageDays)}, остаток ${fmt(baseline.closingStock)} ед. С дополнительной поставкой: неудовлетворённый спрос ${fmt(alternative.lostTotal)} ед., дней с дефицитом ${fmt(alternative.shortageDays)}, остаток ${fmt(alternative.closingStock)} ед. Разница неудовлетворённого спроса: ${fmt(baseline.lostTotal - alternative.lostTotal)} ед.`;
    const rows = document.getElementById('case-rows');
    baseline.days.forEach((day, i) => {
      const other = alternative.days[i];
      const tr = document.createElement('tr');
      for (const [index, value] of [day.day, day.received, day.lost, day.balance, other.received, other.lost, other.balance].entries()) {
        const cell = document.createElement(index === 0 ? 'th' : 'td');
        if (index === 0) cell.scope = 'row';
        cell.textContent = fmt(value);
        tr.appendChild(cell);
      }
      rows.appendChild(tr);
    });
    output.hidden = false;
  });
  form.querySelector('button[type="submit"]').disabled = false;
})();
