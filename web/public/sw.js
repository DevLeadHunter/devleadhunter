/* DevLeadHunter service worker — Web Push notifications (mobile PWA). */

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch (e) {
    data = {}
  }
  const title = data.title || 'DevLeadHunter'
  const options = {
    body: data.body || '',
    icon: '/android-chrome-192x192.png',
    badge: '/android-chrome-192x192.png',
    data: { url: data.url || '/dashboard' },
    tag: data.tag || undefined,
  }
  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const targetUrl = (event.notification.data && event.notification.data.url) || '/dashboard'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // An already-open PWA window is routed in-app via postMessage: on iOS a
      // client.navigate() is ignored and the tab just refocuses on its current
      // page (the reported "opens the dashboard home" bug). Only a cold start
      // falls back to openWindow, which lands straight on the target URL.
      for (const client of clientList) {
        if (client.url.startsWith(self.location.origin) && 'focus' in client) {
          client.postMessage({ type: 'notification-navigate', url: targetUrl })
          return client.focus()
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl)
      }
      return undefined
    }),
  )
})
