import type { CreditSettings } from '~/types'

export type LandingPricingProps = {
  settings: CreditSettings | null
  loading: boolean
}

/** One credit metric displayed in the pricing card. */
export type LandingPricingStat = {
  value: string
  labelKey: string
}
