<template>
  <div class="space-y-8">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <NuxtLink
        to="/dashboard/support"
        class="btn-secondary inline-flex items-center gap-2 w-fit"
      >
        <i class="fa-solid fa-arrow-left"></i>
        Back to tickets
      </NuxtLink>
      
      <p class="text-xs uppercase tracking-wider text-[#71A3DB] font-semibold">
        Ticket #{{ ticketId }}
      </p>
    </div>

    <header class="space-y-2">
      <h1 class="text-[28px] font-semibold text-[#f9f9f9] leading-tight break-words">
        {{ ticket?.subject || 'Loading…' }}
      </h1>
      <p class="text-sm text-[#8b949e] max-w-2xl">
        Keep track of the latest replies. Members can only access their own tickets while admins
        see the global queue. Status updates are handled automatically by the platform.
      </p>
    </header>

    <UiLoader v-if="isLoading" />

    <div v-else-if="!ticket" class="card flex items-center justify-center py-16 text-[#8b949e]">
      <p class="text-sm">We could not find this ticket. Check the URL or return to the list.</p>
    </div>

    <div v-else class="grid gap-6 xl:grid-cols-[320px_1fr] max-w-full items-start">
      <aside class="card p-4 sm:p-6 space-y-6 bg-[#101216] h-fit max-w-full overflow-hidden xl:sticky xl:top-6">
        <div class="space-y-3">
          <h2 class="text-sm font-semibold text-[#f9f9f9] uppercase tracking-wide">
            Ticket summary
          </h2>
          <dl class="space-y-3 text-xs text-[#8b949e] leading-relaxed">
            <div class="flex items-start justify-between gap-4">
              <dt class="font-medium text-[#f9f9f9]">Requester</dt>
              <dd class="text-right break-words min-w-0">{{ ticket.user_name }}</dd>
            </div>
            <div class="flex items-start justify-between gap-4">
              <dt class="font-medium text-[#f9f9f9]">Topic</dt>
              <dd class="text-right break-words min-w-0">{{ topicLabel(ticket.topic) }}</dd>
            </div>
            <div class="flex items-start justify-between gap-4">
              <dt class="font-medium text-[#f9f9f9]">Created</dt>
              <dd class="text-right break-words min-w-0">{{ formatDate(ticket.created_at, true) }}</dd>
            </div>
            <div class="flex items-start justify-between gap-4">
              <dt class="font-medium text-[#f9f9f9]">Last update</dt>
              <dd class="text-right break-words min-w-0">
                {{ ticket.last_message_at ? formatDate(ticket.last_message_at, true) : 'Just now' }}
              </dd>
            </div>
            <div class="flex items-start justify-between gap-4">
              <dt class="font-medium text-[#f9f9f9]">Status</dt>
              <dd>
                <span
                  :class="[
                    'px-3 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wide',
                    statusStyles[ticket.status] || statusStyles.default
                  ]"
                >
                  {{ statusLabels[ticket.status] || ticket.status }}
                </span>
              </dd>
            </div>
          </dl>
        </div>

        <div class="space-y-2">
          <h3 class="text-sm font-semibold text-[#f9f9f9]">Initial description</h3>
          <p class="text-xs text-[#8b949e] whitespace-pre-wrap leading-relaxed break-words overflow-wrap-anywhere">
            {{ ticket.description }}
          </p>
        </div>

        <div v-if="ticket.attachments.length" class="space-y-3">
          <h3 class="text-sm font-semibold text-[#f9f9f9]">Attached images</h3>
          <div class="grid gap-3 sm:grid-cols-2">
            <a
              v-for="attachment in ticket.attachments"
              :key="attachment.id"
              :href="attachment.url"
              target="_blank"
              rel="noopener"
              class="block overflow-hidden rounded-lg border border-[#30363d] bg-[#0d1117]"
            >
              <img
                :src="attachment.url"
                :alt="attachment.original_filename"
                class="h-32 w-full object-cover"
              />
              <p class="px-3 py-2 text-[11px] text-[#8b949e] truncate">
                {{ attachment.original_filename }}
              </p>
            </a>
          </div>
        </div>
      </aside>

      <section class="card p-4 sm:p-6 flex flex-col space-y-6 max-w-full overflow-hidden h-[600px] md:h-[calc(100vh-280px)]">
        <div
          ref="conversationContainer"
          class="flex-1 overflow-y-auto space-y-5 pr-2 custom-scrollbar min-h-0"
        >
          <div
            v-for="message in ticket.messages"
            :key="message.id"
            :class="[
              'flex flex-col gap-3 w-full max-w-[85%]',
              message.sender_id === userStore.user?.id ? 'ml-auto items-end' : 'items-start'
            ]"
          >
            <div class="flex items-center gap-2 text-xs text-[#8b949e]">
              <span class="font-medium text-[#f9f9f9]">{{ message.sender_name }}</span>
              <span>{{ formatDate(message.created_at, true) }}</span>
            </div>
            <div
              v-if="message.content && message.content.trim()"
              :class="[
                'px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words max-w-full',
                message.sender_id === userStore.user?.id
                  ? 'bg-[#71A3DB] text-[#050505]'
                  : 'bg-[#1a1f26] text-[#f9f9f9]'
              ]"
            >
              {{ message.content }}
            </div>
            <div
              v-if="message.attachments.length"
              :class="[
                'flex flex-wrap gap-3 w-full',
                message.sender_id === userStore.user?.id ? 'justify-end' : 'justify-start'
              ]"
            >
              <a
                v-for="attachment in message.attachments"
                :key="attachment.id"
                :href="attachment.url"
                target="_blank"
                rel="noopener"
                class="block overflow-hidden rounded-lg border border-[#30363d] bg-[#0d1117] w-[200px]"
              >
                <img
                  :src="attachment.url"
                  :alt="attachment.original_filename"
                  class="h-28 w-full object-cover"
                />
                <p class="px-3 py-2 text-[11px] text-[#8b949e] truncate">
                  {{ attachment.original_filename }}
                </p>
              </a>
            </div>
          </div>
        </div>

        <form class="space-y-4 border-t border-[#1f252d] pt-4 flex-shrink-0" @submit.prevent="sendMessage">
          <div class="relative">
            <textarea
              v-model="messageInput"
              rows="3"
              class="input-field pr-28"
              placeholder="Write a reply…"
              @keydown="handleKeydown"
            ></textarea>
            <div class="absolute right-3 bottom-3 flex items-center gap-2">
              <label
                class="flex items-center justify-center w-9 h-9 rounded-lg border border-[#30363d] bg-[#050505] text-[#8b949e] hover:text-[#f9f9f9] cursor-pointer transition-colors"
              >
                <i class="fa-solid fa-paperclip text-sm"></i>
                <input
                  ref="composerInput"
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  class="hidden"
                  multiple
                  @change="handleComposerAttachments"
                />
              </label>
              <button
                type="submit"
                class="w-10 h-10 rounded-full bg-[#71A3DB] text-[#050505] flex items-center justify-center hover:bg-[#71A3DB]/80 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                :disabled="(!messageInput.trim() && composerPreviews.length === 0) || isSending"
                title="Send"
              >
                <i class="fa-solid fa-paper-plane"></i>
              </button>
            </div>
          </div>

          <div v-if="composerPreviews.length" class="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
            <figure
              v-for="(preview, index) in composerPreviews"
              :key="preview.url"
              class="relative rounded-lg border border-[#30363d] bg-[#0d1117] overflow-hidden"
            >
              <img :src="preview.url" :alt="preview.name" class="h-28 w-full object-cover" />
              <figcaption class="px-3 py-2 text-[11px] text-[#8b949e] truncate">
                {{ preview.name }}
              </figcaption>
              <button
                type="button"
                class="absolute top-2 right-2 h-6 w-6 rounded-full bg-[#050505]/80 text-[#f9f9f9] hover:bg-[#DC4747] hover:text-white transition-colors flex items-center justify-center text-[11px]"
                @click="removeComposerAttachment(index)"
              >
                <i class="fa-solid fa-xmark"></i>
              </button>
            </figure>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useUserStore } from '~/stores/user';
import { useToast } from '~/composables/useToast';
import type { SupportTicketDetail, SupportMessage } from '~/types';
import * as supportService from '~/services/supportService';

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth'
});

const route = useRoute();
const toast = useToast();
const userStore = useUserStore();
const runtimeConfig = useRuntimeConfig();

const ticketId = computed(() => Number(route.params.id));
const ticket = ref<SupportTicketDetail | null>(null);
const isLoading = ref(true);
const isSending = ref(false);

const messageInput = ref('');
const composerFiles = ref<File[]>([]);
const composerPreviews = ref<Array<{ url: string; name: string }>>([]);
const composerInput = ref<HTMLInputElement | null>(null);

const conversationContainer = ref<HTMLDivElement | null>(null);
const websocketRef = ref<WebSocket | null>(null);
const globalWebsocketRef = ref<WebSocket | null>(null);

const statusLabels: Record<string, string> = {
  open: 'Open',
  waiting_support: 'Waiting on support',
  waiting_user: 'Waiting on customer',
  resolved: 'Resolved',
  closed: 'Closed'
};

const statusStyles: Record<string, string> = {
  open: 'bg-[#71A3DB]/20 text-[#71A3DB]',
  waiting_support: 'bg-[#F8D57E]/15 text-[#F8D57E]',
  waiting_user: 'bg-[#A585DB]/20 text-[#A585DB]',
  resolved: 'bg-[#2BAD5F]/20 text-[#2BAD5F]',
  closed: 'bg-[#8b949e]/20 text-[#8b949e]',
  default: 'bg-[#30363d] text-[#f9f9f9]'
};

const topicMap: Record<string, string> = {
  credits_billing: 'Credits & billing',
  missing_results: 'Missing results',
  bug_report: 'Bug report',
  refund_credits: 'Credit refund',
  refund_payment: 'Payment refund',
  feature_request: 'Feature request',
  other: 'Other'
};

function topicLabel(topic: SupportTicketDetail['topic']): string {
  return topicMap[topic] ?? topic;
}

function formatDate(value: string | null | undefined, includeTime = false): string {
  if (!value) return '';
  const date = new Date(value);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: includeTime ? '2-digit' : undefined,
    minute: includeTime ? '2-digit' : undefined
  });
}

function resolveAttachmentUrl(path: string): string {
  if (!path) return '';
  if (path.startsWith('http')) {
    return path;
  }
  const base = runtimeConfig.public.apiBase.replace(/\/$/, '');
  return `${base}${path.startsWith('/') ? path : `/${path}`}`;
}

async function loadTicket(): Promise<void> {
  if (!ticketId.value) return;
  try {
    isLoading.value = true;
    ticket.value = await supportService.getTicket(ticketId.value);
    await nextTick();
    scrollToBottom();
    connectWebSocket();
  } catch (error) {
    console.error('Failed to load ticket', error);
    toast.error('Unable to load this ticket right now.');
  } finally {
    isLoading.value = false;
  }
}

function scrollToBottom(): void {
  if (!conversationContainer.value) return;
  requestAnimationFrame(() => {
    if (!conversationContainer.value) return;
    conversationContainer.value.scrollTop = conversationContainer.value.scrollHeight;
  });
}

function resetComposerInput(): void {
  if (composerInput.value) {
    composerInput.value.value = '';
  }
}

function revokeComposerPreview(index: number): void {
  URL.revokeObjectURL(composerPreviews.value[index].url);
}

function handleComposerAttachments(event: Event): void {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files ?? []);

  files.forEach(file => {
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      toast.error('Unsupported format. Please use PNG, JPG or WEBP.');
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      toast.error('File is too large (maximum 8 MB per image).');
      return;
    }
    composerFiles.value.push(file);
    composerPreviews.value.push({
      url: URL.createObjectURL(file),
      name: file.name
    });
  });

  resetComposerInput();
}

function removeComposerAttachment(index: number): void {
  composerFiles.value.splice(index, 1);
  revokeComposerPreview(index);
  composerPreviews.value.splice(index, 1);
}

async function sendMessage(): Promise<void> {
  if (!ticket.value || (!messageInput.value.trim() && composerFiles.value.length === 0)) return;
  try {
    isSending.value = true;
    const message = await supportService.postMessage(ticket.value.id, {
      message: messageInput.value.trim() || ' ',
      attachments: composerFiles.value
    });
    appendMessage(message);
    messageInput.value = '';
    composerFiles.value = [];
    composerPreviews.value.forEach(preview => URL.revokeObjectURL(preview.url));
    composerPreviews.value = [];
    resetComposerInput();
  } catch (error) {
    console.error('Failed to send message', error);
    toast.error('We could not send your reply. Please try again.');
  } finally {
    isSending.value = false;
  }
}

function appendMessage(message: SupportMessage): void {
  if (!ticket.value) return;
  const exists = ticket.value.messages.some(item => item.id === message.id);
  if (!exists) {
    ticket.value.messages.push(message);
    ticket.value.last_message_at = message.created_at;
    scrollToBottom();
  }
}

function handleWebsocketEvent(event: { event?: string; data?: any }): void {
  if (!event || !event.event || !ticket.value) return;
  switch (event.event) {
    case 'message.created':
      if (event.data?.ticket_id === ticket.value.id) {
        appendMessage(event.data as SupportMessage);
      }
      break;
    case 'ticket.updated':
      if (event.data?.id === ticket.value.id) {
        ticket.value = {
          ...ticket.value,
          ...event.data,
          messages: ticket.value.messages
        };
      }
      break;
    default:
      break;
  }
}

function connectWebSocket(): void {
  disconnectWebSocket();
  const token = userStore.token;
  if (!token || !ticket.value) return;
  try {
    const apiUrl = new URL(runtimeConfig.public.apiBase);
    apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
    const basePath = apiUrl.pathname.replace(/\/$/, '');
    apiUrl.pathname = `${basePath}/api/v1/support/tickets/${ticket.value.id}/ws`;
    apiUrl.searchParams.set('token', token);

    const ws = new WebSocket(apiUrl.toString());
    websocketRef.value = ws;
    ws.onmessage = event => {
      try {
        const payload = JSON.parse(event.data);
        handleWebsocketEvent(payload);
      } catch (error) {
        console.warn('Invalid websocket event', error);
      }
    };
    ws.onclose = () => {
      websocketRef.value = null;
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

function handleGlobalWebsocketEvent(event: { event?: string; data?: any }): void {
  if (!event || !event.event) return;
  
  // Handle new message notifications
  if (event.event === 'ticket.message') {
    const messageTicketId = event.data?.id;
    const currentTicketId = ticketId.value;
    
    // Debug log
    console.log('[WebSocket] Message event:', {
      messageTicketId,
      currentTicketId,
      areEqual: messageTicketId === currentTicketId,
      messageTicketIdType: typeof messageTicketId,
      currentTicketIdType: typeof currentTicketId
    });
    
    // Don't show notification if the message is for the current ticket
    // Use == instead of === to handle type coercion (string vs number)
    if (messageTicketId && messageTicketId == currentTicketId) {
      console.log('[WebSocket] Skipping notification - user is on this ticket page');
      return; // User is already on this ticket page, no need to notify
    }
    
    // Show notification for messages in other tickets
    const senderId = event.data?._sender_id;
    const senderName = event.data?._sender_name;
    const currentUserId = userStore.user?.id;
    const isAdmin = userStore.user?.role === 'ADMIN';
    const ticketUserId = event.data?.user_id;
    
    const shouldNotify = senderId && currentUserId && senderId !== currentUserId && 
                        (ticketUserId === currentUserId || isAdmin);
    
    if (shouldNotify) {
      const ticketSubject = event.data?.subject || 'a ticket';
      toast.info(`${senderName} replied to "${ticketSubject}"`);
    }
  }
  
  // Handle ticket created notifications for admins
  if (event.event === 'ticket.created') {
    const isAdmin = userStore.user?.role === 'ADMIN';
    if (isAdmin) {
      const userCreatedBy = event.data?.user_name;
      if (userCreatedBy && userCreatedBy !== userStore.user?.name) {
        toast.info(`New ticket created by ${userCreatedBy}`);
      }
    }
  }
}

function connectGlobalWebSocket(): void {
  disconnectGlobalWebSocket();
  const token = userStore.token;
  if (!token) return;
  
  try {
    const apiUrl = new URL(runtimeConfig.public.apiBase);
    apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
    const basePath = apiUrl.pathname.replace(/\/$/, '');
    apiUrl.pathname = `${basePath}/api/v1/support/tickets/ws`;
    apiUrl.searchParams.set('token', token);

    const ws = new WebSocket(apiUrl.toString());
    globalWebsocketRef.value = ws;
    
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleGlobalWebsocketEvent(payload);
      } catch (error) {
        console.warn('Invalid websocket event', error);
      }
    };
    
    ws.onclose = () => {
      globalWebsocketRef.value = null;
    };
    
    ws.onerror = () => {
      console.warn('Global WebSocket error');
    };
  } catch (error) {
    console.error('Failed to connect global websocket', error);
  }
}

function disconnectGlobalWebSocket(): void {
  if (globalWebsocketRef.value) {
    globalWebsocketRef.value.close();
    globalWebsocketRef.value = null;
  }
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    void sendMessage();
  }
}

watch(() => route.params.id, () => {
  disconnectWebSocket();
  ticket.value = null;
  composerFiles.value = [];
  composerPreviews.value.forEach(preview => URL.revokeObjectURL(preview.url));
  composerPreviews.value = [];
  resetComposerInput();
  void loadTicket();
});

onMounted(() => {
  void loadTicket();
  connectGlobalWebSocket();
});

onBeforeUnmount(() => {
  disconnectWebSocket();
  disconnectGlobalWebSocket();
  composerPreviews.value.forEach(preview => URL.revokeObjectURL(preview.url));
});
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #30363d;
  border-radius: 999px;
}
</style>

