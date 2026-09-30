<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open && log"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] shadow-2xl"
      >
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>

          <div class="min-w-0 flex-1">
            <div class="mb-1.5 flex flex-wrap items-center gap-1.5">
              <UiEmailStatusBadge
                v-for="s in statusBadges"
                :key="s"
                :status="s"
                :count="s === 'opened' ? (log.open_count ?? 1) : 1"
              />
              <span
                v-if="campaignName"
                class="inline-flex items-center gap-1 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)] px-2 py-0.5 text-[10px] font-medium text-[var(--app-ink-soft)]"
              >
                <UIcon name="i-lucide-megaphone" class="h-2.5 w-2.5" />
                {{ campaignName }}
              </span>
            </div>
            <h2 class="truncate text-base leading-tight font-semibold text-[var(--app-ink)]">
              {{ log.recipient_name || log.recipient_email }}
            </h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">{{ log.recipient_email }}</p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto">
          <div class="px-5 py-4">
            <div class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface-2)] p-4">
              <p class="mb-1 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Sujet</p>
              <p class="text-sm leading-snug font-medium text-[var(--app-ink)]">{{ log.subject }}</p>
            </div>
          </div>

          <div class="px-5 pb-2">
            <p class="mb-4 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Suivi</p>
            <UTimeline :items="timelineItems" size="md" color="neutral" :ui="{ date: 'text-[var(--app-ink-soft)]' }" />
          </div>

          <template v-if="threadItems.length > 0 || replyTarget">
            <div class="mx-5 border-t border-[var(--app-surface-2)]"></div>

            <div class="px-5 py-4">
              <p class="mb-3 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
                Conversation
              </p>

              <div class="space-y-3">
                <template v-for="item in threadItems" :key="threadItemKey(item)">
                  <UiScheduledReplyCard v-if="item.scheduled_id" :item="item" @changed="onScheduledChanged" />
                  <div v-else :class="item.direction === 'inbound' ? 'mr-6' : 'ml-6'">
                    <div
                      :class="[
                        'rounded-xl border px-3 py-2.5',
                        item.direction === 'inbound'
                          ? 'border-[var(--app-line)] bg-[var(--app-surface-2)]'
                          : 'border-[var(--app-accent)]/25 bg-[var(--app-accent-soft)]',
                      ]"
                    >
                      <div class="mb-1 flex flex-wrap items-center gap-2">
                        <span class="text-[11px] font-medium text-[var(--app-ink)]">
                          {{ item.direction === 'inbound' ? item.counterpart : 'Moi' }}
                        </span>
                        <span v-if="item.timestamp" class="text-[10px] text-[var(--app-faint)]">
                          {{ formatCompactDateTime(item.timestamp) }}
                        </span>
                        <span v-if="item.is_auto_reply" class="app-badge text-[10px]">
                          <UIcon name="i-lucide-bot" class="h-2.5 w-2.5" />
                          Réponse automatique
                        </span>
                        <template v-else>
                          <span
                            v-if="item.intent && INTENT_BADGES[item.intent]"
                            :class="['app-badge text-[10px]', INTENT_BADGES[item.intent]?.variant]"
                          >
                            <UIcon :name="INTENT_BADGES[item.intent]?.icon ?? 'i-lucide-tag'" class="h-2.5 w-2.5" />
                            {{ INTENT_BADGES[item.intent]?.label }}
                          </span>
                          <span v-if="item.pending" class="app-badge app-badge--progress text-[10px]">
                            <UIcon name="i-lucide-clock" class="h-2.5 w-2.5" />
                            À traiter
                          </span>
                        </template>
                      </div>
                      <p
                        v-if="item.direction === 'inbound'"
                        class="text-xs leading-relaxed [overflow-wrap:anywhere] break-words whitespace-pre-wrap text-[var(--app-ink)]"
                      >
                        {{ item.body_text }}
                      </p>
                      <!-- eslint-disable vue/no-v-html -- Outbound replies are our own HTML (message + signature) -->
                      <div
                        v-else-if="item.body_html"
                        class="mt-0.5 overflow-hidden rounded-md border border-[var(--app-line)]/50 bg-white p-2 text-xs text-neutral-900"
                        v-html="stripScriptTags(item.body_html)"
                      />
                      <!-- eslint-enable vue/no-v-html -->
                      <p
                        v-else
                        class="text-xs leading-relaxed [overflow-wrap:anywhere] break-words whitespace-pre-wrap text-[var(--app-ink)]"
                      >
                        {{ outboundPreview(item) }}
                      </p>
                      <button
                        v-if="item.intent === 'unsubscribe' && item.pending"
                        class="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-[var(--app-red)]/40 px-2.5 py-1 text-[11px] font-medium text-[var(--app-red)] transition-colors hover:bg-[var(--app-red)]/10"
                        title="Ajoute cette adresse aux désinscrits — plus aucune prospection ne lui sera envoyée"
                        @click="unsubscribeFromReply(item.id)"
                      >
                        <UIcon name="i-lucide-user-x" class="h-3 w-3" />
                        Honorer la désinscription
                      </button>
                    </div>
                  </div>
                </template>
              </div>

              <div v-if="replyTarget" class="mt-4">
                <textarea
                  v-model="replyText"
                  rows="4"
                  class="input-field w-full text-sm"
                  placeholder="Votre réponse au prospect…"
                ></textarea>
                <UiScheduleSendControls
                  class="mt-2"
                  :can-send="replyText.trim().length > 0"
                  :is-busy="isSendingReply"
                  send-label="Envoyer la réponse"
                  @send="sendReply"
                  @schedule="scheduleReply"
                >
                  <template #secondary>
                    <button
                      v-if="pendingTarget"
                      class="text-muted text-xs font-medium transition-colors hover:text-[var(--app-ink)]"
                      title="J'ai déjà répondu ailleurs (ex : depuis ma boîte mail)"
                      @click="markHandled(pendingTarget.id)"
                    >
                      Marquer comme traité sans répondre
                    </button>
                  </template>
                </UiScheduleSendControls>
                <p class="text-muted mt-1.5 text-[11px]">
                  Envoyée dans le fil de discussion du prospect, sa prochaine réponse reviendra ici. L'horloge à côté du
                  bouton la programme pour plus tard.
                </p>
              </div>
            </div>
          </template>

          <div class="mx-5 border-t border-[var(--app-surface-2)]"></div>

          <div class="px-5 py-4">
            <p class="mb-3 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Contenu</p>
            <iframe
              v-if="sanitizedBodyHtml"
              :srcdoc="sanitizedBodyHtml"
              sandbox="allow-same-origin"
              class="h-64 w-full rounded-xl border border-[var(--app-line)] bg-white"
              title="Email preview"
            />
            <div
              v-else
              class="flex h-24 items-center justify-center rounded-xl border border-dashed border-[var(--app-line)] bg-[var(--app-surface)]"
            >
              <p class="text-xs text-[var(--app-faint)]">Contenu non disponible</p>
            </div>

            <a
              v-if="sentDemoLink"
              :href="sentDemoLink"
              target="_blank"
              rel="noopener"
              class="font-label mt-3 inline-flex items-center gap-2 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-2.5 py-1.5 text-xs text-[var(--app-ink)] transition-colors hover:border-[var(--app-accent)] hover:bg-[var(--app-accent-soft)] hover:text-[var(--app-accent-ink)]"
              title="Ouvre le lien démo exact reçu par le prospect — votre visite est exclue du suivi"
            >
              <UIcon name="i-lucide-globe" class="h-3.5 w-3.5 shrink-0" />
              Ouvrir le lien envoyé
              <UIcon name="i-lucide-arrow-up-right" class="h-3 w-3 shrink-0 opacity-70" />
            </a>
          </div>

          <div class="mx-5 border-t border-[var(--app-surface-2)]"></div>

          <div class="px-5 py-4">
            <p class="mb-3 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
              Détails techniques
            </p>
            <div class="space-y-2.5">
              <div class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                  <UIcon name="i-lucide-server" class="h-3.5 w-3.5" />
                  Fournisseur
                </span>
                <span class="text-xs font-medium text-[var(--app-ink)] capitalize">{{ log.provider }}</span>
              </div>
              <div class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                  <UIcon name="i-lucide-hash" class="h-3.5 w-3.5" />
                  ID log
                </span>
                <span class="font-mono text-xs text-[var(--app-ink)]">#{{ log.id }}</span>
              </div>
              <div v-if="log.recipient_name" class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                  <UIcon name="i-lucide-user" class="h-3.5 w-3.5" />
                  Destinataire
                </span>
                <span class="text-xs text-[var(--app-ink)]">{{ log.recipient_email }}</span>
              </div>
              <div class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                  <UIcon name="i-lucide-calendar-plus" class="h-3.5 w-3.5" />
                  Créé le
                </span>
                <span class="text-xs text-[var(--app-ink)]">{{ formatCompactDateTime(log.created_at) }}</span>
              </div>
              <div v-if="log.machine_opened_at" class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                  <UIcon name="i-lucide-bot" class="h-3.5 w-3.5" />
                  Prefetch machine
                </span>
                <span class="text-xs text-[var(--app-ink-soft)]">{{
                  formatCompactDateTime(log.machine_opened_at)
                }}</span>
              </div>
              <div v-if="log.provider_message_id" class="flex items-start justify-between gap-3">
                <span class="flex shrink-0 items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                  <UIcon name="i-lucide-fingerprint" class="h-3.5 w-3.5" />
                  Message ID
                </span>
                <span class="max-w-[240px] text-right font-mono text-[11px] break-all text-[var(--app-ink-soft)]">
                  {{ log.provider_message_id }}
                </span>
              </div>
            </div>

            <div
              v-if="log.failure || log.error_message"
              class="mt-3 rounded-lg border border-[var(--app-red)]/30 bg-[var(--app-red)]/5 px-3 py-2"
            >
              <div class="flex items-start gap-2">
                <UIcon name="i-lucide-triangle-alert" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-red)]" />
                <p class="text-xs text-[var(--app-red)]">{{ log.failure?.reason ?? log.error_message }}</p>
              </div>
              <p
                v-if="log.failure?.is_expected === true"
                class="mt-1.5 pl-[22px] text-[11px] text-[var(--app-ink-soft)]"
              >
                C'est normal, pas un problème dans le code : il suffit de la bonne adresse.
              </p>
              <p
                v-else-if="log.failure?.is_expected === false"
                class="mt-1.5 pl-[22px] text-[11px] text-[var(--app-ink-soft)]"
              >
                À vérifier côté envoi (configuration ou contenu du message).
              </p>
            </div>
          </div>
        </div>

        <div class="border-t border-[var(--app-line)] px-5 py-4">
          <template v-if="log.failure">
            <button class="btn-primary w-full" @click="emit('retry')">
              <UIcon name="i-lucide-send" class="mr-1.5 h-4 w-4" />
              Renvoyer
            </button>
            <p class="text-muted mt-2 text-center text-[11px]">Réenvoie ce mail, en corrigeant l'adresse si besoin.</p>
          </template>
          <template v-else>
            <button class="btn-primary w-full" @click="emit('resend')">
              <UIcon name="i-lucide-send" class="mr-1.5 h-4 w-4" />
              Renvoyer un email
            </button>
            <p class="text-muted mt-2 text-center text-[11px]">
              Ouvre le composeur pré-rempli avec ce destinataire, ce sujet et ce contenu.
            </p>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { EmailDeliveryStage, EmailTimelineEntry, UiEmailLogDrawerEmits } from '~/types/UiEmailLogDrawer'
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { ConversationItem, EmailLog, EmailStatus } from '~/types'
import type { EmailLogDrawerProps } from '~/types/EmailLogDrawer'
import { DemoSiteService } from '~/services/demoSiteService'
import { EmailLogsService } from '~/services/emailLogsService'
import { formatCompactDateTime, formatScheduledMoment } from '~/utils/date'
import { ReplyBodyFormat } from '~/utils/replyBodyFormat'
import { useToast } from '~/composables/useToast'
import { useDrawerStackStore } from '~/stores/drawerStack'

/** Drawer showing email delivery timeline and events. */
const props: EmailLogDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  log: {
    type: Object as PropType<EmailLog | null>,
    default: null,
  },
  campaignName: {
    type: String,
    default: undefined,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiEmailLogDrawerEmits> = defineEmits<UiEmailLogDrawerEmits>()

/**
 * Returns all status badges to display: best positive state + complaint if any.
 * @returns Ordered array of EmailStatus values.
 */
const statusBadges: ComputedRef<EmailStatus[]> = computed((): EmailStatus[] => {
  if (!props.log) return []
  const l: EmailLog = props.log
  const badges: EmailStatus[] = []

  if (l.replied_at) badges.push('replied')
  else if (l.clicked_at) badges.push('clicked')
  else if (l.opened_at) badges.push('opened')
  else if (l.delivered_at) badges.push('delivered')
  else badges.push(l.status)

  if (l.complained_at && !badges.includes('complained')) badges.push('complained')

  return badges
})

// ------------------------------------------------------------------ //
// Conversation (captured replies + threaded answers)
// ------------------------------------------------------------------ //

const toast: ReturnType<typeof useToast> = useToast()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

const conversation: Ref<ConversationItem[]> = ref([])
const replyText: Ref<string> = ref('')
const isSendingReply: Ref<boolean> = ref(false)

/** Badge presentation per LLM intent verdict on a reply. */
const INTENT_BADGES: Record<string, { label: string; icon: string; variant: string }> = {
  interested: { label: 'Intéressé', icon: 'i-lucide-target', variant: 'app-badge--success' },
  not_interested: { label: 'Pas intéressé', icon: 'i-lucide-x', variant: 'app-badge--danger' },
  later: { label: 'À relancer plus tard', icon: 'i-lucide-calendar-clock', variant: 'app-badge--progress' },
  question: { label: 'Pose une question', icon: 'i-lucide-message-circle-question', variant: 'app-badge--engaged' },
  unsubscribe: { label: 'Demande de désinscription', icon: 'i-lucide-user-x', variant: 'app-badge--danger' },
}

/** The exchange bubbles: captured replies + answers sent from the app (outreach sends stay in « Contenu »). */
const threadItems: ComputedRef<ConversationItem[]> = computed((): ConversationItem[] =>
  conversation.value.filter((item: ConversationItem) => item.direction === 'inbound' || item.is_conversation_reply),
)

/** The reply the answer box targets: the prospect's most recent human reply. */
const replyTarget: ComputedRef<ConversationItem | null> = computed((): ConversationItem | null => {
  const humans: ConversationItem[] = conversation.value.filter(
    (item: ConversationItem) => item.direction === 'inbound' && !item.is_auto_reply,
  )
  return humans.length > 0 ? (humans[humans.length - 1] ?? null) : null
})

/** The most recent reply still awaiting an answer, if any. */
const pendingTarget: ComputedRef<ConversationItem | null> = computed((): ConversationItem | null => {
  const pending: ConversationItem[] = conversation.value.filter((item: ConversationItem) => item.pending)
  return pending.length > 0 ? (pending[pending.length - 1] ?? null) : null
})

/**
 * Strip ``<script>`` tags before rendering trusted outbound HTML in the UI.
 * @param html - Raw HTML body.
 * @returns Sanitised HTML safe for ``v-html`` / iframe ``srcdoc``.
 */
function stripScriptTags(html: string): string {
  return html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
}

/**
 * Flatten an outbound answer's HTML to plain text when no HTML body is stored.
 * @param item - The outbound conversation item.
 * @returns The message as plain text.
 */
function outboundPreview(item: ConversationItem): string {
  return ReplyBodyFormat.toText(item.body_html ?? '')
}

/**
 * Stable key of a thread bubble: planned answers and sent emails share id ranges.
 * @param item - The conversation item.
 * @returns The key.
 */
function threadItemKey(item: ConversationItem): string {
  return item.scheduled_id ? `scheduled-${item.scheduled_id}` : `${item.direction}-${item.id}`
}

/**
 * Load the conversation for the currently displayed log.
 * @returns A promise resolved once loaded (silently empty on failure).
 */
async function loadConversation(): Promise<void> {
  const id: number | undefined = props.log?.id
  if (!props.open || !id) {
    conversation.value = []
    return
  }
  try {
    conversation.value = await EmailLogsService.getConversation(id)
  } catch {
    conversation.value = []
  }
}

watch(
  (): [boolean, number | undefined] => [props.open, props.log?.id],
  (): void => {
    replyText.value = ''
    void loadConversation()
  },
  { immediate: true },
)

/**
 * Send the typed answer to the prospect, threaded into their mail client.
 * @returns A promise resolved once the send is attempted.
 */
async function sendReply(): Promise<void> {
  const target: ConversationItem | null = replyTarget.value
  const text: string = replyText.value.trim()
  if (!target || !text || isSendingReply.value) return
  isSendingReply.value = true
  try {
    const html: string = ReplyBodyFormat.toHtml(text)
    const result: { success: boolean; error?: string } = await EmailLogsService.sendReply(target.id, html)
    if (result.success) {
      toast.success('Réponse envoyée')
      replyText.value = ''
      await loadConversation()
      drawerStack.bumpEmailLogsRefresh()
    } else {
      toast.error(result.error || "Échec de l'envoi de la réponse")
    }
  } catch {
    toast.error("Échec de l'envoi de la réponse")
  } finally {
    isSendingReply.value = false
  }
}

/**
 * Plan the typed answer for later; it leaves at that time exactly like « Envoyer la réponse ».
 * @param moment - When to send it.
 * @returns A promise resolved once planned.
 */
async function scheduleReply(moment: Date): Promise<void> {
  const target: ConversationItem | null = replyTarget.value
  const text: string = replyText.value.trim()
  if (!target || !text || isSendingReply.value) return
  isSendingReply.value = true
  try {
    await EmailLogsService.scheduleReply(target.id, ReplyBodyFormat.toHtml(text), moment)
    toast.success(`Réponse programmée ${formatScheduledMoment(moment)}`)
    replyText.value = ''
    await onScheduledChanged()
  } catch (error: unknown) {
    toast.error(error instanceof Error && error.message ? error.message : 'Impossible de programmer la réponse')
  } finally {
    isSendingReply.value = false
  }
}

/**
 * Reload the thread after a planned answer changed (planned, edited, cancelled or sent).
 * @returns A promise resolved once reloaded.
 */
async function onScheduledChanged(): Promise<void> {
  await loadConversation()
  drawerStack.bumpEmailLogsRefresh()
}

/**
 * Mark a reply as dealt with (answered outside the app).
 * @param replyId - The reply to mark.
 * @returns A promise resolved once marked.
 */
async function markHandled(replyId: number): Promise<void> {
  try {
    await EmailLogsService.markReplyHandled(replyId)
    toast.success('Réponse marquée comme traitée')
    await loadConversation()
    drawerStack.bumpEmailLogsRefresh()
  } catch {
    toast.error('Impossible de marquer la réponse')
  }
}

/**
 * Honour an unsubscribe request expressed in the reply (one click, user-validated).
 * @param replyId - The reply carrying the request.
 * @returns A promise resolved once done.
 */
async function unsubscribeFromReply(replyId: number): Promise<void> {
  try {
    await EmailLogsService.unsubscribeFromReply(replyId)
    toast.success('Adresse ajoutée aux désinscrits')
    await loadConversation()
    drawerStack.bumpEmailLogsRefresh()
  } catch {
    toast.error('Impossible de désinscrire cette adresse')
  }
}

/**
 * Strip ``<script>`` tags from the HTML body as a defence-in-depth measure
 * before rendering in the sandboxed iframe.
 * @returns Sanitised HTML string, or ``null`` when no body is available.
 */
const sanitizedBodyHtml: ComputedRef<string | null> = computed((): string | null => {
  const html: string | null | undefined = props.log?.body_html
  if (!html) return null
  return stripScriptTags(html)
})

/**
 * The exact demo-site link the email carried, flagged as an internal visit so opening it to verify
 * does not pollute the prospect's behaviour tracking. Excludes the video player link (``/v/``).
 * @returns The demo URL to open, or ``null`` when the body carries none.
 */
const sentDemoLink: ComputedRef<string | null> = computed((): string | null => {
  const html: string | null | undefined = props.log?.body_html
  if (!html) return null
  const match: RegExpMatchArray | null = html.match(/https?:\/\/demo\.dibodev\.fr\/(?!v\/)[^"'\s<>]+/i)
  if (!match) return null
  return DemoSiteService.withInternalFlag(match[0]) ?? match[0]
})

/** Muted indicator style applied to stages that haven't occurred yet. */
const MUTED_INDICATOR: string =
  'bg-[var(--app-surface)] text-[var(--app-faint)] ring-1 ring-inset ring-[var(--app-line)]'

/** Timeline items for UTimeline from the log's delivery events. */
const timelineItems: ComputedRef<EmailTimelineEntry[]> = computed((): EmailTimelineEntry[] => {
  if (!props.log) return []
  const l: EmailLog = props.log
  const openCount: number = l.open_count && l.open_count > 0 ? l.open_count : l.opened_at ? 1 : 0

  const stages: EmailDeliveryStage[] = [
    {
      key: 'sent',
      label: 'Envoyé',
      icon: 'i-lucide-send',
      timestamp: l.sent_at,
      alwaysShow: true,
      style: {
        indicator: 'bg-[var(--app-blue-soft)] text-[var(--app-blue)] ring-1 ring-inset ring-[var(--app-blue)]/25',
        separator: 'bg-[var(--app-blue)]/30',
      },
    },
    {
      key: 'delivered',
      label: 'Délivré',
      icon: 'i-lucide-circle-check',
      timestamp: l.delivered_at,
      alwaysShow: true,
      style: {
        indicator: 'bg-[var(--app-green-soft)] text-[var(--app-green)] ring-1 ring-inset ring-[var(--app-green)]/25',
        separator: 'bg-[var(--app-green)]/30',
      },
    },
    {
      key: 'opened',
      label: openCount > 1 ? `Ouvert · ${openCount}×` : 'Ouvert',
      icon: 'i-lucide-mail-open',
      timestamp: l.opened_at,
      alwaysShow: true,
      description:
        openCount > 1 && l.last_open_at
          ? `1ʳᵉ ${formatCompactDateTime(l.opened_at)} · dernière ${formatCompactDateTime(l.last_open_at)}`
          : undefined,
      style: {
        indicator: 'bg-[var(--app-violet-soft)] text-[var(--app-violet)] ring-1 ring-inset ring-[var(--app-violet)]/25',
        separator: 'bg-[var(--app-violet)]/30',
      },
    },
    {
      key: 'clicked',
      label: 'Cliqué',
      icon: 'i-lucide-mouse-pointer-click',
      timestamp: l.clicked_at,
      alwaysShow: true,
      style: {
        indicator: 'bg-[var(--app-ink)] text-[var(--app-bg)] ring-1 ring-inset ring-[var(--app-ink)]/20',
        separator: 'bg-[var(--app-ink)]/25',
      },
    },
    {
      key: 'replied',
      label: 'Répondu',
      icon: 'i-lucide-reply',
      timestamp: l.replied_at,
      alwaysShow: false,
      style: {
        indicator: 'bg-[var(--app-green-soft)] text-[var(--app-green)] ring-1 ring-inset ring-[var(--app-green)]/25',
        separator: 'bg-[var(--app-green)]/30',
      },
    },
    {
      key: 'bounced',
      label: 'Bounce',
      icon: 'i-lucide-undo-2',
      timestamp: l.bounced_at,
      alwaysShow: false,
      style: {
        indicator: 'bg-[var(--app-red-soft)] text-[var(--app-red)] ring-1 ring-inset ring-[var(--app-red)]/25',
        separator: 'bg-[var(--app-red)]/30',
      },
    },
    {
      key: 'complained',
      label: 'Marqué comme spam',
      icon: 'i-lucide-octagon-alert',
      timestamp: l.complained_at,
      alwaysShow: false,
      style: {
        indicator: 'bg-[var(--app-red-soft)] text-[var(--app-red)] ring-1 ring-inset ring-[var(--app-red)]/25',
        separator: 'bg-[var(--app-red)]/30',
      },
    },
    {
      key: 'suppressed',
      label: 'Adresse supprimée (liste Resend)',
      icon: 'i-lucide-circle-minus',
      timestamp: l.suppressed_at,
      alwaysShow: false,
      style: {
        indicator: 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)] ring-1 ring-inset ring-[var(--app-line)]',
        separator: 'bg-[var(--app-line)]',
      },
    },
    {
      key: 'failed',
      label: "Échec d'envoi",
      icon: 'i-lucide-x',
      timestamp: l.failed_at,
      alwaysShow: false,
      style: {
        indicator: 'bg-[var(--app-red-soft)] text-[var(--app-red)] ring-1 ring-inset ring-[var(--app-red)]/25',
        separator: 'bg-[var(--app-red)]/30',
      },
    },
  ]

  return stages
    .filter((stage: EmailDeliveryStage): boolean => stage.alwaysShow || !!stage.timestamp)
    .map((stage: EmailDeliveryStage): EmailTimelineEntry => {
      const reached: boolean = !!stage.timestamp
      return {
        value: stage.key,
        title: stage.label,
        description: reached ? (stage.description ?? formatCompactDateTime(stage.timestamp)) : 'En attente',
        icon: stage.icon,
        ui: {
          indicator: reached ? stage.style.indicator : MUTED_INDICATOR,
          separator: reached ? stage.style.separator : 'bg-[var(--app-surface-2)]',
          title: reached ? 'text-[var(--app-ink)] text-sm font-medium' : 'text-[#4b5563] text-sm font-medium',
          description: reached ? 'text-[11px] text-[var(--app-ink-soft)]' : 'text-[11px] text-[var(--app-faint)]',
        },
      }
    })
})
</script>

<style scoped>
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
