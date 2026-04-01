let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  document.querySelectorAll('.install-app-btn, #installAppBtn, #installAppBtnFooter').forEach(btn => {
    btn.style.display = 'inline-block';
  });
});

async function triggerInstall() {
  if (!deferredPrompt) {
    alert('Установка не поддерживается или приложение уже установлено.');
    return;
  }
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  console.log(`User response to the install prompt: ${outcome}`);
  deferredPrompt = null;
  document.querySelectorAll('.install-app-btn, #installAppBtn, #installAppBtnFooter').forEach(btn => {
    btn.style.display = 'none';
  });
}

document.querySelectorAll('.install-app-btn, #installAppBtn, #installAppBtnFooter').forEach(btn => {
  btn.addEventListener('click', triggerInstall);
});

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
