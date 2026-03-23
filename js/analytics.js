// js/analytics.js – расширенная версия с сессиями при каждом заходе
(function() {
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
            sessionId: getSessionId() // используем актуальный sessionId
        });
        localStorage.setItem(collection, JSON.stringify(events));
        console.log(`Событие сохранено: ${collection}`, data);
    }

    // Получение или создание sessionId – теперь при каждом вызове создаётся новая сессия?
    // Нет, чтобы не плодить тысячи сессий, будем создавать новую сессию при загрузке страницы.
    // Для этого используем отдельный флаг.
    let sessionId = null;

    function getSessionId() {
        if (!sessionId) {
            sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        }
        return sessionId;
    }

    // Создаём новую сессию при загрузке страницы (DOMContentLoaded)
    function createSession() {
        const id = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        sessionId = id;
        const sessionMeta = {
            sessionId: id,
            startTime: new Date().toISOString(),
            referrer: document.referrer || 'direct',
            userAgent: navigator.userAgent,
            screenSize: `${screen.width}x${screen.height}`,
            language: navigator.language,
            firstPage: window.location.pathname,
            country: null
        };
        let sessions = JSON.parse(localStorage.getItem('sessions') || '[]');
        sessions.push(sessionMeta);
        localStorage.setItem('sessions', JSON.stringify(sessions));
        console.log('Новая сессия создана:', sessionMeta);

        // Асинхронно получаем страну по IP
        fetch('https://ipapi.co/json/')
            .then(res => res.json())
            .then(data => {
                const country = data.country_name || data.country || 'Unknown';
                // Обновляем последнюю сессию
                let sessions2 = JSON.parse(localStorage.getItem('sessions') || '[]');
                if (sessions2.length > 0) {
                    sessions2[sessions2.length - 1].country = country;
                    localStorage.setItem('sessions', JSON.stringify(sessions2));
                    console.log('Страна определена:', country);
                }
            })
            .catch(err => console.warn('Не удалось определить страну:', err));
    }

    // Создаём сессию при загрузке DOM
    document.addEventListener('DOMContentLoaded', () => {
        createSession();

        // Просмотр страницы
        saveEvent('pageViews', { page: window.location.pathname });
    });

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
        });
    }
})();
