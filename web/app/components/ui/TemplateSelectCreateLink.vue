<template>
  <div :class="wrapperClass" class="flex justify-end">
    <button
      type="button"
      class="flex items-center gap-1 text-[11px] font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
      @click="emit('click')"
    >
      <UIcon name="i-lucide-plus" class="h-3 w-3" />
      Nouveau modèle
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { UiTemplateSelectCreateLinkEmits } from '~/types/UiTemplateSelectCreateLink'
import type { EmitFn } from 'vue'
/** Inline « create template » link for TemplateSelect. */
defineProps({
  wrapperClass: {
    type: String,
    default: '',
  },
})

const emit: EmitFn<UiTemplateSelectCreateLinkEmits> = defineEmits<UiTemplateSelectCreateLinkEmits>()
</script>
