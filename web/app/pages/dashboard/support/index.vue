<template>
  <div class="space-y-10">
    <header class="mb-6 space-y-4">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-2">
          <h1 class="text-lg leading-tight font-semibold text-[var(--app-ink)] md:text-xl">Tickets de support</h1>
          <p class="max-w-2xl text-sm text-[var(--app-ink-soft)]">
            Retrouvez toutes vos demandes au même endroit et reprenez les conversations en un clic. Les admins voient
            toute la file, les membres uniquement leurs tickets.
          </p>
        </div>
        <div class="flex w-full items-center gap-3 lg:ml-auto lg:w-auto">
          <button class="btn-secondary flex-1 gap-2 px-4 lg:flex-none" type="button" @click="refreshTickets">
            <UIcon name="i-lucide-rotate-cw" class="h-4 w-4" />
            <span class="lg:inline">Actualiser</span>
          </button>
          <NuxtLink to="/dashboard/support/new" class="btn-primary flex-1 gap-2 px-4 lg:flex-none">
            <UIcon name="i-lucide-plus" class="h-4 w-4" />
            <span class="lg:inline">Nouveau ticket</span>
          </NuxtLink>
        </div>
      </div>
      <div class="text-sm font-medium text-[var(--app-ink)]">
        {{ filteredTickets.length }} ticket{{ filteredTickets.length !== 1 ? 's' : '' }}
      </div>
    </header>

    <div class="space-y-4">
      <div v-if="isAdmin" class="card p-4 sm:p-6">
        <div class="space-y-3">
          <h2 class="text-sm font-semibold tracking-wide text-[var(--app-ink)] uppercase">Filtrer</h2>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="filter in statusFilters"
              :key="filter.value"
              type="button"
              :class="[
                'rounded-full border px-3 py-1.5 text-xs font-medium transition-all',
                activeStatus === filter.value
                  ? `${filter.classes} border-transparent`
                  : 'border-[var(--app-line)] text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]',
              ]"
              @click="updateStatus(filter.value)"
            >
              {{ filter.label }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="isLoading" class="space-y-2">
        <div v-for="n in 6" :key="`skeleton-${n}`" class="card">
          <div class="animate-pulse">
            <div class="mb-2 h-4 w-3/4 rounded bg-[var(--app-surface-2)]"></div>
            <div class="h-4 w-full rounded bg-[var(--app-surface-2)]"></div>
          </div>
        </div>
      </div>

      <div v-else-if="filteredTickets.length === 0" class="card px-6 py-12 text-center">
        <LandingAsterisk class="text-4xl text-[var(--app-accent)]" />
        <h3 class="font-display mt-5 text-2xl font-semibold text-[var(--app-ink)]">Aucun ticket</h3>
        <p class="text-muted mx-auto mt-2 max-w-sm text-sm leading-relaxed">
          Rien pour ce filtre — créez une demande ou changez de statut ci-dessus.
        </p>
      </div>

      <div v-else class="space-y-2">
        <NuxtLink
          v-for="ticket in filteredTickets"
          :key="ticket.id"
          :to="`/dashboard/support/${ticket.id}`"
          class="card relative block overflow-hidden transition-colors hover:border-[var(--app-ink)]"
        >
          <div :class="['absolute top-0 bottom-0 left-0 w-1.5', getStatusBorderColor(ticket.status)]"></div>
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div class="min-w-0 flex-1 space-y-2">
              <h3 class="text-base font-semibold text-[var(--app-ink)]">{{ ticket.subject }}</h3>
              <p class="line-clamp-2 text-sm text-[var(--app-ink-soft)]">
                {{ ticket.description }}
              </p>
              <div class="flex flex-wrap items-center gap-3 text-xs text-[var(--app-ink-soft)]">
                <span class="inline-flex items-center gap-1">
                  <UIcon name="i-lucide-user-round" class="h-3.5 w-3.5 text-[var(--app-ink)]" />
                  {{ ticket.user_name }}
                </span>
                <span class="inline-flex items-center gap-1">
                  <UIcon name="i-lucide-tag" class="h-3.5 w-3.5 text-[var(--app-ink)]" />
                  {{ topicLabel(ticket.topic) }}
                </span>
                <span class="inline-flex items-center gap-1">
                  <UIcon name="i-lucide-clock" class="h-3.5 w-3.5 text-[var(--app-ink)]" />
                  {{ formatRelative(ticket.last_message_at || ticket.created_at) }}
                </span>
                <span v-if="ticket.attachments_count > 0" class="inline-flex items-center gap-1">
                  <UIcon name="i-lucide-paperclip" class="h-3.5 w-3.5 text-[var(--app-ink)]" />
                  {{ ticket.attachments_count }}
                </span>
                <span
                  :class="[
                    'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                    statusStyles[ticket.status] || statusStyles.default,
                  ]"
                >
                  {{ statusLabels[ticket.status] || ticket.status }}
                </span>
              </div>
            </div>
          </div>
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useUserStore } from '~/stores/user'
import { useToast } from '~/composables/useToast'
import type { SupportTicketSummary, SupportTicketStatus } from '~/types'
import * as supportService from '~/services/supportService'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const toast = useToast()
const userStore = useUserStore()
const runtimeConfig = useRuntimeConfig()
const websocketRef = ref<WebSocket | null>(null)

const isAdmin = computed(() => userStore.user?.role === 'ADMIN')
const scope = computed(() => (isAdmin.value ? 'all' : 'mine'))

// For non-admin users, show all tickets by default (no filter)
const activeStatus = ref<string>(isAdmin.value ? 'open' : 'all')
const tickets = ref<SupportTicketSummary[]>([])
const isLoading = ref(false)

const statusLabels: Record<string, string> = {
  open: 'Ouvert',
  waiting_support: 'Attente support',
  waiting_user: 'Attente client',
  resolved: 'Résolu',
  closed: 'Fermé',
}

const statusStyles: Record<string, string> = {
  open: 'bg-[var(--app-accent-ink)]/20 text-[var(--app-accent-ink)]',
  waiting_support: 'bg-[var(--app-accent)]/20 text-[var(--app-accent-ink)]',
  waiting_user: 'bg-[var(--app-violet-soft)] text-[var(--app-violet)]',
  resolved: 'bg-[var(--app-green)]/20 text-[var(--app-green)]',
  closed: 'bg-[var(--app-ink-soft)]/20 text-[var(--app-ink-soft)]',
  default: 'bg-[var(--app-surface-2)] text-[var(--app-ink)]',
}

const statusFilters = [
  { value: 'open', label: 'Ouverts', classes: statusStyles.open },
  { value: 'waiting_support', label: 'Attente support', classes: statusStyles.waiting_support },
  { value: 'waiting_user', label: 'Attente client', classes: statusStyles.waiting_user },
  { value: 'resolved', label: 'Résolus', classes: statusStyles.resolved },
  { value: 'closed', label: 'Fermés', classes: statusStyles.closed },
  { value: 'all', label: 'Tous les tickets', classes: 'bg-[var(--app-bg)] text-[var(--app-ink)]' },
]

const filteredTickets = computed(() => {
  const sorted = tickets.value.slice().sort((a, b) => {
    const dateA = new Date(a.last_message_at || a.created_at).getTime()
    const dateB = new Date(b.last_message_at || b.created_at).getTime()
    return dateB - dateA
  })

  if (activeStatus.value === 'all') {
    return sorted
  }
  return sorted.filter((ticket) => ticket.status === activeStatus.value)
})

function topicLabel(topic: SupportTicketSummary['topic']): string {
  const mapping: Record<string, string> = {
    credits_billing: 'Crédits & facturation',
    missing_results: 'Résultats manquants',
    bug_report: 'Signalement de bug',
    refund_credits: 'Remboursement crédits',
    refund_payment: 'Remboursement paiement',
    feature_request: 'Suggestion',
    other: 'Autre',
  }
  return mapping[topic] ?? 'Support'
}

function getStatusBorderColor(status: string): string {
  const borderColors: Record<string, string> = {
    open: 'bg-[var(--app-accent-ink)]',
    waiting_support: 'bg-[var(--app-accent)]',
    waiting_user: 'bg-[var(--app-violet)]',
    resolved: 'bg-[var(--app-green)]',
    closed: 'bg-[var(--app-ink-soft)]',
  }
  return borderColors[status] || 'bg-[var(--app-surface-2)]'
}

function formatRelative(value: string): string {
  const date = new Date(value)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMinutes < 1) return "À l'instant"
  if (diffMinutes < 60) return `il y a ${diffMinutes} min`
  if (diffHours < 24) return `il y a ${diffHours} h`
  if (diffDays === 1) return 'Hier'
  if (diffDays < 7) return `il y a ${diffDays} jours`
  return date.toLocaleDateString('fr-FR', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

async function loadTickets(): Promise<void> {
  try {
    isLoading.value = true
    const includeClosed = activeStatus.value === 'closed' || activeStatus.value === 'all'
    const status = activeStatus.value === 'all' ? undefined : (activeStatus.value as SupportTicketStatus)
    tickets.value = await supportService.getTickets({
      scope: scope.value,
      status,
      includeClosed,
    })
  } catch (error) {
    console.error('Failed to load tickets', error)
    toast.error('Impossible de charger les tickets pour le moment.')
  } finally {
    isLoading.value = false
  }
}

function updateStatus(value: string): void {
  if (activeStatus.value === value) return
  activeStatus.value = value
}

async function refreshTickets(): Promise<void> {
  await loadTickets()
}

type SupportWebsocketEvent = {
  event?: string
  data?: Record<string, unknown>
}

function handleWebsocketEvent(event: SupportWebsocketEvent): void {
  if (!event || !event.event) return

  switch (event.event) {
    case 'ticket.created': {
      // Only notify admins when a user creates a ticket
      if (isAdmin.value) {
        const userCreatedBy = event.data?.user_name
        if (userCreatedBy && userCreatedBy !== userStore.user?.name) {
          toast.info(`Nouveau ticket créé par ${String(userCreatedBy)}`)
        }
      }
      void loadTickets()
      break
    }
    case 'ticket.updated': {
      const existingTicket = tickets.value.find((t) => t.id === event.data?.id)
      if (existingTicket) {
        Object.assign(existingTicket, event.data)
      } else {
        void loadTickets()
      }
      break
    }
    case 'ticket.message': {
      const senderId = event.data?._sender_id
      const senderName = event.data?._sender_name
      const ticketUserId = event.data?.user_id
      const currentUserId = userStore.user?.id

      const shouldNotify =
        senderId && currentUserId && senderId !== currentUserId && (ticketUserId === currentUserId || isAdmin.value)

      if (shouldNotify) {
        const ticketSubject = event.data?.subject || 'un ticket'
        toast.info(`${String(senderName)} a répondu à « ${String(ticketSubject)} »`)
      }

      const ticket = tickets.value.find((t) => t.id === event.data?.id)
      if (ticket) {
        Object.assign(ticket, event.data)
      } else {
        void loadTickets()
      }
      break
    }
    default:
      break
  }
}

function connectWebSocket(): void {
  disconnectWebSocket()
  const token = userStore.token
  if (!token) return

  try {
    const apiUrl = new URL(runtimeConfig.public.apiBase)
    apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
    const basePath = apiUrl.pathname.replace(/\/$/, '')
    apiUrl.pathname = `${basePath}/api/v1/support/tickets/ws`
    apiUrl.searchParams.set('token', token)

    const ws = new WebSocket(apiUrl.toString())
    websocketRef.value = ws

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        handleWebsocketEvent(payload)
      } catch (error) {
        console.warn('Invalid websocket event', error)
      }
    }

    ws.onclose = () => {
      websocketRef.value = null
      // Retry connection after 5 seconds
      setTimeout(() => {
        if (!websocketRef.value) {
          connectWebSocket()
        }
      }, 5000)
    }

    ws.onerror = () => {
      console.warn('WebSocket error')
    }
  } catch (error) {
    console.error('Failed to connect websocket', error)
  }
}

function disconnectWebSocket(): void {
  if (websocketRef.value) {
    websocketRef.value.close()
    websocketRef.value = null
  }
}

watch([activeStatus, () => scope.value], () => {
  void loadTickets()
})

onMounted(() => {
  void loadTickets()
  connectWebSocket()
})

onBeforeUnmount(() => {
  disconnectWebSocket()
})
</script>
