const CACHE_NAME = 'scm-news-v1';
const urlsToCache = [
  '.',
  'index.html',
  'about.html',
  'expertise.html',
  'experience.html',
  'trends.html',
  'contact.html',
  'data/news.json',
  'rss.xml',
  'sitemap.xml',
  'robots.txt',
  '1favicon.ico',
  'js/subscribe.js',
  'js/analytics.js',
  'js/register-sw.js',
  'icons/android/launchericon-192x192.png',
  'icons/android/launchericon-512x512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.map(key => {
        if (key !== CACHE_NAME) return caches.delete(key);
      })
    ))
  );
});
