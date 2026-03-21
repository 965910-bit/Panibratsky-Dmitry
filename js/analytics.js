// js/analytics.js
(function() {
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
        console.log(`Событие сохранено: ${collection}`, data);
    }

    document.addEventListener('DOMContentLoaded', function() {
        saveEvent('pageViews', { page: window.location.pathname });

        document.addEventListener('click', function(e) {
            const link = e.target.closest('a[download]');
            if (link) {
                const fileName = link.getAttribute('download') || link.href.split('/').pop();
                saveEvent('downloads', { fileName: fileName });
                console.log('Скачивание зафиксировано:', fileName);
            }
        });

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
