<template>
  <Teleport to="body">
    <div
      v-if="props.open"
      class="fixed inset-0 z-[100] flex items-center justify-center backdrop-blur-sm"
      :style="{ backgroundColor: 'var(--app-overlay, rgba(0, 0, 0, 0.7))' }"
    >
      <div class="app-card mx-4 w-full max-w-lg p-6 shadow-[var(--app-shadow-soft)]">
        <div class="mb-4 flex items-center justify-between gap-3">
          <h2 class="font-display text-lg font-semibold text-[var(--app-ink)]">{{ props.title }}</h2>
          <span class="text-xs font-medium text-[var(--app-ink-soft)] tabular-nums">{{ elapsedLabel }}</span>
        </div>

        <ol class="space-y-2.5">
          <li v-for="step in props.steps" :key="step.key" class="flex items-center gap-3">
            <span
              :class="[
                'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border',
                stepBadgeClass(step.state),
              ]"
            >
              <UIcon v-if="step.state === 'done'" name="i-lucide-check" class="h-3.5 w-3.5" />
              <UIcon
                v-else-if="step.state === 'active'"
                name="i-lucide-loader-circle"
                class="h-3.5 w-3.5 animate-spin"
              />
              <UIcon v-else-if="step.state === 'error'" name="i-lucide-x" class="h-3.5 w-3.5" />
              <span v-else class="h-1.5 w-1.5 rounded-full bg-[var(--app-ink-soft)]" aria-hidden="true" />
            </span>
            <span :class="['text-sm', stepTextClass(step.state)]">{{ step.label }}</span>
          </li>
        </ol>

        <div
          v-if="props.logLines.length"
          ref="logRef"
          class="mt-4 max-h-28 space-y-1 overflow-y-auto rounded-lg bg-[var(--app-bg)] px-3 py-2 font-mono text-[11px] leading-relaxed text-[var(--app-ink-soft)]"
        >
          <p v-for="(line, index) in props.logLines" :key="index">{{ line }}</p>
        </div>

        <UiCallout v-if="props.errorMessage" variant="danger" class="mt-4">{{ props.errorMessage }}</UiCallout>

        <div class="mt-5 flex justify-end">
          <button type="button" class="app-btn-secondary" @click="emit('close')">
            {{ props.isRunning ? 'Masquer (la génération continue)' : 'Fermer' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import { computed, nextTick, ref, watch } from 'vue'
import type {
  UiVideoGenerationModalEmits,
  UiVideoGenerationModalProps,
  VideoGenerationStep,
  VideoGenerationStepState,
} from '~/types/UiVideoGenerationModal'

const props: UiVideoGenerationModalProps = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    default: 'Génération de la vidéo',
  },
  steps: {
    type: Array as PropType<VideoGenerationStep[]>,
    default: (): VideoGenerationStep[] => [],
  },
  logLines: {
    type: Array as PropType<string[]>,
    default: (): string[] => [],
  },
  elapsedSeconds: {
    type: Number,
    default: 0,
  },
  errorMessage: {
    type: String,
    default: '',
  },
  isRunning: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiVideoGenerationModalEmits> = defineEmits<UiVideoGenerationModalEmits>()

const logRef: Ref<HTMLDivElement | null> = ref(null)

/** Elapsed time as m:ss, next to the title. */
const elapsedLabel: ComputedRef<string> = computed((): string => {
  const minutes: number = Math.floor(props.elapsedSeconds / 60)
  const seconds: number = props.elapsedSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
})

/**
 * Badge classes for a step marker.
 * @param state - The step's lifecycle state.
 * @returns Tailwind classes for the round marker.
 */
function stepBadgeClass(state: VideoGenerationStepState): string {
  if (state === 'done') return 'border-[var(--app-green)]/40 bg-[var(--app-green)]/15 text-[var(--app-green)]'
  if (state === 'active') return 'border-[var(--app-ink)] bg-[var(--app-surface-2)] text-[var(--app-ink)]'
  if (state === 'error') return 'border-[var(--app-red)]/40 bg-[var(--app-red)]/15 text-[var(--app-red)]'
  return 'border-[var(--app-line)] bg-[var(--app-surface)]'
}

/**
 * Text classes for a step label.
 * @param state - The step's lifecycle state.
 * @returns Tailwind classes for the label.
 */
function stepTextClass(state: VideoGenerationStepState): string {
  if (state === 'active') return 'font-medium text-[var(--app-ink)]'
  if (state === 'error') return 'font-medium text-[var(--app-red)]'
  if (state === 'pending') return 'text-[var(--app-ink-soft)]'
  return 'text-[var(--app-ink)]'
}

// Keep the newest log line in view as they stream in.
watch(
  (): number => props.logLines.length,
  async (): Promise<void> => {
    await nextTick()
    if (logRef.value) logRef.value.scrollTop = logRef.value.scrollHeight
  },
)
</script>
