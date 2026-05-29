const CACHE_NAME = 'xe-platform-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/manifest.json',
  '/static/img/icon-192.svg',
  '/static/img/icon-512.svg'
];

// Install: cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Fetch: serve from cache first, fallback to network
self.addEventListener('fetch', event => {
  // Don't cache API calls
  if (event.request.url.includes('/auth/') ||
      event.request.url.includes('/api/') ||
      event.request.url.includes('/payment/') ||
      event.request.url.includes('/crypto/') ||
      event.request.url.includes('/stocks/') ||
      event.request.url.includes('/exchange/') ||
      event.request.url.includes('/traffic-coin/') ||
      event.request.url.includes('/tradebot/') ||
      event.request.url.includes('/admin/') ||
      event.request.url.includes('/kyc/')) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then(cached => {
      // Return cached version first, then update
      const fetchPromise = fetch(event.request).then(response => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => cached);

      return cached || fetchPromise;
    })
  );
});

// Handle push notifications (future use)
self.addEventListener('push', event => {
  const data = event.data.json();
  self.registration.showNotification(data.title || 'XE平台', {
    body: data.body || '',
    icon: '/static/img/icon-192.svg'
  });
});
