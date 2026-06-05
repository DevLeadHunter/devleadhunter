<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <Transition name="drawer-backdrop">
      <div v-if="open" class="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" @click="emit('close')" />
    </Transition>

    <!-- Panel -->
    <Transition name="drawer-panel">
      <div
        v-if="open && log"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[#30363d] bg-[#0d0d0d] shadow-2xl"
      >
        <!-- ───────────────────────── Header ───────────────────────── -->
        <div class="flex items-start gap-3 border-b border-[#30363d] px-5 py-4">
          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[#30363d] bg-gradient-to-br from-[#1f2937] to-[#111827]"
          >
            <UIcon name="i-lucide-mail" class="h-5 w-5 text-[#58a6ff]" />
          </div>

          <div class="min-w-0 flex-1">
            <div class="mb-1.5 flex flex-wrap items-center gap-1.5">
              <UiEmailStatusBadge v-for="s in statusBadges" :key="s" :status="s" />
              <span
                v-if="campaignName"
                class="inline-flex items-center gap-1 rounded-full border border-[#30363d] bg-[#1a1a1a] px-2 py-0.5 text-[10px] font-medium text-[#8b949e]"
              >
                <UIcon name="i-lucide-megaphone" class="h-2.5 w-2.5" />
                {{ campaignName }}
              </span>
            </div>
            <h2 class="truncate text-base leading-tight font-semibold text-[#f9f9f9]">
              {{ log.recipient_name || log.recipient_email }}
            </h2>
            <p class="mt-0.5 truncate text-[11px] text-[#8b949e]">{{ log.recipient_email }}</p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[#8b949e] transition-colors hover:bg-[#1a1a1a] hover:text-[#f9f9f9]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- ───────────────────────── Body ────────────────────────── -->
        <div class="flex-1 overflow-y-auto">
          <!-- Subject card -->
          <div class="px-5 py-4">
            <div class="rounded-xl border border-[#30363d] bg-[#111318] p-4">
              <p class="mb-1 text-[10px] font-semibold tracking-wider text-[#8b949e] uppercase">Sujet</p>
              <p class="text-sm leading-snug font-medium text-[#f9f9f9]">{{ log.subject }}</p>
            </div>
          </div>

          <!-- Timeline -->
          <div class="px-5 pb-2">
            <p class="mb-4 text-[10px] font-semibold tracking-wider text-[#8b949e] uppercase">Suivi</p>
            <UTimeline :items="timelineItems" size="md" color="neutral" :ui="{ date: 'text-[#8b949e]' }" />
          </div>

          <!-- Divider -->
          <div class="mx-5 border-t border-[#1f1f1f]"></div>

          <!-- Email content -->
          <div class="px-5 py-4">
            <p class="mb-3 text-[10px] font-semibold tracking-wider text-[#8b949e] uppercase">Contenu</p>
            <iframe
              v-if="sanitizedBodyHtml"
              :srcdoc="sanitizedBodyHtml"
              sandbox="allow-same-origin"
              class="h-64 w-full rounded-xl border border-[#30363d] bg-white"
              title="Email preview"
            />
            <div
              v-else
              class="flex h-24 items-center justify-center rounded-xl border border-dashed border-[#30363d] bg-[#0d0d0d]"
            >
              <p class="text-xs text-[#30363d]">Contenu non disponible</p>
            </div>
          </div>

          <!-- Divider -->
          <div class="mx-5 border-t border-[#1f1f1f]"></div>

          <!-- Technical details -->
          <div class="px-5 py-4">
            <p class="mb-3 text-[10px] font-semibold tracking-wider text-[#8b949e] uppercase">Détails techniques</p>
            <div class="space-y-2.5">
              <div class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-xs text-[#8b949e]">
                  <UIcon name="i-lucide-server" class="h-3.5 w-3.5" />
                  Fournisseur
                </span>
                <span class="text-xs font-medium text-[#f9f9f9] capitalize">{{ log.provider }}</span>
              </div>
              <div class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-xs text-[#8b949e]">
                  <UIcon name="i-lucide-hash" class="h-3.5 w-3.5" />
                  ID log
                </span>
                <span class="font-mono text-xs text-[#f9f9f9]">#{{ log.id }}</span>
              </div>
              <div v-if="log.recipient_name" class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-xs text-[#8b949e]">
                  <UIcon name="i-lucide-user" class="h-3.5 w-3.5" />
                  Destinataire
                </span>
                <span class="text-xs text-[#f9f9f9]">{{ log.recipient_email }}</span>
              </div>
              <div class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-xs text-[#8b949e]">
                  <UIcon name="i-lucide-calendar-plus" class="h-3.5 w-3.5" />
                  Créé le
                </span>
                <span class="text-xs text-[#f9f9f9]">{{ formatDate(log.created_at) }}</span>
              </div>
              <div v-if="log.provider_message_id" class="flex items-start justify-between gap-3">
                <span class="flex shrink-0 items-center gap-2 text-xs text-[#8b949e]">
                  <UIcon name="i-lucide-fingerprint" class="h-3.5 w-3.5" />
                  Message ID
                </span>
                <span class="max-w-[240px] text-right font-mono text-[11px] break-all text-[#8b949e]">
                  {{ log.provider_message_id }}
                </span>
              </div>
            </div>

            <!-- Error -->
            <div
              v-if="log.error_message"
              class="mt-3 flex items-start gap-2 rounded-lg border border-[#DC4747]/30 bg-[#DC4747]/5 px-3 py-2"
            >
              <UIcon name="i-lucide-triangle-alert" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#DC4747]" />
              <p class="text-xs text-[#DC4747]">{{ log.error_message }}</p>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { EmailLog, EmailStatus } from '~/types'
import type { EmailLogDrawerProps } from '~/types/EmailLogDrawer'
import { formatDate } from '~/utils/date'

// ─── Props & emits ────────────────────────────────────────────────────────────

/**
 * Defines the component props.
 */
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
})

const emit = defineEmits<{
  /** Fired when the user dismisses the drawer. */
  (e: 'close'): void
}>()

// ─── Status badges ────────────────────────────────────────────────────────────

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

// ─── Email body ───────────────────────────────────────────────────────────────

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

// ─── Timeline ─────────────────────────────────────────────────────────────────

/** Per-stage visual configuration for the timeline indicator + connector. */
interface StageStyle {
  /** Tailwind classes for the colored indicator circle (reached state). */
  indicator: string
  /** Tailwind class for the connector line below a reached node. */
  separator: string
}

/** A single definition for one possible email event stage. */
interface StageDef {
  /** Stable key used as the timeline item value. */
  key: string
  /** French label shown as the item title. */
  label: string
  /** Lucide icon name. */
  icon: string
  /** Timestamp for this stage, or null/undefined when it hasn't happened. */
  ts: string | null | undefined
  /** Visual style applied when the stage is reached. */
  style: StageStyle
  /** When false, the stage is only rendered if it actually occurred. */
  alwaysShow: boolean
}

/** Shape of a Nuxt UI timeline item with per-item style overrides. */
interface EmailTimelineItem {
  value: string
  title: string
  description?: string
  icon: string
  ui: {
    indicator: string
    title: string
    description: string
    separator: string
  }
}

/** Muted indicator style applied to stages that haven't occurred yet. */
const MUTED_INDICATOR: string = 'bg-[#0d0d0d] text-[#30363d] ring-1 ring-inset ring-[#30363d]'

/**
 * Build the ordered list of timeline items for the Nuxt UI ``UTimeline``.
 *
 * Positive stages (sent → delivered → opened → clicked) are always shown,
 * dimmed when not yet reached, so the recipient's journey is visible at a
 * glance.  Negative stages (bounced, spam, failed) appear only when they
 * actually occurred.  Each item carries per-item ``ui`` overrides so every
 * stage gets its own colour.
 * @returns Array of timeline items consumable by ``UTimeline``.
 */
const timelineItems: ComputedRef<EmailTimelineItem[]> = computed((): EmailTimelineItem[] => {
  if (!props.log) return []
  const l: EmailLog = props.log

  const stages: StageDef[] = [
    {
      key: 'sent',
      label: 'Envoyé',
      icon: 'i-lucide-send',
      ts: l.sent_at,
      alwaysShow: true,
      style: {
        indicator: 'bg-[#0d2847] text-[#58a6ff] ring-1 ring-inset ring-[#1f3a5c]',
        separator: 'bg-[#1f3a5c]',
      },
    },
    {
      key: 'delivered',
      label: 'Délivré',
      icon: 'i-lucide-circle-check',
      ts: l.delivered_at,
      alwaysShow: true,
      style: {
        indicator: 'bg-[#0f2e1a] text-[#3fb950] ring-1 ring-inset ring-[#1a3a2a]',
        separator: 'bg-[#1a3a2a]',
      },
    },
    {
      key: 'opened',
      label: 'Ouvert',
      icon: 'i-lucide-mail-open',
      ts: l.opened_at,
      alwaysShow: true,
      style: {
        indicator: 'bg-[#1e1b4b] text-[#a78bfa] ring-1 ring-inset ring-[#2a2060]',
        separator: 'bg-[#2a2060]',
      },
    },
    {
      key: 'clicked',
      label: 'Cliqué',
      icon: 'i-lucide-mouse-pointer-click',
      ts: l.clicked_at,
      alwaysShow: true,
      style: {
        indicator: 'bg-[#241a52] text-[#c4b5fd] ring-1 ring-inset ring-[#2a1a6c]',
        separator: 'bg-[#2a1a6c]',
      },
    },
    {
      key: 'bounced',
      label: 'Bounce',
      icon: 'i-lucide-undo-2',
      ts: l.bounced_at,
      alwaysShow: false,
      style: {
        indicator: 'bg-[#2d1212] text-[#DC4747] ring-1 ring-inset ring-[#3a1a1a]',
        separator: 'bg-[#3a1a1a]',
      },
    },
    {
      key: 'complained',
      label: 'Marqué comme spam',
      icon: 'i-lucide-octagon-alert',
      ts: l.complained_at,
      alwaysShow: false,
      style: {
        indicator: 'bg-[#2d1f0a] text-[#f97316] ring-1 ring-inset ring-[#3a2a1a]',
        separator: 'bg-[#3a2a1a]',
      },
    },
    {
      key: 'suppressed',
      label: 'Adresse supprimée (liste Resend)',
      icon: 'i-lucide-circle-minus',
      ts: l.suppressed_at,
      alwaysShow: false,
      style: {
        indicator: 'bg-[#1f0f2d] text-[#c084fc] ring-1 ring-inset ring-[#2a1a2a]',
        separator: 'bg-[#2a1a2a]',
      },
    },
    {
      key: 'failed',
      label: "Échec d'envoi",
      icon: 'i-lucide-x',
      ts: l.failed_at,
      alwaysShow: false,
      style: {
        indicator: 'bg-[#2d1212] text-[#DC4747] ring-1 ring-inset ring-[#3a1a1a]',
        separator: 'bg-[#3a1a1a]',
      },
    },
  ]

  return stages
    .filter((s: StageDef): boolean => s.alwaysShow || !!s.ts)
    .map((s: StageDef): EmailTimelineItem => {
      const reached: boolean = !!s.ts
      return {
        value: s.key,
        title: s.label,
        description: reached ? formatDate(s.ts) : 'En attente',
        icon: s.icon,
        ui: {
          indicator: reached ? s.style.indicator : MUTED_INDICATOR,
          separator: reached ? s.style.separator : 'bg-[#30363d]',
          title: reached ? 'text-[#f9f9f9] text-sm font-medium' : 'text-[#4b5563] text-sm font-medium',
          description: reached ? 'text-[11px] text-[#8b949e]' : 'text-[11px] text-[#30363d]',
        },
      }
    })
})
</script>

<style scoped>
.drawer-backdrop-enter-active,
.drawer-backdrop-leave-active {
  transition: opacity 0.2s ease;
}
.drawer-backdrop-enter-from,
.drawer-backdrop-leave-to {
  opacity: 0;
}

.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
