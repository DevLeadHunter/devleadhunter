<template>
  <div class="mx-auto max-w-2xl space-y-5">
    <button
      type="button"
      class="inline-flex items-center gap-1.5 text-sm text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
      @click="goBack"
    >
      <UIcon name="i-lucide-arrow-left" class="h-4 w-4" />
      Retour
    </button>

    <div v-if="isLoading" class="app-card p-8">
      <UiLoader label="Chargement de la notification…" />
    </div>

    <div v-else-if="!notification" class="app-card p-8 text-center text-sm text-[var(--app-ink-soft)]">
      Cette notification est introuvable ou a expiré.
    </div>

    <div v-else class="app-card overflow-hidden p-0">
      <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
        <span
          class="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
          :class="presentation.tile"
        >
          <UIcon :name="presentation.icon" class="h-5 w-5" />
        </span>
        <div class="min-w-0 flex-1">
          <h1 class="text-lg font-semibold [overflow-wrap:anywhere] break-words text-[var(--app-ink)]">
            <UiArrowText :text="notification.title" />
          </h1>
          <p class="mt-0.5 text-xs text-[var(--app-faint)]">{{ formatDateTime(notification.created_at) }}</p>
        </div>
      </div>

      <div class="px-5 py-5">
        <p
          class="text-sm leading-relaxed [overflow-wrap:anywhere] break-words whitespace-pre-wrap text-[var(--app-ink)]"
        >
          <UiArrowText :text="notification.body" />
        </p>
      </div>

      <div v-if="hasTarget" class="border-t border-[var(--app-line)] px-5 py-4">
        <NuxtLink :to="notification.url" class="app-btn-primary inline-flex">
          {{ targetLabel }}
          <UIcon name="i-lucide-arrow-right" class="h-4 w-4" />
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { NotificationItem } from '~/services/notificationsService'
import type { NotificationLevelPresentation } from '~/types/UiNotificationList'
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'
import { NotificationsService } from '~/services/notificationsService'
import { notificationPresentation } from '~/constants/notificationLevels'
import { parseApiDate } from '~/utils/date'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const route: ReturnType<typeof useRoute> = useRoute()
const router: ReturnType<typeof useRouter> = useRouter()

const notification: Ref<NotificationItem | null> = ref(null)
const isLoading: Ref<boolean> = ref(true)

const presentation: ComputedRef<NotificationLevelPresentation> = computed(
  (): NotificationLevelPresentation => notificationPresentation(notification.value?.level ?? 'info'),
)

const hasTarget: ComputedRef<boolean> = computed((): boolean => {
  const url: string = notification.value?.url ?? ''
  return Boolean(url) && url !== '/dashboard'
})

const targetLabel: ComputedRef<string> = computed((): string => {
  switch (notification.value?.category) {
    case 'sale':
      return 'Voir la vente'
    case 'email':
    case 'demo':
      return 'Voir le prospect'
    case 'sms':
      return notification.value?.url?.startsWith('/dashboard/my-prospects') ? 'Voir le prospect' : 'Voir les SMS'
    default:
      return 'Ouvrir'
  }
})

/**
 * Format an ISO timestamp to a full French date-time.
 * @param iso - The ISO timestamp.
 * @returns The formatted date-time.
 */
function formatDateTime(iso: string): string {
  return parseApiDate(iso).toLocaleString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Go back in history, or to the dashboard when opened cold from a push. */
function goBack(): void {
  if (window.history.length > 1) {
    router.back()
  } else {
    void navigateTo('/dashboard')
  }
}

onMounted(async (): Promise<void> => {
  const id: number = Number(route.params.id)
  if (!Number.isFinite(id)) {
    isLoading.value = false
    return
  }
  try {
    notification.value = await NotificationsService.getOne(id)
    if (!notification.value.read) {
      await NotificationsService.markRead(id).catch((): void => {})
    }
  } catch {
    notification.value = null
  } finally {
    isLoading.value = false
  }
})
</script>
