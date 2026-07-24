<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <div>
      <NuxtLink
        to="/dashboard/support"
        class="text-muted mb-4 inline-flex items-center gap-1.5 text-xs font-medium transition-colors hover:text-[var(--app-ink)]"
      >
        <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
        Support
      </NuxtLink>

      <div class="flex flex-wrap items-start justify-between gap-3">
        <h1 class="min-w-0 text-2xl font-bold break-words text-[var(--app-ink)]">
          {{ ticket?.subject || 'Chargement…' }}
        </h1>
        <span
          v-if="ticket"
          :class="['app-badge shrink-0 font-medium', SUPPORT_STATUS_PRESENTATION[ticket.status]?.badgeClass ?? '']"
        >
          {{ SUPPORT_STATUS_PRESENTATION[ticket.status]?.label ?? ticket.status }}
        </span>
      </div>

      <p v-if="ticket" class="text-muted mt-1.5 flex flex-wrap items-center gap-x-2 text-xs">
        <span>#{{ ticket.id }}</span>
        <span aria-hidden="true">·</span>
        <span>{{ topicLabel(ticket.topic) }}</span>
        <span aria-hidden="true">·</span>
        <span>{{ ticket.user_name }}</span>
        <span aria-hidden="true">·</span>
        <span>ouvert le {{ formatShortMonthDate(ticket.created_at) }}</span>
      </p>
    </div>

    <UiLoader v-if="isLoading" />

    <div
      v-else-if="!ticket"
      class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-6 py-14 text-center"
    >
      <p class="text-muted text-sm">Ticket introuvable. Vérifiez l'URL ou revenez à la liste.</p>
    </div>

    <template v-else>
      <UiCollapsibleCard icon="i-lucide-file-text" title="La demande initiale">
        <div class="space-y-4 px-4 py-4">
          <p class="text-sm leading-relaxed whitespace-pre-wrap text-[var(--app-ink)]">{{ ticket.description }}</p>
          <div v-if="ticket.attachments.length" class="grid gap-3 sm:grid-cols-3">
            <a
              v-for="attachment in ticket.attachments"
              :key="attachment.id"
              :href="attachment.url"
              target="_blank"
              rel="noopener"
              class="block overflow-hidden rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] transition-colors hover:border-[var(--app-ink-soft)]"
            >
              <img :src="attachment.url" :alt="attachment.original_filename" class="h-24 w-full object-cover" />
              <p class="text-muted truncate px-2 py-1.5 text-[11px]">{{ attachment.original_filename }}</p>
            </a>
          </div>
        </div>
      </UiCollapsibleCard>

      <div class="space-y-5">
        <div v-for="message in ticket.messages" :key="message.id" class="space-y-1.5">
          <p :class="['text-muted flex items-center gap-2 text-xs', isMine(message) ? 'justify-end' : 'justify-start']">
            <span class="font-medium text-[var(--app-ink)]">{{ message.sender_name }}</span>
            <span>{{ formatShortMonthDateTime(message.created_at) }}</span>
          </p>

          <div :class="['flex', isMine(message) ? 'justify-end' : 'justify-start']">
            <div class="max-w-[85%] space-y-2">
              <div
                v-if="message.content && message.content.trim()"
                :class="[
                  'rounded-2xl px-4 py-2.5 text-sm leading-relaxed break-words whitespace-pre-wrap',
                  isMine(message)
                    ? 'bg-[var(--app-ink)] text-[var(--app-surface)]'
                    : 'bg-[var(--app-surface-2)] text-[var(--app-ink)]',
                ]"
              >
                {{ message.content }}
              </div>

              <div v-if="message.attachments.length" class="grid grid-cols-2 gap-2">
                <a
                  v-for="attachment in message.attachments"
                  :key="attachment.id"
                  :href="attachment.url"
                  target="_blank"
                  rel="noopener"
                  class="block overflow-hidden rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] transition-colors hover:border-[var(--app-ink-soft)]"
                >
                  <img :src="attachment.url" :alt="attachment.original_filename" class="h-24 w-full object-cover" />
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>

      <form class="space-y-3" @submit.prevent="sendMessage">
        <div class="relative">
          <textarea
            v-model="messageInput"
            rows="3"
            class="input-field h-auto py-2.5 pr-24"
            placeholder="Écrire une réponse… (Entrée pour envoyer)"
            @keydown="handleKeydown"
          ></textarea>
          <div class="absolute right-2.5 bottom-2.5 flex items-center gap-2">
            <label
              class="flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg border border-[var(--app-line)] text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-ink-soft)] hover:text-[var(--app-ink)]"
              title="Joindre une image"
            >
              <UIcon name="i-lucide-paperclip" class="h-4 w-4" />
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
              class="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--app-ink)] text-[var(--app-surface)] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
              :disabled="(!messageInput.trim() && composerPreviews.length === 0) || isSending"
              title="Envoyer"
            >
              <UIcon
                :name="isSending ? 'i-lucide-loader-circle' : 'i-lucide-send'"
                :class="['h-4 w-4', isSending && 'animate-spin']"
              />
            </button>
          </div>
        </div>

        <div v-if="composerPreviews.length" class="grid gap-3 sm:grid-cols-4">
          <figure
            v-for="(preview, index) in composerPreviews"
            :key="preview.url"
            class="relative overflow-hidden rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)]"
          >
            <img :src="preview.url" :alt="preview.name" class="h-20 w-full object-cover" />
            <button
              type="button"
              class="btn-danger absolute top-1.5 right-1.5 flex h-5 w-5 items-center justify-center !p-0"
              :aria-label="`Retirer ${preview.name}`"
              @click="removeComposerAttachment(index)"
            >
              <UIcon name="i-lucide-x" class="h-3 w-3" />
            </button>
          </figure>
        </div>
      </form>
    </template>
  </div>
</template>

<script lang="ts" setup>
import { SUPPORT_STATUS_PRESENTATION } from '~/constants/supportStatus'
import { formatShortMonthDate, formatShortMonthDateTime } from '~/utils/date'
import type { UseToastReturn } from '~/types/Composables'
import type { SupportWebsocketEvent } from '~/types/SupportTicketPage'
import type { ComputedRef, Ref } from 'vue'
import type { SupportMessage, SupportTicketDetail } from '~/types'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '~/stores/user'
import { useToast } from '~/composables/useToast'
import { SupportService } from '~/services/supportService'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

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

/** Accepted image types for attachments. */
const ALLOWED_TYPES: string[] = ['image/png', 'image/jpeg', 'image/webp']

/** Maximum attachment size, in bytes. */
const MAX_ATTACHMENT_BYTES: number = 8 * 1024 * 1024

const route: ReturnType<typeof useRoute> = useRoute()
const toast: UseToastReturn = useToast()
const userStore: ReturnType<typeof useUserStore> = useUserStore()
const runtimeConfig: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()

const ticket: Ref<SupportTicketDetail | null> = ref(null)
const isLoading: Ref<boolean> = ref(true)
const isSending: Ref<boolean> = ref(false)
const messageInput: Ref<string> = ref('')
const composerFiles: Ref<File[]> = ref([])
const composerPreviews: Ref<Array<{ url: string; name: string }>> = ref([])
const composerInput: Ref<HTMLInputElement | null> = ref(null)
const websocketRef: Ref<WebSocket | null> = ref(null)
const globalWebsocketRef: Ref<WebSocket | null> = ref(null)

const ticketId: ComputedRef<number> = computed((): number => Number(route.params.id))

/**
 * Whether a message was written by the current user.
 * @param message - Message to test.
 * @returns True when the current user is the sender.
 */
function isMine(message: SupportMessage): boolean {
  return message.sender_id === userStore.user?.id
}

/**
 * Human label for a ticket topic.
 * @param topic - Raw topic value.
 * @returns Localised label.
 */
function topicLabel(topic: SupportTicketDetail['topic']): string {
  return TOPIC_LABELS[topic] ?? topic
}

/**
 * Scroll the window to the latest message.
 */
function scrollToBottom(): void {
  requestAnimationFrame((): void => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  })
}

/**
 * Stage the picked images after validating type and size.
 * @param event - Native change event of the file input.
 */
function handleComposerAttachments(event: Event): void {
  const input: HTMLInputElement = event.target as HTMLInputElement
  for (const file of Array.from(input.files ?? [])) {
    if (!ALLOWED_TYPES.includes(file.type)) {
      toast.error('Format non pris en charge. Utilisez PNG, JPG ou WEBP.')
      continue
    }
    if (file.size > MAX_ATTACHMENT_BYTES) {
      toast.error('Fichier trop volumineux (8 Mo maximum par image).')
      continue
    }
    composerFiles.value.push(file)
    composerPreviews.value.push({ url: URL.createObjectURL(file), name: file.name })
  }
  if (composerInput.value) composerInput.value.value = ''
}

/**
 * Remove a staged image and release its preview URL.
 * @param index - Position in the staged list.
 */
function removeComposerAttachment(index: number): void {
  const preview: { url: string; name: string } | undefined = composerPreviews.value[index]
  if (preview) URL.revokeObjectURL(preview.url)
  composerFiles.value.splice(index, 1)
  composerPreviews.value.splice(index, 1)
}

/**
 * Append a message to the thread when it is not already there.
 * @param message - Message to add.
 */
function appendMessage(message: SupportMessage): void {
  if (!ticket.value) return
  if (ticket.value.messages.some((item: SupportMessage): boolean => item.id === message.id)) return
  ticket.value.messages.push(message)
  ticket.value.last_message_at = message.created_at
  scrollToBottom()
}

/**
 * Apply a realtime event scoped to this ticket.
 * @param event - Incoming websocket payload.
 */
function handleWebsocketEvent(event: SupportWebsocketEvent): void {
  if (!event?.event || !ticket.value) return
  if (event.event === 'message.created' && event.data?.ticket_id === ticket.value.id) {
    appendMessage(event.data as unknown as SupportMessage)
    return
  }
  if (event.event === 'ticket.updated' && event.data?.id === ticket.value.id) {
    ticket.value = { ...ticket.value, ...event.data, messages: ticket.value.messages }
  }
}

/**
 * Notify about activity happening on OTHER tickets.
 * @param event - Incoming websocket payload.
 */
function handleGlobalWebsocketEvent(event: SupportWebsocketEvent): void {
  if (!event?.event) return
  const isAdmin: boolean = userStore.user?.role === 'ADMIN'

  if (event.event === 'ticket.message') {
    // Déjà sur ce ticket : la conversation se met à jour, pas besoin de toast.
    if (event.data?.id && event.data.id === ticketId.value) return
    const senderId: unknown = event.data?._sender_id
    const currentUserId: number | undefined = userStore.user?.id
    const shouldNotify: unknown =
      senderId && currentUserId && senderId !== currentUserId && (event.data?.user_id === currentUserId || isAdmin)
    if (shouldNotify) {
      toast.info(`${String(event.data?._sender_name)} a répondu à « ${String(event.data?.subject || 'un ticket')} »`)
    }
    return
  }

  if (event.event === 'ticket.created' && isAdmin) {
    const author: unknown = event.data?.user_name
    if (author && author !== userStore.user?.name) toast.info(`Nouveau ticket créé par ${String(author)}`)
  }
}

/**
 * Close the per-ticket realtime connection, if any.
 */
function disconnectWebSocket(): void {
  if (websocketRef.value) {
    websocketRef.value.close()
    websocketRef.value = null
  }
}

/**
 * Close the global realtime connection, if any.
 */
function disconnectGlobalWebSocket(): void {
  if (globalWebsocketRef.value) {
    globalWebsocketRef.value.close()
    globalWebsocketRef.value = null
  }
}

/**
 * Build a websocket URL on the API host.
 * @param path - Path appended after the API prefix.
 * @param token - Auth token passed as a query param.
 * @returns The absolute ws/wss URL.
 */
function buildSocketUrl(path: string, token: string): string {
  const apiUrl: URL = new URL(runtimeConfig.public.apiBase)
  apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  apiUrl.pathname = `${apiUrl.pathname.replace(/\/$/, '')}/api/v1/support/${path}`
  apiUrl.searchParams.set('token', token)
  return apiUrl.toString()
}

/**
 * Open the realtime connection scoped to this ticket.
 */
function connectWebSocket(): void {
  disconnectWebSocket()
  const token: string | null = userStore.token
  if (!token || !ticket.value) return
  try {
    const ws: WebSocket = new WebSocket(buildSocketUrl(`tickets/${ticket.value.id}/ws`, token))
    websocketRef.value = ws
    ws.onmessage = (event: MessageEvent): void => {
      try {
        handleWebsocketEvent(JSON.parse(event.data))
      } catch {
        // Événement illisible : on ignore.
      }
    }
    ws.onclose = (): void => {
      websocketRef.value = null
    }
  } catch {
    // Pas de temps réel : la page reste utilisable.
  }
}

/**
 * Open the global realtime connection (notifications for other tickets).
 */
function connectGlobalWebSocket(): void {
  disconnectGlobalWebSocket()
  const token: string | null = userStore.token
  if (!token) return
  try {
    const ws: WebSocket = new WebSocket(buildSocketUrl('tickets/ws', token))
    globalWebsocketRef.value = ws
    ws.onmessage = (event: MessageEvent): void => {
      try {
        handleGlobalWebsocketEvent(JSON.parse(event.data))
      } catch {
        // Événement illisible : on ignore.
      }
    }
    ws.onclose = (): void => {
      globalWebsocketRef.value = null
    }
  } catch {
    // Pas de notifications temps réel : sans impact sur la page.
  }
}

/**
 * Load the ticket and open its realtime connection.
 * @returns A promise resolving once loaded.
 */
async function loadTicket(): Promise<void> {
  if (!ticketId.value) return
  try {
    isLoading.value = true
    ticket.value = await SupportService.getTicket(ticketId.value)
    await nextTick()
    scrollToBottom()
    connectWebSocket()
  } catch {
    toast.error('Impossible de charger ce ticket pour le moment.')
  } finally {
    isLoading.value = false
  }
}

/**
 * Post the composed reply (text and/or images).
 * @returns A promise resolving once sent.
 */
async function sendMessage(): Promise<void> {
  if (!ticket.value || (!messageInput.value.trim() && composerFiles.value.length === 0)) return
  try {
    isSending.value = true
    const message: SupportMessage = await SupportService.postMessage(ticket.value.id, {
      message: messageInput.value.trim() || ' ',
      attachments: composerFiles.value,
    })
    appendMessage(message)
    messageInput.value = ''
    composerFiles.value = []
    composerPreviews.value.forEach((preview: { url: string; name: string }): void => URL.revokeObjectURL(preview.url))
    composerPreviews.value = []
    if (composerInput.value) composerInput.value.value = ''
  } catch {
    toast.error("Impossible d'envoyer votre réponse. Réessayez.")
  } finally {
    isSending.value = false
  }
}

/**
 * Send on Enter, newline on Shift+Enter.
 * @param event - Keyboard event from the composer.
 */
function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void sendMessage()
  }
}

watch(
  (): string | string[] => route.params.id ?? '',
  (): void => {
    disconnectWebSocket()
    ticket.value = null
    composerFiles.value = []
    composerPreviews.value.forEach((preview: { url: string; name: string }): void => URL.revokeObjectURL(preview.url))
    composerPreviews.value = []
    if (composerInput.value) composerInput.value.value = ''
    void loadTicket()
  },
)

onMounted((): void => {
  void loadTicket()
  connectGlobalWebSocket()
})

onBeforeUnmount((): void => {
  disconnectWebSocket()
  disconnectGlobalWebSocket()
  composerPreviews.value.forEach((preview: { url: string; name: string }): void => URL.revokeObjectURL(preview.url))
})
</script>
