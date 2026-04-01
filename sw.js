const CACHE_NAME = 'scm-news-v1';
const urlsToCache = [
  '/Panibratsky-Dmitry/',
  '/Panibratsky-Dmitry/index.html',
  '/Panibratsky-Dmitry/about.html',
  '/Panibratsky-Dmitry/expertise.html',
  '/Panibratsky-Dmitry/experience.html',
  '/Panibratsky-Dmitry/trends.html',
  '/Panibratsky-Dmitry/contact.html',
  '/Panibratsky-Dmitry/data/news.json',
  '/Panibratsky-Dmitry/rss.xml',
  '/Panibratsky-Dmitry/sitemap.xml',
  '/Panibratsky-Dmitry/robots.txt',
  '/Panibratsky-Dmitry/1favicon.ico',
  '/Panibratsky-Dmitry/js/subscribe.js',
  '/Panibratsky-Dmitry/js/analytics.js',
  '/Panibratsky-Dmitry/js/register-sw.js',
  '/Panibratsky-Dmitry/js/install-prompt.js',
  '/Panibratsky-Dmitry/icons/android/launchericon-192x192.png',
  '/Panibratsky-Dmitry/icons/android/launchericon-512x512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.pathname.includes('/data/news.json')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseClone);
          });
          return response;
        })
        .catch(() => caches.match(event.request))
    );
  } else {
    event.respondWith(
      caches.match(event.request).then(response => response || fetch(event.request))
    );
  }
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
