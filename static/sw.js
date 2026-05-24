/* House Price Prediction — Service Worker
   Caches static assets for fast loading & offline shell */

const CACHE_NAME = 'houseprice-v2';

const STATIC_ASSETS = [
  '/',
  '/predict',
  '/static/style.css',
  '/static/script.js',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/images/house1.png',
  '/static/images/house2.png',
  '/static/images/house3.png',
  '/static/images/house4.png',
  '/static/images/house5.png'
];

/* Install: cache static assets */
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

/* Activate: clean old caches */
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

/* Fetch: network-first for API, cache-first for static */
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Always go to network for API calls (predictions)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Cache-first for static assets
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then(cached => cached || fetch(event.request))
    );
    return;
  }

  // Network-first for pages (fall back to cache if offline)
  event.respondWith(
    fetch(event.request)
      .then(response => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
