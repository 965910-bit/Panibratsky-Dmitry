'use strict';
// Search only the already-rendered directory. No tracking or external requests.
(function () {
  const area = document.getElementById('knowledge-search');
  const input = document.getElementById('topic-search');
  const status = document.getElementById('topic-count');
  const empty = document.getElementById('topic-empty');
  const cards = Array.from(document.querySelectorAll('[data-knowledge-card]'));
  if (!area || !input || !status || !empty || !cards.length) return;
  const normalise = text => text.normalize('NFKC').toLocaleLowerCase('ru-RU').replace(/ё/g,'е').trim();
  const update = () => {
    const terms = normalise(input.value).split(/\s+/).filter(Boolean);
    let count = 0;
    for (const card of cards) {
      const text = normalise(`${card.dataset.keywords || ''} ${card.textContent}`);
      const match = terms.every(term => text.includes(term));
      card.hidden = !match;
      if (match) count++;
    }
    status.textContent = `Показано направлений: ${count} из ${cards.length}.`;
    empty.hidden = count !== 0;
  };
  input.addEventListener('input', update);
  update();
  area.hidden = false;
})();
