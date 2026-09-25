<template>
  <div class="card overflow-hidden p-0">
    <div class="flex items-start justify-between gap-3 border-b border-[var(--app-line)] px-5 py-4">
      <div>
        <h2 class="font-semibold text-[var(--app-ink)]">Aperçu de la page de démo</h2>
        <p class="text-xs text-[var(--app-ink-soft)]">
          Ce que le prospect reçoit : la scène, la conversation, le prix. Vos visites ici ne comptent pas.
        </p>
      </div>
      <button
        type="button"
        class="btn-secondary inline-flex h-8 shrink-0 items-center gap-1.5 text-xs"
        title="Recharger l'aperçu"
        @click="reloads += 1"
      >
        <UIcon name="i-lucide-refresh-cw" class="h-3.5 w-3.5" />
        Recharger
      </button>
    </div>
    <iframe
      :key="`${props.reloadKey}-${reloads}`"
      :src="props.demoUrl"
      class="w-full border-0 bg-white"
      :class="props.heightClass"
      title="Aperçu de la page de démo"
      loading="lazy"
    />
  </div>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import { ref } from 'vue'
import type { AssistantDemoPreviewCardProps } from '~/types/AssistantDemoPreviewCard'

/** The demo page in a frame; a new `reloadKey` (a save) or the button reloads it. */
const props: AssistantDemoPreviewCardProps = defineProps({
  demoUrl: {
    type: String,
    required: true,
  },
  reloadKey: {
    type: Number,
    default: 0,
  },
  heightClass: {
    type: String,
    default: 'h-[720px]',
  },
})

/** Manual reloads, added to the key the page changes on a save. */
const reloads: Ref<number> = ref(0)
</script>
