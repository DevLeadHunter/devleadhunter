/** Semantic variant of a callout annotation. */
export type UiCalloutVariant = 'info' | 'warning' | 'success' | 'neutral'

/**
 * Props of the UiCallout component.
 */
export type UiCalloutProps = {
  variant?: UiCalloutVariant
  icon?: string
}

export type CalloutToneClasses = {
  icon: string
  accent: string
  bg: string
  border: string
}
