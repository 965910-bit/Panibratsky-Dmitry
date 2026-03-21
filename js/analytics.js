// js/analytics.js
(function() {
    function saveEvent(collection, data) {
        let events = JSON.parse(localStorage.getItem(collection) || '[]');
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
    }

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
})();
