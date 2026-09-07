<template>
  <div
    class="flex items-start justify-between gap-3 rounded-lg border border-[var(--app-red)]/40 bg-[var(--app-red-soft)] px-3 py-2.5"
  >
    <span class="flex items-start gap-2 text-xs font-medium text-[var(--app-red)]">
      <UIcon name="i-lucide-ban" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>
        Ne plus contacter — exclu des campagnes et des SMS.
        <span v-if="props.reason" class="mt-0.5 block font-normal text-[var(--app-ink-soft)]">
          « {{ props.reason }} »
        </span>
      </span>
    </span>
    <button type="button" class="btn-secondary shrink-0 text-xs" :disabled="props.isToggling" @click="emit('resume')">
      <UIcon v-if="isToggling" name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
      Réactiver
    </button>
  </div>
</template>

<script lang="ts" setup>
import type {
  UiProspectDoNotContactBannerEmits,
  UiProspectDoNotContactBannerProps,
} from '~/types/UiProspectDoNotContactBanner'
import type { EmitFn, PropType } from 'vue'

/** Red « ne plus contacter » status banner with its « Réactiver » action. */
const props: UiProspectDoNotContactBannerProps = defineProps({
  reason: {
    type: String as PropType<string | null>,
    default: null,
  },
  isToggling: {
    type: Boolean,
    required: true,
  },
})

const emit: EmitFn<UiProspectDoNotContactBannerEmits> = defineEmits<UiProspectDoNotContactBannerEmits>()
</script>
