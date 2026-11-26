/* Local OTIF example. No storage, external requests or analytics payloads. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else factory(root.document, root.SCMOTIF);
})(typeof window !== 'undefined' ? window : globalThis, function (document, model) {
  'use strict';
  const form = document.getElementById('otif-form');
  const result = document.getElementById('otif-output');
  if (!form || !result || !model || typeof model.calculate !== 'function') return;
  const button = form.querySelector('button[type="submit"]');
  if (button) button.disabled = false;
  form.addEventListener('input', function () { result.textContent = ''; });
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    const percentage = model.calculate(form.elements.completed.value, form.elements.total.value);
    if (percentage === null) {
      result.textContent = 'Введите целые неотрицательные числа: всего заказов больше нуля, выполненных — не больше общего числа.';
      return;
    }
    result.textContent = 'OTIF по заказам: ' + new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 2}).format(percentage) + ' %. Результат округлён до двух знаков.';
  });
});
