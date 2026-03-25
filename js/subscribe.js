// Подписка на новости
document.addEventListener('DOMContentLoaded', () => {
    const subForm = document.getElementById('subscribeForm');
    if (subForm) {
        subForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const email = document.getElementById('subscribeEmail').value.trim();
            const statusDiv = document.getElementById('subscribeStatus');
            if (!email || !email.includes('@')) {
                statusDiv.innerHTML = '<span style="color: #ef4444;">Введите корректный email</span>';
                setTimeout(() => statusDiv.innerHTML = '', 3000);
                return;
            }
            let subscribers = JSON.parse(localStorage.getItem('subscribers') || '[]');
            if (!subscribers.includes(email)) {
                subscribers.push(email);
                localStorage.setItem('subscribers', JSON.stringify(subscribers));
                statusDiv.innerHTML = '<span style="color: #10b981;">✅ Спасибо! Вы подписаны.</span>';
                document.getElementById('subscribeEmail').value = '';
            } else {
                statusDiv.innerHTML = '<span style="color: #f59e0b;">Вы уже подписаны.</span>';
            }
            setTimeout(() => statusDiv.innerHTML = '', 5000);
        });
    }
});
