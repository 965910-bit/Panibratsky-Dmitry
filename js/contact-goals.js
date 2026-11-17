/* Staged only: enable after consent requirements and existing goals are reviewed.
 * This switch is not a consent manager and must not bypass visitor choice. */
(() => {
  const CONTACT_GOALS_ENABLED = false;
  if (!CONTACT_GOALS_ENABLED) return;

  const goals = Object.freeze({
    phone: 'contact_phone_click',
    email: 'contact_email_click',
    profile: 'contact_profile_click'
  });
  document.addEventListener('click', event => {
    if (event.defaultPrevented || (typeof event.button === 'number' && event.button !== 0)) return;
    const target = event.target;
    if (!target || typeof target.closest !== 'function') return;
    const link = target.closest('a[data-contact-goal]');
    if (!link) return;
    const key = link.getAttribute('data-contact-goal');
    if (!Object.prototype.hasOwnProperty.call(goals, key)) return;
    // No URL, number, email, text, or user input is passed to the counter.
    try {
      if (typeof window.ym === 'function') window.ym(108401876, 'reachGoal', goals[key]);
    } catch (_) { /* Analytics must not interfere with the link. */ }
  });
})();
