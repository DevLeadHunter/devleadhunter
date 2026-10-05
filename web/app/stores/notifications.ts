import type { Ref } from 'vue'
import type { NotificationHistory } from '~/services/notificationsService'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { NotificationsService } from '~/services/notificationsService'
import { useUserStore } from '~/stores/user'

const UNREAD_COUNT_POLL_INTERVAL_MS: number = 60_000

/** Pinia store for the count of unread notifications, shown on the tab bar of the installed app. */
// Pinia ne fournit pas de type nommé pour un store : TypeScript l'élide, il est inécrivable.
// eslint-disable-next-line @typescript-eslint/typedef
export const useNotificationStore = defineStore('notifications', () => {
  const userStore: ReturnType<typeof useUserStore> = useUserStore()

  const unreadCount: Ref<number> = ref(0)

  let pollTimer: ReturnType<typeof setInterval> | null = null

  /**
   * Ask the server how many notifications are still unread.
   * @returns A promise resolved once the count is up to date, or kept after a failed look.
   */
  async function refreshUnreadCount(): Promise<void> {
    if (!userStore.token) return
    try {
      const firstPage: NotificationHistory = await NotificationsService.getHistory(undefined, 1)
      unreadCount.value = firstPage.unread_count
    } catch {
      // Kept as it was until the next look.
    }
  }

  /**
   * Take the count a notification list just read, or changed by marking notifications read.
   * @param count - The unread count now.
   */
  function setUnreadCount(count: number): void {
    unreadCount.value = count
  }

  /** Look at the count again when the app comes back to the foreground. */
  function refreshWhenVisible(): void {
    if (document.visibilityState === 'visible') void refreshUnreadCount()
  }

  /** Follow the unread count while the tab bar shows it. */
  function startWatching(): void {
    if (pollTimer !== null) return
    void refreshUnreadCount()
    pollTimer = setInterval(refreshWhenVisible, UNREAD_COUNT_POLL_INTERVAL_MS)
    document.addEventListener('visibilitychange', refreshWhenVisible)
  }

  /** Stop following the unread count. */
  function stopWatching(): void {
    if (pollTimer === null) return
    clearInterval(pollTimer)
    pollTimer = null
    document.removeEventListener('visibilitychange', refreshWhenVisible)
  }

  return { unreadCount, refreshUnreadCount, setUnreadCount, startWatching, stopWatching }
})
