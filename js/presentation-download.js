/* Count activation attempts, not completed downloads. Do not block navigation. */
(() => {
  document.addEventListener('click', event => {
    if (event.defaultPrevented || (typeof event.button === 'number' && event.button !== 0)) return;
    if (!event.target || typeof event.target.closest !== 'function' || !event.target.closest('a[data-presentation-download]')) return;
    // Only fixed event names: no URL, contact information, or visitor input.
    try { if (typeof window.ym === 'function') window.ym(108401876, 'reachGoal', 'presentation_download'); } catch (_) { /* ignore blocked analytics */ }
    try { if (typeof window.gtag === 'function') window.gtag('event', 'presentation_download'); } catch (_) { /* keep download working */ }
  });
})();
