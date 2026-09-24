<template>
  <span class="cs-badge" :class="toneClass"><slot /></span>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import type { ClientSpaceBadgeProps, ClientSpaceBadgeTone } from '~/types/ClientSpaceBadge'

/**
 * A small pill of the client space: a request's type, a flag, an appointment's kind.
 * @param tone Tinted with the business's colour (default), alarming, or discreet.
 */
const props: ClientSpaceBadgeProps = defineProps({
  tone: { type: String as PropType<ClientSpaceBadgeTone>, default: 'accent' },
})

const toneClass: ComputedRef<string> = computed((): string => `cs-badge--${props.tone}`)
</script>

<style scoped>
.cs-badge {
  border-radius: 999px;
  font-size: 12px;
}

.cs-badge--accent {
  padding: 2px 10px;
  font-weight: 600;
  color: var(--cs-ink);
  background: var(--cs-accent-soft);
}

.cs-badge--danger {
  padding: 2px 10px;
  font-weight: 600;
  color: var(--cs-on-ink);
  background: var(--cs-danger);
}

.cs-badge--outline {
  border: 1px solid var(--cs-line);
  padding: 1px 8px;
  color: var(--cs-ink-dim);
}
</style>
