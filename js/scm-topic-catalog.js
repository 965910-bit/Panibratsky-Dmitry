(() => {
  const box = document.getElementById('catalog-search-box');
  const input = document.getElementById('catalog-search');
  const status = document.getElementById('catalog-search-status');
  const groups = [...document.querySelectorAll('[data-topic-group]')];
  if (!box || !input || !status || !groups.length) return;
  const normalize = value => value.toLocaleLowerCase('ru').replace(/ё/g, 'е').trim();
  const entries = groups.map(group => ({ group, cards: [...group.querySelectorAll('[data-topic]')] }));
  const update = () => {
    const words = normalize(input.value).split(/\s+/).filter(Boolean);
    let count = 0;
    for (const { group, cards } of entries) {
      let visible = 0;
      for (const card of cards) {
        const text = normalize(card.textContent);
        card.hidden = !words.every(word => text.includes(word));
        if (!card.hidden) { visible++; count++; }
      }
      group.hidden = visible === 0;
    }
    status.textContent = words.length ? `Найдено тем: ${count}` : '';
  };
  input.addEventListener('input', update);
  box.hidden = false;
})();
