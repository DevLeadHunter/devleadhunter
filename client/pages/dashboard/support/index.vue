<template>
  <div class="space-y-10">
    <header class="space-y-4 mb-6">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-2">
          <h1 class="text-lg md:text-xl font-semibold text-[#f9f9f9] leading-tight">
            Support tickets
          </h1>
          <p class="text-sm text-[#8b949e] max-w-2xl">
            Review every request in one place and jump back into conversations instantly. Admins see the full queue while members only see their own tickets.
          </p>
        </div>
        <div class="flex items-center gap-3 w-full lg:w-auto lg:ml-auto">
          <button
            class="btn-secondary gap-2 px-4 flex-1 lg:flex-none"
            type="button"
            @click="refreshTickets"
          >
            <i class="fa-solid fa-rotate-right text-sm"></i>
            <span class="lg:inline">Refresh</span>
          </button>
          <NuxtLink
            to="/dashboard/support/new"
            class="btn-primary gap-2 px-4 flex-1 lg:flex-none"
          >
            <i class="fa-solid fa-plus text-sm"></i>
            <span class="lg:inline">New ticket</span>
          </NuxtLink>
        </div>
      </div>
      <div class="text-sm text-[#c9d1d9] font-medium">
        {{ filteredTickets.length }} ticket{{ filteredTickets.length !== 1 ? 's' : '' }}
      </div>
    </header>

    <div class="space-y-4">
      <div v-if="isAdmin" class="card p-4 sm:p-6">
        <div class="space-y-3">
          <h2 class="text-sm font-semibold text-[#f9f9f9] uppercase tracking-wide">
            Filter
          </h2>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="filter in statusFilters"
              :key="filter.value"
              type="button"
              :class="[
                'px-3 py-1.5 rounded-full text-xs font-medium transition-all border',
                activeStatus === filter.value
                  ? `${filter.classes} border-transparent`
                  : 'border-[#30363d] text-[#8b949e] hover:text-[#f9f9f9]'
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
            <div class="h-4 bg-[#2a2a2a] rounded w-3/4 mb-2"></div>
            <div class="h-4 bg-[#2a2a2a] rounded w-full"></div>
          </div>
        </div>
      </div>

      <div v-else-if="filteredTickets.length === 0" class="card text-center py-16">
        <i class="fa-regular fa-face-smile text-5xl text-[#71A3DB] mb-3"></i>
        <p class="text-sm text-[#8b949e]">
          No tickets for this filter yet. Create a request or adjust the status above.
        </p>
      </div>

      <div v-else class="space-y-2">
        <NuxtLink
          v-for="ticket in filteredTickets"
          :key="ticket.id"
          :to="`/dashboard/support/${ticket.id}`"
          class="card hover:border-[#f9f9f9] transition-colors block relative overflow-hidden"
        >
          <div
            :class="[
              'absolute left-0 top-0 bottom-0 w-1.5',
              getStatusBorderColor(ticket.status)
            ]"
          ></div>
          <div class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
            <div class="flex-1 min-w-0 space-y-2">
              <h3 class="text-base font-semibold text-[#f9f9f9]">{{ ticket.subject }}</h3>
              <p class="text-sm text-[#8b949e] line-clamp-2">
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
                <span
                  v-if="ticket.attachments_count > 0"
                  class="inline-flex items-center gap-1"
                >
                  <i class="fa-solid fa-paperclip text-[#f9f9f9]"></i>
                  {{ ticket.attachments_count }}
                </span>
                <span
                  :class="[
                    'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                    statusStyles[ticket.status] || statusStyles.default
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useUserStore } from '~/stores/user';
import { useToast } from '~/composables/useToast';
import type { SupportTicketSummary, SupportTicketStatus } from '~/types';
import * as supportService from '~/services/supportService';

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth'
});

const toast = useToast();
const userStore = useUserStore();
const runtimeConfig = useRuntimeConfig();
const websocketRef = ref<WebSocket | null>(null);

const isAdmin = computed(() => userStore.user?.role === 'ADMIN');
const scope = computed(() => (isAdmin.value ? 'all' : 'mine'));

// For non-admin users, show all tickets by default (no filter)
const activeStatus = ref<string>(isAdmin.value ? 'open' : 'all');
const tickets = ref<SupportTicketSummary[]>([]);
const isLoading = ref(false);

const statusLabels: Record<string, string> = {
  open: 'Open',
  waiting_support: 'Waiting on support',
  waiting_user: 'Waiting on customer',
  resolved: 'Resolved',
  closed: 'Closed'
};

const statusStyles: Record<string, string> = {
  open: 'bg-[#71A3DB]/20 text-[#71A3DB]',
  waiting_support: 'bg-[#F8D57E]/20 text-[#F8D57E]',
  waiting_user: 'bg-[#A585DB]/25 text-[#A585DB]',
  resolved: 'bg-[#2BAD5F]/20 text-[#2BAD5F]',
  closed: 'bg-[#8b949e]/20 text-[#8b949e]',
  default: 'bg-[#30363d] text-[#f9f9f9]'
};

const statusFilters = [
  { value: 'open', label: 'Open', classes: statusStyles.open },
  { value: 'waiting_support', label: 'Waiting on support', classes: statusStyles.waiting_support },
  { value: 'waiting_user', label: 'Waiting on customer', classes: statusStyles.waiting_user },
  { value: 'resolved', label: 'Resolved', classes: statusStyles.resolved },
  { value: 'closed', label: 'Closed', classes: statusStyles.closed },
  { value: 'all', label: 'All tickets', classes: 'bg-[#050505] text-[#f9f9f9]' }
];

const activeStatusLabel = computed(() => {
  if (activeStatus.value === 'all') return 'all tickets';
  return statusLabels[activeStatus.value] ?? '';
});

const filteredTickets = computed(() => {
  const sorted = tickets.value
    .slice()
    .sort((a, b) => {
      const dateA = new Date(a.last_message_at || a.created_at).getTime();
      const dateB = new Date(b.last_message_at || b.created_at).getTime();
      return dateB - dateA;
    });

  if (activeStatus.value === 'all') {
    return sorted;
  }
  return sorted.filter(ticket => ticket.status === activeStatus.value);
});

function topicLabel(topic: SupportTicketSummary['topic']): string {
  const mapping: Record<string, string> = {
    credits_billing: 'Credits & billing',
    missing_results: 'Missing results',
    bug_report: 'Bug report',
    refund_credits: 'Credit refund',
    refund_payment: 'Payment refund',
    feature_request: 'Feature request',
    other: 'Other'
  };
  return mapping[topic] ?? 'Support';
}

function getStatusBorderColor(status: string): string {
  const borderColors: Record<string, string> = {
    open: 'bg-[#71A3DB]',
    waiting_support: 'bg-[#F8D57E]',
    waiting_user: 'bg-[#A585DB]',
    resolved: 'bg-[#2BAD5F]',
    closed: 'bg-[#8b949e]'
  };
  return borderColors[status] || 'bg-[#30363d]';
}

function formatRelative(value: string): string {
  const date = new Date(value);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMinutes < 1) return 'Just now';
  if (diffMinutes < 60) return `${diffMinutes} min ago`;
  if (diffHours < 24) return `${diffHours} h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
}

async function loadTickets(): Promise<void> {
  try {
    isLoading.value = true;
    const includeClosed = activeStatus.value === 'closed' || activeStatus.value === 'all';
    const status = activeStatus.value === 'all'
      ? undefined
      : (activeStatus.value as SupportTicketStatus);
    tickets.value = await supportService.getTickets({
      scope: scope.value,
      status,
      includeClosed
    });
  } catch (error) {
    console.error('Failed to load tickets', error);
    toast.error('Unable to fetch tickets right now.');
  } finally {
    isLoading.value = false;
  }
}

function updateStatus(value: string): void {
  if (activeStatus.value === value) return;
  activeStatus.value = value;
}

async function refreshTickets(): Promise<void> {
  await loadTickets();
}

function handleWebsocketEvent(event: { event?: string; data?: any }): void {
  if (!event || !event.event) return;
  
  switch (event.event) {
    case 'ticket.created':
      // Only notify admins when a user creates a ticket
      if (isAdmin.value) {
        const userCreatedBy = event.data?.user_name;
        if (userCreatedBy && userCreatedBy !== userStore.user?.name) {
          toast.info(`New ticket created by ${userCreatedBy}`);
        }
      }
      // Refresh tickets for everyone
      void loadTickets();
      break;
    case 'ticket.updated':
      // Update existing ticket or refresh list
      const existingTicket = tickets.value.find(t => t.id === event.data?.id);
      if (existingTicket) {
        // Update the ticket in the list
        Object.assign(existingTicket, event.data);
      } else {
        // Refresh the list if we don't have this ticket
        void loadTickets();
      }
      break;
    case 'ticket.message':
      // New message in a ticket
      const senderId = event.data?._sender_id;
      const senderName = event.data?._sender_name;
      const ticketUserId = event.data?.user_id;
      const currentUserId = userStore.user?.id;
      
      // Show notification if:
      // 1. The message is from someone else (not yourself)
      // 2. AND either you're the ticket owner OR you're an admin
      const shouldNotify = senderId && currentUserId && senderId !== currentUserId && 
                          (ticketUserId === currentUserId || isAdmin.value);
      
      if (shouldNotify) {
        const ticketSubject = event.data?.subject || 'a ticket';
        toast.info(`${senderName} replied to "${ticketSubject}"`);
      }
      
      // Update the ticket in the list
      const ticket = tickets.value.find(t => t.id === event.data?.id);
      if (ticket) {
        Object.assign(ticket, event.data);
      } else {
        // Refresh the list if we don't have this ticket
        void loadTickets();
      }
      break;
    default:
      break;
  }
}

function connectWebSocket(): void {
  disconnectWebSocket();
  const token = userStore.token;
  if (!token) return;
  
  try {
    const apiUrl = new URL(runtimeConfig.public.apiBase);
    apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
    const basePath = apiUrl.pathname.replace(/\/$/, '');
    apiUrl.pathname = `${basePath}/api/v1/support/tickets/ws`;
    apiUrl.searchParams.set('token', token);

    const ws = new WebSocket(apiUrl.toString());
    websocketRef.value = ws;
    
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleWebsocketEvent(payload);
      } catch (error) {
        console.warn('Invalid websocket event', error);
      }
    };
    
    ws.onclose = () => {
      websocketRef.value = null;
      // Retry connection after 5 seconds
      setTimeout(() => {
        if (!websocketRef.value) {
          connectWebSocket();
        }
      }, 5000);
    };
    
    ws.onerror = () => {
      console.warn('WebSocket error');
    };
  } catch (error) {
    console.error('Failed to connect websocket', error);
  }
}

function disconnectWebSocket(): void {
  if (websocketRef.value) {
    websocketRef.value.close();
    websocketRef.value = null;
  }
}

watch([activeStatus, () => scope.value], () => {
  void loadTickets();
});

onMounted(() => {
  void loadTickets();
  connectWebSocket();
});

onBeforeUnmount(() => {
  disconnectWebSocket();
});
</script>
