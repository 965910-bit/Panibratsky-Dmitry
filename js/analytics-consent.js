/* Optional analytics: no analytics vendor is loaded before the visitor opts in.
 * This is a technical control, not a substitute for a privacy/legal review. */
(function () {
  'use strict';
  const key = 'scm_analytics_choice_v1';
  let choice = null;
  try { choice = localStorage.getItem(key); } catch (_) { /* session-only choice */ }
  let started = false;
  const gaPages = new Set(['/', '/index.html', '/about.html', '/blog.html', '/career.html', '/contact.html', '/experience.html', '/expertise.html', '/prompts.html', '/trends.html']);
  function addScript(url) {
    const script = document.createElement('script');
    script.async = true; script.src = url; document.head.appendChild(script);
  }
  function startAnalytics() {
    if (started) return;
    started = true;
    const pageUrl = location.origin + location.pathname;
    let referrer = '';
    try { if (document.referrer) referrer = new URL(document.referrer).origin + '/'; } catch (_) {}
    window.ym = window.ym || function () { (window.ym.a = window.ym.a || []).push(arguments); };
    window.ym.l = Date.now();
    window.ym(108401876, 'init', {webvisor:false, clickmap:false, trackLinks:false, accurateTrackBounce:true, url:pageUrl, referrer:referrer});
    addScript('https://mc.yandex.ru/metrika/tag.js?id=108401876');
    // GA4 remains limited to pages where it was installed before this change.
    // Enhanced measurement must still be reviewed in the GA4 property.
    if (gaPages.has(location.pathname)) {
      window.dataLayer = window.dataLayer || [];
      window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
      window.gtag('js', new Date());
      window.gtag('config', 'G-DM41FJYWX0', {page_location:pageUrl, page_referrer:referrer});
      addScript('https://www.googletagmanager.com/gtag/js?id=G-DM41FJYWX0');
    }
  }
  const style = document.createElement('style');
  style.textContent = '.analytics-choice{position:fixed;z-index:2147483647;left:12px;bottom:12px;width:min(460px,calc(100% - 24px));background:#fff;color:#142033;border:1px solid #536477;border-radius:8px;padding:16px;font:15px/1.5 Arial,sans-serif;box-shadow:0 4px 20px #0004}.analytics-choice[hidden]{display:none}.analytics-choice p{margin:0 0 12px}.analytics-choice button,.analytics-settings{font:inherit;cursor:pointer;border:1px solid #31445d;border-radius:5px;padding:8px 12px;margin:3px;background:#fff;color:#142033}.analytics-choice button:first-of-type{background:#163e78;color:#fff}.analytics-settings{position:fixed;z-index:2147483646;right:8px;bottom:8px;font:12px Arial,sans-serif;background:#fff;color:#142033}.analytics-choice button:focus-visible,.analytics-settings:focus-visible{outline:3px solid #ed9000;outline-offset:2px}@media print{.analytics-choice,.analytics-settings{display:none!important}}';
  document.head.appendChild(style);
  const panel = document.createElement('section');
  panel.className = 'analytics-choice'; panel.setAttribute('aria-label', 'Настройки аналитики');
  panel.innerHTML = '<p>С вашего разрешения сайт использует Яндекс Метрику и на некоторых страницах Google Analytics для статистики посещений и кликов. Можно отказаться или изменить выбор в любое время. Ответы чек-листа и значения расчётов не передаются нашими событиями.</p><button type="button" data-choice="yes">Разрешить аналитику</button><button type="button" data-choice="no">Отказаться</button>';
  const settings = document.createElement('button');
  settings.type = 'button'; settings.className = 'analytics-settings'; settings.textContent = 'Настройки аналитики';
  settings.setAttribute('aria-expanded', choice === null ? 'true' : 'false');
  panel.hidden = choice === 'yes' || choice === 'no';
  document.body.append(panel, settings);
  settings.addEventListener('click', function () { panel.hidden = !panel.hidden; settings.setAttribute('aria-expanded', String(!panel.hidden)); if (!panel.hidden) panel.querySelector('button').focus(); });
  panel.addEventListener('click', function (event) {
    const button = event.target.closest('button[data-choice]');
    if (!button) return;
    const next = button.dataset.choice;
    try { localStorage.setItem(key, next); } catch (_) {}
    const wasStarted = started;
    choice = next;
    panel.hidden = true; settings.setAttribute('aria-expanded', 'false');
    if (next === 'yes') startAnalytics();
    else if (wasStarted) location.reload(); // unload vendor scripts after withdrawal
  });
  if (choice === 'yes') startAnalytics();
})();
