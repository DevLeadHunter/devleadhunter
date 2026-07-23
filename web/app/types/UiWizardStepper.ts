/**
 * Props & item types for the reusable `UiWizardStepper` component.
 * @module types/UiWizardStepper
 */

/** A single step of a wizard. */
export type UiWizardStep = {
  /** 1-based step number — also the v-model value of the stepper. */
  id: number
  /** Visible label. */
  label: string
  /** Optional one-line hint shown under the label (hidden on small screens). */
  hint?: string
}

/** Props of the `UiWizardStepper` component. */
export type UiWizardStepperProps = {
  /** Steps to render, left to right. */
  steps: UiWizardStep[]
  /** Current step id (v-model). */
  modelValue: number
}
