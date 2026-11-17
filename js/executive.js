(() => {
  const body = document.body;
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

  const menuControl = document.getElementById('menu-check');
  const nav = document.querySelector('.site-nav');
  // The checkbox controls the menu without JavaScript; enhance close behavior only.
  const closeMenu = () => { menuControl.checked = false; };
  nav.addEventListener('click', event => { if (event.target.closest('a')) closeMenu(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && menuControl.checked) { closeMenu(); menuControl.focus(); } });
  window.addEventListener('resize', () => { if (window.innerWidth > 820) closeMenu(); });

  const form = document.getElementById('chat-form');
  const field = document.getElementById('chat-question');
  const messages = document.getElementById('chat-messages');
  const submit = form.querySelector('button');
  const status = document.getElementById('chat-status');
  const retry = document.getElementById('chat-retry');
  const suggestions = Array.from(document.querySelectorAll('[data-question]'));
  let available = false;
  let checking = false;
  function setAvailable(enabled) {
    available = enabled;
    field.disabled = !enabled;
    submit.disabled = !enabled;
    suggestions.forEach(button => { button.disabled = !enabled; });
  }
  async function checkAvailability() {
    if (checking) return;
    checking = true;
    setAvailable(false);
    retry.hidden = true;
    status.textContent = 'ПРОВЕРЯЕМ ПОДКЛЮЧЕНИЕ';
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch('/api/chat', { cache: 'no-store', signal: controller.signal });
      if (!response.ok || !(response.headers.get('content-type') || '').includes('application/json')) throw new Error('unavailable');
      const data = await response.json();
      if (data.configured !== true) throw new Error('unavailable');
      setAvailable(true);
      status.textContent = 'СЕРВИС ПОДКЛЮЧЁН · ОТВЕТ МОЖЕТ БЫТЬ НЕДОСТУПЕН';
    } catch (_) {
      status.textContent = 'ВРЕМЕННО НЕДОСТУПЕН · СВЯЖИТЕСЬ НАПРЯМУЮ';
      retry.hidden = false;
    } finally { clearTimeout(timer); checking = false; }
  }
  let observer;
  retry.addEventListener('click', () => { if (observer) observer.disconnect(); checkAvailability(); });
  // Do not probe an optional service until its section is near the viewport.
  // The visible button remains usable if IntersectionObserver is unsupported.
  const assistant = document.getElementById('assistant');
  if (assistant && typeof window.IntersectionObserver === 'function') {
    observer = new window.IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        observer.disconnect();
        checkAvailability();
      }
    }, { rootMargin: '200px' });
    observer.observe(assistant);
  }
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
    if (!question || !available || submit.disabled) return;
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
  suggestions.forEach(button => button.addEventListener('click', () => sendQuestion(button.dataset.question)));
})();
