<template>
  <div class="card px-6 py-12 text-center">
    <LandingAsterisk class="text-4xl text-[var(--app-accent)]" />
    <h3 class="font-display mt-5 text-2xl font-semibold text-[var(--app-ink)]">{{ props.title }}</h3>
    <p v-if="props.description" class="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-[var(--app-ink-soft)]">
      {{ props.description }}
    </p>
    <div v-if="$slots.action" class="mt-5 flex justify-center">
      <slot name="action" />
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { UiEmptyStateProps } from '~/types/UiEmptyState'

/** Empty-list placeholder in the Atelier look, with an optional call to action. */
const props: UiEmptyStateProps = defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: undefined,
  },
})
</script>
