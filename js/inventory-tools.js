'use strict';
// These tools run only in the browser. Values are never persisted or sent.
(function () {
  const form = document.querySelector('[data-inventory-tool]');
  if (!form || !window.SCMInventory || !window.SCMInventoryMetrics) return;
  const output = document.getElementById('tool-result');
  const fmt = n => SCMInventory.format(n).replace('.', ',');
  form.addEventListener('input', () => { output.textContent = ''; output.classList.remove('error'); });
  form.addEventListener('submit', event => {
    event.preventDefault();
    const values = Array.from(form.querySelectorAll('input')).map(input => input.value);
    let result, text;
    switch (form.dataset.inventoryTool) {
      case 'turnover':
        result = SCMInventoryMetrics.turnoverDays(values);
        if (result !== null) text = `${fmt(result.ratio)} раз за период; ${result.days === null ? 'дни не определены при нулевой себестоимости' : `оценка ${fmt(result.days)} дней`}.`;
        break;
      case 'safety':
        result = SCMInventory.safetyScenario(values);
        if (result !== null) text = `Сценарная оценка: ${fmt(result)} единиц.`;
        break;
      case 'reorder':
        result = SCMInventory.reorderPoint(values);
        if (result !== null) text = `Расчётный порог: ${fmt(result)} единиц.`;
        break;
      default: return;
    }
    output.classList.toggle('error', result === null);
    output.textContent = result === null ? 'Проверьте все поля: нужны конечные значения и допустимые границы, указанные в форме.' : text;
  });
  form.querySelector('button[type=submit]').disabled = false;
})();
