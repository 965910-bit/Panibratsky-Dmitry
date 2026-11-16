const CACHE_NAME = 'scm-news-v2';
// Only cache public, static assets. Never cache forms or private dashboard data.
const OFFLINE_URLS = ['./', './trends.html', './icons/android/launchericon-192x192.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(OFFLINE_URLS)));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('scm-news-') && key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  // Network first: changes are visible immediately; only the offline shell is cached.
  if (request.mode === 'navigate' && (url.pathname === '/' || url.pathname === '/trends.html')) {
    event.respondWith(fetch(request).catch(() => caches.match(url.pathname === '/' ? './' : './trends.html')));
  }
});
