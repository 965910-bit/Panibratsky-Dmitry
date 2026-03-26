document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('subscribeForm');
    const statusDiv = document.getElementById('subscribeStatus');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const emailInput = document.getElementById('subscribeEmail');
        const email = emailInput.value.trim();

        const emailRegex = /^[^\s@]+@([^\s@]+\.)+[^\s@]+$/;
        if (!emailRegex.test(email)) {
            showStatus('❌ Введите корректный email', 'error');
            return;
        }

        let subscribers = JSON.parse(localStorage.getItem('subscribers') || '[]');
        if (subscribers.some(s => s.email === email)) {
            showStatus('✅ Вы уже подписаны на новости!', 'success');
            emailInput.value = '';
            return;
        }

        const newSubscriber = {
            type: 'subscriber',
            email: email,
            timestamp: new Date().toISOString(),
            source: 'footer'
        };
        subscribers.push(newSubscriber);
        localStorage.setItem('subscribers', JSON.stringify(subscribers));

        // Используем BACKEND_URL, объявленный на странице (в contact.html)
        if (typeof BACKEND_URL !== 'undefined') {
            try {
                await fetch(BACKEND_URL, {
                    method: 'POST',
                    mode: 'no-cors',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(newSubscriber)
                });
                console.log('Подписчик отправлен на сервер');
            } catch (err) {
                console.error('Ошибка отправки на сервер:', err);
            }
        }

        showStatus('✅ Спасибо! Вы подписаны на новости.', 'success');
        emailInput.value = '';
    });

    function showStatus(message, type) {
        if (!statusDiv) return;
        statusDiv.innerHTML = message;
        statusDiv.style.color = type === 'error' ? '#dc2626' : '#10b981';
        statusDiv.style.fontSize = '12px';
        statusDiv.style.marginTop = '10px';
        setTimeout(() => {
            statusDiv.innerHTML = '';
        }, 4000);
    }
});
