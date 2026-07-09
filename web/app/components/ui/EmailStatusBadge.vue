<template>
  <span :class="['app-badge', config.variant]">
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
  /** app-badge variant modifier ('' = neutral). */
  variant: string
}

/**
 * Visual configuration for every possible EmailStatus value, mapped onto the
 * four semantic badge families of the app theme (neutral / progress /
 * success / danger). Using ``Record<EmailStatus, StatusConfig>`` ensures a
 * compile error if a new status is added without updating this map.
 */
const STATUS_CONFIG: Record<EmailStatus, StatusConfig> = {
  pending: { label: 'En attente', icon: 'fa-solid fa-clock', variant: '' },
  sending: { label: 'Envoi…', icon: 'fa-solid fa-spinner fa-spin', variant: 'app-badge--progress' },
  scheduled: { label: 'Planifié', icon: 'fa-solid fa-calendar-clock', variant: 'app-badge--progress' },
  sent: { label: 'Envoyé', icon: 'fa-solid fa-paper-plane', variant: 'app-badge--progress' },
  delivered: { label: 'Délivré', icon: 'fa-solid fa-check', variant: 'app-badge--success' },
  delivery_delayed: {
    label: 'Retardé',
    icon: 'fa-solid fa-clock-rotate-left',
    variant: 'app-badge--progress',
  },
  opened: { label: 'Ouvert', icon: 'fa-regular fa-envelope-open', variant: 'app-badge--success' },
  clicked: { label: 'Cliqué', icon: 'fa-solid fa-arrow-pointer', variant: 'app-badge--success' },
  bounced: { label: 'Bounce', icon: 'fa-solid fa-triangle-exclamation', variant: 'app-badge--danger' },
  failed: { label: 'Échoué', icon: 'fa-solid fa-xmark', variant: 'app-badge--danger' },
  complained: { label: 'Spam', icon: 'fa-solid fa-ban', variant: 'app-badge--danger' },
  suppressed: { label: 'Supprimé', icon: 'fa-solid fa-circle-minus', variant: '' },
}

const config: ComputedRef<StatusConfig> = computed(
  (): StatusConfig => STATUS_CONFIG[props.status] ?? STATUS_CONFIG.pending,
)
</script>
