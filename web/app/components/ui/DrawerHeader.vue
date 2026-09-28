<template>
  <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
    <button
      v-if="props.showBack"
      type="button"
      class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
      title="Revenir au volet précédent"
      aria-label="Revenir au volet précédent"
      @click="emit('back')"
    >
      <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
    </button>
    <div
      class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)]"
    >
      <UIcon :name="props.icon" class="h-4 w-4 text-[var(--app-ink-soft)]" />
    </div>
    <div class="min-w-0 flex-1">
      <slot name="badges" />
      <h2 :id="props.titleId" class="truncate text-base leading-tight font-semibold text-[var(--app-ink)]">
        {{ props.title }}
      </h2>
      <slot name="subtitle">
        <p v-if="props.subtitle" class="text-muted mt-0.5 truncate text-sm">{{ props.subtitle }}</p>
      </slot>
    </div>
    <button
      type="button"
      class="flex h-7 w-7 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
      aria-label="Fermer"
      @click="emit('close')"
    >
      <UIcon name="i-lucide-x" class="h-4 w-4" />
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { EmitFn } from 'vue'
import type { UiDrawerHeaderEmits, UiDrawerHeaderProps } from '~/types/UiDrawerHeader'

const props: UiDrawerHeaderProps = defineProps({
  title: {
    type: String,
    required: true,
  },
  icon: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: undefined,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
  titleId: {
    type: String,
    default: undefined,
  },
})

const emit: EmitFn<UiDrawerHeaderEmits> = defineEmits<UiDrawerHeaderEmits>()
</script>
