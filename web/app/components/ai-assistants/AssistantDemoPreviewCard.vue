<template>
  <div class="card overflow-hidden p-0">
    <div class="border-b border-[var(--app-line)] px-5 py-4">
      <h2 class="font-semibold text-[var(--app-ink)]">Aperçu de la page de démo</h2>
      <p class="text-xs text-[var(--app-ink-soft)]">
        Ce que le prospect reçoit : la scène, la conversation, le prix. Vos visites ici ne comptent pas.
      </p>
    </div>
    <iframe
      :src="props.demoUrl"
      class="h-[720px] w-full border-0 bg-white"
      title="Aperçu de la page de démo"
      loading="lazy"
    />
  </div>
</template>

<script lang="ts" setup>
import type { AssistantDemoPreviewCardProps } from '~/types/AssistantDemoPreviewCard'

const props: AssistantDemoPreviewCardProps = defineProps({
  demoUrl: {
    type: String,
    required: true,
  },
})
</script>
