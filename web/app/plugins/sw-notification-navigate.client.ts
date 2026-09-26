/**
 * Route the PWA in-app when the service worker relays a notification tap.
 *
 * The service worker posts ``{ type: 'notification-navigate', url }`` to an
 * already-open window instead of a hard ``client.navigate`` (ignored on iOS),
 * and this listener turns it into a real router navigation. No-op during SSR
 * and where service workers are unavailable.
 */
export default defineNuxtPlugin((): void => {
  if (!import.meta.client || !('serviceWorker' in navigator)) {
    return
  }
  navigator.serviceWorker.addEventListener('message', (event: MessageEvent): void => {
    const data: { type?: string; url?: string } = event.data ?? {}
    if (data.type === 'notification-navigate' && typeof data.url === 'string' && data.url) {
      void navigateTo(data.url)
    }
  })
})
