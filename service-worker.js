
self.addEventListener('install', function(e) {
  e.waitUntil(
    caches.open('tierschutz-cache').then(function(cache) {
      return cache.addAll([
        '/',
        '/static/icon-512.png'
      ]);
    })
  );
});

self.addEventListener('fetch', function(e) {
  e.respondWith(
    caches.match(e.request).then(function(response) {
      return response || fetch(e.request);
    })
  );
});
