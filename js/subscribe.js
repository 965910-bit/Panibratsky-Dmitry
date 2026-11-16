document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('subscribeForm');
    const status = document.getElementById('subscribeStatus');
    if (!form) return;
    // No verified subscription backend is configured. Do not claim success or store personal data locally.
    form.addEventListener('submit', function (event) {
        event.preventDefault();
        if (status) {
            status.textContent = 'Подписка временно недоступна. Свяжитесь с нами через страницу контактов.';
            status.style.color = '#b91c1c';
            status.setAttribute('role', 'status');
        }
    });
});
