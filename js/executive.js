(() => {
  const body = document.body;
  body.classList.add('js-ready');
  const theme = document.querySelector('.theme-toggle');
  try { if (localStorage.getItem('executive-theme') === 'light') body.classList.add('light'); } catch (_) {}
  function updateTheme() {
    const light = body.classList.contains('light');
    theme.setAttribute('aria-label', light ? 'Переключить тёмную тему' : 'Переключить светлую тему');
    theme.title = theme.getAttribute('aria-label');
    theme.firstElementChild.textContent = light ? '☾' : '☼';
  }
  updateTheme();
  theme.addEventListener('click', () => {
    body.classList.toggle('light');
    try { localStorage.setItem('executive-theme', body.classList.contains('light') ? 'light' : 'dark'); } catch (_) {}
    updateTheme();
  });

  const menuButton = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.site-nav');
  const closeMenu = () => { nav.classList.remove('open'); menuButton.setAttribute('aria-expanded', 'false'); };
  menuButton.addEventListener('click', () => {
    const isOpen = nav.classList.toggle('open');
    menuButton.setAttribute('aria-expanded', String(isOpen));
  });
  nav.addEventListener('click', event => { if (event.target.closest('a')) closeMenu(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && nav.classList.contains('open')) { closeMenu(); menuButton.focus(); } });
  window.addEventListener('resize', () => { if (window.innerWidth > 760) closeMenu(); });

  const form = document.getElementById('chat-form');
  const field = document.getElementById('chat-question');
  const messages = document.getElementById('chat-messages');
  const submit = form.querySelector('button');
  function addMessage(text, type, links = []) {
    const message = document.createElement('div');
    message.className = 'message ' + (type === 'user' ? 'user-message' : 'assistant-message');
    message.textContent = text;
    for (const source of links) {
      // Only links to known sections of this page are allowed in model responses.
      if (!['#cases', '#experience', '#expertise', '#contact'].includes(source.href)) continue;
      const anchor = document.createElement('a');
      anchor.className = 'chat-source';
      anchor.href = source.href;
      anchor.textContent = source.label;
      message.appendChild(anchor);
    }
    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
  }
  async function sendQuestion(question) {
    question = question.trim();
    if (!question || submit.disabled) return;
    if (question.length > 600) { addMessage('Вопрос слишком длинный. Пожалуйста, сократите его до 600 символов.', 'assistant'); return; }
    addMessage(question, 'user');
    field.value = '';
    submit.disabled = true;
    field.disabled = true;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 25000);
    try {
      const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }), signal: controller.signal });
      const data = await response.json();
      if (!response.ok || typeof data.answer !== 'string') throw new Error('unavailable');
      addMessage(data.answer, 'assistant', Array.isArray(data.sources) ? data.sources : []);
    } catch (_) {
      addMessage('Сейчас ассистент недоступен. Пожалуйста, воспользуйтесь контактами ниже — Дмитрий ответит лично.', 'assistant', [{href:'#contact',label:'Перейти к контактам ↗'}]);
    } finally {
      clearTimeout(timer);
      submit.disabled = false;
      field.disabled = false;
      field.focus();
    }
  }
  form.addEventListener('submit', event => { event.preventDefault(); sendQuestion(field.value); });
  document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => sendQuestion(button.dataset.question)));
})();
