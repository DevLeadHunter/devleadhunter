/**
 * Props & item types for the reusable `UiWizardStepper` component.
 */

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

export type UiWizardStepperEmits = {
  'update:modelValue': [step: number]
}
