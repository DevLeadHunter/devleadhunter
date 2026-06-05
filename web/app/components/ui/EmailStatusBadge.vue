<template>
  <span :class="['inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold', config.bg, config.text]">
    <i :class="[config.icon, 'text-[10px]']"></i>
    {{ config.label }}
  </span>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { EmailStatus } from '~/types'
import type { EmailStatusBadgeProps } from '~/types/EmailStatusBadge'

// ─── Props ────────────────────────────────────────────────────────────────────

/**
 * Defines the component props.
 */
const props: EmailStatusBadgeProps = defineProps({
  status: {
    type: String as PropType<EmailStatus>,
    required: true,
  },
})

// ─── Visual config ────────────────────────────────────────────────────────────

interface StatusConfig {
  /** Human-readable French label. */
  label: string
  /** Font Awesome icon class. */
  icon: string
  /** Tailwind background class. */
  bg: string
  /** Tailwind text colour class. */
  text: string
}

/**
 * Visual configuration for every possible EmailStatus value.
 * Using ``Record<EmailStatus, StatusConfig>`` ensures a compile error if a
 * new status is added to the union without updating this map.
 */
const STATUS_CONFIG: Record<EmailStatus, StatusConfig> = {
  pending: { label: 'En attente', icon: 'fa-solid fa-clock', bg: 'bg-[#30363d]', text: 'text-[#8b949e]' },
  sending: { label: 'Envoi…', icon: 'fa-solid fa-spinner fa-spin', bg: 'bg-[#1f3a5c]', text: 'text-[#58a6ff]' },
  scheduled: { label: 'Planifié', icon: 'fa-solid fa-calendar-clock', bg: 'bg-[#1f3a5c]', text: 'text-[#58a6ff]' },
  sent: { label: 'Envoyé', icon: 'fa-solid fa-paper-plane', bg: 'bg-[#1f3a5c]', text: 'text-[#58a6ff]' },
  delivered: { label: 'Délivré', icon: 'fa-solid fa-check', bg: 'bg-[#1a3a2a]', text: 'text-[#3fb950]' },
  delivery_delayed: {
    label: 'Retardé',
    icon: 'fa-solid fa-clock-rotate-left',
    bg: 'bg-[#3a2a0a]',
    text: 'text-[#fbbf24]',
  },
  opened: { label: 'Ouvert', icon: 'fa-regular fa-envelope-open', bg: 'bg-[#2a2060]', text: 'text-[#a78bfa]' },
  clicked: { label: 'Cliqué', icon: 'fa-solid fa-cursor', bg: 'bg-[#2a1a6c]', text: 'text-[#c4b5fd]' },
  bounced: { label: 'Bounce', icon: 'fa-solid fa-triangle-exclamation', bg: 'bg-[#3a1a1a]', text: 'text-[#DC4747]' },
  failed: { label: 'Échoué', icon: 'fa-solid fa-xmark', bg: 'bg-[#3a1a1a]', text: 'text-[#DC4747]' },
  complained: { label: 'Spam', icon: 'fa-solid fa-ban', bg: 'bg-[#3a2a1a]', text: 'text-[#f97316]' },
  suppressed: { label: 'Supprimé', icon: 'fa-solid fa-circle-minus', bg: 'bg-[#2a1a2a]', text: 'text-[#c084fc]' },
}

const config: ComputedRef<StatusConfig> = computed(
  (): StatusConfig => STATUS_CONFIG[props.status] ?? STATUS_CONFIG.pending,
)
</script>
