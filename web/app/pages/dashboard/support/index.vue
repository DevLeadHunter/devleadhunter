<template>
  <div class="space-y-10">
    <header class="mb-6 space-y-4">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-2">
          <h1 class="text-lg font-semibold leading-tight text-[#f9f9f9] md:text-xl">Support tickets</h1>
          <p class="max-w-2xl text-sm text-[#8b949e]">
            Review every request in one place and jump back into conversations instantly. Admins see the full queue
            while members only see their own tickets.
          </p>
        </div>
        <div class="flex w-full items-center gap-3 lg:ml-auto lg:w-auto">
          <button class="btn-secondary flex-1 gap-2 px-4 lg:flex-none" type="button" @click="refreshTickets">
            <i class="fa-solid fa-rotate-right text-sm"></i>
            <span class="lg:inline">Refresh</span>
          </button>
          <NuxtLink to="/dashboard/support/new" class="btn-primary flex-1 gap-2 px-4 lg:flex-none">
            <i class="fa-solid fa-plus text-sm"></i>
            <span class="lg:inline">New ticket</span>
          </NuxtLink>
        </div>
      </div>
      <div class="text-sm font-medium text-[#c9d1d9]">
        {{ filteredTickets.length }} ticket{{ filteredTickets.length !== 1 ? 's' : '' }}
      </div>
    </header>

    <div class="space-y-4">
      <div v-if="isAdmin" class="card p-4 sm:p-6">
        <div class="space-y-3">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-[#f9f9f9]">Filter</h2>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="filter in statusFilters"
              :key="filter.value"
              type="button"
              :class="[
                'rounded-full border px-3 py-1.5 text-xs font-medium transition-all',
                activeStatus === filter.value
                  ? `${filter.classes} border-transparent`
                  : 'border-[#30363d] text-[#8b949e] hover:text-[#f9f9f9]',
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
            <div class="mb-2 h-4 w-3/4 rounded bg-[#2a2a2a]"></div>
            <div class="h-4 w-full rounded bg-[#2a2a2a]"></div>
          </div>
        </div>
      </div>

      <div v-else-if="filteredTickets.length === 0" class="card py-16 text-center">
        <i class="fa-regular fa-face-smile mb-3 text-5xl text-[#71A3DB]"></i>
        <p class="text-sm text-[#8b949e]">
          No tickets for this filter yet. Create a request or adjust the status above.
        </p>
      </div>

      <div v-else class="space-y-2">
        <NuxtLink
          v-for="ticket in filteredTickets"
          :key="ticket.id"
          :to="`/dashboard/support/${ticket.id}`"
          class="card relative block overflow-hidden transition-colors hover:border-[#f9f9f9]"
        >
          <div :class="['absolute bottom-0 left-0 top-0 w-1.5', getStatusBorderColor(ticket.status)]"></div>
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div class="min-w-0 flex-1 space-y-2">
              <h3 class="text-base font-semibold text-[#f9f9f9]">{{ ticket.subject }}</h3>
              <p class="line-clamp-2 text-sm text-[#8b949e]">
                {{ ticket.description }}
              </p>
              <div class="flex flex-wrap items-center gap-3 text-xs text-[#8b949e]">
                <span class="inline-flex items-center gap-1">
                  <i class="fa-solid fa-user text-[#f9f9f9]"></i>
                  {{ ticket.user_name }}
                </span>
                <span class="inline-flex items-center gap-1">
                  <i class="fa-solid fa-tag text-[#f9f9f9]"></i>
                  {{ topicLabel(ticket.topic) }}
                </span>
                <span class="inline-flex items-center gap-1">
                  <i class="fa-regular fa-clock text-[#f9f9f9]"></i>
                  {{ formatRelative(ticket.last_message_at || ticket.created_at) }}
                </span>
                <span v-if="ticket.attachments_count > 0" class="inline-flex items-center gap-1">
                  <i class="fa-solid fa-paperclip text-[#f9f9f9]"></i>
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
  open: 'Open',
  waiting_support: 'Waiting on support',
  waiting_user: 'Waiting on customer',
  resolved: 'Resolved',
  closed: 'Closed',
}

const statusStyles: Record<string, string> = {
  open: 'bg-[#71A3DB]/20 text-[#71A3DB]',
  waiting_support: 'bg-[#F8D57E]/20 text-[#F8D57E]',
  waiting_user: 'bg-[#A585DB]/25 text-[#A585DB]',
  resolved: 'bg-[#2BAD5F]/20 text-[#2BAD5F]',
  closed: 'bg-[#8b949e]/20 text-[#8b949e]',
  default: 'bg-[#30363d] text-[#f9f9f9]',
}

const statusFilters = [
  { value: 'open', label: 'Open', classes: statusStyles.open },
  { value: 'waiting_support', label: 'Waiting on support', classes: statusStyles.waiting_support },
  { value: 'waiting_user', label: 'Waiting on customer', classes: statusStyles.waiting_user },
  { value: 'resolved', label: 'Resolved', classes: statusStyles.resolved },
  { value: 'closed', label: 'Closed', classes: statusStyles.closed },
  { value: 'all', label: 'All tickets', classes: 'bg-[#050505] text-[#f9f9f9]' },
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
    credits_billing: 'Credits & billing',
    missing_results: 'Missing results',
    bug_report: 'Bug report',
    refund_credits: 'Credit refund',
    refund_payment: 'Payment refund',
    feature_request: 'Feature request',
    other: 'Other',
  }
  return mapping[topic] ?? 'Support'
}

function getStatusBorderColor(status: string): string {
  const borderColors: Record<string, string> = {
    open: 'bg-[#71A3DB]',
    waiting_support: 'bg-[#F8D57E]',
    waiting_user: 'bg-[#A585DB]',
    resolved: 'bg-[#2BAD5F]',
    closed: 'bg-[#8b949e]',
  }
  return borderColors[status] || 'bg-[#30363d]'
}

function formatRelative(value: string): string {
  const date = new Date(value)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMinutes < 1) return 'Just now'
  if (diffMinutes < 60) return `${diffMinutes} min ago`
  if (diffHours < 24) return `${diffHours} h ago`
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  return date.toLocaleDateString('en-US', {
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
    toast.error('Unable to fetch tickets right now.')
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
          toast.info(`New ticket created by ${String(userCreatedBy)}`)
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
        const ticketSubject = event.data?.subject || 'a ticket'
        toast.info(`${String(senderName)} replied to "${String(ticketSubject)}"`)
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
