const CACHE_NAME = 'scm-news-v3';
const OFFLINE_URL = './offline.html';
// Only public pages receive an offline fallback. Forms, APIs and workspaces are never cached.
const PUBLIC_PAGES = new Set([
  '/', '/index.html', '/about.html', '/blog.html', '/scm-problems.html', '/career.html',
  '/contact.html', '/experience.html', '/expertise.html', '/prompts.html', '/trends.html',
  '/calculators.html', '/certificates.html', '/projects.html', '/business-plan.html',
  '/tools.html', '/wiki.html', '/trends-logistics.html', '/analytics.html'
]);
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.add(OFFLINE_URL)));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('scm-news-') && key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || request.mode !== 'navigate' || !PUBLIC_PAGES.has(url.pathname)) return;
  event.respondWith(fetch(request).catch(async () => (await caches.open(CACHE_NAME)).match(OFFLINE_URL)));
});
