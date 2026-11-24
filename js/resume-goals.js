/* Prepared only: do not load/enable until privacy, consent and existing goals are reviewed. */
(() => {
  const RESUME_GOALS_ENABLED = false;
  if (!RESUME_GOALS_ENABLED) return;

  const goals = Object.freeze({hh: 'resume_click_hh', zarplata: 'resume_click_zarplata'});
  document.addEventListener('click', event => {
    if (event.defaultPrevented || (typeof event.button === 'number' && event.button !== 0)) return;
    if (!event.target || typeof event.target.closest !== 'function') return;
    const link = event.target.closest('a[data-resume-goal]');
    if (!link) return;
    const key = link.getAttribute('data-resume-goal');
    if (!Object.prototype.hasOwnProperty.call(goals, key)) return;
    // Send only a fixed identifier, never the link, visitor information or input.
    try {
      if (typeof window.ym === 'function') window.ym(108401876, 'reachGoal', goals[key]);
    } catch (_) { /* Analytics must not interrupt navigation. */ }
  });
})();
