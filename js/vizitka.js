'use strict';
(() => {
  const message = document.getElementById('message');
  const subject = document.getElementById('subject');
  const email = document.getElementById('email');
  const status = document.getElementById('status');
  const originalMessage = message.value;
  const originalSubject = subject.value;
  const announce = text => { status.textContent = text; };
  document.getElementById('copy').addEventListener('click', async () => {
    if (!message.value.trim()) { announce('Введите текст визитки.'); return; }
    try {
      if (!navigator.clipboard || typeof navigator.clipboard.writeText !== 'function') throw Error('unavailable');
      await navigator.clipboard.writeText(message.value);
      announce('Текст скопирован. Откройте нужный чат и вставьте сообщение.');
    } catch { message.focus(); message.select(); announce('Не удалось скопировать автоматически. Выделенный текст можно скопировать вручную.'); }
  });
  document.getElementById('reset').addEventListener('click', () => {
    // Confirm before overwriting a personalised message.
    if ((message.value !== originalMessage || subject.value !== originalSubject) && !window.confirm('Вернуть исходные тему и текст? Ваши правки будут потеряны.')) return;
    message.value = originalMessage; subject.value = originalSubject; announce('Исходный текст восстановлен.');
  });
  document.getElementById('email-button').addEventListener('click', () => {
    const address = email.value.trim();
    // One address only; prevent CR/LF and mailto header injection.
    if (!address || address.length > 254 || !/^[A-Za-z0-9.!#$%&'*+\/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$/.test(address) || !email.validity.valid) {
      announce('Укажите один корректный адрес электронной почты.'); email.focus(); return;
    }
    if (!message.value.trim() || !subject.value.trim() || /[\r\n]/.test(subject.value)) { announce('Заполните тему и текст сообщения.'); return; }
    const link = `mailto:${encodeURIComponent(address).replace('%40', '@')}?subject=${encodeURIComponent(subject.value)}&body=${encodeURIComponent(message.value)}`;
    if (link.length > 12000) { announce('Текст слишком длинный для открытия почтового приложения. Скопируйте его вручную.'); return; }
    announce('Открываем почтовое приложение. Проверьте письмо и отправьте его самостоятельно.');
    window.location.href = link;
  });
})();
