<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open && log"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
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
              <UiEmailStatusBadge v-for="s in statusBadges" :key="s" :status="s" />
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
              v-if="log.error_message"
              class="mt-3 flex items-start gap-2 rounded-lg border border-[var(--app-red)]/30 bg-[var(--app-red)]/5 px-3 py-2"
            >
              <UIcon name="i-lucide-triangle-alert" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-red)]" />
              <p class="text-xs text-[var(--app-red)]">{{ log.error_message }}</p>
            </div>
          </div>
        </div>

        <div class="border-t border-[var(--app-line)] px-5 py-4">
          <button class="btn-primary w-full" @click="emit('resend')">
            <UIcon name="i-lucide-send" class="mr-1.5 h-4 w-4" />
            Renvoyer un email
          </button>
          <p class="text-muted mt-2 text-center text-[11px]">
            Ouvre le composeur pré-rempli avec ce destinataire, ce sujet et ce contenu.
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { EmailDeliveryStage, EmailTimelineEntry, UiEmailLogDrawerEmits } from '~/types/UiEmailLogDrawer'
import type { ComputedRef, EmitFn, PropType } from 'vue'
import type { EmailLog, EmailStatus } from '~/types'
import type { EmailLogDrawerProps } from '~/types/EmailLogDrawer'
import { formatCompactDateTime } from '~/utils/date'

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

  if (l.clicked_at) badges.push('clicked')
  else if (l.opened_at) badges.push('opened')
  else if (l.delivered_at) badges.push('delivered')
  else badges.push(l.status)

  if (l.complained_at && !badges.includes('complained')) badges.push('complained')

  return badges
})

/**
 * Strip ``<script>`` tags from the HTML body as a defence-in-depth measure
 * before rendering in the sandboxed iframe.
 * @returns Sanitised HTML string, or ``null`` when no body is available.
 */
const sanitizedBodyHtml: ComputedRef<string | null> = computed((): string | null => {
  const html: string | null | undefined = props.log?.body_html
  if (!html) return null
  return html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
})

/** Muted indicator style applied to stages that haven't occurred yet. */
const MUTED_INDICATOR: string =
  'bg-[var(--app-surface)] text-[var(--app-faint)] ring-1 ring-inset ring-[var(--app-line)]'

/** Timeline items for UTimeline from the log's delivery events. */
const timelineItems: ComputedRef<EmailTimelineEntry[]> = computed((): EmailTimelineEntry[] => {
  if (!props.log) return []
  const l: EmailLog = props.log

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
      label: 'Ouvert',
      icon: 'i-lucide-mail-open',
      timestamp: l.opened_at,
      alwaysShow: true,
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
        description: reached ? formatCompactDateTime(stage.timestamp) : 'En attente',
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
