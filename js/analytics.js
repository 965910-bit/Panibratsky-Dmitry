// js/analytics.js
(function() {
    // ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
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
            sessionId: localStorage.getItem('sessionId') || (() => {
                let id = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('sessionId', id);
                return id;
            })()
        });
        localStorage.setItem(collection, JSON.stringify(events));
        // console.log(`Событие сохранено: ${collection}`, data); // опционально
    }

    // ========== МЕТАДАННЫЕ СЕССИИ ==========
    if (!localStorage.getItem('sessionId')) {
        const sessionId = localStorage.getItem('sessionId');
        const sessionData = {
            sessionId: sessionId,
            startTime: new Date().toISOString(),
            referrer: document.referrer || 'direct',
            userAgent: navigator.userAgent,
            screenSize: `${screen.width}x${screen.height}`,
            language: navigator.language
        };
        let sessions = JSON.parse(localStorage.getItem('sessions') || '[]');
        sessions.push(sessionData);
        localStorage.setItem('sessions', JSON.stringify(sessions));
    }

    // ========== ВРЕМЯ НА СТРАНИЦЕ ==========
    let pageStartTime = Date.now();
    window.addEventListener('beforeunload', () => {
        const duration = Date.now() - pageStartTime;
        saveEvent('pageDurations', {
            page: window.location.pathname,
            duration: duration
        });
    });

    // ========== ГЛУБИНА ПРОКРУТКИ ==========
    let sentDepths = [];
    window.addEventListener('scroll', () => {
        const scrollPercent = (window.scrollY + window.innerHeight) / document.body.scrollHeight * 100;
        [25, 50, 75, 100].forEach(threshold => {
            if (scrollPercent >= threshold && !sentDepths.includes(threshold)) {
                sentDepths.push(threshold);
                saveEvent('scrollDepth', {
                    page: window.location.pathname,
                    depth: threshold
                });
            }
        });
    });

    // ========== СТАНДАРТНЫЕ СОБЫТИЯ ==========
    document.addEventListener('DOMContentLoaded', function() {
        // Просмотр страницы
        saveEvent('pageViews', { page: window.location.pathname });

        // Скачивания
        document.addEventListener('click', function(e) {
            const link = e.target.closest('a[download]');
            if (link) {
                const fileName = link.getAttribute('download') || link.href.split('/').pop();
                saveEvent('downloads', { fileName: fileName });
            }
        });

        // Видео
        const video = document.getElementById('myVideo');
        if (video) {
            video.addEventListener('play', () => {
                saveEvent('videoViews', { videoName: 'about_video' });
                // обновляем отображаемый счётчик, если есть
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
    });
})();
