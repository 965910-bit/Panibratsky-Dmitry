// js/analytics.js – с сохранением города и координат
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
            sessionId: getSessionId()
        });
        localStorage.setItem(collection, JSON.stringify(events));
        console.log(`Событие сохранено: ${collection}`, data);
    }

    let sessionId = null;

    function getSessionId() {
        if (!sessionId) {
            sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        }
        return sessionId;
    }

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
            country: null,
            region: null,
            city: null,
            lat: null,
            lon: null
        };
        let sessions = JSON.parse(localStorage.getItem('sessions') || '[]');
        sessions.push(sessionMeta);
        localStorage.setItem('sessions', JSON.stringify(sessions));
        console.log('Новая сессия создана:', sessionMeta);

        // Асинхронное определение геолокации (страна, регион, город, координаты)
        fetch('https://ipapi.co/json/')
            .then(res => res.json())
            .then(data => {
                const country = data.country_name || data.country || 'Unknown';
                const region = data.region || '';
                const city = data.city || '';
                const lat = data.latitude;
                const lon = data.longitude;
                let sessions2 = JSON.parse(localStorage.getItem('sessions') || '[]');
                if (sessions2.length > 0) {
                    sessions2[sessions2.length - 1].country = country;
                    sessions2[sessions2.length - 1].region = region;
                    sessions2[sessions2.length - 1].city = city;
                    sessions2[sessions2.length - 1].lat = lat;
                    sessions2[sessions2.length - 1].lon = lon;
                    localStorage.setItem('sessions', JSON.stringify(sessions2));
                    console.log('Геоданные обновлены:', { country, region, city, lat, lon });
                }
            })
            .catch(err => console.warn('Не удалось определить геолокацию:', err));
    }

    document.addEventListener('DOMContentLoaded', () => {
        createSession();
        saveEvent('pageViews', { page: window.location.pathname });
    });

    // ... (остальные функции без изменений) ...
})();
