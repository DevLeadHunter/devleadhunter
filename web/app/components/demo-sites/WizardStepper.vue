<template>
  <!-- Vertical rail (builder sidebar) -->
  <nav v-if="orientation === 'vertical'" aria-label="Étapes du builder">
    <ol class="flex flex-col">
      <li v-for="(step, index) in steps" :key="step.id" class="flex flex-col">
        <!-- Connector -->
        <div
          v-if="index > 0"
          class="my-1 ml-3.5 h-5 w-px rounded-full transition-colors duration-500"
          :class="currentStep > step.id - 1 ? 'bg-[var(--app-ink)]' : 'bg-[var(--app-line)]'"
        ></div>

        <!-- Node (past steps are clickable to go back) -->
        <button
          type="button"
          class="group flex items-center gap-2.5"
          :class="step.id < currentStep ? 'cursor-pointer' : 'cursor-default'"
          :aria-current="currentStep === step.id ? 'step' : undefined"
          :disabled="step.id >= currentStep"
          @click="emit('navigate', step.id)"
        >
          <span
            class="font-label flex h-7 w-7 items-center justify-center rounded-full text-[0.65rem] font-medium transition-all duration-300"
            :class="nodeClass(step.id)"
          >
            <UIcon v-if="currentStep > step.id" name="i-lucide-check" class="h-3.5 w-3.5" />
            <span v-else>0{{ step.id }}</span>
          </span>
          <span class="text-xs font-medium whitespace-nowrap transition-colors" :class="labelClass(step.id)">
            {{ step.label }}
          </span>
        </button>
      </li>
    </ol>
  </nav>

  <!-- Horizontal bar (default) -->
  <nav v-else class="mb-8" aria-label="Étapes du builder">
    <ol class="flex items-center">
      <li v-for="(step, index) in steps" :key="step.id" class="flex items-center" :class="index > 0 ? 'flex-1' : ''">
        <!-- Connector -->
        <div
          v-if="index > 0"
          class="mx-3 h-px flex-1 rounded-full transition-colors duration-500"
          :class="currentStep > step.id - 1 ? 'bg-[var(--app-ink)]' : 'bg-[var(--app-line)]'"
        ></div>

        <!-- Node (past steps are clickable to go back) -->
        <button
          type="button"
          class="group flex items-center gap-2"
          :class="step.id < currentStep ? 'cursor-pointer' : 'cursor-default'"
          :aria-current="currentStep === step.id ? 'step' : undefined"
          :disabled="step.id >= currentStep"
          @click="emit('navigate', step.id)"
        >
          <span
            class="font-label flex h-7 w-7 items-center justify-center rounded-full text-[0.65rem] font-medium transition-all duration-300"
            :class="nodeClass(step.id)"
          >
            <UIcon v-if="currentStep > step.id" name="i-lucide-check" class="h-3.5 w-3.5" />
            <span v-else>0{{ step.id }}</span>
          </span>
          <span
            class="hidden text-xs font-medium whitespace-nowrap transition-colors md:block"
            :class="labelClass(step.id)"
          >
            {{ step.label }}
          </span>
        </button>
      </li>
    </ol>
  </nav>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type {
  DemoSitesWizardStep,
  DemoSitesWizardStepperOrientation,
  DemoSitesWizardStepperProps,
} from '~/types/DemoSitesWizardStepper'

/**
 * Defines the component props.
 */
const props: DemoSitesWizardStepperProps = defineProps({
  steps: {
    type: Array as PropType<DemoSitesWizardStep[]>,
    required: true,
  },
  currentStep: {
    type: Number,
    required: true,
  },
  orientation: {
    type: String as PropType<DemoSitesWizardStepperOrientation>,
    default: 'horizontal',
  },
})

const emit = defineEmits<{
  /** A past step node was clicked — the wizard may navigate back to it. */
  (e: 'navigate', stepId: number): void
}>()

/**
 * Classes of a step node for its state (done / active / upcoming).
 * @param stepId - The node's step id.
 * @returns Tailwind classes for the node circle.
 */
function nodeClass(stepId: number): string {
  if (props.currentStep > stepId) {
    return 'bg-[var(--app-green-soft)] text-[var(--app-green)] group-hover:bg-[var(--app-green)] group-hover:text-white'
  }
  if (props.currentStep === stepId) {
    return 'bg-[var(--app-ink)] text-[var(--app-btn-text)] ring-2 ring-[var(--app-accent)] ring-offset-2 ring-offset-[var(--app-bg)]'
  }
  return 'border border-[var(--app-line)] bg-[var(--app-surface)] text-[var(--app-faint)]'
}

/**
 * Classes of a step label for its state (done / active / upcoming).
 * @param stepId - The label's step id.
 * @returns Tailwind classes for the label.
 */
function labelClass(stepId: number): string {
  if (props.currentStep === stepId) return 'text-[var(--app-ink)]'
  if (stepId < props.currentStep) return 'text-[var(--app-ink-soft)] group-hover:text-[var(--app-ink)]'
  return 'text-[var(--app-faint)]'
}
</script>
