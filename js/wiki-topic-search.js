/* Filters the local curated index only. No storage, network or analytics. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else factory(root.document);
})(typeof window !== 'undefined' ? window : globalThis, function (document) {
  'use strict';
  const box = document.getElementById('wiki-search-control');
  const input = document.getElementById('wiki-search-input');
  const status = document.getElementById('wiki-search-status');
  const empty = document.getElementById('wiki-search-empty');
  const entries = Array.from(document.querySelectorAll('[data-wiki-topic]'));
  if (!box || !input || !status || !empty || !entries.length) return;
  const normalise = text => text.normalize('NFKC').toLocaleLowerCase('ru-RU').replace(/ё/g, 'е').trim();
  const update = function () {
    const terms = normalise(input.value).split(/\s+/).filter(Boolean);
    let count = 0;
    for (const entry of entries) {
      const content = normalise((entry.dataset.keywords || '') + ' ' + entry.textContent);
      const visible = terms.every(term => content.includes(term));
      entry.hidden = !visible;
      if (visible) count++;
    }
    status.textContent = 'Показано тем: ' + count + ' из ' + entries.length + '.';
    empty.hidden = count !== 0;
  };
  input.addEventListener('input', update);
  update();
  box.hidden = false;
});
