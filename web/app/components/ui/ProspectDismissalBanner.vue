<template>
  <div
    class="flex items-start justify-between gap-3 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)] px-3 py-2.5"
  >
    <span class="flex items-start gap-2 text-xs font-medium text-[var(--app-ink)]">
      <UIcon name="i-lucide-archive" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>
        {{ props.isDismissedByApp ? "Écarté par l'app" : 'Écarté' }} — hors des listes, des campagnes et des
        enrichissements.
        <span v-if="props.reason" class="mt-0.5 block font-normal text-[var(--app-ink-soft)]">
          « {{ props.reason }} »
        </span>
      </span>
    </span>
    <button type="button" class="btn-secondary shrink-0 text-xs" :disabled="props.isRestoring" @click="emit('restore')">
      <UIcon v-if="props.isRestoring" name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
      Remettre
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { UiProspectDismissalBannerEmits, UiProspectDismissalBannerProps } from '~/types/UiProspectDismissalBanner'
import type { EmitFn, PropType } from 'vue'

const props: UiProspectDismissalBannerProps = defineProps({
  reason: {
    type: String as PropType<string | null>,
    default: null,
  },
  isDismissedByApp: {
    type: Boolean,
    required: true,
  },
  isRestoring: {
    type: Boolean,
    required: true,
  },
})

const emit: EmitFn<UiProspectDismissalBannerEmits> = defineEmits<UiProspectDismissalBannerEmits>()
</script>
