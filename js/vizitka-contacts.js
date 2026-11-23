'use strict';
(() => {
  // Session memory only. This is deliberately not a protected admin backend.
  const input = document.getElementById('contact-input');
  const select = document.getElementById('contact-select');
  const email = document.getElementById('email');
  const status = document.getElementById('contacts-status');
  let contacts = [];
  const valid = value => value.length <= 254 && /^[A-Za-z0-9.!#$%&'*+\/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$/.test(value);
  function render(selected = '') {
    select.replaceChildren();
    const placeholder = document.createElement('option'); placeholder.value = ''; placeholder.textContent = contacts.length ? 'Выберите адресата' : 'Список пуст'; select.append(placeholder);
    for (const contact of contacts) {
      const option = document.createElement('option'); option.value = contact.address; option.textContent = contact.address + (contact.marked ? ' — отмечено вручную' : ''); select.append(option);
    }
    select.value = selected;
  }
  document.getElementById('contacts-load').addEventListener('click', () => {
    const lines = input.value.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    if (!lines.length || lines.length > 100 || lines.some(s => !valid(s))) { status.textContent = 'Укажите от 1 до 100 корректных адресов, каждый с новой строки. Список не изменён.'; return; }
    if (contacts.length && !window.confirm('Заменить список и сбросить ручные отметки?')) return;
    const seen = new Set(); contacts = [];
    for (const address of lines) { const key = address.toLowerCase(); if (!seen.has(key)) {seen.add(key); contacts.push({address,marked:false});} }
    input.value = ''; render(); status.textContent = `Подготовлено контактов: ${contacts.length}. Ничего не отправлено.`;
  });
  document.getElementById('contact-use').addEventListener('click', () => {
    const contact = contacts.find(c => c.address === select.value);
    if (!contact) { status.textContent = 'Сначала выберите адресата.'; return; }
    email.value = contact.address; email.focus(); status.textContent = 'Адрес выбран. Нажмите «Открыть письмо» и проверьте черновик.';
  });
  document.getElementById('contact-mark').addEventListener('click', () => {
    const contact = contacts.find(c => c.address === select.value);
    if (!contact) { status.textContent = 'Сначала выберите адресата.'; return; }
    contact.marked = !contact.marked; render(contact.address);
    status.textContent = contact.marked ? 'Отметка добавлена вручную. Доставка не подтверждена.' : 'Ручная отметка снята.';
  });
  document.getElementById('contacts-clear').addEventListener('click', () => {
    if ((contacts.length || input.value.trim()) && !window.confirm('Очистить список и все ручные отметки?')) return;
    contacts = []; input.value = ''; email.value = ''; render(); status.textContent = 'Список очищен.';
  });
})();
