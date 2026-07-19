<template>
  <div class="overflow-x-auto rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] p-1.5">
    <ol class="flex min-w-max items-stretch sm:min-w-0">
      <li v-for="(step, index) in steps" :key="step.id" class="flex flex-1 items-center">
        <button
          type="button"
          :disabled="step.id >= modelValue"
          class="flex flex-1 items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors"
          :class="
            step.id === modelValue
              ? 'bg-[var(--app-surface-2)]'
              : step.id < modelValue
                ? 'cursor-pointer hover:bg-[var(--app-surface-2)]/60'
                : 'cursor-default'
          "
          @click="handleStepNavigate(step.id)"
        >
          <span
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-sm font-semibold transition-colors"
            :class="stepNodeClass(step.id)"
          >
            <UiStepCheck v-if="step.id < modelValue" class="h-4 w-4" />
            <template v-else>{{ step.id }}</template>
          </span>
          <span class="min-w-0">
            <span
              class="block text-sm font-semibold"
              :class="step.id === modelValue ? 'text-[var(--app-ink)]' : 'text-[var(--app-ink-soft)]'"
              >{{ step.label }}</span
            >
            <span v-if="step.hint" class="hidden truncate text-[11px] text-[var(--app-faint)] sm:block">
              {{ step.hint }}
            </span>
          </span>
        </button>
        <UIcon
          v-if="index < steps.length - 1"
          name="i-lucide-chevron-right"
          class="mx-0.5 h-4 w-4 shrink-0 text-[var(--app-faint)]"
        />
      </li>
    </ol>
  </div>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { UiWizardStep, UiWizardStepperProps } from '~/types/UiWizardStepper'

/**
 * Defines the component props.
 *
 * Horizontal step timeline used by the app's multi-step flows: the current step
 * is highlighted, completed steps show an animated green check and can be
 * clicked to go back, upcoming steps stay inert.
 */
const props: UiWizardStepperProps = defineProps({
  steps: {
    type: Array as PropType<UiWizardStep[]>,
    required: true,
  },
  modelValue: {
    type: Number,
    required: true,
  },
})

const emit = defineEmits<{
  /** A completed step was clicked — the parent should navigate back to it. */
  'update:modelValue': [step: number]
}>()

/**
 * Classes for a step node based on its state (done / current / upcoming).
 * @param stepId - The step id (1-based).
 * @returns Border, background and text classes.
 */
function stepNodeClass(stepId: number): string {
  if (stepId < props.modelValue) {
    return 'border-[var(--app-green)] bg-[var(--app-green-soft)] text-[var(--app-green)] cursor-pointer'
  }
  if (stepId === props.modelValue) return 'border-[var(--app-ink)] text-[var(--app-ink)]'
  return 'border-[var(--app-line)] text-[var(--app-ink-soft)] cursor-default'
}

/**
 * A step node was clicked — only going back to a completed step is allowed.
 * @param stepId - Target step id.
 */
function handleStepNavigate(stepId: number): void {
  if (stepId < props.modelValue) emit('update:modelValue', stepId)
}
</script>
