<template>
  <span :class="['app-badge', config.variant]">
    <UIcon :name="config.icon" :class="['h-3 w-3', config.spin && 'animate-spin']" />
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
  /** Lucide icon name. */
  icon: string
  /** app-badge variant modifier ('' = neutral). */
  variant: string
  /** Whether the icon should spin (in-progress states). */
  spin?: boolean
}

/**
 * Visual configuration for every possible EmailStatus value. Each step of the
 * positive funnel gets its own colour family so a list of logs reads at a
 * glance: sent = info (blue), delivered = success (green), opened = engaged
 * (violet), clicked = strong (full ink). Transient states are progress
 * (amber), failures are danger (red). Using ``Record<EmailStatus,
 * StatusConfig>`` ensures a compile error if a new status is added without
 * updating this map.
 */
const STATUS_CONFIG: Record<EmailStatus, StatusConfig> = {
  pending: { label: 'En attente', icon: 'i-lucide-clock', variant: '' },
  sending: { label: 'Envoi…', icon: 'i-lucide-loader-circle', variant: 'app-badge--progress', spin: true },
  scheduled: { label: 'Planifié', icon: 'i-lucide-calendar-clock', variant: 'app-badge--progress' },
  sent: { label: 'Envoyé', icon: 'i-lucide-send', variant: 'app-badge--info' },
  delivered: { label: 'Délivré', icon: 'i-lucide-check', variant: 'app-badge--success' },
  delivery_delayed: {
    label: 'Retardé',
    icon: 'i-lucide-clock-alert',
    variant: 'app-badge--progress',
  },
  opened: { label: 'Ouvert', icon: 'i-lucide-mail-open', variant: 'app-badge--engaged' },
  clicked: { label: 'Cliqué', icon: 'i-lucide-mouse-pointer-click', variant: 'app-badge--strong' },
  bounced: { label: 'Bounce', icon: 'i-lucide-triangle-alert', variant: 'app-badge--danger' },
  failed: { label: 'Échoué', icon: 'i-lucide-x', variant: 'app-badge--danger' },
  complained: { label: 'Spam', icon: 'i-lucide-ban', variant: 'app-badge--danger' },
  suppressed: { label: 'Supprimé', icon: 'i-lucide-circle-minus', variant: '' },
}

const config: ComputedRef<StatusConfig> = computed(
  (): StatusConfig => STATUS_CONFIG[props.status] ?? STATUS_CONFIG.pending,
)
</script>
