/** One step of the website builder wizard. */
export interface DemoSitesWizardStep {
  /** 1-based step number. */
  id: number
  /** Visible label. */
  label: string
}

/**
 * Props for the DemoSitesWizardStepper component.
 */
export interface DemoSitesWizardStepperProps {
  /** Ordered wizard steps. */
  steps: DemoSitesWizardStep[]
  /** Currently active step id. */
  currentStep: number
}
