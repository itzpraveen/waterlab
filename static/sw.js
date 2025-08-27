// Minimal service worker placeholder
self.addEventListener('install', (event) => {
  // Activate immediately
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  // Claim control so it starts managing pages asap
  event.waitUntil(self.clients.claim());
});

// No caching logic; acts as a stub to avoid 404s
self.addEventListener('fetch', () => {});

