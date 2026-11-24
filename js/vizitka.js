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
  document.getElementById('short-template').addEventListener('click', () => {
    if ((message.value !== originalMessage || subject.value !== originalSubject) && !window.confirm('Заменить текущие тему и текст коротким письмом? Ваши правки будут потеряны.')) return;
    subject.value = 'Дмитрий Герасимов — операционное управление и логистика';
    message.value = `Здравствуйте!

Меня зовут Дмитрий Герасимов. Я операционный руководитель в логистике и SCM, рассматриваю постоянные руководящие роли. Буду рад обсудить, какие задачи стоят перед вашей компанией и чем мой опыт может быть полезен.

Мой подход — люди, клиент и процессы как единая система. Я основатель Академии цепи поставок и автор книги «Мост в цифровое будущее», написанной и готовящейся к изданию.

Портфолио: https://scm-news.ru/
Презентация с фото: https://scm-news.ru/documents/gerasimov-presentation.pdf
Резюме на hh.ru: https://surgut.hh.ru/resume/33d5f7abff115bad460039ed1f7166544f5263
Резюме на Зарплата.ру: https://surgut.zarplata.ru/resume/dc1875b3ff115ecddd0039ed1f6c487a655144
Телефон: +7 (982) 581-07-87
Почта: dmitry.gerasimov.2026@yandex.ru

С уважением,
Дмитрий Герасимов`;
    announce('Короткое письмо готово. Добавьте имя и причину обращения перед отправкой.');
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
