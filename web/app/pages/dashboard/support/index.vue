<template>
  <div class="mx-auto max-w-3xl space-y-8">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 class="text-3xl font-bold text-[var(--app-ink)]">Support</h1>
        <p class="text-muted mt-2 text-sm leading-relaxed">Vos demandes et leurs réponses, au même endroit.</p>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <button
          type="button"
          class="btn-secondary h-9 min-h-9 px-2.5"
          title="Actualiser"
          :disabled="isLoading"
          @click="loadTickets"
        >
          <UIcon name="i-lucide-rotate-cw" :class="['h-4 w-4', isLoading ? 'animate-spin' : '']" />
        </button>
        <NuxtLink to="/dashboard/support/new" class="btn-primary gap-2">
          <UIcon name="i-lucide-plus" class="h-4 w-4" />
          Nouveau ticket
        </NuxtLink>
      </div>
    </div>

    <div v-if="isAdmin" class="flex flex-wrap gap-2">
      <button
        v-for="filter in STATUS_FILTERS"
        :key="filter.value"
        type="button"
        :class="[
          'rounded-full border px-3 py-1 text-xs transition-colors',
          activeStatus === filter.value
            ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-surface)]'
            : 'border-[var(--app-line)] text-[var(--app-ink)] hover:bg-[var(--app-surface-2)]',
        ]"
        @click="updateStatus(filter.value)"
      >
        {{ filter.label }}
      </button>
    </div>

    <UiLoader v-if="isLoading" />

    <div v-else-if="filteredTickets.length" class="space-y-2">
      <NuxtLink
        v-for="ticket in filteredTickets"
        :key="ticket.id"
        :to="`/dashboard/support/${ticket.id}`"
        class="block rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3.5 transition-colors hover:border-[var(--app-ink-soft)]"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-semibold text-[var(--app-ink)]">{{ ticket.subject }}</p>
            <p class="text-muted mt-1 line-clamp-1 text-xs leading-relaxed">{{ ticket.description }}</p>
            <p class="text-muted mt-1.5 flex flex-wrap items-center gap-x-2 text-xs">
              <span v-if="isAdmin">{{ ticket.user_name }}</span>
              <span v-if="isAdmin" aria-hidden="true">·</span>
              <span>{{ topicLabel(ticket.topic) }}</span>
              <span aria-hidden="true">·</span>
              <span>{{ formatRelative(ticket.last_message_at || ticket.created_at) }}</span>
              <span v-if="ticket.attachments_count > 0" class="inline-flex items-center gap-1">
                <span aria-hidden="true">·</span>
                <UIcon name="i-lucide-paperclip" class="h-3 w-3" />
                {{ ticket.attachments_count }}
              </span>
            </p>
          </div>
          <span :class="['app-badge shrink-0 font-medium', statusBadgeClass(ticket.status)]">
            {{ statusLabel(ticket.status) }}
          </span>
        </div>
      </NuxtLink>
    </div>

    <div
      v-else
      class="flex flex-col items-center gap-3 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-6 py-14 text-center"
    >
      <span class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--app-surface-2)]">
        <UIcon name="i-lucide-life-buoy" class="h-5 w-5 text-[var(--app-ink-soft)]" />
      </span>
      <p class="text-sm font-medium text-[var(--app-ink)]">Aucun ticket</p>
      <p class="text-muted max-w-xs text-sm leading-relaxed">
        {{ isAdmin ? 'Rien pour ce filtre.' : 'Une question ou un souci ? Ouvrez un ticket, on vous répond ici.' }}
      </p>
      <NuxtLink to="/dashboard/support/new" class="btn-primary mt-1 gap-2">
        <UIcon name="i-lucide-plus" class="h-4 w-4" />
        Nouveau ticket
      </NuxtLink>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { SupportWebsocketEvent } from '~/types/SupportListPage'
import type { ComputedRef, Ref } from 'vue'
import type { SupportTicketStatus, SupportTicketSummary } from '~/types'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useUserStore } from '~/stores/user'
import { useToast } from '~/composables/useToast'
import { SupportService } from '~/services/supportService'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

/** Status filters offered to admins (members see all their tickets). */
const STATUS_FILTERS: Array<{ value: string; label: string }> = [
  { value: 'open', label: 'Ouverts' },
  { value: 'waiting_support', label: 'Attente support' },
  { value: 'waiting_user', label: 'Attente client' },
  { value: 'resolved', label: 'Résolus' },
  { value: 'closed', label: 'Fermés' },
  { value: 'all', label: 'Tous' },
]

/** Human labels for ticket statuses. */
const STATUS_LABELS: Record<string, string> = {
  open: 'Ouvert',
  waiting_support: 'Attente support',
  waiting_user: 'Attente client',
  resolved: 'Résolu',
  closed: 'Fermé',
}

/** Human labels for ticket topics. */
const TOPIC_LABELS: Record<string, string> = {
  credits_billing: 'Crédits & facturation',
  missing_results: 'Résultats manquants',
  bug_report: 'Signalement de bug',
  refund_credits: 'Remboursement crédits',
  refund_payment: 'Remboursement paiement',
  feature_request: 'Suggestion',
  other: 'Autre',
}

const toast: UseToastReturn = useToast()
const userStore: ReturnType<typeof useUserStore> = useUserStore()
const runtimeConfig: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()

const tickets: Ref<SupportTicketSummary[]> = ref([])
const isLoading: Ref<boolean> = ref(false)
const websocketRef: Ref<WebSocket | null> = ref(null)

const isAdmin: ComputedRef<boolean> = computed((): boolean => userStore.user?.role === 'ADMIN')
const scope: ComputedRef<'all' | 'mine'> = computed((): 'all' | 'mine' => (isAdmin.value ? 'all' : 'mine'))

// Les membres voient tous leurs tickets ; les admins arrivent sur la file ouverte.
const activeStatus: Ref<string> = ref(isAdmin.value ? 'open' : 'all')

/** Tickets sorted by latest activity, filtered by the active status. */
const filteredTickets: ComputedRef<SupportTicketSummary[]> = computed((): SupportTicketSummary[] => {
  const sorted = tickets.value.slice().sort((a: SupportTicketSummary, b: SupportTicketSummary): number => {
    const dateA: number = new Date(a.last_message_at || a.created_at).getTime()
    const dateB: number = new Date(b.last_message_at || b.created_at).getTime()
    return dateB - dateA
  })
  if (activeStatus.value === 'all') return sorted
  return sorted.filter((ticket: SupportTicketSummary): boolean => ticket.status === activeStatus.value)
})

/**
 * Human label for a ticket topic.
 * @param topic - Raw topic value.
 * @returns Localised label.
 */
function topicLabel(topic: SupportTicketSummary['topic']): string {
  return TOPIC_LABELS[topic] ?? 'Support'
}

/**
 * Human label for a ticket status.
 * @param status - Raw status value.
 * @returns Localised label.
 */
function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status
}

/**
 * Badge modifier for a status — reuses the app badge family (no ad-hoc colours).
 * @param status - Raw status value.
 * @returns The modifier class, or an empty string for the neutral badge.
 */
function statusBadgeClass(status: string): string {
  if (status === 'resolved') return 'app-badge--success'
  if (status === 'open' || status === 'waiting_support') return 'app-badge--progress'
  return ''
}

/**
 * Format a timestamp as a short relative label.
 * @param value - ISO timestamp.
 * @returns Relative label (e.g. « il y a 3 h »).
 */
function formatRelative(value: string): string {
  const date: Date = new Date(value)
  const diffMinutes = Math.floor((Date.now() - date.getTime()) / (1000 * 60))
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMinutes < 1) return "À l'instant"
  if (diffMinutes < 60) return `il y a ${diffMinutes} min`
  if (diffHours < 24) return `il y a ${diffHours} h`
  if (diffDays === 1) return 'Hier'
  if (diffDays < 7) return `il y a ${diffDays} jours`
  return date.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric', year: 'numeric' })
}

/**
 * Load the tickets matching the active scope and status.
 * @returns A promise resolving once loaded.
 */
async function loadTickets(): Promise<void> {
  try {
    isLoading.value = true
    const includeClosed = activeStatus.value === 'closed' || activeStatus.value === 'all'
    const status = activeStatus.value === 'all' ? undefined : (activeStatus.value as SupportTicketStatus)
    tickets.value = await SupportService.getTickets({ scope: scope.value, status, includeClosed })
  } catch {
    toast.error('Impossible de charger les tickets pour le moment.')
  } finally {
    isLoading.value = false
  }
}

/**
 * Switch the active status filter.
 * @param value - Status to activate.
 */
function updateStatus(value: string): void {
  if (activeStatus.value === value) return
  activeStatus.value = value
}

/**
 * Apply a realtime ticket event to the local list.
 * @param event - Incoming websocket payload.
 */
function handleWebsocketEvent(event: SupportWebsocketEvent): void {
  if (!event?.event) return

  switch (event.event) {
    case 'ticket.created': {
      if (isAdmin.value) {
        const author = event.data?.user_name
        if (author && author !== userStore.user?.name) {
          toast.info(`Nouveau ticket créé par ${String(author)}`)
        }
      }
      void loadTickets()
      break
    }
    case 'ticket.updated': {
      const existing = tickets.value.find((t: SupportTicketSummary): boolean => t.id === event.data?.id)
      if (existing) Object.assign(existing, event.data)
      else void loadTickets()
      break
    }
    case 'ticket.message': {
      const senderId = event.data?._sender_id
      const ticketUserId = event.data?.user_id
      const currentUserId = userStore.user?.id
      const shouldNotify =
        senderId && currentUserId && senderId !== currentUserId && (ticketUserId === currentUserId || isAdmin.value)
      if (shouldNotify) {
        toast.info(`${String(event.data?._sender_name)} a répondu à « ${String(event.data?.subject || 'un ticket')} »`)
      }
      const ticket = tickets.value.find((t: SupportTicketSummary): boolean => t.id === event.data?.id)
      if (ticket) Object.assign(ticket, event.data)
      else void loadTickets()
      break
    }
    default:
      break
  }
}

/**
 * Close the realtime connection, if any.
 */
function disconnectWebSocket(): void {
  if (websocketRef.value) {
    websocketRef.value.close()
    websocketRef.value = null
  }
}

/**
 * Open the realtime tickets connection (auto-retries on close).
 */
function connectWebSocket(): void {
  disconnectWebSocket()
  const token = userStore.token
  if (!token) return

  try {
    const apiUrl = new URL(runtimeConfig.public.apiBase)
    apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
    apiUrl.pathname = `${apiUrl.pathname.replace(/\/$/, '')}/api/v1/support/tickets/ws`
    apiUrl.searchParams.set('token', token)

    const ws = new WebSocket(apiUrl.toString())
    websocketRef.value = ws

    ws.onmessage = (event: MessageEvent): void => {
      try {
        handleWebsocketEvent(JSON.parse(event.data))
      } catch {
        // Événement illisible : on ignore plutôt que de casser la page.
      }
    }
    ws.onclose = (): void => {
      websocketRef.value = null
      setTimeout((): void => {
        if (!websocketRef.value) connectWebSocket()
      }, 5000)
    }
  } catch {
    // Pas de temps réel : la liste reste utilisable via le bouton Actualiser.
  }
}

watch([activeStatus, (): string => scope.value], (): void => {
  void loadTickets()
})

onMounted((): void => {
  void loadTickets()
  connectWebSocket()
})

onBeforeUnmount((): void => {
  disconnectWebSocket()
})
</script>
