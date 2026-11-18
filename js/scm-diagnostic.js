'use strict';
// A checklist, not a rating, prediction or professional audit. No storage/network.
(function () {
  const form = document.getElementById('scm-checklist');
  if (!form) return;
  const result = document.getElementById('checklist-result');
  const questions = [
    ['stock', 'Сверить спрос, средний запас и период расчёта.', 'inventory-turnover-calculator.html', 'Оборачиваемость запасов'],
    ['supply', 'Проверить срок до доступности товара и расчёт порога пополнения.', 'reorder-point-calculator.html', 'Точка заказа'],
    ['safety', 'Проверить допущения и сценарии страхового запаса.', 'safety-stock-calculator.html', 'Страховой запас'],
    ['service', 'Согласовать определение уровня сервиса и порядок учёта дефицита.', 'calculators.html', 'Калькуляторы SCM'],
  ];
  form.addEventListener('change', () => { result.replaceChildren(); result.classList.remove('error'); });
  form.addEventListener('submit', event => {
    event.preventDefault();
    result.replaceChildren();
    if (questions.some(([id]) => !['yes', 'review', 'unknown'].includes(form.elements[id].value))) {
      result.classList.add('error'); result.textContent = 'Ответьте на все вопросы или выберите «Не знаю».'; return;
    }
    result.classList.remove('error');
    const open = questions.filter(([id]) => form.elements[id].value !== 'yes');
    const title = document.createElement('p');
    title.textContent = open.length ? 'Вопросы, которые можно проверить дальше:' : 'Вы отметили все пункты как проверенные. Это не подтверждает состояние процессов; периодически пересматривайте допущения.';
    result.append(title);
    if (open.length) {
      const ul = document.createElement('ul');
      for (const [, text, href, label] of open) {
        const li = document.createElement('li'); li.append(document.createTextNode(text + ' '));
        const a = document.createElement('a'); a.href = href; a.textContent = label; li.append(a); ul.append(li);
      }
      result.append(ul);
    }
  });
  form.querySelector('button[type=submit]').disabled = false;
})();
