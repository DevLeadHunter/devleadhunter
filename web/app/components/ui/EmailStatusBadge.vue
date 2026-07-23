<template>
  <span :class="['app-badge', config.variant]">
    <UIcon :name="config.icon" :class="['h-3 w-3', config.spin && 'animate-spin']" />
    {{ config.label }}
  </span>
</template>

<script lang="ts" setup>
import type { EmailStatusPresentation, EmailStatusBadgeProps } from '~/types/EmailStatusBadge'
import type { ComputedRef, PropType } from 'vue'
import type { EmailStatus } from '~/types'

/** Badge for a single email delivery status. */
const props: EmailStatusBadgeProps = defineProps({
  status: {
    type: String as PropType<EmailStatus>,
    required: true,
  },
})

/** Per-status badge colours and icons for email delivery states. */
const STATUS_CONFIG: Record<EmailStatus, EmailStatusPresentation> = {
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

const config: ComputedRef<EmailStatusPresentation> = computed(
  (): EmailStatusPresentation => STATUS_CONFIG[props.status] ?? STATUS_CONFIG.pending,
)
</script>
