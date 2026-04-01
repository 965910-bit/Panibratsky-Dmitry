// install-prompt.js
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  // Показываем все кнопки установки
  document.querySelectorAll('.install-app-btn, #installAppBtn, #installAppBtnFooter').forEach(btn => {
    btn.style.display = 'inline-block';
  });
});

async function triggerInstall() {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  console.log(`User response to the install prompt: ${outcome}`);
  deferredPrompt = null;
  // Скрываем кнопки после установки или отказа (можно оставить видимыми, но они не будут работать до следующего beforeinstallprompt)
  document.querySelectorAll('.install-app-btn, #installAppBtn, #installAppBtnFooter').forEach(btn => {
    btn.style.display = 'none';
  });
}

// Навешиваем обработчики на все кнопки
document.querySelectorAll('.install-app-btn, #installAppBtn, #installAppBtnFooter').forEach(btn => {
  btn.addEventListener('click', triggerInstall);
});

// Для iOS (показываем инструкцию)
const isIos = () => {
  const userAgent = window.navigator.userAgent.toLowerCase();
  return /iphone|ipad|ipod/.test(userAgent);
};

if (isIos() && !window.navigator.standalone) {
  document.querySelectorAll('.install-app-btn, #installAppBtn, #installAppBtnFooter').forEach(btn => {
    btn.style.display = 'inline-block';
    btn.textContent = '📱 Установить (iOS)';
    btn.onclick = () => {
      alert('Нажмите «Поделиться» → «На экран «Домой»»');
    };
  });
}
