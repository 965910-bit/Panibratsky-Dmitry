'use strict';
// Filters the table of contents only; articles remain visible and work without JavaScript.
(function () {
  const box = document.getElementById('chapter-search-box');
  const input = document.getElementById('chapter-search');
  const status = document.getElementById('chapter-search-status');
  const empty = document.getElementById('chapter-empty');
  const entries = Array.from(document.querySelectorAll('[data-chapter-entry]'));
  if (!box || !input || !status || !empty || !entries.length) return;
  const normalise = text => text.normalize('NFKC').toLocaleLowerCase('ru-RU').replace(/ё/g, 'е').trim();
  const update = () => {
    const terms = normalise(input.value).split(/\s+/).filter(Boolean);
    let count = 0;
    for (const entry of entries) {
      const text = normalise(`${entry.dataset.keywords || ''} ${entry.textContent}`);
      const matches = terms.every(term => text.includes(term));
      entry.hidden = !matches;
      if (matches) count++;
    }
    status.textContent = `Показано тем: ${count} из ${entries.length}.`;
    empty.hidden = count !== 0;
  };
  input.addEventListener('input', update);
  update();
  box.hidden = false;
})();
