/* Filters already published cards on this page; no network or persistence. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else factory(root.document);
})(typeof window !== 'undefined' ? window : globalThis, function (document) {
  'use strict';
  const control = document.getElementById('metric-search-control');
  const input = document.getElementById('metric-search-input');
  const status = document.getElementById('metric-search-status');
  const empty = document.getElementById('metric-search-empty');
  const entries = Array.from(document.querySelectorAll('.metric-entry'));
  if (!control || !input || !status || !empty || !entries.length) return;
  const normalise = text => text.normalize('NFKC').toLocaleLowerCase('ru-RU').replace(/ё/g, 'е').trim();
  function update() {
    const terms = normalise(input.value).split(/\s+/).filter(Boolean);
    let total = 0;
    for (const entry of entries) {
      const text = normalise(entry.textContent);
      const visible = terms.every(term => text.includes(term));
      entry.hidden = !visible;
      if (visible) total++;
    }
    // Keep every section, example and navigation visible even if no card matches.
    // This avoids hiding a fragment target reached from another page.
    status.textContent = 'Показано показателей: ' + total + ' из ' + entries.length + '.';
    empty.hidden = total !== 0;
  }
  input.addEventListener('input', update);
  update();
  control.hidden = false;
});
