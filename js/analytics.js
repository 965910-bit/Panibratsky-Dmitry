// js/analytics.js – расширенная версия с геолокацией и Telegram-уведомлениями
(function() {
    // ========== КОНФИГУРАЦИЯ ==========
    // Замените на свой токен бота и chat_id (получите у @BotFather и @userinfobot)
    const TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN';
    const TELEGRAM_CHAT_ID = 'YOUR_CHAT_ID';

    // Универсальная функция сохранения события
    function saveEvent(collection, data) {
        let events = localStorage.getItem(collection);
        try {
            events = JSON.parse(events);
            if (!Array.isArray(events)) events = [];
        } catch(e) {
            events = [];
        }
        events.push({
            ...data,
            timestamp: new Date().toISOString(),
            sessionId: getSessionId()
        });
        localStorage.setItem(collection, JSON.stringify(events));
        console.log(`Событие сохранено: ${collection}`, data);
    }

    // Получение или создание sessionId
    function getSessionId() {
        let id = localStorage.getItem('sessionId');
        if (!id) {
            id = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('sessionId', id);
            // Сохраняем метаданные сессии асинхронно, с геолокацией
            const sessionMeta = {
                sessionId: id,
                startTime: new Date().toISOString(),
                referrer: document.referrer || 'direct',
                userAgent: navigator.userAgent,
                screenSize: `${screen.width}x${screen.height}`,
                language: navigator.language,
                firstPage: window.location.pathname,
                country: null // будет заполнено позже
            };
            let sessions = JSON.parse(localStorage.getItem('sessions') || '[]');
            sessions.push(sessionMeta);
            localStorage.setItem('sessions', JSON.stringify(sessions));

            // Асинхронно получаем страну по IP
            fetch('https://ipapi.co/json/')
                .then(res => res.json())
                .then(data => {
                    const country = data.country_name || data.country || 'Unknown';
                    let sessions2 = JSON.parse(localStorage.getItem('sessions') || '[]');
                    if (sessions2.length > 0) {
                        sessions2[sessions2.length - 1].country = country;
                        localStorage.setItem('sessions', JSON.stringify(sessions2));
                        console.log('Страна определена:', country);
                    }
                })
                .catch(err => console.warn('Не удалось определить страну:', err));
        }
        return id;
    }

    // Отправка уведомления в Telegram
    function sendTelegramNotification(message) {
        if (!TELEGRAM_BOT_TOKEN || TELEGRAM_BOT_TOKEN === 'YOUR_BOT_TOKEN') return;
        const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: TELEGRAM_CHAT_ID,
                text: message,
                parse_mode: 'HTML'
            })
        }).catch(err => console.warn('Telegram уведомление не отправлено:', err));
    }

    // Функция для вычисления времени на странице
    let pageStartTime = Date.now();
    window.addEventListener('beforeunload', () => {
        const duration = Math.round((Date.now() - pageStartTime) / 1000);
        if (duration > 0) {
            saveEvent('pageDurations', {
                page: window.location.pathname,
                duration: duration
            });
        }
    });

    // Функция для отслеживания глубины прокрутки
    let sentDepths = [];
    window.addEventListener('scroll', () => {
        const scrollPercent = (window.scrollY + window.innerHeight) / document.body.scrollHeight * 100;
        const thresholds = [25, 50, 75, 100];
        thresholds.forEach(threshold => {
            if (scrollPercent >= threshold && !sentDepths.includes(threshold)) {
                sentDepths.push(threshold);
                saveEvent('scrollDepth', {
                    page: window.location.pathname,
                    depth: threshold
                });
            }
        });
    });

    // === Основные события ===
    document.addEventListener('DOMContentLoaded', function() {
        // Просмотр страницы
        saveEvent('pageViews', { page: window.location.pathname });

        // Скачивания
        document.addEventListener('click', function(e) {
            const link = e.target.closest('a[download]');
            if (link) {
                const fileName = link.getAttribute('download') || link.href.split('/').pop();
                saveEvent('downloads', { fileName: fileName });
                console.log('Скачивание зафиксировано:', fileName);
            }
        });

        // Видео
        const video = document.getElementById('myVideo');
        if (video) {
            video.addEventListener('play', () => {
                saveEvent('videoViews', { videoName: 'about_video' });
                console.log('Видео запущено, событие сохранено');
                const viewDisplay = document.getElementById('videoViewCountDisplay');
                if (viewDisplay) {
                    let views = localStorage.getItem('videoViews') ? (() => {
                        try {
                            let arr = JSON.parse(localStorage.getItem('videoViews'));
                            return Array.isArray(arr) ? arr.length : 0;
                        } catch(e) { return 0; }
                    })() : 0;
                    viewDisplay.textContent = views;
                }
            });
            console.log('Видео найдено, обработчик добавлен');
        } else {
            console.log('Элемент с id="myVideo" не найден');
        }

        // Форма обратной связи
        const feedbackForm = document.getElementById('feedbackForm');
        if (feedbackForm) {
            feedbackForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const name = document.getElementById('feedbackName').value;
                const email = document.getElementById('feedbackEmail').value;
                const message = document.getElementById('feedbackMessage').value;
                saveEvent('messages', { name, email, message });
                const statusDiv = document.getElementById('feedbackStatus');
                if (statusDiv) {
                    statusDiv.innerHTML = '<span style="color: #10b981;">Сообщение отправлено!</span>';
                } else {
                    alert('Сообщение отправлено!');
                }
                feedbackForm.reset();

                // Отправляем уведомление в Telegram
                const msg = `📩 <b>Новое сообщение с сайта</b>\n👤 Имя: ${escapeHtml(name)}\n📧 Email: ${escapeHtml(email)}\n💬 Сообщение: ${escapeHtml(message)}`;
                sendTelegramNotification(msg);
            });
        }
    });

    // Вспомогательная функция для экранирования HTML (для сообщения в Telegram)
    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>]/g, function(m) {
            if (m === '&') return '&amp;';
            if (m === '<') return '&lt;';
            if (m === '>') return '&gt;';
            return m;
        });
    }
})();
