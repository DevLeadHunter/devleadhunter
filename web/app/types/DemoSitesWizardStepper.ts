/** One step of the website builder wizard. */
export type DemoSitesWizardStep = {
  /** 1-based step number. */
  id: number
  /** Visible label. */
  label: string
}

/** Visual orientation of the wizard stepper. */
export type DemoSitesWizardStepperOrientation = 'horizontal' | 'vertical'

/**
 * Props for the DemoSitesWizardStepper component.
 */
export type DemoSitesWizardStepperProps = {
  /** Ordered wizard steps. */
  steps: DemoSitesWizardStep[]
  /** Currently active step id. */
  currentStep: number
  /** Layout direction (vertical fits the builder side rail). */
  orientation?: DemoSitesWizardStepperOrientation
}
