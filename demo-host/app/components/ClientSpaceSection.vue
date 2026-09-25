<template>
  <section class="cs-section">
    <header class="cs-section__head">
      <h2 class="cs-section__title">{{ props.title }}</h2>
      <span v-if="props.meta !== null" class="cs-section__meta">{{ props.meta }}</span>
    </header>
    <slot />
  </section>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { ClientSpaceSectionProps } from '~/types/ClientSpaceSection'

/**
 * A card of the client space: its title, a short status on the title's right, then its content.
 * @param title The section title.
 * @param meta The short status right of the title; none when null.
 */
const props: ClientSpaceSectionProps = defineProps({
  title: { type: String, required: true },
  meta: { type: String as PropType<string | null>, default: null },
})
</script>

<style scoped>
.cs-section {
  border: 1px solid var(--cs-line);
  border-radius: 18px;
  background: color-mix(in srgb, var(--cs-card) 70%, transparent);
  padding: 20px;
}

.cs-section__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.cs-section__title {
  margin: 0;
  font-family: Fraunces, Georgia, serif;
  font-size: 20px;
  font-weight: 600;
}

.cs-section__meta {
  font-size: 13px;
  font-weight: 500;
  color: var(--cs-ink-dim);
}
</style>
