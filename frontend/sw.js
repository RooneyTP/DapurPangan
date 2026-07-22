// DapurPangan — Service Worker (PWA offline cache)
const CACHE_NAME = 'zephyrus-v1';
const ASSETS = [
  'index.html',
  'manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request).catch(() => {
        // Offline fallback: tetap tampilkan yang di-cache
        return caches.match('index.html');
      });
    })
  );
});
