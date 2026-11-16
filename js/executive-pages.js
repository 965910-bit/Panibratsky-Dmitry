(() => {
  const root = document.documentElement;
  const bar = document.querySelector('.executive-bar');
  if (!bar) return;
  document.body.classList.add('js-executive-shell');
  const button = bar.querySelector('.executive-menu');
  const nav = bar.querySelector('.executive-nav');
  const theme = bar.querySelector('.executive-theme');
  function updateTheme() {
    const light = root.dataset.executiveTheme === 'light';
    theme.textContent = light ? '☾' : '☼';
    theme.setAttribute('aria-label', light ? 'Переключить тёмную тему' : 'Переключить светлую тему');
    theme.title = theme.getAttribute('aria-label');
    // Research pages use the same light-mode class as the home page.
    if (document.body.classList.contains('executive-research')) document.body.classList.toggle('light', light);
  }
  updateTheme();
  theme.addEventListener('click', () => {
    root.dataset.executiveTheme = root.dataset.executiveTheme === 'light' ? 'dark' : 'light';
    try { localStorage.setItem('executive-theme', root.dataset.executiveTheme); } catch (_) {}
    updateTheme();
  });
  const close = () => { nav.classList.remove('is-open'); button.setAttribute('aria-expanded', 'false'); };
  button.addEventListener('click', () => {
    const open = nav.classList.toggle('is-open');
    button.setAttribute('aria-expanded', String(open));
  });
  nav.addEventListener('click', event => { if (event.target.closest('a')) close(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && nav.classList.contains('is-open')) { close(); button.focus(); } });
  window.addEventListener('resize', () => { if (window.innerWidth > 820) close(); });
})();
