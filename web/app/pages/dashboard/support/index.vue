<template>
  <div class="space-y-5">
    <UiPageHeader eyebrow="Aide" title="Support" description="Vos demandes et leurs réponses, au même endroit.">
      <template #actions>
        <button
          type="button"
          class="app-btn-secondary h-11 px-4 text-sm whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50 @2xl:pointer-fine:h-9 @2xl:pointer-fine:text-xs"
          :disabled="isLoading"
          @click="loadTickets"
        >
          <UIcon name="i-lucide-refresh-cw" :class="['h-3.5 w-3.5', isLoading && 'animate-spin']" />
          Actualiser
        </button>
      </template>
      <template #primary-action>
        <NuxtLink
          to="/dashboard/support/new"
          class="app-btn-primary h-11 px-4 text-sm whitespace-nowrap @2xl:pointer-fine:h-9 @2xl:pointer-fine:text-xs"
        >
          <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
          Nouveau ticket
        </NuxtLink>
      </template>
    </UiPageHeader>

    <UiChipFilters v-if="isAdmin" v-model="activeStatus" :options="STATUS_FILTERS" label="Statut des tickets" />

    <UiLoader v-if="isLoading" label="Chargement des tickets…" />

    <div v-else-if="filteredTickets.length" class="grid gap-3 @3xl:grid-cols-2">
      <NuxtLink
        v-for="ticket in filteredTickets"
        :key="ticket.id"
        :to="`/dashboard/support/${ticket.id}`"
        class="app-card group flex flex-col gap-3 p-4 transition-colors hover:border-[var(--app-ink-soft)]"
      >
        <div class="flex items-start justify-between gap-3">
          <p class="min-w-0 flex-1 truncate text-sm font-semibold text-[var(--app-ink)]">{{ ticket.subject }}</p>
          <span
            :class="['app-badge shrink-0 font-medium', SUPPORT_STATUS_PRESENTATION[ticket.status]?.badgeClass ?? '']"
          >
            {{ SUPPORT_STATUS_PRESENTATION[ticket.status]?.label ?? ticket.status }}
          </span>
        </div>

        <p class="line-clamp-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">{{ ticket.description }}</p>

        <div
          class="mt-auto flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-[var(--app-line-soft)] pt-3 text-xs text-[var(--app-ink-soft)]"
        >
          <span class="app-badge">{{ topicLabel(ticket.topic) }}</span>
          <span v-if="isAdmin" class="truncate">{{ ticket.user_name }}</span>
          <span v-if="isAdmin" aria-hidden="true">·</span>
          <span>{{ formatRelative(ticket.last_message_at || ticket.created_at) }}</span>
          <span v-if="ticket.attachments_count > 0" class="inline-flex items-center gap-1">
            <span aria-hidden="true">·</span>
            <UIcon name="i-lucide-paperclip" class="h-3 w-3" />
            {{ ticket.attachments_count }}
          </span>
          <UIcon
            name="i-lucide-arrow-right"
            class="ml-auto h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5"
          />
        </div>
      </NuxtLink>
    </div>

    <UiEmptyState
      v-else
      title="Aucun ticket"
      :description="
        isAdmin ? 'Rien pour ce filtre.' : 'Une question ou un souci ? Ouvrez un ticket, on vous répond ici.'
      "
    >
      <template #action>
        <NuxtLink to="/dashboard/support/new" class="app-btn-primary">
          <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
          Nouveau ticket
        </NuxtLink>
      </template>
    </UiEmptyState>
  </div>
</template>

<script lang="ts" setup>
import { SUPPORT_STATUS_PRESENTATION } from '~/constants/supportStatus'
import type { UseToastReturn } from '~/types/Composables'
import type { SupportWebsocketEvent } from '~/types/SupportListPage'
import type { SelectFieldOption } from '~/types/SelectField'
import type { ComputedRef, Ref } from 'vue'
import type { SupportTicketStatus, SupportTicketSummary } from '~/types'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useUserStore } from '~/stores/user'
import { SupportService } from '~/services/supportService'
import { useToast } from '~/composables/useToast'
import { isPlatformAdmin } from '~/utils/userRoles'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

/** Status filters offered to admins (members see all their tickets). */
const STATUS_FILTERS: SelectFieldOption[] = [
  { value: 'open', label: 'Ouverts' },
  { value: 'waiting_support', label: 'Attente support' },
  { value: 'waiting_user', label: 'Attente client' },
  { value: 'resolved', label: 'Résolus' },
  { value: 'closed', label: 'Fermés' },
  { value: 'all', label: 'Tous' },
]

/** Human labels for ticket statuses. */
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

const isAdmin: ComputedRef<boolean> = computed((): boolean => isPlatformAdmin(userStore.user?.role))
const scope: ComputedRef<'all' | 'mine'> = computed((): 'all' | 'mine' => (isAdmin.value ? 'all' : 'mine'))

// Les membres voient tous leurs tickets ; les admins arrivent sur la file ouverte.
const activeStatus: Ref<string> = ref(isAdmin.value ? 'open' : 'all')

/** Tickets sorted by latest activity, filtered by the active status. */
const filteredTickets: ComputedRef<SupportTicketSummary[]> = computed((): SupportTicketSummary[] => {
  const sorted: SupportTicketSummary[] = tickets.value
    .slice()
    .sort((a: SupportTicketSummary, b: SupportTicketSummary): number => {
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
 * Format a timestamp as a short relative label.
 * @param value - ISO timestamp.
 * @returns Relative label (e.g. « il y a 3 h »).
 */
function formatRelative(value: string): string {
  const date: Date = new Date(value)
  const diffMinutes: number = Math.floor((Date.now() - date.getTime()) / (1000 * 60))
  const diffHours: number = Math.floor(diffMinutes / 60)
  const diffDays: number = Math.floor(diffHours / 24)

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
    const includeClosed: boolean = activeStatus.value === 'closed' || activeStatus.value === 'all'
    const status: string | undefined =
      activeStatus.value === 'all' ? undefined : (activeStatus.value as SupportTicketStatus)
    tickets.value = await SupportService.getTickets({
      scope: scope.value,
      status: status as SupportTicketStatus | undefined,
      includeClosed,
    })
  } catch {
    toast.error('Impossible de charger les tickets pour le moment.')
  } finally {
    isLoading.value = false
  }
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
        const author: unknown = event.data?.user_name
        if (author && author !== userStore.user?.name) {
          toast.info(`Nouveau ticket créé par ${String(author)}`)
        }
      }
      void loadTickets()
      break
    }
    case 'ticket.updated': {
      const existing: SupportTicketSummary | undefined = tickets.value.find(
        (t: SupportTicketSummary): boolean => t.id === event.data?.id,
      )
      if (existing) Object.assign(existing, event.data)
      else void loadTickets()
      break
    }
    case 'ticket.message': {
      const senderId: unknown = event.data?._sender_id
      const ticketUserId: unknown = event.data?.user_id
      const currentUserId: number | undefined = userStore.user?.id as number | undefined
      const shouldNotify: boolean = Boolean(
        senderId && currentUserId && senderId !== currentUserId && (ticketUserId === currentUserId || isAdmin.value),
      )
      if (shouldNotify) {
        toast.info(`${String(event.data?._sender_name)} a répondu à « ${String(event.data?.subject || 'un ticket')} »`)
      }
      const ticket: SupportTicketSummary | undefined = tickets.value.find(
        (t: SupportTicketSummary): boolean => t.id === event.data?.id,
      )
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
  const token: string | null = userStore.token
  if (!token) return

  try {
    const apiUrl: URL = new URL(runtimeConfig.public.apiBase)
    apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
    apiUrl.pathname = `${apiUrl.pathname.replace(/\/$/, '')}/api/v1/support/tickets/ws`
    apiUrl.searchParams.set('token', token)

    const ws: WebSocket = new WebSocket(apiUrl.toString())
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
