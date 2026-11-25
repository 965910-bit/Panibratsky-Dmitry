/* Prepared for review only. Not loaded by the site; the switch is not consent management.
 * Before integration review privacy, counter setup, consent and existing goals. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else {
    const DEPLOYMENT_APPROVED = false;
    if (DEPLOYMENT_APPROVED) factory(root.document, root, root.location);
  }
})(typeof window !== 'undefined' ? window : globalThis, function installVisitorEvents(document, analytics, location) {
  'use strict';
  const internalPages = Object.freeze({
    '/career.html': 'interest_career', '/experience.html': 'interest_experience',
    '/scm-review-questions.html': 'interest_checklist',
    '/scm-academy.html': 'interest_academy', '/scm-internal-academy.html': 'interest_academy',
    '/scm-practical-guides.html': 'interest_guides', '/expertise.html': 'interest_expertise',
    '/calculators.html': 'interest_calculators', '/inventory-turnover-calculator.html': 'interest_calculators',
    '/safety-stock-calculator.html': 'interest_calculators', '/reorder-point-calculator.html': 'interest_calculators',
    '/scm-diagnostic.html': 'interest_diagnostic', '/trends.html': 'interest_news',
    '/blog.html': 'interest_articles', '/projects.html': 'interest_projects',
    '/scm-problems.html': 'interest_problems', '/scm-architect.html': 'interest_architecture'
  });
  function classifyLink(link) {
    const raw = link.getAttribute('href');
    if (!raw) return null;
    let url;
    try { url = new URL(raw, location.href); } catch (_) { return null; }
    if (url.protocol === 'tel:') return 'contact_phone_click';
    if (url.protocol === 'mailto:') return 'contact_email_click';
    if (url.protocol !== 'https:') return null;
    if (url.hostname === location.hostname) {
      if (url.pathname === '/expertise.html' && url.hash === '#corporate-training') return 'corporate_training_click';
      if (url.hash && url.pathname === new URL(location.href).pathname && url.hash !== '#book') return null;
      if (url.pathname === '/documents/gerasimov-presentation.pdf') return null; // existing handler
      if (url.pathname === '/index.html' || url.pathname === '/') {
        if (url.hash === '#book') return 'interest_book';
        return null;
      }
      return internalPages[url.pathname] || null;
    }
    if (url.hostname === 'surgut.hh.ru' && url.pathname === '/resume/33d5f7abff115bad460039ed1f7166544f5263') return 'resume_click_hh';
    if (url.hostname === 'surgut.zarplata.ru' && url.pathname === '/resume/dc1875b3ff115ecddd0039ed1f6c487a655144') return 'resume_click_zarplata';
    if (url.hostname === 't.me' && url.pathname === '/LogisticaandSupplyChain') return 'channel_telegram_click';
    if (url.hostname === 'max.ru' && url.pathname === '/join/hiHnbqRI5mxvakFeqTpBq3gjXiWuYPN45VeiuJmhOR0') return 'channel_max_click';
    if (url.hostname === 'dzen.ru' && url.pathname === '/id/6b053062ab2c62327a016bcd') return 'channel_dzen_click';
    if (url.hostname === 'set.ki' && url.pathname === '/EYUBwz5') return 'setka_profile_click';
    if (url.hostname === 'setka.ru' && url.pathname.replace(/\/$/, '') === '/communities/01a15b2e-dfa8-7b4d-9059-6b74529f0ac3') return 'setka_community_click';
    if (url.hostname === 'setka.ru' && url.pathname.replace(/\/$/, '') === '/communities/01a19c5c-b9c8-7a87-b08c-60a87d8f6049') return 'setka_channel_click';
    return null;
  }
  document.addEventListener('click', function (event) {
    if (event.defaultPrevented || (typeof event.button === 'number' && event.button !== 0)) return;
    const target = event.target;
    if (!target || typeof target.closest !== 'function') return;
    const print = target.closest('#print-checklist');
    const link = target.closest('a[href]');
    const name = print ? 'checklist_print_click' : link ? classifyLink(link) : null;
    if (!name) return;
    // Fixed identifiers only. Never send href, text, form values or visitor input.
    try { if (typeof analytics.ym === 'function') analytics.ym(108401876, 'reachGoal', name); } catch (_) {}
    try { if (typeof analytics.gtag === 'function') analytics.gtag('event', name); } catch (_) {}
  });
});
