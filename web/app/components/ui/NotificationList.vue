<template>
  <section>
    <div class="app-card p-0">
      <div class="flex items-center justify-between gap-3 border-b border-[var(--app-line)] px-4 py-3">
        <span class="flex items-center gap-2">
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Historique</h2>
          <span v-if="unreadCount > 0" class="app-badge app-badge--info">
            {{ unreadCount }} non lu{{ unreadCount > 1 ? 's' : '' }}
          </span>
        </span>
        <button
          v-if="unreadCount > 0"
          type="button"
          class="text-xs text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
          @click="markAllRead"
        >
          Tout marquer lu
        </button>
      </div>

      <div v-if="isLoading && items.length === 0" class="p-6">
        <UiLoader label="Chargement de l'historique…" />
      </div>

      <p v-else-if="items.length === 0" class="px-4 py-8 text-center text-sm text-[var(--app-ink-soft)]">
        Aucune notification pour l'instant.
      </p>

      <ul v-else class="divide-y divide-[var(--app-line)]">
        <li v-for="item in items" :key="item.id">
          <button
            type="button"
            class="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-[var(--app-surface-2)]"
            :class="item.read ? '' : 'bg-[var(--app-accent-soft)]/50'"
            @click="open(item)"
          >
            <span
              class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
              :class="notificationPresentation(item.level).tile"
            >
              <UIcon :name="notificationPresentation(item.level).icon" class="h-4 w-4" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="flex items-center gap-2">
                <span class="truncate text-sm font-medium text-[var(--app-ink)]">{{ item.title }}</span>
                <span v-if="!item.read" class="ml-auto h-2 w-2 shrink-0 rounded-full bg-[var(--app-accent-ink)]"></span>
              </span>
              <span class="mt-0.5 block truncate text-xs text-[var(--app-ink-soft)]">{{ item.body }}</span>
              <span class="mt-1 block text-[11px] text-[var(--app-faint)]">{{
                formatRelativeTime(item.created_at)
              }}</span>
            </span>
          </button>
        </li>
      </ul>

      <div v-if="hasMore" class="border-t border-[var(--app-line)] p-3">
        <button type="button" class="app-btn-secondary w-full text-xs" :disabled="isLoading" @click="loadMore">
          {{ isLoading ? 'Chargement…' : 'Charger plus' }}
        </button>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { NotificationHistory, NotificationItem } from '~/services/notificationsService'
import type { Ref } from 'vue'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { NotificationsService } from '~/services/notificationsService'
import { notificationPresentation } from '~/constants/notificationLevels'
import { formatRelativeTime } from '~/utils/date'

const PAGE_SIZE: number = 20

const items: Ref<NotificationItem[]> = ref([])
const unreadCount: Ref<number> = ref(0)
const isLoading: Ref<boolean> = ref(false)
const hasMore: Ref<boolean> = ref(false)
let pollTimer: ReturnType<typeof setInterval> | undefined

/**
 * Load the first page of the notification history.
 * @returns Nothing.
 */
async function load(): Promise<void> {
  isLoading.value = true
  try {
    const page: NotificationHistory = await NotificationsService.getHistory(undefined, PAGE_SIZE)
    items.value = page.items
    unreadCount.value = page.unread_count
    hasMore.value = page.items.length === PAGE_SIZE
  } finally {
    isLoading.value = false
  }
}

/**
 * Load the next page of older notifications and append them.
 * @returns Nothing.
 */
async function loadMore(): Promise<void> {
  const last: NotificationItem | undefined = items.value[items.value.length - 1]
  if (!last || isLoading.value) {
    return
  }
  isLoading.value = true
  try {
    const page: NotificationHistory = await NotificationsService.getHistory(last.id, PAGE_SIZE)
    items.value = [...items.value, ...page.items]
    unreadCount.value = page.unread_count
    hasMore.value = page.items.length === PAGE_SIZE
  } finally {
    isLoading.value = false
  }
}

/**
 * Mark a notification read (locally + server-side) then open its own detail page.
 * @param item - The clicked notification.
 * @returns Nothing.
 */
async function open(item: NotificationItem): Promise<void> {
  if (!item.read) {
    item.read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    await NotificationsService.markRead(item.id).catch((): void => {})
  }
  await navigateTo(`/dashboard/notifications/${item.id}`)
}

/**
 * Mark every notification of the user as read.
 * @returns Nothing.
 */
async function markAllRead(): Promise<void> {
  await NotificationsService.markAllRead().catch((): void => {})
  items.value = items.value.map((item: NotificationItem): NotificationItem => ({ ...item, read: true }))
  unreadCount.value = 0
}

/**
 * Merge notifications newer than the top of the list — near real-time, no reload.
 * @returns Nothing.
 */
async function refresh(): Promise<void> {
  if (document.visibilityState !== 'visible') {
    return
  }
  const page: NotificationHistory = await NotificationsService.getHistory(undefined, PAGE_SIZE)
  unreadCount.value = page.unread_count
  const newestId: number = items.value[0]?.id ?? 0
  const fresh: NotificationItem[] = page.items.filter((item: NotificationItem): boolean => item.id > newestId)
  if (fresh.length > 0) {
    items.value = [...fresh, ...items.value]
  }
}

onMounted((): void => {
  load().catch((): void => {})
  pollTimer = setInterval((): void => {
    refresh().catch((): void => {})
  }, 10000)
})

onBeforeUnmount((): void => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
})
</script>
