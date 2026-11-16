(function () {
  const nav = document.querySelector('header nav');
  if (!nav) return;
  const list = nav.querySelector('ul');
  if (!list) return;
  list.id = 'portfolio-navigation';
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'portfolio-menu-toggle';
  button.textContent = 'Меню';
  button.setAttribute('aria-controls', list.id);
  button.setAttribute('aria-expanded', 'false');
  nav.insertBefore(button, list);
  nav.classList.add('portfolio-nav-ready');
  function close() { nav.classList.remove('portfolio-nav-open'); button.setAttribute('aria-expanded', 'false'); }
  button.addEventListener('click', () => {
    const open = nav.classList.toggle('portfolio-nav-open');
    button.setAttribute('aria-expanded', String(open));
  });
  nav.addEventListener('keydown', event => { if (event.key === 'Escape') { close(); button.focus(); } });
  list.addEventListener('click', event => { if (event.target.closest('a')) close(); });
  window.addEventListener('resize', () => { if (window.innerWidth > 900) close(); });
})();
