// FocusGoals Service Worker (PWA & iOS Web Push)
const CACHE_NAME = 'focusgoals-v1';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

// Handle local notifications triggered via postMessage
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SHOW_NOTIFICATION') {
    const { title, options } = event.data;
    event.waitUntil(
      self.registration.showNotification(title, {
        icon: 'icon-192.png',
        badge: 'icon-192.png',
        vibrate: [200, 100, 200],
        ...options
      })
    );
  }
});

// Handle incoming Web Push (if push service is connected)
self.addEventListener('push', (event) => {
  let data = { title: '🎯 FocusGoals', body: 'У вас есть запланированная цель!' };
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body || 'Напоминание о выполнении задачи',
    icon: 'icon-192.png',
    badge: 'icon-192.png',
    tag: data.tag || 'focusgoals-alert',
    renotify: true,
    vibrate: [200, 100, 200],
    data: { url: data.url || './' }
  };

  event.waitUntil(
    self.registration.showNotification(data.title || '🎯 FocusGoals', options)
  );
});

// Click on notification focuses or opens the app window
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ('focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow('./');
      }
    })
  );
});
