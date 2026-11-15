<template>
  <section class="rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5">
    <div class="flex items-center justify-between gap-3">
      <h2 class="min-w-0 truncate text-base font-semibold text-[var(--app-ink)]">{{ props.highlight.title }}</h2>
      <span
        class="inline-flex shrink-0 items-center rounded-full bg-[var(--app-green-soft)] px-2.5 py-0.5 text-xs font-medium whitespace-nowrap text-[var(--app-green)]"
      >
        {{ props.highlight.badge }}
      </span>
    </div>
    <p v-if="props.highlight.meta" class="mt-1 text-sm text-[var(--app-ink-soft)]">{{ props.highlight.meta }}</p>
    <p v-if="props.highlight.text" class="mt-2 text-sm leading-normal text-[var(--app-ink)]">
      {{ props.highlight.text }}
    </p>
    <NuxtLink :to="props.highlight.link_to" class="app-btn-primary mt-4 w-full @xl:w-auto pointer-coarse:min-h-11">
      {{ props.highlight.link_label }}
    </NuxtLink>
  </section>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { ModuleAssistantHighlight } from '~/types/ModuleAssistant'
import type { UiModuleAssistantHighlightCardProps } from '~/types/UiModuleAssistantHighlightCard'

/** The one thing an answer of a module's assistant puts first, with the link that handles it. */
const props: UiModuleAssistantHighlightCardProps = defineProps({
  highlight: {
    type: Object as PropType<ModuleAssistantHighlight>,
    required: true,
  },
})
</script>
