<template>
  <div>
    <!-- ── Mobile : indicateur compact, jamais de scroll horizontal ───────── -->
    <div class="rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] p-4 md:hidden">
      <div class="flex items-center gap-1.5">
        <span
          v-for="step in steps"
          :key="step.id"
          class="h-1 flex-1 rounded-full transition-colors"
          :class="segmentClass(step.id)"
        />
      </div>
      <p class="app-label mt-3">Étape {{ modelValue }} sur {{ steps.length }}</p>
      <p class="mt-1 text-base leading-snug font-semibold text-[var(--app-ink)]">{{ activeStep?.label }}</p>
      <p v-if="activeStep?.hint" class="mt-0.5 text-xs leading-snug text-[var(--app-ink-soft)]">
        {{ activeStep.hint }}
      </p>
    </div>

    <!-- ── Desktop : timeline, une colonne par étape ──────────────────────── -->
    <ol
      class="hidden rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] p-2 md:flex md:items-stretch"
      aria-label="Progression"
    >
      <li v-for="(step, index) in steps" :key="step.id" class="flex min-w-0 flex-1">
        <button
          type="button"
          :disabled="step.id >= modelValue"
          :aria-current="step.id === modelValue ? 'step' : undefined"
          class="flex w-full flex-col items-center rounded-xl pt-3 pb-3.5 transition-colors"
          :class="
            step.id === modelValue
              ? 'bg-[var(--app-surface-2)]'
              : step.id < modelValue
                ? 'cursor-pointer hover:bg-[var(--app-surface-2)]/60'
                : 'cursor-default'
          "
          @click="handleStepNavigate(step.id)"
        >
          <!-- Pastille + traits de liaison, centrés d'eux-mêmes -->
          <span class="flex w-full items-center gap-2">
            <span
              class="h-px flex-1 rounded-full transition-colors"
              :class="index === 0 ? 'invisible' : connectorClass(step.id - 1)"
            />
            <span
              class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-sm font-semibold transition-colors"
              :class="stepNodeClass(step.id)"
            >
              <UiStepCheck v-if="step.id < modelValue" class="h-4 w-4" />
              <template v-else>{{ step.id }}</template>
            </span>
            <span
              class="h-px flex-1 rounded-full transition-colors"
              :class="index === steps.length - 1 ? 'invisible' : connectorClass(step.id)"
            />
          </span>

          <!-- Libellé : au large sous la pastille, il peut passer à la ligne -->
          <span class="mt-2.5 block px-2 text-center text-balance">
            <span
              class="block text-[13px] leading-snug font-semibold"
              :class="step.id === modelValue ? 'text-[var(--app-ink)]' : 'text-[var(--app-ink-soft)]'"
            >
              {{ step.label }}
            </span>
            <span v-if="step.hint" class="mt-0.5 block text-[11px] leading-snug text-[var(--app-faint)]">
              {{ step.hint }}
            </span>
          </span>
        </button>
      </li>
    </ol>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import type { UiWizardStep, UiWizardStepperProps } from '~/types/UiWizardStepper'

/**
 * Defines the component props.
 *
 * Step progress for the app's multi-step flows. Below `md` it collapses to a
 * compact « Étape 2 sur 4 » indicator (segments + current label) so nothing ever
 * scrolls sideways; from `md` up it renders the full timeline, one column per
 * step, with an animated green check on completed steps that can be clicked to
 * go back.
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

/** The step currently being shown. */
const activeStep: ComputedRef<UiWizardStep | undefined> = computed((): UiWizardStep | undefined =>
  props.steps.find((step: UiWizardStep): boolean => step.id === props.modelValue),
)

/**
 * Classes for a step node based on its state (done / current / upcoming).
 * @param stepId - The step id (1-based).
 * @returns Border, background and text classes.
 */
function stepNodeClass(stepId: number): string {
  if (stepId < props.modelValue) {
    return 'border-[var(--app-green)] bg-[var(--app-green-soft)] text-[var(--app-green)]'
  }
  if (stepId === props.modelValue) return 'border-[var(--app-ink)] text-[var(--app-ink)]'
  return 'border-[var(--app-line)] text-[var(--app-ink-soft)]'
}

/**
 * Classes for the line drawn after a given step.
 * @param stepId - The step the connector starts from (1-based).
 * @returns Background classes for the 1px line.
 */
function connectorClass(stepId: number): string {
  return stepId < props.modelValue ? 'bg-[var(--app-green)]' : 'bg-[var(--app-line)]'
}

/**
 * Classes for a segment of the mobile progress bar.
 * @param stepId - The step the segment stands for (1-based).
 * @returns Background classes for the segment.
 */
function segmentClass(stepId: number): string {
  if (stepId < props.modelValue) return 'bg-[var(--app-green)]'
  if (stepId === props.modelValue) return 'bg-[var(--app-ink)]'
  return 'bg-[var(--app-line)]'
}

/**
 * A step node was clicked — only going back to a completed step is allowed.
 * @param stepId - Target step id.
 */
function handleStepNavigate(stepId: number): void {
  if (stepId < props.modelValue) emit('update:modelValue', stepId)
}
</script>
