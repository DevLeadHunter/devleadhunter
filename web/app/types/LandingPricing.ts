import type { CreditSettings } from '~/types'

/**
 * Props for the LandingPricing component.
 */
export interface LandingPricingProps {
  /** Credit settings fetched from the API, or null while loading/on error. */
  settings: CreditSettings | null
  /** Whether the credit settings are still loading. */
  loading: boolean
}
