/**
 * Props & item types for the reusable `UiWizardStepper` component.
 */

/** A single step of a wizard. */
export type UiWizardStep = {
  id: number
  label: string
  hint?: string
}

/** Props of the `UiWizardStepper` component. */
export type UiWizardStepperProps = {
  steps: UiWizardStep[]
  modelValue: number
}
